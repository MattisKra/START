# Topic B: Estimation / ML pipeline for "Claim to Fame" (Claude research agent)

*Scope: from (damage report + policy + invoice PDF + optional photos) to a per-line posterior over the hidden fair value t (including a point mass at t=0), then to (a, b). Time-boxed to about 25 min of desk research on 2026-11-21.*

**Method note (honesty):** every source below was found through web search. For most papers I read the abstract, the official page or search-surfaced excerpts, **not the full PDF**. Numbers quoted from papers come from those excerpts. Where I only had a secondary source, or nothing, I mark the claim **unverified**. Labels used: **[R]** published result, **[I]** my interpretation, **[H]** hypothesis that it transfers here. Confidence: **high / med / low**.

---

## TL;DR (ranked by usefulness for winning)

1. **[I, high] b only needs one calibrated number: the 1/3-quantile of your posterior on t.** For a charge a ≤ c: accepting costs a, and rejecting costs 1.5·a·P(t ≥ a). So you should accept iff P(t ≥ a) ≥ 2/3, i.e. iff a ≤ Q_t(1/3). The rule is pointwise and threshold-shaped, so **b\* = Q_t(1/3) whatever the other teams charge**. Corollary: if P(t = 0) ≥ 1/3 (excluded or unrelated line), then b\* = 0. The whole ML problem for b reduces to **calibrated lower-tercile estimation** (pinball loss at τ = 1/3), plus a good P(t = 0). Caveat: for a > c the accepted-fraud cost is capped at c, so very large charges can become worth accepting. A single threshold cannot express "accept huge, reject medium", so ignore this unless c turns out to be small.
2. **[R→H, high] Raw LLM intervals are far too narrow. Plan to widen them with a conformal or empirical correction.** In FermiEval, LLMs' nominal 99% intervals covered the truth only about 65% of the time, and split-conformal recalibration restored coverage while cutting the Winkler score by about 54% ([arXiv 2510.26995](https://arxiv.org/abs/2510.26995)). Verbalized confidence clusters at 80–100% and is overconfident, while sampling-consistency signals do better ([Xiong et al., ICLR 2024](https://arxiv.org/abs/2306.13063)). Because our b sits at a *lower* quantile, overconfidence pushes b too high, which means accepting inflated charges.
3. **[I, high] Use an "anytime" submission loop.** Submit a fallback within about 5–10 s of decryption (from a cached category price prior, with b set to a conservative but non-zero value), then resubmit as better estimates arrive. The slides say the last submission before the deadline counts. A missed round sets b = 0, so every fair charge then costs 1.5·a. That is the single largest avoidable loss.
4. **[I, high] Let deterministic code do all the arithmetic.** The LLM returns *net unit price* quantiles plus flags. Code computes qty × unit × 1.19 (German standard VAT is 19%, [§12 UStG](https://www.gesetze-im-internet.de/ustg_1980/__12.html)). Parse quantities with German number formats ("1.071,50"). Slide 8 lists net and per-unit submissions as the #1 way to lose money.
5. **[R→H, med] Ensemble across models and samples to get a distribution, but expect correlated errors.** LLM crowds can match human crowds on forecasting ([Schoenegger et al.](https://arxiv.org/abs/2402.19379)), and self-consistency sampling helps ([Wang et al.](https://arxiv.org/abs/2203.11171)). However, LLMs agree on *wrong* answers far more often than chance, and more so for stronger models and same-provider pairs ([Kim et al., ICML 2025](https://arxiv.org/abs/2506.07962)). So ensemble spread **underestimates** uncertainty, and you still need the calibration step from #2.
6. **[I, high] Learn t online from rejections only, using censored-data estimators.** Feedback on t only exists when a charge was *rejected*: being paid 1.5·a reveals t ≥ a, and being paid 0 reveals t < a. Accepted charges pay a either way, so they reveal nothing (unless a > c). That is interval-censored ("current status") data. Naive online conformal (ACI) updated only on the observed cases can be biased; [Ge, Bastani & Bastani (ICML 2025)](https://arxiv.org/abs/2405.13268) show this for semi-bandit feedback. Use a likelihood-based recalibration (for example, fit a log-scale bias and spread from the censored observations) rather than naive ACI.
7. **[H, med] Expect the organizers' t to come from a consistent internal price model.** Most of the attainable gain is probably in learning *their* systematic level (a multiplicative bias per category) during the first rounds, not in better world knowledge. Log everything per line (category, unit, qty, model quantiles, a, b, settlement) from round 1.
8. **[R→H, med] Coverage and relatedness checks are a separate, cheaper LLM task, and should be a probability, not a yes/no.** Legal and insurance benchmarks show LLMs handle simple coverage questions but degrade on exclusion-exception logic ([LegalBench](https://arxiv.org/abs/2308.11462), [InsLogicBench, ACL 2026](https://aclanthology.org/2026.acl-long.1035.pdf), [INSEva](https://arxiv.org/abs/2509.04455)). Feed P(covered)·P(related) into the zero mass, π0 = 1 − P(cov)·P(rel), and let the τ = 1/3 rule decide b.
9. **[R, med] Do not trust VLMs for cost from photos.** Use photos only for a coarse consistency check ("does the image show water damage in the room named?"). GPT-4V struggled with loss assessment and hallucinated ([arXiv 2404.09690](https://arxiv.org/abs/2404.09690)), and none of the tested MLLMs reliably estimated vehicle repair cost ([arXiv 2501.04150](https://arxiv.org/abs/2501.04150)).
10. **[R→H, med] Competition lessons: modular estimate→predict→optimize, automate early, don't overfit to noisy round outcomes.** The TacTex09 TAC/AA winner was structured exactly as estimate hidden state → predict → optimize ([Pardoe et al., AAMAS 2010](https://www.cs.utexas.edu/~dpardoe/papers/AAMAS10.pdf)). Kaggle public-leaderboard overfitting is well documented ([Blum & Hardt, ICML 2015](https://proceedings.mlr.press/v37/blum15.html)).

---

## 0. The interface: posterior → (a, b)

**Notation.** S(x) = P(t ≥ x) under our posterior. Q(τ) is the τ-quantile.

**Insurer side (b).** [I, high; my own derivation from the payoff table in the slides, independently consistent with the "P(fraud) > 1/3" note in GAME_SPEC.md]

- Accept: we pay a if fair, and min(a, c) if inflated. For a ≤ c we pay a regardless of fairness.
- Reject: we pay 1.5·a if fair, and 0 if inflated.
- So we accept iff a ≤ 1.5·a·S(a), i.e. S(a) ≥ 2/3, i.e. a ≤ Q(1/3).
- S is non-increasing, so the optimal accept set is {a ≤ Q(1/3)}, and it is exactly implementable by **b = Q(1/3)**. No model of the other teams' a is needed.
- Zero mass: if π0 = P(t = 0) ≥ 1/3, then Q(1/3) = 0 and b = 0, so we reject any positive charge.
- Otherwise, with a continuous part F₊ on (0, ∞): Q(1/3) = F₊⁻¹((1/3 − π0)/(1 − π0)). A zero mass of, say, 0.2 pushes b down to the ~17th percentile of the positive part.
- **Sensitivity [I]:** the loss from a miscalibrated b is asymmetric. Setting b too high accepts inflated charges, costing about the charge each time. Setting b too low rejects fair ones, costing 1.5·a each time. Both are bounded by the charge, so b mistakes are expensive only on high-value lines. **Spend LLM budget on the most expensive lines first.**

**Handyman side (a).** [I, med] Against an insurer with limit b_j:

- If a ≤ b_j we receive a (for a ≤ c) **regardless of fairness**.
- If a > b_j we receive 1.5·a·1[a ≤ t].

So E[receipt] = p(a)·a + (1 − p(a))·1.5·a·S(a), where p(a) is the fraction of other teams with b ≥ a. This needs a model of the *other teams' b* (topic A, game theory). From the estimation side it needs **S(·) over the whole range**, not just one quantile. Deliver the full posterior (for example as a quantile grid τ ∈ {0.05, 0.1, …, 0.95} plus π0) to the strategy module.

---

## 1. LLM/VLM price and cost estimation

### What is published

- **[R, high]** LLMs can do in-context numeric regression competitively with RF/GBM baselines on synthetic tasks, with sub-linear regret as examples accumulate ([Vacareanu et al., COLM 2024](https://arxiv.org/abs/2404.07544)). **[H, med]** This suggests that few-shot examples of *organizer-revealed t values* in the prompt could calibrate the level. That only works if t (or bounds on it) becomes observable.
- **[R, high]** Fine-tuned LLMs with quantile heads (Mistral-7B, pinball loss) beat traditional methods on point and distributional price prediction (Amazon products, used cars, boats) ([Vedula et al., Findings ACL 2025](https://aclanthology.org/2025.findings-acl.641)). **[I]** We cannot fine-tune in 24 h without labelled data, but the paper supports the target format: K quantiles trained or calibrated with pinball loss.
- **[R, med]** Retrieval of similar products before LLM pricing substantially reduced error in e-commerce second-hand pricing ([LLP, arXiv 2510.09347](https://arxiv.org/abs/2510.09347); I could not parse the table columns exactly, so the size of the gain is **unverified**).
- **[R, low–med]** Web-search grounding improves exactness, but grounded answers can still be wrong with plausible citations, for example from aggregator pages or the wrong product variant ([CostBench study](https://costbench.com/ai-retrieval-index/accuracy-study/), vendor study; [Apify blog](https://blog.apify.com/llm-grounding-with-live-data/), vendor blog, unverified).
- **[R, med]** Construction estimation knowledge: GPT-4.1 scored 75.4% on the CEQuest construction-estimation QA benchmark ([arXiv 2508.16081](https://arxiv.org/abs/2508.16081)). A vendor blog reports a general chatbot at roughly 14–34% mean absolute error on bill-of-quantities quantities versus a chartered surveyor ([civils.ai](https://civils.ai/blog/can-llms-perform-good-civil-estimates/); vendor, conflict of interest, unverified). I found **no peer-reviewed benchmark of LLM unit-rate pricing for German repair or water-damage trades**, so this is unverified.
- **[R, high]** On Fermi-style estimation, models were historically off by orders of magnitude ([Kalyan et al. 2021](https://arxiv.org/abs/2110.14207)). Modern models land much closer but are overconfident ([FermiEval](https://arxiv.org/abs/2510.26995)).
- **[R, med]** Numeric anchoring: LLM estimates shift toward irrelevant numbers in the prompt, and standard mitigations are largely ineffective ([SynAnchors, arXiv 2505.15392](https://arxiv.org/abs/2505.15392); [arXiv 2511.05766](https://arxiv.org/abs/2511.05766)). **[H, med]** Don't put numbers in the prompt that you don't want copied, such as another line's price or a "typical claim €4,000" figure. If you add a reference price, expect the model to anchor on it, which is good only if the reference is trustworthy.

### Price reference sources (German/EU context)

- **BKI "Baukosten Positionen Altbau"** (renovation and existing-building unit prices): the 2026 edition has more than 2,500 positions across 51 trades, with prices from settled project bills, VOB/C-conformant, about €99 for the book ([baulinks 2026](https://www.baulinks.de/webplugin/2026/1438.php4); [Baunetzwissen 2025 edition](https://www.baunetzwissen.de/controlling-und-management/tipps/buecher/bki-baukosten-gebaeude-altbau-2025-10186794)). **[I]** This is the closest public analogue of "what a claims expert would accept" for building trades. It is paid and offline, so it is not usable unless someone owns a copy. It is fine to use as a reference for building a small prior table by hand if available.
- **Sirados**: unverified. My search returned nothing usable.
- **Xactimate (US)**: price lists are researched across 460+ US/Canada markets ([Xactware product page](https://www.xactware.com/products/xactimate.html)). The methodology summary says Verisk reports "a market price based on recent submitted transactions" and targets the most representative price ([methodology summary PDF](https://propertyinsurancecoveragelaw.com/wp-content/uploads/2024/10/Xactimate-Pricing-Methodology-Summary.pdf), hosted by a third party). **[I]** This is the conceptual model of how an insurer's t is likely set: a mid-market reference price per line item. Not directly usable for EUR.
- **Claim size scale prior (Germany, Leitungswasser):** about €4.9 bn in claims for about 1.13 m tap-water claims in 2024, roughly €4,000–4,300 per claim. That figure is my own division of secondary-source totals ([Finanztip press release](https://www.finanztip.de/presse/leitungswasserschaeden-steigen-stark-und-verteuern-die-wohngebaeudeversicherung-massiv/), [test.de](https://www.test.de/Wasserschaden-Welche-Versicherung-wann-zahlt-5700777-0)). It is not a GDV-published average, so unverified. **[H, low]** Useful only as a sanity check on invoice totals.

### Recommendation [I/H]

- Per line: ask each model for **net unit price p10/p50/p90** in EUR for the German market in 2026, with the unit made explicit.
- **Treat log(price) as roughly Gaussian or Student-t per line.** Combine the models as a mixture in log-space.
- **Build a cached prior table by (trade, unit)** during the first hours. Seed it from LLM answers to a canonical list of about 100–200 water-damage line items (leak detection, technical drying per device-day, screed removal per m², tiles per m², laminate per m², painting per m², plumber hours, call-out flat fee, and so on). Refine it with whatever feedback arrives. Use it both as the fallback and as a shrinkage prior: posterior ∝ LLM ensemble × table prior, in log-space.

---

## 2. Calibrated uncertainty for numeric LLM outputs

### Published

- **[R, high] Conformalized quantile regression (CQR):** fit lower and upper quantile regressors, then shift them by a conformal correction computed on a calibration set. The result keeps finite-sample coverage and adapts to heteroscedasticity ([Romano, Patterson & Candès, NeurIPS 2019](https://arxiv.org/abs/1905.03222)).
- **[R, high] Split conformal on LLM intervals:** restores 99% coverage on FermiEval and reduces the Winkler score by about 54% ([arXiv 2510.26995](https://arxiv.org/abs/2510.26995)). A similar finding, that conformal prediction fixes under-coverage of LLM 95% intervals on population statistics (raw coverage 9–44%), is in [arXiv 2604.01896](https://arxiv.org/abs/2604.01896) (excerpt only, med).
- **[R, high] Verbalized confidence is overconfident; consistency-based measures are better; hybrids help** ([Xiong et al.](https://arxiv.org/abs/2306.13063)).
- **[R, high] Pinball (check) loss** is the proper scoring rule for a quantile ([Gneiting & Raftery 2007, JASA](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jrssb.pdf)). Use τ = 1/3 pinball loss as the metric for b. Use the CRPS or a quantile-grid average for the full posterior.
- **[R, high] Online, distribution-shift-robust calibration:** Adaptive Conformal Inference updates the miscoverage level α_t online and gets long-run coverage without exchangeability ([Gibbs & Candès, NeurIPS 2021](https://arxiv.org/abs/2106.00170)). A later variant adapts the step size ([arXiv 2208.08401](https://arxiv.org/abs/2208.08401)).
- **[R, med] Partial feedback:** when labels are observed only in some cases, standard ACI can lose coverage. There are sublinear-regret algorithms for the semi-bandit setting, with an auction price-setting experiment ([Ge, Bastani & Bastani, ICML 2025](https://arxiv.org/abs/2405.13268)) and an adversarial variant ([arXiv 2604.17984](https://arxiv.org/abs/2604.17984)). I did not check the bounds.

### How to calibrate here with little or censored feedback [I/H]

**Cold start (no labels):** use a fixed *inflation of spread*, for example multiply the log-σ from the ensemble by 2–3. FermiEval-type overconfidence suggests raw spreads cover far less than nominal (med confidence that roughly ×2 is in the right ballpark; unverified for prices). Also put a floor on σ_log per category, for example ≥ 0.25, i.e. about ±28% (my guess, low confidence).

**If per-line t is revealed after rounds:**

- Run split-conformal / CQR in log-space. Score s = (log t − μ̂)/σ̂.
- Track the empirical **1/3-quantile of s** online, with an ACI-style update in the score domain: q ← q + η·(1[s < q] − 1/3).
- About 100 rounds × N lines gives hundreds to thousands of points, which is plenty for one global shift and scale, and maybe per-trade shifts.

**If only settlements are revealed (accept/reject plus money):**

- Every *rejected* charge a, whether ours as handyman or theirs as insurer, gives a censored label: t ≥ a (paid 1.5·a) or t < a (paid 0).
- Fit the global log-bias β and scale k by maximum likelihood on these binary outcomes: P(t ≥ a) = 1 − Φ((log a − μ̂ − β)/(k·σ̂)). This is a probit fit, which is robust and needs only tens of observations.
- Accepted charges carry **no** information about t, so do not update on them. That is exactly the bias Ge et al. warn about.

**Exploration [H, low]:** rejected charges are informative but costly. Deliberate probing, such as lowering b on cheap lines to learn the level, could be worth a small budget early. That is a strategy call for topic A.

---

## 3. Coverage, relatedness and exclusion classification; photo consistency

### Published

- **[R, med]** LLM coverage reasoning: LegalBench includes an insurance-policy-interpretation task (covered / not covered / unclear) ([arXiv 2308.11462](https://arxiv.org/abs/2308.11462)). InsLogicBench targets exclusion clauses and their exceptions, with clause-to-decision reasoning traces ([ACL 2026](https://aclanthology.org/2026.acl-long.1035.pdf)). INSEva reports that general LLMs score above 80 on basic insurance knowledge but struggle with complex scenarios ([arXiv 2509.04455](https://arxiv.org/abs/2509.04455)). I did not verify the headline numbers of the first two.
- **[R, med]** Insurance claim automation with LLMs (LoRA-fine-tuned, structured corrective-action outputs from claim narratives) ([arXiv 2602.16836](https://arxiv.org/abs/2602.16836)). A vendor report compares LLMs on information extraction from repair quotes and invoices ([Shift Technology](https://www.shift-technology.com/resources/reports-and-insights/the-state-of-ai-in-insurance-llms); vendor, unverified).
- **[R, low] Claims-leakage practice:** "leakage" is the amount paid above what optimal handling would pay. The 5–10% figure, often attributed to PwC, is repeated by vendors ([IRMI definition](https://www.irmi.com/term/insurance-definitions/claims-leakage); [Hyland brief](https://www.hyland.com/-/media/Project/Hyland/HylandV2DotCom/pdfs/nuxeo_insurance_brief_claims-leakage.pdf?sc_lang=en)). I did not verify the primary PwC study. Commercial line-item auditing compares unit prices and labour hours against Xactimate-style benchmarks and flags duplicates and unrelated items ([Nomad Data](https://www.nomad-data.com/doc-chat/detecting-falsified-receipts-and-repair-invoices-with-ai-in-homeowners-claims-property-claims-adjuster); marketing, low).
- **[R, med] Multimodal:** GPT-4V shows hallucination and weak loss assessment on insurance images ([arXiv 2404.09690](https://arxiv.org/abs/2404.09690)). INS-MMBench finds models are better on auto and health than on property images ([arXiv 2406.09105](https://arxiv.org/abs/2406.09105)). No MLLM reliably estimated repair cost ([arXiv 2501.04150](https://arxiv.org/abs/2501.04150)). Out-of-context image/text checking is an established fact-checking task ([MFC-Bench](https://arxiv.org/abs/2406.11288)). I found no damage-photo-specific benchmark, so that is unverified.

### Recommendation [I/H]

- **One structured call per case** that returns, for every line index: `{covered_prob, related_prob, exclusion_clause_quote, reason_short}`. Require **quoting** the policy clause that excludes the line. Fabricated quotes can then be checked by string match against policy.txt. That is a cheap hallucination guard (my design, unverified).
- Typical traps worth explicit prompt rules (my hypotheses from the slide examples and German household and building insurance conventions; unverified against the actual cases):
  - Wrong room or object: the slide's example is "burst bathroom pipe → kitchen cabinets".
  - Upgrades or betterment, for example premium instead of like-for-like.
  - Pre-existing defects, wear, mould from long-term moisture.
  - Repair of the leaking pipe itself versus the consequential damage, which policies treat differently.
  - Items explicitly excluded in policy.txt.
  - Duplicate lines.
  - Quantities implausible for the described area, for example 60 m² of flooring for a "small bathroom".
- **Quantity plausibility is part of "reasonable".** t is a line *total*, so an inflated quantity makes t smaller than qty × fair unit price. Ask the model for a plausible quantity range given the description, and price min(qty, plausible_max) as the centre (hypothesis, med).
- **Photos:** one VLM call with "does this image plausibly show the damage described (room, type, extent)?" returning a probability. Use it only to mildly raise π0 for lines tied to a contradicted claim. Never let it drive prices.

---

## 4. Engineering for a 60-second budget

### Facts from docs

- Claude PDF input: each page is converted to an image *and* its extracted text is sent alongside ([Anthropic PDF support docs](https://platform.claude.com/docs/en/build-with-claude/pdf-support)). Page and size limits are unverified (third-party figures only).
- OpenAI Structured Outputs guarantees schema adherence of completed non-refusal outputs, but the docs say you must still handle refusals, incomplete responses and API errors, and validate business rules ([OpenAI docs](https://developers.openai.com/api/docs/guides/structured-outputs)).
- Anthropic prompt caching caches the prefix (tools → system → messages) up to the `cache_control` breakpoint. Cache reads cost 0.1× base input price, and below a minimum length the prompt is silently not cached ([Anthropic prompt caching docs](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)). Latency benefit figures are unverified.
- PDF parsing: table structure and reading order remain the hardest parts. Tools make typos on blurry or watermarked scans ([OmniDocBench, CVPR 2025](https://arxiv.org/abs/2412.07626)), and general VLMs are weaker on table reconstruction than specialised parsers (secondary claim from [FinixDoc](https://arxiv.org/abs/2608.22842), unverified).

### Design [I]

- **Timeline target:**

  | Time (s) | Step |
  | --- | --- |
  | 0–3 | Fetch key, `7z x` |
  | 3–5 | Deterministic PDF text parse |
  | ≤8 | **Submit fallback** |
  | 8–40 | Parallel LLM calls |
  | 40–45 | Aggregate and resubmit |
  | 45–55 | Optional second resubmit if late answers arrived |

  Hard per-call timeout of about 30 s. Never wait for a straggler; use whatever answered.
- **Parse deterministically first** (for example PyMuPDF or pdfplumber) when the PDF has a text layer. Use the VLM or PDF-native LLM path only as a fallback or a cross-check.
- **Validate:** number of lines, contiguous indices, qty > 0, known unit. If the deterministic parse and the LLM parse disagree on line count, submit for the union of indices. A missing index means a = 0 and b = 0, and b = 0 rejects a fair charge at a cost of 1.5·a.
- **Unit and quantity pitfalls:**
  - German decimal comma.
  - Lump-sum lines ("psch", "pauschal", qty 1): the price is the total.
  - Time-based units (Std = hours, Tag/Tage = days, e.g. drying-device days, which may be written as qty = devices × days).
  - lfm (running metres) vs m vs m², m³, Stk (pieces), kg.
  - Do the invoice lines already state "netto"? We must add 19%.
  - Submit the **line total**, not the unit price.
  - Unit tests on the slide example: 18 m² × €50 × 1.19 = €1,071.
- **Parallelism:** fan out one pricing call per model (×2 samples at temperature > 0) plus one coverage call per model, all concurrently with asyncio. Batch all lines of a case into one call per model rather than one call per line, which saves latency and keeps the case context.
- **Caching:** put the static system prompt, few-shot examples and the prior table first, to use prompt caching. Keep a local cache keyed by a normalised line description (e.g. "Bautrocknung | Tag") → last posterior, for instant fallback.
- **Watchdog:** a separate cron/systemd process that submits the fallback if the main bot has not submitted by T+20 s. Alert on any HTTP error from the submission endpoint. Test continuously against **Game 0** (always open, stores nothing, per the slides).
- **Fallback values when everything fails [I]:** a = prior-table median × 0.9. b = prior-table Q(1/3) shrunk toward 0 only if the line looks unrelated by keyword. **Never b = 0 by accident.**

---

## 5. Lessons from similar live bot/market competitions

- **[R, med] TAC Ad Auctions:** the winning TacTex09 agent estimated the hidden game state from limited data, predicted outcomes, then optimized bids ([AAMAS 2010](https://www.cs.utexas.edu/~dpardoe/papers/AAMAS10.pdf); [tech report](https://apps.dtic.mil/sti/pdfs/AD1024600.pdf)). A top-3 2011 agent built "strategic fingerprints" of opponents with ML ([Hertz thesis](https://www.tau.ac.il/~mansour/students/Shai_Hertz_Thesis.pdf)). Overview of TAC lessons: [Ketter & Symeonidis, AI Magazine](https://ojs.aaai.org/aimagazine/index.php/aimagazine/article/download/2396/2289) (not read in full). **[H, med]** Mirror this structure: the estimation module (this doc) is separate from the opponent model (others' a and b distributions, from settlements) and the optimizer (a, b).
- **[R, low] IMC Prosperity (trading sim):** participants credit tooling, automation and dashboards. One solo entrant says not having working algorithms for every round hurt their ranking ([IMC winner profile](https://www.imc.com/eu/articles/discovering-imc-through-prosperity-lorenzo-s-story); [davidteather repo](https://awesome.ecosyste.ms/projects/github.com%2Fdavidteather%2Fimc-prosperity-2024)). These are anecdotes. **[H, med]** The analogue here is robustness and never missing a round, which beats cleverness.
- **[R, high] Kaggle:** adaptive tuning against a noisy public leaderboard overfits ([Blum & Hardt, ICML 2015](https://proceedings.mlr.press/v37/blum15.html)), and shake-ups follow (e.g. M5 anecdote in [Kaggle Chronicles](https://arxiv.org/abs/2511.06304)). **[H, med]** Round-level PnL is very noisy (it depends on which lines and which opponents appear). Change parameters on pooled evidence, such as the censored-likelihood fit, not on the last round's leaderboard move.
- **[I] LLM arenas/forecasting:** blending several model forecasts and *averaging with external evidence* beat single models ([Schoenegger et al.](https://arxiv.org/abs/2402.19379)). Cross-provider error correlation limits the gains ([Kim et al.](https://arxiv.org/abs/2506.07962)).

---

## Minimal pipeline that can run in 60 s (sketch)

```text
T+0   poll /api/games/list → on start: GET key → 7z x → files
T+2   parse invoices.pdf (PyMuPDF text; regex rows: idx | text | qty | unit) → lines[]
      validate; if parse fails → send PDF to fastest VLM for extraction (timeout 10 s)
T+5   FALLBACK: for each line: cat = keyword→(trade,unit) map; prior = table[cat] (log-mu, log-sigma)
      a = 0.9*median_gross(prior, qty); b = Q(1/3) of prior ; PUT submissions   ← never miss
T+5   async fan-out (timeouts 30 s), all with JSON-schema outputs:
        P_k  (k = GPT, Claude, Gemini; 2 samples each, temp 0.7):
             per line: unit_net_eur {p10,p50,p90}, plausible_qty_max, unit_check
        C_k  (2 models, temp 0):
             per line: covered_prob, related_prob, exclusion_quote, dup_of
        V    (if images): photo_consistent_prob for the described damage
T+40  aggregate per line:
        mu, sigma (log-space) = mixture over P_k answers ∪ prior (shrinkage weight w_prior)
        sigma *= k_cal ; mu += beta_cal            # online-calibrated (section 2)
        qty_eff = min(qty, plausible_qty_max_median)
        gross quantiles = qty_eff * exp(quantiles(mu, sigma)) * 1.19
        pi0 = 1 - mean(covered_prob)*mean(related_prob)  (+ small bump if photo contradicts)
        verify exclusion_quote ⊂ policy.txt else ignore that exclusion vote
        b = 0 if pi0 >= 1/3 else gross_quantile((1/3 - pi0)/(1 - pi0))
        a = strategy_module(posterior, opponent_b_model)   # topic A; default ≈ Q(0.4–0.5) of posterior
      PUT submissions (overwrite)
T+50  if late answers arrived → recompute → PUT again
after round: log everything; update beta_cal, k_cal, opponent model from settlements (censored MLE)
```

---

## Risks and failure modes

1. **Missed or late submission:** b = 0 rejects every fair charge at a cost of 1.5·a. *Mitigation:* fallback at T+5, watchdog, retries, monitoring. (high)
2. **Unit and VAT errors** (net, per-unit, decimal comma, lump-sum, device-days). *Mitigation:* code-side arithmetic, unit tests, sanity bounds per (trade, unit). (high)
3. **Overconfident LLM spreads → b too high → paying for fraud.** *Mitigation:* spread inflation, conformal or censored-MLE recalibration. (high)
4. **Correlated model errors** (all models share a training-data price bias). *Mitigation:* the prior table plus learning the organizers' level online; don't treat agreement as certainty. (med)
5. **Systematic level mismatch with the organizers' t** (e.g. they used a specific price list or an LLM-generated t). *Mitigation:* a global multiplicative β learned from rejections in the first rounds. (med, hypothesis)
6. **Coverage false positives** (marking a covered line excluded → b = 0 → 1.5·a penalties). The τ = 1/3 rule makes this costly. *Mitigation:* require a verified exclusion quote, use ensemble probabilities, cap π0 when the evidence is weak. (med)
7. **PDF table-parse errors** (shifted columns → qty read as price or index mismatch). *Mitigation:* dual-parse cross-check and per-index matching. (med)
8. **Anchoring and prompt leakage:** numbers in the prompt (e.g. a qty of 18 near "€50") get copied. *Mitigation:* separate fields, examples carefully chosen. (low–med)
9. **API rate limits or outages at round start** (all teams hit providers simultaneously, every 13 min). *Mitigation:* multi-provider, short timeouts, the table fallback. (med)
10. **Overreacting to noisy round PnL.** *Mitigation:* update only on pooled likelihood evidence. (med)

---

## Source list

**Calibration / uncertainty**
- FermiEval, LLM interval overconfidence + conformal fix: https://arxiv.org/abs/2510.26995
- LLM 95% intervals on population statistics + conformal: https://arxiv.org/abs/2604.01896 (excerpt only)
- Xiong et al., confidence elicitation (ICLR 2024): https://arxiv.org/abs/2306.13063
- Romano, Patterson, Candès, CQR (NeurIPS 2019): https://arxiv.org/abs/1905.03222
- Gibbs & Candès, ACI (NeurIPS 2021): https://arxiv.org/abs/2106.00170 ; follow-up: https://arxiv.org/abs/2208.08401
- Ge, Bastani, Bastani, online conformal with semi-bandit feedback (ICML 2025): https://arxiv.org/abs/2405.13268
- Adversarial semi-bandit online conformal (ICLR 2026): https://arxiv.org/abs/2604.17984
- Gneiting & Raftery 2007, proper scoring rules: https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jrssb.pdf
- QuantSightBench, LLM prediction intervals: https://arxiv.org/abs/2604.15859 (abstract only)
- LLM hidden-state quantile probes (ICLR 2026): https://arxiv.org/abs/2603.02913 (abstract only)

**LLM numeric / price estimation**
- Vedula et al., quantile regression LLM price prediction (Findings ACL 2025): https://aclanthology.org/2025.findings-acl.641 ; https://arxiv.org/abs/2506.06657
- Vacareanu et al., LLMs as in-context regressors (COLM 2024): https://arxiv.org/abs/2404.07544
- LLP, retrieval-augmented product pricing: https://arxiv.org/abs/2510.09347
- Kalyan et al., Fermi problems: https://arxiv.org/abs/2110.14207
- CEQuest, construction estimation benchmark: https://arxiv.org/abs/2508.16081
- civils.ai blind test (vendor): https://civils.ai/blog/can-llms-perform-good-civil-estimates/
- Search-grounded price accuracy (vendor): https://costbench.com/ai-retrieval-index/accuracy-study/ ; https://blog.apify.com/llm-grounding-with-live-data/
- Anchoring: https://arxiv.org/abs/2505.15392 ; https://arxiv.org/abs/2511.05766

**Ensembles**
- Wisdom of the silicon crowd: https://arxiv.org/abs/2402.19379
- Self-consistency: https://arxiv.org/abs/2203.11171
- Correlated errors in LLMs (ICML 2025): https://arxiv.org/abs/2506.07962

**Insurance / coverage / multimodal**
- LegalBench: https://arxiv.org/abs/2308.11462
- InsLogicBench (ACL 2026): https://aclanthology.org/2026.acl-long.1035.pdf
- INSEva: https://arxiv.org/abs/2509.04455
- Claim automation using LLM: https://arxiv.org/abs/2602.16836
- GPT-4V for insurance: https://arxiv.org/abs/2404.09690
- INS-MMBench: https://arxiv.org/abs/2406.09105
- Large vs small MLLMs, vehicle damage: https://arxiv.org/abs/2501.04150
- MFC-Bench (multimodal fact-checking): https://arxiv.org/abs/2406.11288
- Shift Technology LLM report (vendor): https://www.shift-technology.com/resources/reports-and-insights/the-state-of-ai-in-insurance-llms
- Claims leakage: https://www.irmi.com/term/insurance-definitions/claims-leakage ; https://www.hyland.com/-/media/Project/Hyland/HylandV2DotCom/pdfs/nuxeo_insurance_brief_claims-leakage.pdf?sc_lang=en
- Nomad Data (marketing): https://www.nomad-data.com/doc-chat/detecting-falsified-receipts-and-repair-invoices-with-ai-in-homeowners-claims-property-claims-adjuster

**Price references / market context**
- BKI Positionen Altbau 2026: https://www.baulinks.de/webplugin/2026/1438.php4 ; 2025: https://www.baunetzwissen.de/controlling-und-management/tipps/buecher/bki-baukosten-gebaeude-altbau-2025-10186794
- Xactimate: https://www.xactware.com/products/xactimate.html ; methodology summary: https://propertyinsurancecoveragelaw.com/wp-content/uploads/2024/10/Xactimate-Pricing-Methodology-Summary.pdf
- §12 UStG (19%): https://www.gesetze-im-internet.de/ustg_1980/__12.html
- Leitungswasser claim totals (secondary): https://www.finanztip.de/presse/leitungswasserschaeden-steigen-stark-und-verteuern-die-wohngebaeudeversicherung-massiv/ ; https://www.test.de/Wasserschaden-Welche-Versicherung-wann-zahlt-5700777-0
- Sirados: unverified (no source found)

**Engineering docs**
- Anthropic PDF support: https://platform.claude.com/docs/en/build-with-claude/pdf-support
- Anthropic prompt caching: https://docs.claude.com/en/docs/build-with-claude/prompt-caching
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OmniDocBench: https://arxiv.org/abs/2412.07626 ; FinixDoc: https://arxiv.org/abs/2608.22842

**Competitions**
- TacTex09 (AAMAS 2010): https://www.cs.utexas.edu/~dpardoe/papers/AAMAS10.pdf ; https://apps.dtic.mil/sti/pdfs/AD1024600.pdf
- Tau11 thesis: https://www.tau.ac.il/~mansour/students/Shai_Hertz_Thesis.pdf
- TAC lessons (AI Magazine): https://ojs.aaai.org/aimagazine/index.php/aimagazine/article/download/2396/2289
- IMC Prosperity: https://www.imc.com/eu/articles/discovering-imc-through-prosperity-lorenzo-s-story ; https://awesome.ecosyste.ms/projects/github.com%2Fdavidteather%2Fimc-prosperity-2024
- Blum & Hardt, Ladder (ICML 2015): https://proceedings.mlr.press/v37/blum15.html
- Kaggle Chronicles: https://arxiv.org/abs/2511.06304
