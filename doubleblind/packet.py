"""Assemble a review packet, and refuse to send one that gives the answer away.

A reviewer with no context is only useful while it stays without context. The
way that property is lost is almost never dramatic - nobody pastes the
conversation. It is lost in the request itself:

    "Confirm that all four estimators fall below the card number."

There is exactly one way to answer that and still sound useful, and the model
takes it. The same request without its answer -

    "For each numeric claim, state what these files actually support."

- cannot be answered by agreeing, because it does not contain anything to agree
  with.

So this module does two things. It builds a packet out of the artifact and the
evidence it rests on, and it reads the instructions you were about to send and
tells you which phrases have the conclusion in them. The second is the part
that matters; the first is bookkeeping.

The patterns below are not a style guide. Each is a way a request stops being a
question, grouped by the mechanism rather than the wording, because the wording
changes and the mechanism does not.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass

__all__ = ["Leak", "intent_leaks", "build_packet", "packet_fingerprint", "REVIEWER_BRIEF"]


@dataclass
class Leak:
    line_no: int
    phrase: str
    mechanism: str
    line: str
    fix: str


# (regex, mechanism, suggested rewrite)
_PATTERNS: list[tuple[str, str, str]] = [
    # --- the request contains its own answer -------------------------------
    (r"\b(?:please\s+)?(?:confirm|verify|validate|make sure|ensure)\s+(?:that|the|these|this|all|it)\b",
     "answer-in-the-request",
     "Ask what the evidence supports, not whether a stated thing is true: "
     "'state what these files support' instead of 'confirm that X'."),
    (r"(?:^|(?<=[.!?])\s+|\bplease\s+|\bcan you\s+|\bcould you\s+)check\s+that\b",
     "answer-in-the-request",
     "'Check that X' presumes X. 'Check whether X' does not - or better, ask "
     "what the evidence gives."),
    (r"\bdouble[- ]check\b",
     "answer-in-the-request",
     "'Double-check' presumes a first check that passed. Ask for a first check."),
    (r"\b(?:is|are|does|do|was|were)\s+(?:this|that|it|the\s+\w+)\s+(?:correct|right|accurate|fine|ok|okay)\b\s*\?",
     "answer-in-the-request",
     "A yes/no question about correctness invites yes. Ask for the derivation instead."),

    # --- the conclusion is stated before the review ------------------------
    (r"\bwe\s+(?:show|find|demonstrate|prove|establish|conclude)\b",
     "conclusion-stated",
     "Remove the claim from the brief. The artifact can state it; the request must not."),
    (r"\b(?:as|which is)\s+expected\b",
     "conclusion-stated",
     "Delete. It tells the reviewer which outcome is the acceptable one."),
    (r"\bthis\s+(?:demonstrates|proves|confirms|establishes|shows)\b",
     "conclusion-stated",
     "Delete; let the reviewer decide what it demonstrates."),
    (r"\bthe\s+(?:result|answer|number|conclusion)\s+should\s+be\b",
     "conclusion-stated",
     "Stating the expected value makes disagreement a contradiction of you."),

    # --- polarity steering --------------------------------------------------
    (r"\b(?:should|ought to|is supposed to|must)\s+(?:be|show|give|match|agree)\b",
     "polarity-steering",
     "Replace the expectation with the question: 'what do the files give?'"),
    (r"\b(?:obviously|clearly|of course|naturally|needless to say)\b",
     "polarity-steering",
     "These words mark a claim as not-up-for-review. Remove them."),
    (r"\b(?:minor|small|cosmetic|trivial)\s+(?:issue|problem|change|fix)\b",
     "polarity-steering",
     "Pre-sizing a problem tells the reviewer how seriously to take it."),

    # --- social pressure ----------------------------------------------------
    (r"\bI\s+(?:already\s+)?(?:checked|verified|confirmed|tested|reviewed)\b",
     "social-pressure",
     "Saying you checked makes a finding an accusation. Leave it out."),
    (r"\bI'?m\s+(?:fairly\s+|pretty\s+|quite\s+)?(?:sure|confident|certain)\b",
     "social-pressure",
     "Stating your confidence sets the bar a finding has to clear."),
    (r"\b(?:quick|brief|fast|light)\s+(?:sanity\s+)?(?:check|look|pass|review)\b",
     "social-pressure",
     "Asking for a quick look licenses a shallow one."),
    (r"\b(?:just|only)\s+(?:need|want)\s+(?:you\s+)?to\b",
     "social-pressure",
     "Minimising the task lowers the effort it gets."),

    # --- scope narrowing ----------------------------------------------------
    (r"\b(?:ignore|skip|don'?t worry about|no need to (?:check|look at))\b",
     "scope-narrowing",
     "Exclusions hide exactly where the problem is. If something is out of "
     "scope, remove it from the packet instead of naming it."),
    (r"\b(?:only|just)\s+(?:look at|check|review|consider)\b",
     "scope-narrowing",
     "Narrowing the scope in the brief pre-decides where the error is not."),

    # --- authorship leak ----------------------------------------------------
    (r"\b(?:my|our)\s+(?:readme|paper|repo|repository|result|analysis|code|figure|draft)\b",
     "authorship-leak",
     "Ownership words make the reviewer a guest in your work. Refer to it as "
     "'the attached document'."),
    (r"\bI\s+(?:wrote|made|built|produced|ran)\b",
     "authorship-leak",
     "Same: the reviewer should not know who produced the artifact."),
]

_COMPILED = [(re.compile(p, re.I), mech, fix) for p, mech, fix in _PATTERNS]


def intent_leaks(text: str) -> list[Leak]:
    """Phrases in a review request that tell the reviewer what to conclude."""
    out: list[Leak] = []
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith(">"):
            continue  # quoted material is the artifact, not the request
        for rx, mech, fix in _COMPILED:
            for m in rx.finditer(line):
                out.append(Leak(i, m.group(0).strip(), mech, line.strip(), fix))
    return out


REVIEWER_BRIEF = """\
You are reviewing an attached document against the data files attached with it.

