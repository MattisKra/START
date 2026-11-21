# Claim to Fame: Game Description

Converted from `pdf/GAME_DESCRIPTION.pdf` (QuantCo, 5 pages). Wording preserved; emoji and layout removed. This is the
**authoritative rules document** (it supersedes the slide deck where they differ; see "Differences from the slides" at the end).

## Scenario

In insurance, a claim is a request by a policyholder asking for payment or financial compensation. After property damage or a car
accident, tradespeople such as handymen and repair garages issue invoices. Policyholders submit these invoices to their insurance
providers, which decide whether to pay.

Not everyone is honest, so for each invoiced item the insurer must judge whether it is:

- **Covered** by the policy,
- **Related** to the reported damage, and
- **Reasonably priced** ("total" price per line item = quantity × unit price).

A fraudulent claim fails one of these: it isn't insured, the item is unrelated to the case, or the price is inflated.

## Your task

Compete against other teams in rounds. Goal: a) maximize the money you make and b) do so with style.
You take on two roles simultaneously:

| Role | What you do |
| --- | --- |
| Invoice Issuer (Handyman) | Set the price (= quantity × unit price) for each line item on the invoice that you think you're entitled to. If you set a fair price, you get your money. |
| Insurance Claim Review Handling | Review incoming invoices and minimize the amount your team pays. Spot fraudulent items and set a maximum fair price above which you reject payments. |

Each round you submit the prices **a** and **b** for all items; your submissions are matched against all other teams.

> You can't charge or pay whatever you like. There is a fair value threshold **t** for each item. If you reject a request that was
> at or below this value, you get a penalty.

## The game

Every TODO minutes, starting at TODO, a case is released (the deep-dive slides say: every ~13 min, 2 pm to 12 pm next day).
You then have **exactly one minute** to submit. Once released you can fetch a decryption key from the API and decrypt the `.zip`.
Each case consists of:

| File | Contents |
| --- | --- |
| `policy.txt` | An insurance policy describing what is covered |
| `description.txt` | A damage description explaining the claim |
| `invoices.pdf` | An invoice containing line items **without prices** |
| `images.png` | Some cases might also contain images (actual files are named `photo.png`, `photo.jpg`, `photo1.png`, `photo2.png`, ...) |

For every line item set two values:

- **Charge price (a):** the amount you charge opposing teams. **Default: 0**
- **Acceptance limit (b):** the maximum amount your team is willing to accept and pay when receiving the same line item from
  another team. **Default: 0**

> **Always submit the brutto Gesamtbetrag.** Both a and b must be the **gross total (including VAT) for the whole line item**.
> Never the net amount, never a per-unit price.

There is a secret threshold **t** = the maximum price a claims expert would consider appropriate. For line items **not covered by the
policy: t = 0**.

## Payoffs

H = the handyman who issues the invoice, I = the insurance doing claim handling.

- **Fair zone (a ≤ t):** the charge is legitimate, H is entitled to the money. I should accept: accepting pays the fair a, while
  rejecting still owes H the a plus 0.5a in damages, also paid to H.
- **Fraud zone (a > t):** the charge is inflated, H is owed nothing. I should reject: rejecting means no money flows, accepting
  hands H the fraudulent amount.

**Accepted-payment cap.** Each line item has a secret payment cap **c, shared across all teams, where c ≥ 4t (and never below an
absolute floor)**. If a charge is accepted, the insurer pays and the issuer receives min(a, c). This prevents winning through a
single exorbitant charge.

| | a ≤ t: price okay | a > t: price fraudulent |
| --- | --- | --- |
| **a ≤ b** (accepted) | I pays a, H gets a | I pays min(a, c), H gets min(a, c) |
| **a > b** (rejected) | I pays 1.5a, H gets 1.5a | I pays 0, H gets 0 |

## Example round (three teams, one line item: windshield, t = 100)

| Team | Charge a | Acceptance limit b |
| --- | ---: | ---: |
| Alpha Squad | 100 | 130 |
| Beta Dynamics | 150 | 90 |
| Delta Strategies | 100 | 110 |

