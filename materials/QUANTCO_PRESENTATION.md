# Hackathon presentation 21.11.26 (QuantCo intro)

Converted from `pdf/Hackathon presentation 21.11.26.pdf` (6 pages). Mostly company context; nothing here changes the rules.
Marked "Strictly Confidential" on the company slide, so keep it out of public write-ups.

## QuantCo

People present: Marvin Lob, Carolin Thomas, Simon Langer, Moritz Feik. (Discord help contacts per the deep-dive slides: Marvin,
Moritz, Simon, tag `[QuantCo]`.)

QuantCo is an AI expert company serving large enterprise clients across industries.

- Founded 2016 by four Harvard & Stanford PhDs, Cambridge MA. 260+ experts (AI/ML, software engineering, econometrics, product,
  business strategy and organisational transformation). Offices in London, Zurich, Munich, Berlin, San Francisco, Boston and more.
- **Enterprise AI:** claims optimisation and fraud detection suite; econometric optimisation and AI co-pilots to improve claims-handler
  efficiency in health and P&C claims; AI pricing suite deployed with leading firms in insurance, online retail, tech, automotive.
- **Generative AI innovation:** Predictive Health (forecasting costly preventable health events from unique data access) and Virdx
  (physics-AI platform for virtual microscopy and cancer diagnostics from MRI scans).

## Claim to Fame (challenge)

"Price sharp. Detect fraud. Sixty seconds per case."

1. **A case drops:** damage report, policy, an invoice without prices, and photos.
2. **You price it:** read, and send charge price and acceptance limit for every item to the API.
3. **Everyone plays everyone:** your prices meet every other team's.

Build it your way: document parsing, LLMs, price models, game theory. **Win:** most money plus the best approach.
**Prize: AirPods and merch.**

Two sides of every claim: the handyman sets charge price a ("bill as high as you dare; stay at or below its fair value, or the insurer
rejects you and you earn nothing"); the insurer sets acceptance limit b ("pay the fair invoices, reject the inflated ones; wrongly
rejecting a fair price costs you 1.5x that price, paid to the other team"). Hidden fair value t: fair zone a ≤ t (insurer should pay),
fraud zone a > t (insurer should reject). "Find t and you win on both sides. Miss it and you pay twice."

Challenge deep dive session: 11 am to 12 pm (room 1200).
