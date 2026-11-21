"""Claude models via the Anthropic SDK, same schema and instructions as the OpenAI path."""

import base64
import mimetypes
import os
import time
from pathlib import Path

import anthropic

from . import config
from .case import Case
from .estimator import INSTRUCTIONS, case_text
from .schema import CaseEstimate

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set (put it in .env)")
        # One retry at most: the round only lasts 60 s.
        _client = anthropic.Anthropic(timeout=config.LLM_TIMEOUT_S, max_retries=1)
    return _client


def _image_block(path: Path) -> dict:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}


def estimate(case: Case, effort: str, model: str) -> tuple[CaseEstimate, dict]:
    t0 = time.monotonic()
    content = [_image_block(p) for p in case.images] + [{"type": "text", "text": case_text(case)}]
    resp = _get_client().messages.parse(
        model=model,
        max_tokens=16000,
        system=INSTRUCTIONS,
        messages=[{"role": "user", "content": content}],
        output_config={"effort": effort},
        output_format=CaseEstimate,
    )
    if resp.stop_reason == "refusal":
        cat = resp.stop_details.category if resp.stop_details else None
        raise RuntimeError(f"{model} refused (category {cat})")
    parsed = resp.parsed_output
    if parsed is None:
        raise RuntimeError(f"{model} returned no parsed output (stop_reason={resp.stop_reason})")
    meta = {
        "model": model,
        "effort": effort,
        "latency_s": round(time.monotonic() - t0, 2),
        "usage": resp.usage.model_dump() if resp.usage else None,
        "response_id": resp.id,
    }
    return parsed, meta
