from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("audit.json")


def read_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        failures.append(f"could not read {path.relative_to(ROOT)}: {exc}")
        return ""


def tracked_source_hits(pattern: str, failures: list[str]) -> list[str]:
    try:
        run = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "grep",
                "-l",
                "-E",
                pattern,
                "--",
                "*.py",
                "*.rs",
                ":!experiments/M-PHASE0-PIPE/**",
                ":!experiments/M163-m10-uncertainty/**",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        failures.append(f"git grep failed to start: {exc}")
        return []
    if run.returncode not in (0, 1):
        failures.append(f"git grep failed with exit {run.returncode}: {run.stderr.strip()}")
        return []
    return sorted(line for line in run.stdout.splitlines() if line)


def main() -> int:
    failures: list[str] = []
    m161 = read_text(ROOT / "docs/research/M161-bar-feasibility.md", failures)
    correction = read_text(
        ROOT / "docs/research/M161-m3-ratification.md", failures
    )
    measure_path = ROOT / "experiments/SCORECARD-BASELINE/measure.py"
    verify_path = ROOT / "experiments/SCORECARD-BASELINE/verify.py"
    measure = read_text(measure_path, failures)
    verify = read_text(verify_path, failures)
    manifest_text = read_text(
        ROOT / "experiments/SCORECARD-BASELINE/out/RUN-MANIFEST.json", failures
    )

    measure_functions: list[str] = []
    try:
        tree = ast.parse(measure, filename=str(measure_path))
        measure_functions = sorted(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("measure_m")
        )
    except Exception as exc:
        failures.append(f"could not parse measure.py: {exc}")

    verified_axes = sorted(
        set(re.findall(r'data\["(m[0-9]+)"\]', verify, flags=re.IGNORECASE))
    )
    try:
        manifest = json.loads(manifest_text)
        help_mentions_depth_output = manifest["capability_preflight"][
            "stack_help_mentions_depth_output"
        ]
    except Exception as exc:
        failures.append(f"could not read depth capability from run manifest: {exc}")
        help_mentions_depth_output = None

    decision_sources = tracked_source_hits(
        "ruler slope error|synthetic layer confusion|flat-null p95|valid target pixels",
        failures,
    )
    depth_sigma_sources = tracked_source_hits("depth_sigma_um", failures)
    sigma_z_sources = tracked_source_hits("sigma_z", failures)

    m161_read_only_anchor = (
        "This is a read-only document audit. I decoded no RAW, opened no protected "
        "output,\nran no stack, and ran no benchmark."
    )
    correction_anchor = (
        "describes an experiment M161 did not run. M161 proved a functional\n"
        "   invariance"
    )

    actual_m10_implementation_found = bool(
        "measure_m10" in measure_functions
        or "m10" in verified_axes
        or decision_sources
        or help_mentions_depth_output is True
    )
    substitutions = {
        name: {
            "status": "NOT_RUN",
            "reason": "no executable M10 decision accepts an uncertainty input",
        }
        for name in ("zero", "infinity", "random")
    }

    checks = {
        "m161_declares_read_only_document_audit": m161.count(m161_read_only_anchor)
        == 1,
        "later_report_says_substitution_was_not_run": correction.count(
            correction_anchor
        )
        == 1,
        "scorecard_measure_functions_are_only_m1_m2": measure_functions
        == ["measure_m1", "measure_m2"],
        "scorecard_verifier_reads_only_m1_m2": verified_axes == ["m1", "m2"],
        "frozen_cli_did_not_advertise_depth_output": help_mentions_depth_output is False,
        "no_tracked_m10_decision_source_contains_registered_terms": len(
            decision_sources
        )
        == 0,
        "no_actual_m10_implementation_found": not actual_m10_implementation_found,
    }
    if failures:
        checks["audit_completed_without_read_or_parse_failures"] = False

    result = {
        "verdict": "FAIL",
        "reason": (
            "The requested zero/infinity/random reproduction cannot run: the "
            "repository has no executable M10 score decision or compatible depth "
            "plus uncertainty product."
        ),
        "counts": {
            "m10_decision_source_files": len(decision_sources),
            "depth_sigma_symbol_source_files": len(depth_sigma_sources),
            "sigma_z_symbol_source_files": len(sigma_z_sources),
            "scorecard_measure_functions": len(measure_functions),
            "scorecard_verified_axes": len(verified_axes),
        },
        "files": {
            "m10_decision_source_files": decision_sources,
            "depth_sigma_symbol_source_files": depth_sigma_sources,
            "sigma_z_symbol_source_files": sigma_z_sources,
        },
        "scorecard_baseline": {
            "measure_functions": measure_functions,
            "verified_axes": verified_axes,
            "stack_help_mentions_depth_output": help_mentions_depth_output,
        },
        "actual_m10_implementation_found": actual_m10_implementation_found,
        "substitutions": substitutions,
        "checks": checks,
        "failures": failures,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(
        "FAIL substitution probe: no executable M10 implementation accepts "
        "reported uncertainty"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
