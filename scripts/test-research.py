"""CLI regression tests for research discovery, retrieval and generated navigation.

Wrong inputs must fail: unknown terms, partial AND matches, generated-only hits,
missing catalog entries and output-tree copies. Run: python scripts/test-research.py
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/research.py"


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="strehl-research-test-", dir=os.environ.get("STREHL_TEST_TMP"))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs/research").mkdir(parents=True)
        self.write("docs/research/M41-wiener.md", "# M41 — Wiener deconvolution\n\nNoise model\nrejects the candidate.\n")
        self.write("experiments/marigold-pyramid/results.md", "# Marigold pyramid: rejected\n\nCoherent source membership failed.\n")
        self.write("experiments/marigold-pyramid/independent-results.md", "# Independent photographic review\n\nCoherent source membership failed.\n")
        self.write("experiments/marigold-pyramid/independent-plan.md", "# Proposed controls\n\nCoherent source membership plan.\n")

    def write(self, path, text):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8", newline="\n")

    def cli(self, *args, expected=0):
        run = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        self.assertNotIn("Traceback", run.stdout + run.stderr)
        return run.stdout

    def search(self, *args):
        return json.loads(self.cli("search", *args, "--json"))

    def test_default_and_and_explicit_any_have_different_results(self):
        self.assertEqual(self.search("Wiener", "membership")["total"], 0)
        self.assertGreaterEqual(self.search("Wiener", "membership", "--any")["total"], 3)
        self.assertEqual(self.search("zirconiumtuba")["total"], 0)

    def test_phrase_crosses_line_wrap_but_requires_order(self):
        result = self.search("noise model rejects", "--phrase")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["results"][0]["path"], "docs/research/M41-wiener.md")
        self.assertEqual(self.search("model noise", "--phrase")["total"], 0)

    def test_phrase_cannot_borrow_a_word_boundary_from_another_occurrence(self):
        self.write("docs/research/example.md", "# Example\n\nRAW colors. Draw focus paths.\n")
        self.assertEqual(self.search("raw focus", "--phrase")["total"], 0)
        self.write("docs/research/example.md", "# Example\n\nRAW focus paths.\n")
        self.assertEqual(self.search("raw focus", "--phrase")["total"], 1)

    def test_opaque_r3_report_is_browsable_under_reconstruction(self):
        self.write("docs/research/M41-r3-kill-measured.md",
                   "# M41 — the R3 kill experiment, measured\n\nMulti-frame Wiener deconvolution.\n")
        output = json.loads(self.cli("browse", "--topic", "reconstruction", "--area", "reports", "--json"))
        self.assertIn("docs/research/M41-r3-kill-measured.md", [d["path"] for d in output["results"]])

    def test_legacy_prior_art_excludes_generated_navigation(self):
        for name in ["README.md", "report-index.md", "experiment-index.md"]:
            self.write("docs/research/" + name, "# Generated navigation\n\nnavonlyword\n")
        spec = importlib.util.spec_from_file_location(
            "prior_art", ROOT / "experiments/ORCH-drift-check/prior_art.py")
        prior = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prior)
        prior.RESEARCH = str(self.root / "docs/research")
        self.assertEqual(prior.run(["navonlyword"], quiet=True), [])
        self.assertTrue(any(d["name"] == "M41-wiener.md" for d in prior.run(["Wiener"], quiet=True)))

    def test_word_boundaries_and_case(self):
        self.write("docs/research/drawn.md", "# Drawn figures\n\nDrawn once.\n")
        self.assertEqual(self.search("raw")["total"], 0)
        self.assertEqual(self.search("WIENER")["total"], 1)

    def test_filters_separate_results_reviews_plans_and_scenes(self):
        result = self.search("membership", "--scene", "marigold", "--kind", "result")
        self.assertEqual([d["path"] for d in result["results"]],
                         ["experiments/marigold-pyramid/results.md"])
        review = self.search("membership", "--kind", "review")
        self.assertEqual([d["path"] for d in review["results"]],
                         ["experiments/marigold-pyramid/independent-results.md"])
        self.assertEqual(self.search("membership", "--kind", "plan")["total"], 1)
        self.assertEqual(self.search("membership", "--area", "reports")["total"], 0)
        self.assertEqual(self.search("membership", "--scene", "printer")["total"], 0)
        self.assertGreater(self.search("pyramid", "--topic", "reconstruction")["total"], 0)

    def test_titles_beat_repetition_in_a_large_cross_reference(self):
        self.write("docs/research/giant.md", "# A cross-reference list\n\n" + "Wiener deconvolution " * 2000)
        result = self.search("Wiener", "deconvolution")
        self.assertEqual(result["results"][0]["path"], "docs/research/M41-wiener.md")

    def test_snippets_point_to_original_line_numbers(self):
        result = self.search("candidate")
        snippets = result["results"][0]["snippets"]
        self.assertEqual(snippets, [{"line": 4, "text": "rejects the candidate."}])

    def test_long_line_snippets_contain_the_match(self):
        self.write("docs/research/long.md", "# Long row\n\n" + "x " * 400 + "needle " + "y " * 400 + "\n")
        result = self.search("needle")
        snippet = result["results"][0]["snippets"][0]
        self.assertEqual(snippet["line"], 3)
        self.assertIn("needle", snippet["text"])
        self.assertTrue(snippet["text"].startswith("…"))
        self.assertTrue(snippet["text"].endswith("…"))

    def test_planarity_is_not_a_plan_and_pre_registration_is(self):
        self.write("experiments/chip/chip-planarity-triage.md", "# Planarity triage\n\nUniqueplanarityword.\n")
        self.write("experiments/chip/PRE-REGISTRATION.md", "# Proposed protocol\n\nUniqueplanarityword.\n")
        result = self.search("Uniqueplanarityword", "--kind", "plan")
        self.assertEqual([d["path"] for d in result["results"]],
                         ["experiments/chip/PRE-REGISTRATION.md"])

    def test_generated_indexes_and_deep_outputs_do_not_become_evidence(self):
        for name in ["README.md", "report-index.md", "experiment-index.md"]:
            self.write("docs/research/" + name, "# Navigation\n\nnavonlyword\n")
        self.write("experiments/marigold-pyramid/out/results.md", "# Output copy\n\noutputonlyword\n")
        self.write("experiments/marigold-pyramid/work/source/report.md", "# Snapshot\n\nsnapshotonlyword\n")
        self.assertEqual(self.search("navonlyword")["total"], 0)
        self.assertEqual(self.search("outputonlyword")["total"], 0)
        self.assertEqual(self.search("snapshotonlyword")["total"], 0)

    def test_source_only_directories_are_discoverable_without_reading_code(self):
        self.write("experiments/warp-baseline/source.rs", "not a document")
        result = self.search("warp", "--kind", "directory")
        self.assertEqual(result["results"][0]["path"], "experiments/warp-baseline")
        self.assertEqual(self.search("not a document")["total"], 0)

    def test_catalog_check_detects_a_missing_new_entry_and_does_not_write(self):
        self.cli("catalog")
        self.cli("catalog", "--check")
        path = self.root / "docs/research/report-index.md"
        before = path.read_bytes()
        self.write("docs/research/new-noise.md", "# New sensor noise report\n")
        output = self.cli("catalog", "--check", expected=1)
        self.assertIn("STALE:", output)
        self.assertEqual(path.read_bytes(), before)
        self.cli("catalog")
        self.cli("catalog", "--check")
        self.assertIn("new-noise.md", path.read_text(encoding="utf-8"))

    def test_catalog_does_not_change_sources_and_escapes_table_pipes(self):
        self.write("docs/research/pipe.md", "# Noise | signal\n\nRetained content.\n")
        path = self.root / "docs/research/pipe.md"
        before = path.read_bytes()
        self.cli("catalog")
        self.assertEqual(path.read_bytes(), before)
        report = (self.root / "docs/research/report-index.md").read_text(encoding="utf-8")
        self.assertIn(r"Noise \| signal", report)
        self.assertEqual(report.count("](pipe.md)"), 1)

    def test_review_count_does_not_move_a_reconstruction_group(self):
        self.cli("catalog")
        path = self.root / "docs/research/experiment-index.md"
        before = path.read_text(encoding="utf-8")
        for i in range(8):
            self.write(f"experiments/marigold-pyramid/review-{i}.md", "# Independent review\n")
        self.cli("catalog")
        after = path.read_text(encoding="utf-8")
        for catalog in [before, after]:
            reconstruction = catalog.split('<a id="reconstruction"></a>')[1].split('<a id="focus"></a>')[0]
            self.assertIn("marigold-pyramid", reconstruction)

    def test_invalid_inputs_are_errors_not_empty_successes(self):
        self.cli("search", "!!!", expected=2)
        self.cli("search", "Wiener", "--limit", "0", expected=2)
        self.cli("browse", "--topic", "invented-topic", expected=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
