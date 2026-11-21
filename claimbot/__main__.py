"""CLI.

    uv run python -m claimbot estimate CASE_DIR_OR_ZIP [--password PW] [--effort medium]
    uv run python -m claimbot round GAME_ID --zip cases/case_17.zip [--dry-run]
    uv run python -m claimbot games
    uv run python -m claimbot watch
    uv run python -m claimbot archive [--once]
    uv run python -m claimbot ensemble CASE_DIR_OR_ZIP [--password PW]
    uv run python -m claimbot memory build [--until N] [--out DIR] [--labels own|leaderboard] [--no-llm]
    uv run python -m claimbot memory refresh [--pull] [--loop 120]       (live machine: keep the memory current)
    uv run python -m claimbot memory prompts [--until N] / memory import   (enrichment by hand in a chat UI)
    uv run python -m claimbot memory query CASE_DIR [--exclude 2,3] [--until N] [--build DIR] [--parts warnings,neighbours]
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

    en = sub.add_parser("ensemble", help="run the model ensemble on a local case, no submission")
    en.add_argument("path")
    en.add_argument("--password")

    sub.add_parser("games", help="list games")
    sub.add_parser("watch", help="play every upcoming game automatically")
    ar = sub.add_parser("archive", help="decrypt every released case into past-cases/ (never submits)")
    ar.add_argument("--once", action="store_true", help="backfill released cases and exit")
    ar.add_argument("--no-push", action="store_true", help="do not commit/push past-cases/ to origin/main")

    mem = sub.add_parser("memory", help="case memory: build from past-cases/, or query it for a case")
    msub = mem.add_subparsers(dest="mcmd", required=True)
    mb = msub.add_parser("build", help="build (and activate) a memory from past-cases/")
    mb.add_argument("--until", type=int, help="only games <= N (forward evaluation)")
    mb.add_argument("--out", help="write the build here and do NOT activate it (benchmarks)")
    mb.add_argument("--labels", choices=["own", "leaderboard"], default=None,
                    help="leaderboard (default, CLAIMS_MEMORY_LABELS) = own rows plus brackets from all teams' public rows; own = our rows only")
    mb.add_argument("--no-llm", action="store_true", help="no enrichment call: entries without hypotheses")
    mx = msub.add_parser("prompts", help="write one paste-ready enrichment prompt per case (ChatGPT / claude.ai)")
    mx.add_argument("--until", type=int)
    mx.add_argument("--all", action="store_true", help="also cases that already have a cached answer")
    mi = msub.add_parser("import", help="read the chat answers (case_NNN.answer.json) into the enrichment cache")
    mi.add_argument("--source", default="chatgpt-manual", help="recorded as the model of these answers")
    mr = msub.add_parser("refresh", help="labels + rebuild only if inputs changed (run next to the live watch bot)")
    mr.add_argument("--pull", action="store_true", help="git pull --ff-only first (past-cases/ from the archive machine)")
    mr.add_argument("--loop", type=float, default=0, help="repeat every N seconds (0 = once)")
    mq = msub.add_parser("query", help="print the hint block the memory gives for a case")
    mq.add_argument("path")
    mq.add_argument("--password")
    mq.add_argument("--exclude", default="", help="games to leave out, e.g. 2,3,4,5")
    mq.add_argument("--until", type=int, help="only games <= N (default for past-cases/case_NNN: N-1)")
    mq.add_argument("--build", help="build directory (default: CURRENT)")
    mq.add_argument("--parts", default="warnings,neighbours")

    args = ap.parse_args()
    if args.cmd == "estimate":
        from .runner import run_local
        run_local(args.path, args.password, args.effort)
    elif args.cmd == "round":
        from .runner import play_round, play_round_ensemble
        (play_round_ensemble if config.USE_ENSEMBLE else play_round)(args.game_id, args.zip, args.dry_run)
    elif args.cmd == "ensemble":
        from .runner import run_local_ensemble
        run_local_ensemble(args.path, args.password)
    elif args.cmd == "watch":
        from .watch import watch
        watch()
    elif args.cmd == "archive":
        from .archive import archive_loop
        archive_loop(once=args.once, push=not args.no_push)
    elif args.cmd == "memory":
        _memory_cmd(args)
    elif args.cmd == "games":
        from .api import GameAPI
        print(json.dumps(GameAPI().list_games(), indent=2))


def _memory_cmd(args) -> None:
    from pathlib import Path
    if args.mcmd == "build":
        from .memory_build import build
        build(until=args.until, out=Path(args.out) if args.out else None, labels=args.labels, use_llm=not args.no_llm)
        return
    if args.mcmd == "prompts":
        from .memory_build import MANUAL_DIR, manual_export
        files = manual_export(until=args.until, only_missing=not args.all)
        print("\n".join(str(f.relative_to(config.ROOT)) for f in files) or "(every case already has a cached answer)")
        print(f"\nPaste each file into the chat, save its reply as {MANUAL_DIR.relative_to(config.ROOT)}/case_NNN.answer.json, "
              "then: claimbot memory import && claimbot memory build")
        return
    if args.mcmd == "refresh":
        import time
        from datetime import datetime
        from .memory_build import refresh
        while True:
            try:
                print(f"{datetime.now():%H:%M:%S} {refresh(pull=args.pull)}", flush=True)
            except Exception as e:  # noqa: BLE001 - keep looping; the live bot keeps the last good build
                print(f"{datetime.now():%H:%M:%S} refresh FAILED {e!r}", flush=True)
            if not args.loop:
                return
            time.sleep(args.loop)
    if args.mcmd == "import":
        from .memory_build import manual_import
        print("\n".join(manual_import(source=args.source)) or "(no case_NNN.answer.json found)")
        return
    from . import memory
    from .case import extract_zip, load_case
    path = Path(args.path)
    if path.suffix.lower() == ".zip":
        if not args.password:
            raise SystemExit("--password is required for a zip")
        path = extract_zip(path, args.password, config.WORK_DIR / path.stem)
    m = memory.Memory()
    if not m.load(Path(args.build) if args.build else None):
        raise SystemExit("no memory build (run: claimbot memory build)")
    until = args.until
    g = memory.game_of(path)
    if until is None and g is not None:
        until = g - 1  # never let a past case see itself or later games
    excl = [int(x) for x in args.exclude.split(",") if x.strip()]
    case = load_case(path)
    m.warm()
    res = m.query(case, exclude_games=excl, until=until, parts=tuple(args.parts.split(",")))
    print(f"build {res.get('build')}  status {res['status']}  {res['ms']} ms  embeddings {res.get('embed')}  until {until}  exclude {excl}")
    for h in res.get("hits", []):
        print(f"  line {h['line']} <- game {h['game']} line {h['entry_line']}: score {h['score']} (cos {h['cos']}, bm25 {h['bm25']}, clause {h['clause']})")
    print("\n" + (res.get("block") or "(no hint block)"))


if __name__ == "__main__":
    main()
