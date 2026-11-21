"""Freeze three future releases for the technician-hours and equipment-days comparison."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from claimbot import config
from claimbot.api import GameAPI
from claimbot.watch import _parse
from . import fable_arm, time_components
from .__main__ import round_pair
from .trace import write_json


def main(reuse):
    api = GameAPI()
    schedule = api.list_games()
    now = datetime.now(timezone.utc)
    future = sorted((g for g in schedule if g['id'] and _parse(g['start_time']) > now),
                    key=lambda g: _parse(g['start_time']))[:3]
    if len(future) != 3:
        raise ValueError("Three future games required")
    controls = {}
    if reuse:
        previous = json.loads((reuse / "manifest.json").read_text())
        if previous["control_prompt"] != fable_arm.PROMPT or previous["model"] != fable_arm.MODEL or previous["tools"] != fable_arm.TOOLS:
            raise ValueError("Control configuration differs")
        controls = {(g['id'], g['start_time']): g['control_dir'] for g in previous['games']}
    root = config.RUNS_DIR / 'shadow' / now.strftime('time-components-%Y%m%dT%H%M%S%fZ')
    root.mkdir(parents=True)
    games = [dict(id=g['id'], start_time=g['start_time'],
                  control_dir=controls.get((g['id'], g['start_time']), str(root / str(g['id'])))) for g in future]
    write_json(root / 'manifest.json', dict(frozen_at=now.isoformat(), games=games, model=fable_arm.MODEL,
               tools=fable_arm.TOOLS, control_prompt=fable_arm.PROMPT, treatment_addition=time_components.INSTRUCTION,
               source_sha256={m.__name__: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
                              for m in (fable_arm, time_components)},
               primary="Whole-invoice net change at 54 s, treatment minus standard Fable, fixed opposing field",
               secondary="Both roles at 54 and 60 s, first and final timing, predeclared invoice time slice, "
                         "line-level components, arithmetic, coverage, unchanged decisions and missing receipts"))
    print(root, flush=True)
    for g in games:
        folder = root / str(g['id'])
        arms = {'time_components': time_components.run}
        if Path(g['control_dir']).resolve() == folder.resolve():
            arms['fable'] = fable_arm.run
        try:
            round_pair(api, g, folder, arms)
        except Exception as exc:
            write_json(folder / 'error.json', dict(error=str(exc), exception=type(exc).__name__))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-policy-first', type=Path)
    main(parser.parse_args().reuse_policy_first)
