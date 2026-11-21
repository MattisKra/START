# Slice B: processing pipeline, coverage/relatedness/fraud, cost-efficient serving

Author: Claude (research sub-agent B), 2026-11-21, ~30 min time-box. Read `CONTEXT.md` first.
Tags: **[opened]** = the primary page was read and the number was quoted from it. **[opened\*]** = the primary page was read, but the
number came from a summary of a truncated page or a table I did not see verbatim. Treat these as likely but re-check before citing to the jury.
Every [snippet]/[memory] item is in §6 (unverified). Labels: **(i)** published result, **(ii)** my interpretation, **(iii)** a hypothesis that it transfers to our setting.

---

## 0. Bottom line, ranked by expected benefit under the 60 s limit (0-5 s / ~15 s / ~45 s tiers)

| # | Change | Tier | Benefit | Evidence | Cost |
|---|---|---|---|---|---|
| 1 | **Don't trust LLM-stated p10/p90.** Use the LLM's p50 only, and set the spread from an empirical per-trade log-σ or from disagreement between models, with a floor. | all | **High.** `b` is a quantile, so a too-narrow σ moves `b` directly. | Overprecision paper: stated 90-95 % intervals hit 5-80 %, never nominal (§3.4) | 0 tokens |
| 2 | **Deterministic tier-0 parser** (pdftotext `-layout` + regex on `POS.` rows, German number normalisation, index assertion). It needs no ML. | 0 | **High.** The safety net and the index mapping both depend on it. | Invoices are born-digital, generated, one layout (CONTEXT). OCR/VLM parsers are slower and add errors (§1) | ~50 ms |
| 3 | **One call per case, all lines batched, schema with a short reason field *before* the numbers, clause-cited coverage fields** | 1, 2 | Medium-high. Fewer tokens, consistent cross-line reasoning, auditable | JSON mode helps classification but can hurt reasoning, so order the fields (§3.3). Constrained decoding is ≥ as accurate and faster (§3.3) | −(n−1) prompt copies |
| 4 | **Race, don't cascade-in-series**: start the fast and strong calls at t=0. Submit fast at ~15 s. Let strong overwrite. Cancel strong only when the fast tier is confident *and* agrees with tier 0. | 1, 2 | Medium. Avoids the cascade's serial latency and keeps the jury's "economical" story | FrugalGPT / MoT-cascade / RouteLLM savings (§3.1). Agreement/consistency is the published escalation signal | saves strong-tier tokens on easy cases |
| 5 | **Low reasoning effort by default.** Spend tokens on a second independent sample or model, not on longer chains | 1, 2 | Medium. Lets us show accuracy-per-token evidence to the jury | Overthinking: zero gain low→high for GPT-5/o-series. OckBench: 5× token spread at equal accuracy (§3.2) | fewer tokens |
| 6 | **Prompt caching**: put a static ≥1,024-token prefix first (rules, trade price anchors, schema). Rounds are 13 min 20 s apart, so pick a TTL that covers the gap | 1, 2 | Low-medium (latency/cost) | OpenAI default 30 min retention on GPT-5.6+. Anthropic default 5 min, so pay for `ttl: 1h` (§3.5) | write premium once |
| 7 | **Explicit per-line coverage fields**: `related_to_story`, `excluded_by_clause`, `covered_by_clause`, `mixed_scope` | 1, 2 | Medium for the planted line, low elsewhere (CONTEXT says coverage is easy) | Benchmarks: LLMs get final decisions right but miss exception clauses and causation (§2.1) | ~20 tokens/line |
| 8 | **Photo**: send it at most in the strong tier, low-res, only to check scale (m² and pipe count against the picture). **Do not** run AI-generated-image detection | 2 | Low | FraudBench: MLLMs miss most fakes and detectors false-flag real damage. All our photos are likely synthetic anyway (§2.3) | image tokens |
| 9 | Layout-aware parsers or VLM OCR (Docling, MinerU, olmOCR, Marker) | none | **Negative** for our input | 0.8-2 s/page CPU (Docling), a 7B GPU model (olmOCR). They solve scanned/complex layouts we don't have (§1) | seconds |

