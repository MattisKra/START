# Claim Explorer

Offline page to browse the settlement data and our model's decisions: overview of our net per game, per-game line tables, a
per-line chart (t bracket, every team's charge, our `a`, `b`, median and each ensemble member's median), the issuer x reviewer
outcome matrix, and the team standing / per-game net heatmap. A switch hides team names.

```sh
# 1. fetch the public rows into a scratch dir OUTSIDE the repo (other teams' data must not be written here)
#    research/raw4/scripts/fetch_field.py  (see its header)
# 2. build the page, also outside the repo
uv run python research/explorer/build_explorer.py FIELD_DIR --us "Team Name" --out ~/claim_explorer/explorer.html
open ~/claim_explorer/explorer.html
```

The generator refuses a field dir or output inside the repo. Our decisions come from `outputs/model_outputs.json` (games the live
bot played); games without a log still show the public rows. Bracket for `t` and reconstructed limits come from
`research/bench/euro_replay.py` (interval-valued, see its header for what is and is not identified).
