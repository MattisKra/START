# Best overall approach for the remaining ~20 h (Fable F, independent second pass)

Written 2026-11-21, 15:27-16:10 CET, on games 1-9 (91 games left). Independent of `research/raw3/` (read last, challenged in 4.3)
and of the other reviewer's files in `research/raw4/` (not read).

**Evidence labels.** [opened] = a file I read or a script I ran here. [team] = a number the team reported, not re-derived.
[memory] = recalled from the literature, not opened; no links are given for these.

**Data handling.** Other teams' rows were read from the organisers' public leaderboard JSON (same endpoints as the page, 1 request
per second, about 170 requests) into a scratch folder under `/private/tmp`, outside the repo. This file contains counts, shares,
distributions and anonymous archetypes only; bracket values are rounded, as in `past-cases/README.md`. Scripts in
`research/raw4/scripts/` contain no data. I did not read `.env`, call the game API, call any model, submit, commit or push.

**How weak the evidence is.** 9 games, 33 invoice lines, 19 of them priced by us as valid, 7 with a two-sided bracket. Every
multiplier below is a starting value. I formed two hypotheses on games 1-8 and tested both blind on game 9: one was confirmed,
one failed in the form I had written it. Both outcomes are reported (2.3, 2.4). The rule I now recommend was redrawn after
game 9 and is therefore untested.

---

## Executive summary (one page)

1. **The acceptance limit is the emergency.** In games 7, 8 and 9 the field as a whole overpriced, all 12 teams were active, and
   we accepted nearly everything: 5.9k, 3.7k and 14.0k paid for inflated charges, last place in games 8 and 9, from 4th to
   **7th** (total −2.0k). Replay of `b = k × our median` over games 1-9: reject everything 31.9k, `k = 0.5` 33.8k, `k = 1.0` 46.3k,
   `k = 1.25` (live) 50.2k, a perfect reviewer 21.3k [opened: `multiplier_replay_all_games.py`].
2. **Why strict is the right default, not just the lucky one.** A wrong acceptance costs the full charge and can happen 11 times
   per line; a wrong rejection costs half a charge. With the price-level error we actually have (a factor of 2 either way), a
   limit near half the median is the minimax choice, and the simulation in 1.3 gave `b* = 0.65-0.75 m` before game 9 existed.
   Games 1-6 favoured a lenient limit only because their case mix was repairs that models under-price.
3. **Our price error is two opposite errors.** Lines that name a repair of the damaged item (or its labour) were priced at or
   below `t`: 11 % of all teams' charges on those 8 lines were inflated. On every other priced line (services, cost heads,
   replacement goods, mixed lump sums; 11 lines) 84 % were inflated and `t` was 0.13 to 0.8 of our median. **Blunt caveat:** my
   first version of this split ("work on the object" against "service") failed on game 9, where two replacement-goods lines
   were overpriced like services. The current version was drawn afterwards and rests on three repair families.
4. **The previous review's central claim is refuted.** "Medians are low with probability 0.94-0.99, hence `b = 1.25 × median`"
   cost about 21k against a limit of half the median in the three games that followed it. `claimbot_fable` carries the same rule.
5. **Cases repeat: confirmed out of sample.** Games 2 and 6 share a byte-identical `policy.txt`; so do games 1 and 9. Invoice
   numbers of siblings are adjacent (…0211/…0212; …0188-0189/…0190). Game 5 is the laptop claim of games 2 and 6 again, in
   another edition. But my own blind use of the precedent in game 9 was wrong by a factor of two (I undid a halving that the brackets do not show).
   So precedents are valuable and dangerous: use them to **cap** prices, raise prices only for the same item under the same reductions.
6. **Where we lose, through game 9:** issuer side 42.6k (17.1k because our charge was inflated, 25.5k because it was below the
   highest fair charge), reviewer side 30.8k (27.8k paid for inflated charges, 3.0k in penalties). We pay 3.1k per game for
   inflated charges; the other always-active teams pay about 1.1k.

**Recommendation.** Keep "the model reads, Python computes". Change the rules Python applies:
(a) **a strict limit by default**: `b = 0.45 m` on every priced line (and `a = 0.80 m` until (b) exists);
(b) **two line classes**: repair-work lines `a = 0.90 m`, `b = 1.25 m`; every other priced line `a = 0.55 m`, `b = 0.45 m`;
(c) **precedents by policy hash**, applied as a cap on `a` and `b`, and as a floor only for the same item under the same reductions;
(d) **a closed loop per line class after every game** (our own fair/inflated bit moves `KA`; brackets move the level factor);
(e) **two cheap text-only readers on two providers**, a strong reader only when they disagree on a discrete fact; no photos;
(f) fat-finger guards, a no-model tier-0 submit that rejects, and a shadow table that scores every candidate rule each game.
Do (a) now: it is three environment values or two lines of code (5.5). Replay over games 1-9, opponents fixed, lower bound to upper bound:
live rule −1.9k to +8.2k; (a) +15.2k to +19.8k; (a)+(b) +32.7k to +44.2k. The last figure is post hoc.
On the limit alone, (a) would have cost about 4.6k in games 1-6 and gained about 21k in games 7-9; which mix comes next is unknown.

---

## 1. First-principles model

### 1.1 Payoff of one line, one ordered pair [opened: `GAME_DESCRIPTION.md`]