**Single most promising edge (ii/iii):** the stack already gets coverage and parsing nearly right. The money is in **calibrating σ**: LLM-verbalised
numeric intervals are badly over-precise in every published measurement I found. Replacing LLM p10/p90 with empirically set or
disagreement-based widths is free, and it changes `b` on every line.

---

## 1. Invoice PDF → line items

**(ii) Framing.** Our invoices are 1-page, born-digital, generated from one template (`POS. 1..n DESCRIPTION AMOUNT UNIT TOTAL`, TOTAL blank).
The literature below targets scanned or heterogeneous documents. For us, extracting the text layer is exact, and the only real risks are
a misread number format or a line-wrapped description. `claimbot/case.py:52` already uses `pdftotext` when it is present (it is installed at
`/opt/homebrew/bin/pdftotext`), else pypdf. pypdf's text order is less layout-faithful, so make poppler a hard requirement for tier 0.

| Artifact | What / headline (i) | Relevance (ii) |
|---|---|---|
| **Berghaus et al., "Multi-Modal Vision vs. Text-Based Parsing: Benchmarking LLM Strategies for Invoice Processing"**, arXiv 2509.04469, 29 Aug 2025, arXiv licence; code at an anonymous 4open.science link. [opened] | Table I: native image input beat the Docling-markdown route. Clean invoices: gemini-2.5-pro **96.50 %**. Scanned invoices: **92.71 %** native vs best parsing route **64.03 %**. The parsing route clusters at **84-85 %** on clean invoices. Exact-match field accuracy, not a line-item F1. Failure mode (IV-C): OCR character confusions such as "zero with the letters O or U". Models: gpt-5-chat/mini/nano, gemini-2.5-pro/flash/flash-lite, gemma-3-12b/4b. | (ii) Their text route went through *Docling OCR markdown*, not a native text layer, so the gap is mostly OCR loss. (iii) For a born-digital PDF the text layer has no OCR errors. If we ever call the LLM to parse, send text **and** a page image only when the regex fails. |
| **olmOCR 2** (Poznanski et al.), arXiv 2510.19817, 22 Oct 2025, paper CC BY 4.0; model olmOCR-2-7B-1025 under "permissive open licenses". [opened] | Table 3: olmOCR-Bench overall **82.4 ± 1.1**, tables **84.9**. 7B VLM trained with RL on unit-test rewards. No inference throughput given in the part I read. | (ii) SOTA for open OCR, but it needs a GPU and solves the wrong problem for us. Skip. Its idea of **unit tests as the parser spec** is worth copying for our tests (below). |
| **MinerU2.5** (Niu et al.), arXiv 2509.22186, v2 29 Sep 2025; code github.com/opendatalab/MinerU. [opened\*] | 1.2B params ("675M-parameter NaViT" + 0.5B Qwen2 decoder, verbatim). OmniDocBench overall **90.67**, table TEDS 88.22. **2.12 pages/s** on A100 with optimisations (0.95 baseline). Stated failure: pipeline error propagation, VLM hallucination on long documents. | (ii) Fast on a GPU but adds a GPU dependency. Not needed. |
| **Docling Technical Report** (Auer et al.), arXiv 2408.09869, v5 Dec 2024, MIT software. [opened] | Table 1 (225 pages, OCR off): M3 Max 4 threads **1.27 pages/s**. Xeon 4 threads 0.60 pages/s. Sec 3.2: table structure takes "between 2 and 6 seconds" on CPU. EasyOCR runs "upwards of 30 seconds per page". The faster pypdfium backend gives "worse quality results, especially in table structure recovery". | (ii) ~1 s best case, up to 6 s with table models. That busts tier 0 and buys nothing over regex on a fixed template. |
| **ReceiptBench** (Wang et al.), arXiv 2605.22413, 21 May 2026; github.com/wwwT0ri/ReceiptBench. [opened\*] | 10,656 images. Line-item structure F1 is low even for the best models: Qwen3-VL-4B SFT **0.648**, Gemini-3-Pro **0.578**. Failure modes (verbatim intro): "arithmetic inconsistencies (e.g., line items not summing to the total)". Models also alter item prices or invent a "Tax" line. | (ii) Even frontier VLMs are poor at nested line items on photos. (iii) Another reason not to let the LLM re-transcribe quantities. Python owns qty and unit, and the LLM only returns per-line judgments keyed by the printed POS number. |
| **Marker** benchmarks README, github.com/VikParuchuri/marker. [opened] | The README has no headline numbers (they are in the top-level README, not fetched). It warns not to compare one system's latency with another's throughput. | n/a |

