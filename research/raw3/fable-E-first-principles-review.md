# First-principles review of the "Claim to Fame" approach (Fable E, independent reviewer)

Written 2026-11-21, 14:40-15:15 CET, during the live tournament. Data: games 1-5 (16 invoice lines), the four decrypted cases 1-4,
the team's saved model answers and replay files, the organisers' public leaderboard JSON.
Evidence labels: **[opened]** = I read the primary file or endpoint myself, **[team]** = a number from the team's own files that I
read but did not recompute, **[memory]** = from my memory, do not rely on it. Scripts: `research/raw3/scripts/` (no data in them).

**Data handling.** Other teams' rows were read from the public leaderboard endpoints only (about 90 requests, at most one per
second), cached in a scratch folder under `/private/tmp` and nowhere else. This file has aggregates and anonymous archetypes only,
and it does not print the bracket endpoints (each endpoint is one team's charge). I did not read `.env`, did not call the game API,
did not submit, and did not touch `claimbot/`.

**Limits you should keep in mind while reading.** Five games. Nine lines on which a fair charge was seen, six of them with only a
lower bound for `t`. Every quantitative claim below rests on that, and several of the team's earlier conclusions rest on less.

---

## Executive summary (the answer)

1. **With `t` known the game is trivial: `a = b = t`.** All the money is in knowing `t`. On the real field, a line charged at
   exactly `t` earns 15.6 × `t`; an estimate with 15 % error earns about 10.9, with 30 % about 8.7, with 50 % about 7.0 (replay on the
   real acceptance limits, section A6). Tuning the `a`/`b` formula moves the result by 5-15 %. Estimate quality moves it by a factor of 2.
2. **The money is on the issuer side, about 4 to 1.** Over games 1-5 we collected 35.3k on valid lines where 63.8k was available
   at `a = t` (55 %). We lost 10.9k on two lines where our own charge was inflated and 17.6k by charging below `t`. The reviewer side
   cost us 6.8k (4.2k paid for inflated charges, 2.6k in penalties). The team's benchmark scores mainly the reviewer side.
3. **`t` = justified quantity × the expert's price × policy arithmetic.** Validity (zero or not) is solved by every model tried.
   The arithmetic is deterministic but the schema cannot express it: an aggregate sub-limit shared rateably across lines (game 4),
   a justified quantity below the invoiced one, a total stated in the description (game 2). The price level is the residual noise.
4. **The live prompt contains a wrong rule.** It tells models to value property at time value after depreciation. Three of the four
   policies I read pay "same kind and quality in new condition" and the fourth "a replacement of the same kind, quality and
   specification"; none depreciates. That instruction was added after game 1, whose real cause was a missed
   halving clause. It pushes medians down.
5. **`a` and `b` currently contradict each other.** `b ≥ 1.25 × median` assumes our medians are about 20 % low. `a ≈ 0.78 × median`
   assumes they are unbiased. An interval-censored fit of the brackets says the medians are low with probability 0.94-0.99
   (size uncertain, at least about 12 %). So `a` is the one that is wrong, except on lines whose value is pinned by a policy limit.
6. **One strong call does what twenty do.** In the team's own replay a single Fable call earns 22.4-22.7k over games 1-4, the
   20-member ensemble 21.0-21.8k, the ensemble without web members 23.3-23.8k, web members alone 11.0-19.5k **[team]**. The live
   bot now runs 18 calls per round, 12 of them on the three largest models. That is the "token maxing" the jury penalises, with no measured gain.
7. **The field** (12 teams): 3-5 silent per game in games 1-5, one in game 6. Active teams charge a tight cluster at a median of
   0.77 × `t`, 79 % of their charges are fair, and at least 62 % of their acceptance limits sit below `t`, so they pay each other
   1.5×. Nobody with four or more games collects more than about 70 % of the available issuer income. We are 3rd after game 6.
8. **Game 6 arrived while I was writing and is the first test of point 5 on a game I had not seen** (addendum at the end):
   one open line, all eleven active teams charged fairly, and our charge was half of the highest one that got through. We made
   +5 EUR on a game where about 12k of issuer income was available.

**Recommendation in one paragraph.** Keep the split "the model reads, Python computes" and make it real: one strong reader
(`claude-fable-5-2`, low effort) that returns per line the validity, justified quantity, unit price, payable fraction, and per case
the aggregate limits and description anchors; Python applies fractions, limits (rateably) and anchors. A second provider
(`gpt-6.1-terra`, medium) runs as standby, a cheap fast call (`gpt-6-luna`, low) gives a first submission by about 15 s. Drop the web
members, the size weights, DSPy/GEPA and per-model bias corrections. Price with two multipliers per line type: open lines
`a = 0.90 × median`, `b = 1.25 × median`; lines pinned by a limit or anchor `a = 0.85 ×`, `b = 1.05 ×`; `b = 0` when P(valid) < 2/3;
charge excluded lines as if valid (free option, disclosed). Refit the multipliers every five games by leave-one-game-out replay in
EUR. Expected gain: about +1-2k per game from the reader fixes if they prevent half of the rule misses, +0.5-1k from `a`, and the
same score at a tenth or less of the calls. Biggest risk: a new schema breaking in production, so test it offline on cases 1-5 first.

---

## A. First-principles model

### A1. Payoff of one line, one ordered pair

Issuer H charges `a`, reviewer I has limit `b`, fair value `t`, cap `c ≥ 4t` **[opened: GAME_DESCRIPTION.md]**.

| | `a ≤ t` | `a > t` |
| --- | --- | --- |
| `a ≤ b` | I pays `a` | I pays `min(a, c)` |
| `a > b` | I pays `1.5a` | I pays 0 |

Our net is a sum over opponents of (what they pay on our `a`) minus (what we pay on their `a`). Our `a` appears only in the first
sum and our `b` only in the second, so **`a` and `b` are separate problems**. The team has this right.

### A2. Known `t`

- **`b = t`** is exactly optimal whatever the others do: it accepts every fair charge (cost `a` instead of `1.5a`) and rejects
  every inflated one (cost 0).
- **`a = t`**: any `a ≤ t` earns `a × (n + 0.5 R(a))`, where `n` is the number of opponents and `R(a)` the number who reject it.
  That rises with `a`, and rejection *helps* a fair charge. Above `t` we earn `a × A(a)`, where `A(a)` is the number of reviewers
  who still accept. Inflating pays only if `a × A(a) > t × (n + 0.5 R(t))`. On the real field `n + 0.5 R(t) ≈ 15.6` and `A` is 1-3
  of 11, so even at the cap (`a = 4t`) we would need four or more accept-everything teams. There are none to one. **Never inflate
  on purpose on a valid line.**

So the whole value of the game is information about `t`.

### A3. A belief about `t`, opponents' charges carry no information

- Reviewer: accepting costs `a`, rejecting costs `1.5a × P(a ≤ t)`. Reject iff `P(t < a) > 1/3`. One threshold for all charges:
  `b` = the 1/3-quantile of the belief. If `P(t = 0) ≥ 1/3` then `b = 0`. If `a > c` the threshold becomes `a/(a + 2c)`; it never
  matters for realistic charges.
- Issuer: maximise `a × [S(a) m_f + (1 − S(a)) m_i]` with `S(a) = P(t ≥ a)`, `m_f` what a fair charge earns per unit (about 15) and
  `m_i` what an inflated one earns (about 1-3). With `m_i = 0` and a lognormal belief the first-order condition is
  `φ(z)/(1 − Φ(z)) = σ` at `a = median × e^{σz}`. That gives `a/median` = 0.80, 0.74, 0.77 for σ = 0.15, 0.30, 0.50: **the shading
  factor is about 0.75-0.80 for any plausible σ**. So the elicited σ hardly matters for `a`. The fair share at the optimum is 93 %,
  84 %, 70 %.

This is what `claimbot/pricing.py` implements. Under its assumptions it is correct.

### A4. Opponents' charges do carry information (the part the 1/3-quantile leaves out)

Other teams read the same documents. Write, in logs, our estimate `x = ln t + β + c + e_u` and an opponent's charge
`ln a = ln t + γ + c + e_j`: `β` is our bias, `γ` the field's shading plus bias, `c` an error shared by everybody (same kind of
model, variance `σ_c²`), `e_u`, `e_j` our and their own errors (`σ_u²`, `σ_j²`). With a flat prior on `ln t`, the posterior given
our estimate and a charge at level `a` is normal with mean `(1 − w)(x − β) + w(ln a − γ)`, `w = σ_u²/(σ_u² + σ_j²)`, and variance
`S² = σ_c² + σ_u²σ_j²/(σ_u² + σ_j²)`. Accepting iff `P(t ≥ a | x, a) ≥ 2/3` gives

