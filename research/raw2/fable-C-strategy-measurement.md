# Slice C: strategy and measurement without ground truth

Written 2026-11-21 by the research sub-agent (Fable). Scope: how to choose `a`, `b` and how to measure anything when the only feedback is the public
leaderboard. Sources were opened by fetch sub-agents; every claim carries one of **[opened]** (primary page read; "abs" = abstract page only,
"sum" = the passage came back as a machine summary of the page, not verbatim), **[snippet]** (search result only) or **[memory]**.
Everything [snippet]/[memory] is repeated in section 8. Simulation numbers are mine (section 9) and rest on an invented opponent population.

Labels: **(P)** published result, **(I)** my interpretation, **(H)** hypothesis that it transfers to our game.

## 0. Bottom line

**Premise check.** My brief assumed no feedback beyond a leaderboard. While I was writing, `research/03-leaderboard-findings.md` (14:04 CET)
reported 12 teams, five of them absent in game 1, per-game totals for every team, and a transactions view (issuer, reviewer, accepted flag,
amount per line). I have not called any of it. If our own rows show what that note infers, points 1 and 2 below change as marked.

1. **Aggregate leaderboard deltas cannot tune a multiplier in 100 rounds.** In simulation one round of our normalised payoff has SD ≈ 0.22-0.30
   of line value. A two-arm round-level A/B over all 100 rounds detects only effects ≥ 12-15 % of line value (80 % power). Plausible
   multiplier effects are 1-3 %, which need 2,000-18,000 rounds. Thompson sampling over `b`-multipliers scored no better than a fixed arm.
   **With per-line rows this changes:** the fair-or-inflated bit on our own charges pins our price-level bias to ±0.07 (1 SD, log units)
   after about 9 rounds and ±0.04 after 22 (section 2.5).
2. **Charge multiplier depends on how many teams are absent.** Worst-case regret over five opponent populations, 11 opponents:
   no absentees → `a ≈ 0.85 × median` (1.7 %); two absent → 0.80-0.85 (1.2-1.5 %); five absent, as in game 1 → **0.75-0.80 (0.7 %)**, where
   `a = 0.9` loses up to 6 % and `a = 1.0` up to 15 %. The current `claimbot` rule (0.76 × median at σ = 0.25) is right for the field as it
   stands. Absentees make shading *more* valuable, not less: against `b = 0` a charge earns 1.5× if fair and nothing otherwise.
3. **Do not raise `b` above the 1/3-quantile.** The earlier in-repo hypothesis (`B_MULT` ≈ e^+0.10) holds only when opponents shade charges
   15-25 % below their estimate *and* estimation errors are independent across teams. With a shared LLM error of 0.2-0.3 log units, or opponents
   charging at or above their estimate, the best `b` is 0.75-0.95 × median. LLM-auction papers point to too little shading, not too much.
   With per-line rows `b` can be steered directly: among charges we rejected just above `b`, two thirds should turn out fair (section 2.5).
4. **Estimator accuracy is worth 5× more than any multiplier.** Cutting our log-error from 0.25 to 0.15 added 12 % of line value per round;
   that moved mean rank from about 6th to about 2nd of 20 in the rank simulation. A level 20 % too high cost 13 %; 20 % too low cost about
   1.5 %, 30 % too low about 6 %. When unsure about the price level, err low, but not by more than about 20 %.
5. **Accept-everything teams give little leverage.** Charging the cap pays only if more than about 21-24 % of teams accept everything.
   Never submit `a = 0` on a line we think is excluded: the free option was worth +1.5 % of line value in every run.

**Single most promising edge:** the fair-or-inflated bit in our own transaction rows. It is the ground truth the brief said we lack: one
bit per line per round, free, and enough to hold our price level inside the 0.85-0.95 × `t` band where payoff is flat. A level 20 % too
high costs 13 % of line value per round, and the bit detects that within about two hours. If the rows turn out not to carry it, the
fallback is an outside reference-price set (section 5.2) and the frozen robust rule.

## 1. LLM agents in strategic markets (2024-2026)

No paper, benchmark or repo covers a dual-role, hidden-threshold claims-acceptance game. The closest evidence is sealed-bid auctions,
posted pricing and negotiation.

