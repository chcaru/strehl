from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import commission
import denominator_audit as audit
import finalize_ledger as finalizer


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class DenominatorAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="M151-denominator-test-"
        )
        self.root = Path(self.temporary.name) / "repo"
        write_text(
            self.root / "docs" / "research" / "alpha.md",
            "# Alpha\n"
            "Plain 25% and 3/4 and 7 of 9 and 8 out of 10.\n"
            "| coverage | 4/5 pass |\n"
            "> Success reached 90 percent.\n"
            "```\n"
            "eligible = 2 of 3; admissions are tracked\n"
            "```\n",
        )
        write_text(
            self.root / "docs" / "proposals" / "beta.md",
            "# Beta\nNo proportion here.\n",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def scan_outputs(
        self,
    ) -> tuple[Path, dict, list[dict], dict[str, str], dict[str, str]]:
        out = self.root / "audit-out"
        audit.scan_to_directory(self.root, out)
        manifest, candidates, errors = audit.validate_manifest_and_candidates(
            out / "corpus-manifest.json", out / "candidates.jsonl"
        )
        self.assertEqual(errors, [])
        file_owner, candidate_owner, shard_errors = audit.load_and_validate_shards(
            [out / "shards"], manifest, candidates
        )
        self.assertEqual(shard_errors, [])
        return out, manifest, candidates, file_owner, candidate_owner

    def valid_records(
        self,
        manifest: dict,
        candidates: list[dict],
        file_owner: dict[str, str],
        candidate_owner: dict[str, str],
    ) -> list[dict]:
        rows = [
            {
                "record_type": "disposition",
                "occurrence_id": candidate["occurrence_id"],
                "reviewer": candidate_owner[candidate["occurrence_id"]],
                "classification": "population",
                "denominator_chain": ["all fixture rows", "reported subset"],
                "evidence_label": "VERIFIED",
                "consequence": "No consequence in a synthetic unit fixture.",
                "source_line": candidate["line"],
                "resolution_status": "verified",
            }
            for candidate in candidates
        ]
        rows.extend(
            {
                "record_type": "file_attestation",
                "file": file_row["path"],
                "reviewer": file_owner[file_row["path"]],
                "sha256": file_row["sha256"],
                "complete": True,
            }
            for file_row in manifest["files"]
        )
        return rows

    def write_ledger(self, path: Path, rows: list[dict]) -> None:
        audit.atomic_write(path, audit.jsonl_bytes(rows))

    def test_detects_all_required_forms_in_all_markdown_contexts(self) -> None:
        manifest, candidates = audit.scan_corpus(self.root)
        kinds = {row["kind"] for row in candidates}
        contexts = {row["markdown_context"] for row in candidates}
        matches = {row["match_text"].lower() for row in candidates}
        self.assertEqual(manifest["file_count"], 2)
        self.assertTrue(
            {
                "percentage",
                "numeric_fraction",
                "number_of_number",
                "rate_or_coverage_claim",
            }.issubset(kinds)
        )
        self.assertTrue({"text", "table", "quote", "fence"}.issubset(contexts))
        self.assertTrue(
            {"25%", "3/4", "7 of 9", "8 out of 10", "90 percent"}.issubset(
                matches
            )
        )
        self.assertIn("admissions", matches)

    def test_inventory_is_direct_child_only_and_records_exact_bytes(self) -> None:
        write_text(
            self.root / "docs" / "research" / "nested" / "hidden.md",
            "100% hidden\n",
        )
        write_text(
            self.root / "docs" / "research" / "ignored.MD",
            "100% wrong suffix\n",
        )
        manifest, candidates = audit.scan_corpus(self.root)
        paths = {row["path"] for row in manifest["files"]}
        self.assertNotIn("docs/research/nested/hidden.md", paths)
        self.assertNotIn("docs/research/ignored.MD", paths)
        alpha = next(
            row for row in manifest["files"] if row["path"].endswith("alpha.md")
        )
        payload = (self.root / "docs" / "research" / "alpha.md").read_bytes()
        self.assertEqual(alpha["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(alpha["bytes"], len(payload))
        self.assertEqual(alpha["lines"], 7)
        self.assertEqual(alpha["git_state"], "not_git")
        self.assertEqual(
            alpha["candidate_count"],
            sum(row["path"].endswith("alpha.md") for row in candidates),
        )

    def test_occurrence_ids_survive_unrelated_prior_line_insertions(self) -> None:
        path = self.root / "docs" / "research" / "alpha.md"
        before = audit.scan_corpus(self.root)[1]
        original = path.read_text(encoding="utf-8")
        path.write_text(
            "An unrelated line without a trigger.\n" + original,
            encoding="utf-8",
            newline="\n",
        )
        after = audit.scan_corpus(self.root)[1]
        self.assertEqual(
            {row["occurrence_id"] for row in before},
            {row["occurrence_id"] for row in after},
        )

    def test_scan_and_eight_whole_file_shards_are_deterministic(self) -> None:
        out_a = self.root / "out-a"
        out_b = self.root / "out-b"
        first = audit.scan_to_directory(self.root, out_a)
        second = audit.scan_to_directory(self.root, out_b)
        self.assertEqual(first, second)
        self.assertEqual(
            (out_a / "corpus-manifest.json").read_bytes(),
            (out_b / "corpus-manifest.json").read_bytes(),
        )
        self.assertEqual(
            (out_a / "candidates.jsonl").read_bytes(),
            (out_b / "candidates.jsonl").read_bytes(),
        )
        shards_a = sorted((out_a / "shards").glob("*.json"))
        shards_b = sorted((out_b / "shards").glob("*.json"))
        self.assertEqual(len(shards_a), 8)
        self.assertEqual(
            [path.read_bytes() for path in shards_a],
            [path.read_bytes() for path in shards_b],
        )
        assigned_files: list[str] = []
        assigned_candidates: list[str] = []
        for path in shards_a:
            shard = json.loads(path.read_text(encoding="ascii"))
            assigned_files.extend(shard["files"])
            assigned_candidates.extend(shard["candidate_ids"])
        self.assertEqual(len(assigned_files), len(set(assigned_files)))
        self.assertEqual(len(assigned_candidates), len(set(assigned_candidates)))
        self.assertEqual(set(assigned_files), {row["path"] for row in first["files"]})

    def test_forbidden_path_is_rejected_before_filesystem_access(self) -> None:
        aliases = (
            r"d:/PERSONAL/macro/requests/x/../7-aperture-pairs/child",
            r"\\?\D:\personal\macro\requests\7-aperture-pairs\child",
            r"\\.\D:\personal\macro\requests\7-aperture-pairs\child",
            "D:\\personal\\macro\\requests\\7-aperture-pairs.\\child",
            "D:\\personal\\macro\\requests\\7-aperture-pairs \\child",
        )
        for forbidden in aliases:
            with self.subTest(forbidden=forbidden), mock.patch.object(
                Path, "is_dir", side_effect=AssertionError("filesystem touched")
            ) as is_dir:
                with self.assertRaisesRegex(audit.AuditError, "forbidden path"):
                    audit.discover_corpus(forbidden)
            is_dir.assert_not_called()
        forbidden = aliases[0]
        stderr = io.StringIO()
        with mock.patch.object(
            Path, "is_dir", side_effect=AssertionError("filesystem touched")
        ) as is_dir, contextlib.redirect_stderr(stderr):
            result = audit.main(["scan", "--repo-root", forbidden])
        self.assertEqual(result, 2)
        self.assertIn("forbidden path", stderr.getvalue())
        is_dir.assert_not_called()

    def test_manifest_candidate_and_shard_tampering_fail_closed(self) -> None:
        out, manifest, candidates, _, _ = self.scan_outputs()
        candidate_path = out / "candidates.jsonl"
        tampered = [dict(row) for row in candidates]
        tampered[0]["match_text"] = "tampered"
        candidate_path.write_bytes(audit.jsonl_bytes(tampered))
        _, _, errors = audit.validate_manifest_and_candidates(
            out / "corpus-manifest.json", candidate_path
        )
        self.assertTrue(any("candidates_sha256 mismatch" in error for error in errors))
        shard_path = out / "shards" / "shard-01.json"
        shard = json.loads(shard_path.read_text(encoding="ascii"))
        shard["candidate_count"] += 1
        audit.atomic_json(shard_path, shard)
        _, _, shard_errors = audit.load_and_validate_shards(
            [out / "shards"], manifest, candidates
        )
        self.assertTrue(any("shard_sha256 mismatch" in error for error in shard_errors))

    def test_manifest_inventory_totals_and_digest_are_recomputed(self) -> None:
        out, manifest, _, _, _ = self.scan_outputs()
        manifest["files"][0]["lines"] += 999
        unsigned = {
            key: value
            for key, value in manifest.items()
            if key != "manifest_sha256"
        }
        manifest["manifest_sha256"] = audit.payload_sha256(unsigned)
        audit.atomic_json(out / "corpus-manifest.json", manifest)
        _, _, errors = audit.validate_manifest_and_candidates(
            out / "corpus-manifest.json", out / "candidates.jsonl"
        )
        joined = "\n".join(errors)
        self.assertIn("total_lines does not match", joined)
        self.assertIn("corpus_sha256 does not match", joined)

    def test_noncanonical_unbalanced_shards_are_rejected(self) -> None:
        out, manifest, candidates, _, _ = self.scan_outputs()
        all_files = [row["path"] for row in manifest["files"]]
        all_candidates = [row["occurrence_id"] for row in candidates]
        for index in range(1, 9):
            files = all_files if index == 1 else []
            ids = all_candidates if index == 1 else []
            unsigned = {
                "schema": "denominator-review-shard-v1",
                "schema_version": audit.SCHEMA_VERSION,
                "reviewer": f"reviewer-{index:02d}",
                "manifest_sha256": manifest["manifest_sha256"],
                "corpus_sha256": manifest["corpus_sha256"],
                "candidate_count": len(ids),
                "file_count": len(files),
                "files": files,
                "candidate_ids": ids,
            }
            audit.atomic_json(
                out / "shards" / f"shard-{index:02d}.json",
                unsigned | {"shard_sha256": audit.payload_sha256(unsigned)},
            )
        _, _, errors = audit.load_and_validate_shards(
            [out / "shards"], manifest, candidates
        )
        self.assertTrue(
            any(
                "does not match deterministic balanced assignment" in error
                for error in errors
            )
        )

    def test_scan_removes_stale_numbered_shards(self) -> None:
        out = self.root / "out"
        stale = out / "shards" / "shard-09.json"
        write_text(stale, "{}\n")
        audit.scan_to_directory(self.root, out)
        self.assertFalse(stale.exists())
        self.assertEqual(len(list((out / "shards").glob("shard-*.json"))), 8)

    def test_valid_complete_ledger_is_green(self) -> None:
        out, manifest, candidates, file_owner, candidate_owner = self.scan_outputs()
        ledger = out / "ledger.jsonl"
        self.write_ledger(
            ledger,
            self.valid_records(
                manifest, candidates, file_owner, candidate_owner
            ),
        )
        self.assertEqual(
            audit.validate_ledgers(
                manifest,
                candidates,
                [ledger],
                file_owner=file_owner,
                candidate_owner=candidate_owner,
            ),
            [],
        )
        assembled, provenance = finalizer.assemble(
            manifest,
            candidates,
            [ledger],
            file_owner,
            candidate_owner,
        )
        assembled_path = out / "assembled.jsonl"
        self.write_ledger(assembled_path, assembled)
        self.assertEqual(
            audit.validate_ledgers(
                manifest,
                candidates,
                [assembled_path],
                file_owner=file_owner,
                candidate_owner=candidate_owner,
            ),
            [],
        )
        self.assertEqual(provenance["disposition_count"], len(candidates))
        self.assertEqual(provenance["attestation_count"], manifest["file_count"])

        records = self.valid_records(
            manifest, candidates, file_owner, candidate_owner
        )
        negative_controls = {
            "missing": records[1:],
            "duplicate": records + [dict(records[0])],
            "stale-line": [
                (dict(row) | {"source_line": 999})
                if row["record_type"] == "disposition" and index == 0
                else row
                for index, row in enumerate(records)
            ],
            "stale-hash": [
                (dict(row) | {"sha256": "0" * 64})
                if row["record_type"] == "file_attestation"
                else row
                for row in records
            ],
            "malformed": [
                (dict(row) | {"record_type": "unknown"})
                if index == 0
                else row
                for index, row in enumerate(records)
            ],
        }
        for name, control_rows in negative_controls.items():
            with self.subTest(finalizer_control=name):
                control = out / f"finalizer-{name}.jsonl"
                self.write_ledger(control, control_rows)
                with self.assertRaises(audit.AuditError):
                    finalizer.assemble(
                        manifest,
                        candidates,
                        [control],
                        file_owner,
                        candidate_owner,
                    )
        report = out / "report.md"
        write_text(
            report,
            "NO VERDICT FLIPS: 0 unstated denominators found, "
            "none load-bearing\n\n"
            "**VERIFIED BY RUNNING:** Synthetic end-to-end validation is "
            "complete.\n",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            result = audit.main(
                [
                    "check",
                    "--manifest",
                    str(out / "corpus-manifest.json"),
                    "--candidates",
                    str(out / "candidates.jsonl"),
                    "--shards",
                    str(out / "shards"),
                    "--ledgers",
                    str(ledger),
                    "--report",
                    str(report),
                    "--repo-root",
                    str(self.root),
                ]
            )
        self.assertEqual(result, 0)

    def test_missing_duplicate_and_malformed_dispositions_are_red(self) -> None:
        out, manifest, candidates, file_owner, candidate_owner = self.scan_outputs()
        records = self.valid_records(
            manifest, candidates, file_owner, candidate_owner
        )
        dispositions = [
            row for row in records if row["record_type"] == "disposition"
        ]
        attestations = [
            row for row in records if row["record_type"] == "file_attestation"
        ]
        broken = dispositions[1:] + [dict(dispositions[1])] + attestations
        broken[0]["classification"] = "sample"
        broken[0]["denominator_chain"] = []
        broken[0]["evidence_label"] = "ASSUMED"
        broken[0]["consequence"] = ""
        broken[0]["source_line"] = 999
        broken[0]["resolution_status"] = "done"
        ledger = out / "broken.jsonl"
        self.write_ledger(ledger, broken)
        errors = audit.validate_ledgers(
            manifest,
            candidates,
            [ledger],
            file_owner=file_owner,
            candidate_owner=candidate_owner,
        )
        joined = "\n".join(errors)
        self.assertIn("expected exactly one disposition, found 0", joined)
        self.assertIn("expected exactly one disposition, found 2", joined)
        self.assertIn("classification must be one of", joined)
        self.assertIn("denominator_chain", joined)
        self.assertIn("evidence_label", joined)
        self.assertIn("consequence", joined)
        self.assertIn("source_line", joined)
        self.assertIn("resolution_status", joined)

    def test_missing_or_stale_complete_file_attestation_is_red(self) -> None:
        out, manifest, candidates, file_owner, candidate_owner = self.scan_outputs()
        records = self.valid_records(
            manifest, candidates, file_owner, candidate_owner
        )
        attestations = [
            row for row in records if row["record_type"] == "file_attestation"
        ]
        dispositions = [
            row for row in records if row["record_type"] == "disposition"
        ]
        stale = dict(attestations[0])
        stale["sha256"] = "0" * 64
        ledger = out / "stale.jsonl"
        self.write_ledger(ledger, dispositions + [stale])
        errors = audit.validate_ledgers(
            manifest,
            candidates,
            [ledger],
            file_owner=file_owner,
            candidate_owner=candidate_owner,
        )
        joined = "\n".join(errors)
        self.assertIn("attested sha256 does not match", joined)
        self.assertIn("complete-file attestation, found 0", joined)

    def test_final_report_supports_markdown_and_all_three_leads(self) -> None:
        out, manifest, _, _, _ = self.scan_outputs()
        report = out / "report.md"
        write_text(
            report,
            "\n"
            "VERDICTS FLIP: 12 \N{EM DASH} M10 sharpness and M11 coverage\n"
            "\n"
            "# Neutral ATX heading\n"
            "\n"
            "Neutral setext heading\n"
            "----------------------\n"
            "\n"
            "**VERIFIED BY RUNNING:** Every denominator was traced across\n"
            "the complete synthetic corpus.\n"
            "\n"
            "- **INFERRED BY READING:** One document changes interpretation.\n"
            "1. **VERIFIED BY RUNNING:** The ledger remains complete.\n"
            "\n"
            "> **INFERRED BY READING:** The quoted conclusion is bounded\n"
            "> by the source text.\n"
            "\n"
            "| Finding | Axis |\n"
            "| --- | --- |\n"
            "| **VERIFIED BY RUNNING:** Reproduced | sharpness |\n"
            "| **INFERRED BY READING:** Source-only | coverage |\n"
            "| **VERIFIED BY RUNNING:** A short row |\n"
            "| **INFERRED BY READING:** An extra cell | coverage | ignored |\n"
            "\n"
            "```text\n"
            "literal command output needs no evidence label\n"
            "**UNKNOWN:** literal text is ignored\n"
            "```\n",
        )
        self.assertEqual(audit.validate_final_report(report, manifest), [])

        for lead in (
            "VERDICTS FLIP: 0 \N{EM DASH} no axes remain affected",
            "NO VERDICT FLIPS: 31 unstated denominators found, "
            "none load-bearing",
            "AUDIT BLOCKED: need the missing capture manifest",
        ):
            with self.subTest(lead=lead):
                write_text(report, lead + "\n")
                self.assertEqual(
                    audit.validate_final_report(report, manifest),
                    [],
                )

    def test_final_report_rejects_malformed_leads_and_negative_counts(self) -> None:
        out, manifest, _, _, _ = self.scan_outputs()
        report = out / "report.md"
        malformed = (
            "",
            "# Denominator provenance audit final report\n",
            "VERDICTS FLIP: 7 - sharpness\n",
            "VERDICTS FLIP: 7 \N{EM DASH} \n",
            "NO VERDICT FLIPS: 2 unstated denominators found\n",
            "AUDIT BLOCKED: \n",
        )
        for text in malformed:
            with self.subTest(text=text):
                write_text(report, text)
                errors = "\n".join(
                    audit.validate_final_report(report, manifest)
                )
                self.assertTrue(
                    "first non-empty line" in errors
                    or "no non-empty lead" in errors
                )

        write_text(
            report,
            "VERDICTS FLIP: -1 \N{EM DASH} sharpness\n",
        )
        self.assertIn(
            "VERDICTS FLIP count must be non-negative",
            "\n".join(audit.validate_final_report(report, manifest)),
        )
        write_text(
            report,
            "NO VERDICT FLIPS: -2 unstated denominators found, "
            "none load-bearing\n",
        )
        self.assertIn(
            "NO VERDICT FLIPS count must be non-negative",
            "\n".join(audit.validate_final_report(report, manifest)),
        )
        malformed = "\n".join(audit.validate_final_report(report, {}))
        self.assertIn("report manifest needs", malformed)

    def test_final_report_fails_closed_on_unlabelled_unknown_and_empty_claims(
        self,
    ) -> None:
        out, manifest, _, _, _ = self.scan_outputs()
        report = out / "report.md"
        write_text(
            report,
            "AUDIT BLOCKED: need source data\n"
            "\n"
            "An unlabelled prose claim starts here and\n"
            "**VERIFIED BY RUNNING:** a claim is hidden on its second line.\n"
            "\n"
            "- An unlabelled bullet claim.\n"
            "\n"
            "> An unlabelled blockquote claim.\n"
            "\n"
            "**ASSUMED:** An unknown label.\n"
            "\n"
            "**VERIFIED BY RUNNING:**   \n"
            "\n"
            "**:** An empty label.\n"
            "\n"
            "| Finding | Axis |\n"
            "| --- | --- |\n"
            "| Unlabelled data | sharpness |\n",
        )
        errors = "\n".join(audit.validate_final_report(report, manifest))
        self.assertIn("prose paragraph must begin exactly", errors)
        self.assertIn("hidden inside a multiline paragraph", errors)
        self.assertIn("bullet must begin exactly", errors)
        self.assertIn("blockquote paragraph must begin exactly", errors)
        self.assertIn("unknown evidence label 'ASSUMED'", errors)
        self.assertIn("empty VERIFIED BY RUNNING claim", errors)
        self.assertIn("empty evidence label", errors)
        self.assertIn("data table row must begin exactly", errors)

        write_text(
            report,
            "AUDIT BLOCKED: need source data\n\n"
            "**VERIFIED BY RUNNING:** A labelled prose paragraph.\n"
            "> A new unlabelled quote cannot hide as a continuation.\n",
        )
        errors = "\n".join(audit.validate_final_report(report, manifest))
        self.assertIn("blockquote paragraph must begin exactly", errors)

    def test_final_report_requires_closed_fenced_literal_blocks(self) -> None:
        out, manifest, _, _, _ = self.scan_outputs()
        report = out / "report.md"
        write_text(
            report,
            "AUDIT BLOCKED: need source data\n\n"
            "```text\n"
            "unlabelled literal output\n",
        )
        errors = "\n".join(audit.validate_final_report(report, manifest))
        self.assertIn("fenced literal block is not closed", errors)

    def test_live_corpus_changes_make_artifacts_stale(self) -> None:
        _, manifest, candidates, _, _ = self.scan_outputs()
        path = self.root / "docs" / "proposals" / "beta.md"
        path.write_text(
            path.read_text(encoding="utf-8") + "Admissions increased to 3 of 4.\n",
            encoding="utf-8",
            newline="\n",
        )
        errors = audit.validate_live_artifacts(self.root, manifest, candidates)
        self.assertTrue(any("manifest is stale" in error for error in errors))
        self.assertTrue(any("candidates JSONL is stale" in error for error in errors))

    def test_commissioning_baseline_plant_and_anchor_controls(self) -> None:
        result = commission.run_commission(self.root)
        self.assertEqual(result["baseline"], "GREEN")
        self.assertEqual(result["planted_unlabeled_report_claim"], "RED")
        self.assertGreater(result["unlabeled_report_errors"], 0)
        self.assertEqual(result["report_missing_anchor_control"], "RED")
        self.assertEqual(result["report_duplicate_anchor_control"], "RED")
        self.assertEqual(result["planted_unreviewed_denominator"], "RED")
        self.assertGreater(result["missing_dispositions"], 0)
        self.assertEqual(result["missing_anchor_control"], "RED")
        self.assertEqual(result["duplicate_anchor_control"], "RED")
        self.assertEqual(result["real_corpus_immutable"], "GREEN")
        with self.assertRaisesRegex(commission.CommissioningError, "found 0"):
            commission.replace_unique_anchor("missing", commission.ANCHOR, "x")
        with self.assertRaisesRegex(commission.CommissioningError, "found 2"):
            commission.replace_unique_anchor(
                commission.ANCHOR + commission.ANCHOR,
                commission.ANCHOR,
                "x",
            )
        with self.assertRaisesRegex(commission.CommissioningError, "found 0"):
            commission.replace_unique_anchor(
                "missing",
                commission.REPORT_LABEL_ANCHOR,
                commission.UNLABELED_REPORT_CLAIM,
            )
        with self.assertRaisesRegex(commission.CommissioningError, "found 2"):
            commission.replace_unique_anchor(
                commission.REPORT_LABEL_ANCHOR * 2,
                commission.REPORT_LABEL_ANCHOR,
                commission.UNLABELED_REPORT_CLAIM,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
