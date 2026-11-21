# Adversarial audit of the Claim to Fame euro replay

## Verdict

**No-go as the sole live policy selector.** The shipped evaluator can exclude the true payoff from either end of its range with two teams, one line and whole-euro inputs. Its largest accepted-payment inference can erase a fair-charge penalty. Its hidden-charge ceiling can print a lower bound hundreds or thousands of euros above a feasible result. It also drops omitted lines even though the platform settles them at the defaults. The label “worst case consistent with the data” is false.

| Use | Trust level |
|---|---|
| Reconcile realized historical net from complete public rows | **High for this snapshot.** All 120 team-game totals reconcile to the organizer's matrix. |
| Bound a fixed policy on a past field | **Unsafe as shipped.** The tested core patch fixes the identified logic failures on exact settlements with cent-grid charges. Verify that money contract and validate each input before using the bounds. |
| Shortlist candidates on games 1–8 | **Exploratory.** The arithmetic patch preserves several positive historical lower deltas. Shape, ranking and time-to-submit still need separate evidence. |
| Choose the live winner, infer future euros or claim tournament rank | **Unsupported.** No independent future-game test, representative repeat draws or counterfactual opponent standings. |

**Observed.** With every Kiebler transaction withheld from reconstruction, the nine logged games are covered, but the median range widens to **€4,663.48** and game 7 alone spans **€61,662.74**. On 42,000 rule-exact adversarial candidate trials, the shipped code misses **936** times, including **30** above its upper endpoint. The worst miss is **€14,588**. The core patch has **0/42,000** misses in that experiment. It still certifies only **24.8%** of strict candidate-pair orders using disjoint intervals. A separate legal sub-cent example still breaks the core patch.

**Decision standard.** Treat realized row sums as accounting and repaired ranges as conditional historical bounds. Require complete matched inputs, a verified precision contract and a frozen forward comparison before promoting a live policy. Use a paired difference on the same feasible field to choose between historical candidates. Larger lower endpoints alone do not establish which policy earned more.

---

## Ranked findings

### CRITICAL — wrong counterfactual answers

