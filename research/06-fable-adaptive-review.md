# Fixed or adaptive? Independent review after game 18

Advisor memo, 21 November 2026, revision `ed0dee4`. Local, read-only analysis: no submissions, no model calls, no leaderboard requests.

> **Timing and scope note from the joint review.** Fable worked from the local game 18 snapshot. Games 19 and 20 had already settled by the time the advice was delivered. The proposed 19–40 block was not frozen before game 19. Later multipliers are unverified because the decision log ends at game 15. The joint review reruns the zero-limit benchmark and an explicit version of the proposed split with complete fields, caps and identical policy text as the family definition. [Results and qualifications](05-adaptive-strategy-review.md)

## Recommendation

**Stop tuning the acceptance factor, and do not adapt it to recent games.** Sixteen games cannot tell 0.55 from 0.9, and no forward-adaptive rule beat a fixed one. Adapt two other things: what we know about the fair value `t` of recurring items, and the charge against the field's measured acceptance.

The advisor proposed the following shadow comparison using the archive through game 18.

| # | Proposed prediction | Falsified if |
| --- | --- | --- |
| H1 | On lines we treat as valid, opponents' charges on **ancillary** lines (disposal, vehicle, call-out, diagnostic, shipping, installation, cleaning, leak detection, flat fees) are fair less than 2/3 of the time. On **principal** lines (the device, part or repair itself) they are fair more than 2/3 of the time. | Either share lands on the wrong side of 2/3, euro-weighted, with at least 40 classified charges per slice. |
| H2 | Shadow limit: `b = 0` on ancillary lines; `b = 1.25 × median` on principal lines whose scenario family has a settled earlier game; `b = 0.55 × median` on principal lines of a new family. Its reviewer cost is below the live rule's. | Its cost interval is not wholly below the live rule's over games 19–40, or it is worse in more than a third of the games. |
| H3 | Picking the factor from past games has no forward value. | Follow-the-leader on the factor beats the best frozen factor by more than €600 per game (the detectable effect, see below). |
| H4 | Charge `1.0 × median` on principal lines with a settled family and `0.6 × median` on ancillary lines, both instead of 0.9. Principal income rises about 11%. | Fewer than 80% of those principal charges are fair, or ancillary income falls. |

Any limit rule must also beat `b = 0` on every line. That benchmark is unbeaten so far (table below). I do not recommend playing it: its whole margin comes from games 7–10.

## Evidence

Method: the official payoff applied to our logged medians and validity (`outputs/model_outputs.json`, games 1–15) against every incoming charge in `runs/bench/labels.jsonl`. Ranges come from two unknowns: charges inside the bracket for `t`, and hidden charges we rejected. Replaying our logged limits returns our actual cost to the cent in all 15 games.

Reviewer cost, games 1–15, in thousand euros (we actually paid 76.4):

| Limit rule | Games 1–6 | Games 7–10 | Games 11–15 | All |
| --- | ---: | ---: | ---: | ---: |
| Reject everything (`b = 0`) | 29.5 | 3.0–3.2 | 22.2 | **54.7–54.9** |
| 0.45 × median | 29.4 | 7.4 | 22.2 | 59.0 |
| 0.55 × median | 29.4 | 8.4–9.1 | 22.3–24.2 | 60.0–62.6 |
| 0.9 × median | 27.0–28.5 | 22.6–23.7 | 18.3–23.6 | 67.9–75.8 |
| 1.25 × median | 24.5–27.0 | 28.2–29.9 | 16.2–24.9 | 69.0–81.8 |
| Follow-the-leader on all earlier games | | | | 65.5 |
| Best factor of the previous game | | | | 60.6–66.3 |
| Best factor of the previous three games | | | | 60.7–65.8 |
| Best factor per game, in hindsight | | | | 44.0–52.9 |
| `b` at the lower end of the `t` bracket | 20.5–21.8 | 2.0–2.2 | 14.8–20.4 | 37.2–44.4 |

- **The factor is not identified.** Per game, 0.55 beats 0.9 in 8 of 16 games and loses in 8 (mean difference −€694, SD €2,647, t = −1.05). Over games 10–16 the mean is +€214 in favour of 0.9. The 82 remaining games can detect about €600 per game at two standard errors.
- **Knowing `t` is worth far more than the factor.** The gap between the best fixed factor and a limit at the bracket is 15–20k; the gap between factors 0.45 and 1.25 outside games 7–10 is at most about 5k and changes sign.
- **Line kind separates the errors, and chronology does not.** On 37 valid-treated lines (games 1–16) our median exceeded the upper bracket end on 16 of 18 ancillary lines. On the 19 principal lines it was below the lower end on 11 and above the upper end on 5. Game 14 alone ranges from 0.52× to 4.4× of the lower bracket end across its four lines.
- **Games 10–16 by slice** (thousand euros; game 16 medians inferred as charge ÷ 0.9): ancillary lines cost 5.5 at `b = 0` against 8.0 at 0.45× and 7.2–11.9 at 0.9×. Principal lines cost 15.2–20.6 at 1.25× against 21.4–22.2 at 0.55× and 21.5 at `b = 0`. Combined, the H2 split costs 20.7–26.1 against 27.0 for reject-all and 29.4–32.1 for 0.55×.
- **The split fails on new principal items.** Over games 1–16 it costs 61.1–68.5 against 59.1–59.3 for reject-all, because games 1 and 9 (electronics, first sightings) had medians 1.7–4.3 times too high. Hence the "new family" guard in H2.
- **Charge side, games 10–16.** At 0.9× and at 1.0× the same 8 of 9 principal charges are surely fair; at 1.1× only 4 are. A fair charge earns more the higher it is, whoever rejects it. Eight of 9 ancillary charges at 0.9× were inflated; at 0.6×, 4 of 9 are surely fair.
- **The field has loosened.** Opponents accepted our fair charges 2–7 times out of 11 in games 2–15 and 6–10 times in games 16–18, so the 1.5× bonus is shrinking. Inflated charges of ours on lines the field treats as valid were accepted 6–8 times out of 11 in games 13–16 (1–4 before).

