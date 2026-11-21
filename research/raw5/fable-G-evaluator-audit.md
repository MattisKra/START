# Audit G (Fable): is the euro replay evaluator sound, and what may it be used for?

Independent adversarial audit of `research/bench/euro_replay.py`, `euro_replay_check.py`, `euro_eval.py` and the README section "THE EVALUATOR WE CAN TRUST".
Written 2026-11-21, 16:02 to 16:35 CET. Everything below was run; the scripts are in `research/raw5/scripts/g_*.py` and contain no data.

**Two versions were tested, because the file changed while I was auditing it.**
- **as shipped** = commit `5cfdaf3` (16:00:50), the version behind the README table of "16:15".
- **now** = commit `1db2c88` (16:23:32), with "patch A" from the other audit applied. I did not read that audit (`gpt-G-evaluator-audit.md`); I only saw its summary in the README, which is in my scope. My findings on the shipped version were made before the patch appeared.

Field data: public settlement rows of games 1 to 10 (4,620 rows, 35 lines, 12 teams), read from a scratch folder outside the repo. Our own submissions: `outputs/model_outputs.json`, games 1 to 9 (game 10 is not logged). No other team is named and no per-team number is given below.

---

## 1. Verdict

**Is it sound?**

| Version | Answer | Evidence |
| --- | --- | --- |
| as shipped | **No.** Two deductions were not valid. | 240,000 adversarial line replays: the true value was below `lo` in **2.81 %** and above `hi` in 0.17 % (4.65 % below `lo` when our own log is not supplied). In 12-team fields: 0.49 %, worst miss EUR 29k. One failure on real data in 420 leave-one-team-out cost tests. |
| now (patch A) | **Yes, as a bound.** I found no remaining unsound deduction. | 0 misses in 480,000 line replays and in 1.2 million more by field size; 0 of 732 real leave-one-team-out tests; 9 of 9 games and 33 of 33 lines with all our rows withheld. |

Sound means only this: *the true net of a past game, with the other teams' submissions held as they were, lies inside the printed range.* It does not mean the range is narrow, and it does not mean the tool can choose between candidates.

**Trust level by use**

| Use | Trust | Why |
| --- | --- | --- |
| Reconcile our real net with the public rows | High | Organisers' matrix equals the row sums in 120 of 120 team-game cells; our 33 logged lines agree with our own rows; replay of our actual submission is exact in 7 of 9 games (9 of 9 with the small fix in section 9). |
| "This candidate would surely have done better / worse than what we played, on these past games" | High now, was unsafe as shipped | Sound bound against an exactly known number. Synthetic power about 47 %: it stays silent on half of the truly better candidates. |
| Choose the acceptance multiplier (the `b` side) | Medium | The cost side is measured: range width EUR 0.1k to 4.2k over 8 games. But the answer is carried by one or two games (section 7.4). |
| Choose the charge multiplier (the `a` side), or rank two candidates | **None** | The revenue side is not measured: range width EUR 32k to 104k. 0 of 342 candidate pairs can be separated. The lower bound jumps by EUR 9k to 16k when the multiplier moves by 0.05. |
| Forecast a future game, or state an expected gain | None | It replays the past. A second saved draw of the same reader moves the lower bounds by EUR 3k to 14k. |
| Tournament rank (the 70 points) | Not evaluated | The tool scores our net only. |

**Three things that change the team's reading of the README table**

1. **The `b` side is measured, the `a` side is not.** Split every candidate's range into revenue (set by `a`) and cost (set by `b`). On games 1 to 8 the cost ranges are 0.1k to 4.2k wide and separate 97 of 171 candidate pairs; the revenue ranges are 32k to 104k wide and separate none. The tool is an acceptance-limit evaluator. It says almost nothing about the charge.
2. **"luna KA 0.7 / KB 0.9 is surely better by 11k" is one game.** With the patched bound the figure is +15.4k, of which **+10.1k (66 %) is game 1**, where the live bot misread the policy. On games 5 to 8 (the ones that did not shape the prompt) the order of the three luna candidates reverses. With the other saved luna draw the order reverses too.
3. **"The engine defaults can lose 22k, this is why 1.25 hurt" is a misattribution.** Of the 22.7k, 16.8k is the revenue side of KA 0.9 being unidentified. On the cost side the defaults (KB 1.25) are *surely better* than what we played by 2.7k. KB 1.25 against KB 1.0 costs between 0.8k less and 5.5k more.

---

## 2. Findings, ranked

### CRITICAL: wrong answers (all three are fixed in the current file; the README table of "16:15" was computed with them)

**C1. The ceiling for charges nobody revealed was not a bound.**
A charge that every reviewer rejected for 0 has an unknown amount. If a candidate limit `b'` is above everything known to have rejected it, we may accept it. The shipped code capped that exposure at `4 * max(U or L, floor, 1)`. Nothing in the rules supports this. The only proven ceiling is `b'` itself (accepted means `a <= b'`, and we pay `min(a, c) <= a`).
- Minimal counterexample (section 6.2, case A): range [-4, 0], truth -900.
- Share of all lower-bound misses in the adversarial search: about 65 %.
- **Real data:** in the leave-one-team-out test one team really paid about 24 times the shipped ceiling on one line (ceiling EUR 32, excess about EUR 0.7k).
- In the README table the error went the other way: the heuristic was *larger* than `b'` (for luna defaults 12.7k against a proven 4.1k), mostly because on lines where everybody was rejected `U` is our own charge. So the published lower bounds were too pessimistic by up to 8.6k, not too optimistic. The README's claim that the ceiling "held on every synthetic case" was true only because its generator never produced a case that tests it.

