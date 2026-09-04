#!/usr/bin/env python3
"""Adversarial tests for v2954 positions(), rounds_to(), and the 7c repairs.

All full-verifier mutations are confined to a temporary Git archive.
"""

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
DEFAULT_COMMIT = "7c65f8a4444d2c2fb239e589f56466da9e7aa7e2"
TARGET_COMMIT = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_COMMIT
M134_SHA = "8EA64C98795E51BC007E04775866C2145D1E2D6CFBA9F4F13B8413A3721FD1EF"
M167_SHA = "210675AB3BC25FCE53EE090AAEE98E69330E95F3EC8C19FDC1CA59BCEF9229B0"


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(f"anchor {old!r}: expected {count}, got {actual}")
    return text.replace(old, new)


def archive_tree(root: Path, archive: Path) -> None:
    command = [
        "git", "-C", str(REPO), "archive", "--format=zip", f"--output={archive}",
        TARGET_COMMIT, "docs", "experiments/ORCH-verify", "experiments/M136-m8o-bar",
        "experiments/M163-m10-uncertainty", "experiments/M175-fork-arm",
    ]
    optional = "experiments/M175-fork-arm"
    exists = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "-e", f"{TARGET_COMMIT}:{optional}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if exists.returncode != 0:
        command.remove(optional)
    proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.returncode != 0:
        raise AssertionError(proc.stdout)
    shutil.unpack_archive(archive, root)
    source = REPO / "experiments" / "M134-kernel-frontier" / "M137-clamped-detail.md"
    if source.exists():
        payload = source.read_bytes()
        if hashlib.sha256(payload).hexdigest().upper() != M134_SHA:
            raise AssertionError("untracked M134 dependency changed")
    else:
        payload = b"M168 clean-clone fixture: 13.314850036584688\n"
    destination = root / "experiments" / "M134-kernel-frontier" / "M137-clamped-detail.md"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)


def load_helpers(checker: Path):
    tree = ast.parse(checker.read_text(encoding="utf-8"), filename=str(checker))
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"variants", "rounds_to", "positions"}
    ]
    namespace = {"re": re}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(checker), "exec"), namespace)
    return namespace["positions"], namespace["rounds_to"]


