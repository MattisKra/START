"""Audit G, step 2: test the MODEL ASSUMPTIONS of research/bench/euro_replay.py against the real public settlement rows.

    python3 -I research/raw5/scripts/g_invariants.py FIELD_DIR [--us "Team Name"]

FIELD_DIR = scratch folder written by research/raw4/scripts/fetch_field.py (must be OUTSIDE the repo). Prints AGGREGATE COUNTS ONLY: no team names,
no per-team amounts. Contains no data.
"""
import collections, json, sys
from pathlib import Path

d = Path(sys.argv[1]).resolve()
repo = Path(__file__).resolve().parents[3]
assert repo not in d.parents and d != repo, "field cache must live outside the repo"
us = sys.argv[sys.argv.index("--us") + 1] if "--us" in sys.argv else None
games = {int(f.stem[4:]): json.loads(f.read_text()) for f in sorted(d.glob("tx_g*.json"), key=lambda p: int(p.stem[4:]))}

C = collections.Counter()
detail = collections.defaultdict(list)


def cents(x):
    return abs(x * 100 - round(x * 100)) < 1e-6


for g, rows in games.items():
    teams = sorted({r["issuer"] for r in rows} | {r["reviewer"] for r in rows})
    lines = sorted({r["line_item_index"] for r in rows})
    C["games"] += 1; C["lines"] += len(lines); C["rows"] += len(rows)
    # --- completeness: every ordered pair on every line exactly once, nobody reviews itself
    keys = collections.Counter((r["issuer"], r["reviewer"], r["line_item_index"]) for r in rows)
    C["dup_rows"] += sum(v - 1 for v in keys.values())
    C["self_rows"] += sum(1 for r in rows if r["issuer"] == r["reviewer"])
    want = len(teams) * (len(teams) - 1) * len(lines)
    C["missing_pairs"] += want - len(keys)
    if len(teams) != 12:
        detail["team_count"].append((g, len(teams)))
    # --- field types / ranges
    for r in rows:
        C["amount_negative"] += r["amount"] < 0
        C["amount_not_cents"] += not cents(r["amount"])
        C["accepted_not_bool"] += not isinstance(r["accepted"], bool)
    # --- zero-sum is trivially true for a bilateral transfer table; the check that matters is against the organisers' matrix (below)
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[r["line_item_index"]][r["issuer"]].append(r)
    for ln, issuers in by.items():
        acc_all = sorted({r["amount"] for rs in issuers.values() for r in rs if r["accepted"] and r["amount"] > 0})
        fair_all = [r["amount"] / 1.5 for rs in issuers.values() for r in rs if not r["accepted"] and r["amount"] > 0]
        L = max(fair_all, default=0.0)
        infl_x = []            # lowest evidence of an inflated charge
        n_pos = n_all_acc = n_hidden = n_zero = n_fair = n_infl = 0
        clipped_candidates = collections.Counter()
        for i, rs in issuers.items():
            acc_pos = sorted({r["amount"] for r in rs if r["accepted"] and r["amount"] > 0})
            acc_zero = sum(1 for r in rs if r["accepted"] and r["amount"] == 0)
            pos_rej = sorted({r["amount"] for r in rs if not r["accepted"] and r["amount"] > 0})
            zero_rej = sum(1 for r in rs if not r["accepted"] and r["amount"] == 0)
            # I1: one accepted amount per issuer and line
            C["I1_issuer_lines_with_accepts"] += bool(acc_pos); C["I1_viol_two_accepted_amounts"] += len(acc_pos) > 1
            # I2: one penalty amount per issuer and line
            C["I2_issuer_lines_with_penalties"] += bool(pos_rej); C["I2_viol_two_penalty_amounts"] += len(pos_rej) > 1
            # I3: penalty = 1.5 x accepted amount (to the cent) when both exist
            if acc_pos and pos_rej:
                C["I3_both"] += 1
                err = abs(pos_rej[0] - round(1.5 * acc_pos[0], 2))
                C["I3_viol_penalty_not_1.5x_accepted(>1ct)"] += err > 0.011
                C["I3_off_by_1ct"] += 0.001 < err <= 0.011
            # I4: a charge is fair for everybody or inflated for everybody (never 1.5a from one reviewer and 0 from another)
            C["I4_viol_fair_and_inflated_mixed"] += bool(pos_rej) and zero_rej > 0
            # I5: an accepted zero and a positive amount cannot coexist (a = 0 is one value)
            C["I5_viol_zero_accept_with_positive"] += acc_zero > 0 and bool(acc_pos or pos_rej or zero_rej)
            # I6: a = 0 is accepted by everybody (0 <= b)
            if not acc_pos and not pos_rej and not zero_rej:
                n_zero += 1
            # classification counts
            if pos_rej:
                n_fair += 1
            elif acc_pos and zero_rej:
                n_infl += 1; infl_x.append(acc_pos[-1])
            elif acc_pos:
                n_all_acc += 1                      # positive charge that NOBODY rejected: fair/inflated unknowable
                C["allacc_is_line_max_accepted"] += acc_pos[-1] >= max(acc_all)
                C["allacc_ge_4L"] += acc_pos[-1] >= 4 * L
            elif zero_rej:
                n_hidden += 1
            n_pos += bool(acc_pos or pos_rej or zero_rej)
            if acc_pos and not pos_rej:
                clipped_candidates[acc_pos[-1]] += 1
            # I7: penalty amount /1.5 must be a cent value if charges are cent values (tells us whether charges carry sub-cent digits)
            for p in pos_rej:
                C["pen_rows_distinct"] += 1; C["pen_implies_subcent_charge"] += not cents(round(p / 1.5, 2)) or abs(round(round(p / 1.5, 2) * 1.5, 2) - p) > 1e-9
        U = min(infl_x, default=float("inf"))
        C["issuer_lines"] += len(issuers); C["positive_charges"] += n_pos; C["status_zero"] += n_zero; C["status_fair"] += n_fair
        C["status_inflated_seen"] += n_infl; C["status_hidden(rejected by all for 0)"] += n_hidden; C["status_all_accepted(unknown)"] += n_all_acc
        C["lines_with_hidden"] += n_hidden > 0; C["lines_with_L>0"] += L > 0; C["lines_with_U<inf"] += U < float("inf")
        C["lines_L>0_and_U<inf"] += L > 0 and U < float("inf")
        # I8: t-bracket consistency: highest fair charge must be below lowest inflated accepted amount
        C["I8_viol_L>=U"] += L >= U
        # I9: shared cap: no accepted amount of an inflated charge above another issuer's ... (cap = one value): the max accepted amount by 2+
        #     issuers that were never penalised = strong evidence of the cap itself
        top = max(acc_all, default=None)
        if top is not None:
            C["lines_with_accepts"] += 1
            C["lines_top_accepted_shared_by_2+_issuers"] += clipped_candidates[top] >= 2
            C["lines_top_accepted_ge_4L"] += top >= 4 * L and L > 0
            C["lines_top_accepted_gt_4L"] += top > 4 * L + 0.011 and L > 0
            C["lines_some_accepted_amount_gt_4L"] += L > 0 and any(x > 4 * L + 0.011 for x in acc_all)
            if clipped_candidates[top] >= 2 and L > 0:
                detail["cap_over_L"].append(round(top / L, 3))
            if clipped_candidates[top] >= 2 and L == 0:
                detail["cap_when_L0"].append(top)
        # I10: reviewer limits consistent: every accepted charge <= every rejected charge of the same reviewer (b is one number)
        Aval = {}
        for i, rs in issuers.items():
            pr = [r["amount"] / 1.5 for r in rs if not r["accepted"] and r["amount"] > 0]
            ap = [r["amount"] for r in rs if r["accepted"] and r["amount"] > 0]
            zr = any(not r["accepted"] and r["amount"] == 0 for r in rs)
            if pr:
                Aval[i] = (round(max(pr), 2), True)
            elif ap:
                Aval[i] = (max(ap), max(ap) < max([4 * L] + acc_all))      # (value or lower bound, exact?)
            elif zr:
                Aval[i] = (None, False)
            else:
                Aval[i] = (0.0, True)
        lo = collections.defaultdict(float); hi = collections.defaultdict(lambda: float("inf")); hi_any = collections.defaultdict(lambda: float("inf"))
        for i, rs in issuers.items():
            a, exact = Aval[i]
            for r in rs:
                j = r["reviewer"]
                lo[j] += 0.0; hi[j] = hi[j]
                if a is None:
                    continue
                if a == 0:
                    C["zero_charge_rows"] += 1; C["I6_viol_zero_charge_rejected"] += not r["accepted"]
                    continue
                if r["accepted"]:
                    lo[j] = max(lo[j], a)
                else:
                    hi_any[j] = min(hi_any[j], a)       # a rejected charge with accepted amount x has a >= x, so this is only a lower bound of it
                    if exact:
                        hi[j] = min(hi[j], a)
        for j in lo:
            C["reviewer_lines"] += 1
            C["I10_viol_limit_inconsistent(lo>=hi, exact)"] += lo[j] >= hi[j]
            C["I10_ties(lo==hi)"] += lo[j] == hi[j]
            C["reviewer_lines_limit_bracketed_both_sides"] += lo[j] > 0 and hi[j] < float("inf")
            C["reviewer_lines_b_zero_like(lo=0, rejected a positive)"] += lo[j] == 0 and hi[j] < float("inf")
            C["reviewer_lines_accept_everything(hi=inf)"] += hi[j] == float("inf")
        # silent reviewers: reject every positive charge on the line
        C["lines_with_a_reviewer_rejecting_every_positive_charge"] += any(lo[j] == 0 and hi[j] < float("inf") for j in lo)
        C["n_reviewers_rejecting_all_sum"] += sum(1 for j in lo if lo[j] == 0 and hi[j] < float("inf"))

