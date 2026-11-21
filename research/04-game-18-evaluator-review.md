# Game 18 evaluator and strategy review

Reviewed revision `4961b12` on 21 November 2026. Kiebler Software Solutions stood seventh of twelve after game 18, at −€11,050.61 and €10,848.74 behind sixth. Tournament rank determines 70% of the grade.

The logged ensemble combines readers' estimates of coverage, justified quantity and gross value. Python converts those estimates into a charge and an acceptance limit for each invoice line. The code defaults to 0.90 times the median for the charge and 0.55 times the median for a sufficiently likely valid line's limit. The decision log ends at game 15, so the live settings for games 16–18 are unverified. [Pricing defaults](../claimbot/config.py) · [Decision log](../outputs/model_outputs.json) · [Official standings](https://c2f.public.quantco.cloud/leaderboard/)

## Findings

| Priority | Finding | Evidence and correction |
| --- | --- | --- |
| P1 | A failed submission can become the recorded decision. | An offline run rejected its only PUT and still logged seven submitted lines. With a falsely recorded limit, replay returned exactly €0 for a known €90 cost. Record the last acknowledged payload and use only verified decisions to tighten bounds. [Runner](../claimbot/runner.py) · [Euro replay](bench/euro_replay.py) |
| P1 | The field downloader can permanently cache an incomplete game. | Removing a counterparty changed a known −€150 net into an exact €0. A baseline computed from the same incomplete rows also passes. Check the expected participants and every directed matchup per invoice position before accepting the cache. [Field downloader](raw4/scripts/fetch_field.py) |
| P1 | The euro report can compare different sets of games. | It skips missing candidate answers but subtracts actual net across every requested game. The saved Fable answers end at game 10 and Luna's at game 15. Require a shared set of games for a ranking and print the game IDs. [Euro report](bench/euro_game_report.py) |
| P1 | The proxy benchmark systematically understates the risk of raising limits. | It discards 391 of 858 incoming rows whose rejected charges were hidden. Accepting every charge scored better than actual in aggregate and worse on zero of 78 lines. Use the euro interval evaluator for limit decisions. [Proxy benchmark](bench/bench.py) · [Multiagent comparison](../claimbot_multiagent/report.py) |
| P1 | The main runner starts its deadline after the watcher obtains the key. | Receiving the key 20 seconds after release gives the runner until second 74 in a 60-second game. Pass the organizer's round start through to the runner. A specific tournament loss attributable to this defect remains unverified. [Watcher](../claimbot/watch.py) · [Runner](../claimbot/runner.py) |
| P2 | The proxy shifts omitted positions and converts uncertainty into exclusion. | Reader positions 1 and 3 were scored against 1 and 2. On 38 unannotated lines the proxy inferred zero fair value from an upper bound alone. Use printed positions and retain the unknown interval. [Scoring](bench/bench.py) |
| P2 | A description total can override a binding policy cap. | The alternative rule engine returned €100 for a €100 cap, then €300 when given a €300 description total on the same line. Apply the binding cap after reconciling the description. [Rule engine](../claimbot_fable/engine.py) |
| P2 | Historical replay can fail to build or reverse a strategy comparison. | Suite preparation failed at game 16 because the submission log stops at 15. Even with a complete log, the scenario places rejecting opponents' limits one cent below our charge. A one-cent reduction can appear to change every rejection into an acceptance. Report missing games and reserve this scenario for baseline reproduction. [Historical suite](replay/history.py) |

Three smaller issues also reproduced. Refreshing two labels yielded four rows. The archive describes a hidden charge rejected by everyone as “nothing charged,” including game 18 line 6. An older downloader placed 1,650 opponent-to-opponent settlement rows from games 1–4 in tracked files, contrary to the current repository storage convention. [Label refresh](bench/build_labels.py) · [Archive formatter](../claimbot/archive.py) · [Historical downloader](prompt_opt/fetch_tx.py)

## What to test next

Game 17's 19 wrongful rejections cost €2,463.88 above the cost of accepting those fair charges. In game 18 we accepted all 11 labour charges and paid €9,891.44 on that line. The complete field establishes €5,148.30 in fair payments and €4,743.14 in inflated payments. Our own €1,150 labour charge was inflated and nine teams rejected it. The two cases show why either direction of a blanket limit change carries risk. [Game 17](../past-cases/case_017/results.json) · [Game 18](../past-cases/case_018/results.json)

Fable proposed testing a limit of 1.25 times the median on lines with a usable historical price reference and at most 0.70 times the median on the rest. Its supporting six-game replay inferred game 16's medians and omitted payment caps. Freeze the rule before new cases arrive, record which lines receive a usable reference, hold charges fixed, and compare reviewer-cost intervals against the existing rule on identical rounds. [Reference experiment](bench/README.md)

## Verification

Static checks covered 121 tracked Python files. The multiagent and replay tests, Fable engine self-test and clause-parser checks passed. With complete fields, 40,000 synthetic line replays contained the known payoff. The euro replay also contained actual net in six checked games (1–4, 6 and 15) without using our logged limits to narrow the intervals. No observable settlement contradicted the tracked decisions through game 15. Hidden charges limit what that last check can prove.
