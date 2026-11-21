"""Print aggregate and own-only tables used in the failure-pattern report."""
from collections import Counter
from math import isfinite, log
from statistics import median
import sys

import numpy as np

from account import add, delta, field_aggregate, initialize, status
from inputs import load, read_json, ROOT, US, replay, shipped


def fmt(rng):
    return f"{rng[0]:.0f}..{rng[1]:.0f}"


def accounting(rows):
    for g in range(1, 12):
        group = [r for r in rows if r["g"] == g]
        print("G", g, len(group), len(group[0]["active"]),
              *(round(sum(r[k] for r in group), 2) for k in ("income", "cost", "net")),
              *(fmt(add(r[k] for r in group)) for k in ("below", "inflated", "review_oracle", "loss", "fair_oracle")),
              round(sum(r["penalty"] for r in group),2), round(sum(r["accepted"]["inflated"] for r in group),2),
              round(sum(r["accepted"]["unknown"] for r in group),2),
              sum(r["below_field"] for r in group))
        if g <= 9:
            old = add(shipped.line_value(r["raw_state"], US, r["play"]["a"], r["play"]["b"])[:2] for r in group)
            new = add(replay.line_value(r["state"], US, r["play"]["a"], r["play"]["b"])[:2] for r in group)
            print("  RECON", fmt(old), fmt(new))
        archive = read_json(ROOT / f"past-cases/case_{g:03}/results.json")
        assert abs(archive["net"] - sum(r["net"] for r in group)) < .011
    print("TOTAL", *(sum(r[k] for r in rows) for k in ("income", "cost", "net", "penalty")),
          *(fmt(add(r[k] for r in rows)) for k in ("below", "inflated", "review_oracle", "loss", "fair_oracle")),
          sum(r["accepted"]["inflated"] for r in rows), sum(r["accepted"]["unknown"] for r in rows))
    print("TOP", [(r["g"], r["p"], fmt(r["loss"])) for r in sorted(rows, key=lambda r:r["loss"][0], reverse=True)[:12]])
    print("POSITIVE", Counter(r["verdict"] for r in rows if r["decision"]=="C"))
    print("XOPTION", [(r["g"],r["p"],round(r["income"],2)) for r in rows if r["decision"]=="X" and r["income"]])
    print("SOURCE", Counter((r["g"], r["state"]["U"] < (r["label"]["t_hi"] or np.inf)) for r in rows))
    print("PER LINE")
    for r in rows:
        print(f'{r["g"]}.{r["p"]}', *(round(r[k]) for k in ("income", "cost", "net")),
              fmt(r["below"]), fmt(r["inflated"]), round(r["accepted"]["inflated"]),
              round(r["accepted"]["unknown"]), round(r["penalty"]), fmt(r["loss"]),
              round(r["net"]+r["loss"][0]), round(r["net"]+r["loss"][1]))


def field(rows):
    print("FIELD")
    for g in range(1, 12):
        group = [r for r in rows if r["g"] == g and r["decision"] == "C"]
        print(g, field_aggregate((r,x) for r in group for x in r["field"]))
    print("LINE FIELD")
    for r in rows:
        if r["decision"] == "C":
            print(r["g"],r["p"],field_aggregate((r,x) for x in r["field"]))
    for split in ("object", "repair"):
        for test in (False, True):
            for cls in (False, True):
                group = [r for r in rows if r["decision"] == "C" and (r["g"]>8)==test and r[split]==cls]
                print(split, test, cls, len(group), field_aggregate((r,x) for r in group for x in r["field"]))
    weak = [r for r in rows if r["below_field"]]
    win = [(r,x) for r in weak for x in r["field"] if x["net"] > r["field_median"] + 1e-7]
    rest = [(r,x) for r in weak for x in r["field"] if x["net"] <= r["field_median"] + 1e-7]
    for label, g in [("weak upper",win),("weak lower",rest)]:
        print(label, len(weak),len(g),field_aggregate(g))
        print(label,"C",field_aggregate((r,x) for r,x in g if r["decision"]=="C"))
    print("weak own",len(weak),sum(r["decision"]=="X" for r in weak),
          Counter(r["verdict"] for r in weak if r["decision"]=="C"))
    for tag in ("fair","inflated"):
        out = [(r,z) for r in weak for i,z in r["incoming"].items()
               if status(r["state"]["A"][i],r["state"]["L"],r["state"]["U"]) in
               ({tag,"hidden"} if tag=="inflated" else {tag})]
        print("own",tag,len(out),sum(z["accepted"] for _,z in out))
    print("field on exclusions",field_aggregate((r,x) for r in rows if r["decision"]=="X" for x in r["field"]))


