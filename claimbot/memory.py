"""Case memory, online side: hints from earlier, settled games for the prompt of a new case.

Built offline by memory_build.py into runs/memory/builds/<stamp>/ and activated through runs/memory/CURRENT.
Per new case (target 100-300 ms, in ONE persistent worker thread so it never blocks a round):

  1. parse the invoice lines and the new policy's clauses (memtext.py)
  2. clause match: a clause that decided an earlier line is found in THIS policy by exact hash, or (paraphrase) by
     MinHash candidates >= 0.8 with identical numbers, scored by exact Jaccard
  3. score every memory entry per line: 0.55 cos + 0.15 bm25 + 0.20 clause hit + 0.10 same edition, where
     cos = 0.8 cos(line text) + 0.2 cos(trade and damage context), rescaled so bge's unrelated-text baseline (~0.5) is 0
  4. a hint block (<= ~600 tokens): clause warnings quoting the condition and exception from THIS policy, then the k best
     neighbours per line with what their settlement showed. THIS policy and description always win.

Everything fails silently: no build, a broken build, a missing embedding model or a slow worker just means no hints.
"""

import hashlib
import json
import math
import re
import threading
import time
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from . import memtext as mt

EMBED_MODEL = "BAAI/bge-small-en-v1.5"  # fastembed (ONNX, CPU), 384 dims
W_COS, W_BM25, W_CLAUSE, W_EDITION = 0.55, 0.15, 0.20, 0.10
W_LINE, W_CTX = 0.8, 0.2
COS_FLOOR = 0.5  # bge-small gives ~0.5 to unrelated short texts; cos is rescaled to (cos - floor) / (1 - floor)
MAX_WARNINGS = 5
MAX_CHARS = 2400  # ~600 tokens
CURRENT = config.MEMORY_DIR / "CURRENT"

# --- embeddings -------------------------------------------------------------------------------------------------------

_emb = None
_emb_failed = False
_emb_lock = threading.Lock()


def embedder():
    """The fastembed model, loaded once (≈10 s cold, from runs/memory/models). None if fastembed is unavailable."""
    global _emb, _emb_failed
    if _emb is None and not _emb_failed:
        with _emb_lock:
            if _emb is None and not _emb_failed:
                try:
                    from fastembed import TextEmbedding
                    _emb = TextEmbedding(EMBED_MODEL, cache_dir=str(config.MEMORY_DIR / "models"))
                except Exception as e:  # noqa: BLE001 - fall back to BM25 + clause hashes
                    print(f"memory: embedding model unavailable ({e!r}); using BM25 only")
                    _emb_failed = True
    return _emb


def embed(texts: list[str]):
    """L2-normalised float32 matrix (n, 384), or None without an embedding model."""
    m = embedder()
    if m is None or not texts:
        return None
    import numpy as np
    v = np.array(list(m.embed(texts)), dtype=np.float32)
    v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
    return v


# --- BM25 -------------------------------------------------------------------------------------------------------------

STOP = set("the of and a an to in for on with at by or incl including from new old pcs flat rate per".split())


def toks(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-zäöüß]{3,}", s.lower()) if w not in STOP]


@dataclass
class _BM25:
    docs: list[Counter]
    df: Counter
    avgdl: float

    @classmethod
    def build(cls, texts: list[str]) -> "_BM25":
        docs = [Counter(toks(t)) for t in texts]
        df = Counter(w for d in docs for w in d)
        return cls(docs, df, (sum(sum(d.values()) for d in docs) / len(docs)) if docs else 1.0)

    def scores(self, query: str, k1: float = 1.2, b: float = 0.75) -> list[float]:
        n = len(self.docs)
        out = []
        q = set(toks(query))
        for d in self.docs:
            dl = sum(d.values()) or 1
            s = 0.0
            for w in q:
                if w in d:
                    idf = math.log(1 + (n - self.df[w] + 0.5) / (self.df[w] + 0.5))
                    s += idf * d[w] * (k1 + 1) / (d[w] + k1 * (1 - b + b * dl / self.avgdl))
            out.append(s)
        return out


# --- loaded build -----------------------------------------------------------------------------------------------------

