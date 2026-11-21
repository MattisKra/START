# Score A/B values

By default replay **every scored game** in the prepared archive:

```sh
python3 research/replay/history.py --ref origin/main
python3 research/replay/replay.py
python3 research/replay/replay.py --values submissions.json
```

Preparation reads our own public settlements and saves a gitignored suite in `runs/replay/history.json`. Repeat preparation after fetching newly archived results. The default replay uses recorded submissions and prints income, costs and net per case and totals (sum of rounded case results). Case 0 has no scored settlement.

For alternatives, supply a JSON object keyed by game ID, each value an ordinary submission array; every game must have an entry. An empty array explicitly plays defaults for that game. Use `--values -` to pipe this object from stdin. Baselines are checked against the archive to cent-level rounding at preparation. Alternative values are scored under one settlement-compatible scenario per case; hidden opponent limits, caps and fair thresholds are not known exactly.

## Single fixture

Select a scenario once, then supply the ordinary game submission array. Each invoice index has a gross charge (A) and acceptance limit (B). Omitted lines use zero for both.

```sh
python3 research/replay/replay.py research/replay/example_case.json research/replay/example_submission.json
```

Omit the submission path to read the array from stdin. The callable interface is `score(case, submission)`. Each scenario supplies the fair value, payment cap and opponents’ A/B values needed to compute the payoff. The example is synthetic.
