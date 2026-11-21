"""Does retrieval over PAST games help? Leave-one-game-out test of a 'reference assessments' block in the prompt.

    uv run --with pyzipper python research/bench/rag_bench.py [--models a,b,c] [--repeats 2] [--k 2] [--min-sim 0.15] [--numbers yes|no]

Store   every labelled line of the OTHER games: invoice text, quantity/unit, trade, and the experts' outcome (excluded, or gross amount bounds
        t_lo / t_hi from runs/bench/labels.jsonl, derived from the leaderboard; local only, never committed).
Query   each line of the held-out case: TF-IDF cosine over the line text and trade; the k best matches above --min-sim.
Prompt  v2_policy_math + a block "REFERENCE ASSESSMENTS FROM EARLIER CLAIMS" with those neighbours (numbers can be switched off to see
        whether only the verdict helps). Cases with no neighbour keep the plain v2 prompt (no call is made, baseline is reused).
Score   exactly as bench.py, compared with the saved plain-v2 answers of the same models on the same case.
The point is as much to expose when retrieval MISLEADS as when it helps: similar-looking lines can have opposite outcomes because the
outcome depends on the policy clause, not on the item.
"""
import argparse, collections, glob, importlib.util, json, math, os, re, statistics as st, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("bench", ROOT / "research/bench/bench.py")
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
oc = bench.oc
STOP = set("the of and a an to in for on with at by or incl including from new old".split())


def toks(s):
    return [w for w in re.findall(r"[a-zäöüß]{3,}", s.lower()) if w not in STOP]


def trade_of(case):
    txt = subprocess.run(["pdftotext", "-layout", str(bench.RUNS / "cases" / case / "invoices.pdf"), "-"], capture_output=True, text=True).stdout
    m = re.search(r"INVOICE NO\.\s+DATE\s+DUE\s+TRADE\s*\n\s*(\S+)\s+(.+?)\s{2,}(.+?)\s{2,}(.+)", txt)
    return m.group(4).strip() if m else ""