## Where I disagree

1. **"The field over-charged in games 7–10" is the wrong cause.** In those games our own median was 1.2–5.7 times the upper bracket end, while the field's median charge was 1.0–2.0 times that end. A strict factor helped by cancelling our price error on service, disposal and lump-sum lines. It is a line-level estimation error shared by all readers, not a regime in time, so the next "regime" cannot be read from the last games.
2. **0.55 is described as the chosen default, but it was not what we played.** In games 16–17 every observable limit interval contains our charge (for example line 1 of game 17: limit in [260.11, 280.00), charge 267.21). That fits `b = a = 0.9 × median` and rules out 0.55. Game 18 used round numbers and a different rule. Conclusions about 0.55 "in the current regime" rest on replay only.
3. **"A fixed value is as good as an adaptive one" (`claimbot/config.py`) understates it.** Adaptive was worse than fixed 0.45 by 1.6–7.3k, and every median multiple was worse than rejecting everything. The medians have not yet earned a place in the limit decision; the comment reads as if they had.
4. **The earlier proposal of 1.25× wherever a price reference exists is too broad.** References transfer wrongly across contexts. "Vehicle costs" settled at 12.89–16.06 in game 14 and at 60.42 or more in game 16, where we charged 12.85. The speaker settled below 335.99 in game 9 and at 389.00 or more in game 15. Lump sums are consistent with the brackets of their parts in the two cases I could check (game 10 line 1 against game 8 lines 1–4; game 7 against game 16), so use a reference as a prior within a family and never as a cap.
5. **"Charges above our median are almost always fair" is survivorship.** All 37 known charges above 0.9× our median in games 10–16 were fair, but inflated charges above our limit are hidden. Counting those, games 16–17 had 43 wrongful and 38 rightful rejections above our limit: 53% fair, below the 2/3 needed to accept. The rejections saved at least €3,462 against €3,650 of penalty excess, so a blanket raise is not supported.

## Game theory in three lines

- **Limit:** `b = t` is weakly dominant once `t` is known: accepting a fair charge costs `a` instead of `1.5a`, and rejecting an inflated one costs 0. The field only decides which estimation errors are expensive. This is why the limit should follow evidence about `t` and not the field's recent mood. Under uncertainty, accept at the margin only where P(fair) exceeds 2/3 given that someone charges that amount; that conditional rate is what H1 measures per slice (the winner's-curse logic of Milgrom and Weber, 1982).
- **Charge:** there is no dominant charge. With `A(x)` the share of opponents whose limit is at least `x`, a charge earns `x·(1.5 − 0.5·A(x))` if fair and `x·A(x)` if inflated. Charging `(1+δ)·t` beats charging `t` only if `(1+δ)·A((1+δ)t) > 1.5 − 0.5·A(t)`. With `A(t)` near 0.8 that needs about 0.9 acceptance just above `t`; we observe 0.55–0.73. So do not overcharge on purpose, but the penalty for a near miss has fallen, which supports 1.0× on well-known lines. Track `A` per game from the reviewer-limit intervals the euro evaluator already builds.
- **Adaptation:** follow-the-leader has linear regret when the best action alternates (Kalai and Vempala, 2005), which is what the per-game best factor does here. Bandit bounds (Auer, Cesa-Bianchi and Fischer, 2002) put the games needed to separate two factors at roughly (2 × SD ÷ gap)², which is 58 games for the observed gap and far more for the gap of the last seven games.

## Limits of this review

- Labels cover games 1–16 and our logged medians games 1–15; games 17–18 enter only through our own rows. I did not re-fetch the field, so hidden charges stay as ranges.
- The ancillary/principal keyword list was written after seeing all 16 games. The split itself was first noted after game 8 (`bench/README.md`, 15:50), so games 10–16 are a forward check of the idea but not of my list. Eighteen lines per slice, nine in games 10–16.
- Costs hold the field fixed and ignore the payment cap on charges we did not actually accept.
- Tournament rank is not evaluated. We are 7th, €10.8k behind 6th, with 82 games left: too early for variance-seeking play.
- The three papers are cited from memory and were not re-read for this memo.

Sources: [rules](../materials/GAME_DESCRIPTION.md) · [pricing](../claimbot/pricing.py) · [settings](../claimbot/config.py) · [decision log](../outputs/model_outputs.json) · [our settlements](../past-cases/README.md) · [benchmark log](bench/README.md) · [game 18 review](04-game-18-evaluator-review.md). Analysis scripts were run from a scratch directory and are not committed.