> **`b = t̂ × e^{−β} × exp( [w·|γ| − 0.43·S] / (1 − w) )`**

Checks: a perfect own estimate (`σ_u → 0`) gives back the 1/3-quantile; `σ_c → 0` too gives `b = t`. What it says:

- `b` rises with the field's shading `|γ|` and with our own noise relative to theirs; it falls with the shared error.
- **Correlated versus independent errors:** a larger shared part `σ_c` lowers `b`, because an opponent's charge then tells us
  little we do not already believe. A larger own part raises `b`, because the charge is then real evidence about `t`.
- With the observed field (`γ = ln 0.77`, within-line spread `σ_j ≈ 0.24`): a precise, unbiased reader (`σ_u = 0.10`, `σ_c = 0.15`)
  gets a multiplier of 0.96; a noisy one (`σ_u = 0.30`) 1.15; and every case is multiplied by `e^{−β}`, which is 1.18-1.28 if our
  medians are 15-22 % low. **So `b` belongs at 1.0-1.3 × our median, not at 0.81-0.94 × as the 1/3-quantile gives.**

The same `e^{−β}` multiplies the optimal `a`. Whatever is believed about the bias must be applied to both.

### A5. A population with silent, accept-everything and noisy-rational teams

Simulation, `scripts/sim_first_principles.py` (numpy, assumptions only; scenario 1 is set to the aggregate shape of the field:
76 % of opponents' charges fair, median charge 0.78 `t`). Units: multiples of `t` per valid line.

| scenario | our error sd | best `a`/est | income | best `b`/est | reviewer regret | loss of `pricing.py` vs best |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1. field-like, we share the field's low level, uncorrected | 0.15 | 1.05 | 11.1 | 1.20 | 0.47 | **2.69** |
| | 0.30 | 0.95 | 9.0 | 1.10 | 0.97 | **1.07** |
| 2. same field, our estimate de-biased | 0.15 | 0.80 | 11.1 | 0.90 | 0.46 | 0.04 |
| | 0.30 | 0.75 | 9.0 | 0.90 | 0.99 | 0.00 |
| 4. errors almost fully shared (ρ = 0.9), de-biased | 0.30 | 0.80 | 9.3 | 0.80 | 1.08 | 0.25 |
| 5. no silent teams, de-biased | 0.30 | 0.80 | 8.6 | 0.90 | 1.78 | 0.15 |
| 6. textbook field (unbiased, no shading) | 0.30 | 0.75 | 9.0 | 0.70 | 1.03 | 0.12 |
| 7. 60 % of active reviewers accept up to 3× | 0.30 | 0.80 | 9.1 | 0.90 | 0.98 | 0.05 |
| any scenario, `t` known | 0 | 1.00 | 14.3-15.3 | 1.00 | 0 | |

Reading:

- **With an unbiased estimate the closed-form rule is within 0.0-0.2 `t` of the best response in the field-like world**
  (scenario 2) and within 0.65 `t` in every de-biased scenario I tried (the worst are a noisy estimate with almost fully shared
  errors, and the textbook field). The formula was never the main problem.
- **If our estimate shares the field's low price level and we do not correct it, the same rule loses 1.1-2.7 `t` per valid line**
  (about 500-1,200 EUR per line at the average `t` seen so far). The price level is the first-order parameter.
- **Silent teams** change nothing for `b` (they charge 0). For `a` they add 1.5 × `a` each on a fair charge and nothing on an
  inflated one. Without them income falls by about 5 % and the reviewer side doubles in weight (more charges to review). The best
  shading barely moves (0.75-0.85). Their number is falling (5, 4, 5, 5, 3), so do not build on them.
- **Accept-everything teams** raise the value of an inflated charge, but not enough to inflate on purpose until they are a
  majority of the active field (scenario 7 still prefers a fair charge).

### A6. Value of information, measured on the real field

`scripts/field_replay.py` **[opened: public rows, games 1-5]**. Our `a` and `b` are replaced by `k ×` a noisy estimate of the
bracket value and replayed against the real acceptance limits and real charges, opponents fixed. Nine valid lines.

| our log error sd | best `a` multiplier | issuer income per valid line (× `t`) | best `b` multiplier | reviewer regret (× `t`) |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 1.00 | 15.6 | 1.00 | 0 |
| 0.15 | 0.80 | 10.9 | 1.10 | 0.38 |
| 0.30 | 0.70-0.75 | 8.7 | 1.20-1.35 | 0.55 |
| 0.50 | 0.70 | 7.0 | 1.50 | 0.69 |
| 0.30 and 26 % low (uncorrected) | 0.95 | 8.7 | 2.00 | 0.56 |

Three consequences. Halving the error from 0.30 to 0.15 is worth 2.2 `t` on the issuer side and 0.17 `t` on the reviewer side:
**issuer accuracy is worth about ten times reviewer accuracy.** The payoff has a cliff at `t`: at 0.9 `t` a line earns 13.7, at
1.1 `t` it earns 1.5. And `b = 0` on a valid line costs 1.79 `t`, accepting everything 0.94 `t` plus whatever the unseen inflated
charges were (they could be at the cap), so there is no safe "no information" setting for `b`.
Caveat: on six of nine lines the bracket has no upper end and I used the lower bound as `t`. That removes charges "just above
`t`" by construction and biases the best `b` multiplier upward. Section A4's formula does not have that problem and gives 1.0-1.3.

### A7. What the 1.5× penalty does

It sets the reviewer's break-even at one third (A3). It makes strictness expensive: active opponents wrongly rejected 20 %, 26 %,
61 %, 60 % and 40 % of each other's fair charges in games 1-5. And it turns every strict or silent reviewer into extra income for
a fair charge: about 62 % of the top three teams' issuer income in games 1-5 is penalty money. That is why being fair and high beats everything else.

### A8. Should `a` be shaded?

Yes, relative to an *unbiased* estimate, by about 20-25 % (A3, A6). No, relative to a median that is already low. The decision
variable is the fair rate of our own charges: at the optimum 84-93 % of them are fair. So far 7 of 9 were fair (78 %), and both
failures were rule misses, not level misses; the seven fair ones sat at 0.46-0.97 of the highest fair charge seen (mean 0.72).
Shading cannot protect against a factor-3 rule miss, and it is too deep for the ordinary error.

### A9. The excluded-line "free option"

On a line with `t = 0` a positive charge earns `a × A(a)` and can lose nothing. On the seven lines where no fair charge was seen,
the number of accepted opponent pairs per line was 5, 0, 0, 0, 0, 13, 12: nothing where the exclusion is obvious, something where
the line is small and looks payable. It paid us 954 EUR in five games. The stronger reason to keep it is that it hedges our own
validity call: if we are wrong about an exclusion, the charge earns the full fair income. So `a` should ignore `P(valid)`, which
is what the bot does. Disclose it in the write-up.

### A10. What the rank-scaled 70 % implies about risk

Twelve teams, 70/11 = 6.4 points per rank, about a fifth of the whole jury budget per rank. Our per-game net has a standard
deviation of about 3.3k; over the 95 remaining games that is about 32k of noise against expected differences between active teams
of about 1k per game, so about 95k. **Play for expected value now.** Risk matters only in the last 5-10 rounds, relative to the gap
to the neighbouring ranks: take variance when just behind, shed it when just ahead. Two smaller points: a mistake on `b` pays a
direct rival (a double swing in rank terms), and the two always-silent teams hold the bottom ranks for free, so our rank is decided
among about ten teams.

---

## B. What actually determines `t`

### B1. The four cases I read **[opened: policy.txt, description.txt, invoices.pdf of cases 1-4]**

All policies are editions of one framework, "WD-2026", 40-75 KB each. Each edition hides one or two mechanisms, and the
description states the fact that triggers them.

| game | edition | mechanism that decided the lines | trigger in the description | outcome in the brackets |
| --- | --- | --- | --- | --- |
| 1 | Electrical and Electronic Equipment | appliances without an overvoltage protective device are paid at **one half**; an appliance sub-limit of 5,000 (not binding); call-out and diagnostic charges are "not a repair cost" | "nothing on that circuit was on a surge-protected strip" | line 1 paid at half; line 2 zero |
| 2 | Portable Equipment, Repair and Replacement | examination cost is its own insured head (capped at 250); repair is paid unless it exceeds the replacement amount; pre-existing condition is not damage | "bought for about 1,400", "the two repairs came to nearly that, most of it for the display", "still less than a new one", "scuff was there before" | lines 1-2 paid, at or above the highest charge any team got through (cheap models' medians 12-20 % below that); line 3 zero; line 4 small and paid |
| 3 | Accidental Damage and Optional Glazing | glazing is an optional peril; if it is not agreed, the pane, its fitting **and the drilling for it** are out; timber parts are paid; one attendance per undertaking is paid | "accidental damage claim on the home contents cover", "two kinds of damage on the one cabinet" | lines 1-3 zero, 4-5 paid, vehicle costs tiny |
| 4 | Mobility Equipment and Recovery | a **500 EUR aggregate sub-limit** for cycles, covering repair and recovery together, applied **rateably** to the lines | "we did not have anything listed individually, the bike included" | the three brackets are consistent with a sum of 500; every team's charge on the 3-piece recovery line was inflated |

Game 5: I only have the rows (one line, large value); the case is not decrypted in this checkout.

### B2. Deterministic given the documents, versus noise

- **Validity (zero or not): deterministic and already solved.** Mean P(valid) over all saved cheap-model answers is 0.01-0.13 on the
  five clearly excluded lines and 0.65-0.92 on valid ones **[opened: runs/bench/results]**; the strong ensemble gives 0.01-0.09 and
  0.72-0.93 **[team]**. No money is left here.
- **Policy arithmetic: deterministic, and where the big single losses were.** The halving (game 1) cost us 10k of issuer income and
  3.1k of accepted fraud in one line. The rateable sub-limit (game 4) pins the *sum* of three lines; the models got the sum about
  right (487 against 500 **[team]**) and the split wrong. The split depends on the pre-limit amounts, and probably on the justified
  quantity: "3 pcs" of a recovery for one bicycle looks like a quantity trap (hypothesis, consistent with the brackets, not proven).
- **Anchors in the description: deterministic when present.** Game 2 gives the total of two lines almost literally. The strong
  ensemble's median for the display line lands near the highest fair charge seen; the cheap models stay 12-20 % below it. Nobody
  is known to have charged the anchored total and been paid, so whether `t` reaches it is open.
- **Price level: noise.** For generic items ("TV set", "labour and sundries, flat rate", "vehicle costs") the expert's number
  cannot be derived from the documents. Models priced the small ancillary lines 20-100 % too high and the open repair lines too low.

### B3. Is there a price-level bias, and how large?

The team concluded at 14:52 that the pooled bias is small (0-14 % low). That test used the lower bound as if it were `t`. Six of
nine valid lines have only a lower bound, so that understates it. An interval-censored likelihood is the right tool
(`scripts/censored_bias.py`: each line contributes `P(t_lo ≤ t < t_hi)`), applied to the production ensemble's medians on the
eight valid lines of games 1-4:

| fit | most likely `log(t/median)` | 90 % interval | P(medians are low) |
| --- | ---: | --- | ---: |
| all eight lines | +0.39 (sd 0.39) | +0.12 to +0.87 | 0.99 |
| leaving out one game at a time | +0.30 to +0.50 | lower ends −0.01 to +0.11 | 0.94 to 0.99 |

The sign is stable when any one game is left out; the size is not identified (the upper end is set by my prior). The two lines
with a tight two-sided bracket that are pinned by a limit or are small sit slightly *above* `t`. So the honest statement is:
**on open repair and replacement lines the medians are low, by at least about 12 % and plausibly 30 % or more; on small ancillary
lines and on limit-pinned lines they are not.**

### B4. The accuracy ceiling, and what a perfect reader extracts

Distance of the median to the bracket: 0.08-0.10 log units for the best strong member, 0.2-0.6 for cheap models **[team; opened
for the cheap models]**. Those are optimistic because a one-sided bracket only catches under-estimates. A realistic ceiling for an
LLM pipeline is an error of about 0.15-0.20 on lines with an anchor or a binding limit and 0.25-0.35 on open price lines. That
corresponds to 65-70 % of the available issuer income, against our 55 % and a field median of about 50-60 %.

What the reader has to return, per case:

1. Per line: valid or not, with the clause; the **charge class** (principal work, ancillary to line k, attendance, examination,
   pre-existing, improvement, overhead).
2. Per line: the **justified quantity** and the unit price on the policy's stated basis (here: as new, standard grade).
3. Per line: a **payable fraction** with its clause and the description fact that triggers it.
4. Per case: **aggregate limits** (amount, which lines, rateable or not), caps on a cost head, deductible, "one attendance per invoice".
5. Per case: **anchors** (a stated price or total and the lines it covers).

Items 2 (quantity), 4 and 5 have no place in today's schema; item 3 exists (`payout_fraction`). Python then does the arithmetic.

---

## C. The field (aggregates, games 1-5) **[opened: public leaderboard JSON]**

- **Participation.** 12 teams. Silent per game (charge 0, reject everything): 5, 4, 5, 5, 3. Two teams silent in every game, five in
  at least one. Each always-silent team has lost about 5.2k per game. One team in one game charged nothing but accepted everything.
- **Charges on valid lines.** 56 positive charges by active opponents: 79 % fair. Fair charges relative to the bracket value:
  quartiles 0.66 / 0.77 / 0.89. Six inflated charges were seen at 1.06-2.6 × (median 1.2) and six more were rejected by everyone,
  so their size is invisible. Within one line the active teams' charges have a log spread of only 0.24 (median over lines): **the
  teams are closer to each other than to `t`**, which is what similar LLM pipelines would produce.
- **Reviewers.** Of 59 active reviewer-lines on valid lines, at least 62 % had the limit below `t` (54 % between 0.5 `t` and `t`,
  8 % below 0.5 `t`), 34 % cannot be placed, 3 % were lax (1.5 `t` or more). An active reviewer accepts a charge below 0.85 `t` with
  probability 0.65-0.78, between 0.85 and 1.0 `t` with 0.31, above `t` with 0.23-0.38.
- **Lines where no fair charge was seen (7).** Active opponents still charged on 33 of 43 issuer-lines, so most of the field uses
  the free option, by design or by not classifying. As reviewers they rejected everything on 33 of 43.
- **Learning.** Share of fair charges by game: 60, 76, 90, 75, 88 %. Median fair charge relative to the bracket: 0.54, 0.77, 0.78,
  0.71, 0.81. After game 1 there is no clear trend in charges. Reviewers got stricter (wrong rejections 20 → 60 %, then 40 %).
- **Profit.** After five games we are 3rd of 12 with 14.3k; the top three average about 19k and the median team is at about 4k. Comparing the top three active
  teams with the other active teams after game 4 (before late joiners distort it): income 28.0k against 19.1k, cost 12.7k against
  14.9k. **Four fifths of the gap is issuer income.** The top three paid *more* penalties than the rest (2.7k against 2.0k) and
  much less for inflated charges (0.5k against 3.0k). With 8-10 active teams, rank correlations between net and either component
  are not distinguishable from zero.
- **Issuer efficiency** (income on valid lines divided by income at `a = t`): after game 4 the active opponents were at
  0.33-0.68, median 0.58, and we at 0.49; after game 5 we are at 0.55.
- **Copying or shared code.** Two of 76 positive charges coincide exactly with another team's on the same line. No evidence of a
  copy-the-market strategy (it would also be impossible, since charges are submitted blind).

**What they are probably doing.** One LLM call per case with a prompt of the same kind as ours: the tight clusters and the common
low level point to that. A minority submit charge and limit near the same number; most have the limit at or below their own
estimate. One or two teams sometimes submit values far below the cluster, which looks like a per-unit or net amount.

**What can be beaten or exploited.** (1) Strict and silent reviewers pay 1.5× on fair charges, so a fair charge close to `t` is
the whole game; the field leaves 30-70 % of that on the table. (2) The field's charges are low, so a limit a little above our own
median accepts nearly all fair charges at face value while the field pays penalties on them. (3) Lax reviewers are too few to
inflate against. (4) On small ancillary lines a few reviewers accept as-if prices; the free option collects that.

**Our own replay** (`scripts/field_archetypes.py`, opponents fixed):

| error type | games 1-5, EUR |
| --- | ---: |
| issuer income collected on valid lines | 35,306 |
| issuer income available at `a = t` | 63,754 |
| lost because our own charge was inflated (2 lines: halving missed; small diagnostic over-priced) | 10,896 |
| lost by charging below `t` on fair lines | 17,552 |
| reviewer: penalty excess on wrongly rejected fair charges | 2,616 |
| reviewer: paid for inflated charges (3.1k of it in game 1) | 4,219 |
| free-option income on lines where no fair charge was seen | 954 |

---

## D. Critique of the current approach

### D1. The live bot

1. **The depreciation instruction is wrong for these policies** (`estimator.py` INSTRUCTIONS and three field descriptions in
   `schema.py`). The policies pay replacement as new, or of the same kind, quality and specification; depreciation appears only
   for the special case where reinstatement is omitted **[opened]**. Under the current prompt the cheap models sit 0.15-1.1 log
   units below the game-1 bracket,
   and the strong ensemble's median is about 0.7 of it. Replace it with "apply the valuation basis the policy states".
2. **The schema cannot express what decided games 2 and 4**: aggregate limits with rateable sharing, anchors, and a quantity
   that is checked rather than copied. `payout_fraction` is per line and cannot represent a limit across lines.
3. **`a` and `b` imply different beliefs** (executive summary point 5). After the 14:39 change `b` is at least 1.25 × median while
   `a` stays near 0.78 ×. Either the medians are low or they are not.
4. **`B_VALID_MULT = 1.25` is applied to every valid line.** On the limit-pinned line of game 4 it accepted two inflated charges
   (573 EUR). The multiplier should depend on whether the value is a market guess or pinned by arithmetic.
5. **18 calls per round (10 plain, 8 with web search), 12 of them on the three largest models**, each reading 10-19k tokens of
   policy plus a photo (this needs the Anthropic key to be set; without it the Claude members are skipped).
   The team's own replay says one Fable call is as good, and that the web members are worse **[team]**. I could not measure the
   token cost (the live logs are not in this checkout); a rough guess is 10-20 times the cost of the single-call design.
6. **The final submission depends on arrival order.** `on_update` resubmits after every member, so what stands at the deadline
   is whatever subset finished. It should be the best available answer by a fixed priority.
7. **No safety tier.** If the providers stall there is no submission, and a missed round costs about 5k plus the 3k we normally
   make. A 2 % miss rate costs more than most tuning gains.
8. **The elicited p10/p90 does almost nothing.** `a`/median is 0.74-0.80 for any σ and `b` is now floored at a multiple of the
   median. Keep it for logging; do not build pooling rules on it.
9. Still right, keep: the facts/arithmetic split, structured output, `b = 0` when P(invalid) ≥ 1/3 (the break-even for accepting a
   cluster of charges is P(valid) > 2/3, same number), charging excluded lines as if valid, the watch loop.

### D2. The benchmark

- **`b_regret` on a line with no inflated charge is minimised by accepting everything.** On six of nine valid lines the metric
  rewards any over-pricing model. That is why gpt-6.1-terra looked best on game 3.
- **`a_score` drops "uncertain" answers.** A charge above the highest fair charge is excluded when there is no upper bound, so
  over-pricing is never punished (10 of 12 answers were dropped for some rows).
- **It scores the side that holds a fifth of the money.** Use net EUR per game, replayed against the real field
  (`research/ensemble_analysis/analyze.py` does this for the ensemble logs; `scripts/eur_replay.py` does it for the bench answers).
- In EUR, on the 1,018 saved cheap-model line answers of games 1-4 (`scripts/eur_replay.py`, opponents fixed, lower bound as `t`):

  | rule or configuration | replayed net, games 1-4 |
  | --- | ---: |
  | our live bot, actual | 6,694 |
  | `a = b = t` | 35,636 |
  | mean of 14 model × prompt rows, `pricing.py` | 10,079 (range 1,040 to 23,380) |
  | same rows, `a = 0.8 m`, `b = 0.85 m` | 10,989 |
  | same rows, `a = 0.9 m`, `b = 1.3 m` (best cell of the average grid) | 11,915 |
  | same rows, multipliers chosen leave-one-game-out per row | 11,702 (better than `pricing.py` in 7 of 14 rows) |

  The spread between configurations on the same four games is a factor of 20. Multipliers are worth about +10-18 % on average
  and are not reliably learnable *per model* from three games.
- **Prompt v1 against v2, single model, mean per game** (fixed rule): 5,146 / 3,076 / 2,971 / 821 against 4,851 / 2,955 / 2,624 /
  854. No difference. I agree with the team: v2 did not replicate.
- **Ensembles of cheap models.** The median over seven models with v2 looks 60 % better in total, but all of that comes from games
  1-2, which v2 was written on (10,968 and 8,020 against 4,851 and 2,955); on games 3-4 it is 2,510 and 691 against 2,624 and 854.
  Not evidence.

### D3. The other findings

- **Web search: drop.** Worse in the team's replay, slower, most tokens. The expert value is not a shop price.
- **DSPy/GEPA: drop.** It memorised labels on three cases. With 100 games total there will never be enough held-out cases to
  trust an optimised prompt during the tournament, and the hours are worth more elsewhere.
- **Retrieval over past lines: not yet.** The team's test is within noise and shows the real risk (the same item word is paid in
  one edition and excluded in another). Revisit at 15-20 games, keyed by edition and charge class.
- **Bias correction from past brackets.** My leave-one-game-out test on the cheap-model answers (`scripts/logo_bias.py`): mean
  absolute log error 0.35 uncorrected, 0.33 with one multiplier per model (better in 10 of 21 rows), 0.39 with two multipliers by
  line size. **A per-model point correction does not work yet.** What does hold is the sign for open lines (B3). Too little data
  for more, and the team's reading "the shared bias is small" is as unsupported as "it is 40-55 %".
- **"Price-level bias dominates."** Half right. On the reviewer side and for cheap models, model-to-model spread dominates. On
  the issuer side the two largest single losses were rule misses, and the systematic loss is the low level on open lines.

---

## E. The recommendation

### E1. Information sources

| source | verdict | evidence |
| --- | --- | --- |
| policy text | essential, read in full by one strong model | decided zero or not on 5 of 16 lines and the arithmetic in 2 of 4 read cases |
| description | essential; it carries the trigger fact for every mechanism | all four read cases |
| photo | unproven; keep it out of the fast call, test it for the main call | no line in cases 1-4 turns on something only a photo could show, as far as the texts go; I did not inspect the photos |
| past brackets as a price book | not yet | team's test within noise; misleading-anchor risk |
| past brackets for two multipliers | yes | B3, D2 |
| web search | no | team's replay |
| paragraph diff against earlier policies | cheap experiment | policies of games 2 and 3 share 61 % of their paragraphs; 42-79 % of a policy is new so far. Marking new paragraphs and every paragraph with an amount or a fraction would point the reader at the edition's own clauses. Untested. |

### E2. Models and structure

- **Main reader: `claude-fable-5-2`, low effort, one call.** Replayed net over games 1-4: 22.4k (low), 22.7k (medium), against
  21.0-21.8k for the 20-member ensemble **[team]**. Low and medium are indistinguishable, so take the faster one.
- **Standby on a second provider: `gpt-6.1-terra`, medium** (20.3k alone **[team]**, bias of the opposite tendency). Use its answer
  only if the main call is missing at the cut-off. Averaging the two was not better than Fable alone (22.0k against 22.4k **[team]**).
  One refinement worth testing offline: where the two disagree by more than a factor 1.5 on a line, charge the lower and accept up
  to the higher.
- **Fast tier: `gpt-6-luna`, low effort, text only**, 11-16 s on these policies at about $0.002 **[opened: bench logs]**.
- **No judge, no pooling, no size weights.** Nothing measured supports them.
- **Decomposition** (a policy reader in parallel with a small price panel that sees only invoice and description) is attractive
  on cost, but untested. Do not build it before experiment 1 below is done.

That is 3 calls per round instead of 18, one of them on a flagship model.

### E3. From the reader's answer to `a` and `b` (Python)

```
m_i   = justified_qty_i × unit_price_p50_i × (1 + vat_i)        # as new, standard grade
m_i  *= payout_fraction_i
for each aggregate limit (L, lines G, rateable):                 # sub-limit, cost-head cap
    if sum(m_i for i in G) > L:  m_i *= L / sum(...)  for i in G;  pinned_i = True
for each anchor (total T, lines G):                              # stated total in the description
    scale m_i (i in G) so they sum to T;                           pinned_i = True
a_i = KA[pinned_i] × m_i                    # every line, also those we think are excluded
b_i = 0 if P(valid_i) < 2/3 else KB[pinned_i] × m_i
```

Starting values: open lines `KA = 0.90`, `KB = 1.25`; pinned lines `KA = 0.85`, `KB = 1.05`. In today's terms that is
`CHARGE_MULT ≈ 1.15` on open lines and the existing `B_VALID_MULT` on open lines only.

- Why 0.90: the optimum on an unbiased estimate is 0.75-0.80 (A3, A6) and the medians are low by at least 12 % (B3); 0.78 × 1.15 =
  0.90. At 0.90 × the ensemble median all six open lines of games 1-4 would still have been fair. Move to 1.0 only if the next six
  or more open-line charges are at least 85 % fair.
- Why 1.25: A4 with medians 15-22 % low. Why 1.05 on pinned lines: A4 with no bias and a small own error.
- Silent teams need no special rule. Do not inflate against lax teams.
- Excluded lines: same `a` as if valid. Never above `4 ×` our median, so that the cap cannot bite.

### E4. The calibration loop (after every round, about two minutes after the start)

1. Fetch our own rows. For each of our charges: fair or inflated (visible whenever one reviewer rejected it). For each charge
   we received: accepted, wrongly rejected, rightly rejected.
2. Rebuild the brackets (in memory, as today) and append them to the gitignored labels file.
3. Replay the saved answer of the production reader with a grid of (`KA`, `KB`) per line type. Every five games move each
   multiplier **halfway** to the leave-one-game-out optimum, within `KA ∈ [0.80, 1.10]`, `KB ∈ [1.0, 1.5]`.
4. Refit the censored bias (B3) and log it; it is the evidence for the direction of the move.
5. Two alarms: our fair rate on open lines below 75 % over the last 10 lines (lower `KA` by 0.05 at once), and any round in which
   our rows show all zeros (the submission failed).

A version that uses **only our own rows** exists and is safe under any reading of the rules: raise `KA` by 1.2 % after each fair
charge, lower it by 6.6 % after each inflated one (target fair rate 85 %) **[memory: adaptive conformal inference, Gibbs and
Candès 2021, the team lists arXiv 2106.00170 as existing; I did not open it]**.

**Fair-play check, please do it:** `GAME_DESCRIPTION.md` lists "read other teams' submissions, extract the secret thresholds"
under attacks on the platform. The transaction rows are published by the organisers, and the user has decided that reading them
is acceptable. Reconstructing every team's `a` and bracketing `t` from them is still close to that wording. One line to the
organisers settles it; if the answer is no, use the own-rows version.

### E5. Timeline inside the 60 seconds

| time | step |
| --- | --- |
| T − 60 s | pre-flight: games list reachable, one-token ping to each provider, zip present, clock offset |
| T + 0-3 s | key (poll every 0.25 s), decrypt, invoice text; start all three calls at once |
| by T + 15 s | fast tier answer → submit (tier 1) |
| by T + 40 s | main reader → rule engine → submit (tier 2, overwrites) |
| T + 45 s | if the main reader is missing: submit the standby's answer |
| T + 52 s | last possible submit; nothing after it |

The standing submission is always the best available by priority main > standby > fast, never "whatever arrived last". If nothing
has arrived by T + 30 s, alert a human.

### E6. Reliability

Two providers; a supervisor that restarts the loop; the machine must not sleep during the night (22 hours); one submitting
process only, a second machine may watch but must not submit unless the first one's heartbeat is gone; assert before every submit
that the indices equal the printed `POS.` numbers, that every value is finite and non-negative, and that the sum of `a` over a
limit group does not exceed the limit; keep the per-round log with token usage.

### E7. Keep, change, drop

| | item | expected effect | risk |
| --- | --- | --- | --- |
| keep | model reads, Python computes; structured output; `b = 0` below P(valid) 2/3; free option; watch loop; out-of-sample discipline | | |
| change | remove the depreciation instruction, state "apply the policy's basis" | fixes a 20-30 % under-valuation on replacement lines | none |
| change | schema: justified quantity (checked), aggregate limits, anchors, `pinned` flag; arithmetic in Python | +1-2k per game if it prevents half of the rule misses (they cost 10.9k + 4.2k in five games) | parsing failures; test offline first |
| change | `KA` 0.78 → 0.90 on open lines | +10-15 % issuer income on those lines, about +0.5-1k per game | a line flips to inflated; bounded by the alarm in E4 |
| change | `KB` 1.25 on open lines, 1.05 on pinned ones | +0.1-0.3k per game | small |
| change | 18 calls → 3 | same replayed score, far fewer tokens, deterministic final answer | the single reader has an off round; standby and replay cover it |
| change | benchmark metric → net EUR per game, replayed, leave-one-game-out | stops rewarding over-pricing | none |
| add | fast tier, priority-ordered final submit, alarms | avoids about −8k per missed round | none |
| drop | web members, size weights, belief pooling on σ, per-model bias corrections, DSPy/GEPA | time and tokens | none |
| later | retrieval and price book, at 15-20 games | unknown | misleading anchors |

### E8. The three experiments that would most change the plan (next two hours)

1. **New reader schema against the current prompt, same model (Fable low), on cases 1-5 offline, scored in net EUR by replay.**
   Does it get the halving, the 500 split and the game-2 anchor without breaking the rest? Promote it only if it also wins on
   the games released after it is frozen. This decides the largest item.
2. **Single reader against the ensemble, forward.** The logs already contain every member's answer. From now on record per game
   what Fable alone, Fable with Terra as standby, the ensemble without web and the full ensemble would have earned. Switch the
   live bot to "no web" immediately (the team's own numbers favour it) and to the single reader once it is level or ahead over
   eight more games.
3. **`KA` and `KB` by line type, forward replay.** For every new game replay `KA ∈ {0.8, 0.9, 1.0}` and `KB ∈ {1.0, 1.25, 1.5}`,
   separately for open and pinned lines. No live randomisation is needed, because the replay against the real field is a
   counterfactual for our side.

### E9. What I could not verify

- The true `t` on any line; six of nine valid brackets are one-sided.
- That game 4's values sum to 500, and that the quantity on its first line was cut (both consistent, neither proven).
- Latency and token cost of Fable and Terra on these policies (the live logs are not in this checkout).
- Whether the photos ever matter. Whether the price panel decomposition works.
- Case 5 (not decrypted here). The cap floor. Whether silent teams stay silent.
- Whether the organisers accept bracket reconstruction from public rows (E4).
- All replay numbers hold opponents fixed and use five games. The strong-model numbers are the team's, not recomputed by me.

---

## F. The jury story this approach supports

1. **Method.** One model call reads the policy and the claim and returns facts per line: valid or not, justified quantity, unit
   price, payable fraction, limits, anchors. Deterministic code turns them into the fair value, the charge and the acceptance limit.
2. **Uncertainty.** We never see `t`, only a bracket per line from the settlements. We fit the price level with an
   interval-censored likelihood and set two multipliers from the payoff matrix: charge where about 85 % of our charges are fair,
   accept where a charge is fair with probability two thirds given what the field charges.
3. **Evidence.** After every round we replay our saved answer against the real settlements in EUR and keep only changes that
   win on games released after the change was frozen. Three of our own ideas failed that test and were dropped: a rewritten
   prompt, web search, and prompt optimisation, which had memorised the labels.
4. **What we learned from the data.** The game is decided on the charging side, four to one. With `t` known the best play is
   `a = b = t`; everything else is estimation. Our two largest losses were misread policy clauses, not prices.
5. **Economy.** Three calls per round, one of them on a large model. We ran eighteen to twenty for a while, measured that one
   did the same, and removed the rest. Tokens per round are logged.
6. **Reliability.** A fast first submission by second 15, the full answer by second 40, a second provider on standby, a fixed
   priority for the final answer, checks on indices and limits before every submit.
7. **Honesty.** Five games in we were third, collecting 55 % of the issuer income that was available. Our brackets are one-sided
   on most lines, so our bias estimate has a known sign and an unknown size. We charge lines we believe excluded, because a
   rejected inflated charge costs nothing and it protects us when our exclusion call is wrong; we say so here.
8. **Weaknesses.** Generic items have a price we cannot derive; a clause the reader misses still costs a full line; and all
   replays hold the other teams fixed.

---

## Addendum: game 6 (15:08 CET, not used for any number above)

One line, value in the high hundreds. Eleven teams were active and one silent, so the silent-team subsidy is nearly gone
(silent per game: 5, 4, 5, 5, 3, 1). All ten opponent charges were fair, with a median of 0.62 of the highest fair charge;
39 % of those fair charges were still wrongly rejected by other active reviewers.

Our charge was fair at **0.50** of the highest fair charge. Issuer income 4.9k against 12.1k at the highest fair charge (more if
`t` is above it). Our net for the game was +5 EUR, 8th of 12 in that game. If the charge was the usual 0.78 × median, the median
was at most 0.64 of `t`, a ninth valid line for B3 and again on the low side (`log(t/median) ≥ +0.44`). On the reviewer side
we still wrongly rejected fair charges (penalty excess 372) even with `b = 1.25 × median`.

Updated totals for our replay over games 1-6: collected 40.2k of 75.8k available on valid lines (53 %); lost to inflated own
charges 10.9k, to charging below `t` 24.8k; reviewer penalties 3.0k, inflated charges paid 4.2k. We remain 3rd of 12.

What it changes: nothing in the recommendation, but it raises the urgency of the issuer side. One game is one game. Counting
games 5 and 6 from our actual charge, the production median sat clearly below the highest fair charge any team made on four of
eight open lines and within about 6 % of it on the other four; on none is it known to be above `t`. Game 6 is the first of
these lines released after I had fixed the claim. With eleven active teams the reviewer side also gains weight (more charges to
review each round), as scenario 5 of A5 predicts.

---

## Appendix: scripts (no data inside; rows stay in a scratch folder outside the repo)

| script | what it does |
| --- | --- |
| `scripts/fetch_public_rows.py` | reads the public leaderboard endpoints into a `/private/tmp` folder, one request per second; refuses any other target |
| `scripts/field_reconstruct.py` | per line: bracket, each issuer's charge, each reviewer's acceptance bracket (in memory) |
| `scripts/field_aggregates.py`, `field_archetypes.py` | the anonymous aggregates of section C and our own replay |
| `scripts/field_replay.py` | value-of-information tables of A6 |
| `scripts/eur_replay.py` | net EUR replay of the saved bench answers, with leave-one-game-out multipliers (D2) |
| `scripts/logo_bias.py` | leave-one-game-out point bias correction (D3) |
| `scripts/censored_bias.py` | interval-censored bias fit (B3) |
| `scripts/sim_first_principles.py` | population simulation (A5) |
