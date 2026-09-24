"""Check a figure for the defects a person catches and a number-checker cannot.

This repository's ledger is blunt about where the gap is: of the defects
recorded there, most were caught by someone looking at the rendered artifact,
and most of those were rendering defects. Not one of them was reachable by
comparing quantities, because every quantity in them was correct. A headline
lying across a tile grid, two labels three pixels apart that read as one word, a
subscript the font could not draw, a caption too small to read in a thumbnail -
the data behind all of these was right.

So this is the third layer, and every rule in it was paid for by something that
shipped:

**Legibility at the size it will be seen.** A figure drawn at full size is
consumed at thumbnail size - a link unfurl is about 30% of the canvas. Text that
falls under about 10 px there is texture, whatever it says. The floor is
therefore ``10 / scale`` on the canvas, and the caller declares which text is
*chrome* (a footer URL, a watermark) and exempt, because the role cannot be read
off the geometry. An earlier version measured legible *area* instead and was
dominated by the length of the footer, so a figure failed harder the more
carefully it was labelled.

**Contrast.** WCAG 2.1 relative luminance, 4.5:1 for body text and 3:1 for large
text, against whatever the text actually sits on rather than against the page.

**Text on artwork, including artwork that is a line.** A title over a field of
small tiles covers a few percent of its own bounding box and is still a title
with tiles through it, so the threshold is *any* real overlap rather than a
share - a 12% threshold passed that twice. And a rule is a ``Line2D``, not a
patch: a set of column headers sat across a separator and every check that
walked ``ax.patches`` reported clean.

**Text that merely touches.** Two strings three pixels apart do not overlap, so a
collision test scores them at zero, and a reader sees one run-on word. Reported
when the gap on a shared line is under a third of a character, negative gaps
included.

**Characters the font cannot draw.** A missing glyph renders as an empty box and
has a bounding box like any other glyph, so it is invisible to every geometric
test. The renderer mentions it once, in a warning, in a long build log.

Declare roles with matplotlib's own ``gid``, so nothing new has to be imported::

    ax.text(..., gid="doubleblind:chrome")      # not part of the message
    ax.add_patch(Rectangle(..., gid="doubleblind:panel"))   # a declared ground

matplotlib is an optional dependency: ``pip install doubleblind[render]``.
"""

from __future__ import annotations

import warnings

__all__ = ["audit", "contrast", "UNFURL_SCALE", "READABLE_PX"]

UNFURL_SCALE = 0.30      # a shared link is shown at about 30% of the canvas
READABLE_PX = 10.0       # below this a reader sees texture, not words

CHROME = "doubleblind:chrome"
PANEL = "doubleblind:panel"


def _require_matplotlib():
    try:
        import matplotlib  # noqa: F401
    except ImportError as exc:                              # pragma: no cover
        raise SystemExit(
            "doubleblind render needs matplotlib, which the core deliberately does "
            "not depend on.\n    pip install 'doubleblind[render]'") from exc


