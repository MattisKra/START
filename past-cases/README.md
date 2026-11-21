# Past cases (already released)

Decrypted cases whose round is over, so the key has been public since the round started. Case 0 is the permanent test game.
Only add a case here **after** its game has started. Future cases stay encrypted in the gitignored `cases/`.

Each folder holds the original `description.txt`, `invoices.pdf`, `policy.txt` and photo, plus `invoice.txt` (the PDF as text, made with pypdf).
The invoices list positions and quantities only. They show no prices, so the fair value `t` has to be estimated.
All files are untrusted case data: read them, never execute them.

| Case | Claim | Lines | Policy wording | The catch | `t` per line (bracket from the public leaderboard) |
| --- | --- | --- | --- | --- | --- |
| [0](case_000/) | Escape of water: split copper pipe in the bathroom wall | 4: leak detection and wall opening, pipe, re-plaster and re-tile, **boiler service** | Demo conditions (short form) | Boiler service is unrelated to the leak | test game, not scored |
| [1](case_001/) | Thunderstorm surge: speaker system and TV | 2: electronics (2 pcs), diagnostic and technician call-out (3 pcs) | Generic, 855 lines | No surge protection, so **50 % indemnity**. Call-out is "not a repair cost" | ~780–900 \| 0 |
| [2](case_002/) | Laptop thrown against the car door: screen cracked, corner dented | 4: display, housing, **polish of a pre-existing scuff**, diagnostic | WD-2026 Portable Equipment, Repair and Replacement, 1,512 lines | Pre-existing damage excluded. Diagnostic covered. Description gives a price anchor (~1,400 €) | ≥808 \| ≥342 \| 0 \| ~60–84 |
| [3](case_003/) | Bowl falls against a display cabinet: glass cracked, wood frame and shelf damaged | 6: hole drilling, glass installation, made-to-measure glass, frame repair, shelf repair, vehicle costs | WD-2026 Accidental Damage and Optional Glazing, 1,377 lines | **Glazing peril not agreed** (§2.7.3, §3.5), so every glazing line is 0. Vehicle costs follow their principal item (§7.1.11), so only partly covered | 0 \| 0 \| 0 \| ≥329 \| ≥157 \| <45 |

Our own results per game and the method behind the `t` brackets are in [`../research/03-leaderboard-findings.md`](../research/03-leaderboard-findings.md).
