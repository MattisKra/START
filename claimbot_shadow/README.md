# Shadow the next three games

From the checkout with the encrypted case ZIPs, run:

```sh
.venv/bin/python -u -m claimbot_shadow
```

The watcher freezes the next three scheduled game IDs before release and exits after them. Run one instance per experiment. It needs a working team key for the release endpoint, the normal ensemble provider credentials, a ZIP extractor, and a signed-in Claude Code CLI with access to `claude-fable-5-2`. Both arms make real model calls. Only the existing tournament submission server handles live decisions.

Both arms receive the same released case, with past-game references disabled. Direct Fable can read the local source files and write decisions. The original games 24–26 arm has case files only. New runs can search public market sources and fetch supplier pages after their first complete decision. The ensemble uses its configured readers, the standard weighted combination and local selective web routing. The member list depends on provider credentials. The experiment compares these two configurations together. It cannot isolate the benefit of full context alone.

The printed run directory contains a frozen manifest and one folder per game:

- `input.json` records the archive SHA-256, release time, preparation time and invoice positions.
- `python.jsonl` records reader arrivals, weights, estimates, stated evidence, aggregate decisions, exact before/after amounts, and failures.
- `fable.jsonl` records tool requests and results, model-reported usage, and complete decision writes with line-level evidence.
- `result.json` compares the last complete decision from each arm within 60 seconds of official release. A missing receipt is null. `error.json` records a round-level failure.

Times are local observations relative to release. Tool results identify what Fable opened. Its evidence strings report what it says drove each decision. The ensemble log identifies the reader arrival that changed the arithmetic. Neither arm provides access to private model reasoning.

For a specific line, follow its position through successive decision events. The first event establishes the baseline. Later events show each change to the charge and limit in gross euros. Compare the final amounts across arms in `fable_minus_python`. A price difference alone does not establish a payoff.

Once a game settles, run the paired payoff replay from the project root with the game folder printed by the watcher:

```sh
.venv/bin/python research/bench/score_shadow.py runs/shadow/<run>/<game>
```

`score.json` stores per-line bounds and totals for Fable minus Python under the opponents' observed decisions. Positive reviewer savings mean Fable paid less. Within each arm, `successive_revision_eur` compares each complete on-time revision to the preceding decision, holding opponents fixed. Hidden charges and limits can leave either winner possible. Missing on-time decisions are marked unscored. The replay reads public settlements and reconciles each team's total against the standings.

To score all three as settlements arrive, start the scorer once with `--follow runs/shadow/<run>`. It waits up to 15 minutes after each release. A single game can be rescored later if the public standings arrive late.

The watcher saves `decision_reasons.json` locally at the end of a round. The scorer builds it for older runs from their saved traces. Look up a printed position for each revision's two amounts, the amounts it replaced, and the model's stated reason. A null reason means the reader supplied none. For Fable, the write ID links to successful file reads or searches since its preceding decision. This records access. Only the reader's explanation attributes a decision to a source. For Python, the index preserves each arriving reader's quantity, price range, coverage judgment and rationale alongside the resulting combined median and limit, including arrivals that left the amounts unchanged. The raw trace holds the pricing factors and web lookup metadata. New Fable runs request a brief numerical basis for each changed amount. Games 24–26 use the original frozen prompt.


## Replay Fable with the Python pricing rule

New Fable receipts contain an independent gross median conditional on eligibility and a probability that the line is payable. The scorer applies the Python factors and rejection gate recorded for that game. Its `explicit_beliefs` results compare this hybrid with Fable's own actions, then compare it with Python under the same rule.

Older receipts contain actions alone. The scorer keeps the original issuer charge fixed and changes positive reviewer limits to charge × limit factor / charge factor. A separate sensitivity analysis treats the charge itself as the median. Neither proxy recovers an unrecorded estimate. All payoff bounds assume the historical opponents hold their actions fixed.

Fable can read `decision_check.json` after each write for duplicate or missing positions, invalid amounts, missing estimates and evidence. Queries, fetch requests, and check results appear in its local trace. For an already running frozen comparison, start `.venv/bin/python -m claimbot_shadow.companion runs/shadow/<run>` once to add the tool-enabled Fable arm to still-future games. It uses a separate output directory and the existing Python decisions. The scorer verifies matching input digests before comparing the arms.

