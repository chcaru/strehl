#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
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


class Inventory(ast.NodeVisitor):
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
            raise RuntimeError(f"no source segment at {node.lineno}")
        self.rows.append(
            {
                "id": len(self.rows) + 1,
                "kind": kind,
                "function": self.functions[-1] if self.functions else "<module>",
                "line": getattr(node, "lineno", test.lineno),
                "test_line": test.lineno,
                "test_end_line": getattr(test, "end_lineno", test.lineno),
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = args.source.read_text(encoding="utf-8")
    inventory = Inventory(source)
    inventory.visit(ast.parse(source))
    by_kind: dict[str, int] = {}
    by_function: dict[str, int] = {}
    for row in inventory.rows:
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
        by_function[row["function"]] = by_function.get(row["function"], 0) + 1
    result = {
        "definition": "statement-level executable decision guards in production adjudicator and CLI; excludes fixture builders and run_self_test",
        "total": len(inventory.rows),
        "by_kind": by_kind,
        "by_function": by_function,
        "guards": inventory.rows,
    }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded, encoding="utf-8")
        print(
            json.dumps(
                {
                    "total": len(inventory.rows),
                    "by_kind": by_kind,
                    "output": str(args.output),
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
