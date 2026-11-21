# Synthesis of research wave 1 (GPT-6.2 Sol ×2, Claude Opus 5.5 ×2) + real-data check

Written 2026-11-21 ~14:00 CET. Inputs: `raw/{gpt,claude}-{A-game-theory,B-estimation}.md`, `00-challenge-model.md`, `sim/`, and case 0 (decrypted with the sanctioned Game 0 key).
Wave 2 (GPT / Claude / Fable on SOTA papers, repos, HF artifacts) is still running; its files land in `raw2/`.

## 1. Evidence status (per citation-verification)

- All **35 arXiv IDs** cited across the four reports resolve to a real paper with a title that matches the claimed topic (checked against the arXiv API, not read in full).
  Examples: 2510.26995 *LLMs are Overconfident … FermiEval*, 2506.06657 *Quantile Regression with LLMs for Price Prediction*, 2506.07962 *Correlated Errors in LLMs*,
  2405.13268 *Stochastic Online Conformal Prediction with Semi-Bandit Feedback*, 2106.00170 *Adaptive Conformal Inference*, 2508.16081 *CEQuest (construction estimation)*.
- **Not verified:** whether each paper supports the *specific number or claim* the report attaches to it, and all non-arXiv sources (BKI, Sirados, Carglass, Miele, ACL/ICML pages).
  One weak spot: 2501.04150's title is generic ("Benchmarking Large and Small MLLMs"); the claim "no tested MLLM reliably estimated vehicle repair cost" needs a read before it goes in the write-up.
  The reports themselves say there is no peer-reviewed benchmark of LLM unit pricing for German repair trades and no source for Sirados.
