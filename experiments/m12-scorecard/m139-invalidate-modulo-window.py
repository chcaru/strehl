import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


MEASURED_COMMIT = "8009447e059febb8f9c59fda509f141835d6abdb"
NAMED_CONTENDERS = {
    "cargo.exe",
    "exiftool.exe",
    "link.exe",
    "rustc.exe",
    "strehl.exe",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def preload_contenders(row: dict) -> list[dict]:
    attempts = row.get("preload_gate", {}).get("attempts", [])
    if not attempts:
        return []
    return [
        {
            "name": process.get("name"),
            "pid": process.get("pid"),
            "capacity_fraction": process.get("capacity_fraction"),
        }
        for process in attempts[-1].get("top_process_cpu", [])
        if str(process.get("name", "")).lower() in NAMED_CONTENDERS
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
            or row.get("kind") not in {"modulo-warmup", "modulo-scored"}
        ):
            continue
        contenders = preload_contenders(row)
        row["accepted_for_protocol"] = False
        row["external_invalidation"] = {
            "reason": (
                "Excluded for a conservative single-window rerun after named "
                "compiler or Strehl contenders were discovered during the timing "
                "arm. The registered CPU gate does not bound memory, storage, "
                "filesystem-cache, thermal, or turbo-state carryover."
            ),
            "decision": (
                "Rerun every modulo warm-up and scored position so all timing "
                "minima come from one enforced isolation window."
            ),
            "original_load_gate_valid": row.get("load_gate_valid"),
            "original_accepted_for_protocol": True,
            "named_contenders_in_final_preload_sample": contenders,
        }
        invalidated.append(
            {
                "position_key": row.get("position_key"),
                "attempt": row.get("attempt"),
                "kind": row.get("kind"),
                "started_utc": row.get("started_utc"),
                "completed_utc": row.get("completed_utc"),
                "named_contenders_in_final_preload_sample": contenders,
            }
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
        "decision": {
            "affected_rule": "N-mod-4 per-frame spread uses wall time.",
            "registered_gates_unchanged": {
                "preload_whole_host_busy_fraction_max": 0.15,
                "during_run_external_busy_fraction_max": 0.10,
            },
            "reason": (
                "Post-run inspection found external Strehl processes before the "
                "first scored sweep and compiler/linker processes during the tail. "
                "The CPU gates accepted several rows because the named contenders "
                "were below the CPU thresholds, but those gates cannot bound their "
                "memory, I/O, cache-state, or thermal effects."
            ),
            "action": (
                "Retain every prior row, mark the accepted modulo window "
                "non-protocol, and rerun all four warm-ups and 24 scored positions "
                "under an enforced named-contender hold."
            ),
        },
        "records": {
            "backup_path": str(args.backup.resolve()),
            "backup_sha256": sha256(args.backup),
            "rewritten_path": str(args.records.resolve()),
            "rewritten_sha256_before_rerun": sha256(args.records),
            "accepted_rows_invalidated": len(invalidated),
            "rows_with_named_contenders_in_final_preload_sample": sum(
                bool(row["named_contenders_in_final_preload_sample"])
                for row in invalidated
            ),
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
