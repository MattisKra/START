"""Live performance analysis from the organisers' PUBLIC leaderboard endpoints (stdlib only, no keys).

    python3 -I research/live/lb_analyze.py --team "Kiebler Software Solutions"            # our own settlements only
    python3 -I research/live/lb_analyze.py --team "..." --har ~/Downloads/x.har            # offline test from a browser HAR
    python3 -I research/live/lb_analyze.py --team "..." --others                           # ALSO read other teams' rows (see below)

What it reports (everything is derived from rows the page itself shows):
  * standing: our rank/net vs the field, number of teams with identical negative totals (= probably silent teams),
  * per completed game: net, income/costs, how our CHARGES fared (accepted / rejected-fair pays 1.5x / rejected-inflated pays 0),
    how our REVIEWS fared (accepted / wrongly rejected = penalty / rightly rejected), implied accept-limit bracket,
  * the platform's own counters (`performance`): accepted-right / accepted-wrong / correct rejections / penalties,
  * with --others: a bracket [L, U) for each line's hidden fair value t, and a verdict on our a and b against it.

Row semantics (from GAME_DESCRIPTION.md): amount = what the insurer paid the issuer.
  accepted: a (fair) or min(a,c) (inflated)    rejected & fair: 1.5*a    rejected & inflated: 0
An issuer submits ONE a per line to everyone, so a is readable from any row with amount > 0.

DATA HANDLING (decided by the user): other teams' rows may be READ (in memory, to judge the field and bracket t) but are never
written to disk or to the repo. Only our own rows are cached, under the gitignored runs/. --others is off by default and does
the extra reads (one request per team per game, 1 s apart, same public endpoints the leaderboard UI uses).
"""
import argparse, collections, json, statistics as st, sys, time, urllib.parse, urllib.request
from pathlib import Path

BASE = "https://c2f.public.quantco.cloud/leaderboard/api"
DATA = Path(__file__).resolve().parents[2] / "runs" / "live"   # gitignored; only OUR OWN rows are ever cached here
_last = [0.0]


class Source:
    """Fetch JSON from the live endpoints (rate limited) or from a HAR file."""

    def __init__(self, har=None, pause=1.0):
        self.har, self.pause = {}, pause
        if har:
            for e in json.load(open(har))["log"]["entries"]:
                u = urllib.parse.urlparse(e["request"]["url"])
                txt = e["response"]["content"].get("text")
                if u.path.startswith("/leaderboard/api/") and txt:
                    self.har[(u.path.rsplit("/", 1)[1], tuple(sorted(urllib.parse.parse_qsl(u.query))))] = json.loads(txt)

    def get(self, ep, **q):
        key = (ep, tuple(sorted((k, str(v)) for k, v in q.items())))
        if self.har:
            return self.har.get(key)
        wait = self.pause - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        url = f"{BASE}/{ep}?{urllib.parse.urlencode(q)}"
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "team-analysis/1.0"})
                with urllib.request.urlopen(req, timeout=25) as r:
                    _last[0] = time.monotonic()
                    return json.load(r)
            except Exception as e:  # noqa: BLE001
                print(f"  ! {ep} {q}: {e!r} (try {attempt + 1}/3)", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
        return None


def tx_pages(src, game, team, cache=False):
    """All transaction rows of one team in one game. Cached on disk ONLY when cache=True (use it for our own team only)."""
    safe = "".join(c if c.isalnum() else "_" for c in team)
    f = DATA / f"tx_g{game}_{safe}.json"
    if cache and f.exists() and not src.har:
        return json.loads(f.read_text())
    rows, page = [], 1
    while True:
        d = src.get("transactions", game_id=game, team=team, page=page)
        if not d:
            return None
        rows += d["items"]
        if page >= d.get("total_pages", 1):
            break
        page += 1
    if cache and not src.har:
        DATA.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(rows))
    return rows


def a_hat(amount, accepted):
    """The issuer's a, if this row reveals it."""
    if amount > 0:
        return amount if accepted else amount / 1.5
    return None