Every team is matched against every other team in both roles, giving six transactions:

| Issuer (H) → Reviewer (I) | a | b | a ≤ t? | a ≤ b? | Outcome |
| --- | ---: | ---: | --- | --- | --- |
| Alpha → Beta | 100 | 90 | fair | reject | Wrongful reject: Beta pays 1.5a = 150, Alpha gets 150 |
| Alpha → Delta | 100 | 110 | fair | accept | Delta pays 100, Alpha gets 100 |
| Delta → Alpha | 100 | 130 | fair | accept | Alpha pays 100, Delta gets 100 |
| Delta → Beta | 100 | 90 | fair | reject | Wrongful reject: Beta pays 150, Delta gets 150 |
| Beta → Alpha | 150 | 130 | fraud | reject | Rightful reject: no money flows |
| Beta → Delta | 150 | 110 | fraud | reject | Rightful reject: no money flows |

Net (gets − pays): Alpha gets 250 / pays 100 = **+150**; Delta gets 250 / pays 100 = **+150**; Beta gets 0 / pays 300 = **−300**.
Lesson in the document: Beta loses on both sides (overcharged, so its charges were rightfully rejected; and its b = 90 < t wrongfully
rejected fair claims, paying 1.5a twice).

## Game setup

1. **Register.** You obtain a unique, unchangeable team key. Do not share it outside the team (others could trade on your behalf).
2. **Get the cases.** Download the folder from the shared Drive. It contains one encrypted `.zip` per case, including a **test case
   (case 0)**. Together with `starter_script.py` you can use the endpoint to check that requests are well-formed. The endpoint accepts
   any well-formatted JSON. Details: `API_HANDBOOK.md`.

## Fair play

- **No cross-team collaboration.** Do not coordinate prices, acceptance limits or strategies with other teams, and do not share
  your analysis of a case with them.
- **No sharing keys or credentials.** Never submit on behalf of another team or let another team submit on yours.
- **No attacking the platform.** Do not try to obtain decryption keys before release, read other teams' submissions, extract the
  secret thresholds, or otherwise probe, overload or exploit the API and its infrastructure.
- **Anything inside your own team is fair game:** build tooling, use LLMs, do stuff manually, research the domain.

Cheating gets the team disqualified. If unsure, ask the organizers.

## How to win

- **70 % score:** cumulative net payoff across all games, as shown on the leaderboard.
- **30 % presentation and method:** each team pitches its approach and hands in a short write-up (max. 1 page) shortly before the
  challenge ends. "We value sound, well-founded and resourceful approaches over brute force."

Details: `EVALUATION_CRITERIA.md`.

## What you need

`starter_script.py` (Python) implements the flow for test case 0. Needs `TEAM_API_KEY` and `OPENAI_KEY` as environment variables,
packages `requests` and `openai`, and 7-Zip (the script calls it to decrypt).
Easy way: `pixi.toml` pulls in Python, both packages and 7-Zip: `pixi install` then `pixi run python starter_script.py`.
Manual: `pip install requests openai`; install 7-Zip so `7z` is on PATH (macOS: `brew install p7zip`).

"It makes sense to decide on one person to actually run and submit the script. **Later submissions overwrite earlier ones.** Also
think about how you will schedule future runs, as new challenges might run throughout the entire tournament."

Leaderboard and upcoming games: https://c2f.public.quantco.cloud/leaderboard/

## Differences from the slides (`claim-to-fame-challenge-deep-dive.md`)

| Topic | Slides | This document |
| --- | --- | --- |
| Payment cap | "Payment cap c" with no value | **c ≥ 4t, never below an absolute floor**, secret, same for all teams |
| Example | Beta a = 120, b = 90 → Alpha +30 / Delta +150 / Beta −180 | Beta a = 150, b = 90 → +150 / +150 / −300 (different numbers, same rules) |
| Photo file name | `images.png` | same, but real files are `photo*.png/jpg` |
| Round timing | every ~13 min, 2 pm → 12 pm | "every TODO minutes, starting at TODO" (unfilled) |
