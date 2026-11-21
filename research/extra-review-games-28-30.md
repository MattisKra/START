# Did extra Fable reviews change the decision? Games 28–30

**Extra review changed no charge, limit, fair-price estimate or payable probability.** Two of three scheduled games produced initial decisions. The three follow-up attempts yielded one verified keep and two rejected writes. Neither rejection was late. Game 30 failed before Fable started and contributes no payoff observation.

The manifest froze at 18:53:39.777 UTC on 21 November 2026, before the 19:00, 19:13:20 and 19:26:40 UTC releases. Each game allowed one policy-first Fable session, with up to two follow-ups on distinct positions ordered by the larger of charge and limit. A pass had to start before 54 seconds and obtain fresh source evidence before writing. Source hashes match the implementation in commit `2348f78`. For the two played games, archive digests and printed positions match, all turn results have the same session ID within each game, and the last accepted trace receipt matches the stored final decision.

## Receipts and settlement

Times are seconds from release. The primary comparison takes the last complete initial-turn decision by 54 seconds and compares it with the last complete decision by that same cutoff, holding opponents fixed. Repeating the comparison at 60 seconds selected the same receipts. Exact euro values below have identical lower and upper bounds. Model costs are separate.

| Game | Initial → final receipt at both cutoffs | Extra reviews | Reviewer savings | Issuer income change | Net change |
|---|---|---|---:|---:|---:|
| 28 | 24.14 → 24.14 s | One rejected write | €0 | €0 | €0 |
| 29 | 21.01 → 35.43 s | One accepted keep, then one rejected write | €0 | €0 | €0 |
| 30 | No initial or final receipt | Preparation failed | Unscored | Unscored | Unscored |
| **Paired total, 2 games** | **54 s and 60 s** | **Zero numerical revisions** | **€0** | **€0** | **€0** |

| Game / pass | Assigned position | Start | Write requested → decision or rejection | Turn result | Increment versus preceding accepted decision |
|---|---|---:|---:|---:|---|
| 28 / 1 | 1 · Kitchen air conditioner | 30.46 | 35.71 → 35.73 | 39.44 | Rejected. Original decision retained, €0 in each role and net. |
| 29 / 1 | 1 · Stolen household contents | 27.03 | 35.42 → 35.43 | 39.71 | Accepted keep, €0 in each role and net. |
| 29 / 2 | 2 · Emergency door securing | 39.71 | 43.84 → 43.87 | 47.23 | Rejected. Preceding decision retained, €0 in each role and net. |

**Game 28.** The initial write began at 24.12 s and was accepted at 24.14 s. Fable priced one of three invoiced units under the like-for-like replacement clause, §7.1.9. It estimated €2,600 gross conditional on coverage, gave coverage 85%, charged €2,300 and set a €3,000 limit. The description placed the unit close to the hob with no endorsement. The initial rationale missed the kitchen exclusion in §2.3.10(c). The follow-up’s only tool call was its write. The recorder rejected it for lacking a fresh source check and the session exited at 39.90 s. The rejected patch contents were not retained, so its intended numbers and reason are unknown. [Case description](../past-cases/case_028/description.txt) · [Policy](../past-cases/case_028/policy.txt)

**Game 29.** The initial write began at 20.98 s and was accepted at 21.01 s for both positions. On contents, Fable kept the €1,800 charge, €4,500 limit, €2,800 conditional median and 75% payability. Its new policy search on co-insurance and itemisation completed at 30.47 s, before the keep write. It cited the everyday-apparel and modest-jewellery provisions (§§4.4.5–6), saw no schedule confirming co-insurance and still had no item values or quote. The wording supports the everyday-item exceptions and the conditional per-article rule in §9.6. A separate duty in §9.2.2 requires an itemised list for removed property. The case records police notification but does not establish whether that list was supplied. The search establishes access. Neither the keep nor its zero incremental payoff establishes the accuracy of €4,500 or 75%. On door securing, the initial €550 charge, €1,000 limit, €750 conditional median and 90% payability persisted. The second follow-up called only Write, with no fresh source check. Its intended change and reason are unknown. The session exited at 47.70 s. [Case description](../past-cases/case_029/description.txt) · [Policy](../past-cases/case_029/policy.txt)

**Game 30.** The invoice parser rejected the printed dash in the unit column of position 9, disposal of the old boiler. There was no model session, usage record, initial decision or review. The later parser fix was verified against all ten positions and was not used to replay this frozen game. [Invoice](../past-cases/case_030/invoice.txt)

## Model-reported usage

Tokens are per-turn CLI reports. Cost is the change in the reported cumulative session cost, shown in US dollars. No turn reported a web search or web fetch.

| Game / turn | Input | Cache write | Cache read | Output | Incremental cost |
|---|---:|---:|---:|---:|---:|
| 28 initial | 8 | 12,095 | 49,706 | 2,741 | $0.31317 |
| 28 review 1 | 6 | 1,414 | 40,890 | 724 | $0.05981 |
| 29 initial | 8 | 15,227 | 52,959 | 2,629 | $0.35945 |
| 29 review 1 | 8 | 1,875 | 71,678 | 1,036 | $0.08584 |
| 29 review 2 | 6 | 1,145 | 50,714 | 692 | $0.05619 |
| **Extra turns only** | **20** | **4,434** | **163,282** | **2,452** | **$0.20184** |

The extra turns occupied 29.18 seconds in total across the two sessions, measured from each pass start to its model result. Both rejected writes arrived with time left. Fresh evidence and a usable review receipt were the limiting steps in those attempts. With one accepted keep and no accepted revision, this block supplies no evidence to adopt extra turns in live play. [Shadow protocol](../claimbot_shadow/README.md) · [Settlement scorer](bench/score_review_turns.py)
