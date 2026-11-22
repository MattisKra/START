# Round dashboard (two live charts)

Separate from `research/live/lb_chart.py`: own server, own page, own port.

```sh
python3 -I research/dash/dash.py --open      # http://127.0.0.1:8378
```

| Chart | What it shows | Source |
| --- | --- | --- |
| Net result per round against context size | One point per round: our net result as a share of all dollars moved in that round (y), against the context size of the playing session at the start of that round (x). Dashed trend line and Pearson r for the segment marked `"trend": true`. | y: live from the leaderboard API. x: `context_sizes.json` |
| Dollars moved between teams per round | Sum of all transaction amounts of all teams per round, split into accepted charges and 1.5× penalties. | live from the leaderboard API |

## Where the numbers come from

- `matrix` gives our net result per completed round, `games` the schedule. Both are refreshed every 20 s (`--ttl`).
- The round's total volume needs every transaction row of the round. The API only returns rows per team, so the server
  reads the rows of all teams but one (each row has an issuer and a reviewer, so that covers every row). That is 11 requests
  per round, done once per completed round and then kept in `runs/live/dash_volume.json` (gitignored).
  The first start therefore needs about 20 minutes for 100 rounds; the page fills in while it reads. Later starts are instant.
- Requests go out one at a time, at least 1.1 s apart (`--pace`), and only for completed rounds.
- Only per-round totals are stored: no team names and no per-team amounts.

## Context sizes are not in the API

`context_sizes.json` holds `tokens` (round → context size in tokens), the `segments` (legend groups, colour, marker shape,
which one gets the trend line) and a `note` that the page prints under the chart. The file is read on every page refresh,
so edits show up without a restart. A round without an entry is not plotted and is listed under the chart.
