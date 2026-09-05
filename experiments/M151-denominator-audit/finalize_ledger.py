#!/usr/bin/env python3
"""Assemble the exact final ledger from the frozen review and later overlays."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import sys

import denominator_audit as audit


DEFAULT_SOURCES = (
    "audit-ledger.jsonl",
    "review-current-delta.jsonl",
    "review-final-delta.jsonl",
    "review-lock-a.jsonl",
    "review-lock-b.jsonl",
    "review-lock3-changing.jsonl",
    "review-lock4-report-m177.jsonl",
    "review-lock5-proposal.jsonl",
    "review-lock6-report.jsonl",
)


def assemble(
    manifest: dict,
    candidates: list[dict],
    sources: list[Path],
    file_owner: dict[str, str],
    candidate_owner: dict[str, str],
) -> tuple[list[dict], dict]:
    candidate_ids = {row["occurrence_id"] for row in candidates}
    file_rows = {row["path"]: row for row in manifest["files"]}
    dispositions: dict[str, tuple[Path, dict]] = {}
    attestations: dict[str, tuple[Path, dict]] = {}

    for source in sources:
        payload, rows = audit.read_jsonl(source)
        seen_dispositions: set[str] = set()
        seen_attestations: set[str] = set()
        for row in rows:
            if row.get("record_type") == "disposition":
                key = row.get("occurrence_id")
                if not isinstance(key, str) or key in seen_dispositions:
                    raise audit.AuditError(
                        f"{source}: duplicate or invalid disposition key {key!r}"
                    )
                seen_dispositions.add(key)
                if key in candidate_ids:
                    dispositions[key] = (source, row)
            elif row.get("record_type") == "file_attestation":
                key = row.get("file")
                if not isinstance(key, str) or key in seen_attestations:
                    raise audit.AuditError(
                        f"{source}: duplicate or invalid attestation key {key!r}"
                    )
                seen_attestations.add(key)
                if key in file_rows:
                    attestations[key] = (source, row)
            else:
                raise audit.AuditError(
                    f"{source}: unknown record_type {row.get('record_type')!r}"
                )
        if not payload:
            raise audit.AuditError(f"{source}: empty review source")

    missing_dispositions = candidate_ids - set(dispositions)
    missing_attestations = set(file_rows) - set(attestations)
    if missing_dispositions or missing_attestations:
        raise audit.AuditError(
            "review overlays are incomplete: "
            f"{len(missing_dispositions)} dispositions and "
            f"{len(missing_attestations)} attestations missing"
        )

    rows: list[dict] = []
    selected_disposition_sources: Counter[str] = Counter()
    selected_attestation_sources: Counter[str] = Counter()
    selection_basis: list[dict[str, str]] = []
    classifications: Counter[str] = Counter()

    for candidate in candidates:
        key = candidate["occurrence_id"]
        source, original = dispositions[key]
        if original.get("source_line") != candidate["line"]:
            raise audit.AuditError(
                f"{source}: stale source_line for {key}; "
                f"expected {candidate['line']}"
            )
        row = dict(original)
        original_reviewer = row.get("reviewer")
        row["reviewer"] = candidate_owner[key]
        rows.append(row)
        selected_disposition_sources[source.name] += 1
        classifications[row["classification"]] += 1
        selection_basis.append(
            {
                "record_type": "disposition",
                "key": key,
                "source": source.name,
                "source_reviewer": str(original_reviewer),
            }
        )

    for file_row in manifest["files"]:
        key = file_row["path"]
        source, original = attestations[key]
        if original.get("sha256") != file_row["sha256"]:
            raise audit.AuditError(f"{source}: stale attestation for {key}")
        row = dict(original)
        original_reviewer = row.get("reviewer")
        row["reviewer"] = file_owner[key]
        rows.append(row)
        selected_attestation_sources[source.name] += 1
        selection_basis.append(
            {
                "record_type": "file_attestation",
                "key": key,
                "source": source.name,
                "source_reviewer": str(original_reviewer),
            }
        )

    provenance = {
        "schema": "denominator-final-ledger-provenance-v1",
        "schema_version": 1,
        "manifest_sha256": manifest["manifest_sha256"],
        "candidates_sha256": manifest["candidates_sha256"],
        "source_precedence_low_to_high": [source.name for source in sources],
        "source_sha256": {
            source.name: hashlib.sha256(source.read_bytes()).hexdigest()
            for source in sources
        },
        "selection_sha256": audit.payload_sha256(selection_basis),
        "selected_dispositions_by_source": dict(
            sorted(selected_disposition_sources.items())
        ),
        "selected_attestations_by_source": dict(
            sorted(selected_attestation_sources.items())
        ),
        "classification_counts": dict(sorted(classifications.items())),
        "disposition_count": len(candidates),
        "attestation_count": len(manifest["files"]),
        "reviewer_field": (
            "Rebound to the exact final canonical shard owner; source reviewer "
            "and source ledger are committed by selection_sha256."
        ),
        "prohibited_path_accessed_during_finalization": False,
    }
    return rows, provenance


def main(argv: list[str] | None = None) -> int:
    lane = Path(__file__).parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default=str(lane / "out-final"))
    parser.add_argument("--out-ledger", default=str(lane / "final-ledger.jsonl"))
    parser.add_argument(
        "--out-provenance",
        default=str(lane / "final-ledger-provenance.json"),
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=[str(lane / name) for name in DEFAULT_SOURCES],
    )
    args = parser.parse_args(argv)

    try:
        snapshot = audit.checked_path(args.snapshot)
        output = audit.checked_path(args.out_ledger)
        provenance_output = audit.checked_path(args.out_provenance)
        sources = [audit.checked_path(path) for path in args.sources]
        manifest, candidates, errors = audit.validate_manifest_and_candidates(
            snapshot / "corpus-manifest.json",
            snapshot / "candidates.jsonl",
        )
        if errors:
            raise audit.AuditError("; ".join(errors))
        file_owner, candidate_owner, shard_errors = audit.load_and_validate_shards(
            [snapshot / "shards"], manifest, candidates
        )
        if shard_errors:
            raise audit.AuditError("; ".join(shard_errors))
        rows, provenance = assemble(
            manifest,
            candidates,
            sources,
            file_owner,
            candidate_owner,
        )
        audit.atomic_write(output, audit.jsonl_bytes(rows))
        ledger_errors = audit.validate_ledgers(
            manifest,
            candidates,
            [output],
            file_owner=file_owner,
            candidate_owner=candidate_owner,
        )
        if ledger_errors:
            raise audit.AuditError("; ".join(ledger_errors))
        provenance["final_ledger_sha256"] = hashlib.sha256(
            output.read_bytes()
        ).hexdigest()
        audit.atomic_json(provenance_output, provenance)
        print(
            "GREEN: "
            f"{len(candidates)} dispositions, "
            f"{manifest['file_count']} attestations, "
            f"ledger_sha256={provenance['final_ledger_sha256']}"
        )
        return 0
    except audit.AuditError as error:
        print(f"RED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
