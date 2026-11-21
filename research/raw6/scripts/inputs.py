"""Read the fixed 11-game snapshot. Settlement rows are kept in memory."""
from collections import defaultdict
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "research/bench"), str(ROOT / "research/raw5/scripts")]
import euro_replay as shipped
import g_replay_fixed as replay

US = "Kiebler Software Solutions"
READERS = (
    "openrouter:openai/gpt-6-luna:low:noimage",
    "openrouter:openai/gpt-6.1-terra:medium",
    "openrouter:anthropic/claude-fable-5.2:low",
)
REPAIR = re.compile(r"repair|refinish|labou?r|damage payment", re.I)
OTHER = re.compile(r"leak (detection|location)|call-?out|diagnos|dispos|vehicle|travel|transport|deliver|install|shipping", re.I)
POS = re.compile(r"^\s*(\d+)\s{2,}(.+)$")
UNIT = re.compile(r"\s{2,}(\d+(?:\.\d+)?)\s+(pcs|flat rate)\s*$")


def read_json(path):
    return json.loads(path.read_text())


def invoice(path):
    """Join wrapped POS descriptions, preserving the printed trade, quantity and unit."""
    rows, trade, pos = {}, None, None
    pdf = subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)
    for line in pdf.splitlines():
        if re.match(r"^\s*\d{4}-\d{4}\s{2,}", line):
            trade = re.split(r"\s{2,}", line.strip())[-1]
        match = POS.match(line)
        if match:
            pos, content = int(match[1]), match[2]
            unit = UNIT.search(content)
            assert unit and pos not in rows, (path, line)
            rows[pos] = dict(text=content[:unit.start()].strip(), qty=float(unit[1]),
                             flat=unit[2] == "flat rate", trade=trade)
        elif pos is not None:
            if not line.strip() or line.lstrip().startswith(("INVOICE", "Created on", "ITEMS")):
                pos = None
            else:
                rows[pos]["text"] += " " + line.strip()
    return rows


def scope(g, p):
    """Document interpretation. Hard exclusions are independent of the settlements."""
    excluded = {
        1: {2}, 2: {3}, 3: {1, 2, 3}, 7: {2}, 8: {5, 6, 7},
        9: {2, 3, 5, 6, 7}, 10: {2}, 11: {1, 2, 3, 4, 6, 8, 9},
    }
    return "X" if p in excluded.get(g, set()) else "C"


def kind(text):
    if re.search(r"vehicle costs", text, re.I):
        return "travel"
    if re.search(r"disposal", text, re.I):
        return "disposal"
    if re.search(r"shipp|install|diagnos|drilling|administrative|service order", text, re.I):
        return "ancillary" if not re.search(r"frost-burst", text, re.I) else "bundle"
    if re.search(r"speaker system|^TV set|replacement glass pane", text, re.I):
        return "goods"
    if re.search(r"recover stolen|leak detection|property and liability", text, re.I):
        return "bundle"
    return "repair" if REPAIR.search(text) or "polish" in text.lower() else "other"


def reader_lines(est):
    """Apply the saved reader schema arithmetic without importing live/config code."""
    result = {}
    for line in est["lines"]:
        p = line["index"] + 1
        q = min(line["p_valid"], 1 if line["covered"] and line["related"] else .15)
        fraction = line["payout_fraction"]
        if fraction <= 0:
            fraction, q = 1, min(q, .05)
        qty = min(line["quantity_justified"] or line["quantity_invoiced"], line["quantity_invoiced"])
        price = line["net_unit_price_p50"]
        if price <= 0:
            price = statistics.median(line[f"net_unit_price_p{k}"] for k in (10, 50, 90))
        m = qty * price * (1 + line["vat_rate"]) * fraction
        result[p] = dict(q=q, m=m, fraction=fraction, justified=qty, raw=line)
    for key, value in (("aggregate_limits", "amount_gross"), ("anchors", "total_gross")):
        for item in est.get(key, []):
            covered = [result[i+1] for i in item["line_indices"] if result[i+1]["q"] >= .5]
            total = sum(r["m"] for r in covered)
            if total > 0 and item[value] > 0 and (total > item[value] or item.get("kind") == "total"):
                for row in covered:
                    row["m"] *= item[value] / total
    return result


