#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

EXCLUDED_FUNCTIONS = {
    "ref_for",
    "make_uniform_compatibility",
    "make_power_compatibility",
    "make_standardisation",
    "make_noise_evidence",
    "make_pilot_evidence",
    "make_hull_evidence",
    "fake_checker_source",
    "fake_temporal_extractor_source",
    "run_self_test",
}


class Collector(ast.NodeVisitor):
    def __init__(self, source: str) -> None:
        self.source = source
        self.functions: list[str] = []
        self.rows: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in EXCLUDED_FUNCTIONS:
            return
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def add(self, kind: str, node: ast.AST, test: ast.AST) -> None:
        expression = ast.get_source_segment(self.source, test)
        if expression is None:
            line = getattr(test, "lineno", "?")
            raise RuntimeError("no source segment at line {}".format(line))
        self.rows.append(
            {
                "id": len(self.rows) + 1,
                "kind": kind,
                "function": self.functions[-1] if self.functions else "<module>",
                "line": getattr(node, "lineno", test.lineno),
                "test_line": test.lineno,
                "test_end_line": getattr(test, "end_lineno", test.lineno),
                "col": test.col_offset,
                "end_col": getattr(test, "end_col_offset", test.col_offset),
                "expression": expression,
            }
        )

    def visit_If(self, node: ast.If) -> None:
        self.add("if", node, node.test)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.add("ifexp", node, node.test)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.add("while", node, node.test)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        for test in node.ifs:
            self.add("comprehension-if", node, test)
        self.generic_visit(node)

    def visit_match_case(self, node: ast.match_case) -> None:
        if node.guard is not None:
            self.add("match-guard", node, node.guard)
        self.generic_visit(node)


def char_column(line: str, byte_column: int) -> int:
    return len(line.encode("utf-8")[:byte_column].decode("utf-8"))


def offsets(source: str, row: dict[str, Any]) -> tuple[int, int]:
    lines = source.splitlines(keepends=True)
    start_line = row["test_line"] - 1
    end_line = row["test_end_line"] - 1
    start = sum(len(line) for line in lines[:start_line]) + char_column(
        lines[start_line], row["col"]
    )
    end = sum(len(line) for line in lines[:end_line]) + char_column(
        lines[end_line], row["end_col"]
    )
    return start, end


def unique_full_line_anchor(source: str, row: dict[str, Any]) -> str:
    lines = source.splitlines()
    left = row["test_line"] - 1
    right = row["test_end_line"]
    while True:
        anchor = "\n".join(lines[left:right])
        if source.count(anchor) == 1:
            return anchor
        if left == 0 and right == len(lines):
            raise RuntimeError(
                "no unique full-line anchor for guard {}".format(row["id"])
            )
        if left > 0:
            left -= 1
        if right < len(lines):
            right += 1


def mutate(source: str, row: dict[str, Any]) -> tuple[str, str]:
    anchor = unique_full_line_anchor(source, row)
    if source.count(anchor) != 1:
        raise RuntimeError("guard {} anchor count is not one".format(row["id"]))
    start, end = offsets(source, row)
    observed = source[start:end]
    if observed != row["expression"]:
        raise RuntimeError("guard {} source-position mismatch".format(row["id"]))
    replacement = "(False and ({}))".format(observed)
    mutant = source[:start] + replacement + source[end:]
    ast.parse(mutant)
    return mutant, anchor


def run(path: Path, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, str(path), "--self-test"],
            cwd=path.parent,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "timeout": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "returncode": None,
            "stdout": (error.stdout or "") if isinstance(error.stdout, str) else "",
            "stderr": (error.stderr or "") if isinstance(error.stderr, str) else "",
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "timeout": True,
        }


