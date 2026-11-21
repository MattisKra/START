"""Rule engine: reader answer -> (a, b) per line. All arithmetic lives here so it is deterministic and tunable.

    m_i  = justified_qty_i x unit_price_p50_i x (1 + vat_i)            # gross, valuation basis as read
    m_i *= payout_fraction_i
    aggregate limit (L, lines G):   if sum(m_i, G) > L:  m_i *= L / sum   for i in G;   pinned_i = True    (shared rateably)
    anchor (total T, lines G):      'total'       -> scale G so the sum is T;           pinned_i = True
                                    'upper_bound' -> scale down only if the sum > T;    pinned_i = True
    a_i  = KA[pinned_i] x m_i                      (also for lines we believe excluded: the free option, switchable)
    b_i  = 0 if P(valid_i) < B_ZERO_BELOW else KB[pinned_i] x m_i

Defaults: open lines KA 0.90 / KB 0.55, pinned lines KA 0.85 / KB 0.55, b = 0 below P(valid) 2/3. KB was 1.25 / 1.05 in the first review; the audited cost
replay (research/bench/README.md, 17:15 and 17:35) moved it to 0.55.
Every constant can be overridden by an environment variable (FABLE_*), so the calibration loop can move them without code changes.
"""

import math
import os
import re
from dataclasses import asdict, dataclass, field

from .schema import ReaderCase


def _f(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Params:
    ka_open: float = field(default_factory=lambda: _f("FABLE_KA_OPEN", 0.90))
    kb_open: float = field(default_factory=lambda: _f("FABLE_KB_OPEN", 0.55))
    ka_pinned: float = field(default_factory=lambda: _f("FABLE_KA_PINNED", 0.85))
    kb_pinned: float = field(default_factory=lambda: _f("FABLE_KB_PINNED", 0.55))
    b_zero_below: float = field(default_factory=lambda: _f("FABLE_B_ZERO_BELOW", 2 / 3))
    # Excluded / unrelated lines (P(valid) below this): how to set a. 'as_valid' = charge like a valid line (free option, to be
    # disclosed in the write-up), 'zero' = charge nothing, or a fraction of the valid-line charge, e.g. '0.5'.
    excluded_below: float = field(default_factory=lambda: _f("FABLE_EXCLUDED_BELOW", 0.5))
    excluded_a: str = field(default_factory=lambda: os.getenv("FABLE_EXCLUDED_A", "as_valid"))
    max_a_over_median: float = 4.0  # never charge above 4 x our median so the secret cap (>= 4 t) cannot bite


@dataclass
class LineOut:
    index: int          # 0-based invoice order
    a: float
    b: float
    m: float            # gross median after fraction / limits / anchors
    m_raw: float        # before limits and anchors
    q: float
    pinned: bool
    note: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def printed_positions(invoice_text: str) -> list[int]:
    """The POS. numbers printed on the invoice, in order of appearance."""
    return [int(m.group(1)) for m in re.finditer(r"(?m)^\s*(\d{1,3})\s{2,}\S", invoice_text)]


def compute(est: ReaderCase, params: Params | None = None) -> list[LineOut]:
    p = params or Params()
    lines = sorted(est.lines, key=lambda l: l.index)
    out: dict[int, LineOut] = {}
    for l in lines:
        q = min(max(l.p_valid, 0.0), 1.0)
        if not (l.covered and l.related):
            q = min(q, 0.15)  # the booleans and the probability disagree: trust the veto
        qty = l.quantity_justified if l.quantity_justified and l.quantity_justified > 0 else l.quantity_invoiced
        qty = max(min(qty, l.quantity_invoiced) if l.quantity_invoiced > 0 else qty, 0.0)
        vat = l.vat_rate if 0.0 <= l.vat_rate <= 0.3 else 0.19
        pf = min(max(l.payout_fraction, 0.0), 1.0)
        note = ""
        if pf <= 0.0:                       # 'nothing payable' is a validity statement; keep a price so the free option still works
            pf, q, note = 1.0, min(q, 0.05), "payout 0 treated as excluded"
        price = sorted([l.net_unit_price_p10, l.net_unit_price_p50, l.net_unit_price_p90])[1] if l.net_unit_price_p50 <= 0 else l.net_unit_price_p50
        m = max(qty * price * (1 + vat) * pf, 0.0)
        out[l.index] = LineOut(l.index, 0.0, 0.0, m, m, q, False, note)

    def group(idxs):
        return [out[i] for i in idxs if i in out and out[i].m > 0 and out[i].q >= 0.5]

    for lim in est.aggregate_limits:           # shared rateably
        g = group(lim.line_indices)
        s = sum(x.m for x in g)
        if g and lim.amount_gross > 0 and s > lim.amount_gross:
            f = lim.amount_gross / s
            for x in g:
                x.m *= f; x.pinned = True; x.note = (x.note + f" limit {lim.amount_gross:g}").strip()
    for an in est.anchors:
        g = group(an.line_indices)
        s = sum(x.m for x in g)
        if not g or an.total_gross <= 0 or s <= 0:
            continue
        if an.kind == "total" or s > an.total_gross:
            f = an.total_gross / s
            for x in g:
                x.m *= f; x.pinned = True; x.note = (x.note + f" anchor {an.total_gross:g}").strip()

    for x in out.values():
        ka, kb = (p.ka_pinned, p.kb_pinned) if x.pinned else (p.ka_open, p.kb_open)
        a = ka * x.m
        if x.q < p.excluded_below:
            a = 0.0 if p.excluded_a == "zero" else a * (1.0 if p.excluded_a == "as_valid" else float(p.excluded_a))
        a = min(a, p.max_a_over_median * x.m) if x.m > 0 else 0.0
        b = 0.0 if x.q < p.b_zero_below else kb * x.m
        x.a, x.b = round(a, 2), round(b, 2)
        for v in (x.a, x.b):
            assert math.isfinite(v) and v >= 0, f"bad value on line {x.index}: {v}"
    return [out[i] for i in sorted(out)]


def check(est: ReaderCase, invoice_text: str) -> tuple[list[int], list[str]]:
    """Return the submission index for every reader line (the printed POS number) and a list of warnings."""
    warns = []
    pos = printed_positions(invoice_text)
    n = len(est.lines)
    if sorted(l.index for l in est.lines) != list(range(n)):
        warns.append(f"reader indices are not 0..{n - 1}: {sorted(l.index for l in est.lines)}")
    if len(pos) == n:
        return pos, warns
    warns.append(f"invoice shows {len(pos)} POS numbers but the reader returned {n} lines; assuming 1..{n}")
    return list(range(1, n + 1)), warns
