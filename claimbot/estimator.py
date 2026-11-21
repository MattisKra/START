"""Calls GPT-6 Luna with structured outputs and returns a CaseEstimate."""

import base64
import mimetypes
import time
from pathlib import Path

from openai import OpenAI

from . import config
from .case import Case
from .schema import CaseEstimate

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
  the policy's valuation basis: usually the pre-loss / time value after
  depreciation for age and wear ("no improvement"), not the price of new
  equipment. Old consumer electronics are often worth a small fraction of the
  new price.
- Proportional reductions in the policy (e.g. indemnity halved for a missing
  surge protector, deductibles, sub-limits) go into payout_fraction, not into
  the unit price.
- Price and quantity are always estimated AS IF the line were valid, even for
  lines you think are excluded or unrelated. Validity goes only into p_valid.
- p_valid is your probability that the line passes both the coverage and the
  relatedness tests. Use values near 0 or 1 only when the documents are clear.
"""


def _client() -> OpenAI:
    if not config.OPENAI_KEY:
        raise RuntimeError("OPENAI_KEY is not set (put it in .env)")
    return OpenAI(api_key=config.OPENAI_KEY, timeout=config.LLM_TIMEOUT_S, max_retries=1)


def _image_part(path: Path) -> dict:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode()
    return {"type": "input_image", "image_url": f"data:{mime};base64,{data}", "detail": "high"}


def build_input(case: Case) -> list[dict]:
    text = (
        f"=== policy.txt ===\n{case.policy}\n\n"
        f"=== description.txt ===\n{case.description}\n\n"
        f"=== invoice (extracted from PDF) ===\n{case.invoice_text}\n"
    )
    if case.images:
        text += f"\n{len(case.images)} photo(s) attached below.\n"
    content = [{"type": "input_text", "text": text}]
    content += [_image_part(p) for p in case.images]
    return [{"role": "user", "content": content}]


def estimate(case: Case, effort: str = config.EFFORT) -> tuple[CaseEstimate, dict]:
    """Returns the parsed estimate and some metadata (latency, token usage)."""
    t0 = time.monotonic()
    resp = _client().responses.parse(
        model=config.MODEL,
        instructions=INSTRUCTIONS,
        input=build_input(case),
        reasoning={"effort": effort},
        text_format=CaseEstimate,
    )
    parsed = resp.output_parsed
    if parsed is None:
        raise RuntimeError(f"model returned no parsed output (status={resp.status})")
    meta = {
        "model": config.MODEL,
        "effort": effort,
        "latency_s": round(time.monotonic() - t0, 2),
        "usage": resp.usage.model_dump() if resp.usage else None,
        "response_id": resp.id,
    }
    return parsed, meta
