# What the public leaderboard shows (read 2026-11-21 14:04 CET, after game 1)

Source: the organisers' public leaderboard page `https://c2f.public.quantco.cloud/leaderboard/` and the JSON endpoints that page itself loads (no key needed):
`/leaderboard/api/{games, matrix, matchup, performance, transactions}`. Requests made so far: the page once, `games` once, `matrix` once. Snapshot saved in `data/leaderboard_matrix_after_game1.json`.
**Not yet done:** any `transactions`, `matchup` or `performance` call, and nothing about other teams' individual lines (see "Fair-play line" below).

## Facts (observed; other teams' data is NOT stored in this repo, see "Data handling")

- **12 teams.** (Resolves the open question "how many teams".)
- Game 1 (start 13:00Z = 14:00 CET) was `completed` a few minutes after the start; the other 99 were `scheduled`.
- **Zero-sum confirmed:** game-1 totals sum to 0.00.
- Game-1 spread: the leader was at about +11,100, the field's bottom at about −8,000, and **five teams share one identical negative total**. We were 6th of 12 (−1575.29).
- The transactions view lists per item: issuer, reviewer, accepted flag, amount. The UI takes `game_id`, `team` and optional `line_item`.

## Inference (not verified)

- **Five teams with the same negative total are most likely teams that submitted nothing** (defaults `a = b = 0`): they charge nothing and reject everything, so each pays 1.5 × every fair charge made by the 7 active teams.
- **Absentees fund active teams that charge near `t`:** a `b = 0` insurer turns every fair charge into a 1.5× payment. The strategy reports disagree on what this means for shading `a` (see `raw2/fable-C-strategy-measurement.md`).
- **A feedback channel exists.** A rejected charge pays 1.5× if fair (`t ≥ a`) and 0 if inflated (`t < a`). With silent teams present every charge of ours is rejected several times, so we get a clean "was `a ≤ t`?" bit per line per round, from **our own rows alone**.
- Rows from several teams bracket `t` tighter (`t_lo` = highest fair charge, `t_hi` = lowest inflated charge). Only the resulting bracket numbers are kept, without team names.

## Data handling (decided by the user, 2026-11-21)

Other teams' performance and transactions may be **looked at** on the public leaderboard to judge the field, but **no data about other teams is written into this repo**: no names, no per-team amounts, no cached rows, no standings snapshots.
`research/live/lb_analyze.py` and `research/bench/build_labels.py` read other teams' rows in memory only and keep, on disk, only our own rows and anonymous per-line `t` brackets, under the gitignored `runs/`.
(The repo's `CLAUDE.md` still says "never read other teams' data"; that line now disagrees with this decision and should be reconciled.)

## Game 1 decoded (our team only; browser HAR the user supplied + our decrypted case 1; 14:10 CET)

Assumption to confirm: **"Kiebler Software Solutions" is our team** (its rows reconcile exactly: income 2888.52 − costs 4463.81 = −1575.29).
Case 1 (electronics): line 1 "speaker system + TV set", 2 pcs; line 2 "diagnostic surge-failure report and technician call-out", 3 pcs.

| | what the rows show |
| --- | --- |
| Line 1, hidden `t` | **t ∈ [780.69, 900.00)** (bracket from fair and inflated charges seen in game 1). |
| Line 1, our `a` | 2592.74: accepted by 1 of 11, rejected as fraud by 10 → **3.3 × the lower bound**. |
| Line 1, our `b` | ≥ 2215.16: of our 5 accepted positive charges **two were inflated (2215.16 and 900.00 = 3115.16 paid for fraud)**; the platform counter says accepted-wrong 2. |
| Line 2, `t` | ≈ 0 (bracket [0, 5.58)): the call-out/diagnostic is an ancillary charge, not a repair cost. |
| Line 2, our `a` | 147.89 on an excluded line: accepted by 2 of 11 → +295.78; 9 rejected for 0. The free option paid, but only against two teams. |
| Line 2, our `b` | rejected 4 positive charges, all rightly. |

**Why line 1 was 2-3 × too high (policy arithmetic, not market price):** `policy.txt` is 41 KB. Clause 2.3.3 covers electronics only under the overvoltage peril, with an appliance sub-limit of EUR 5,000 per event and across all invoices, and says that where an appliance was connected **without an overvoltage protective device the indemnity is one half**. The description says "nothing on that circuit was on a surge-protected strip". So `t` ≈ 0.5 × (valuation of 2 pcs), consistent with the bracket.
Ancillary charges (call-out, travel, commissioning, administration…) are "not a repair cost" → `t = 0` for line 2.
The first estimator schema had no field for a payable fraction, sub-limit or deductible. The team has since added `payout_fraction` (commit `032f803`).

## Game 2 (our team + aggregate field facts; 14:16 CET)

Case 2 (laptop screen claim): line 1 laptop screen crack repair, line 2 lower-right corner / housing repair, line 3 polish of a **pre-existing** lid scuff, line 4 diagnostic inspection. `policy.txt` is **74.6 KB** (case 1: 41 KB), so a live call reads about 10-19k tokens of policy.

**Result:** our net **+3,460** (income 10,930, costs 7,470); cumulative **+1,885**, rank **7 of 12** (6th after game 1). Field: median team about +3,180, leader about +11,300; four teams still share one identical negative total (silent), down from five.
Platform counters (cumulative): accepted-right 44, **accepted-wrong 4**, correct rejections 12, **penalties 6** (rejected a fair charge), charges accepted 16/66.

| line | expert bracket for `t` (from rows read in memory, numbers only) | our `a` | our `b` | what happened |
| --- | --- | --- | --- | --- |
| 1 screen | t ≥ 808.45 (no inflated charge seen) | 535.22 (0.66 × t) | ~572-621 | fair; 6 accepted, 5 rejected and paid us 1.5×. We **wrongly rejected 4 fair charges** (≥ 621) |
| 2 housing | t ≥ 342.00 | 266.29 (0.78 × t) | ~264-321 | fair; same pattern; **wrongly rejected 2 fair charges** |
| 3 pre-existing scuff | t = 0 (description says pre-existing) | positive | rejects all | all 11 teams rejected our positive charge: free option earned 0 this time |
| 4 diagnostic | **t ∈ [59.80, 83.60)** (covered here, small) | 109.66 (1.31 × upper end) | ≥ 85.5 | our charge was inflated: 10 of 11 rejected it for 0. We **accepted two inflated charges (83.6 and 85.5 = 169.10)** |

**Hindsight, with opponents unchanged (a lower bound):** a fair charge's revenue is `a × (1 + 0.5 × share rejecting)`, which rises with `a`; so charging the bracket's lower bound would have earned about +3,690 on line 1 and +1,020 on line 2.
Wrongly rejecting 6 fair charges cost 1,689 over accepting; the two accepted inflated charges cost 169; a fair `a` on line 4 instead of 109.66 would have earned at least +550.
That sums to about **+7,100 on top of +3,460** (≈ +10,600 instead). Needs hindsight, not a forecast.

**Reading across both games:** game 1 overshot (line 1 × 3.3, policy halving missed), game 2 undershot (× 0.66-0.78) and overshot the small diagnostic. Errors have opposite signs, so this is estimation noise plus missed policy rules, not a constant bias; two games cannot fit a correction.
**The descriptions carry numeric anchors** the estimator should use (case 2 says the laptop cost about 1,400, repairs came to "nearly" that "most of it for the display", "the same model is still on sale").
**Silent teams subsidise everyone:** with four to five teams at `a = b = 0`, every fair charge of ours is paid 1.5× by them, so under-charging is expensive: shading by 25-35 % cost more than any other single decision.
