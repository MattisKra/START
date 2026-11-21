"""Reader calls. A reader spec is  provider:model:effort[:noimage]  e.g.
    anthropic:claude-fable-5-2:low          Anthropic SDK, needs ANTHROPIC_API_KEY
    openai:gpt-6.1-terra:medium             OpenAI Responses API, needs OPENAI_KEY
    openai:gpt-6-luna:low:noimage           fast tier, text only
    openrouter:anthropic/claude-fable-5.2:low   OpenRouter chat completions, needs OPENROUTER_API_KEY (offline tests, no team keys)
Each call returns (ReaderCase, meta). No retries beyond one (the round lasts 60 s); the caller owns deadlines.
"""

import base64
import copy
import json
import os
import time
from dataclasses import dataclass

import requests

from claimbot import config
from claimbot.case import Case

from .prompt import FAST_NOTE, INSTRUCTIONS, case_text
from .schema import ReaderCase


@dataclass(frozen=True)
class Spec:
    provider: str
    model: str
    effort: str
    image: bool = True

    @property
    def name(self) -> str:
        return f"{self.provider}:{self.model}:{self.effort}" + ("" if self.image else ":noimage")


def parse_spec(s: str) -> Spec:
    parts = s.split(":")
    if len(parts) < 3:
        raise ValueError(f"reader spec must be provider:model:effort[:noimage], got {s!r}")
    return Spec(parts[0], parts[1], parts[2], image=not (len(parts) > 3 and parts[3] == "noimage"))


def _meta(spec, t0, usage=None, rid=None):
    return {"reader": spec.name, "provider": spec.provider, "model": spec.model, "effort": spec.effort, "images": spec.image,
            "latency_s": round(time.monotonic() - t0, 2), "usage": usage, "response_id": rid}


# ---------------------------------------------------------------- OpenAI
def _openai(case: Case, spec: Spec, fast: bool, instructions: str | None = None, *, schema=ReaderCase, max_tokens=None):
    from openai import OpenAI
    if not config.OPENAI_KEY:
        raise RuntimeError("OPENAI_KEY is not set (put it in .env)")
    t0 = time.monotonic()
    content = [{"type": "input_text", "text": case_text(case)}]
    if spec.image:
        for mime, raw in case.image_blobs:
            content.append({"type": "input_image", "image_url": f"data:{mime};base64,{base64.b64encode(raw).decode()}", "detail": "high"})
    resp = OpenAI(api_key=config.OPENAI_KEY, timeout=config.LLM_TIMEOUT_S, max_retries=1).responses.parse(
        model=spec.model, instructions=(instructions or INSTRUCTIONS) + (FAST_NOTE if fast else ""), input=[{"role": "user", "content": content}],
        reasoning={"effort": spec.effort}, text_format=schema, **({"max_output_tokens": max_tokens} if max_tokens else {}))
    if resp.output_parsed is None:
        raise RuntimeError(f"{spec.name} returned no parsed output (status={resp.status})")
    return resp.output_parsed, _meta(spec, t0, resp.usage.model_dump() if resp.usage else None, resp.id)


# ---------------------------------------------------------------- Anthropic
def _anthropic(case: Case, spec: Spec, fast: bool, instructions: str | None = None, *, schema=ReaderCase, max_tokens=None):
    import anthropic
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set (put it in .env)")
    t0 = time.monotonic()
    blocks = []
    if spec.image:
        for mime, raw in case.image_blobs:
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": base64.standard_b64encode(raw).decode()}})
    blocks.append({"type": "text", "text": case_text(case)})
    resp = anthropic.Anthropic(timeout=config.LLM_TIMEOUT_S, max_retries=1).messages.parse(
        model=spec.model, max_tokens=max_tokens or 16000, system=(instructions or INSTRUCTIONS) + (FAST_NOTE if fast else ""),
        messages=[{"role": "user", "content": blocks}], output_config={"effort": spec.effort}, output_format=schema)
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"{spec.name} refused")
    if resp.parsed_output is None:
        raise RuntimeError(f"{spec.name} returned no parsed output (stop_reason={resp.stop_reason})")
    return resp.parsed_output, _meta(spec, t0, resp.usage.model_dump() if resp.usage else None, resp.id)


# ---------------------------------------------------------------- OpenRouter (chat completions, flattened strict schema)
def strict_schema(model_cls) -> dict:
    """Pydantic JSON schema with $defs inlined, every property required, additionalProperties false (works across providers)."""
    root = model_cls.model_json_schema()
    defs = root.get("$defs", {})

    def walk(n):
        if isinstance(n, dict):
            if "$ref" in n:
                return walk(copy.deepcopy(defs[n["$ref"].split("/")[-1]]))
            n = {k: walk(v) for k, v in n.items() if k not in ("title", "default", "$defs")}
            if n.get("type") == "object" and "properties" in n:
                n["additionalProperties"] = False
                n["required"] = list(n["properties"])
            return n
        if isinstance(n, list):
            return [walk(x) for x in n]
        return n

    return walk(root)


def _openrouter(case: Case, spec: Spec, fast: bool, instructions: str | None = None, *, schema=ReaderCase, max_tokens=None):
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    t0 = time.monotonic()
    content = [{"type": "text", "text": case_text(case)}]
    if spec.image:
        for mime, raw in case.image_blobs:
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(raw).decode()}"}})
    body = {"model": spec.model, "max_tokens": max_tokens or 12000, "usage": {"include": True},
            "messages": [{"role": "system", "content": (instructions or INSTRUCTIONS) + (FAST_NOTE if fast else "")}, {"role": "user", "content": content}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "reader_case", "strict": True, "schema": strict_schema(schema)}},
            "provider": {"require_parameters": True}, "reasoning": {"effort": spec.effort}}
    for attempt in (1, 2):
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=body, headers={"Authorization": f"Bearer {key}"},
                          timeout=config.LLM_TIMEOUT_S * 2)
        if r.status_code == 400 and attempt == 1 and "reasoning" in body:
            body.pop("reasoning"); continue
        r.raise_for_status()
        break
    data = r.json()
    raw = (data["choices"][0]["message"].get("content") or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
    est = schema.model_validate(json.loads(raw))
    return est, _meta(spec, t0, data.get("usage"), data.get("id"))


PROVIDERS = {"openai": _openai, "anthropic": _anthropic, "openrouter": _openrouter}


def read(case: Case, spec: Spec, fast: bool = False, instructions: str | None = None, *, schema=ReaderCase, max_tokens=None):
    return PROVIDERS[spec.provider](case, spec, fast, instructions, schema=schema, max_tokens=max_tokens)
