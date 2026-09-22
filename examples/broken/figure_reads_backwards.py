"""A figure with nothing geometrically wrong and a conclusion that is backwards.

Every number in it is correct. Nothing overlaps, nothing is too small, every
contrast clears WCAG, no glyph is missing - `doubleblind render` passes it, and
a test in this repository asserts that it keeps passing it.

What a reader takes from it is that the relationship is steeply positive,
because each family's three points are joined and each of those segments is
steep. Over the range actually measured the relationship is almost flat: the
families sit at different heights, and joining within a family shows the
within-family slope while the eye reads it as the overall one.

This is the third blind spot. The numbers layer cannot see it because the
numbers are right; the reviewer layer, given the data rather than the image,
would not see it either; and no geometric rule about a figure knows which slope
a reader will perceive. Somebody has to look at the picture and ask whether it
says what the data says.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BG, INK, A, B = "#fbfaf8", "#17181a", "#b4562a", "#1f6f6b"

FAMILIES = {
    "family A": ([1.0, 1.1, 1.2], [2.0, 5.0, 8.0]),
    "family B": ([5.0, 5.1, 5.2], [3.0, 6.0, 9.0]),
}

fig = plt.figure(figsize=(12, 6.3), dpi=100)
fig.patch.set_facecolor(BG)
ax = fig.add_axes([0.17, 0.20, 0.78, 0.64])
ax.set_facecolor(BG)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)

for (name, (xs, ys)), colour in zip(FAMILIES.items(), (A, B)):
    ax.plot(xs, ys, "o-", color=colour, lw=4, ms=14, label=name)

ax.set_xlim(0, 6.0)
ax.set_ylim(0, 10)
ax.set_xlabel("dose", fontsize=34, color=INK)
ax.set_ylabel("response", fontsize=34, color=INK)
ax.set_title("Response rises steeply with dose", fontsize=40, color=INK, pad=18)
ax.tick_params(labelsize=34, colors=INK)
ax.legend(fontsize=34, frameon=False, loc="upper left")

if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from doubleblind.render import audit
    raise SystemExit(1 if audit(fig) else 0)
