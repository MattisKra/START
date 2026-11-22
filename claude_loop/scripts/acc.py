import json,sys,collections
tx=sys.argv[1]
# for each game/item/issuer: a and number of acceptors -> gives others' b distribution
for g in range(int(sys.argv[2]),int(sys.argv[3])+1):
    d=json.load(open(f"{tx}/{g}.json"))
    by=collections.defaultdict(list)
    for x in d: by[(x["line_item_index"],x["issuer"])].append(x)
    res=collections.defaultdict(list)
    for (i,iss),xs in by.items():
        a=None
        for x in xs:
            if x["accepted"]: a=x["amount"]
            elif x["amount"]>0: a=x["amount"]/1.5
        if a is None: continue
        n=sum(x["accepted"] for x in xs); fair=any((not x["accepted"]) and x["amount"]>0 for x in xs)
        fraud=any((not x["accepted"]) and x["amount"]==0 for x in xs)
        res[i].append((round(a),n,"F" if fraud else ("ok" if fair else "?")))
    print("game",g)
    for i in sorted(res): print(" ",i,sorted(res[i]))
