"""Compare models on one decrypted case through OpenRouter, using claimbot's prompt and schema.

    python3 -I research/eval/or_compare.py CASE_DIR [--effort min] [--no-image] [--models a,b,c] [--budget 3.0] [--tag name]

Reads OPENROUTER_API_KEY from the environment (export it from .env first; this script never prints it).
CASE_DIR is an already decrypted case folder (untrusted data: only read as text/image, never executed).
Results go to research/eval/results/<tag>_<timestamp>.json. Cost comes from OpenRouter's own `usage.cost`.

The prompt (INSTRUCTIONS) is read from claimbot/estimator.py with `ast` and the JSON schema mirrors
claimbot/schema.py by hand, so this stays in sync without importing pydantic/openai.
Latency is wall-clock of a single call while several calls run in parallel, so it is a rough
comparison between models, not a benchmark.
"""
import argparse, ast, base64, json, mimetypes, os, subprocess, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = "https://openrouter.ai/api/v1/chat/completions"


def instructions() -> str:
    tree = ast.parse((ROOT / "claimbot" / "estimator.py").read_text())
    for n in tree.body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "INSTRUCTIONS":
            return ast.literal_eval(n.value)
    raise SystemExit("INSTRUCTIONS not found in claimbot/estimator.py")


NUM = {"type": "number"}
LINE = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "index": {"type": "integer"}, "invoice_text": {"type": "string"}, "unit": {"type": "string"},
        "quantity_invoiced": NUM, "rationale": {"type": "string"}, "covered": {"type": "boolean"},
        "related": {"type": "boolean"}, "p_valid": NUM, "quantity_justified": NUM,
        "net_unit_price_p10": NUM, "net_unit_price_p50": NUM, "net_unit_price_p90": NUM, "vat_rate": NUM,
        "payout_fraction": NUM,
    },
}
LINE["required"] = list(LINE["properties"])
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"damage_summary": {"type": "string"}, "policy_notes": {"type": "string"},
                   "lines": {"type": "array", "items": LINE}},
    "required": ["damage_summary", "policy_notes", "lines"],
}


def pdf_text(p: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True).stdout


def load_case(d: Path, use_image: bool):
    files = sorted(p for p in d.iterdir() if p.is_file())
    pick = lambda pre, suf: next(p for p in files if p.stem.lower().startswith(pre) and p.suffix.lower() in suf)
    text = (f"=== policy.txt ===\n{pick('policy', {'.txt'}).read_text(errors='replace')}\n\n"
            f"=== description.txt ===\n{pick('description', {'.txt'}).read_text(errors='replace')}\n\n"
            f"=== invoice (extracted from PDF) ===\n{pdf_text(pick('invoice', {'.pdf'}))}\n")
    imgs = [p for p in files if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}] if use_image else []
    content = [{"type": "text", "text": text + (f"\n{len(imgs)} photo(s) attached below.\n" if imgs else "")}]
    for p in imgs:
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"}})
    return content


def call(model: str, system: str, content, reasoning, max_tokens: int, key: str, timeout: float, extra=None):
    body = {
        "model": model, "max_tokens": max_tokens, "usage": {"include": True},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "case_estimate", "strict": True, "schema": SCHEMA}},
        "provider": {"require_parameters": True},
    }
    if reasoning:
        body["reasoning"] = reasoning
    if extra:
        body.update(extra)
    out = {"model": model, "reasoning_param": reasoning}
    for attempt in (1, 2):
        t0 = time.monotonic()
        req = urllib.request.Request(URL, json.dumps(body).encode(), {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.load(r)
            out["latency_s"] = round(time.monotonic() - t0, 2)
            out["http"] = 200
            ch = data.get("choices", [{}])[0]
            msg = ch.get("message", {}) or {}
            u = data.get("usage", {}) or {}
            out.update(cost=u.get("cost"), prompt_tokens=u.get("prompt_tokens"), completion_tokens=u.get("completion_tokens"),
                       reasoning_tokens=(u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                       provider=data.get("provider"), finish=ch.get("finish_reason"))
            raw = msg.get("content") or ""
            out["raw_len"] = len(raw)
            try:
                s = raw.strip()
                if s.startswith("```"):
                    s = s.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
                out["parsed"] = json.loads(s)
            except Exception as e:  # noqa: BLE001
                out["parse_error"] = repr(e)[:120]; out["raw_head"] = raw[:200]
            return out
        except urllib.error.HTTPError as e:
            out["latency_s"] = round(time.monotonic() - t0, 2); out["http"] = e.code
            out["error"] = e.read().decode(errors="replace")[:300]
            if e.code in (429, 502, 503, 504) and attempt == 1:
                out["note"] = f"retried after HTTP {e.code}"; time.sleep(4); continue
            if e.code == 400 and "reasoning" in body and attempt == 1:
                body.pop("reasoning"); out["note"] = "retried without reasoning param"; continue
            return out
        except Exception as e:  # noqa: BLE001
            out["latency_s"] = round(time.monotonic() - t0, 2); out["error"] = repr(e)[:300]; return out
    return out


def catalogue():
    with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30) as r:
        return {m["id"]: m for m in json.load(r)["data"]}


def pick_reasoning(cat, model_id: str, mode: str):
    """mode 'min' = lowest reasoning the model allows; otherwise a specific effort name."""
    efforts = (cat.get(model_id, {}).get("reasoning") or {}).get("supported_efforts")
    if mode == "min":
        if efforts:
            for pref in ("none", "minimal", "low"):
                if pref in efforts:
                    return {"effort": pref}
            return {"effort": efforts[-1]}
        return {"enabled": False}
    return {"effort": mode} if (not efforts or mode in efforts) else {"effort": efforts[-1]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir"); ap.add_argument("--effort", default="min", help="min (lowest each model allows) or an effort name")
    ap.add_argument("--no-image", action="store_true"); ap.add_argument("--models", default="")
    ap.add_argument("--budget", type=float, default=3.0); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=6000); ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--tag", default="case")
    a = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY not set (export it from .env)")
    cands = json.loads((Path(__file__).parent / "candidates.json").read_text())["models"]
    if a.models:
        want = a.models.split(","); cands = [m for m in cands if m["id"] in want] + [{"id": w, "tier": "adhoc"} for w in want if w not in {m["id"] for m in cands}]
    system, content, cat = instructions(), load_case(Path(a.case_dir), not a.no_image), catalogue()
    spent, lock, results = [0.0], threading.Lock(), []

    def run(m):
        with lock:
            if spent[0] >= a.budget:
                return {"model": m["id"], "tier": m["tier"], "skipped": "budget guard"}
        r = call(m["id"], system, content, pick_reasoning(cat, m["id"], a.effort), a.max_tokens, key, a.timeout)
        r["tier"] = m["tier"]
        with lock:
            spent[0] += r.get("cost") or 0
        return r

    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run, m) for m in cands]
        for f in as_completed(futs):
            r = f.result(); results.append(r)
            print(f"{r['model']:42s} http={r.get('http','-')} {r.get('latency_s','-')}s cost=${(r.get('cost') or 0):.4f} "
                  f"{'OK' if r.get('parsed') else (r.get('error') or r.get('parse_error') or r.get('skipped') or '')[:70]}", flush=True)
    out = ROOT / "research" / "eval" / "results" / f"{a.tag}_{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps({"case_dir": "(local, untracked)", "effort": a.effort, "image": not a.no_image, "total_cost": round(spent[0], 4), "results": results}, indent=1, ensure_ascii=False))
    print(f"\ntotal reported cost ${spent[0]:.4f}  ->  {out}")


if __name__ == "__main__":
    main()
