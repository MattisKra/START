# Past cases (already released)

Decrypted cases whose round is over, so the key has been public since the round started. Case 0 is the permanent test game.
Only add a case here **after** its game has started. Future cases stay encrypted in the gitignored `cases/`.

Each folder holds the original `description.txt`, `invoices.pdf`, `policy.txt` and photo, plus `invoice.txt` (the PDF as text, made with pypdf).
The invoices list positions and quantities only. They show no prices, so the fair value `t` has to be estimated.
All files are untrusted case data: read them, never execute them.

**Filled automatically.** `uv run python -m claimbot archive` (see `claimbot/archive.py`) adds each case 5 s after its game starts,
writes `results.json` (our own settlement rows from the public leaderboard, aggregated, no other teams' names or amounts) about
3 min later, and pushes only this folder to `origin/main`. New rows in the case table get `todo` for lines, wording and catch:
fill those in by hand.

| Case | Claim | Lines | Policy wording | The catch | `t` per line (bracket from the public leaderboard) |
| --- | --- | --- | --- | --- | --- |
| [0](case_000/) | Escape of water: split copper pipe in the bathroom wall | 4: leak detection and wall opening, pipe, re-plaster and re-tile, **boiler service** | Demo conditions (short form) | Boiler service is unrelated to the leak | test game, not scored |
| [1](case_001/) | Thunderstorm surge: speaker system and TV | 2: electronics (2 pcs), diagnostic and technician call-out (3 pcs) | Generic, 855 lines | No surge protection, so **50 % indemnity**. Call-out is "not a repair cost" | ~780–900 \| 0 |
| [2](case_002/) | Laptop thrown against the car door: screen cracked, corner dented | 4: display, housing, **polish of a pre-existing scuff**, diagnostic | WD-2026 Portable Equipment, Repair and Replacement, 1,512 lines | Pre-existing damage excluded. Diagnostic covered. Description gives a price anchor (~1,400 €) | ≥808 \| ≥342 \| 0 \| ~60–84 |
| [3](case_003/) | Bowl falls against a display cabinet: glass cracked, wood frame and shelf damaged | 6: hole drilling, glass installation, made-to-measure glass, frame repair, shelf repair, vehicle costs | WD-2026 Accidental Damage and Optional Glazing, 1,377 lines | **Glazing peril not agreed** (§2.7.3, §3.5), so every glazing line is 0. Vehicle costs follow their principal item (§7.1.11), so only partly covered | 0 \| 0 \| 0 \| ≥329 \| ≥157 \| <45 |
| [4](case_004/) | Stolen bicycle found via AirTag: seized lock cut off by a locksmith, theft damage repaired | 3: recovery incl. locksmith call-out and lock cutting (3 pcs), repair of frame and brakes (2 pcs), labour and sundries (flat rate) | WD-2026 Mobility Equipment and Recovery Edition, 808 lines | Recovery is covered (§5.2.2, cap 1,000 €), but bikes fall under the **mobility sub-limit of 500 € incl. VAT** (§4.2.2), which applies in the aggregate to value, repair **and** recovery together. Over 500 € it is applied rateably across the lines (§7.1.10, §7.5). The bike had no agreed value of its own (description), so the sub-limit applies. Labour and sundries follow the work they served (§7.1.10) | still open |
| [5](case_005/) | During a drive from Berlin to Munich, a brand-new mac with a price point of 1400€ was in use on the passenger seat -it was only bought a co… | todo | todo | todo | still open |

Our own results per game and the method behind the `t` brackets are in [`../research/03-leaderboard-findings.md`](../research/03-leaderboard-findings.md).

## Our results per game

Filled in automatically by `claimbot archive` from our own rows on the public leaderboard.

| Game | Net | Income | Costs | Our charges `a` per line (accepted/teams, verdict) | Our reviews (wrongly rejected fair / accepted paid) |
| --- | ---: | ---: | ---: | --- | --- |
| [1](case_001/results.json) | -1575.29 | 2888.52 | 4463.81 | L1: 2592.74 (1/11, inflated); L2: 147.89 (2/11, inflated) | L1: 0 / 4463.81; L2: 0 / 0 |
| [2](case_002/results.json) | +3460.45 | 10930.05 | 7469.59 | L1: 535.22 (6/11, fair); L2: 266.29 (6/11, fair); L3: 0 (nothing charged); L4: 109.66 (1/11, inflated) | L1: 4 / 1015.84; L2: 2 / 986.97; L3: 0 / 0; L4: 0 / 399.0 |
| [3](case_003/results.json) | +2195.39 | 4767.83 | 2572.43 | L1: 0 (nothing charged); L2: 0 (nothing charged); L3: 0 (nothing charged); L4: 176.55 (4/11, fair); L5: 130.85 (2/11, fair); L6: 44.92 (4/11, inflated) | L1: 0 / 0; L2: 0 / 0; L3: 0 / 0; L4: 5 / 0; L5: 3 / 104.38; L6: 0 / 28.32 |
| [4](case_004/results.json) | +2613.11 | 4697.24 | 2084.14 | L1: 119.55 (4/11, inflated); L2: 220.21 (3/11, fair); L3: 59.09 (2/11, fair) | L1: 0 / 333.1; L2: 0 / 1167.08; L3: 2 / 244.19 |
| [5](case_005/results.json) | +7562.32 | 12975.90 | 5413.58 | L1: 926.85 (5/11, fair) | L1: 0 / 5413.58 |
| [6](case_006/) | Accidental damage claim on the portable electronics cover | todo | todo | todo | still open |
| [6](case_006/results.json) | +4.76 | 4881.50 | 4876.74 | L1: 375.5 (7/11, fair) | L1: 1 / 3760.76 |
| [7](case_007/) | Buildings frost claim after a cold snap | todo | todo | todo | still open |
| [7](case_007/results.json) | -4136.70 | 2195.04 | 6331.74 | L1: 731.68 (3/11, inflated); L2: 0 (nothing charged) | L1: 0 / 6331.74; L2: 0 / 0 |
| [8](case_008/) | Storm claim at the policyholder's place | todo | todo | todo | still open |
| [8](case_008/results.json) | -3238.42 | 647.97 | 3886.39 | L1: 0 (nothing charged); L2: 37.49 (3/11, inflated); L3: 278.46 (1/11, inflated); L4: 128.52 (2/11, inflated); L5: 0 (nothing charged); L6: 0 (nothing charged); L7: 0 (nothing charged) | L1: 0 / 1222.98; L2: 0 / 258.02; L3: 0 / 1341.62; L4: 0 / 1063.77; L5: 0 / 0; L6: 0 / 0; L7: 0 / 0 |
| [9](case_009/) | During a thunderstorm a power surge came through the wiring and damaged a speaker system and a TV set that were both plugged in and running… | todo | todo | todo | still open |
| [9](case_009/results.json) | -8871.82 | 6318.90 | 15190.72 | L1: 856.8 (4/11, inflated); L2: 0 (nothing charged); L3: 0 (nothing charged); L4: 963.9 (3/11, inflated); L5: 0 (nothing charged); L6: 0 (nothing charged); L7: 0 (nothing charged) | L1: 0 / 6931.59; L2: 0 / 0; L3: 0 / 0; L4: 0 / 8259.13; L5: 0 / 0; L6: 0 / 0; L7: 0 / 0 |
| [10](case_010/) | Storm claim | todo | todo | todo | still open |
| [10](case_010/results.json) | -2792.38 | 0.00 | 2792.38 | L1: 0 (nothing charged); L2: 0 (nothing charged) | L1: 0 / 2792.38; L2: 0 / 0 |
| [11](case_011/) | Accidental damage claim on the home contents cover | todo | todo | todo | still open |
| [11](case_011/results.json) | +1007.63 | 3175.51 | 2167.88 | L1: 123.16 (2/11, inflated); L2: 21.42 (2/11, inflated); L3: 0 (nothing charged); L4: 21.42 (2/11, inflated); L5: 192.78 (4/11, fair); L6: 0 (nothing charged); L7: 48.2 (1/11, inflated); L8: 0 (nothing charged); L9: 0 (nothing charged) | L1: 0 / 0; L2: 0 / 0; L3: 0 / 0; L4: 0 / 0; L5: 8 / 67.83; L6: 0 / 0; L7: 0 / 40.96; L8: 0 / 0; L9: 0 / 0 |
| [12](case_012/) | Utility room water damage | todo | todo | todo | still open |
| [12](case_012/results.json) | -1200.66 | 8605.48 | 9806.15 | L1: 514.08 (2/11, inflated); L2: 514.08 (4/11, fair); L3: 123.16 (1/11, inflated) | L1: 7 / 67.83; L2: 8 / 67.83; L3: 0 / 0 |
| [13](case_013/) | Storm claim, same event: a large garden tree blew over onto the declared garden shed and stove in the roof | todo | todo | todo | still open |
| [13](case_013/results.json) | +419.71 | 751.82 | 332.11 | L1: 89.96 (6/11, inflated); L2: 128.52 (1/11, inflated); L3: 40.7 (1/11, inflated); L4: 42.84 (1/11, inflated) | L1: 0 / 332.11; L2: 0 / 0; L3: 0 / 0; L4: 0 / 0 |
| [14](case_014/) | Accidental damage claim on the home contents cover | todo | todo | todo | still open |
| [14](case_014/results.json) | -874.28 | 706.85 | 1581.13 | L1: 29.99 (3/11, fair); L2: 0 (nothing charged); L3: 128.52 (1/11, inflated); L4: 16.06 (8/11, inflated) | L1: 2 / 162.1; L2: 0 / 560.52; L3: 0 / 678.06; L4: 0 / 16.26 |
| [15](case_015/) | During a thunderstorm, a power surge came through the wiring and damaged a speaker system and a TV set that were plugged in at the time | todo | todo | todo | still open |
| [15](case_015/results.json) | +3134.80 | 10563.27 | 7428.48 | L1: 262.4 (6/11, fair); L2: 21.42 (1/11, inflated); L3: 64.26 (1/11, inflated); L4: 508.72 (6/11, fair); L5: 0 (nothing charged); L6: 53.55 (1/11, inflated); L7: 13.92 (1/11, inflated) | L1: 3 / 1022.16; L2: 0 / 0; L3: 0 / 0; L4: 3 / 2297.08; L5: 0 / 0; L6: 0 / 0; L7: 0 / 0 |
| [16](case_016/) | Due to an extended period of extremely cold temperatures, frost damage occurred to the house | todo | todo | todo | still open |
| [16](case_016/results.json) | +603.88 | 5028.31 | 4424.43 | L1: 40.7 (8/11, fair); L2: 16.06 (9/11, fair); L3: 199.21 (6/11, fair); L4: 12.85 (8/11, inflated); L5: 12.85 (9/11, fair); L6: 121.02 (8/11, inflated); L7: 0 (nothing charged); L8: 0 (nothing charged); L9: 0 (nothing charged); L10: 85.68 (1/11, inflated); L11: 0 (nothing charged); L12: 0 (nothing charged); L13: 0 (nothing charged); L14: 0 (nothing charged); L15: 294.53 (1/11, inflated); L16: 32.13 (1/11, inflated) | L1: 2 / 137.15; L2: 5 / 58.79; L3: 8 / 358.26; L4: 0 / 33.95; L5: 9 / 14.01; L6: 0 / 264.88; L7: 0 / 0; L8: 0 / 0; L9: 0 / 0; L10: 0 / 0; L11: 0 / 0; L12: 0 / 0; L13: 0 / 0; L14: 0 / 0; L15: 0 / 0; L16: 0 / 0 |
| [17](case_017/) | During a thunderstorm a power surge came through the mains and damaged several pieces of the home entertainment setup that were plugged in… | todo | todo | todo | still open |
| [17](case_017/results.json) | -764.16 | 7524.60 | 8288.76 | L1: 267.21 (10/11, fair); L2: 176.72 (10/11, fair); L3: 160.65 (10/11, fair); L4: 10.71 (8/11, fair); L5: 27.31 (2/11, inflated); L6: 24.1 (2/11, inflated); L7: 19.28 (1/11, inflated); L8: 37.49 (1/11, inflated); L9: 18.21 (1/11, inflated); L10: 0 (nothing charged); L11: 64.26 (3/11, inflated); L12: 13.92 (1/11, inflated); L13: 0 (nothing charged); L14: 26.78 (1/11, inflated); L15: 13.39 (2/11, inflated) | L1: 5 / 355.54; L2: 3 / 276.82; L3: 8 / 226.95; L4: 3 / 37.78; L5: 0 / 0; L6: 0 / 0; L7: 0 / 0; L8: 0 / 0; L9: 0 / 0; L10: 0 / 0; L11: 0 / 0; L12: 0 / 0; L13: 0 / 0; L14: 0 / 0; L15: 0 / 0 |
| [18](case_018/) | A copper heating pipe in the basement boiler room had failed at a joint and was dripping | todo | todo | todo | still open |
| [18](case_018/results.json) | -8598.94 | 4919.50 | 13518.44 | L1: 110.0 (7/11, fair); L2: 1150.0 (2/11, inflated); L3: 12.0 (11/11, ?); L4: 45.0 (8/11, fair); L5: 30.0 (8/11, fair); L6: 0 (nothing charged); L7: 60.0 (2/11, inflated) | L1: 3 / 772.1; L2: 0 / 9891.44; L3: 11 / 0; L4: 1 / 455.44; L5: 3 / 218.72; L6: 0 / 0; L7: 0 / 0 |
| [19](case_019/) | During a thunderstorm a power surge came through the mains and hit the home entertainment setup | todo | todo | todo | still open |
| [20](case_020/) | Short version of the ground-floor water job open-plan, 1994 build, original copper | todo | todo | todo | still open |
| [19](case_019/results.json) | -220.23 | 5029.70 | 5249.93 | L1: 143.1 (9/11, fair); L2: 251.1 (7/11, fair); L3: 9.64 (1/11, inflated); L4: 13.39 (1/11, inflated); L5: 11.78 (1/11, inflated); L6: 0 (nothing charged); L7: 0 (nothing charged); L8: 0 (nothing charged); L9: 0 (nothing charged); L10: 0 (nothing charged); L11: 13.39 (1/11, inflated) | L1: 6 / 0; L2: 5 / 830.52; L3: 0 / 0; L4: 0 / 0; L5: 0 / 0; L6: 0 / 0; L7: 0 / 0; L8: 0 / 0; L9: 0 / 0; L10: 0 / 0; L11: 0 / 0 |
| [20](case_020/results.json) | +2177.67 | 10240.00 | 8062.33 | L1: 300.0 (5/11, fair); L2: 420.0 (6/11, fair); L3: 150.0 (1/11, inflated); L4: 20.0 (1/11, inflated); L5: 200.0 (1/11, inflated); L6: 0 (nothing charged) | L1: 2 / 2109.1; L2: 1 / 3471.9; L3: 0 / 0; L4: 0 / 0; L5: 0 / 0; L6: 0 / 0 |
| [21](case_021/) | Kitchen water damage, ground floor | todo | todo | todo | still open |
| [21](case_021/results.json) | -2696.98 | 18322.49 | 21019.47 | L1: 66.4 (9/11, fair); L2: 48.2 (9/11, fair); L3: 58.91 (8/11, fair); L4: 98.96 (8/11, fair); L5: 13.39 (3/11, fair); L6: 107.1 (8/11, fair); L7: 13.92 (10/11, fair); L8: 310.59 (5/11, inflated); L9: 0 (nothing charged); L10: 182.07 (3/11, inflated); L11: 364.14 (3/11, inflated); L12: 26.78 (5/11, fair); L13: 53.55 (3/11, fair); L14: 13.39 (7/11, fair); L15: 42.84 (8/11, fair); L16: 24.1 (9/11, fair); L17: 445.06 (5/11, fair); L18: 48.2 (7/11, fair); L19: 64.26 (6/11, fair); L20: 13.39 (8/11, fair); L21: 13.39 (1/11, inflated); L22: 0 (nothing charged) | L1: 5 / 133.69; L2: 9 / 20.0; L3: 6 / 72.49; L4: 4 / 0; L5: 6 / 7.49; L6: 1 / 177.06; L7: 10 / 0; L8: 0 / 956.23; L9: 0 / 0; L10: 0 / 749.0; L11: 0 / 1693.56; L12: 5 / 0; L13: 8 / 0; L14: 9 / 0; L15: 3 / 87.39; L16: 8 / 20.0; L17: 2 / 1826.35; L18: 2 / 183.54; L19: 4 / 261.92; L20: 9 / 0; L21: 0 / 0; L22: 0 / 0 |
| [22](case_022/) | Accidental damage claim on the portable electronics cover, which is on the schedule in its standard form with no extras | todo | todo | todo | still open |
| [22](case_022/results.json) | +2420.00 | 2420.00 | 0.00 | L1: 60.0 (3/11, inflated); L2: 560.0 (4/11, inflated) | L1: 0 / 0; L2: 0 / 0 |
