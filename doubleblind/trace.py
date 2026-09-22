"""Trace every number in prose back to a file that was actually committed.

The failure this exists for is not exotic. Someone writes a README, quotes a
result from memory or from an earlier version of a run, and ships. The number
is plausible, the sentence reads well, and nothing in the repository disagrees
with it because nothing in the repository is looking.

What this module does is narrow on purpose: for each number in the prose it
answers *is there a committed value this could be a correct rounding of*, and
nothing else. What it deliberately does **not** do is decide whether the
sentence containing that number is true. A correct number inside a false
sentence passes here every time, and the only thing that catches that is a
reader who does not already know what the answer was supposed to be. That is
the other half of this repository, and the reason it is called doubleblind.

Design notes, each one paid for by something that shipped broken:

* **Anchoring.** ``79.75`` must not match inside ``179.751``. Every pattern is
  bounded with lookarounds rather than ``\\b``, which treats ``.`` as a
  boundary and happily matches the ``75`` in ``79.75``.
* **Precision is a claim.** Prose that says ``88.4`` claims one decimal, so
  ``0.88449`` supports it and ``0.885`` does not support ``88.4`` being written
  as ``88.50``. Tolerance is therefore half an ulp *at the precision the prose
  chose*, not a fixed epsilon.
* **Counts are exact.** If both the prose number and the stored value are
  integers, rounding is not on offer: ``11`` means 11.
* **Digits are not the whole story.** "two thirds to four fifths" shipped in
  place of 64.4%-81.2% and every digit-based check passed it, because it has no
  digits. Spelled-out quantities are reported as uncheckable rather than
  ignored.
* **Percent scaling both ways.** Data files store ``0.8845``; prose says
  ``88.45``. Which scale matched is printed, so a genuine off-by-100 is still
  visible to a reader of the report.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
from dataclasses import dataclass, field

__all__ = [
    "Number", "Value", "Finding",
    "extract_numbers", "load_evidence", "run_derivations", "vague_quantities", "trace",
]

# ---------------------------------------------------------------- extraction

# A numeric literal, anchored so it cannot start or end inside a longer one.
# Accepts thousands separators and a trailing percent sign.
# Trailing guard rejects only a dot that starts more digits (part of a longer
# decimal or a version), never a sentence-ending period - "...reached 1079.75."
# must still be seen.
_NUM = re.compile(r"(?<![\w.])(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)(%?)(?!\w|\.\d)")

# Spans removed before extraction, in this order. Each one is a place where
# digits appear that are not claims about results.
_FENCE = re.compile(r"^[ \t]*(?:```|~~~).*?^[ \t]*(?:```|~~~)[ \t]*$", re.S | re.M)
_URL = re.compile(r"(?:https?://|www\.)\S+")
_MDLINK_TARGET = re.compile(r"\]\([^)]*\)")
_IMG = re.compile(r"!\[[^\]]*\]")
_HTMLATTR = re.compile(r"<[^>]+>")
_ISODATE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?")
_CLOCK = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?::\d{2})?(?!\d)")
# A hex digest must contain at least one a-f, or this masks a seven-figure
# count - 1234567 is a number somebody may be quoting.
_SHA = re.compile(r"(?<![\w])(?=[0-9a-f]{7,40}(?![\w]))[0-9a-f]*[a-f][0-9a-f]*")
# Semantic versions are never result claims and cannot be read as one number.
_SEMVER = re.compile(r"(?<![\w.])\d+\.\d+\.\d+(?![\w.])")
_FOOTNOTE = re.compile(r"\[\^?\d+\]")

_MASKS = [_FENCE, _IMG, _MDLINK_TARGET, _URL, _HTMLATTR, _ISODATE, _CLOCK, _SEMVER, _SHA, _FOOTNOTE]


@dataclass
class Number:
    """A numeric literal found in prose."""
    raw: str
    value: float
    decimals: int
    percent: bool
    line_no: int
    line: str

    @property
    def is_int(self) -> bool:
        return self.decimals == 0 and float(self.value).is_integer()

    def __str__(self) -> str:
        return self.raw


def _mask(text: str) -> str:
    """Blank out spans whose digits are never result claims, preserving offsets.

    Offsets are preserved (spaces replace the span, newlines kept) so that line
    numbers reported to the user still point at the right line.
    """
    out = text
    for pat in _MASKS:
        out = pat.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), out)
    return out


def extract_numbers(text: str, skip_code_fences: bool = True) -> list[Number]:
    """Every numeric literal in ``text`` that could be a claim about a result."""
    masked = _mask(text) if skip_code_fences else _mask(text.replace("```", "   "))
    lines = text.splitlines()
    found: list[Number] = []
    for m in _NUM.finditer(masked):
        raw, pct = m.group(1), m.group(2)
        digits = raw.replace(",", "")
        dec = len(digits.split(".")[1]) if "." in digits else 0
        line_no = masked.count("\n", 0, m.start()) + 1
        found.append(Number(
            raw=raw + pct,
            value=float(digits),
            decimals=dec,
            percent=bool(pct),
            line_no=line_no,
            line=lines[line_no - 1].strip() if line_no <= len(lines) else "",
        ))
    return found


# ------------------------------------------------------------------ evidence

@dataclass
class Value:
    """A number that exists in a committed file."""
    value: float
    source: str      # file path
    where: str       # dotted json path, or row/col, or line number


def _walk_json(node, path, out, source):
    if isinstance(node, bool):
        return
    if isinstance(node, (int, float)):
        out.append(Value(float(node), source, path or "$"))
    elif isinstance(node, dict):
        for k, v in node.items():
            _walk_json(v, f"{path}.{k}" if path else str(k), out, source)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk_json(v, f"{path}[{i}]", out, source)
    elif isinstance(node, str):
        # numbers stored as strings are still numbers a reader will quote
        s = node.strip().rstrip("%")
        try:
            out.append(Value(float(s), source, path or "$"))
        except ValueError:
            pass


def _from_text(text: str, source: str, out: list[Value]) -> None:
    for i, line in enumerate(text.splitlines(), 1):
        for m in _NUM.finditer(line):
            try:
                out.append(Value(float(m.group(1).replace(",", "")), source, f"line {i}"))
            except ValueError:
                pass


def run_derivations(commands: list[str], cwd: str | None = None) -> list[Value]:
    """Numbers printed by a committed script count as evidence too.

    Per-task accuracies, paired gains and medians usually live in no file: a
    script recomputes them from per-item records each time. Refusing to trace
    them would push the honest response - commit the script - into an allow
    list, where it stops being checkable. So a derivation is a command whose
    stdout is scanned for numbers, recorded with the command as its source.

    The discipline survives because the command is in the repository: a reader
    runs the same line and gets the same numbers, or does not.
    """
    import subprocess
    out: list[Value] = []
    for cmd in commands:
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                  cwd=cwd, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            raise SystemExit(f"derivation failed to start: {cmd}\n  {exc}")
        if proc.returncode != 0:
            raise SystemExit(
                f"derivation exited {proc.returncode}: {cmd}\n"
                f"  A derivation that cannot run is not evidence.\n"
                f"{proc.stderr.strip()[:800]}")
        _from_text(proc.stdout, f"$({cmd})", out)
    return out


def load_evidence(paths: list[str]) -> list[Value]:
    """Read every number out of the given files or directories.

    JSON keeps its dotted path so the report can say exactly where a number
    lives. CSV keeps row and column. Anything else is scanned as text, which is
    lossy but means a log file or a results table in Markdown still counts as
    evidence.
    """
    files: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                # Skip hidden directories, but "." and ".." are ordinary path
                # components - treating them as hidden silently drops every
                # relative path the user is most likely to type.
                if any(part.startswith(".") and part not in (".", "..")
                       for part in root.split(os.sep)):
                    continue
                for n in sorted(names):
                    if not n.startswith("."):
                        files.append(os.path.join(root, n))
        else:
            files.append(p)

    out: list[Value] = []
    for f in sorted(set(files)):
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except OSError:
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext == ".json":
            try:
                _walk_json(json.loads(raw), "", out, f)
                continue
            except json.JSONDecodeError:
                pass  # fall through to the text scanner
        elif ext == ".jsonl":
            ok = True
            for i, line in enumerate(raw.splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    _walk_json(json.loads(line), f"[{i}]", out, f)
                except json.JSONDecodeError:
                    ok = False
                    break
            if ok:
                continue
        elif ext in (".csv", ".tsv"):
            delim = "\t" if ext == ".tsv" else ","
            try:
                rows = list(csv.reader(io.StringIO(raw), delimiter=delim))
            except csv.Error:
                rows = []
            head = rows[0] if rows else []
            for r, row in enumerate(rows[1:], 2) if len(rows) > 1 else []:
                for c, cell in enumerate(row):
                    try:
                        v = float(cell.strip().rstrip("%").replace(",", ""))
                    except ValueError:
                        continue
                    col = head[c] if c < len(head) else f"col{c}"
                    out.append(Value(v, f, f"row {r}, {col}"))
            if rows:
                continue
        _from_text(raw, f, out)
    return out


# ------------------------------------------------------------------ matching

def _supports(n: Number, v: Value) -> str | None:
    """Return the scale that makes ``v`` support ``n``, or None."""
    # Only two scales. A stored fraction quoted as a percentage (0.8845 ->
    # 88.45) is the everyday case and is safe, because a stored value in [0,1]
    # with four decimals almost never coincides with an unrelated one. The
    # reverse (/100) is not a real pattern and is a large source of false
    # matches: in a pool holding per-item integers, "88.45" would be declared
    # traced by any stored 8845.
    for scale, label in ((1.0, ""), (100.0, " x100")):
        scaled = v.value * scale
        if n.is_int:
            # A whole number in prose is almost always a count, and a count is
            # not a rounding: "11 items" is not supported by a stored 10.6.
            # The cost is a false alarm when someone rounds a mean to a whole
            # number, and the fix for that - write 10.6, or say in the allow
            # file why 11 is right - leaves better prose behind either way.
            if float(scaled).is_integer() and int(scaled) == int(n.value):
                return label or "exact"
            continue
        tol = 0.5 * 10 ** (-n.decimals) + 1e-9
        if abs(scaled - n.value) <= tol:
            return label or "exact"
    return None


# ------------------------------------------------------------- vague amounts

_WORD_FRACTIONS = [
    "half", "a third", "two thirds", "one third", "three quarters", "a quarter",
    "two fifths", "three fifths", "four fifths", "one fifth", "nine tenths",
    "a tenth", "two thirds to four fifths",
]
_VAGUE = [
    "almost all", "nearly all", "the vast majority", "most of", "a handful of",
    "roughly half", "about half", "the bulk of", "several times",
    "an order of magnitude", "orders of magnitude",
]


def vague_quantities(text: str) -> list[tuple[int, str, str]]:
    """Quantities written as words, which no digit-based check can see.

    This is here because "two thirds to four fifths" once shipped where the data
    said 64.4% to 81.2% - a bound stated tighter than the evidence supported,
    through prose that contained no digits at all.
    """
    masked = _FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    lines = masked.splitlines()
    lowered = masked.lower()
    spans = []
    for phrase in _WORD_FRACTIONS + _VAGUE:
        for m in re.finditer(r"(?<![\w-])" + re.escape(phrase) + r"(?![\w-])", lowered):
            spans.append((m.start(), m.end(), phrase))
    # Drop a match that sits entirely inside a longer one ("two thirds" inside
    # "two thirds to four fifths"), but keep separate matches on the same line -
    # deduplicating by line number hid the second half of a stated range.
    keep = [s for s in spans
            if not any(o is not s and o[0] <= s[0] and s[1] <= o[1] and
                       (o[1] - o[0]) > (s[1] - s[0]) for o in spans)]
    out = []
    for start, _end, phrase in sorted(set(keep)):
        line_no = masked.count("\n", 0, start) + 1
        line = lines[line_no - 1].strip() if line_no <= len(lines) else ""
        out.append((line_no, phrase, line))
    return out


# -------------------------------------------------------------------- result

@dataclass
class Finding:
    number: Number
    verdict: str                     # "traced" | "unsupported" | "allowed"
    matched: Value | None = None
    scale: str = ""
    reason: str = ""                 # for "allowed"
    nearest: list[Value] = field(default_factory=list)


def trace(prose: str, evidence: list[Value], allow: dict[str, str] | None = None) -> list[Finding]:
    """Decide, for every number in ``prose``, whether a committed value supports it."""
    allow = allow or {}
    findings: list[Finding] = []
    for n in extract_numbers(prose):
        key = n.raw.rstrip("%")
        if key in allow:
            findings.append(Finding(n, "allowed", reason=allow[key]))
            continue
        hit = None
        for v in evidence:
            scale = _supports(n, v)
            if scale:
                hit = (v, scale)
                break
        if hit:
            findings.append(Finding(n, "traced", matched=hit[0], scale=hit[1]))
        else:
            nearest = sorted(
                evidence,
                key=lambda v: min(abs(v.value - n.value), abs(v.value * 100 - n.value)),
            )[:3]
            findings.append(Finding(n, "unsupported", nearest=nearest))
    return findings