For each printed position, `explicit_beliefs.lines` records both strategies’ charge and limit, reviewer savings, issuer income change, net change and separate winners for all three measures. Positive differences favour Python’s factors applied to Fable’s estimates. A winner requires the whole interval to be strictly above or below zero. Older decisions get separate line breakdowns under the two price-proxy assumptions.

## Shadow a per-line hybrid reviewer

Run `.venv/bin/python -u -m claimbot_shadow.hybrid_watch --reuse runs/shadow/<active-paired-run>`. With no active paired run, omit `--reuse`. This freezes the next three game IDs, the selector description and a hash of its source before release. It reuses overlapping arms and runs one Python ensemble and one tool-enabled Fable process on each new game. The manifest records each source directory.

The three strategies use the same Fable charge and case. Their limits are Fable's own limit, the Python factor on Fable's estimate, and a choice between those limits. The hybrid starts with the factor limit. It switches a line only when at least two distinct Python model names support Fable's limit. For each supporting model, every effort received so far must identify hourly billing or assembly, pass the Python payability gate, and put the gross median strictly closer to Fable's limit. Two efforts of one model count as one vote. A weak gate on Fable's estimate can therefore be overridden by agreement from other readers.

The observer writes a timestamped local revision when Fable or the arriving readers change the inputs. Before Python readers arrive, a complete Fable belief is enough to apply the factor policy. Each line records both candidate limits, the chosen limit and the reader evidence. Only complete decisions observed within 60 seconds count. The selector reads released inputs and local decisions. Settlement data enters only during scoring.

Run `.venv/bin/python research/bench/score_hybrid.py --follow runs/shadow/<hybrid-run>` once to score all three releases. Each game reports the hybrid's reviewer savings versus always using each limit. Since all three use identical charges, reviewer savings equal the net difference. Zero switches and missing receipts are reported. Games 24 and 25 informed the rule; only games 26–28 form the initial prospective block.

A development replay exercised both directions. In game 24 the selector chose Fable's limits on bicycle apprentice, bicycle mechanic and skilled locksmith hours. Those choices cost €1,118–€1,446 versus always using the factor. In game 25 it chose Fable only on senior installer hours, saving €1,095.89 versus the factor. These two cases motivated the experiment and provide no forward result.

Before game 26, Fable reviewed the selector. Agreement on a median can reflect shared price assumptions; the benefit of changing a limit depends on the fairness of the opponent charges it crosses. The scorer therefore reports paired euro savings on each switch against always using the factor. It also replays the last complete receipt by 54 seconds from release to represent the live runner’s six-second safety margin. The original 60-second shadow result remains the experiment’s primary timing record.

For this exploratory block, fewer than five switched lines by 54 seconds is insufficient to assess repeatability. Positive total lower-bound savings versus the factor, with positive lower bounds in at least two games, would justify a second frozen block. Three games cannot establish a live policy. A next experiment could compare the labour/assembly condition alone with the model votes alone to learn which condition contributes.

## Label-only and vote-only shadows

Start `.venv/bin/python -u -m claimbot_shadow.ablation_watch runs/shadow/<hybrid-run>` before release. It freezes the selectors for remaining games and reads the same timestamped hybrid revisions. Each invoice is independently read after release and its archive digest checked against the hybrid input. All policies keep Fable's issuer charge.

- **Label only** uses Fable’s limit when the printed invoice uses an hourly unit or the word “assembly” and Fable’s payability estimate passes the existing gate. Otherwise it uses the factor limit. It needs no reader votes.
- **Vote only** uses Fable’s limit when two distinct model names support it. Every available effort of each supporting model must pass the payability gate and put the gross median strictly closer to Fable’s limit. This arm ignores the work label.
- The frozen hybrid uses each reader’s work classification and validity. The printed-label rule uses Fable’s validity, so comparisons measure the full policies. They do not isolate a text label independently of its coverage gate.

