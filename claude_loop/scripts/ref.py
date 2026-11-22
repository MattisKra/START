# builds work/ref.txt: per game, policy family + inferred threshold range per line
import json,sys,subprocess,re,collections,hashlib,os
tx,ex,out=sys.argv[1],sys.argv[2],sys.argv[3]
L=[]
for g in sorted(int(f[:-5]) for f in os.listdir(tx) if f.endswith(".json")):
    d=json.load(open(f"{tx}/{g}.json")); p=f"{ex}/{g:03d}"
    fam=hashlib.md5(open(p+"/policy.txt","rb").read()).hexdigest()[:6]
    txt=subprocess.run(["pdftotext","-layout",p+"/invoices.pdf","-"],capture_output=True,text=True).stdout
    desc={};cur=None
    for line in txt.splitlines():
        m=re.match(r"\s{0,3}(\d+)\s{2,}(\S.*)",line)
        if m: cur=int(m.group(1)); desc[cur]=re.sub(r"\s{2,}"," | ",m.group(2).strip())
        elif cur and line.startswith("    ") and line.strip() and len(line)-len(line.lstrip())<12 and not line.strip().startswith(("Created","INVOICE","Invoice","FROM","ITEMS","POS")): desc[cur]+=" "+line.strip()
    by=collections.defaultdict(list)
    for x in d: by[x["line_item_index"]].append(x)
    L.append(f"=== game {g} fam {fam}")
    for i in sorted(by):
        A={};fair=set();fraud=set()
        for x in by[i]:
            k=x["issuer"]
            if x["accepted"]: A[k]=x["amount"]
            elif x["amount"]>0: A[k]=x["amount"]/1.5; fair.add(k)
            else: fraud.add(k)
        lo=max([A[k] for k in fair]+[0]); fr=[A[k] for k in fraud if A.get(k,0)>0]; hi=min(fr) if fr else None
        nz=sum(1 for v in A.values() if v==0)
        if lo==0: tag=f"ZERO(<{hi:.0f})" if hi else "ZERO"
        else: tag=f"{lo:.0f}-{hi:.0f}" if hi else f">={lo:.0f}"
        L.append(f"g{g} #{i} t={tag} :: {desc.get(i,'?')[:95]}")
open(out,"w").write("\n".join(L)+"\n")
