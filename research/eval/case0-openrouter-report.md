# Case 0 across 30 OpenRouter models (2026-11-21 ~14:00 CET)

Script: `or_compare.py`; models: `candidates.json`; raw results incl. parsed outputs: `results/case0_min_20261121-135936.json`.
Setup: claimbot's own prompt and schema, text + the case photo, **lowest reasoning each model allows** (`none` / `minimal` / `low`, or `enabled: false` when the catalogue lists no control),
`max_tokens` 6000, 8 calls in parallel, one call per model. Cost is OpenRouter's reported `usage.cost`. Total spend **$0.39**.

## What it shows

1. **Structured output is solved:** 30/30 models returned schema-valid JSON with 4 lines. All used 0-based indices (as our prompt demands). The invoice prints `POS. 1…4`, so submission must add 1; keep the parser tied to the printed number.
2. **Coverage is solved by everything, including the cheapest models.** All 30 give the excluded boiler line (line 4) `p_valid ≤ 0.03` and lines 1-3 `p_valid ≥ 0.88`. Don't pay for a strong model for the coverage/relatedness step on cases like this one.
3. **Price level is where models disagree, and they disagree far more than they say.**

   | line | crowd median gross (EUR) | range across models | log-sd across models | median stated σ (p10-p90) |
   | --- | ---: | --- | ---: | ---: |
   | 1 leak detection, 2 hrs | 214 | 86-309 | 0.27 | 0.22 |
   | 2 copper pipe 15 mm, 1 pcs | 161 | 54-357 | 0.38 | 0.35 |
   | 3 re-plaster/re-tile ~0.2 m² | 107 | 13-428 | **0.85** | 0.37 |
   | 4 boiler service (excluded) | 214 if it were valid | n/a, `t = 0` | n/a | n/a |

   Cross-model spread is at or above each model's own stated σ, and 2.3× it on line 3. That is the same direction as the published "LLM intervals are too narrow" finding (wave 1/2), but note: disagreement is not error, and we have no `t`.
4. **Latency at minimum reasoning:** most models answer in 5-15 s; slow ones are mandatory-reasoning models (`mistral-large-4` 81 s, `nex-n2.6` 47 s, `grok-4.7` 38 s, `qwen4-max` 29 s, `gemini-4-neon` 27 s, `gemini-4-carbon` 25 s). With a 54 s cut-off, these are unsafe as the only call.
5. **Cost per case:** cheap tier $0.0002-0.0010; mid $0.002-0.019; strong $0.034-0.073. Five diverse cheap models cost about $0.004 per round, about $0.4 over 100 rounds.
6. **Distance to the crowd median** (mean |log deviation| on lines 1-3; not accuracy): closest were `qwen4-max` 0.05, `claude-opus-5.5` 0.07, `claude-fable-5.2` 0.12, `inkling-2-mini` 0.13, `claude-sonnet-5.5` 0.14, `gpt-6-luna` 0.20. Furthest: `mistral-small` 0.86, `deepseek-v4.1-flash` 0.78, `gpt-6.1-terra` 0.77, `gpt-6.2-sol` 0.68 (those two priced line 3 about 3-4× the median). Being near the crowd is weak evidence of being right.

## Candidate fast-tier models for a ~10 s call (this case only)

`nvidia/nemotron-3.5-super-vl` 4.8 s, `thinkingmachines/inkling-2-small` 5.2 s, `mistral-small-2603` 6.6 s, `gemini-3.8-flash` 7.0 s, `meta/muse-ember` 7.5 s, `inkling-2-mini` 7.6 s, `gpt-6-luna` 8.8 s, `claude-haiku-5.5` 9.8 s.
Of these, `inkling-2-mini`, `muse-ember` and `gpt-6-luna` were closest to the crowd; `mistral-small`, `nemotron` and `haiku` were far off on line 3.

## Limits (read before using)

- **One case, one call per model, no truth.** The crowd median is a reference, not `t`. Re-run on more cases as keys are released and on repeated calls per model to separate model bias from sampling noise.
- Latency was measured with 8 parallel calls and provider load at that moment; treat as a rough ordering. Two providers returned 429/5xx once and were retried (see `note` fields).
- Minimum reasoning was chosen deliberately for speed; higher effort was not tested here.
- The prompt asks for the "maximum reasonable" price, which models read differently; part of the line-3 spread may be prompt ambiguity (unit `m²` for a 0.2 m² patch, minimum call-out charges), not model quality. A prompt rewrite should be tested against the same table.
- Photo value was not isolated: all calls included the photo. An image vs no-image A/B on a few models is the next cheap test.
