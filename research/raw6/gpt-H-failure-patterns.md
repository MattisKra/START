# Claim to Fame — where Kiebler loses euros

21 November 2026 · Games 1–11 · 44 invoice lines · Independent offline analysis

## One-page summary

**The strongest change to test is a tighter acceptance limit for uncertain prices.** We earned **−€3,771**. Against a conservative hindsight benchmark, the measurable shortfall was **€76.8k–€79.7k**. Five lines account for about **60%** of the lower estimate. The benchmark recovers **€24.4k–€26.4k** from raising low fair charges, **€18.4k–€19.1k** from replacing inflated charges, **€30.4k–€30.5k** from rejecting inflated charges we paid, and **€3.7k** from accepting fair charges we rejected. These are historical euros against the same field.

1. **Loose review limits made shared overpricing expensive.** The field commonly overcharged for the frost repair, storm clearance and replacement electronics. Our own review paid €14.0k in confirmed inflated charges in game 9 and €2.5k in game 10. Using Luna's saved price estimate, a review limit of **0.45 × gross median** selected on games 1–8 adds **€13,289 in game 9** and **€2,370 in game 10**, with the issuer action held fixed. Game 11 has no saved median. The same rule costs **€2,530 and €1,761** on the laptop lines in games 5 and 6. Use it as a shadow candidate and keep the repair exception as a separate comparison.
2. **Reader agreement is a poor price check.** All three saved readers overshot the bracket for both items in game 9 despite agreeing within 1.4×. They also agreed within 1.12× on game 7's overpriced frost line. On game 10 they disagreed by 6.5×, and Luna's lower estimate was compatible with the bracket. An escalation to Fable based on Luna's wide price band helped game 9 and lost **at least €3.2k** versus the same Luna policy in game 10. Ask for independent evidence about the parts, labour or haul when needed. A second generalist is a weak substitute.
3. **Coverage decisions transfer better than euro amounts.** The existing validity gate matched the policy reading on **26/26** live training lines and **7/7** live game-9 lines. All three saved readers also matched **9/9** lines in games 9–10. In game 11, the seven documented exclusions had zero reviewer cost. Same-policy siblings kept the glazing and ground-material exclusions, but the surge endorsement, laptop settlement basis and invoice grouping changed the pricing problem.
4. **The original broad object-versus-service split failed. The narrower repair split remains provisional.** On the only priced simple repair after game 8, the game-11 side table, our own charge was fair and **9/10** positive opponent charges were fair. On the four other potentially payable holdout lines, **36/42** positive opponent charges were confirmed inflated, with one unresolved. That supports testing a repair exception. The side-table median is missing and the only qualifying repair repeats the wood/glazing family. The holdout cannot establish that a lenient repair limit earns more.

**Priority:** Freeze the review-only rule and the repair-exception variant for the next fresh families. Hold issuer prices fixed in the first comparison. Preserve the coverage gate and verify arithmetic when a clause specifies a reduction. Score both roles against actual settlements and record which payload would have been available inside the minute. **[opened]** [Game rules](../../materials/GAME_DESCRIPTION.md) · [Live model outputs](../../outputs/model_outputs.json) · [Settled cases](../../past-cases/) · [Replay and audit](../raw5/gpt-G-evaluator-audit.md)

## 1. Where we lose

### Accounting and benchmark

I matched 44 consecutive invoice positions to **5,808 unique ordered-pair rows** in the supplied public cache. The rows reconcile to our archived net for every game and to all 132 team-game totals in the supplied matrix. I used logged submissions for games 1–9 and our settled amounts and outcomes for games 10–11. The original evaluator covers our observed net in all nine logged games, with zero-width ranges in seven. Games 8 and 9 have widths of about €357 and €997. The audit version reconciles all nine exactly. I used that version's reconstruction and payoff functions, and paired each changed action with the settled outcome for that role. A separate 18,000-check cent-grid simulation found no paired replay misses. **[opened]** [Original evaluator](../bench/euro_replay.py) · [Audit evaluator](../raw5/scripts/g_replay_fixed.py) · [Analysis](scripts/account.py) · [Own results](../../past-cases/)

- **Issuer benchmark:** On a potentially payable line, take the better of our actual receipts and receipts at the highest observed fair charge, (L). If (L=0), there is no demonstrated fair-price upside. The ranges carry unresolved acceptance by other reviewers. On a documented exclusion, hold our issuer receipts fixed. A fair price earns more as it increases, even when it crosses a reviewer limit and triggers the 1.5× fair-rejection payment.
- **Reviewer oracle:** (b=t) minimizes the reviewer's cost. Each paid fair rejection cost an extra third of its transfer. Each accepted inflated charge cost its entire transfer. Two positive all-accepted tickets totaling €135.66 have unresolved fairness. These add zero to €136 of reviewer shortfall.
- **Full hindsight:** The conservative benchmark earns **€73.0k–€75.9k net**. The true fair-price oracle can earn more, and the upper end is unbounded by this evidence for eight potentially payable lines. The unrestricted oracle can also choose any profitable inflated charge, including on exclusions, and cannot be identified from the observed reviewer limits and known lower bound on the cap. The replay ranges are limits for this historical field. Sampling uncertainty about future games is separate. **[opened]** [Game rules](../../materials/GAME_DESCRIPTION.md) · [Bracket labels](../../runs/bench/labels.jsonl) · [Analysis](scripts/account.py)

Amounts are rounded to whole euros. “Below” and “inflated issuer” are issuer shortfall against the benchmark. “Paid inflated” counts confirmed payments. Add €0–68 of unresolved review cost in each of games 8 and 9. “Penalty” counts the excess over the fair charge. Rank uses all 12 teams.

