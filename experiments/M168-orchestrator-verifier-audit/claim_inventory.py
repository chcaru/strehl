#!/usr/bin/env python3
"""Inventory claim anchoring, skipped controls, and duplicate probes in v2954."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
FROZEN_COMMIT = "f267bbccfd450982720f747c64e383376df2c4f9"
AUDIT_COMMIT = sys.argv[1] if len(sys.argv) > 1 else FROZEN_COMMIT
M134_SHA = "8EA64C98795E51BC007E04775866C2145D1E2D6CFBA9F4F13B8413A3721FD1EF"


def variants(value: str) -> list[str]:
    result = {value, value.replace(",", "")}
    digits = value.replace(",", "")
    if re.fullmatch(r"\d+", digits):
        result.add(f"{int(digits):,}")
    return list(result)


def section(raw: str, section_id: str) -> str:
    match = re.search(rf"(?m)^### {re.escape(section_id)} .*?$", raw)
    if not match:
        return ""
    tail = raw[match.end():]
    next_heading = re.search(r"(?m)^###? ", tail)
    end = match.end() + (next_heading.start() if next_heading else len(tail))
    return raw[match.start():end]


def max_hits(text: str, probe: str) -> int:
    return max(text.count(value) for value in variants(probe))


def checker_matcher(tree: ast.Module, checker: Path):
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"variants", "rounds_to", "positions"}
    ]
    namespace = {"re": re}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(checker), "exec"), namespace)
    window = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "WINDOW" for target in node.targets):
            window = ast.literal_eval(node.value)
            break
    if window is None:
        raise AssertionError("WINDOW assignment not found")
    return namespace["positions"], window


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="M168-orch-inventory-") as td:
        root = Path(td) / "repo"
        archive = Path(td) / "snapshot.zip"
        proc = subprocess.run(
            [
                "git", "-C", str(REPO), "archive", "--format=zip",
                f"--output={archive}", AUDIT_COMMIT, "docs", "experiments/ORCH-verify",
                "experiments/M136-m8o-bar", "experiments/M163-m10-uncertainty",
            ],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(proc.stdout)
        shutil.unpack_archive(archive, root)
        m134_source = REPO / "experiments" / "M134-kernel-frontier" / "M137-clamped-detail.md"
        m134_dest = root / "experiments" / "M134-kernel-frontier" / "M137-clamped-detail.md"
        m134_dest.parent.mkdir(parents=True)
        if m134_source.exists():
            payload = m134_source.read_bytes()
            if hashlib.sha256(payload).hexdigest().upper() != M134_SHA:
                raise AssertionError("untracked M134 dependency changed")
            m134_dest.write_bytes(payload)
        else:
            m134_dest.write_text("M168 clean-clone fixture: 13.314850036584688\n", encoding="utf-8")

        checker = root / "experiments" / "ORCH-verify" / "v2954.py"
        tree = ast.parse(checker.read_text(encoding="utf-8"))
        checker_positions, window = checker_matcher(tree, checker)
        claim_node = None
        sections_node = None
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if "CLAIMS" in names and claim_node is None:
                claim_node = node.value
            if "SECTIONS" in names:
                sections_node = node.value
        if claim_node is None or sections_node is None:
            raise AssertionError("CLAIMS or SECTIONS assignment not found")
        sections = ast.literal_eval(sections_node)
        claims = eval(
            compile(ast.Expression(claim_node), str(checker), "eval"),
            {"__builtins__": {}},
            {"R": "docs/research/", "E": "experiments/"},
        )

        status_raw = (root / "docs" / "STATUS.md").read_text(encoding="utf-8")
        status_scope = re.sub(r"\s+", " ", "\n".join(section(status_raw, item) for item in sections))
        skipped = []
        status_duplicates = []
        source_duplicates = []
        source_literal_count = 0
        context_count = 0
        status_match_duplicates = []
        source_match_duplicates = []
        contextual_source_matches = []

        for claim in claims:
            label, needle, rel_path, *optional = claim
            context = optional[0] if len(optional) >= 1 else None
            source_literal = optional[1] if len(optional) >= 2 else None
            if context is not None:
                context_count += 1
            if source_literal is not None:
                source_literal_count += 1
            status_count = max_hits(status_scope, needle)
            if status_count > 1:
                status_duplicates.append((label, status_count, needle))
            status_matches = checker_positions(status_scope, needle, extend=False)
            if len(status_matches) > 1:
                status_match_duplicates.append((label, len(status_matches), needle))
            source = re.sub(
                r"\s+", " ",
                (root / rel_path).read_text(encoding="utf-8", errors="replace"),
            )
            source_probe = source_literal if source_literal is not None else needle
            source_count = max_hits(source, source_probe)
            if source_count > 1:
                source_duplicates.append((label, source_count, source_probe))
            source_matches = checker_positions(source, source_probe, extend=True)
            if context is not None:
                source_matches = [
                    match for match in source_matches
                    if context in source[max(0, match.start() - window):match.end() + window]
                ]
            if context is not None:
                contextual_source_matches.append((label, len(source_matches), context))
            if len(source_matches) > 1:
                source_match_duplicates.append((label, len(source_matches), source_probe))
            if re.search(r"\d", source_probe) is None:
                skipped.append(label)

        print(f"CLAIMS={len(claims)}")
        print(f"CTX_NON_NULL={context_count}")
        print(f"SOURCE_LITERAL_NON_NULL={source_literal_count}")
        print(f"SKIPPED={len(skipped)} {skipped}")
        print(f"STATUS_NON_UNIQUE={len(status_duplicates)}")
        for label, count, probe in status_duplicates:
            print(f"  {label}: hits={count} probe={probe}")
        print(f"SOURCE_NON_UNIQUE={len(source_duplicates)}")
        for label, count, probe in source_duplicates:
            print(f"  {label}: hits={count} probe={probe}")

        print(f"STATUS_MATCH_NON_UNIQUE={len(status_match_duplicates)}")
        for label, count, probe in status_match_duplicates:
            print(f"  {label}: matches={count} probe={probe}")
        print(f"SOURCE_MATCH_NON_UNIQUE={len(source_match_duplicates)}")
        for label, count, probe in source_match_duplicates:
            print(f"  {label}: matches={count} probe={probe}")
        print(f"CONTEXTUAL_SOURCE_MATCHES={len(contextual_source_matches)}")
        for label, count, context in contextual_source_matches:
            print(f"  {label}: matches={count} ctx={context}")

        pass_count = status_scope.count("PASS")
        intended = "recommissioned tonight and **passed**"
        print(f"RECOMMISSION_PASS_DECOYS={pass_count}")
        intended_has_uppercase_pass = "PASS" in intended
        print(f"INTENDED_RECOMMISSION_SENTENCE_CONTAINS_UPPERCASE_PASS={intended_has_uppercase_pass}")

        tracked = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "--error-unmatch", "--", "experiments/M134-kernel-frontier/M137-clamped-detail.md"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )
        print(f"M134_DEPENDENCY_TRACKED={tracked.returncode == 0}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
