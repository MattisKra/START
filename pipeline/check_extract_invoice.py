"""Runs the invoice extraction on archived cases and compares it with the PDF's text layer.

    uv run python -m pipeline.check_extract_invoice case_000 case_003 case_007 case_009

The reference is past-cases/<case>/invoice.txt (pdftotext). For each invoice the
item table is compared as one string with all whitespace removed, so wrapped
descriptions need no parsing: "<pos><description><amount><unit>" per row must
reproduce the printed table exactly. Header fields must occur in the text.
Results go to runs/pipeline/extract_<case>.json.
"""

import json
import re
import sys

from .extract_invoice import ROOT, extract_invoice


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


def reference_tables(text: str) -> list[str]:
    """The printed item table of each invoice, whitespace removed."""
    return [squash(m) for m in re.findall(r"POS\. DESCRIPTION AMOUNT UNIT TOTAL\n(.*?)\nINVOICE\b", text, flags=re.S)]


def check(case: str) -> bool:
    case_dir = ROOT / "past-cases" / case
    text = (case_dir / "invoice.txt").read_text()
    parsed, meta = extract_invoice(case_dir / "invoices.pdf")
    out = ROOT / "runs" / "pipeline" / f"extract_{case}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "extraction": parsed.model_dump()}, indent=2, ensure_ascii=False))

    problems = []
    ref = reference_tables(text)
    if len(ref) != len(parsed.invoices):
        problems.append(f"{len(parsed.invoices)} invoices extracted, {len(ref)} in the PDF text")
    for i, (inv, table) in enumerate(zip(parsed.invoices, ref), 1):
        got = squash("".join(f"{ln.position}{ln.description}{ln.quantity:g}{ln.unit}" for ln in inv.lines))
        if got != table:
            problems.append(f"invoice {i} table differs:\n    extracted {got}\n    printed   {table}")
        for name in ("invoice_no", "date", "due_date", "trade", "issuer_name", "recipient_name"):
            if squash(getattr(inv, name)) not in squash(text):
                problems.append(f"invoice {i} {name}={getattr(inv, name)!r} is not in the PDF text")
        for name in ("issuer_address", "recipient_address"):
            for part in getattr(inv, name).split(", "):
                if squash(part) not in squash(text):
                    problems.append(f"invoice {i} {name} part {part!r} is not in the PDF text")
        if inv.other_text:
            problems.append(f"invoice {i} other_text={inv.other_text!r}")

    usage = meta["usage"] or {}
    n_lines = sum(len(inv.lines) for inv in parsed.invoices)
    print(
        f"{case}: {'OK  ' if not problems else 'DIFF'} {len(parsed.invoices)} invoice(s), {n_lines} line(s), "
        f"{meta['pages']} page(s), {meta['latency_s']} s, {usage.get('input_tokens')} in / {usage.get('output_tokens')} out tokens"
    )
    for p in problems:
        print("  -", p)
    return not problems


if __name__ == "__main__":
    cases = sys.argv[1:] or ["case_000", "case_003", "case_007", "case_009"]
    results = [check(c) for c in cases]
    sys.exit(0 if all(results) else 1)
