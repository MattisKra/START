# Slice D2: parallelising the live pipeline under a 60 s round (and using the 740 s between rounds)

Author: Claude (research sub-agent D2), 2026-11-21, ~30 min time-box. Read `CONTEXT.md` first; slice B (`claude-B-pipeline-fraud-routing.md`) already covers
parsing, cascades/routing, reasoning effort, structured output and prompt caching, so I don't repeat those here.
Tags: **[opened]** = I (or a fetch sub-agent) read the primary page and quote it. **[opened\*]** = primary page read, but the number came from the fetch tool's
summary of a part not shown verbatim, so re-check before citing to the jury. **[measured]** = measured on this machine today. **[snippet]/[memory]** = §8 only.
Labels: **(i)** published result, **(ii)** my interpretation, **(iii)** hypothesis that it transfers to our setting.

---

## 0. Bottom line

**Two measured facts change the design.** I read them from the zip central directories, which can be listed without the key. No content was decrypted.

| Fact [measured] | Value | Consequence |
|---|---|---|
| `policy.txt` size over the 101 archives | min 866 B (case 0 only) · p25 41 KB · **median 55.8 KB** · p90 66 KB · max 74.6 KB. **99/101 > 20 KB.** | Live cases have a policy of roughly **10-20 k tokens** (my estimate, not tokenised), while case 0 is tiny. **Every latency and cost number taken from case 0 underestimates live rounds.** The policy is also the input that makes each extra parallel call expensive. |
| Photos per case | 0 photos: 1 case · 1: 93 · 2: 6 · 3: 1. Total photo bytes: median 3.3 MB, p90 9.3 MB, max 31 MB (case 44: 3 PNGs). | Uploading full PNGs as base64 (+33 %) puts megabytes on the critical path over venue Wi-Fi. Downscale them in a parallel stage before any call. |
| `invoices.pdf` size | 14-75 KB (case 0: 15 KB) | Many cases probably have more lines or pages than case 0's 4. Not verifiable until the keys are released. |
| `7z`/`7zz` on this Mac | **not installed** (`which` finds nothing). `claimbot/case.py:_sevenzip` raises without it. `materials/pixi.toml` ships `p7zip`. | `play_round` crashes on round 1 unless it runs inside the pixi env or `brew install sevenzip` is done. **This is the highest-priority reliability fix.** |

**Ranked patterns.** Gains are expected-value judgments (ii/iii). Nothing here is measured on live cases yet.

