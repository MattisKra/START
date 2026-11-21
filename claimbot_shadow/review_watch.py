"""Freeze three future games to measure incremental, same-session Fable reviews."""
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from claimbot import config
from claimbot.api import GameAPI
from claimbot.watch import _parse
from . import fable_arm, policy_gate, review_turns
from .__main__ import round_pair
from .trace import write_json


def main():
    api = GameAPI()
    schedule = api.list_games()
    now = datetime.now(timezone.utc)
    future = sorted((g for g in schedule if g["id"] and _parse(g["start_time"]) > now),
                    key=lambda g: _parse(g["start_time"]))[:3]
    if len(future) != 3:
        raise ValueError("Three future releases are required")
    games = [{k: g[k] for k in ("id", "start_time")} for g in future]
    root = config.RUNS_DIR / "shadow" / now.strftime("reviews-%Y%m%dT%H%M%S%fZ")
    root.mkdir(parents=True)
    write_json(root / "manifest.json", dict(
        frozen_at=now.isoformat(), games=games, model=fable_arm.MODEL, tools=fable_arm.TOOLS,
        initial_prompt=fable_arm.PROMPT + policy_gate.INSTRUCTION, review_instruction=review_turns.INSTRUCTION,
        max_passes=review_turns.MAX_PASSES, start_before_s=review_turns.START_BEFORE_S,
        target="Largest remaining max(charge, limit), ties by ascending printed position",
        primary="Final receipt minus last initial-turn receipt available by 54 seconds, on the same field",
        secondary="Same comparison by 60 seconds and each individual review versus the preceding receipt",
        availability="No accepted revision retains initial decision; missing initial decision is unscored",
        source_sha256={m.__name__: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
                       for m in (fable_arm, policy_gate, review_turns)}))
    print(root, flush=True)
    for game in games:
        dest = root / str(game["id"])
        try:
            round_pair(api, game, dest, {"review": fable_arm.run_extra_reviews})
        except Exception as exc:
            write_json(dest / "error.json", dict(exception=type(exc).__name__, detail=str(exc)[:500]))


if __name__ == "__main__":
    main()