def run_verifier(checker: Path, root: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-B", str(checker), str(root)],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def selected(output: str, labels: tuple[str, ...]) -> str:
    lines = []
    for line in output.splitlines():
        if line.startswith("VERDICT:"):
            lines.append(line.strip())
        elif line.startswith(("GREEN", "RED")) and any(label in line for label in labels):
            lines.append(line.strip())
    return " | ".join(lines)


def mutate_contexts(checker_text: str, contexts: list[str]) -> str:
    result = checker_text
    for context in contexts:
        old = f"R + \"M164-reference-identifiability.md\", \"{context}\")"
        new = f"R + \"M164-reference-identifiability.md\", None, \"{context}\")"
        result = replace_exact(result, old, new)
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="M168-boundary-") as td:
        root = Path(td) / "repo"
        archive_tree(root, Path(td) / "snapshot.zip")
        checker = root / "experiments" / "ORCH-verify" / "v2954.py"
        status = root / "docs" / "STATUS.md"
        ref_source = root / "docs" / "research" / "M164-reference-identifiability.md"
        original_checker = checker.read_text(encoding="utf-8")
        original_status = status.read_text(encoding="utf-8")
        original_ref = ref_source.read_text(encoding="utf-8")

        positions, rounds_to = load_helpers(checker)
        digest = M167_SHA
        cases = [
            ("exact decimal", "v=2.0312x", "2.0312", False, True),
            ("strict longer prefix", "v=2.031203x", "2.0312", False, False),
            ("rounded source prefix", "v=2.031203x", "2.0312", True, True),
            ("nonrounding source prefix", "v=2.03126x", "2.0312", True, False),
            ("negative sign ignored", "v=-0.27", "0.27", False, False),
            ("fractional suffix accepted", "v=0.96", "96", False, False),
            ("integer prefix of decimal", "v=96.5", "96", False, False),
            ("grouped larger number", "v=1,602,000", "1,602", False, False),
            ("numeric token inside hex", "sha=A96F", "96", False, False),
            ("full SHA with appended hex", f"sha={digest}A", digest, False, False),
            ("mantissa mistaken for scalar", "v=1.11e-15", "1.11", False, False),
            ("left-side longer number", "v=10.27", "0.27", False, False),
            ("rounded percent source", "v=1.5604%", "1.560%", True, True),
            ("rounded unit source", "v=2.031203x", "2.0312x", True, True),
            ("rounded exponent source", "v=1.1100e-15", "1.11e-15", True, True),
        ]
        bugs = 0
        for name, haystack, needle, extend, expected in cases:
            actual = bool(positions(haystack, needle, extend=extend))
            result = "OK" if actual == expected else ("FALSE_GREEN" if actual else "FALSE_RED")
            if actual != expected:
                bugs += 1
            print(f"DIRECT {name}: expected={expected} actual={actual} result={result}")

        decimal_expected = False
        float_actual = rounds_to("2.675", "2.67")
        round_result = "FALSE_GREEN" if float_actual else "OK"
        print(
            "ROUNDS binary midpoint 2.675->2.67: "
            f"decimal_half_even_expected={decimal_expected} actual={float_actual} "
            f"result={round_result}"
        )
        if float_actual != decimal_expected:
            bugs += 1
        print(f"DIRECT_BUGS={bugs}")
        if bugs != 11:
            raise AssertionError(f"expected 11 direct boundary defects, got {bugs}")

        baseline_rc, baseline_out = run_verifier(checker, root)
        print(f"BASELINE commit={TARGET_COMMIT} exit={baseline_rc} | {selected(baseline_out, ())}")
        if baseline_rc != 0:
            raise AssertionError(baseline_out)

        def status_false_green(name: str, label: str, old: str, new: str) -> None:
            status.write_text(replace_exact(original_status, old, new), encoding="utf-8")
            ref_source.write_text(original_ref, encoding="utf-8")
            checker.write_text(original_checker, encoding="utf-8")
            rc, output = run_verifier(checker, root)
            print(f"INTEGRATION_FALSE_GREEN {name}: exit={rc} | {selected(output, (label,))}")
            if rc != 0 or "VERDICT: GREEN" not in output:
                raise AssertionError(output)

        status_false_green(
            "negative exponent",
            "aperture airy calibration error",
            "relative calibration error between the two worlds is `1.11e-15`, machine epsilon.",
            "relative calibration error between the two worlds is `-1.11e-15`, machine epsilon.",
        )
        status_false_green(
            "comma-grouped larger count",
            "M1 capture exposures",
            "first-stated minimum capture is **1,661 exposures**",
            "first-stated minimum capture is **1,661,000 exposures**",
        )
        status_false_green(
            "SHA with appended hex digit",
            "m167 results sha",
            f"`{digest}`",
            f"`{digest}A`",
        )

        status.write_text(original_status, encoding="utf-8")
        checker.write_text(original_checker, encoding="utf-8")
        changed_source = replace_exact(original_ref, "ratio of `0.698970`", "ratio of `0.698971`")
        ref_source.write_text(changed_source, encoding="utf-8")
        rc, output = run_verifier(checker, root)
        print(f"MIS_SLOT_REPAIR numeric source mutation: exit={rc} | {selected(output, ('ref info dominance ratio',))}")
        if rc == 0 or "RED   ref info dominance ratio" not in output:
            raise AssertionError(output)

        contextual_decoy = replace_exact(
            original_ref,
            "ratio of `0.698970`, despite",
            "ratio of `0.698971` (not `0.698970`), despite",
        )
        ref_source.write_text(contextual_decoy, encoding="utf-8")
        rc, output = run_verifier(checker, root)
        print(f"CTX_FALSE_GREEN negated nearby decoy: exit={rc} | {selected(output, ('ref info dominance ratio',))}")
        if rc != 0 or "VERDICT: GREEN" not in output:
            raise AssertionError(output)

        negative_source = replace_exact(original_ref, "ratio of `0.698970`", "ratio of `-0.698970`")
        ref_source.write_text(negative_source, encoding="utf-8")
        rc, output = run_verifier(checker, root)
        print(f"INTEGRATION_FALSE_GREEN negative source ratio: exit={rc} | {selected(output, ('ref info dominance ratio',))}")
        if rc != 0 or "VERDICT: GREEN" not in output:
            raise AssertionError(output)

        rounded_source = replace_exact(original_ref, "`1.560%`", "`1.5604%`")
        ref_source.write_text(rounded_source, encoding="utf-8")
        rc, output = run_verifier(checker, root)
        print(f"INTEGRATION_FALSE_RED rounded percent source: exit={rc} | {selected(output, ('margin over bar',))}")
        if rc == 0 or "RED   margin over bar" not in output:
            raise AssertionError(output)

        ref_source.write_text(original_ref, encoding="utf-8")
        canonical_old = "`2.7015 / 1.33 = 2.0312x` with a margin"
        canonical_new = "`2.7015 / 1.33 = 2.0313x` with a margin"
        status.write_text(replace_exact(original_status, canonical_old, canonical_new), encoding="utf-8")
        checker.write_text(original_checker, encoding="utf-8")
        current_rc, current_out = run_verifier(checker, root)
        bare_checker = replace_exact(
            original_checker,
            "in_status = bool(positions(sec, needle))",
            "in_status = any(v in sec for v in variants(needle))",
        )
        checker.write_text(bare_checker, encoding="utf-8")
        bare_rc, bare_out = run_verifier(checker, root)
        print(f"PREFIX_REPAIR current: exit={current_rc} | {selected(current_out, ('preflight design ratio',))}")
        print(f"PREFIX_REPAIR reconstructed_bare: exit={bare_rc} | {selected(bare_out, ('preflight design ratio',))}")
        if current_rc == 0 or bare_rc != 0:
            raise AssertionError("prefix repair reconstruction did not separate current and bare matching")

        contexts = [
            "a ratio of",
            "reference information",
            "scored state",
            "stronger reference transfer",
            "dominance gate can move",
            "relative to the bar",
            "achieved ratio",
        ]
        status.write_text(original_status, encoding="utf-8")
        ref_source.write_text(original_ref, encoding="utf-8")
        checker.write_text(mutate_contexts(original_checker, contexts[:5]), encoding="utf-8")
        five_rc, five_out = run_verifier(checker, root)
        five_skips = re.search(r"controls skipped\s+: (\d+)", five_out)
        print(f"MIS_SLOT first_five: exit={five_rc} skipped={five_skips.group(1) if five_skips else 'missing'}")

        all_misslotted = mutate_contexts(original_checker, contexts)
        checker.write_text(all_misslotted, encoding="utf-8")
        seven_rc, seven_out = run_verifier(checker, root)
        seven_skips = re.search(r"controls skipped\s+: (\d+)", seven_out)
        print(f"MIS_SLOT all_seven: exit={seven_rc} skipped={seven_skips.group(1) if seven_skips else 'missing'} | {selected(seven_out, ('ref info dominance ratio',))}")
        if five_rc != 0 or seven_rc != 0 or five_skips is None or seven_skips is None:
            raise AssertionError(seven_out)
        if five_skips.group(1) != "11" or seven_skips.group(1) != "13":
            raise AssertionError("mis-slot skip counts did not match reconstruction")

        wrong_numbers = original_ref
        replacements = {
            "0.698970": "0.698971",
            "1.160964": "1.160965",
            "1.660964": "1.660965",
            "2.350220": "2.350221",
            "1.414973": "1.414974",
            "1.560%": "1.561%",
            "1.536%": "1.537%",
        }
        for value, replacement in replacements.items():
            if value not in wrong_numbers:
                raise AssertionError(f"missing source value {value}")
            wrong_numbers = wrong_numbers.replace(value, replacement)
        ref_source.write_text(wrong_numbers, encoding="utf-8")
        checker.write_text(all_misslotted, encoding="utf-8")
        wrong_rc, wrong_out = run_verifier(checker, root)
        print(f"MIS_SLOT all_source_numbers_changed: exit={wrong_rc} | {selected(wrong_out, ('ref info dominance ratio', 'ref bits inferior', 'margin over bar'))}")
        if wrong_rc != 0 or "VERDICT: GREEN" not in wrong_out:
            raise AssertionError(wrong_out)

    print("BOUNDARY_ATTACKS: ALL EXPECTED RESULTS REPRODUCED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
