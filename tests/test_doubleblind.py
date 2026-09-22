"""Tests. Several of these assert that a check FAILS to catch something.

That is deliberate. This repository's claim is that its two layers are blind to
different things, and a claim about a blind spot is worth nothing unless it is
pinned down: if `trace` ever started catching the false sentence in
`examples/broken/report.md`, the README would be overstating one layer and
understating the need for the other, and nobody would notice. So the blind spot
has a test.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from doubleblind.cli import read_allow  # noqa: E402
from doubleblind.packet import build_packet, intent_leaks  # noqa: E402
from doubleblind.trace import (  # noqa: E402
    Value, extract_numbers, load_evidence, run_derivations, trace, vague_quantities,
)

EX = os.path.join(ROOT, "examples")
DERIVE = f'{sys.executable} examples/gain.py'


def _trace_example(doc):
    ev = load_evidence([os.path.join(EX, "results.json")])
    ev += run_derivations([DERIVE], cwd=ROOT)
    return trace(open(doc, encoding="utf-8").read(), ev)


class Extraction(unittest.TestCase):
    def check(self, text, want):
        self.assertEqual([n.raw for n in extract_numbers(text)], want)

    def test_anchored_not_inside_a_longer_number(self):
        self.check("79.75 and 179.751 and 1079.75.", ["79.75", "179.751", "1079.75"])

    def test_sentence_final_period_is_not_part_of_the_number(self):
        self.check("strict accuracy was 87.5.", ["87.5"])

    def test_percent_sign_is_kept(self):
        self.check("reaches 88.45% strict", ["88.45%"])

    def test_thousands_separator(self):
        self.check("over 16,384 tokens", ["16,384"])

    def test_dates_and_clock_times_are_not_results(self):
        self.check("on 2026-09-04 at 12:38 we ran 541 prompts", ["541"])

    def test_semantic_versions_are_not_results(self):
        self.check("torch 2.10.0 and cuda 12.8", ["12.8"])

    def test_hex_digest_is_masked_but_a_seven_figure_count_is_not(self):
        self.check("commit 2ff2fca over 1234567 tokens", ["1234567"])

    def test_code_fences_are_skipped(self):
        self.check("before 5.5\n```\nbatch=8\n```\nafter 6.6", ["5.5", "6.6"])

    def test_url_and_link_targets_are_skipped(self):
        self.check("see https://x.io/a/123 and [t](y/456), giving 77.2", ["77.2"])


class Matching(unittest.TestCase):
    def test_stored_fraction_supports_a_percentage(self):
        f = trace("accuracy was 88.45%", [Value(0.8845, "f.json", "acc")])[0]
        self.assertEqual(f.verdict, "traced")
        self.assertEqual(f.scale, " x100")

    def test_rounding_is_allowed_at_the_precision_the_prose_chose(self):
        self.assertEqual(trace("about 88.4%", [Value(0.88449, "f", "a")])[0].verdict, "traced")
        self.assertEqual(trace("about 88.40%", [Value(0.8849, "f", "a")])[0].verdict, "unsupported")

    def test_counts_are_exact_not_rounded(self):
        # 11 items means 11. A stored 10.6 rounds to 11 and must not support it.
        self.assertEqual(trace("11 items", [Value(11, "f", "n")])[0].verdict, "traced")
        self.assertEqual(trace("11 items", [Value(10.6, "f", "n")])[0].verdict, "unsupported")

    def test_a_percentage_is_not_supported_by_a_stored_value_100x_larger(self):
        # Dropping the /100 scale: in a pool of per-item integers, a stored 8845
        # would otherwise declare "88.45" traced.
        self.assertEqual(trace("88.45%", [Value(8845, "f", "id")])[0].verdict, "unsupported")

    def test_unsupported_reports_the_nearest_stored_values(self):
        f = trace("97.50%", [Value(0.875, "f", "acc"), Value(0.81, "f", "b")])[0]
        self.assertEqual(f.verdict, "unsupported")
        self.assertIn(0.875, [v.value for v in f.nearest])


class WordQuantities(unittest.TestCase):
    def test_both_ends_of_a_spelled_out_range_are_reported(self):
        hits = vague_quantities("between two thirds and four fifths of the effect")
        self.assertEqual([h[1] for h in hits], ["two thirds", "four fifths"])

    def test_a_longer_phrase_absorbs_the_shorter_one_it_contains(self):
        hits = vague_quantities("roughly half of them")
        self.assertEqual([h[1] for h in hits], ["roughly half"])


class Examples(unittest.TestCase):
    def test_clean_report_traces_completely(self):
        bad = [f for f in _trace_example(os.path.join(EX, "report.md"))
               if f.verdict == "unsupported"]
        self.assertEqual(bad, [], f"clean example should trace: {[str(f.number) for f in bad]}")

    def test_broken_report_catches_the_fabricated_number(self):
        bad = [str(f.number) for f in _trace_example(os.path.join(EX, "broken/report.md"))
               if f.verdict == "unsupported"]
        self.assertEqual(bad, ["97.50%"])

    def test_broken_report_catches_the_spelled_out_bound(self):
        text = open(os.path.join(EX, "broken/report.md"), encoding="utf-8").read()
        self.assertEqual([h[1] for h in vague_quantities(text)], ["two thirds", "four fifths"])

    def test_the_blind_spot_is_real(self):
        """The false sentence about `shape` passes tracing, and must keep passing.

        `shape` is 0.74 before and 0.74 after: it is the one category the
        treatment does not move. The broken report calls it "where the treatment
        pays ... the largest movement of any category" and quotes 74.00%, which
        is the correct number. Every quantity in that sentence checks out; the
        sentence is false.

        No quantity-comparing check can see this, and pretending otherwise is
        how a repository ends up with one layer and a false sense of coverage.
        """
        findings = _trace_example(os.path.join(EX, "broken/report.md"))
        shape = [f for f in findings if f.number.raw == "74.00%"]
        self.assertTrue(shape, "the example must still contain the 74.00% claim")
        self.assertTrue(all(f.verdict == "traced" for f in shape))
        r = json.load(open(os.path.join(EX, "results.json")))
        self.assertEqual(r["per_category_accuracy"]["shape"],
                         r["per_category_accuracy_baseline"]["shape"],
                         "the example only works while shape genuinely does not move")


class Leaks(unittest.TestCase):
    LEAKY = ("Hi! I wrote this README and I already verified the numbers.\n"
             "Please confirm that all four estimators fall below the card number.\n"
             "It's a quick sanity check - just need you to look at the tables, "
             "ignore the appendix.\n"
             "Obviously the result should be that thinking mode helps.\n")

    def test_every_mechanism_fires_on_a_leaky_brief(self):
        mechs = {l.mechanism for l in intent_leaks(self.LEAKY)}
        self.assertEqual(mechs, {"answer-in-the-request", "conclusion-stated",
                                 "polarity-steering", "social-pressure",
                                 "scope-narrowing", "authorship-leak"})

    def test_a_question_that_cannot_be_answered_by_agreeing_is_clean(self):
        clean = ("Review the attached document against the attached data files.\n"
                 "For each numeric claim, state what the files support and flag any "
                 "claim they do not.\n")
        self.assertEqual(intent_leaks(clean), [])

    def test_quoted_material_is_not_linted(self):
        self.assertEqual(intent_leaks("> we show that X\n"), [])


class AllowFile(unittest.TestCase):
    @staticmethod
    def _tmp(text):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write(text)
            return fh.name

    def test_an_entry_without_a_reason_is_refused(self):
        path = self._tmp("# comment\nREADME.md  400  the dataset size\nREADME.md  1234\n")
        try:
            with self.assertRaises(SystemExit) as cm:
                read_allow(path, "README.md")
            self.assertIn("reason", str(cm.exception))
        finally:
            os.unlink(path)

    def test_an_entry_with_a_reason_is_accepted_and_exempts_the_number(self):
        path = self._tmp("report.md  9999  an identifier, not a measurement\n")
        try:
            allow = read_allow(path, "docs/report.md")
            f = trace("see run 9999", [Value(1, "f", "x")], allow)[0]
            self.assertEqual(f.verdict, "allowed")
            self.assertIn("identifier", f.reason)
        finally:
            os.unlink(path)

    def test_an_exemption_for_one_document_does_not_cover_another(self):
        """The bug this format exists for.

        With bare numbers, the README entry exempting an illustrative 97.50
        also exempted the figure deliberately fabricated into the broken
        example - and the test asserting that fixture fails started passing.
        An exemption is about one claim in one document.
        """
        path = self._tmp("README.md  97.50  an illustration, not a result\n")
        try:
            self.assertIn("97.50", read_allow(path, "README.md"))
            self.assertEqual(read_allow(path, "examples/broken/report.md"), {})
        finally:
            os.unlink(path)


class Derivations(unittest.TestCase):
    def test_a_derivation_that_fails_is_not_evidence(self):
        with self.assertRaises(SystemExit) as cm:
            run_derivations([f'{sys.executable} -c "import sys; sys.exit(3)"'])
        self.assertIn("exited 3", str(cm.exception))

    def test_printed_numbers_become_evidence_with_the_command_as_source(self):
        vals = run_derivations([f'{sys.executable} -c "print(6.25)"'])
        self.assertEqual([v.value for v in vals], [6.25])
        self.assertIn("print(6.25)", vals[0].source)


class ShippedExamplesRunFromAnywhere(unittest.TestCase):
    """The example a reader copies out of the README must not need a cwd.

    Found by installing the package into a clean virtualenv and running the
    README's own quickstart from an unrelated directory - which is the only way
    this class of defect shows up, because the repository root is where every
    test and every author happens to be standing.
    """

    def test_the_derivation_example_runs_from_another_directory(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            proc = subprocess.run([sys.executable, os.path.join(EX, "gain.py")],
                                  cwd=elsewhere, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("gain_points", proc.stdout)

    def test_tracing_the_example_from_another_directory(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            proc = subprocess.run(
                [sys.executable, "-m", "doubleblind", "trace",
                 os.path.join(EX, "report.md"),
                 "--data", os.path.join(EX, "results.json"),
                 "--derive", f'{sys.executable} {os.path.join(EX, "gain.py")}',
                 "--no-color"],
                cwd=elsewhere, capture_output=True, text=True,
                env={**os.environ, "PYTHONPATH": ROOT})
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("0 unsupported", proc.stdout)


class Packet(unittest.TestCase):
    def test_packet_contains_the_document_and_the_data_and_the_brief(self):
        text = build_packet([os.path.join(EX, "report.md")],
                            [os.path.join(EX, "results.json")])
        self.assertIn("DOCUMENT UNDER REVIEW", text)
        self.assertIn("DATA FILE", text)
        self.assertIn("not being told what it concluded", text)

    def test_the_shipped_brief_does_not_leak_intent_into_itself(self):
        from doubleblind.packet import REVIEWER_BRIEF
        self.assertEqual(intent_leaks(REVIEWER_BRIEF), [])


class CommandLine(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, "-m", "doubleblind", *args],
                              cwd=ROOT, capture_output=True, text=True,
                              env={**os.environ, "PYTHONPATH": ROOT})

    def test_clean_report_exits_zero(self):
        p = self._run("trace", "examples/report.md", "--data", "examples/results.json",
                      "--derive", DERIVE, "--no-color")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("does not say the sentences around them are true", p.stdout)

    def test_broken_report_exits_one(self):
        p = self._run("trace", "examples/broken/report.md", "--data", "examples/results.json",
                      "--derive", DERIVE, "--no-color")
        self.assertEqual(p.returncode, 1)
        self.assertIn("97.50%", p.stdout)

    def test_lint_exits_one_on_a_leaky_brief(self):
        p = self._run("lint", "examples/brief-leaky.md", "--no-color")
        self.assertEqual(p.returncode, 1)
        self.assertIn("answer-in-the-request", p.stdout)

    def test_lint_exits_zero_on_the_clean_brief(self):
        p = self._run("lint", "examples/brief-clean.md", "--no-color")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
