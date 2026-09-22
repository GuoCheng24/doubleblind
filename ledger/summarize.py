#!/usr/bin/env python3
"""Aggregate counts over ledger/findings.json.

Every count this repository quotes about its own evidence is printed here, so
`doubleblind trace README.md --data ledger/findings.json --derive 'python3
ledger/summarize.py'` can check the README against the ledger it describes. A
repository that asks people to trace their numbers should be traceable.
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "ledger", "findings.json"), encoding="utf-8") as fh:
    F = json.load(fh)["findings"]


def emit(name, value):
    print(f"{name} {value}")


emit("total_findings", len(F))
emit("conclusion_changing", sum(1 for f in F if f["conclusion_changed"]))

for field in ("missed_by", "caught_by", "category"):
    for key, n in sorted(collections.Counter(f[field] for f in F).items()):
        emit(f"{field}_{key.replace(' ', '_').replace('-', '_')}", n)

run1 = [f for f in F if f.get("source") == "fresh-eyes-run-1"]
emit("fresh_eyes_run1_verified", len(run1))
emit("fresh_eyes_run1_correct_number_false_sentence",
     sum(1 for f in run1 if f["category"] == "correct-number-false-sentence"))

own = [f for f in F if f.get("source") == "doubleblind-itself"]
emit("defects_in_this_repository", len(own))

missed_by_mechanical = sum(1 for f in F if f["missed_by"] in ("mechanical", "both"))
emit("missed_by_a_mechanical_check", missed_by_mechanical)

human = [f for f in F if f["caught_by"] == "human eye"]
emit("caught_by_human_eye_that_were_rendering",
     sum(1 for f in human if f["category"] == "rendering"))

with open(os.path.join(ROOT, "ledger", "findings.json"), encoding="utf-8") as fh:
    CTX = json.load(fh).get("context", {})
for group, block in CTX.items():
    for k, v in block.items():
        if not k.startswith("_"):
            emit(f"{group}_{k}", v)

if "--table" in sys.argv:
    print()
    for f in F:
        print(f"{f['id']:<28} {f['missed_by']:<10} {f['category']}")
