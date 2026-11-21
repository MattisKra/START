"""Freeze three prospective paired policy-first sessions, adding an exclusion check to one."""
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from claimbot import config
from claimbot.api import GameAPI
from claimbot.watch import _parse
from . import exclusions, fable_arm, policy_gate
from .__main__ import round_pair
from .trace import write_json


def main():
    api = GameAPI()
    schedule = api.list_games()
    now = datetime.now(timezone.utc)
    future = sorted((g for g in schedule if g["id"] and _parse(g["start_time"]) > now),
                    key=lambda g: _parse(g["start_time"]))[:3]
    if len(future) != 3:
        raise ValueError("Three future releases required")
    games = [{k: g[k] for k in ("id", "start_time")} for g in future]
    root = config.RUNS_DIR / "shadow" / now.strftime("exclusions-%Y%m%dT%H%M%S%fZ")
    root.mkdir(parents=True)
    write_json(root / "manifest.json", dict(
        frozen_at=now.isoformat(), games=games, model=fable_arm.MODEL, tools=fable_arm.TOOLS,
        control_prompt=fable_arm.PROMPT + policy_gate.INSTRUCTION, treatment_addition=exclusions.INSTRUCTION,
        source_sha256={m.__name__: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
                       for m in (fable_arm, policy_gate, exclusions)},
        primary="Latest complete receipt by 54 seconds, treatment minus policy-first net EUR on fixed field",
        secondary="First and 60s decisions, per-role and per-line bounds, false exclusions and restorations, "
                  "evidence for endorsement status, control spontaneous checks, verified reads, timing and misses",
        population="All three games including unchanged actions. Unpaired receipts unscored and counted as misses. "
                   "Record missing evidence without dropping otherwise valid decisions."))
    print(root, flush=True)
    for game in games:
        folder = root / str(game["id"])
        try:
            round_pair(api, game, folder, {"policy_first": fable_arm.run_policy_first, "exclusions": exclusions.run})
        except Exception as exc:
            write_json(folder / "error.json", dict(exception=type(exc).__name__, detail=str(exc)[:500]))


if __name__ == "__main__":
    main()
