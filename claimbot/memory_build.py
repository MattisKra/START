"""Case memory, offline side: turn past-cases/ plus what the settlements showed into a versioned memory build.

    uv run python -m claimbot memory build [--until N] [--out DIR] [--labels own|leaderboard] [--no-llm]

Per released case (past-cases/case_NNN, read as text only):
  observed    what the data PROVES about the hidden fair value t per line: our own settlement rows (results.json:
              our charge judged fair -> t >= a; judged inflated -> t < a; a fair charge we rejected (paid 1.5x) -> t >= it),
              merged with the bracket from ALL teams' public leaderboard rows (runs/bench/labels.jsonl, written by
              research/bench/build_labels.py; organisers' OK on 2026-11-21). `--labels own` = our rows only.
              `t < 45` does NOT mean excluded.
  hypothesis  ONE cheap LLM call per case proposes, per line, outcome / clause effect / deciding clause / verbatim quotes
              and a reusable lesson. Python then checks it: quotes must be verbatim in the policy and the description or
              invoice, the clause must exist, and it must not contradict `observed`; otherwise it becomes `unknown`.
              `checked` = it agrees with the hand-written "The catch" column in past-cases/README.md (independent source).
Output: runs/memory/builds/<stamp>/{entries.jsonl, clauses.jsonl, index.npz, manifest.json}, then runs/memory/CURRENT is
switched with os.replace (atomic). --out DIR writes a build for benchmarks and never touches CURRENT.
LLM answers are cached per case in runs/memory/enrich/ (keyed by the inputs), so rebuilds cost nothing.
"""

import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from . import config
from . import memtext as mt

PROMPT_VERSION = "mem-v2"
ENRICH_DIR = config.MEMORY_DIR / "enrich"
BUILDS = config.MEMORY_DIR / "builds"
KEEP_BUILDS = 5

Effect = Literal[
    "covered_in_full", "excluded_peril_not_agreed", "excluded_pre_existing_or_wear", "excluded_not_a_repair_cost",
    "excluded_other", "unrelated_to_damage", "sublimit_cap", "proportional_reduction", "follows_principal",
    "time_value_no_improvement", "deductible", "quantity_reduced", "unknown",
]


class LineLesson(BaseModel):
    pos: int = Field(description="the printed POS. number of the invoice line (1-based)")
    category: str = Field(description="short generic snake_case kind of item, e.g. diagnostic_report, technician_callout, "
                                      "screen_repair, glass_pane, travel_vehicle_costs, labour_sundries")
    outcome: Literal["excluded", "paid", "partial", "unknown"]
    clause_effect: Effect
    clause_ids: list[str] = Field(description="deciding clause numbers exactly as printed, e.g. ['7.1.11']")
    clause_quote: str = Field(description="ONE sentence copied verbatim from the policy that decides the line")
    fact_quote: str = Field(description="the words copied verbatim from the description or invoice that trigger the clause")
    lesson: str = Field(description="one reusable sentence: the rule AND the condition under which it applies")


class CaseLessons(BaseModel):
    damage_summary: str = Field(description="one short sentence: what was damaged, how")
    lines: list[LineLesson]


INSTRUCTIONS = """\
You annotate an insurance claim whose settlement is over, to build a memory of lessons for future claims.
You get the policy, the damage description, the invoice lines and, per line, what the settlement revealed about the
hidden fair value t (gross EUR for the whole line; t = 0 means nothing was owed for the line).

For every invoice line return:
- category: a short generic snake_case kind of item, no case specifics.
- outcome: excluded (nothing owed), paid (owed in full at a fair price), partial (owed but reduced: sub-limit,
  proportional reduction, time value, or only part of the line covered), or unknown.
- clause_effect: the mechanism, from the fixed list.
- clause_ids: the clause numbers that decide the line, exactly as printed in the policy.
- clause_quote: ONE sentence copied VERBATIM from the policy that decides it (no ellipsis, no paraphrase).
- fact_quote: the words copied VERBATIM from the description or invoice that trigger the clause.
- lesson: one sentence a future adjuster can reuse: the rule AND the condition under which it applies.

Rules:
- Decide from the POLICY wording and the FACTS of the description and invoice, as a careful adjuster would. The
  settlement facts are only bounds that your answer must not contradict: "t below 45" does not mean excluded,
  "t at least 300" does not mean paid in full, and "nothing known" says nothing either way.
- Answer unknown only when the policy reading is genuinely open (the deciding condition is not stated in the facts,
  or two clauses point different ways). A confident wrong lesson is worse than unknown.
- excluded only when a clause excludes THIS item. Ancillary costs (travel, vehicle, call-out, labour, sundries) that
  follow principal items which are partly covered are partial, not excluded.
- Never invent clause numbers. Quotes must be exact copies of the text.
"""


