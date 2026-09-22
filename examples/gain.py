#!/usr/bin/env python3
"""Numbers the report quotes that no file stores: recomputed here, in the repo.

`doubleblind trace --derive 'python3 examples/gain.py'` adds what this prints to
the evidence pool. The point is not convenience - it is that a reader can run
this line and get the same numbers, which an entry in an allow list would not
give them.
"""
import json

with open("examples/results.json") as fh:
    r = json.load(fh)
gain = (r["treatment"]["accuracy"] - r["baseline"]["accuracy"]) * 100
print(f"gain_points {gain:.2f}")
for cat, after in r["per_category_accuracy"].items():
    before = r["per_category_accuracy_baseline"][cat]
    print(f"delta_{cat} {(after - before) * 100:.2f}")
