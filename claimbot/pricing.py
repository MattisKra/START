"""Turns the LLM's beliefs into a (charge a, acceptance limit b) pair per line.

Belief about the fair value t of a line (gross, whole line):
    with prob 1 - q:  t = 0              (excluded or unrelated)
    with prob q:      t ~ LogNormal(mu, sigma)
where q = p_valid, and mu/sigma come from the net unit price p10/p50/p90
scaled by quantity and VAT.

Insurer (b): rejecting a charge a is better iff P(t < a) > REJECT_P (1/3 by
default, from 1.5a(1-p) < a). So b is the REJECT_P-quantile of the belief.
If P(t = 0) alone exceeds REJECT_P, b = 0.

Handyman (a): a fair charge (a <= t) earns a or 1.5a, an inflated one earns
nothing unless the insurer is generous. We maximize a * P(t >= a), which for
a lognormal lands somewhat below the median.
"""

import math
from dataclasses import asdict, dataclass
from statistics import NormalDist

from . import config
from .schema import CaseEstimate, LineEstimate

_N = NormalDist()
_Z90 = _N.inv_cdf(0.9)


@dataclass
class LinePrice:
    index: int
    a: float  # charge price (gross line total)
    b: float  # acceptance limit (gross line total)
    t_median: float  # median gross line total if valid
    q: float  # P(valid)
    sigma: float

    def as_dict(self) -> dict:
        return asdict(self)


def _belief(line: LineEstimate) -> tuple[float, float, float, float]:
    """Returns (q, mu, sigma, median) for the gross line total."""
    q = min(max(line.p_valid, 0.0), 1.0)
    if not (line.covered and line.related):
        q = min(q, 0.15)  # booleans and probability disagree: trust the veto
    qty = max(min(line.quantity_justified, line.quantity_invoiced), 0.0)
    vat = line.vat_rate if 0.0 <= line.vat_rate <= 0.3 else 0.19
    p10, p50, p90 = sorted([line.net_unit_price_p10, line.net_unit_price_p50, line.net_unit_price_p90])
    payout = min(max(line.payout_fraction, 0.0), 1.0)
    if payout <= 0:  # "nothing payable" is a validity question; keep a price so we still charge
        payout, q = 1.0, min(q, 0.05)
    scale = qty * (1 + vat) * payout
    median = p50 * scale
    if median <= 0:
        return 0.0, 0.0, config.MIN_SIGMA, 0.0
    if p10 > 0 and p90 > 0:
        sigma = (math.log(p90) - math.log(p10)) / (2 * _Z90)
    else:
        sigma = 0.5
    sigma = max(sigma, config.MIN_SIGMA)
    return q, math.log(median), sigma, median


def _best_charge(mu: float, sigma: float) -> float:
    """argmax_x x * P(T >= x) for T ~ LogNormal(mu, sigma), by grid search over z."""
    best_x, best_v = 0.0, -1.0
    for i in range(-300, 151):
        z = i / 100
        x = math.exp(mu + sigma * z)
        v = x * (1 - _N.cdf(z))
        if v > best_v:
            best_x, best_v = x, v
    return best_x


def _accept_limit(q: float, mu: float, sigma: float) -> float:
    """Largest x with P(t < x) <= REJECT_P under the mixture belief, raised to at
    least B_VALID_MULT x median for lines we consider valid."""
    p_zero = 1 - q
    if q <= 0 or p_zero >= config.REJECT_P:
        return 0.0
    z = _N.inv_cdf((config.REJECT_P - p_zero) / q)
    return max(math.exp(mu + sigma * z), config.B_VALID_MULT * math.exp(mu))


def price_line(line: LineEstimate) -> LinePrice:
    q, mu, sigma, median = _belief(line)
    if median <= 0:
        return LinePrice(line.index, 0.0, 0.0, 0.0, q, sigma)
    a = _best_charge(mu, sigma) * config.CHARGE_MULT
    b = _accept_limit(q, mu, sigma)
    return LinePrice(line.index, round(a, 2), round(b, 2), round(median, 2), round(q, 3), round(sigma, 3))


def price_case(est: CaseEstimate) -> list[LinePrice]:
    prices = [price_line(l) for l in est.lines]
    prices.sort(key=lambda p: p.index)
    return prices
