from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LANE = Path(__file__).resolve().parent
OUTPUT_RECORD = LANE / "results" / "negative-control.json"
FLOAT_RECORD = LANE / "results" / "float-witness.json"
SUMMARY = LANE / "results" / "negative-control-summary.json"
PATCH = LANE / "float-witness.patch"
WORKERS = (1, 2, 4, 8, 16)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def compact_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def sha256_file(path: Path, block_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, indent=2, sort_keys=True, allow_nan=False)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def by_key(records: list[dict[str, Any]]) -> dict[tuple[str, int, str, int], dict[str, Any]]:
    result = {}
    for row in records:
        key = (row["arm"], row["limit"], row["alignment"], row["workers"])
        require(key not in result, f"duplicate output record {key}")
        result[key] = row
    return result


def validate_record_rows(
    rows: list[dict[str, Any]],
    planned_ids: set[str],
    label: str,
) -> None:
    require(
        {row["run_id"] for row in rows} == planned_ids,
        f"{label} run IDs do not match the frozen plan",
    )
    for row in rows:
        frozen = row["record_sha256"]
        actual = compact_sha256(
            {key: value for key, value in row.items() if key != "record_sha256"}
        )
        require(frozen == actual, f"{label} record hash failed: {row['run_id']}")
        require(row["valid"], f"{label} invalid run: {row['run_id']}")
        require(row["returncode"] == 0, f"{label} nonzero exit: {row['run_id']}")
        require(not row["output_retained"], f"{label} retained TIFF: {row['run_id']}")


def validate_output(data: dict[str, Any]) -> dict[str, Any]:
    require(
        data["protocol_sha256"] == compact_sha256(data["protocol"]),
        "output protocol hash failed",
    )
    planned_ids = {row["run_id"] for row in data["protocol"]["plans"]}
    rows = data["records"]
    validate_record_rows(rows, planned_ids, "output")
    require(len(rows) == 19, "output matrix is incomplete")
    keyed = by_key(rows)

    n16 = [keyed[("pre", 16, "off", worker)] for worker in WORKERS]
    n17 = [keyed[("pre", 17, "off", worker)] for worker in (1, 16)]
    n33_off = [keyed[("pre", 33, "off", worker)] for worker in (1, 16)]
    n33_pre = [keyed[("pre", 33, "on", worker)] for worker in WORKERS]
    n33_post = [keyed[("post", 33, "on", worker)] for worker in WORKERS]

    n16_pixels = {row["workers"]: row["pixel_sha256"] for row in n16}
    n33_pre_pixels = {row["workers"]: row["pixel_sha256"] for row in n33_pre}
    n33_post_pixels = {row["workers"]: row["pixel_sha256"] for row in n33_post}
    require(len(set(n16_pixels.values())) == 4, "N=16 must have four pixel hashes")
    require(n16_pixels[1] == n16_pixels[16], "N=16 W1/W16 structural null moved")
    require(n16_pixels[1] != n16_pixels[2], "N=16 W1/W2 negative control did not fire")
    require(
        n17[0]["pixel_sha256"] != n17[1]["pixel_sha256"],
        "N=17 W1/W16 negative control did not fire",
    )
    require(
        n33_off[0]["pixel_sha256"] != n33_off[1]["pixel_sha256"],
        "N=33 unaligned W1/W16 negative control did not fire",
    )
    require(
        len(set(n33_pre_pixels.values())) == 5,
        "N=33 aligned pre arm must have five pixel hashes",
    )
    require(
        len(set(n33_post_pixels.values())) == 1,
        "N=33 aligned post arm must have one pixel hash",
    )
    require(
        len({row["output_sha256"] for row in n33_post}) == 1,
        "N=33 aligned post arm must have one TIFF hash",
    )
    return {
        "n16_unaligned_pre": {
            "distinct_pixel_sha256": len(set(n16_pixels.values())),
            "pixel_sha256_by_worker": n16_pixels,
        },
        "n17_unaligned_pre": {
            "w1": n17[0]["pixel_sha256"],
            "w16": n17[1]["pixel_sha256"],
        },
        "n33_unaligned_pre": {
            "w1": n33_off[0]["pixel_sha256"],
            "w16": n33_off[1]["pixel_sha256"],
        },
        "n33_aligned_pre": {
            "distinct_pixel_sha256": len(set(n33_pre_pixels.values())),
            "pixel_sha256_by_worker": n33_pre_pixels,
        },
        "n33_aligned_post": {
            "distinct_pixel_sha256": len(set(n33_post_pixels.values())),
            "pixel_sha256": n33_post[0]["pixel_sha256"],
            "tiff_sha256": n33_post[0]["output_sha256"],
        },
    }


