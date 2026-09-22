"""The same figure with six defects planted, one for each rule in render.py.

Each is a real defect that shipped in this project, not an invented one:

1. a caption under the legibility floor          - unreadable in a thumbnail
2. grey-on-near-grey                             - fails WCAG contrast
3. a headline over an undeclared tile grid       - the 12% threshold passed this twice
4. a label lying across the separator rule       - rules are Line2D, not patches
5. two labels three pixels apart                 - read as one run-on word
6. a character the font cannot draw              - renders as an empty box
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BG, INK, ACCENT = "#fbfaf8", "#17181a", "#1f6f6b"

fig = plt.figure(figsize=(12, 6.3), dpi=100)
fig.patch.set_facecolor(BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 12)
ax.set_ylim(0, 6.3)
ax.axis("off")

# 3 - a field of small tiles nobody declared, with the headline over it
for r_ in range(6):
    for c_ in range(16):
        ax.add_patch(Rectangle((0.8 + c_ * 0.34, 5.1 + r_ * 0.13), 0.28, 0.1,
                               fc="#cfe3e1", ec="none", zorder=1))
ax.text(0.8, 5.4, "One category does not move", fontsize=44,
        fontweight="bold", color=INK, zorder=5)

ax.plot([0.8, 11.2], [5.0, 5.0], color="#dcd8d2", lw=1.4)
# 4 - a label lying across that rule
ax.text(6.0, 4.96, "per category", fontsize=34, color=INK, va="center")

for i, (name, after) in enumerate([("colour", 91.0), ("count", 89.0), ("shape", 74.0)]):
    y = 4.1 - i * 1.0
    ax.text(0.8, y, name, fontsize=34, color=INK, va="center")
    ax.barh(y, 7.2 * after / 100, height=0.42, left=3.1, color=ACCENT, zorder=3)
    ax.text(3.1 + 7.2 * after / 100 + 0.2, y, f"{after:.0f}%", fontsize=34,
            fontweight="bold", color=ACCENT, va="center")

# 5 - two labels three pixels apart on the same line
ax.text(0.8, 1.15, "strict", fontsize=34, color=INK, va="center")
ax.text(2.05, 1.15, "87.5%", fontsize=34, color=INK, va="center")

# 1 - a caption far under the legibility floor
ax.text(0.8, 0.95, "measured on the 150-item subset, paired", fontsize=11, color="#55585c")

# 2 - grey on near-grey
ax.text(6.5, 0.95, "provisional", fontsize=16, color="#e2e0dc")

# 6 - a subscript the font cannot draw
ax.text(0.8, 0.45, "batch shape 🧪 measured", fontsize=34, color=INK)

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from doubleblind.render import audit
    raise SystemExit(1 if audit(fig) else 0)