| # | Pattern | Expected gain | Extra token cost | Risk | How to test (no ground truth needed) |
|---|---|---|---|---|---|
| 1 | **Deadline-driven anytime submitter** (asyncio). Tier 0 is deterministic and goes out at ≤ 3 s. After that, re-submit **the full line set** whenever the merged belief improves. Final PUT by T0+54 s, last-chance PUT at T0+57 s. Per-call timeouts come from the remaining budget, with `max_retries=0`. | **Largest.** Never a `b = 0` round (`01-claimbot-review.md` #2). The 10-min SDK default timeout and the retry-at-50 s behaviour go away. | 0 | low | Fake game server plus fault injection (§6). Assert a PUT with all indices lands by 3 s and by 54 s in 100 % of 1,000 simulated rounds. |
| 2 | **Decompose by input, then fan out only where inputs are small.** (a) One coverage/relatedness call reads policy + story + lines, has **no photo** and returns short output. (b) Price-level calls read story + lines and **no policy** (~1-2 k tokens), so they are cheap enough to run **k = 2-3 across providers**. (c) The photo/quantity check runs only on m²/pcs lines. | High for price accuracy at low cost. The expensive input (policy) is sent once, and samples go to the hard part (price level). | (b) ~k × 2 k input tokens instead of k × 15 k | medium (merge logic) | Replay released cases. Compare the merged price against the slow oracle (§4) with pinball loss at τ = 0.33/0.5, against the current single monolithic call. Report Δloss per 1 k tokens. |
| 3 | **Median aggregation of cross-model price p50s**, a **linear-pool (mixture) σ** instead of a quantile average, and an inflation floor. | Medium. Location gets more robust, and σ is never narrower than the models' disagreement. | included in #2 | low | Coverage of the fast-tier interval against oracle p50 on released cases. Target: the 80 % interval covers ≥ 75 %. |
| 4 | **Early stop on agreement.** If the first 2 price answers agree (|log ratio| < δ ≈ 0.1 on every line), cancel the 3rd and skip escalation. | Saves ~⅓ of price-tier tokens on easy cases (iii). | negative | low | Log how often the stop fires and the loss gap between stopped and full runs on replays. |
| 5 | **Pre-round planning from the zip directory plus warm-up at T−60 s.** Read file names and sizes (policy length, photo count, PDF size). Open TLS connections. Run a 1-token health check per provider. Measure clock offset from the game API's `Date` header. Optionally warm the static prompt prefix. | Low-medium (a few hundred ms to seconds), but it removes cold-start variance. | ~0 | low | Log T0→key and T0→first-byte with warm-up on and off over the first rounds. |
| 6 | **Two-phase extraction.** Extract `policy.txt`, `description.txt` and `invoices.pdf` first and start the text calls. Extract and downscale photos in parallel. | Photo decode and upload come off the critical path. | 0 | low | Time `extract_text` → first LLM byte on case 0 and synthetic big-photo fixtures. |
| 7 | **Between-round slow oracle, price book and σ re-fit** in a separate low-priority process with its **own API keys / rate-limit budget**, hard-stopped at T_next − 120 s. | Medium-high over 100 rounds. It provides the only labels we will ever have, and the evidence for the write-up. | Large per case, but off the clock. Report it separately as "offline compute". | Low if it is isolated. High if it shares a rate limit with the live call (429 in a live round). | Its own outputs are the test harness for #2-#4. |
| 8 | **Supervision.** One long-running scheduler under `caffeinate` and launchd/tmux, a heartbeat file, a dead-man alert, and **one** submitter only (last write wins). | Prevents the overnight failure modes: sleep, Wi-Fi drop, crashed process. | 0 | low | Chaos drills (§6). Kill -9 mid-round and confirm the restart submits tier 0 before T0+30 s. |

**Single most promising edge (ii/iii).** Split the monolithic call by input. Coverage needs the 55 KB policy but is easy (CONTEXT). Price is the hard part and needs only a
few hundred tokens of story plus lines. So the parallel budget should go to **2-3 cross-provider, policy-free price calls aggregated by median**, with the
policy read once. This is "economical, not brute force" in a form the jury can verify: tokens per round drop while the number of independent
price opinions rises. The current design does the opposite. It re-sends policy and photo in every parallel call (`estimator.build_input`) and gets
its diversity from reasoning effort, which the literature says buys little (§1.4).

---

## 1. When fan-out beats one stronger call (evidence)

### 1.1 Numeric aggregation of several LLM answers

| Source | (i) Published result | (ii)/(iii) Use here |
|---|---|---|
| **Chuang et al., "Probing LLM World Models: Enhancing Guesstimation with Wisdom of Crowds Decoding"**, arXiv 2501.17310 v4 (23 Sep 2025), arXiv non-exclusive licence. [opened] | Table 1 (MARBLES, normalised error, columns WOC/median · self-consistency · mean · greedy): llama-3.1-70b **0.49** · 1.07 · 3.12 · 6.55. gpt-4-0125 **1.00** · 1.07 · 1.29 · 1.04. Taken over "30 sampled reasoning paths" at T = 1. §3: "WOC decoding using 5 samples achieves higher accuracy than self-consistency decoding using 30 samples." Limitations: the gain was "less consistent" in a German-election follow-up. | (ii) For numbers, **take the median, never the mean**: the mean is wrecked by one outlier sample. The gain is large for the weaker model and small for GPT-4 (1.00 vs 1.04 greedy). (iii) With frontier models expect a small location gain, while the robustness to a single bad sample remains. 3 samples is a reasonable minimum, since a median of 2 is just a mean. |
| **Talebirad et al., "Wisdom of the Machines: Exploring Collective Intelligence in LLM Crowds"**, AAMAS 2026, pp. 2456-, CC BY 4.0. [opened] (PDF p.1-3 only) | Abstract: "aggregating deterministic (temperature 0) outputs from a diverse set of models is the most effective strategy, outperforming any single model, as temperature-induced diversity provides no significant benefit while increasing inference costs. The median aggregation of deterministic responses from multiple models outperformed 68% of individual guesses on average, with context providing a significant additional benefit for tasks where it is directly informative (e.g., product titles for price estimation)." Models: Qwen2-VL-72B, Llama-3.2-Vision-11B, GPT-4o-mini. Tasks include **Amazon product prices from images**. | (ii) This is the closest published analogue to our price pass: numeric, price, vision, median. **Diversity should come from different models at T = 0, not from temperature.** Caveat: these are older, weaker models, and "68 % of individuals" is not "better than the best model". |
| **Schoenegger et al., "Wisdom of the Silicon Crowd"**, arXiv 2402.19379 v6 (22 Jul 2024), arXiv licence; published in Science Advances. [opened] | 12 LLMs × 3 queries, "we computed the median from all non-missing forecasts on each question" (§2.1). The LLM crowd "is not statistically different from the human crowd" (abstract). Shared bias: mean forecast 57.35 % with 14/31 positive (§3.1, "acquiescence bias"). | (ii) The median of a model crowd works, but the **crowd shares a directional bias**. For us the analogous risk is that all models share a Munich-2026 price bias. The ensemble does not remove it, and only the price book / oracle can (§4). |
| **Halawi et al., "Approaching Human-Level Forecasting with Language Models"**, arXiv 2402.18563 v1 (28 Feb 2024), CC BY 4.0. [opened] / [opened\*] | Fig. 1(b) caption: "The forecasts are then aggregated into a final forecast using the trimmed mean." [opened\*] Validation Brier (Table 14): trimmed mean 0.1649, median 0.1651, geo-mean 0.1655, mean 0.1656, so the aggregators barely differ. Table 3 caption: "in every setting the aggregate (average) of our system and crowd prediction is the best." [opened] | (ii) Once outliers are handled, the choice of robust aggregator matters little. **Averaging with an independent source matters more.** (iii) Our second source is the cross-case price book (§4.2). Combine LLM median and book prior in log space, weighting each by its observed error. |
| **Renda et al., "OpenEstimate"**, arXiv 2510.15096 v2 (22 Apr 2026), arXiv licence. [opened] | §3.1: "all model families exhibit a tendency towards systematic overestimation". Fig. 4: overconfidence on 2 of 3 datasets. Table 3, CRPS ratio vs a 5-sample statistical baseline: o4-mini 2.42 / 1.17 / 1.01. §3.2: temperature, reasoning effort, system prompt and elicitation protocol: "None of the settings tested has a consequential impact on performance." | (ii) Independent support for slice B's point that reasoning effort is not where accuracy comes from. LLM-stated intervals are usually too narrow. (iii) Spend the parallel budget on independent sources, not on higher effort of the same model. |
| **Lichtendahl, Grushka-Cockayne & Winkler, "Is It Better to Average Probabilities or Quantiles?"**, Management Science 59(7), 2013. [snippet] (paywalled) | Per abstract snippets: both averages have the same mean, and the quantile average is always sharper (lower variance). | (ii) If our sources are **over-confident** (OpenEstimate; slice B's overprecision evidence), the sharper quantile average makes things worse. **Use a linear pool (mixture of the per-model lognormals) for σ**, or at minimum σ = max(median stated σ, cross-model log-spread) × inflation. |

### 1.2 Diversity vs quality, and correlated errors

| Source | (i) | (ii)/(iii) |
|---|---|---|
| **Li, Lin, Xia, Jin, "Rethinking Mixture-of-Agents: Is Mixing Different LLMs Beneficial?"**, arXiv 2502.00674 v1 (2 Feb 2025), CC BY 4.0; TMLR 2026. [opened] | Table 1, AlpacaEval 2.0 LC: 2-layer MoA 59.1 vs 2-layer Self-MoA 65.7. Table 3 (MMLU/CRUX/MATH): Mixed-MoA 68.21/45.50/62.56 vs Self-MoA 69.01/50.75/68.42. §4: "There exists a trade-off in the achievable Pareto front between diversity and quality." Quality coefficients exceed diversity coefficients on all three tasks (Table 4). | (ii) This seems to contradict Talebirad, but it doesn't: mixing helps only when the members are of **comparable quality**. Adding a weak cheap model to a median of 3 drags it. (iii) Choose the 2-3 price models by **measured agreement with the oracle on released cases**, not by brand diversity. |
| **Kim, Garg, Peng, Garg, "Correlated Errors in Large Language Models"**, arXiv 2506.07962 (9 Jun 2025), CC BY 4.0, ICML 2025. [opened] | "models agree 60% of the time when both models err" (abstract, Helm). Same company and same architecture raise agreement (Table 1). "pairs of models that are more accurate individually also have more correlated errors" (§1). | (ii) The ensemble spread **understates** uncertainty, and more so with stronger models. Use the spread as a lower bound on σ, never as σ itself. |
| **Hossain, Yousefi, Lim, "Agreement Overstates Evidence: Error Dependence in LLM Judge Consensus"**, arXiv 2609.22512 v1 (18 Sep 2026), CC BY 4.0. [opened] / [opened\*] | Abstract: mean pairwise error correlation 0.21, and "the ten judges only provide roughly as much statistical information as 3.5 independent judges." Intro: "Judges from different providers are about as correlated as judges from the same provider." "mixing frontier and open-weight judges provides the most independent information." | (ii) Diminishing returns are steep: going from 3 to 10 members buys little. (iii) **k = 2-3 is the sensible ceiling inside 60 s.** If a third member is added, use an open-weight model rather than a third frontier vendor. That is cheap, and per this paper the most independent choice. |
| **Chen et al., "Are More LLM Calls All You Need? Towards Scaling Laws of Compound Inference Systems"**, arXiv 2403.02419 v2 (4 Jun 2024), arXiv licence; NeurIPS 2024. [opened] (abstract only) | "the performance of both Vote and Filter-Vote can first increase but then decrease as a function of the number of LM calls"; "more LM calls lead to higher performance on 'easy' queries, but lower performance on 'hard' queries". | (ii) That is a voting result, but it implies **k should be chosen empirically**, not maximised. (iii) Our "hard" lines are unusual trades with a shared price bias, where more samples only tighten a wrong median. Pick k from the replay curve (§4.3). |
| **Wang et al., "Mixture-of-Agents Enhances LLM Capabilities"**, arXiv 2406.04692 v1 (7 Jun 2024), CC BY 4.0. [opened] | 65.1 % LC win (Table 2a). §5 Limitations: "the model cannot decide the first token until the last MoA layer is reached. This potentially results in a high Time to First Token (TTFT)". | (ii) A **layered LLM aggregator** (an LLM that reads the other LLMs' answers) puts a whole extra LLM call on the critical path. Inside 60 s, aggregate **numerically in code**. |

### 1.3 Early-stopping rules

- **Aggarwal et al., "Let's Sample Step by Step: Adaptive-Consistency…"**, arXiv 2305.11860 v2 (16 Nov 2023), CC BY 4.0, EMNLP 2023. [opened] Beta/Dirichlet posterior stop at C_thresh = 0.95.
  "reduces sample budget by up to 7.9 times with an average accuracy drop of less than 0.1%". Table 1: math 40 → 13.8 samples (3.3×), Δacc −0.1.
- **Li et al., "Escape Sky-high Cost: Early-stopping Self-Consistency"**, arXiv 2401.10480 v1 (19 Jan 2024), ICLR 2024. [opened] "Stop sampling when answers within a window are all the same". Window 5 (8 for MATH).
  The abstract reports large sample savings (GSM8K −80.1 %), but the per-dataset labels in the abstract and Table 1 look swapped, so re-check before citing.
- (ii) Both methods are for discrete answers with 40-64 samples. We have ≤ 3 numeric samples, so only the *idea* carries over. Adapt it as: **stop after 2 answers if every line's
  |log(p50₁/p50₂)| < δ and both give the same coverage verdict; otherwise wait for the 3rd.** Set δ from replays as the value below which adding the 3rd changed the oracle pinball loss by < 1 %.
  (iii) Because the price calls run in parallel, an early stop saves **tokens, not wall-clock**. The 3rd call is already running, so the stop must actually cancel it (§3.3). Whether a cancelled request is billed is provider-specific and unverified (§8).

### 1.4 Net judgement on fan-out vs one stronger call (ii)
Fan-out beats a single stronger call **only when** (a) the members are of similar measured quality, (b) they are from different families, (c) aggregation is a robust statistic in code (median),
and (d) the per-call input is small. In our task (a)-(d) hold for the **price** sub-question, and fail for coverage, where the input is a 55 KB policy, the task is easy and the answer is close to binary.
For coverage, one call plus an escalation only on disputed or expensive lines (slice B's cascade) is better value.

---

## 2. Frameworks: what they cost inside 60 s

| Option | Evidence | Verdict for the live path |
|---|---|---|
| **LangGraph / CrewAI / AutoGen / OpenAI Agents SDK** | **Orogat, Rostam, Mansour, "Architectural Design, Not Only Model Intelligence, Governs Multi-Agent LLM Performance" (MAFBench)**, arXiv 2602.03128 v2 (17 Sep 2026), SIGMOD 2027. [opened] Abstract: "Orchestration alone increases latency by over 60×". Table 1 orchestration row: 1.1× best, 62× worst. Table 9 p50 on a trivial task [opened\*]: direct LLM 495 ms, LangGraph 548, CrewAI 741, AutoGen 964, "OpenAI SDK" 1,275, Concordia 30,564. Abstract: schema-constrained planning interfaces "reduce accuracy by up to 32 points through formatting failures". | (ii) The 50-800 ms of overhead is affordable in 60 s. **What we cannot afford is hidden retry and timeout behaviour plus the formatting-failure modes.** The pipeline is a fixed DAG of ≤ 5 calls with no tool loop, so a framework adds nothing we need. **Don't use one live.** LangGraph is acceptable offline (§4) if someone already knows it. |
| **Claude Agent SDK** | Hosting docs [opened]: "the SDK spawns a separate `claude` CLI process and talks to it over stdio"; "One agent session maps to one subprocess"; "1 GiB RAM, 5 GiB disk, and 1 CPU per agent is a reasonable starting point". Pre-warm (`startup()`) exists in TypeScript only. A GitHub issue reports ~80 s to first message on Windows [snippet]. | **Not for the live path.** Use the plain Messages API with `httpx`/`anthropic` async. The Agent SDK is fine for the offline oracle, if it is useful there at all. |
| **Temporal** | Docs [opened]: "Workflow Task Execution is typically very fast (milliseconds)". Its purpose: "Durable Execution preserves state and progress so code resumes after transient failures." No scheduling-latency figure. | (ii) It solves durability across hours, which we need only between rounds, and it requires a server. **Overkill.** A JSON-lines log plus an idempotent restart gives the same durability for one process. |
| **Ray** | Moritz et al., arXiv 1712.05889 v2, OSDI 2018. [opened] "scaling beyond 1.8 million tasks per second", "millisecond-level latencies". | It solves cluster scheduling, and we have ≤ 10 concurrent I/O-bound calls on one machine. **Overkill.** |
| **Hand-rolled asyncio** | Python docs [opened]: `TaskGroup` cancels the remaining tasks when one fails. That is **wrong** for a race, so use `create_task` + `asyncio.wait(FIRST_COMPLETED)`. "`wait()` does not cancel the futures when a timeout occurs." `as_completed` "does not cancel the tasks". openai-python README [opened]: "By default requests time out after 10 minutes", "retried 2 times by default", `AsyncOpenAI` has identical functionality. | **Use this.** About 80 lines, no hidden retries, explicit cancellation. A sketch is in §3.3. |

**Cross-check of claims the provider-mechanics agent is likely to make:**
- *Hedged requests.* Dean & Barroso, "The Tail at Scale", CACM 56(2) 2013, read from the authors' PDF at barroso.org [opened]: defer the secondary request
  "until the first request has been outstanding for more than the 95th-percentile expected latency for this class of requests. This approach limits the additional load to approximately 5%";
  BigTable: "sending a hedging request after a 10ms delay reduces the **99.9th-percentile** latency for retrieving all 1,000 values from 1,800ms to 74ms while sending just 2% more requests".
  The page says it is p99.9; secondary sources mislabel it as p99. They also note that more aggressive hedging "requires faster cancellation of requests".
  (ii) The transfer caveat: their requests are idempotent ms-scale reads on replicas, ours are 5-40 s generative calls on a shared provider. A hedge at the p95 point (say 25 s) leaves too little time for
  a hedge of the same size to finish, so **the hedge for an LLM call must be a different, faster model, launched at t = 0 rather than at p95.** That is exactly the fast/strong race.
  A late same-model hedge only helps if p95 is well under 30 s, which needs to be measured.
- *Cancellation saves cost.* Unverified for every provider (§8). Don't claim it in the write-up until `usage` on a cancelled request (or the provider's billing page) shows it.
- *Prompt caching across concurrent calls.* Whether two calls sent at the same instant with the same prefix both pay full prefill is unverified (§8). If it matters, stagger by about 1 s, or use the policy-free price calls of pattern #2, which makes the question moot.

---

## 3. Concrete parallel decomposition for this task

### 3.1 Dependency graph (text form)

```
PRE-ROUND (T0-120 s .. T0), no case content available
  P1  list zip central directory  -> plan {policy_bytes, n_photos, photo_bytes, pdf_bytes}
  P2  open TLS to game API + each LLM provider; 1-token health check; clock offset from HTTP Date
  P3  (optional) warm static prompt prefix per provider   [slice B §3.4]
  P4  load price book + calibration params from last between-round job (read-only snapshot)

LIVE ROUND
  S1  poll GET /key from T0-1 s every 250 ms            (needs: nothing)       wall: RTT, unmeasured
  S2a 7z x -i policy.txt description.txt invoices.pdf   (needs S1)             wall: ms, unmeasured
  S2b 7z x photo*  ->  Pillow downscale <=1024 px JPEG  (needs S1)             off critical path
  S3  pdftotext -layout  -> raw invoice text            (needs S2a)            ~50 ms (slice B, unmeasured here)
  S4  regex POS parser -> lines L (index, desc, qty, unit, approx-flag)  (needs S3)   <1 ms
  S5  policy clause splitter (regex on "1.x/2.x/3.x")   (needs S2a)            <10 ms
  S6  trade classifier + price-book lookup -> prior per line    (needs S4)     <10 ms
  T0* TIER-0 SUBMIT  (a,b) from prior + deterministic exclusion keywords  (needs S4,S6)   target <= T0+3 s
  L1  COVERAGE LLM   policy+story+raw invoice, no photo, short JSON   (needs S2a,S3; NOT S4)   unmeasured
  L2  PRICE LLM x k  story+raw invoice lines, no policy, k=2-3 cross-provider (needs S2a,S3)  unmeasured
  L3  PHOTO/QTY LLM  photo(s)+story+m2/pcs lines only, optional        (needs S2b,S3)  unmeasured
  M   merge in code: q from L1 (else prior), mu = median(L2 p50s) shrunk to prior,
      sigma = max(linear-pool sigma, spread) x inflation, qty cap from L3   (needs any subset)
  SUB submit FULL line set when the merged (a,b) moves by > eps; final at T0+50..54; last-chance T0+57
```

**Independent stages** (they can start the moment their inputs exist): {S2b, S3, S5} after S1/S2a, and {L1, L2, L3} after S3 (L3 also after S2b).
**Speculative before parsing:** the LLM calls need only the raw `pdftotext` output, not the regex parse (S4). The parse is used for **indexing and merging**,
so a parser failure must not delay the LLM calls. If S4 fails, the merge falls back to the LLM's own POS numbers and must still pass the index assertion before any PUT.
**Nothing case-specific can start before S1.** The case content is encrypted until the key arrives. The file sizes (P1) are the only per-case signal available before T0.

**Critical path:** S1 → S2a → S3 → max(L1, L2) → M → SUB. L3 is off the critical path by design: the merge uses it only if it arrives in time.
Slice B puts the strong call at ~45 s. If we keep a strong monolithic call, it becomes the critical path, and pattern #2 is what takes it off.

### 3.2 Wall-clock per stage
I found **no primary vendor page with TTFT or tokens/s for the current models** (GPT-6 Luna, Claude 5.5, Gemini 4, etc.) and did not cite third-party leaderboards.
**All LLM stage times are unmeasured.** The only primary latency figure found is the MAFBench direct-LLM p50 of 495 ms on a trivial prompt [opened\*]. It is a lower bound on one round-trip and says nothing about a 15 k-token prefill.
**How to measure (≈ 20 min, no game API):** build 3 synthetic fixture cases from case 0. Pad the policy to 55 KB and 75 KB with neutral clauses, use 4 and 10 invoice lines, and 0, 1 and 3 photos.
Run each model in `research/eval/candidates.json` **sequentially** (`or_compare.py` runs calls in parallel, which confounds latency), with 5 repeats per model.
Record wall-clock, TTFT (stream=True), input/cached/output/reasoning tokens and cost, and report p50/p95 per (model, stage). This table is the "reliability within 60 s" evidence for the jury.
Pick the L2 members as the models whose p95 is ≤ 20 s on the 75 KB fixture **and** whose price p50 is closest to the oracle on released cases.

### 3.3 Minimal async fan-out (sketch; replaces the ThreadPoolExecutor race)
Problems in the current `runner.play_round` that this fixes, beyond `01-claimbot-review.md` #2/#7:
(1) `t0` is taken when the function starts, not from the server's `start_time`, so a late manual start silently overruns the real deadline.
(2) `OpenAI(timeout=50, max_retries=1)` can retry at ~T0+50 s and run past the deadline.
(3) `shutdown(wait=False, cancel_futures=True)` cannot stop threads that are already running. Calls keep running (and billing) after the round, and the interpreter's exit joins them.
(4) A single `get_key` call returns 403 if issued a few ms early.

```python
async def play_round(game, plan):
    deadline = server_start(game) + 60 - clock_offset - 6          # absolute, from server time
    key = await poll_key(game, until=deadline)                    # retry 403 every 250 ms
    case = await to_thread(extract_text_files, key)               # S2a
    photos = create_task(to_thread(extract_and_downscale, key))   # S2b, off critical path
    raw = pdftotext(case.pdf); lines = parse_pos(raw)             # S3/S4 (S4 may fail -> None)
    best = tier0(lines, price_book); await submit(game, best)     # T0*, full line set
    def budget(): return max(1.0, deadline - now())
    tasks = {create_task(coverage(case, raw, timeout=budget())): "cov"}
    for m in PRICE_MODELS:                                         # k = 2..3, different families
        tasks[create_task(price(m, case.story, raw, timeout=budget()))] = m
    results = {}
    while tasks and now() < deadline:
        done, _ = await asyncio.wait(tasks, timeout=deadline - now(), return_when=FIRST_COMPLETED)
        for t in done:
            name = tasks.pop(t)
            if not t.cancelled() and t.exception() is None: results[name] = t.result()
        if agree_early(results): cancel_rest(tasks, keep={"cov"})  # early stop on price agreement
        new = merge(lines, results, price_book)                   # deterministic, monotone in info
        if changed(new, best): best = new; await submit(game, best)
    for t in tasks: t.cancel()                                     # really cancels the HTTP call
    await submit(game, best, final=True)                           # idempotent; ≤ T0+57 s
```
Rules: every client gets `max_retries=0` and `timeout=budget()`; `submit` never raises (log and continue) and is retried once if more than 2 s of budget remain. Merging is order-independent: it uses
the **set** of results, so the "fast result overwrites full result" race (`01-claimbot-review.md` #7) cannot happen. Every PUT carries **all** indices, because the handbook says omitted lines take defaults.

---

## 4. Between rounds: using the 740 s safely

(i) **Sleep-time compute.** Lin, Snell, … Gonzalez, arXiv 2504.13171 v1 (17 Apr 2025), CC BY 4.0. [opened] "During sleep-time we are given the context c but not the query q".
Result: "reduce the amount of test-time compute needed to achieve the same accuracy by ∼5×". "decrease the average cost per query by up to 2.5× when there are 10 queries per context".
Benefit is "well correlated" with how predictable the query is from the context. It beats pass@k parallel scaling at equal test-time tokens, but at high test-time budgets the baseline "slightly outperforms".
(ii) Our next case is encrypted, so per-case pre-computation is impossible. What *is* predictable is the **distribution**: trade families, recurring invoice items, and (possibly) policy templates. Sleep-time work should therefore build
**case-independent artefacts** that shrink the live call.
(The anytime-algorithm literature, Zilberstein 1996 AI Magazine, is the classic framing of "interruptible algorithms with a monotone quality profile". I could not open it (bot wall), so it is [memory]/§8 only.)

Jobs, in priority order. They run in a separate process (`nice`), never on the live API keys, and are hard-killed at T_next − 120 s:
1. **Slow oracle on the just-released case.** The key is public after the round. Run the strongest available models at high effort, each **twice** (two families), with the full policy and full-res photo and no time limit.
   Store the per-line oracle p50 and coverage verdict. This is the only "label" source. It is biased in the same direction as the models (§1.2), so report **oracle disagreement** alongside it.
2. **Score the live tiers against the oracle.** Compute pinball loss at τ = 0.1/0.33/0.5, interval coverage, and tier-0 vs tier-1 vs tier-2 deltas. From that, report **Δ expected payoff per 1 k tokens for each extra call** (value of information).
   This number justifies (or kills) each parallel call in front of the jury.
3. **Update the price book.** Key it by normalised item description + unit, store log-price observations from the oracle, and use shrinkage (hierarchical mean per trade) for the next round's tier-0 prior and the L2 merge.
   Report how often items recur. If they don't recur after ~10 cases, demote the book to a trade-level prior only.
4. **Re-fit the σ inflation and δ (early stop)** on the growing replay set. Publish them to the live process by **atomic file swap** (write tmp, `os.replace`) with a version id that the live process logs. The live process reads the snapshot only at T0 − 60 s, never mid-round.
5. **Policy template digest (iii).** If the released policies share boilerplate (likely, given 41-75 KB sizes from one insurer generator; unverified), precompute clause indices so that the live L1 can be sent
   only the clauses that differ plus §3 exclusions. This is the direct sleep-time analogue and cuts the biggest input. Test it by diffing the first 5 released policies.
6. **Opponent/rule simulation.** Run the `sim/` tournament for candidate (a, b) rules with the updated σ (synthesis edge #3).
7. **T − 60 s pre-flight** for the next round (P1-P4 in §3.1).

**Isolation rules (why it can't hurt the live round):** separate API keys/projects (rate limits are per key/org, and a 429 in the live window is the realistic failure mode); a CPU-only process at lower priority;
no writes to files the live process reads except the atomic snapshot; and a kill switch tied to the schedule (game times are known exactly: `/api/games/list`).

---

## 5. Reliability engineering for one human-run submitter

| Risk | Mitigation | Drill |
|---|---|---|
| 7-Zip missing (true on this Mac today) | Run inside `pixi run` (p7zip), or `brew install sevenzip`. Startup self-test: decrypt nothing, but assert that `7z` and `pdftotext` are found and print their versions. | `python -m claimbot selftest` exits non-zero if a dependency is missing. |
| Mac sleeps overnight (rounds run 13:00 → 11:00) | `caffeinate -dimsu` wrapping the scheduler, mains power, lid open or clamshell with display. Better: a small cloud VM as primary, with the laptop as monitor. | Leave it running 30 min with the lid closed and check the heartbeat. |
| Process crash | launchd `KeepAlive` (or tmux + a restart loop). The scheduler is **stateless per round**: on restart it reads `/api/games/list`, and if inside a live window it goes straight to tier 0. | `kill -9` at T0+10 s on a fake server. Assert the restart submits before T0+30 s. |
| Network loss | Phone hotspot as a second route. All HTTP timeouts are ≤ remaining budget. Tier 0 needs no LLM. | Pull the Wi-Fi at T0+5 s on a fake round. |
| Provider outage / 429 / slow | Cross-provider L2 means any single provider can fail. Health check at T−60 s picks the members. `max_retries=0`. | Fault-injecting proxy: 500, 429, a 40 s stall, truncated JSON, a missing line, a wrong index. |
| Two submitters overwrite each other (last write wins) | **Exactly one** submitting process. The standby runs `--dry-run` and is promoted by a human only. | n/a |
| Deadline from the local clock | Deadline = server `start_time` + 60 s − measured offset (from HTTP `Date`) − margin. | Skew the clock by 5 s in a test. Assert the final PUT is still < T0+57 s server time. |
| Index or VAT error | Assert {submitted indices} == {printed POS}, all values finite and ≥ 0, and gross = net × qty × 1.19 in code (slice B, synthesis §3). | 20 synthetic invoices (slice B §1) plus every released case. |
| Silent wrong answer | A per-round sanity band: Σ a within [0.3, 3]× the tier-0 Σ, unless L1 marks lines excluded. Outside the band: log, alert, and submit the median of tier 0 and the LLM. | Mutate an LLM output ×10 in a test. |
| Secrets | `.env` only, never logged. Redact `X-API-Key`/`Authorization` in the HTTP log hook. Separate keys for live vs offline. | `grep` the logs for key prefixes in CI. |

**Dry-run replays.** Only case 0 is decryptable today, and it is unrepresentative (866 B policy). The replay set grows by one real case per round (keys are released per round),
so by the evening there are ~20 real cases. Until then, use the synthetic big-policy/multi-photo fixtures from §3.2. Replay = the full live code path against a local fake game server,
with time compressed by nothing (real LLM calls), asserting the §3.3 timings.

**Logging that doubles as evidence.** Write one JSON line per event, `{round, t_rel_ms, event, ...}`. Events: plan (P1), key_received, extract_done, parse_done, each call
start/first_byte/end with model, tokens (input/cached/output/reasoning), cost and status, each merge with the per-line (q, μ, σ, a, b), each PUT with payload hash, HTTP status and server `submitted_at`, and cancellations.
From this one file the write-up gets: latency CDF per stage, % of rounds with tier 0 / tier 1 / tier 2 as the final answer, tokens and € per round, how much each tier moved (a, b), and (from §4) Δpayoff per token for each call.

---

## 6. Don't do this (with evidence)

1. **Don't add an LLM aggregator layer (MoA-style) inside the round.** It delays the first token until the last layer finishes (Wang et al. 2406.04692 §5 [opened]). Aggregate numerically in code.
2. **Don't run a multi-agent framework or the Claude Agent SDK on the live path.** Orchestration can add "over 60×" latency, and schema-constrained planning costs up to 32 points from formatting failures (MAFBench 2602.03128 [opened]). The Agent SDK runs one CLI subprocess per session (hosting docs [opened]).
3. **Don't get diversity from temperature on one model.** "temperature-induced diversity provides no significant benefit while increasing inference costs" (Talebirad et al., AAMAS 2026 [opened]).
4. **Don't read the ensemble spread as σ.** Errors are correlated: 60 % of the time two models are wrong together (Kim et al. [opened]), 10 judges ≈ 3.5 independent ones, and cross-provider judges are no less correlated (Hossain et al. [opened]). LLM priors are mostly over-confident (OpenEstimate [opened]).
5. **Don't maximise k.** Voting accuracy can fall as calls increase (Chen et al. 2403.02419 [opened]). Mixing weaker members lowers quality (Self-MoA [opened]). Choose k from the replay curve. It is probably 2-3.
6. **Don't buy accuracy with reasoning effort by default.** "None of the settings tested has a consequential impact" (OpenEstimate §3.2 [opened]). See also slice B §3.2.
7. **Don't send the 55 KB policy and full-res PNGs in every parallel call.** Measured sizes are in §0. That is the token-maxing the jury penalises, and it also costs wall-clock.
8. **Don't rely on SDK defaults.** The default is a 10 min timeout and 2 retries, including on timeouts (openai-python README [opened]). Ours are 50 s and 1 retry.
9. **Don't use `TaskGroup` for the race** (one failure cancels the rest). And don't assume `wait`/`as_completed` cancel anything (Python docs [opened]).
10. **Don't run offline oracle jobs on the live keys, and don't run two submitters.** The first risks 429s mid-round, the second gives last-write-wins chaos.
11. **Don't benchmark latency on case 0 alone.** Its policy is 1/64 of the median live policy [measured].
12. **Don't hedge with the same model at p95.** The Tail at Scale's p95 hedge targets ms-scale idempotent reads ([opened]). For a 20-40 s generation, the hedge must be a faster model launched at t = 0.

---

## 7. Open questions this slice could not settle
- TTFT and tokens/s of the candidate models on a 15 k-token prompt (measure, §3.2).
- Whether policies share a template (diff the first released cases).
- Whether the leaderboard shows per-round scores, which would allow a live A/B of k = 1 vs k = 3 on top of the offline value-of-information estimate.

## 8. Unverified (snippet / memory, do not cite without opening)
- Lichtendahl, Grushka-Cockayne, Winkler (2013) Management Science 59(7):1594-1611, "quantile average is always sharper". [snippet: IDEAS/RePEc + INFORMS listing]
- Zilberstein (1996), "Using Anytime Algorithms in Intelligent Systems", AI Magazine 17(3): definitions of interruptible vs contract anytime algorithms. [memory; the OJS page was bot-walled]
- Claude Agent SDK ~80 s first-message latency on Windows (GitHub issue, closed 2026-02-23). [snippet]
- Whether cancelling an in-flight request (closing the HTTP connection) stops generation billing at OpenAI / Anthropic / Google / OpenRouter. [memory: generally *not* guaranteed for non-streaming requests]
- Whether concurrent requests with an identical prefix share a prompt-cache write. [memory: the first request must finish prefill before others hit the cache]
- OpenAI image handling: high-detail images are internally resized (≈ 2048 px long side, 768 px short side), so uploading 1536×1024 PNGs at full size wastes upload bandwidth. [memory]
- CGES (arXiv 2511.02603), ReASC (arXiv 2601.02970), CASE (EMNLP Findings 2026): newer confidence-weighted early-stopping methods. [snippet]
- AIMultiple and DEV.to framework benchmarks (contradictory LangGraph rankings). [snippet; not primary]
