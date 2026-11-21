# Topic A: game theory and transferable fields for "Claim to Fame"

Claude research agent A, 2026-11-21. Based on `research/raw/GAME_SPEC.md` and the slide text in `claim-to-fame-challenge-deep-dive.md`.
Labels used throughout: **[PUB]** = a published result with a source. **[INT]** = my interpretation or derivation. **[HYP]** = a hypothesis that the result carries over to this game. Confidence is marked **H/M/L**.
Every derivation below uses the payoff table from the slides. The numerical checks are my own Monte-Carlo runs, using lognormal estimation error with seeds fixed. They are illustrations, not evidence about the real teams.

---

## TL;DR (ranked by expected usefulness for winning)

1. **b is a newsvendor critical fractile.** [INT, H] The insurer's cost per line is minimised by accepting a charge exactly when P(fraud | a) ≤ 1/3. The two costs are: a fair charge wrongly rejected costs an extra 0.5a, and a fraudulent charge wrongly accepted costs min(a,c). The critical ratio is 0.5/(0.5+1) = 1/3, which is Elkan's cost-sensitive threshold. P(fraud | a) rises with a, so a single cutoff is optimal: **b\* = the 1/3-quantile of your belief about t**. Example: under lognormal error with σ = 0.2, b\* ≈ 0.92 × your median estimate.
2. **The "1/3 rule" is correct but incomplete. Two corrections:** [INT, H]
   - (a) **The cap c.** For charges above c the threshold becomes P(fraud) > a/(a+2c), which is above 1/3. On big-ticket lines you should be *more* lenient.
   - (b) **Charges carry information.** The relevant probability is P(t < a | your info **and** the fact that a team charged a). It is not your prior CDF F(a). Other teams' charges carry information about t (the winner's-curse logic of Milgrom–Weber). So **the optimal b depends on how other teams price.**
     - Simulation, honest noisy charges: best b ≈ median × e^{−0.60σ}.
     - Simulation, others shading to 0.8×: best b ≈ median × e^{+0.45σ}, above the median.
     - Simulation, perfect handymen: accept everything.
     - Once feedback is available, fit P(fraud | a/t̂) empirically and cut it at 1/3.
3. **The game almost decouples.** [INT, H] Your score is Σ recv(a_you, b_others) − Σ pay(a_others, b_you), which is additively separable, as the spec says. You cannot target a single opponent and there is no spite lever: any money you pay goes to rivals. b is close to a dominant strategy given your beliefs. **The only real strategic interaction is your a against the population distribution of b.** That is a monopoly-pricing / posted-price problem.
4. **There is a cliff at t, so a small overcharge never pays.** [INT, H] At a ≤ t you receive a (or 1.5a if rejected). Just above t you receive a only from the teams that accept, and nothing from the rest. **Shade a below your point estimate.** With insurers who are mostly strict, a\* solves a = (1−F(a))/f(a), which is Myerson's monopoly-price / optimal-reserve formula. Under lognormal error:
   | σ | a\* / median estimate |
   |---|---|
   | 0.05 | 0.90 |
   | 0.10 | 0.84 |
   | 0.20 | 0.78 |
   | 0.30 | 0.75 |

   In a simulated population of rational insurers (σ = 0.2), a ≈ 0.80·t̂ was best. Charging exactly t̂ lost about 25%.
5. **Excluded or unrelated lines (t = 0) are a free option for the handyman.** [INT, H] Charging a > 0 can only earn min(a,c) from teams that miss the exclusion, and costs nothing if rejected (the honest payoff is 0 anyway). Optimal a = argmax a·S(a), where S(a) is the share of teams with b ≥ a. **As insurer, set b = 0 whenever P(excluded or unrelated) > 1/3.** This is a game mechanic. Keep it in mind for how the write-up and presentation will be judged.
6. **Large inflation pays only against lax teams, and only if c is large.** [INT, H] It is profitable iff max_{a>t} min(a,c)·S(a) > t·(1.5 − 0.5·S(t)). In the simulation, with 3 of 9 teams accepting everything and no cap, charging 3·t̂ beat shading (1.02 vs 0.80 per insurer). With c = 2t it lost. **Learn c and look for lax teams early.**
7. **Accuracy of the t estimate is worth more than anything else.** [INT, H] Handyman revenue at the optimal shade falls from 0.88·t at σ = 0.05 to 0.62·t at σ = 0.3. Insurer cost rises with σ in the same way. Every bit of reduction in pricing error pays twice.
8. **Use online calibration rather than fixed constants.** [PUB → HYP, M]
   - If t is revealed after each round, track the realised rate of "t < b" and push it toward the target with adaptive conformal inference (Gibbs & Candès 2021).
   - If acceptance is revealed, learn the shading multiplier with a no-regret method (Hedge, or a posted-price bandit in the style of Kleinberg–Leighton or Cohen–Lobel–Paes Leme).
