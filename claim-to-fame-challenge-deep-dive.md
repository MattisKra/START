# Claim to Fame - Challenge Deep Dive

QuantCo Challenge · 10-minute presentation

*Converted from the 10-slide PDF. Slide order and substantive content are preserved; decorative graphics and repeated footers are omitted. Relative dates such as “today” and “tomorrow” are retained from the presentation.*

## Slide 1: Claim to Fame

Rules, payoffs, case files, the API, and the traps to avoid.

## Slide 2: Every invoice line has to pass three checks

| Check | Question | What to verify |
| --- | --- | --- |
| **Covered** | By the policy? | The policy lists what's insured and what's excluded. An excluded item has a fair value of **t = 0**. |
| **Related** | To this damage? | A burst bathroom pipe doesn't explain new kitchen cabinets. Check every line against the damage report. |
| **Reasonable** | In price? | The line total (**quantity × unit price**) must not exceed what an insurance would accept. |

**Fail any one check and the line is considered fraud.** Your job as the insurer: judge every line, in one minute.

## Slide 3: You set two numbers for every line item

### As the handyman: charge price a

What you bill every other team for this line. Aim as close to the fair value **t** as you can, from below.

### As the insurer: acceptance limit b

The most you'll pay when another team bills you.

- **Accept** a charge when **a ≤ b**.
- **Reject** it otherwise (**a > b**).

### Secret fair value t

The fair value **t** is set by the claims experts.

| Zone | Condition | Entitlement |
| --- | --- | --- |
| Fair zone | **a ≤ t** | The handyman is owed the money. |
| Fraud zone | **a > t** | The handyman is owed nothing. |

## Slide 4: Where a falls relative to t decides who pays

| Insurer's decision | a ≤ t: fair price (handyman is owed it) | a > t: inflated price (handyman is owed nothing) |
| --- | --- | --- |
| **Accepted: a ≤ b** | **Right call.** Insurer pays **a**; handyman gets **a**. | **Wrong call.** Insurer pays **min(a, c)**; handyman pockets it. |
| **Rejected: a > b** | **Wrong call.** Insurer pays **1.5 × a**: the price plus a **50% penalty**. | **Right call.** Fraud caught: no money flows. |

- **Payment cap c:** prevents one absurd charge from winning the game.
- **Not covered:** if the policy excludes an item, **t = 0**, and any charge above **0** is fraud.
- **Zero-sum:** every payment goes from one team straight to another.

## Slide 5: Example round - one windshield, fair value t = 100

### Team choices and net results

| Team | Charge price a | Acceptance limit b | Net result |
| --- | ---: | ---: | ---: |
| Alpha Squad | 100 | 130 | +30 |
| Delta Strategies | 100 | 110 | +150 |
| Beta Dynamics | 120 | 90 | -180 |

### Payments between teams

| Handyman → Insurer | a | b | Outcome | Money |
| --- | ---: | ---: | --- | --- |
| Alpha → Delta | 100 | 110 | Fair, accepted: right call | Delta pays Alpha 100. |
| Delta → Alpha | 100 | 130 | Fair, accepted: right call | Alpha pays Delta 100. |
| Alpha → Beta | 100 | 90 | Fair, rejected: wrong call | Beta pays Alpha 150 (penalty). |
| Delta → Beta | 100 | 90 | Fair, rejected: wrong call | Beta pays Delta 150 (penalty). |
| Beta → Alpha | 120 | 130 | Inflated, accepted: wrong call | Alpha pays Beta 120. |
| Beta → Delta | 120 | 110 | Inflated, rejected: right call | Nothing: fraud caught. |

**Delta wins: it charged t and accepted only a little above it.**

## Slide 6: What's inside each case

| File | Contents and use |
| --- | --- |
| `description.txt` | The damage report: what happened and what's damaged. Hold every invoice line against it. |
| `policy.txt` | The insurance terms: coverage and exclusions. Excluded item → **t = 0**. |
| `invoices.pdf` | The line items with quantities and units, but **no prices**. Pricing them is your job. |
| `images.png` | Optional photos of the damage. Do they match the story? |

### Submit the gross line total

Always submit the **gross amount: quantity × unit price, VAT included**. Never net, never per unit.

Illustrative example: **18 m²** of laminate at **€50/m² net**, with a VAT multiplier of **1.19**:

```text
18 m² × €50 × 1.19 = €1,071
```

Submit **one a and one b per line item**, matched by its **index on the invoice**. A line you leave out counts as **a = 0 and b = 0**.

## Slide 7: Each round - one minute, four steps

1. **Find the next round.**

   ```http
   GET /api/games/list
   ```

2. **Fetch the key when it starts.**

   ```http
   GET /api/games/{id}/key
   ```

3. **Decrypt with 7-Zip and analyze.**

   ```sh
   7z x <case>.zip -p<key>
   ```

4. **Submit before the minute is up.**

   ```http
   PUT /api/games/{id}/submissions
   ```

### Submission format

```http
PUT /api/games/{id}/submissions
X-API-Key: <your team key>
```

```json
[
  {"index": 1, "charge_price": 50.0, "acceptance_limit": 80.0},
  {"index": 2, "charge_price": 120.0, "acceptance_limit": 150.0}
]
```

- **Test anytime:** Game **0** is always open and stores nothing.
- **Resubmit freely:** the **last submission before the deadline** counts.
- **Starter kit:** `starter_script.py` and `pixi.toml` are in the materials.

## Slide 8: Five ways to lose money fast

1. **Submitting net or per-unit prices.** Always use the gross line total, VAT included.
2. **Missing a round.** **b defaults to 0**: you reject every charge, and every fair one costs you **1.5×**.
3. **Skimming the policy.** Excluded items have **t = 0**. Paying for them is paying for fraud.
4. **Rejecting everything to be safe.** Each wrongful rejection costs the price plus **50%**. It adds up fast.
5. **Pricing by hand.** Sixty seconds per case, many line items, rounds all day. Automate early.

### Think in expected value

**When is rejecting worth it?**

- Accepting a charge costs you **a**.
- Rejecting it costs **1.5 × a** if it was fair, and **nothing** if it was inflated.

So how sure of fraud do you need to be before you reject?

## Slide 9: How to win, and the fine print

### How to win

- Most money across all rounds.
- A short write-up (**at most one page**) of your approach, **due before the end**.
- Best team presentation and approach.
- See `EVALUATION_CRITERIA`.

### Fair play

- No collaboration across teams.
- Your API key stays in your team.
- No attacking or probing the platform.
- Inside your team, anything goes.

### Logistics

- **Register:** via the Platform.
- **Case files:** Google Drive.
- **Rounds:** every **~13 minutes**, **2 pm today to 12 pm tomorrow**.
- **Help:** Discord Marvin, Moritz, Simon with `[QuantCo]`.
- **First round starts at 2 p.m.**

### Leaderboard and upcoming rounds

[c2f.public.quantco.cloud/leaderboard](https://c2f.public.quantco.cloud/leaderboard)

## Slide 10: Questions? Good luck!

Water (damage claim handling) is our thing. For the next **24 hours**, it's yours too.
