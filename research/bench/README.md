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

## Update 16:15: the euro evaluator (`euro_replay.py`, `euro_replay_check.py`, `euro_eval.py`)  **[PARTLY SUPERSEDED, see the 16:50 audit below: the claims 'trust', '100 %' and 'worst case consistent with the data' were too strong]**

**Everything above `b_regret` / `a_score` is a proxy with known flaws** (one-sided brackets used as if they were values, charges skipped when unclassified, price ratios instead of euros, the cap ignored, ~20-26 lines, in-sample prompts, one model draw per cell). Use it to find ideas, not to decide. The decision tool is the euro replay below.

**What it is.** The official payoff (accepted: min(a, c); rejected and fair: 1.5 a; rejected and inflated: 0; cap c >= 4t with a floor) applied to our candidate `(a, b)` per line against the real field of that game, reconstructed only from the public settlement rows (charges, fair/inflated bits, a bracket for `t`, an interval for every reviewer's limit, a proven lower bound for the shared cap). Every unknown is carried as an interval, so each game gets a net range `[lo, hi]` and an identified share. It never uses point guesses for hidden quantities.
**How it was validated (both passed):**
1. *Reproduces reality:* replaying our logged ACTUAL `(a, b)` returns our actual net **exactly in 7 of 9 games** (range width 0) and to within EUR 360 / 1,000 in games 8 and 9 (99 % of pair outcomes identified); the true value was inside the range in 9 of 9.
2. *Sound on known truth:* on 12,000 synthetic cases (random fields with silent, rational, accept-everything, strict and over-charging teams, random cap) the true counterfactual net was inside `[lo, hi]` **in 100 %** (largest overshoot 6 cents of rounding); median range width EUR 1.9k, 86 % of pair outcomes identified. The first version failed this test (97.9 %; caught clipped accepted amounts at the cap), the fix is in the code.
**What it cannot do:** it holds the field fixed (opponents do not react), assumes our readers' saved answers are what we would have submitted (one draw each), and bounds the exposure to charges nobody ever revealed with a heuristic ceiling (not a proof, but it held on every synthetic case). Upper bounds are very loose (an unseen lax reviewer could have accepted anything); **the lower bound is the useful number: the worst case consistent with the data.** A candidate is only "better" if its whole delta range is above zero.

**First results, games 1-8** (readers luna / terra / fable through the engine; our actual net over these games +6,886; `delta` = candidate minus actual):
| candidate | net range | delta vs actual | surely better / worse games |
| --- | ---: | ---: | ---: |
| actual (live bot) | [6.9k, 7.2k] | [0, +0.4k] | |
| luna, engine defaults (KA .9, KB 1.25) | [-15.8k, 85.9k] | [-22.7k, +79.1k] | 4 / 1 |
| terra / fable, engine defaults | [-2.4k, 38.3k] / [-14.9k, 43.6k] | [-9.3k, ...] / [-21.7k, ...] | 3 / 0 each |
| luna, KA 0.8 / KB 1.0 | [5.0k, 86.2k] | [-1.9k, +79.3k] | 4 / 0 |
| luna, KA 0.8 / KB 0.8 | [9.2k, 85.8k] | [**+2.3k**, +79.0k] | 4 / 0 |
| luna, **KA 0.7 / KB 0.9** | [18.2k, 71.4k] | [**+11.3k**, +64.6k] | **6 / 0** |
| luna, KA 0.6 / KB 0.6 | [17.7k, 58.7k] | [**+10.8k**, +51.8k] | 4 / 2 |
| terra, KA 0.8 / KB 0.8 or 1.0 | [~8k, ~87k] | [+1.2k / +0.8k, ...] | 3 / 2 |
| luna, excluded lines charged 'as_valid' vs 'zero' | same worst case (5.0k vs 4.9k), best case 86k vs 44k | | the free option does not change the worst case |
- **Reading:** with the luna reader and a lower charge and a tighter acceptance limit (KA 0.6-0.8, KB 0.6-0.9) the **worst case is better than what we actually earned** (delta lower bound +2k to +11k), while the engine defaults (KA 0.9, KB 1.25) can lose up to 22k in the worst case. This reproduces, now in euros, why the 1.25x acceptance multiplier hurt in games 7-8.
- **Caveats on these first numbers:** the multipliers were picked from 7 candidates after seeing games 1-8 (multiple comparisons), cases 1-4 shaped the reader prompt, one saved draw per reader, game 9+ not yet included. Treat them as the first shortlist to confirm on the games that come next, not as a final choice.
- Usage: `python3 -I research/raw4/scripts/fetch_field.py FIELD_DIR` (FIELD_DIR **outside** the repo), then `uv run --with pyzipper python research/bench/euro_eval.py FIELD_DIR --us "Team Name"`. Re-run `euro_replay_check.py FIELD_DIR --us "Team Name" --synthetic 2000` after any change to the replay.

## Update 16:35: out-of-sample replay of games 9 and 10 (`euro_game_report.py`)

The multiplier shortlist (luna KA .7/KB .9, KA .6/KB .6, KA .8/KB .8; terra KA .8/KB .8) was chosen from games 1-8 at 16:15. Games 9 and 10 came afterwards, so they are a genuine out-of-sample replay. Our official net was -8,872 (game 9) and -2,792 (game 10), sum **-11,664**. The evaluator's replay of our logged actual submission for game 9 returned [-8,872, -7,875], which contains the official result.
| candidate | net range, games 9+10 | delta vs official (lower / upper bound) | verdict |
| --- | ---: | ---: | --- |
| luna KA .7 / KB .9 (shortlist) | [-2.6k, +1.7k] | +9.1k / +13.4k | surely better |
| luna KA .6 / KB .6 (shortlist) | [+6.0k, +9.7k] | +17.6k / +21.3k | surely better |
| luna KA .8 / KB .8 (shortlist) | [-3.1k, +0.5k] | +8.6k / +12.2k | surely better |
| terra KA .8 / KB .8 (shortlist) | [-0.7k, +6.8k] | +11.0k / +18.4k | surely better (but see below) |
| luna / fable engine defaults (KB 1.25) | [-12.6k, -3.8k] / [-12.8k, -3.5k] | -1.0k / +7.9k and -1.1k / +8.2k | unclear |
| luna strict KA .8 / KB .45 (formulated after game 9) | [+5.9k, +9.5k] | +17.6k / +21.2k | surely better |
| luna charge .8, reject everything | [+6.0k, +9.8k] | +17.7k / +21.4k | surely better |
- **Reading:** every pre-chosen shortlist candidate beat the live result out of sample, the live-style engine defaults did not, and strict acceptance was the best family. All of this holds opponents fixed and one saved reader draw per cell.
- **Caveats:** games 9 and 10 are in the same regime (the field over-charged), which favours strict rules; games 1-6 favoured lenient limits. The reader matters: in game 10 luna's candidates were positive while terra's and fable's were negative with the same multipliers (their prices were higher), so a rule is only as good as the reader behind it. Our logged submission for game 10 is missing (the log ends at game 9), so only the official net is known for it (-2,792, all of it paid for 9 accepted charges on one line whose true value was about 157-218).
- **How the old proxy differs from the euro replay on the same two games:** it ranks the candidates in the same broad order for the limit (reject everything and strict best, defaults worst: b_regret 230-314 vs 4,848-5,201), but it gives no euro size, and it disagrees on terra KA .8 / KB .8, which its `a_score` rates 0.0 (charges counted as inflated) while the replay shows it earned on the charging side in game 9 ([+4.3k, +8.3k]). Use the euro replay for decisions.

## Update 16:50: independent adversarial audit of the evaluator, and what changed (`../raw5/gpt-G-evaluator-audit.md`)

A GPT reviewer audited `euro_replay.py` adversarially (a second audit by a Fable agent is still running). **Verdict: not safe as the sole live selector as shipped.** What it found, and what we did:
- **Four critical defects** (wrong counterfactual answers): (C1) the largest accepted payment was wrongly treated as proof of inflation; (C2) the cost ceiling for charges nobody revealed (`4 * max(...)`) had no justification and could print a lower bound hundreds of euros above a feasible result; (C3) omitted lines were silently dropped instead of settling at the defaults a = b = 0; (C4) amounts are rounded to cents although the platform contract is unspecified (can flip a decision on sub-cent inputs).
- **Measured:** 42,000 rule-exact adversarial trials: the shipped replay missed the true payoff 936 times (30 above the upper end, worst miss EUR 14,588). The reviewer's own 480,000-case search: original logic 13,346 misses below `lo` and 1,296 above `hi`; with fixes 1+2 **0 and 0**. My earlier synthetic test (12,000 cases, 100 %) was not adversarial enough to find these.
- **Applied now (patch A):** C1, C2 and C3 are fixed in `euro_replay.py` (the repo file now behaves as the reviewer's fixed version; I re-ran the stress search against it: 0 misses in 480,000 cases per field size). The module docstring no longer claims a worst case. **Not applied yet:** C4 (exact cent-grid arithmetic and input validation; needs the organisers' money contract; all 4,620 observed rows passed the reviewer's cent-grid check), the paired same-field comparison, and the diffs B and C.
- **Other findings that still stand:** (M1) replaying our actual submission reconciles the books but has little power to test a different `(a, b)` because it reuses its own outcomes; with all of OUR rows withheld the real coverage was 9/9 games but the median width grew to EUR 4,663 (game 7 alone EUR 61,663); (M2) summed per-pair endpoints can contain states that cannot coexist, so the bounds are conservative in an uncontrolled way; (M3) the candidate sweep compares one saved draw per reader on the games that shaped the prompt; (M4) **the scorecard does not evaluate tournament rank** (greater own net can buy a worse rank, because opponents' balances change too); (M5) the offline scorer imports `bench.py` and loads `.env` and maps candidates by `reader index + 1` instead of the printed POS numbers.
- **Discrimination is weak:** disjoint intervals certify only about 25 % of strict policy orderings (median width about 3.3 x the median gap between sensible policies); the lower endpoint has Spearman 0.74-0.78 with the truth, but 6 false sure orders per 56,350 in the shipped version (0 after the patch). A candidate is therefore not proven better by a larger lower endpoint alone.

**Numbers with the patched evaluator** (games 1-9, our actual net -1,986; game 9 now included; selected from games 1-8, so game 9 is not clean): luna KA .6 / KB .6 delta [+24.7k, +68.2k], surely better in 5 of 9 games and surely worse in 2; terra KA .8 / KB .8 [+17.1k, +96.8k]; luna and fable engine defaults (KB 1.25) [-18.3k, +82.4k] and [-12.6k, +42.8k]. **Games 9-10 out of sample, patched:** the shortlist is still surely better (lower deltas +8.6k to +17.6k, terra .8/.8 now +12.4k) and the 1.25 defaults still unclear; the conclusions did not change, the endpoints moved by up to about EUR 1.4k.

**What the evaluator may and may not be used for (wording from the audit):**
- *Safe to say:* "We reconciled the organiser's historical net totals against the public settlement rows. We bound each saved policy's net on the same completed games with opponents' submissions held fixed; the bounds are conservative because charges, limits and caps are only partially identified. Several tighter settings have positive lower deltas versus our historical submissions. We selected them retrospectively and test the frozen policy separately on later games."
- *Do not say or do:* guarantee a live gain, call the lower endpoint a "worst case", pick a multiplier by its midpoint or lower endpoint alone, quote an expected euro return, estimate a reader's quality from one saved draw, convert our net to ranking points, or treat a replay of our own actual submission as a test of a different policy.
- *Next gates before the evaluator may choose a live policy:* a frozen shortlist scored on consecutive games played after the freeze, with saved submission receipts and timing; paired same-field comparisons; exact cent-grid accounting once the contract is confirmed; the second audit's findings.

## Update 17:05: second audit (Fable, `../raw5/fable-G-evaluator-audit.md`) and RETRACTIONS

Two independent audits now agree. **The patched `euro_replay.py` is sound as a bound** (0 misses in 480,000 adversarial line replays and 1.2 M more by field size; 0 of 732 real leave-one-team-out tests; 9 of 9 games and 33 of 33 lines with all of OUR rows withheld; the organisers' matrix equals the row sums in 120 of 120 team-game cells). **The version I first shipped was not**: truth fell below `lo` in 2.81 % of 240,000 adversarial line replays (0.49 % in 12-team fields, worst miss EUR 29k) and once on real rows. My published "100 % of 12,000 synthetic cases" could not detect either defect (it sums 88 pairs per game with a EUR 1 tolerance and a benign generator), and `euro_replay_check.py` still reports 100 % on the broken version. **Use `research/raw5/scripts/g_adversarial.py` as the regression gate, not that number.**

**What the tool actually measures.** Split every candidate range into revenue (set by `a`) and cost (set by `b`):
- **Acceptance limit `b` (cost side): measured.** Range width EUR 0.1k-4.2k over games 1-8; it separates 97 of 171 candidate pairs.
- **Charge `a` (revenue side): NOT measured.** Range width EUR 32k-104k; it separates 0 of 342 pairs, and the lower bound moves by 9-16k when the multiplier moves by 0.05. **Do not use the evaluator to choose the charge multiplier or to rank two candidates.**
- Synthetic power about 47 %: it stays silent on half of the truly better candidates.

**Retractions of things I said earlier (and the correct statement):**
1. *"luna KA .7 / KB .9 is surely better by 11k"* -> with the patch it is +15.4k, of which **+10.1k (66 %) is game 1**, where the live bot misread the policy. On games 5-8 the order of the three luna candidates reverses, and it reverses again with the second saved luna draw (bounds move by EUR 3-14k). Not robust.
2. *"Engine defaults can lose 22k, this is why the 1.25 limit hurt"* -> misattributed: 16.8k of it is the unidentified revenue side of KA 0.9. On the cost side the defaults (KB 1.25) are **surely 2.7k better than what we actually played**; KB 1.25 against KB 1.0 costs between 0.8k less and 5.5k more.
3. *"Games 9 and 10 are a genuine out-of-sample test"* -> **only game 10 is.** Game 9 had already been played and its rows were public before the shortlist; I did not use it for the selection, but it is not clean.
4. *"The worst case consistent with the data"* -> say "proven lower bound on those past games", not an attained worst case.
5. *"The free option does not change the worst case"* -> true by construction (the worst case of a charge on an excluded line is 0); it is not evidence for or against the free option.

**The limit evidence, honestly (cost by acceptance multiplier, luna answer, actual cost over games 1-8 was 37.1k):** KB 0.5 / 0.8 / 1.0 / 1.25 -> cost about 30.5k / 29.2k / 28.8k / 30.1k-34k: **flat between 0.5 and 1.0 over eight games** (within 2.5k). Per game: strict limits cost MORE in games 5 and 6 (penalties for rejecting fair charges: KB 0.5 costs 7.9k and 6.6k against 5.4k and 4.9k) and far LESS in games 7-9 (the field over-charged; game 8 about 0.3k vs 1.3-1.8k, game 9 1.9k vs 14.2k-15.2k). **Game 9 alone is worth 12-13k between KB 0.5 and KB 1.0.** So the measured evidence says: lower limits win when the field over-charges and lose a few thousand euros per game when it does not; the generalisation depends on which regime the next games are in. The case for a strict default rests on the asymmetry (a wrong acceptance costs a full charge, a wrong rejection half a charge) and on what the strongest opponents do, not on this evaluator alone.

**Safe to use the evaluator for:** reconciling our net with the public rows; discarding candidates that are *surely worse* than what we played on those games; setting the limit rule from the cost side. **Not for:** the charge multiplier, ranking candidates, forecasts or expected gains, tournament rank (the tool scores our net only), or any claim that identified share means accuracy. Do not pick by a lower-bound difference smaller than the draw noise (EUR 3-14k). Exact safe write-up wording is in the Fable audit, section 8.

## Update 17:15: the acceptance limit measured on the trusted cost side over games 1-14 (`limit_sweep.py`)

Only the reviewer cost is evaluated (our charge is set to 0), using the audited `euro_replay.py`; cost ranges are narrow (often exact). `b = k x median` on lines with P(valid) >= 2/3, else 0. The live default is k = 1.25.
| k | LIVE medians, games 1-9 (actual cost 52.3k) | luna medians, games 1-14 (actual cost 69.0k) |
| --- | ---: | ---: |
| 0 (reject all) | 32.0-32.3k, saves 20.0k | 45.6-45.8k, saves 23.2k |
| 0.45 | 34.0k, saves 18.3k | 44.6-44.7k, saves 24.3k |
| 0.6 | 36.3k, saves 16.0k | 44.8-44.9k, saves 24.0k |
| 0.8 | 45.5-45.8k, saves 6.5-6.8k | 52.4-54.0k, saves 14.9-16.5k |
| 1.0 | 46.1-47.8k, saves 4.5-6.2k | 56.7-60.7k, saves 8.2-12.3k |
| **1.25 (live default)** | 48.7-52.3k, saves 0.0-3.5k | 58.4-65.0k, saves 4.0-10.6k |
- **Reading:** the live default saves almost nothing against what we actually played (it IS roughly what we played). Cost falls steeply between k = 0.8 and k = 0.6 (the field's fair charges cluster around 0.7-0.8 of the value) and is flat below 0.6, down to reject-all. Strict limits cost more only where the field charged fairly: games 2, 5, 6 (+0.9k, +2.5k, +1.8k at k = 0.45) and a few hundred euros in game 13; they save 2.4k in game 10, 1.0k in game 14 and 13-14k in game 9.
- **Freshest games, 11-14 (not used for any choice):** k = 0.45 costs 12.7k against 13.9k actually paid (saves 1.2k); k = 1.0 and 1.25 save nothing. In a calm stretch the choice barely matters; in an over-charging stretch it is worth 10k+ per game. Asymmetric: the downside of strict is a few thousand in fair-heavy games, the downside of lenient is 5-15k in over-charging games.
- **Mechanics:** the live code uses `b = max(1/3-quantile of the belief, B_VALID_MULT x median)`, so lowering `B_VALID_MULT` alone cannot go below the quantile (about 0.9 x median at a spread of 0.2); a median-based cap is needed to reach 0.45-0.6.
- **Not measured here (and not measurable by this evaluator):** the charge multiplier, model or ensemble choice, memory.

## Update 17:35: the acceptance factor chosen, and why 0.55 (cost side, trusted part of the evaluator)

Money saved against what we actually paid, by factor `k` (`b = k x median` on valid lines, else 0):
| k | LIVE medians g1-9 | cheap reader g1-6 (calm) | g7-10 (over-charging) | g11-15 (latest 5) | g1-15 (all) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.40 | +18.9k | -2.4k | +24.4k | +0.5k | +22.4k |
| 0.45 | +18.3k | -2.0k | +25.1k | +1.2k | +24.3k |
| 0.50 | +18.5k | -1.4k | +23.6-23.8k | +0.7..1.2k | +22.9..23.5k |
| **0.55** | **+17.4k** | **-1.1k** | **+21.8-21.9k** | **+1.8..2.3k** | **+22.5..23.1k** |
| 0.60 | +16.0k | -0.7k | +21.7-21.8k | +0.7..2.0k | +21.8..23.2k |
| 0.70 | +11.8-12.0k | +0.6..0.9k | +17.6-17.7k | +0.1..2.2k | +18.3..20.8k |
| 0.80 | +6.5-6.8k | +2.8..3.5k | +11.0k | -1.5..+1.0k | +12.2..15.6k |
**Choice: 0.55.** It sits safely below the cliff (savings drop from about 17k to 12k between 0.6 and 0.7 on the live medians), keeps about 95 % of the best overall saving, costs less than 0.45 in calm stretches (-1.1k vs -2.0k per six games) and is the best tested value in the latest five games. Going from 0.55 to 0.45 buys 3k more in an over-charging stretch and loses about 1k per calm stretch. The previous default of 0.9 sits above the cliff (about 5-6k saved), as does the old 1.25 (0-3.5k). `CLAIMS_B_MEDIAN_MULT` overrides it (0 restores the quantile rule with the `B_VALID_MULT` floor); check that no `.env` on the live machine sets it explicitly. Cost side only; the charge multiplier is not evaluated.

## Update 18:05: re-check of the factor on the live medians of games 1-15 (what the 0.55 choice does and does not rest on)

Same cost-side replay, but each game's medians and validity (`q`) taken from the live bot's own log (`outputs/model_outputs.json`), so the medians include the price-reference era (games 10-15). The live bot played `b = 0.5 x median` in games 10-12 and `0.9 x` in games 13-15 (set on the live machine), so "k" below is a re-pricing of the same lines, not a new run.

Reviewer cost per game in EUR (midpoint of the evaluator's range; lowest per game marked):
| game | 0.45 | 0.55 | 0.7 | 0.9 | 1.25 | actually paid |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | **2249** | **2249** | 4464 | 4464 | 4464 | 4464 |
| 2 | 8302 | 8302 | 8017 | 6912 | **6539** | 7470 |
| 5 | 7943 | 7943 | 7943 | 5997 | **5414** | 5414 |
| 6 | 6757 | 6637 | 6318 | 6093 | **4877** | 4877 |
| 7 | **673** | 1893 | 3046 | 5219 | 6332 | 6332 |
| 9 | 2418 | **1902** | 3740 | 10957 | 14692 | 15191 |
| 10 | **2792** | 3133 | 3226 | 3349 | 3566 | 2792 |
| 12 | 9806 | 9806 | 8535 | **7155** | 9359 | 9806 |
| 15 | 9052 | 9052 | 8952 | 7428 | 7846 | 7428 |
(Games 3, 4, 8, 11, 13, 14 omitted for length; their per-game costs differ by at most about 1.3k between factors.)

Extra cost against the best fixed factor of each game (hindsight regret): k=0.45 12.4k, 0.55 13.8k, 0.7 18.1k, 0.9 22.1k, 1.25 29.1k over games 1-15. Split: games 1-9 0.55 = 8.3k vs 0.9 = 20.2k (game 9 alone is 9k for 0.9); games 10-15 0.55 = 5.4k vs 0.9 = 1.9k.

Honest reading:
- The 0.55 choice is a **risk choice**, not a demonstrated gain in the current regime. Its advantage comes from over-charging games (7, 9: tens of thousands); in the six latest games (10-15, price references on) 0.9 would have saved about 1.7-2.9k more than what was played, while 0.55 would have saved nothing or lost 1-1.6k.
- Per game the best factor swings from 0.45 to 1.25. The loss from a too-strict limit is bounded (about 0.5-2.7k per game here); the loss from a too-lenient one was 9-13k in game 9. That asymmetry, not a measured average gain, is the argument for the lower factor. If the field stays calm, 0.7-0.9 is cheaper.
- "The factor change alone is better" is therefore **not established**: the cost-side replay holds the field fixed, the six latest games point the other way, and the charge side is not measured at all.
- Not yet run: the with/without price-references comparison (references change the medians that `k` multiplies). Until then the medians of games 10-15 and the earlier ones are not like-for-like.
- Decision knob stays `CLAIMS_B_MEDIAN_MULT`; the live machine's `.env` may override the default.

## Update 18:30: price references on vs off (games 10-15, forward only), and why the factor depends on them

`research/bench/refs_ab.py`: one cheap reader (`gpt-6-luna`, effort low), 3 draws per arm and game, games 10-15. Arm `refs` gets the reference block built only from games before the one read (like live); arm `noref` gets none. Each arm's geometric-mean medians and mean `q` are scored with the same cost-side replay. (A first run shared one `Case` object across threads and leaked the arms into each other; it was discarded and the script now copies the case per job.)

| arm | valid lines with informative bracket | median below L | inside | above U | median abs log error to bracket |
| --- | ---: | ---: | ---: | ---: | ---: |
| no references | 12 | 1 | 1 | 10 | 0.53 |
| references | 10 | 5 | 1 | 4 | 0.41 |

Reviewer cost over games 10-15 (EUR, `b = k x median`, midpoint of the evaluator range; we actually paid 24.1k):
| arm | 0.45 | 0.55 | 0.70 | 0.90 | 1.25 |
| --- | ---: | ---: | ---: | ---: | ---: |
| no references | 22.0k | 21.4k | **18.9k** | 23.3k | 25.9k |
| references | 23.2k | 23.2k | 23.3k | **22.0k** | 22.3k |

Reading:
- Without references the reader's medians are mostly **above** the public bracket (10 of 12), so a strict factor corrects for that and 0.7 is best. With references the medians move toward the bracket (error 0.53 to 0.41) and more of them fall **below** it, so the same strict factor over-rejects and the cost curve becomes flat (22.0-23.3k for every k from 0.45 to 1.25).
- So the factor and the median level are **coupled**: 0.55 was fitted on reader medians from games 1-9 without references; with references on (the current live default) it is probably too strict, and 0.7-0.9 is about as good or better in games 10-15. The spread between factors with references is about 1.3k over six games, which is inside this test's noise (one model, 3 draws, six games, 10-12 informative lines).
- What this does not show: that references improve the final payoff (charge side not measured), that the no-reference arm at 0.7 (18.9k) is a real optimum (picked in hindsight on six games), or anything about the full 8-member ensemble.
- Practical consequence: if references stay on, the lower-risk setting is a middle factor (about 0.7), not 0.55 or 0.9 on this evidence; the choice remains a risk call that the next forward games should confirm. `CLAIMS_B_MEDIAN_MULT` is the knob; nothing else changes.

## What this does and does not support

- Supports: a benchmark loop exists; the live bot's actual `b` replay (regret ≈ 1142 on games 1-2, 281 on game 3) can be compared with any candidate on the same lines; model price-level bias is large and varies by case; ensembles and web search are not a fix by themselves.
- Does not support: any claim that v2 or an ensemble is better. With 3 cases that would be overfitting. Re-run on every new completed game (`build_labels.py`, then `bench.py --cases case_00N`); a candidate only counts on games released **after** it was frozen.
- Next tests worth running: (1) the variance side, i.e. which signals shrink the per-line spread (description anchors, cached price table, more diverse models) and (2) the policy-reading step, since a misread clause (game 1) cost more than any bias.