| Game · case | Net | Rank | Below | Inflated issuer | Paid inflated | Penalty | Total shortfall | Benchmark net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 · surge, combined | −1,575 | 6 | 0 | 8,727–9,118 | 3,115 | 0 | 11,842–12,233 | 10,267–10,657 |
| 2 · laptop, itemized | 3,460 | 6 | 7,012–7,587 | 698–728 | 169 | 1,689 | 9,568–10,173 | 13,028–13,633 |
| 3 · cabinet and glazing | 2,195 | 4 | 3,105–3,348 | 0 | 28 | 813 | 3,947–4,190 | 6,142–6,385 |
| 4 · bicycle and recovery | 2,613 | 2 | 1,331–1,444 | 0 | 907 | 113 | 2,350–2,464 | 4,963–5,077 |
| 5 · new laptop | 7,562 | 4 | 5,095–5,678 | 0 | 0 | 0 | 5,095–5,678 | 12,657–13,240 |
| 6 · laptop, combined | 5 | 8 | 7,022–7,394 | 0 | 0 | 372 | 7,394–7,766 | 7,399–7,771 |
| 7 · frost | −4,137 | 11 | 0 | 3,192 | 5,883 | 0 | 9,075 | 4,939 |
| 8 · clearance, itemized | −3,238 | 12 | 0 | 483–503 | 3,677 | 0 | 4,159–4,248 | 921–1,009 |
| 9 · surge, itemized | −8,872 | 12 | 0 | 3,314–3,573 | 14,022 | 0 | 17,336–17,663 | 8,464–8,791 |
| 10 · clearance, combined | −2,792 | 11 | 0 | 1,957–2,035 | 2,511 | 0 | 4,468–4,546 | 1,676–1,754 |
| 11 · side table and glazing | 1,008 | 4 | 839–956 | 0 | 41 | 686 | 1,566–1,684 | 2,574–2,691 |
| **Total** | **−3,771** | | **24,404–26,408** | **18,371–19,149** | **30,353** | **3,674** | **76,802–79,719** | **73,031–75,948** |

The top five lines were **1.1 surge appliances (€11.8k–€12.2k), 9.4 TV (€10.5k–€10.7k), 7.1 frost fitting and imaging (€9.1k), 6.1 combined laptop (€7.4k–€7.8k), and 9.1 speaker (€6.9k)**. Together they account for **€45.6k–€46.7k**. Games 1 and 9 account for €29.2k–€29.9k on surge. Games 2, 5 and 6 contribute €22.1k–€23.6k on laptop cases. Frost adds €9.1k, clearance €8.6k–€8.8k, wood/glazing €5.5k–€5.9k, and bicycle €2.4k–€2.5k.