| | `a ≤ t` | `a > t` |
| --- | --- | --- |
| `a ≤ b` accepted | reviewer pays `a` | reviewer pays `min(a, c)`, `c ≥ 4t` |
| `a > b` rejected | reviewer pays `1.5a` | nothing |

- **An accepted charge pays `a` whether or not it is fair.** Our income from a charge is
  `a × [#accepting + 1.5 × #rejecting × 1(a ≤ t)]`. The best `a` depends on where the field's limits are, not only on `t`.
- **The reviewer's rule is per charge:** accept iff `P(fair) ≥ 2/3`. Errors are asymmetric in size (a full charge against half
  a charge) and, with 11 opponents who share one prior, they come in blocks: when one charge on a line is inflated, most are.

### 1.2 Known `t`

`b = t` against any field. `a = t`, unless many reviewers accept above `t`; then just under the cluster of their limits.

### 1.3 A belief about `t` when the whole field shares the error [opened: `common_shock_sim.py`, no real data]

Consensus `M`; `t = M·e^ε`, `ε ~ N(μ, σ²)` unknown to everybody; each team sees `M` with small private noise; opponents charge
0.70-0.95 of their estimate and accept up to 0.7-1.6 of it (strict, neutral, lax types). 40,000 lines, payoffs summed over 11
opponents, units of `M`, one silent team:

| setting | best `a` | income at 0.75 / 0.90 / 1.00 / 1.10 × m | best `b` | cost at 0 / 0.80 / 1.00 / 1.25 / 2.0 × m |
| --- | --- | --- | --- | --- |
| σ 0.5, μ 0 | 0.95 m | 8.10 / 8.68 / 8.73 / 8.57 | 0.75 m | 7.50 / 7.23 / 7.48 / 7.89 / 8.44 |
| σ 0.7, μ 0 | 1.10 m | 8.03 / 8.80 / 9.02 / 9.06 | 0.65 m | 7.25 / 7.24 / 7.54 / 7.96 / 8.45 |
| σ 0.5, μ +0.15 (models run low) | 1.05 m | 8.52 / 9.49 / 9.77 / 9.81 | 1.00 m | 8.80 / 8.10 / 8.01 / 8.13 / 8.46 |
| σ 0.5, μ 0, our log error 0.25 | 0.75 m | 10.26 / 9.59 / 8.43 / 7.04 | 0.90 m | 7.51 / 5.85 / 5.82 / 6.29 / 7.72 |
| σ 0.5, μ 0, our log error 0.10 | 0.85 m | 11.69 / 12.71 / 9.56 / 5.81 | 0.95 m | 7.49 / 5.65 / 5.34 / 6.20 / 7.86 |

- Uninformed, both curves are flat: the whole tuning range of both multipliers is worth about 1.3 `M` per line. An estimate with
  a log error of 0.25 is worth +3 `M`, with 0.10 about +6 `M` (the line is worth 16 `M` at `a = t`). **Information beats tuning by 2 to 5 times.**
- Uninformed and unbiased, **reject-all is cheaper than accept-all** (7.50 against 8.44) and the best limit is below the median.
  Only a belief that the models run low moves it to the median or above. That belief was the 1.25 rule.
- The best shading of `a` reverses with knowledge: charge near the median when ignorant, shade 15-25 % when informed.
- The simulation assumes the error is symmetric. Reality has been worse than that for a lenient reviewer (1.4).

### 1.4 The same on the real field [opened: `multiplier_replay_all_games.py`, live medians, opponents fixed]

| `b = k × m` on lines we priced as valid | games 1-6 | games 7-9 | all |
| --- | --- | --- | --- |
| reject everything | 29.5k | 2.4k | 31.9k |
| `k` = 0.5 | 29.4k | 4.5k | 33.8k |
| `k` = 0.67 | 30.9k | 8.7k | 39.7k |
| `k` = 0.8 | 29.5k | 16.2k | 45.7k |
| `k` = 1.0 | 25.5k | 20.8k | 46.3k |
| `k` = 1.25 (live) | 24.7k | 25.4k | 50.2k |
| accept everything | 24.8k | 25.6k | 50.4k |
| what we paid / a perfect reviewer | 26.9k / 19.7k | 25.4k / 1.6k | 52.3k / 21.3k |

Charge side, `a = k × m`, lower bound to upper bound over 9 games: 0.5: 39.2k-44.8k; 0.7: 48.5k-51.7k; 0.8: 49.2k-53.8k;
0.9 (live): 48.3k-58.4k; 1.0: 26.1k-59.7k. The ranges are wide because 7 brackets are right-censored (nobody charged above `t`).
In games 7-9 alone the lower bound is 12.8k at 0.5 and 3.5k at 0.9; in games 1-6 it is 26.4k at 0.5 and 44.8k at 0.9.

A pooled interval-censored fit of `log(t/m)` is not identified on games 1-7 (μ +0.58, σ 1.22; leave-one-out μ +0.36 to +0.90):
four two-sided brackets sit at −0.1 to −1.4, seven right-censored ones at ≥ −0.06 to ≥ +0.6. That is two populations (2.3).

**Where the value is:** charge side 42.6k, acceptance side 30.8k left on the table through game 9. Through game 6 the acceptance
side was about 7k against 36k on the charge side [team: `raw3` addendum]; it is now the faster-growing part, because every
line has 11 incoming charges.

