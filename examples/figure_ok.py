"""A figure that passes `doubleblind render` at link-unfurl scale.

Run it and `fig` is left at module level, which is what `doubleblind render`
looks for. Its counterpart in examples/broken/figure.py is the same figure with
six defects planted in it.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from doubleblind.render import CHROME  # noqa: E402

BG, INK, ACCENT = "#fbfaf8", "#17181a", "#1f6f6b"

fig = plt.figure(figsize=(12, 6.3), dpi=100)
fig.patch.set_facecolor(BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 12)
ax.set_ylim(0, 6.3)
ax.axis("off")

ax.text(0.8, 5.4, "One category does not move", fontsize=44,
        fontweight="bold", color=INK)
ax.plot([0.8, 11.2], [5.0, 5.0], color="#dcd8d2", lw=1.4)

for i, (name, before, after) in enumerate(
        [("colour", 86.0, 91.0), ("count", 81.0, 89.0), ("shape", 74.0, 74.0)]):
    y = 4.1 - i * 1.0
    ax.text(0.8, y, name, fontsize=34, color=INK, va="center")
    ax.barh(y, 7.2 * after / 100, height=0.42, left=3.1, color=ACCENT, zorder=3)
    ax.text(3.1 + 7.2 * after / 100 + 0.2, y, f"{after:.0f}%", fontsize=34,
            fontweight="bold", color=ACCENT, va="center")

ax.text(0.8, 0.45, "github.com/GuoCheng24/doubleblind", fontsize=18,
        color="#55585c", gid=CHROME)

if __name__ == "__main__":
    from doubleblind.render import audit
    raise SystemExit(1 if audit(fig) else 0)
