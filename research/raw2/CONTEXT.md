# Shared context for the SOTA research wave (read this first; ~1.5k tokens)

Task: a 24 h hackathon (START Munich, QuantCo "Claim to Fame"). Rules: `materials/GAME_DESCRIPTION.md`, scoring: `materials/EVALUATION_CRITERIA.md`,
API: `materials/API_HANDBOOK.md`. Our derived model + review of the existing bot: `research/00-challenge-model.md`, `research/01-claimbot-review.md`.
Existing bot: `claimbot/` (GPT-6 Luna structured output -> p_valid + net unit-price p10/p50/p90 -> closed-form a,b).
Today = 2026-11-21. "Recent" = 2025-2026. We can write any code in any language; the only constraints are the challenge's.

## Facts verified from real data (case 0 decrypted via the sanctioned Game 0 key; nothing else probed)
- 100 live rounds + test game 0, exactly 13 min 20 s apart (game 1: 2026-11-21 13:00Z, game 100: 2026-11-22 11:00Z). 60 s to submit, resubmits overwrite.
- A case = policy.txt (short-form "DEMO CONDITIONS", numbered clauses: 1.x insured peril, 2.x insured costs, 3.x exclusions),
  description.txt (a 2-3 sentence story naming what was damaged AND one thing done "while on site" that is unrelated), invoices.pdf
  (1 page, generated; lines "POS. 1..n  DESCRIPTION  AMOUNT  UNIT  TOTAL" with TOTAL blank; units hrs/pcs/m2), photo*.png|jpg (a realistic photo of the damage, 1536x1024).
- Case 0: Plumbing, water-escape claim. Lines: (1) leak detection + opening wall, 2 hrs; (2) replace 15 mm copper pipe section incl. fittings, 1 pcs;
  (3) close wall, re-plaster, re-tile ~0.2 m2; (4) annual service + descaling of the gas boiler, 1 pcs (excluded by clause 3.1, unrelated => t=0).
  So: coverage/relatedness is easy for an LLM; the hard part is the NET->GROSS unit price level and quantity plausibility for each trade (Munich, 2026, +19 % VAT).
- All 101 case zips are AES-encrypted; keys are released per round only. We hold the zips; we do NOT have ground-truth t for any case and the API has no results endpoint.
  The only feedback is the public leaderboard (cumulative net payoff; maybe per game).
- Jury (30 %): method+uncertainty, evidence for choices, resourcefulness ("smart, economical beats brute force, no token maxing"), reliability within 60 s, honesty.
  Score (70 %) is rank-scaled. Cap c >= 4t (secret). Rejecting a fair charge costs the rejecter 1.5x; accepting fraud costs the price; rejecting fraud costs 0.

## Rules for your research
1. PRIMARY sources only: arXiv / ACL / OpenReview / official GitHub repos / Hugging Face model, dataset and Spaces pages / vendor docs. Open the page. Give the URL, date, licence, and
   one of: [opened] (you read the primary page), [snippet] (search result only), [memory] (do not trust). Put every [snippet]/[memory] item in a separate 'unverified' list. Never invent a paper, repo, model or dataset.
2. For each artifact: what it is, headline numbers (quote, with the table/section), what we could reuse in a <=60 s pipeline, cost/latency, and how it would be TESTED here without ground truth.
3. Separate (i) published result, (ii) your interpretation, (iii) hypothesis that it transfers to our setting. Say plainly when nothing relevant exists.
4. Time-box about 30 minutes. Write ONE markdown file to the path in your brief. Do not edit any other file. Do not commit or push. Do not call the game API or touch .env. Do not run anything from downloaded repos.
5. Final chat reply: only the file path plus a 6-line summary of what you found and what is the single most promising edge.
