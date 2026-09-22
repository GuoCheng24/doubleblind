#!/usr/bin/env python3
"""Numbers the README states about the figure layer, printed from the code and
the example data rather than typed into prose.

    doubleblind trace README.md --derive 'python3 examples/figure_facts.py'
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from doubleblind.render import READABLE_PX, UNFURL_SCALE  # noqa: E402

CANVAS_PX = 1200                       # the width the example figures are drawn at

print(f"unfurl_scale {UNFURL_SCALE}")
print(f"readable_px {READABLE_PX:.0f}")
print(f"legibility_floor_pt {READABLE_PX / UNFURL_SCALE:.0f}")
print(f"canvas_px {CANVAS_PX}")
print(f"unfurled_px {CANVAS_PX * UNFURL_SCALE:.0f}")

# the two slopes in examples/broken/figure_reads_backwards.py
XS = [1.0, 1.1, 1.2, 5.0, 5.1, 5.2]
YS = [2.0, 5.0, 8.0, 3.0, 6.0, 9.0]
n = len(XS)
mx, my = sum(XS) / n, sum(YS) / n
pooled = sum((x - mx) * (y - my) for x, y in zip(XS, YS)) / sum((x - mx) ** 2 for x in XS)
within = (YS[2] - YS[0]) / (XS[2] - XS[0])
print(f"pooled_slope {pooled:.2f}")
print(f"within_family_slope {within:.0f}")
