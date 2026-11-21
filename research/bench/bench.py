"""Benchmark candidate approaches (prompt variant x model) on released cases against leaderboard-derived expert bounds.

    uv run --with pyzipper python research/bench/bench.py [--variants v0_original,v1_current,v2_policy_math]
        [--models openai/gpt-6-luna,...] [--cases case_001,case_002] [--repeats 1] [--budget 4] [--no-image]

Inputs
  runs/bench/labels.jsonl        built by build_labels.py (gitignored; per line: t bracket [t_lo, t_hi), our charges received, our a)
  research/bench/annotations.json  qualitative hints + 'zero' flags (committed, no other-team data)
  research/bench/prompts/*.txt     the instruction variants (v0 = first claimbot prompt, v1 = current claimbot prompt, v2 = candidate)
  the case zips in cases/, decrypted with the released key (needs TEAM_API_KEY; only started games)

How an answer is scored (hindsight replay; all numbers are against the BRACKET, not the unknown exact t)
  The model's per-line answer goes through claimbot.pricing.price_line (the production a/b rule), so a prompt change is scored
  by what it would have submitted.
  b side  Each charge we actually received on the line is classified fair (a <= t_lo), inflated (a >= t_hi, or the line is
          excluded) or unknown (inside the bracket: skipped). Replaying b': accept if a <= b' (pay a), else reject (pay 1.5a if
          fair, 0 if inflated). regret = cost - best possible cost (accept all fair, reject all inflated). b_score = 1 - regret/sum(a).
  a side  a' <= t_lo -> certainly fair, a_score = a'/t_lo (1.0 = charging the lower bound; revenue rises with a while fair).
          a' >= t_hi -> inflated, a_score = 0. Anything else is uncertain and left out (counted in n_unc). Excluded lines are skipped.
  zero    On excluded lines, zero_ok = (b' == 0).
  bias    log(model median gross / t_lo) on non-excluded lines: > 0 means too high (a lower bound, so the true error is even larger
          when this is positive and only an upper limit on under-pricing when negative).
  'actual' row = what the live bot really submitted, scored the same way from the rows we received.
Caveats: a handful of lines; brackets, not point labels; opponents' behaviour is held fixed; weights are not tuned.
"""
import argparse, collections, importlib.util, json, math, os, statistics as st, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from claimbot.pricing import price_line  # noqa: E402
from claimbot.schema import LineEstimate  # noqa: E402

spec = importlib.util.spec_from_file_location("oc", ROOT / "research" / "eval" / "or_compare.py")
oc = importlib.util.module_from_spec(spec); spec.loader.exec_module(oc)

BENCH = Path(__file__).parent
RUNS = ROOT / "runs" / "bench"
DEFAULT_MODELS = ["openai/gpt-6-luna", "anthropic/claude-haiku-5.5", "google/gemini-3.8-flash", "thinkingmachines/inkling-2-mini",
                  "deepseek/deepseek-v4.1-flash", "openai/gpt-6.1-terra", "anthropic/claude-sonnet-5.5"]


# ----------------------------------------------------------------------------- data
def load_labels():
    f = RUNS / "labels.jsonl"
    if not f.exists():
        sys.exit("runs/bench/labels.jsonl missing: run research/bench/build_labels.py first")
    out = collections.defaultdict(dict)
    for l in f.read_text().splitlines():
        d = json.loads(l); out[d["case"]][d["line"]] = d
    return out


def ensure_case(case_id: str) -> Path:
    """Decrypt cases/<case_id>.zip with the released key into runs/bench/cases/<case_id> (fresh dir, cached)."""
    import pyzipper
    dest = RUNS / "cases" / case_id
    if dest.exists() and any(dest.iterdir()):
        return dest
    gid = int(case_id.split("_")[1])
    req = urllib.request.Request(f"{oc_base()}/api/games/{gid}/key", headers={"X-API-Key": os.environ["TEAM_API_KEY"]})
    key = json.load(urllib.request.urlopen(req, timeout=40))["decryption_key"]
    dest.mkdir(parents=True, exist_ok=True)
    with pyzipper.AESZipFile(ROOT / "cases" / f"{case_id}.zip") as z:
        z.pwd = key.encode()
        assert all(not n.startswith("/") and ".." not in n for n in z.namelist())
        z.extractall(dest)
    return dest


def oc_base():
    return "https://c2f.public.quantco.cloud"


# ----------------------------------------------------------------------------- scoring
def is_zero(lab, ann):
    if "zero" in ann:
        return bool(ann["zero"])
    return lab["t_lo"] == 0 and lab.get("n_fair", 0) == 0 and lab.get("n_inflated", 0) >= 1


