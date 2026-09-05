import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


MEASURED_COMMIT = "8009447e059febb8f9c59fda509f141835d6abdb"
CONTAMINATION_START = datetime.fromisoformat(
    "2026-09-05T01:30:30.9875502+00:00"
)
CONTAMINATION_END = datetime.fromisoformat(
    "2026-09-05T01:36:59.801403+00:00"
)
EXPECTED_INVALIDATED = 12


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def overlaps(row: dict) -> bool:
    started = datetime.fromisoformat(row["started_utc"])
    completed = datetime.fromisoformat(row["completed_utc"])
    return started < CONTAMINATION_END and completed > CONTAMINATION_START


def preload_contenders(row: dict) -> list[dict]:
    attempts = row.get("preload_gate", {}).get("attempts", [])
    if not attempts:
        return []
    names = {"cargo.exe", "rustc.exe", "link.exe", "strehl.exe", "exiftool.exe"}
    return [
        {
            "name": process.get("name"),
            "pid": process.get("pid"),
            "capacity_fraction": process.get("capacity_fraction"),
        }
        for process in attempts[-1].get("top_process_cpu", [])
        if str(process.get("name", "")).lower() in names
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.backup.exists():
        raise RuntimeError(f"backup already exists: {args.backup}")

    original = args.records.read_bytes()
    rows = [
        json.loads(line)
        for line in original.decode("utf-8").splitlines()
        if line.strip()
    ]
    if any(row.get("measured_commit") != MEASURED_COMMIT for row in rows):
        raise RuntimeError("record measured commit does not match M139")

    args.backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.records, args.backup)

    invalidated = []
    for row in rows:
        if (
            row.get("valid") is not True
            or row.get("accepted_for_protocol") is not True
            or row.get("kind") != "modulo-scored"
            or not overlaps(row)
        ):
            continue
        contenders = preload_contenders(row)
        row["accepted_for_protocol"] = False
        row["external_invalidation"] = {
            "reason": (
                "The scored timing interval overlaps an external Cargo/Rust "
                "workload admitted below the CPU threshold. The registered CPU "
                "gate does not bound its memory, I/O, cache, thermal, or turbo "
                "effects."
            ),
            "contamination_interval_utc": {
                "start": CONTAMINATION_START.isoformat(),
                "end_conservative": CONTAMINATION_END.isoformat(),
            },
            "original_load_gate_valid": row.get("load_gate_valid"),
            "original_accepted_for_protocol": True,
            "named_contenders_in_final_preload_sample": contenders,
        }
        invalidated.append(
            {
                "position_key": row.get("position_key"),
                "attempt": row.get("attempt"),
                "started_utc": row.get("started_utc"),
                "completed_utc": row.get("completed_utc"),
                "named_contenders_in_final_preload_sample": contenders,
            }
        )

    if len(invalidated) != EXPECTED_INVALIDATED:
        raise RuntimeError(
            f"expected {EXPECTED_INVALIDATED} affected rows, found {len(invalidated)}"
        )

    rewritten = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    args.records.write_bytes(rewritten)

    artifact = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "measured_commit": MEASURED_COMMIT,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "contamination": {
            "interval_utc": {
                "start": CONTAMINATION_START.isoformat(),
                "end_conservative": CONTAMINATION_END.isoformat(),
            },
            "observed_cargo": {
                "root_pid": 7676,
                "child_pid": 38192,
                "command": (
                    "cargo test --release -p strehl-cli --test byte-freeze "
                    "the_frozen_renders_still_produce_their_recorded_bytes "
                    "-- --exact"
                ),
                "started_utc": CONTAMINATION_START.isoformat(),
            },
            "subsequent_evidence": (
                "Later final-preload samples retained rustc.exe and link.exe "
                "processes through the N98/R5 position."
            ),
        },
        "decision": {
            "affected_rule": "N-mod-4 per-frame spread uses wall time.",
            "registered_gates_unchanged": {
                "preload_whole_host_busy_fraction_max": 0.15,
                "during_run_external_busy_fraction_max": 0.10,
            },
            "action": (
                "Retain and mark non-protocol every scored row overlapping the "
                "conservative interval, then rerun only those 12 positions."
            ),
        },
        "records": {
            "backup_path": str(args.backup.resolve()),
            "backup_sha256": sha256(args.backup),
            "rewritten_path": str(args.records.resolve()),
            "rewritten_sha256_before_rerun": sha256(args.records),
            "accepted_rows_invalidated": len(invalidated),
            "affected": invalidated,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(artifact["records"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