# --- inputs -----------------------------------------------------------------------------------------------------------

def load_past(d: Path) -> dict:
    inv = d / "invoice.txt"
    if inv.exists():
        invoice = inv.read_text(errors="replace")
    else:
        from .case import pdf_text
        invoice = pdf_text(next(d.glob("invoice*.pdf")))
    return dict(game=int(d.name.split("_")[1]), policy=(d / "policy.txt").read_text(errors="replace"),
                description=(d / "description.txt").read_text(errors="replace"), invoice=invoice)


def observed_own(d: Path) -> dict[int, dict]:
    """{pos: observed} from our own settlement rows (results.json, written by `claimbot archive`)."""
    f = d / "results.json"
    if not f.exists():
        return {}
    out = {}
    for k, v in json.loads(f.read_text())["lines"].items():
        ch, rv = v.get("charge") or {}, v.get("review") or {}
        a, verdict = ch.get("a"), ch.get("verdict", "")
        lo = hi = None
        av = None
        if a:  # a is None when we charged 0: then the verdict says nothing about t
            if verdict.startswith("fair"):
                lo, av = a, "fair"
            elif verdict.startswith("INFLATED"):
                hi, av = a, "inflated"
            else:
                av = "unknown"
        if rv.get("b_upper"):  # the smallest fair charge we rejected (it paid 1.5x): t >= it
            lo = max(lo or 0.0, rv["b_upper"])
        out[int(k)] = dict(source="own", t_lo=lo, t_hi=hi, our_a=a, our_a_verdict=av)
    return out


def observed_leaderboard() -> dict[tuple[int, int], dict]:
    """{(game, line): bracket} from runs/bench/labels.jsonl (all teams' public rows); {} when the file is missing."""
    f = config.LABELS_FILE
    if not f.exists():
        return {}
    out = {}
    for l in f.read_text().splitlines():
        if l.strip():
            d = json.loads(l)
            out[(d["game"], d["line"])] = dict(t_lo=d["t_lo"] or None, t_hi=d["t_hi"])
    return out


def merge_obs(own: dict | None, lb: dict | None) -> dict:
    o = dict(own or dict(source="none", t_lo=None, t_hi=None, our_a=None, our_a_verdict=None))
    if lb:
        lo = [x for x in (o["t_lo"], lb["t_lo"]) if x]
        hi = [x for x in (o["t_hi"], lb["t_hi"]) if x is not None]
        o.update(t_lo=max(lo) if lo else None, t_hi=min(hi) if hi else None, source=o["source"] + "+leaderboard")
    return o


def readme_catches() -> dict[int, str]:
    """The hand-written 'The catch' column of past-cases/README.md, per game ('todo' rows are skipped)."""
    f = config.PAST_DIR / "README.md"
    out = {}
    if not f.exists():
        return out
    for ln in f.read_text().splitlines():
        m = re.match(r"^\| \[(\d+)\]\(case_\d+/\) \|", ln)
        if not m:
            continue
        cols = [c.strip() for c in re.split(r"(?<!\\)\|", ln)[1:-1]]
        if len(cols) >= 5 and cols[4] and cols[4].lower() != "todo":
            out[int(m.group(1))] = cols[4]
    return out


