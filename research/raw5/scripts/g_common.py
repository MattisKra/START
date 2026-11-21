"""Audit G: shared helpers (no data). Which evaluator is under test, and a field loader that refuses a folder inside the repo.

Every audit script takes  --replay PATH  = the euro_replay.py to test (default: research/bench/euro_replay.py as it is on disk now).
The version that was audited first ('as shipped') is commit 5cfdaf3:
    git show 5cfdaf3:research/bench/euro_replay.py > SCRATCH/euro_replay_shipped.py        (SCRATCH outside the repo)
"""
import importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def replay_under_test():
    p = Path(sys.argv[sys.argv.index("--replay") + 1]).resolve() if "--replay" in sys.argv else ROOT / "research/bench/euro_replay.py"
    return load("er", p), ("research/bench/euro_replay.py (on disk now)" if "--replay" not in sys.argv else f"--replay {p.name} in {p.parent.name}/")


def fixed_reference():
    return load("fx", HERE / "g_replay_fixed.py")


def load_field(dir_):
    d = Path(dir_).resolve()
    assert ROOT not in d.parents and d != ROOT, "field cache must live outside the repo"
    return {int(f.stem[4:]): json.loads(f.read_text()) for f in sorted(d.glob("tx_g*.json"), key=lambda p: int(p.stem[4:]))}
