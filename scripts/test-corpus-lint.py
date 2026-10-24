"""Regression tests for corpus-linter rule and allocation document routing.

Run: python scripts/test-corpus-lint.py
Fixtures use the CLI, including failing controls; no research corpus is modified.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LINTER = ROOT / "scripts" / "corpus_lint.py"
SYNTHESIS = """# Fixture

## 4. Measured facts

| n | claim | implication | source |
| --- | --- | --- | --- |
| 1 | A fixture fact. | None. | Fixture. |

## 5. Engineering discipline

## 7. Risks

## 10. Open questions
"""


class DocumentRoutingTests(unittest.TestCase):
    def setUp(self):
        # The optional override supports constrained Windows hosts whose default
        # native temporary-directory mapping is not writable by subprocesses.
        self.temp = tempfile.TemporaryDirectory(
            prefix="strehl-corpus-lint-", dir=os.environ.get("STREHL_TEST_TMP"))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("docs/research/SYNTHESIS.md", SYNTHESIS)
        self.write("AGENTS.md", "# Instructions\n\nRead the reference documents.\n")

    def write(self, path, text):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8", newline="\n")

    def lint(self, check):
        run = subprocess.run(
            [sys.executable, str(LINTER), "--root", str(self.root), "--only", check],
            capture_output=True, text=True, encoding="utf-8")
        self.assertNotIn("Traceback", run.stdout + run.stderr)
        return run.returncode, run.stdout

    def test_historical_rule_citations_resolve_in_ledger(self):
        self.write("docs/agents/engineering-ledger.md", "49. **Process ownership.**\n")
        self.write("docs/research/review.md", "Follow rule 49.\n")
        code, output = self.lint("C1")
        self.assertEqual(code, 0, output)
        self.assertIn("1 rules", output)
        # A renamed or missing rule must still be rejected, at its actual source.
        self.write("docs/research/review.md", "Follow rule 50.\n")
        code, output = self.lint("C1")
        self.assertEqual(code, 1, output)
        self.assertIn("engineering-ledger.md has no rule 50", output)

    def test_root_numbered_items_do_not_declare_historical_rules(self):
        self.write("docs/agents/engineering-ledger.md", "49. **Process ownership.**\n")
        self.write("AGENTS.md", "1. **Unrelated startup step.**\n")
        self.write("docs/research/review.md", "Follow rule 1.\n")
        code, output = self.lint("C1")
        self.assertEqual(code, 1, output)
        self.assertIn("engineering-ledger.md has no rule 1", output)

    def test_allocated_report_is_exempt_and_unallocated_report_fails(self):
        self.write("docs/agents/milestone-ledger.md",
                   "| milestone | report |\n| --- | --- |\n"
                   "| M900 | `docs/research/M900-future.md` |\n")
        self.write("docs/research/review.md", "See docs/research/M900-future.md.\n")
        code, output = self.lint("C2")
        self.assertEqual(code, 0, output)
        self.write("docs/research/review.md", "See docs/research/M901-missing.md.\n")
        code, output = self.lint("C2")
        self.assertEqual(code, 1, output)
        self.assertIn("M901-missing.md", output)
        self.assertIn("not allocated in the ledger", output)

    def test_arbitrary_reference_prose_does_not_exempt_dead_reports(self):
        self.write("docs/agents/milestone-ledger.md", "# Allocations\n")
        self.write("AGENTS.md", "See docs/research/M900-missing.md.\n")
        self.write("docs/agents/research-index.md", "See docs/research/M900-missing.md.\n")
        code, output = self.lint("C2")
        self.assertEqual(code, 1, output)
        self.assertIn("AGENTS.md:1: [C2]", output)
        self.assertIn("docs/agents/research-index.md:1: [C2]", output)

    def test_reference_markdown_is_checked_not_only_loaded_for_rules(self):
        self.write("docs/agents/experiment-history.md",
                   "| a | b |\n| --- | --- |\n| x | y | extra |\n")
        code, output = self.lint("S1")
        self.assertEqual(code, 1, output)
        self.assertIn("docs/agents/experiment-history.md:3: [S1]", output)
        # Removing the extra cell must remove the specific finding.
        self.write("docs/agents/experiment-history.md",
                   "| a | b |\n| --- | --- |\n| x | y |\n")
        code, output = self.lint("S1")
        self.assertEqual(code, 0, output)

    def test_legacy_fixture_roots_still_work(self):
        self.write("AGENTS.md", "49. **Original rule.**\n\n"
                   "| milestone | report |\n| --- | --- |\n"
                   "| M900 | docs/research/M900-future.md |\n")
        self.write("docs/research/review.md", "Follow rule 49; see docs/research/M900-future.md.\n")
        code, output = self.lint("C1,C2")
        self.assertEqual(code, 0, output)
        self.assertIn("1 rules", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