@dataclass
class _State:
    name: str
    dir: Path
    entries: list[dict]
    vecs: object  # numpy (n, d) line-text vectors, or None
    ctx: object   # numpy (n, d) context vectors (trade + damage), or None
    clauses: dict  # (game, clause id) -> clause record (+ "minhash")
    bm25: _BM25
    manifest: dict = field(default_factory=dict)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_build(d: Path) -> _State:
    """Load one build directory and verify it against its manifest. Raises on any inconsistency."""
    d = Path(d)
    man = json.loads((d / "manifest.json").read_text())
    for fname, digest in man["files"].items():
        if _sha(d / fname) != digest:
            raise ValueError(f"{d.name}/{fname}: hash does not match manifest")
    entries = [json.loads(l) for l in (d / "entries.jsonl").read_text().splitlines() if l.strip()]
    clauses = {}
    for l in (d / "clauses.jsonl").read_text().splitlines():
        if l.strip():
            c = json.loads(l)
            clauses[(c["game"], c["id"])] = c
    vecs = ctx = None
    if "index.npz" in man["files"]:
        import numpy as np
        z = np.load(d / "index.npz")
        vecs, ctx = z["vecs"], z["ctx"]
        if vecs.shape[0] != len(entries):
            raise ValueError(f"{d.name}: {vecs.shape[0]} vectors for {len(entries)} entries")
        if man.get("embed_model") != EMBED_MODEL:
            raise ValueError(f"{d.name}: built with {man.get('embed_model')}, online model is {EMBED_MODEL}")
    for c in clauses.values():
        try:
            c["minhash"] = mt.minhash(c["body"])
        except ImportError:
            c["minhash"] = None
    return _State(d.name, d, entries, vecs, ctx, clauses, _BM25.build([e["emb_text"] for e in entries]), man)


def usable(e: dict) -> bool:
    """Only hypotheses checked against the hand-written 'catch', or fully quoted ones, may become rules."""
    h = e.get("hypothesis") or {}
    return h.get("outcome", "unknown") != "unknown" and bool(h.get("checked") or (h.get("clause_quote") and h.get("fact_quote")))


def informative(e: dict) -> bool:
    """A neighbour is shown only if it tells the model something: a proven bound on t or a usable hypothesis.
    'settlement unknown; reason unknown' or 'a charge was too high; reason unknown' only cost tokens."""
    o = e.get("observed") or {}
    return o.get("t_lo") is not None or usable(e)  # "a charge was too high" alone tells the model nothing


def _obs_str(o: dict) -> str:
    """Only LOWER bounds are shown as amounts. An upper bound ("our charge of X was too high") read like a price anchor
    in the forward evaluation (game 9: b and a nearly doubled), so it is reported without the number."""
    lo, hi = o.get("t_lo"), o.get("t_hi")
    if lo:
        return f"owed at least {lo:.0f} EUR gross (a lower bound, not a price)"
    if hi is not None:
        return "an earlier charge on it was too high (no amount known)"
    return "settlement unknown"


def _qty(e: dict) -> str:
    return f"{e['qty']:g} {e['unit']}" if e.get("qty") is not None else e.get("unit") or "?"


