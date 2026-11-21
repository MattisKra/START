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
from .policy_gate import INSTRUCTION, PolicyGate
from .review_turns import ReviewTurns, send
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


async def run_case(case, trace, *, require_policy=False, extra_reviews=False):
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
        gate = PolicyGate(work, case.policy) if require_policy else None
        prompt = PROMPT + INSTRUCTION if require_policy else PROMPT
        cmd = ["claude", "-p", "--model", MODEL, "--restricted", "--strict-mcp-config",
               "--mcp-config", '{"mcpServers":{}}', "--disable-slash-commands", "--no-session-persistence",
               "--permission-mode", "dontAsk", "--tools", TOOLS,
               "--allowedTools", TOOLS, "--output-format", "stream-json",
               "--verbose", "--", prompt]
        reviews = ReviewTurns(work.iterdir()) if extra_reviews else None
        if reviews:
            cmd[-2:] = ["--input-format", "stream-json"]
        proc = await asyncio.create_subprocess_exec(*cmd, cwd=work, env=env,
                    stdin=asyncio.subprocess.PIPE if reviews else None,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, limit=16*1024*1024)
        stderr = asyncio.create_task(proc.stderr.read())
        calls = {}
        try:
            async with asyncio.timeout(max(.01, trace.start + 61 - time.time())):
                if reviews:
                    await send(proc, prompt)
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
                            turn = event["message"].get("id") or block["id"]
                            prior = gate.prior_reads(turn) if gate and name == "Write" else []
                            sources = reviews.prior_sources(turn) if reviews and name == "Write" else []
                            calls[block["id"]] = (name, inp, turn, prior, sources)
                            trace.log("tool", tool=name, id=block["id"], arguments={k:v for k,v in inp.items() if k!="content"})
                        if block.get("type") != "tool_result":
                            continue
                        name, inp, turn, prior, sources = calls.pop(block["tool_use_id"], ("", {}, None, [], []))
                        if gate:
                            gate.result(block["tool_use_id"], turn, name, inp, block)
                        failed = bool(block.get("is_error"))
                        trace.log("tool_result", tool=name, id=block["tool_use_id"], failed=failed)
                        if reviews and reviews.targets:
                            reviews.source(block["tool_use_id"], turn, name, inp, failed, work)
                            if name == "Write" and not failed and (work / inp["file_path"]).resolve() == work / "review.json":
                                try:
                                    reviews.record(trace, json.loads(inp["content"]), sources, block["tool_use_id"])
                                except (ValueError, TypeError, KeyError) as exc:
                                    write_json(work / "decision_check.json", {"issues": [str(exc)]})
                                    trace.log("invalid_review", error=str(exc))
                            continue
                        if name == "Write" and not failed and (work / inp["file_path"]).resolve() == work / "decision.json":
                            try:
                                rows = json.loads(inp["content"])
                                issues = check(rows, trace.positions)
                                trigger = dict(tool_call=block["tool_use_id"])
                                if gate:
                                    proof = gate.proof(rows, prior)
                                    if not proof:
                                        issues.append("Read the body of the relevant clause in policy.txt first, then "
                                                      "supply its heading number and a matching six-word or longer quote.")
                                        write_json(work / "decision_check.json", {"issues": issues})
                                        trace.log("policy_rejected", write=block["tool_use_id"], issues=issues)
                                        continue
                                    trigger["policy_proof"] = proof
                                write_json(work / "decision_check.json", {"issues": issues})
                                trace.log("self_check", issues=issues, write=block["tool_use_id"])
                                if reviews and issues:
                                    trace.log("invalid_revision", error=" | ".join(issues))
                                else:
                                    trace.record(rows, trigger)
                            except (KeyError, ValueError, TypeError) as exc:
                                write_json(work / "decision_check.json", {"issues": [str(exc)]})
                                trace.log("invalid_revision", error=str(exc))
                    if event.get("type") == "result":
                        trace.log("result", status=event.get("subtype"), error=event.get("is_error"),
                                  detail=event.get("result") if event.get("is_error") else None,
                                  usage=event.get("usage"), **(dict(review_pass=len(reviews.targets),
                                  session_id=event.get("session_id"), total_cost_usd=event.get("total_cost_usd"),
                                  duration_api_ms=event.get("duration_api_ms")) if reviews else {}))
                        if reviews:
                            followup = None if event.get("is_error") else reviews.next(trace, time.time() - trace.start)
                            if followup:
                                await send(proc, followup)
                            else:
                                proc.stdin.close()
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


def run_policy_first(case, trace):
    asyncio.run(run_case(case, trace, require_policy=True))


def run_extra_reviews(case, trace):
    asyncio.run(run_case(case, trace, require_policy=True, extra_reviews=True))
