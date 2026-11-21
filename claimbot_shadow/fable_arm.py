"""Run a restricted Claude Code process in a private copy of the released case."""
import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from claimbot import config
from .checks import check
from .trace import write_json

MODEL = "claude-fable-5-2"
TOOLS = "Read,Glob,Grep,Write,WebSearch,WebFetch"
PROMPT = """Play this insurance round as a single case owner. Read rules.md, invoice.txt,
description.txt and the relevant policy clauses. Inspect the photo or original PDF if useful.
The deadline is 60 seconds from the official release, including preparation. First write
a COMPLETE JSON array to decision.json with Write as soon as possible. Then use any time
remaining to check the most consequential uncertain line and overwrite decision.json if needed.
Each row must have integer index (printed position), charge_price and acceptance_limit
(nonnegative gross EUR for the whole line), and a short evidence string giving the case fact,
clause or assumption that drove those amounts. For a changed line, name the source and new
observation, the estimate or assumption it changes, and the numerical basis for each changed
amount. Label a judgment call when there is no quote or calculation. Keep this brief. No prose
outside the array in that file. For EACH line, report fair_median_gross_if_valid: your
independent median estimate of the expert's gross threshold for the whole line assuming
eligibility, before strategic adjustments. Also report p_valid: probability the line is
covered, related and payable. State these beliefs separately from your chosen actions.
After each write the recorder produces decision_check.json with mechanical checks. Read it
and correct any issues while time remains. After the first complete decision, optionally use
WebSearch and WebFetch for a public supplier quote or tariff if it could change the most
consequential decision. Search generic product or trade details only. Use public market
sources, never tournament pages, other teams, settlements, claim identifiers or names.
Check date, specifications, unit, VAT, and whether the policy makes the item payable.
Cite the source and the value it supports, or explain the assumption if there is no match.
The local recorder timestamps successful writes. Finish when done."""


async def run_case(case, trace):
    with tempfile.TemporaryDirectory(prefix="claims-shadow-") as temp:
        work = Path(temp).resolve()
        (work / "policy.txt").write_text(case.policy)
        (work / "invoice.txt").write_text(case.invoice_text)
        (work / "description.txt").write_text(case.description)
        rules = (config.ROOT / "materials/GAME_DESCRIPTION.md").read_text().split("## Game setup")[0]
        (work / "rules.md").write_text(rules)
        for file in [*case.images, *case.case_dir.rglob("*.pdf")]:
            shutil.copy(file, work / file.name)
        env = {k: os.environ[k] for k in ("HOME", "PATH", "USER", "LANG", "TMPDIR",
                                           "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN") if k in os.environ}
        cmd = ["claude", "-p", "--model", MODEL, "--restricted", "--strict-mcp-config",
               "--mcp-config", '{"mcpServers":{}}', "--disable-slash-commands", "--no-session-persistence",
               "--permission-mode", "dontAsk", "--tools", TOOLS,
               "--allowedTools", TOOLS, "--output-format", "stream-json",
               "--verbose", "--", PROMPT]
        proc = await asyncio.create_subprocess_exec(*cmd, cwd=work, env=env,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, limit=16*1024*1024)
        stderr = asyncio.create_task(proc.stderr.read())
        calls = {}
        try:
            async with asyncio.timeout(max(.01, trace.start + 61 - time.time())):
                async for raw in proc.stdout:
                    event = json.loads(raw)
                    if event.get("type") == "system" and event.get("subtype") == "init":
                        trace.log("session", model=event.get("model"), session_id=event.get("session_id"),
                                  tools=event.get("tools"))
                    for block in (event.get("message") or {}).get("content") or []:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "tool_use":
                            name, inp = block["name"], block["input"]
                            calls[block["id"]] = (name, inp)
                            trace.log("tool", tool=name, id=block["id"], arguments={k:v for k,v in inp.items() if k!="content"})
                        if block.get("type") != "tool_result":
                            continue
                        name, inp = calls.pop(block["tool_use_id"], ("", {}))
                        failed = bool(block.get("is_error"))
                        trace.log("tool_result", tool=name, id=block["tool_use_id"], failed=failed)
                        if name == "Write" and not failed and (work / inp["file_path"]).resolve() == work / "decision.json":
                            try:
                                rows = json.loads(inp["content"])
                                issues = check(rows, trace.positions)
                                write_json(work / "decision_check.json", {"issues": issues})
                                trace.log("self_check", issues=issues, write=block["tool_use_id"])
                                trace.record(rows, dict(tool_call=block["tool_use_id"]))
                            except (KeyError, ValueError, TypeError) as exc:
                                write_json(work / "decision_check.json", {"issues": [str(exc)]})
                                trace.log("invalid_revision", error=str(exc))
                    if event.get("type") == "result":
                        trace.log("result", status=event.get("subtype"), error=event.get("is_error"),
                                  detail=event.get("result") if event.get("is_error") else None,
                                  usage=event.get("usage"))
                await proc.wait()
        except TimeoutError:
            trace.log("deadline")
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            error = await stderr
            trace.log("exit", code=proc.returncode, stderr_bytes=len(error))


def run(case, trace):
    asyncio.run(run_case(case, trace))
