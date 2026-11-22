# claude_loop

Scripts and reference files Claude used to play games 18–100 of Claim to Fame from an interactive session. Copied from `~/Desktop/[PUBLIC] Road to Start HACK/work` on 2026-11-22.

## Files

- `lessons.txt` — pricing rules A–G and one entry per game with the mistakes made and the thresholds learned. Printed at every release.
- `ref.txt` — inferred threshold range for every invoice line of games 1–100, grouped by game and policy family (first 6 characters of the policy's md5). Rebuilt by `scripts/ref.py`.
- `bounds.txt` — early version of the threshold bounds (games 1–17), from `scripts/bounds.py`.
- `tx/` — public leaderboard transactions per game (`G.json`), downloaded by `scripts/tx.py`.

## Scripts

- `next.sh` — waits for the next game's start time, then runs `go.sh`.
- `go.sh GAME` — fetches the case key, decrypts the case, prints description, invoice, policy excerpts, past thresholds for the same policy family, and the lessons.
- `submit.sh GAME 'idx:charge:limit ...'` — submits or updates lines.
- `after.sh GAME` — downloads the round's transactions, rebuilds `ref.txt`, prints thresholds, team nets and per-line results (`tx.py`, `ref.py`, `acc.py`, `eval.py`).
- `sim.py`, `bounds.py` — early analysis helpers.

## Notes

- The API key is read from the `TEAM_API_KEY` environment variable; it is not stored here.
- The shell scripts still contain the absolute path of the original working folder (`R=...`) and expect `work/ex`, `work/tx`, `work/ref.txt` under it. Change `R` and the `work/` prefix before running them from this folder.
- Not copied: the decrypted cases (`ex/`, 450 MB) and the per-case decryption keys (`keys/`).
