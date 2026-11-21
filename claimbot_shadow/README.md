# Shadow the next three games

From the checkout with the encrypted case ZIPs, run:

```sh
.venv/bin/python -u -m claimbot_shadow
```

The watcher freezes the next three scheduled game IDs before release and exits after them. Run one instance per experiment. It needs a working team key for the release endpoint, the normal ensemble provider credentials, a ZIP extractor, and a signed-in Claude Code CLI with access to `claude-fable-5-2`. Both arms make real model calls. Only the existing tournament submission server handles live decisions.

Both arms receive the same released case, with past-game references disabled. Direct Fable can read the local source files and write decisions. The original games 24–26 arm has case files only. New runs can search public market sources and fetch supplier pages after their first complete decision. The ensemble uses its configured readers, the standard weighted combination and local selective web routing. The member list depends on provider credentials. The experiment compares these two configurations together. It cannot isolate the benefit of full context alone.

The printed run directory contains a frozen manifest and one folder per game:

- `input.json` records the archive SHA-256, release time, preparation time and invoice positions.
- `python.jsonl` records reader arrivals, weights, estimates, stated evidence, aggregate decisions, exact before/after amounts, and failures.
- `fable.jsonl` records tool requests and results, model-reported usage, and complete decision writes with line-level evidence.
- `result.json` compares the last complete decision from each arm within 60 seconds of official release. A missing receipt is null. `error.json` records a round-level failure.

Times are local observations relative to release. Tool results identify what Fable opened. Its evidence strings report what it says drove each decision. The ensemble log identifies the reader arrival that changed the arithmetic. Neither arm provides access to private model reasoning.

For a specific line, follow its position through successive decision events. The first event establishes the baseline. Later events show each change to the charge and limit in gross euros. Compare the final amounts across arms in `fable_minus_python`. A price difference alone does not establish a payoff.

Once a game settles, run the paired payoff replay from the project root with the game folder printed by the watcher:

```sh
.venv/bin/python research/bench/score_shadow.py runs/shadow/<run>/<game>
```

`score.json` stores per-line bounds and totals for Fable minus Python under the opponents' observed decisions. Positive reviewer savings mean Fable paid less. Within each arm, `successive_revision_eur` compares each complete on-time revision to the preceding decision, holding opponents fixed. Hidden charges and limits can leave either winner possible. Missing on-time decisions are marked unscored. The replay reads public settlements and reconciles each team's total against the standings.

To score all three as settlements arrive, start the scorer once with `--follow runs/shadow/<run>`. It waits up to 15 minutes after each release. A single game can be rescored later if the public standings arrive late.

The watcher saves `decision_reasons.json` locally at the end of a round. The scorer builds it for older runs from their saved traces. Look up a printed position for each revision's two amounts, the amounts it replaced, and the model's stated reason. A null reason means the reader supplied none. For Fable, the write ID links to successful file reads or searches since its preceding decision. This records access. Only the reader's explanation attributes a decision to a source. For Python, the index preserves each arriving reader's quantity, price range, coverage judgment and rationale alongside the resulting combined median and limit, including arrivals that left the amounts unchanged. The raw trace holds the pricing factors and web lookup metadata. New Fable runs request a brief numerical basis for each changed amount. Games 24–26 use the original frozen prompt.


## Replay Fable with the Python pricing rule

New Fable receipts contain an independent gross median conditional on eligibility and a probability that the line is payable. The scorer applies the Python factors and rejection gate recorded for that game. Its `explicit_beliefs` results compare this hybrid with Fable's own actions, then compare it with Python under the same rule.

Older receipts contain actions alone. The scorer keeps the original issuer charge fixed and changes positive reviewer limits to charge × limit factor / charge factor. A separate sensitivity analysis treats the charge itself as the median. Neither proxy recovers an unrecorded estimate. All payoff bounds assume the historical opponents hold their actions fixed.

Fable can read `decision_check.json` after each write for duplicate or missing positions, invalid amounts, missing estimates and evidence. Queries, fetch requests, and check results appear in its local trace. For an already running frozen comparison, start `.venv/bin/python -m claimbot_shadow.companion runs/shadow/<run>` once to add the tool-enabled Fable arm to still-future games. It uses a separate output directory and the existing Python decisions. The scorer verifies matching input digests before comparing the arms.

For each printed position, `explicit_beliefs.lines` records both strategies’ charge and limit, reviewer savings, issuer income change, net change and separate winners for all three measures. Positive differences favour Python’s factors applied to Fable’s estimates. A winner requires the whole interval to be strictly above or below zero. Older decisions get separate line breakdowns under the two price-proxy assumptions.
