import argparse
import json
import math
import os
from pathlib import Path
from time import monotonic
from uuid import uuid4

from claimbot import config
from claimbot.case import load_case
from claimbot_fable.readers import parse_spec
from claimbot_fable.runner import LAST_SUBMIT, default_specs

from .runner import estimate


def main():
    parser = argparse.ArgumentParser(description="Estimate or compare archived cases locally.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["estimate", "shadow", "compare"]:
        p = commands.add_parser(name)
        p.add_argument("cases", type=Path, nargs="+" if name == "compare" else 1)
        p.add_argument("--reader", help="provider:model:effort[:noimage]")
        p.add_argument("--history", action="store_true")
        p.add_argument("--web", action="store_true", help="Enable optional Brave price lookups")
        p.add_argument("--seconds", type=float, default=LAST_SUBMIT)
        p.add_argument("--tokens", type=int, default=12000, help="Total specialist output token ceiling per case")
        if name == "shadow":
            p.add_argument("--fallback", help="Fast full-case reader spec")
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0 or args.tokens < 300:
        parser.error("provide positive finite seconds and at least 300 output tokens")
    if args.web and not os.getenv("BRAVE_SEARCH_API_KEY"):
        parser.error("--web requires BRAVE_SEARCH_API_KEY")
    specs = default_specs()
    spec = parse_spec(args.reader) if args.reader else specs["main"]
    fast = None
    if args.command == "shadow":
        fast = parse_spec(args.fallback) if args.fallback else specs.get("fast", spec)
    folder = config.RUNS_DIR / "multiagent"
    folder.mkdir(parents=True, exist_ok=True)
    success = True
    records = []
    for directory in sorted(args.cases):
        for count in ([1, 2, 3] if args.command == "compare" else [2]):
            started = monotonic()
            case = load_case(directory)
            record = estimate(case, spec=spec, count=count, fast=fast, history=args.history, web=args.web,
                              seconds=max(0, args.seconds - (monotonic() - started)), budget=args.tokens)
            record.update(reader=spec.name, total_elapsed_s=round(monotonic() - started, 3))
            path = folder / f"{directory.name}_{count}_{uuid4().hex[:12]}.json"
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
            print(json.dumps({k: record[k] for k in ["case", "architecture", "winner", "payload", "errors",
                                                       "total_elapsed_s"]}), flush=True)
            print(f"Log: {path}", flush=True)
            records.append(record)
            success &= record["payload"] is not None
    if args.command == "compare":
        from .report import summarize
        print(json.dumps(summarize(records), indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