def line_texts(case, saved):
    """invoice line text/unit/qty for a case, from any saved parsed answer of that case."""
    for r in saved:
        if r["case"] == case and r.get("parsed"):
            return [dict(text=l["invoice_text"], unit=l["unit"], qty=l["quantity_invoiced"], idx=i + 1)
                    for i, l in enumerate(sorted(r["parsed"]["lines"], key=lambda x: x["index"]))]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="openai/gpt-6-luna,google/gemini-3.8-flash,anthropic/claude-haiku-5.5,openai/gpt-6.1-terra")
    ap.add_argument("--repeats", type=int, default=2); ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--min-sim", type=float, default=0.15); ap.add_argument("--numbers", default="yes")
    ap.add_argument("--budget", type=float, default=1.0)
    a = ap.parse_args()
    labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
    saved = []
    for f in sorted(glob.glob(str(ROOT / "runs/bench/results/bench_*.json"))):
        saved += [r for r in json.load(open(f))["results"] if r.get("parsed")]
    cases = sorted(labels)
    store = []                                                    # one entry per labelled line
    for c in cases:
        trade = trade_of(c)
        for lt in line_texts(c, saved):
            lab = labels[c].get(lt["idx"])
            if lab:
                store.append(dict(case=c, **lt, trade=trade, lab=lab, zero=bench.is_zero(lab, anns.get(c, {}).get(str(lt["idx"]), {}))))
    df = collections.Counter(w for e in store for w in set(toks(e["text"] + " " + e["trade"])))
    N = len(store)
    vec = lambda s: {w: (1 + math.log(1 + n)) * math.log((N + 1) / (1 + df.get(w, 0)) + 1) for w, n in collections.Counter(toks(s)).items()}
    cos = lambda u, v: sum(u[w] * v.get(w, 0) for w in u) / ((math.sqrt(sum(x * x for x in u.values())) * math.sqrt(sum(x * x for x in v.values()))) or 1)
    for e in store:
        e["vec"] = vec(e["text"] + " " + e["trade"])

    def fmt(e):
        qty = f"{e['qty']:g} {e['unit']}"
        if e["zero"]:
            res = "the experts treated it as EXCLUDED (amount 0)"
        elif a.numbers == "no":
            res = "the experts treated it as covered"
        else:
            hi = "" if e["lab"]["t_hi"] is None else f" and below {e['lab']['t_hi']:.0f}"
            res = f"the experts' amount for the whole line was at least {e['lab']['t_lo']:.0f}{hi} EUR gross"
        return f"- \"{e['text']}\" ({qty}, {e['trade']}): {res}."

    prompts, shown = {}, {}
    base = (bench.BENCH / "prompts" / "v2_policy_math.txt").read_text()
    for c in cases:
        block = []
        for lt in line_texts(c, saved):
            q = vec(lt["text"] + " " + trade_of(c))
            nb = sorted(((cos(q, e["vec"]), e) for e in store if e["case"] != c), key=lambda x: -x[0])[:a.k]
            nb = [(s, e) for s, e in nb if s >= a.min_sim]
            if nb:
                block.append(f"Line {lt['idx']} (\"{lt['text'][:60]}\"):\n" + "\n".join(fmt(e) for s, e in nb))
        if block:
            prompts[c] = base + ("\n\nREFERENCE ASSESSMENTS FROM EARLIER CLAIMS IN THIS TOURNAMENT (neighbours by item text; use them only as an anchor when the "
                                 "item AND the governing policy clause are comparable, otherwise ignore them; the same wording can have opposite outcomes under "
                                 "different policies):\n" + "\n".join(block))
            shown[c] = block
    print(f"store {N} lines from {len(cases)} cases; cases that get a reference block: {sorted(prompts)} (numbers={a.numbers})")
    for c, b in shown.items():
        print(f"\n--- {c} reference block\n" + "\n".join(b))
    if not prompts:
        return
    key = os.environ["OPENROUTER_API_KEY"]; cat = oc.catalogue(); models = a.models.split(",")
    content = {c: oc.load_case(bench.ensure_case(c), True) for c in prompts}
    jobs = [(c, m, r) for c in prompts for m in models for r in range(a.repeats)]
    spent = [0.0]; out = collections.defaultdict(list)

    def run(j):
        c, m, r = j
        if spent[0] >= a.budget:
            return j, None
        for _ in range(2):
            res = oc.call(m, prompts[c], content[c], oc.pick_reasoning(cat, m, "min"), 6000, key, 150)
            spent[0] += res.get("cost") or 0
            if res.get("parsed") and res["parsed"].get("lines"):
                return j, bench.score_answer(res["parsed"], labels[c], anns.get(c, {}))
        return j, None

    with ThreadPoolExecutor(8) as ex:
        for f in as_completed([ex.submit(run, j) for j in jobs]):
            (c, m, r), rows = f.result()
            if rows:
                out[(c, m)] += rows
    print("\nper case and model: plain v2 (saved) vs v2 + references   [b_regret EUR/line | a_score | |bias|]")
    tot_b, tot_r = [], []
    for c in sorted(prompts):
        for m in models:
            plain = [x for r in saved if r["case"] == c and r["variant"] == "v2_policy_math" and r["model"] == m
                     for x in bench.score_answer(r["parsed"], labels[c], anns.get(c, {}))]
            rag = out.get((c, m), [])
            if not plain or not rag:
                continue
            s0, s1 = bench.summarize(plain), bench.summarize(rag)
            tot_b += plain; tot_r += rag
            print(f"  {c} {m.split('/')[-1]:22s} plain {s0['b_regret']!s:>7s} | {s0['a_score']!s:>5s} | {s0['abs_bias']!s:>5s}    +refs {s1['b_regret']!s:>7s} | {s1['a_score']!s:>5s} | {s1['abs_bias']!s:>5s}")
    s0, s1 = bench.summarize(tot_b), bench.summarize(tot_r)
    print(f"\nALL (cases with references): plain  b_regret {s0['b_regret']} a_score {s0['a_score']} |bias| {s0['abs_bias']}   with references  b_regret {s1['b_regret']} a_score {s1['a_score']} |bias| {s1['abs_bias']}")
    print(f"spent ${spent[0]:.3f}")


if __name__ == "__main__":
    main()
