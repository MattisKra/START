"""Do photos (or zoomed crops of them) help the reader? Same metric as bench.py / fable_eval.py.

    uv run --with pyzipper python research/bench/image_test.py [--readers SPEC,SPEC] [--budget 2]

Variants per reader and case: none (text only), full (the photo as the bot sends it), tiles (the full photo plus its four quadrant crops,
a stand-in for a zoom/crop tool: the model sees every region at about twice the resolution).
"""
import argparse, collections, copy, importlib.util, io, json, sys, statistics as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("bench", ROOT / "research/bench/bench.py")
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
from claimbot.case import load_case  # noqa: E402
from claimbot_fable import engine, readers  # noqa: E402


def tiles(path):
    im = Image.open(path).convert("RGB"); w, h = im.size; out = []
    for box in ((0, 0, w // 2, h // 2), (w // 2, 0, w, h // 2), (0, h // 2, w // 2, h), (w // 2, h // 2, w, h)):
        t = im.crop(box); t.thumbnail((1400, 1400)); b = io.BytesIO(); t.save(b, "JPEG", quality=88); out.append(("image/jpeg", b.getvalue()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--readers", default="openrouter:openai/gpt-6-luna:low,openrouter:openai/gpt-6.1-terra:medium"); ap.add_argument("--budget", type=float, default=2.0)
    a = ap.parse_args()
    labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
    cases = sorted(labels); loaded = {c: load_case(bench.ensure_case(c)) for c in cases}
    jobs = [(s, v, c) for s in a.readers.split(",") for v in ("none", "full", "tiles") for c in cases]
    spent = [0.0]; rows = collections.defaultdict(list); meta_ = collections.defaultdict(list)
    def run(j):
        s, v, c = j
        if spent[0] >= a.budget:
            return j, None
        case = copy.copy(loaded[c]); sp = readers.parse_spec(s)
        if v == "none":
            case.image_blobs = []; sp = readers.Spec(sp.provider, sp.model, sp.effort, image=False)
        elif v == "tiles":
            case.image_blobs = list(loaded[c].image_blobs) + [t for p in loaded[c].images for t in tiles(p)]
        for _ in range(2):
            try:
                est, meta = readers.read(case, sp)
                spent[0] += (meta.get("usage") or {}).get("cost") or 0
                return j, (est, meta)
            except Exception as e:  # noqa: BLE001
                err = repr(e)[:100]
        print("  FAILED", s, v, c, err); return j, None
    with ThreadPoolExecutor(8) as ex:
        for f in as_completed([ex.submit(run, j) for j in jobs]):
            (s, v, c), r = f.result()
            if not r:
                continue
            est, meta = r
            for x in engine.compute(est):
                ln = x.index + 1
                if ln in labels[c]:
                    sc = bench.score_line(dict(a=x.a, b=x.b, t_median=x.m, q=x.q), labels[c][ln], anns.get(c, {}).get(str(ln), {})); sc["case"] = c
                    rows[(s, v)].append(sc)
            meta_[(s, v)].append((meta["latency_s"], (meta.get("usage") or {}).get("cost") or 0, (meta.get("usage") or {}).get("prompt_tokens") or 0))
    print(f"cases {cases}; spent ${spent[0]:.3f}")
    print(f"{'reader':34s}{'photo':7s}{'n':>3s}{'b_regret':>9s}{'b_score':>8s}{'a_score':>8s}{'bias':>6s}{'|bias|':>7s}{'lat s':>7s}{'$/case':>8s}{'prompt tok':>11s}  b_regret w/o cases 7-8")
    for k in sorted(rows):
        s = bench.summarize(rows[k]); s2 = bench.summarize([r for r in rows[k] if r["case"] not in ("case_007", "case_008")]); m = meta_[k]
        print(f"{k[0].split(':')[1]:34s}{k[1]:7s}{s['n']:>3d}{s['b_regret']!s:>9s}{s['b_score']!s:>8s}{s['a_score']!s:>8s}{s['bias']!s:>6s}{s['abs_bias']!s:>7s}"
              f"{st.mean(x[0] for x in m):>7.0f}{st.mean(x[1] for x in m):>8.3f}{st.mean(x[2] for x in m):>11.0f}  {s2['b_regret']}")


if __name__ == "__main__":
    main()
