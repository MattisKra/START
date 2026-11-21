# Review of `claimbot/` (Leo's commits `42e6821`, `f8e9060`) against the challenge model

Scope: read-only review of what is on `main` at 13:50 CET. Nothing in `claimbot/` was edited. Nothing was run against the real API
(no key; cases are encrypted). Severity = my estimate of expected money lost.

## What is already good

- Fast/full race with overwrite and a pre-deadline cutoff (`runner.play_round`) matches slide 7 ("last submission counts").
- LLM estimates *facts and uncertainty*; Python owns arithmetic, VAT, `a`/`b`. Right split, and the 1/3 rule is correct
  (`pricing._accept_limit`, `config.REJECT_P`).
- The prompt asks for `p_valid` separately from price, handling `t = 0` lines as a mixture.

## Issues, ranked

| # | Severity | Finding | Evidence | Suggested fix |
| --- | --- | --- | --- | --- |
| 1 | **High (unknown)** | **Index mapping can silently misalign every line.** LLM returns a 0-based invoice-order index; `api.build_payload` adds `INDEX_BASE=1`. The slide says lines are "matched by its index **on the invoice**". If the invoice prints its own numbering (e.g. positions 10, 20, 30, or 1…n with a header row), we score the wrong lines. | `schema.py`, `api.py:build_payload`, slide 6 | Parse the printed index from the invoice text; assert the set of submitted indices equals the set on the invoice; test against Game 0 first. |
| 2 | **High** | **No tier 0.** The fastest path is still an LLM call at `low` effort. A cold start, rate limit or 429 yields **no submission → `b = 0` → every fair charge costs 1.5×**. `play_round` also needs `--zip` by hand, so there is no loop that polls `/api/games/list` every ~13 min. | `runner.py`, `__main__.py` | A scheduler loop (poll list → fetch key → decrypt → race) and a non-LLM fallback submit within a few seconds. Pre-download zips if Drive has them up front. |
| 3 | **Medium** | **`b` is probably too low.** `b` = 1/3-quantile of *our own* belief about `t`. But other teams shade their charges below their own estimates (model fixed point `ka ≈ 0.1–0.3`), so a charge of `x` is less likely to be inflated than `P(t < x)` says. In the population model the rule's `b` earns ≈ 0 while the best `b` (`≈ t̂·e^{+0.10}`) earns +1…+5 % of line value per line. | `sim/review_pricing_rule.py` | Add a `B_MULT` knob next to `CHARGE_MULT` (currently only `a` has one), start at 1.0, A/B on live rounds once feedback exists. **Hypothesis, not verified on real opponents.** |
| 4 | **Medium** | **Stated σ is the LLM's p10/p90 spread and `MIN_SIGMA = 0.08` is low.** Verbalised quantiles from LLMs tend to be too narrow (to be confirmed in the literature notes). Both `a` and `b` are driven by σ. In the model, σ claimed 0.10 vs true 0.30 moves the best `b` from `+0.0` to `−0.10`. | `config.py`, `pricing._belief`; `sim/review_pricing_rule.py` rows 4–6 | Treat σ as calibrated, not read off: multiply by a factor learned from outcomes, or ensemble 3–5 samples/models and use their spread. |
| 5 | **Medium** | **`a` ignores the opponent side.** `_best_charge` maximises `x·P(T ≥ x)`, i.e. assumes rejected-fair pays `x` and inflated pays 0. Real payoff for fair charges is `x(1+0.5·r)`, and inflated charges still pay `min(x,c)` when accepted. Close to optimal in the symmetric-noise model, but blind to lax opponents (where `a > t` is profitable) and to strict ones (where shading costs money). | `pricing._best_charge`; `payoff_check.py` §3 | Keep as default; add an opponent-aware layer once the distribution of other teams' `b` is observable. |
| 6 | **Low–Med** | **Excluded lines are priced as if valid.** Schema says "never 0 just because excluded", so `a` for an excluded line ≈ the valid price. That is accidentally right (a rejected inflated charge costs nothing, accepted pays you) but it is un-flagged behaviour: nothing in the code says it is deliberate. | `schema.py`, `pricing.price_line` | Document it as a deliberate free option, and cap `a` at `c` once `c` is known. |
| 7 | **Low** | **Ordering race on overwrite.** `for fut in done:` iterates a `set`; if fast and full finish inside the same `wait`, the fast result can be submitted *after* the full one and overwrite it. | `runner.py:play_round` | Sort `done` so the full effort is processed last, or skip fast if full is already done. |
| 8 | **Low** | **No calibration loop.** Runs are logged to `runs/*.json`, but nothing tunes σ/multipliers between rounds. The API has no results endpoint (`materials/API_HANDBOOK.md`), so this must run on self-consistency and the 100 cases, not on settlements. | `runner.save_run` | Offline evaluation script over decrypted cases; log it for the write-up (graded: "evidence for your choices"). |
| 9 | **Low** | **Cost is invisible.** The jury rubric penalises "token maxing". Token usage is saved per run (`meta.usage`) but not summarised. | `estimator.estimate` | Report tokens/EUR per round in the write-up; justify the second (full) call by measured gain. |

## Assumptions in this review

- `t` is a deterministic per-line fair value; teams' estimation errors are independent lognormal; cap `c = 3t`; all other teams use one rule.
  None of these are known. The model supports *directions* (b may be too strict, a is near-optimal), not magnitudes.
- I did not test the LLM estimator quality at all. That needs the real cases.

## Smallest next steps (in order)

1. Run Game 0 end to end with `--dry-run` off; confirm index base, response shapes of `/list` and `/key`, and what (if anything) comes back after `PUT`.
2. Fix #1 and #2 before round 1 matters; #7 is a two-line fix.
3. Add `B_MULT`; keep `B_MULT = 1.0` until there is data.
