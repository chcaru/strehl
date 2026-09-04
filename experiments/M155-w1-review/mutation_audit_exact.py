#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import types
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


class CachedSubprocess:
    CalledProcessError = subprocess.CalledProcessError
    SubprocessError = subprocess.SubprocessError

    def __init__(self) -> None:
        self.cache: dict[tuple[Any, ...], tuple[int, str, str]] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def referenced_files(value: Any, base: Path) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        if isinstance(value, dict):
            if set(value) == {"path", "sha256"} and isinstance(value.get("path"), str):
                dependency = (base / value["path"]).resolve()
                if dependency.is_file():
                    digest = hashlib.sha256(dependency.read_bytes()).hexdigest()
                else:
                    digest = "MISSING"
                found.append((value["path"], digest))
            for child in value.values():
                found.extend(CachedSubprocess.referenced_files(child, base))
        elif isinstance(value, list):
            for child in value:
                found.extend(CachedSubprocess.referenced_files(child, base))
        return found

    @staticmethod
    def key(command: list[str]) -> tuple[Any, ...]:
        parts: list[Any] = []
        for token in command:
            path = Path(token)
            if path.is_file():
                data = path.read_bytes()
                parts.append(("file", hashlib.sha256(data).hexdigest()))
                if path.suffix == ".json":
                    try:
                        value = json.loads(data.decode("utf-8"))
                    except (UnicodeError, json.JSONDecodeError):
                        value = None
                    parts.extend(CachedSubprocess.referenced_files(value, path.parent))
            else:
                parts.append(("arg", token))
        return tuple(parts)

    def run(
        self, command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        key = self.key(command)
        if key not in self.cache:
            completed = subprocess.run(command, **kwargs)
            self.cache[key] = (completed.returncode, completed.stdout, completed.stderr)
            self.misses += 1
        else:
            self.hits += 1
        returncode, stdout, stderr = self.cache[key]
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    @staticmethod
    def check_output(*args: Any, **kwargs: Any) -> bytes:
        return subprocess.check_output(*args, **kwargs)


def run(
    path: Path, contract: Path, cache: CachedSubprocess, serial: int
) -> dict[str, Any]:
    started = time.monotonic()
    stdout = io.StringIO()
    stderr = io.StringIO()
    returncode: int | None = None
    module_name = "m138_mutant_{}".format(serial)
    try:
        module = types.ModuleType(module_name)
        module.__file__ = str(path)
        module.__package__ = ""
        sys.modules[module_name] = module
        source_bytes = path.read_bytes()
        exec(
            compile(source_bytes, str(path), "exec", dont_inherit=True), module.__dict__
        )
        module.subprocess = cache
        old_argv = sys.argv
        sys.argv = [str(path), "--self-test", "--contract", str(contract)]
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = module.main()
        finally:
            sys.argv = old_argv
    except BaseException:
        traceback.print_exc(file=stderr)
        returncode = 1
    finally:
        sys.modules.pop(module_name, None)
    return {
        "returncode": returncode,
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "timeout": False,
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
        cache = CachedSubprocess()
        baseline = run(mutant_path, root / "corrected-gate-contract.json", cache, 0)
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
            observed = run(
                mutant_path, root / "corrected-gate-contract.json", cache, index
            )
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
        inert_observed = run(
            mutant_path, root / "corrected-gate-contract.json", cache, len(selected) + 1
        )
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
        "subprocess_cache": {
            "hits": cache.hits,
            "misses": cache.misses,
            "entries": len(cache.cache),
        },
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
