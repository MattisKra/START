"""Compare claimbot/pricing.py's closed-form rule with best responses inside the lognormal-noise population model
from payoff_check.py. Model assumptions (NOT evidence about real teams): t=100, every team sees t*exp(sigma_true*eps),
cap c=400 (=4t, rules: c>=4t), all other teams play the SAME rule. Per-pair payoffs are additive, so a and b can be scored separately.
Run: python3 -I research/sim/review_pricing_rule.py"""
import sys, math
from statistics import NormalDist
import numpy as np
sys.path.insert(0, "research/sim")
from payoff_check import pair

N = NormalDist(); T = 100.0; C = 400.0; REJECT_P = 1/3

def teammate_ka(sigma_claimed):
    best, bv = 0, -1
    for i in range(-300, 151):
        z = i/100; v = math.exp(sigma_claimed*z)*(1-N.cdf(z))
        if v > bv: best, bv = z, v
    return -sigma_claimed*best          # a = t_hat*exp(-ka)

def teammate_kb(sigma_claimed):
    return sigma_claimed*N.inv_cdf(REJECT_P)    # b = t_hat*exp(+kb) ; z(1/3) = -0.43 -> kb = -0.43*sigma (b BELOW the median)

def score(ka, kb, ka_pop, kb_pop, sigma_true, n=200000, seed=0):
    rng = np.random.default_rng(seed)
    that = T*np.exp(rng.normal(0, sigma_true, n))
    that_j = T*np.exp(rng.normal(0, sigma_true, n))
    recv = pair(that*np.exp(-ka), that_j*np.exp(kb_pop), T, C).mean()      # as handyman vs population insurer
    paid = pair(that_j*np.exp(-ka_pop), that*np.exp(kb), T, C).mean()      # as insurer vs population handyman
    return recv, paid

def best_response(ka_pop, kb_pop, sigma_true):
    grid = np.linspace(-0.4, 1.0, 71)
    ka = max(grid, key=lambda k: score(k, 0, ka_pop, kb_pop, sigma_true, 60000)[0])
    kb = min(grid, key=lambda k: score(0, k, ka_pop, kb_pop, sigma_true, 60000)[1])
    return ka, kb

print("population + deviant both use the closed-form rule; compare to the best response (net = received - paid per line)")
print("sig_true sig_claimed | rule ka,kb | rule net | BR ka,kb | BR net | gain of BR")
for s_true, s_claim in [(0.10,0.10),(0.20,0.20),(0.30,0.30),(0.20,0.10),(0.30,0.10),(0.40,0.15)]:
    ka_p, kb_p = teammate_ka(s_claim), teammate_kb(s_claim)       # everybody plays the rule with the claimed sigma
    r, p = score(ka_p, kb_p, ka_p, kb_p, s_true)
    bka, bkb = best_response(ka_p, kb_p, s_true)
    br, bp = score(bka, bkb, ka_p, kb_p, s_true)
    print(f"{s_true:6.2f} {s_claim:9.2f} | {ka_p:+.2f},{kb_p:+.2f} | {r-p:8.2f} | {bka:+.2f},{bkb:+.2f} | {br-bp:7.2f} | {(br-bp)-(r-p):6.2f}")
