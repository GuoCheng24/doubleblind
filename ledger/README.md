# The ledger

Real defects that shipped, or reached a publishable artifact, in one
researcher's public repositories. Each entry records **which layer missed it and
why that layer could not have seen it** - not to apportion blame, but because
the pattern is the only thing here that generalises.

This file is generated from `findings.json` by `render.py`. Edit the data.


## correct number false sentence  (5)

### `coco-count-causal`

*benchmark reproduction README*

"counting is where thinking pays ... COCO Count to 91.3%". On the subsample thinking moved COCO Count by zero: 91.30% before, 91.30% after, one item fixed and one broken. The gain came from a different task.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** 91.3 is the correct number. The guard compares the quoted figure with the computed one and they agree; the causal sentence around it is what is false, and no quantity comparison reads sentences.
- **Caught by:** zero-context reviewer
- **Check now:** none possible of the same kind - this class is why the reviewer layer exists

### `four-estimators`

*benchmark reproduction README*

A table of "four estimators". Under a binary auxiliary variable the regression and post-stratified estimators are the same estimator - identical point estimates and identical bootstrap intervals. Four rows, three readings.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The guard checked both rows against the results file. The results file is right; the framing is not.
- **Caught by:** zero-context reviewer
- **Check now:** none possible of the same kind

### `furthest-from-card`

*benchmark reproduction README*

"the least precise of the four and the furthest from the card". True for one benchmark; for the other that row is the closest - 1.63 against 2.16 and 2.51.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The sentence is prose about a table. The guard reads cells.
- **Caught by:** zero-context reviewer
- **Check now:** none possible of the same kind

### `guard-own-promise`

*the number guard itself*

A 37-check guard printed "every number on the page is re-derived from results/" and exited 0 on a README with eight claims falsified into it, among them a McNemar p of 0.064 written as 0.640 and a paired gain of +6.00 written as +60.0. Those figures existed in no committed file, so nothing compared them to anything.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The guard searched the whole document for each computed number. A falsified figure that appears nowhere in the data was simply never looked for.
- **Caught by:** zero-context reviewer
- **Check now:** checks anchored to the sentence that carries the claim, not to the document; 37 checks became 50, and the two falsifications above now fail by name

### `spelled-out-bound`

*manuscript prose*

"two thirds to four fifths" where the interval was 64.43% to 81.17% - a bound stated tighter than the data supports, in prose containing no digits at all.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The number guard reads digits. There were none.
- **Caught by:** zero-context reviewer
- **Check now:** doubleblind trace reports spelled-out quantities as UNCHECKABLE rather than passing over them

## unexamined data column  (1)

### `unclosed-reasoning-blocks`  **changed a conclusion**

*benchmark reproduction README*

11 of 100 thinking-on items never closed their reasoning block, all against the token budget. The answer extractor credited 5 of them from a half-written trace. Scored as no-answer instead, three of the four estimator intervals stop containing the model card's number - the verdict turns on how those 11 are counted, and the page did not say so.

- **Missed by:** both automated layers
- **Why it could not see it:** No check read the column recording whether the block closed. The guard compared stated numbers with computed ones and both were computed the same way, from the same silently truncated traces.
- **Caught by:** zero-context reviewer
- **Check now:** the unclosed count is a first-class reported result and the sensitivity of the verdict to it is written to a results file

## rendering  (7)

### `buried-labels`

*social preview card*

Two labels overlapping by 8 px, rendering as one run-together word.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The collision test divided the intersection by the area of the smaller box; two long labels touching at their ends scored 6.5% and passed.
- **Caught by:** human eye
- **Check now:** a pair is also reported when the horizontal overlap buries half a character of the narrower font, and negative gaps are included

### `title-across-artwork`

*social preview card*

A headline lying across a 128-tile grid, twice.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The text-on-artwork test keyed on filled patches above a 12% area threshold. A field of small tiles never reached it.
- **Caught by:** human eye
- **Check now:** any text over undeclared artwork larger than 2 px is reported; chrome must be declared explicitly

