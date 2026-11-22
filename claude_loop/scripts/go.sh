#!/bin/zsh
# usage: go.sh GAME_ID  -> waits for key, decrypts, prints case
G=$1; N=$(printf "%03d" $G); R="/Users/leo/Desktop/[PUBLIC] Road to Start HACK"; K=${TEAM_API_KEY:?set TEAM_API_KEY}
for i in $(seq 1 400); do
  r=$(curl -s -m 3 -H "X-API-Key: $K" https://c2f.public.quantco.cloud/api/games/$G/key)
  key=$(print -r -- "$r" | python3 -I -c 'import sys,json
try: print(json.load(sys.stdin).get("decryption_key",""))
except Exception: print("")')
  [[ -n "$key" ]] && break
  sleep 1
done
date -u
[[ -z "$key" ]] && { echo "NO KEY: $r"; exit 1; }
mkdir -p "$R/work/ex/$N"; 7zz x -y -p"$key" -o"$R/work/ex/$N" "$R/Cases/case_$N.zip" >/dev/null 2>&1 || echo DECRYPT_FAIL
cd "$R/work/ex"; ls $N
h=$(md5 -q $N/policy.txt); echo "policy md5 $h size $(wc -c <$N/policy.txt); same as:"; for d in 0*; do [[ $d != $N && $(md5 -q $d/policy.txt 2>/dev/null) == $h ]] && echo -n "$d "; done; echo
echo "--- DESCRIPTION"; cat $N/description.txt
echo; echo "--- INVOICE"; pdftotext -layout $N/invoices.pdf - | grep -v '^\s*$'
echo "--- POLICY LAST PART"; L=$(grep -n '^PART ' $N/policy.txt | tail -1 | cut -d: -f1); tail -n +$L $N/policy.txt | grep -q 'LOSS DESC' && tail -n +$L $N/policy.txt | grep -v '^[-=]*$' | head -40
echo "--- POLICY NUMERIC"; grep -n -i -E "EUR|per cent|one half|percent|sub-limit of|hourly|per hour" $N/policy.txt | cut -c1-220 | head -30
date -u
F=$(md5 -q $N/policy.txt | cut -c1-6); echo "--- PAST THRESHOLDS SAME POLICY FAMILY $F"; awk -v f="fam $F" '/^=== game/{p=index($0,f)>0} p' "$R/work/ref.txt"
echo "--- LESSONS"; cat "$R/work/lessons.txt"
