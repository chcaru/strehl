from __future__ import annotations

import json
import unittest
from copy import deepcopy

import numpy as np

from analyze import array_difference, metadata_relation
from common import (
    APPROVED_INPUT,
    EXPERIMENT_DIR,
    FORBIDDEN_CAPTURE,
    REPO_ROOT,
    EvidenceError,
    chunk_sizes,
    guard_capture_path,
)
from mutation_commission import (
    BASE_FIXTURE_TEXT,
    CLAIM_AUDIT_MUTATIONS,
    CHECKOUT_POLICY_MUTATIONS,
    INERT,
    MUTATIONS,
    mutate_unique_full_line,
)
from verify import (
    CLAIM_AUDIT_CHECK_COUNT,
    EXPECTED_GROUP_MEMBERS,
    fixture_verdict,
    validate_commission_payload_binding,
    validate_evidence_citations,
    validate_fixture,
    validate_group_members,
    verify_claim_audit,
)


class DifferenceTests(unittest.TestCase):
    def test_magnitude_sign_and_relative_definition(self) -> None:
        a = np.array([[[100, 200, 300], [0, 0, 0]]], dtype=np.uint16)
        b = np.array([[[101, 198, 300], [0, 0, 0]]], dtype=np.uint16)
        result = array_difference(a, b)
        self.assertEqual(result["signed_delta_histogram"], {"-2": 1, "1": 1})
        self.assertEqual(
            result["per_channel_differing_samples"],
            {"R": 1, "G": 1, "B": 0},
        )
        self.assertEqual(result["differing_pixels_any_channel"], 1)
        self.assertEqual(result["max_absolute_dn16"], 2)
        self.assertEqual(result["max_relative_per_pixel_channel"], 0.01)
        self.assertEqual(result["differing_pixel_bbox_xyxy_inclusive"], [0, 0, 0, 0])

    def test_zero_over_zero_relative_is_zero(self) -> None:
        a = np.zeros((1, 1, 3), dtype=np.uint16)
        result = array_difference(a, a)
        self.assertEqual(result["max_relative_per_pixel_channel"], 0.0)

    def test_metadata_only_is_not_a_pixel_difference(self) -> None:
        relation = metadata_relation("a", "b", "same", "same")
        self.assertEqual(relation, "FILE_METADATA_ONLY")
        self.assertEqual(metadata_relation("a", "b", "x", "y"), "PIXELS_DIFFER")


class GuardTests(unittest.TestCase):
    def test_only_literal_input_is_accepted(self) -> None:
        self.assertEqual(guard_capture_path(APPROVED_INPUT), APPROVED_INPUT)
        with self.assertRaisesRegex(EvidenceError, "M176-E-INPUT"):
            guard_capture_path(r"C:\not-approved")

    def test_protected_and_forbidden_paths_fail_lexically(self) -> None:
        with self.assertRaisesRegex(EvidenceError, "M176-E-PROTECTED-PATH"):
            guard_capture_path(r"D:\personal\macro")
        with self.assertRaisesRegex(EvidenceError, "M176-E-FORBIDDEN-PATH"):
            guard_capture_path(FORBIDDEN_CAPTURE)


class ReductionTests(unittest.TestCase):
    def test_requested_workers_change_affected_chunks(self) -> None:
        self.assertEqual(chunk_sizes(19, 1), [19])
        self.assertEqual(chunk_sizes(19, 2), [10, 9])
        self.assertEqual(chunk_sizes(19, 3), [7, 7, 5])
        self.assertEqual(chunk_sizes(19, 4), [5, 5, 5, 4])

    def test_baseline_fixture_reaches_reduction_order(self) -> None:
        fixture = json.loads(BASE_FIXTURE_TEXT)
        self.assertEqual(fixture_verdict(fixture), "REDUCTION_ORDER")
        result = validate_fixture(fixture)
        self.assertEqual(result["verdict"], "REDUCTION_ORDER")


class MutationAnchorTests(unittest.TestCase):
    def test_all_commissioning_anchors_are_unique_full_lines(self) -> None:
        for mutation in [*MUTATIONS, INERT]:
            with self.subTest(mutation=mutation.name):
                changed = mutate_unique_full_line(BASE_FIXTURE_TEXT, mutation)
                self.assertNotEqual(changed, BASE_FIXTURE_TEXT)
                self.assertIn(mutation.replacement, changed.splitlines())

    def test_nonunique_anchor_hard_errors(self) -> None:
        bad = INERT.__class__(
            "bad-anchor",
            "}",
            "}",
            "",
        )
        text = BASE_FIXTURE_TEXT + "}\n"
        with self.assertRaisesRegex(EvidenceError, "M176-E-COMMISSION-ANCHOR"):
            mutate_unique_full_line(text, bad)