**C1. The largest accepted payment is not evidence of inflation.** At [reconstruct, lines 49–59](../bench/euro_replay.py#L49), `x >= c_lo` means equality. The top observed payment contributes to `c_lo` by construction. There may be an uncapped world with `a=x≤t` and `c≥4x`. The code erases that world twice. It lowers `U` for every candidate charge, and its possibly clipped cost branch incorrectly prices certain rejection at zero. This can create false assurances in either direction. None of the 420 full-field issuer-line groups or the held-out groups had this trigger without an actual rejection in this snapshot, so this bug did not change the displayed historical sweep. It did change valid synthetic replays, including the two minimal examples below.

**C2. The hidden-charge ceiling has the wrong justification and no upper-bound proof.** At [line 121](../bench/euro_replay.py#L116), `4*max(U or L, floor, 1)` extrapolates a potential cap from threshold clues. The rule supplies a **lower** bound on the cap. The actual cap can exceed the heuristic by any factor. The historical reviewer-limit floor only bounds the hidden charge from below. For a finite candidate limit `b'`, hidden-charge cost is zero on rejection and at most `b'` on acceptance. In the minimal test, a €500 cost becomes at most €4 in the code. On the historical sweep, the heuristic was *too pessimistic* in all 65 activated pair-policy evaluations, counting repeated candidate invocations. Its replacement raises the luna default lower delta by €8,620.75 and changes luna 0.8/1.0 from −€1,863.03 to +€2,972.90. This direction in the snapshot supplies no guarantee for future fields or higher limits.

**C3. Missing policies and missing data quietly change the quantity being scored.** [game_value](../bench/euro_replay.py#L137) iterates candidate keys, silently skips unknown keys and omits the consequences of default reviews. An omitted line with one fair €10 charge costs €15 at `b'=0`. The function returns zero for an entirely empty policy. Missing field rows similarly shrink the opponent and line universe, even if the actual benchmark includes those flows. [fetch_field](../raw4/scripts/fetch_field.py#L45) writes a cache after a failed page, overwrites duplicate keys, and skips existing files indefinitely. The cache cannot reveal disagreements that were overwritten. The audited snapshot is complete. Candidate and field line keys also match in the reproduced sweep. A two-team holdout leaves no rows and cannot use the current interface to recover either the line or the opponent roster.

**C4. Undocumented quantization can flip a categorical decision by a large amount.** [reconstruct](../bench/euro_replay.py#L39) rounds `y/1.5` to cents. The handbook accepts finite nonnegative amounts and does not specify a cent grid or settlement rounding. An actual fair charge €99.996 is accepted by a €99.997 limit. Even from a precise €149.994 historical penalty the code reconstructs €100 and pays a €150 penalty. True cost €99.996 differs by €50.004. A cent-rounded row can flip the decision in the opposite direction. Final-output tolerances cannot repair either changed branch. The observed data support a cent-grid model for this snapshot, with exact half-cent penalty values up to serialization noise. They do not prove the platform contract.

### MAJOR — numbers or conclusions the code cannot support

**M1. Exact historical replay reuses the outcomes it claims to predict.** Our historical charge acceptance/rejection tightens all opposing `B` intervals at the same price being replayed. Our historical reviews expose cost states and our logged limit rules out many hidden costs by construction. A match is a useful reconciliation test. It carries little power to test a different `(a,b)`. The independent outcome holdout below measures how well the rest of the field bounds the same recorded policy. It still does not test a future case or a newly drawn reader response.

**M2. The conservative sum of pair endpoints can be far outside the feasible set, even with the logic repaired.** The per-pair construction lets different pairs use conflicting values of shared `t`, `c`, issuer charges and reviewer limits. A demonstrated two-team state has core range [−€150, €150] and true feasible extremes [−€50, €100]. Historically large positive upper deltas can arise from loose upper reviewer limits and cap ceilings. Minima of different pairs need not coexist either. Call a repaired lower endpoint a *conservative historical lower bound*. The current endpoint additionally has the unsoundness in C1–C4.

**M3. The sweep is a conditional historical comparison of saved responses.** [arch_bench.load_saved](../bench/arch_bench.py#L37) uses lexicographic file order and overwrites each reader-case entry. The script selects an intersection of available data, derives a single answer per reader-case and tunes among candidates on the same games. Early games shaped the prompt. Data absence changes the cohort, and an environment-dependent `Params()` can change the named “defaults” and parameters omitted in the sweep. The live tiering, response failures, latency, overruns and last-write behavior are not simulated. The 19 candidate invocations include a duplicate configuration, plus the live baseline is a separate invocation. Repeated lookups or lines give no new independent games.

**M4. The scorecard does not evaluate tournament rank.** Official points scale with rank on cumulative net. Changing our charge or limit changes opponents' balances as well as ours. Synthetic example: start with nets `(us,X,Y)=(0,7,-7)`. On two excluded lines, only X accepts €4 on the first and only Y accepts €6 on the second. Opponent charges are zero. Billing only the first gives `(4,3,-7)` and first place. Billing only the second gives `(6,7,-13)` and second place. Greater own net can buy a worse rank across candidate policies. Jointly bound head-to-head margins after updating both sides of each transfer if claiming rank effects. The source has no provision for a euro-to-points conversion independent of opponents.

**M5. Unpinned input and import behavior weaken reproducibility.** [euro_eval.py](../bench/euro_eval.py#L14) imports `arch_bench`, which imports [bench.py](../bench/bench.py#L33) and loads `.env` at import time. I ran the exact candidate sweep and saved-answer selector with those imports bypassed, using the real engine and saved answers. The offline evaluator has no need for credentials. Its candidate mapping also assumes `reader index + 1`; the live runner uses printed POS numbers. I verified printed positions from the layout-preserving PDFs for games 1–9 and equality with the replay's field/log index sets. All were sequential. A missing or shifted reader line on another invoice can silently move or overwrite submissions. Use the same strict position mapping as the live path and reject ambiguous matches.

### MINOR — diagnostics and wording

- The original CLI says ACTUAL is “surely better” in 4/8 games and “surely worse” in 2, because it compares float endpoints with row sums using strict signs at zero. Its true delta to itself is exactly zero. Compare in exact units and display this identity explicitly. Full-row game 3 displays €2,195.39 vs €2,195.40 due to floating-point formatting of the half-cent total. Raw values reconcile up to representation noise.
- The synthetic checker accepts up to €1 outside an interval and prints the median width again under “median |true net| scale.” Its €0.01 diagnostic is narrower, but it does not enter the pass count. Neither threshold proves a rounding cause. Print strict exceedances, serialization allowances, absolute gaps and an actual net-magnitude statistic separately.
- “Identified share” counts pairs with point-like outcomes under interval logic. It misses some point payoffs when the acceptance branch is unknown but both branches pay the same amount, and can count erroneous points from a false status. One unpriced pair can dominate a game. It says nothing about width in euros or the probability of an outcome. The same heuristic is used inside the claim that the output “never uses point guesses.”
- The engine's `max_a_over_median` caps our charge against a **reader estimate**, so the comment “the secret cap ... cannot bite” is false. The rule compares the cap with expert `t`. Charging a positive amount instead of zero at a fixed `b` cannot reduce own historical euro net through the issuer payoff. This weak dominance is an algebraic fact for the fixed-opponent scenario. It does not establish a positive gain, accurate exclusion, behavior under adaptation or the jury's method score. The replay's displayed lower endpoints differed by €152.32 even before repair.

## Rule derivation and edge cases

In this section, **PROVEN** means a deduction for rule-conforming rows, nonnegative inputs and exact monetary comparisons. **ASSUMPTION** means an input or evidence condition. **HEURISTIC** means an unproved choice in the implementation. These are deterministic constraints; none is a statistical confidence interval. [opened: authoritative payoff and cap rules](../../materials/GAME_DESCRIPTION.md#L48) · [opened: API defaults, last write, value domain](../../materials/API_HANDBOOK.md#L39)

| Code or observation | Verdict and derivation |
|---|---|
| One charge per issuer and one limit per reviewer, shared cap, fixed opponents | **ASSUMPTION** about supplied data or the counterfactual. The rules justify the first three for a complete real game. Holding behavior fixed in a different game or after a live policy change is an extra restriction. A valid unilateral replay on a closed game changes only transfers involving us. |
| Rejected `y>0` | **PROVEN** with exact settlement amounts: `a=2y/3>0`, `a≤t` and `b<a`. Fair includes `a=t`. Any same-issuer acceptance must pay `a`, as `c≥4t≥a`. Another rejected row cannot pay zero for this issuer-line. The rounding in code is an **ASSUMPTION** about the input grid. |
| Accepted `y=0` | **PROVEN** if exact `y` and `c>0`: `a=0`. Nonnegative `b) then makes every row for that issuer accepted, including `b=0`. Display rounding of a positive micropayment can destroy the inference. |
| Rejected `y=0` | **PROVEN** with exact payments: rejection implies `a>b≥0`, so fair payment would be positive. Therefore `a>t`. If all observed rows reject, the charge can exceed every observed rejecting limit and `t`, with no finite upper bound from these observations alone. A rounded zero penalty can make the inference fail. |
| Accepted `x>0`, no positive rejection | **PROVEN**: `a≥x`, `c≥x`. If `x<c_lo`, then `a=x` exactly. If `x=c_lo`, possibilities include an uncapped `a=x`, the exact tie `a=c=x`, and a clipped `a>c=x`. For `c=x>0`, both the cap tie and clipping are inflated since `t≤x/4`. Without evidence that `c=x), labeling the maximum inflated is an invalid inference. A separate zero rejection does imply `t<x`: if `a=x` use the rejected row, otherwise `x=c≥4t` and `x>0`. Charges everybody accepts can still be classified when independent constraints establish their status. |
| `L` and `U` | **PROVEN**: each identified fair charge gives `t≥a`. Each exact inflated charge gives `t<a`. For an accepted positive payment with a zero rejection, `t<x` also holds as above. Take the maximum lower and minimum upper constraint, defaulting to 0 and infinity. `U` is the lowest *proven upper bound*, which need not be the actual lowest inflated charge. A fully hidden charge contributes no direct finite upper bound. No fair observations means `L=0`, with `t` still unknown. Contradictions such as `L≥U` must fail validation. |
| `c_lo=max(4L,max accepted payments)` | **PROVEN** under exact observations. The absolute floor may tighten this if its value is documented. The authoritative source does not provide its value. A line with `t=0` can have positive accepted payments and a positive cap. Since `c≥c_lo`, accepted candidate `a'` pays in `[min(a',c_lo),a']`; it pays in full if `a'≤c_lo`, including equality. This does not reveal gross submitted amounts at the cap. |
| `B[j]=[lo,hi)` | **PROVEN outer interval**: an accepted exact price gives `b_j≥a`; an accepted clipped-or-exact amount gives the weaker `b_j≥x`. Rejected exact price gives `b_j<a`, strictly. A rejected lower bound on an unknown charge cannot give an upper bound on `b_j`. Ties `a=b` accept and `b=hi` is excluded. Two equal actual charges cannot receive different flags from the same reviewer. Coincident capped payment amounts need not be equal charges. The code takes extrema without checking whether the interval or wider constraint system is empty. |
| Historical own `a,b` | **ASSUMPTION** that logs are the final accepted API payload using the correct line keys, with no late overwrite. An inflated hidden own charge can be revealed by a verified own log. Applying `a` only when wholly hidden leaves useful constraints on other own rows unused. A hidden opponent charge exceeds `our_b` **only if** our row actually rejected it. Pass neither own observations nor own bounds for an outcome holdout. |
| `line_value` issuer revenue | **PROVEN conditional on sound reconstructed bounds**: if `a'≤B.lo` accept, if `a'≥B.hi` reject, otherwise allow both. Rejection pays `1.5a'` if `a'≤L`, zero if `a'≥U`, and either otherwise. With an uncertain acceptance bit take the min and max of feasible branch bounds. Code-level endpoint selection is sound only if those branches have sound inputs. |
| `line_value` reviewer cost | **PROVEN** for exact charges and correct status: pay observed `x` or uncut `a` if accepted, otherwise evaluate the fair threshold. For accepted historical `x=c_lo`, if `b'≥x` eventual pay is 0 or `x`: accepting repeats the same capped amount, and only `a>x` could still reject, which implies clipping and inflation. If `b'<x`, rejection is certain, but payment can include `1.5x` if the uncapped fair branch is possible. That is the C1 fix. |
| Hidden cost in `line_value` | **PROVEN**: if `b'` does not exceed an established lower bound on the charge and the strict inequality is known, it must still reject. Use `t≥L` or the maximum lower limit of actual rejecting reviewers, including verified own `b` only where applicable. Exclude the issuer's self-limit. Otherwise use cost interval `[0,b']`: acceptance requires `a≤b'`, and pays no more than `a`. **HEURISTIC:** using `4*max(...)`. No one charging fair, only one positive issuer, silent opponents or an excluded line do not invalidate these deductions. They remove information and may widen the bounds. |
| Sum of proceeds minus costs | **PROVEN outer interval** if individual pairs are bounded and all pairs are counted. `sum(revenue_lo)−sum(cost_hi)` and its symmetric upper bound require no independence. An attainable worst case requires optimize over a *jointly* feasible field. |

For the attainable-endpoint example in M2, consider two teams. Historical K charges 0, reviews with limit 100, the opponent has an accepted payment of 100, and the opponent accepted K's zero charge. Score K at `(a',b')=(100,0)`. If `t≥100`, the opponent's historical charge must be exactly 100, so K pays 150 and receives either 100 or 150. If `t<100`, the opponent charge is inflated and K pays zero, receiving between zero and 100. A positive floor at or below 100 suffices for the endpoint constructions. This is a gap in identification, even with error-free data.

## Real-field invariants

The supplied scratch folder grew to ten completed games during the audit. The invariant pass uses games 1–10, which are all in the reconciled matrix. Games 1–9 have our logged submissions and enter the outcome holdout. Game 10 has no entry in the opened submission log. The candidate sweep is the script's games 1–8. I used the public snapshot offline. [opened: local field acquisition code](../raw4/scripts/fetch_field.py) · [opened: row semantics](../live/lb_analyze.py#L12) · [opened: own submission log](../../outputs/model_outputs.json)

| Invariant | Result |
|---|---:|
| 12 teams per line, every directed non-self pair exactly once | 4,620/4,620 rows, 35 lines, 0 missing, 0 extra, 0 duplicate keys in the deduplicated snapshot |
| Boolean acceptance, finite nonnegative amount | 0 malformed rows |
| Same issuer-line accepted amount identical across reviewers, including zero | 0/321 groups disagree |
| Same issuer-line positive rejected amount identical across reviewers | 0/72 groups disagree |
| Positive rejection mixed with zero rejection for same issuer-line | 0/420 groups |
| Zero acceptance mixed with any rejection for same issuer-line | 0/420 groups |
| Accepted and positive rejected mixed with penalty different from 1.5× accepted amount | 0/68 mixed groups, using absolute €10⁻⁹ tolerance |
| Positive rejection compatible with 1.5× a cent-valued common price | 0/436 inconsistent rows at €10⁻⁹; **284/436** positive penalties have a fractional cent |
| Accepted payments on cent grid | 0 exceptions among accepted rows |
| Reviewer accepted a known price and rejected an equal or lower known price | 0/420 reviewer-line groups, including our exact logged charges where available |
| One charge and one limit with the same threshold and cap can explain every row on a line | 35/35 feasible under the observed cent-grid model; 0 require clipping; 13 also admit the cap at the largest observed positive payment |
| Verified own logs against directly identified events | 0 own-charge mismatches where exactly identified, 0 accepted payments above logged charge, 0/53 own positive penalties disagree, 0 known-price acceptance flag mismatches against our logged limit |
| Zero-sum and external reconciliation | Row nets sum to exactly zero under decimal arithmetic in 10/10. Official matrix sum per game is within €10⁻⁹ of zero. 0/120 team-game nets differ from the matrix by more than €10⁻⁹. All 12 cumulative performance totals reconcile within €0.01. |

The feasibility check tries two cap branches. A cap strictly above the largest observed payment makes all accepted prices exact. A cap at that maximum allows the issuers paid that amount to have charged more, and requires `t≤c/4`. Within each branch it propagates the fair/inflated relations and every strict `accepted issuer price < rejected issuer price` constraint for the same reviewer. It also checks the available own logs as exact constraints. A feasible assignment shows consistency with the model, not latent identification. “Accepted amounts never exceed one value per line” alone is vacuous without independent evidence of the cap. Per-issuer consistency, shared-cap feasibility and matrix reconciliation are separate checks. All teams' net sums from the same transactions are zero by construction, even with some missing rows. The matrix and pair-count comparisons make the reconciliation informative.

Reaction to a failed invariant should be to block the result for that game. The current code otherwise picks maxima from disagreeing rows, tightens `U` from incompatible observations, may pick an impossible `B` branch when `lo≥hi`, and silently drops absent flows. When charge equality is proven, a mixed acceptance flag for the same reviewer is a contradiction. When only payment equality is known, the feasible-cap check is necessary.

## Real holdout with all Kiebler rows removed

For each game I removed every row where Kiebler was issuer **or** reviewer. This withheld 726 rows and left 3,630 rows across 33 lines. I supplied neither logged `a` nor logged `b` during reconstruction. I then scored the logged pair per line and compared against the net from the withheld rows. Decimal sums are shown to €0.001 where needed. All values in the table are our team totals, measured in euros.

| Game | Actual net | Shipped held-out range | Width | Identified pairs | Core patch width | Outside by >€0.01 |
|---:|---:|---:|---:|---:|---:|:---:|
| 1 | −1,575.290 | [−4,315.920, 1,165.340] | 5,481.260 | 90.9% | 5,481.260 | No |
| 2 | 3,460.455 | [2,741.185, 4,799.160] | 2,057.975 | 78.4% | 1,822.645 | No |
| 3 | 2,195.395 | [1,951.855, 6,074.050] | 4,122.195 | 71.2% | 4,122.195 | No |
| 4 | 2,613.110 | [1,430.035, 3,978.490] | 2,548.455 | 81.8% | 1,861.275 | No |
| 5 | 7,562.320 | [2,898.840, 7,562.320] | 4,663.480 | 95.5% | 1,487.500 | No |
| 6 | 4.755 | [4.755, 4.755] | 0 | 100.0% | 0 | No |
| 7 | −4,136.700 | [−6,868.810, 54,793.930] | 61,662.740 | 70.5% | 59,739.660 | No |
| 8 | −3,238.420 | [−4,670.950, 5,799.695] | 10,470.645 | 69.5% | 9,746.535 | No |
| 9 | −8,871.820 | [−15,666.300, 1,676.730] | 17,343.030 | 58.4% | 15,133.030 | No |

Both versions cover 9/9 game nets and 33/33 line nets at €0.01; no game exceeds its endpoints beyond floating-point noise. Shipped median and total widths are €4,663.480 and €108,349.780. Core patch median and total widths are €4,122.195 and €99,394.100. The full-row replay has seven point ranges and widths €356.65 and €996.62 in games 8 and 9. Only game 6 stays a point without our outcomes. The holdout therefore provides a genuine check against observed payouts outside the reconstruction. It gives little evidence of sharpness, does not probe our unrealized policies, and uses opponents from the same games with strong exposure to each game's common price level. Counting games, lines or transactions as independent draws from future competition would be unjustified.

## Adversarial synthetic replay

I first reproduced the original seed-7 result: 12,000/12,000 with a €1 allowance, 260 beyond €0.01, largest about €0.06, median width €1,910. The author generator uses independent price errors within most lines, near-continuous amounts, settlement amounts rounded to cents, a weak absolute pass threshold, and a candidate grid limited to a few multiples of the reference value. It rarely samples equalities and cannot establish universal coverage.

### Minimal counterexamples

Each row is a standalone one-line synthetic game. K is our team and O is the opponent. Unless marked otherwise, all settlements are exact. Policy pairs are `(a,b)`.

| Failure | Truth and historical play | Candidate | True net | Shipped range | Core patch |
|---|---|---|---:|---:|---:|
| C1 incoming fair penalty erased | `t=10,c=100,K=(0,10),O=(10,0)`. Both historical rows accepted. | `(0,0)` | −15 | [0, 0] | [−15, 0] |
| C1 outgoing fair penalty erased | `t=10,c=100,K=(1,10),O=(10,0)`. K's 1 was rejected for 1.50, O's 10 was accepted. | `(10,10)` | 5 | [−10, 0] | [−10, 15] |
| C2 unbounded cap, candidate limit binds exposure | `t=0,c=500,K=(0,0),O=(500,0)`. K's zero accepted, O's 500 rejected for zero. | `(0,500)` | −500 | [−4, 0] | [−500, 0] |
| C2 can also overstate exposure | Same rows. Candidate limit permits a maximum €1 cost in any feasible world. | `(0,1)` | 0 | [−4, 0] | [−1, 0] |
| C3 omitted line keeps default review | `t=10,c=100,K=(0,0),O=(10,0)`. Fair charge rejected and paid 15. | `{}` | −15 | [0, 0] | [−15, −15] |
| C4 snapping exact sub-cent charge | `t=100,c=400,K=(0,0),O=(99.996,0)`. Historical penalty €149.994. | `(0,99.997)` | −99.996 | [−150, −150] | [−150, −150] |
| C4 snapping a cent-rounded row | Same truth. Publish historical penalty as €149.99 and compare with the exact payoff. | `(0,99.99)` | −149.994 | [−99.99, −99.99] | [−99.99, −99.99] |

I also tested an accepted sub-cent payoff that displayed as zero, and coincident accepted payments for charges at and above a shared cap. The cap-tie case covered its true payoff. With labeled prices, ties `a=b` must accept and `a=t` must pay 1.5× upon rejection. A field with no fair charges supplies no positive lower threshold clue. The random test exercises each of these regimes under the exact-money contract, and the targeted sub-cent tests exercise departures from it.

### Random stress coverage

An independent direct-payoff simulator produced 3,000 games with 1–7 lines, 2/3/4/12 teams and shared opponent valuation errors. Seed 290137, 500 games per regime, 14 alternatives per game. Seven alternatives used multiplier settings on a shared noisy estimate and seven sampled boundaries and high limits. Whole-euro submissions keep penalties exact in half-euro steps. Max gap is the distance from truth to the nearest endpoint when outside. All 936 misses exceed €0.01. The routes to failure include both C1 and C2.

| Regime | Shipped misses / 7,000 | Largest miss |
|---|---:|---:|
| Correlated estimates | 140 | €1,056 |
| Ties, repeated prices and cap ties | 263 | €14,588 |
| All charges above fair threshold | 15 | €92 |
| Excluded lines and cap floor | 114 | €8,800 |
| Silent / accept-everything mixtures | 196 | €14,400 |
| Cap exactly 4t when it dominates the floor, near-threshold prices | 208 | €4,678.50 |
| **Total** | **936 / 42,000** | **€14,588** |

Shipped coverage is 97.77%. The truth was below the lower endpoint 906 times and above the upper endpoint 30 times. The seven sensible multiplier policies miss 417/21,000 with a maximum miss of €1,596. The boundary and high-limit policies miss 519/21,000. The tested core patch misses 0/42,000 under this exact-money experiment. These are stress-distribution frequencies. They estimate neither live failure rates nor a confidence level for the output.

### Policy discrimination and power

Each field compares the seven sensible multiplier policies. Spearman is the mean correlation of within-game midranks where both rankings vary. Strict pair metrics exclude 6,650 true ties from 63,000 pair comparisons. “Sure” requires disjoint interval ordering. For the fixed reference, I also compare each candidate's interval to the known true reference net, which favors power and approximates the historical-actual setup.

| Metric | Shipped | Core patch |
|---|---:|---:|
| Spearman, lower endpoint vs truth | 0.7831 (2,675 games) | 0.7354 (2,773 games) |
| Spearman, midpoint vs truth | 0.7403 (2,869 games) | 0.7459 (2,870 games) |
| Correct sure order, all strict pairs | 14,295/56,350 = 25.37% | 13,983/56,350 = 24.81% |
| False sure order, all strict pairs | 6/56,350 | 0/56,350 |
| Truly better than reference, correctly sure | 1,887/8,501 = 22.20% | 1,887/8,501 = 22.20% |
| Truly worse than reference, correctly sure | 2,040/7,476 = 27.29% | 2,007/7,476 = 26.85% |
| Truly better, reference *net known* | 4,695/8,501 = 55.23% | 4,738/8,501 = 55.73% |
| Truly worse, reference *net known* | 3,735/7,476 = 49.96% | 3,678/7,476 = 49.20% |
| Median width / median strict policy gap | €418.50 / €117.50 = 3.56× | €390.00 / €117.50 = 3.32× |
| Median pair-average width divided by that pair's actual gap | 2.89× | 2.89× |

Correlation does not make an endpoint a ranking certificate. The original lower endpoint has higher mean rank correlation on its nonconstant games, yet produces six false sure orders. Both versions leave roughly three-quarters of strict orders unresolved by disjoint intervals. Computing the paired difference under one common feasible field can improve this without pretending that an unknown threshold has a most likely value.

## What survives the games 1–8 sweep

I reproduced the README's table from the local saved answers with the exact evaluation loop and the production engine. The actual net is €6,885.625 from game-row sums. Games 1–6 contributed +€14,260.745 and games 7–8 contributed −€7,375.120. Only our aggregated candidate deltas appear below. “Core” here means the tested logic patch with the money format seen in this snapshot. The core outputs are still retrospective.

| Selected candidate | Shipped lower delta | Core range, delta vs actual | Core lower delta, games 1–6 | Core lower delta, games 7–8 |
|---|---:|---:|---:|---:|
| luna defaults | −22,715.22 | [−14,094.47, +79,051.46] | −14,894.91 | +800.44 |
| luna 0.8 / 1.0 | −1,863.03 | [+2,972.90, +79,285.65] | +684.16 | +2,288.74 |
| luna 0.8 / 0.8 | +2,349.22 | [+3,912.46, +78,957.30] | +948.48 | +2,963.98 |
| luna 0.7 / 0.9 | +11,333.52 | [+15,352.30, +64,556.14] | +10,427.39 | +4,924.90 |
| luna 0.6 / 0.6 | +10,802.84 | [+10,802.84, +51,802.18] | +2,448.83 | +8,354.01 |
| terra 0.8 / 1.0 | +784.89 | [+4,353.89, +80,610.43] | +7,017.27 | −2,663.38 |

Games 7–8 account for 77% of the 0.6/0.6 lower delta and 32% of the 0.7/0.9 lower delta. The stronger early contribution for 0.7/0.9 earns historical attention. The tightest-setting benefit is much more concentrated in our two large historical losses. Game 7 alone also accounts for 57% of the shipped holdout's sum of widths. Show the split, rather than carrying a statement about large late losses over to every recipe. The intervals for the two leading settings overlap widely. Subtracting the two absolute ranges gives a conservative difference of approximately [−€36,450, +€53,753] for 0.7/0.9 minus 0.6/0.6. A same-field paired bound could materially narrow this comparison. This table does not determine the better candidate.

The old proxy `b_regret` loses uncertain transactions and ignores capped accepts. `a_score` substitutes price ratios and does not measure which opponents accept or owe a penalty. The euro replay improves the target variable. That improvement supplies no validation of the reconstruction or the strategy selection.

### Safe write-up wording

**Today, with the shipped code:**

> We reconciled the organizer's historical net totals against the public settlement rows. A leave-our-transactions-out diagnostic covered our observed net in all nine logged games, with a median range of €4,663. Adversarial tests found that the initial counterfactual replay can miss the true payoff. Its retrospective sweep helped shortlist policies for forward testing.

**After applying the core patch, confirming the settlement precision contract, and validating inputs:**

> For each saved policy output, we bound its net payoff on the same completed games with opponents' submissions held fixed. The bounds are conservative because some charges, acceptance limits and caps are only partially identified. Several tighter settings have positive lower deltas versus our historical submissions on games 1–8. We selected those settings retrospectively and test the frozen policy separately on subsequent games.

Use the current tool to reconcile accounting and generate hypotheses. **Do not use it to guarantee a live gain, pick a multiplier by its midpoint or lower endpoint alone, assert a worst-case feasible loss, quote an expected euro return, estimate a model's average quality from one saved draw, or convert our counterfactual net to ranking points.** Keep signed historical comparisons conditional on the precision contract and check simultaneous feasibility for head-to-head conclusions. [opened: official rank and jury scoring](../../materials/EVALUATION_CRITERIA.md#L12)

## Fixes and gates

**P0.** Apply the tested core diff below. The bound proof is the branch argument in the derivation section. It requires complete rows at the expected game, exact charge recovery from penalties, normalized amounts, finite nonnegative policy inputs, and verified own log inputs. Keep omitted lines at the game's defaults and reject unknown indices. Amend the module docstring and README to remove the universal coverage and attainable-worst-case language. Keep tolerance out of the acceptance and fair predicates.

**P0.** Get the organizers' money representation contract. For exact cent-grid charges and exact half-cent penalties, canonicalize amounts before any inequality and accumulate in exact arithmetic. The proposed diff uses rational values and rejects off-grid observations beyond a declared €10⁻⁹ allowance for export noise. A cent-shaped exported value can still hide an arbitrary-precision input. Enable this path only with a confirmed source contract. For exact arbitrary-precision amounts, use rational arithmetic and `a=2y/3` directly. For rounded settlement rows, use the source's actual inverse rounding bins, including endpoints. For nearest-cent display and a positive observed rejected value `y`, conservatively use `a∈[(y−0.005)/1.5,(y+0.005)/1.5]` and widen acceptance, threshold and cap constraints. For a rounded zero rejection, keep both the small-fair and inflated branches. Propagate payment rounding if the target is the organizer's rounded balance. Reject unsupported formats until a mode exists.

**P0.** Insert input validation prior to replay. Require each expected line and historical participant, every non-self ordered pair, one consistent observation per key, finite nonnegative shape, the correct snapshot and verified final own payload. Reconcile matrix totals before processing candidate policies. Validate necessary issuer and reviewer relations and require at least one jointly feasible cap/threshold branch. Make the fetcher stop on a failed page, compare duplicate records before deduplication, and publish a cache atomically only after reconciliation against the snapshot. A roster and line manifest must come from a trusted source so a wholly missing team or line cannot erase itself. If partial rows are deliberately supported, carry an explicit roster and record which reviewer rejected each hidden charge. Apply `our_b` only to actually observed own rejection rows.

**P1.** Carry the field's common constraints through comparisons. One cap per line has an uncapped branch and, when supported, a branch at the maximum observed accepted payment. For each feasible branch, constrain every historical accept/reject relation, the candidate-order ties, shared threshold and common opponent variables. Optimize `NET(P)−NET(Q)` in that same feasible field, including strict inequalities or their exact cent-grid equivalents. Optimize each head-to-head payoff margin similarly if rank is a deliverable. Test against exhaustive enumerations of tiny finite games. This approach produces informative comparisons even where absolute intervals heavily overlap. Report an outer bound with an explicit optimality gap if using a relaxation.

**P1.** Stop importing `arch_bench` in the offline replay. Extract the saved-answer loader to an offline module shared by both callers. Require a manifest of game IDs, exact reader run and repeat identifiers, parameter values, prompt version, complete line mapping and field snapshot. Replace implicit environment-dependent defaults with explicit parameters for reported runs. Score submitted estimates with the live POS mapping and record omissions rather than silently dropping lines. Compare the recorded actual policy to itself at exactly zero delta. Show actual versus candidate strict signs only after using precision-aware accounting. Diff C reports the historical baseline identity and, with diff B, compares candidate intervals in exact units.

**P1.** Freeze the shortlist and promotion criterion before opening future outcomes. Evaluate consecutive games that played after the freeze. Include saved submission receipts, end-to-end timing, any default or late fallback outcome, and representative repeat reader draws. Show per-game and cumulative paired results and sensitivity with each large game removed. Keep these forward results separate from the historical tuning cohort.

**Regression gates.** Add the two minimal cap-status examples, both hidden-cost directions, omitted vs explicit defaults, exact accept/fair/cap equalities, sub-cent acceptance inversions, rounded zero, identical prices with mixed flags, equal capped payments with different charges, impossible `L/U`, two- and three-team fields, missing pages, conflicting duplicates, late participation, roster gaps, and own log disagreement. Fail tests on out-of-range truth under the stated precision contract. Run the real leave-Kiebler-out diagnostic as a saved snapshot check with line-level misses and widths. Re-run discrimination against the paired comparison as well as the independent endpoints.

### Exact proposed diffs

The first diff was applied in memory for the numbers labeled “core.” The precision gate accepts the 4,620 observed rows and rejects the off-grid targeted input. The eight-game candidate sweep also runs with the precision gate. I checked that all three diffs apply to their stated bases and compile. No target source file was edited.

#### A. Tested replay logic patch

```diff
--- a/research/bench/euro_replay.py
+++ b/research/bench/euro_replay.py
@@ -49,7 +49,7 @@
             elif acc_pos:
                 x = max(acc_pos)
                 # exact only if x is below the proven cap level (then x = min(a, c) < c forces a = x); a clipped amount means a > c >= 4t: inflated
-                A[i] = dict(a=x, x=x, exact=x < c_lo, status=("inflated" if (zero_rej or x >= c_lo) else "unknown"))
+                A[i] = dict(a=x, x=x, exact=x < c_lo, status=("inflated" if zero_rej else "unknown"))
             elif zero_rej:
                 A[i] = dict(a=None, status="hidden", exact=False, x=None)
             else:
@@ -118,7 +118,7 @@
             if b_c <= floor:
                 ident += 1                          # still above our limit: rejected, inflated, costs nothing
             else:
-                cost_hi += 4 * max(U if U < INF else L, floor, 1.0)   # unidentified exposure, heuristic ceiling
+                cost_hi += b_c  # acceptance requires a <= b_c, and payment <= a
             continue
         x = Ai["x"] if Ai["x"] is not None else a
         if Ai["exact"]:
@@ -129,7 +129,9 @@
                 cost_lo += pr[0]; cost_hi += pr[1]; ident += int(pr[0] == pr[1])
         else:                                       # amount may be clipped by the cap: a >= x, and a clipped charge is certainly inflated
             if b_c < x:
-                ident += 1                          # rejected for sure, inflated: costs 0
+                pr = _rej_pay(x, L, U, Ai["status"])
+                cost_hi += pr[1]  # only the uncapped a == x branch can be fair
+                ident += int(pr[1] == 0)
             else:
                 cost_hi += x                        # accepted pays exactly x (same cap); rejected pays 0
     return rev_lo - cost_hi, rev_hi - cost_lo, n, ident
@@ -138,9 +140,12 @@
 def game_value(lines, us, policy):
     """policy: {line: (a, b)} for our lines. Returns (lo, hi, identified_share)."""
     lo = hi = 0.0; n = ident = 0
-    for ln, (a, b) in policy.items():
-        if ln not in lines:
-            continue
+    if policy.keys() - lines.keys():
+        raise ValueError("policy contains unknown line indices")
+    for ln in lines:
+        a, b = policy.get(ln, (0.0, 0.0))
+        if not all(math.isfinite(v) and v >= 0 for v in (a, b)):
+            raise ValueError("charge and limit must be finite and nonnegative")
         l, h, k, i = line_value(lines[ln], us, a, b)
         lo += l; hi += h; n += k; ident += i
     return lo, hi, (ident / n if n else float("nan"))
```

#### B. Precision gate and exact accumulation, apply after A and after confirming the cent-grid contract

```diff
--- a/research/bench/euro_replay.py
+++ b/research/bench/euro_replay.py
@@ -19,29 +19,51 @@
 Validation (see euro_replay_check.py): (1) replaying our ACTUAL submissions reproduces our actual net, (2) on synthetic fields with known truth the
 range always contains the true counterfactual.   Other teams' rows are held in memory / a scratch dir OUTSIDE the repo; nothing is written here.
 """
-import collections, json, math, sys
+import collections, json
+from fractions import Fraction
 from pathlib import Path
 
 INF = float("inf")
+CENT = Fraction(1, 100)
+PENALTY = Fraction(3, 2)
+EXPORT_NOISE = Fraction(1, 10**9)
+
+
+def _on_grid(value, step, tolerance=0):
+    """Canonicalize values under the confirmed exact-settlement money contract."""
+    x = Fraction(str(value))
+    normalized = round(x / step) * step
+    if x < 0 or abs(x - normalized) > tolerance:
+        raise ValueError("money is off the declared settlement grid")
+    return normalized
+
+
+def _row_amount(row):
+    if type(row["accepted"]) is not bool:
+        raise ValueError("accepted must be boolean")
+    step = CENT if row["accepted"] else CENT * PENALTY
+    return _on_grid(row["amount"], step, EXPORT_NOISE)
 
 
 def reconstruct(rows, us, our_b=None, our_a=None):
     """rows: dicts issuer, reviewer, line_item_index, accepted, amount (all ordered pairs of one game). Returns {line: Line}.
     our_b / our_a: optional {line: value}, OUR OWN logged actual submission. our_b: a hidden charge was rejected by us too, so it lies above
     it; our_a: our own charge when the rows hide it (it was rejected by everybody)."""
+    our_a = {ln: _on_grid(a, CENT) for ln, a in (our_a or {}).items()}
+    our_b = {ln: _on_grid(b, CENT) for ln, b in (our_b or {}).items()}
     by = collections.defaultdict(lambda: collections.defaultdict(list))
     for r in rows:
-        by[r["line_item_index"]][r["issuer"]].append(r)
+        by[r["line_item_index"]][r["issuer"]].append(dict(r, amount=_row_amount(r)))
     out = {}
     for ln, issuers in by.items():
         # a pass over all accepted amounts: the cap is shared, so c >= every accepted amount, and c >= 4 t >= 4 L
         acc_amounts = [r["amount"] for rs in issuers.values() for r in rs if r["accepted"] and r["amount"] > 0]
-        fair_a = [round(r["amount"] / 1.5, 2) for rs in issuers.values() for r in rs if (not r["accepted"]) and r["amount"] > 0]
-        L = max(fair_a, default=0.0)
+        fair_a = [r["amount"] / PENALTY for rs in issuers.values() for r in rs if (not r["accepted"]) and r["amount"] > 0]
+        L = max(fair_a, default=0)
         c_lo = max([4 * L] + acc_amounts)
         A = {}
         for i, rs in issuers.items():
-            pos_rej = [round(r["amount"] / 1.5, 2) for r in rs if not r["accepted"] and r["amount"] > 0]
+            pos_rej = [r["amount"] / PENALTY for r in rs if not r["accepted"] and r["amount"] > 0]
             acc_pos = [r["amount"] for r in rs if r["accepted"] and r["amount"] > 0]
             zero_rej = any((not r["accepted"]) and r["amount"] == 0 for r in rs)
             if pos_rej:
@@ -53,7 +75,7 @@
             elif zero_rej:
                 A[i] = dict(a=None, status="hidden", exact=False, x=None)
             else:
-                A[i] = dict(a=0.0, status="zero", exact=True, x=None)
+                A[i] = dict(a=0, status="zero", exact=True, x=None)
         if our_a and ln in our_a and A.get(us, {}).get("status") == "hidden":
             A[us] = dict(a=our_a[ln], status="inflated", exact=True, x=None)      # rejected for 0 by everybody: inflated, value from our log
         U = min([v["x"] if v["x"] is not None else v["a"] for v in A.values() if v["status"] == "inflated" and (v["x"] is not None or v["a"] is not None)], default=INF)
@@ -61,7 +83,7 @@
         for i, rs in issuers.items():
             for r in rs:
                 j = r["reviewer"]
-                B.setdefault(j, dict(lo=0.0, hi=INF))
+                B.setdefault(j, dict(lo=0, hi=INF))
                 a = A[i]["a"]
                 if a is None or a <= 0:
                     continue
@@ -69,7 +91,7 @@
                     B[j]["lo"] = max(B[j]["lo"], a)
                 elif A[i]["exact"]:
                     B[j]["hi"] = min(B[j]["hi"], a)
-        out[ln] = dict(A=A, L=L, U=U, B=B, c_lo=c_lo, our_b=(our_b or {}).get(ln, 0.0))
+        out[ln] = dict(A=A, L=L, U=U, B=B, c_lo=c_lo, our_b=(our_b or {}).get(ln, 0))
     return out
 
 
@@ -80,20 +102,20 @@
 
 def _rej_pay(x, L, U, status=None):
     if status == "fair":
-        return (1.5 * x, 1.5 * x)
+        return (PENALTY * x, PENALTY * x)
     if status == "inflated":
-        return (0.0, 0.0)
+        return (0, 0)
     if x <= L:
-        return (1.5 * x, 1.5 * x)
+        return (PENALTY * x, PENALTY * x)
     if x >= U:
-        return (0.0, 0.0)
-    return (0.0, 1.5 * x)
+        return (0, 0)
+    return (0, PENALTY * x)
 
 
 def line_value(line, us, a_c, b_c):
     """Our net range on one line for candidate charge a_c and limit b_c: (lo, hi, n_pairs, n_identified)."""
     L, U, c_lo = line["L"], line["U"], line["c_lo"]
-    rev_lo = rev_hi = cost_lo = cost_hi = 0.0
+    rev_lo = rev_hi = cost_lo = cost_hi = 0
     n = ident = 0
     for j, Bj in line["B"].items():
         if j == us:
@@ -114,7 +136,7 @@
             ident += 1
             continue
         if a is None:                              # hidden charge: rejected by everybody, so it is above every limit that rejected it
-            floor = max([B["lo"] for jj, B in line["B"].items() if jj != i] + [line.get("our_b", 0.0)])
+            floor = max([B["lo"] for jj, B in line["B"].items() if jj != i] + [line.get("our_b", 0)])
             if b_c <= floor:
                 ident += 1                          # still above our limit: rejected, inflated, costs nothing
             else:
@@ -139,21 +161,19 @@
 
 def game_value(lines, us, policy):
     """policy: {line: (a, b)} for our lines. Returns (lo, hi, identified_share)."""
-    lo = hi = 0.0; n = ident = 0
+    lo = hi = 0; n = ident = 0
     if policy.keys() - lines.keys():
         raise ValueError("policy contains unknown line indices")
     for ln in lines:
-        a, b = policy.get(ln, (0.0, 0.0))
-        if not all(math.isfinite(v) and v >= 0 for v in (a, b)):
-            raise ValueError("charge and limit must be finite and nonnegative")
-        l, h, k, i = line_value(lines[ln], us, a, b)
+        a, b = policy.get(ln, (0, 0))
+        l, h, k, i = line_value(lines[ln], us, _on_grid(a, CENT), _on_grid(b, CENT))
         lo += l; hi += h; n += k; ident += i
     return lo, hi, (ident / n if n else float("nan"))
 
 
 def actual_net(rows, us):
-    inc = sum(r["amount"] for r in rows if r["issuer"] == us)
-    cost = sum(r["amount"] for r in rows if r["reviewer"] == us)
+    inc = sum(_row_amount(r) for r in rows if r["issuer"] == us)
+    cost = sum(_row_amount(r) for r in rows if r["reviewer"] == us)
     return inc - cost
 
 
@@ -164,5 +184,5 @@
     assert repo not in d.parents and d != repo, "field cache must live outside the repo"
     games = {}
     for f in sorted(d.glob("tx_g*.json"), key=lambda p: int(p.stem[4:])):
-        games[int(f.stem[4:])] = json.loads(f.read_text())
+        games[int(f.stem[4:])] = json.loads(f.read_text(), parse_float=Fraction)
     return games
```

#### C. Report the historical baseline identity, apply after B

```diff
--- a/research/bench/euro_eval.py
+++ b/research/bench/euro_eval.py
@@ -27,12 +27,18 @@
     rec[g] = (er.reconstruct(games[g], us, our_b={l: b for l, (a, b) in sub.items()}, our_a={l: a for l, (a, b) in sub.items()}), sub, er.actual_net(games[g], us))
 act_total = sum(v[2] for v in rec.values())
 
-def evaluate(name, policies):
-    lo = hi = 0.0; per = []
+def evaluate(name, policies, *, historical=False):
+    lo = hi = 0
+    per = []
     for g in G:
         l, h, _ = er.game_value(rec[g][0], us, policies[g]); lo += l; hi += h; per.append((l, h))
-    d_lo = lo - act_total; d_hi = hi - act_total
-    wins = sum(1 for g, (l, h) in zip(G, per) if l > rec[g][2]); losses = sum(1 for g, (l, h) in zip(G, per) if h < rec[g][2])
+    if historical:
+        print(f"{name:52s} reconciliation [{lo:.3f}, {hi:.3f}]  baseline delta exactly 0")
+        return
+    d_lo = lo - act_total
+    d_hi = hi - act_total
+    wins = sum(1 for g, (l, _) in zip(G, per) if l > rec[g][2])
+    losses = sum(1 for g, (_, h) in zip(G, per) if h < rec[g][2])
     print(f"{name:52s} net [{lo:9.0f}, {hi:9.0f}]  delta vs actual [{d_lo:+9.0f}, {d_hi:+9.0f}]  surely better in {wins}/{len(G)} games, surely worse in {losses}")
 
 def policy_from(reader, params, games_=G):
@@ -42,8 +48,8 @@
         out[g] = {x.index + 1: (x.a, x.b) for x in engine.compute(est, params)}
     return out
 
-print(f"games {G}; our actual net over these games: {act_total:+.0f} (exact)\n")
-evaluate("ACTUAL submissions (live bot at the time)", {g: rec[g][1] for g in G})
+print(f"games {G}; our actual net over these games: {act_total:+.3f}\n")
+evaluate("ACTUAL submissions (live bot at the time)", {g: rec[g][1] for g in G}, historical=True)
 P = engine.Params
 for nm, rd in (("luna", ab.LUNA), ("terra", ab.TERRA), ("fable", ab.FABLE)):
     evaluate(f"{nm}: engine defaults (KA .9/.85, KB 1.25/1.05)", policy_from(rd, P()))
```

### Reproduction

Use the provided scratch directory as `FIELD_DIR`. The audit scripts read it in memory and print aggregates only.

```sh
python3 -B research/raw5/scripts/gpt_g_real.py "$FIELD_DIR"
python3 -B research/raw5/scripts/gpt_g_synthetic.py
.venv/bin/python -B research/raw5/scripts/gpt_g_candidates.py "$FIELD_DIR"
python3 -B research/bench/euro_replay_check.py "$FIELD_DIR" \
  --us "Kiebler Software Solutions" --synthetic 2000
```

[opened: euro replay](../bench/euro_replay.py) · [opened: original checker](../bench/euro_replay_check.py) · [opened: offline candidate sweep](../bench/euro_eval.py) · [opened: historical claims and proxy definitions](../bench/README.md#L94) · [opened: pricing engine](../../claimbot_fable/engine.py) · [opened: live line mapping](../../claimbot_fable/runner.py#L48)

No API call, credential access, live submission or storage of settlement records took place. No other reviewer's audit files were read.
