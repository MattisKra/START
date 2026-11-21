"""Tracked record of what every model returned in each live round.

outputs/model_outputs.json holds one entry per game: the prices we submitted and, per ensemble member, its
full structured estimate, the prices that member alone would give, latency and token usage. The file is
committed and pushed from time to time; the per-run logs under runs/ stay local.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from . import config

OUTPUTS_FILE = Path(os.getenv("CLAIMS_OUTPUTS_FILE", config.RUNS_DIR.parent / "outputs" / "model_outputs.json"))
NOTE = ("Per game: 'submitted' is our final a (charge) and b (acceptance limit) per line, gross line totals. "
        "'index' is the 0-based invoice order; the API line number is index + 1. "
        "'members' holds each model's structured estimate and the prices it would give on its own.")


def record(game_id: int | str, members: list[dict], failures: list[dict], timed_out: list[str],
           prices: list[dict], played_at: str | None = None) -> None:
    """Adds or replaces the entry of one game. Written atomically."""
    data = json.loads(OUTPUTS_FILE.read_text()) if OUTPUTS_FILE.exists() else {}
    games = data.get("games", {})
    games[str(game_id)] = {
        "game": int(game_id),
        "played_at": played_at or datetime.now().astimezone().isoformat(timespec="seconds"),
        "submitted": prices,
        "members": members,
        "failures": failures,
        "timed_out": timed_out,
    }
    out = {"note": NOTE, "games": dict(sorted(games.items(), key=lambda kv: int(kv[0])))}
    OUTPUTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUTS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(OUTPUTS_FILE)
