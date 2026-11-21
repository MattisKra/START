"""Audit G: research/bench/euro_replay.py with the fixes proposed in research/raw5/fable-G-evaluator-audit.md applied (reference only; no data).

Same interface as euro_replay.py (reconstruct / line_value / game_value). Differences, each marked FIX n in the code:
  FIX 1 (soundness)  an accepted amount equal to the proven cap level c_lo is NOT proof of clipping: c_lo is only a lower bound of the cap, and the
                     highest accepted amount of every line equals it by construction. Such a charge is 'inflated' only if somebody rejected it for 0.
                     If nobody rejected it, rejecting it ourselves can cost 1.5 x (it may be fair).
  FIX 2 (soundness)  a charge that everybody rejected for 0 ('hidden') has no known ceiling. If our candidate limit b' is above everything known to
                     have rejected it, the only proven ceiling of what we pay is b' itself (accepted means a <= b', and we pay min(a, c) <= a).
                     The old value 4 x max(U or L, floor, 1) is not a bound.
  FIX 3 (precision)  our OWN top accepted amount: the log says whether it was clipped. If our logged a is above the amount we received, the cap is
                     revealed exactly (c = amount); otherwise our charge is exact. Either way every reviewer that rejected us gets its upper limit.
  FIX 4 (soundness)  a line the candidate policy does not mention still trades with a = b = 0 (API handbook); it is no longer skipped.
  FIX 5 (precision)  optional known cap ceiling c_hi (from FIX 3) tightens accepted payments and the hidden exposure.
  FIX 6 (precision)  another team's possibly clipped charge (a >= x) that WE accepted with our logged limit lies in [x, our_b]: any candidate limit
                     b' >= our_b accepts it too and pays exactly x. With this the replay of our actual submissions is exact in every game.
"""
import collections

INF = float("inf")
FLAGS = dict(fix1=True, fix2=True)      # switches for the audit only: lets g_adversarial.py attribute each violation of the original to one cause


def reconstruct(rows, us, our_b=None, our_a=None):
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[r["line_item_index"]][r["issuer"]].append(r)
    out = {}
    for ln, issuers in by.items():
        acc_amounts = [r["amount"] for rs in issuers.values() for r in rs if r["accepted"] and r["amount"] > 0]
        fair_a = [round(r["amount"] / 1.5, 2) for rs in issuers.values() for r in rs if (not r["accepted"]) and r["amount"] > 0]
        L = max(fair_a, default=0.0)
        c_lo = max([4 * L] + acc_amounts)
        c_hi = INF
        A = {}
        for i, rs in issuers.items():
            pos_rej = [round(r["amount"] / 1.5, 2) for r in rs if not r["accepted"] and r["amount"] > 0]
            acc_pos = [r["amount"] for r in rs if r["accepted"] and r["amount"] > 0]
            zero_rej = any((not r["accepted"]) and r["amount"] == 0 for r in rs)
            if pos_rej:
                A[i] = dict(a=max(pos_rej), status="fair", exact=True, x=max(acc_pos, default=None))
            elif acc_pos:
                x = max(acc_pos)
                A[i] = dict(a=x, x=x, exact=x < c_lo, status=("inflated" if (zero_rej or (x >= c_lo and not FLAGS["fix1"])) else "unknown"))   # FIX 1
            elif zero_rej:
                A[i] = dict(a=None, status="hidden", exact=False, x=None)
            else:
                A[i] = dict(a=0.0, status="zero", exact=True, x=None)
        if our_a and ln in our_a and us in A:
            me = A[us]
            if me["status"] == "hidden":
                A[us] = dict(a=our_a[ln], status="inflated", exact=True, x=None)
            elif not me["exact"]:                                                                              # FIX 3
                if our_a[ln] > me["x"] + 0.005:
                    c_hi = me["x"]                                   # we charged more than we received: the cap is exactly this amount
                    A[us] = dict(a=our_a[ln], status="inflated", exact=True, x=me["x"])
                else:
                    me["exact"] = True
        U = min([v["x"] if v["x"] is not None else v["a"] for v in A.values() if v["status"] == "inflated" and (v["x"] is not None or v["a"] is not None)], default=INF)
        B = {}
        for i, rs in issuers.items():
            for r in rs:
                j = r["reviewer"]
                B.setdefault(j, dict(lo=0.0, hi=INF))
                a = A[i]["a"]
                if a is None or a <= 0:
                    continue
                if r["accepted"]:
                    B[j]["lo"] = max(B[j]["lo"], a)
                elif A[i]["exact"]:
                    B[j]["hi"] = min(B[j]["hi"], a)
        if our_b and ln in our_b:                                                                              # FIX 6
            for i, rs in issuers.items():
                if i != us and not A[i]["exact"] and A[i]["a"] is not None and any(r["reviewer"] == us and r["accepted"] for r in rs):
                    A[i]["a_hi"] = our_b[ln]
        out[ln] = dict(A=A, L=L, U=U, B=B, c_lo=c_lo, c_hi=c_hi, our_b=(our_b or {}).get(ln, 0.0))
    return out


