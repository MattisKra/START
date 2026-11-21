"""CLI.

    uv run python -m claimbot estimate CASE_DIR_OR_ZIP [--password PW] [--effort medium]
    uv run python -m claimbot round GAME_ID --zip cases/case_17.zip [--dry-run]
    uv run python -m claimbot games
    uv run python -m claimbot watch
"""

import argparse
import json

from . import config


def main() -> None:
    ap = argparse.ArgumentParser(prog="claimbot")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("estimate", help="estimate a local case, no submission")
    e.add_argument("path")
    e.add_argument("--password")
    e.add_argument("--effort", default=config.EFFORT)

    r = sub.add_parser("round", help="play one round: fetch key, decrypt, estimate, submit")
    r.add_argument("game_id")
    r.add_argument("--zip", required=True)
    r.add_argument("--dry-run", action="store_true")

    sub.add_parser("games", help="list games")
    sub.add_parser("watch", help="play every upcoming game automatically")

    args = ap.parse_args()
    if args.cmd == "estimate":
        from .runner import run_local
        run_local(args.path, args.password, args.effort)
    elif args.cmd == "round":
        from .runner import play_round
        play_round(args.game_id, args.zip, args.dry_run)
    elif args.cmd == "watch":
        from .watch import watch
        watch()
    elif args.cmd == "games":
        from .api import GameAPI
        print(json.dumps(GameAPI().list_games(), indent=2))


if __name__ == "__main__":
    main()
