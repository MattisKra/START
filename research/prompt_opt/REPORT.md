# Prompt optimisation for the estimator (games 1-3)

All numbers come from `evaluate.py` (raw LLM outputs in `runs_llm/`, full table in `results.md` / `results.json`).
gpt-6-luna, effort medium, real `claimbot.pricing.price_case`. LLM calls used: 51 (no game API calls; leaderboard GETs only, 2.1 s apart).

## t-bounds from public transactions (`bounds.py`, `data/bounds_game_*.json`)

| game | line | item | t bounds (gross) |
|---|---|---|---|
| 1 | 1 | surge-damaged TV + speakers (indemnity halved) | [780.69, 900.00) |
| 1 | 2 | diagnostic report + call-out | [0, 5.58) → ≈0 |
| 2 | 1 | laptop screen repair | ≥ 808.45 (no inflated charge seen) |
| 2 | 2 | housing repair | ≥ 342.00 |
| 2 | 3 | polish of pre-existing scuff | nobody charged > 0 → presumably 0 |
| 2 | 4 | diagnostic inspection | [59.80, 83.60) |
| 3 | 1-3 | (glass items) | every positive charge rejected with nothing paid → ≈0 |
| 3 | 4 | | ≥ 328.51 |
| 3 | 5 | | ≥ 157.25 |
| 3 | 6 | | [0, 28.32) |

Game 3 was not used for prompt design; it was run once the final candidates were fixed, as a holdout.

## Metric

Main score: "net replay" = our money on each line against the other 11 teams' revealed charges and
revealed acceptance ranges (point guess = middle of each team's known b range), averaged over 5 values of t
spread log-uniformly over the bound interval (upper end 1.5·t_lo when unbounded; t=0 when no fair charge was seen).
Also: charge status (fair = a ≤ t_lo, INFL = a ≥ t_hi), whether b ∈ [t_lo, t_hi), log distance of the valid-median to the interval.
Reference `~ref_a=b=t_lo` (charge and accept exactly the highest known-fair charge) shows what is reachable.

## Candidates (`candidates/`)

- baseline: snapshot of `claimbot/estimator.py` INSTRUCTIONS at 032f803.
- v1: + policy-reading procedure (claim-specific section first, "not a repair cost" lists apply to bundled lines,
  attendance follows the work), literal valuation basis (new-for-old unless the policy says time value),
  p90/p10 ≈ 2 for well-defined items, sharper p_valid. Schema: price descriptions without the default depreciation.
- v2: v1 + schema `rationale` must cite the deciding clauses.
- v3: baseline with only the valuation paragraph changed.
- v4: v2 + "anchor on figures in the documents" + "p50 at the upper end of the normal price range" + "small labour items are modest".
- v5: v3 + v4's anchoring block.
- v6: v4 without the "upper end of range" sentence. **Chosen** (`best_prompt.py`).

## Results (mean net replay per game, ± stdev across runs; 3 runs each unless noted)

| cand | g1 | g2 | g3 (holdout) | g1+g2 | all 3 |
|---|---:|---:|---:|---:|---:|
| baseline | 4757 ± 3195 | 5863 ± 2645 | 4150 ± 937 | 10620 | 14770 |
| v1 (2 runs) | 5845 | 5376 | – | 11221 | – |
| v2 | 6989 ± 339 | 4338 ± 2338 | 4497 ± 245 | 11327 | 15824 |
| v3 (2 runs) | 4164 | 7418 | – | 11582 | – |
| v4 | 4008 ± 5386 | 11690 ± 1268 | 4297 ± 1022 | 15698 | 19995 |
| v5 (2 runs) | 2023 | 11473 | – | 13496 | – |
| **v6** | 8095 ± 1009 | 8923 ± 2378 | 3983 ± 1120 | 17018 | 21001 |
| ref a=b=t_lo | 10362 | 13753 | 6206 | 24114 | 30320 |

Observations:
- The anchoring rule (use purchase price / "the bill came to nearly X" figures) is what lifts game 2: medians for the
  screen line go from 714-833 to ~1000, so b stops rejecting fair 808 charges. "Upper end of range" (v4) overshoots game 1
  (median 1250-1309 vs t < 900 in 2/3 runs), so it was removed in v6.
- v6 has the lowest median log-distance to the bounds (0.02 vs 0.10 baseline) and the most fair charges (14/36 vs 10/36).
- Holdout game 3: baseline 4150, v2 4497, v4 4297, v6 3983. **No difference outside noise.** The systematic
  error there is underestimation (L4 median ~270-500 vs t ≥ 329, L5 ~155-240 vs t ≥ 157 → b < t, we wrongly reject),
  which no candidate fixed.
- Counterfactual (no LLM calls): multiplying b by 1.25 adds ~+600 (v6) / +1200 (baseline) over 3 games; 1.5 is no
  better. Small and noisy, but in line with `B_MULT` from 01-claimbot-review.

## Honest read

- The g1+g2 gain (10.6k → 17.0k) is in-sample: the anchoring and "diagnostics are modest" rules were written after
  seeing games 1-2, and run-to-run stdev is 1-5k per game. On the one unseen game it gives nothing.
- What I would trust: the valuation fix (the baseline's "old electronics are worth a small fraction of new" contradicts
  both observed t's, which look like new-equivalent prices), the anchoring rule (generic, and it cannot hurt when the
  description has no figures), and the policy-reading rules (the baseline already got validity right in games 1-3).
- Single samples swing 2-3×; averaging two calls (the runner already makes a low and a medium call) would likely
  help more than further prompt wording.
