"""Official-rules euro replay with honest bounds.  The closest offline stand-in for the real scoring that the public data allows.

Payoff of one ordered pair (issuer charges a, reviewer limit b, hidden fair value t, hidden cap c >= 4t with a positive floor):
    a <= b          -> reviewer pays min(a, c)                       (accepted, fair or inflated)
    a > b, a <= t   -> reviewer pays 1.5 a                           (wrongly rejected fair charge)
    a > b, a > t    -> 0
Our net for a game = sum over lines and opponents of what we receive as issuer minus what we pay as reviewer.

What the public settlement rows identify (per line):
  * an issuer's charge a_i: exactly, from any row with amount > 0 (accepted: a = min(a, c); rejected and fair: a = amount / 1.5); a charge
    rejected for 0 by everybody stays hidden (only: a_i > t and a_i above every limit that rejected it);
  * fair / inflated for every charge that someone rejected (amount 1.5a vs 0), nothing for charges everybody accepted;
  * t: only a bracket [L, U): L = highest fair charge seen, U = lowest inflated charge seen (U = inf if none);
  * each reviewer's limit: only an interval [b_lo, b_hi) from which charges it accepted and rejected.
A candidate policy (a', b') for one of our lines is replayed against that reconstructed field. Every unknown is carried as an interval, so
the result for a game is a range [lo, hi]; 'identified share' reports how many pair outcomes were pinned down.
Cap: c >= 4t >= 4L, so an accepted charge up to 4L is paid in full; above that the payment is only bounded (between 4L and a').

STATUS (after the GPT audit, research/raw5/gpt-G-evaluator-audit.md): the ranges are CONDITIONAL, historical bounds that hold only under the stated
assumptions (complete rows, exact cent-grid amounts, opponents held fixed). They are NOT a 'worst case consistent with the data': the sum of per-pair
endpoints can include states that cannot coexist, and soundness was only tested on synthetic fields. Use the tool to reconcile accounting and to shortlist
candidates, not as the sole live selector. The audit's logic patch A (clipped-amount status, hidden-charge cost <= b, omitted lines at defaults) is applied.
   Other teams' rows are held in memory / a scratch dir OUTSIDE the repo; nothing is written here.
"""
import collections, json, math, sys
from pathlib import Path

INF = float("inf")


def reconstruct(rows, us, our_b=None, our_a=None):
    """rows: dicts issuer, reviewer, line_item_index, accepted, amount (all ordered pairs of one game). Returns {line: Line}.
    our_b / our_a: optional {line: value}, OUR OWN logged actual submission. our_b: a hidden charge was rejected by us too, so it lies above
    it; our_a: our own charge when the rows hide it (it was rejected by everybody)."""
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[r["line_item_index"]][r["issuer"]].append(r)
    out = {}
    for ln, issuers in by.items():
        # a pass over all accepted amounts: the cap is shared, so c >= every accepted amount, and c >= 4 t >= 4 L
        acc_amounts = [r["amount"] for rs in issuers.values() for r in rs if r["accepted"] and r["amount"] > 0]
        fair_a = [round(r["amount"] / 1.5, 2) for rs in issuers.values() for r in rs if (not r["accepted"]) and r["amount"] > 0]
        L = max(fair_a, default=0.0)
        c_lo = max([4 * L] + acc_amounts)
        A = {}
        for i, rs in issuers.items():
            pos_rej = [round(r["amount"] / 1.5, 2) for r in rs if not r["accepted"] and r["amount"] > 0]
            acc_pos = [r["amount"] for r in rs if r["accepted"] and r["amount"] > 0]
            zero_rej = any((not r["accepted"]) and r["amount"] == 0 for r in rs)
            if pos_rej:
                A[i] = dict(a=max(pos_rej), status="fair", exact=True, x=max(acc_pos, default=None))
            elif acc_pos:
                x = max(acc_pos)
                # exact only if x is below the proven cap level (then x = min(a, c) < c forces a = x); a clipped amount means a > c >= 4t: inflated
                A[i] = dict(a=x, x=x, exact=x < c_lo, status=("inflated" if zero_rej else "unknown"))
            elif zero_rej:
                A[i] = dict(a=None, status="hidden", exact=False, x=None)
            else:
                A[i] = dict(a=0.0, status="zero", exact=True, x=None)
        if our_a and ln in our_a and A.get(us, {}).get("status") == "hidden":
            A[us] = dict(a=our_a[ln], status="inflated", exact=True, x=None)      # rejected for 0 by everybody: inflated, value from our log
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
        out[ln] = dict(A=A, L=L, U=U, B=B, c_lo=c_lo, our_b=(our_b or {}).get(ln, 0.0))
    return out