**C2. The highest accepted amount of a line was taken as proof of an inflated charge.**
`c_lo = max(4L, accepted amounts)` is a *lower* bound of the cap. The largest accepted amount of every line equals `c_lo` by construction whenever it is at least `4L`. The shipped code read `x >= c_lo` as "clipped by the cap, hence inflated". If nobody rejected that charge it may be perfectly fair.
- Consequences: `U` is set too low (a fair candidate charge above it is scored 0 when rejected, so `hi` is too low); and rejecting that charge ourselves is scored as free when it costs 1.5 times the charge (so `lo` is too high). The pair is even counted as "identified".
- Minimal counterexamples: cases B, C, D in section 6.2 (B: range [0, 0], 4 of 4 pairs "identified", truth -142.50).
- All upper-bound misses and about 31 % of the lower-bound misses come from this.
- **Real data: latent.** It needs a positive charge that no reviewer rejected and that is the line's highest accepted amount. In 35 lines there were 3 never-rejected positive charges (all in games 8 and 9), none of them the highest. It will fire as soon as the strict reviewers on a line disappear.

**C3. A line missing from a candidate policy was skipped instead of trading at `a = b = 0`.**
The API handbook says omitted lines still trade [opened: `materials/API_HANDBOOK.md`]. Skipping scores a missing line as 0, while in reality `b = 0` pays 1.5 times every fair charge. The three readers used in `euro_eval.py` return every line for games 1 to 9 (0 missing), so the published table is unaffected. Among the other 20 saved readers, 2 return a wrong number of lines on at least one case. Patch A now settles missing lines at the defaults and raises on unknown indices; note that `euro_eval.py` does not catch that error, so one reader with an extra line now aborts the whole run.

### MAJOR: sound numbers, misleading conclusions

**M1. Ranking candidates by the lower bound is a maximin rule with cliffs, and the README shortlist is not robust.**
The lower bound of the revenue is `a'` per reviewer when `a' <= L` (proven fair) and 0 when `a'` is just above `L` and the reviewer's limit is unknown. So it is discontinuous in the multiplier (luna, games 1 to 8, one multiplier for open and pinned lines, EUR):

| KA | 0.60 | 0.65 | 0.70 | 0.75 | 0.80 | 0.85 | 0.90 | 0.95 | 1.00 | 1.05 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| revenue `lo` | 48.6k | 48.2k | 49.5k | 40.1k | 40.9k | 25.1k | 27.2k | 23.2k | 24.1k | 12.9k |
| revenue `hi` | 89.5k | 93.9k | 100.5k | 107.9k | 111.7k | 107.6k | 116.2k | 122.6k | 128.7k | 134.3k |

The lower bound says "charge less", the upper bound says "charge more". Both are consistent with the data. Whether a multiplier lands under `L` on one large line is luck of that reader draw, and `L` is not known before a game.
- Per game, delta of the lower bound against actual for luna KA 0.7 / KB 0.9: +10,089 / -2,557 / +1,716 / -98 / +744 / +533 / +1,042 / +3,883. Game 1 is 66 %, games 1 and 8 together 91 %. The task brief expected games 7 and 8 to dominate; it is game 1.
- Games 5 to 8 only: KA 0.8 / KB 1.0 **+7.4k**, KA 0.8 / KB 0.8 +7.0k, KA 0.7 / KB 0.9 +6.2k, KA 0.6 / KB 0.6 +2.1k. The README order is reversed.
- Two saved luna answers exist for games 1 to 6 (15:13 and 15:35; I could not tell whether the prompt changed in between). Same multipliers, delta of the lower bound against actual:

| luna | draw 1 | draw 2 (used in the README) | difference |
| --- | ---: | ---: | ---: |
| KA 0.9 / KB 1.25 | -0.6k | -14.9k | 14.3k |
| KA 0.8 / KB 1.0 | **+13.2k** | +0.7k | 12.6k |
| KA 0.8 / KB 0.8 | +9.4k | +0.9k | 8.4k |
| KA 0.7 / KB 0.9 | +7.3k | **+10.4k** | 3.1k |
| KA 0.6 / KB 0.6 | -4.0k | +2.4k | 6.5k |

The winner changes with the draw. The noise of one draw (3k to 14k) is larger than the median gap between neighbouring candidates (1.1k) and as large as the headline.

**M2. The ranges cannot separate two candidates.**
Games 1 to 8, 19 candidates, patched evaluator: 0 of 342 ordered candidate pairs have `lo(A) > hi(B)`. Median range width EUR 68k; spread of all lower bounds 29k; median gap between neighbours 1.1k (the range is 60 times the gap). The only comparisons with power are against our actual submission, because that number is known exactly: 10 of 19 candidates are surely above it. Synthetic check in section 6.3: 1 to 3 % of truly ordered pairs are separated.

**M3. The reading "defaults can lose up to 22k; this reproduces why the 1.25 multiplier hurt" is wrong in its attribution.**
Shipped: delta lower bound -22.7k. Patched: -14.1k. Split (patched, games 1 to 8): revenue lower bound 27.2k against an actual revenue of 44.0k = **-16.8k from the charge side**, identical for every luna candidate with KA 0.9; cost upper bound 34.4k against an actual cost of 37.1k = **+2.7k surely saved on the limit side**. Cost range of KB 1.25: [30.1k, 34.4k]; of KB 1.0: [28.8k, 30.9k]. So 1.25 is probably somewhat worse than 1.0, by at most 5.5k, and the tool cannot prove even the sign.

**M4. "Surely better than actual" is a low bar and is partly in-sample.**
Our actual play contains identified mistakes that any later reader run avoids (game 1: charge about three times above the fair bracket and a limit that paid EUR 3.1k for inflated charges; game 7: EUR 5.9k paid for inflated charges). Leave-one-game-out selection among the 14 multiplier candidates (pick the best lower bound on 7 games, read the held-out game): sum of held-out lower-bound deltas **+10.0k**, of which game 1 is +10.1k and the other seven games together **-0.07k**. Outside game 1 the tool does not prove that the shortlisted multipliers beat what we played.

