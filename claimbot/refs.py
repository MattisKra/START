"""Price references from finished games, put in front of the case text.

The game uses its own price list and reuses items across cases (game 10 line 1 was the sum of game 8 lines 1-4).
For every finished game the bracket of the fair value per line is derived from the public leaderboard: a charge
rejected with a penalty was fair (t >= charge), a charge rejected for 0 was inflated (t < charge). Only the derived
bracket per line is cached (runs/t_brackets.json, not tracked); no leaderboard rows are stored.
"""

import json
import re
import time
from collections import defaultdict

import requests

from . import config
from .outputs import OUTPUTS_FILE

BASE = "https://c2f.public.quantco.cloud/leaderboard/api/"
CACHE = config.WORK_DIR.parent / "t_brackets.json"
ENABLED = config.os.getenv("CLAIMS_PRICE_REFS", "1") == "1"
PAUSE_S = 2.1  # between leaderboard requests


def _get(path: str, **params) -> dict:
    r = requests.get(BASE + path, params=params, timeout=30)
    r.raise_for_status()
    time.sleep(PAUSE_S)
    return r.json()


def _load() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}


def fetch_brackets(game: int) -> dict:
    """{line (1-based, str): [t_lo, t_hi or None]} for one finished game."""
    teams = [t["team_name"] for t in _get("matrix", page=1, game_limit=20)["items"]]
    seen = {}
    for team in teams:
        page = 1
        while True:
            d = _get("transactions", game_id=game, team=team, page=page)
            for r in d.get("items", []):
                seen[(r["issuer"], r["reviewer"], r["line_item_index"])] = r
            if page >= d.get("total_pages", 1) or not d.get("items"):
                break
            page += 1
    by_line = defaultdict(list)
    for r in seen.values():
        by_line[r["line_item_index"]].append(r)
    out = {}
    for line, rs in by_line.items():
        charge = {}
        for r in rs:
            if r["accepted"]:
                charge[r["issuer"]] = max(charge.get(r["issuer"], 0.0), r["amount"])
        for r in rs:
            if not r["accepted"] and r["amount"] > 0:
                charge[r["issuer"]] = r["amount"] / 1.5
        lo, hi = 0.0, None
        for r in rs:
            if r["accepted"]:
                continue
            a = charge.get(r["issuer"], 0.0)
            if r["amount"] > 0:
                lo = max(lo, a)
            elif a > 0:
                hi = a if hi is None else min(hi, a)
        out[str(line)] = [round(lo, 2), None if hi is None else round(hi, 2)]
    return out


def refresh(before_game: int, budget_s: float = 1e9) -> None:
    """Fetch brackets of finished games (id < before_game) that are not cached yet. Call only between rounds."""
    if not ENABLED:
        return
    cache = _load()
    stop = time.monotonic() + budget_s
    for g in range(before_game - 1, 0, -1):  # newest first
        if str(g) in cache:
            continue
        if time.monotonic() + 60 > stop:  # one game takes about 30 s
            return
        try:
            br = fetch_brackets(g)
        except Exception as e:  # noqa: BLE001 - references are optional
            print(f"refs: game {g} not available ({e!r}); trying again later")
            return  # never retry in a tight loop
        if br:
            cache[str(g)] = br
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache, indent=1))
            print(f"refs: game {g} brackets cached ({len(br)} lines)")
    try:
        embed_missing()
    except Exception as e:  # noqa: BLE001
        print(f"refs: embedding failed: {e!r}")


def _rows(exclude_game=None) -> list[dict]:
    """Past lines with an informative bracket: {game, text, label, rng}."""
    try:
        cache = _load()
        games = json.loads(OUTPUTS_FILE.read_text())["games"]
    except (OSError, ValueError, KeyError):
        return []
    rows = []
    for g in sorted(cache, key=int):
        if exclude_game is not None and str(g) == str(exclude_game):
            continue
        entry = games.get(str(g))
        if not entry or not entry.get("members"):
            continue
        ms = entry["members"]
        lines = max((m["estimate"]["lines"] for m in ms), key=len)
        for l in lines:
            br = cache[g].get(str(l["index"] + 1))
            if not br:
                continue
            lo, hi = br
            pv = [x["p_valid"] for m in ms for x in m["estimate"]["lines"] if x["index"] == l["index"]]
            valid = sum(pv) / len(pv) >= 2 / 3 if pv else False
            if lo > 0 and hi is not None:
                rng = f"{lo:.0f} to {hi:.0f} EUR"
            elif lo > 0:
                rng = f"at least {lo:.0f} EUR"
            elif hi is not None and valid:
                rng = f"below {hi:.0f} EUR"
            else:  # nothing known, or probably a line that was not owed: no price signal
                continue
            text = " ".join(l["invoice_text"].split())[:160]
            rows.append({"game": int(g), "text": text, "rng": rng,
                         "label": f"- case {g}: \"{text}\" ({l['quantity_invoiced']:g} {l['unit']}): {rng}"})
    return rows