- All simulation numbers (Claude-A's, mine) are model outputs under assumed populations, not observations of real teams.

## 2. Where the four reports agree / disagree

| Question | GPT-A | Claude-A | GPT-B | Claude-B | My sim (`sim/`) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `a`, `b` separable | yes, exact (linearity) | yes | yes | implied | yes | **Settled.** |
| `b` = 1/3-quantile of own belief | only if charges carry no extra info and cap inactive | correct but incomplete | yes, below median | yes, "whatever others charge" | too low if others shade `a` below `t̂` | **Contested.** Claude-B's "whatever others charge" holds only when an incoming charge adds no information about `t`. Three of five sources say it does. |
| Cap correction | threshold `y/(y+2·min(y,c))` | `a/(a+2c)` | "binding cap changes the rule" | ignore unless `c` small | same formula | **Settled.** With `c ≥ 4t` it rarely binds on fair-priced lines. |
| `a` below the median estimate | maximise expected receipts over a price grid; minimax benchmark | 0.90 / 0.84 / 0.78 / 0.75 × median at σ = 0.05 / 0.10 / 0.20 / 0.30 | `argmax x·P(t≥x)` | n/a | 0.92 / 0.89 / 0.82 / 0.77 (σ = 0.05 / 0.10 / 0.20 / 0.30) | **Consensus** ≈ 0.8-0.9 × median if opponents are strict or rational. |
| Inflating above `t` | pays iff enough opponents accept | only vs lax teams and large `c` | n/a | n/a | only if others' `b` > `t` | **Consensus**: don't, unless we observe lax teams. |
| `t = 0` lines | `b = 0`; positive `a` can only gain | `b = 0` if P(excl.) > 1/3; `a > 0` is a free option | own probability mass at exactly 0 | `b = 0` if P(t=0) ≥ 1/3 | n/a | **Consensus** on the math; **see §5 on whether to use the option.** |
| Learn from outcomes | depends on what feedback exists | ACI / bandits if `t` or acceptance revealed | accept/reject alone cannot identify `t` | fit bias/spread from rejections | n/a | **Blocked:** API has no results endpoint (`materials/API_HANDBOOK.md`). Everything in this row waits on what the leaderboard shows. |
| Ensemble across models | n/a | n/a | compare GPT/Claude/Gemini on disputed lines only | helps, but errors are correlated so spread understates uncertainty | n/a | **Use sparingly**; also the jury's "no token maxing". |

## 3. Rules we can already commit to (high agreement, cheap, testable)

1. **Never miss a round, never mis-index, always gross.** Tier-0 submission within seconds, then overwrite. Index = the invoice's printed `POS.` number (case 0: 1…4).
2. **Zero mass first.** Model `P(t=0) = 1 − P(covered)·P(related)` per line, from the clause numbers in `policy.txt` and the story in `description.txt`.
3. **`b`:** reject iff `P(inflated | charge) > y/(y+2·min(y,c))` (= 1/3 when the cap is inactive). Set `b = 0` when `P(t=0) ≥ 1/3`. Treat the 1/3-quantile as the **default**, with a tunable `B_MULT` (see §4).
4. **`a`:** shade below the median estimate by σ-dependent factor from the table above; never above `t̂` unless there is evidence that opponents accept above-`t` charges.
5. **Arithmetic in code:** the model returns quantity-justified, net unit price quantiles and flags; code computes `qty × unit × 1.19`.
6. **Widen the model's own intervals** (published: nominal 99 % intervals cover ~65 %, FermiEval; ensembles share errors, Kim et al.). Start with σ_eff = 2 × stated spread until we can check coverage some other way.

## 4. How to get an edge, given that code is not the bottleneck

The binding constraints are **no ground truth, no per-round feedback, 100 rounds, rank-scaled scoring, and a jury that scores economy and honesty.**
That makes the edge a *measurement* problem. Ranked by expected value, with how each is checked:

| # | Edge | Mechanism | How we measure it | Cost |
| --- | --- | --- | --- | --- |
| 1 | **Reliability field edge** | Teams that miss a round, mis-index or submit net values leak money to teams that don't (`b = 0` against a fair charge pays the charger 1.5×). | Dry-run all 101 cases through the pipeline; assert every `POS.` index is present, no NaN, finished < 54 s; watchdog that submits tier 0 if nothing is out by ~25 s. | low |
| 2 | **Slow-oracle backtest ("own rounds", labelled)** | After each live round we hold a real case. Run a *slow, expensive* process on it (multi-model, long reasoning, web price lookup, no time limit) to produce a pseudo-`t`. Score the 60 s pipeline against it with pinball loss at τ = 0.1 / 0.33 / 0.5 and interval coverage. | Rolling table over released cases; shows whether the fast pipeline is calibrated *relative to a stronger offline process*. Shared bias between slow and fast models is the known weakness, so also report disagreement across providers. | medium |
| 3 | **Opponent-population simulator ("own tournaments")** | Extend `sim/` to many lines and a menu of opponent types: honest-noisy (σ ∈ 0.05…0.4), strict, lax, accept-all, `b = 0` absentees, over-chargers. Pick `(a, b)` rules that do well **across** the menu (minimax regret), not against one guess. GPT-A's pure saddle `a* = argmax min(U,D)`, `b* = max{y : U ≤ D}` is the baseline: it guarantees non-negative expected score against any opponent actions under its stated assumptions. | Tournament table: expected net per line of each rule × each population; report worst-case column. This is the "evidence for choices" the jury asks for. | medium |
| 4 | **Cross-case price book** | The cases are synthetic and probably built from a finite catalogue of trades and items. Pool our estimates for the same item across rounds and shrink each new estimate toward the pooled value. | Check after ~10 released cases how often item types recur and how much the pooled estimate disagrees with a fresh single-call estimate. | low |
| 5 | **Leaderboard A/B across rounds** | Randomise one global knob per round (e.g. `B_MULT ∈ {0.9, 1.0, 1.1}`), regress round-level net on the knob with case-mix controls. Only possible if the leaderboard gives per-round scores. | Wave-2 Fable agent is computing the power; expect only large effects (> several %) to be detectable with 100 rounds. | low if data exists |
| 6 | **Photo and quantity checks** | The description and invoice often disagree on quantity (case 0: "approx. 0.2 m²" for a wall patch; photo shows a hole of roughly 30 × 30 cm). Use the photo only for "does this match the story / is the quantity plausible", not for pricing. | Spot-check against released cases. | low |
| 7 | **Economy narrative for the jury** | Cheap model for coverage/relatedness (short texts), one price call, cached priors, escalation only on disputed or expensive lines. Report tokens per round. | `meta.usage` totals in `runs/`. | low |

What does **not** work and should not be planned on: online recalibration from rejection outcomes, adaptive conformal updates, or any "learn `t` from settlements" step. They need feedback the API does not provide.

## 5. A decision for you: the `t = 0` free option

For a line that is excluded or unrelated, a positive `a` can only gain money (a rejected inflated charge pays 0, an accepted one pays `min(a, c)`), and **all five reports flag it**.
But `GAME_DESCRIPTION.md` frames the handyman as setting "the price … that you think you're entitled to", and the jury scores "clarity and honesty".
The rules allow it and the claimbot already does it implicitly (excluded lines are priced as if valid). Options:

- **Use it deliberately and disclose it** in the write-up as a game-mechanics finding, with the measured gain (if any).
- **Don't use it** (set `a = 0` on lines we believe excluded) and give up the upside against weak opponents.
- **Use it only at a small amount** and report it as an experiment.

My recommendation: disclose and use it, because the payoff is real and the rules text does not forbid it, but this is a call on spirit-of-the-game risk that is yours, not mine.

## 6. Next steps I'd take (nothing started)

1. Wire the pipeline's tier 0, the index parser (`POS.`), and `B_MULT` — owner: whoever holds `claimbot/`.
2. Build the multi-line population simulator and the pseudo-`t` backtest harness (research side, ≈ 1-2 h).
3. After round 1 (14:00), look at what the leaderboard shows per game; that decides whether edge #5 exists and whether anything online is possible.
4. Read wave 2 for ready-made baselines before building anything we could reuse.
