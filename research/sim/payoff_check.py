"""Sanity checks for the Claim-to-Fame payoff structure (rules from the slides only).

Run:  python3 -I research/sim/payoff_check.py

Checks
  1. pair payoff table reproduces the slide-5 example (Alpha +30, Delta +150, Beta -180).
  2. insurer side: reject iff P(fraud) > 1/3 (and how the cap c shifts it).
  3. handyman side: with t known, charging a>t only pays if other teams' b are lax.
  4. symmetric best-response fixed point when every team estimates t with lognormal noise sigma:
     a = t_hat * exp(-ka),  b = t_hat * exp(+kb).  Gives the equilibrium shading vs sigma.

Everything here is a MODEL under stated assumptions (private lognormal noise, no fraud-by-intent,
cap c = 4t (rules: c >= 4t), t>0). It is not evidence about the real field of teams.
"""
import numpy as np

REJECT_MULT = 1.5


def pair(a, b, t, c):
    """Return (handyman receives, insurer pays) for one line, vectorised."""
    a, b, t = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float), np.asarray(t, float))
    fair = a <= t
    acc = a <= b
    pay = np.where(acc, np.where(fair, a, np.minimum(a, c)), np.where(fair, REJECT_MULT * a, 0.0))
    return pay


# ---------------------------------------------------------------- 1. slide example
def slide_example():
    t, c = 100.0, 1e9
    teams = {"Alpha": (100, 130), "Delta": (100, 110), "Beta": (120, 90)}
    net = {k: 0.0 for k in teams}
    for h, (ah, _) in teams.items():
        for i, (_, bi) in teams.items():
            if h == i:
                continue
            m = float(pair(ah, bi, t, c))
            net[h] += m
            net[i] -= m
    return net


# ---------------------------------------------------------------- 2. insurer threshold
def insurer_breakeven(c_over_a=np.inf):
    """P(fraud)=p at which reject (1.5a(1-p)) equals accept ((1-p)a + p*min(a,c))."""
    # accept cost = a * ((1-p) + p*m), m = min(1, c/a)
    # reject cost = 1.5 a (1-p)
    m = min(1.0, c_over_a)
    # (1-p) + p m = 1.5 (1-p)  ->  p m = 0.5 (1-p) -> p = 0.5/(m+0.5)
    return 0.5 / (m + 0.5)


# ---------------------------------------------------------------- 3. handyman side
def handyman_expected(a, t, b_samples, c):
    return pair(a, b_samples, t, c).mean()


def fraud_pays_demo():
    rng = np.random.default_rng(0)
    t, c = 100.0, 400.0
    out = []
    for label, b in {
        "all others b = 0.8 t (strict)": np.full(20000, 80.0),
        "all others b = t (exact)": np.full(20000, 100.0),
        "others b ~ t*LN(+0.10, 0.15)": 100 * np.exp(rng.normal(0.10, 0.15, 20000)),
        "others b ~ t*LN(0, 0.15)": 100 * np.exp(rng.normal(0.0, 0.15, 20000)),
        "others b = 1.5 t (lax)": np.full(20000, 150.0),
    }.items():
        grid = np.linspace(40, 250, 211)
        vals = np.array([handyman_expected(a, t, b, c) for a in grid])
        out.append((label, grid[vals.argmax()], vals.max(), handyman_expected(t, t, b, c)))
    return out


# ---------------------------------------------------------------- 4. symmetric fixed point
def best_ka(ka_pop_unused, kb_pop, sigma, n=40000, seed=1, c_mult=4.0):
    """Best response of the charge shading ka against a population with b = t_hat_j * exp(kb_pop)."""
    rng = np.random.default_rng(seed)
    t = 100.0
    c = c_mult * t
    t_hat_dev = t * np.exp(rng.normal(0, sigma, n))
    b_j = t * np.exp(rng.normal(0, sigma, n) + kb_pop)
    grid = np.linspace(-0.4, 1.0, 71)
    vals = [pair(t_hat_dev * np.exp(-k), b_j, t, c).mean() for k in grid]
    return grid[int(np.argmax(vals))], max(vals)


def best_kb(ka_pop, sigma, n=40000, seed=2, c_mult=4.0):
    """Best response of the acceptance limit kb against a population charging a_j = t_hat_j * exp(-ka_pop)."""
    rng = np.random.default_rng(seed)
    t = 100.0
    c = c_mult * t
    t_hat_dev = t * np.exp(rng.normal(0, sigma, n))
    a_j = t * np.exp(rng.normal(0, sigma, n) - ka_pop)
    grid = np.linspace(-0.4, 1.0, 71)
    costs = [pair(a_j, t_hat_dev * np.exp(k), t, c).mean() for k in grid]
    return grid[int(np.argmin(costs))], min(costs)


def fixed_point(sigma, iters=30):
    ka, kb = 0.0, 0.0
    for _ in range(iters):
        ka_new, _ = best_ka(ka, kb, sigma)
        kb_new, _ = best_kb(ka, sigma)
        ka = 0.5 * ka + 0.5 * ka_new
        kb = 0.5 * kb + 0.5 * kb_new
    return ka, kb


if __name__ == "__main__":
    print("1. slide-5 example nets:", slide_example(), "(expect Alpha +30, Delta +150, Beta -180)")
    print("\n2. insurer break-even P(fraud) to reject:")
    for r in [np.inf, 3.0, 1.5, 1.0, 0.5]:
        print(f"   c/a = {r:>4}: p* = {insurer_breakeven(r):.3f}")
    print("\n3. handyman, t=100, c=400: best a given others' b (a>t only pays if others are lax)")
    for label, a_star, v, v_t in fraud_pays_demo():
        print(f"   {label:34s} a*={a_star:6.1f}  E={v:7.2f}   (a=t gives {v_t:7.2f})")
    print("\n4. symmetric best-response fixed point (a = t_hat*e^-ka, b = t_hat*e^+kb)")
    for s in [0.05, 0.10, 0.20, 0.30, 0.50]:
        ka, kb = fixed_point(s)
        print(f"   sigma={s:.2f}: ka={ka:+.3f} (a~{100*np.exp(-ka):5.1f}%)  kb={kb:+.3f} (b~{100*np.exp(kb):5.1f}%)  [t_hat=100%]")
