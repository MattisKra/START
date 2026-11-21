"""Run tool-enabled Fable alongside the remaining games of a frozen comparison."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from claimbot.api import GameAPI
from claimbot.watch import _parse
from . import fable_arm
from .__main__ import round_pair
from .trace import write_json


def run(frozen):
    now = datetime.now(timezone.utc)
    games = [g for g in json.loads((frozen / "manifest.json").read_text())["games"]
             if _parse(g["start_time"]) > now]
    if not games:
        raise SystemExit("No future games in this manifest")
    folder = frozen / "verified-fable"
    folder.mkdir()
    write_json(folder / "manifest.json", dict(frozen_at=now.isoformat(), games=games,
                                              model=fable_arm.MODEL, tools=fable_arm.TOOLS,
                                              prompt=fable_arm.PROMPT))
    api = GameAPI()
    for game in games:
        dest = folder / str(game["id"])
        try:
            round_pair(api, game, dest, {"fable": fable_arm.run})
        except Exception as exc:
            write_json(dest / "error.json", dict(exception=type(exc).__name__, detail=str(exc)[:500]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frozen_run", type=Path)
    run(parser.parse_args().frozen_run)