def issuer_view(rows, team):
    """Our charges per line: who accepted, who paid the 1.5x penalty, who rejected us as fraud."""
    out = {}
    for ln in sorted({r["line_item_index"] for r in rows}):
        mine = [r for r in rows if r["issuer"] == team and r["line_item_index"] == ln]
        acc = [r for r in mine if r["accepted"]]
        pen = [r for r in mine if not r["accepted"] and r["amount"] > 0]
        fr = [r for r in mine if not r["accepted"] and r["amount"] == 0]
        a_vals = [a_hat(r["amount"], r["accepted"]) for r in mine if r["amount"] > 0]
        a = st.mode(a_vals) if a_vals else None
        verdict = ("fair: t >= a (rejection paid 1.5x)" if pen else
                   "INFLATED: t < a (rejected for 0)" if fr else "unknown (everyone accepted)")
        out[ln] = dict(a=round(a, 2) if a else None, n=len(mine), accepted=len(acc), penalty_paid_to_us=len(pen), rejected_as_fraud=len(fr),
                       income=round(sum(r["amount"] for r in mine), 2), verdict=verdict,
                       silent_reviewers=len([r for r in mine if not r["accepted"] and r["amount"] > 0]))
    return out


def reviewer_view(rows, team):
    out = {}
    for ln in sorted({r["line_item_index"] for r in rows}):
        inc = [r for r in rows if r["reviewer"] == team and r["line_item_index"] == ln]
        pos = [r for r in inc if r["accepted"] and r["amount"] > 0]
        zero = [r for r in inc if r["accepted"] and r["amount"] == 0]
        wrong = [r for r in inc if not r["accepted"] and r["amount"] > 0]  # we rejected a fair charge
        right = [r for r in inc if not r["accepted"] and r["amount"] == 0]  # we rejected a fraudulent one
        acc_a = [r["amount"] for r in pos]
        rej_a = [r["amount"] / 1.5 for r in wrong]
        out[ln] = dict(incoming=len(inc), zero_charges=len(zero), accepted_positive=len(pos), accepted_paid=round(sum(acc_a), 2),
                       wrongly_rejected=len(wrong), penalty_cost=round(sum(r["amount"] for r in wrong), 2),
                       penalty_excess_vs_accepting=round(sum(r["amount"] for r in wrong) / 3, 2), rightly_rejected=len(right),
                       b_lower=round(max(acc_a), 2) if acc_a else None, b_upper=round(min(rej_a), 2) if rej_a else None,
                       charges_seen=sorted(round(x, 2) for x in acc_a + rej_a))
    return out