def _acc_pay(x, c_lo, c_hi=INF):
    return (min(x, c_lo), min(x, c_hi))                                                                       # FIX 5


def _rej_pay(x, L, U, status=None):
    if status == "fair":
        return (1.5 * x, 1.5 * x)
    if status == "inflated":
        return (0.0, 0.0)
    if x <= L:
        return (1.5 * x, 1.5 * x)
    if x >= U:
        return (0.0, 0.0)
    return (0.0, 1.5 * x)


def line_parts(line, us, a_c, b_c):
    """(rev_lo, rev_hi, cost_lo, cost_hi, n_pairs, n_identified)"""
    L, U, c_lo, c_hi = line["L"], line["U"], line["c_lo"], line.get("c_hi", INF)
    rev_lo = rev_hi = cost_lo = cost_hi = 0.0
    n = ident = 0
    for j, Bj in line["B"].items():
        if j == us:
            continue
        n += 1
        acc = True if a_c <= Bj["lo"] else (False if a_c >= Bj["hi"] else None)
        pa, pr = _acc_pay(a_c, c_lo, c_hi), _rej_pay(a_c, L, U)
        lo = {True: pa[0], False: pr[0], None: min(pa[0], pr[0])}[acc]
        hi = {True: pa[1], False: pr[1], None: max(pa[1], pr[1])}[acc]
        rev_lo += lo; rev_hi += hi
        ident += int(acc is not None and lo == hi)
    for i, Ai in line["A"].items():
        if i == us:
            continue
        a = Ai["a"]
        n += 1
        if Ai["status"] == "zero" or a == 0:
            ident += 1
            continue
        if a is None:
            floor = max([B["lo"] for jj, B in line["B"].items() if jj != i] + [line.get("our_b", 0.0)])
            if b_c <= floor:
                ident += 1
            else:
                cost_hi += min(b_c, c_hi) if FLAGS["fix2"] else 4 * max(U if U < INF else L, floor, 1.0)        # FIX 2 (+5)
            continue
        x = Ai["x"] if Ai["x"] is not None else a
        if Ai["exact"]:
            if a <= b_c:
                cost_lo += x; cost_hi += x; ident += 1
            else:
                pr = _rej_pay(a, L, U, Ai["status"] if Ai["status"] in ("fair", "inflated") else None)
                cost_lo += pr[0]; cost_hi += pr[1]; ident += int(pr[0] == pr[1])
        else:                                       # a >= x; either a == x, or a > c == x (clipped, then certainly inflated)
            if b_c < x:                             # rejected for sure
                if Ai["status"] == "inflated":
                    ident += 1
                else:                                                                                         # FIX 1
                    pr = _rej_pay(x, L, U)          # applies if a == x; the clipped alternative costs 0
                    cost_hi += pr[1]; ident += int(pr[1] == 0)
            elif b_c >= Ai.get("a_hi", INF):                                                                   # FIX 6
                cost_lo += x; cost_hi += x; ident += 1
            else:
                cost_hi += x
    return rev_lo, rev_hi, cost_lo, cost_hi, n, ident


def line_value(line, us, a_c, b_c):
    rl, rh, cl, ch, n, ident = line_parts(line, us, a_c, b_c)
    return rl - ch, rh - cl, n, ident


def game_value(lines, us, policy):
    lo = hi = 0.0; n = ident = 0
    for ln in lines:                                                                                           # FIX 4
        a, b = policy.get(ln, (0.0, 0.0))
        l, h, k, i = line_value(lines[ln], us, a, b)
        lo += l; hi += h; n += k; ident += i
    return lo, hi, (ident / n if n else float("nan"))
