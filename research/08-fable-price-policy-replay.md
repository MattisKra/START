# Game 24 · Fable's prices under the Python policy

The original Fable receipt contained a charge and an acceptance limit on each of 13 lines. It omitted the underlying fair-price estimate. All comparisons below use the same game 24 opponents and validated settlement field. Positive differences favour the changed policy.

| Comparison | Reviewer savings | Net improvement |
|---|---:|---:|
| Keep Fable's original charges and replace its positive limits with charge × 0.55 / 0.90, versus original Fable | €7,493–€12,070 | €7,493–€12,070 |
| Treat original Fable charges as the medians and apply both factors, versus original Fable | €7,540–€12,117 | €7,782–€17,469 |
| Fresh Fable estimates with both Python factors, versus the same fresh Fable's chosen actions | €6,848–€10,613 | €3,024–€15,201 |
| Fresh Fable estimates versus Python estimates, both with Python's policy | €1,073 | −€2,890 to +€7,041 |

The first comparison isolates reviewer strategy by holding issuer income fixed. In the second comparison, treating a strategic charge as the underlying estimate is a sensitivity assumption. The fresh retrospective run saw the released case documents. It supplied a conditional gross median and payable probability independently of the factors and produced all 13 lines at 19.28 s. For the frame it gave a €1,200 median and 75% payable probability, chose a €1,000 charge and €1,500 limit, and would have charged €1,080 and accepted up to €660 under the Python rule.

Fable had public web tools in the fresh run and used local document checks. One rerun of a known case cannot recover the original process or establish an overall estimator ranking. Games 25 and 26 add an independently timed, tool-enabled Fable shadow alongside the frozen arms.

[Replay implementation](bench/factor_replay.py) · [Shadow runner and scoring instructions](../claimbot_shadow/README.md)

## Which lines benefit?

Game 24 retrospective rerun, with the same Fable estimates on both sides. Ranges show the change in euros from replacing Fable’s strategy with Python’s factors. Reviewer savings and issuer income can move in opposite directions. The bounds allow for hidden opponent actions.

| Position and item | Reviewer savings | Issuer income change | Net change | Net winner |
|---|---:|---:|---:|---|
| 1. Bicycle shop · Bicycle frame replacement | 4,237.56 to 6,733.47 | −2,000.00 to 2,160.00 | 2,237.56 to 8,893.47 | Python factors |
| 2. Bicycle shop · Bicycle brake replacement | 1,092.88 to 1,312.88 | −891.00 to 1,164.00 | 201.88 to 2,476.88 | Python factors |
| 3. Bicycle shop · Shipping | 74.24 to 164.25 | −294.00 to 330.00 | −219.75 to 494.25 | Unresolved |
| 4. Bicycle shop · Vehicle costs | 162.02 to 384.03 | −88.50 to 33.00 | 73.52 to 417.03 | Python factors |
| 5. Bicycle shop · Assembly costs | −296.81 to −176.81 | 113.50 to 334.50 | −183.31 to 157.69 | Unresolved |
| 6. Bicycle shop · Miscellaneous items | 101.86 to 162.06 | −37.50 to 47.50 | 64.36 to 209.56 | Python factors |
| 7. Bicycle shop · Apprentice hours | 256.01 to 300.98 | −156.80 to 6.40 | 99.21 to 307.38 | Python factors |
| 8. Bicycle shop · Skilled worker hours | 361.53 to 539.60 | −181.00 to 21.00 | 180.53 to 560.60 | Python factors |
| 9. Locksmith · Vehicle costs | 259.18 to 319.18 | −112.50 to 189.50 | 146.68 to 508.68 | Python factors |
| 10. Locksmith · Assembly costs | −176.10 | 94.00 to 148.25 | −82.10 to −27.85 | Fable |
| 11. Locksmith · Miscellaneous items | 81.32 to 145.15 | −9.00 to 31.50 | 72.32 to 176.65 | Python factors |
| 12. Locksmith · Apprentice hours | 193.00 to 298.53 | −70.40 to 96.00 | 122.60 to 394.53 | Python factors |
| 13. Locksmith · Skilled worker hours | 500.81 to 605.81 | −190.50 to 26.00 | 310.31 to 631.81 | Python factors |

The frame and brakes account for at least €5,330 of reviewer savings. Both assembly lines favour Fable on review. On locksmith assembly the eligibility gate set the Python limit to €0 because Fable assigned a 60% probability of payability. Fable chose €90. The extra wrongful-rejection costs exceeded the issuer gain from charging €58.50 instead of €50. On bicycle assembly a 70% probability passed the gate, but the 0.55 multiplier still cut the limit from €120 to €49.50. This also increased reviewer costs. The two assembly examples share a direction within this invoice. A rule for other invoices needs forward evidence.

As a cross-check, the original game 24 receipt also favoured its two assembly limits under the fixed-charge ratio diagnostic. That diagnostic helped on all eleven other review lines. It does not require a reconstruction of the original Fable median.

## Forward check on game 25

The tool-enabled Fable arm recorded all 16 decisions during the official minute. Applying the frozen Python factors to those same estimates produced three clear net wins, one clear net loss and twelve unresolved lines. The original and changed strategies faced the same historical opponents.

| Position and item | Fable limit → factor limit | Reviewer savings from factors | Net change from factors |
|---|---:|---:|---:|
| 2. Connection hose | €40 → €15.40 | +€63.51 | +€97.31 to +€155.51 |
| 3. Senior installer, three hours | €340 → €156.75 | −€1,095.89 | −€1,001.64 to −€748.39 |
| 4. Auxiliary and cleaning material | €45 → €17.60 | +€77.39 to +€146.66 | +€52.39 to +€175.46 |
| 6. Thermal imaging camera for leak detection | €220 → €88 | +€440.13 to +€813.96 | +€64.13 to +€985.96 |

On the senior installer line, charging €256.50 instead of €250 gained €94.25–€347.50 in issuer income. The loss from tightening the reviewer limit outweighed even that upper bound. Fable also did better as reviewer on the filling valve, but the issuer uncertainty prevents a net verdict. The vehicle line is unresolved despite savings on review. Lines 7–16 have zero limits under both policies and uncertain issuer effects. The whole-game net interval spans zero.

Taken with game 24, similar labour labels led to opposite results. The payoff depends on whether the reduced limit crosses fair or inflated opponent charges. Historical winners can diagnose which assumption to check in a future game. Line labels alone do not establish a switching rule.