**M5. The synthetic validation could not have found the defects, and still cannot.**
`euro_replay_check.py` is unchanged. Run on the *shipped* evaluator it still reports 12,000 of 12,000. Reasons: its generator has no charge far above every limit and no candidate limit far above the field; it checks game totals (88 pairs each) with a EUR 1 tolerance, so slack on one pair hides a miss on another; it rounds amounts to cents although the platform does not (section 4). With the author's own generator and candidates but checked per line I find 0 misses below `lo` in 48,000 and 1 above `hi`. The claim "100 %" was true and uninformative. It also prints "median |true net| scale" from the list of widths (a label bug).

**M6. "Replaying our actual submission reproduces our actual net" is close to a tautology.**
The reconstruction uses our own rows and our own log; for our actual `(a, b)` every outcome is read back. The real test is in section 5: with all our rows withheld, 9 of 9 games and 33 of 33 lines are inside the range, at a median width of EUR 4.7k (shipped) or 4.1k (patched) instead of 0.

**M7. Game 9 is not out of sample for the shortlist (README "16:35").**
Game 9 started at 15:46:40 CET and its rows were public before 15:57. The shortlist was committed at 16:00:50, and the same commit reports the replay of game 9. So the game-9 result (-8.9k, a field that over-charged) was known when "tighter" candidates were shortlisted, even though the saved reader answers for case 9 came later. Game 10 started 50 seconds before that commit and is clean in that sense, but our submission for game 10 is not logged, so only one side of the comparison is exact. One clean game is not a test.

**M8. One game carries the "strict limit" conclusion** (section 7.4): going from KB 1.0 to KB 0.5 saves 12.3k to 13.3k in game 9 alone, saves 3.3k in game 7, and *costs* 2.5k and 1.8k in games 5 and 6. Over games 1 to 8 the cost is flat between KB 0.5 and 1.0 (all within [28.4k, 30.9k]).

**M9. Net is not rank.** 70 % of the grade is linear in rank [opened: `materials/EVALUATION_CRITERIA.md`]. A euro we pay goes to another team, so it moves the gap to that team by two euros and the gaps to the other ten by one. The tool reports our net only.

### MINOR

- **m1. Our own rows are under-used.** Our own highest accepted amount is treated as "possibly clipped" although the log says whether it was; another team's possibly clipped charge that we accepted with our real limit is treated as "maybe accepted". This is why games 8 and 9 show widths of EUR 357 and 997 in the replay of our actual play. With the 12-line fix in section 9 the replay is exact in 9 of 9 games, and synthetic power rises (section 6.3).
- **m2. "Identified share" is not accuracy.** In case B the shipped code reported 4 of 4 pairs identified with the wrong value. It is also a count of pairs, not of euros.
- **m3. `fetch_field.py` can cache a partial game.** A failed request ends the loop for that team with `break`, the file is still written, and completed games on disk are never fetched again. `load_field` does not check completeness. The 10 games in the snapshot are complete (132 rows per line, no duplicates).
- **m4. `euro_eval.py` is not reproducible as documented.** Its game list is "every game with saved answers"; it changed from 1 to 8 to 1 to 9 during this audit when new answers were saved, so the README table can no longer be regenerated without pinning. It maps lines by `reader index + 1` instead of the printed positions that `engine.check` provides.
- **m5. The cap has never been observed.** No line has its highest accepted amount shared by two never-penalised issuers, and only 1 of the 15 lines with a proven fair charge has an accepted amount above `4L`. So `c >= 4t` is taken from the rules and is untested; in practice the cap logic changes almost nothing on real data.
- **m6. Cent grid.** `round(amount / 1.5, 2)` assumes charges are whole cents. True for all 72 penalty rows so far. A charge with sub-cent digits would shift `L` by at most half a cent.
- **m7. Opponents held fixed.** Inside one game this is exact, not an assumption: submissions are sealed and simultaneous, so no opponent could have reacted to a different submission of ours in that game. It becomes an assumption only across games.

---

## 3. Every inference, checked against the rules

Rules used [opened: `materials/GAME_DESCRIPTION.md`]: accepted iff `a <= b`, payment `min(a, c)`; rejected and `a <= t`: payment `1.5a`; rejected and `a > t`: 0; `c >= 4t` and never below a positive floor; one `a` and one `b` per team and line.

