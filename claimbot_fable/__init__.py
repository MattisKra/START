"""Reader + rule engine bot, built from the first-principles review (research/raw3/fable-E-first-principles-review.md, section E).

The model READS the case (validity, justified quantity, unit price, payable fraction, aggregate limits, description anchors);
Python COMPUTES a and b (limits shared rateably, anchors, two multipliers per line type). Three calls per round instead of 18:
a fast text-only call for a first submission, one strong reader, one standby on a second provider.
Separate from `claimbot/` on purpose: it reuses claimbot's decryption, API client and watch helpers and changes nothing there.
DEFAULT IS DRY-RUN: pass --live to submit. Only ONE process may submit at a time (later PUTs overwrite earlier ones).
"""
