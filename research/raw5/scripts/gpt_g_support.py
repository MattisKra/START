"""Shared, read-only helpers for the independent evaluator audit."""

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
US = "Kiebler Software Solutions"
sys.dont_write_bytecode = True


def import_file(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPLAY = "research/bench/euro_replay.py"
er = import_file(REPLAY, "er")


def core_patch():
    """Patch exact-price logic in memory. The cent-input assumption still applies."""
    source = (ROOT / REPLAY).read_text()
    edits = {
        '("inflated" if (zero_rej or x >= c_lo) else "unknown")':
            '("inflated" if zero_rej else "unknown")',
        'cost_hi += 4 * max(U if U < INF else L, floor, 1.0)   # unidentified exposure, heuristic ceiling':
            'cost_hi += b_c  # acceptance requires a <= b_c, and payment <= a',
        'ident += 1                          # rejected for sure, inflated: costs 0':
            'pr = _rej_pay(x, L, U, Ai["status"])\n'
            '                cost_hi += pr[1]  # only the uncapped a == x branch can be fair\n'
            '                ident += int(pr[1] == 0)',
        'for ln, (a, b) in policy.items():\n        if ln not in lines:\n            continue':
            'if policy.keys() - lines.keys():\n'
            '        raise ValueError("policy contains unknown line indices")\n'
            '    for ln in lines:\n'
            '        a, b = policy.get(ln, (0.0, 0.0))\n'
            '        if not all(math.isfinite(v) and v >= 0 for v in (a, b)):\n'
            '            raise ValueError("charge and limit must be finite and nonnegative")',
    }
    for old, new in edits.items():
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    return source


def patched_module():
    spec = importlib.util.spec_from_loader("patched", loader=None)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(ROOT / REPLAY)
    exec(compile(core_patch(), REPLAY, "exec"), module.__dict__)
    return module