# --- organisers' matrix vs row sums (zero-sum and row semantics): net per team and game recomputed from the rows
m = json.loads((d / "matrix.json").read_text()) if (d / "matrix.json").exists() else None
if m:
    gids = m["game_ids"]; bad = 0; n = 0; tot_abs = 0.0
    sample = m["items"][0]
    key = next((k for k in sample if isinstance(sample[k], (list, dict)) and k != "team_name"), None)
    for t in m["items"]:
        per = t.get(key)
        for idx, g in enumerate(gids):
            if g not in games:
                continue
            v = per[idx] if isinstance(per, list) else per.get(str(g), per.get(g))
            if isinstance(v, dict):
                v = v.get("net", v.get("value"))
            if v is None:
                continue
            mine = sum(r["amount"] for r in games[g] if r["issuer"] == t["team_name"]) - sum(r["amount"] for r in games[g] if r["reviewer"] == t["team_name"])
            n += 1; bad += abs(mine - v) > 0.011; tot_abs = max(tot_abs, abs(mine - v))
    print(f"matrix check: team-game nets recomputed from rows vs the organisers' matrix: {n} cells, {bad} differ by > 1 ct (largest gap {tot_abs:.2f}); matrix field used: {key!r}")
    print(f"matrix zero-sum: sum of all totals = {sum(t['total'] for t in m['items']):+.2f}")

w = max(len(k) for k in C)
for k in sorted(C):
    print(f"{k:<{w}}  {C[k]}")
print("cap evidence (top accepted amount shared by 2+ never-penalised issuers) / L, per line with L > 0:", sorted(detail["cap_over_L"]))
print("same, on lines with L = 0 (absolute amounts):", sorted(detail["cap_when_L0"]))
print("games with a team count other than 12:", detail["team_count"])
