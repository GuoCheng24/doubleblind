#!/usr/bin/env python3
"""Render ledger/findings.json to ledger/README.md.

The prose version is generated so it cannot drift from the data. CI runs this
with --check and fails if the committed file is not what the data produces -
a ledger about drift that had drifted would be a poor advertisement.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "ledger", "README.md")

LAYER = {"mechanical": "a machine that recomputes",
         "reviewer": "a reader with no context",
         "both": "both automated layers"}

HEAD = """\
# The ledger

Real defects that shipped, or reached a publishable artifact, in one
researcher's public repositories. Each entry records **which layer missed it and
why that layer could not have seen it** - not to apportion blame, but because
the pattern is the only thing here that generalises.

This file is generated from `findings.json` by `render.py`. Edit the data.

"""


def render():
    with open(os.path.join(ROOT, "ledger", "findings.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    findings = data["findings"]
    parts = [HEAD]

    by_cat = {}
    for f in findings:
        by_cat.setdefault(f["category"], []).append(f)

    order = ["correct-number-false-sentence", "unexamined-data-column",
             "rendering", "staleness", "tooling"]
    for cat in order + [c for c in sorted(by_cat) if c not in order]:
        if cat not in by_cat:
            continue
        parts.append(f"## {cat.replace('-', ' ')}  ({len(by_cat[cat])})\n")
        for f in by_cat[cat]:
            flag = "  **changed a conclusion**" if f["conclusion_changed"] else ""
            parts.append(f"### `{f['id']}`{flag}\n")
            parts.append(f"*{f['artifact']}*\n")
            parts.append(f"{f['shipped']}\n")
            parts.append(f"- **Missed by:** {LAYER[f['missed_by']]}\n"
                         f"- **Why it could not see it:** {f['why_invisible']}\n"
                         f"- **Caught by:** {f['caught_by']}\n"
                         f"- **Check now:** {f['check_now']}\n")
    parts.append("---\n")
    parts.append("Counts over this file are printed by `summarize.py`, which is what the\n"
                 "top-level README is traced against.\n")
    return "\n".join(parts)


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if current != text:
            sys.exit(f"{OUT} is out of date with findings.json - run: python3 ledger/render.py")
        print(f"{OUT} matches findings.json")
    else:
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {OUT} ({len(text)} bytes)")