def validate_float(
    data: dict[str, Any],
    output_rows: dict[tuple[str, int, str, int], dict[str, Any]],
) -> dict[str, Any]:
    require(
        data["protocol_sha256"] == compact_sha256(data["protocol"]),
        "float protocol hash failed",
    )
    require(
        data["protocol"]["instrument"]["patch_sha256"] == sha256_file(PATCH),
        "float witness patch hash failed",
    )
    for arm, build in data["builds"].items():
        binary = Path(build["binary"])
        log = Path(build["build_log"])
        require(binary.is_file(), f"{arm} diagnostic binary is missing")
        require(
            sha256_file(binary) == build["binary_sha256"],
            f"{arm} diagnostic binary hash failed",
        )
        require(log.is_file(), f"{arm} build log is missing")
        require(
            sha256_file(log) == build["build_log_sha256"],
            f"{arm} build log hash failed",
        )
        require(
            "Compiling strehl-cli"
            in log.read_text(encoding="utf-8", errors="replace"),
            f"{arm} build log lacks a compile witness",
        )

    planned_ids = {row["run_id"] for row in data["protocol"]["plans"]}
    rows = data["records"]
    validate_record_rows(rows, planned_ids, "float")
    require(len(rows) == 10, "float matrix is incomplete")
    for row in rows:
        key = (row["arm"], row["limit"], row["alignment"], row["workers"])
        reference = output_rows[key]
        require(
            row["pixel_sha256"] == reference["pixel_sha256"]
            and row["output_sha256"] == reference["output_sha256"],
            f"float observer perturbed {row['run_id']}",
        )
        if row["probe"] == "on":
            require(row["f32_fingerprint"] is not None, "missing f32 fingerprint")
            require(
                row["f32_sample_count"] == 4 * 3516 * 2344,
                f"wrong f32 population in {row['run_id']}",
            )
        else:
            require(row["f32_fingerprint"] is None, "probe-off emitted fingerprint")

    run = {row["run_id"]: row for row in rows}
    n16 = [
        run[f"pre-n16-off-w{worker}-probe-on"] for worker in WORKERS
    ]
    n16_f32 = {row["workers"]: row["f32_fingerprint"] for row in n16}
    pre33_w1 = run["pre-n33-on-w1-probe-on"]["f32_fingerprint"]
    pre33_w16 = run["pre-n33-on-w16-probe-on"]["f32_fingerprint"]
    post33_w1 = run["post-n33-on-w1-probe-on"]["f32_fingerprint"]
    post33_w16 = run["post-n33-on-w16-probe-on"]["f32_fingerprint"]
    probe_on = run["pre-n16-off-w4-probe-on"]
    probe_off = run["pre-n16-off-w4-probe-off"]

    require(len(set(n16_f32.values())) == 4, "N=16 must have four f32 hashes")
    require(n16_f32[1] == n16_f32[16], "N=16 f32 W1/W16 null moved")
    require(pre33_w1 != pre33_w16, "pre N=33 f32 control did not fire")
    require(post33_w1 == post33_w16, "post N=33 f32 invariance failed")
    require(
        probe_on["pixel_sha256"] == probe_off["pixel_sha256"]
        and probe_on["output_sha256"] == probe_off["output_sha256"],
        "probe on/off inertness failed",
    )
    return {
        "n16_unaligned_pre": {
            "distinct_f32_fingerprints": len(set(n16_f32.values())),
            "f32_fingerprint_by_worker": n16_f32,
        },
        "n33_aligned_pre": {"w1": pre33_w1, "w16": pre33_w16},
        "n33_aligned_post": {"w1": post33_w1, "w16": post33_w16},
        "sample_count": 4 * 3516 * 2344,
        "observer_inert": True,
        "all_outputs_match_unmodified_production": True,
    }


def verify(output_data: dict[str, Any], float_data: dict[str, Any]) -> dict[str, Any]:
    output_summary = validate_output(output_data)
    float_summary = validate_float(float_data, by_key(output_data["records"]))
    return {
        "schema": "M172-negative-control-verification-v1",
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "output_record_sha256": sha256_file(OUTPUT_RECORD),
        "float_record_sha256": sha256_file(FLOAT_RECORD),
        "output": output_summary,
        "prequantization": float_summary,
        "verdict": "PRE CONTROL FIRES; POST D9 IS WORKER-INVARIANT",
    }


def expect_rejected(
    output_data: dict[str, Any],
    float_data: dict[str, Any],
    mutation: str,
) -> None:
    try:
        verify(output_data, float_data)
    except RuntimeError:
        return
    raise AssertionError(f"mutation was not rejected: {mutation}")


def self_test(output_data: dict[str, Any], float_data: dict[str, Any]) -> None:
    broken = copy.deepcopy(output_data)
    for row in broken["records"]:
        if row["arm"] == "pre" and row["limit"] == 16:
            row["pixel_sha256"] = "0" * 64
            row["record_sha256"] = compact_sha256(
                {key: value for key, value in row.items() if key != "record_sha256"}
            )
    expect_rejected(broken, float_data, "blind pre control")

    broken = copy.deepcopy(output_data)
    row = next(
        row
        for row in broken["records"]
        if row["arm"] == "post" and row["workers"] == 16
    )
    row["pixel_sha256"] = "F" * 64
    row["record_sha256"] = compact_sha256(
        {key: value for key, value in row.items() if key != "record_sha256"}
    )
    expect_rejected(broken, float_data, "post output divergence")

    broken = copy.deepcopy(float_data)
    row = next(
        row
        for row in broken["records"]
        if row["run_id"] == "post-n33-on-w16-probe-on"
    )
    row["f32_fingerprint"] = "F" * 32
    row["record_sha256"] = compact_sha256(
        {key: value for key, value in row.items() if key != "record_sha256"}
    )
    expect_rejected(output_data, broken, "post f32 divergence")

    broken = copy.deepcopy(float_data)
    row = next(
        row
        for row in broken["records"]
        if row["run_id"] == "pre-n16-off-w4-probe-off"
    )
    row["output_sha256"] = "F" * 64
    row["record_sha256"] = compact_sha256(
        {key: value for key, value in row.items() if key != "record_sha256"}
    )
    expect_rejected(output_data, broken, "observer perturbation")

    broken = copy.deepcopy(output_data)
    broken["records"][0]["record_sha256"] = "0" * 64
    expect_rejected(broken, float_data, "record corruption")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    output_data = json.loads(OUTPUT_RECORD.read_text(encoding="utf-8"))
    float_data = json.loads(FLOAT_RECORD.read_text(encoding="utf-8"))
    result = verify(output_data, float_data)
    if args.self_test:
        self_test(output_data, float_data)
        result["red_controls"] = 5
    atomic_write(SUMMARY, result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
