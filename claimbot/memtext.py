"""Text helpers for the case memory, shared by the offline build (memory_build.py) and the online query (memory.py).

  parse_clauses        numbered policy clauses (headings like "2.3.3 Overvoltage caused by lightning")
  clause fingerprints  exact hash (numbers and cross-references kept) + MinHash for paraphrase candidates
  parse_invoice_lines  invoice positions (text, quantity, unit) from the pypdf / invoice.txt layout
  edition, trade_of    which policy edition and which trade a case belongs to

Pure stdlib; numpy is imported only for MinHash. Everything here only READS case text, it never executes it.
"""

import hashlib
import re
import zlib
from dataclasses import dataclass

from .invoice_quantity import QUANTITY, parse_quantity


# --- policy clauses ---------------------------------------------------------------------------------------------------

HEADING = re.compile(r"^(\d+(?:\.\d+){1,3})\s+([A-Z].*)$")
SLACK = 3  # numbering may skip a few numbers, but no more


@dataclass
class Clause:
    id: str      # "2.3.3"
    title: str   # rest of the heading line (cut to 90 chars)
    text: str    # heading + body, whitespace collapsed, paragraphs separated by "\n"
    line: int    # 1-based line of the heading in policy.txt

    @property
    def body(self) -> str:
        """Text without the leading clause number (numbering may differ between editions; the wording counts)."""
        return self.text[len(self.id):].strip()


def _key(cid: str) -> tuple[int, ...]:
    return tuple(int(x) for x in cid.split("."))


def _successor(last: tuple[int, ...] | None, new: tuple[int, ...]) -> bool:
    """Is `new` a plausible next heading after `last`? (monotone, same parent group, small steps)"""
    if last is None:
        return all(x <= 20 for x in new)
    if len(new) == len(last) + 1 and new[:-1] == last and new[-1] <= SLACK:  # first child: 2.3 -> 2.3.1
        return True
    for i in range(len(last)):  # next sibling at level i, optionally opening children: 2.3.10 -> 2.4 / 2.4.1 / 3.1
        if len(new) > i and new[:i] == last[:i] and last[i] < new[i] <= last[i] + SLACK \
                and all(x <= SLACK for x in new[i + 1:]):
            return True
    return False


def _section_break(s: str) -> bool:
    """Top-level markers that end a clause without starting a numbered one (PART 2 ..., ====, ALL-CAPS headings)."""
    return s.startswith("===") or bool(re.match(r"^(PART|SECTION|ANNEX|APPENDIX|SCHEDULE)\b", s)) or (len(s) > 3 and s.isupper())


def parse_clauses(policy: str) -> list[Clause]:
    """A heading is a line `^\\d+(\\.\\d+){1,3}\\s+[A-Z]` whose PREVIOUS line is blank (or ends a sentence) and whose
    number fits the running outline. Wrapped cross-references ("...set out in\\n2.3.3 and no other") therefore never start
    a clause."""
    lines = policy.splitlines()
    out: list[Clause] = []
    cur: list | None = None  # [id, title, paragraphs(list[list[str]]), line]
    last = None

    def close():
        if cur:
            text = "\n".join(" ".join(" ".join(p).split()) for p in cur[2] if p)
            out.append(Clause(cur[0], cur[1][:90], text, cur[3]))

    for i, raw in enumerate(lines):
        s = raw.strip()
        prev_blank = i == 0 or not lines[i - 1].strip()
        # a heading follows a blank line, or a line that ends a sentence (short-form lists "2.1 ... .\n2.2 ...")
        prev_ok = prev_blank or lines[i - 1].rstrip().endswith((".", ";", ":"))
        m = HEADING.match(s)
        if m and prev_ok:
            k = _key(m.group(1))
            if _successor(last, k):
                close()
                # a title-only heading ("2.3.3 Overvoltage caused by lightning") is its own paragraph; an inline one
                # ("9.1.5 Appliances insured under 2.3.3 must be ...") runs on into its sentence
                title_only = len(s) <= 80 and not s.endswith((".", ",", ";", ":")) and (
                    i + 1 >= len(lines) or not lines[i + 1].strip() or lines[i + 1].strip()[:1].isupper())
                cur, last = [m.group(1), m.group(2).strip(), [[s], []] if title_only else [[s]], i + 1], k
                continue
        if cur is None:
            continue
        if not s:
            if cur[2][-1]:
                cur[2].append([])
            continue
        if prev_blank and _section_break(s):
            close()
            cur = None
            continue
        cur[2][-1].append(s)
    close()
    return out


