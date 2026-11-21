"""Weighted multi-model ensemble.

Every member (provider, model, effort) produces a full CaseEstimate. Per line we
combine the members' beliefs:
  q      weighted mean of P(valid)
  mu     weighted median of log(median gross total)  (robust to one wild model)
  sigma  sqrt(weighted mean of sigma_i^2 + weighted variance of mu_i)
         so disagreement between models widens the belief
and price (a, b) from that with the usual pricing rules.
"""

import math
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass

from . import config, pricing
from .case import Case
from .schema import CaseEstimate

# Bigger models get more weight.
SIZE_WEIGHT = {
    "claude-fable-5-2": 3.0,
    "claude-opus-5-5": 2.5,
    "gpt-6.2-sol": 2.0,
    "gpt-6.1-terra": 1.5,
}
EFFORT_WEIGHT = {"low": 1.0, "medium": 1.5}
# Extra members with web search; they get this multiplier on top. Off by default: on games 1-5 they cost
# 72 % of the spend and did not improve the result (research/ensemble_analysis/redundancy.py). Sonnet was
# dropped for the same reason. CLAIMS_WEB_MODELS="model,model" turns web members back on.
WEB_MODELS: list[str] = []
WEB_WEIGHT = 1.0
PROVIDER = {m: ("anthropic" if m.startswith("claude-") else "openai") for m in SIZE_WEIGHT}


@dataclass(frozen=True)
class Member:
    provider: str
    model: str
    effort: str
    weight: float
    web: bool = False

    @property
    def name(self) -> str:
        return f"{self.model}/{self.effort}" + ("+web" if self.web else "")


def members() -> list[Member]:
    """CLAIMS_ENSEMBLE="model,model,..." and CLAIMS_ENSEMBLE_EFFORTS="low,medium" override the defaults."""
    models = [m.strip() for m in os.getenv("CLAIMS_ENSEMBLE", ",".join(SIZE_WEIGHT)).split(",") if m.strip()]
    efforts = [e.strip() for e in os.getenv("CLAIMS_ENSEMBLE_EFFORTS", "low,medium").split(",") if e.strip()]
    have_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    out = []
    for m in models:
        provider = PROVIDER.get(m, "anthropic" if m.startswith("claude-") else "openai")
        if provider == "anthropic" and not have_anthropic:
            continue
        for e in efforts:
            out.append(Member(provider, m, e, SIZE_WEIGHT.get(m, 1.0) * EFFORT_WEIGHT.get(e, 1.0)))
    web_models = [m.strip() for m in os.getenv("CLAIMS_WEB_MODELS", ",".join(WEB_MODELS)).split(",") if m.strip()]
    web_efforts = [e.strip() for e in os.getenv("CLAIMS_WEB_EFFORTS", "low,medium").split(",") if e.strip()]
    for m in web_models:
        provider = PROVIDER.get(m, "anthropic" if m.startswith("claude-") else "openai")
        if provider == "anthropic" and not have_anthropic:
            continue
        for e in web_efforts:
            w = SIZE_WEIGHT.get(m, 1.0) * EFFORT_WEIGHT.get(e, 1.0) * WEB_WEIGHT
            out.append(Member(provider, m, e, w, web=True))
    return out


def run_member(case: Case, m: Member) -> tuple[CaseEstimate, dict]:
    if m.provider == "anthropic":
        from .anthropic_estimator import estimate
        return estimate(case, m.effort, m.model, web=m.web)
    from .estimator import estimate
    return estimate(case, m.effort, m.model, web=m.web)


def _wmedian(values: list[float], weights: list[float]) -> float:
    pairs = sorted(zip(values, weights))
    half = sum(weights) / 2
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= half:
            return v
    return pairs[-1][0]


def combine(results: list[tuple[CaseEstimate, float]]) -> list[pricing.LinePrice]:
    per_line: dict[int, list[tuple[float, float, float, float, float]]] = {}
    for est, w in results:
        for line in est.lines:
            q, mu, sigma, median = pricing._belief(line)
            per_line.setdefault(line.index, []).append((q, mu, sigma, median, w))
    prices = []
    for idx in sorted(per_line):
        rows = per_line[idx]
        wsum = sum(r[4] for r in rows)
        q = sum(r[0] * r[4] for r in rows) / wsum
        priced = [r for r in rows if r[3] > 0]
        if not priced:
            prices.append(pricing.LinePrice(idx, 0.0, 0.0, 0.0, round(q, 3), config.MIN_SIGMA))
            continue
        pw = [r[4] for r in priced]
        mus = [r[1] for r in priced]
        mu = _wmedian(mus, pw)
        mean_mu = sum(m * w for m, w in zip(mus, pw)) / sum(pw)
        between = sum(w * (m - mean_mu) ** 2 for m, w in zip(mus, pw)) / sum(pw)
        within = sum(w * r[2] ** 2 for r, w in zip(priced, pw)) / sum(pw)
        sigma = max(math.sqrt(within + between), config.MIN_SIGMA)
        if config.A_MEDIAN_MULT > 0:
            a = config.A_MEDIAN_MULT * math.exp(mu)
        else:
            a = pricing._best_charge(mu, sigma) * config.CHARGE_MULT
        b = pricing._accept_limit(q, mu, sigma)
        prices.append(pricing.LinePrice(idx, round(a, 2), round(b, 2), round(math.exp(mu), 2), round(q, 3), round(sigma, 3)))
    return prices


def run(case: Case, deadline: float, on_update=None, ms: list[Member] | None = None):
    """Runs all members in parallel until done or the monotonic deadline.

    on_update(prices, done, total, member, est, meta) is called after every
    successful member with the combined prices so far.
    Returns (results, failures) where results = [(member, est, meta)].
    """
    ms = ms if ms is not None else members()
    pool = ThreadPoolExecutor(max_workers=max(len(ms), 1))
    futures = {pool.submit(run_member, case, m): m for m in ms}
    results, failures = [], []
    pending = set(futures)
    try:
        while pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            done, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
            for fut in done:
                m = futures[fut]
                try:
                    est, meta = fut.result()
                except Exception as e:  # noqa: BLE001 - one model failing must not stop the round
                    failures.append((m, repr(e)))
                    continue
                results.append((m, est, meta))
                if on_update:
                    prices = combine([(e, mm.weight) for mm, e, _ in results])
                    on_update(prices, len(results), len(ms), m, est, meta)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    timed_out = [futures[f] for f in pending]
    return results, failures, timed_out