### `text-across-rule`

*social preview card*

Chart headers sitting on the card's own separator rule.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The artwork test walked patches. A rule is a Line2D and was never in the list.
- **Caught by:** human eye
- **Check now:** rules are checked as artwork

### `missing-glyph-tofu`

*figure*

A subscript rendered as two empty boxes because the font could not draw it.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** A missing glyph has a bounding box like any other glyph, so every geometric check passed. The renderer mentions it once, in a warning, in a long build log.
- **Caught by:** human eye
- **Check now:** renderer warnings are captured and missing characters are reported by name

### `inverted-figure`  **changed a conclusion**

*figure*

Per-family points joined by line segments made the shallower fit look steeper, reversing the figure's visual conclusion while every number in it was correct.

- **Missed by:** both automated layers
- **Why it could not see it:** Nothing about the plot was wrong as data. A geometric check has no notion of which slope a reader will perceive, and a reviewer given the numbers rather than the image would not see it either.
- **Caught by:** human eye
- **Check now:** fitted lines are drawn over a common range; the rendered image is read, not the script

### `card-label-touching-bar`

*this repository's own social card*

The longest bar label ended three pixels from the bar it labelled, so at a glance the words ran into the shape. The card's own acceptance test - legibility at unfurl scale, WCAG contrast, frame, text-against-text collision, missing glyphs - reported it clean and wrote the file.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The gap was between text and a filled rectangle rather than between two pieces of text, and it was positive. Every threshold in the audit was written for overlap, and three pixels of clearance is not overlap.
- **Caught by:** human eye
- **Check now:** the bars start at a measured offset past the widest rendered label instead of a hand-picked coordinate, so the gap cannot depend on how long the labels happen to be

### `vertical-rule-through-text`

*this repository's figure auditor*

A social card drew a dashed vertical threshold line through its own caption - the line ran straight through 'p = 0.549'. The figure auditor passed it, as did the card's own acceptance test.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The rule check skipped any line whose bounding box was taller than eight pixels, on the reasoning that a rule is thin. That is true of a rule, and the test was written for horizontal ones only, so every vertical rule was excluded by the very condition meant to identify rules.
- **Caught by:** human eye
- **Check now:** a line counts as a rule when it is thin in EITHER direction, the report names which, and a test covers a vertical rule through text and a vertical rule clear of it

## staleness  (3)

### `stale-artifact`

*compiled PDF*

A built PDF quoting figures that the data behind it had since replaced.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** Every check ran against the source. Nothing compared the built artifact with the source it was built from.
- **Caught by:** human eye
- **Check now:** the built artifact's numbers are re-extracted and matched against the current results, anchored so a figure cannot match inside a longer one

### `unread-prose-state`

*profile page*

A page describing an upstream pull request as open after it had been closed.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The guard checked that the links resolved. It never read the words next to them.
- **Caught by:** human eye
- **Check now:** the status written in prose after each link is parsed and compared with the live state

### `stale-count-matched-another-field`

*this repository's README*

"9 were caught by a person looking at the rendered artifact, and 6 of those 9 were rendering defects", after the ledger had moved to 10 and 7 - which the same README gave a few paragraphs later. It also said "the six defects that got through in this repository" when the ledger held seven.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** trace checks that a number exists somewhere in the evidence, and both stale numbers did: 9 is how many findings one review run returned, and 6 is how many the zero-context reviewer caught. It matched each to the wrong field and passed. 'six', written as a word, was not checked at all.
- **Caught by:** zero-context reviewer
- **Check now:** a test binds each ledger count the README states to the summarize.py field it names, by the phrase around it; it was seen failing on the stale README before the fix

## tooling  (6)

### `vendored-drift`

*shared tooling*

Copies of a shared checking tool vendored into several repositories had drifted from the source, so a fix in one place was not a fix anywhere else.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** Each copy passed its own tests. Nothing compared the copies.
- **Caught by:** human eye
- **Check now:** a sync step copies the source into every consumer and names what changed

### `hidden-relative-path`

