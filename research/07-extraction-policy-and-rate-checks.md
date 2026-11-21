# Is the error in reading, coverage, or pricing?

The strongest evidence points to three different decisions. An invoice can be read correctly, the work can be covered, and the team can still lose money by choosing the wrong payable hours or reviewer limit. Game 18 demonstrates this distinction. Game 20 demonstrates why a rate lookup should follow the coverage check.

## What the archive can establish

At archive revision `6af8d68`, games 1–21 have settlements and games 1–15 have tracked reader outputs. The latter contain 134 completed calls, 530 line rationales, coverage and causation flags, justified quantities, price percentiles, model effort, latency and token usage. There are reasoning-token counts on 72 calls. The rationales are the models' stated explanations. Token counts measure reported compute. Neither establishes what happened internally. The ten recorded failures were in game 5 and all cited the image-size limit. The shared log has no recorded timeout in this 15-game block. [Reader log](../outputs/model_outputs.json) · [Output schema](../claimbot/schema.py)

**Extraction.** I compared invoice PDFs, archived plain text and the official settlement position numbers for all 139 lines. There are 108 piece-based lines, 25 flat rates, five hourly lines and one metered electricity line. Every one of the 530 saved model line records agreed with the printed position, invoiced quantity and unit. This does not validate the interpretation of the description, photo, or justified quantity. Two editions of a policy can also require different actions on identically worded invoice lines. [Reproducible audit](bench/check_invoice_archive.py)

I reproduced one implementation defect outside those 15 logged games. Game 20's specialist parser failed on `2,412.1 kWh`, and the reference selector missed that position. The shared quantity pattern now accommodates that printed format. PDF and plain-text paths agree on all 139 positions. The main free-text reader in the archived experiment also read 2,412.1 correctly. [Specialist parser](../claimbot_multiagent/settlement.py) · [Regression test](../claimbot_multiagent/test_system.py)