def _acc_pay(x, c_lo):
    """Payment range of an ACCEPTED charge x: min(x, c) with c >= c_lo."""
    return (min(x, c_lo), x)


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


def line_value(line, us, a_c, b_c):
    """Our net range on one line for candidate charge a_c and limit b_c: (lo, hi, n_pairs, n_identified)."""
    L, U, c_lo = line["L"], line["U"], line["c_lo"]
    rev_lo = rev_hi = cost_lo = cost_hi = 0.0
    n = ident = 0
    for j, Bj in line["B"].items():
        if j == us:
            continue
        n += 1
        acc = True if a_c <= Bj["lo"] else (False if a_c >= Bj["hi"] else None)
        pa, pr = _acc_pay(a_c, c_lo), _rej_pay(a_c, L, U)
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
        if a is None:                              # hidden charge: rejected by everybody, so it is above every limit that rejected it
            floor = max([B["lo"] for jj, B in line["B"].items() if jj != i] + [line.get("our_b", 0.0)])
            if b_c <= floor:
                ident += 1                          # still above our limit: rejected, inflated, costs nothing
            else:
                cost_hi += b_c  # acceptance requires a <= b_c, and the payment is at most a
            continue
        x = Ai["x"] if Ai["x"] is not None else a
        if Ai["exact"]:
            if a <= b_c:
                cost_lo += x; cost_hi += x; ident += 1
            else:
                pr = _rej_pay(a, L, U, Ai["status"] if Ai["status"] in ("fair", "inflated") else None)
                cost_lo += pr[0]; cost_hi += pr[1]; ident += int(pr[0] == pr[1])
        else:                                       # amount may be clipped by the cap: a >= x, and a clipped charge is certainly inflated
            if b_c < x:
                pr = _rej_pay(x, L, U, Ai["status"])
                cost_hi += pr[1]                    # only the uncapped a == x branch can be fair
                ident += int(pr[1] == 0)
            else:
                cost_hi += x                        # accepted pays exactly x (same cap); rejected pays 0
    return rev_lo - cost_hi, rev_hi - cost_lo, n, ident


def game_value(lines, us, policy):
    """policy: {line: (a, b)} for our lines. Returns (lo, hi, identified_share)."""
    lo = hi = 0.0; n = ident = 0
    if policy.keys() - lines.keys():
        raise ValueError("policy contains unknown line indices")
    for ln in lines:
        a, b = policy.get(ln, (0.0, 0.0))                    # an omitted line is settled at the defaults a = b = 0
        if not all(math.isfinite(v) and v >= 0 for v in (a, b)):
            raise ValueError("charge and limit must be finite and nonnegative")
        l, h, k, i = line_value(lines[ln], us, a, b)
        lo += l; hi += h; n += k; ident += i
    return lo, hi, (ident / n if n else float("nan"))


def actual_net(rows, us):
    inc = sum(r["amount"] for r in rows if r["issuer"] == us)
    cost = sum(r["amount"] for r in rows if r["reviewer"] == us)
    return inc - cost


def load_field(dir_):
    """Load the scratch dir written by research/raw4/scripts/fetch_field.py (must be OUTSIDE the repo)."""
    d = Path(dir_).resolve()
    repo = Path(__file__).resolve().parents[2]
    assert repo not in d.parents and d != repo, "field cache must live outside the repo"
    games = {}
    for f in sorted(d.glob("tx_g*.json"), key=lambda p: int(p.stem[4:])):
        games[int(f.stem[4:])] = json.loads(f.read_text())
    return games
