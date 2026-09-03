"""Verify source pins and vendored candidate function equivalence.

This is deliberately separate from the measurement adapter.  It imports
neither candidate nor vendor code and reads live sources only by
repository-relative path.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path


EXPECTED = {
    "experiments/SCORECARD-BASELINE/common.py":
        "dff25996f1b4c055f5740e0fbd29b2e9ee848eaca7d5207dcb12f08e78d5ea45",
    "experiments/V-HEADTOHEAD3/ordinal.py":
        "8f27f44ae317880ca6bad2bc3fda9de03c9ca728dbb2432c91a92d896f27355f",
    "experiments/V-HEADTOHEAD3/sharpening_core.py":
        "0ea758cba1be5506ab370e9e7205ff0354ed63288e4d9c319e8bdb8389bc798d",
}

GROUPS = (
    (
        "experiments/SCORECARD-BASELINE/common.py",
        "experiments/M-PHASE0-SLANTEDGE/vendor_m1.py",
        ("window_2d", "frequency_grid", "m1_tile"),
    ),
    (
        "experiments/V-HEADTOHEAD3/ordinal.py",
        "experiments/M-PHASE0-SLANTEDGE/vendor_ordinal.py",
        ("midrank_field", "_spectral_shares", "ordinal_shares"),
    ),
    (
        "experiments/V-HEADTOHEAD3/sharpening_core.py",
        "experiments/M-PHASE0-SLANTEDGE/vendor_ordinal.py",
        ("_window", "frequency_radius", "licensed_mask", "q25_rank_field", "q25"),
    ),
)


def lf_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def function_asts(path: Path) -> dict[str, str]:
    tree = ast.parse(lf_bytes(path).decode("utf-8"), filename=str(path))
    return {
        node.name: ast.dump(node, annotate_fields=True, include_attributes=False)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def main() -> int:
    source_results = {}
    for relative, expected in EXPECTED.items():
        path = Path(relative)
        actual = hashlib.sha256(lf_bytes(path)).hexdigest()
        source_results[relative] = {
            "expected_lf_sha256": expected,
            "actual_lf_sha256": actual,
            "pass": actual == expected,
        }

    function_results = {}
    for live_relative, vendor_relative, names in GROUPS:
        live = function_asts(Path(live_relative))
        vendor = function_asts(Path(vendor_relative))
        for name in names:
            key = f"{live_relative}::{name}"
            function_results[key] = {
                "vendor": f"{vendor_relative}::{name}",
                "pass": name in live and name in vendor and live[name] == vendor[name],
            }

    green = (
        all(row["pass"] for row in source_results.values())
        and all(row["pass"] for row in function_results.values())
    )
    print(json.dumps({
        "schema": 1,
        "sources": source_results,
        "functions": function_results,
        "green": green,
    }, indent=2, sort_keys=True))
    return 0 if green else 2


if __name__ == "__main__":
    raise SystemExit(main())

