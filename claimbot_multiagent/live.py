"""Live round for the multi-agent estimator: decrypt, estimate with the parallel fast fallback, submit.

Used by `claimbot watch` when CLAIMS_ENGINE=multiagent. The fast fallback reader's complete answer is submitted as soon
as it arrives; the coordinator's final selection (specialist, mixed or fallback) overwrites it. The price references of
finished games (claimbot/refs.py) are appended to the description unless CLAIMS_PRICE_REFS=0.
"""

import json
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from claimbot import config, outputs
from claimbot.api import GameAPI
from claimbot.case import extract_zip, load_case
from claimbot_fable import readers
from claimbot_fable.runner import LAST_SUBMIT, default_specs

from .runner import estimate, settle
from .settlement import invoice_items


def _put(api: GameAPI, game_id, payload: list[dict]) -> None:
    body = [{"index": p["index"], "charge_price": round(p["charge_price"], 2),
             "acceptance_limit": round(p["acceptance_limit"], 2)} for p in payload]
    r = api.s.put(f"{api.base}/api/games/{game_id}/submissions", json=body, timeout=10)
    r.raise_for_status()


def play_round(game_id: str, zip_path: Path, key: str | None = None, dry_run: bool = False) -> None:
    api = GameAPI()
    t0 = time.monotonic()
    if key is None:
        key = api.get_key(game_id)
    case_dir = extract_zip(Path(zip_path), key, config.WORK_DIR / f"game_{game_id}")
    case = load_case(case_dir)
    items = invoice_items(case.invoice_text)
    ref_text = ""
    try:
        from claimbot import refs
        ref_text = refs.block(exclude_game=game_id, case=case)
    except Exception as e:  # noqa: BLE001 - references are optional
        print(f"refs: not used ({e!r})")
    # case_NNN as the directory name lets the history retrieval know which archived cases are earlier
    work = replace(case, case_dir=config.ROOT / "past-cases" / f"case_{int(game_id):03d}",
                   description=case.description + ("\n\n" + ref_text if ref_text else ""))
    specs = default_specs()
    spec, fast = specs["main"], specs.get("fast")
    print(f"[{time.monotonic() - t0:5.1f}s] case loaded: {case_dir} ({len(items)} lines), reader {spec.name}, "
          f"fallback {fast.name if fast else 'none'}")

    def send(tag: str, payload: list[dict]) -> None:
        stamp = f"[{time.monotonic() - t0:5.1f}s] {tag}"
        if dry_run:
            print(f"{stamp}: dry run")
            return
        try:
            _put(api, game_id, payload)
            print(f"{stamp}: submitted {len(payload)} lines")
        except Exception as e:  # noqa: BLE001
            print(f"{stamp}: SUBMIT FAILED {e!r}")

    def call(c, s, fast=False, **kw):
        answer, meta = readers.read(c, s, fast=fast, **kw)
        if fast:  # the fallback's complete answer goes out at once, as a safety submission
            try:
                send("fallback", settle(items, answer))
            except Exception as e:  # noqa: BLE001
                print(f"fallback answer not submittable: {e!r}")
        return answer, meta

    seconds = min(LAST_SUBMIT, config.ROUND_SECONDS - config.SAFETY_MARGIN_S) - (time.monotonic() - t0)
    record = estimate(work, spec=spec, count=2, fast=fast, history=True, web=False, seconds=seconds, call=call)
    payload = record["payload"]
    if payload:
        send(f"final ({record['winner']})", payload)
    else:
        print(f"[{time.monotonic() - t0:5.1f}s] NO PAYLOAD: errors {record['errors']}, timed out {record.get('timed_out')}")
    if record["errors"] or record.get("fallback_reasons"):
        print(f"  errors {record['errors']}; fallback lines {record.get('fallback_reasons')}")
    by_pos = {i.position: i for i in items}
    print(f"\n  #      q       t_med           a           b  item")
    for p in payload or []:
        print(f"{p['index']:3d}   {p['probability']:4.2f}  {p['median']:10.2f}  {p['charge_price']:10.2f}  "
              f"{p['acceptance_limit']:10.2f}  {by_pos[p['index']].description[:55]}")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    record.update(game=game_id, reader=spec.name, fallback=fast.name if fast else None, refs=ref_text, dry_run=dry_run)
    log = config.RUNS_DIR / f"{stamp}_game{game_id}_multiagent.json"
    log.write_text(json.dumps(record, indent=1, ensure_ascii=False, default=str))
    print(f"log: {log}")
    if payload and not dry_run and str(game_id) != "0":
        try:  # same shape as the ensemble entries, so refs.py and the analysis scripts keep working
            lines = [dict(index=p["index"] - 1, invoice_text=by_pos[p["index"]].description,
                          quantity_invoiced=by_pos[p["index"]].quantity, unit=by_pos[p["index"]].unit,
                          p_valid=p["probability"]) for p in payload]
            submitted = [dict(index=p["index"] - 1, q=p["probability"], t_median=p["median"],
                              a=p["charge_price"], b=p["acceptance_limit"]) for p in payload]
            member = dict(member=f"multiagent:{spec.name}", weight=1.0, meta=dict(winner=record["winner"]),
                          estimate=dict(lines=lines), prices=submitted)
            outputs.record(game_id, [member], [], record.get("timed_out", []), submitted)
            print(f"outputs: game {game_id} written to {outputs.OUTPUTS_FILE}")
        except Exception as e:  # noqa: BLE001
            print(f"outputs: not written ({e!r})")
