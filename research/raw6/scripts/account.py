"""Own settlement decomposition and fixed-field candidate bounds."""
from collections import Counter, defaultdict
from math import inf, isfinite
from statistics import median

from inputs import US, replay, shipped

EPS = 1e-7


def add(bounds):
    lo, hi = 0., 0.
    for lower, upper in bounds:
        lo += lower
        hi += upper
    return lo, hi


def status(issuer, L, U):
    a, s = issuer["a"], issuer["status"]
    if s != "unknown" or a is None:
        return s
    if issuer["exact"] and a <= L:
        return "fair"
    return "inflated" if a >= U else s


def audit_line(row):
    ln, tx, played = row["state"], row["tx"], row["play"]
    L, U = ln["L"], ln["U"]
    label = row["label"]
    assert L == label["t_lo"], (row["g"], row["p"], L, label["t_lo"])
    if label["t_hi"] is not None:
        assert U <= label["t_hi"] + EPS
    assert L < U, (row["g"], row["p"], L, U)
    own = {r["reviewer"]: r for r in tx if r["issuer"] == US}
    incoming = {r["issuer"]: r for r in tx if r["reviewer"] == US}
    assert len(own) == len(incoming) == 11
    income = sum(r["amount"] for r in own.values())
    cost = sum(r["amount"] for r in incoming.values())
    penalty = sum(r["amount"]/3 for r in incoming.values() if not r["accepted"])
    accepted = defaultdict(float)
    for issuer, r in incoming.items():
        if r["accepted"] and r["amount"] > 0:
            accepted[status(ln["A"][issuer], L, U)] += r["amount"]
    us_a = ln["A"][US]
    verdict = status(us_a, L, U)
    own_a = played["a"] if played else us_a["a"] if us_a["exact"] else None
    if played:
        assert all(r["amount"] <= own_a + EPS if r["accepted"]
                   else abs(r["amount"]-1.5*own_a) < EPS or r["amount"] == 0 for r in own.values())
        assert all(r["amount"] <= played["b"] + EPS if r["accepted"]
                   else r["amount"] == 0 or r["amount"]/1.5 > played["b"] - EPS for r in incoming.values())
    lb_review, ub_review = penalty + accepted["inflated"], penalty + accepted["inflated"] + accepted["unknown"]
    row.update(income=income, cost=cost, net=income-cost, penalty=penalty, accepted=accepted,
               own_a=own_a, verdict=verdict, review_oracle=(lb_review, ub_review),
               own_rows=own, incoming=incoming)
    at_L = issuer_delta(row, L)
    row["at_L"] = at_L
    is_covered = row["decision"] == "C"
    below = at_L if is_covered and verdict in ("fair", "zero") and own_a < L else (0., 0.)
    inflated = tuple(max(0, x) for x in at_L) if is_covered and verdict in ("inflated", "hidden") else (0., 0.)
    unattributed = tuple(max(0, x) for x in at_L) if is_covered and verdict == "unknown" else (0., 0.)
    row.update(below=below, inflated=inflated, unattributed=unattributed,
               loss=add([below, inflated, unattributed, row["review_oracle"]]))
    if not is_covered:
        # Compare to the actual issuer payment on exclusions. The full optimal issuer may earn more.
        ceiling = 0.
    elif isfinite(U):
        ceiling = max(0., sum(U if B["lo"] >= U else 1.5*U for j, B in ln["B"].items() if j != US) - income)
    else:
        ceiling = inf
    row["fair_oracle"] = (row["loss"][0], ceiling+ub_review)


def issuer_delta(row, a):
    if a is None or a == row["own_a"]:
        return (0., 0.)
    ln = row["state"]
    # A whole positive historical rejection is ruled out for a zero charge.
    if a == 0:
        return (-row["income"], -row["income"])
    a = round(a, 2)
    actual = row["own_a"]
    accept_pay = replay._acc_pay(a, ln["c_lo"], ln["c_hi"])
    reject_pay = replay._rej_pay(a, ln["L"], ln["U"])
    bounds = []
    for reviewer, observed in row["own_rows"].items():
        B = ln["B"][reviewer]
        must_accept = a <= B["lo"] or (actual is not None and a <= actual and observed["accepted"])
        must_reject = a >= B["hi"] or (actual is not None and a >= actual and not observed["accepted"])
        assert not (must_accept and must_reject), (row["g"], row["p"], a)
        rl, rh = (accept_pay if must_accept else reject_pay if must_reject
                  else (min(accept_pay[0], reject_pay[0]), max(accept_pay[1], reject_pay[1])))
        bounds.append((rl - observed["amount"], rh - observed["amount"]))
    return add(bounds)