**Policy and scope.** Game 1 previously exposed a missed half-payment provision. Game 18 §7.1.7(g) allows customary local trade labour. Its 1½ days on site describe attendance across the job. The case gives neither a technician time sheet by task nor a helper start and finish time. In game 20, the description attributes the leak to gradual porosity. Section 7.1.10 limits indemnity to the leaking pipe sections and specified investigation costs. All three experimental readers assigned zero validity to the drying and electricity lines. The conditional electricity prices still exist because the issuer and reviewer use them differently. [Game 1 audit](raw6/gpt-H-failure-patterns.md) · [Game 18 policy](../past-cases/case_018/policy.txt) · [Game 20 archive at the reviewed revision](https://github.com/MattisKra/START/tree/6af8d68/past-cases/case_020)

**Price plausibility.** In game 9 all eight speaker medians were above the supported upper bound. In game 15 all eight were below the supported lower bound. In game 15 one reader's rationale explicitly cited game 9's lower price as its reference. Agreement measures consistency among readers, which can inherit the same bad comparison. [Saved responses](../outputs/model_outputs.json) · [Policy-family review](05-adaptive-strategy-review.md)

**Decision rule.** We never see an opponent's current offer before submitting. We set one acceptance limit per line. The ensemble's positive limit and issuer charge default to different multiples of the same median. The reviewer gate can be zero while the issuer still charges for a line it considers excluded. For example, at 0.90×, the revised game 20 reader's conditional €832.42 gross electricity estimate would yield a €749.18 charge and a €0 acceptance limit. This is a hypothetical action. Its profitability depends on opponents, not just the policy. [Ensemble](../claimbot/ensemble.py) · [Official settlement rules](../materials/GAME_DESCRIPTION.md)

## Experiments on released cases

One medium-effort `gpt-6.2-sol` call per arm per case, with the same case documents and photo. Original uses the main estimator prompt at `ed0dee4`. Revised uses the shared rate and scope instructions and the corrected replacement-basis guidance. Selective adds optional native web lookup. No arm received historical price references or opponent results. This isolates the revised reader package and, between the two revised arms, web availability. One sample per arm leaves model variability unresolved. These runs never submitted to the game.

| Game | Original / revised / selective call time | Revised reviewer saving vs original | Selective reviewer saving vs original |
|---|---|---:|---:|
| 18, seven positions | 21.95 / 24.49 / 33.17 s | −€1,760.23 | −€2,153.70 |
| 20, six positions | 19.01 / 21.92 / 30.26 s | +€200.38 | €0.00 |
| 21, 22 positions | 49.33 s / API timeout / API timeout | Unscored | Unscored |

Reviewer savings use the same 0.55× factor, coverage gate, positions and historical opponents. The data identifies the reviewer differences in those two games. Issuer bounds at 0.90× remain much wider. In game 18 the selective arm's issuer change was +€1,742 to +€6,665, so its total net change still admits both signs after the €2,154 reviewer loss. Game 20 does not identify an issuer winner. Game 21's missing answers count against availability and carry no counterfactual payoff claim. Calls are reader latencies, excluding case preparation, other ensemble members and submissions. [Replay on complete public fields](bench/rate_check_replay.py)

**Game 18 labour.** The full field places the fair threshold from €965.65 inclusive to €1,100 exclusive, gross for the entire line. Original estimated €1,576.75, revised €1,172.15, and selective €718.76. The selective reader found €74.75 net per technician hour and €58.95 per helper/trainee hour on a Munich contractor's tariff effective 12 January 2026. I verified both entries in the contractor's PDF. Technician and helper hours remained assumptions. Its central allocation was 6.5 and 2 hours. At a fixed 0.55×, its €395.32 reviewer limit cost €1,895.89 more on labour alone than the original €867.21 limit. A separately tested attendance assumption of 12 technician hours and four helper hours produced a much higher price. The rate evidence was independently checkable. The case did not establish a single payable-hours allocation. [Contractor tariff](https://www.moenner.de/uploads/documents/preisliste.pdf) · [Incident description](../past-cases/case_018/description.txt)

**Case checks to carry forward.** For equipment and electricity, price a day of hire or a kWh only after checking whether the policy includes the expense in another line. For travel and diagnostics, check whether two printed fees refer to one contractor attendance. For disposal, reconcile loads, materials, and whose property was affected. For replacement goods, check valuation basis and explicit prices first. Game 21 supplies a current €440 net price for the same pine table and specifies new-for-old cover. That case also incurred €4,943.60 in excess penalties for rejecting fair charges across the invoice. [Archived case](https://github.com/MattisKra/START/tree/6af8d68/past-cases/case_021) · [Coverage and rate instructions](../claimbot/rate_evidence.py)

## Fable running directly in Claude Code

The team reports using this approach in recent live rounds. I found no local receipt that attributes a specific later live payload to a direct Claude Code session. The tracked ensemble file stops at game 15. The local Fable Python runner's saved game 4 example is a dry run. A Claude Code agent that chooses its own actions is a distinct implementation from the Fable Python reader and rule engine.

I gave two fresh Claude Fable 5.2 sessions separate anonymous case directories. Each contained the original documents and photo, public rules and an offline receipt recorder. The sessions were instructed to avoid repository history, previous results and other sessions. The clock started on opening the package, after agent startup and document preparation. Each selected its own actions. Elapsed times exclude live key retrieval and network submission.

| Game | Recorded local submissions | Direct Fable net against the archived field | Team's actual historical net | Direct Fable net change vs original full-context GPT reader at fixed 0.90× / 0.55× |
|---|---|---:|---:|---:|
| 18 | All seven positions at 7.13 s and 15.53 s | −€6,806 to −€4,541 | −€8,599 | −€6,528 to −€333 |
| 21 | All 22 positions at 18.50 s | −€127 to +€10,841 | −€2,697 | −€22,630 to +€4,754 |

Direct Fable beat the historical team net in both replays. It lost to the original reader on game 18. The game 21 comparison with the original reader is unresolved. Its reviewer cost was €3,476 higher in game 18 and €3,092–€6,790 higher in game 21 against that reader. These are fixed-field bounds over hidden actions. The direct agent and original reader differ in model, tool use, input acquisition and action selection. The trial cannot assign the difference to centralizing context. Local rehearsal receipts are stored under `runs/bench/rate-check-game{18,21}/`. [Scoring](bench/rate_check_replay.py)

Both Fable sessions reported reading the incident and extracted invoice. Neither opened the photo or original invoice PDF. On game 21 the agent inspected policy search matches at headline level and skipped market research. It correctly used the explicit €440 net replacement price, charging €523.60 gross. It also charged €900 for 14 technician hours and set a €1,000 limit. The historical field puts the fair threshold in [€622.35, €679.74). On game 18 it picked the same €1,150 labour charge as the historical team and a €1,400 limit.

The ordinary Python ensemble passes the policy, incident, extracted invoice and available photos to every standard reader. It combines numeric estimates without a final deliberation over the underlying rationales. A direct agent can revisit the evidence and revise a complete answer. Access to all files does not guarantee inspection of each file or correct allocation of payable hours. To isolate the architecture, run the same Fable model on the same fresh case with the same evidence, tools and release clock, and save both pre-deadline payloads. Comparing its direct prices with prices computed from its own recorded valuation would additionally isolate the pricing rule. For the team's actual Claude Code runs, the most useful missing link is the local session ID joined to game ID, submitted payload and server acknowledgement.

## What changed, and what would justify using it live

The main, Fable and specialist valuation prompts now distinguish role, hours, billing unit, scope and source. Historical references require matching work, units, scope and valuation basis. A local ensemble or dry round gives one existing OpenAI medium reader the option to search, preserving the original weights and parallel readers. Its output includes the search actions and provider-returned sources. Live selective lookup requires the explicit existing setting `CLAIMS_WEB_MODELS=selective`. An explicit list of web models keeps its previous behavior. The main single-reader path and standalone Fable reader receive the prompt guidance. The multiagent CLI retains its existing explicit Brave lookup option. Changes were tested locally. [Reader](../claimbot/estimator.py) · [Routing](../claimbot/ensemble.py) · [Reference wording](../claimbot/refs.py)

Decide what to adapt per line. Resolve the policy first. If coverage or scope is uncertain, inspect that clause or task allocation. If a material rate remains uncertain and could move the decision, check a comparable source. If a case already specifies the applicable price, use it. Compare the resulting decisions against the same live control on future games, including late and missing candidates. The current evidence supports this diagnostic sequence and keeping automatic live search off.

For a full bottleneck profile, the next missing records are the official release time and local stage times, the exact evidence delivered to each reader, the amount and reason for each ensemble revision, and the first and last server-acknowledged payload and timestamps. The tracked `played_at` and per-call latency cannot recover these. Follow the largest euro difference from the document, through the arithmetic, to the actual receipt. That would distinguish an expensive slow reader from a slow reader that actually corrected the decision. [Current runner](../claimbot/runner.py) · [Receipt format](../materials/API_HANDBOOK.md)

To repeat the checks with this checkout:

```sh
.venv/bin/python research/bench/check_invoice_archive.py 6af8d68 21
.venv/bin/python -m unittest claimbot_multiagent.test_system
.venv/bin/python -I research/bench/test_clause_parser.py
.venv/bin/python research/bench/rate_check_replay.py 18 20 21
```

The payoff replay uses the locally saved reader answers and public completed-game settlements. It reports missing arms explicitly. Raw model outputs remain in the local benchmark folders.
