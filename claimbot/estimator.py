"""Calls GPT-6 Luna with structured outputs and returns a CaseEstimate."""

import base64
import mimetypes
import time
from pathlib import Path

from openai import OpenAI

from . import config
from .case import Case
from .schema import CaseEstimate
from .rate_evidence import LOOKUP, RATE_CHECK

INSTRUCTIONS = """\
You are an experienced German insurance claims adjuster for property damage
(Hausrat / Wohngebäude). You receive a policy, a damage description, an invoice
WITHOUT prices, and sometimes photos.

For every invoice line, estimate the fair-value threshold t: the MAXIMUM total
price a claims expert would still consider appropriate for that line. t is 0
when the item is excluded by the policy or not related to the reported damage.

Check every line against three tests:
1. Covered: does any policy exclusion, limit or condition apply?
2. Related: does the item belong to the reported damage (same room, same
   cause, plausible repair step)? Watch for items in other rooms, upgrades,
   unrelated maintenance, and anything the photos contradict.
3. Reasonable: what is the highest net unit price a German tradesperson could
   justify in 2026 for this work or material, and is the invoiced quantity
   plausible for the described damage?

Rules:
- Return exactly one entry per invoice line, in invoice order, with 0-based
  index. Do not merge, split, skip or add lines.
- Prices are NET per unit in EUR. VAT is separate (normally 0.19 in Germany,
  unless the invoice or policy says otherwise).
- p10/p50/p90 describe your uncertainty about the maximum reasonable net unit
  price. Make the range wide when you are unsure.
- t is what the insurer OWES under the policy, not what the work costs on the
  open market. For damaged property (appliances, furniture, electronics) use
  the valuation basis of the applicable clause and endorsements. Depreciate
  only when the policy requires it. Match the pre-loss specification when
  pricing like-for-like new replacements.
- Proportional reductions in the policy (e.g. indemnity halved for a missing
  surge protector, deductibles, sub-limits) go into payout_fraction, not into
  the unit price.
- Price and quantity are always estimated AS IF the line were valid, even for
  lines you think are excluded or unrelated. Validity goes only into p_valid.
- p_valid is your probability that the line passes both the coverage and the
  relatedness tests. Use values near 0 or 1 only when the documents are clear.
"""


INSTRUCTIONS += RATE_CHECK


def _client() -> OpenAI:
    if not config.OPENAI_KEY:
        raise RuntimeError("OPENAI_KEY is not set (put it in .env)")
    return OpenAI(api_key=config.OPENAI_KEY, timeout=config.LLM_TIMEOUT_S, max_retries=1)


def _image_part(blob: tuple[str, bytes]) -> dict:
    mime, raw = blob
    data = base64.b64encode(raw).decode()
    return {"type": "input_image", "image_url": f"data:{mime};base64,{data}", "detail": "high"}


def case_text(case: Case, references: str | None = None) -> str:
    """The case as prompt text. `references` is the optional hint block from the case memory (memory.py); without it
    the text is exactly what it was before the memory existed."""
    text = case.refs + (
        f"=== policy.txt ===\n{case.policy}\n\n"
        f"=== description.txt ===\n{case.description}\n\n"
        f"=== invoice (extracted from PDF) ===\n{case.invoice_text}\n"
    )
    if case.image_blobs:
        text += f"\n{len(case.image_blobs)} photo(s) of the damage are attached.\n"
    if references:
        text += f"\n=== hints from earlier claims (case memory) ===\n{references}\n"
    return text


def build_input(case: Case, web: bool = False, references: str | None = None, *, selective: bool = False) -> list[dict]:
    hint = LOOKUP if selective else WEB_HINT if web else ""
    content = [{"type": "input_text", "text": hint + case_text(case, references)}]
    content += [_image_part(b) for b in case.image_blobs]
    return [{"role": "user", "content": content}]


WEB_HINT = "Use the web search tool to check a price before answering. " + LOOKUP


def estimate(case: Case, effort: str = config.EFFORT, model: str | None = None, web: bool = False,
             references: str | None = None, *, selective: bool = False) -> tuple[CaseEstimate, dict]:
    """Returns the parsed estimate and some metadata (latency, token usage)."""
    model = model or config.MODEL
    t0 = time.monotonic()
    extra = {"tools": [{"type": "web_search"}], "tool_choice": "required"} if web else {}
    if selective:
        extra = {"tools": [{"type": "web_search"}], "tool_choice": "auto", "max_tool_calls": 2}
    if web or selective:
        extra["include"] = ["web_search_call.action.sources"]
    from . import oai
    resp = oai.call(lambda client: client.responses.parse(
        model=model,
        instructions=INSTRUCTIONS,
        **extra,
        input=build_input(case, web, references, selective=selective),
        reasoning={"effort": effort},
        text_format=CaseEstimate,
    ), timeout=config.LLM_TIMEOUT_S)
    parsed = resp.output_parsed
    if parsed is None:
        raise RuntimeError(f"model returned no parsed output (status={resp.status})")
    meta = {
        "model": model,
        "effort": effort,
        "web": web or selective,
        "web_searches": 0,
        "latency_s": round(time.monotonic() - t0, 2),
        "usage": resp.usage.model_dump() if resp.usage else None,
        "response_id": resp.id,
    }
    if web or selective:
        calls = [o for o in (resp.output or []) if getattr(o, "type", None) == "web_search_call"]
        actions = [call.action for call in calls if getattr(call, "action", None) is not None]
        meta["web_searches"] = sum(action.type == "search" for action in actions)
        meta["web_calls_without_action"] = len(calls) - len(actions)
        meta["search_mode"] = "selective" if selective else "required"
        meta["web_actions"] = [action.model_dump(exclude_none=True) for action in actions]
    return parsed, meta
