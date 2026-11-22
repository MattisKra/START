#!/bin/zsh
# waits for the next game to start, then runs go.sh for it
R="/Users/leo/Desktop/[PUBLIC] Road to Start HACK"; K=${TEAM_API_KEY:?set TEAM_API_KEY}
read G S <<< $(curl -s -H "X-API-Key: $K" https://c2f.public.quantco.cloud/api/games/list | python3 -I -c '
import sys,json,datetime as d
now=d.datetime.now(d.timezone.utc)
for g in json.load(sys.stdin):
    t=d.datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
    if (t-now).total_seconds()>5: print(g["id"],int((t-now).total_seconds())); break')
echo "GAME $G in ${S}s"
[[ -z "$G" ]] && exit 1
sleep $((S-2)); "$R/work/scripts/go.sh" $G