# --- LLM enrichment ---------------------------------------------------------------------------------------------------

def _obs_text(o: dict) -> str:
    parts = []
    if o.get("t_lo"):
        parts.append(f"t is at least {o['t_lo']:.2f}")
    if o.get("t_hi") is not None:
        parts.append(f"t is below {o['t_hi']:.2f}")
    return " and ".join(parts) if parts else "nothing known"


def _enrich_input(pc: dict, lines: list[dict], obs: dict[int, dict]) -> tuple[str, str, Path]:
    """(case text for the LLM, cache key, cache file). The key covers prompt, model, effort and inputs."""
    listing = "\n".join(f"POS {l['pos']}: {l['text']} ({l['qty']:g} {l['unit']}) - settlement: {_obs_text(obs[l['pos']])}"
                        if l["qty"] is not None else f"POS {l['pos']}: {l['text']} - settlement: {_obs_text(obs[l['pos']])}"
                        for l in lines)
    text = (f"=== policy.txt ===\n{pc['policy']}\n\n=== description.txt ===\n{pc['description']}\n\n"
            f"=== invoice (extracted from PDF) ===\n{pc['invoice']}\n\n=== invoice lines and settlement ===\n{listing}\n")
    key = hashlib.sha256(f"{PROMPT_VERSION}|{config.MEMORY_MODEL}|{config.MEMORY_EFFORT}|{INSTRUCTIONS}|{text}".encode()).hexdigest()
    # one file per case AND input: switching labels (own / leaderboard) or the prompt never overwrites another answer
    return text, key, ENRICH_DIR / f"case_{pc['game']:03d}_{key[:10]}.json"


def enrich(pc: dict, lines: list[dict], obs: dict[int, dict]) -> tuple[CaseLessons, dict]:
    text, key, cache = _enrich_input(pc, lines, obs)
    if cache.exists():
        c = json.loads(cache.read_text())
        if c.get("key") == key:
            return CaseLessons(**c["lessons"]), dict(cached=True, usage=c.get("usage"))
    if config.MEMORY_MODEL.startswith("claude-"):
        from .anthropic_estimator import _get_client
        resp = _get_client().messages.parse(
            model=config.MEMORY_MODEL, max_tokens=8000, system=INSTRUCTIONS,
            messages=[{"role": "user", "content": [{"type": "text", "text": text}]}],
            output_config={"effort": config.MEMORY_EFFORT}, output_format=CaseLessons,
        )
        parsed = resp.parsed_output
    else:
        from .estimator import _client
        resp = _client().responses.parse(
            model=config.MEMORY_MODEL, instructions=INSTRUCTIONS,
            input=[{"role": "user", "content": [{"type": "input_text", "text": text}]}],
            reasoning={"effort": config.MEMORY_EFFORT}, text_format=CaseLessons,
        )
        parsed = resp.output_parsed
    if parsed is None:
        raise RuntimeError(f"{config.MEMORY_MODEL}: no parsed output")
    usage = resp.usage.model_dump() if resp.usage else None
    ENRICH_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dict(key=key, model=config.MEMORY_MODEL, effort=config.MEMORY_EFFORT,
                                     lessons=parsed.model_dump(), usage=usage), indent=1, ensure_ascii=False))
    return parsed, dict(cached=False, usage=usage)


# --- checks -----------------------------------------------------------------------------------------------------------

def _n2(s: str) -> tuple[str, str]:
    """Two normalisations: plain, and with line-break hyphens re-joined ("lower- right" -> "lower-right")."""
    n = mt.norm(s)
    return n, re.sub(r"(\w)- (\w)", r"\1-\2", n)


def _quote(s: str) -> str:
    s = s.strip().strip("\"'“”‘’").strip()
    return re.sub(r"\s*(\.\.\.|…)\s*$", "", s)


def _contains(hay: tuple[str, str], needle: str) -> bool:
    n = _n2(needle)
    return n[0] in hay[0] or n[1] in hay[1]