def load(field_path):
    games = shipped.load_field(field_path)
    matrix = read_json(Path(field_path) / "matrix.json")
    live = read_json(ROOT / "outputs/model_outputs.json")["games"]
    labels = {(x["game"], x["line"]): x for s in (ROOT / "runs/bench/labels.jsonl").read_text().splitlines()
              if s.strip() for x in [json.loads(s)] if 1 <= x["game"] <= 11}
    saved = {}
    for file in sorted((ROOT / "runs/bench/fable_eval").glob("*.json")):
        for answer in read_json(file)["answers"]:
            if answer["reader"] in READERS and answer["est"]:
                saved[(int(answer["case"][-3:]), READERS.index(answer["reader"]))] = reader_lines(answer["est"])
    all_lines = []
    for g in range(1, 12):
        case = ROOT / f"runs/bench/cases/case_{g:03d}"
        rows = invoice(case / "invoices.pdf")
        policy = (case / "policy.txt").read_bytes()
        digest = hashlib.sha256(policy).hexdigest()[:12]
        desc = (case / "description.txt").read_text()
        actual = {s["index"]+1: s for s in live.get(str(g), {}).get("submitted", [])}
        members = live.get(str(g), {}).get("members", [])
        opponent_rows = games[g]
        assert {r["line_item_index"] for r in opponent_rows} == rows.keys()
        assert len(rows)*132 == len(opponent_rows)
        assert len({(r["line_item_index"], r["issuer"], r["reviewer"]) for r in opponent_rows}) == len(opponent_rows)
        assert all(r["issuer"] != r["reviewer"] and type(r["accepted"]) == bool for r in opponent_rows)
        assert all(abs(r["amount"] / (.01 if r["accepted"] else .015) -
                       round(r["amount"] / (.01 if r["accepted"] else .015))) < 1e-6 for r in opponent_rows)
        totals = defaultdict(float)
        for record in opponent_rows:
            totals[record["issuer"]] += record["amount"]
            totals[record["reviewer"]] -= record["amount"]
        matrix_position = matrix["game_ids"].index(g)
        assert len(totals) == len(matrix["items"]) == 12
        assert all(abs(totals[item["team_name"]] - item["cells"][matrix_position]) < .011
                   for item in matrix["items"])
        model_a = {p: s["a"] for p, s in actual.items()}
        model_b = {p: s["b"] for p, s in actual.items()}
        states = replay.reconstruct(opponent_rows, US, model_b, model_a)
        raw_states = shipped.reconstruct(opponent_rows, US, model_b, model_a)
        photo = bool(list(case.glob("photo*")))
        for p, row in sorted(rows.items()):
            played = actual.get(p)
            lit = row["text"]
            with_line = [m["estimate"]["lines"][p-1] for m in members
                         if m.get("estimate") and len(m["estimate"].get("lines", [])) == len(rows)]
            fable = tuple(saved.get((g, r), {}).get(p) for r in range(3))
            assert all(model is None or math.isclose(model["raw"]["quantity_invoiced"], row["qty"]) for model in fable)
            label = labels[(g, p)]
            split = bool(REPAIR.search(lit) and not OTHER.search(lit))
            legacy = split or kind(lit) == "goods"
            anchor = g in {2, 5} and scope(g, p) == "C" and "diagnos" not in lit.lower()
            row.update(g=g, p=p, decision=scope(g, p), play=played, state=states[p], raw_state=raw_states[p],
                       digest=digest, desc=desc, label=label, photo=photo, nlines=len(rows),
                       tx=[r for r in opponent_rows if r["line_item_index"] == p],
                       game_tx=opponent_rows, readers=fable, members=with_line, kind=kind(lit),
                       repair=split, object=legacy, anchor=anchor,
                       bundle=bool(re.search(r"incl\.|including|\band\b|\bsundries\b|liability|damage payment", lit, re.I))
                       and not (g in {3, 11} and p in ({4, 5} if g == 3 else {5, 6})))
            all_lines.append(row)
        for row in [r for r in all_lines if r["g"] == g]:
            for name, source in (("live", lambda r: r["play"]["t_median"] if r["play"] else 0),
                                 ("luna", lambda r: r["readers"][0]["m"] if r["readers"][0] else 0)):
                total = sum(source(r) for r in all_lines if r["g"] == g)
                row[f"share_{name}"] = source(row) / total if total else None
                covered_total = sum(source(r) for r in all_lines if r["g"] == g and r["decision"]=="C")
                row[f"covered_share_{name}"] = source(row) / covered_total if covered_total else None
    return all_lines