9. **Teams that reject a lot fund honest handymen.** [INT, H] A wrongful rejection pays the handyman 1.5a, and a team that misses a round has b = 0. Those teams hand money to honest chargers. You gain from them by staying fair, not by inflating.
10. **Tournament effect.** [PUB → HYP, L] Only the winner matters, so in the final rounds a trailing team should take on variance and the leader should cut it (Lazear–Rosen; Chevalier–Ellison). For your own position this means going conservative if you lead late.

---

## 0. Verifying the spec's claims

### 0.1 Additive separability. **Correct.** [INT, H]
Per line, with the other teams fixed:
`Score_i = Σ_{j≠i} R(a_i; b_j, t) − Σ_{j≠i} P(a_j; b_i, t)`.

- R depends only on a_i and P only on b_i, so the two decisions separate exactly.
- What you receive from j, R(a; b_j, t), is:

  | | accepted (a ≤ b_j) | rejected (a > b_j) |
  |---|---|---|
  | **fair (a ≤ t)** | a | 1.5a |
  | **inflated (a > t)** | min(a, c) | 0 |

- What you pay is the same table seen from the other side.
- **What separability does not mean:** that the decisions don't depend on the other teams. The best a depends on the distribution of the others' b (§0.3). The best b depends on how informative the others' a are about t (§0.2b).

### 0.2 The 1/3 threshold. **Correct for a ≤ c and uninformative charges. Incomplete otherwise.**
**(a) Per charge.** [INT, H] Let p = P(a > t).
- Expected cost of accepting: (1−p)·a + p·min(a,c).
- Expected cost of rejecting: 1.5·(1−p)·a.
- Reject iff 0.5·(1−p)·a < p·min(a,c), i.e. **p > a / (a + 2·min(a,c))**.
  - For a ≤ c this is **p > 1/3**.
  - For a > c it is p > a/(a+2c), which tends to 1 as a/c grows. With a capped downside on accepted fraud but an uncapped 1.5a penalty, a huge charge needs near-certainty of fraud before you reject it.
  - Caveat: if the 1.5a penalty is itself capped (not stated), redo this with min(1.5a, c′).

**(b) Why a single threshold b works.** [INT, H]
- b is one number per line, applied to every team's a.
- Total expected cost given the density h of incoming charges: `C(b) = ∫_{a≤b} a·h(a) da + ∫_{a>b} 1.5·a·(1−F(a))·h(a) da`, so `C′(b) = h(b)·b·(1.5·F(b) − 0.5)`.
- This is zero at F(b) = 1/3, negative below and positive above. **b\* = F⁻¹(1/3)**, the newsvendor critical fractile.
- When F has an atom at 0 with mass π (the "excluded" probability):
  - b\* = 0 if π ≥ 1/3.
  - Otherwise b\* = F₊⁻¹((1/3 − π)/(1 − π)), where F₊ is the price belief given the line is covered.
- Ties: a = b counts as accepted.

**(c) The correction: what "F" must be.** [INT, H; magnitudes M]
- F(a) must be P(t < a | your info, **a was charged**).
- If other teams' charges are correlated with t (they are: they are estimating the same t), observing a charge is evidence about t.
- Simulation: prior log t ~ N(0, 0.5²), your error σ = 0.2, 4 incoming charges, b = posterior median × e^{zσ}. Optimal z by charging model:

| How the others charge | best z | cost at best z | cost at z = −0.43 (marginal 1/3-quantile) | accept-all cost |
|---|---|---|---|---|
| independent of t | −0.40 | 1.880 | 1.881 | 4.53 |
| honest noisy estimate (σ = 0.2) | −0.60 | 2.638 | 2.643 | 4.63 |
| 0.8 × noisy estimate (shading) | **+0.45** | 3.459 | 3.582 (+3.6%) | 3.70 |
| exactly t | +1.5 (grid edge = accept all) | 4.748 | 6.193 (+30%) | 4.53 |

- **Practical rule:** model P(fraud | a/t̂) directly. Fit it on revealed data with a logistic or isotonic fit of 1[a > t] on log(a/t̂) plus line features, then set b where the fitted curve crosses 1/3.
- Before any data, the marginal 1/3-quantile is a robust default. It is within 0.2% of optimal when charges are honest-noisy, but costly if the population shades heavily.

### 0.3 Can a > t ever be profitable? **Yes, in three cases.** [INT, H]
Expected receipt for a handyman with belief F about t, where S(a) = share of insurers with b ≥ a:
`R(a) = (1 − F(a))·a·(1.5 − 0.5·S(a)) + F(a)·min(a,c)·S(a)`

- **Known t.** Inflating beats honest a = t iff ∃ a > t with min(a,c)·S(a) > t·(1.5 − 0.5·S(t)) ≥ t.
  - Just above t: min(a,c)·S(a) ≈ t·S(t) < t·(1.5 − 0.5·S(t)). So **marginal inflation never pays.** Only a jump to a high a with enough lax teams (or a missing or large cap) can.
- **t = 0 (excluded or unrelated):** R(a) = min(a,c)·S(a) ≥ 0. Charging something is always weakly better than 0.
- **Everyone accepts everything (S ≡ 1):** R(a) = a up to c, so charge c. **Everyone rejects (S ≡ 0):** R(a) = 1.5·a·(1 − F(a)), so use the monopoly price.

Simulation: me σ = 0.2, 9 insurers. Values are E[receipt per insurer]/t at a = m·t̂.

| m | 9 rational (b = q₁/₃) | 6 rational + 3 naive (b = 1.3·t̂) | 6 rational + 3 accept-all, c = ∞ | same, c = 2t |
|---|---|---|---|---|
| 0.70 | 0.740 | 0.730 | 0.731 | 0.732 |
| 0.80 | **0.787** | **0.787** | 0.797 | 0.796 |
| 0.85 | 0.772 | 0.786 | **0.804** | **0.804** |
| 1.00 | 0.595 | 0.671 | 0.738 | 0.736 |
| 1.30 | 0.178 | 0.318 | 0.561 | 0.559 |
| 2.00 | 0.004 | 0.036 | 0.682 | 0.622 |
| 3.00 | 0.000 | 0.001 | **1.020** | 0.666 |

The receipt curve is **bimodal**: one peak from honest shading, a second from deliberately charging far above t against lax teams. Which peak wins depends on S(·) and c.

### 0.4 Other points the spec leaves out [INT]
- **Handymen do not compete with each other.** Each handyman–insurer pair settles on its own; no "closest bid wins". The bid-shading logic of auctions carries over only through *uncertainty about t*, not through competition. (H)
- **Rejecting a fair charge hands the handyman 1.5a.** Skeptical or crashed teams transfer money to honest handymen. Strategies that reject everything lose against honest teams, which is slide 8, point 4. (H)
- **No spite lever.** Your b applies to everyone equally, and lowering it can only *give* money away (1.5a penalties). Minimising your own payments is also optimal for relative rank. (H)
- **Unsubmitted lines are a = b = 0.** b = 0 is the worst possible b on fair lines. Always submit every line, with a fallback price model. (H)

---

## 1. Strategic structure of the game itself

