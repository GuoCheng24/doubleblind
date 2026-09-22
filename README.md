# doubleblind

[![tests](https://github.com/GuoCheng24/doubleblind/actions/workflows/ci.yml/badge.svg)](https://github.com/GuoCheng24/doubleblind/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![licence](https://img.shields.io/badge/licence-MIT-green)](LICENSE)

**Your agent wrote the report. Ask it whether the report is true and it will say yes.**

Not because it is lying. The reasoning that produced the claim is the reasoning
being asked to check it, and it cannot notice what it did not think of the first
time. The same goes for the tests it writes for itself and the review it gives
itself when you ask it to look again.

Three things catch that, and **no two of them catch the same defects**:

| | finds | structurally cannot see |
|---|---|---|
| **a machine that recomputes** | a number that exists in no file; a built artifact older than the data behind it; a bound stated tighter than the interval | anything nobody thought to check — above all a **correct number inside a sentence that does not follow from it** |
| **a reader with no context** | claims that do not follow; a comparison pointing the wrong way; a framing the data will not carry | anything needing exact recomputation — a fabricated number that looks plausible reads as fine |
| **your own eyes, on the rendered thing** | labels run together; a figure whose slope reads backwards; a character the font could not draw | anything past the first page, and anything that needs arithmetic |

`doubleblind` automates the first two, tells you honestly where each one stops,
and keeps a ledger of what got through anyway.

```bash
pip install -e .          # or run it in place: python -m doubleblind
```

Standard library only, no dependencies, Python 3.9+. The reviewer layer works
with Claude Code, Codex CLI, DeepSeek, Kimi, or any OpenAI-compatible endpoint.

---

## Both blind spots, in one file, in sixty seconds

`examples/broken/report.md` has three defects planted in it.

```console
$ doubleblind trace examples/broken/report.md \
      --data examples/results.json --derive 'python3 examples/gain.py'

  UNSUPPORTED  97.50%   examples/broken/report.md:3
      On all 400 items of widgets-v2, the treatment reaches 97.50% accuracy against a
      nearest committed values: 0.91 (results.json per_category_accuracy.colour),
                                0.89 (results.json per_category_accuracy.count),
                                0.875 (results.json treatment.accuracy)

  UNCHECKABLE  "two thirds"    examples/broken/report.md:10
  UNCHECKABLE  "four fifths"   examples/broken/report.md:10
      Head removal accounts for between two thirds and four fifths of the effect.
      A quantity written as words cannot be traced to a file. Write the number.
```

Two of three, and it pointed at the `0.875` that `97.50%` should have been. The
third defect is this sentence:

> Shape is where the treatment pays: it rises to **74.00%**, the largest
> movement of any category.

`74.00%` is right — `shape` really is 0.74. It is also 0.74 *before* the
treatment. Shape is the one category that does not move, and the two that do are
not in the sentence. Every quantity checks out and the sentence is false, so
`trace` passes it, and **a test in this repository asserts that `trace` keeps
passing it**. A claim about a blind spot is worth nothing unless it is pinned
down.

That sentence is what the second layer is for.

---

## The second layer: a reader who was told nothing

```console
$ doubleblind review examples/broken/report.md --data examples/results.json --agent claude
packet: packet.md  (1847 bytes, sha256 4f2a9c...)

Send it with Claude Code:

    Agent(
        subagent_type='general-purpose',
        model='<a model that is NOT the one that wrote the artifact>',
        run_in_background=False,
        prompt=open('packet.md').read(),
    )

Then, before you believe the verdict, record two things next to it:
  1. which model answered - it must not be the one that wrote the artifact;
  2. this packet's sha256 - 4f2a9c...
```

Two properties make that reader independent and **both are required**: a
**different model**, because the same model with a fresh context still carries
the priors that wrote the artifact; and **zero context**, because a reviewer who
knows the wanted answer is not a second opinion.

The second is the one that gets lost, and never on purpose. It is lost in the
request:

```console
$ doubleblind lint examples/brief-leaky.md

  answer-in-the-request
      examples/brief-leaky.md:2  "Please confirm that"
      -> Ask what the evidence supports, not whether a stated thing is true.

  social-pressure
      examples/brief-leaky.md:1  "I already verified"
      examples/brief-leaky.md:3  "quick sanity check"
      -> Saying you checked makes a finding an accusation.

  ... 6 mechanisms, 9 phrases

9 phrase(s) in this brief tell the reviewer what to conclude.
A reviewer that knows the wanted answer is not a second opinion.
```

`lint` reads the request you were about to send and finds the phrases that carry
the answer, grouped by mechanism rather than wording: **answer-in-the-request**,
**conclusion-stated**, **polarity-steering**, **social-pressure**,
**scope-narrowing**, **authorship-leak**. The brief this repository ships is
linted by its own test suite, so it cannot rot.

---

## On your own work

```bash
# every number on the page must exist in a file you committed
doubleblind trace README.md --data results/

# numbers no file stores - per-category gains, medians, paired deltas - come
# from a script that is also committed, so a reader can run the same line
doubleblind trace README.md --data results/ --derive 'python scripts/metrics.py'

# exemptions need a reason, or the allow list becomes somewhere to hide things
echo "400   the dataset size, fixed by the benchmark" >> doubleblind-allow.txt

# then the reader who was told nothing
doubleblind review README.md --data results/ --agent codex
```

`trace` exits 1 on an unsupported number, `lint` exits 1 on a leaky brief, so
both drop into CI unchanged. See [`protocol/`](protocol/) for the reviewer brief
and the per-agent adapters, and [`protocol/blindness.md`](protocol/blindness.md)
for how to record that the reviewer really was blind.

### What `trace` gets right, and where it gets weaker

Every rule in it was paid for. `79.75` must not match inside `179.751`, so
patterns are anchored rather than `\b`-bounded. Prose that says `88.4` claims one
decimal, so the tolerance is half an ulp *at the precision the prose chose*. A
whole number is a count, so `11 items` is not supported by a stored `10.6`.
Dates, clock times, semantic versions, hex digests, URLs and fenced code are not
results. A quantity written in words is reported rather than skipped, because
*"two thirds to four fifths"* once shipped in place of 64.43%–81.17% and every
digit-based check passed it.

It gets **weaker the more data you point it at**. A raw per-item dump holds every
id, index and token count, so a round number in prose will coincide with one of
them and be called traced. `trace` says so when the pool gets large. Point
`--data` at summary files and use `--derive` for the rest.

---

## The ledger

[`ledger/`](ledger/) records real defects that shipped, each with the layer that
missed it and why that layer could not have seen it. It is the part of this
repository that cannot be regenerated, and it includes 3 defects in
`doubleblind` itself - one of which disarmed a CI step for every document in
the repository at once.

The pattern is consistent enough to plan around. On a document that had already
passed 37 mechanical checks and two rounds of its author's own review, a
zero-context reviewer on a different model returned nine findings in ten
minutes; 5 were verified command by command and all five stood. **4 of those 5
were correct numbers in sentences that did not follow from them** — a causal
claim, a framing, a ranking, and a promise the guard made about itself. None is
reachable by comparing quantities.

The fifth was the other kind: a column in the data nobody had looked at. 11 of
100 items had never finished writing their reasoning, and the answer extractor
had credited 5 of them from a half-written trace. Counted as no-answer instead,
three of four confidence intervals stopped containing the number being
reproduced. The page's verdict turned on it and the page did not mention it.

And the honest part: of 17 recorded defects, **8 were caught by a human looking
at the rendered artifact** — 5 of those 8 rendering defects that no amount of
number-checking would ever have reached. That is the number this tooling
exists to shrink, and the ledger is how you find out whether it does.

## What this is not

It is not an autonomous research agent and it writes nothing. It is what you run
*after* an agent has produced something you are about to publish, on the premise
that the agent that produced it is the wrong thing to ask.

For the generative side — reading literature, proposing experiments, drafting
papers — [ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)
does that, and its cross-model review gate is careful work: it builds an
un-forgeable evidence chain from the host's session events to prove the reviewer
really was a different model. `doubleblind` needs no such machinery because it
never asserts the reviewer was independent. It tells you to write down the model
and the packet hash, and gives you nothing if you don't.

## Licence

MIT.
