#!/usr/bin/env python3
"""Numbers the report quotes that no file stores: recomputed here, in the repo.

`doubleblind trace --derive 'python3 examples/gain.py'` adds what this prints to
the evidence pool. The point is not convenience - it is that a reader can run
this line and get the same numbers, which an entry in an allow list would not
give them.
"""
import json
import os

# Resolved against this file, not the working directory. A derivation is a
# command a reader copies out of the README and runs from wherever they happen
# to be; one that only works from the repository root is a trap, and the error
# it produces names the wrong thing.
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "results.json")) as fh:
    r = json.load(fh)
gain = (r["treatment"]["accuracy"] - r["baseline"]["accuracy"]) * 100
print(f"gain_points {gain:.2f}")
for cat, after in r["per_category_accuracy"].items():
    before = r["per_category_accuracy_baseline"][cat]
    print(f"delta_{cat} {(after - before) * 100:.2f}")
