"""Is document parsing a bottleneck? Time, size and correctness of claimbot's case loading on the decrypted cases, and how much of the
model latency depends on the input size.   uv run --with pyzipper python research/bench/parse_profile.py
"""
import glob, importlib.util, json, re, statistics as st, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from pypdf import PdfReader
from claimbot.case import load_case
from claimbot_fable import engine
from claimbot_fable.schema import ReaderCase

cases = sorted(p for p in (ROOT / "runs/bench/cases").iterdir() if (p / "policy.txt").exists())
saved = {}
for f in sorted(glob.glob(str(ROOT / "runs/bench/fable_eval/*.json"))):
    for r in json.load(open(f))["answers"]:
        saved[(r["reader"], r["case"])] = r
print(f"{'case':9s}{'load_case s':>12s}{'pdftotext s':>12s}{'pypdf s':>9s}{'policy KB':>10s}{'~tok policy':>12s}{'~tok invoice':>13s}{'pages':>6s}{'POS parsed':>11s}{'reader lines':>13s}  invoice text sample")
rows = []
for c in cases:
    t0 = time.perf_counter(); case = load_case(c); t_load = time.perf_counter() - t0
    inv = next(c.glob("invoice*.pdf"))
    t0 = time.perf_counter(); subprocess.run(["pdftotext", "-layout", str(inv), "-"], capture_output=True); t_pt = time.perf_counter() - t0
    t0 = time.perf_counter(); txt = "\n".join((p.extract_text() or "") for p in PdfReader(str(inv)).pages); t_py = time.perf_counter() - t0
    pos = engine.printed_positions(case.invoice_text)
    rl = len(saved[("openrouter:openai/gpt-6.1-terra:medium", c.name)]["est"]["lines"]) if ("openrouter:openai/gpt-6.1-terra:medium", c.name) in saved else None
    npages = len(PdfReader(str(inv)).pages)
    sample = re.sub(r"\s+", " ", case.invoice_text.split("ITEMS")[-1])[:60]
    rows.append((c.name, t_load, t_pt, t_py, len(case.policy), len(case.invoice_text)))
    print(f"{c.name:9s}{t_load:12.2f}{t_pt:12.3f}{t_py:9.3f}{len(case.policy)/1000:10.0f}{len(case.policy)//4:12d}{len(case.invoice_text)//4:13d}{npages:6d}{str(pos):>11s}{str(rl):>13s}  {sample}")
print(f"\nmean load_case {st.mean(r[1] for r in rows):.2f}s (includes photo downscale), pdftotext {st.mean(r[2] for r in rows)*1000:.0f} ms, pypdf {st.mean(r[3] for r in rows)*1000:.0f} ms")
print(f"policy share of the prompt: {st.mean(r[4]/(r[4]+r[5]) for r in rows):.1%} of characters")
# model latency vs prompt size, per reader, from saved answers (OpenRouter metas)
print("\nmodel latency vs prompt tokens (saved answers):")
import numpy as np
for reader in sorted({k[0] for k in saved}):
    pts = [(r["meta"]["usage"]["prompt_tokens"], r["meta"]["latency_s"], r["meta"]["usage"].get("completion_tokens") or 0) for (rd, c), r in saved.items() if rd == reader and r["meta"].get("usage")]
    if len(pts) < 5: continue
    x, y, o = (np.array(v, float) for v in zip(*pts))
    A = np.vstack([x / 1000, o / 1000, np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    print(f"  {reader.split(':',1)[1]:45s} n={len(pts):2d} latency {y.mean():5.1f}s | per 1k input tokens {coef[0]:+.2f}s, per 1k output tokens {coef[1]:+.2f}s, base {coef[2]:.1f}s | mean in {x.mean():.0f} out {o.mean():.0f}")