| Inference in `reconstruct` / `line_value` | Status | Note |
| --- | --- | --- |
| Rejected with amount > 0 implies fair, and `a = amount / 1.5` | PROVEN | Real data: 68 of 68 issuer-lines with both an accepted and a penalty amount have penalty = 1.5 times accepted to 1e-6. |
| Rejected with amount 0 implies `a > t` (inflated) | PROVEN | `a = 0` is never rejected (0 of 1,507 zero-charge rows). |
| All rows accepted with amount 0 implies `a = 0` | PROVEN | Needs a positive cap floor (stated in the rules). |
| `L` = highest fair charge, `t >= L` | PROVEN | |
| `U` = lowest inflated charge, `t < U`, from charges somebody rejected for 0 | PROVEN | Also valid when the accepted amount was clipped (`x = c >= 4t`, and `c > 0`). |
| `U` from "accepted amount equals `c_lo`" | **WRONG (shipped)**, removed now | C2. |
| `c_lo = max(4L, accepted amounts)`, `c >= c_lo` | PROVEN given the rule `c >= 4t` | The factor 4 itself is untestable on this data (m5). |
| Accepted amount below `c_lo` is the exact charge | PROVEN | `x = min(a, c) < c_lo <= c` forces `a = x`. |
| Accepted amount equal to `c_lo`: `a >= x`, not exact | PROVEN | Correctly conservative. |
| Reviewer limit `b_j >= ` every charge it accepted (`lo`) | PROVEN | For a possibly clipped charge `x <= a <= b_j`. |
| Reviewer limit `b_j < ` every exact charge it rejected (`hi`) | PROVEN | Rejections of non-exact charges are ignored, which is conservative. |
| Candidate `a' <= lo`: accepted; `a' >= hi`: rejected | PROVEN | Ties are right: `a' = lo` is accepted, `a' = hi` is rejected. |
| Accepted candidate is paid between `min(a', c_lo)` and `a'` | PROVEN | |
| Rejected candidate: `1.5a'` if `a' <= L`, 0 if `a' >= U`, else [0, `1.5a'`] | PROVEN | `a' = t` counts as fair; covered by `a' <= L <= t`. |
| Unknown acceptance: min and max over both outcomes, per pair | PROVEN, loose | Each pair picks its own `t`; the sum can describe a state no single `t` allows. Sound, not tight. |
| Hidden charge is above every limit that rejected it, including our logged `b` | PROVEN | Needs the log to be what was live; 33 of 33 logged lines agree with our rows. |
| Hidden charge and candidate `b'` above that floor: cost at most `4 * max(...)` | **HEURISTIC, false (shipped)** | C1. Now `b'`, which is PROVEN. |
| Possibly clipped charge, `b' >= x`: cost in [0, x] | PROVEN | Same issuer, same cap, so an accepted payment is exactly `x`; if rejected, `a > b' >= x` means clipped, hence inflated. |
| Possibly clipped charge, `b' < x`: cost 0 | **WRONG (shipped)** unless somebody rejected it for 0 | C2. Now [0, `1.5x`] in that case. |
| A policy without a line: line skipped | **WRONG (shipped)** | C3. Now `a = b = 0`. |
| Lower bound = "worst case consistent with the data" | **FALSE as wording** | Shipped: not even a bound. Now: a bound, but not attained in general (per-pair independence). |