---

## 2. What determines `t` in the real cases [opened: 8 distinct policies in the relevant parts, 9 descriptions and invoices, 3 photos]

### 2.1 Case by case (brackets rounded)

| game | claim and lines | what fixed `t` | bracket vs what models said |
| --- | --- | --- | --- |
| 1 | surge: electronics 2 pcs; diagnostic report and call-out | halving without surge protector (2.3.3) per the policy; report and call-out are not a repair cost | 780-900; 0 |
| 2 | laptop: screen, housing, pre-existing scuff, diagnostic | all damage areas covered; pre-existing condition not; examination up to 250; description: paid about 1,400, repairs "nearly" that | ≥ 810; ≥ 340; 0; 60-84. Live medians 714; 357; 143 |
| 3 | cabinet: 3 glazing lines, frame, shelf, vehicle costs | glazing is an optional peril, not shown as agreed | 0; 0; 0; ≥ 330; ≥ 160; < 30 |
| 4 | bicycle: recovery with locksmith, repair, labour and sundries | mobility sub-limit 500 incl. VAT over repair and recovery together, rateably | < 120; 230-250; ≥ 130 (consistent with a total of 500) |
| 5 | new laptop, price 1,400, one "damage payment" line | repair, or replacement amount if uneconomic | ≥ 1,170 |
| 6 | the laptop of game 2 as one combined line, **identical policy file** | as game 2 | ≥ 740 (nobody charged more); 18 model answers 340-600 |
| 7 | frost: fitting repair incl. thermal-imaging leak location; facade | leak location covered; external frost is optional, not agreed | about 450; 0. Models 770-1,430 |
| 8 | storm: disposal of timber, glass, green waste, root ball; three ground-material lines | clearance head covers debris and tree material; ground material excluded | < 75; 30-34; 40-70; < 50; 0; 0; 0. Our medians 42-310 |
| 9 | the surge claim of game 1, itemised, **identical policy file**, with a waiver of the surge condition: speaker, shipping, installation, TV, liability item, service order, vehicle costs | carriage and fitting are not repair costs (7.1.8); liability and service-order charges excluded (3.1.4, 3.1.5) | < 340; 0; 0; 520-620; 0; 0; 0. Our medians about 950 and 1,070 |

### 2.2 Three layers, three error rates

- **Zero or not: solved.** On the 14 clear `t = 0` lines the ensemble had `P(valid) ≤ 0.12`; on the 14 lines with a positive
  lower bound `≥ 0.73` [opened: `outputs/model_outputs.json`]. My blind reading of game 9 had all five exclusions right. The recurring trick is the missing Schedule: an optional peril counts as not agreed (games 3, 7).
- **Policy arithmetic: deterministic, and the new schema covers what occurred** (fraction, rateable limit, anchor, quantity).
- **Price level: the residual, and it is a factor of two either way.** Nothing in the documents states the experts' price list.

### 2.3 The price-level error has structure: hypothesis, failed test, revision

**H1 as written before game 9:** object work is priced at or below `t`, ancillary services far above. On games 1-8: 15 % of
charges inflated on 9 object lines, 86 % on 7 service lines.
**Blind test on game 9:** the two priced lines are replacement goods (speaker, TV), "object" lines under H1. Result: 9 of 12
charges inflated on one and 11 of 12 on the other (the twelfth undetermined); our medians were 1.7 to 2.1 and more than 2.8
times `t`. **H1 failed.**
**H1′, redrawn after game 9:** only *repair work* is under-priced.

| class | lines | all teams' charges inflated | `t / our median` |
| --- | --- | --- | --- |
| repair of the damaged item, its labour, a damage payment with a stated price | 8 (games 2-6; three families: laptop, cabinet, bicycle) | 7 of 62 = 11 % | ≥ 1.13, ≥ 0.96, ≥ 1.45, ≥ 0.94, 0.87-0.97, ≥ 1.81, ≥ 0.98, ≥ 1.49 |
| everything else we priced: services and cost heads, replacement goods, a mixed lump sum | 11 (games 1, 2, 3, 4, 7, 8, 9) | 93 of 111 = 84 % | 0.13 to 0.82; and 0.25 on the misread line of game 1 |

A reading that fits: the experts price lean ("equivalent standard-grade replacement", clause 7.1.9; plain rates for a call or a
skip), and models price a mid-range TV and a contractor's quote. Repairs are the exception, and two of the three repair
families carry a price anchor in the description. Caveats: redrawn after the fact; three families; the next trade (tiling,
painting, flooring by area) may behave differently. Frozen classifier for the test in 5.9: a line is *repair* iff its text
matches `repair|refinish|labou?r|damage payment` and does not match
`leak (detection|location)|call-?out|diagnos|dispos|vehicle|travel|transport|deliver|install|shipping`.

### 2.4 Cases repeat: confirmed, with a warning

- Games 2 and 6: identical policy file, invoices …0211 and …0212. Games 1 and 9: identical policy file, invoices …0190 and
  …0188/…0189. Game 5 is the laptop accident again in another edition. So 5 of 9 games belong to two families, and 2 of the last
  4 games had an exact policy precedent on disk. Invoice numbers run from 0001 to at least 0215 for 101 cases.