# ---------------------------------------------------------------- retrieval by embedding

EMBED_MODEL = config.os.getenv("CLAIMS_EMBED_MODEL", "text-embedding-3-small")
TOP_K = int(config.os.getenv("CLAIMS_REFS_TOP_K", "3"))  # most similar past lines per invoice line; 0 = list all
EMB_CACHE = config.WORK_DIR.parent / "ref_embeddings.json"
_LINE = re.compile(r"^\s*(\d{1,2})\s{2,}(\S.*?)\s{2,}\d+(?:[.,]\d+)?\s+\S")


def _embed(texts: list[str], timeout: float) -> list[list[float]]:
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_KEY, timeout=timeout, max_retries=0)
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def _emb_load() -> dict:
    try:
        return json.loads(EMB_CACHE.read_text())
    except (OSError, ValueError):
        return {}


def embed_missing() -> None:
    """Embed past line texts that are not in the cache yet. Call only between rounds."""
    if not ENABLED or TOP_K <= 0:
        return
    emb = _emb_load()
    todo = sorted({r["text"] for r in _rows()} - set(emb))
    if not todo:
        return
    for t, v in zip(todo, _embed(todo, timeout=30)):
        emb[t] = v
    EMB_CACHE.write_text(json.dumps(emb))
    print(f"refs: embedded {len(todo)} past lines")


def invoice_lines(invoice_text: str) -> list[str]:
    """Line descriptions from the pdftotext layout (POS., description over one or more rows, amount, unit)."""
    out, cur = [], None
    for raw in invoice_text.splitlines():
        m = _LINE.match(raw)
        if m:
            cur = [m.group(2)]
            out.append(cur)
        elif cur is not None and raw.strip() and not raw.lstrip().startswith(("Created on", "POS.")) and raw.startswith("   "):
            cur.append(raw.strip())
        else:
            cur = None
    return [" ".join(" ".join(c).split()) for c in out]


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / ((sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) or 1.0)


def _select(rows: list[dict], case) -> tuple[list[dict], str]:
    """The TOP_K most similar past lines for each line of the present invoice. Falls back to all rows."""
    if TOP_K <= 0 or case is None or len(rows) <= TOP_K:
        return rows, "all"
    try:
        queries = invoice_lines(case.invoice_text)
        emb = _emb_load()
        cand = [r for r in rows if r["text"] in emb]
        if not queries or len(cand) < len(rows):
            return rows, "all (no invoice lines parsed)" if not queries else "all (embeddings missing)"
        keep = set()
        for qv in _embed(queries, timeout=4):
            ranked = sorted(range(len(cand)), key=lambda i: -_cos(qv, emb[cand[i]["text"]]))
            keep.update(ranked[:TOP_K])
        return [cand[i] for i in sorted(keep)], f"top {TOP_K} for each of {len(queries)} lines"
    except Exception as e:  # noqa: BLE001 - the full list still works
        return rows, f"all (retrieval failed: {e!r})"


def block(exclude_game=None, case=None) -> str:
    """Reference text for the prompt; empty if nothing is known."""
    if not ENABLED:
        return ""
    rows, how = _select(_rows(exclude_game), case)
    if not rows:
        return ""
    print(f"refs: {len(rows)} past lines in the prompt ({how})")
    return (
        "=== PRICE REFERENCES (known outcomes of earlier cases from the same assessor) ===\n"
        "The earlier invoice lines most similar to the lines of this invoice, with the amount finally owed per line "
        "(gross total for the whole line). The assessor uses one fixed price list, "
        "and it is often far below ordinary market prices for disposal, flat-rate and service lines. Earlier cases recur "
        "with lines split or merged. If a line of the present case matches an earlier line, or combines several earlier "
        "lines, set p50 so that the gross line total lands inside the referenced amount (the sum for combined lines) and "
        "give a narrow p10-p90. For other lines use the references to calibrate the price level of similar kinds of work "
        "or goods. Coverage (p_valid) is still decided from the present policy and description only.\n"
        + "\n".join(r["label"] for r in rows) + "\n\n"
    )