def norm(s: str) -> str:
    """Lower-case, unify quotes and dashes, collapse whitespace. Numbers are kept."""
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("–", "-").replace("—", "-")
    return " ".join(s.lower().split())


NUM = re.compile(r"\d+(?:[.,]\d+)*")


def exact_hash(c: Clause) -> str:
    return hashlib.sha1(norm(c.body).encode()).hexdigest()[:16]


def numbers(s: str) -> list[str]:
    """Every number in the text (amounts, percentages, cross-references), sorted, so 500 vs 5,000 never look alike."""
    return sorted(set(NUM.findall(s)))


def shingles(s: str, n: int = 5) -> set[str]:
    w = re.findall(r"[a-z0-9]+(?:[.,][0-9]+)*", norm(s))
    return {" ".join(w[i:i + n]) for i in range(max(len(w) - n + 1, 1))} if w else set()


N_PERM = 64
_P = 4294967311  # prime > 2^32
_perm = None


def minhash(s: str):
    """64-value MinHash signature (numpy uint64 array) of the 5-word shingles. Only used to find paraphrase candidates."""
    import numpy as np
    global _perm
    if _perm is None:
        rng = np.random.default_rng(20261121)
        _perm = (rng.integers(1, 2**31, N_PERM, dtype=np.uint64), rng.integers(0, 2**31, N_PERM, dtype=np.uint64))
    sh = shingles(s)
    if not sh:
        return np.full(N_PERM, _P, dtype=np.uint64)
    x = np.array([zlib.crc32(t.encode()) for t in sh], dtype=np.uint64)
    a, b = _perm
    return ((x[None, :] * a[:, None] + b[:, None]) % np.uint64(_P)).min(axis=1)


def jaccard(a: str, b: str) -> float:
    sa, sb = shingles(a), shingles(b)
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


SENT = re.compile(r"(?<=[.;:])\s+(?=[A-Z(\"'])")
CONDITION = re.compile(r"\b(where|unless|only|except|provided|does not apply|no reduction|not covered|excluded|exclusion|"
                       r"one half|sub-limit|in the aggregate|rateably|deductible|not agreed|endorsement|not a repair cost|"
                       r"not itself|is not|are not)\b", re.I)


def sentences(text: str) -> list[str]:
    return [s.strip() for p in text.split("\n") for s in SENT.split(p) if s.strip()]


def condition_excerpt(clause_text: str, anchor: str = "", max_words: int = 100) -> str:
    """The sentences of a clause that carry its condition and exceptions, in their original order: always the sentence
    closest to `anchor` (the quote from the earlier case), then as many sentences with condition words as fit."""
    sents = sentences(clause_text)[1:] or sentences(clause_text)  # [0] is the heading paragraph
    if not sents:
        return ""
    a = -1
    if anchor:
        aw = set(norm(anchor).split())
        a = max(range(len(sents)), key=lambda j: len(aw & set(norm(sents[j]).split())) / (len(aw) or 1))
    keep = {a} if a >= 0 else set()
    n = len(sents[a].split()) if a >= 0 else 0
    for j in sorted(range(len(sents)), key=lambda j: (abs(j - a), j < a)):  # nearest to the anchor first, the following before the preceding
        s = sents[j]
        if j not in keep and CONDITION.search(s) and n + len(s.split()) <= max_words:
            keep.add(j)
            n += len(s.split())
    out = " ".join(sents[j] for j in sorted(keep))
    w = out.split()
    return out if len(w) <= max_words + 40 else " ".join(w[:max_words + 40]) + " ..."