def reviewer_delta(row, b):
    if b is None:
        return (0., 0.)
    b = round(b, 2)
    ln = row["state"]
    bounds = []
    for issuer, r in row["incoming"].items():
        I = ln["A"][issuer]
        a, paid = I["a"], r["amount"]
        if a == 0:
            continue
        if a is None:
            floor = max([ln["our_b"]] + [B["lo"] for j, B in ln["B"].items() if j != issuer])
            bounds.append((-min(b, ln["c_hi"]) if b > floor else 0., 0.))
            continue
        x = I["x"] if I["x"] is not None else a
        if (I["exact"] and a <= b) or (r["accepted"] and b >= min(I.get("a_hi", inf), ln["B"][US]["hi"])):
            new = (x, x)
        else:
            st = status(I, ln["L"], ln["U"])
            reject = replay._rej_pay(a, ln["L"], ln["U"], st)
            if I["exact"] or b < a:
                new = reject
            else:
                new = (0. if st != "fair" else x, x)
        bounds.append((paid-new[1], paid-new[0]))
    return add(bounds)


def delta(row, a=None, b=None):
    """None denotes a role left unchanged at its actual settled action."""
    return add((issuer_delta(row, a), reviewer_delta(row, b)))


def field_for_line(row):
    ln = row["state"]
    active = row["active"]
    tx = row["tx"]
    stats = []
    for team in active - {US}:
        a = ln["A"][team]
        st = status(a, ln["L"], ln["U"])
        received = [r for r in tx if r["issuer"] == team]
        paid = [r for r in tx if r["reviewer"] == team]
        fair = inflated = fair_rej = infl_acc = 0
        for z in paid:
            ze = status(ln["A"][z["issuer"]], ln["L"], ln["U"])
            if ze == "fair":
                fair += 1
                fair_rej += not z["accepted"]
            if ze in {"inflated", "hidden"}:
                inflated += 1
                infl_acc += z["accepted"]
        stats.append(dict(net=sum(z["amount"] for z in received) - sum(z["amount"] for z in paid),
                          verdict=st, a=a["a"], exact=a["exact"], fair=fair, infl=inflated,
                          fair_rej=fair_rej, infl_acc=infl_acc,
                          free_option=row["decision"] == "X" and sum(z["amount"] for z in received)>0))
    return stats


def field_aggregate(data):
    data = list(data)
    states = Counter(x["verdict"] for r, x in data)
    states["inflated"] += states.pop("hidden", 0)
    ratios = {}
    for s in ("fair", "inflated"):
        vals = [x["a"]/r["state"]["L"] for r, x in data if x["verdict"] == s and
                x["exact"] and x["a"] and r["state"]["L"] > 0]
        ratios[s] = (len(vals), round(median(vals), 3) if vals else None)
    known_upper = [(r, x) for r, x in data if x["verdict"] == "inflated" and
                   x["exact"] and x["a"] and isfinite(r["state"]["U"])]
    return dict(states), ratios, (len(known_upper), round(median(x["a"]/r["state"]["U"]
                for r, x in known_upper), 3) if known_upper else None), [
                sum(x[k] for _, x in data) for k in ("fair_rej", "fair", "infl_acc", "infl", "free_option")]


def initialize(rows):
    games = {}
    for row in rows:
        g = row["g"]
        if g not in games:
            games[g] = {r["issuer"] for r in row["game_tx"] if r["amount"] > 0 or not r["accepted"]}
            games[g].update(r["reviewer"] for r in row["game_tx"] if r["accepted"] and r["amount"] > 0)
        row["active"] = games[g]
        audit_line(row)
        if row["play"]:
            a, b = row["play"]["a"], row["play"]["b"]
            assert max(map(abs, delta(row, b=b))) < EPS, (g, row["p"], delta(row, b=b))
            lo, hi, _, _ = shipped.line_value(row["raw_state"], US, a, b)
            assert lo-EPS <= row["net"] <= hi+EPS
        row["field"] = field_for_line(row)
        row["field_median"] = median(x["net"] for x in row["field"])
        row["below_field"] = row["net"] < row["field_median"] - EPS
