"""Pair a policy-first Fable with the standard tool-enabled Fable on future releases."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from claimbot import config
from claimbot.api import GameAPI
from claimbot.watch import _parse
from . import fable_arm, policy_gate
from .__main__ import round_pair
from .trace import write_json


def start(reuse):
    api = GameAPI()
    schedule = api.list_games()
    now = datetime.now(timezone.utc)
    future = sorted((g for g in schedule if g["id"] and _parse(g["start_time"]) > now),
                    key=lambda g: _parse(g["start_time"]))[:3]
    if not future:
        raise ValueError("No future releases")
    prior = json.loads((reuse / "manifest.json").read_text())["games"] if reuse else []
    controls = {(g["id"], g["start_time"]): g["fable_dir"] for g in prior}
    root = config.RUNS_DIR / "shadow" / now.strftime("policy-first-%Y%m%dT%H%M%S%fZ")
    root.mkdir(parents=True)
    games = [dict(id=g["id"], start_time=g["start_time"],
                  control_dir=controls.get((g["id"], g["start_time"]), str(root / str(g["id"]))))
             for g in future]
    write_json(root / "manifest.json", dict(frozen_at=now.isoformat(), games=games, model=fable_arm.MODEL,
               tools=fable_arm.TOOLS, control_prompt=fable_arm.PROMPT, treatment_addition=policy_gate.INSTRUCTION,
               gate_sha256=hashlib.sha256(Path(policy_gate.__file__).read_bytes()).hexdigest(),
               primary="Last complete paired receipts by 54 s, policy-first minus standard net EUR on fixed field",
               secondary="First complete decisions and last by 60 s; separate issuer/reviewer bounds, misses, "
                         "read-before-write order, exact clause, per-line action and payable probability changes"))
    print(root, flush=True)
    for g in games:
        folder = root / str(g["id"])
        arms = {"policy_first": fable_arm.run_policy_first}
        if Path(g["control_dir"]).resolve() == folder.resolve():
            arms["fable"] = fable_arm.run
        try:
            round_pair(api, g, folder, arms)
        except Exception as exc:
            write_json(folder / "error.json", dict(error=str(exc), exception=type(exc).__name__))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-hybrid", type=Path, help="Use the tool-enabled Fable controls in this hybrid run")
    start(parser.parse_args().reuse_hybrid)