def classify(a, lab, zero):
    if a <= 0:
        return None
    if zero:
        return "inflated"
    if a <= lab["t_lo"]:
        return "fair"
    if lab["t_hi"] is not None and a >= lab["t_hi"]:
        return "inflated"
    return None


def b_replay(b, inc, lab, zero):
    cost = best = tot = 0.0
    for r in inc:
        c = classify(r["a"], lab, zero)
        if c is None:
            continue
        a = r["a"]; tot += a
        if c == "fair":
            best += a
        cost += (a if a <= b else 1.5 * a) if c == "fair" else (a if a <= b else 0.0)
    return cost - best, tot


def b_actual(inc, lab, zero):
    cost = best = tot = 0.0
    for r in inc:
        c = classify(r["a"], lab, zero)
        if c is None:
            continue
        tot += r["a"]; cost += r["paid"]
        if c == "fair":
            best += r["a"]
    return cost - best, tot


def a_score(a, lab, zero):
    if zero or a is None or a <= 0:
        return None
    if a <= lab["t_lo"]:
        return a / lab["t_lo"]
    if lab["t_hi"] is not None and a >= lab["t_hi"]:
        return 0.0
    return "unc"


def score_line(price, lab, ann):
    zero = is_zero(lab, ann)
    reg, tot = b_replay(price["b"], lab["incoming"], lab, zero)
    out = dict(b=price["b"], a=price["a"], t_med=price["t_median"], q=price["q"], b_regret=reg, b_tot=tot,
               b_score=(1 - reg / tot) if tot else None, a_score=a_score(price["a"], lab, zero), zero=zero,
               zero_ok=(price["b"] == 0) if zero else None)
    if not zero and lab["t_lo"] > 0 and price["t_median"] > 0:
        out["bias"] = math.log(price["t_median"] / lab["t_lo"])
    return out


def score_answer(parsed, labs, anns):
    """parsed = model JSON ({'lines': [...]}) -> list of per-line score dicts (aligned to label lines by position)."""
    lines = sorted(parsed["lines"], key=lambda l: l["index"])
    out = []
    for i, l in enumerate(lines):
        ln = i + 1
        if ln not in labs:
            continue
        l = dict(l); l.setdefault("payout_fraction", 1.0)
        p = price_line(LineEstimate(**l)).as_dict()
        s = score_line(p, labs[ln], anns.get(str(ln), {})); s["line"] = ln
        out.append(s)
    return out


def actual_row(labs, anns):
    out = []
    for ln, lab in sorted(labs.items()):
        zero = is_zero(lab, anns.get(str(ln), {}))
        reg, tot = b_actual(lab["incoming"], lab, zero)
        out.append(dict(line=ln, b_regret=reg, b_tot=tot, b_score=(1 - reg / tot) if tot else None,
                        a_score=a_score(lab["our_a"], lab, zero), zero=zero, a=lab["our_a"],
                        bias=(math.log(lab["our_a"] / lab["t_lo"]) if (not zero and lab["our_a"] and lab["t_lo"] > 0) else None)))
    return out


def summarize(rows):
    """rows: list of per-line dicts (possibly several cases/repeats) -> aggregate metrics."""
    reg = [r["b_regret"] for r in rows if r.get("b_tot")]
    bs = [r["b_score"] for r in rows if r.get("b_score") is not None]
    a_ok = [r["a_score"] for r in rows if isinstance(r.get("a_score"), float)]
    unc = sum(1 for r in rows if r.get("a_score") == "unc")
    zk = [r["zero_ok"] for r in rows if r.get("zero_ok") is not None]
    bias = [r["bias"] for r in rows if r.get("bias") is not None]
    f = lambda xs, nd=2: round(st.mean(xs), nd) if xs else None
    return dict(n=len(rows), b_regret=f(reg, 1), b_score=f(bs), a_score=f(a_ok), n_unc=unc, zero_ok=f(zk), bias=f(bias),
                abs_bias=f([abs(x) for x in bias]))


