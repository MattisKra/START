"""Replay the evaluator's candidate sweep with its import-time credential load removed."""

import ast
from collections import Counter
import contextlib
import io
import sys
from types import SimpleNamespace

from gpt_g_support import ROOT, US, er, patched_module

sys.path.insert(0, str(ROOT))
from claimbot_fable import engine  # noqa: E402
from claimbot_fable.schema import ReaderCase  # noqa: E402


def isolated_saved():
    # Importing arch_bench normally imports bench.py, which reads .env.
    # Execute only the exact reader IDs and the saved-answer loader.
    import glob
    import json
    path = ROOT / "research/bench/arch_bench.py"
    nodes = ast.parse(path.read_text()).body
    keep = [n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == "load_saved"
            or isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Tuple)
            and tuple(x.id for x in n.targets[0].elts) == ("LUNA", "TERRA", "FABLE")]
    env = dict(ROOT=ROOT, json=json, glob=glob)
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(path), "exec"), env)
    return SimpleNamespace(**env, engine=engine)


def sweep(field, oracle):
    path = ROOT / "research/bench/euro_eval.py"
    nodes = ast.parse(path.read_text()).body
    # Preserve the evaluator from field loading onward, including the exact sweep.
    start = next(i for i, n in enumerate(nodes) if isinstance(n, ast.Assign)
                 and isinstance(n.targets[0], ast.Tuple)
                 and n.targets[0].elts[0].id == "field_dir")
    import json
    import sys
    ab = isolated_saved()
    env = dict(ROOT=ROOT, er=oracle, ab=ab, engine=engine, ReaderCase=ReaderCase,
               sys=SimpleNamespace(argv=[str(path), field, "--us", US]), json=json)
    captured = {}

    def capture(frame, event, arg):
        if event == "call" and frame.f_code.co_name == "evaluate":
            captured[frame.f_locals["name"]] = frame.f_locals["policies"]

    with contextlib.redirect_stdout(io.StringIO()) as output:
        sys.setprofile(capture)
        try:
            exec(compile(ast.Module(body=nodes[start:], type_ignores=[]), str(path), "exec"), env)
        finally:
            sys.setprofile(None)
    rec = env["rec"]
    scored = {}
    exposure = Counter()
    for name, policies in captured.items():
        scored[name] = {}
        for g, policy in policies.items():
            assert policy.keys() == rec[g][0].keys(), (name, g)
            lo, hi, _ = oracle.game_value(rec[g][0], US, policy)
            scored[name][g] = (lo - rec[g][2], hi - rec[g][2])
            if oracle is er:
                for ln, (_, b) in policy.items():
                    line = rec[g][0][ln]
                    for issuer, a in line["A"].items():
                        if issuer == US or a["a"] is not None:
                            continue
                        floor = max([bb["lo"] for reviewer, bb in line["B"].items()
                                     if reviewer != issuer] + [line["our_b"]])
                        if b > floor:
                            ceiling = 4 * max(line["U"] if line["U"] < er.INF else line["L"],
                                              floor, 1.0)
                            key = "old below b" if ceiling < b else "old above b" if ceiling > b else "equal"
                            exposure[key] += 1
    if exposure:
        print("heuristic branches across evaluator invocations, including repeated policies:", dict(exposure))
    return output.getvalue(), scored, {g: v[2] for g, v in rec.items()}


def sum_delta(by_game, games):
    return tuple(round(sum(by_game[g][i] for g in games), 2) for i in (0, 1))


if __name__ == "__main__":
    before, old, actual = sweep(sys.argv[1], er)
    _, core, _ = sweep(sys.argv[1], patched_module())
    print(before)
    print("our actual early and late subtotals:", sum(actual[g] for g in range(1, 7)),
          sum(actual[g] for g in (7, 8)))
    for name, by_game in core.items():
        if name.startswith("ACTUAL") or name.startswith("luna") or name.startswith("terra"):
            print(name, "old all", sum_delta(old[name], actual), "core all", sum_delta(by_game, actual),
                  "core g1-6", sum_delta(by_game, range(1, 7)), "core g7-8", sum_delta(by_game, (7, 8)))
