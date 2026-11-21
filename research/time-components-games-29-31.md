# Did separating technician hours from equipment days help? Games 29–31

**The only payable line with an explicit hours calculation lost €30.** On game 29’s emergency door repair, the time check raised Fable’s issuer charge from €380 to €450 and its reviewer limit from €800 to €1,000. The charge change cost €30. The limit change had zero effect. Two of three games produced paired decisions. Neither priced equipment-days, and the whole-invoice net result remains unresolved.

## Paired payoff and availability

Amounts are euros from the time-check arm’s perspective. Positive reviewer savings mean it paid less. Issuer change measures the difference in income against the same opponents. The bounds allow for hidden charges and limits consistent with the settlements. Both the 54-second primary cutoff and the 60-second final cutoff selected the same receipts in every scored game, so every interval below applies to both.

| Game | Standard first → final (s) | Time check first → final (s) | Reviewer savings (€) | Issuer change (€) | Net change (€) | Predefined time slice at both cutoffs |
|---|---:|---:|---:|---:|---:|---|
| 29 | 16.12 → 16.12 | 15.78 → 15.78 | −5,000 to 0 | −36,330 to +41,220 | −41,330 to +41,220 | No matching lines |
| 30 | No receipt | No receipt | Unscored | Unscored | Unscored | No paired actions |
| 31 | 19.30 → 19.30 | 18.83 → 34.55 | 0 | −45,050 to +44,200 | −45,050 to +44,200 | No matching lines |
| **Two paired games** | | | **−5,000 to 0** | **−81,380 to +85,420** | **−86,380 to +85,420** | **No estimable interval** |

The slice used the frozen invoice-description and unit rule. The game 29 door repair was billed by the piece. The game 31 translation was billed by the line. Neither matched the rule. On the missed game 30 invoice, the rule identifies position 1, electrician labour, billed at 12 hours. The case also describes a submersible pump, but supplies no rental duration. A dash in the unit column of position 9 (boiler disposal) stopped preparation before either Fable session started. The later parser fix recovered all ten printed positions. Game 30 stays a miss in this experiment. [Game 30 invoice](../past-cases/case_030/invoice.txt) · [Case description](../past-cases/case_030/description.txt)

## What the two calculations meant

| Game / line | Standard Fable’s stated basis | Time check’s gross arithmetic | Effect on settled payoff |
|---|---|---|---|
| 29 / 2 · Door repair | Named emergency call-out, boarding and lock work and gave a bundled €500 estimate. It supplied no hours or rates. | 2.5 inferred locksmith/joiner hours × €100 + €300 materials and call-out = **€550**. Equipment array empty. Payability rose from 90% to 92%. | **−€30 issuer, €0 reviewer, −€30 net.** |
| 31 / 1 · Translation | Independently calculated 68 invoice lines × about €1.85 net × 1.19 VAT ≈ **€150** if payable. | 68 lines × €2 gross = **€136**. The labour field expressed this as 1.1 inferred hours × €123.64 = €136.004, which rounds to €136. Equipment array empty. | **€0 in both roles.** Both arms excluded the translation and set charge and limit to zero. |

The door calculation makes an assumption inspectable. The case confirms a tradesperson re-secured the forced door but gives no attendance or tariff that validates 2.5 hours at €100. For translation, both arms used the invoiced quantity without prompting the control. Converting a per-line price to hours supplied a second way to write the amount. No additional evidence of time spent appeared in the treatment’s rationale. All reported breakdowns reconciled, including the repeated translation breakdown on the final receipt. The four other paired positions declared time components inapplicable. [Game 29 case](../past-cases/case_029/description.txt) · [Game 31 invoice](../past-cases/case_031/invoice.txt)

## Why the whole-game bounds are wide

- **Game 29, stolen contents.** With no time component in either rationale, the conditional median rose from €3,000 to €3,500. The charge rose from €2,200 to €2,500 and the limit from €4,500 to €5,000. Both arms gave 85% payability. This line accounted for all reviewer uncertainty (−€5,000 to €0) and −€36,300 to +€41,250 of issuer change. Only the exact €30 issuer loss on the door repair can be localized to a line with a substantive labour breakdown.
- **Game 31, stolen watch and cash.** The control spontaneously added the €2,500 watch and €500 cash sub-limits, setting both charge and limit to €3,000. The treatment initially estimated €3,000 and charged €2,900. After a policy read it cited the €50 deductible, revised its median and charge to €2,950, and kept its €3,000 limit. That final €50 charge difference versus control accounts for the entire −€45,050 to +€44,200 issuer interval and €0 reviewer change. Those conservative replay bounds do not establish a gain or loss from the deductible. Materials and shipping stayed at zero charge and limit in both arms. [Game 31 policy, §7.8](../past-cases/case_031/policy.txt#L592)

The manifest froze at 19:12:12.980 UTC on 21 November, before releases at 19:13:20, 19:26:40 and 19:40:00 UTC. The source hashes and prompts match commit `82b6ff6`. Game 29 reused the standard Fable control from the concurrent policy-first experiment. Game 31 ran both arms on the same release. For both scored games, the released archive hashes, game IDs, release times and printed positions reconciled across arms. All five complete receipts matched successful writes. Each arm’s last receipt matched its stored final decision. Re-running the read-only settlement scorer reproduced both score files byte for byte. Across six paired positions there was one substantive payable labour estimate, one excluded service expressed in hours, and zero equipment-day estimates. These separate model sessions and the empty predefined slice leave the benefit of separating labour from equipment time unestablished. [Frozen treatment](../claimbot_shadow/time_components.py) · [Settlement scorer](bench/score_time_components.py)
