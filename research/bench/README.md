# Benchmark: compare approaches on our own machine

Replays candidate pipelines (prompt variant × model × aggregation) on the **released** cases and scores them against the hidden fair value
`t`, which we learn after each round from the public leaderboard (a bracket per line, see `../03-leaderboard-findings.md`).
**No other-team data is stored in this repo.** The bracket labels are derived from other teams' rows, so they live in the gitignored
`runs/bench/labels.jsonl`; rebuild them with `build_labels.py`. Everything committed here is code, prompts and qualitative hints.

| file | role |
| --- | --- |
| `build_labels.py` | reads the public leaderboard (other teams' rows in memory only) → `runs/bench/labels.jsonl` (bracket per line, our received charges, our `a`) |
| `bench.py` | runs prompt variants × models on labelled cases through OpenRouter, scores each answer by replaying the production `a`/`b` rule (`claimbot.pricing`) against the real charges. Includes an `ACTUAL` row = what our live bot did. `--web` adds OpenRouter's web-search plugin |
| `ensemble.py` | replays aggregation rules on saved answers: mean/median/trimmed `a`,`b`, belief pooling (with/without disagreement term), and an LLM "final reviewer" that reads all answers |
| `dspy_opt.py` | DSPy program + metric with textual feedback; `eval` scores a prompt, `optimize` runs GEPA (guarded: refuses < 6 cases without `--force`) |
| `prompts/` | `v0_original` (first claimbot prompt), `v1_current` (claimbot now), `v2_policy_math` (candidate, written 14:20 after games 1-2) |
| `annotations.json` | qualitative hints and `zero` flags per case/line (used for DSPy feedback; contains no numbers from other teams) |

Run: `uv run --with pyzipper python research/bench/bench.py [--variants ...] [--models ...] [--cases case_003] [--repeats 2] [--web]`;
DSPy: `uv run --with "dspy[litellm]" --with pyzipper python research/bench/dspy_opt.py eval`. Spend so far about $3 of the $50 OpenRouter limit.

## Metric (hindsight replay against brackets)

`b` side: each charge we received is classified fair (`a ≤ t_lo`) or inflated (`a ≥ t_hi`, or the line is excluded); unknown ones are skipped. Replaying `b'`: accept if `a ≤ b'` (pay `a`), else reject (pay 1.5 a if fair, 0 if inflated). `b_regret` = cost − best possible cost (EUR per line, lower is better).
`a` side: `a_score = a'/t_lo` when `a' ≤ t_lo` (certainly fair; revenue rises with `a` while fair), 0 when `a' ≥ t_hi`, otherwise "uncertain" and excluded. `bias` = mean log(model median gross / `t_lo`).
Opponents are held fixed, brackets are not point values, and weights are untuned. 3 cases = about 12 scored lines, so **everything below is anecdotal**.

## Results (as of game 3, 14:35 CET)

**1. Prompt variants, in-sample (games 1-2; v2 was written after seeing them).** v2 looked better for most models: gpt-6-luna regret 585 → 119, gemini-3.8-flash 393 → 252, gpt-6.1-terra 373 → 192, claude-sonnet 599 → 347 (v1 → v2, 2 repeats). The live bot's actual row on those games: 1142.
**2. Prompt variants, out-of-sample (game 3; v2 frozen before it started).** The gain **did not replicate**: v1 vs v2 regret was luna 230 vs 245, gemini 260 vs 298, inkling-mini 152 vs 257, sonnet 298 vs 293, terra 37 vs 9. Most models under-priced game 3 by 40-55 % (bias −0.4 to −0.55); gpt-6.1-terra over-priced (+0.5) and had by far the lowest `b` regret. The model-to-model spread and each individual model's bias, which flips between cases, matter more than the wording of the prompt. (Corrected at 14:52, see the bias-correction section: the bias *pooled over models* is small, about −0.00 to −0.14 in log units in every game.)
**3. Ensembles.** In-sample (games 1-2, v2): median of 7 models regret 262 vs 402 for the average single model; median of the 3 cheap models (luna, gemini-flash, haiku) 271 at $0.011 per case; an LLM final reviewer (gpt-6-luna) 241 for +$0.003 and about +10 s; belief pooling with a disagreement term was worse (444). Out-of-sample (game 3): **no aggregator beat the average single model** (single 241, mean 260, median 293, pooled 288, reviewer-luna 288); averaging does not cancel an error all models share. One exception worth a second look: the gpt-6.1-terra reviewer fixed the `a` side (bias +0.06, `a_score` 0.97) but not the `b` side.
**4. Tools: web search.** OpenRouter's web plugin (3 results) on luna / gemini-flash / terra over 3 cases: regret 357 → 368, 232 → 300, 136 → 185, higher cost (terra $0.003 → $0.03 per case), +1-5 s. No benefit seen; the expert values are not market prices.
**5. DSPy/GEPA.** The program, metric and feedback work end to end (seed prompt scores 0.66-0.80 mean over the cases). A first GEPA run on 3 cases with `--force` (train = validation, 24 rollout budget, stopped early) raised the in-sample score from 0.80 to 0.93 after one reflection step, and **the new prompt had memorised the labels**: it contained "a shop diagnostic for a laptop is about EUR 50-70 net / 60-84 gross" (the leaderboard bracket from the feedback) and "pre-existing scuff polish: ~0.01". So the number means nothing, and the guard (`--min-cases 6`, no `--force`) is right. Before a real run: (a) have at least 6-10 labelled cases and a **held-out** validation set that the optimiser never sees, (b) strip numeric brackets and case facts from the feedback (give direction and clause hints only), (c) read the optimised text for copied values, (d) only promote it if it beats the seed on games released after it was frozen. Never commit an optimised prompt unreviewed.

## Update 14:45: game 4 and the new acceptance rule (`rule_replay.py`, no API calls)

At 14:39 the live bot changed `b` for valid lines to at least 1.25 × the median (`CLAIMS_B_VALID_MULT`), tuned on game 3. Replaying the old and new rule on **all saved model answers** (176 answers, games 1-4; b_regret EUR/line, lower is better):

| rule | game 1 | game 2 | game 3 | game 4 | all |
| --- | ---: | ---: | ---: | ---: | ---: |
| old 1/3-quantile | 521 | 443 | 224 | **185** | 339 |
| 1.0 × median | 509 | 313 | 146 | 230 | 274 |
| 1.25 × median (live now) | 688 | 154 | 101 | 296 | 236 |
| 1.5 × median | 784 | 116 | 67 | 325 | 230 |

- It helps in games 2 and 3 (models under-priced) and **hurts in games 1 and 4** (accurate or over-priced medians: more inflated charges get accepted). Game 4 is the only game released after the change: regret went **185 → 296** (b_score 0.69 → 0.50). The pooled gain comes from games 2-3, which the rule was tuned on.
- Reading: a multiplier is a bet on a systematic under-estimate. The sign of the models' price bias changed from game to game (high, low, low, mixed), so a fixed multiplier is unlikely to hold. The data are too few to tell either way; this argues for estimating the bias from earlier brackets (leave-one-game-out) instead of fixing it by hand.
- Game 4 prompt results (out-of-sample for v1 and v2): no variant stands out; v2 is better for 4 of 7 models and worse for 3, the model-to-model spread is larger than the prompt effect. The live bot's actual row on game 4: regret 340.
- Game 4 labels: one excluded-looking line, one line with a tight bracket (about 228-253) and one line where our `a` was about half of the lower bound.

## Update 14:52: does a bias correction learned from other games help? (`bias_correction.py`, no API calls)

Setting: each saved answer's price quantiles are scaled by `exp(-λ·β)`, with β = mean log(model median / reference) over earlier games (forward) or all other games (leave-one-game-out), per model or pooled over models, then the production rule runs. Reference = geometric middle of the bracket (or the lower bound where there is no upper bound, which makes the measured bias too optimistic).

- **The pooled bias is small and has one sign.** Mean log(median / reference), pooled over models and prompts: game 1 −0.14, game 2 −0.06, game 3 −0.12, game 4 −0.13 (with the lower bound as reference: −0.07, 0.00, −0.12, −0.11). So models are 0-14 % low on average, not the 40-55 % I read off game 3 alone. The **spread between models is large**: standard deviation of the per-answer bias 0.18-0.49 per game.
- **Forward test (games 2-4; b_regret EUR/line, lower is better).** With the old 1/3-quantile rule: 312 uncorrected → 272 pooled β (λ = 1), 262 per-model β; shrunk λ = 0.5: 290 / 280. With the live 1.25 × median rule: 169 → 151 pooled, 153 per-model. Gains of about 10-16 %, from games 2 and 3. **Game 4 got worse in every variant** (185 → 204-209; 296 → 298-315). With the lower bound as reference the gains shrink to 2-5 %. Leave-one-game-out looks similar (339 → 284-301; 236 → 219-227). The `a` score does not move (0.57-0.60).
- **Reading:** with four games this is a first sign at best. A correction learned from past games is not a big lever, because the shared part of the error is small. Most of the error is per-line and per-model variance, which a fixed multiplier cannot fix. It would not replace a better reader of the policy or a better price anchor, and it interacts with the acceptance multiplier (the live 1.25 × rule already gives a larger change than the correction, at the cost of game 4). Re-run on every new game; promote nothing on this evidence.

## Update 14:56: past games as a reference (retrieval) (`rag_bench.py`)

What the cases share (4 games): every policy is the same "WD-2026" framework with a different **edition** (electronics, portable equipment, glazing, mobility). Only editions that repeat share much text (47 % of lines for games 2 and 3, 3-9 % otherwise). Trades and vendors differ by case, a few item words recur (diagnostic, call-out, repair).
Test (leave-one-game-out, so it uses "future" games and is optimistic): for each invoice line retrieve the best matching lines of the *other* games by TF-IDF over the line text and trade, put them with the experts' outcome (excluded / amount bounds) into the v2 prompt, run 4 models × 2 repeats, compare with plain v2.

- **Result:** pooled b_regret 215 → 193 (−10 %), `a` score 0.64 → 0.65, |bias| 0.29 → 0.32. Per model and case it is mixed: clearly better for gemini and haiku on game 3 and for most on game 4, worse for terra on game 1 (699 → 900) and for luna on game 3. With 2 repeats per cell and 16 cells this is **within noise**.
- **It also shows the main risk.** The retrieved neighbours were often spurious (a door-frame line matched a bicycle repair) or **contradictory**: "diagnostic inspection" is paid (about 60-84) in game 2 but a "diagnostic report and call-out" is excluded in game 1, because the outcome depends on the policy clause and edition, not on the item wording. A retrieved amount can anchor a model on the wrong answer.
- **Reading:** with four games there is almost nothing to retrieve, so this cannot yet show a benefit. If memory is used it should be keyed by **edition and clause** (what the clause did to the amount) and by **normalised item category** (gross amount per unit), not by raw line text; amounts should only shrink an estimate, not replace it. Re-run after about 15-20 completed games; until then the evidence says "no harm, no clear gain".
- Memory contains numbers derived from other teams' rows, so it stays in the gitignored `runs/` and is rebuilt locally with `build_labels.py`; it is never committed.

## Update 15:50: architectures, photos and a multiplier sweep on games 1-8 (`arch_bench.py`, `image_test.py`, `multiplier_sweep.py`)

**Game results first.** After game 8 we are 6th of 12 (3rd after game 6): games 7 and 8 were -4,137 (rank 11) and -3,238 (last). In both, the *whole field* priced far above the expert value (game 7: expert about 450, charges up to 1,112; game 8: expert about 30-70 per line, charges up to 217), and we accepted 10 of 11 and 11 of 11 incoming charges, paying 6.3k and 3.9k, most of it for inflated charges; our own `a` was inflated too (1.6x; 2.5-7x on three lines). The silent teams have gone (0 silent in games 6-8, 5 in games 1-5), so the 1.5x penalty subsidy that rewarded high charging has disappeared.
The readers did **read the clauses right** in both games (game 7: leak location cap, lump-sum and combined-line rules; game 8: debris clause 5.2.1 covers roof timber, glass, felled tree and a root ball under 1 m3, and excludes ground material, so lines 5-7 are excluded). The failure is **price level**: readers say 850-1,100 where the experts pay about 450 (game 7), and about 100-200 where they pay 30-70 (game 8).

**Architectures** (19-26 lines, cases 1-8, same metric; b_regret EUR/line, lower is better; **noise is large, one case dominates**):
single readers luna 586 / terra 513 / fable 566; median of the three in parallel 583; lowest-a / highest-b rule 573; cascade luna+terra -> fable 583 and it **escalated on 0 of 7 cases**; cheap draft + strong review agent 600 (terra) / 576 (fable). **No orchestration beat a single reader.** The three readers agree with each other, also when all are wrong (game 7), so disagreement triggers, voting, medians and reviewers have nothing to catch. Same-edition memory (cases 2, 5, 6 share a policy; case 6 is the same story as case 2): for case 6 the estimate moved from 250/464 to 1,150/1,238 against an expert lower bound of 744; over the 6 lines of those cases terra's `a` score went 0.58 -> 0.94 with equal regret, luna's regret got worse (34 -> 348). Mixed, n = 6.
**Photos:** no photo vs full photo vs full photo + four zoomed crops (a stand-in for a zoom/crop tool), 2 readers x 8 cases: no photo was as good or better for both (luna regret 667 none / 887 full / 845 tiles; terra 622 / 659 / 692), photos raised the bias (+0.18 to +0.28 for luna, +0.23 to +0.37 for terra) and the prompt by 1.6-3.8k tokens. The photos are generated scenes that repeat the text (case 8: shed, debris, soil heaps, root ball). **No evidence that photos, zooming or cropping help.**
**Multiplier sweep** (all saved answers, KA/KB for open lines): regret by KB_open on games 1-6 / games 7-8 / all: 0.5 -> 680 / 547 / 641; 0.8 -> 293 / 1,438 / 630; 1.0 -> 148 / 1,592 / 573; 1.25 -> 116 / 1,778 / 605. KA_open: share of our charges that would be inflated at 0.8 / 0.9: games 1-6 0% / 18%; games 7-8 100% / 100% (even 0.5: 75%). A multiplier tuned on games 1-6 is wrong for games 7-8 and vice versa: **the price-level bias depends on the kind of line** (devices and repairs: readers low; disposal, lump-sum and service lines: readers 2-5x too high), so one number cannot fix it.

## Update 15:58: is parsing a bottleneck, and are specialist agents better? (`parse_profile.py`, `specialist_bench.py`)

**Parsing is not a bottleneck.** On the 8 decrypted cases `load_case` takes 0.02-0.12 s (including the photo downscale), `pdftotext` about 15 ms, and the printed POS numbers parse correctly on all 8 (including the two-page invoice of game 7). The policy is 97.7 % of the prompt characters (9-19k tokens; the invoice is 240-470 tokens).
**Model latency follows OUTPUT tokens, not input.** Regression over the saved answers: per 1,000 input tokens the latency changes by about -0.3 to +0.2 s for nearly every model (Fable +0.14, luna -0.03, terra -0.19), per 1,000 output tokens it grows by 3-13 s (luna 6.3, terra 10-13, Fable 9.7, Gemini Flash 3.9, GLM-flashx 3.6). Reading a 19k-token policy is nearly free in time; writing the JSON (about 1,000-1,350 output tokens, mostly the rationales) is what takes the 8-19 s. Levers: shorter rationales / a compact schema (latency), prompt caching or an edition digest (cost: for Fable 24k input tokens are about $0.19 of its $0.25 per case).

**Specialist agents vs one generalist** (26 lines, 8 cases, same metric; coverage agent reads the whole policy and returns validity, quantity, fraction, limits, anchors but no prices; price agents see only description + invoice, no policy, k cheap models from different providers, median price):
| architecture | b_regret | a_score | bias | $/case | latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| generalist luna / terra / fable | 549 / 613 / 653 | 0.34 / 0.39 / 0.49 | +0.25 / +0.33 / +0.28 | 0.001 / 0.023 / 0.247 | 10 / 17 / 19 s |
| coverage(luna) + 1 price agent | 573 | 0.59 | +0.13 | 0.003 | 9 s |
| coverage(luna) + panel of 3 | 680 | 0.54 | +0.07 | 0.008 | 9 s |
| coverage(luna) + panel of 5 | 614 | 0.56 | -0.03 | 0.009 | 9 s |
| coverage(terra) + panel of 1 / 3 / 5 | 565 / 673 / 607 | 0.59 / 0.54 / 0.56 | +0.13 / +0.07 / -0.03 | 0.024-0.030 | 14 s |
- **No clear gain.** b_regret is within noise of the generalists (and one game dominates it); excluding games 7-8 the generalists are as good or better (terra 66 vs 138). The specialists lower the over-pricing (bias +0.25..+0.33 to +0.13..-0.03) and raise the `a` score (0.34-0.49 to 0.54-0.59), probably because the price agents without the policy do not inherit a policy-reader's inflated amounts; that is the one consistent difference and it is untested out of sample.
- **More price agents do not help** (k = 1, 3, 5: 573, 680, 614): cheap models from different providers share their price-level error, so a bigger panel averages the same mistake. The decomposition is not slower (parallel, about 9-14 s) and costs $0.003-0.03 per case.
- **How many agents?** The data supports 1 reader, or 2 specialists (coverage + one price call). More agents only make sense if each brings **independent information** (a labour/parts breakdown, a stated anchor, a same-edition memory), not another look at the same inputs.

## What this does and does not support

- Supports: a benchmark loop exists; the live bot's actual `b` replay (regret ≈ 1142 on games 1-2, 281 on game 3) can be compared with any candidate on the same lines; model price-level bias is large and varies by case; ensembles and web search are not a fix by themselves.
- Does not support: any claim that v2 or an ensemble is better. With 3 cases that would be overfitting. Re-run on every new completed game (`build_labels.py`, then `bench.py --cases case_00N`); a candidate only counts on games released **after** it was frozen.
- Next tests worth running: (1) the variance side, i.e. which signals shrink the per-line spread (description anchors, cached price table, more diverse models) and (2) the policy-reading step, since a misread clause (game 1) cost more than any bias.
