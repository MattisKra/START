# Does requiring a policy read before pricing help Fable?

Three prospective games compared standard Fable with the same model, tools and case plus a requirement to read policy text and quote a numbered clause on a material line. Both arms produced complete decisions on all seven printed positions by 54 seconds. The treatment gained €972.50–€3,817.50 in game 27, lost exactly €30 in game 29, and left the net result open in game 28. The three-game net difference spans −€19,831 to +€5,614. In game 28 it cited a real provision about quantity but missed the exclusion that decided whether anything was payable.

## What Fable consulted

The manifest froze at 18:42:59.54 UTC on 21 November, before game 27. Games 27–28 reused the standard Fable sessions from the concurrent hybrid shadow. Game 29 ran both arms together. Times are local seconds after official release. Every control search completed successfully in content mode. The trace retains the query and completion time. The decision evidence shows which provisions the model said it used. A direct Read opened a range of lines in the policy. The recorder verified the treatment quote against the clause body and the prior Read result.

| Game | Control policy search / first direct Read | Control decision receipts | Treatment first direct Read / Read supplying quote | Treatment receipt | Extra time to first decision |
|---|---|---|---|---:|---:|
| 27 | 6.89 / 16.38 | 15.13 | 7.22 / 8.75 | 23.93 | +8.81 s |
| 28 | 8.96 / 17.84 | 16.33, 24.72 | 9.08 / 9.08 | 18.92 | +2.59 s |
| 29 | 8.93 / 17.31 | 16.12 | 7.90 / 11.87 | 26.14 | +10.01 s |

Every control voluntarily searched policy contents before its first write. All three completed their first direct policy Read after that write. Game 28’s control searched with two lines of surrounding context, inspected the photo before pricing and later read the exclusion directly. Its revision lowered payability from 12% to 7% and retained a zero charge and limit. The treatment did not open that photo. All seven decision receipts across both arms passed the mechanical checks. There were no rejected writes, missing positions or deadline misses. The median additional time to a first receipt was 8.81 seconds.

## Did the quoted clause resolve the line?

- **27, position 1 · Leak detection.** Clause 7.1.7(e) includes “the investigation necessary to locate and identify the source of the damage”. It applies to finding the concealed pinhole and mapping moisture. Both arms cited this provision and allowed the two technicians’ seven-hour visit. The treatment estimated €1,200 gross with a stated hourly rate and call-out. The control estimated €1,100. Raising the charge from €900 to €1,000 gained €2,450–€3,400 in issuer income. Raising the reviewer limit from €1,250 to €1,500 changed reviewer cost by €0. The block’s favourable game therefore has a pricing explanation without a coverage reversal.
- **28, position 1 · Kitchen air conditioner.** Clause 2.3.3 says “an installation that the event did not damage is not brought within the indemnity by the fact that a neighbouring installation was damaged”. This supports excluding two extra units on the invoice. The treatment priced the remaining unit at €2,600 gross and set a €2,900 limit. Clause 2.3.10(c) separately excludes lightning-overvoltage damage to climate equipment within five metres of a cooking appliance, unless the kitchen climate endorsement applies. The case explicitly put the unit close to the hob and specified no endorsements. The control found the exclusion in its search and priced the whole line at zero. The treatment’s three direct Read ranges omitted the exclusion. Against the actual field the zero limit rightly rejected all nine positive incoming charges. Its higher limit cost €473.50–€20,773.50 on review. The issuer effect leaves the net result open.
- **29, position 2 · Emergency door securing.** Clause 5.2.2 says “indemnity under this head is capped at EUR 1,000 including value added tax per insured event”. Restoring a forced door to a lockable condition fits the emergency-securing head. The ceiling establishes the maximum reimbursement. The value of the work still requires a price estimate. Both arms treated the door repair as 90% payable. The treatment raised the charge from €380 to €450 and set the limit to the €1,000 ceiling. On stolen contents it disputed the control’s per-article cap for ordinary clothing and everyday jewellery, but kept the same €3,000 median, charge and limit.

## All final decisions

Amounts are gross euros for the entire printed line. Each cell shows standard Fable → policy-first Fable. Payability is the model’s stated probability.

| Game / position | Payability | Median if payable | Issuer charge | Reviewer limit |
|---|---:|---:|---:|---:|
| 27 / 1 · Leak detection | 92% → 93% | 1,100 → 1,200 | 900 → 1,000 | 1,250 → 1,500 |
| 27 / 2 · Pipe repair | 90% → 93% | 520 → 440 | 420 → 380 | 620 → 600 |
| 27 / 3 · Vehicle | 85% → 85% | 65 → 55 | 50 → 45 | 85 → 85 |
| 27 / 4 · Drying | 92% → 93% | 480 → 400 | 380 → 330 | 600 → 560 |
| 28 / 1 · Air conditioner | 7% → 85% | 2,800 → 2,600 | 0 → 2,300 | 0 → 2,900 |
| 29 / 1 · Stolen contents | 85% → 82% | 3,000 → 3,000 | 2,200 → 2,200 | 4,500 → 4,500 |
| 29 / 2 · Door securing | 90% → 90% | 500 → 550 | 380 → 450 | 800 → 1,000 |

## Fixed-field payoff

Positive values favour policy-first Fable. Reviewer savings plus issuer income change give the net interval. Opponents keep their observed actions. The scorer bounds hidden actions compatible with the settlements. For each game, the first complete pair, the last pair by 54 seconds (primary), and the last pair by 60 seconds have identical prices. The same euro bounds apply at all three checkpoints.

| Game | Reviewer savings (€) | Issuer change (€) | Net change (€) |
|---|---:|---:|---:|
| 27 | 0 to +620.00 | +972.50 to +3,197.50 | +972.50 to +3,817.50 |
| 28 | −20,773.50 to −473.50 | 0 to +2,300.00 | −20,773.50 to +1,826.50 |
| 29 | 0 | −30.00 | −30.00 |
| **Games 27–29** | **−20,773.50 to +146.50** | **+942.50 to +5,467.50** | **−19,831.00 to +5,614.00** |

In game 29 the entire €30 loss came from raising the issuer charge for door securing. The higher reviewer limit cost exactly the same against this field. Across the block, the issuer side improved even at its lower bound, while the reviewer and net intervals both include zero.

The gate verified that Fable consulted and cited a real provision before writing. The comparison measures the full mandatory-read-and-citation prompt, including time, search choices and variation between separate model sessions. All controls used the policy voluntarily. Game 28 demonstrates that verifying one quotation can still leave the controlling exclusion undiscovered. This block does not establish a net benefit from enforcing the gate.

The audit matched the frozen gate hash, released archive hashes, printed position sets, tool order, accepted writes and final receipts. It checked each quoted passage against the original case policy. The read-only scorer reconciled the historical field to the standings. [Game 27 policy](../past-cases/case_027/policy.txt) · [Game 28 policy](../past-cases/case_028/policy.txt) · [Game 28 case description](../past-cases/case_028/description.txt) · [Game 29 policy](../past-cases/case_029/policy.txt) · [Payoff scorer](bench/score_policy_first.py)
