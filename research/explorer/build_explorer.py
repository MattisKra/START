"""Build a self-contained, offline explorer page (one HTML file) from the public settlement data and our own decision log.

    uv run python research/explorer/build_explorer.py FIELD_DIR --us "Team Name" --out ~/claim_explorer/explorer.html

FIELD_DIR is the scratch dir written by research/raw4/scripts/fetch_field.py (tx_g*.json, matrix.json, games.json, performance.json).
It holds OTHER TEAMS' public rows, so both FIELD_DIR and the generated page must live OUTSIDE the repo (checked below); only this
generator and the template are tracked. Our own decisions come from outputs/model_outputs.json (per line: submitted a, b, median, q and
each ensemble member's reading). The page runs offline: no server, no network, data is embedded.
"""
import argparse, importlib.util, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sp = importlib.util.spec_from_file_location("er", ROOT / "research/bench/euro_replay.py")
er = importlib.util.module_from_spec(sp); sp.loader.exec_module(er)

ap = argparse.ArgumentParser()
ap.add_argument("field_dir"); ap.add_argument("--us", required=True); ap.add_argument("--out", required=True)
args = ap.parse_args()
field = Path(args.field_dir).expanduser().resolve(); out = Path(args.out).expanduser().resolve()
for p in (field, out):
    assert ROOT not in (p, *p.parents), f"{p} is inside the repo: other teams' data must stay outside it"
US = args.us

games_meta = {g["id"]: g for g in json.loads((field / "games.json").read_text())["items"]}
matrix = json.loads((field / "matrix.json").read_text())
perf = json.loads((field / "performance.json").read_text())
txs = er.load_field(field)
logs = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]
ids = matrix["game_ids"]
teams = [t["team_name"] for t in matrix["items"]]
net = {t["team_name"]: dict(zip(ids, t["cells"])) for t in matrix["items"]}

DATA = {"us": US, "teams": teams, "game_ids": ids,
        "net": {t: [net[t].get(g) for g in ids] for t in teams},
        "perf": {t: {k: v for k, v in perf[t].items() if k != "team_name"} for t in perf},
        "games": {}}

for g, rows in sorted(txs.items()):
    log = logs.get(str(g)) or {}
    ms = log.get("members") or []
    sub = {s["index"] + 1: s for s in log.get("submitted", [])}
    text, unit, qty = {}, {}, {}
    est_lines = max((m["estimate"]["lines"] for m in ms), key=len, default=[])
    for l in est_lines:
        text[l["index"] + 1] = l["invoice_text"]; unit[l["index"] + 1] = l["unit"]; qty[l["index"] + 1] = l["quantity_invoiced"]
    rec = er.reconstruct(rows, US, our_b={k: v["b"] for k, v in sub.items()}, our_a={k: v["a"] for k, v in sub.items()})
    lines = []
    for ln in sorted(rec):
        r = rec[ln]
        mem = []
        for m in ms:
            pr = next((p for p in m["prices"] if p["index"] + 1 == ln), None)
            el = next((x for x in m["estimate"]["lines"] if x["index"] + 1 == ln), None)
            if pr:
                mem.append({"name": m["member"], "w": m["weight"], "median": pr["t_median"], "q": pr["q"], "a": pr["a"], "b": pr["b"],
                            "why": (el or {}).get("rationale", ""), "qty_ok": (el or {}).get("quantity_justified")})
        pairs = [[x["issuer"], x["reviewer"], 1 if x["accepted"] else 0, x["amount"]] for x in rows if x["line_item_index"] == ln]
        s = sub.get(ln)
        lines.append({
            "ln": ln, "text": text.get(ln, ""), "unit": unit.get(ln, ""), "qty": qty.get(ln),
            "L": r["L"], "U": None if r["U"] == float("inf") else r["U"], "c_lo": r["c_lo"],
            "charges": {i: {"a": v["a"], "status": v["status"], "exact": v["exact"]} for i, v in r["A"].items()},
            "limits": {j: [b["lo"], None if b["hi"] == float("inf") else b["hi"]] for j, b in r["B"].items()},
            "ours": ({"a": s["a"], "b": s["b"], "median": s["t_median"], "q": s["q"], "sigma": s["sigma"]} if s else None),
            "members": mem, "pairs": pairs,
            "received": round(sum(x["amount"] for x in rows if x["line_item_index"] == ln and x["issuer"] == US), 2),
            "paid": round(sum(x["amount"] for x in rows if x["line_item_index"] == ln and x["reviewer"] == US), 2),
        })
    m0 = ms[0]["estimate"] if ms else {}
    DATA["games"][str(g)] = {"id": g, "start": games_meta.get(g, {}).get("start_time"), "played_at": log.get("played_at"),
                             "summary": m0.get("damage_summary", ""), "policy_notes": m0.get("policy_notes", ""),
                             "logged": bool(log), "failures": log.get("failures", []), "timed_out": log.get("timed_out", []), "lines": lines}

tpl = (Path(__file__).parent / "template.html").read_text()
blob = json.dumps(DATA, separators=(",", ":")).replace("</", "<\\/")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(tpl.replace("/*__DATA__*/null", blob))
print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB), {len(DATA['games'])} games, {sum(len(g['lines']) for g in DATA['games'].values())} lines")
