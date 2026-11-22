import json,sys,collections
tx,g,spec=sys.argv[1],sys.argv[2],sys.argv[3]
U="Kiebler Software Solutions"
mine={int(i):(float(a),float(b)) for i,a,b in (x.split(":") for x in spec.split())}
d=[x for x in json.load(open(f"{tx}/{g}.json"))]
act_got=sum(x["amount"] for x in d if x["issuer"]==U); act_paid=sum(x["amount"] for x in d if x["reviewer"]==U)
o=[x for x in d if U not in (x["issuer"],x["reviewer"])]
teams=sorted({x["issuer"] for x in o})
got_lo=got_hi=paid=0; unk=0; rows=[]
for i in sorted(mine):
    a,b=mine[i]; it=[x for x in o if x["line_item_index"]==i]
    # issuer a + status
    A={};st={}
    for T in teams:
        xs=[x for x in it if x["issuer"]==T]; av=None
        for x in xs:
            if x["accepted"]: av=x["amount"]
            elif x["amount"]>0: av=x["amount"]/1.5
        fair=any((not x["accepted"]) and x["amount"]>0 for x in xs); fraud=any((not x["accepted"]) and x["amount"]==0 for x in xs)
        A[T]=av; st[T]="fair" if fair else ("fraud" if fraud else "all-acc")
    tlo=max([A[T] for T in teams if st[T]=="fair"]+[0]); fr=[A[T] for T in teams if st[T]=="fraud" and A[T]]; thi=min(fr) if fr else float("inf")
    # my pay as reviewer
    p=0;u=0
    for T in teams:
        if A[T] is None: u+=1; continue
        if A[T]<=b: p+=A[T]
        elif st[T]=="fair" or (st[T]=="all-acc" and A[T]<=tlo): p+=1.5*A[T]
        elif st[T]=="all-acc" and A[T]<thi: p+=1.5*A[T]  # ambiguous: assume fair (pessimistic)
    # my receipts as issuer
    glo=ghi=0
    for R in teams:
        xs=[x for x in it if x["reviewer"]==R]
        blo=max([A[x["issuer"]] for x in xs if x["accepted"] and A[x["issuer"]] is not None]+[0])
        bh=[A[x["issuer"]] for x in xs if not x["accepted"] and A[x["issuer"]] is not None]; bhi=min(bh) if bh else float("inf")
        def pay(fair,acc): return a if acc else (1.5*a if fair else 0)
        outs=[]
        for fair in ([True] if a<=tlo else [False] if a>=thi else [True,False]):
            for acc in ([True] if a<=blo else [False] if a>=bhi else [True,False]):
                outs.append(pay(fair,acc))
        glo+=min(outs);ghi+=max(outs)
    got_lo+=glo;got_hi+=ghi;paid+=p;unk+=u
    rows.append(f"{i:2d} a={a:6.0f} b={b:6.0f} t∈[{tlo:.0f},{thi:.0f}) get {glo:6.0f}..{ghi:6.0f} pay {p:6.0f} unknown-a issuers {u}")
print("\n".join(rows))
print(f"SIM got {got_lo:.0f}..{got_hi:.0f} paid {paid:.0f} (+ up to {unk} unknown inflated charges) net {got_lo-paid:.0f}..{got_hi-paid:.0f}")
print(f"ACTUAL got {act_got:.0f} paid {act_paid:.0f} net {act_got-act_paid:.0f}")