- **[INT, H]** The stage game per line is a simultaneous N-player game.
  - Each player's b problem is a single-agent decision. It is dominant given beliefs, except through the informativeness effect in §0.2c.
  - The a problem is a best response to the population's b distribution.
  - So the equilibrium is: insurers play b = calibrated 1/3-quantile, and handymen best-respond to S(·). With accurate, calibrated insurers, S(t) is small (many b sit below t), so the best response is honest shading (TL;DR #4).
- **Feedback loop.** If the population shades, the conditional fraud probability at a given a falls, insurers should raise b, and S(t) rises. A rising S makes "jump inflation" (the second peak) more attractive. That in turn raises fraud rates and lowers the optimal b.
  - [HYP, M] Over about 100 rounds this may cycle. A team that re-estimates P(fraud | a/t̂) from data each round tracks the cycle automatically.
- **No commitment problem.** [PUB] In insurance-fraud auditing, an insurer that cannot commit to auditing faces a credibility problem: ex post it does not want to audit, which invites fraud (Picard 1996, https://ideas.repec.org/a/eee/pubeco/v63y1996i1p27-56.html). [INT, H] Here the 1/3 rule is ex-post optimal, so b is credible by construction. There is no gain from a "tough reputation" because you cannot target and every team sees one b.
- **Tournament objective.** [PUB] In rank-order tournaments, effort and risk choices respond to the prize structure (Lazear & Rosen 1981, JPE, https://doi.org/10.1086/261010). Mutual-fund managers change risk according to their position relative to the year-end ranking (Chevalier & Ellison 1997, JPE, https://doi.org/10.1086/516389, DOI from memory; not checked this session). [HYP, L] Maximise expected money for most of the game. In the last ~10 rounds, the leader should cut variance (no jump inflation, b at the calibrated quantile) and a trailing team should add it.

---

## 2. Transferable fields

### 2.1 Newsvendor / critical fractile / quantile (pinball) loss. Maps to **b**.
- **[PUB]** Single-period inventory: the optimal order quantity is the cu/(cu+co) quantile of demand (Arrow, Harris & Marschak 1951, Econometrica, https://www.jstor.org/stable/1906817; bibliographic details from memory). The quantile is the functional that the piecewise-linear "pinball" loss elicits. Quantile regression (Koenker & Bassett 1978, https://www.jstor.org/stable/1913643, from memory). Consistency of scoring functions for quantiles is characterised by the generalized piecewise-linear class (Gneiting 2011, https://arxiv.org/abs/0912.0902).
- **[INT, H] Mapping:** cu = 0.5a (extra cost of a wrongful rejection) and co = min(a,c) (cost of accepting fraud), so the ratio is 1/3. Proof via C′(b) in §0.2b.
- **Rule:**
  - Train the price model with **pinball loss at τ = 1/3** on log price, or output a predictive distribution and read off its 1/3-quantile. That quantile is b.
  - The same model with a different functional gives a (§2.3).
  - With an exclusion probability π, use the mixture quantile from §0.2b.

### 2.2 Cost-sensitive classification thresholds. Maps to **b**, and to the per-line fraud classifier.
- **[PUB]** With misclassification costs, predict positive iff P(positive | x) ≥ C_FP/(C_FP + C_FN) for the 0-cost-diagonal case (Elkan 2001, IJCAI, https://ijcai.org/proceedings/2001/133).
- **[INT, H] Mapping:** "positive" = fraud. A false positive (rejecting fair) costs 0.5a; a false negative (accepting fraud) costs min(a,c). That gives p\* = 1/3 for a ≤ c and a/(a+2c) above c. Elkan's paper also requires *calibrated* probabilities, so calibrate the LLM or heuristic fraud score (Platt, isotonic, or the online method in §2.10).
- **Rule:** for each line, compute p_excl = P(not covered or not related) and p_price(a) = P(t < a | covered). Then P(fraud | a) = p_excl + (1 − p_excl)·p_price(a). Reject at 1/3.

### 2.3 Posted-price / reserve-price / monopoly pricing. Maps to **a**.
- **[PUB]** Optimal auctions with a single buyer reduce to a take-it-or-leave-it price r with virtual value r − (1−F(r))/f(r) = seller value (Myerson 1981, https://doi.org/10.1287/moor.6.1.58).
- **[INT, H] Mapping:**
  - The handyman's fair entitlement acts as a "buyer" with value t, who "buys" (counts as fair) iff t ≥ a.
  - With insurers mostly strict, R(a) ≈ 1.5·a·(1 − F(a)), so **a\* = (1 − F(a\*))/f(a\*)**.
  - Lognormal belief t = m·e^{σZ}: a\* = m·e^{σz\*}, where z\* solves φ(z)/(1 − Φ(z)) = 1/σ. Equivalently, σ·(1 − Φ(z)) = φ(z).
  - Numerically, a\*/m = 0.90, 0.84, 0.78, 0.75 for σ = 0.05, 0.1, 0.2, 0.3, and P(fair) ≈ 0.98, 0.96, 0.90, 0.83.
- **With the population term:** maximise the full R(a) from §0.3 over a grid of multipliers of t̂, using a model of S(a/t̂). Gaussian error gives similar results to lognormal for small σ.

### 2.4 First-price-auction bid shading and "The Price Is Right". Maps to **a** (partly).
- **[PUB]** "The Price Is Right" is a "closest without going over" contest. Contestants measurably deviate from rational strategic bidding (Berk, Hughson & Vandezande 1996, AER 86(4), https://ideas.repec.org/a/aea/aecrev/v86y1996i4p954-70.html).
- **[PUB]** Learning to bid in repeated first-price auctions with censored feedback achieves Õ(√T) regret (Han, Zhou & Weissman, https://arxiv.org/abs/2003.09795).
- **[INT, M]** The "don't go over" payoff a·1[a ≤ t] is shared, but here *no other handyman competes*. Use the monopoly-price formula (§2.3), not the competitive shading formula ((n−1)/n·v and similar).
- **[HYP, M]** Han et al.'s censored-feedback learning carries over to learning the shading multiplier if we only see accept/reject outcomes.

### 2.5 Posted-price learning with binary feedback. Maps to learning **a** online.
- **[PUB]** Kleinberg & Leighton (FOCS 2003), https://www.cs.cornell.edu/~rdk/papers/oppa.pdf: regret bounds for online posted prices with accept/reject feedback.
  - Stochastic (i.i.d.) valuations: Θ(√(T log T)) regret.
  - Adversarial valuations: Θ(T^{2/3}) up to log factors.
  - Exact constants are in the paper; I did not re-check the theorem statements this session.
- **[PUB]** Contextual version: Cohen, Lobel & Paes Leme, "Feature-Based Dynamic Pricing", Management Science 2020, https://doi.org/10.1287/mnsc.2019.3485. Ellipsoid method, regret O(d² log T) for a linear valuation model.
- **[INT/HYP, M] Mapping:**
  - The "price" is the multiplier m = a/t̂. The "demand" is the reward from §0.3, which depends on others' b and on t.
  - With about 100 rounds × several lines, we have a few hundred noisy samples, enough for a K = 8–12 arm bandit over m ∈ {0.6, …, 1.2, 2, 3}.
  - **If per-pair outcomes or per-team b are revealed after a round**, use *full-information* Hedge instead: the counterfactual payoff of every m can be computed exactly. Hedge regret is O(√(T log K)) (Freund & Schapire 1997, JCSS; DOI not checked).

### 2.6 Winner's curse / affiliated common values. Maps to **b** (the correction).
- **[PUB]** With affiliated signals about a common value, rational bidding conditions on the event of winning; ignoring this causes the winner's curse (Milgrom & Weber 1982, Econometrica 50(5), https://www.jstor.org/stable/1911865).
  - Empirical origin: Capen, Clapp & Campbell 1971, J. Petroleum Technology. Survey: Thaler 1988, JEP. Both unverified this session.
- **[INT, H]** Other teams' charges are signals of the common t. "Accepting a" should condition on the charge, which is §0.2c.
  - **Direction:** if others shade (charge below their estimate), charges below your estimate are more likely fair than your prior says, so raise b. If others charge their raw estimate, lower b slightly.
- **Rule:** estimate the charge-generating process from revealed a's (if published), or from the leaderboard reaction. Recompute b\* = the root in a of P(t < a | t̂, a) = 1/3.
  - Under a Gaussian log-model with others honest and errors equal to yours: b\* ≈ t̂·exp(√2·σ·z₁/₃) = t̂·e^{−0.61σ}. This matched the simulation (best z ≈ −0.60).

### 2.7 Ultimatum game / take-it-or-leave-it offers. Weak mapping.
- **[PUB]** Responders often reject low but positive offers, against the subgame-perfect prediction (Güth, Schmittberger & Schwarze 1982, JEBO, https://doi.org/10.1016/0167-2681(82)90011-7, from memory).
- **[HYP, L]** Human or LLM-designed teams may "punish" perceived inflation more than expected value justifies. Concretely, they set b below their 1/3-quantile, perhaps at their own estimate minus a margin. That lowers S(·), which **favours honest-shading handymen** and makes jump inflation unprofitable.
- **Refuted if:** revealed b's sit above the teams' implied estimates.

### 2.8 Costly state verification, audit and inspection games, Stackelberg audit games. Maps to **b** as an audit policy.
- **[PUB] Costly state verification:** verify only in states where it pays (Townsend 1979, JET, https://doi.org/10.1016/0022-0531(79)90031-0).
- **[PUB] Inspection games:** inspection is a non-cooperative extension of hypothesis testing; equilibria are often mixed, with the inspection probability making the violator indifferent (Avenhaus, von Stengel & Zamir 2002, Handbook of Game Theory vol. 3 ch. 51, https://ideas.repec.org/h/eee/gamchp/3-51.html).
- **[PUB] Audit games:** Stackelberg security games extended with a punishment parameter (Blocki, Christin, Datta, Procaccia & Sinha, IJCAI 2013, https://www.andrew.cmu.edu/user/nicolasc/publications/BCDPS-IJCAI13.pdf).
- **[INT, M]** In those models, auditing is costly and the auditor mixes. Here "auditing" (rejecting) is free, but *wrong* audits are penalised at 0.5a, which is what produces the 1/3 cutoff.
  - No mixing is needed, because P(fraud | a) is monotone and the problem is a decision problem, not a game.
  - The Stackelberg insight survives only as deterrence: if b's become visible, handymen will tune a to S(·). Deterrence is a public good shared by all insurers, so no single team should pay for it (an extra-low b). (H)

### 2.9 Insurance-fraud red-flag scoring, claims leakage, invoice auditing. Maps to the **fraud-probability input** for b.
- **[PUB]** The optimal audit rule is a "red flags" strategy: score claims by fraud indicators and audit above a cutoff. Calibrated on data from a large European insurer (Dionne, Giuliano & Picard 2009, Management Science 55(1), https://doi.org/10.1287/mnsc.1080.0905; WP: https://mpra.ub.uni-muenchen.de/18374/1/MPRA_paper_18374.pdf).
- **[HYP, M]** Use the slide's three checks (covered / related / reasonable) as red-flag features in a per-line fraud score. Calibrate the score to a probability and threshold it at 1/3 (or a/(a+2c)).
- Industry "claims leakage" statistics (for example, that x% of payouts are excess): **unverified**; I found no primary source in the time box.

### 2.10 Online quantile calibration (adaptive conformal inference). Maps to keeping b at the true 1/3-quantile.
- **[PUB]** ACI updates one parameter online from recent miscoverage and attains the target long-run coverage under arbitrary distribution shift (Gibbs & Candès 2021, NeurIPS, https://arxiv.org/abs/2106.00170). Variant without a tuned step size: https://arxiv.org/abs/2208.08401.
- **[HYP, M] Rule:** let err_k = 1[t_k < b_k] for every line with revealed t. Update q ← q + γ·(1/3 − err_k) on the quantile level used for b. Typical γ is 0.005–0.05; a scalar log-offset works equally well.
  - The same tracking with target "P(fair) ≈ the P(fair) implied by the chosen shade" corrects a.
  - Works even if the price model is biased (for example, an LLM systematically under-pricing a category).
- Needs: post-round reveal of t, or at least of fair/fraud outcomes. **Unknown.**

### 2.11 Tax compliance / Allingham–Sandmo. Contrast case for **a**.
- **[PUB]** A risk-averse taxpayer evades a positive amount iff the expected marginal penalty is below 1: audit probability × (1 + penalty rate) < 1 (Allingham & Sandmo 1972, J. Public Econ., https://doi.org/10.1016/0047-2727(72)90010-2, from memory).
- **[INT, H]** Here a caught inflation forfeits the *whole* line, not just the excess, so the marginal-evasion logic fails at t. Inflation is all-or-nothing: either honest shading, or a large jump against lax insurers (§0.3).

### 2.12 Fictitious play, no-regret learning, opponent modelling in population games
- **[PUB]**
  - Fictitious play converges in zero-sum two-player games (Robinson 1951, Annals of Math., https://www.jstor.org/stable/1969530, from memory).
  - Regret matching converges to the set of correlated equilibria (Hart & Mas-Colell 2000, Econometrica, https://doi.org/10.1111/1468-0262.00153, from memory).
- **[INT, M]** Since b is near-dominant, the population "game" is the handymen learning S(·), which is a contextual bandit (§2.5).
  - Opponent modelling is worth it only for S(·): the share of insurers who accept at ratio a/t̂, by line category. It is not worth it for anything team-specific, since a is common to all insurers.
  - Fictitious-play analogue: keep an empirical distribution of revealed b/t (or acceptance rates) over the last k rounds and best-respond to it with the §0.3 formula.

### 2.13 Additional: proper scoring for the price model
- **[PUB]** Quantiles are elicitable by pinball loss. **CVaR is not elicitable** (Gneiting 2011, https://arxiv.org/abs/0912.0902).
- **[INT, H]** Train one predictive-distribution model (for example, log-price mean and σ per line category). Then derive b (1/3-quantile, adjusted per §0.2c) and a (monopoly price per §2.3) from it. Do not train two separate point models; one distribution keeps a and b consistent.

---

## 3. Recommended strategy hypotheses (and what would refute each)

| # | Hypothesis | Default action | Refuting observation |
|---|---|---|---|
| H1 | b\* ≈ the 1/3-quantile of the calibrated belief about t, for a ≤ c | b = t̂·e^{−0.43σ} (lognormal); b = 0 if P(excl) > 1/3 | Revealed outcomes show our realised wrongful-reject share differing from the 1/3 cost-balance; or the spec turns out to cap the 1.5a penalty |
| H2 | The population shades below t, so b should move up toward or above the median | Fit P(fraud \| a/t̂) on revealed data; cut at 1/3 | Revealed charges cluster at or above the experts' t |
| H3 | Honest shading a ≈ 0.8–0.9·t̂ (by σ) beats charging t̂ | m from the §2.3 table, then a bandit over m | Acceptance rate at a ≈ t̂ is high (S(t) > ~0.7) *and* t is revealed to sit above t̂ on average (our model under-prices) |
| H4 | Jump inflation (a = 2–3·t̂ or c) loses unless ≥ ~25% of teams are lax and c ≫ t | Default off; test cheaply on low-value lines only if feedback shows lax teams | Leaderboard or feedback shows a cluster of teams accepting far above t; c revealed as large or absent |
| H5 | Excluded/unrelated lines: charge a > 0 (zero downside), target the typical b of teams that miss the exclusion | a ≈ shaded market price for the item | Zero acceptance on such lines over ~10 rounds; or the evaluation criteria penalise it |
| H6 | Estimation accuracy (σ) dominates all strategic tuning | Spend most build time on the pricing and coverage pipeline | Score differences between teams turn out driven by a few big inflation wins rather than steady pricing |
| H7 | b is near-dominant, so opponent modelling matters only for S(·) | No team-specific logic | Evidence that the platform uses per-team b (contradicts the slides) |
| H8 | The tournament end game: lead → cut variance; trail → add it | Switch in the last ~10 rounds | Score gaps late in the game far exceed achievable per-round variance |

---

## 4. Open facts that change the math (find out first)
1. **Value and form of c.** Is it a constant, per line, or a multiple of t? Does it also cap the 1.5a penalty?
2. **Post-round feedback.** Are t, the others' a/b, or per-pair outcomes revealed? This decides between full-information Hedge, bandit learning and ACI.
3. **Number of teams, and the share that are lax or crashed.** Missed rounds mean b = 0, which is a windfall for honest charging.
4. **EVALUATION_CRITERIA.** Does the write-up or presentation penalise deliberate t = 0 or jump charging?

---

## 5. Sources
Every URL here appeared in my search results this session, except entries marked "from memory", whose identifiers I did not re-check.
- Arrow, Harris, Marschak (1951). Optimal Inventory Policy. Econometrica. https://www.jstor.org/stable/1906817 (from memory)
- Koenker & Bassett (1978). Regression Quantiles. Econometrica. https://www.jstor.org/stable/1913643 (from memory)
- Gneiting (2011). Making and Evaluating Point Forecasts. JASA. https://arxiv.org/abs/0912.0902
- Elkan (2001). The Foundations of Cost-Sensitive Learning. IJCAI. https://ijcai.org/proceedings/2001/133
- Myerson (1981). Optimal Auction Design. Math. of OR. https://doi.org/10.1287/moor.6.1.58
- Kleinberg & Leighton (2003). The Value of Knowing a Demand Curve. FOCS. https://www.cs.cornell.edu/~rdk/papers/oppa.pdf
- Cohen, Lobel, Paes Leme (2020). Feature-Based Dynamic Pricing. Management Science. https://doi.org/10.1287/mnsc.2019.3485 (PDF: https://maxccohen.github.io/Feature-Based-Dynamic-Pricing.pdf)
- Han, Zhou, Weissman. Optimal No-Regret Learning in Repeated First-Price Auctions. https://arxiv.org/abs/2003.09795
- Berk, Hughson, Vandezande (1996). The Price Is Right, but Are the Bids? AER 86(4). https://ideas.repec.org/a/aea/aecrev/v86y1996i4p954-70.html
- Milgrom & Weber (1982). A Theory of Auctions and Competitive Bidding. Econometrica 50(5). https://www.jstor.org/stable/1911865
- Güth, Schmittberger, Schwarze (1982). An experimental analysis of ultimatum bargaining. JEBO. https://doi.org/10.1016/0167-2681(82)90011-7 (from memory)
- Townsend (1979). Optimal contracts and competitive markets with costly state verification. JET. https://doi.org/10.1016/0022-0531(79)90031-0
- Avenhaus, von Stengel, Zamir (2002). Inspection Games. Handbook of Game Theory vol. 3. https://ideas.repec.org/h/eee/gamchp/3-51.html
- Blocki, Christin, Datta, Procaccia, Sinha (2013). Audit Games. IJCAI. https://www.andrew.cmu.edu/user/nicolasc/publications/BCDPS-IJCAI13.pdf
- Picard (1996). Auditing claims in the insurance market with fraud: the credibility issue. J. Public Econ. https://ideas.repec.org/a/eee/pubeco/v63y1996i1p27-56.html
- Dionne, Giuliano, Picard (2009). Optimal Auditing with Scoring: Theory and Application to Insurance Fraud. Management Science. https://doi.org/10.1287/mnsc.1080.0905
- Gibbs & Candès (2021). Adaptive Conformal Inference Under Distribution Shift. NeurIPS. https://arxiv.org/abs/2106.00170 ; follow-up https://arxiv.org/abs/2208.08401
- Allingham & Sandmo (1972). Income tax evasion: a theoretical analysis. J. Public Econ. https://doi.org/10.1016/0047-2727(72)90010-2 (from memory)
- Lazear & Rosen (1981). Rank-Order Tournaments as Optimum Labor Contracts. JPE. https://doi.org/10.1086/261010 (from memory)
- Chevalier & Ellison (1997). Risk Taking by Mutual Funds as a Response to Incentives. JPE. https://doi.org/10.1086/516389 (from memory)
- Robinson (1951). An Iterative Method of Solving a Game. Annals of Math. https://www.jstor.org/stable/1969530 (from memory)
- Hart & Mas-Colell (2000). A Simple Adaptive Procedure Leading to Correlated Equilibrium. Econometrica. https://doi.org/10.1111/1468-0262.00153 (from memory)
- Freund & Schapire (1997). Hedge / decision-theoretic generalization of on-line learning. JCSS. (unverified; no URL)
- Capen, Clapp, Campbell (1971), winner's curse; Thaler (1988), JEP. (unverified)
- Claims-leakage industry statistics: unverified, no primary source found.
