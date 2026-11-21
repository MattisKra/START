"""Build an offline suite from our archived submissions and our own public settlements."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "runs/replay/history.json"


def build_case(game, submission, rows):
    """Choose one compatible scenario. Values on unobserved sides of decisions are assumptions."""
    team = "Kiebler Software Solutions"
    lines, opponents = [], {}
    if {r["line_item_index"] for r in rows} != {p["index"] for p in submission}:
        raise ValueError(f"game {game}: invoice index mismatch")
    for p in submission:
        i, a, b = p["index"], p["charge_price"], p["acceptance_limit"]
        outgoing = {r["reviewer"]: r for r in rows if r["line_item_index"] == i and r["issuer"] == team}
        incoming = {r["issuer"]: r for r in rows if r["line_item_index"] == i and r["reviewer"] == team}
        if not outgoing or outgoing.keys() != incoming.keys():
            raise ValueError(f"game {game}, line {i}: incomplete matchups")
        fair = max([0] + [a for r in outgoing.values() if not r["accepted"] and r["amount"] > 0]
                   + [round(r["amount"] / 1.5, 2) for r in incoming.values() if not r["accepted"] and r["amount"] > 0])
        capped = [r["amount"] for r in outgoing.values() if r["accepted"] and r["amount"] < a - 0.001]
        cap = min(capped) if capped else max([4 * fair, a] + [r["amount"] for r in incoming.values()]) + 1
        lines.append(dict(index=i, fair_value=fair, cap=cap))
        for name, issued in outgoing.items():
            reviewed = incoming[name]
            if reviewed["accepted"]:
                charge = reviewed["amount"]
            elif reviewed["amount"]:
                charge = round(reviewed["amount"] / 1.5, 2)
            else:
                charge = max(fair, b) + 1
            limit = a if issued["accepted"] else max(0, a - 0.01)
            opponents.setdefault(name, []).append(dict(index=i, charge_price=charge, acceptance_limit=limit))
    return dict(case_id=str(game), lines=lines, opponents=list(opponents.values()))


def prepare(ref):
    from replay import score
    sys.path.insert(0, str(ROOT / "research/live"))
    from lb_analyze import Source, tx_pages

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True)

    revision = git("rev-parse", "--verify", ref + "^{commit}").strip()
    paths = git("ls-tree", "-r", "--name-only", revision, "past-cases").splitlines()
    games = sorted(int(Path(p).parent.name.split("_")[1]) for p in paths if p.endswith("/results.json"))
    logs = json.loads(git("show", revision + ":outputs/model_outputs.json"))["games"]
    source = Source()
    cases = []
    for game in games:
        key = str(game)
        actual = json.loads(git("show", f"{revision}:past-cases/case_{game:03}/results.json"))
        ab = [dict(index=p["index"] + 1, charge_price=p["a"], acceptance_limit=p["b"])
              for p in logs[key]["submitted"]]
        rows = tx_pages(source, game, actual["team"])
        if not rows:
            raise ValueError(f"no settlements for game {game}")
        case = build_case(game, ab, rows)
        result = score(case, ab)
        if any(abs(result[k] - actual[k]) > 0.011 for k in ("income", "costs", "net")):
            raise ValueError(f"game {game}: baseline fails to reproduce archived settlement")
        cases.append(dict(scenario=case, baseline=ab))
    if not cases:
        raise ValueError("no scored cases in archive")
    SUITE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=SUITE.parent, delete=False) as stream:
        json.dump(dict(revision=revision, cases=cases), stream)
    os.replace(stream.name, SUITE)
    print(f"Prepared {len(cases)} cases from {revision[:8]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    prepare(parser.parse_args().ref)
