# claimbot_fable: reader + rule engine (built from the first-principles review)

Implements section E of `research/raw3/fable-E-first-principles-review.md`. A separate package next to `claimbot/`: it **reuses** claimbot's
decryption (`case.py`), API client (`api.py`) and watch helpers and **changes nothing in `claimbot/`**.

**Idea:** the model reads, Python computes. One strong reader returns per line the validity, justified quantity, unit price (on the policy's own
valuation basis, no depreciation), payable fraction, and per case the aggregate limits and description anchors. `engine.py` applies fractions,
shares limits rateably, scales to anchors, and sets `a`/`b` with two multipliers per line type. **3 calls per round instead of 18.**

## Run it (default is DRY-RUN; nothing is submitted without `--live`)

```sh
uv run python -m claimbot_fable selftest                                   # engine checks, no network
uv run python -m claimbot_fable estimate runs/bench/cases/case_004 --reader openai:gpt-6-luna:low:noimage   # read one decrypted case
uv run python -m claimbot_fable round 4 --case-dir runs/bench/cases/case_004   # full 3-tier round on a decrypted case, dry-run
uv run python -m claimbot_fable round 17 --zip cases/case_017.zip              # same with key + 7-Zip decrypt, still dry-run
uv run python -m claimbot_fable watch                                          # whole tournament, dry-run
uv run python -m claimbot_fable watch --live                                   # submits. STOP `claimbot watch` first: only ONE process may submit
uv run python -m claimbot_fable replay runs/fable/<log>.json                    # recompute a saved round with the current FABLE_* values
```

Keys in `.env` (same as claimbot): `TEAM_API_KEY`, `OPENAI_KEY`, `ANTHROPIC_API_KEY`. `OPENROUTER_API_KEY` is only a fallback / test path.
Readers (override with env): `FABLE_MAIN` (default `anthropic:claude-fable-5-2:low`), `FABLE_STANDBY` (`openai:gpt-6.1-terra:medium`),
`FABLE_FAST` (`openai:gpt-6-luna:low:noimage`). Spec = `provider:model:effort[:noimage]`, providers `openai`, `anthropic`, `openrouter`.
If a native key is missing the code falls back to the OpenRouter equivalent when `OPENROUTER_API_KEY` is set.
Multipliers (defaults from the review): `FABLE_KA_OPEN=0.90 FABLE_KB_OPEN=1.25 FABLE_KA_PINNED=0.85 FABLE_KB_PINNED=1.05 FABLE_B_ZERO_BELOW=0.667`,
`FABLE_EXCLUDED_A=as_valid|zero|0.5` (the excluded-line free option; switchable, to be disclosed in the write-up).

## Round timeline (`runner.py`)

T+0 key, decrypt, start fast / main / standby together. Fast answer -> submit (tier 1). Main answer -> engine -> submit (tier 3, overwrites).
Standby is held while main may still arrive; at T+45 it is submitted if main is missing (tier 2). Last submit T+52. Priority main > standby > fast,
never "whatever arrived last". Nothing by T+30: prints ALERT. T0 is the server's round start when called from `watch`.
Submitted `index` = the invoice's printed POS number (falls back to 1..n with a warning). Every round writes `runs/fable/<stamp>_game<N>.json`
(each tier's raw reader answer, token usage, engine output) so multipliers can be refitted without new calls.

## What was tested, what was not

Tested here: `selftest` (multipliers, halving, excluded line, rateable limit, anchor, justified quantity, POS parsing); the new schema through
OpenRouter for luna, terra and Fable; the native OpenAI path and the whole 3-tier timeline as a dry-run on a decrypted case (fast at 10 s, standby
held, main at 24 s took over, standby not submitted); offline scoring on 6 completed games (below).
**Not tested:** the native Anthropic path (no Anthropic key on the machine used; it mirrors `claimbot/anthropic_estimator.py`), `--live`
submission (uses `claimbot.api.GameAPI.submit` unchanged), and the zip + 7-Zip path (7-Zip is not installed on that machine). Run one `round ... --zip` dry-run first.

## Offline results (`research/bench/fable_eval.py`, 17 lines over games 1-6, same metric as `research/bench/README.md`)

| reader through the new schema + engine | b_regret EUR/line | b_score | a_score | bias (mean log) | latency | cost per case |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| live bot at the time (actual) | 536 | 0.56 | 0.55 | -0.14 (abs 0.50) | | |
| gpt-6-luna low, text only | 144 | 0.77 | 0.77 | +0.04 (abs 0.24) | 9-14 s | $0.003 |
| gpt-6.1-terra medium | 66 | 0.79 | 0.59 | +0.04 (abs 0.30) | 9-22 s | $0.02-0.03 |
| claude-fable-5.2 low (via OpenRouter) | 123 | 0.80 | 0.79 | +0.03 (abs 0.17) | 13-25 s | $0.19-0.30 |

Caveats: 17 lines, brackets not point labels, cases 1-4 were seen when the prompt was written (in-sample); games 5-6 have one line each.
**All three readers beat the old bot by a wide margin and are indistinguishable from each other at this sample size.** The gain comes from
the schema and the engine (halving, justified quantity, no depreciation, multipliers), not from the strongest model: luna through the new
path is within noise of Fable at roughly 1/80 of the cost. That matters for the jury's "no token maxing" criterion and for the cost.
The 1.25 x acceptance multiplier accepted one slightly inflated charge in game 1 for the two readers whose median was accurate: the usual price of KB > 1.
