import json,sys,subprocess,re,collections
tx,ex=sys.argv[1],sys.argv[2]
for g in range(int(sys.argv[3]),int(sys.argv[4])+1):
    d=json.load(open(f"{tx}/{g}.json"))
    txt=subprocess.run(["pdftotext","-layout",f"{ex}/{g:03d}/invoices.pdf","-"],capture_output=True,text=True).stdout
    desc={}
    cur=None
    for line in txt.splitlines():
        m=re.match(r"\s{0,3}(\d+)\s{2,}(\S.*)",line)
        if m: cur=int(m.group(1)); desc[cur]=re.sub(r"\s{2,}"," | ",m.group(2).strip())
        elif cur and line.strip() and line.startswith("    ") and not line.strip().startswith(("Created","INVOICE","Invoice","FROM","ITEMS","POS")) and len(line)-len(line.lstrip())<12: desc[cur]+=" "+line.strip()
    by=collections.defaultdict(list)
    for x in d: by[x["line_item_index"]].append(x)
    print(f"=== game {g}")
    for i in sorted(by):
        fair=[];fraud=[];acc=collections.defaultdict(float);rej0=set();
        for x in by[i]:
            k=x["issuer"]
            if x["accepted"]: acc[k]=x["amount"]
            elif x["amount"]>0: fair.append(x["amount"]/1.5); acc[k]=x["amount"]/1.5
            else: rej0.add(k)
        fairset=set()
        for x in by[i]:
            if not x["accepted"] and x["amount"]>0: fairset.add(x["issuer"])
        fr=[acc[k] for k in rej0 if k in acc and acc[k]>0]
        lo=max(fair) if fair else 0; hi=min(fr) if fr else float("inf")
        a=sorted(round(v) for v in acc.values())
        print(f"{i:3d} t in [{lo:8.2f},{hi:8.2f})  a's={a}  :: {desc.get(i,'?')[:110]}")
