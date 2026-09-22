"""The 1200x630 card GitHub shows when the link is shared.

The chart is read from ledger/findings.json, so it cannot drift from the data
it summarises - and the honest bar is the biggest one: a person looking at the
rendered artifact caught more of these than either automated layer. That is the
number this repository exists to shrink.

Built through cardkit, which refuses to write a card that fails its own
legibility, contrast and collision audit at the ~360 px a link unfurl gives it.
That floor is why the rows are set at 34 pt and why there are four of them.
"""
import collections
import json
import pathlib
import sys

from matplotlib.patches import Rectangle

sys.path.insert(0, str(pathlib.Path.home() / "bin"))
from cardkit import INK, SANS, card  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
with open(ROOT / "ledger" / "findings.json", encoding="utf-8") as fh:
    FINDINGS = json.load(fh)["findings"]

# Short labels for the card. Two different kinds of first real use - running it
# on a real repository, and installing it into a clean virtualenv and following
# the README from elsewhere - are one bar, because on a card they are one idea.
LABEL = {
    "human eye": "your own eyes",
    "zero-context reviewer": "a different model",
    "test": "a test",
    "running it on a real repository": "first real use",
    "running it on a real figure": "first real use",
    "installing it into a clean virtualenv and following the README from elsewhere":
        "first real use",
}
COUNTS = collections.Counter(f["caught_by"] for f in FINDINGS)
missing = sorted(set(COUNTS) - set(LABEL))
if missing:
    # A new catcher must be given a label rather than silently dropped from the
    # chart, which would leave the card's total disagreeing with the ledger's.
    raise SystemExit(f"ledger has catchers with no card label: {missing}")
merged = collections.Counter()
for k, n in COUNTS.items():
    merged[LABEL[k]] += n
ROWS = sorted(merged.items(), key=lambda r: -r[1])
TOTAL = sum(n for _, n in ROWS)

ACCENT = "#1f6f6b"
WARN = "#b4562a"


def chart(ax, accent):
    top, gap, end = 3.30, 0.72, 10.95

    # Where the bars start is measured, not guessed. A hand-picked x0 left the
    # longest label touching its bar with a 3 px gap - legible to every
    # geometric check in cardcheck, and the first thing a person notices. Two
    # entries in the ledger are that same defect.
    labels = [ax.text(0.78, top - i * gap, label, fontsize=34, color=INK,
                      family=SANS, va="center")
              for i, (label, _n) in enumerate(ROWS)]
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    px_per_unit = ax.figure.dpi                      # canvas units are inches
    widest = max(t.get_window_extent(renderer).x1 for t in labels) / px_per_unit
    x0 = widest + 0.30                               # a clear gap, not a hairline

    unit = (end - x0) / max(n for _, n in ROWS)
    for i, (label, n) in enumerate(ROWS):
        y = top - i * gap
        colour = WARN if label == "your own eyes" else accent
        ax.add_patch(Rectangle((x0, y - 0.21), n * unit, 0.42, fc=colour, ec="none"))
        ax.text(x0 + n * unit + 0.18, y, str(n), fontsize=34, fontweight="bold",
                color=colour, family=SANS, va="center")


if __name__ == "__main__":
    out = ROOT / ".github" / "assets" / "social-preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    card(out=str(out), accent=ACCENT, badge="db",
         kicker="DOUBLEBLIND",
         headline="Nothing that wrote it can check it",
         evidence=f"Who caught {TOTAL} defects the author's checks missed",
         chart=chart,
         footer="github.com/GuoCheng24/doubleblind")
    print("wrote", out)