| Artifact | Date, licence | Headline result (P) | What it implies here (I/H) |
| --- | --- | --- | --- |
| Shah, Zhu, Jiang, Wang, Dayi, Horton, Parkes, "LLM Bidders Preserve the Mechanism-Level Orderings of Human Bidders" (v1 title "Learning from Synthetic Labs…" [snippet]). https://arxiv.org/abs/2507.09083 ; code https://github.com/KeHang-Zhu/llm-auction [opened] | v1 2025-07-12, v2 2026-09-28; CC BY 4.0; repo licence not seen | First-price sealed bid, Table 8, share of deviating bids below/above risk-neutral Nash: humans 32/68, GPT-4o 14/86, Claude 3.5 Haiku 2/98, Gemini 2.0 Flash 10/90. Common value, App. F Table 9 (GPT-4o): mean winner profit −2.54 (4 bidders) to −5.55 (7); "All five models nevertheless reproduce the stronger first-price winner's curse." App. C: "no statistical evidence of learning effects, behavioral drift" over 15 rounds. GPT-5-mini "sits essentially at the theoretical benchmark" (SMAD < 1.4 %) in private-value formats. | (H) A team that lets an LLM set its charge will shade less than a best response, so charges sit at or above the team's own estimate. That supports a strict `b`. LLM bots do not correct for selection and do not adapt across rounds. Reasoning models are closer to theory, so the strongest teams may be near equilibrium. |
| Chen et al., AucArena. https://arxiv.org/abs/2310.05746 [opened] | v1 2023-10-09, v4 2024-08-25; CC BY-NC-SA 4.0 | §4.2: "rule bidders establish an intriguing and powerful baseline, surpassing most LLMs in most settings." §4.3: other models "do not clearly demonstrate this adaptive behavior." | (I) Keep the split we have: the LLM estimates facts, a deterministic rule sets `a`, `b`. |
| Müller & Müller, Cattle Trade. https://arxiv.org/abs/2605.14537 [opened] | 2026-05-14; arXiv licence | Abstract: "Two heuristic code agents outperform most tested LLMs." §4.4: "The three code agents never overbid"; Gemini 2.5 Flash-Lite overbids at 1.20 %, the highest rate, "and finishes last." | Same as above. |
| Ahmed, Cai, Minaei, Rachuri (Visa Research), Bazaar. https://arxiv.org/abs/2608.00102 [opened] | 2026-07-30; CC BY 4.0 | Abstract: "even the strongest agent captures less than a third of hindsight-optimal profit"; "agents that learned fastest pre-shock are typically the slowest to revise their beliefs afterwards." Failure archetypes are "Loser" and "Underpricer". Per-customer Thompson sampling baseline: $1,426, 66.4 % win rate [sum]. | (H) LLM pricing agents left to themselves under-price or miss. Some opponents will charge well below `t`, which is harmless to us as insurer. |
| Fish, Shephard, Li, Shorrer, Gonczarowski, EconEvals. https://arxiv.org/abs/2503.18825 [opened] | v1 2025-03-24, v4 2026-02-18 | Pricing benchmark over 100 periods with hidden demand; collusiveness litmus scores GPT-4o 0.71, GPT-5 0.04 [sum]. | Weak relevance. Shows 100 periods is the usual horizon for LLM pricing tests, with explicit per-period feedback that we lack. |
| Fish, Gonczarowski, Shorrer, "Algorithmic Collusion by LLMs". https://arxiv.org/abs/2404.00806 [opened] | v1 2024-03-31, v6 2026-08-31, "Accepted to EC 2026" | Abstract: "LLM-based pricing agents quickly and autonomously reach supracompetitive prices and profits"; "Variation in seemingly innocuous phrases in LLM instructions" changes the degree. | (H) "Maximise profit" prompts push LLM-set charges above fair. More reason for a strict `b`. Prompt wording makes opponents heterogeneous. |
| Bichler, Hierhager, Köck, Pieroth (TUM), "How language model agents reshape price competition". https://arxiv.org/abs/2610.21711 [opened] | 2026-10-15; CC BY 4.0 | Abstract: "LLMs outperform standard online learners through faster adaptation." §2.2: an LLM agent "earns between 71 and 72 percent of cumulative industry profit" against Exp3, UCB, PPO over 2,000 periods. | (I) Standard online learners need thousands of periods with per-period feedback. We have 100 and aggregate feedback. Matches section 2. |
| Bianchi et al., NegotiationArena (ICML 2024). https://arxiv.org/abs/2402.05863 ; https://github.com/vinid/NegotiationArena (MIT) [opened] | 2024-02-08 | §5.1: "a strong correlation between the final accepted price and the initial price proposal", Spearman ρ = 0.716. Abstract: "pretending to be desolate and desperate, LLMs can improve their payoffs by 20%". Models are 2023-era. | (H) Anchoring: see next row. |
| Ríos, Manrique, Quijano, Giraldo, "The Illusion of Rationality". https://arxiv.org/abs/2512.09254 [opened] | 2025-12-10 | §4.2: anchoring ρ ≈ 0.78 (Claude 4.5 Sonnet) and ≈ 0.91 (Gemini 2.5 Pro); opening proposals "gravitat[e] heavily towards 50 or other multiples of 5." | (H) Opponents' numbers cluster on focal unit prices and on the examples in the rules. The starter script and the rules example show `b` above `a` (50/80, 120/150, 100/130, 100/110). Expect many teams with `b ≈ 1.1-1.6 × a`. |
| Huang et al., γ-Bench / GAMA-Bench (ICLR 2025). https://arxiv.org/abs/2403.11807 ; https://github.com/CUHK-ARISE/GAMABench (GPL-3.0) [opened] | 2024-03-18 | Guess-2/3: agents "consistently select 50 (or close to 50)" in round 1; "more aligned with human behavior than the game's NE." Sealed bid: "agents generally submit bids that are lower than their valuations in the First-Price auction." | (H) Depth of reasoning is low. Do not assume opponents play the equilibrium of this game. |
| Bansal et al., Magentic Marketplace. https://arxiv.org/abs/2510.25779 ; https://github.com/microsoft/multi-agent-marketplace (MIT) [opened] | 2025-10-27; CC BY 4.0 | "severe first-proposal bias, creating 10-30x advantages for response speed over quality." | Does not transfer: our game is simultaneous and sealed. No sealed-submission mechanism in the framework. |
| Frankfurt Hedgehogs, 2nd place IMC Prosperity 3. https://github.com/HendrikMS/imc-prosperity-3 [opened, sum] | 2025 | Manual rounds where payoff depends on the crowd. Round 3: most teams bid 284, average 287, they bid 303 and lost about 5.5 % against the optimum. Round 4: predicted crowd share 4.25 % against actual 6.72 % on the top pick; "our modeling was way off." | (I) A top team's crowd model, calibrated on last year's data, was badly wrong, and the crowd was less sophisticated than game theory assumed. Budget for being wrong about the population; score ourselves against the field average. |

Interpretation across the row set (I): three findings recur. Simple coded rules beat LLMs that decide for themselves. LLM agents shade too little
and anchor on round numbers and examples. They adapt weakly. Evidence that directly measures *human-written bots in a hackathon* does not exist;
the Prosperity write-up is the only comparable live-competition source I could open, and its lesson is humility about crowd models.

## 2. Learning the opponent population from the leaderboard

### 2.1 What a leaderboard delta contains (I)

Our round payoff is `Δ = R(a) − P(b)`: receipts depend only on our `a` and others' `b`, payments only on our `b` and others' `a`. This additivity
is exact. Consequences:

- A 2×2 factorial (a-multiplier × b-multiplier, randomised per round) estimates both main effects from all rounds with no interaction term.
  Testing two knobs costs no more than testing one.
- Opponents cannot see our submissions, so there is no carry-over between rounds. Under Bojinov, Simchi-Levi & Zhao the optimal switchback
  design with carry-over order 0 re-randomises every period, and exact randomisation p-values are valid (https://arxiv.org/abs/2009.00148,
  CC BY 4.0, [opened, design rule from sum]). Pair consecutive rounds (AB/BA) to absorb drift from teams editing their bots.
