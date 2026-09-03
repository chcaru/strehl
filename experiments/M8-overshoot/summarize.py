"""Validate M8 evidence and write a compact, persistent result record."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np


ARMS = (
    ("flat-et1s", 60),
    ("flat-et2.5s", 61),
    ("flat-et6s", 65),
)
COVER_RE = re.compile(r"field of view scaled to ([0-9.]+)")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def manifest_index(rows: list[dict]) -> str:
    text = "\n".join(
        f"{row['frame']}|{row['site']}|{row['count']}|{row['sha256']}"
        for row in sorted(rows, key=lambda row: (row["frame"], row["site"]))
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def validate_r(state: Path, expected_frames: int) -> tuple[dict, dict]:
    result_path = state / "m8-r.json"
    result = read_json(result_path)
    expected_sites = 4 * expected_frames
    if result["frames"] != expected_frames or result["sites"] != expected_sites:
        raise RuntimeError(
            f"{state}: expected {expected_frames} frames/{expected_sites} sites, "
            f"got {result['frames']}/{result['sites']}"
        )
    if result["coverage_mismatches"] != 0:
        raise RuntimeError(f"{state}: coordinate-validity mismatch")
    blocks = list((state / "blocks").glob("*.m8site"))
    if blocks:
        raise RuntimeError(f"{state}: {len(blocks)} trace blocks were not consumed")
    seen = list((state / "seen").iterdir())
    if len(seen) != expected_sites:
        raise RuntimeError(f"{state}: expected {expected_sites} markers, got {len(seen)}")

    counted = 0
    for row in result["violation_manifests"]:
        path = Path(row["path"])
        if sha256(path) != row["sha256"]:
            raise RuntimeError(f"{path}: manifest hash mismatch")
        count = int(np.load(path, mmap_mode="r").shape[0])
        if count != row["count"]:
            raise RuntimeError(f"{path}: expected {row['count']} rows, got {count}")
        counted += count
    if counted != result["violations"]:
        raise RuntimeError(
            f"{state}: manifests contain {counted}, result says {result['violations']}"
        )

    compact = {
        key: result[key]
        for key in (
            "denominator",
            "violations",
            "lower_violations",
            "upper_violations",
            "fraction",
            "percent",
            "min_lower_signed_excess",
            "max_upper_signed_excess",
            "max_abs_signed_excess",
            "coverage_mismatches",
        )
    }
    evidence = {
        "summary_sha256": sha256(result_path),
        "manifest_count": len(result["violation_manifests"]),
        "manifest_coordinates": counted,
        "manifest_index_sha256": manifest_index(result["violation_manifests"]),
    }
    return compact, evidence


def validate_o(state: Path) -> tuple[dict, dict]:
    result_path = state / "m8-o.json"
    result = read_json(result_path)
    manifest = Path(result["violations_file"])
    if sha256(manifest) != result["violations_sha256"]:
        raise RuntimeError(f"{manifest}: manifest hash mismatch")
    count = int(np.load(manifest, mmap_mode="r").shape[0])
    if count != result["violations"]:
        raise RuntimeError(f"{manifest}: expected {result['violations']} rows, got {count}")
    if result["unbracketed_samples"] != 0:
        raise RuntimeError(f"{state}: unbracketed final-output samples")

    compact = {
        key: result[key]
        for key in (
            "denominator",
            "violations",
            "lower_violations",
            "upper_violations",
            "fraction",
            "percent",
            "min_lower_signed_excess_linear",
            "max_upper_signed_excess_linear",
            "max_abs_signed_excess_linear",
            "max_abs_signed_excess_u16_lsb",
            "quantisation_tolerance",
            "unbracketed_samples",
            "clamping_caveat",
            "tiff_sha256",
        )
    }
    evidence = {
        "summary_sha256": sha256(result_path),
        "manifest_coordinates": count,
        "manifest_sha256": result["violations_sha256"],
    }
    return compact, evidence


def sum_int(rows: list[dict], key: str) -> int:
    return sum(int(row[key]) for row in rows)


def aggregate(rows: list[dict], *, linear: bool) -> dict:
    denominator = sum_int(rows, "denominator")
    violations = sum_int(rows, "violations")
    lower_key = (
        "min_lower_signed_excess_linear" if linear else "min_lower_signed_excess"
    )
    upper_key = (
        "max_upper_signed_excess_linear" if linear else "max_upper_signed_excess"
    )
    payload = {
        "denominator": denominator,
        "violations": violations,
        "lower_violations": sum_int(rows, "lower_violations"),
        "upper_violations": sum_int(rows, "upper_violations"),
        "fraction": violations / denominator,
        "percent": 100.0 * violations / denominator,
        lower_key: min(float(row[lower_key]) for row in rows),
        upper_key: max(float(row[upper_key]) for row in rows),
    }
    if linear:
        payload["max_abs_signed_excess_linear"] = max(
            float(row["max_abs_signed_excess_linear"]) for row in rows
        )
        payload["max_abs_signed_excess_u16_lsb"] = max(
            float(row["max_abs_signed_excess_u16_lsb"]) for row in rows
        )
    else:
        payload["max_abs_signed_excess"] = max(
            float(row["max_abs_signed_excess"]) for row in rows
        )
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    out = args.out_root.resolve()

    before = read_json(out / "inputs-before.json")
    after = read_json(out / "inputs-after.json")
    if before["captures"] != after["captures"]:
        raise RuntimeError("read-only capture metadata changed during the M8 run")

    commission = read_json(out / "commission" / "commission.json")
    if not commission["passed"]:
        raise RuntimeError("commissioning did not pass")
    independence = read_json(out / "independence-audit.json")
    if not independence["independent"]:
        raise RuntimeError("checker imports Strehl")

    identity, identity_evidence = validate_r(out / "identity-state", 1)
    if identity["violations"] or identity["coverage_mismatches"]:
        raise RuntimeError("identity M8-R null is not green")
    identity_meta = read_json(out / "identity-state" / "m8-r.json")
    if (
        identity_meta["copy_violations"]
        or identity_meta["copy_denominator"] != identity_meta["denominator"]
    ):
        raise RuntimeError("identity exact-copy null is not green")

    arms = {}
    r_rows: list[dict] = []
    o_rows: list[dict] = []
    for name, frames in ARMS:
        state = out / f"{name}-state"
        r_result, r_evidence = validate_r(state, frames)
        o_result, o_evidence = validate_o(state)
        meta = read_json(state / "meta.json")
        site_rows = list(meta["sites"].values())
        gain_ranges = {
            str(channel): [
                min(
                    float(row["site_gain"])
                    for row in site_rows
                    if row["channel"] == channel
                ),
                max(
                    float(row["site_gain"])
                    for row in site_rows
                    if row["channel"] == channel
                ),
            ]
            for channel in range(3)
        }
        log = (out / f"{name}-stack-v2.log").read_text(
            encoding="utf-8-sig", errors="replace"
        )
        match = COVER_RE.search(log)
        if match is None:
            raise RuntimeError(f"{name}: scale factor absent from run log")
        arms[name] = {
            "frames": frames,
            "sites": 4 * frames,
            "cover_scale": float(match.group(1)),
            "m8_o_normalization": {
                "formula": "output_gain / frame_site_gain / sensor_range",
                "output_gains": meta["output_gains"],
                "frame_site_gain_ranges": gain_ranges,
                "sensor_range": meta["range"],
            },
            "m8_r": r_result,
            "m8_r_evidence": r_evidence,
            "m8_o": o_result,
            "m8_o_evidence": o_evidence,
        }
        r_rows.append(r_result)
        o_rows.append(o_result)

    commission_arms = commission["arms"]
    commission_compact = {
        "passed": commission["passed"],
        "checks": commission["checks"],
        "catmull_hard_step": {
            key: commission_arms["catmull-hard-step"][key]
            for key in (
                "denominator",
                "violations",
                "lower_violations",
                "upper_violations",
                "min_lower_signed_excess",
                "max_upper_signed_excess",
            )
        },
        "copy_null": {
            key: commission_arms["copy-null"][key]
            for key in (
                "denominator",
                "violations",
                "copy_denominator",
                "copy_violations",
                "copy_max_abs",
            )
        },
        "bilinear_null": {
            key: commission_arms["bilinear-null"][key]
            for key in ("denominator", "violations")
        },
        "explicit_hi_lo_plant": {
            key: commission_arms["explicit-hi-lo-plant"][key]
            for key in (
                "denominator",
                "violations",
                "lower_violations",
                "upper_violations",
                "min_lower_signed_excess",
                "max_upper_signed_excess",
            )
        },
    }
    instrumentation = read_json(out / "source-instrumentation.json")
    payload = {
        "protocol": 2,
        "verdict": "FAIL",
        "reason": "M8-R and M8-O require exactly 0.0000%; all three development arms violate both bars.",
        "commissioning": commission_compact,
        "independence": independence,
        "identity": {
            "m8_r": identity,
            "copy_denominator": identity_meta["copy_denominator"],
            "copy_violations": identity_meta["copy_violations"],
            "copy_max_abs": identity_meta["copy_max_abs"],
            "evidence": identity_evidence,
        },
        "development_arms": arms,
        "aggregate": {
            "m8_r": aggregate(r_rows, linear=False),
            "m8_o": aggregate(o_rows, linear=True),
        },
        "read_only_inputs": {
            "method": before["method"],
            "before_utc": before["captured_utc"],
            "after_utc": after["captured_utc"],
            "unchanged": True,
            "captures": before["captures"],
        },
        "instrumentation": {
            "source_before_sha256": instrumentation["before"],
            "source_after_sha256": instrumentation["after"],
            "checker_sha256": independence["sha256"],
            "value_only_trace_protocol": 2,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
