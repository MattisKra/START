"""First-principles simulation of one valid invoice line of "Claim to Fame" (numpy only, no data of any team).

    python3 -I research/raw3/scripts/sim_first_principles.py

Population (all numbers are ASSUMPTIONS; scenario 1 is set near the aggregate shape of the observed field, see the report):
  11 opponents: N_SILENT with a = b = 0, the rest "noisy-rational": estimate = t * exp(BIAS_OPP + c + e_j),
  c ~ N(0, RHO*SIG^2) is an error shared by everybody (same kind of LLM), e_j ~ N(0, (1-RHO)*SIG^2) is their own.
  They charge a = KA_OPP * estimate and accept up to b = KB_OPP * estimate. A share LAX of them uses b = 3 * estimate.
We see t * exp(BIAS_US + (SIG_US/SIG) * (c + e_us)): a scaled copy of a typical team, total error sd SIG_US, correlation RHO
  with every opponent. We play a = ka * estimate, b = kb * estimate.
Payoff per ordered pair (GAME_DESCRIPTION.md): accepted -> a (min(a, c) if inflated, cap c = 4t); rejected -> 1.5a if a <= t else 0.
Output: expected income and reviewer regret per line in units of t, the best (ka, kb), and the rule in claimbot/pricing.py
  (a = argmax x*P(t>=x), b = 1/3-quantile of the own lognormal belief) for comparison.
"""
import math
import numpy as np

rng = np.random.default_rng(7)
N = 40000
KA = np.round(np.arange(0.50, 1.31, 0.05), 2)
KB = np.round(np.concatenate([np.arange(0.60, 1.61, 0.10), [2.0, 3.0]]), 2)


def phi(z): return math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
def Phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def team_rule(sig):
    """claimbot/pricing.py: a = argmax x*P(t>=x) (grid over z), b = 1/3-quantile; both as multiples of the median."""
    zs = np.arange(-3, 1.5, 0.01)
    v = np.exp(sig * zs) * (1 - np.array([Phi(z) for z in zs]))
    return float(np.exp(sig * zs[v.argmax()])), math.exp(sig * -0.4307)


def run(sig_us, bias_us=0.0, bias_opp=0.0, sig_opp=0.35, rho=0.5, n_silent=5, lax=0.10, ka_opp=1.0, kb_opp=1.0, n_opp=11):
    n_act = n_opp - n_silent
    c = rng.normal(0, math.sqrt(rho) * sig_opp, N)                       # shared error (log)
    e_opp = rng.normal(0, math.sqrt(1 - rho) * sig_opp, (N, n_act))
    e_us = rng.normal(0, math.sqrt(1 - rho) * sig_opp, N)
    est_opp = np.exp(bias_opp + c[:, None] + e_opp)                       # t = 1
    a_opp = ka_opp * est_opp
    is_lax = rng.random((N, n_act)) < lax
    b_opp = np.where(is_lax, 3.0, kb_opp) * est_opp
    est_us = np.exp(bias_us + (sig_us / sig_opp) * (c + e_us)) if sig_us > 0 else np.ones(N)
    cap = 4.0
    inc = np.zeros(len(KA)); cost = np.zeros(len(KB))
    for i, ka in enumerate(KA):
        a = (ka * est_us)[:, None]
        fair = a <= 1.0
        acc = a <= b_opp
        pay_act = np.where(fair, np.where(acc, a, 1.5 * a), np.where(acc, np.minimum(a, cap), 0.0)).sum(1)
        pay_sil = np.where(fair[:, 0], 1.5 * a[:, 0], 0.0) * n_silent     # silent reviewers: b = 0
        inc[i] = (pay_act + pay_sil).mean()
    fair_o = a_opp <= 1.0
    for j, kb in enumerate(KB):
        b = (kb * est_us)[:, None]
        acc = a_opp <= b
        cost[j] = np.where(acc, np.where(fair_o, a_opp, np.minimum(a_opp, cap)), np.where(fair_o, 1.5 * a_opp, 0.0)).sum(1).mean()
    best_cost = np.where(fair_o, a_opp, 0.0).sum(1).mean()                # cost with perfect knowledge of t
    return inc, cost - best_cost, float((a_opp <= 1).mean()), float(np.median(a_opp)), float(np.median(b_opp))


def report(label, **kw):
    first = True
    for sig_us in [0.0, 0.15, 0.30, 0.50]:
        inc, reg, pf, ma, mb = run(sig_us, **({k: v for k, v in kw.items() if k != "bias_us"} if sig_us == 0 else kw))
        if first:
            print(f"\n### {label}\n  field: {pf:.0%} of opponents' charges fair, median charge {ma:.2f} t, median limit {mb:.2f} t")
            print("  sig_us | best ka  income | best kb  regret | pricing.py: ka   income    kb   regret | loss of pricing.py vs best")
            first = False
        i, j = inc.argmax(), reg.argmin()
        if sig_us > 0:
            tka, tkb = team_rule(sig_us)
            ti = np.interp(tka, KA, inc); tr = np.interp(tkb, KB, reg)
            extra = f"{tka:10.2f} {ti:8.2f} {tkb:5.2f} {tr:8.2f} | {(inc[i] - ti) + (tr - reg[j]):6.2f}"
        else:
            extra = "   (known t: a = b = t)"
        print(f"  {sig_us:6.2f} | {KA[i]:6.2f} {inc[i]:8.2f} | {KB[j]:6.2f} {reg[j]:8.2f} | {extra}")


if __name__ == "__main__":
    print("units: multiples of the line's fair value t; income = what we receive as issuer (11 opponents);")
    print("regret = what we pay as reviewer above the minimum possible. sig_us = sd of our log error.")
    low = math.log(0.78)
    report("1. FIELD-LIKE, we share the field's low price level: everybody 22 % low, opponents charge 1.0x and accept 1.1x their estimate", bias_us=low, bias_opp=low, kb_opp=1.1)
    report("2. same field, our estimate de-biased (calibrated on past brackets)", bias_opp=low, kb_opp=1.1)
    report("3. same as 2, errors independent between teams (rho = 0)", bias_opp=low, kb_opp=1.1, rho=0.0)
    report("4. same as 2, errors almost fully shared (rho = 0.9)", bias_opp=low, kb_opp=1.1, rho=0.9)
    report("5. same as 2, no silent teams (11 active)", bias_opp=low, kb_opp=1.1, n_silent=0)
    report("6. TEXTBOOK field: unbiased opponents charge and accept exactly their estimate", )
    report("7. same as 2, lax field: 60 % of active reviewers accept up to 3x", bias_opp=low, kb_opp=1.1, lax=0.6)