- Use `y_r = Δ_r / ((N−1) · Σ_i t̂_i)` as the outcome. Raw euros are dominated by one large case.

### 2.2 Power calculation (mine; code in section 9)

Setup: 20 teams, 3-6 lines per case, line values lognormal (σ = 0.9), one excluded line in 80 % of cases, opponents a mix of five types,
shared log-error 0.2, own log-error 0.25, 5 % average miss rate. Nine population draws for N = 10, 20, 40.

| Quantity | Value |
| --- | --- |
| SD of `y_r` per round | 0.22-0.28 (0.22-0.30 across all populations in section 4) |
| R² from public covariates (log case scale, line count, SD / min / median of other teams' deltas) | 0.17-0.36 |
| Minimum detectable effect, 2 arms, 100 rounds, 80 % power, 5 % two-sided | 12-15 % of line value raw, 11-12 % adjusted |
| True effect of `b`-multiplier 1.0 → 0.9 | +1.9 to +3.1 % |
| True effect of `a`-multiplier 1.0 → 0.9 | +2.1 to +3.4 % |

Formula: `n_total = (5.6 · SD / δ)²` for two equal arms; multiply by `(1 − R²)` with regression adjustment. With SD = 0.24 and R² = 0.22:

| Effect δ (share of line value) | Rounds, raw | Rounds, adjusted |
| ---: | ---: | ---: |
| 1 % | 18,174 | 14,188 |
| 2 % | 4,543 | 3,547 |
| 3 % | 2,019 | 1,576 |
| 5 % | 727 | 568 |
| 10 % | 182 | 142 |
| 15 % | 81 | 63 |

Even a gross level error is slow to see: if our estimates are 20 % too high, switching to a 0.7 level multiplier gains 12.8 % and needs about
46 rounds per arm.

Adaptive allocation over six `b`-multipliers, 100 rounds, 3,000 simulated tournaments (mean `y` per round):

| Policy | Mean | 
| --- | ---: |
| Fixed 1.0 | +0.104 |
| Explore 5 rounds per arm, then commit | +0.108 |
| Thompson sampling, six arms | +0.102 |
| Thompson sampling, three arms | +0.108 |
| Fixed 0.9 (the 1/3-quantile at σ = 0.25) | +0.128 |
| Oracle best arm | +0.143 |

What an edge is worth in rank (20 teams, 100 rounds, raw euros; "us" starts above the median by construction):

| Edge per round | Mean rank | P(top 3) |
| ---: | ---: | ---: |
| 0 % | 5.8 | 0.14 |
| 2 % | 4.7 | 0.33 |
| 5 % | 3.3 | 0.69 |
| 10 % | 1.7 | 0.98 |

**Caveat.** The effects and the SD come from an invented population. The SD is the number that decides everything and it can be measured:
the realised SD of our own `y_r` over the first 10 rounds is good to about ±45 %. If the real SD is below about 0.08, a 2×2 factorial becomes
worth running (MDE ≈ 4.5 %); otherwise not.

### 2.3 Can we estimate opponents' acceptance limits from deltas? (I)

Only through how our receipts change with our `a`, which needs randomised `a`. A wide contrast (0.8 vs 1.2 × median) separates a lenient
population from a strict one in about 40 rounds (receipts fall by 0.23 in the strict case and by 0.02 in the lenient one). It costs about 0.22
of line value on each of the 20 high-arm rounds if opponents are strict, roughly 4 % of the tournament, to learn something worth under 1 %.
A cheap contrast (0.85 vs 1.0) needs about 250 rounds. **Not worth doing.**

Other things the leaderboard does give, at one read-only page load per round:

- N, and who misses rounds. A team with `a = b = 0` receives nothing and pays 1.5 × every fair charge. In simulation the most negative delta
  belonged to a misser in only 39-67 % of rounds with a misser, so this is a rough flag.
- A rough check on the case total. A misser's loss ÷ 1.5 ÷ number of chargers is the average *fairly charged* total, which was well below
  the true total (median across runs 0.37-0.44 of it; 10th-90th percentile 0.14-0.61). Useful to catch a factor-of-two error, not a 10 % one.
- Our rank against the median, as a tripwire.

### 2.4 What the bandit and experimentation literature says

| Source | Result (P) | Use here (I) |
| --- | --- | --- |
| Pike-Burke, Agrawal, Szepesvári, Grünewälder, ICML 2018. https://arxiv.org/abs/1709.06853 [opened] | With delayed, aggregated, anonymous rewards, regret O(√(KT log K) + K·E[τ]·log T) if the expected delay is known. | With T = 100 and K = 5 the leading term is about 28 rounds of regret. The guarantee says nothing useful at our horizon. |
| Wu, Shariff, Lattimore, Szepesvári, Conservative Bandits. https://arxiv.org/abs/1602.04282 [opened] | Constraint: "earn at least a 1−α fraction of the reward from simply playing arm 0"; cost is "an extra additive regret of order O(KL/αμ0)" and "the additive penalty is unavoidable." | Safe exploration has a price that does not shrink with a short horizon. If we explore at all, restrict arms to the robust region (section 4) so worst-case regret per round is ≤ 2 %. |
| Hadad, Hirshberg, Zhan, Wager, Athey. https://arxiv.org/abs/1911.02768 [opened, abs] | "the sample mean is biased in adaptive trials." | If we ever adapt, the write-up cannot report naive arm means. Fixed randomisation keeps the analysis honest. |
| Deng, Xu, Kohavi, Walker, CUPED, WSDM 2013. https://exp-platform.com/cuped/ [opened, page abstract] | "we can reduce variance by about 50%" on Bing. | Our covariates give 17-36 %. Not enough to change the conclusion. |
| Deng et al., "From Augmentation to Decomposition". https://arxiv.org/abs/2312.02935 [opened, abs] | CUPED as a general augmentation framework that can "leverage in-experiment data". | Other teams' same-round deltas are in-experiment covariates. Our treatment moves them by 1/(N−1), which is negligible for N ≥ 10. |
| Blum & Hardt, The Ladder, ICML 2015. https://proceedings.mlr.press/v37/blum15.html [opened, abs] | Participants "may begin to overfit to the holdout data that supports the leaderboard." | Reacting to each round's delta is fitting noise with SD 0.24. |
| Han, Zhou, Weissman, repeated first-price auctions. https://arxiv.org/abs/2003.09795 [opened] | "O(√T log^2.5 T) regret" with censored feedback: "if she wins the bid, then she is not able to observe the highest bid of the other bidders." | Needs per-auction win/lose feedback. We get one scalar for all lines and opponents together. Not applicable. |

### 2.5 If our own transaction rows are usable: per-line feedback (I, simulation)

`research/03-leaderboard-findings.md` reports a transactions view with issuer, reviewer, accepted flag and amount per line, and infers what
our own rows would show. Nobody has read them yet, so treat this subsection as conditional. Whether rows of *other* teams may be used is a
fair-play question for the organisers and the team lead; everything below needs only our own rows.

| What a row shows | What it identifies |
| --- | --- |
| Our charge, rejected, amount 1.5·a | `t ≥ a`. With absentees (`b = 0`) every charge is rejected by someone, so this bit exists for every line. |
| Our charge, rejected, amount 0 | `t < a`: we over-charged that line. |
| Our charge, accept flag per opponent | Whether that opponent's `b ≥ a`. Forty or so points per opponent in two hours: its acceptance curve relative to our estimate. |
| Their charge, rejected by us, amount 1.5·a_j | `t ≥ a_j > b`: we were too strict on that line. |
| Their charge, rejected by us, amount 0 | The charge was inflated; rejecting was right. |
| Their charge, accepted by us | The size of `a_j`. Nothing about `t`. |

How fast the price-level bias is learned from the first two rows alone (probit with σ fixed at 0.32, charges at two nearby levels,
2,000 replications):

| Lines observed | Rounds (4.5 lines each) | SD of the bias estimate (log units) |
| ---: | ---: | ---: |
| 20 | 4 | 0.10-0.12 |
| 40 | 9 | 0.07-0.08 |
| 100 | 22 | 0.04-0.05 |
| 450 | 100 | 0.02 |

A bias of +0.18 (20 % high) is 2.5 SD after two hours and more than 4 SD after five. Compare section 2.2, where the same error needed
46 rounds per arm through aggregate deltas. The estimates were unbiased in the simulation (mean +0.176 to +0.181 for a true +0.18).

Three uses, in order of value:

1. **Level correction.** Fit bias and, once there are about 100 lines, σ. Multiply the median by `exp(−bias)`, shrunk by
   `n / (n + 40)` lines. Per trade or unit type only when a group has 30 or more lines.
2. **Steering `b`.** Among the charges we rejected that lie within 10 % above our `b`, the fair share should be about 2/3 (the break-even
   in section 4.1, applied where it holds exactly). Above 2/3 raise `b`, below lower it, in steps of a few percent. Expect 3-5 such
   charges per round, so the share has a standard error of about 0.08 after two hours (my estimate, not simulated). This is the quantile-tracking idea behind adaptive
   conformal inference (Gibbs & Candès, cited in wave 1; not re-opened by me).
3. **Choosing `a` from a fitted model instead of an A/B.** Receipts at multiplier m are `m·[P(t ≥ m·median)·(1 + 0.5·rejected share) +
   P(t < m·median)·accepted share]`. The first factor comes from the probit, the shares from opponents' flags. Maximise over
   m ∈ [0.75, 0.95]. A model with two parameters uses each line; a model-free A/B on receipts per line is no better than section 2.2
   (assuming a per-line SD of about 0.45, the MDE is about 12 % with 450 lines).

Related published setting: learning to bid with censored feedback (Han, Zhou & Weissman, section 2.4) and posted-price learning from
accept/reject bits (wave 1, topic A, section 2.5) both assume this kind of per-decision signal. They become applicable; their regret bounds
are still too loose to say anything at 450 observations, so the fitted two-parameter model is the practical route.

## 3. Offline evaluation without ground truth

**Nothing ready-made fits.** No dataset of invoice line items with expert fair prices turned up, and no arena implements this payoff.

| Artifact | Facts | Verdict |
| --- | --- | --- |
| AgentDS-Insurance. https://huggingface.co/datasets/lainmn/AgentDS-Insurance [opened; PDFs not opened] | CC BY-NC-SA 4.0, about 1.4 GB, 1,316 rows; `Insurance/invoices/` holds PDFs of about 2.3 kB each plus claims CSVs. Tasks: claims complexity, loss estimation, fraud detection. | Possibly a source of invoice-shaped documents. Line-item prices and labels unverified. Skip unless someone opens three PDFs. |
| scoringrules. https://github.com/frazane/scoringrules [opened] | Apache-2.0, `pip install scoringrules`, Python ≥ 3.12, `sr.crps_ensemble(obs, fct)`. Pinball and interval scores not confirmed in the README. | Optional. Pinball loss is three lines of numpy. |
| OpenSpiel. https://github.com/google-deepmind/open_spiel [opened] | Apache-2.0; n-player simultaneous-move games; Alpha-Rank page in docs; action sets are enumerated lists. | Discrete actions only as far as the docs show. Too heavy for two continuous numbers per line. |
| PettingZoo. https://github.com/Farama-Foundation/PettingZoo [opened] | MIT, `pip install pettingzoo`, Parallel API for simultaneous moves. | Works, adds nothing over numpy here. |
| Axelrod. https://github.com/Axelrod-Python/Axelrod [opened] | "A research tool for the Iterated Prisoner's Dilemma"; tournaments and Moran processes. | Wrong game. Borrow the idea (round-robin of named strategies, then population dynamics), not the code. |
| TextArena. https://github.com/LeonGuertler/TextArena [opened] | MIT, 100+ text games, negotiation games added 2025-11-26. | Not needed. |

Recommendation (I): a 100-line numpy round-robin (section 9 is a starting point; `research/sim/` already has the payoff function). Score each
candidate `(a, b)` rule against several opponent mixes and choose by worst-case regret, not by the best average in one mix.

### 3.1 Synthetic cases with known `t`

- Generate cases in the observed format (policy clauses 1.x/2.x/3.x, a 2-3 sentence description with one "while on site" item, 3-6 lines with
  units hrs/pcs/m2) and plant: an unrelated item, an item excluded by clause, a quantity out of line with the description.
- **Circularity warning.** If an LLM invents the prices, `t` is the LLM's own prior and the estimator will look calibrated. LLM-generated cases
  may be scored only on mechanics: exclusion and relatedness detection, `P(valid)` Brier score, parsing, VAT, quantity handling.
- Price level and spread need an outside source: 25-30 lines with documented German trade prices. With n = 30 the standard error of p10-p90
  coverage is 7 points, enough to tell 80 % from the 50 % range that over-confident LLM intervals produce.

### 3.2 Calibration checks we can run

| Check | Needs truth? | What it tells us |
| --- | --- | --- |
| Coverage of p10-p90, PIT histogram, pinball loss at τ = 1/3 | Yes: the reference-price set | Whether σ is honest and whether the level is biased. Pinball at 1/3 scores the exact quantile `b` uses. |
| Spread of log p50 across independent vendors' models on the same line | No | A lower bound on our error. It misses the error all models share, so add a floor (I used 0.2). |
| Share of identical unit prices across models | No | How strongly opponents' charges will cluster. |
| LLM as judge of "would an expert accept this price" | No | A consistency check only. Reported agreement with domain experts is 64-68 % [snippet]; judges share the estimator's prior. |
| Red team: prompt the estimator with the planted traps reversed (a covered item described as "while on site", an excluded item described as the cause) | Synthetic | Whether `P(valid)` follows the policy text or the story's wording. |

Plug-in quantiles from a few samples are poor. Besbes & Mouchtaki (https://arxiv.org/abs/2107.02742 [opened]): "with 20 samples, SAA already
leads to a relative regret of 26.8%" and "SAA is suboptimal" (worst case, service level 0.9). (I) Do not take the empirical 1/3-quantile of 3-5
LLM samples. Fit a lognormal and widen σ.

## 4. Decision rules for the asymmetric-cost, hidden-threshold game

### 4.1 Where the simple "1/3-quantile for b" rule is wrong

The exact condition (I, derived): raise `b` while, among opponent charges *at* `b`, the fair ones outweigh the inflated ones 2:1. That is the
1/3-quantile of the belief about `t` **conditioned on a charge having been made at that level**, not of our own belief alone. It differs when:

| Situation | Direction for `b` | Evidence |
| --- | --- | --- |
| Opponents shade charges below their estimate, errors independent | Up, as far as 1.15-1.3 × median when all opponents charge 0.75-0.85 × estimate and noise is small | My simulation; this is the case behind the earlier `B_MULT` hypothesis |
| Shared error across teams (same LLM priors), 0.2-0.3 log units | Down to 0.75-0.95 × median even when opponents shade 15-25 % | My simulation. A charge near our estimate is weak evidence about `t` when both rest on the same prior. |
| Opponents charge at or above their estimate | Down to about 0.75 × median | My simulation. Shah et al. Table 8 and Fish et al. suggest this is the likelier case (H). |
| Stated σ too small | Down: the quantile is `exp(−0.43 σ)` and σ must include the shared error | Section 3.2 |
| `P(excluded) > 1/3` | `b = 0` | Already in `claimbot` |
| Charge above the cap | Break-even moves to 1/2 | Irrelevant near `t` |
| Few samples | Do not use the empirical quantile | Besbes & Mouchtaki |

Cost of the insurer side by `b`-multiplier (share of line value, per opponent; higher is better):

| Opponents charge | Shared / own / their error | 0.75 | 0.85 | 0.95 | 1.05 | 1.15 | 1.30 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.85 × estimate | 0 / 0.10 / 0.10 | −1.125 | −1.001 | −0.889 | −0.846 | **−0.845** | −0.851 |
| 0.85 × estimate | 0 / 0.25 / 0.25 | −0.750 | −0.722 | **−0.710** | −0.715 | −0.731 | −0.765 |
| 0.85 × estimate | 0.2 / 0.25 / 0.25 | −0.703 | **−0.697** | −0.703 | −0.718 | −0.741 | −0.775 |
| 1.00 × estimate | 0.2 / 0.25 / 0.25 | **−0.579** | −0.590 | −0.617 | −0.655 | −0.702 | −0.777 |
| 1.15 × estimate | 0.2 / 0.25 / 0.25 | **−0.420** | −0.441 | −0.479 | −0.532 | −0.599 | −0.709 |

`b` too high by 0.2 costs 2-6 %; `b` too low by 0.1 costs under 1.5 % except in the first row, where small independent noise and shading
opponents make a low `b` very expensive (−1.00 at 0.85 against −0.85 at 1.15). That row is the risk in my recommendation: if most teams are
accurate (σ ≈ 0.1), do not share our errors and shade their charges, `b = 0.85` is a 15 % mistake.

### 4.2 A rule that survives all five populations

Receipts by `a`-multiplier and payments by `b`-multiplier (valid lines, share of our estimated line value, per opponent):

| Opponent population | Best `a` | Loss at `a` = 0.8 / 0.9 / 1.0 | Best `b` | Loss at `b` = 0.85 / 1.05 |
| --- | ---: | --- | ---: | --- |
| Naive: `a = b =` estimate | 0.8 | 0 / 1.0 / 6.0 % | 0.75 | 1.2 / 7.9 % |
| Anchored on the examples: `a` = estimate, `b` = 1.1-1.6× | 1.0 | 5.0 / 0.9 / 0 % | 0.75 | 1.1 / 7.4 % |
| Greedy and anchored: `a` = 1.1-1.3×, `b` = 1.1-1.6× | 1.0 | 6.5 / 1.8 / 0 % | 0.75 | 2.0 / 11.4 % |
| Equilibrium-like: `a` = 0.85×, `b` = 1.0-1.1× | 0.8 | 0 / 0.1 / 4.1 % | 0.85 | 0 / 1.9 % |
| Clones of the quantile rule: `a` = 0.85×, `b` = 0.9× | 0.8 | 0 / 2.4 / 8.7 % | 0.85 | 0 / 1.6 % |

Minimax regret with 19 opponents and a 5 % miss rate: **`a` = 0.9 × median (worst case 2.4 %)**, **`b` = 0.85 × median (worst case 2.0 %)**.
All populations here share a 0.2 error with us.

The charge side moves with the number of absent teams. Worst-case regret of receipts over the same five populations, 11 opponents (the real
field size), by `a`-multiplier:

| Absent of 11 | 0.70 | 0.75 | 0.80 | 0.85 | 0.90 | 1.00 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 10.9 % | 7.1 % | 4.1 % | **1.7 %** | 2.3 % | 8.9 % |
| 2 | 6.3 % | 3.4 % | 1.5 % | **1.2 %** | 3.6 % | 10.9 % |
| 5 (game 1) | 2.6 % | **0.7 %** | **0.7 %** | 3.1 % | 6.1 % | 14.9 % |

A usable rule: `a`-multiplier ≈ 0.85 − 0.15 × (share of opponents absent last round), i.e. 0.78 at 5 of 11 and 0.85 at none. An absent team
pays 1.5·a for a fair charge and nothing for an inflated one, so it rewards being under `t` and gives nothing for being over. Lenient active
teams pay even an inflated charge, which is what pulls the optimum up as absentees return.

Level uncertainty adds a second reason to stay low. Payoff by a global level multiplier λ applied to both numbers (base rule here:
`a = 0.9·λ·median`, `b = λ·median`; all rows rescaled to true line value so they compare):

| Scenario | λ = 0.8 | 0.9 | 1.0 | 1.1 | 1.25 |
| --- | ---: | ---: | ---: | ---: | ---: |
| No bias anywhere | +0.142 | **+0.157** | +0.133 | +0.076 | −0.049 |
| We are 20 % high, herd unbiased | **+0.148** | +0.092 | −0.001 | −0.112 | −0.276 |
| We are 20 % low, herd unbiased | +0.053 | +0.106 | +0.142 | **+0.156** | +0.131 |
| We and the herd are 20 % high | **+0.320** | +0.278 | +0.193 | +0.082 | −0.108 |
| We and the herd are 20 % low | −0.059 | +0.005 | +0.048 | **+0.065** | +0.038 |
| Herd 20 % high, we are right | +0.302 | **+0.323** | +0.310 | +0.264 | +0.146 |
| Herd 20 % low, we are right | +0.047 | **+0.065** | +0.039 | −0.018 | −0.134 |

Reading it (I):

- The best *effective* level (our median ÷ true value) is 0.85-0.95 in every row. Payoff is flat between 0.8 and 1.0, drops about 13-16
  points at 1.2 and about 6 points at 0.7, 12 points at 0.64.
- If the herd is 20 % high, being right is worth +0.31 against +0.19 for sharing the bias. If the herd is 20 % low, being right is worth
  nothing (+0.04 against +0.05). Accuracy pays on one side only.
- A blanket 10 % downward shade is right when we are unbiased or high and costs 3.6 points when we are already 20 % low. That is why the
  sign of the LLM's level bias is the measurement that matters most (step 4 of the plan).

### 4.3 Related published rules

- Critical fractile and data-driven newsvendor: Chen & Ma survey (https://arxiv.org/abs/2409.03505, CC BY 4.0, forthcoming in Operations
  Research [opened]): the plug-in quantile's regret lies "between 1/√n and 1/n"; for hard distributions they point to "a robustified algorithm".
- Bid shading with a learned win-rate model: Pan et al., AdKDD 2020 (https://arxiv.org/abs/2009.09259 [opened, abs]): "4.3% higher surplus than
  an industry Sell-Side Platform shading service". (I) The method is "maximise surplus × win probability", the same shape as
  `argmax x·P(T ≥ x)`, but it is fitted on per-bid win/loss logs we do not have. Gains of this size are also what my simulation shows for
  multiplier choice: a few percent.
- Wasserstein/moment-robust newsvendor: Singh & Zhang (https://arxiv.org/abs/2010.16369, CC BY 4.0 [opened]) gives piecewise closed forms and
  does not restate Scarf's rule. I found no robust-newsvendor result that changes our rule beyond "widen σ".

### 4.4 Teams that miss rounds or accept everything (I, simulation)

- **Missers (`a = b = 0`).** Each fair charge against them pays 1.5×. Receipts from a misser are `1.5·a·P(a ≤ t)`, maximised by
  `argmax x·P(T ≥ x)`, which is 0.75-0.85 × median, the rule `claimbot` already uses. So many absentees call for *more* shading than a
  lenient active field does (table in section 4.2). `research/03-leaderboard-findings.md` reads the absentees as a reason to charge at `t`
  rather than below; my numbers say the opposite, because a charge that lands above `t` earns nothing from them. Every submitting team
  collects the windfall, so the relative gain comes only from being fair more often than the others.
- **Accept-everything teams.** They pay `min(a, c)` even on inflated charges. Charging near the cap on every line beat `a = 0.9` only when
  their share exceeded about 21-24 % (payoff +0.07 against +0.19 at a 20 % share; +0.40 against +0.21 at 30 %). Below that it is ruinous
  (−0.60 at 0 %). Aggregate deltas cannot measure their share; per-opponent accept flags can (section 2.5). Until they show it, do not do it.
- **Excluded lines.** A rejected inflated charge costs nothing. Charging the normal shaded price on lines we believe excluded was worth
  +1.4 to +1.6 % of line value in all 11 runs, paid by teams that missed the exclusion. Keep `b = 0` there when `P(excluded) > 1/3`.
- **Rank scaling.** Only order counts. If we lead late, prefer the low-variance rule; if we trail late, variance has value. This is standard
  tournament reasoning, not something I have a source for.

## 5. Findings ranked by expected benefit

| # | Finding | Expected benefit | Confidence | Cost |
| --- | --- | --- | --- | --- |
| 1 | Read our own transaction rows each round; fit the level bias from the fair-or-inflated bit; steer `b` by the 2/3 share (section 2.5) | Keeps us in the flat band: avoids up to −13 % per round if we are 20 % high, known after about 9 rounds | Medium: the rows are reported, not yet read; the estimator is simulated | One page load per round, 40 lines of code |
| 2 | Never miss a round; always submit every line | A missed round costs about 0.6 of case value per opponent plus all receipts. Five of twelve teams did in game 1 | High: follows from the rules | Tier-0 fallback |
| 3 | Reduce estimator error; aim the median at 0.85-0.95 × true value | 12-14 % of line value per 0.1 of log-error; +12 % if the herd is 20 % high and we are not | Medium: simulation plus consistent LLM-herding evidence | The work of slices A/B |
| 4 | `a`-multiplier by absent share (0.78 now, 0.85 when everyone plays); `b` ≈ 0.85 × median with σ ≥ 0.3 including shared error | Up to 6 % against `a = 0.9` and 15 % against `a = 1.0` while five teams are absent; avoids a 2-11 % loss from `b > 1` | Medium: five invented populations; the `b` part fails if opponents are accurate, independent and shading | Two constants and one count |
| 5 | Do not A/B multipliers on aggregate deltas | Saves 0-2.5 % and a false "evidence" story | High given SD ≥ 0.2 | None |
| 6 | Charge on lines we think are excluded | +1.5 % | Medium-high | None (already the behaviour; document it) |
| 7 | Outside reference-price set | Prior for the level before the bit accumulates; the only level check if rows are unusable | Medium | 30 minutes |
| 8 | Cap-charging, wide `a` contrasts, Thompson sampling | Negative in expectation | Medium-high | — |

### 5.2 The edge in one paragraph (H)

Most teams will price with a general LLM and so share its level error. Payoff differences between teams come from who sits in the
0.85-0.95 × `t` band, and the loss from being 20 % high is about nine times the loss from being 20 % low. A small table of real German
trade rates (hourly rates by trade, common materials, call-out fees, gross of 19 % VAT) tells us on which side the LLM errs. If it errs
high, correcting it separates us from the herd by about 12 % of line value per round; if it errs low, we lose nothing by knowing and avoid
shading a price that is already low. It is also the kind of economical, evidenced method the jury rubric asks for. Whether general LLMs
over- or under-price German trade work is not something I found a source for; it has to be measured. The transaction-row bit
(section 2.5) measures the same thing on the real cases, so the reference set matters most in the first hour and as the fallback.

## 6. Minimal experiment plan for the next two hours

Rounds are already running (about nine in two hours). Nothing here spends a live round on exploration.

| Step | Minutes | What | Decision it feeds |
| --- | ---: | --- | --- |
| 1 | 15 | Read **our own** transaction rows for the completed games, once per round. Confirm the three amounts (a, 1.5·a, 0) appear as inferred. Store per line: our `a`, `b`, median, each opponent's accept flag and amount. Also store the per-game totals of all teams. | Whether section 2.5 is available at all; absent count; real SD of `y_r` |
| 2 | 20 | Fit the level bias (probit, σ = 0.32 fixed for now) on all own-charge bits so far. Report estimate and SD each round. | λ in step 6 |
| 3 | 15 | Tabulate rejected incoming charges within 10 % above `b`: fair share against the 2/3 target. Tabulate each opponent's accept rate against our charge multiplier. | Direction for `b`; whether any opponent accepts everything |
| 4 | 25 | Round-robin simulator (section 9) next to `research/sim/`, with the five populations of section 4.2, the absent count from step 1 and one "accurate, independent, shading" population. Score the current `claimbot` rule against `(0.78, 0.85)` and `(0.85, 0.85)`. | Confirms or kills the constants on our own code |
| 5 | 25 | Fallback and prior: 25-30 lines with documented German prices; p10-p90 coverage, pinball loss at 1/3, mean log bias. Skip the synthetic-case test unless exclusion errors show up in step 1 (an own charge on a line we called valid that pays 0 everywhere). | Prior for λ and the σ multiplier; the only level check if step 1 fails |
| 6 | 10 | Freeze and write down: `a = (0.85 − 0.15·absent share)·λ·median`, `b = exp(−0.43·σ_total)·λ·median`, `σ_total = sqrt(σ_stated² + 0.2²)`, `λ = exp(−bias·n/(n+40))`. Update λ and the absent share each round; change nothing else without a tripwire. | The rule we run |

Pre-registered tripwires:

- Bias estimate beyond ±2 SD after 40 lines: apply the full correction instead of the shrunk one.
- Fair share among near-`b` rejections above 0.8 or below 0.5 with at least 30 charges: move `b` by 5 % and re-measure.
- An opponent that accepted every one of at least 20 charges at or above our median: count it as accept-everything. At three or more such
  teams of eleven, revisit cap-charging.
- If step 1 fails (rows unavailable or not allowed): freeze `(0.78-0.85, 0.85)` with λ from step 5, compute the SD of `y_r` after 10
  rounds, and run the 2×2 factorial only if that SD is below 0.08.

For the write-up: the power table shows why aggregate A/B testing was rejected, and the bit-based calibration shows what replaced it, with
its own error bars. That covers "how did you convince yourselves" with two small computations and no extra model calls.

## 7. What I did not establish

- No source measures behaviour of human-written bots in a game like this one. Every transfer in section 1 is a hypothesis.
- All magnitudes in sections 2 and 4 come from my population model. Directions were stable over nine population draws and three team counts;
  the `b` direction flips under one specific population (section 4.1, first row).
- I did not test the estimator, call the game API or read the leaderboard. Section 2.5 rests on a teammate's description of the
  transactions view and on their inference about what the amounts mean. Step 1 of the plan checks it.
- The rank table uses 20 teams; the field is 12. The power numbers were run for 10, 20 and 40 teams and barely moved.
- The cap floor is unknown; I assumed €100. It affects only the excluded-line and cap-charging numbers.
- Several long papers were read partly through machine summaries (marked "sum"). Numbers marked that way should be re-read before the pitch.

## 8. Unverified items ([snippet] or [memory]; do not cite without opening)

- Siegel & Wagner, "Data-Driven Profit Estimation Error in the Newsvendor Model" (https://faculty.washington.edu/mrwagner/SW23.pdf): plug-in
  estimates overstate expected profit by 2.4 % (lognormal) and 3.0 % (normal). PDF did not parse. [snippet]
- Scarf's distribution-free order quantity `μ + (σ/2)(√(r/(1−r)) − √((1−r)/r))`, which at r = 1/3 gives μ − 0.35σ, less extreme than the
  normal quantile μ − 0.43σ. [memory]
- CUPED variance factor `1 − ρ²`. [memory] (the "about 50%" claim is [opened])
- The Ladder's update rule (only move the public score when the improvement exceeds a step) and the mixture-SPRT of Johari, Pekelis & Walsh
  (https://arxiv.org/abs/1512.04922; abstract opened, mechanism not). [memory]
- Gibbs & Candès, adaptive conformal inference (https://arxiv.org/abs/2106.00170), used in section 2.5 as the idea behind steering `b`.
  Taken from the wave-1 notes, not re-opened. [memory]
- Russo et al., Thompson sampling tutorial (https://arxiv.org/abs/1707.02038): statements about short horizons and non-stationarity. Abstract only. [memory]
- LLM-as-judge agreement with domain experts of 64-68 % (https://arxiv.org/abs/2410.20266). [snippet]
- Level-k studies of LLMs: Lee & Kader (https://arxiv.org/abs/2412.13013), Trencsenyi et al. (https://arxiv.org/abs/2502.07443), Gao et al.,
  "Take Caution in Using LLMs as Human Surrogates" (https://arxiv.org/abs/2410.19599). Findings conflict. [snippet]
- Vending-Bench Arena reports of price-fixing between agents (press coverage only). [snippet]
- "Generating Synthetic Invoices via Layout-Preserving Content Replacement" (https://arxiv.org/abs/2508.03754). [snippet]
- EGTtools (https://github.com/Socrats/EGTTools), GPL-3.0 per an aggregator; the URL I first tried returned 404. [snippet]
- Axelrod's licence (I believe MIT). OpenSpiel's `open_spiel.python.egt.alpharank` module path. [memory]
- Kaggle Rock-Paper-Scissors and Halite IV write-ups (https://github.com/0Zeta/RockPaperScissors, https://github.com/0Zeta/HaliteIV-Bot):
  Halite team dropped evolutionary tuning late "because of problems with overfitting". [snippet]
- IMC Prosperity 2 (https://github.com/ericcccsliu/imc-prosperity-2): opened, but it contains no account of the crowd in the manual rounds.
- Besbes & Mouchtaki Table 1 sample counts and the direction of the optimal correction: from a machine summary. [opened, sum]

## 9. Simulation core (to reproduce; the full scripts were scratch files and are not in the repo)

```python
import numpy as np
Z = 1.96 + 0.84                                   # two-sided 5 %, power 80 %

def settle(a, b, t, c):                           # what insurer pays handyman, per line
    fair, acc = a <= t, a <= b
    return np.where(fair, np.where(acc, a, 1.5 * a), np.where(acc, np.minimum(a, c), 0.0))

def population(rng, k):                           # k opponents: typical / shader / greedy / strict / lax
    typ = rng.choice(5, size=k, p=[.50, .20, .15, .10, .05])
    lo_a, hi_a = np.array([.9, .8, 1.2, .95, .9])[typ], np.array([1.1, .9, 1.5, 1.05, 1.1])[typ]
    lo_b, hi_b = np.array([.95, 1.05, .95, .7, 2.5])[typ], np.array([1.3, 1.15, 1.05, .9, 4.0])[typ]
    return dict(ma=rng.uniform(lo_a, hi_a), mb=rng.uniform(lo_b, hi_b), sig=rng.uniform(.10, .40, k),
                q=rng.uniform(.8, 1.0, k), free=rng.random(k) < .5, pm=np.where(rng.random(k) < .3, .10, .01))

def rounds(rng, pop, N, M, L, am, bm, sig_c=.2, sig_us=.25, floor=100.):
    k = N - 1
    v = np.exp(rng.normal(np.log(250), .9, (M, L)))                 # fair gross value if valid
    excl = np.zeros((M, L), bool); excl[np.arange(M), rng.integers(0, L, M)] = rng.random(M) < .8
    t = np.where(excl, 0., v); c = np.maximum(4 * t, floor); common = rng.normal(0, sig_c, (M, L))
    est = v[:, None] * np.exp(common[:, None] + pop['sig'][None, :, None] * rng.normal(size=(M, k, L)))
    flag = np.where(excl[:, None], rng.random((M, k, L)) < pop['q'][None, :, None], rng.random((M, k, L)) < .02)
    a = np.where(flag, np.where(pop['free'][None, :, None], est * pop['ma'][None, :, None], 0.), est * pop['ma'][None, :, None])
    b = np.where(flag, 0., est * pop['mb'][None, :, None])
    miss = rng.random((M, k)) < pop['pm'][None]; a[miss] = 0.; b[miss] = 0.
    mine = v * np.exp(common + sig_us * rng.normal(size=(M, L)))
    myflag = np.where(excl, rng.random((M, L)) < .95, rng.random((M, L)) < .02)
    a0, b0 = mine * am, np.where(myflag, 0., mine * bm)
    net = settle(a0[:, None], b, t[:, None], c[:, None]).sum((1, 2)) - settle(a, b0[:, None], t[:, None], c[:, None]).sum((1, 2))
    return net / (k * mine.sum(1))                                   # y_r

rng = np.random.default_rng(1); pop = population(rng, 19)
y = np.concatenate([rounds(rng, pop, 20, 6000, L, 1.0, 1.0) for L in (3, 4, 5, 6)])
sd = y.std(); print("SD per round", sd, "MDE at n=100", Z * sd * 2 / np.sqrt(100))
print({d: round((2 * Z * sd / d) ** 2) for d in (.01, .02, .03, .05, .10)})   # total rounds for effect d
```

Effects by arm were computed with common random numbers (same cases and opponents, different multiplier). The other tables (five named
populations, absent teams, level multiplier, probit bias estimate, bandit policies, rank) reuse `settle` with the opponent multipliers and
noise levels stated next to each table; those scripts were not kept. Covariate R² is from an OLS of `y`
on log case scale, line count and the SD, minimum and median of other teams' normalised deltas.
