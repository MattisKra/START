import json,urllib.request,urllib.parse,sys,os
from concurrent.futures import ThreadPoolExecutor
B="https://c2f.public.quantco.cloud/leaderboard/api"
teams=["404","alpha","FDN","TRINNERS4WINNERS","Humble Legends","chineseModels","Kiebler Software Solutions","GemischtesHack","Lumenauts","Asgardians","CHOOMS","vietgang"]
out=sys.argv[1]
def get(g,t):
    items=[];page=1
    while True:
        u=f"{B}/transactions?game_id={g}&team={urllib.parse.quote(t)}&page={page}&page_size=1000"
        d=json.load(urllib.request.urlopen(u,timeout=20))
        items+=d["items"]
        if page>=d.get("total_pages",1): break
        page+=1
    return items
def game(g):
    seen={}
    for t in teams:
        for x in get(g,t): seen[(x["issuer"],x["reviewer"],x["line_item_index"])]=x
    json.dump(list(seen.values()),open(f"{out}/{g}.json","w"))
    return g,len(seen)
with ThreadPoolExecutor(3) as ex:
    for r in ex.map(game,range(int(sys.argv[2]),int(sys.argv[3])+1)): print(r)
