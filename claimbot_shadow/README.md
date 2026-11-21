# Shadow the next three games

From the checkout with the encrypted case ZIPs, run:

```sh
.venv/bin/python -u -m claimbot_shadow
```

The watcher freezes the next three scheduled game IDs before release and exits after them. Run one instance per experiment. It needs a working team key for the release endpoint, the normal ensemble provider credentials, a ZIP extractor, and a signed-in Claude Code CLI with access to `claude-fable-5-2`. Both arms make real model calls. Only the existing tournament submission server handles live decisions.

Both arms receive the same released case, with past-game references disabled. Direct Fable can read the local source files and write decisions. It has no web tool. The ensemble uses its configured readers, the standard weighted combination and local selective web routing. The member list depends on provider credentials. The experiment compares these two configurations together. It cannot isolate the benefit of full context alone.

The printed run directory contains a frozen manifest and one folder per game:

- `input.json` records the archive SHA-256, release time, preparation time and invoice positions.
- `python.jsonl` records reader arrivals, weights, estimates, stated evidence, aggregate decisions, exact before/after amounts, and failures.
- `fable.jsonl` records tool requests and results, model-reported usage, and complete decision writes with line-level evidence.
- `result.json` compares the last complete decision from each arm within 60 seconds of official release. A missing receipt is null. `error.json` records a round-level failure.

Times are local observations relative to release. Tool results identify what Fable opened. Its evidence strings report what it says drove each decision. The ensemble log identifies the reader arrival that changed the arithmetic. Neither arm provides access to private model reasoning.

For a specific line, follow its position through successive decision events. The first event establishes the baseline. Later events show each change to the charge and limit in gross euros. Compare the final amounts across arms in `fable_minus_python`. A price difference alone does not establish a payoff.
