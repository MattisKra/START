# Multi-agent claims estimator

Run from the repository root with the project's Python environment. Supply the API key for your selected reader in the existing environment or root `.env`. Reader specs and defaults are shared with `claimbot_fable`. All commands operate on a decrypted local case directory and produce local estimates.

```sh
uv run python -m claimbot_multiagent estimate past-cases/case_004 --history
uv run python -m claimbot_multiagent estimate past-cases/case_009 --history --web
uv run python -m claimbot_multiagent shadow past-cases/case_009 --reader openai:gpt-6.1-terra:medium --fallback openai:gpt-6-luna:low:noimage
uv run python -m claimbot_multiagent compare past-cases/case_007 past-cases/case_008 --history --tokens 12000
uv run python -m unittest claimbot_multiagent.test_system
```

## Readers and settlement

The default estimate uses two parallel model calls. The policy and incident reader returns separate coverage and causality findings with evidence. It identifies the covered valuation basis, attributable scope, payout fraction and shared caps. The valuation reader returns prices conditional on eligibility, their source or assumption, VAT, inclusions, operation count and printed units per operation, and any explicit case price anchors.

Both readers use the printed position, quantity and unit supplied by the coordinator. Valuation gives a market quote per printed unit and an explicit conversion for the full scope. For example, two doors at two hours each require four hours. If only one door is related, the causal share of one half gives two payable hours. For a necessary fixed visit covering two devices, the fee applies once. Partial attribution of a fixed fee requires evidence of the number of necessary fees. Coverage selects among valuation bases. A unique as-valid quote may price clearly excluded work under the configured exclusion strategy.

With a parallel fallback available, an unsupported conversion, missing line or ambiguous price switches just that position to the fallback reader. When the readers disagree about the membership, kind or amount of a shared cap or anchor, the fallback supplies its terms and every line of the affected group. Overlapping groups are resolved together. Python recomputes settlement from the assembled raw lines and terms. Each run records line sources and fallback reasons. A missing reader or malformed case-wide reference can still require whole-case fallback.

The adapter translates printed positions to Fable's internal zero-based indices for arithmetic, then restores the printed positions in the output. The existing engine applies fractions, shared caps, case anchors and configured charge and acceptance multipliers. Its existing excluded-line charge strategy also applies.

## Research

Use `--history` to retrieve up to three comparable earlier invoice lines by task wording and unit. Chronology comes from the directory name `case_NNN`. For other names the retrieved list is empty. The only historical inputs are invoice text and incident descriptions. They provide scope examples and occasional explicit anchors.

Use `--web` with `BRAVE_SEARCH_API_KEY` to allow one optional research round. The valuation reader first supplies a complete estimate and may request up to two generic price queries. Matching search snippets and URLs support one revision. Queries and responses are cached locally for 30 days. The provisional estimate remains available if search fails, returns no evidence or runs late. Web search uses current sources, so leave it disabled for a strictly historical replay.

## Comparison and timing

`compare` runs one combined reader, two readers and three separate policy, incident and valuation readers with the same model, evidence options, engine parameters and aggregate **output** token ceiling. Input tokens vary by architecture. When web is enabled, the pricing reader's allowance is split across its initial answer and optional revision. For a research ablation, repeat the same held-out directories with case-only inputs, history, then history plus web.

The comparison reports complete cases, elapsed time and provider-reported model cost when available. Existing local `runs/bench/labels.jsonl` enables the repo's charge-score and acceptance-regret metrics. Without labels, scored line count is zero. Each run writes responses, source evidence, provider usage, validation errors and the selected prices to `runs/multiagent/`.

`shadow` starts the existing fast full-case reader concurrently. At the deadline it uses the best complete candidate received, preferring validated specialist results. The default cutoff is 52 seconds measured from the start of local case loading. `--seconds` can supply the time remaining when starting later in a round. In-flight provider requests may still incur charges after local selection. This CLI does not submit to the game API.
