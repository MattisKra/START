import json,collections,sys
g=sys.argv[2]; u="Kiebler Software Solutions"
d=json.load(open(f"{sys.argv[1]}/{g}.json"))
got=collections.defaultdict(float);paid=collections.defaultdict(float)
for x in d: got[x["issuer"]]+=x["amount"]; paid[x["reviewer"]]+=x["amount"]
for t in sorted(got,key=lambda t:got[t]-paid[t],reverse=True): print(f"{t:28s} got {got[t]:8.0f} paid {paid[t]:8.0f} net {got[t]-paid[t]:8.0f}")
for i in sorted({x["line_item_index"] for x in d}):
    gg=[x for x in d if x["issuer"]==u and x["line_item_index"]==i]; p=[x for x in d if x["reviewer"]==u and x["line_item_index"]==i]
    print(i,"got",round(sum(x["amount"] for x in gg)),"acc",sum(x["accepted"] for x in gg),"| paid",round(sum(x["amount"] for x in p)),"accepted",sorted(round(x["amount"]) for x in p if x["accepted"] and x["amount"]>0),"wrongful(charge a = paid/1.5)",sorted(round(x["amount"]/1.5) for x in p if not x["accepted"] and x["amount"]>0))