EXPECT = [
    ("excluded", re.compile(r"\b(excluded|not covered|no cover|unrelated|not agreed|not a repair cost|is 0|are 0|line is 0)\b", re.I)),
    ("partial", re.compile(r"\b(partly|partial|rateabl\w*|half|sub-limit|aggregate|capped|cap|reduc\w*|follow\w*)\b|\b\d{1,2}\s?%", re.I)),
    ("paid", re.compile(r"\b(covered|is owed|paid)\b", re.I)),
]


_CATCH_STOP = set("which where their there these those under every other about after before covered excluded "
                  "partly applies apply follow follows principal item items lines line cost damage damaged repair that "
                  "this with from have been were".split())


def _words(s: str) -> set[str]:
    return {w.rstrip("s") for w in re.findall(r"[a-z]{4,}", s.lower())} - _CATCH_STOP


def catch_agrees(hyp: dict, catch: str | None, line_text: str = "") -> bool | None:
    """Does the hand-written catch confirm the hypothesis? True = a sentence about this line implies the same outcome,
    False = sentences about this line imply only other outcomes (contradiction), None = the catch says nothing about it.
    "About this line": the sentence names a clause the hypothesis cites, or it shares a content word with the line text
    or the fact quote (most catches name no clause, and the model may cite a neighbouring one)."""
    if not catch:
        return None
    sents = re.split(r"(?<!incl\.)(?<!approx\.)(?<!e\.g\.)(?<=[.;])\s+", catch.replace("**", ""))
    about = _words(line_text + " " + hyp.get("fact_quote", ""))
    seen = False
    for s in sents:
        refs = set(re.findall(r"(\d+(?:\.\d+){1,3})", s))
        if not (refs & set(hyp["clause_ids"]) or _words(s) & about):
            continue
        expected = [o for o, rx in EXPECT if rx.search(s)]
        if not expected:
            continue
        seen = True
        if expected[0] == hyp["outcome"]:  # first matching class wins: "not covered" before "covered"
            return True
    return False if seen else None


def validate(ll: LineLesson | None, obs: dict, clauses: list[mt.Clause], policy_n, facts_n, catch: str | None,
             line_text: str = "") -> dict:
    if ll is None:
        return dict(outcome="unknown", clause_effect="unknown", clause_ids=[], clause_quote="", fact_quote="",
                    checked=False, why_unknown="no LLM annotation")
    h = dict(outcome=ll.outcome, clause_effect=ll.clause_effect, clause_ids=[c.strip().lstrip("§").strip() for c in ll.clause_ids],
             clause_quote=_quote(ll.clause_quote), fact_quote=_quote(ll.fact_quote), checked=False, why_unknown=None)

    def unknown(reason):
        h.update(outcome="unknown", clause_effect="unknown", why_unknown=reason)
        return h

    if h["outcome"] == "unknown" or h["clause_effect"] == "unknown":
        return unknown("model said unknown")
    if len(h["clause_quote"]) < 25 or not _contains(policy_n, h["clause_quote"]):
        return unknown("clause quote is not verbatim in the policy")
    if len(h["fact_quote"]) < 4 or not _contains(facts_n, h["fact_quote"]):
        return unknown("fact quote is not verbatim in the description or invoice")
    home = [c for c in clauses if _contains(_n2(c.text), h["clause_quote"])]
    if not home:
        return unknown("clause quote is not inside a parsed clause")
    known = {c.id for c in clauses}
    ids = [i for i in h["clause_ids"] if i in known]
    if home[0].id not in ids:
        ids = [home[0].id] + ids
    h["clause_ids"] = ids[:3]
    if h["outcome"] == "excluded" and obs.get("t_lo"):
        return unknown(f"excluded contradicts the settlement (t >= {obs['t_lo']})")
    agrees = catch_agrees(h, catch, line_text)
    if agrees is False:
        return unknown("contradicts the hand-written catch")
    h["checked"] = bool(agrees)
    return h


