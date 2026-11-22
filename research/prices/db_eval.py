#!/usr/bin/env python3
"""Would the price database have helped in the finished games?

For every invoice line of the past cases: the database's price (pricedb.lookup, no LLM), our bot's own price at the time,
and the bracket of the fair value t from the public leaderboard (runs/bench/labels.jsonl).

Only lines that were owed tell us about prices: t_lo > 0 means at least one charge was confirmed fair, so t >= t_lo.
Lines with t_lo = 0 were mostly not covered (t = 0); a price cannot be judged on them.

err    = signed log distance of a price to the bracket (0 inside). With no upper bound every price >= t_lo counts as inside.
bot    = median of our belief for the line, logged in outputs/model_outputs.json (games 1-15 only; later games were played
         by another build, so only our charge a is known for them).
replay = hindsight in EUR: on every line the database prices and our bot treated as owed (it accepted at least one positive
         charge), replace our numbers by a' = A x database price and b' = B x database price (A, B = the live multipliers)
         and settle them against the same brackets and the same incoming charges. Opponents are held fixed.
         Baseline: games 1-15 the SAME rule on the bot's logged median (so only the price source differs); later games
         what we really charged and paid (the build and its rule are not logged here).

Writes research/prices/db_report.md. Run: python3 -I research/prices/db_eval.py [--from GAME] [--to GAME]
"""
import importlib.machinery
import importlib.util
import json
import math
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


db = _load("pricedb", HERE / "pricedb.py")
# claimbot.memtext imports a sibling module; register the package by path so claimbot/__init__.py (third-party imports) is
# not executed and this script keeps running under python3 -I.
_pkg = importlib.util.module_from_spec(importlib.machinery.ModuleSpec("claimbot", None, is_package=True))
_pkg.__path__ = [str(ROOT / "claimbot")]
sys.modules["claimbot"] = _pkg
mt = importlib.import_module("claimbot.memtext")


def err(p, lo, hi):
    """Signed log distance of a price to the bracket [lo, hi): 0 inside, negative below, positive above."""
    if p is None or p <= 0:
        return None
    if p < lo:
        return math.log(p / lo)
    if hi is not None and p >= hi:
        return math.log(p / hi)
    return 0.0


A_MULT, B_MULT = 0.9, 0.55   # claimbot.config A_MEDIAN_MULT, B_MEDIAN_MULT


def bot_prices():
    """{(game, line): {"median": logged belief median or None, "a": our charge, "valid": we accepted a positive charge}}"""
    out = {}
    try:
        games = json.loads((ROOT / "outputs" / "model_outputs.json").read_text())["games"]
    except (OSError, ValueError):
        games = {}
    for g, e in games.items():
        for s in e.get("submitted", []):
            if s.get("t_median"):
                out[(int(g), s["index"] + 1)] = {"median": s["t_median"], "a": s["a"], "valid": s["b"] > 0}
    for d in sorted((ROOT / "past-cases").glob("case_*")):
        g = int(d.name[-3:])
        try:
            res = json.loads((d / "results.json").read_text())
        except (OSError, ValueError):
            continue
        for k, v in res.get("lines", {}).items():
            e = out.setdefault((g, int(k)), {"median": None})
            e["a"] = (v.get("charge") or {}).get("a") or 0.0
            e.setdefault("valid", ((v.get("review") or {}).get("accepted_positive") or 0) > 0)
    return out


def income(a, lo, hi, n=11):
    """Charge side: a fair charge earns at least a from each team, an inflated one is taken as 0. None = not decidable."""
    if a <= 0:
        return 0.0
    if a <= lo:
        return n * a
    if hi is not None and a >= hi:
        return 0.0
    return None


def cost(b, incoming, lo, hi):
    """Review side: what the charges we received cost under limit b. Charges whose class is unknown are left out."""
    total, skipped = 0.0, 0
    for c in incoming:
        a = c["a"]
        if a <= 0:
            continue
        fair = a <= lo
        inflated = hi is not None and a >= hi
        if not (fair or inflated):
            skipped += 1
            continue
        total += a if a <= b else (1.5 * a if fair else 0.0)
    return total, skipped


