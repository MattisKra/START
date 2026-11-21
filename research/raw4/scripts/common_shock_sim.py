"""Common-shock model of one line (no real data; parameters are stylised from aggregate observations).

    python3 -I research/raw4/scripts/common_shock_sim.py

World: every team prices from the same kind of LLM prior, so the price-level error is SHARED.
  consensus M = 1;  fair value  t = exp(eps),  eps ~ N(mu, sigma^2)                 (shared shock: nobody knows it)
  opponent j: estimate m_j = exp(eta_j), eta_j ~ N(0, tau^2); charge a_j = ka_j m_j; limit b_j = kb_j m_j; or silent (a = b = 0)
  we: estimate m = exp(eta_us) (uninformed) or m = t * exp(N(0, s_own^2)) (informed: memory / anchor / pin); a = x m, b = y m
Payoff per ordered pair as in GAME_DESCRIPTION.md (cap ignored: no charge here exceeds 4 t by construction of the grid we report).
Output: best multipliers and the value of information, in units of M per line, summed over the 11 opponents.
"""
import numpy as np

rng = np.random.default_rng(7)
N, K = 11, 40000


def world(mu, sigma, tau, silent, lax_share):
    eps = rng.normal(mu, sigma, K)
    t = np.exp(eps)
    m = np.exp(rng.normal(0, tau, (K, N)))
    ka_opp = rng.uniform(0.70, 0.95, (K, N))
    kind = rng.random((K, N))
    kb_opp = np.where(kind < lax_share, rng.uniform(1.2, 1.6, (K, N)), np.where(kind < lax_share + 0.3, rng.uniform(0.7, 0.9, (K, N)), rng.uniform(0.95, 1.15, (K, N))))
    a, b = ka_opp * m, kb_opp * m
    is_silent = np.arange(N)[None, :] < silent
    a = np.where(is_silent, 0.0, a); b = np.where(is_silent, 0.0, b)
    return t, a, b


def net(t, a_opp, b_opp, a_us, b_us):
    """Our expected net per line (income - cost), arrays over K worlds."""
    au = a_us[:, None]
    acc = au <= b_opp
    income = np.where(acc, au, np.where(au <= t[:, None], 1.5 * au, 0.0)).sum(1)
    pos = a_opp > 0
    accu = a_opp <= b_us[:, None]
    cost = np.where(~pos, 0.0, np.where(accu, a_opp, np.where(a_opp <= t[:, None], 1.5 * a_opp, 0.0))).sum(1)
    return income, cost


def run(mu, sigma, tau=0.25, silent=1, lax_share=0.35, s_own=None, label=""):
    t, a, b = world(mu, sigma, tau, silent, lax_share)
    m_us = np.exp(rng.normal(0, tau, K)) if s_own is None else t * np.exp(rng.normal(0, s_own, K))
    xs = np.round(np.arange(0.4, 1.81, 0.05), 2); ys = np.round(np.arange(0.0, 2.01, 0.05), 2)
    inc = np.array([net(t, a, b, x * m_us, np.zeros(K))[0].mean() for x in xs])
    cst = np.array([net(t, a, b, np.zeros(K), y * m_us)[1].mean() for y in ys])
    bx, by = xs[inc.argmax()], ys[cst.argmin()]
    f = lambda arr, grid, v: arr[np.abs(grid - v).argmin()]
    oracle_inc = np.array([net(t, a, b, t, np.zeros(K))[0].mean()]); oracle_cost = net(t, a, b, np.zeros(K), t)[1].mean()
    print(f"{label:34s} mu {mu:+.2f} sig {sigma:.2f} silent {silent}: a* = {bx:.2f} m (income {inc.max():5.2f}; at 0.75 {f(inc, xs, .75):5.2f}, 0.90 {f(inc, xs, .9):5.2f}, 1.00 {f(inc, xs, 1.0):5.2f}, 1.10 {f(inc, xs, 1.1):5.2f}; a=t {oracle_inc[0]:5.2f})"
          f" | b* = {by:.2f} m (cost {cst.min():5.2f}; at 0 {f(cst, ys, 0):5.2f}, 0.80 {f(cst, ys, .8):5.2f}, 1.00 {f(cst, ys, 1.0):5.2f}, 1.25 {f(cst, ys, 1.25):5.2f}, 2.0 {f(cst, ys, 2.0):5.2f}; b=t {oracle_cost:5.2f})")
    return inc.max() - cst.min()


if __name__ == "__main__":
    print("-- uninformed (we share the field's price-level error)")
    base = {}
    for mu in (0.0, 0.15):
        for sigma in (0.3, 0.5, 0.7):
            for silent in (5, 1, 0):
                base[(mu, sigma, silent)] = run(mu, sigma, silent=silent, label="uninformed")
    print("\n-- informed: our estimate is within s_own of the true t (memory, anchor or policy pin); the field is unchanged")
    for mu in (0.0, 0.15):
        for sigma in (0.5, 0.7):
            for s_own in (0.25, 0.10):
                v = run(mu, sigma, silent=1, s_own=s_own, label=f"informed s_own={s_own}")
                print(f"      value of the information vs uninformed best multipliers: {v - base[(mu, sigma, 1)]:+.2f} M per line")
    print("\n-- field becomes stricter (lax share 0.35 -> 0.10) with 1 silent team")
    for sigma in (0.5,):
        run(0.0, sigma, silent=1, lax_share=0.10, label="uninformed, strict field")
        run(0.15, sigma, silent=1, lax_share=0.10, label="uninformed, strict field")