class ClaimAuditTests(unittest.TestCase):
    def load_claim_audit(self) -> dict:
        return json.loads(
            (EXPERIMENT_DIR / "out" / "claim-audit.json").read_text(encoding="utf-8")
        )

    def test_claim_audit_contract_passes_all_named_checks(self) -> None:
        result = verify_claim_audit(
            EXPERIMENT_DIR / "out" / "claim-audit.json",
            REPO_ROOT,
            REPO_ROOT / "docs" / "STATUS.md",
        )
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["checks_run"], CLAIM_AUDIT_CHECK_COUNT)
        self.assertEqual(result["claim_count"], 30)
        self.assertEqual(result["material_file_count"], 82)
        self.assertTrue(result["checkout_stability"]["bytes_identical"])

    def test_all_claim_audit_mutations_use_unique_full_line_anchors(self) -> None:
        text = (EXPERIMENT_DIR / "out" / "claim-audit.json").read_text(encoding="utf-8")
        for mutation in CLAIM_AUDIT_MUTATIONS:
            with self.subTest(mutation=mutation.name):
                changed = mutate_unique_full_line(text, mutation)
                self.assertNotEqual(changed, text)
                self.assertIn(mutation.replacement, changed)

    def test_group_member_arrays_match_explicit_contracts(self) -> None:
        claims = self.load_claim_audit()["claims"]
        validate_group_members(claims)
        pinned = next(
            claim for claim in claims if claim["id"] == "PINNED-WORKER-PYRAMID-GROUPS"
        )
        self.assertEqual(
            tuple(pinned["group_members"]),
            EXPECTED_GROUP_MEMBERS["PINNED-WORKER-PYRAMID-GROUPS"],
        )

    def test_fabricated_pinned_group_member_is_rejected(self) -> None:
        claims = deepcopy(self.load_claim_audit()["claims"])
        pinned = next(
            claim for claim in claims if claim["id"] == "PINNED-WORKER-PYRAMID-GROUPS"
        )
        index = pinned["group_members"].index("V-ca")
        pinned["group_members"][index] = "FABRICATED-NOT-A-GROUP-MEMBER"
        with self.assertRaisesRegex(
            EvidenceError,
            "M176-E-CLAIM-GROUP-MEMBERS",
        ):
            validate_group_members(claims)

    def test_missing_pinned_group_member_is_rejected(self) -> None:
        claims = deepcopy(self.load_claim_audit()["claims"])
        pinned = next(
            claim for claim in claims if claim["id"] == "PINNED-WORKER-PYRAMID-GROUPS"
        )
        pinned["group_members"].remove("V-ca")
        with self.assertRaisesRegex(
            EvidenceError,
            "M176-E-CLAIM-GROUP-MEMBERS",
        ):
            validate_group_members(claims)

    def test_nonexistent_evidence_path_with_nonempty_anchor_is_rejected(self) -> None:
        document = self.load_claim_audit()
        claims = deepcopy(document["claims"])
        claims[0]["evidence"][0]["path"] = "docs/research/DOES-NOT-EXIST-M176.md"
        inventory = set(document["material_file_inventory"]["paths"])
        inventory.add("docs/research/DOES-NOT-EXIST-M176.md")
        with self.assertRaisesRegex(EvidenceError, "M176-E-CLAIM-EVIDENCE-PATH"):
            validate_evidence_citations(claims, REPO_ROOT, inventory)

    def test_fabricated_nonempty_anchor_in_existing_blob_is_rejected(self) -> None:
        document = self.load_claim_audit()
        claims = deepcopy(document["claims"])
        claims[0]["evidence"][0]["anchor"] = (
            "M176 FABRICATED NONEMPTY ANCHOR THAT IS NOT IN THIS BLOB"
        )
        with self.assertRaisesRegex(
            EvidenceError,
            "M176-E-CLAIM-EVIDENCE-ANCHOR",
        ):
            validate_evidence_citations(
                claims,
                REPO_ROOT,
                set(document["material_file_inventory"]["paths"]),
            )

    def test_checkout_policy_mutation_anchor_is_unique_full_line(self) -> None:
        text = (EXPERIMENT_DIR / ".gitattributes").read_text(encoding="utf-8")
        for mutation in CHECKOUT_POLICY_MUTATIONS:
            with self.subTest(mutation=mutation.name):
                changed = mutate_unique_full_line(text, mutation)
                self.assertNotEqual(changed, text)
                self.assertIn(mutation.replacement, changed)

    def test_commission_output_binds_its_canonical_payload(self) -> None:
        document = json.loads(
            (EXPERIMENT_DIR / "out" / "commission.json").read_text(encoding="utf-8")
        )
        validate_commission_payload_binding(document)


if __name__ == "__main__":
    unittest.main()