Edge cases asked for: tie `a = b` accepted (handled, confirmed by 1,507 zero-charge rows against zero limits). `t = 0` with a positive floor (handled: every positive charge is inflated, accepted ones pay up to the floor). Accepted amount 0 (only `a = 0`). Charge equal to the cap (indistinguishable from clipping; treated as "possibly clipped"). Several issuers with the same charge (handled; tested). A reviewer who accepted a higher charge and rejected a lower one (impossible under the model; 0 of 420 reviewer-lines). Lines where only one team charged (handled). Our own rows (used for `L`, `U`, `c_lo` and the other teams' limits; skipped in the sums).

---

## 4. Model assumptions against the real rows (`g_invariants.py`)

10 games, 35 lines, 4,620 rows, 12 teams in every game.

| Invariant | Result |
| --- | --- |
| Every ordered pair present once per line; no self rows; no duplicates | 0 missing, 0 duplicates, 0 self rows |
| Organisers' per-game net of every team equals issuer rows minus reviewer rows | 120 of 120 cells, largest gap EUR 0.00 |
| Zero-sum | sum of all totals +0.00 (follows from the bilateral table) |
| One accepted amount per issuer and line across reviewers | 0 violations in 184 issuer-lines |
| One penalty amount per issuer and line | 0 violations in 72 |
| Penalty = 1.5 times the accepted amount | 68 of 68 exact to 1e-6 |
| A charge is fair for all reviewers or inflated for all (never 1.5a from one and 0 from another) | 0 violations |
| A zero charge is never rejected | 0 of 1,507 rows |
| `L < U` on every line | 0 violations |
| Reviewer limits consistent (highest accepted below lowest exact rejected) | 0 violations and 0 ties in 420 reviewer-lines |
| No negative amounts; `accepted` is boolean | 0 violations |
| Amounts are cent values | **No: 224 rows are not** (1.5 times an odd-cent charge has a half cent). Amounts are unrounded; all 184 accepted amounts and all 72 charges implied by a penalty are whole cents. |
| Shared cap: accepted amounts never exceed one value per line | Cannot fail by construction; the cap was never seen binding (m5) |

No assumption of the evaluator fails on the real rows. The only surprise is the last-but-one row: the platform does not round, the synthetic check does.

Field composition (aggregates): of 420 issuer-lines, 137 charge 0, 72 are proven fair, 113 proven inflated with a known amount, **95 were rejected for 0 by everybody (amount unknown)** and 3 were never rejected. 24 of 35 lines carry at least one such unknown charge. That is why C1 mattered.

---

## 5. Out-of-sample tests on real data (`g_loo.py`)

**(0) Is the log what was live?** 33 logged lines: our charge matches the rows wherever a row reveals it, and our limit lies inside the bracket implied by what we accepted and rejected. 0 inconsistencies.

**(1) Leave our rows out.** The field is rebuilt from the rows that involve us neither as issuer nor as reviewer, without our log. Then our logged `(a, b)` is replayed and compared with the real net from all rows.

| Game | actual net | shipped range | patched range | inside |
| ---: | ---: | --- | --- | --- |
| 1 | -1,575 | [-4,316, 1,165] | same | yes |
| 2 | 3,460 | [2,741, 4,799] | [2,977, 4,799] | yes |
| 3 | 2,195 | [1,952, 6,074] | same | yes |
| 4 | 2,613 | [1,430, 3,978] | [2,117, 3,978] | yes |
| 5 | 7,562 | [2,899, 7,562] | [6,075, 7,562] | yes |
| 6 | 5 | [5, 5] | same | yes |
| 7 | -4,137 | [-6,869, 54,794] | [-4,946, 54,794] | yes |
| 8 | -3,238 | [-4,671, 5,800] | [-3,947, 5,800] | yes |
| 9 | -8,872 | [-15,666, 1,677] | [-13,456, 1,677] | yes |

Coverage 9 of 9 games and 33 of 33 lines, both versions. Median width EUR 4,663 (shipped) and 4,122 (patched); game 7 alone is EUR 60k wide because one line has no fair charge at all and the range must allow that our charge there was fair.

**(2) Leave one team out, every team in turn.** Twelve times more tests. A team's policy is not logged, so I use what its rows prove: its charge where a row reveals it exactly, and as its limit the highest charge it accepted (every outcome of a reviewer is the same for any limit inside its bracket). The field is rebuilt without any row of that team.

| | tests | outside, shipped | outside, patched |
| --- | ---: | ---: | ---: |
| cost as reviewer | 420 | **1** (real cost above the ceiling: C1) | 0 |
| revenue as issuer | 312 (108 skipped: charge not revealed exactly) | 0 | 0 |

Mean cost width EUR 75 (shipped) and 40 (patched); mean revenue width EUR 589; 159 of 312 revenue ranges have width 0.

**What this proves:** the reconstruction of other teams' limits and charges predicts the settlements of a team it has never seen, for the policy that team really played, on real rows, 765 times without a miss after the patch. **What it does not prove:** anything about a candidate far from what teams really played (those outcomes were never observed, which is exactly where the ranges get wide), anything about how opponents would react, and nothing about tightness.

---

## 6. Adversarial synthetic tests (`g_adversarial.py`, `g_discrimination.py`)

### 6.1 Search for violations

Fields with known truth, rows generated exactly like the platform (unrounded), reconstruction from rows only, **checked per line** with a 2 cent tolerance. Ten field families, 2 to 12 teams, 8 candidates per line of which half sit on a critical value (another team's charge or limit, `t`, `t` plus or minus a cent, the cap, the cap plus or minus a cent, 0, very large).

| Family | shipped: truth < `lo` | shipped: truth > `hi` | now |
| --- | ---: | ---: | ---: |
| the author's kinds, but per line and small fields too | 387 | 58 | 0 |
| mixed | 559 | 67 | 0 |
| no silent team (everybody accepts something) | 920 | 15 | 0 |
| mostly accept-everything | 432 | 15 | 0 |
| mostly silent | 1,266 | 10 | 0 |
| few distinct values (ties everywhere) | 378 | 18 | 0 |
| excluded lines with free-option charges | 1,458 | 0 | 0 |
| charges at and above the cap, cap exactly 4t or at the floor | 512 | 63 | 0 |
| correlated errors of the whole field | 387 | 88 | 0 |
| several issuers with the identical charge | 434 | 64 | 0 |
| **all, 24,000 each** | **6,733 (2.81 %)** | **398 (0.17 %)** | **0 and 0** |

Without our own log the shipped version misses 11,150 (4.65 %). By field size (240,000 each, shipped): 12 teams 0.49 % below `lo` (worst EUR 29,363) and none above `hi`; 6 teams 2.11 %; 4 teams 2.94 %; 3 teams 3.50 %; 2 teams 4.97 % and 0.58 % above `hi`. Current file: 0 in all five sizes, 0 with amounts rounded to cents, 0 with a second seed. The fix in section 9 was run through the same search: 0.

### 6.2 Minimal counterexamples (shipped version; one line; team 0 is us; all synthetic)

| | Field `(a, b)` | We played | Candidate | Shipped range | Truth | Now |
| --- | --- | --- | --- | --- | ---: | --- |
| A (C1) | `t` = 100, cap 5,000. T1 (900, 0), T2 (0, 0) | (0, 0) | (0, 1000) | [-4, 0], 3 of 4 "identified" | **-900** | [-1000, 0] |
| B (C2) | `t` = 100, cap 400. T1 (95, 0), T2 (0, 1e9) | (0, 100) | (0, 90) | [0, 0], 4 of 4 "identified" | **-142.50** | [-142.50, 0] |
| C (C2) | as B plus T3 (0, 96) | (0, 100) | (98, 100) | [-95, 294] | **297** | [-95, 441] |
| D (C2) | 12 teams, `t` = 100, cap 400. Ten teams (0, 150), one team (90, 150) | (80, 120) | (85, 85) | [850, 977.5], 21 of 22 "identified" | **800** | [715, 977.5] |

In A the charge of 900 was rejected by everybody, so its amount is invisible; a limit of 1,000 accepts it. In B to D the charge of 95 (or 90) is fair, nobody rejected it, it is the line's highest accepted amount, and the shipped code called it inflated.

### 6.3 Can it rank policies?

Synthetic tournaments of 8 games, 12 teams (about 30 % silent, the others price with a reader that shares part of its error with ours, 35 % excluded lines, 15 % wrong validity calls). We "actually" played KA 0.9 / KB 1.25 on one reader draw; the 25 candidates are KA times KB on another draw. 300 tournaments. These numbers depend on the generator; read them as orders of magnitude.

| | shipped | now | now + fix of section 9 |
| --- | ---: | ---: | ---: |
| Truth outside the tournament range | 0 of 7,500 | 0 | 0 |
| Spearman of `lo` with the truth (median; 10 % quantile) | 0.73; 0.15 | 0.73; 0.11 | 0.73; 0.12 |
| Spearman of the midpoint with the truth | 0.76 | 0.77 | 0.78 |
| Best-`lo` candidate is the truly best of 25 | 31 % | 31 % | 32 % |
| Regret of the best-`lo` pick (median; mean; random pick 16.3k) | 2.5k; 5.1k | 2.4k; 5.0k | 2.4k; 5.1k |
| Truly better than actual and "surely better" (power) | 38 % | 47 % | 49 % |
| Truly worse than actual and "surely worse" | 12 % | 12 % | 21 % |
| False "surely" verdicts against actual | 0 | 0 | 0 |
| Truly ordered candidate pairs separated by the ranges | 1.1 % | 1.3 % | 2.7 % |
| `lo` orders a candidate pair correctly (coin = 50 %) | 77 % | 77 % | 77 % |
| Median range width / true spread between best and worst candidate | 1.9 | 1.8 | 1.3 |

Reading: the shipped version shows 0 misses here although it is unsound, which is the same masking by aggregation as in M5. The lower bound carries real but weak ordering information (it gets about 3 of 4 pairs right and its best pick is the true best one time in three). A field with half the teams silent lowers the Spearman to 0.65 with 12 % of tournaments negatively correlated. On the real games the picture is worse than in this generator: 0 of 342 pairs separated, width 60 times the median gap.

---

## 7. `euro_eval.py` and the README claims

### 7.1 The published table reproduces, and how it moves (games 1 to 8, our actual net +6,886)

| Candidate | shipped net range | shipped delta `lo` | patched delta `lo` | cost surely saved vs actual | revenue `lo` vs actual |
| --- | --- | ---: | ---: | ---: | ---: |
| luna, engine defaults | [-15.8k, 85.9k] | -22.7k | -14.1k | +2.7k | -16.8k |
| terra, engine defaults | [-2.4k, 38.3k] | -9.3k | -5.4k | +3.7k | -9.0k |
| fable, engine defaults | [-14.9k, 43.6k] | -21.7k | -13.6k | +1.8k | -15.4k |
| luna KA 0.8 / KB 1.0 | [5.0k, 86.2k] | -1.9k | +3.0k | +6.2k | -3.2k |
| luna KA 0.8 / KB 0.8 | [9.2k, 85.8k] | +2.3k | +3.9k | +7.1k | -3.2k |
| luna KA 0.7 / KB 0.9 | [18.2k, 71.4k] | +11.3k | +15.4k | +7.1k | +8.3k |
| luna KA 0.6 / KB 0.6 | [17.7k, 58.7k] | +10.8k | +10.8k | +6.6k | +4.2k |
| terra KA 0.8 / KB 0.8 | [8.1k, 86.5k] | +1.2k | +4.0k | +2.3k | +1.7k |

The shipped column equals the README to the euro. The last two columns are the split that the tool should print: every candidate saves cost against what we played (surely), and the sign of the total is decided by the revenue lower bound, which is the unidentified part.

### 7.2 Claim by claim

| README claim | Verdict |
| --- | --- |
| "returns our actual net exactly in 7 of 9 games, inside the range in 9 of 9" | True, reproduced, close to a tautology (M6). |
| "12,000 synthetic cases, truth inside in 100 %" | True, reproduced, uninformative (M5). |
| "heuristic ceiling ... held on every synthetic case" | The generator never tested it. It fails in the adversarial search and once on real rows (C1). |
| "the lower bound is ... the worst case consistent with the data" | False as shipped (not a bound). Now a bound, not an attained worst case. |
| "A candidate is only better if its whole delta range is above zero" | Correct as a statement about those past games against what we played. Not a statement about the future, and not about another candidate. |
| "with luna and lower multipliers the worst case is better than what we earned (+2k to +11k)" | Now +3.9k to +15.4k, of which game 1 is +2.1k to +10.1k. Not robust to the reader draw (M1). |
| "engine defaults can lose up to 22k ... why the 1.25 multiplier hurt" | Misattributed (M3). |
| "the free option does not change the worst case" | True by construction: the worst case of a charge on an excluded line is 0. It is not evidence for the free option. The "best case 86k vs 44k" is the upper bound, which assumes the excluded lines were valid. |
| Caveats listed (7 candidates, cases 1 to 4 shaped the prompt, one draw) | Honest and necessary; the draw caveat is now quantified (3k to 14k). |
| "16:35": games 9 and 10 "came afterwards, genuine out-of-sample" | True for game 10 only (M7). |

### 7.3 What the tool is good for: the limit side

Cost range by acceptance multiplier, luna answer, one KB for all lines, games 1 to 8 (actual cost 37.1k):

| KB | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 | 1.1 | 1.2 | 1.3 | 1.5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cost `lo` | 30.5k | 30.4k | 30.1k | 29.2k | 28.4k | 28.8k | 30.1k | 30.1k | 29.9k | 30.3k |
| cost `hi` | 30.6k | 30.5k | 30.5k | 30.0k | 30.0k | 30.9k | 33.9k | 34.3k | 34.3k | 35.4k |

Between 0.5 and 1.0 the cost is flat within 2.5k. Above 1.0 only the upper end rises. These ranges are narrow enough to compare, which is not true of anything on the charge side.

### 7.4 But it is one or two games

Cost per game, luna answer (ranges collapsed where exact):

| Game | actual cost | KB 0.5 | KB 0.8 | KB 1.0 | KB 1.25 |
| ---: | ---: | --- | --- | --- | --- |
| 1 | 4,464 | 1,739 | 1,349 | 2,249 | 2,249 |
| 2 | 7,470 | 7,923 | [6,969, 7,397] | [6,015, 7,324] | [5,780, 7,417] |
| 3 | 2,572 | 2,487 | [2,073, 2,357] | [1,909, 2,250] | [1,909, 2,322] |
| 4 | 2,084 | 1,596 | 1,553 | [1,873, 2,203] | [1,873, 2,286] |
| 5 | 5,414 | **7,943** | 5,997 | 5,414 | [5,414, 7,164] |
| 6 | 4,877 | **6,637** | 5,400 | 4,877 | 4,877 |
| 7 | 6,332 | 1,893 | 5,219 | 5,219 | 6,332 |
| 8 | 3,886 | [234, 335] | [609, 710] | [1,284, 1,386] | [1,678, 1,780] |
| 9 | 15,191 | **1,902** | 10,957 | [14,194, 15,191] | 15,191 |

Strict limits cost more in games 5 and 6 (penalties for rejecting fair charges) and far less in games 7 to 9 (the field over-charged). Game 9 alone is worth 12k to 13k between KB 0.5 and KB 1.0. Including game 9 turns "flat" into "lower is better". The measurement is good; the generalisation rests on which regime the next games are in.

---

## 8. Wording

**Safe to say in the write-up**

> For every completed game we replay the official payoff for a candidate `(a, b)` against the other teams' real submissions, as far as the public settlement rows reveal them. What the rows do not reveal (the fair value between the highest fair and the lowest inflated charge, a reviewer's limit between what it accepted and rejected, charges that everybody rejected) is carried as an interval, so each result is a range and not a number. We checked the tool three ways: it reproduces our own real net; with all our rows withheld the real net was inside the range in 9 of 9 games and 33 of 33 lines; with any other single team withheld, in 732 of 732 line tests. An independent adversarial search first broke an earlier version (2.8 % of line replays) and found no miss in 480,000 replays after two fixes. The tool measures the acceptance-limit side to within a few thousand euros over eight games; it does not measure the charging side (ranges of EUR 32k to 104k), so we used it to set the limit rule and to discard candidates, not to pick the charge multiplier. Opponents are held fixed, each reader answer is one draw (a second draw moved the bounds by EUR 3k to 14k), and the candidates were chosen after seeing these games.

**Must not be said or done**

- Not "worst case". Say "proven lower bound on those past games".
- Not "A is better than B" for two candidates. No pair is separated.
- Not "KA 0.7 is the best charge multiplier". Two thirds of that margin is game 1 and it flips with the reader draw.
- Not "validated on 12,000 synthetic cases, 100 %" without adding that this test did not detect two defects.
- Not "we lost up to 22k because of the 1.25 limit".
- Not "games 9 and 10 are out of sample". Game 10 is; game 9 was known.
- Not a forecast, an expected value or a confidence interval. The midpoint is not an estimate.
- Not "identified share = accuracy".
- Do not pick by a lower-bound difference smaller than the draw noise (EUR 3k to 14k).
- Do not use it to argue about rank.

---

## 9. Fixes and further checks

Patch A (C1, C2, C3) is already in the file and passes my search. What is still open, as exact diffs against the current files (`1db2c88`). I did not edit any file; each diff was applied to a scratch copy and tested: 0 misses in 480,000 adversarial line replays and 1.2 million by field size, 0 of 732 leave-one-team-out tests, replay of our actual play exact in 9 of 9 games.

**Fix 1: use our own rows (m1) and expose the two sides (the main recommendation).**

```diff
--- a/research/bench/euro_replay.py
+++ b/research/bench/euro_replay.py
@@ -59,6 +59,15 @@
                 A[i] = dict(a=0.0, status="zero", exact=True, x=None)
         if our_a and ln in our_a and A.get(us, {}).get("status") == "hidden":
             A[us] = dict(a=our_a[ln], status="inflated", exact=True, x=None)      # rejected for 0 by everybody: inflated, value from our log
+        elif our_a and ln in our_a and us in A and not A[us]["exact"]:           # our own top accepted amount: the log says whether it was clipped
+            if our_a[ln] > A[us]["x"] + 0.005:
+                A[us] = dict(a=our_a[ln], status="inflated", exact=True, x=A[us]["x"])   # charged more than received: clipped, so inflated
+            else:
+                A[us]["exact"] = True                                             # received what we charged: our charge is known exactly
+        if our_b and ln in our_b:                                                 # a possibly clipped charge that WE accepted lies in [x, our_b]
+            for i, rs in issuers.items():
+                if i != us and not A[i]["exact"] and A[i]["a"] is not None and any(r["reviewer"] == us and r["accepted"] for r in rs):
+                    A[i]["a_hi"] = our_b[ln]
         U = min([v["x"] if v["x"] is not None else v["a"] for v in A.values() if v["status"] == "inflated" and (v["x"] is not None or v["a"] is not None)], default=INF)
         B = {}
         for i, rs in issuers.items():
@@ -95,6 +104,12 @@
 
 def line_value(line, us, a_c, b_c):
     """Our net range on one line for candidate charge a_c and limit b_c: (lo, hi, n_pairs, n_identified)."""
+    rev_lo, rev_hi, cost_lo, cost_hi, n, ident = line_sides(line, us, a_c, b_c)
+    return rev_lo - cost_hi, rev_hi - cost_lo, n, ident
+
+
+def line_sides(line, us, a_c, b_c):
+    """The two sides separately: revenue as issuer (set by a_c) and cost as reviewer (set by b_c): (rev_lo, rev_hi, cost_lo, cost_hi, n, ident)."""
     L, U, c_lo = line["L"], line["U"], line["c_lo"]
     rev_lo = rev_hi = cost_lo = cost_hi = 0.0
     n = ident = 0
@@ -135,9 +150,11 @@
                 pr = _rej_pay(x, L, U, Ai["status"])
                 cost_hi += pr[1]                    # only the uncapped a == x branch can be fair
                 ident += int(pr[1] == 0)
+            elif b_c >= Ai.get("a_hi", INF):        # we accepted it with our real limit, so every limit at least as high accepts it too
+                cost_lo += x; cost_hi += x; ident += 1
             else:
                 cost_hi += x                        # accepted pays exactly x (same cap); rejected pays 0
-    return rev_lo - cost_hi, rev_hi - cost_lo, n, ident
+    return rev_lo, rev_hi, cost_lo, cost_hi, n, ident
 
 
 def game_value(lines, us, policy):
```

Then let `euro_eval.py` print, per candidate, the revenue range and the cost range next to the actual revenue and cost (the last two columns of the table in 7.1), take the games as an argument instead of "whatever is saved", and catch the `ValueError` of a reader with an unknown line.

**Fix 2: refuse incomplete fields (m3).**

```diff
--- a/research/bench/euro_replay.py
+++ b/research/bench/euro_replay.py
@@ -167,5 +184,9 @@
     assert repo not in d.parents and d != repo, "field cache must live outside the repo"
     games = {}
     for f in sorted(d.glob("tx_g*.json"), key=lambda p: int(p.stem[4:])):
-        games[int(f.stem[4:])] = json.loads(f.read_text())
+        rows = json.loads(f.read_text())
+        teams = {r["issuer"] for r in rows} | {r["reviewer"] for r in rows}; n_lines = len({r["line_item_index"] for r in rows})
+        keys = {(r["issuer"], r["reviewer"], r["line_item_index"]) for r in rows}
+        assert len(keys) == len(rows) == len(teams) * (len(teams) - 1) * n_lines, f"{f.name}: incomplete or duplicated rows, fetch the game again"
+        games[int(f.stem[4:])] = rows
     return games
--- a/research/raw4/scripts/fetch_field.py
+++ b/research/raw4/scripts/fetch_field.py
@@ -52,12 +52,14 @@
             while True:
                 d = get("transactions", game_id=gid, team=t, page=page)
                 if not d:
-                    break
+                    raise SystemExit(f"game {gid}: a request failed; nothing was written for this game, run again")
                 for r in d["items"]:
                     rows[(r["issuer"], r["reviewer"], r["line_item_index"])] = r
                 if page >= d.get("total_pages", 1):
                     break
                 page += 1
+        n_lines = len({k[2] for k in rows})
+        assert len(rows) == len(teams) * (len(teams) - 1) * n_lines, f"game {gid}: {len(rows)} rows, expected {len(teams) * (len(teams) - 1) * n_lines}"
         f.write_text(json.dumps(list(rows.values())))
         print(f"  game {gid}: {len(rows)} distinct rows")
     perf = {}
```

**Fix 3: the label bug in the check (M5), and make the check able to fail.**

```diff
--- a/research/bench/euro_replay_check.py
+++ b/research/bench/euro_replay_check.py
@@ -86,7 +86,7 @@
 def synthetic(n_games, seed=7):
     rng = random.Random(seed)
-    inside = tot = 0; widths = []; ident = []; viol = []; rounding = []
+    inside = tot = 0; widths = []; ident = []; viol = []; rounding = []; nets = []
@@ -98,7 +98,7 @@
             lo, hi, idn = er.game_value(lines, 0, cand)
-            tn = true_net(truth, cand, base)
+            tn = true_net(truth, cand, base); nets.append(abs(tn))
@@ -106,7 +106,7 @@
     print(f"synthetic: truth inside the range in {inside}/{tot} cases ({inside / tot:.1%}); median width {st.median(widths):.0f} EUR "
-          f"(median |true net| scale {st.median([abs(v) for v in widths]):.0f}); median identified share {st.median([x for x in ident if x == x]):.0%}")
+          f"(median |true net| {st.median(nets):.0f}); median identified share {st.median([x for x in ident if x == x]):.0%}")
```

The label fix does not make the test stronger. After any change to the replay run `g_adversarial.py` and `g_loo.py` instead (commands in section 10); they are the tests that fail on the shipped version.

**Further checks, most valuable first**

1. **A frozen shadow test.** Before each new game, write the `(a, b)` of two or three frozen candidates to a file with the game id (dry run, no submission). After settlement, replay them. This is the only test with no selection, no in-sample prompt and the real 60 second answer. One game takes 13 minutes; ten games give ten clean points. Log our live submission for every game too (game 10 is missing).
2. **Report the two sides separately** and decide the limit rule on the cost side only. For the charge side, print the whole KA sweep of the lower and the upper bound, not single points, so the cliffs are visible.
3. **Three reader draws per case**, and quote the *worst* lower bound over the draws.
4. **Leave-one-game-out** for every headline, and state the share of the largest game.
5. **`g_invariants.py` after every fetch**, `g_loo.py` after every new game. A violated invariant (two accepted amounts for one issuer and line, a reviewer accepting above a rejection) means the model of the rows is wrong and every range is void.
6. Optional: a paired replay of two candidates against the same unknowns. It would tighten comparisons on the limit side further. It cannot rescue the charge side, because there the unknown is `t` itself.

---

## 10. Reproduce, and sources

```sh
F=/path/outside/the/repo/field                     # written by research/raw4/scripts/fetch_field.py
SHIPPED=/path/outside/the/repo/a/b/euro_replay.py  # git show 5cfdaf3:research/bench/euro_replay.py > $SHIPPED
python3 -I research/raw5/scripts/g_invariants.py $F
python3 -I research/raw5/scripts/g_loo.py $F --us "Team Name" [--replay $SHIPPED]
python3 -I research/raw5/scripts/g_adversarial.py --n 3000 --seed 1 --minimal [--replay $SHIPPED]
python3 -I research/raw5/scripts/g_discrimination.py --n 300 --seed 3 [--replay $SHIPPED]
.venv/bin/python -I research/raw5/scripts/g_eval_audit.py $F --us "Team Name" --games 1-8 [--replay $SHIPPED]
```

Without `--replay` the scripts test `research/bench/euro_replay.py` as it is on disk. `g_replay_fixed.py` is my reference implementation (patch A plus Fix 1 plus an exact cap ceiling when our own charge was clipped); `g_common.py` holds the loaders. Runtimes: 1 to 40 seconds each.

Limits of this audit: one snapshot of 10 games; the adversarial truth function is my reading of the rules document, the same reading the evaluator uses, so a rule both of us misread would not show (the real-row invariants of section 4 are the guard against that); the discrimination figures depend on my generator; I did not check `euro_game_report.py` or `field_strategies.py`, which appeared during the audit.

Sources: `materials/GAME_DESCRIPTION.md`, `materials/API_HANDBOOK.md`, `materials/EVALUATION_CRITERIA.md`, `research/bench/README.md` and the code under audit [all opened]; the public leaderboard rows [opened, scratch copy]. No external literature is used for any claim. The terms "bound" and "maximin" are used in their plain sense.