Run `.venv/bin/python research/bench/score_ablations.py --follow runs/shadow/<hybrid-run>/ablations` to collect per-line and total reviewer savings. The scorer compares each arm against the factor, the single-condition arms head-to-head, and the hybrid against each. Each cutoff uses the same latest decision observed by all arms by that time. Zero differences are ties. Missing receipts are unscored. A zero-straddling savings interval leaves the payoff comparison unresolved.

## Require Fable to consult the policy before deciding

Run `.venv/bin/python -u -m claimbot_shadow.policy_first_watch --reuse-hybrid runs/shadow/<hybrid-run>` to reuse the standard tool-enabled Fable on overlapping releases. Omit the reuse argument to start both arms on the same released case. The watcher freezes three future releases and the gate source hash.

Standard Fable may consult the policy whenever it chooses. The treatment must first complete a successful Read of the case’s policy, then cite a numbered clause and at least six consecutive words from its body on a material invoice line. The recorder checks the quote against both the original clause and the text returned before the write request. A same-turn parallel read, failed read, heading alone, or later read cannot qualify the earlier decision. Failed attempts are logged and Fable receives a correction in `decision_check.json`. This verifies prior access to evidence; whether the clause applies correctly still requires review.

Run `.venv/bin/python research/bench/score_policy_first.py --follow runs/shadow/<policy-first-run>` to score the block. The primary comparison uses the last complete local decisions by 54 seconds. The scorer also compares the first complete decisions and the last by 60 seconds. Each paired result includes issuer, reviewer and net bounds against the same field, line-level changes, control policy access and the treatment’s cited passage. A missing receipt counts against availability and leaves the paired score open. The intervention includes the requirement to cite evidence and its time cost. On games where the control also reads early, both arms have seen policy text.

## Give Fable another verification turn

Run `.venv/bin/python -u -m claimbot_shadow.review_watch` to freeze the next three releases. This shadow opens one policy-first Fable session per case. After the initial turn finishes with a complete decision, the harness can request up to two additional turns in the same session. Each turn checks a different printed position. It selects the largest remaining charge or acceptance limit, breaking ties by printed position. This ranks our own euro amounts. A mistakenly zeroed line can therefore escape review.

Each follow-up requires a successful source read or search before a separate write. Fable records the source-linked reason for keeping or revising the assigned line. A revision may change the charge, limit, conditional gross median or payable probability. The recorder preserves the last complete decision when a review fails or finishes late. New passes start only before 54 seconds from release. The primary comparison uses receipts through 54 seconds and the secondary comparison uses the official 60 seconds.

Run `.venv/bin/python research/bench/score_review_turns.py --follow runs/shadow/<reviews-run>` for settlement replay. Both comparisons use the last initial-turn decision available at the same cutoff as their control. A keep or unfinished review leaves its previously saved amounts in effect. A missing initial decision is unscored. Each local score includes source calls, reasons, per-pass timings, model-reported usage when available, and incremental issuer, reviewer and net payoff bounds. The comparison measures what the extra turns changed within this particular session.

## Separate technician hours from equipment days

Run `.venv/bin/python -u -m claimbot_shadow.time_components_watch` to freeze three future games. Pass `--reuse-policy-first runs/shadow/<policy-first-run>` to share its standard Fable control on matching releases. Each pair uses the same archive, model, public market tools and 60-second window. The treatment adds a prompt to price payable person-hours by role, device-days by equipment type, and other costs separately. It requests gross rates, attendance and scope evidence, and a total conditional on coverage. The additional reporting takes time.

Run `.venv/bin/python research/bench/score_time_components.py --follow runs/shadow/<time-components-run>` to score the latest complete decisions by 54 and 60 seconds. The primary outcome is the whole-invoice fixed-field net difference at 54 seconds. Local results also report issuer income, reviewer savings, a frozen invoice-label subset, per-line beliefs and actions, and arithmetic against the treatment's stated median. Missing or malformed breakdowns count in the payoff comparison whenever the arm delivered valid prices. An empty target subset or an invoice with no equipment exposure gives no evidence about equipment-day pricing. Model-supplied quantities and rates remain assumptions unless independently documented.
