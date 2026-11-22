#!/bin/zsh
# usage: submit.sh GAME_ID 'idx:a:b idx:a:b ...'
G=$1; K=${TEAM_API_KEY:?set TEAM_API_KEY}
body=$(python3 -I -c 'import sys,json
print(json.dumps([{"index":int(i),"charge_price":float(a),"acceptance_limit":float(b)} for i,a,b in (x.split(":") for x in sys.argv[1].split())]))' "$2")
curl -s -m 15 -w "\nHTTP %{http_code}\n" -X PUT -H "X-API-Key: $K" -H "Content-Type: application/json" -d "$body" https://c2f.public.quantco.cloud/api/games/$G/submissions | cut -c1-600; date -u