# ----------------------------------------------------------------------------- run
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="v0_original,v1_current,v2_policy_math")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--cases", default="")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--budget", type=float, default=4.0)
    ap.add_argument("--no-image", action="store_true")
    ap.add_argument("--web", action="store_true", help="enable OpenRouter's web-search plugin (3 results) for every call")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--timeout", type=float, default=150)
    a = ap.parse_args()
    key = os.environ["OPENROUTER_API_KEY"]
    labels = load_labels(); anns = json.loads((BENCH / "annotations.json").read_text())
    cases = [c for c in (a.cases.split(",") if a.cases else sorted(labels)) if c in labels]
    variants = {v: (BENCH / "prompts" / f"{v}.txt").read_text() for v in a.variants.split(",")}
    models = a.models.split(",")
    cat = oc.catalogue()
    content = {c: oc.load_case(ensure_case(c), not a.no_image) for c in cases}
    jobs = [(v, m, c, r) for v in variants for m in models for c in cases for r in range(a.repeats)]
    print(f"{len(jobs)} calls: {len(variants)} variants x {len(models)} models x {len(cases)} cases x {a.repeats} repeats; cases {cases}")
    spent, results = [0.0], []

    def run(j):
        v, m, c, r = j
        if spent[0] >= a.budget:
            return dict(variant=v, model=m, case=c, rep=r, skipped="budget")
        tot_cost, tot_lat, tries = 0.0, 0.0, 0
        for tries in (1, 2):  # one retry when the answer is empty / not valid JSON
            res = oc.call(m, variants[v], content[c], oc.pick_reasoning(cat, m, "min"), a.max_tokens, key, a.timeout,
                          extra={"plugins": [{"id": "web", "max_results": 3}]} if a.web else None)
            spent[0] += res.get("cost") or 0; tot_cost += res.get("cost") or 0; tot_lat += res.get("latency_s") or 0
            if isinstance(res.get("parsed"), dict) and len(res["parsed"].get("lines", [])) > 0:
                break
        out = dict(variant=v, model=m, case=c, rep=r, latency_s=round(tot_lat, 2), cost=tot_cost, tries=tries,
                   prompt_tokens=res.get("prompt_tokens"), completion_tokens=res.get("completion_tokens"), http=res.get("http"),
                   error=res.get("error") or res.get("parse_error"), finish=res.get("finish"), parsed=res.get("parsed"))
        if isinstance(res.get("parsed"), dict):
            try:
                out["lines"] = score_answer(res["parsed"], labels[c], anns.get(c, {}))
            except Exception as e:  # noqa: BLE001
                out["error"] = f"score failed: {e!r}"[:200]
        return out

    with ThreadPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(run, j) for j in jobs]):
            r = f.result(); results.append(r)
            print(f"  {r['variant']:16s} {r['model']:34s} {r['case']} {'OK ' if r.get('lines') else 'ERR'} {r.get('latency_s')}s ${(r.get('cost') or 0):.4f} {(r.get('error') or '')[:60]}", flush=True)

    # ---- table
    act = [x for c in cases for x in actual_row(labels[c], anns.get(c, {}))]
    rows = [("ACTUAL (live bot)", "-", summarize(act), None, None)]
    for v in variants:
        for m in models:
            rs = [r for r in results if r["variant"] == v and r["model"] == m and r.get("lines")]
            lines = [x for r in rs for x in r["lines"]]
            if not lines:
                continue
            rows.append((v, m, summarize(lines), st.mean(r["latency_s"] for r in rs), st.mean(r["cost"] or 0 for r in rs)))
    print(f"\nlines scored per row ~ {len(act)}; b_regret = EUR per line over classified charges (lower is better; 0 = perfect), "
          "b_score higher is better, a_score = a/t_lo on certain lines, bias = mean log(median/t_lo)")
    print(f"{'variant':18s}{'model':34s}{'n':>3s}{'b_regret':>9s}{'b_score':>8s}{'a_score':>8s}{'unc':>4s}{'zero_ok':>8s}{'bias':>6s}{'|bias|':>7s}{'lat s':>7s}{'$/case':>8s}")
    for v, m, s, lat, cost in rows:
        print(f"{v:18s}{m:34s}{s['n']:>3d}{str(s['b_regret']):>9s}{str(s['b_score']):>8s}{str(s['a_score']):>8s}{s['n_unc']:>4d}{str(s['zero_ok']):>8s}{str(s['bias']):>6s}{str(s['abs_bias']):>7s}"
              f"{(f'{lat:.1f}' if lat else '-'):>7s}{(f'{cost:.4f}' if cost else '-'):>8s}")
    RUNS.mkdir(parents=True, exist_ok=True); (RUNS / "results").mkdir(exist_ok=True)
    out = RUNS / "results" / f"bench_{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(dict(cases=cases, variants=list(variants), models=models, spent=round(spent[0], 4), results=results,
                                   actual=act), indent=1, default=str))
    print(f"\nspent ${spent[0]:.3f}; details (local, gitignored): {out}")


if __name__ == "__main__":
    main()