**Known failure modes for our template, and the guard for each.** (ii) This is engineering, not literature. I found no paper on German invoice number formats specifically.
- *Multi-line descriptions*: a wrapped description produces a continuation row with no `POS.` token and no unit. Append it to the previous position. Assert that every POS row has exactly one numeric qty and one unit from {hrs, pcs, m2, m², Std., Stk., lfm, …}.
- *Approximate quantities* (`~0.2`, `ca. 0,2`, `approx.`): strip the marker, keep the number, set `qty_approx=true`, and pass that flag to the LLM (an "approx." quantity is a natural place to plant inflation).
- *German decimals/thousands* (`0,2`, `1.234,50`): if the string has a comma, treat it as the decimal separator and drop the dots. Otherwise use the dot as decimal. Unit-test both.
- *Index mapping* (claimbot review issue #1): submit the **printed** POS numbers, and assert that the set equals the parsed set before submitting.
- *Fallback*: if the regex fails any assertion, tier 0 still submits using the qty-free heuristic, and the LLM tiers get the raw layout text plus the page PNG.

**How to test without ground truth:** Game 0 is the real fixture. Then write ~20 unit-test PDFs (olmOCR-style "assert property" tests) in the
same template with wrapped descriptions, `ca.`, comma decimals, 1-8 lines and an `m²` glyph. pass/fail is deterministic. Time the full parse (target < 100 ms).

---

## 2. Coverage, relatedness and fraud reasoning

### 2.1 Benchmarks for policy/claim reasoning (i)

| Artifact | Headline (quoted) | Error types reported |
|---|---|---|
| **InsClaimBench** (Zhang et al.), arXiv 2610.09671, 7 Oct 2026, CC BY 4.0. No dataset link found. [opened] | 3,780 cases, 375 families (auto, property, health). Chain: atomic rule judgments → modules (CCE, EC, CE) → payable decision → payout amount. Six LLMs (GPT-5.6-Sol, Gemini-3.8-Flash, DeepSeek-V4.1-Flash, Qwen3.8-Flash, Kimi-K2.6, Qwen3.5-27B). "Payout-decision accuracy ranges from 74.23–80.19%, while joint decision–amount accuracy drops to 47.54–73.15%." "rule-vector exact match peaks at only 36.90%." | **Event & Causation is the weakest module for all six models (70.21-75.58 %, Table 5).** Correct payouts often hide wrong intermediate judgments (Sec 5.4). "28.57–39.98% of updates fail even when the original prediction is correct" (robustness to perturbation). |
| **InsLogicBench** (Liu et al.), ACL 2026 long, pp. 22592-22619, CC BY 4.0. [opened, abstract only. The PDF did not extract] | Reasoning traces linking facts, clauses and verdict, built on the Nested Toulmin Model. 8 LLMs. | "significant difficulties in handling **exception clauses** and verifying **missing conditions**". Models "often produce correct final decisions but fail to provide precise justifications". |
| **Kant et al., "Towards Robust Legal Reasoning: Harnessing Logical LLMs in Law"**, arXiv 2502.17638, Feb 2025. [opened] | Yes/no coverage of 9 claims on a simplified Chubb policy. Vanilla o1-preview **0.88 ± 0.02**. Guided Prolog encoding reaches 1.00 (GPT-4o and o1). | All vanilla models missed the same 2 exclusion questions. DeepSeek-R1 "treated exclusions as conjunctive conditions" (they are OR). GPT-4o passed the wrong variable to an age-exclusion predicate. |
| **INSEva** (Chen et al.), arXiv 2509.04455, Aug 2025, Chinese, data "will be public soon". [opened] | 38,704 items. General LLMs average > 80. Insurance logical reasoning is weakest, with the "highest score is only 73.66 of deepseek-R1" (Sec 4.2). | Faithfulness and completeness trade off. Not claim-line level. |

**(ii) What this means for us.** The published failures are (a) exclusions and exceptions, (b) causation (is the item caused by the insured event?),
and (c) right answer, wrong reason. Our planted line is exactly (b) ("done while on site", unrelated to the damage) or (a) (a maintenance
exclusion such as 3.1 in case 0). CONTEXT reports that case 0 was trivially easy. These benchmarks are far harder (multi-clause, multi-step), so
(iii) they set a *lower bound* on how easy our task is. The residual risk sits in a few predictable patterns, so guard those explicitly:
1. **Same-trade "while on site" items** (a plumber also replaces a kitchen tap or services a boiler). The trade matches the claim, so a model keyed on the trade passes it. Ask "would this line exist if the insured event had not happened?" per line. That is the causation test InsClaimBench says models are weakest on.
2. **Mixed-scope lines** (e.g., "re-tile 0.2 m² **and** whole wall", "replace pipe incl. new radiator"). Coverage is partial, so `t` is neither 0 nor full. Add a `mixed_scope` flag and let Python give `p_valid` a middle value rather than letting the LLM force 0/1.
3. **Quantity inflation on covered lines** (2 hrs leak detection → 6 hrs. 0.2 m² → 4 m²). This is a pricing problem, not coverage. Story-implied scale ("small leak", "a section of pipe") plus the photo are the only evidence. Make the LLM state the plausible quantity range and price excess quantity as inflated.
4. **Maintenance/wear exclusions**: give the LLM the clause IDs and require `excluded_by_clause ∈ {3.x, null}`. Citing forces a clause lookup, which is the mitigation InsLogicBench and Kant et al. point to (structured clause-level reasoning beat vanilla).

**Synthetic fraud-injection benchmarks.** I searched specifically and found **nothing that matches our setup** (an LLM judging a planted unrelated line
on a repair invoice). The closest are ledger/journal anomaly-injection papers (AuditCopilot 2512.02726, typed injection 2610.06133, legal-invoice
SME synthetic anomalies 2012.14511). All of these are [snippet] only, non-LLM or ledger-level, and listed in §6. (iii) Build our own: take Game 0 and the
cases as they unlock, and write variants with a swapped planted item, inflated quantity or mixed scope. Measure planted-line recall and false-flag rate per model/tier.
That is cheap (text-only, ~1 call per variant) and gives the jury evidence of a measured choice.

### 2.2 How to test coverage without ground truth
- **Planted-line recall** on our synthetic variants (we know the answer because we wrote it).
- **Cross-model agreement** on real cases: fast tier vs strong tier vs a second provider. Disagreement on `p_valid` sets `p_valid` toward 0.5, so Python shades `b`.
- **Stability under perturbation** (InsClaimBench's robustness axis): reorder lines and paraphrase the story. A line whose verdict flips is uncertain.

### 2.3 Photo vs story, and AI-generated-damage detection

| Artifact | Headline (i) | Use for us (ii/iii) |
|---|---|---|
| **FraudBench** (Yan et al.), arXiv 2605.08820, v2 27 Sep 2026, CC BY-NC-SA 4.0. HF `TristanYan/FraudBench` (7.93k rows, 13.4 GB, empty card) and GitHub Tristan0318/FraudBench. [opened. Table numbers opened\*] | Abstract: MLLMs show "fake-damage detection rates (TPR) far below the 50% baseline on most generator subsets". Specialised detectors do better but are inconsistent across generators and "frequently flag[] genuine, unedited images of damaged goods as fake". Table 1 (opened\*): best MLLM balanced accuracy 0.664, ForgeLens 0.904, humans 0.686. | **Do not detect AI images.** CONTEXT says the photos are "realistic" 1536×1024 generated images, so *every* photo is likely synthetic and the signal carries no information about `t`. Detectors would add noise and false flags. |
| **GPT4o-Receipt** (Zhang et al.), arXiv 2603.11442, v3 Oct 2026, CC BY-NC-SA 4.0. [opened, some numbers opened\*] | Claude Sonnet 4 accuracy **0.962** detecting AI receipts. Detection runs mostly through **arithmetic errors** (sum errors flagged on 97.2 % of AI receipts, opened\*). | (ii) The signal is internal arithmetic consistency. Our TOTAL column is blank, so it doesn't apply. Mildly useful as a sanity check that unit/qty are coherent. |

(ii) I found no peer-reviewed 2025-26 paper on VLM photo↔narrative consistency for property claims. Search hits were patents and a 2024 GPT-4V
insurance study ([snippet], §6) noting image hallucination and weak loss assessment. **Recommendation:** the photo is worth at most a low-res pass in the strong tier,
for *scale* (how much wall is open? is 0.2 m² plausible?) and *trade/room* match. It should be one input to the quantity-plausibility field, not a fraud detector.
Test: on Game 0, compare the strong tier's quantity judgments with and without the photo across 3 samples. If the photo doesn't change outputs, drop it and save the tokens.

---

## 3. Cost-efficient inference

### 3.1 Cascades and routing (i)

| Artifact | Headline (abstract, [opened]) | Escalation signal |
|---|---|---|
| **FrugalGPT** (Chen et al.), arXiv 2305.05176, May 2023 | "match the performance of the best individual LLM (e.g. GPT-4) with up to 98% cost reduction" | A learned answer-quality scorer decides whether to stop or call the next LLM |
| **LLM Cascades with Mixture of Thoughts** (Yue et al.), arXiv 2310.03094, ICLR 2024 | comparable to the stronger LLM at "only 40% of its cost" (GPT-3.5 → GPT-4, 6 reasoning datasets) | **Answer consistency** of the weak model across samples and representations (CoT vs PoT) |
| **RouteLLM** (Ong et al.), arXiv 2406.18665, v4 Feb 2025 | reduces costs "by over 2 times in certain cases" without quality loss | A router trained on preference data predicts in advance |

(ii) All three assume verifiable answers and no hard wall-clock deadline. A serial cascade (fast → wait → decide → strong) spends latency we don't have.
(iii) The transferable piece is the **escalation signal**: consistency between the fast tier and tier 0, or between two fast samples. Under a 60 s deadline:
- t=0: tier 0 submits (≤5 s). The fast and strong calls start **in parallel**.
- ~15 s: the fast tier overwrites.
- If the fast tier's per-line log-price agrees with the tier-0 anchor within δ **and** `p_valid` is extreme on every line, cancel the strong stream (saves its output tokens). Otherwise the strong tier overwrites at ~45 s.
- Log tokens and the escalation rate per round. That is the accuracy-per-token evidence the jury asks for.

### 3.2 Reasoning effort vs accuracy (accuracy per token)

| Artifact | Headline |
|---|---|
| **Srivastava et al., "Do LLMs Overthink Basic Math Reasoning?"**, arXiv 2507.04023, v3 Apr 2026, ACL 2026 Findings; code github.com/ctrl-gaurav/LLMThinkBench. [opened. The §5.5 number is opened\*] | Abstract: reasoning models "generate ~18x more tokens while sometimes achieving lower accuracy". "GPT-5/o-series models show zero accuracy gain from low -> medium -> high reasoning effort." §5.5 (opened\*): GPT-5 "identical 97% accuracy on both medium and high". |
| **OckBench** (Du et al.), arXiv 2511.05722, v3 Jun 2026; ockbench.github.io. [opened] | Models with "similar accuracy can exhibit up to a 5.0× difference in token length." |
| **Bahaj et al., "Gauging Overprecision in LLMs"**, arXiv 2504.12098, v2 Apr 2025. [opened] | Abstract: "LLMs are highly uncalibrated for numerical tasks". "there is no correlation between the length of the interval and the imposed confidence level". "Refinement of answers doesn't improve precision". Table 4, hit rate of the stated **95 % / 90 %** interval (GPT-3.5-turbo / GPT-4o-mini): FinQA **6.16/5.50** and **21.14/18.95**. Medical 48.28/47.71 and 60.31/60.41. MMLU 59.40/58.70 and 67.05/68.21. CoT raises coverage (e.g., 79.56 on MMLU) but stays below nominal. |

(ii) No paper measures reasoning effort on *numeric price estimation*. The closest evidence is basic math (no gain from more effort) and numeric
intervals (always too narrow). (iii) Unit-price estimation is recall of market knowledge, not multi-step deduction, so extra reasoning tokens should buy little.
Spend the budget on **2 independent cheap estimates** (two models, or two samples at low effort). Their spread is a σ signal, and that signal is
what the overprecision paper says the verbalised interval lacks. The test is cheap: on Game 0 plus synthetic variants, run the fast model at low and high effort 5× each
and compare p50 dispersion and tokens. If p50 doesn't move, low effort is the documented choice.

**Calibration rule (iii):** σ_line = max(σ_floor_trade, k·|log p50_A − log p50_B|, LLM-stated σ × m). Start with m≈2 and set the floor from the
spread of German trade price ranges (slice A's data). Don't fit `k` and `m` on anything we can't observe. Leave them as stated priors and say so to the jury.

### 3.3 Structured output and constrained decoding

| Artifact | Headline |
|---|---|
| **JSONSchemaBench** (Geng et al.), arXiv 2501.10868, v3 Feb 2025; github.com/guidance-ai/jsonschemabench. [opened. Table 8 opened\*] | Intro: "Constrained decoding can speed up the generation process by 50% compared to unconstrained decoding" and "consistently improves the performance of downstream tasks up to 4%". Table 2 (Llama-3.1-8B): Guidance compile 0.00 s, 6.37 ms/token vs LM-only 15.40 ms/token. Table 3: XGrammar compile 0.12 s. Table 8 (opened\*): GSM8K 80.1 → 83.8 with Guidance. |
| **Tam et al., "Let Me Speak Freely?"**, arXiv 2408.02442, EMNLP 2024 Industry. [opened] | Abstract: "significant decline in LLMs reasoning abilities under format restrictions". Conclusion: JSON mode "can hinder reasoning abilities while **enhancing classification task accuracy**". |

(ii) The two papers conflict on reasoning (JSONSchemaBench: constrained decoding helps. Tam et al.: JSON mode hurts). Both agree it is fine or better for
classification, and coverage is classification. (iii) Keep strict structured output, but put a ≤25-word `reason` string **before** `p_valid` and the price fields
in the schema, so the model "thinks" in field order without a separate free-text pass. One call per case with all lines batched removes per-line
prompt duplication and lets the model see the planted line in context (relatedness is a *contrast* judgment). I found no paper comparing per-line vs per-document
calls for invoices. That part is my interpretation.

### 3.4 Prompt caching (vendor docs, [opened])
- **OpenAI** (developers.openai.com/api/docs/guides/prompt-caching): minimum "1,024 tokens for GPT-5.6 and later". Cached input "discounted up to 95%". GPT-5.6+ retention defaults to "30m" (optional "12h"), with 0.1× read and 1.25× (30 m) or 2.5× (12 h) write. The latency claim is qualitative.
- **Anthropic** (platform.claude.com/docs/en/build-with-claude/prompt-caching): minimum 512 tokens for Haiku/Sonnet/Opus 5.5. Default TTL **5 min** (refreshed on use), optional `"ttl": "1h"`. Read 0.1× base (0.05× on Opus/Sonnet 5.5).
- (iii) Rounds are 800 s apart. OpenAI's 30 min default keeps a static prefix warm between rounds. On Anthropic, 5 min expires, so use 1 h TTL or accept a cold write every round. Put rules, schema and trade price anchors first, and the case (policy, story, invoice) last. The gain is mainly TTFT on the 15 s tier. Measure `cached_tokens` on Game 0 before claiming it.

---

## 4. Published full pipelines (document + policy → decision with calibrated uncertainty)

(i) **Nothing ready to copy exists** that does document + policy → line decision **with calibrated uncertainty**. The best *design* to copy is
**InsClaimBench's decision chain** (atomic rule judgments → coverage/exclusion/causation modules → payable → amount) [opened]. It maps 1:1 onto our
schema: per line `covered_by`, `excluded_by`, `caused_by_event` → `p_valid`, then price. Its finding that correct finals hide wrong intermediate judgments
argues for logging the intermediate fields and checking them against the final decision.
Small GitHub/HF demos exist (a claim-adjudication repo, a FEMA flood-appeal agent example, an HF "policy analyst" Space). All are [snippet] only, tiny or demo-grade (§6).
For interval calibration the only close method paper is PIE (2509.07309, [snippet]): regression on confidence features (verbalised confidence plus consistency) beat
LLM-as-judge intervals. That is the same idea as the σ rule in §3.2.

---

## 5. Concrete pipeline this implies (iii, for the team to accept or reject)

```
t=0     key → decrypt → pdftotext -layout → regex parse + assertions (≤100 ms)
        tier 0: qty from parser × trade-anchor unit price × 1.19; p_valid prior (e.g. 0.85; 0.15 if the line's
                keywords hit an exclusion clause / "Wartung|service|annual"); σ = trade floor → a,b → SUBMIT (<5 s)
        launch in parallel: FAST (low effort, cached prefix, batched schema, no photo)
                            STRONG (low/medium effort, + low-res photo)
~15 s   FAST → merge (p50 from LLM, σ from max(floor, disagreement with tier 0, stated×m)) → SUBMIT
        if FAST agrees with tier 0 within δ on all lines and p_valid ∈ {<0.1, >0.9}: cancel STRONG
~45 s   STRONG → merge (σ from FAST-vs-STRONG spread) → SUBMIT; hard stop at 55 s
log     tokens per tier, escalation/cancel rate, per-line disagreement (accuracy-per-token evidence for the jury)
```

---

## 6. Unverified (snippet/memory only; do not cite without opening)

- **LegalBench insurance-policy-interpretation task** (arXiv 2308.11462): 3-way covered / not covered / unclear. [snippet]
- **CUFEInse** (arXiv 2511.07794): Chinese insurance benchmark including claim settlement. [snippet]
- **AuditCopilot** (arXiv 2512.02726): LLMs for ledger fraud on synthetic data. **Typed anomaly injection in ledgers** (arXiv 2610.06133). **Legal invoice line-item synthetic anomalies** (arXiv 2012.14511, non-LLM). [snippet]
- **BillSim** HF dataset `samreed-research/billsim`: synthetic billing-graph anomalies, non-adversarial. [snippet]
- **Cleanlab/insurance-claims-extraction**, **Maniac/Insurance_dataset**, **rvpierre/insurance-qa-en**, **deccan-ai/insuranceQA-v2** (HF): extraction or generic insurance QA, none on line-level coverage. [snippet]
- **GPT-4V in insurance** (arXiv 2404.09690): image hallucination, weak loss assessment. [snippet]
- **PIE: Performance Interval Estimation** (arXiv 2509.07309). [snippet]
- **Invoice IE survey** (arXiv 2510.15727). [snippet]
- Marker v2 vs MinerU/Docling numbers (MarkTechPost, Jul 2026: Marker 2.9 pages/s B200, Docling 50.3 % at 2.1 pages/s on olmOCR-bench). Secondary source quoting the vendor. [snippet]
- 555vedant/plum (GitHub claim adjudication), superlinked/sie insurance-claims-agent example, HF Space desolo-2918/Insurance-Policy-Analyst, arXiv 2606.06089 (modular claims pipeline). [snippet]
- Surveys: Behera et al. arXiv 2506.06579 (routing/hierarchical inference), Moslem arXiv 2603.04445 (routing and cascading survey), arXiv 2611.15911 (smart model routing). [snippet]
- COThink (arXiv 2505.22017), "Decomposing Reasoning Efficiency" (arXiv 2602.09805, correct answers per 1k tokens). [snippet]
- OpenAI "better prompt caching for GPT-6" post (openai.com/index/better-prompt-caching-for-gpt-6). This may change the retention defaults for the GPT-6 Luna model claimbot uses. Check before relying on the 30 min figure. [snippet]
- Mistral OCR, Qwen2.5/3-VL, Donut, Nougat as invoice parsers. Not opened. Irrelevant for a born-digital, fixed template. [memory]
- Milliman Dec 2025 report on GenAI motor-claim photos (humans ~50 % at spotting fakes). Industry report, not primary research. [snippet]
