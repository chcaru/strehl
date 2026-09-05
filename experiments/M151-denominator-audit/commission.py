#!/usr/bin/env python3
"""Commission the denominator audit with an unreviewed-denominator plant.

The plant is made only in a temporary synthetic corpus.  The real corpus is
hashed before and after commissioning and is never opened for writing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

import denominator_audit as audit


ANCHOR = "Baseline throughput remained 7 of 8 admitted cases."
PLANTED_LINE = "Planted defect: 9 out of 10 cases passed without provenance."
REPORT_LABEL_ANCHOR = (
    "**VERIFIED BY RUNNING:** The synthetic baseline ledger is complete."
)
UNLABELED_REPORT_CLAIM = "The synthetic baseline ledger is complete."


class CommissioningError(AssertionError):
    """A failed commissioning invariant."""


def replace_unique_anchor(text: str, anchor: str, replacement: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise CommissioningError(
            f"anchor must occur exactly once before planting; found {count}: {anchor!r}"
        )
    return text.replace(anchor, replacement, 1)


def corpus_hashes(repo_root: Path) -> dict[str, str]:
    audit.reject_forbidden_path(repo_root)
    return {
        relative: hashlib.sha256(path.read_bytes()).hexdigest()
        for relative, path in audit.discover_corpus(repo_root)
    }


def write_fixture(root: Path) -> Path:
    research = root / "docs" / "research"
    proposals = root / "docs" / "proposals"
    research.mkdir(parents=True)
    proposals.mkdir(parents=True)
    target = research / "baseline.md"
    target.write_text(
        "# Baseline\n\n"
        f"{ANCHOR}\n\n"
        "No other proportion is asserted here.\n",
        encoding="utf-8",
        newline="\n",
    )
    (proposals / "proposal.md").write_text(
        "# Proposal\n\n> Coverage passed at 100% in this fixture.\n",
        encoding="utf-8",
        newline="\n",
    )
    return target


def owner_maps(
    manifest: dict[str, Any], candidates: list[dict[str, Any]]
) -> tuple[dict[str, str], dict[str, str]]:
    file_owner: dict[str, str] = {}
    candidate_owner: dict[str, str] = {}
    for shard in audit.balanced_shards(manifest, candidates):
        reviewer = shard["reviewer"]
        file_owner.update({path: reviewer for path in shard["files"]})
        candidate_owner.update(
            {occurrence: reviewer for occurrence in shard["candidate_ids"]}
        )
    return file_owner, candidate_owner


def baseline_records(
    manifest: dict[str, Any],
    candidates: list[dict[str, Any]],
    file_owner: dict[str, str],
    candidate_owner: dict[str, str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for candidate in candidates:
        records.append(
            {
                "record_type": "disposition",
                "occurrence_id": candidate["occurrence_id"],
                "reviewer": candidate_owner[candidate["occurrence_id"]],
                "classification": "fixture",
                "denominator_chain": [
                    "synthetic commissioning corpus",
                    f"reported expression {candidate['match_text']!r}",
                ],
                "evidence_label": "VERIFIED",
                "consequence": "Commissioning-only baseline; no product consequence.",
                "source_line": candidate["line"],
                "resolution_status": "not_applicable",
            }
        )
    for file_row in manifest["files"]:
        records.append(
            {
                "record_type": "file_attestation",
                "file": file_row["path"],
                "reviewer": file_owner[file_row["path"]],
                "sha256": file_row["sha256"],
                "complete": True,
            }
        )
    return records


def run_commission(repo_root: Path) -> dict[str, Any]:
    audit.reject_forbidden_path(repo_root)
    before = corpus_hashes(repo_root)
    with tempfile.TemporaryDirectory(prefix="M151-denominator-audit-") as temporary:
        fixture_root = Path(temporary) / "fixture"
        target = write_fixture(fixture_root)
        manifest, candidates = audit.scan_corpus(fixture_root)
        file_owner, candidate_owner = owner_maps(manifest, candidates)
        ledger_path = fixture_root / "baseline-ledger.jsonl"
        audit.atomic_write(
            ledger_path,
            audit.jsonl_bytes(
                baseline_records(
                    manifest, candidates, file_owner, candidate_owner
                )
            ),
        )
        baseline_errors = audit.validate_ledgers(
            manifest,
            candidates,
            [ledger_path],
            file_owner=file_owner,
            candidate_owner=candidate_owner,
        )
        report_path = fixture_root / "final-report.md"
        report_text = (
            "NO VERDICT FLIPS: 0 unstated denominators found, "
            "none load-bearing\n\n"
            f"{REPORT_LABEL_ANCHOR}\n"
        )
        report_path.write_text(
            report_text,
            encoding="utf-8",
            newline="\n",
        )
        baseline_errors.extend(audit.validate_final_report(report_path, manifest))
        if baseline_errors:
            raise CommissioningError(
                "baseline was not green:\n" + "\n".join(baseline_errors)
            )

        planted_report = replace_unique_anchor(
            report_text,
            REPORT_LABEL_ANCHOR,
            UNLABELED_REPORT_CLAIM,
        )
        report_path.write_text(
            planted_report,
            encoding="utf-8",
            newline="\n",
        )
        report_plant_errors = audit.validate_final_report(report_path, manifest)
        unlabelled_report_errors = [
            error
            for error in report_plant_errors
            if "prose paragraph must begin exactly" in error
        ]
        if not report_plant_errors or not unlabelled_report_errors:
            raise CommissioningError(
                "planted unlabeled report claim did not make the checker red"
            )

        report_controls: dict[str, bool] = {}
        for name, text in (
            (
                "missing_anchor",
                report_text.replace(REPORT_LABEL_ANCHOR, "", 1),
            ),
            (
                "duplicate_anchor",
                report_text + "\n" + REPORT_LABEL_ANCHOR + "\n",
            ),
        ):
            try:
                replace_unique_anchor(
                    text,
                    REPORT_LABEL_ANCHOR,
                    UNLABELED_REPORT_CLAIM,
                )
            except CommissioningError:
                report_controls[name] = True
            else:
                report_controls[name] = False
        if not all(report_controls.values()):
            raise CommissioningError(
                "report anchor controls did not fail closed: "
                f"{report_controls}"
            )

        original = target.read_text(encoding="utf-8")
        planted = replace_unique_anchor(
            original, ANCHOR, f"{ANCHOR}\n\n{PLANTED_LINE}"
        )
        target.write_text(planted, encoding="utf-8", newline="\n")
        planted_manifest, planted_candidates = audit.scan_corpus(fixture_root)
        planted_file_owner, planted_candidate_owner = owner_maps(
            planted_manifest, planted_candidates
        )
        planted_errors = audit.validate_ledgers(
            planted_manifest,
            planted_candidates,
            [ledger_path],
            file_owner=planted_file_owner,
            candidate_owner=planted_candidate_owner,
        )
        missing_dispositions = [
            error
            for error in planted_errors
            if "expected exactly one disposition, found 0" in error
        ]
        if not planted_errors or not missing_dispositions:
            raise CommissioningError(
                "planted unreviewed denominator did not make the checker red"
            )

        controls: dict[str, bool] = {}
        for name, text in (
            ("missing_anchor", original.replace(ANCHOR, "", 1)),
            ("duplicate_anchor", original + "\n" + ANCHOR + "\n"),
        ):
            try:
                replace_unique_anchor(text, ANCHOR, PLANTED_LINE)
            except CommissioningError:
                controls[name] = True
            else:
                controls[name] = False
        if not all(controls.values()):
            raise CommissioningError(f"anchor controls did not fail closed: {controls}")

    after = corpus_hashes(repo_root)
    if before != after:
        raise CommissioningError("real corpus changed during commissioning")
    return {
        "baseline": "GREEN",
        "baseline_candidates": len(candidates),
        "baseline_files": manifest["file_count"],
        "planted_unlabeled_report_claim": "RED",
        "unlabeled_report_errors": len(unlabelled_report_errors),
        "report_missing_anchor_control": "RED",
        "report_duplicate_anchor_control": "RED",
        "planted_unreviewed_denominator": "RED",
        "planted_candidates": len(planted_candidates),
        "missing_dispositions": len(missing_dispositions),
        "missing_anchor_control": "RED",
        "duplicate_anchor_control": "RED",
        "real_corpus_immutable": "GREEN",
        "real_corpus_files": len(before),
    }


def main() -> int:
    lane = Path(__file__).parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(lane.parent.parent))
    args = parser.parse_args()
    try:
        # Reject the raw argument before constructing or probing the path.
        audit.reject_forbidden_path(args.repo_root)
        result = run_commission(Path(args.repo_root))
    except (audit.AuditError, CommissioningError) as error:
        print(f"COMMISSIONING: RED: {error}")
        return 1
    print(json.dumps(result, sort_keys=True))
    print("COMMISSIONING: GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