class Memory:
    def __init__(self):
        self.state: _State | None = None
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="memory")
        self._busy = False
        self._lock = threading.Lock()

    # -- loading --
    def load(self, build_dir: Path | None = None) -> bool:
        """Load `build_dir`, or the build CURRENT points to. On any error the previous build stays active."""
        try:
            if build_dir is None:
                if not CURRENT.exists():
                    return False
                build_dir = config.MEMORY_DIR / "builds" / CURRENT.read_text().strip()
            st = load_build(build_dir)
        except Exception as e:  # noqa: BLE001
            print(f"memory: could not load {build_dir}: {e!r}; keeping {self.state.name if self.state else 'nothing'}")
            return False
        self.state = st  # one reference swap: a running query keeps the build it started with
        return True

    def maybe_reload(self) -> None:
        """Between rounds: switch to a newer build if CURRENT changed."""
        try:
            name = CURRENT.read_text().strip() if CURRENT.exists() else None
        except OSError:
            return
        if name and (self.state is None or self.state.name != name):
            if self.load():
                print(f"memory: loaded build {name} ({len(self.state.entries)} entries)")

    def warm(self) -> None:
        """Load the embedding model and run the code paths once, so the first live query is fast."""
        embed(["warm up"])
        mt.parse_clauses("1.1 Warm up\nText.")
        try:
            mt.minhash("warm up the minhash permutations")
        except ImportError:
            pass

    # -- query --
    def submit(self, case, **kw) -> Future:
        """Query in the persistent worker. If the worker is still busy with an older query, skip instead of queueing."""
        with self._lock:
            if self._busy:
                f: Future = Future()
                f.set_result(dict(status="skipped", block=None))
                return f
            self._busy = True

        def job():
            try:
                return self.query(case, **kw)
            except Exception as e:  # noqa: BLE001
                return dict(status="error", error=repr(e), block=None)
            finally:
                with self._lock:
                    self._busy = False

        return self._pool.submit(job)

    def query(self, case, exclude_games=(), until: int | None = None, parts=("warnings", "neighbours"),
              k: int | None = None, min_score: float | None = None) -> dict:
        t0 = time.monotonic()
        k = k or config.MEMORY_K
        min_score = config.MEMORY_MIN_SCORE if min_score is None else min_score
        st = self.state
        if st is None:
            return dict(status="no_memory", block=None, ms=0)
        idx = [i for i, e in enumerate(st.entries)
               if e["game"] not in set(exclude_games) and (until is None or e["game"] <= until)]
        if not idx:
            return dict(status="no_hit", block=None, ms=round((time.monotonic() - t0) * 1000), build=st.name)

        lines = mt.parse_invoice_lines(case.invoice_text)
        if not lines:  # unknown invoice layout: one query for the whole case
            lines = [dict(pos=0, text=" ".join(case.description.split())[:300], qty=None, unit="")]
        trade, ed = mt.trade_of(case.invoice_text), mt.edition(case.policy)
        context = f"{trade} | " + " ".join(case.description.split())[:200]
        qtexts = [l["text"] for l in lines]

        # clause matches of the entries' deciding clauses in THIS policy
        new = mt.parse_clauses(case.policy)
        by_hash = {mt.exact_hash(c): c for c in new}
        new_mh = None
        matches: dict[tuple, tuple] = {}  # (game, id) -> (new clause, score, kind)
        need = {(st.entries[i]["game"], cid) for i in idx if usable(st.entries[i])
                for cid in st.entries[i]["hypothesis"]["clause_ids"]}
        for key in need:
            mc = st.clauses.get(key)
            if not mc:
                continue
            if mc["hash"] in by_hash:
                matches[key] = (by_hash[mc["hash"]], 1.0, "same wording")
                continue
            if mc.get("minhash") is None:
                continue
            import numpy as np
            if new_mh is None:
                new_mh = np.stack([mt.minhash(c.body) for c in new]) if new else None
            if new_mh is None:
                continue
            est = (new_mh == mc["minhash"][None, :]).mean(axis=1)
            best = None
            for j in np.nonzero(est >= 0.8)[0]:
                c = new[int(j)]
                if mt.numbers(c.body) != mc["numbers"]:
                    continue
                jac = mt.jaccard(c.body, mc["body"])
                if jac >= 0.6 and (best is None or jac > best[1]):
                    best = (c, jac, f"near-identical wording ({jac:.0%})")
            if best:
                matches[key] = best

        def clause_hit(e):
            if not usable(e):
                return 0.0, None
            hits = [(matches[(e["game"], cid)], cid) for cid in e["hypothesis"]["clause_ids"] if (e["game"], cid) in matches]
            if not hits:
                return 0.0, None
            (c, s, kind), cid = max(hits, key=lambda h: h[0][1])
            return s, (c, s, kind, cid)

        hits_e = {i: clause_hit(st.entries[i]) for i in idx}

        # scores (lines x entries)
        q = embed(qtexts + [context]) if st.vecs is not None else None
        rows = []
        for li, qt in enumerate(qtexts):
            bm = st.bm25.scores(qt)
            row = {}
            for i in idx:
                b = 1 - math.exp(-bm[i] / 3)  # saturating: one shared rare word ~0.5, several ~0.8+
                if q is not None:
                    raw = W_LINE * float(q[li] @ st.vecs[i]) + W_CTX * float(q[-1] @ st.ctx[i])
                    cos = max(raw - COS_FLOOR, 0.0) / (1 - COS_FLOOR)
                else:
                    cos = b
                row[i] = (W_COS * cos + W_BM25 * b + W_CLAUSE * hits_e[i][0]
                          + W_EDITION * (st.entries[i]["edition"] == ed), cos, b)
            rows.append(row)

        out_hits = []
        neigh = []  # per line: [(score, entry index)]
        for li, row in enumerate(rows):
            best = sorted(((v[0], i) for i, v in row.items() if v[0] >= min_score and informative(st.entries[i])),
                          reverse=True)[:k]
            neigh.append(best)
            out_hits += [dict(line=lines[li]["pos"], game=st.entries[i]["game"], entry_line=st.entries[i]["line"],
                              score=round(s, 3), cos=round(row[i][1], 3), bm25=round(row[i][2], 3),
                              clause=round(hits_e[i][0], 2)) for s, i in best]

        # clause warnings: usable entries whose deciding clause is in THIS policy and that resemble some line
        warn = []
        seen = set()
        cand = sorted(((max(r[i][0] for r in rows), i) for i in idx if hits_e[i][1]), reverse=True)
        for s, i in cand:
            if s < min_score - 0.1 or len(warn) >= MAX_WARNINGS:
                continue
            e = st.entries[i]
            c, sc, kind, cid = hits_e[i][1]
            key = (c.id, e["hypothesis"]["outcome"], e["hypothesis"]["clause_effect"])
            if key in seen:
                continue
            seen.add(key)
            h = e["hypothesis"]
            excerpt = mt.condition_excerpt(c.text, anchor=h.get("clause_quote", ""))
            text = (f"- {c.id} {c.title[:60]} ({kind} as game {e['game']} clause {cid}): game {e['game']} line {e['line']} "
                    f"\"{e['text'][:70]}\" was {h['outcome']} ({h['clause_effect']}) because \"{h.get('fact_quote', '')[:140]}\". "
                    f"Condition in THIS policy: \"{excerpt}\"")
            warn.append((text, dict(clause=c.id, game=e["game"], line=e["line"], score=round(s, 3))))

        block = self._block(st, lines, hits_e, warn if "warnings" in parts else [],
                            neigh if "neighbours" in parts else [[] for _ in lines], ed)
        return dict(status="hit" if block else "no_hit", block=block, build=st.name,
                    ms=round((time.monotonic() - t0) * 1000), n_lines=len(lines), hits=out_hits,
                    warnings=[w[1] for w in warn] if "warnings" in parts else [],
                    embed=q is not None, parts=list(parts))

    @staticmethod
    def _block(st: _State, lines, hits_e, warn, neigh, ed: str) -> str | None:
        parts = []
        if warn:
            parts.append("Clauses of THIS policy that decided earlier lines (check whether the condition holds here):")
            parts += [w[0] for w in warn]
        nb_lines = []
        for l, best in zip(lines, neigh):
            if not best:
                continue
            label = f"Line {l['pos']}" if l["pos"] else "This case"
            nb_lines.append(f"{label} \"{l['text'][:60]}\":")
            outcomes = set()
            for s, i in best:
                e = st.entries[i]
                h = e.get("hypothesis") or {}
                if usable(e):
                    outcomes.add(h["outcome"])
                    hs = hits_e[i][1]
                    where = (f"{hs[2]} in THIS policy" if hs else "wording NOT found in this policy")
                    why = f"likely {h['outcome']} ({h['clause_effect']}, clause {', '.join(h['clause_ids'])}; {where})"
                    lesson = f" Lesson: {e['lesson'][:160]}" if e.get("lesson") else ""
                else:
                    why, lesson = "reason unknown", ""
                same = "same edition" if e["edition"] == ed else ""
                nb_lines.append(f"- game {e['game']} line {e['line']} \"{e['text'][:70]}\" ({_qty(e)}, {e['trade']}"
                                f"{', ' + same if same else ''}): {_obs_str(e['observed'])}; {why}.{lesson}")
            if len(outcomes) > 1:
                nb_lines.append("  (these neighbours disagree; the clause and the facts of THIS case decide)")
        if nb_lines:
            parts.append("Similar earlier lines (similar wording can have the opposite outcome under another clause or edition):")
            parts += nb_lines
        if not parts:
            return None
        head = ("Hints from earlier, already settled claims in this tournament. THIS policy and description always win; "
                "reuse an earlier outcome only if the same clause applies here AND its condition holds in this case. "
                "Amounts are lower bounds on the gross total of the whole earlier line, never prices to copy: price THIS "
                "line from its own invoice and description.")
        text = head
        for p in parts:  # stay inside the token budget; later (less important) parts are dropped
            if len(text) + len(p) + 1 > MAX_CHARS:
                break
            text += "\n" + p
        return text