# --- invoice lines ----------------------------------------------------------------------------------------------------

_UNIT = r"[A-Za-z][A-Za-z0-9²³/.]*(?:\s[a-z]+)?"
QTY_ONLY = re.compile(rf"^({QUANTITY})\s+({_UNIT})$")          # "2 hrs", "0.2 m2", "1 flat rate"
QTY_END = re.compile(rf"^(.*\S)\s+({QUANTITY})\s+({_UNIT})$")    # "Hole drilling 1 pcs"
POS_START = re.compile(r"^(\d+)\s+(\S.*)$")


def _finish(item: dict) -> dict:
    rows = item["rows"]
    qty, unit, text_rows = None, "", rows
    m = QTY_ONLY.match(rows[-1]) if len(rows) > 1 else None
    if m:
        qty, unit, text_rows = parse_quantity(m.group(1)), m.group(2), rows[:-1]
    else:
        m = QTY_END.match(rows[-1])
        if m:
            qty, unit, text_rows = parse_quantity(m.group(2)), m.group(3), rows[:-1] + [m.group(1)]
    text = ""
    for r in text_rows:
        text = (text + r) if text.endswith("-") else (text + " " + r).strip()
    return dict(pos=item["pos"], text=text.strip(), qty=qty, unit=unit)


def parse_invoice_lines(invoice_text: str) -> list[dict]:
    """[{pos, text, qty, unit}] in invoice order (pos is the printed 1-based POS.). Empty list when the layout is unknown.

    Handles descriptions wrapped over several lines, the quantity on its own line ("2 hrs") and a description line that
    itself ends in "number unit" ("approx. 0.2 m2" followed by "0.2 m2")."""
    items: list[dict] = []
    cur = None
    inside = False
    for raw in invoice_text.splitlines():
        s = raw.strip()
        if s.startswith("POS.") and "DESCRIPTION" in s:
            inside = True
            continue
        if not inside or not s:
            continue
        if s == "INVOICE" or s.startswith("Created on") or s.startswith("Page "):
            inside = False
            continue
        m = POS_START.match(s)
        expected = (cur["pos"] if cur else (items[-1]["pos"] if items else 0)) + 1
        cur_has_qty = cur is not None and bool(QTY_ONLY.match(cur["rows"][-1]) or QTY_END.match(cur["rows"][-1]))
        if m and int(m.group(1)) == expected and (cur is None or cur_has_qty) \
                and not (cur is not None and QTY_ONLY.match(s) and not cur_has_qty):
            if cur:
                items.append(_finish(cur))
            cur = dict(pos=expected, rows=[m.group(2)])
        elif cur is not None:
            cur["rows"].append(s)
    if cur:
        items.append(_finish(cur))
    return items


# --- edition and trade ------------------------------------------------------------------------------------------------

def edition(policy: str) -> str:
    head = " ".join(policy[:2000].split())
    m = re.search(r'Policy wording "([^"]+)"\s*-\s*(.+?)\s+Edition\b', head)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    names = []
    for ln in policy.splitlines()[:20]:
        s = ln.strip()
        low = s.lower()
        if not s or s.startswith("=") or "mock" in low or "generic" in low or "no real contract" in low or "invented" in low:
            continue
        names.append(s)
        if len(names) == 2:
            break
    return " / ".join(names)


def trade_of(invoice_text: str) -> str:
    lines = [l.strip() for l in invoice_text.splitlines()]
    out = []
    for i, s in enumerate(lines):
        if s == "TRADE":
            nxt = next((x for x in lines[i + 1:] if x), "")
            if nxt and nxt not in out:
                out.append(nxt)
    if not out:  # pdftotext -layout: header row then a value row
        m = re.search(r"INVOICE NO\.\s+DATE\s+DUE\s+TRADE\s*\n\s*(\S+)\s+(.+?)\s{2,}(.+?)\s{2,}(.+)", invoice_text)
        if m:
            out.append(m.group(4).strip())
    return " / ".join(out)
