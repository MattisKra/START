"""Candidate changes from pre-submission inputs, scored against own realized net."""
import sys

from account import add, delta, initialize
from inputs import load
from measure import fmt

GRID = (0, .25, .45, .65, .85, 1.0, 1.25)


def source(row, mode):
    if mode == "live":
        s = row["play"]
        return (s["t_median"], s["q"]) if s else (None, None)
    state = row["readers"][0]
    return (state["m"], state["q"]) if state else (None, None)


def bounds(rows, fn):
    return add(delta(r, *fn(r)) for r in rows)


def guarded(row, mode, ka=None, kb=None, leave_repair=False, leave_excluded_a=True):
    m, q = source(row, mode)
    if m is None:
        return None, 0. if row["decision"] == "X" else None
    if q < 2/3:
        return (None if leave_excluded_a else 0.), 0.
    if leave_repair and row["repair"]:
        return None, None
    return (ka*m if ka is not None else None, kb*m if kb is not None else None)


def tune(train, mode, repair):
    return max(GRID, key=lambda k: bounds(train, lambda r: guarded(r, mode, kb=k, leave_repair=repair))[0])


def show(rows, label, fn):
    scores = {g: bounds([r for r in rows if r["g"] == g], fn) for g in range(1, 12)}
    print(label, "all", fmt(add(scores.values())), "train", fmt(add(scores[g] for g in range(1,9))),
          "test", fmt(add(scores[g] for g in range(9,12))), "game", " ".join(fmt(scores[g]) for g in range(1,12)))


def family_rules(rows):
    d = {(r["g"],r["p"]):r for r in rows}
    for g, new, old in [(2,(6,1),(1,2)), (8,(10,1),(1,2,3,4))]:
        prev = [d[(g,p)] for p in old]
        floor = sum(r["state"]["L"] for r in prev)
        upper = sum(r["state"]["U"] for r in prev)
        print("analogue", g, "->", new, "sum evidence", floor, upper)
        for a,b in [(floor,floor), (floor,None), (None,floor), (None,upper)]:
            if b is None or b < float("inf"):
                print("  ", a,b, fmt(delta(d[new], a,b)))
    for g,p in ((1,1),(4,1),(7,1)):
        r=d[g,p]
        a,b = r["play"]["a"], r["play"]["b"]
        print("reduction sensitivity",g,p,fmt(delta(r,a*.5,b*.5)))


def escalation(row, use_fable, relative):
    luna, _, fable = row["readers"]
    if luna is None:
        return guarded(row, "luna", kb=1.)
    lo, hi = (luna["raw"][f"net_unit_price_p{k}"] for k in (10,90))
    pick = fable if use_fable and fable is not None and luna["q"]>=2/3 and hi >= 4*lo else luna
    return (.80*pick["m"] if relative else None, pick["m"] if pick["q"]>=2/3 else 0.)


def caveats_and_loo(rows):
    train = [r for r in rows if r["g"]<=8]
    for leave_repair in (False, True):
        fitted = tune(train, "luna", leave_repair)
        print("GRID tune Luna", leave_repair, "k", fitted,
              "lower", [(k,fmt(bounds(train,lambda r: guarded(r,"luna",kb=k,leave_repair=leave_repair)))) for k in GRID])
        scores = []
        for g in range(1,9):
            k = tune([r for r in train if r["g"]!=g], "luna", leave_repair)
            s = bounds([r for r in train if r["g"]==g], lambda r: guarded(r,"luna",kb=k,leave_repair=leave_repair))
            scores.append(s)
            print("LOO",g,k,fmt(s))
        print("LOO TOTAL",fmt(add(scores)))
        show(rows, f"Luna grid-selected repair exception={leave_repair} k={fitted}",
             lambda r: guarded(r,"luna",kb=fitted,leave_repair=leave_repair))


def verify_cases(rows):
    for r in rows:
        g,p = r["g"],r["p"]
        if g == 1 or (r["decision"]=="C" and g in (4,7,8,9,10,11)):
            saved = [(x["q"], x["fraction"],x["justified"],round(x["m"],1)) for x in r["readers"] if x]
            members = sorted(set((x.get("payout_fraction","missing"),x["quantity_justified"]) for x in r["members"]),
                             key=str)
            print("ARITHMETIC",g,p,saved,members, r["play"]["q"] if r["play"] else None)
    for g in (7,8,9,10,11):
        pot = [r for r in rows if r["g"]==g]
        for reader in range(3):
            eligible = [r for r in pot if r["decision"]=="C" and r["readers"][reader]]
            print("READER CLASS",g,reader,len(eligible),
                  [sum(r["readers"][reader]["m"] >= r["state"]["U"] for r in eligible),
                   sum(r["readers"][reader]["m"] < r["state"]["L"] for r in eligible)])
    for g in (1,2,3,4,5,6,7,8,9,10,11):
        selected = [r for r in rows if r["decision"]=="C" and r["g"]==g]
        print("FAMILY SUMS",g,sum(r["state"]["L"] for r in selected),sum(r["state"]["U"] for r in selected),
              sum(r["own_a"] or 0 for r in selected),sum(r["loss"][0] for r in selected),selected[0]["digest"])


def main():
    rows = load(sys.argv[1])
    initialize(rows)
    for mode in ("live", "luna"):
        for kb in (0.,.25,.45,.65,.85,1.):
            show(rows, f"{mode} b={kb}m", lambda r: guarded(r,mode,kb=kb))
        show(rows, f"{mode} nonrepair b=.45m", lambda r: guarded(r,mode,kb=.45,leave_repair=True))
        show(rows, f"{mode} nonrepair a=.55m b=.45m", lambda r: guarded(r,mode,ka=.55,kb=.45,leave_repair=True))
        show(rows, f"{mode} nonrepair a=.40m b=.25m", lambda r: guarded(r,mode,ka=.40,kb=.25,leave_repair=True))
    show(rows,"reject all",lambda r:(None,0.))
    show(rows,"exclusions only: b=0",lambda r:(None,0. if r["decision"]=="X" else None))
    show(rows,"exclusions only: a=b=0",lambda r:(0.,0.) if r["decision"]=="X" else (None,None))
    for sw in (False,True):
        show(rows,f"price Luna/Fable, escalation={sw}",lambda r: escalation(r,sw,True))
    for g in (9,10):
        for p in [r["p"] for r in rows if r["g"]==g and r["decision"]=="C"]:
            r=next(r for r in rows if (r["g"],r["p"])==(g,p))
            print("RULE LINE",g,p,fmt(delta(r,*guarded(r,"luna",kb=.45))),
                  fmt(delta(r,*guarded(r,"luna",ka=.55,kb=.45,leave_repair=True))))
    family_rules(rows)
    caveats_and_loo(rows)
    verify_cases(rows)


if __name__=="__main__":
    main()
