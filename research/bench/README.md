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
**2. Prompt variants, out-of-sample (game 3; v2 frozen before it started).** The gain **did not replicate**: v1 vs v2 regret was luna 230 vs 245, gemini 260 vs 298, inkling-mini 152 vs 257, sonnet 298 vs 293, terra 37 vs 9. Most models under-priced game 3 by 40-55 % (bias −0.4 to −0.55); gpt-6.1-terra over-priced (+0.5) and had by far the lowest `b` regret. The dominant error is the **sign and size of each model's price-level bias, which changes from case to case** (game 1 too high, games 2-3 too low), not the wording of the prompt.
**3. Ensembles.** In-sample (games 1-2, v2): median of 7 models regret 262 vs 402 for the average single model; median of the 3 cheap models (luna, gemini-flash, haiku) 271 at $0.011 per case; an LLM final reviewer (gpt-6-luna) 241 for +$0.003 and about +10 s; belief pooling with a disagreement term was worse (444). Out-of-sample (game 3): **no aggregator beat the average single model** (single 241, mean 260, median 293, pooled 288, reviewer-luna 288); averaging does not cancel an error all models share. One exception worth a second look: the gpt-6.1-terra reviewer fixed the `a` side (bias +0.06, `a_score` 0.97) but not the `b` side.
**4. Tools: web search.** OpenRouter's web plugin (3 results) on luna / gemini-flash / terra over 3 cases: regret 357 → 368, 232 → 300, 136 → 185, higher cost (terra $0.003 → $0.03 per case), +1-5 s. No benefit seen; the expert values are not market prices.
**5. DSPy/GEPA.** The program, metric and feedback work end to end (seed prompt scores 0.66-0.80 mean over the cases). A first GEPA run on 3 cases with `--force` is a test of the machinery only (train = validation), see below.

## What this does and does not support

- Supports: a benchmark loop exists; the live bot's actual `b` replay (regret ≈ 1142 on games 1-2, 281 on game 3) can be compared with any candidate on the same lines; model price-level bias is large and varies by case; ensembles and web search are not a fix by themselves.
- Does not support: any claim that v2 or an ensemble is better. With 3 cases that would be overfitting. Re-run on every new completed game (`build_labels.py`, then `bench.py --cases case_00N`); a candidate only counts on games released **after** it was frozen.
- Next test worth running: a **bias correction learned from earlier brackets** (leave-one-game-out) applied on top of any model, since bias dominates the error.