- Game 1's policy even describes game 9's invoices (its Part 11: a retail invoice with delivery and commissioning charges, a
  building-services invoice with a liability arrangement and an attendance charge) and lists the operative clauses.
- **Blind use in game 9, and how it went wrong.** Game 1 said: speaker plus TV, halved by the policy, 780-900. Game 9 waives the
  halving, so I predicted 1,560-1,800 for the two lines together. The brackets say under about 950. Used as it stood, without
  undoing the halving, the precedent would have been right and would have capped our limit at roughly 0.45 of our median; the
  replayed cost for the game falls from 15.2k to 2.4k and the income rises from 6.3k to about 8.4k. Either the experts' base prices differ between siblings or the
  halving is not in game 1's `t`. A person should spend ten minutes on that pair; it decides how precedents transfer.
- Game 6 remains unverified in the other direction: the precedent says at least 1,150, the bracket only says at least 740.

Rule drawn from this: a precedent may always lower a price; it may raise one only for the same item under the same reductions.

### 2.5 The achievable ceiling

Validity is at the ceiling. Without class or precedent the log error is about 0.6-0.7; with the class perhaps 0.35; with a
sound precedent 0.1-0.2. Our income through game 9 is 50.3k; the highest fair charge on each valid line alone would have
brought 88.2k. We pay 2.5 times what a perfect reviewer would.

Two smaller observations. Every tight bracket contains a round gross amount (450; 30; 230-250; 60-80; 800 or 850; 550 or 600),
which chance explains almost as well. The three photos I opened (cases 2, 4, 7) are generated illustrations with no fact that
is not in the text.

---

## 3. The field, games 1-9 [opened: public leaderboard JSON via `field_stats.py`, `group_aggregates.py`]

### 3.1 Aggregates

| | value |
| --- | --- |
| teams | 12; 6 active in every game (we are one), 1 from game 2, 5 joined between games 2 and 7 |
| silent teams per game | 5, 4, 5, 5, 3, 1, 1, 0, 0 (game 1 also had one team that charged nothing and accepted everything) |
| positive charges that were inflated, per game (lines not clearly excluded) | 8/11, 6/24, 8/19, 10/21, 1/9, 0/11, 10/11, 42/48, 53/57 |
| active reviewers rejecting fair charges, games 1-7 | 17 %, 28 %, 65 %, 55 %, 36 %, 36 %, 10 % |
| field's excess cost from rejecting fair charges, per game | 4.4k, 21.1k, 9.3k, 5.5k, 21.0k, 12.9k, 0.4k, 0.2k, 1.0k |
| field's payments for inflated charges, per game | 10.8k, 0.5k, 0.8k, 4.3k, 0, 0, 29.3k, 17.8k, 74.7k |
| clearly excluded lines since game 2 (13 lines) | 5 to 8 teams charged something on each; 5 acceptances in total, all of charges of a few euros |
| the excluded line of game 1 | 7 acceptances by 2 reviewers, 1.1k paid; a charge of several hundred euros was paid in full, so the cap floor is at least that |
| inflated share by charge level relative to our median (bins < 0.5 … > 1.5), games 1-7 | 21 %, 44 %, 31 %, 25 %, 13 %, 50 %, 67 % |

The last row answers idea (b): where a charge sits relative to our estimate says little about whether it is inflated. Which
line it sits on says almost everything (0 % to 92 % by line).

### 3.2 Archetypes (anonymous)

- **Silent** (`a = b = 0`): five teams at the start, none since game 8. They paid 1.5 × every fair charge and funded games 1-5.
- **Median LLM pipeline** (most teams): charges 0.75-0.9 of its estimate and accepts up to about 1.0-1.4 of its own charge.
  On repair lines its limit is below `t` and it pays penalties; on all other lines its limit is above `t` and it pays for
  inflated charges. Of 70 team-lines with a positive charge in games 1-7, the limit was certainly at or above the team's own
  charge in 20, certainly below in 12, undetermined in 38.
- **High charge, low limit** (a small minority; it has done well): limit below its own charge on most lines. It collects
  penalties on repair lines and is barely touched in games 7-9.
- **Strict reviewer with a low price level**: pays the largest penalties in games 2-6, almost nothing in games 7-9.
- **Fallback values**: at least one team submits the same amount on several lines or in several games.

### 3.3 What separates the top from the middle (group means per team and game, through game 9)

| group | income | cost | paid for inflated | penalty excess | median charge / best known fair level | set the highest fair charge of the line | own limit ≥ own charge / below |
| --- | --- | --- | --- | --- | --- | --- | --- |
| two best always-active teams | 7.1k | 3.8k | 0.9k | 0.5k | 0.95 | 7 of 28 | 9 / 7 of 27 |
| three other always-active teams | 5.4k | 4.2k | 1.3k | 0.5k | 0.86 | 2 of 42 | 3 / 9 of 36 |
| us | 5.6k | **5.8k** | **3.1k** | 0.3k | 0.87 | 0 of 14 | 8 / 1 of 14 |
| six late joiners | 2.9k | 4.6k | 1.1k | 0.9k | 0.97 | 5 of 84 | 17 / 5 of 40 |

The top is separated from the middle mainly by income (it charges closer to `t` on the lines where `t` is high). **We are
separated from everybody by cost**: we are the most lenient reviewer in the field's upper half.

### 3.4 How the field is changing