def _lum(c):
    def f(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contrast(fg, bg):
    """WCAG 2.1 contrast ratio between two matplotlib colours."""
    _require_matplotlib()
    from matplotlib.colors import to_rgb
    a, b = _lum(to_rgb(fg)), _lum(to_rgb(bg))
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _texts(fig):
    """Every string a reader will actually see.

    Tick labels are the trap, twice over. `ax.axis("off")` hides the axis but
    Returns `(text, role)`. The role is not decoration: an x-tick and a y-tick
    at the origin sit diagonally adjacent by construction, and without knowing
    which axis each came from the run-on-word rule calls them one word. That
    happened - on matplotlib 3.11 the origin ticks `0` and `0.0` overlap by 5
    px, and a fixture that is supposed to audit clean started failing.

    Tick labels are the trap, twice over. `ax.axis("off")` hides the axis but
    leaves every label in `get_xticklabels()`, each still reporting
    `get_visible() == True`, and `ax.xaxis.get_visible()` stays True as well -
    the flag that actually moves is `ax.axison`. Counting them buried six real
    findings under twenty complaints about ticks that are not drawn.
    """
    out = [(t, "figure") for t in fig.texts]
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        out += [(t, "annotation") for t in ax.texts]
        for lbl, role in ((ax.title, "title"), (ax.xaxis.label, "axis-label"),
                          (ax.yaxis.label, "axis-label")):
            if lbl is not None:
                out.append((lbl, role))
        if getattr(ax, "axison", True):
            if ax.xaxis.get_visible():
                out += [(t, "xtick") for t in ax.get_xticklabels()]
            if ax.yaxis.get_visible():
                out += [(t, "ytick") for t in ax.get_yticklabels()]
        leg = ax.get_legend()
        if leg is not None and leg.get_visible():
            out += [(t, "legend") for t in leg.get_texts()]
    return [(t, role) for t, role in out
            if t.get_text() and t.get_text().strip() and t.get_visible()]


def _patches(fig):
    out = []
    for ax in fig.axes:
        out += [(ax, p) for p in ax.patches]
    return out


def _lines(fig):
    out = []
    for ax in fig.axes:
        out += [(ax, ln) for ln in ax.lines]
    return out


def _ground(fig):
    fc = fig.patch.get_facecolor()
    return fc[:3] if len(fc) >= 3 else (1.0, 1.0, 1.0)


def missing_glyphs(fig):
    """Characters the chosen font cannot draw, from the renderer's own warnings."""
    _require_matplotlib()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.canvas.draw()
        out = []
        for w in caught:
            msg = str(w.message)
            if "missing from font" in msg:
                out.append(msg.split(" missing from")[0].replace("Glyph ", "").strip())
    return sorted(set(out))


def audit(fig, scale=UNFURL_SCALE, min_ratio=4.5, ground=None, verbose=True):
    """Return a list of problems with ``fig``. An empty list means it passes.

    Parameters
    ----------
    fig : matplotlib Figure, already populated.
    scale : the fraction of its drawn size at which the figure will be seen.
        0.30 is a link unfurl; pass 1.0 for something read at full size.
    min_ratio : WCAG ratio required of body text. Large text needs 3:1.
    ground : page colour, if the figure's own facecolor is not it.
    """
    _require_matplotlib()
    tofu = missing_glyphs(fig)                 # draws the figure as a side effect
    r = fig.canvas.get_renderer()
    W, H = fig.canvas.get_width_height()
    floor = READABLE_PX / scale
    page = ground if ground is not None else _ground(fig)
    problems = []

    panels = []
    for _ax, p in _patches(fig):
        if p.get_gid() == PANEL:
            bb = p.get_window_extent(r)
            panels.append((bb, p.get_facecolor()))

    chrome_area = message_area = 0.0
    boxes = []
    for t, role in _texts(fig):
        s = t.get_text().strip()
        box = t.get_window_extent(r)
        boxes.append((t, s, box, role))
        area = box.width * box.height
        is_chrome = t.get_gid() == CHROME

        # A text bounding box includes the font's ascent and descent whether or
        # not those rows carry ink, so a word with no descenders reports a few
        # pixels below its baseline that a reader never sees. The tolerance is a
        # fraction of the box height rather than a fixed number of pixels, so it
        # scales with the type size, and the amount is reported either way.
        slop = 0.2 * box.height
        over = []
        if box.x0 < -slop:
            over.append(f"{-box.x0:.0f} px past the left edge")
        if box.x1 > W + slop:
            over.append(f"{box.x1 - W:.0f} px past the right edge")
        if box.y0 < -slop:
            over.append(f"{-box.y0:.0f} px below the bottom")
        if box.y1 > H + slop:
            over.append(f"{box.y1 - H:.0f} px above the top")
        if over:
            problems.append(f"{s[:40]!r} runs " + ", ".join(over))

        bg = page
        for bb, col in panels:
            if bb.x0 <= (box.x0 + box.x1) / 2 <= bb.x1 and bb.y0 <= (box.y0 + box.y1) / 2 <= bb.y1:
                bg = col
        try:
            ratio = contrast(t.get_color(), bg)
        except (ValueError, TypeError):
            ratio = None
        if ratio is not None:
            need = 3.0 if t.get_fontsize() >= 24 else min_ratio
            if ratio < need:
                problems.append(
                    f"contrast {ratio:.1f}:1 (needs {need}:1) for {s[:36]!r}")

        declared = any(bb.x0 <= (box.x0 + box.x1) / 2 <= bb.x1
                       and bb.y0 <= (box.y0 + box.y1) / 2 <= bb.y1 for bb, _c in panels)

        for _ax, ln in _lines(fig):
            xs, ys = ln.get_xdata(), ln.get_ydata()
            if len(xs) < 2 or ln.get_linestyle() == "None":
                continue
            lb = ln.get_window_extent(r) if hasattr(ln, "get_window_extent") else None
            if lb is None:
                continue
            # A rule is thin in ONE direction, and the first version of this
            # checked only for thin-in-height. A vertical threshold line drawn
            # through a caption passed every check and was obvious in the
            # render: a dashed line ran straight through "p = 0.549".
            horizontal = lb.height <= 8
            vertical = lb.width <= 8
            if not (horizontal or vertical):
                continue
            pad = 4
            if (box.x0 < lb.x1 + pad and box.x1 > lb.x0 - pad
                    and box.y0 < lb.y1 + pad and box.y1 > lb.y0 - pad):
                problems.append(
                    f"{s[:32]!r} sits across a {'vertical' if vertical else 'horizontal'} rule")
                break

        if not declared:
            for _ax, pt in _patches(fig):
                if pt.get_gid() == PANEL:
                    continue
                fc = pt.get_facecolor()
                if len(fc) > 3 and fc[3] < 0.5:
                    continue
                pb = pt.get_window_extent(r)
                if pb.width * pb.height > 0.55 * (W * H):     # the page itself
                    continue
                dx = min(box.x1, pb.x1) - max(box.x0, pb.x0)
                dy = min(box.y1, pb.y1) - max(box.y0, pb.y0)
                if dx > 2 and dy > 2:
                    problems.append(
                        f"{s[:32]!r} sits on undeclared artwork "
                        f"({dx:.0f}x{dy:.0f} px of its box)")
                    break

        if is_chrome:
            chrome_area += area
            continue
        message_area += area
        if t.get_fontsize() < floor:
            problems.append(
                f"{t.get_fontsize():.0f} pt is {t.get_fontsize() * scale:.1f} px at "
                f"{scale:.0%} - unreadable: {s[:40]!r}")

    for i in range(len(boxes)):
        for j in range(len(boxes)):
            if i == j:
                continue
            (ta, sa, ba, ra), (tb, sb, bb, rb) = boxes[i], boxes[j]
            # An x-tick and a y-tick are adjacent at the origin by
            # construction, and nobody reads across a corner. Ticks on the
            # SAME axis still count: a crowded axis is the defect this rule is
            # for.
            if {ra, rb} == {"xtick", "ytick"}:
                continue
            same_line = min(ba.y1, bb.y1) - max(ba.y0, bb.y0) > 0.4 * min(ba.height, bb.height)
            gap = bb.x0 - ba.x1
            per_char = ba.width / max(len(sa), 1)
            if same_line and bb.x0 > ba.x0 and gap < 0.33 * per_char:
                # A small or slightly negative gap reads as one run-on word; a
                # large negative one is not touching, it is one string printed
                # over another, and saying "apart" about it is misleading.
                if gap < -0.5 * per_char:
                    problems.append(
                        f"{sa[:22]!r} and {sb[:22]!r} overlap by {-gap:.0f} px")
                elif gap < 0.5:
                    # Rounds to zero, or is a fraction of a pixel negative:
                    # "-0 px apart" was the message this used to print.
                    problems.append(
                        f"{sa[:22]!r} and {sb[:22]!r} touch and read as one word")
                else:
                    problems.append(
                        f"{sa[:22]!r} and {sb[:22]!r} are {gap:.0f} px apart "
                        "and read as one word")

    if message_area and chrome_area > 0.45 * message_area:
        problems.append(
            f"chrome is {100 * chrome_area / (chrome_area + message_area):.0f}% of the text "
            "area; it should stay out of the way")

    problems += [f"the font cannot draw {c!r} - it renders as an empty box" for c in tofu]

    if verbose:
        seen = f"{floor:.0f} pt on the canvas is {READABLE_PX:.0f} px at {scale:.0%}"
        print(f"  [render] {len(boxes)} text objects; legibility floor {seen}")
        for p_ in problems:
            print(f"  ! {p_}")
        if not problems:
            print("  [render] passes: legibility, contrast, frame, artwork, glyphs")
    return problems
