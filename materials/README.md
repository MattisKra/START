# Materials index (read the `.md` files, not the PDFs)

Source: QuantCo's `[PUBLIC] Road to Start HACK` Drive folder, unpacked 2026-11-21. Markdown versions are ~10x cheaper to read than the PDFs.

| Read this | What it is | Size |
| --- | --- | --- |
| [`GAME_DESCRIPTION.md`](GAME_DESCRIPTION.md) | **Authoritative rules**: payoffs, cap `c ≥ 4t`, example, fair play, how to win | ~2.5k tokens |
| [`EVALUATION_CRITERIA.md`](EVALUATION_CRITERIA.md) | 70 % rank-scaled score + 30 % jury (method, evidence, resourcefulness, reliability, honesty) | ~0.5k |
| [`API_HANDBOOK.md`](API_HANDBOOK.md) | Endpoints, key field `decryption_key`, error codes, omitted lines still trade | ~0.5k |
| [`../claim-to-fame-challenge-deep-dive.md`](../claim-to-fame-challenge-deep-dive.md) | Slide deck as markdown (older numbers; see differences table in `GAME_DESCRIPTION.md`) | ~2k |
| [`QUANTCO_PRESENTATION.md`](QUANTCO_PRESENTATION.md) | Company intro, prizes. No rule changes | ~0.5k |
| `starter_script.py`, `pixi.toml`, `pixi.lock` | QuantCo's starter flow (list → key → submit). Not run by us; `claimbot/` supersedes it | |
| `pdf/` | Original PDFs, only if a layout detail is in doubt | |

## Case files (not in git)

`cases/case_000.zip … case_100.zip` (101 AES-encrypted archives, ~371 MB) sit in the repo's **gitignored** `cases/` folder, which is what
`claimbot/config.py` (`CASES_DIR`) expects. They are not committed: they are encrypted until the round's key is released, each person
has the same Drive folder, and 371 MB would bloat every clone. Re-create them by unzipping the Drive download into `cases/`.

Each archive holds `description.txt`, `invoices.pdf`, `policy.txt` and one or more `photo*.png|jpg` (checked from the zip index only,
nothing was decrypted). Case 0 is the permanent test game; its key comes from `GET /api/games/0/key` with the team key.

## Facts these files settle (and what is still open)

Settled: cap `c ≥ 4t` (floor exists, value unknown); score is rank-scaled; jury rewards economical methods and honest evidence;
key response field is `decryption_key`; omitted lines still transact with `a = b = 0`; only one team member should submit;
later submissions overwrite earlier ones.

Still open: the absolute cap floor; whether the invoice index starts at 1 (handbook examples use 1, 2) and how the invoice labels
its lines; whether any per-round feedback (outcomes, `t`, other teams' `a`/`b`) is returned beyond the leaderboard; exact round cadence
(`TODO` in the rules text, slides say ~13 min); the write-up deadline ("shortly before the challenge ends").