def signature(run_result: dict[str, Any]) -> str:
    if run_result["timeout"]:
        return "timeout"
    stderr_lines = [
        line.strip() for line in run_result["stderr"].splitlines() if line.strip()
    ]
    if stderr_lines:
        return stderr_lines[-1][:500]
    stdout_lines = [
        line.strip() for line in run_result["stdout"].splitlines() if line.strip()
    ]
    if stdout_lines:
        return stdout_lines[-1][:500]
    return "no output"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--stop", type=int)
    args = parser.parse_args()
    source_path = args.source.resolve()
    source = source_path.read_text(encoding="utf-8")
    source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    collector = Collector(source)
    collector.visit(ast.parse(source))
    stop = args.stop or len(collector.rows)
    selected = [row for row in collector.rows if args.start <= row["id"] <= stop]
    if len(selected) != stop - args.start + 1:
        raise RuntimeError("requested mutation range is incomplete")

    with tempfile.TemporaryDirectory(prefix="m155-m138-mutations-") as temporary:
        root = Path(temporary) / "project" / "experiments" / "M138-w1-gate-audit"
        root.mkdir(parents=True)
        mutant_path = root / "adjudicate.py"
        shutil.copy2(args.contract.resolve(), root / "corrected-gate-contract.json")
        mutant_path.write_text(source, encoding="utf-8")
        baseline = run(mutant_path, args.timeout)
        if (
            baseline["returncode"] != 0
            or not baseline["stdout"].startswith("self-test:")
            or baseline["stderr"]
        ):
            raise RuntimeError("baseline failed: {}".format(baseline))
        results = []
        for index, row in enumerate(selected, start=1):
            mutant, anchor = mutate(source, row)
            mutant_path.write_text(mutant, encoding="utf-8")
            observed = run(mutant_path, args.timeout)
            survived = (
                observed["returncode"] == baseline["returncode"]
                and observed["stdout"] == baseline["stdout"]
                and observed["stderr"] == baseline["stderr"]
                and not observed["timeout"]
            )
            result = {**row}
            result.update(
                {
                    "anchor": anchor,
                    "anchor_count": source.count(anchor),
                    "mutated": True,
                    "outcome": "SURVIVED" if survived else "KILLED",
                    "red_check": None
                    if survived
                    else "self_test_completion_banner_exact",
                    "observed_returncode": observed["returncode"],
                    "observed_stdout": observed["stdout"],
                    "observed_stderr": observed["stderr"],
                    "failure_signature": signature(observed),
                    "elapsed_seconds": observed["elapsed_seconds"],
                    "timeout": observed["timeout"],
                }
            )
            results.append(result)
            if index % 25 == 0 or index == len(selected):
                print(
                    json.dumps(
                        {
                            "progress": index,
                            "batch": len(selected),
                            "killed": sum(
                                item["outcome"] == "KILLED" for item in results
                            ),
                            "survived": sum(
                                item["outcome"] == "SURVIVED" for item in results
                            ),
                        }
                    ),
                    flush=True,
                )

        inert_anchor = (
            "Evidence-reading reference adjudicator for the corrected M138 W1 gate."
        )
        if source.count(inert_anchor) != 1:
            raise RuntimeError("inert anchor missing or nonunique")
        inert_source = source.replace(inert_anchor, inert_anchor + " Inert control.")
        mutant_path.write_text(inert_source, encoding="utf-8")
        inert_observed = run(mutant_path, args.timeout)
        inert_survived = (
            inert_observed["returncode"] == baseline["returncode"]
            and inert_observed["stdout"] == baseline["stdout"]
            and inert_observed["stderr"] == baseline["stderr"]
            and not inert_observed["timeout"]
        )

    killed = sum(row["outcome"] == "KILLED" for row in results)
    report = {
        "schema": "m155-m138-guard-mutation/v1",
        "definition": "statement-level executable decision guards in production adjudicator and CLI; excludes fixture builders and run_self_test",
        "source": str(source_path),
        "source_sha256": source_sha,
        "inventory_total": len(collector.rows),
        "range_start": args.start,
        "range_stop": stop,
        "mutated": len(results),
        "killed": killed,
        "survived": len(results) - killed,
        "named_red_check": "self_test_completion_banner_exact",
        "inert_control_survived": inert_survived,
        "inert_observed": inert_observed,
        "baseline": baseline,
        "mutations": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "inventory_total": len(collector.rows),
                "mutated": len(results),
                "killed": killed,
                "survived": len(results) - killed,
                "inert_control_survived": inert_survived,
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0 if inert_survived else 2


if __name__ == "__main__":
    raise SystemExit(main())