**Systematic versus field exposure.** Game 1 contains a documented half-payment omission. Games 7–10 share a price-level and review-limit failure, with €26.1k of confirmed inflated review payments and €35.0k of total shortfall. The field was more active by then. Fixed-field replay still removes most of our losses when only our acceptance limit changes. Games 2 and 6 show the opposite pattern. We undercharged on fair work, and game 6 had just one default-like team to pay fair-rejection premiums. That reduced issuer receipts, but a higher *observed fair* charge still recovers at least €7.0k in the same field. Game 5's zero review regret was helped by the field's mostly fair charges. There is no clean example where bad luck alone explains a major loss. **[opened]** [Per-line ledger below](#per-line-euro-ledger) · [Measurements](scripts/measure.py)

## 2. Which inputs predict price error and loss?

The [feature table](#44-line-feature-table) pairs invoice scope and quantity with documented coverage, price estimates and reader agreement. The main feature screen uses one constant saved Luna configuration because production changed and stopped logging here after game 9. The signed price score is the shortest signed log distance from the median to ([L,U)). A zero means compatible with the bracket. Eight potentially payable lines have no upper bound and six have no positive lower bound. The loss target is the lower benchmark shortfall per line.

For each binary feature I fit two training means on games 1–8 and predicted game-9 and game-10 lines. The table shows the feature-positive minus feature-negative mean, with a **90% whole-game bootstrap interval** from 2,500 draws, and the change in out-of-sample mean absolute error relative to one training mean. Negative error change helps. Bootstrap draws lacking one class are omitted. Counts refer to potentially payable lines with readers. Game 11 supplies settlements but no price predictions. There are just 17 training and 3 held-out lines from 8 and 2 games. I also ran the shorter live-median screen on 17 and 2 lines. This was a comparison of roughly 30 correlated features and two outcomes. The intervals are descriptive and unadjusted for selection. A single held-out edition can move both the score and the euro target. Repeated case families also limit what resampling games can tell us. **[opened]** [Feature definitions and tests](scripts/measure.py) · [Saved readers](../../runs/bench/fable_eval/)

| Feature | Train → test positive | Log price effect [90%] | Loss effect in €k [90%] | Test error change, log / €k | Verdict |
|---|---:|---:|---:|---:|---|
| Original object class | 9/17 → 2/3 | −0.43 [−0.69, −0.23] | +2.52 [−0.42, +5.34] | +0.21 / −0.35 | Price sign reversed in game 9 |
| Narrow repair class | 8/17 → 0/3 | −0.43 [−0.64, −0.25] | +0.47 [−3.30, +3.08] | −0.07 / +0.22 | Repair half untested by held-out reader estimates |
| Goods / replacement basis | 1/17 → 2/3 | +0.01 [−0.15, +0.17] | +9.24 [+7.34, +10.29] | −0.01 / −1.39 | Euro stress repeats in the same surge family. One training line with a reduction miss |
| Repair labour on a flat rate | 3/17 → 0/3 | −0.41 [−0.79, −0.18] | −1.69 [−4.00, −0.15] | −0.02 / −0.30 | Side-table settlement is directionally consistent. Its median is missing |
| Disposal | 4/17 → 1/3 | +0.24 [+0.06, +0.39] | −2.75 [−5.58, −1.16] | +0.10 / +0.27 | Held-out Luna estimate is compatible. Terra and Fable overprice |
| Other named cost head, including travel and bundles with recovery/imaging | 8/17 → 1/3 | +0.43 [+0.23, +0.69] | −2.52 [−5.34, +0.42] | +0.21 / −0.35 | Price contrast reverses. Diagnostics and travel have one training positive each |
| Bundle or explicit grouped scope | 9/17 → 1/3 | −0.15 [−0.33, +0.13] | +2.60 [−0.03, +6.06] | −0.08 / +0.51 | Price and euro directions depend on the story |
| Flat rate / quantity >1 | 4 or 3/17 → 0 or 1/3 | −0.13 [−0.63, +0.64] / −0.02 [−0.16, +0.19] | +0.57 / +1.39, both intervals span 0 | −0.01 / +0.13; −0.01 / −0.22 | No general price correction |
| Electronics trade | 6/17 → 2/3 | −0.27 [−0.52, −0.04] | +3.87 [+0.76, +8.08] | +0.15 / −1.22 | Price sign flips. Laptop and surge behave differently |
| Explicit description price | 3/17 → 0/3 | −0.21 [−0.36, −0.03] | +1.77 [−1.10, +3.34] | −0.01 / +0.31 | Only laptop training lines. The repair-vs-new comparison is one story |
| Reader median <€100 | 7/17 → 0/3 | −0.05 [−0.41, +0.45] | −3.97 [−6.19, −2.25] | −0.01 / −1.43 | Smaller stakes in training. No priced holdout in this band |
| More than three lines | 10/17 → 2/3 | +0.16 [−0.24, +0.38] | −3.34 [−7.95, −0.35] | −0.07 / +0.69 | Loss direction reverses |
| ≥40% of potentially payable estimated total | 7/17 → 3/3 | −0.04 [−0.33, +0.33] | +5.35 [+3.32, +7.46] | +0.01 / −1.93 | Useful for ranking exposure. No holdout contrast or directional price signal |
| (P(mathrm{valid})) ≥.90 | 10/17 → 3/3 | +0.13 [−0.33, +0.41] | +1.29 [−0.93, +5.16] | −0.02 / −0.53 | High confidence in coverage conveys little about price |
| Reader spread ≥2× | 3/17 → 1/3 | +0.29 [+0.13, +0.41] | −2.31 [−4.47, −0.78] | +0.11 / +0.36 | Game 8 drives training signal. Reverses in test |
| Wide price band, Luna p90/p10 ≥4 | 14/17 → 3/3 | +0.21 [+0.03, +0.36] | −1.77 [−3.34, +1.10] | −0.01 / +0.31 | No holdout contrast. The live log-spread proxy worsens held-out euro error by €0.92k/line |

Edition names and individual trades are mostly single-family indicators. An optional-peril flag explained coverage through its actual clause and story facts. As a price feature on potentially payable lines it had a training effect of +0.35 log [+.14,+.81], with no positive held-out Luna observation. A potentially applicable cap had −0.07 log [−.29,+.38] and increased test price error. A fraction below one was a one-line Luna feature. The quantity-cut feature had an interval that spanned zero and had no positive held-out case. All 11 cases contained one photo, and none established a numeric event deductible to apply. The saved Luna/Terra/Fable runs vary reader and image setting together. The separate game-1–8 photo study reported weaker proxy scores with photos. I found no saved held-out paired photo outputs to validate that effect. **[opened]** [Case artifacts](../../runs/bench/cases/) · [Photo experiment code](../bench/image_test.py) · [Benchmark notes and reported photo results](../bench/README.md)

**Which split survives?** I reproduced the original object's blind failure. The live game-9 medians exceeded the observed upper bounds on both goods lines by at least **2.83× and 1.74×**. Both were classified as objects by the original rule. For the narrower post-game-9 regex, the eight training repair medians have **4 below / 3 compatible / 1 above**. The nine other priced medians are **9 above**. Game 9 has no positive repair and is only a retrospective illustration for this revised rule. In the genuine subsequent games, the game-10 clearance results are mixed by reader. The game-11 side-table charge was about 82% of the highest observed fair charge, while its first attendance had no observed fair price. That is consistent with the narrower split, with only one subsequent repair and no live price medians in either game. A claim that simple repairs are always underpriced, or that all other lines are overpriced by every reader, fails on these data. **[opened]** [Original and revised definitions](../raw4/fable-F-best-approach-review.md#23-the-price-level-error-has-structure-hypothesis-failed-test-revision) · [Independent tests](scripts/measure.py)

## 3. Validity, quantity and price level

| Layer | What the sample establishes | Euro attribution |
|---|---|---|
| Validity | 0 documented classification errors in 33 live lines at (q ge 2/3). Train 26/26, game 9 7/7. On games 9–10 the three saved readers each match all 9 document calls. Luna had one marginal false negative in training, at 4.3 (0.65). No game-11 reader log. | **€0 observed review loss on 22 documented exclusions**, including 13 in games 9–11. Our positive charges on four exclusions earned €628. That is issuer revenue under the observed field. |
| Quantity / reductions | **One confirmed live reduction omission**, the 50% surge clause in 1.1, absent from both live members' schema even when mentioned in rationale. All three saved new-schema readers applied 0.5. **Zero independently confirmed mistakes in justified count.** Recovery 4.1 has plausible one-operation scope and live quantities of 1–3, mixed with rateable allocation. In 10.1 all readers use quantity 4 and fraction 1, while gross medians range from €190 to €1,238. | 1.1 accounts for **€11.8k–€12.2k total shortfall**, including price and action effects. Changing only the actual submitted amounts to half size recovers **€919–€3,512** and would still leave the issuer above the bracket. Halving both 4.1 actions as a sensitivity recovers €94–€722. That does not identify the correct allocation or quantity. |
| Effective price | **16/19 live potentially payable medians demonstrably outside** the bracket, 12 above and 4 below. Games 1–8: 14/17 outside. Game 9: 2/2 above. With the known reduction miss removed, 15/18 remain outside. Across games 9–10, exact same-reader scores are Luna 2 above and 1 compatible, Terra and Fable each 3 above. | Largest evidenced failure mode. About **€65.0k–€67.5k** of measurable shortfall sits outside 1.1, mostly on lines with plausible coverage and scope. This is a residual, including action shading and possible scope arithmetic. It is not a causal estimate of what better unit prices would recover. |

Game 7 is a particularly clean price failure. The covered fitting and imaging have quantity one and no identified reduction. The €2,500 gross imaging cap in §5.2.2 is well above the reader medians for the entire line. All three saved medians are around €1.0k–€1.13k against a bracket near €450. One attendance and incremental imaging are plausible components of a lower quote. The artifacts cannot price them separately. Game 9 repeats the high-agreement failure on both goods. Game 8 has three priced lines with reader spread ≥2×, which is the entire training set for that trigger. For game 10 the model's unit price, rather than the shared quantity and fraction, explains the difference between the three answers. **[opened]** [Frost and clearance policies](../../runs/bench/cases/) · [Live outputs](../../outputs/model_outputs.json) · [Saved generalists](../../runs/bench/fable_eval/) · [Saved specialists](../../runs/bench/specialist/)

## 4. Similar policies and repeated claims

Policy hashes are byte-exact. The earlier-to-later predictions below use only the earlier case's evidence and the later case's pre-submission scope. They are single transfers and preserve differences in wording and payee.

| Earlier → later | What transfers | What changed and what happened |
|---|---|---|
| **2 → 6**, exact Portable Equipment, Repair and Replacement; **5** is a related edition and story | Coverage of accident damage and the repair-or-replacement valuation branch. Earlier split repair charges supply a plausible scale, with their combined observed fair floor near €1.15k. | Game 2 describes repairs nearly costing the roughly €1.4k acquisition price, mostly display, and the policyholder is paid. Game 6 combines the work and pays the supplier directly (§7.1.12), with no quantitative anchor in the description. The clause preserves coverage when the payee changes. Copying the earlier sum into both actions gives **−€4.51k to +€14.47k** in game 6. A reviewer-only use would save €372 in the replay, but the uncertainty is asymmetric because a higher limit can pay inflated charges on another sibling. Game 5's €1.4k is the acquisition price and its policy is different. In games 2, 5 and 6 respectively, **12/14, 7/8 and 10/10** positive opponent repair charges were fair. Our laptop charges were fair and below the observed fair floors in all three games. |
| **1 → 9**, exact Electrical and Electronic Equipment | §§2.3.3 and 7.1.9 identify standard-grade equivalent equipment. §§3.1.4–5 and 7.1.8 separate liability, service and other costs. | The explicit waiver in game 9 disables the 50% reduction. The combined line in game 1 had a positive bracket around €0.8k–€0.9k. Summing the two game-9 lines gives evidence from about €0.5k to €1.0k. Doubling the earlier range to undo the reduction would miss the observed sum. Our issuer inflated both times. The field moved from **2/5 to 18/21** confirmed inflated positive charges, with one unknown in game 9. The waiver provides a coverage change. It does not validate an amount transfer. |
| **8 → 10**, exact policy and clearance story | §5.2.1 covers debris and the single small root ball. Standalone ground removal stays outside §§5.2.1–2. The story says one haul and no reinstatement ground works. | Four debris positions became one four-piece line. Summed prior bounds are roughly **€71–€228**, compatible with the later positive bracket around **€157–€218**. Quoting the earlier sum of certified fair floors for both actions adds **€3,149–€3,219** in game 10. This leaves issuer headroom and misses two fair acceptances. The field stayed inflated-heavy, **38/44 to 8/10** confirmed, with one unknown in game 8. This is one episode of useful bounded transfer despite changed scope. |
| **3 → 11**, exact Accidental Damage and Optional Glazing, same accident pattern | Untaken glazing coverage excludes the pane and its ancillary work (§§2.7.3, 3.5 and 7.1.11). The first attendance follows covered work, while a return visit needs prior agreement (§7.1.12). | The covered furniture changed from cabinet repairs to a side table. Game 11 adds glass disposal, old scratches, a return visit and administration. The earlier cabinet repair floor would be too strong a price claim for a different object. On the simple repair lines **9/10** positive opponent charges were fair in game 3 and **9/10** in game 11. Neither first attendance had an observed positive fair charge. Covered work can still have a very small justified travel price. |

**[opened]** [Policy and story files](../../runs/bench/cases/) · [Family tests](scripts/rules.py) · [Earlier hypotheses about repeat cases](../raw4/fable-F-best-approach-review.md#24-cases-repeat-confirmed-with-a-warning)

## 5. What better teams did on the same lines

We were below the median active opponent on **17/44** lines, including 16 potentially payable lines. An active team either issued a positive charge or accepted a positive charge somewhere in that game. The comparison groups are selected by settled line net and describe behavior. They do not predict team identity. Percentages use known outcomes, with all-rejected positive charges counted as inflated but their amounts omitted from price ratios. Across the potentially payable weak lines:

| Metric | Opponent results above the median | At or below the median | Us |
|---|---:|---:|---:|
| Fair issuer charges / known positive | 29/67 | 16/73 | 4/16 |
| Median exact fair charge / best observed fair charge | 0.88 (29) | 0.53 (16) | — |
| Median known inflated charge / observed upper bound | 1.24 (37) | 1.80 (46) | — |
| Known inflated incoming accepted | 56/467 (12%) | 321/515 (62%) | 77/103 (75%) |
| Known fair incoming rejected | 37/162 (23%) | 85/194 (44%) | 12/45 (27%) |

Game 6 illustrates a team-specific miss within a fair-heavy field. All ten positive opposing charges were fair, while our fair charge was lower than the active median and our review paid a fair-rejection penalty. The accept-inflated difference replicated directionally on games 9–11 (**23/184 vs 121/200** after **33/283 vs 200/315** in training). The fair-rejection difference did not (**5/21 vs 2/27** in the holdout). Stronger results came from **clearing the issuer's fair-price threshold where feasible and rejecting costly inflation**. Simply rejecting more would have created penalties on fair laptops and the side table. On 22 excluded lines, 145/209 active opponent issuer-line actions were positive, and 37 issuer-line actions earned positive receipts. On the one excluded line where we trailed the active median (10.2), we collected zero and paid zero. The field shows a neutral/positive payments option under fixed opponents. It gives no evidence that a particular excluded-line quote generalizes. **[opened]** Supplied public settlement cache, in memory · [Aggregate calculations](scripts/account.py)

## 6. Ranked pre-submission rules and their replay

All changes use the documents and reader signals available before settlement. The analog rule additionally uses a previously released sibling. `m` is the gross conditional line median after quantity, VAT and explicit policy arithmetic. On games 1–10 the principal comparison always uses the same saved Luna configuration. In games without a saved median, the numeric rules make no modeled change. Their game-11 entry is zero by definition, which supplies no numeric-rule evidence. A documented exclusion can still be tested there using its clause. The table reports delta from actual net, with games 9 and 10 exposed in the forward column. The rules use cent-rounded prices.

| Rank · action | Games 1–8 delta | Games 9–11 delta | All 11 delta | Main risk and decision |
|---|---:|---:|---:|---|
| **1 · Tighter review only.** If (q ge 2/3), set (b=0.45m). Keep (a) fixed. | +€7,457 to +€7,559 | **+€15,659** | **+€23,116 to +€23,218** | Selected by the lower endpoint on a seven-factor training grid. Forward gains are +€13,289 and +€2,370. Leave-one-game-out training reselection gives +€1,484 to +€1,585 with four wins and four losses. The rule is sensitive to price input. With Fable it loses €0–€557 in game 10. Freeze for shadow scoring. |
| **2 · Tighter review, unchanged simple repairs.** Apply rule 1 only outside the narrow repair definition. | +€12,414 to +€12,516 | **+€15,659** | **+€28,073 to +€28,175** | Avoids the training penalties on laptop repairs. Leave-one-game-out picks 0.45 in all eight folds, but the split was proposed after game 9. There is no evaluated held-out repair median, so the forward gain comes entirely from the shared tight rule. Test as a separate arm. |
| **3 · Tighten both sides of other lines.** Set (a=0.55m, b=0.45m) outside the narrow repair class. | +€18,987 to +€21,934 | **+€17,953 to +€19,301** | **+€36,940 to +€41,235** | Published after game 9. Game 10 independently adds +€3,522 to +€3,627. A lower quote can forfeit issuer income near the true price or where permissive reviewers paid our old price. Game-4 lower bound is negative. Treat the issuer change separately. |
| **4 · Same-scope debris analogue.** For the same policy, covered material list and single haul, use the sum of earlier demonstrated fair floors as (a) and (b) for the matched grouped line. | No earlier match | **+€3,149 to +€3,219** | **+€3,149 to +€3,219** | One forward application, game 8 → 10. Conservative and leaves issuer revenue on the table. A new journey, different scope or allocation can break comparability. The analogous laptop amount transfer had a negative lower bound. |
| **Preserve · Documented exclusions use (b=0).** | €0 | €0 | **€0** | Replicates current effective decisions on all 22 documented exclusions. Misreading the schedule or the principal item would make rejection costly. Setting (a=b=0) changes realized net by **−€628** given this field. |
| **Reject · Escalate to Fable when Luna p90/p10 ≥4.** Both arms quote (a=0.80m, b=m) for valid review; (b=0) otherwise. | Escalation: +€13,263 to +€70,317 | Escalation: +€3,784 to +€9,910 | Escalation: +€17,047 to +€80,228 | Compared with the same Luna-only policy, game 9 helped by at least €591 and game 10 worsened by at least €3,249. Games 7 and 9 show why agreement or another call can miss a shared price error. |

**Would these have avoided games 7–9?** Under rule 1 with saved Luna medians, the review savings are about **€5.88k, €3.54k–€3.64k and €13.29k**. The resulting net is **+€1.75k, +€0.30k–€0.40k and +€4.42k**. With the actual live medians instead, (b=0.45m) gives **+€1.52k, −€0.83k and +€3.90k**. Tightening both sides outside simple repair with the actual medians puts game 8 at **+€0.03k–€0.97k**. Games 7 and 8 helped select the rules. Game 9 tests the tight review limit, and game 10 tests the post-game-9 issuer variant. A price-independent reject-all control gains **€22.4k–€22.6k** over the sample but creates **€5.5k** of additional cost across the four affected training games where it loses. The cost of tight review on fair-heavy lines matters more than the exact ranking of nearby multipliers. **[opened]** [Replay grid, exact candidate definitions and forward folds](scripts/rules.py) · [Previously published parameters](../raw4/fable-F-best-approach-review.md#53-rule-engine-starting-values)

## 7. What we already do well

- **Keep the exclusion review gate.** We paid no positive charge across 22 documented exclusions, including all 13 after game 8. The repeated glazing family, different surge ancillary lines and regrouped ground waste provide held-out checks. The trigger is the policy and the stated scope. A reused invoice noun alone will misclassify paid diagnostics or legitimate attendance.
- **Preserve the fair-price side on anchored or uncomplicated repairs.** All four laptop repair and damage-payment charges were fair in games 2, 5 and 6. Their coverage held across itemized and combined billing. The side table is a held-out fair repair charge. This protects the existing strength and leaves room to raise fair prices. Game 5 was reviewer-optimal and our best actual game. The bicycle repair 4.2 was about 97% of the highest demonstrated fair price on the issuer side, even though its review limit paid about €574 for inflated prices.
- **Keep roles separate.** In game 11 the side table earned nearly €2.8k in receipts but incurred €686 in extra fair-rejection payments. A line can deserve a higher review limit while its issuer price is already fair. Preserve the per-line accounting whenever a rule changes either role. **[opened]** [Own cases and settlements](../../past-cases/) · [Per-line euro ledger](#per-line-euro-ledger)

## Rejected or still unverified predictors

| Candidate | Disposition |
|---|---|
| Object work is cheap and ancillary work is expensive | **Rejected.** The original object class failed on both game-9 items. |
| Every `repair` keyword licenses a larger estimate or limit | **Rejected as written.** The frost fitting includes imaging, the facade has an optional-peril gate, and game 4 shares a rateable cap. The narrower class is still provisional. |
| Universal high review limit or universal low issuer quote | **Rejected as a default.** The price-error direction changes. A low cutoff burns fair-heavy laptop games, while a high cutoff paid inflated claims in games 7–10. |
| Two readers agree, so the amount is reliable | **Rejected.** Agreement missed the priced lines in games 7 and 9. Wide-band escalation failed in game 10. |
| An edition hash pins the amount | **Rejected.** Surge waiver and scope changes are material. Laptop exact transfer has a negative replay lower bound. Clearance has one compatible transfer. |
| Quantity >1, flat rate, optional-peril wording, trade name, bundle, small ticket, price anchor, or large case share alone sets a reliable multiplier | **Unverified.** The holdout is sparse and several signs reverse. Case share is more useful for exposure triage than directional calibration. |
| Image availability or deductible predicts price error | **Untestable here.** Availability is constant. No operative numeric deductible was established. |

### What I could not verify

- Exact expert thresholds, payment caps and clipped or all-rejected charge amounts. The supplied benchmark used a heuristic ceiling for a hidden charge, which can exclude real payouts. The audit evaluator bounds that expense by the candidate acceptance limit and retains uncertainty for an all-accepted maximum. The observed rows fit a cent charge grid and half-cent penalties. The platform's full precision contract remains unverified. **[opened]** [Audit](../raw5/gpt-G-evaluator-audit.md)
- Actual submitted medians, precise limits, timing and model identities for games 10–11, plus the two hidden game-10 issuer prices. Game 10's Luna answer is a saved offline read. Game 11 has no comparable answer. A replay measures fixed-field euros. It cannot verify future rank, reviewer adaptation, or one-minute delivery. The saved model responses are offline runs. The train/test split withholds game outcomes when fitting parameters, but does not prove the responses were generated before the round.
- The expert's item-level split of the bicycle aggregate cap, the precise attendance values on games 3 and 11, whether the replacement-electronics grades match between variants, and whether combining a bill preserves every component value. Scope calls are document interpretations, with public brackets used only to check outcome compatibility. Game 1’s diagnostic and attendance line has an unresolved invoice-context question under §7.1.8(d). Its recorded price and every observed positive competing price were inflated.
- A new independent family supporting the revised repair split, an independent component-price estimate for the frost case, and a paired game-9–11 photo or specialist experiment. Games 9, 10 and 11 each repeat a wording hash from training. All analyses are local to the supplied snapshot. **[opened]** [Cases](../../runs/bench/cases/) · [Training experiments](../bench/README.md) · [Prior reviews](../raw3/fable-E-first-principles-review.md) · [Independent replay review](../raw4/gpt-F-best-approach-review.md) · [Leaderboard notes](../03-leaderboard-findings.md)

## Per-line euro ledger

Each line's benchmark net is the actual net plus the displayed shortfall range. “Unclear paid” can contribute zero up to the amount shown. The replay includes cap uncertainty when it affects a candidate. Full policy hashes, raw rows and reviewer limits are not written here.

| Invoice position and scope | Actual net € | Below € | Inflated issuer € | Paid inflated € | Unclear paid € | Penalty € | Shortfall € |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1.1 Surge-damaged home electronics (speaker system and TV set) | -1,871 | 0 | 8,727–9,118 | 3,115 | 0 | 0 | 11,842–12,233 |
| 1.2 Diagnostic surge-failure report and technician call-out | 296 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2.1 Laptop screen crack repair | 2,137 | 5,306–5,710 | 0 | 0 | 0 | 1,357 | 6,663–7,067 |
| 2.2 Lower-right corner and housing repair | 1,613 | 1,706–1,877 | 0 | 0 | 0 | 332 | 2,038–2,209 |
| 2.3 Polish of pre-existing lid scuff (surface only, does not affect operation) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2.4 Diagnostic inspection | -289 | 0 | 698–728 | 169 | 0 | 0 | 867–897 |
| 3.1 Hole drilling | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3.2 Installation of the new glass into the frame | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3.3 Made-to-measure replacement glass pane | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3.4 Repair of dented and gouged solid-wood door frame | 785 | 2,696–2,860 | 0 | 0 | 0 | 592 | 3,288–3,452 |
| 3.5 Repair and refinish of scratched and chipped wooden shelf | 1,259 | 409–488 | 0 | 0 | 0 | 221 | 631–709 |
| 3.6 Vehicle costs | 151 | 0 | 0 | 28 | 0 | 0 | 28 |
| 4.1 Recover stolen bicycle from secured location, incl. locksmith call-out and cutting of seized lock | 145 | 0 | 0 | 333 | 0 | 0 | 333 |
| 4.2 Repair theft damage to bicycle (frame and brakes) | 2,136 | 111–225 | 0 | 574 | 0 | 0 | 685–798 |
| 4.3 Labour and sundries | 332 | 1,219 | 0 | 0 | 0 | 113 | 1,333 |
| 5.1 Laptop damage payment — cracked screen and lower- right-corner impact damage, thrown against car door during evasive turn | 7,562 | 5,095–5,678 | 0 | 0 | 0 | 0 | 5,095–5,678 |
| 6.1 Laptop accidental damage repair (cracked screen and lower-right corner), settled with supplier | 5 | 7,022–7,394 | 0 | 0 | 0 | 372 | 7,394–7,766 |
| 7.1 Internal frost-burst fitting repair including thermal- imaging leak detection | -4,137 | 0 | 3,192 | 5,883 | 0 | 0 | 9,075 |
| 7.2 Exterior facade frost damage repair (re-plaster and repaint) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 8.1 Disposal of shed roof timber removed from the damaged garden building | -1,223 | 0 | 0 | 1,155 | 68 | 0 | 1,155–1,223 |
| 8.2 Disposal of the broken glass pane from the damaged shed | -146 | 0 | 290 | 157 | 0 | 0 | 447 |
| 8.3 Disposal of green waste from the storm-felled tree (branches and foliage) | -1,063 | 0 | 193–213 | 1,301 | 0 | 0 | 1,493–1,514 |
| 8.4 Disposal of the tree root ball (single mass under one cubic metre) | -807 | 0 | 0 | 1,064 | 0 | 0 | 1,064 |
| 8.5 Disposal of sieved topsoil from the churned-up ground | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 8.6 Disposal of paving grit displaced around the shed | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 8.7 Disposal of excavated soil from the churned-up ground | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 9.1 Speaker system | -3,504 | 0 | 0 | 6,864 | 68 | 0 | 6,864–6,932 |
| 9.2 Shipping | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 9.3 Installation | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 9.4 TV set | -5,367 | 0 | 3,314–3,573 | 7,158 | 0 | 0 | 10,472–10,731 |
| 9.5 Property and liability damage to electronics | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 9.6 Property and liability damage to electronics - service order | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 9.7 Vehicle costs | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 10.1 Disposal of storm debris from the damaged shed and the felled tree (roof timber, broken glass pane, tree green waste and root ball under one cubic metre) | -2,792 | 0 | 1,957–2,035 | 2,511 | 0 | 0 | 4,468–4,546 |
| 10.2 Disposal of ground material from the churned-up area (excavated soil, sieved topsoil and displaced paving grit) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 11.1 Made-to-measure replacement glass pane | 246 | 0 | 0 | 0 | 0 | 0 | 0 |
| 11.2 Hole drilling | 43 | 0 | 0 | 0 | 0 | 0 | 0 |
| 11.3 Installation of the new glass into the frame | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 11.4 Disposal of broken glass | 43 | 0 | 0 | 0 | 0 | 0 | 0 |
| 11.5 Repair of dented solid-wood side table (knocked over in the same fall) | 668 | 839–956 | 0 | 0 | 0 | 686 | 1,525–1,643 |
| 11.6 Touch-up of pre-existing scratches on a second cabinet (present before the incident) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 11.7 Vehicle costs | 7 | 0 | 0 | 41 | 0 | 0 | 41 |
| 11.8 Vehicle costs – return visit | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 11.9 Administrative flat rate | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## 44-line feature table

C = potentially payable under the documents, including lines with no observed positive fair charge. X = document-supported exclusion. R = narrower repair rule, B = bundled scope, A = applicable story price anchor or comparison. Quantity is per piece unless marked flat. “Median · validity · share · spread” shows live median, (q), share of all estimated case amounts including excluded lines, and production log-spread parameter. Game 10 displays Luna for the first three values. The three saved medians and the justified quantities/fractions use Luna/Terra/Fable order. The live medians and saved-reader medians are distinct.

| Edition and trade | Applicable case facts, valuation basis and policy heads |
|---|---|
| 1, 9 · Electrical and Electronic Equipment; Electronics Retail, plus Building Services in 9.5–7 | §2.3.3 standard-grade appliances (§7.1.9), €5,000 event sub-limit and conditional halving. 1 lacks surge protection. 9 expressly has a waiver and itemizes shipping and fitting. §7.1.8 and §§3.1.4–5 exclude the separate unsupported cost heads. |
| 2, 6 · Portable Equipment, Repair and Replacement; Electronics Retail | §§2.6 and 7.1.10 repair or equivalent acquisition; 2.4 examination head §5.2.3, €250 gross cap. Game 2 anchors the combined repairs near the €1,400 purchase cost. In 6 the supplier receives settlement directly (§7.1.12). |
| 3, 11 · Accidental Damage and Optional Glazing; Building Services, plus Glazier 11.1–4 | §2.6 accidental damage to wood. §§2.7.3, 3.5 and 7.1.11 tie drilling, fitting and disposal to optional glazing. §7.1.12 covers one qualifying attendance and excludes the unauthorized extra visit. Game 11 names pre-existing work and general administration separately. |
| 4 · Mobility Equipment and Recovery; Bicycle Service | §§4.2.2, 5.2.2, 7.1.9–10. Recovery and repair share the €500 rateable mobility ceiling. Scope describes one recovered bicycle. No separately listed value. |
| 5 · Portable Equipment and Accidental Damage; Electronics Retail | €1,400 acquisition anchor. Combined impact damage, recent purchase, repair or equivalent replacement on the policy's stated basis. |
| 7 · Water Escape, External Surfaces and Site Charges; Plumbing and Painting | §§2.4.4, 2.4.6, 5.2.2 and 7.1.9 on the covered fitting and imaging. §§2.6 and 3.5 exclude external frost without optional agreement. €2,500 gross leak-location cap. |
| 8, 10 · Residential Dwelling Insurance, storm clearance wording; Recycling Service | §5.2.1 reimburses necessary clearance with a root ball at most 1 m³. §5.2.2 requires qualifying reinstatement for ground material. The story says one haul and no foundation work. Game 10 groups four eligible and three excluded categories into two positions. |

All cases supplied one photo and contain generic deductible wording without an established deductible amount. Game sizes follow the number of positions in each case. **[opened]** [Case text and invoices](../../runs/bench/cases/) · [Feature extraction and output](scripts/tables.py)

| Game.POS | Line type | Quantity | Scope | Flags | Median € · validity · share · spread | Saved gross medians € | Justified qty · fraction |
|---|---|---|:---:|---|---|---|---|
| 1.1 | goods | 2 | C | B | 3332 · 0.94 · 95% · 0.51 | 1071/714/952 | 2/2/2 · 0.5/0.5/0.5 |
| 1.2 | ancillary | 3 | X | B | 190 · 0.12 · 5% · 0.52 | 190/238/131 | 1/1/1 · 1/1/1 |
| 2.1 | repair | 1 | C | RA | 714 · 0.92 · 56% · 0.29 | 774/1056/891 | 1/1/1 · 1/1/1 |
| 2.2 | repair | 1 | C | RBA | 357 · 0.92 · 28% · 0.36 | 536/344/409 | 1/1/1 · 1/1/1 |
| 2.3 | repair | 1 | X | — | 54 · 0.00 · 4% · 0.54 | 60/48/54 | 1/1/1 · 1/1/1 |
| 2.4 | ancillary | 1 | C | — | 143 · 0.92 · 11% · 0.49 | 83/95/77 | 1/1/1 · 1/1/1 |
| 3.1 | ancillary | 1 | X | — | 42 · 0.10 · 6% · 0.63 | 48/54/30 | 1/1/1 · 1/1/1 |
| 3.2 | ancillary | 1 | X | — | 101 · 0.08 · 14% · 0.55 | 119/161/89 | 1/1/1 · 1/1/1 |
| 3.3 | goods | 1 | X | — | 143 · 0.08 · 19% · 0.57 | 190/226/155 | 1/1/1 · 1/1/1 |
| 3.4 | repair | 1 flat | C | R | 226 · 0.92 · 31% · 0.53 | 357/416/262 | 1/1/1 · 1/1/1 |
| 3.5 | repair | 1 flat | C | R | 167 · 0.85 · 23% · 0.54 | 214/262/178 | 1/1/1 · 1/1/1 |
| 3.6 | travel | 1 | C | — | 60 · 0.85 · 8% · 0.45 | 71/54/54 | 1/1/1 · 1/1/1 |
| 4.1 | bundle | 3 | C | B | 155 · 0.91 · 32% · 0.50 | 94/147/154 | 1/1/1 · 1/1/1 |
| 4.2 | repair | 2 | C | RB | 261 · 0.87 · 54% · 0.63 | 330/289/240 | 1/1/1 · 1/1/1 |
| 4.3 | repair | 1 flat | C | RB | 71 · 0.73 · 15% · 0.61 | 75/63/106 | 1/1/1 · 1/1/1 |
| 5.1 | repair | 1 | C | RBA | 1190 · 0.86 · 100% · 0.20 | 1400/1130/1297 | 1/1/1 · 1/1/1 |
| 6.1 | repair | 1 | C | RB | 500 · 0.88 · 100% · 0.42 | 595/476/571 | 1/1/1 · 1/1/1 |
| 7.1 | bundle | 1 flat | C | B | 952 · 0.93 · 17% · 0.49 | 1012/1130/1012 | 1/1/1 · 1/1/1 |
| 7.2 | repair | 1 flat | X | RB | 4522 · 0.06 · 83% · 0.51 | 2975/4284/4165 | 1/1/1 · 1/1/1 |
| 8.1 | disposal | 1 | C | — | 262 · 0.96 · 21% · 0.70 | 54/274/214 | 1/1/1 · 1/1/1 |
| 8.2 | disposal | 1 | C | — | 42 · 0.95 · 3% · 0.72 | 42/77/48 | 1/1/1 · 1/1/1 |
| 8.3 | disposal | 1 | C | B | 309 · 0.95 · 25% · 0.73 | 95/298/333 | 1/1/1 · 1/1/1 |
| 8.4 | disposal | 1 | C | — | 143 · 0.89 · 12% · 0.66 | 119/238/143 | 1/1/1 · 1/1/1 |
| 8.5 | disposal | 1 | X | — | 178 · 0.03 · 15% · 0.76 | 71/214/238 | 1/1/1 · 1/1/1 |
| 8.6 | disposal | 1 | X | — | 95 · 0.04 · 8% · 0.80 | 54/178/178 | 1/1/1 · 1/1/1 |
| 8.7 | disposal | 1 | X | — | 190 · 0.03 · 16% · 0.75 | 71/238/262 | 1/1/1 · 1/1/1 |
| 9.1 | goods | 1 | C | — | 952 · 0.94 · 35% · 0.69 | 1071/833/774 | 1/1/1 · 1/1/1 |
| 9.2 | ancillary | 1 | X | — | 60 · 0.02 · 2% · 0.64 | 48/48/48 | 1/1/1 · 1/1/1 |
| 9.3 | ancillary | 1 | X | — | 178 · 0.02 · 7% · 0.56 | 119/178/155 | 1/1/1 · 1/1/1 |
| 9.4 | goods | 1 | C | — | 1071 · 0.95 · 40% · 0.65 | 1190/833/1071 | 1/1/1 · 1/1/1 |
| 9.5 | bundle | 1 | X | B | 298 · 0.03 · 11% · 0.81 | 0/416/238 | 1/1/1 · 1/1/1 |
| 9.6 | ancillary | 1 | X | B | 89 · 0.02 · 3% · 0.74 | 0/95/119 | 1/1/1 · 1/1/1 |
| 9.7 | travel | 1 | X | — | 60 · 0.03 · 2% · 0.52 | 0/60/65 | 1/1/1 · 1/1/1 |
| 10.1 | disposal | 4 | C | B | 190 · 0.98 · 60% · — | 190/952/1238 | 4/4/4 · 1/1/1 |
| 10.2 | disposal | 3 | X | B | 125 · 0.02 · 40% · — | 125/643/1071 | 3/3/3 · 1/1/1 |
| 11.1 | goods | 1 | X | — | — | — | — |
| 11.2 | ancillary | 1 | X | — | — | — | — |
| 11.3 | ancillary | 1 | X | — | — | — | — |
| 11.4 | disposal | 1 | X | — | — | — | — |
| 11.5 | repair | 1 flat | C | R | — | — | — |
| 11.6 | other | 1 flat | X | — | — | — | — |
| 11.7 | travel | 1 | C | — | — | — | — |
| 11.8 | travel | 1 | X | — | — | — | — |
| 11.9 | ancillary | 1 flat | X | — | — | — | — |

Reproduce from the repo root with `python3 -B research/raw6/scripts/measure.py "$FIELD_DIR"` and `python3 -B research/raw6/scripts/rules.py "$FIELD_DIR"`. Use the supplied public cache outside the repository as `FIELD_DIR`. The scripts read locally and print own results and anonymous aggregates.