def main():
    arg = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    g_from, g_to = int(arg.get("--from", 1)), int(arg.get("--to", 10 ** 6))
    labels = {}
    for line in (ROOT / "runs" / "bench" / "labels.jsonl").read_text().splitlines():
        d = json.loads(line)
        labels[(d["game"], d["line"])] = d
    bot = bot_prices()
    rows, t_lookup = [], 0.0
    for d in sorted((ROOT / "past-cases").glob("case_*")):
        g = int(d.name[-3:])
        if not g_from <= g <= g_to:
            continue
        inv = (d / "invoice.txt").read_text()
        trade = mt.trade_of(inv)
        for x in mt.parse_invoice_lines(inv):
            lb = labels.get((g, x["pos"]))
            if not lb:
                continue
            t0 = time.perf_counter()
            r = db.lookup(x["text"], x["qty"] or 1.0, x["unit"] or "pcs", trade)
            t_lookup += time.perf_counter() - t0
            rows.append({"g": g, "l": x["pos"], "text": x["text"], "qty": x["qty"], "unit": x["unit"], "lo": lb["t_lo"],
                         "hi": lb["t_hi"], "r": r, "bot": bot.get((g, x["pos"])), "lb": lb})

    owed = [r for r in rows if r["lo"] > 0]
    out = ["# Price database vs. the finished games", "",
           f"Generated by `research/prices/db_eval.py`. Games {min(r['g'] for r in rows)}-{max(r['g'] for r in rows)}: "
           f"{len(rows)} labelled invoice lines, {len(owed)} of them owed (t_lo > 0). "
           f"All {len(rows)} lookups took {t_lookup * 1000:.0f} ms in total, with no LLM call.", ""]

    # ---- per line
    out += ["## Lines that were owed (the only ones that say something about prices)", "",
            "err = ln(price / bracket): 0 = inside, -0.69 = half of the lower bound, +0.69 = twice the upper bound. "
            "Our bot's median is logged for games 1-15 only; `a` is what we charged (set below the median on purpose).", "",
            "| game.line | invoice line | t bracket | database | err | bot median | err | closer | our charge a |", "|---|---|---|---|---|---|---|---|---|"]
    both, kinds = [], {}
    for r in owed:
        res = r["r"]
        p = res.get("p50") if res else None
        e_db = err(p, r["lo"], r["hi"])
        b = r["bot"] or {}
        e_bot = err(b.get("median"), r["lo"], r["hi"])
        kind = res["kind"] if res else "no match"
        if res and res["kind"] == "rate" and p is None:
            kind = "rate, no hours"
        k = kinds.setdefault(kind, {"n": 0, "priced": 0, "errs": []})
        k["n"] += 1
        if e_db is not None:
            k["priced"] += 1
            k["errs"].append(e_db)
        closer = ""
        if e_db is not None and e_bot is not None:
            both.append((r, e_db, e_bot, res))
            closer = "tie" if abs(abs(e_db) - abs(e_bot)) < 0.05 else ("database" if abs(e_db) < abs(e_bot) else "bot")
        br = f"{r['lo']:.0f}-{r['hi']:.0f}" if r["hi"] else f">= {r['lo']:.0f}"
        cell = f"{p:.0f} ({res['concept']}, {res['confidence']})" if p is not None else (
            f"- ({res['concept']}" + (f", {res['unit_p50']:.0f} EUR/h" if res.get("unit_p50") else "") + ")" if res else "-")
        out.append(f"| {r['g']}.{r['l']} | {r['text'][:58]} ({r['qty']:g} {r['unit']}) | {br} | {cell} | "
                   f"{'' if e_db is None else f'{e_db:+.2f}'} | {'' if not b.get('median') else format(b['median'], '.0f')} | "
                   f"{'' if e_bot is None else f'{e_bot:+.2f}'} | {closer} | {b.get('a', 0):.0f} |")

    # ---- summary
    def stats(errs):
        if not errs:
            return "-"
        inside = sum(e == 0 for e in errs)
        return (f"{inside}/{len(errs)} inside, median |err| {statistics.median(abs(e) for e in errs):.2f}, "
                f"{sum(e < 0 for e in errs)} too low, {sum(e > 0 for e in errs)} too high")

    out += ["", "## Coverage of the owed lines by kind of answer", "",
            "| answer | owed lines | with a line price | result |", "|---|---|---|---|"]
    for kind, k in sorted(kinds.items(), key=lambda kv: -kv[1]["n"]):
        out.append(f"| {kind} | {k['n']} | {k['priced']} | {stats(k['errs'])} |")
    priced = sum(k["priced"] for k in kinds.values())
    out += ["", f"The database prices **{priced} of {len(owed)}** owed lines.", ""]

    out += ["## Head to head with the bot's logged median (games 1-15)", ""]
    if both:
        e_db = [b[1] for b in both]
        e_bot = [b[2] for b in both]
        win = sum(abs(a) < abs(b) - 0.05 for a, b in zip(e_db, e_bot))
        lose = sum(abs(b) < abs(a) - 0.05 for a, b in zip(e_db, e_bot))
        out += [f"- lines: {len(both)}", f"- database: {stats(e_db)}", f"- our bot:  {stats(e_bot)}",
                f"- database closer on {win}, bot closer on {lose}, tie on {len(both) - win - lose}", ""]
        out += ["| kind | lines | database median abs err | bot median abs err | database closer / bot closer |", "|---|---|---|---|---|"]
        for kind in sorted({b[3]["kind"] for b in both}):
            sel = [b for b in both if b[3]["kind"] == kind]
            w = sum(abs(b[1]) < abs(b[2]) - 0.05 for b in sel)
            lo = sum(abs(b[2]) < abs(b[1]) - 0.05 for b in sel)
            out.append(f"| {kind} | {len(sel)} | {statistics.median(abs(b[1]) for b in sel):.2f} | "
                       f"{statistics.median(abs(b[2]) for b in sel):.2f} | {w} / {lo} |")
        out.append("")

    # ---- replay in EUR
    out += ["## Replay in EUR: our numbers replaced by the database price", "",
            f"Rule: a' = {A_MULT} x database price, b' = {B_MULT} x database price, on lines the database prices and our bot treated "
            "as owed. Income: a fair charge earns a from each of 11 teams, an inflated one 0 (pessimistic), a charge inside an "
            "open bracket is not decidable. Cost: charges we received, settled under b'; charges of unknown class left out on both sides.", "",
            "Baseline (\"ours\"): games 1-15 the same rule on the bot's logged median, so only the price source differs; "
            "games 16+ what we really charged and paid.", "",
            "| game.line | line | t bracket | database | a: ours -> new | income: ours -> new | cost: ours -> new | gain |", "|---|---|---|---|---|---|---|---|"]
    tot = {}
    for r in rows:
        res, b = r["r"], r["bot"] or {}
        if not (res and res.get("p50")) or not b.get("valid"):
            continue
        p, lo, hi = res["p50"], r["lo"], r["hi"]
        c1, _ = cost(B_MULT * p, r["lb"]["incoming"], lo, hi)
        inc1 = income(A_MULT * p, lo, hi)
        if b.get("median"):   # same rule, the bot's own price
            a0 = A_MULT * b["median"]
            c0, _ = cost(B_MULT * b["median"], r["lb"]["incoming"], lo, hi)
            base = "same rule"
        else:                 # what really happened
            a0 = b.get("a", 0.0)
            known = [c for c in r["lb"]["incoming"] if c["a"] > 0 and (c["a"] <= lo or (hi is not None and c["a"] >= hi))]
            c0 = sum(c["paid"] for c in known)
            base = "actual"
        inc0 = income(a0, lo, hi)
        d_inc = None if inc0 is None or inc1 is None else inc1 - inc0
        gain = (d_inc or 0.0) - (c1 - c0)
        k = tot.setdefault((base, res["kind"]), {"n": 0, "inc": 0.0, "cost": 0.0, "open": 0})
        k["n"] += 1
        k["inc"] += d_inc or 0.0
        k["cost"] += c1 - c0
        k["open"] += d_inc is None
        br = f"{lo:.0f}-{hi:.0f}" if hi and lo else (f">= {lo:.0f}" if lo else (f"< {hi:.0f}" if hi else "unknown"))
        f = lambda v: "?" if v is None else f"{v:.0f}"
        out.append(f"| {r['g']}.{r['l']} | {r['text'][:40]} | {br} | {p:.0f} | {a0:.0f} -> {A_MULT * p:.0f} | {f(inc0)} -> {f(inc1)} | "
                   f"{c0:.0f} -> {c1:.0f} | {gain:+.0f}{' (income open)' if d_inc is None else ''} |")
    out += ["", "| baseline | kind | lines | income change | cost change | net gain | lines with undecidable income |", "|---|---|---|---|---|---|---|"]
    for (base, kind), k in sorted(tot.items(), reverse=True):
        out.append(f"| {base} | {kind} | {k['n']} | {k['inc']:+.0f} | {k['cost']:+.0f} | {k['inc'] - k['cost']:+.0f} | {k['open']} |")
    for base in ("same rule", "actual"):
        ks = [k for (b_, _), k in tot.items() if b_ == base]
        if ks:
            out.append(f"| **{base}** | all | {sum(k['n'] for k in ks)} | {sum(k['inc'] for k in ks):+.0f} | {sum(k['cost'] for k in ks):+.0f} | "
                       f"**{sum(k['inc'] - k['cost'] for k in ks):+.0f}** | {sum(k['open'] for k in ks)} |")
    out.append("")

    # ---- not owed lines
    zero = [r for r in rows if r["lo"] == 0]
    zp = [r for r in zero if r["r"] and r["r"].get("p50")]
    over = [r for r in zp if r["hi"] is not None and r["r"]["p50"] >= r["hi"]]
    out += ["## Lines with no confirmed fair charge (t_lo = 0)", "",
            f"{len(zero)} lines, the database returns a price for {len(zp)}; on {len(over)} of those it lies above the upper bound. "
            "Most of these lines were not covered at all, so the market price was never owed. The database knows prices, "
            "not cover: its number must never raise `p_valid`.", ""]
    (HERE / "db_report.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
