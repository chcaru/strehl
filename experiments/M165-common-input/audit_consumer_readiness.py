#!/usr/bin/env python3
"""Record the current machine's real common-input consumer blockers."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "exists": False, "bytes": None, "sha256": None}
    return {
        "path": str(path.resolve()),
        "exists": True,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def zerene_license_evidence(
    log_path: Path, audit_time: datetime
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(log_path),
        "exists": log_path.is_file(),
        "sha256": sha256(log_path) if log_path.is_file() else None,
        "expiry_line": None,
        "category_line": None,
        "expiry_local": None,
        "expired_at_audit": None,
    }
    if not log_path.is_file():
        return result
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    expiry_re = re.compile(
        r"license .* expires on (?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
        r"([A-Z][a-z]{2} \d{2} \d{2}:\d{2}:\d{2}) [A-Z]{2,4} (\d{4})"
    )
    for line_number, line in enumerate(lines, start=1):
        match = expiry_re.search(line)
        if match:
            expiry = datetime.strptime(
                f"{match.group(1)} {match.group(2)}", "%b %d %H:%M:%S %Y"
            )
            result["expiry_line"] = {
                "line_number": line_number,
                "text": (
                    f"license identifier redacted; expires on "
                    f"{match.group(1)} {match.group(2)}"
                ),
            }
            result["expiry_local"] = expiry.isoformat()
            result["expired_at_audit"] = expiry < audit_time.replace(tzinfo=None)
        if "License category =" in line:
            result["category_line"] = {"line_number": line_number, "text": line}
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument(
        "--audit-utc",
        help="Frozen ISO-8601 audit time; defaults to the current UTC time",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out)
    try:
        audit_time = (
            datetime.fromisoformat(args.audit_utc.replace("Z", "+00:00"))
            if args.audit_utc
            else datetime.now(timezone.utc)
        )
    except ValueError as exc:
        print(f"invalid --audit-utc: {exc}", file=sys.stderr)
        return 2
    if audit_time.utcoffset() is None:
        print("--audit-utc must include an offset", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[2]
    m165 = Path(__file__).resolve().parent

    zerene_root = Path(r"C:\Program Files\ZereneStacker")
    zerene_artifacts = [
        artifact(zerene_root / "zerenstk.exe"),
        artifact(zerene_root / "ZereneStacker.jar"),
        artifact(zerene_root / "jre" / "bin" / "java.exe"),
        artifact(zerene_root / "zerenstk.ini"),
        artifact(
            Path.home()
            / "AppData"
            / "Roaming"
            / "ZereneStacker"
            / "zerenstk.launchcmd"
        ),
    ]
    zerene_log = (
        Path.home()
        / "AppData"
        / "Roaming"
        / "ZereneStacker"
        / "LastNormalLog.txt"
    )
    license_evidence = zerene_license_evidence(zerene_log, audit_time)
    zerene_installed = all(item["exists"] for item in zerene_artifacts[:3])
    zerene_expired = license_evidence["expired_at_audit"] is True

    helicon_candidates = [
        Path(r"C:\Program Files\Helicon Software\Helicon Focus 8\HeliconFocus.exe"),
        Path(r"C:\Program Files\Helicon Focus\HeliconFocus.exe"),
        Path(r"C:\Program Files\HeliconFocus\HeliconFocus.exe"),
        Path(
            r"C:\Program Files (x86)\Helicon Software\Helicon Focus 8\HeliconFocus.exe"
        ),
    ]
    helicon_evidence = [artifact(path) for path in helicon_candidates]
    helicon_installed = any(item["exists"] for item in helicon_evidence)

    verifier = root / "target" / "debug" / "strehl-common-input.exe"
    verifier_source = (
        root / "crates" / "strehl-cli" / "src" / "bin" / "strehl-common-input.rs"
    )
    identity_report = m165 / "out" / "commission" / "identity-baseline.json"
    pattern_audit_path = m165 / "out" / "pattern-map-audit.json"
    pattern_audit = json.loads(pattern_audit_path.read_text(encoding="utf-8"))
    fork_blocker_path = m165 / "consumer-registry-fork-blocked.json"
    fork_blocker = json.loads(fork_blocker_path.read_text(encoding="utf-8"))

    required_consumers = [
        {
            "consumer_id": "strehl",
            "outcome": "READY_FOR_SYNTHETIC_IDENTITY_ONLY",
            "required": True,
            "evidence_class": "VERIFIED_BY_RUNNING",
            "evidence_pass": verifier.is_file() and identity_report.is_file(),
            "artifacts": {
                "verifier": artifact(verifier),
                "source": artifact(verifier_source),
                "identity_report": artifact(identity_report),
            },
            "blocker": (
                "No eligible real pattern map or rendered real common-input campaign "
                "exists, so campaign identity cannot yet be exercised."
            ),
        },
        {
            "consumer_id": "zerene-pmax",
            "outcome": "BLOCKED_LICENSE_EXPIRED",
            "required": True,
            "evidence_class": "VERIFIED_BY_RUNNING",
            "evidence_pass": zerene_installed and zerene_expired,
            "installed_version": "1.04T2026-05-04-0750",
            "artifacts": zerene_artifacts,
            "license_evidence": license_evidence,
            "blocker": (
                "The installed trial expired 2026-06-06. Obtain a licensed current "
                "shipping Zerene build and freeze its complete runtime bundle, PMax "
                "settings, invocation, and consumer receipt adapter."
            ),
        },
        {
            "consumer_id": "zerene-dmap",
            "outcome": "BLOCKED_LICENSE_EXPIRED",
            "required": True,
            "evidence_class": "VERIFIED_BY_RUNNING",
            "evidence_pass": zerene_installed and zerene_expired,
            "installed_version": "1.04T2026-05-04-0750",
            "artifacts": zerene_artifacts,
            "license_evidence": license_evidence,
            "blocker": (
                "The installed trial expired 2026-06-06. Obtain a licensed current "
                "shipping Zerene build and freeze its complete runtime bundle, DMap "
                "settings, invocation, and consumer receipt adapter."
            ),
        },
        {
            "consumer_id": "focus-stack-fork",
            "outcome": "BLOCKED_NO_REPRODUCIBLE_BINARY",
            "required": True,
            "evidence_class": "INFERRED_BY_READING",
            "evidence_pass": fork_blocker.get("status") == "BLOCKED",
            "source_revision": "4bc7f95e448cf20ee2bdd758403ec43e2612a1c6",
            "blocker_evidence": artifact(fork_blocker_path),
            "blocker": (
                "Build the pinned retained source, freeze source tree, toolchain, "
                "dependency lock, compiler flags, settings, invocation, and final "
                "executable SHA-256, then run it on the common TIFFs."
            ),
        },
    ]
    optional_consumers = [
        {
            "consumer_id": "helicon-focus",
            "outcome": "OPTIONAL_ABSENT",
            "required": False,
            "evidence_class": "VERIFIED_BY_RUNNING_TARGETED_PATH_PROBE",
            "evidence_pass": not helicon_installed,
            "candidate_paths": helicon_evidence,
            "blocker": (
                "No local installation was found. The live scorecard makes Helicon "
                "optional when unobtainable, so this absence is counted but not fatal."
            ),
        }
    ]
    required_counts = {
        "total_examined": len(required_consumers),
        "READY_FOR_SYNTHETIC_IDENTITY_ONLY": sum(
            item["outcome"] == "READY_FOR_SYNTHETIC_IDENTITY_ONLY"
            for item in required_consumers
        ),
        "BLOCKED_LICENSE_EXPIRED": sum(
            item["outcome"] == "BLOCKED_LICENSE_EXPIRED"
            for item in required_consumers
        ),
        "BLOCKED_NO_REPRODUCIBLE_BINARY": sum(
            item["outcome"] == "BLOCKED_NO_REPRODUCIBLE_BINARY"
            for item in required_consumers
        ),
    }
    required_counts["counted_sum"] = sum(
        value
        for key, value in required_counts.items()
        if key not in {"total_examined", "counted_sum"}
    )
    required_counts["partition_balanced"] = (
        required_counts["counted_sum"] == required_counts["total_examined"]
    )

    scorecard = root / "docs" / "proposals" / "2026-09-sota-scorecard.md"
    report = {
        "schema": "m165-common-input-consumer-readiness-v1",
        "status": "BLOCKED",
        "audit_utc": audit_time.astimezone(timezone.utc).isoformat(),
        "measurement_class": "deterministic correctness; no wall-clock result",
        "governing_scorecard": artifact(scorecard),
        "pattern_map": {
            "audit": artifact(pattern_audit_path),
            "status": pattern_audit.get("status"),
            "blocker": pattern_audit.get("conclusion"),
            "evidence_class": "INFERRED_BY_READING_PRIOR_AUDIT",
        },
        "required_consumer_partition": required_counts,
        "required_consumers": required_consumers,
        "optional_consumers": optional_consumers,
        "owner_asks": [
            {
                "ask": (
                    "After written permission to publish the black-box comparison, "
                    "purchase Zerene Prosumer ($189 plus tax) if the work remains "
                    "eligible personal/unfunded use; otherwise Professional ($289 "
                    "plus tax)."
                ),
                "basis": "inferred by reading docs/research/M132-blocker-d-routes.md",
            },
            {
                "ask": (
                    "Assign a rebuild of focus-stack commit "
                    "4bc7f95e448cf20ee2bdd758403ec43e2612a1c6 and freeze the "
                    "resulting runtime bundle before any comparative render."
                ),
                "basis": "inferred by reading docs/research/M162-noise-regression.md",
            },
            {
                "ask": (
                    "Acquire M164 Stages 1 and 2 converter-on calibration/reference "
                    "frames, then the corresponding TC0 blocks, without violating the "
                    "frozen M165 class and held-out-V contract."
                ),
                "basis": "inferred by reading docs/research/M164-m1-staged-capture.md",
            },
        ],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