_MEM: Memory | None = None


def get() -> Memory:
    """The process-wide memory (loads the CURRENT build on first use)."""
    global _MEM
    if _MEM is None:
        _MEM = Memory()
        _MEM.load()
    return _MEM


def game_of(path) -> int | None:
    """past-cases/case_007 -> 7 (used to keep later games out of the memory when re-estimating an old case)."""
    m = re.search(r"case_(\d{3})", str(path))
    return int(m.group(1)) if m else None


def wait_block(fut: Future | None, until: float) -> tuple[str | None, dict]:
    """Wait for a submitted query until the monotonic time `until`. Returns (block or None, info for meta.memory)."""
    if fut is None:
        return None, dict(used=False, status="off")
    t = time.monotonic()
    try:
        res = fut.result(timeout=max(until - t, 0))
    except TimeoutError:
        return None, dict(used=False, status="timeout", waited_s=round(time.monotonic() - t, 3))
    except Exception as e:  # noqa: BLE001
        return None, dict(used=False, status="error", error=repr(e))
    info = dict(used=bool(res.get("block")), status=res.get("status"), waited_s=round(time.monotonic() - t, 3),
                ms=res.get("ms"), build=res.get("build"))
    return res.get("block"), info


def summary(fut: Future | None) -> dict | None:
    """Non-blocking summary of a query for the run log."""
    if fut is None:
        return None
    if not fut.done():
        return dict(status="pending")
    r = fut.result()
    return {k: r.get(k) for k in ("status", "ms", "build", "n_lines", "hits", "warnings", "embed", "error") if k in r}

