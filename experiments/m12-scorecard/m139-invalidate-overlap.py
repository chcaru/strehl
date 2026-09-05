import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


MEASURED_COMMIT = "8009447e059febb8f9c59fda509f141835d6abdb"
CONTAMINANT_STARTED = datetime.fromisoformat("2026-09-04T16:02:18.199324-07:00")
INVALID_RERUN_STARTED = datetime.fromisoformat("2026-09-04T16:30:00-07:00")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def row_id(row: dict) -> tuple:
    return (
        row.get("position_key"),
        row.get("attempt"),
        row.get("started_utc"),
        row.get("completed_utc"),
    )


def is_initially_affected(row: dict) -> bool:
    if not str(row.get("kind", "")).startswith("modulo-"):
        return False
    return datetime.fromisoformat(row["completed_utc"]) > CONTAMINANT_STARTED


def invalidation(row: dict, was_accepted: bool) -> dict:
    started = datetime.fromisoformat(row["started_utc"])
    common = {
        "original_load_gate_valid": row.get("load_gate_valid"),
        "original_accepted_for_protocol": was_accepted,
    }
    if started >= INVALID_RERUN_STARTED:
        return {
            "reason": (
                "The rerun launcher inherited processor-affinity mask 0x1 from "
                "the temporarily capped agent runtime, so the target was limited "
                "to one logical CPU instead of the registered worker execution "
                "environment. The observation is excluded and rerun."
            ),
            "inherited_processor_affinity_mask": "0x1",
            "concurrent_workloads_were_also_observed_during_first_rerun": True,
            **common,
        }
    return {
        "reason": (
            "Overlapped an undisclosed concurrent N=299/W16 strehl memory "
            "run. The registered CPU gate does not bound memory-bandwidth or "
            "I/O contention, so the timing observation is excluded and rerun."
        ),
        "contaminant_started": CONTAMINANT_STARTED.isoformat(),
        "contaminant_root_pid": 44580,
        "contaminant_child_pid": 34780,
        "contaminant_command": (
            "experiments\\M172-worker-memory\\measure_memory.py "
            "--exe target\\release\\strehl.exe --stack bee-1-cpl "
            "--limit 299 --workers 16 --kind warmup"
        ),
        **common,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    original = args.records.read_bytes()
    first_run = not args.backup.exists()
    if first_run:
        args.backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.records, args.backup)

    rows = [
        json.loads(line)
        for line in original.decode("utf-8").splitlines()
        if line.strip()
    ]
    if any(row.get("measured_commit") != MEASURED_COMMIT for row in rows):
        raise RuntimeError("record measured commit does not match M139")
    backup_rows = [
        json.loads(line)
        for line in args.backup.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(row.get("measured_commit") != MEASURED_COMMIT for row in backup_rows):
        raise RuntimeError("backup measured commit does not match M139")

    prior_artifact = (
        json.loads(args.output.read_text(encoding="utf-8"))
        if args.output.exists()
        else None
    )
    initial = {
        row_id(row): row for row in backup_rows if is_initially_affected(row)
    }
    target_ids = set(initial)
    prior_affected = {}
    if prior_artifact is not None:
        prior_affected = {
            row_id(row): row
            for row in prior_artifact.get("records", {}).get("affected", [])
        }
        target_ids.update(prior_affected)
    if first_run:
        target_ids = {
            row_id(row) for row in rows if is_initially_affected(row)
        }

    current = {row_id(row): row for row in rows}
    missing = sorted(target_ids - set(current))
    if missing:
        raise RuntimeError(f"affected records missing from current stream: {missing}")

    affected = []
    for identity in sorted(
        target_ids,
        key=lambda value: (
            value[2] or "",
            value[3] or "",
            value[0] or "",
            value[1] or 0,
        ),
    ):
        row = current[identity]
        if identity in initial:
            was_accepted = (
                initial[identity].get("accepted_for_protocol") is True
            )
        elif identity in prior_affected:
            was_accepted = (
                prior_affected[identity].get(
                    "original_accepted_for_protocol"
                )
                is True
            )
        else:
            was_accepted = row.get("accepted_for_protocol") is True
        row["accepted_for_protocol"] = False
        row["external_invalidation"] = invalidation(row, was_accepted)
        affected.append(
            {
                "position_key": row.get("position_key"),
                "attempt": row.get("attempt"),
                "started_utc": row.get("started_utc"),
                "completed_utc": row.get("completed_utc"),
                "original_accepted_for_protocol": was_accepted,
            }
        )
    accepted_invalidated = sum(
        row["original_accepted_for_protocol"] for row in affected
    )

    rewritten = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    args.records.write_bytes(rewritten)

    previous_records = (
        prior_artifact.get("records", {}) if prior_artifact is not None else {}
    )
    generated_utc = (
        prior_artifact["generated_utc"]
        if prior_artifact is not None
        else datetime.now().astimezone().isoformat()
    )
    artifact = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "measured_commit": MEASURED_COMMIT,
        "generated_utc": generated_utc,
        "contaminant": {
            "lane": "M172-worker-memory",
            "root_pid": 44580,
            "child_pid": 34780,
            "started_utc": CONTAMINANT_STARTED.isoformat(),
            "observed_root_command": (
                "python.exe experiments\\M172-worker-memory\\measure_memory.py "
                "--exe target\\release\\strehl.exe --output-root "
                "experiments\\M172-worker-memory\\out\\candidate "
                "--stack bee-1-cpl --limit 299 --workers 16 --kind warmup"
            ),
            "observed_child_command": (
                "target\\release\\strehl.exe stack D:\\personal\\macro\\bee-1-cpl "
                "--limit 299 --out experiments\\M172-worker-memory\\out\\candidate"
                "\\runs\\warmup-n299-w16.tiff --linear-srgb --demosaic"
            ),
        },
        "decision": {
            "affected_rule": "N-mod-4 per-frame spread uses wall time.",
            "reason": (
                "The concurrent run consumed the same RAW input, memory subsystem, "
                "and storage path. Passing the CPU-only external-load gate does not "
                "establish an uncontended timing observation. The first rerun was "
                "separately invalid because its target inherited a one-CPU affinity "
                "mask from the agent-runtime throttle."
            ),
            "action": "Retain, mark non-protocol, and rerun every overlapping position.",
        },
        "records": {
            "backup_path": str(args.backup.resolve()),
            "backup_sha256": sha256(args.backup),
            "rewritten_path": str(args.records.resolve()),
            "rewritten_sha256_before_rerun": previous_records.get(
                "rewritten_sha256_before_rerun",
                sha256(args.records),
            ),
            "reconciled_records_sha256": sha256(args.records),
            "rows_annotated": len(affected),
            "accepted_rows_invalidated": accepted_invalidated,
            "originally_rejected_rows_annotated": (
                len(affected) - accepted_invalidated
            ),
            "affected": affected,
        },
        "reconciliation": {
            "method": (
                "Recover original acceptance from the immutable pre-invalidation "
                "backup; retain later affected record identities from the prior "
                "artifact."
            ),
            "initial_backup_rows_annotated": len(initial),
            "later_rows_annotated": len(target_ids - set(initial)),
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