- From 6-7 active teams to 12. Each line now has 11 incoming charges; our lenient limit cost us 0-3k per game in inflated
  charges in games 1-6 and 4-14k in games 7-9.
- Reviewer errors flipped from "rejects fair" (games 2-6) to "accepts inflated" (games 7-9). Case mix explains it without
  assuming that anyone changed behaviour: games 2-6 were repairs, games 7-9 services and goods. Both readings lead to the same rule.
- No sign yet that teams use earlier rounds: in game 9 the field paid 74.7k for inflated charges on two items whose level was
  visible in game 1's rows. That is an opening, for as long as it lasts.

### 3.5 What can be beaten or exploited

1. On non-repair lines most teams accept inflated charges. A moderately inflated charge near the bottom of the field's range is
   paid by 7 to 10 reviewers, and rejecting theirs is right about 5 times in 6.
2. On repair lines most limits are below `t`: every fair euro added to `a` is paid 1.0 to 1.5 times by 11 teams.
3. Our reader shares the field's prior, so it locates the field's charges and limits even where it misses `t`.
4. Precedents. Nobody appears to carry knowledge from one game to the next.

---

## 4. Critique

### 4.1 `claimbot_fable` [opened: all source files, README, `runs/bench/fable_eval/*.json` re-scored through the engine]

Right: reader and engine split, printed POS numbers, tier priority, replayable logs, no depreciation rule.

Wrong or missing:

1. **`KB_OPEN = 1.25` and `KA_OPEN = 0.90` on every open line.** With its own reader (about 1,010 for the game-7 line) it would
   have lost games 7-9 like the live bot. Its "pinned" class does not capture what matters; the line class does.
2. **No memory.** Each case is read as if it were the first; two of the last four had an identical policy on disk.
3. **Anchors and limits scale without bounds.** One cheap reader's answer for case 3, run through the engine, gives medians
   above one million on four lines [opened: re-scoring of `fable_eval/20261121-153554.json`]. Nothing checks a value before it is submitted.
4. **The validity cliff.** `b` is `KB × m` at `P(valid) = 0.67` and 0 at 0.66. At `P(valid) = 0.75` the 2/3 rule needs
   `P(t ≥ charge | valid) ≥ 0.89`, a limit near half the median. The old `pricing.py` had this right before the `max(…, B_VALID_MULT × median)` override.
5. **p10/p90 are requested and never used**: output tokens and latency for nothing.
6. **The flagship reader is the default without a measured gain**: 123 against 144 EUR per line for the cheap reader on 17
   lines at roughly 80 times the cost [team: `claimbot_fable/README.md`]. On price level all models share the error.