def features(r, source):
    pred = r["play"] if source=="live" else r["readers"][0]
    if pred is None:
        return {}
    m = pred["t_median"] if source=="live" else pred["m"]
    mvals = [a["m"] for a in r["readers"] if a and a["m"]>0]
    return {
        "original object": r["object"], "repair split": r["repair"],
        "goods": r["kind"] == "goods", "repair labour": r["kind"] == "repair" and r["flat"],
        "disposal": r["kind"]=="disposal", "ancillary": r["kind"]=="ancillary",
        "vehicle": r["kind"]=="travel", "bundle": r["bundle"], "flat rate": r["flat"],
        "qty >1": r["qty"]>1, "electronics trade": r["trade"]=="Electronics Retail",
        "wood/glazing edition": r["g"] in {3,11}, "portable edition": r["g"] in {2,5,6},
        "named cost head": r["kind"] in {"ancillary","disposal","travel"} or (r["g"],r["p"]) in {(4,1),(7,1)},
        "line reduction": (r["g"],r["p"])==(1,1), "potential cap": r["g"] in {1,4,9} or (r["g"],r["p"]) in {(2,4),(7,1)},
        "optional peril": r["g"] in {3,7,11}, "replacement basis": r["kind"] == "goods",
        "description price": r["anchor"], "description grouping": "combined" in r["desc"].lower() or r["g"] in {8,10},
        "median <100": m<100, "case lines >3": r["nlines"]>3,
        "case share >=40%": r["share_"+source] >= .4,
        "covered share >=40%": r["covered_share_"+source] >= .4,
        "near replacement comparison": r["anchor"] and r["g"]==2,
        "P valid >=.90": pred["q"]>=.90, "reader disagreement >=2x": max(mvals)/min(mvals)>=2 if len(mvals)==3 else None,
        "quantity cut": (median([x["quantity_justified"] for x in r["members"]]) < r["qty"] if r["members"] else None)
                        if source=="live" else pred["justified"]<r["qty"],
        "fraction <1": (median([x.get("payout_fraction",1) for x in r["members"]])<1 if r["members"] else None)
                      if source=="live" else pred["fraction"]<1,
        "wide price band": (pred["sigma"] >= .5 if source=="live" else
                            pred["raw"]["net_unit_price_p90"] >= 4*pred["raw"]["net_unit_price_p10"]),
        "photo": r["photo"], "numeric deductible present": False,
    }


def score(r, m):
    L, U = r["state"]["L"], r["state"]["U"]
    return log(m/U) if m>=U else log(m/L) if 0 < m < L else 0.


def observations(rows, source):
    obs = []
    for r in rows:
        pred = r["play"] if source=="live" else r["readers"][0]
        if r["decision"]!="C" or pred is None:
            continue
        m = pred["t_median"] if source=="live" else pred["m"]
        obs.append((r["g"],r["p"],score(r,m),r["loss"][0],features(r,source)))
    return obs


def contrast(obs, outcome, key):
    groups = [[r[outcome] for r in obs if r[4][key] == yes] for yes in (False, True)]
    return (float(np.mean(groups[1]))-float(np.mean(groups[0]))) if all(groups) else None


def feature_tests(rows, source):
    obs = observations(rows, source)
    print("FEATURES",source,len(obs))
    for key in obs[0][4]:
        valid = [r for r in obs if r[4][key] is not None]
        train = [r for r in valid if r[0]<=8]
        test = [r for r in valid if r[0]>8]
        if not train:
            continue
        groups = {g:[r for r in train if r[0]==g] for g in sorted({r[0] for r in train})}
        if contrast(train,2,key) is None:
            print(key,"constant",len(train),len(test))
            continue
        rng = np.random.default_rng(441)
        boot = [[r for g in sample for r in groups[g]] for sample in rng.choice(list(groups), (2500,len(groups)))]
        print(key, f"{sum(r[4][key] for r in train)}/{len(train)} -> {sum(r[4][key] for r in test)}/{len(test)}", end="")
        for y in (2,3):
            effect = contrast(train,y,key)
            vals = [s for data in boot if (s:=contrast(data,y,key)) is not None]
            lo, hi = np.quantile(vals,[.05,.95])
            pred = {v:np.mean([r[y] for r in train if r[4][key]==v]) for v in (0,1)}
            base = np.mean([r[y] for r in train])
            error = [abs(r[y]-pred[r[4][key]])-abs(r[y]-base) for r in test]
            held = contrast(test,y,key)
            print(f" | {effect:+.2f}[{lo:+.2f},{hi:+.2f}]/{len(vals)} hold {held if held is None else round(held,2)}, MAEd {np.mean(error) if error else np.nan:+.2f}",end="")
        print()
    print("SIGNED",[(r[0],r[1],round(r[2],3),r[4]["repair split"]) for r in obs])
    for split in ("repair split", "original object"):
        for span in ((1,8),(9,9),(9,11)):
            print(split,span,{flag:Counter(np.sign(r[2]) for r in obs if span[0]<=r[0]<=span[1] and r[4][split]==flag) for flag in (False,True)})
    for g in (7,8,9,10):
        print("READ",g,[(r["p"], [None if a is None else (round(a["m"]),a["q"],a["fraction"],a["justified"]) for a in r["readers"]])
                        for r in rows if r["g"]==g and r["decision"]=="C"])


def main():
    rows = load(sys.argv[1])
    initialize(rows)
    accounting(rows)
    field(rows)
    feature_tests(rows,"live")
    feature_tests(rows,"luna")


if __name__ == "__main__":
    main()