# --- build ------------------------------------------------------------------------------------------------------------

def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(until: int | None = None, out: Path | None = None, labels: str | None = None, use_llm: bool = True,
          verbose: bool = True) -> Path:
    from . import memory
    say = print if verbose else (lambda *a, **k: None)
    cases = sorted(d for d in config.PAST_DIR.glob("case_[0-9][0-9][0-9]") if (d / "policy.txt").exists())
    if until is not None:
        cases = [d for d in cases if int(d.name.split("_")[1]) <= until]
    labels = labels or config.MEMORY_LABELS
    lb = {}
    entries, clauses_out, usage, problems = [], {}, [], []
    if labels == "leaderboard":
        lb = observed_leaderboard()
        if not lb:
            problems.append(f"{config.LABELS_FILE.name} missing: own rows only (research/bench/build_labels.py)")
    catches = readme_catches()
    for d in cases:
        pc = load_past(d)
        g = pc["game"]
        lines = mt.parse_invoice_lines(pc["invoice"])
        if not lines:
            problems.append(f"game {g}: invoice lines not parsed, skipped")
            continue
        own = observed_own(d)
        obs = {l["pos"]: merge_obs(own.get(l["pos"]), lb.get((g, l["pos"]))) for l in lines}
        clauses = mt.parse_clauses(pc["policy"])
        by_id = {c.id: c for c in clauses}
        ed, trade = mt.edition(pc["policy"]), mt.trade_of(pc["invoice"])
        lessons = None
        if use_llm and not (d / "results.json").exists():
            problems.append(f"game {g}: not settled yet, no enrichment")
        elif use_llm:
            try:
                lessons, meta = enrich(pc, lines, obs)
                usage.append(dict(game=g, **meta))
            except Exception as e:  # noqa: BLE001 - a failed call leaves this case without hypotheses
                problems.append(f"game {g}: enrichment failed {e!r}")
        by_pos = {ll.pos: ll for ll in (lessons.lines if lessons else [])}
        policy_n = _n2(pc["policy"])
        facts_n = _n2(pc["description"] + "\n" + pc["invoice"])
        summary = lessons.damage_summary if lessons else " ".join(pc["description"].split())[:160]
        for l in lines:
            ll = by_pos.get(l["pos"])
            h = validate(ll, obs[l["pos"]], clauses, policy_n, facts_n, catches.get(g), l["text"])
            cat = ll.category if ll else ""
            entries.append(dict(
                game=g, line=l["pos"], edition=ed, trade=trade, text=l["text"], unit=l["unit"], qty=l["qty"],
                category=cat, observed=obs[l["pos"]], hypothesis=h,
                lesson=(ll.lesson if ll and h["outcome"] != "unknown" else ""),
                emb_text=f"{l['text']} | {cat}" if cat else l["text"], ctx_text=f"{trade} | {summary}"))
            if h["outcome"] != "unknown":
                for cid in h["clause_ids"]:
                    c = by_id[cid]
                    clauses_out[(g, cid)] = dict(game=g, id=cid, title=c.title, edition=ed, hash=mt.exact_hash(c),
                                                 numbers=mt.numbers(c.body), body=c.body)
    if not entries:
        raise SystemExit("memory build: no entries")

    vecs = memory.embed([e["emb_text"] for e in entries])
    ctx = memory.embed([e["ctx_text"] for e in entries])
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    final = Path(out) if out else BUILDS / stamp
    tmp = final.with_name(final.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "entries.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries))
    (tmp / "clauses.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in clauses_out.values()))
    files = ["entries.jsonl", "clauses.jsonl"]
    if vecs is not None:
        import numpy as np
        np.savez(tmp / "index.npz", vecs=vecs, ctx=ctx)
        files.append("index.npz")
    man = dict(created=datetime.now().isoformat(timespec="seconds"), games=sorted({e["game"] for e in entries}),
               until=until, labels=labels, n_entries=len(entries), n_clauses=len(clauses_out),
               n_usable=sum(memory.usable(e) for e in entries), n_checked=sum(e["hypothesis"]["checked"] for e in entries),
               embed_model=memory.EMBED_MODEL if vecs is not None else None, prompt_version=PROMPT_VERSION,
               llm=dict(model=config.MEMORY_MODEL, effort=config.MEMORY_EFFORT, calls=usage) if use_llm else None,
               problems=problems, inputs=inputs_signature(labels), files={f: _sha(tmp / f) for f in files})
    (tmp / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False))
    if final.exists():
        shutil.rmtree(final)
    os.replace(tmp, final)  # the build directory appears complete or not at all
    if out is None:  # activate: CURRENT is switched atomically; a reader sees the old or the new build, never half
        ptr = config.MEMORY_DIR / "CURRENT.tmp"
        ptr.write_text(final.name + "\n")
        os.replace(ptr, config.MEMORY_DIR / "CURRENT")
        _prune(keep=final.name)
    for p in problems:
        say(f"  ! {p}")
    say(f"memory build {final} : {man['n_entries']} entries from games {man['games']}, {man['n_usable']} usable hypotheses "
        f"({man['n_checked']} checked against 'The catch'), {man['n_clauses']} deciding clauses, "
        f"embeddings {'on' if vecs is not None else 'OFF'}{'' if out else ', now CURRENT'}")
    return final


def _prune(keep: str) -> None:
    olds = sorted(p for p in BUILDS.iterdir() if p.is_dir() and not p.name.endswith(".tmp") and p.name != keep)
    for p in olds[:-(KEEP_BUILDS - 1)] if len(olds) > KEEP_BUILDS - 1 else []:
        shutil.rmtree(p, ignore_errors=True)


# --- manual enrichment (paste into a chat UI instead of an API call) -------------------------------------------------

MANUAL_DIR = config.MEMORY_DIR / "manual"
MANUAL_TAIL = """
Answer with ONLY one JSON object that matches this JSON Schema: no prose before or after it, no code fence. One entry in
"lines" per invoice line (POS 1..n). Allowed clause_effect values: {effects}.

JSON Schema:
{schema}

--- CASE ---
"""


def _manual_cases(until: int | None):
    for d in sorted(d for d in config.PAST_DIR.glob("case_[0-9][0-9][0-9]") if (d / "policy.txt").exists()):
        pc = load_past(d)
        if until is not None and pc["game"] > until:
            continue
        if not (d / "results.json").exists():  # not settled yet: the answer would be invalid once results arrive
            continue
        lines = mt.parse_invoice_lines(pc["invoice"])
        if not lines:
            continue
        own = observed_own(d)
        lb = observed_leaderboard() if config.MEMORY_LABELS == "leaderboard" else {}
        obs = {l["pos"]: merge_obs(own.get(l["pos"]), lb.get((pc["game"], l["pos"]))) for l in lines}
        yield pc, lines, obs


def manual_export(until: int | None = None, out: Path = MANUAL_DIR, only_missing: bool = True) -> list[Path]:
    """One self-contained prompt file per case (instructions + schema + case), to paste into ChatGPT / claude.ai."""
    out.mkdir(parents=True, exist_ok=True)
    tail = MANUAL_TAIL.format(effects=", ".join(Effect.__args__), schema=json.dumps(CaseLessons.model_json_schema(), indent=1))
    written = []
    for pc, lines, obs in _manual_cases(until):
        text, key, cache = _enrich_input(pc, lines, obs)
        if only_missing and cache.exists() and json.loads(cache.read_text()).get("key") == key:
            continue
        f = out / f"case_{pc['game']:03d}.prompt.txt"
        f.write_text(INSTRUCTIONS + tail + text)
        written.append(f)
    return written


def _strip_fence(s: str) -> str:
    s = s.strip()
    m = re.match(r"^```[a-zA-Z]*\s*\n(.*)\n```\s*$", s, re.S)
    if m:
        s = m.group(1)
    i, j = s.find("{"), s.rfind("}")
    return s[i:j + 1] if i >= 0 and j > i else s


def manual_import(src: Path = MANUAL_DIR, source: str = "chatgpt-manual") -> list[str]:
    """Read case_NNN.answer.json (the chat's reply, pasted as is) and store it in the enrichment cache, under the key the
    next `memory build` looks for. The answer still goes through validate() like any API answer."""
    by_game = {pc["game"]: (pc, lines, obs) for pc, lines, obs in _manual_cases(None)}
    report = []
    for f in sorted(src.glob("case_[0-9][0-9][0-9].answer.json")):
        g = int(f.name[5:8])
        if g not in by_game:
            report.append(f"game {g}: no such past case, skipped")
            continue
        pc, lines, obs = by_game[g]
        try:
            lessons = CaseLessons.model_validate_json(_strip_fence(f.read_text()))
        except Exception as e:  # noqa: BLE001
            report.append(f"game {g}: answer is not valid JSON for the schema: {str(e).splitlines()[0]}")
            continue
        missing = sorted({l["pos"] for l in lines} - {ll.pos for ll in lessons.lines})
        _, key, cache = _enrich_input(pc, lines, obs)
        ENRICH_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(dict(key=key, model=source, effort="manual", lessons=lessons.model_dump(), usage=None),
                                    indent=1, ensure_ascii=False))
        report.append(f"game {g}: imported {len(lessons.lines)} lines" + (f" (missing POS {missing})" if missing else ""))
    return report