def t_bounds(all_rows):
    """Bracket the hidden fair value per line from every row we were allowed to read. Returns {line: (L, U, detail)}."""
    res = {}
    for ln in sorted({r["line_item_index"] for r in all_rows}):
        by_issuer = collections.defaultdict(list)
        for r in {(r["issuer"], r["reviewer"], r["line_item_index"]): r for r in all_rows}.values():
            if r["line_item_index"] == ln:
                by_issuer[r["issuer"]].append(r)
        fair, infl = {}, {}
        for iss, rs in by_issuer.items():
            av = [a_hat(r["amount"], r["accepted"]) for r in rs if r["amount"] > 0]
            if not av:
                continue
            a = st.mode(av)
            if any(not r["accepted"] and r["amount"] > 0 for r in rs):
                fair[iss] = a
            elif any(not r["accepted"] and r["amount"] == 0 for r in rs):
                infl[iss] = a
        lo = max(fair.values(), default=0.0)
        hi = min(infl.values(), default=float("inf"))
        res[ln] = (lo, hi, dict(fair=fair, inflated=infl))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", required=True); ap.add_argument("--har"); ap.add_argument("--others", action="store_true")
    ap.add_argument("--games", default="", help="comma list of game ids (default: all completed)")
    ap.add_argument("--no-log", action="store_true")
    a = ap.parse_args()
    src = Source(a.har)

    g = src.get("games", completed_only="true", page_size=1000)
    done = sorted(x["id"] for x in (g or {}).get("items", []) if x["status"] == "completed")
    if a.games:
        done = [int(x) for x in a.games.split(",")]
    print(f"completed games: {done[-10:]}{' ...' if len(done) > 10 else ''}  (total {len(done)})")

    # ---- standing (matrix: per-team per-game net)
    m = src.get("matrix", page=1, game_limit=20)
    if m:
        tot = {t["team_name"]: t["total"] for t in m["items"]}
        order = sorted(tot, key=lambda t: -tot[t])
        silent = collections.Counter(round(v, 2) for v in tot.values() if v < 0)
        silent_n = max([n for v, n in silent.items() if n >= 2], default=0)
        print(f"\nSTANDING over games {m['game_ids']} (zero-sum check: sum = {sum(tot.values()):+.2f})")
        for i, t in enumerate(order, 1):
            print(f"  {i:2d}. {t:32s} {tot[t]:10.2f} {'<-- us' if t == a.team else ''}")
        if silent_n:
            print(f"  {silent_n} teams share an identical negative total: probably silent (a = b = 0) teams")
        if a.team in tot:
            others = [v for t, v in tot.items() if t != a.team]
            print(f"  our rank {order.index(a.team) + 1}/{len(order)}; vs median team {st.median(tot.values()):+.2f}; gap to leader {tot[a.team] - tot[order[0]]:+.2f}")
        else:
            print(f"  !! team '{a.team}' not in the matrix; names: {sorted(tot)}")

    perf = src.get("performance", team=a.team)
    if perf:
        print("\nPLATFORM COUNTERS for us (cumulative):")
        print(f"  net {perf['net']:.2f} = income {perf['income']:.2f} - costs {perf['costs']:.2f}")
        print(f"  charges issued {perf['issued_count']}, accepted {perf['issued_accepted']} ({perf['issued_accepted'] / max(perf['issued_count'], 1):.0%})")
        rc = perf["reviewed_count"]
        print(f"  reviews {rc}: accepted-right {perf['reviewed_accepted_right']}, accepted-WRONG {perf['reviewed_accepted_wrong']}, "
              f"correct rejections {perf['reviewed_correct_rejections']}, penalties (rejected fair) {perf['reviewed_penalties']}")

    log = []
    for gid in done:
        rows = tx_pages(src, gid, a.team, cache=True)
        if rows is None:
            print(f"\n[game {gid}] no data"); continue
        iv, rv = issuer_view(rows, a.team), reviewer_view(rows, a.team)
        income = sum(r["amount"] for r in rows if r["issuer"] == a.team)
        cost = sum(r["amount"] for r in rows if r["reviewer"] == a.team)
        print(f"\n=== game {gid}: net {income - cost:+.2f} (income {income:.2f}, costs {cost:.2f}) ===")
        bounds = None
        if a.others:
            teams = sorted({r["issuer"] for r in rows} | {r["reviewer"] for r in rows} - {a.team})
            allr = list(rows)
            for t in teams:
                if t != a.team:
                    rr = tx_pages(src, gid, t)
                    allr += rr or []
            bounds = t_bounds(allr)
        for ln in iv:
            i, r = iv[ln], rv[ln]
            print(f" line {ln}")
            print(f"   our charge a = {i['a']}  accepted by {i['accepted']}/{i['n']}; penalty-paid {i['penalty_paid_to_us']}; rejected-as-fraud {i['rejected_as_fraud']}; income {i['income']}  -> {i['verdict']}")
            print(f"   our reviews: {r['incoming']} incoming ({r['zero_charges']} zero), accepted-positive {r['accepted_positive']} (paid {r['accepted_paid']}), "
                  f"wrongly rejected {r['wrongly_rejected']} (penalty excess {r['penalty_excess_vs_accepting']}), rightly rejected {r['rightly_rejected']}; "
                  f"b in [{r['b_lower']}, {r['b_upper']})  charges seen {r['charges_seen']}")
            if bounds:
                lo, hi, det = bounds[ln]
                print(f"   t bracket from all rows read: [{lo:.2f}, {hi if hi != float('inf') else 'inf'})   fair charges {({k: round(v, 2) for k, v in det['fair'].items()})}   inflated {({k: round(v, 2) for k, v in det['inflated'].items()})}")
                if i["a"] is not None:
                    print(f"   our a vs t: {'ABOVE t (inflated)' if i['a'] >= hi else 'at/below lower bound (fair)' if i['a'] <= lo else 'inside bracket (unclear)'}; ratio a/L = {i['a'] / lo:.2f}" if lo > 0 else f"   our a vs t: {'ABOVE t (inflated)' if i['a'] >= hi else 'unclear'}")
                lost = [c for c in r["charges_seen"]]
            log.append(dict(game=gid, line=ln, issuer=i, reviewer=r, t_lo=bounds[ln][0] if bounds else None, t_hi=(bounds[ln][1] if bounds and bounds[ln][1] != float("inf") else None)))
    if log and not a.no_log and not a.har:
        DATA.mkdir(parents=True, exist_ok=True)
        with open(DATA / "our_rounds.jsonl", "a") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "team": a.team, "lines": log}) + "\n")


if __name__ == "__main__":
    main()