7. **Photos go to the main reader**; I found nothing in the three I opened.
8. **Untested paths** by its own README: native Anthropic call, `--live`, zip plus 7-Zip. In game 5 all 10 Claude calls of the
   live ensemble failed with a 400 error (cause not checked by me; that case's photo is a 10 MB PNG).
9. **No tier 0.** If both providers fail, nothing is submitted.

### 4.2 The benchmark [opened: `bench.py`, `rule_replay.py`, `fable_eval.py`, `build_labels.py`, README]

1. **The acceptance replay is biased toward lenient limits.** `labels.jsonl` keeps the charges we received from our own rows
   only. A charge we rejected as inflated has amount 0 there, so `a = 0.0` and `classify` skips it. A candidate with a higher
   limit than ours would have accepted some of those charges; the replay never bills it. This flattered every "raise `b`"
   variant, including the 1.25 rule and the `fable_eval` table. Fix: take each issuer's charge from any row of the game (`field_recon.py`).
2. **It pools two opposite regimes**, hence "the pooled bias is small" and no correction that replicated.
3. **It scores the acceptance side in EUR and the charge side as a ratio** that ignores who would have accepted.
4. **Right-censoring** understates under-pricing exactly where everyone under-prices.
5. **In-sample prompts** (cases 1-4) are mixed into the headline table; the README says so.
6. Nine games cannot rank models. They can show that a rule is illogical (4.1 points 3, 4) or that an effect is huge (1.4).

### 4.3 The previous review (`raw3/fable-E`) [opened, read last]

Agree: reader and engine split; the charge side holds much of the money; drop web search, size weights and GEPA; ask the
organisers about the transaction rows; the write-up must match what ran.

Disagree:

- "Medians are low with probability 0.94-0.99" came from a pooled censored fit on 9 lines that were mostly repairs. It was
  followed by three games in which the medians were 1.2 to more than 4 times too high.
- "`KB = 1.25` on open lines": see 1.4 and 4.2 point 1.
- "Past brackets as a price book: not yet": written before game 6. Retrieval by line text across editions failed in the team's
  test; a gate on the policy hash is a different design. My own failure in 2.4 shows the limit of it.
- "One strong reader": no measured gain over the cheap one.

I made the same kind of error myself an hour later (H1). The lesson for both reviews: on this much data, prefer the rule whose
worst case is bounded.

---

## 5. The recommendation

### 5.1 Architecture

```
T+0    key, decrypt, MD5(policy.txt) -> precedents from a local file          tier 0: no-model submit, rejects (5.6)
T+0    two cheap text-only readers on two providers: new schema + line class + precedent relation
T+8-12 first reader back -> engine -> submit; second back -> merge -> submit                       tier 1 / tier 2
T+12   discrete facts differ? -> one strong reader sees both rationales, decides the disputed facts -> submit by T+40   tier 3
T+52   last submit. Never overwrite a higher tier.
T+180  results: brackets, memory, per-class calibration, shadow scores of every candidate rule
```

Information sources in order of value: a precedent under the same policy file; description anchors and policy limits
(in the engine already); the reader's price with a per-class factor. No web search, no photos, no panel of models sharing one prior.

### 5.2 Reader changes

Per line add `line_class` in {`repair`, `other`} with the definition of 2.3 (the keyword rule is the fallback and the audit).
Per line add `precedent_ids` and `relation` in {`same_item`, `sum_of`, `part_of`, `none`}, plus `same_reductions` (bool).
Feed up to ten precedent lines (same policy hash first, then same edition title) as a table: line text, "excluded" or the
rounded bracket, the reduction that applied. Tell the reader to look for a section naming the operative clauses, and that an
optional peril without a statement that it was agreed is not agreed. Drop p10/p90.

### 5.3 Rule engine: starting values

`m` is the engine's median after fraction, limits and anchors.

| line | `a` | `b` | basis |
| --- | --- | --- | --- |
| default (`other`) | 0.55 `m` | 0.45 `m` | 84 % of charges inflated; `t/m` 0.13-0.82; bounded worst case |
| `repair` | 0.90 `m` | 1.25 `m` | 11 % inflated; `t/m ≥ 0.94` on 7 of 8; unchanged from today, so nothing new is tuned |
| `repair`, pinned by limit or anchor | 0.88 `m` | 1.10 `m` | shade when informed (1.3) |
| precedent with upper bound `U` | at most 0.95 `U` | at most `U` | always applied |
| precedent with lower bound `L`, `same_item` or `sum_of`, same reductions | at least 0.95 `L` | at least `L` | only then |
| `P(valid)` from 2/3 to 0.9 | as above | table value × (0.4 + 0.6 × (P − 2/3) / 0.233) | removes the cliff |
| `P(valid) < 2/3` | as default (hedge on our own reading) | 0 | unchanged |

Then round `a` down to a multiple of 5 (under 100) or 10. The limit is below the charge on default lines. That is intended: a
quoted spread under adverse selection, and the shape of the best-performing archetype.

Replay over games 1-9, 19 priced lines, live medians, opponents fixed, net as lower bound to upper bound [opened: `strict_default_replay.py`]:

| rule | cost | net | games 1-6 / games 7-9 (lower bound) |
| --- | --- | --- | --- |
| live: 0.90 / 1.25 everywhere | 50.2k | −1.9k to +8.2k | +20.0k / −21.9k |
| 0.90 / 0.50 everywhere | 33.8k | +14.5k to +24.6k | +15.4k / −0.9k |
| 0.90 / reject everything | 31.9k | +16.4k to +26.4k | +15.2k / +1.1k |
| **interim: 0.80 / 0.45 everywhere** | 34.0k | +15.2k to +19.8k | +11.1k / +4.1k |
| 0.55 / 0.45 everywhere | 34.0k | +7.5k to +14.2k | −0.4k / +7.9k |
| `a` 0.90; `b`: repair 1.25, other 0.45 | 26.4k | +21.9k to +32.0k | +23.0k / −1.0k |
| **recommended: repair 0.90 / 1.25, other 0.55 / 0.45** | 26.4k | +32.7k to +44.2k | +24.8k / +7.9k |

Rows 2 to 5 need no classification; they are the robust part, and they show that the strict default belongs on the limit, not
on the charge (a low charge everywhere gives up the repair income). The last two rows use the post hoc class. The repair
values are today's live values, so the exception adds no newly fitted number.

### 5.4 Calibration loop (after every game, about 3 minutes after the start)

1. **Own bit per class** (our own rows only, safe under any reading of the rules): charge fair → `KA_class × 1.02`; inflated →
   `× 0.92`; nobody rejected it → `× 1.02`. Target fair rate about 80 %. Bounds: repair 0.75-1.20, default 0.30-0.90. This is
   Robbins-Monro stochastic approximation, the update behind adaptive conformal inference [memory].
2. **Level factor per class** from the censored brackets: normal model of `log(t/m)` per class, prior centred on the starting
   value with the weight of 4 lines (credibility weighting [memory]); grid fit as in `replay_rules.fit_censored`. `KB` moves only through it.
3. **Memory**: append each line (policy hash, edition title, invoice number, trade, text, class, rounded bracket, reduction,
   our `m`) to a gitignored file. A person checks new entries and class tags between rounds; 12 minutes is enough and manual
   work inside the team is allowed.
4. **Shadow table**: every candidate rule set is computed from the same reader answers each round (no extra calls) and scored
   on the realised field with lower and upper bounds, per game and cumulative.
5. **Alarms**: all-zero rows for us; more than 4 inflated charges accepted on one line; `KA` at a bound; a class with fewer
   than 5 lines driving a change.

### 5.5 Switching the live bot (idea m)

- **Now, no code:** `CLAIMS_B_VALID_MULT=0` and `CLAIMS_REJECT_P=0.2` put the live limit near 0.45-0.6 of the median for the
  ensemble's usual spread of about 0.5 (and at 0 when `P(invalid) ≥ 0.2`, which also zeroes borderline-valid lines). Cleaner:
  one line, `b = 0.45 × median`. Set `CLAIMS_A_MEDIAN_MULT=0.8` until the class exists (income lower bound 49.2k against 48.3k
  at 0.9 over 9 games; 8.7k against 3.5k in games 7-9).
- **Next:** the keyword class in `ensemble.combine` (repair lines back to 0.90 / 1.25).
- **Then:** `claimbot_fable` in dry-run beside the live bot for two rounds with the cheap pair, the new engine table and the
  guards; check zip path and both providers; one supervised live round; switch.
- **Later switches:** promote a candidate when it leads the live rule on the cumulative lower-bound score over at least 6 games
  and 8 affected lines; revert when it trails by more than 3k over 3 games. Per-game results have a standard deviation of
  about 4.6k for us, so do not expect significance; decide on bounded downside.

### 5.6 Reliability

- **Tier 0 at T+1 s, no model:** one entry per printed POS line; `a` = a precedent level if the policy hash is known, otherwise
  about 25; `b = 0`. A blind reject-all was the best blind rule in the replay and cannot pay for inflated charges.
- **Guards before every submit:** anchor or limit scale factor outside 0.4-2.5 → ignore it and log; the two readers' medians
  differ by more than 3 × → use the lower one for both `a` and `b`; any value above 20,000 → hold and alert; POS count must equal the line count.
- Two providers in every round; no photos; no call longer than 40 s.

### 5.7 Keep, change, drop

| | item | expected gain | risk |
| --- | --- | --- | --- |
| keep | reader and engine split, POS mapping, tiers, logs, archive loop, anchors and limits | — | — |
| keep | a charge on lines we think are excluded | about zero (5 tiny acceptances on 13 lines) | sounds like billing fraud in a pitch; call it a hedge on our own reading, or drop it below `P(valid)` 0.05 |
| change | limit 1.25 `m` → 0.45 `m` by default | +16k over 9 games in replay; −4.6k on games 1-6, +21k on games 7-9 | a run of repair cases costs half of each fair charge rejected; the repair exception covers the known ones |
| change | one class → repair exception | +7.4k more on the limit and +10.8k on the charge split (post hoc) | three families behind it; the loop corrects in about 5 lines |
| change | no memory → precedent cap and guarded floor | game 9: about +15k; game 6: +8k to +13k if the floor is right | a wrong transfer (2.4); cap-only is the safe half |
| change | 8 flagship calls → 2 cheap + arbiter | same reading at about 5 % of the tokens | a cheap reader misreading a new edition; the pair and the arbiter cover it |
| change | manual refit → per-class loop each game | catches the next regime surprise in 1-2 games instead of 3 | noisy early steps; bounded |
| change | benchmark replay uses every issuer's charge | honest numbers | — |
| drop | photos, web search, p10/p90, size weights, per-model bias correction, GEPA, "medians are low" | tokens and latency | none measured |
| drop | variance plays before the last hour | — | — |

### 5.8 Ideas a to m, one line each

| | idea | verdict |
| --- | --- | --- |
| a | hierarchical interval-censored bias model | yes, **per line class**; pooled it is unidentified (1.4). Editions as a level once 20+ games exist |
| b | empirical-Bayes `b` from the field's charge/t ratios | the charge level carries little (3.1 last row); the line carries it. Adopted as a class-level inflated share |
| c | closed loop on `a` from our own bit | yes, per class (5.4). It would have cut `KA` after game 7 instead of after three losses |
| d | disagreement cascade, minimax across readers | yes for discrete facts. On price, take the lower reader; a stronger model shares the prior |
| e | soft fusion instead of hard pins | as one-sided clamps and class factors; a full posterior is not worth building on this data |
| f | calculation DSL | no: the fixed fields covered all 9 cases; a DSL adds failure modes inside 60 s |
| g | edition digests, prompt caching | caching: no (13 min between rounds, no common prefix). By policy hash: yes, as the memory |
| h | nonstationarity | silent teams are gone; the acceptance side tripled in weight; the per-class loop and the alarms are the detector |
| i | rank objective, jury | expectation only until the last hour. 30 jury points equal 4.7 rank places. We are 7th; ranks 5-8 lie within about 16k, three to four of our per-game standard deviations, and 91 games remain |
| j | quant analogies | spread quoting (`b < a`), adverse selection on what we accept, fat-finger limits, kill switch: adopted. Kelly sizing: no bankroll constraint here |
| k | level-k | level 0 is the median pipeline; the strict default is the level-1 reply and stays sound if others adopt it, because it does not rely on anyone accepting inflated charges |
| l | ML | conformal: the own-bit loop is its online form. Isotonic `p_valid`: nothing to fix (28 of 28 decidable lines). Fine-tuning: no data. Active learning: probe upward on a repeated family when its precedent is right-censored |
| m | shadow harness | yes (5.4 point 4, 5.5) |

### 5.9 Next five experiments

1. **H1′ blind (no cost).** The classifier in 2.3 is frozen as of game 9. For games 10-25 record, per priced line, class and the
   share of all teams' charges that were inflated. Holds if repair lines stay below 33 % and other lines above 60 % over at
   least 8 new lines each, from at least two new families. If it fails, keep the strict default everywhere.
2. **Precedent audit (no cost).** For every new game with a known policy hash or edition, write the cap and the floor before
   the round and compare with the bracket. Count repeats per 10 games, caps that held, floors that held. First item: have a
   person resolve the game 1 / game 9 pair (2.4).
3. **Shadow table (no cost).** Five rule sets of 5.3 on every game from now on; the table goes into the write-up.
4. **Cheap pair against a strong reader (about $3).** Ten games, text only, same case: do discrete facts agree (valid,
   fraction, quantity, limits, class)? Where they differ, which side does the bracket support? Fix the arbiter trigger and its rate.
5. **Photo ablation (about $0.20).** Nine cases, same reader with and without the image, 2 repeats. Drop photos if no discrete fact changes.

### 5.10 What I could not verify

- H1′ on any game after it was drawn. The repair exception rests on three families.
- That `t` in game 6 is at least game 2's sum; why game 1 and game 9 agree in level although one is halved by the policy.
- How often families repeat over 100 games (2 exact repeats and 1 near repeat in 9).
- Any model call, the cascade, the second provider's latency: I made no calls.
- Whether using the public transaction rows to bracket `t` is acceptable under "do not … extract the secret thresholds". The
  page is the organisers' own, but the memory and step 2 of the loop depend on it. **Ask them.** The strict default, the class
  rule and step 1 of the loop need only our own rows.
- The team's new euro replay evaluator (committed at 16:02 while I was finishing): not read. Compare its numbers with 5.3.
- `kind_replay.py` and `replay_rules.py` were run before the logs of games 8-9 were committed; the final tables (1.4, 5.3) use the logs.
- The round-number pattern, the 500 total in game 4, and whether a photo ever matters.

---

## 6. Ideas I would try that nobody on the team has mentioned

1. **Strict by default, lenient by exception.** The team's debate was which multiple above the median; the answer is below it.
2. **Line class as the regime variable** (2.3), frozen as a keyword rule so it can be tested without judgement.
3. **Policy hash and invoice-number adjacency as family keys** (2.4); the reader states the relation, Python clamps one-sidedly.
4. **Quote a spread**: charge at the low end of the field's range, accept only below it.
5. **Use our reader as a sensor of the field**, not only of `t`.
6. **A person curates the memory between rounds**: not in the 60 s, in the 12 minutes after.
7. **Tier 0 rejects.** A blind reject-all beat every blind multiple over 9 games.
8. **Round `a` down to round amounts**: a charge a few euros above a round `t` loses the whole line.
9. **Fix the replay bias** (4.2 point 1) before another acceptance number is quoted to the jury.
10. **An alarm on accepted inflated charges per line.** Three losing games in a row should have tripped something after the first.
11. **Probe upward on repeats** whose precedent is right-censored: one charge 10-15 % above the highest known fair level, read our own bit.
12. **Do not read future zips' directory listings** to learn the edition early. The size of `policy.txt` would probably reveal
    it; the gain is small (the hash is known at T+0) and it is too close to the fair-play line. I did not do it.

---

## 7. The jury story this approach supports

1. A model reads the policy and names facts; Python does all arithmetic and strategy, so every submitted number can be replayed.
2. We measured where the money goes: 58 % on the charge side, 42 % on the acceptance side, almost none on zero-or-not coverage decisions.
3. Our price estimates were off by a factor of two in both directions, and so was the whole field's, in the same direction on the same lines.
4. So we stopped tuning multipliers and bounded the worst case: accept little by default, more only on repair lines, where the evidence says models run low.
5. Cases repeat under identical policy files. We keep a small memory keyed by the policy and use it to cap prices; a person checks it between rounds.
6. After every round our own results move the multipliers one small step per line class.
7. Two small models on two providers read each case in about ten seconds; a large model is called only when they disagree (from 742k input tokens in game 6 to about 40k; to be measured).
8. Evidence: a per-game table that scores every rule we considered on the realised field, including the ones that failed.
9. What failed, stated openly: a prompt that did not replicate, an optimiser that memorised labels, a benchmark biased toward lenient limits, a 1.25 rule that cost about 21k in three games, and a classification we had to redraw after one blind test.
10. Weaknesses that remain: right-censored labels, three families behind the repair exception, and a price level no document reveals.

---

## Appendix: scripts (no data inside)

| file | purpose |
| --- | --- |
| `scripts/fetch_field.py` | public rows of all teams for completed games into a folder outside the repo, 1 request/s, incremental |
| `scripts/field_recon.py` | per line: each issuer's charge and status, each reviewer's limit bracket, the `t` bracket (in memory) |
| `scripts/field_stats.py` | the aggregates of 3.1 |
| `scripts/group_aggregates.py` | group means of 3.3 and our loss decomposition |
| `scripts/replay_rules.py` | revenue and cost functions, the pooled censored fit |
| `scripts/multiplier_replay_all_games.py` | the table in 1.4: `b = k × m` and `a = k × m` through game 9 |
| `scripts/kind_replay.py` | the first split (H1), as tested before game 9; kept for the record |
| `scripts/strict_default_replay.py` | the table in 5.3 (strict default, repair exception), games 1-9 |
| `scripts/common_shock_sim.py` | the simulation of 1.3 |

Run `python3 -I research/raw4/scripts/fetch_field.py /private/tmp/<dir>`, then any other script with `/private/tmp/<dir> --us "<our team name>"`.