You have not seen this work before and you are not being told what it concluded.
Do not try to infer what answer is wanted; there is no wanted answer.

For every numeric claim and every causal or comparative claim in the document:

1. Name the file and field that would settle it.
2. State what that file actually contains.
3. Say whether the sentence in the document follows from it - not whether the
   number matches, but whether the sentence follows. A correct number inside a
   sentence that does not follow from it is the most common defect here and the
   one you are most needed for.

Report each finding as:

    <file>:<line>  CLAIM: "<quoted sentence>"
                   EVIDENCE: <what the data says>
                   COMMAND: <one shell command that settles it>

A finding with no command is an opinion. Drop it or turn it into one.

If a claim is supported, say so and move on. Do not pad the report, and do not
soften a finding because the rest of the document is careful.
"""


def packet_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_packet(artifacts: list[str], evidence: list[str], brief: str | None = None,
                 max_bytes: int = 400_000) -> str:
    """Return a single self-contained packet: brief, artifacts, evidence.

    Nothing about how the artifact came to exist goes in - no commit messages,
    no changelog, no summary of what was tried. Those are the parts that carry
    intent, and they are the reason this function takes explicit paths rather
    than a repository.
    """
    parts = [brief if brief is not None else REVIEWER_BRIEF, ""]

    def _emit(path: str, kind: str) -> None:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except OSError as exc:
            parts.append(f"<<{kind} {path}: unreadable: {exc}>>")
            return
        if len(raw) > max_bytes:
            raw = raw[:max_bytes] + f"\n<<truncated at {max_bytes} bytes>>\n"
        parts.append(f"===== {kind}: {path} =====")
        parts.append(raw.rstrip())
        parts.append("")

    files: list[str] = []
    for p in evidence:
        if os.path.isdir(p):
            for root, _d, names in os.walk(p):
                if any(part.startswith(".") and part not in (".", "..")
                       for part in root.split(os.sep)):
                    continue
                files += [os.path.join(root, n) for n in sorted(names) if not n.startswith(".")]
        else:
            files.append(p)

    for a in artifacts:
        _emit(a, "DOCUMENT UNDER REVIEW")
    for f in sorted(set(files)):
        _emit(f, "DATA FILE")
    return "\n".join(parts)
