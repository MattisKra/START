"""Tournament loop: wait for each game's start, fetch the key, play the round.

Game N is played with cases/case_{N:03d}.zip.
"""

import time
import traceback
from datetime import datetime, timezone

import requests

from . import config
from .api import GameAPI
from .runner import play_round, play_round_ensemble


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _parse(t: str) -> datetime:
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def _wait_for_key(api: GameAPI, game_id: int, start: datetime) -> str | None:
    """Sleep until start, then poll the key (403 = not started) for up to 30 s."""
    def left() -> float:
        return (start - datetime.now(timezone.utc)).total_seconds()

    if left() > 5:
        time.sleep(left() - 5)
    for n in range(5, 0, -1):  # countdown over the last 5 seconds
        if left() > n:
            time.sleep(left() - n)
        if left() > n - 1:
            print(f"{_ts()} game {game_id}: starts in {n}")
    if left() > 0:
        time.sleep(left())
    give_up = time.monotonic() + 30
    while time.monotonic() < give_up:
        try:
            return api.get_key(game_id)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            if code != 403:
                print(f"{_ts()} game {game_id}: key error {code}: {e}")
        except requests.RequestException as e:
            print(f"{_ts()} game {game_id}: key request failed: {e!r}")
        time.sleep(0.5)
    return None


def watch() -> None:
    api = GameAPI()
    done: set[int] = set()
    if config.USE_ENSEMBLE:
        from .ensemble import members
        print(f"{_ts()} watching for games (ensemble: {', '.join(m.name for m in members())})")
    else:
        print(f"{_ts()} watching for games (model {config.MODEL}, efforts {config.FAST_EFFORT}/{config.EFFORT})")
    mem = None
    if config.MEMORY:
        try:
            from . import memory
            mem = memory.get()
            mem.warm()  # embedding model loaded now, not in the first live round
            st = mem.state
            print(f"{_ts()} memory ON: build {st.name if st else 'none'} ({len(st.entries) if st else 0} entries), "
                  f"budget {config.MEMORY_BUDGET_S}s")
        except Exception as e:  # noqa: BLE001 - play without memory
            print(f"{_ts()} memory: could not start ({e!r}); playing without it")
            mem = None
    while True:
        try:
            games = api.list_games()
        except Exception as e:  # noqa: BLE001
            print(f"{_ts()} list failed: {e!r}")
            time.sleep(10)
            continue
        now = datetime.now(timezone.utc)
        upcoming = sorted(
            ((g["id"], _parse(g["start_time"])) for g in games if g["id"] != 0 and g["id"] not in done),
            key=lambda x: x[1],
        )
        # Skip games whose minute is already over.
        upcoming = [(gid, st) for gid, st in upcoming if (now - st).total_seconds() < config.ROUND_SECONDS - 15]
        if not upcoming:
            print(f"{_ts()} no upcoming games; checking again in 60 s")
            time.sleep(60)
            continue
        gid, start = upcoming[0]
        wait_s = (start - now).total_seconds()
        if wait_s > 90:
            m, sec = divmod(int(round(wait_s)), 60)
            print(f"{_ts()} next: game {gid} at {start.astimezone():%H:%M:%S} (in {m}m {sec:02d}s)")
            time.sleep(min(wait_s - 60, 60))  # one status line per minute; re-checks the game list
            continue
        zip_path = config.CASES_DIR / f"case_{gid:03d}.zip"
        done.add(gid)
        if not zip_path.exists():
            print(f"{_ts()} game {gid}: MISSING {zip_path}")
            continue
        if mem is not None:
            mem.maybe_reload()  # between rounds: pick up the build made after the previous game
        print(f"{_ts()} game {gid}: waiting for start at {start.astimezone():%H:%M:%S} (in {max(wait_s, 0):.0f}s)")
        key = _wait_for_key(api, gid, start)
        if key is None:
            print(f"{_ts()} game {gid}: NO KEY after 30 s, skipping")
            continue
        try:
            if config.USE_ENSEMBLE:
                play_round_ensemble(str(gid), zip_path, key=key)
            else:
                play_round(str(gid), zip_path, key=key)
        except Exception:  # noqa: BLE001 - never let one round kill the loop
            print(f"{_ts()} game {gid}: ROUND FAILED\n{traceback.format_exc()}")