*this repository*

The evidence loader skipped every directory whose path contained a component starting with a dot, in order to ignore hidden directories. It therefore silently found nothing under any relative path beginning with `..` and reported "nothing to trace against".

- **Missed by:** both automated layers
- **Why it could not see it:** Unit tests used absolute paths. The failure mode was an empty result, which looks like a clean run if you are not watching for it.
- **Caught by:** running it on a real repository
- **Check now:** "." and ".." are ordinary path components; a test covers the relative-path case

### `integer-rounding`

*this repository*

The matcher allowed rounding at the precision the prose chose, so "11 items" was reported as traced by a stored 10.6.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** The rule was correct for means and wrong for counts, and nothing distinguished them. It was found only because a test was written to assert the behaviour nobody had checked.
- **Caught by:** test
- **Check now:** a whole number in prose requires a whole number in the evidence

### `repo-wide-allow-list`

*this repository*

The allow list was a flat list of numbers with reasons, read from the repository root for whatever document was being traced. The entry exempting an illustrative 97.50 in the README therefore also exempted the figure deliberately fabricated into the broken example, and the CI step asserting that the broken example fails began to pass.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** Nothing was wrong with either file. The exemption was correct for the document it was written for and silently correct for every other document too, and a check that stops failing looks exactly like a check that has nothing to report.
- **Caught by:** test
- **Check now:** every allow entry names the document it applies to, and a test asserts that an exemption for one document does not cover another

### `example-needs-a-working-directory`

*this repository's quickstart*

The derivation script the README tells readers to run opened its data file by a path relative to the working directory. Copied out of the README and run from anywhere but the repository root, it failed with a FileNotFoundError naming a file the reader had never heard of.

- **Missed by:** both automated layers
- **Why it could not see it:** Every test and every author stands in the repository root, so the path always resolved. Nothing was wrong with the code as exercised; it was wrong only as used.
- **Caught by:** installing it into a clean virtualenv and following the README from elsewhere
- **Check now:** the example resolves its data against __file__, and two tests run it from a temporary directory

### `hidden-axis-still-had-labels`

*this repository's figure auditor*

Run on its first real figure, the auditor produced twenty complaints about tick labels belonging to an axis that had been turned off with ax.axis("off"), burying the six real findings underneath them. It also reported every out-of-canvas problem as an x-axis span whichever edge had actually been crossed, so a label hanging four pixels below its baseline read as a horizontal overflow.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** Three different flags could have said the axis was hidden and only one of them moves: the label's own get_visible() stays True, ax.xaxis.get_visible() stays True, and ax.axison is the one that goes False. Checking the two obvious ones looked like checking visibility.
- **Caught by:** running it on a real figure
- **Check now:** tick labels are gated on ax.axison, a test asserts a hidden axis contributes no text at all, and the frame check names the edge that was crossed and by how much, with a tolerance scaled to the font's own descent

## guard wrong on a dependency version  (1)

### `render-tick-corner-and-threshold-margin`

*the figure layer itself*

The run-on-word rule called an x-tick and a y-tick at the origin one word - they are diagonally adjacent by construction and nobody reads across a corner - so on matplotlib 3.11 a fixture whose job is to audit CLEAN started failing. And the planted run-on pair sat 4.7 px from a 6.6 px threshold; 3.11 renders 'strict' 2.2 px narrower, the gap became 7.0 px and the planted defect stopped being detected.

- **Missed by:** a machine that recomputes
- **Why it could not see it:** Both tests passed on the author's matplotlib. Nothing in the repository changed; a dependency's minor release did, and the figure layer reads font metrics.
- **Caught by:** a dependency's minor version, reproduced in a clean virtualenv
- **Check now:** _texts() carries each string's role and the rule skips x-tick/y-tick pairs; a test asserts the planted gap keeps 3 px of margin on BOTH sides of the threshold, because the detection is what drifted; CI runs the oldest supported matplotlib and the newest

---

Counts over this file are printed by `summarize.py`, which is what the
top-level README is traced against.
