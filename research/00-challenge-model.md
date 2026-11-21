# Claim to Fame: challenge model (preliminary)

Status: **preliminary**, written 2026-11-21 ~13:45 CET, **updated ~13:55 with the QuantCo materials** (`../materials/`: authoritative
`GAME_DESCRIPTION.md`, `EVALUATION_CRITERIA.md`, `API_HANDBOOK.md`). The 101 case zips are in hand but encrypted (keys come per round),
so **no real case has been read yet**. Sources: the slides ([markdown](../claim-to-fame-challenge-deep-dive.md)) and `../materials/`.
Where they differ, `GAME_DESCRIPTION.md` wins. Items marked *derived* or *assumption* are mine.

**What the materials changed:** (a) cap is `c ≥ 4t` plus an unknown absolute floor; (b) ranking is **rank-scaled** (1st = 70 … last = 0), not
margin-scaled; (c) 30 % of the grade is a jury that rewards **economical, evidenced, honest** methods and punishes "token maxing";
(d) the API has **no results endpoint**: only list / key / submit, so per-line outcomes and `t` are probably never revealed.

## 1. What we submit

For every invoice line `i` of every round, two numbers (gross line total = qty × unit price × VAT, never net or per unit):

| symbol | role | meaning |
| --- | --- | --- |
| `a_i` | handyman | price we bill **every** other team |
| `b_i` | insurer | highest charge we accept from **every** other team |
| `t_i` | hidden | fair value set by QuantCo's claims experts; `0` if excluded by the policy or unrelated to the damage |

Slide 4 payoff, per ordered pair (handyman H → insurer I), per line:

| | `a ≤ t` fair | `a > t` inflated |
| --- | --- | --- |
| **accepted** (`a ≤ b_I`) | I pays H `a` | I pays H `min(a, c)` |
| **rejected** (`a > b_I`) | I pays H `1.5·a` | nothing |

Zero-sum between teams. Score = money received as handyman − money paid as insurer, summed over all other teams, lines and rounds.
Slide 5's worked example reproduces exactly (Alpha +30, Delta +150, Beta −180; checked in `sim/payoff_check.py`).

## 2. Facts that follow directly (derived, checked)

1. **`a` and `b` are separate problems.** `a` only changes what we receive, `b` only what we pay. Both are optimised against
   beliefs about the *other teams* (their `b` for our `a`, their `a` for our `b`). Our own `a` never affects our own payments.
2. **Insurer rule: reject iff P(inflated | charge) > 1/3.** Accept costs `a`; reject costs `1.5·a·P(fair)`. The cap `c` only
   matters when `a > c`, where the break-even rises to 1/2 (`sim/payoff_check.py` §2).
3. **Overcharging has no downside except the lost fair-price income.** A rejected inflated charge pays 0, not a penalty. So `a > t`
   only pays when other teams' `b` are above `t`. With others at `b = 1.5t` the best `a` is `1.5t`; with `b ≤ t` it is `t`
   (`sim/payoff_check.py` §3). For an excluded line (`t = 0`) any positive `a` is a free option on lax insurers.
4. **A wrongly rejected fair charge pays the handyman 1.5×.** So being *strict* with `b` also hurts the team that charged us
   fairly, which is the point of the penalty, but it means other teams' strictness *helps* a fair charger.
5. **Missing a round sets `a = b = 0`** and we still trade (`API_HANDBOOK.md`: omitted lines "still participate in transactions"):
   every fair charge against us costs 1.5×, and we earn nothing. A submission within the first seconds is worth more than a perfect
   one at second 61.
6. **Resubmitting is free; only the last submission before the deadline counts** (upsert, "last write wins"). A fast first answer
   followed by a stronger overwrite is explicitly allowed. Both values must be finite and non-negative (`422` otherwise).
7. **Cap `c ≥ 4t`, shared by all teams, never below an absolute floor.** For normal lines it only limits extreme `a`. For excluded
   lines (`t = 0`) the cap is the floor, so a charge up to the floor can still be paid by a lax insurer. The floor's value is unknown.
8. **Rank-scaled score.** Final points = 70 × (linear in rank). Only the *order* of teams matters, not the margin, so protecting a
   lead is as valuable as extending it, and a big lucky win does not help more than a small one. Zero-sum plus rank scaling means we
   mostly need to beat the median team reliably, every round.
9. **No settlement feedback in the API.** The handbook lists only `GET /list`, `GET /{id}/key`, `PUT /{id}/submissions`. Unless the
   leaderboard shows per-game results, we cannot learn `t` or opponents' `a`/`b` online. Calibration has to be offline and
   self-consistency based (see `01-claimbot-review.md`). This undercuts any plan that fits a bias/spread correction to rejection outcomes.

