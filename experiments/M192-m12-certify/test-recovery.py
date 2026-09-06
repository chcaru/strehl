"""Focused fault injection for the M192 runner; no builds or RAW access."""

from __future__ import annotations

import copy
import ast
import errno
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from typing import Any


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m192_recovery_subject", HERE / "campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)


class FailingTerminal:
    closed = False

    def __init__(self, error: Exception, *, on_flush: bool = False):
        self.error = error
        self.on_flush = on_flush

    def write(self, text: str) -> int:
        if not self.on_flush:
            raise self.error
        return len(text)

    def flush(self) -> None:
        raise self.error


def record() -> dict:
    return {
        "run_id": "synthetic-progress-control",
        "memory": {
            "peak_process_tree_private_committed_bytes": 1024,
            "kernel_job_peak_memory": {"peak_job_memory_used_bytes": 2048},
        },
        "wall_seconds": 1.5,
        "sampling_coverage": 1.0,
        "whole_host_cpu_mean_percent": 12.5,
        "output_sha256": "A" * 64,
    }


class RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        # Use workspace ACL inheritance: tempfile's private directory is not
        # traversable from this Windows restricted execution token.
        self.root = HERE / f"recovery-test-{uuid.uuid4().hex}"
        self.root.mkdir()
        self.work = self.root / "work"
        self.results = self.root / "results"
        self.patch_work = patch.object(campaign, "WORK", self.work)
        self.patch_results = patch.object(campaign, "RESULTS", self.results)
        self.patch_work.start()
        self.patch_results.start()
        self.addCleanup(self.patch_work.stop)
        self.addCleanup(self.patch_results.stop)
        self.addCleanup(self.cleanup_workspace)

    def cleanup_workspace(self) -> None:
        target = self.root.resolve()
        self.assertEqual(target.parent, HERE.resolve())
        self.assertTrue(target.name.startswith("recovery-test-"))
        shutil.rmtree(target)

    def test_committed_progress_negative_control_exposes_errno22(self) -> None:
        source = subprocess.check_output(
            ["git", "-C", str(HERE), "show", "744a5c10:experiments/M192-m12-certify/campaign.py"],
            text=True,
        )
        node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "progress")
        namespace = {"Any": Any}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "744a5c10::progress", "exec"), namespace)
        old_record = {**record(), "sequence_index": 34}
        with patch.object(sys, "stdout", FailingTerminal(OSError(errno.EINVAL, "invalid terminal"))):
            with self.assertRaises(OSError) as raised:
                namespace["progress"](old_record)
        self.assertEqual(raised.exception.errno, errno.EINVAL)

    def test_terminal_failures_preserve_scored_journal_bytes(self) -> None:
        closed = io.StringIO()
        closed.close()
        terminals = [
            ("healthy", io.StringIO()),
            ("invalid", FailingTerminal(OSError(errno.EINVAL, "invalid terminal"))),
            ("bad-descriptor", FailingTerminal(OSError(errno.EBADF, "bad terminal"))),
            ("broken-pipe", FailingTerminal(BrokenPipeError(errno.EPIPE, "broken pipe"))),
            ("flush-invalid", FailingTerminal(OSError(errno.EINVAL, "flush failed"), on_flush=True)),
            ("closed", closed),
            ("absent", None),
        ]
        journals = []
        for name, terminal in terminals:
            with self.subTest(name=name):
                work = self.root / name
                with patch.object(campaign, "WORK", work), patch.object(sys, "stdout", terminal):
                    journal = campaign.Journal(work / "records.jsonl")
                    sealed = journal.append(record())
                    before = copy.deepcopy(sealed)
                    campaign.progress(sealed)
                    self.assertEqual(sealed, before)
                journals.append((work / "records.jsonl").read_bytes())
                events = [json.loads(line) for line in (work / "progress.jsonl").read_text().splitlines()]
                self.assertIn("synthetic-progress-control", events[0]["message"])
                if name != "healthy":
                    self.assertIn("terminal_unavailable", events[-1])
        self.assertTrue(all(value == journals[0] for value in journals))

    def test_diagnostic_disk_failure_is_fatal(self) -> None:
        self.work.mkdir()
        with patch.object(campaign.os, "fsync", side_effect=OSError(errno.ENOSPC, "disk full")):
            with self.assertRaises(OSError) as raised:
                campaign.emit_status("must persist before display")
        self.assertEqual(raised.exception.errno, errno.ENOSPC)

    def test_real_closed_descriptors_preserve_exit_and_journal(self) -> None:
        child = """
import importlib.util, json, os, sys
from pathlib import Path
s=importlib.util.spec_from_file_location('campaign', sys.argv[1])
c=importlib.util.module_from_spec(s); s.loader.exec_module(c)
c.WORK=Path(sys.argv[2])
c.Journal(c.WORK/'records.jsonl').append(json.loads(sys.argv[5]))
if sys.argv[4]=='closed': os.close(1 if sys.argv[3]=='stdout' else 2)
c.emit_status('terminal shutdown control', error=sys.argv[3]=='stderr')
"""
        journals = []
        for channel in ("stdout", "stderr"):
            for state in ("healthy", "closed"):
                with self.subTest(channel=channel, state=state):
                    work = self.root / f"child-{channel}-{state}"
                    work.mkdir()
                    completed = subprocess.run(
                        [sys.executable, "-B", "-c", child, str(HERE / "campaign.py"), str(work), channel, state, json.dumps(record())],
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertNotIn("Exception ignored", completed.stderr)
                    output = completed.stdout if channel == "stdout" else completed.stderr
                    self.assertEqual(output, "terminal shutdown control\n" if state == "healthy" else "")
                    journals.append((work / "records.jsonl").read_bytes())
                    diagnostics = (work / "progress.jsonl").read_text()
                    self.assertEqual("terminal_unavailable" in diagnostics, state == "closed")
        self.assertTrue(all(value == journals[0] for value in journals))

    def test_unexpected_terminal_exceptions_are_fatal(self) -> None:
        for error in (RuntimeError("bug"), ValueError("open-stream bug"), OSError(errno.EACCES, "denied")):
            with self.subTest(error=error), self.assertRaises(type(error)):
                campaign.write_terminal("message", FailingTerminal(error))

    def test_abort_keeps_original_traceback_when_stderr_is_unavailable(self) -> None:
        def fatal_campaign(spec: dict, jobs: int) -> None:
            self.work.mkdir()
            raise OSError(errno.EINVAL, "planted product failure")

        with patch.object(sys, "argv", ["campaign.py"]), patch.object(campaign, "run_campaign", fatal_campaign), patch.object(sys, "stderr", FailingTerminal(OSError(errno.EBADF, "gone"))):
            self.assertEqual(campaign.main(), 1)
        aborted = json.loads((self.work / "campaign-aborted.json").read_text())
        self.assertEqual(aborted["error_type"], "OSError")
        self.assertEqual(aborted["errno"], errno.EINVAL)
        self.assertIn("fatal_campaign", aborted["traceback"])
        self.assertIn("planted product failure", aborted["traceback"])
        self.assertFalse(aborted["resume_allowed"])

    def test_abort_record_disk_failure_is_not_swallowed(self) -> None:
        def fatal_campaign(spec: dict, jobs: int) -> None:
            self.work.mkdir()
            raise RuntimeError("original failure")

        with patch.object(sys, "argv", ["campaign.py"]), patch.object(campaign, "run_campaign", fatal_campaign), patch.object(campaign, "write_json", side_effect=OSError(errno.ENOSPC, "disk full")):
            with self.assertRaises(OSError) as raised:
                campaign.main()
        self.assertEqual(raised.exception.errno, errno.ENOSPC)
        self.assertIsInstance(raised.exception.__context__, RuntimeError)

    def test_existing_work_refusal_does_not_modify_previous_evidence(self) -> None:
        self.work.mkdir()
        prior = b'{"error":"original abort"}\n'
        (self.work / "campaign-aborted.json").write_bytes(prior)
        with patch.object(sys, "argv", ["campaign.py"]), patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(campaign.main(), 1)
        self.assertEqual((self.work / "campaign-aborted.json").read_bytes(), prior)
        self.assertEqual([path.name for path in self.work.iterdir()], ["campaign-aborted.json"])

    def test_fresh_campaign_path_is_scoped_and_does_not_touch_old_work(self) -> None:
        self.work.mkdir()
        marker = self.work / "untouched.txt"
        marker.write_text("old evidence")
        with patch.object(campaign, "HERE", self.root):
            work, results = campaign.campaign_paths(self.root / "new-run")
            self.assertEqual(work, self.root / "new-run" / "work")
            self.assertEqual(results, self.root / "new-run" / "results")
            self.assertFalse(work.exists())
            with self.assertRaisesRegex(RuntimeError, "inside M192"):
                campaign.campaign_paths(self.root.parent / "escaped")
        self.assertEqual(marker.read_text(), "old evidence")


if __name__ == "__main__":
    unittest.main(verbosity=2)