# --- refresh (live machine: keep the memory current next to the watch bot) -------------------------------------------

def inputs_signature(labels: str | None = None) -> str:
    """Changes whenever a rebuild could change the memory: settled games, the labels file, the README catches, prompt."""
    labels = labels or config.MEMORY_LABELS
    h = hashlib.sha256(f"{PROMPT_VERSION}|{labels}|{config.MEMORY_MODEL}|{config.MEMORY_EFFORT}".encode())
    for d in sorted(config.PAST_DIR.glob("case_[0-9][0-9][0-9]")):
        r = d / "results.json"
        h.update(f"{d.name}:{(d / 'policy.txt').exists()}:{_sha(r) if r.exists() else '-'}".encode())
    if labels == "leaderboard" and config.LABELS_FILE.exists():
        h.update(_sha(config.LABELS_FILE).encode())
    readme = config.PAST_DIR / "README.md"
    h.update(json.dumps(readme_catches() if readme.exists() else {}, sort_keys=True).encode())
    return h.hexdigest()[:16]


def _current_inputs() -> str | None:
    try:
        name = (config.MEMORY_DIR / "CURRENT").read_text().strip()
        return json.loads((BUILDS / name / "manifest.json").read_text()).get("inputs")
    except Exception:  # noqa: BLE001
        return None


def refresh(pull: bool = False, labels_update: bool = True) -> str:
    """One refresh step: optionally `git pull --ff-only` (new past-cases/ from the archive machine), update the
    leaderboard labels, and rebuild + activate the memory only when its inputs changed. Returns what happened."""
    import subprocess
    msgs = []
    if pull:
        r = subprocess.run(["git", "-C", str(config.ROOT), "pull", "-q", "--ff-only"], capture_output=True, text=True)
        msgs.append("git pull ok" if r.returncode == 0 else f"git pull FAILED: {(r.stderr or r.stdout).strip()[-200:]}")
    if labels_update and config.MEMORY_LABELS == "leaderboard":
        from .archive import _update_labels
        _update_labels()
    sig = inputs_signature()
    if sig == _current_inputs():
        msgs.append("memory up to date")
    else:
        final = build(verbose=False)
        man = json.loads((final / "manifest.json").read_text())
        msgs.append(f"memory rebuilt: {final.name}, games {man['games'][0]}..{man['games'][-1]}, "
                    f"{man['n_usable']} usable hypotheses, problems {len(man['problems'])}")
    return "; ".join(msgs)