## 3. Model result worth acting on (assumption-heavy, see `sim/`)

Model: everybody sees `t·exp(σ·ε)` with independent noise, then shades (`a = t̂·e^{−ka}`, `b = t̂·e^{+kb}`).

- Symmetric best-response fixed point: charge **below** the estimate (`ka ≈ 0.08…0.36` for σ = 0.05…0.5, i.e. 70–92 % of `t̂`);
  acceptance limit **about at `t̂`** (`kb ≈ −0.18…+0.06`) (`payoff_check.py` §4).
- The closed-form rule in `claimbot/pricing.py` (`a` = argmax `x·P(T≥x)`, `b` = 1/3-quantile of own belief) is near the model
  optimum for `a`, but **sets `b` too low** (below the median) because it ignores that other teams shade their charges
  below *their* estimates. In the model the best `b` is ~`t̂·e^{+0.10}` and gains 1–5 % of line value per line over the rule
  (`review_pricing_rule.py`). **Hypothesis only**: it depends on how real teams behave, so it needs a measured check (see `01-claimbot-review.md`).
- Because the game is zero-sum, formula-level gains are a few percent of line value. The big levers are **estimator accuracy**
  (is `t̂` unbiased? is the stated σ honest?), **never missing a round**, and **exploiting weak opponents** (lax `b`, `b = 0` rounds).

## 4. Open questions

Resolved by the materials: **cap** (`c ≥ 4t`), **EVALUATION_CRITERIA** (70/30, rubric above), **API shapes** (`decryption_key`, `/list` returns
`id` + `start_time`), **case availability** (all 101 zips in hand, keys per round), **omitted lines** (still trade with 0/0).

| # | Question | Why it matters | Source to resolve |
| --- | --- | --- | --- |
| 1 | Does the leaderboard or any endpoint show per-game / per-line results, `t`, or others' `a`/`b`? | Handbook shows none. If none, no online calibration and only leaderboard deltas as signal. | Look at the live leaderboard after round 1 |
| 2 | Invoice line index: base 1 (handbook examples use 1, 2) and how the invoice labels its lines | A silent off-by-one scores every line against the wrong line. | Decrypt case 0, compare the printed numbering with a Game 0 PUT |
| 3 | Absolute cap floor (matters for `t = 0` lines) | Sets the size of the "free option" on excluded lines. | Ask on Discord; do **not** probe the API for it |
| 4 | Round cadence and count (rules say `TODO`, slides say ~13 min, 2 pm → 12 pm) | 101 zips ⇒ case 0 + ~100 live rounds fits 22 h / 13 min. | `/api/games/list` |
| 5 | Deadline of the ≤ 1-page write-up ("shortly before the challenge ends") | 30 % of the grade. | organisers |
| 6 | Is `t` a hard maximum or a distribution over what experts would accept? | Changes how aggressive `a` can be. | ask Discord (Marvin / Moritz / Simon, tag `[QuantCo]`) |
| 7 | How many teams are playing? | The scale of any gain from exploiting weak `b` / `a`; the rank-scaled score depends on the field. | leaderboard |

## 5. Delivery plan implied by the rules (proposal, not decided)

Tiers, each overwriting the last, always submitting the best finished one before the ~54 s mark (`claimbot/config.SAFETY_MARGIN_S = 6`):

0. **Safety net (≤ 5 s, no model):** any valid submission that avoids `a = b = 0`. Cheap, no images, fixed fallback.
1. **Fast model (≈ 10-20 s):** small / low-effort model, text only.
2. **Strong pipeline (≈ 40-50 s):** full model with photos, calibrated quantiles. Ensembling across providers costs tokens; the jury
   rubric ("no token maxing") means any ensemble must be justified by measured gain per unit cost.
3. **Offline calibration between rounds:** with no settlement feedback (fact 9), tune σ/multipliers from self-consistency across
   samples/models, the 100 cases once decrypted, and leaderboard deltas. Keep a log: "evidence for your choices" is a graded criterion.

`claimbot/` already implements tiers 1 and 2 as a race (`runner.play_round`). Tier 0 and tier 3 are missing.

## 6. Constraints from the rules that are easy to forget

- **One person submits.** Several people submitting overwrite each other ("later submissions overwrite earlier ones"). Decide who owns the key and the scheduler.
- **Keys are team-private;** do not paste them into chats, notes or commits. `.env` is gitignored.
- **Do not probe the API** (key early, read others' submissions, extract `t`). Disqualification. The only sanctioned test target is Game 0.
- **The write-up** (≤ 1 page) must match what we actually ran, strengths and weaknesses stated openly (criterion: clarity and honesty).
