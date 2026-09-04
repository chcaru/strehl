from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from live_replay import AvailabilityLocks, replay, validate_spec
from m11_core import (
    GUARD_REGISTRY,
    alternating_schedule,
    cold_pair_schedule,
    object_sha256,
    sha256_bytes,
    sha256_file,
)
from m11_harness import (
    CONTRACT_PATH,
    RUNTIME_POLICY_MUTATION_IDS,
    adjudication_allows,
    aggregate_verdict,
    audit,
    begin_campaign_attempt,
    canonicalize_command_file_arguments,
    campaign_attempt_history,
    complete_alternating_schedule,
    complete_cold_pair_cell_records,
    complete_cell_records,
    commission,
    comparator_quality_fingerprint,
    comparative_ratio_control,
    commercial_comparator_execution_allowed,
    commercial_mode_role_allowed,
    cold_bar_pass,
    create_invocation_input_snapshot,
    cross_worker_byte_identity,
    expand_argv,
    finish_campaign_attempt,
    effect_recovery_pass,
    load_adapter_identity,
    m11_publication_verdict,
    m12_bridge,
    m12_join,
    measurement_receipt_valid,
    measurement_unit_for_segment,
    all_timed_outputs_match_quality,
    process_images_match_bound_artifacts,
    product_warm_role_set_valid,
    quality_corpus_evidence_valid,
    quality_envelope_complete_for_cell,
    quality_evidence_valid,
    read_artifact_binding,
    read_json,
    redact_unadjudicable_bar,
    record_identity_matches,
    records_match_campaign_identity,
    require_bound_command_files,
    reset_cold_cache,
    run_commissioned_checker,
    run_segment,
    setting_artifact_guard,
    setting_signature_consistent,
    summarize,
    summary_quality_required,
    synthetic_contract,
    synthetic_invocation,
    timing_commission_allowed,
    validate_authorization,
    validate_frozen_campaign,
    validate_host_instruments,
    validate_input_provenance,
    validate_native_dimensions,
    validate_quality_manifest,
    validate_signed_acquisition_trace,
    verify_cell_input_content,
    verify_staged_input,
    write_json,
)
from m11_runtime import (
    GpuSampler,
    ReadOnlyFileLocks,
    process_image_witness,
    sha256_file_uncached,
    stage_banners,
    tiff_witness,
)
from synthetic_target import DEFAULT_ICC, write_tiff


class RuntimeContractTests(unittest.TestCase):
    @staticmethod
    def owned_temporary_directory() -> tempfile.TemporaryDirectory[str]:
        root = CONTRACT_PATH.parent / "work" / "tests"
        root.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=root)

    def test_aborted_campaign_attempt_is_durable_across_output_paths(self) -> None:
        with self.owned_temporary_directory() as temporary:
            ledger_path = Path(temporary) / "attempts.jsonl"
            campaign_sha256 = "A" * 64
            with mock.patch(
                "m11_harness.campaign_attempt_path",
                return_value=ledger_path,
            ):
                first = begin_campaign_attempt(
                    campaign_sha256=campaign_sha256,
                    segment_name="comparative-warm",
                    records_path=Path(temporary) / "records-a.jsonl",
                )
                finish_campaign_attempt(first, "COMPLETED")
                self.assertTrue(
                    campaign_attempt_history(
                        campaign_sha256,
                        required_attempt_ids={first["attempt_id"]},
                        required_records_path=Path(temporary) / "records-a.jsonl",
                    )["valid"]
                )
                with self.assertRaisesRegex(RuntimeError, "different frozen records"):
                    begin_campaign_attempt(
                        campaign_sha256=campaign_sha256,
                        segment_name="comparative-warm",
                        records_path=Path(temporary) / "records-b.jsonl",
                    )
                second = begin_campaign_attempt(
                    campaign_sha256=campaign_sha256,
                    segment_name="comparative-warm",
                    records_path=Path(temporary) / "records-a.jsonl",
                )
                finish_campaign_attempt(second, "ABORTED")
                self.assertFalse(campaign_attempt_history(campaign_sha256)["valid"])
                with self.assertRaisesRegex(RuntimeError, "durably invalidated"):
                    begin_campaign_attempt(
                        campaign_sha256=campaign_sha256,
                        segment_name="comparative-warm",
                        records_path=Path(temporary) / "records-c.jsonl",
                    )

    def test_run_segment_records_an_aborted_attempt_on_failure(self) -> None:
        attempt = {
            "campaign_sha256": "A" * 64,
            "attempt_id": "fixture-attempt",
        }

        def fail_after_start(**kwargs: object) -> int:
            attempt_box = kwargs["attempt_box"]
            self.assertIsInstance(attempt_box, dict)
            attempt_box["attempt"] = attempt
            raise RuntimeError("planted run failure")

        with (
            mock.patch(
                "m11_harness._run_segment_impl",
                side_effect=fail_after_start,
            ),
            mock.patch("m11_harness.finish_campaign_attempt") as finish,
            self.assertRaisesRegex(RuntimeError, "planted run failure"),
        ):
            run_segment(
                campaign_path=Path("campaign.json"),
                authorization_path=Path("authorization.json"),
                segment_name="comparative-warm",
                work=Path("work"),
                records_path=Path("records.jsonl"),
            )
        finish.assert_called_once_with(attempt, "ABORTED")

    def test_every_observed_process_image_must_be_in_frozen_bundle(self) -> None:
        executable = Path(sys.executable).resolve(strict=True)
        digest = sha256_file(executable)
        process_tree = {
            "process_lifetimes": [
                {
                    "image_path": str(executable),
                    "image_sha256": digest,
                }
            ]
        }
        bound = [{"path": str(executable), "sha256": digest}]
        self.assertTrue(process_images_match_bound_artifacts(process_tree, bound))
        process_tree["process_lifetimes"].append(
            {
                "image_path": str(CONTRACT_PATH),
                "image_sha256": sha256_file(CONTRACT_PATH),
            }
        )
        self.assertFalse(process_images_match_bound_artifacts(process_tree, bound))

    def test_process_image_witness_uses_preverified_hash(self) -> None:
        executable = Path(sys.executable).resolve(strict=True)
        expected = "A" * 64
        with mock.patch(
            "m11_runtime.sha256_file",
            side_effect=AssertionError("buffered hash inside timing"),
        ):
            witness = process_image_witness(
                os.getpid(),
                {str(executable).casefold(): expected},
            )
        self.assertIsNotNone(witness)
        self.assertEqual(witness["sha256"], expected)

    def test_synthetic_tiff_satisfies_exact_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "master.tiff"
            write_tiff(
                path,
                width=4,
                height=4,
                icc=DEFAULT_ICC,
                corrupt="none",
            )
            witness = tiff_witness(path, synthetic_contract())
        self.assertTrue(witness["tiff_valid"])
        self.assertTrue(witness["highest_precision"])
        self.assertEqual(witness["compression"], "NONE")

    @unittest.skip(
        "QUARANTINED_HOST_LOAD: process-sampling timing integration needs a quiet host"
    )
    def test_synthetic_invocation_records_actual_root_image(self) -> None:
        with self.owned_temporary_directory() as temporary:
            record = synthetic_invocation(
                work=Path(temporary),
                scenario="root-image",
                arm="A",
                repetition=1,
                position=0,
                sleep_ms=1.0,
            )
        root_image = record["process_tree"]["root_image"]
        self.assertEqual(
            Path(root_image["path"]).resolve(),
            Path(sys.executable).resolve(),
        )
        self.assertEqual(root_image["sha256"], sha256_file(Path(sys.executable)))
        self.assertGreater(record["qpc_frequency"], 0)
        self.assertEqual(
            record["wall_seconds"],
            (record["finalized_qpc_ticks"] - record["started_qpc_ticks"])
            / record["qpc_frequency"],
        )
        root_sample = record["process_tree"]["process_lifetimes"][0]
        initial_gap_ms = (
            (root_sample["first_seen_qpc_ticks"] - record["started_qpc_ticks"])
            / record["qpc_frequency"]
            * 1000.0
        )
        self.assertGreaterEqual(
            record["process_tree"]["max_gap_ms"],
            initial_gap_ms,
        )

    def test_wrong_icc_fails_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "master.tiff"
            write_tiff(
                path,
                width=4,
                height=4,
                icc=DEFAULT_ICC,
                corrupt="wrong-icc",
            )
            witness = tiff_witness(path, synthetic_contract())
        self.assertFalse(witness["tiff_valid"])

    def test_stage_banner_parser_requires_explicit_banner_lines(self) -> None:
        text = "\n".join(
            [
                "M153_STAGE load wall_seconds=0.1 cpu_seconds=0.1 source=test",
                "ordinary text saying stack",
                "M153_STAGE write wall_seconds=0.2 cpu_seconds=0.1 source=test",
            ]
        )
        self.assertEqual(stage_banners(text), ["load", "write"])

    def test_hardware_probe_is_one_persistent_json_lines_process(self) -> None:
        sampler = GpuSampler(
            {
                "kind": "command",
                "argv": ["bound-probe.exe"],
                "cwd": str(CONTRACT_PATH.parent),
                "source": "test-stream",
            }
        )
        row = (
            json.dumps(
                {
                    "gpu_utilization_percent": 0.0,
                    "thermal_c": 40.0,
                    "hardware_throttle": False,
                    "gpu_processes": [],
                }
            )
            + "\n"
        )

        class FakeStdout:
            def __init__(self) -> None:
                self.lines = [row, row, row]

            def readline(self) -> str:
                value = self.lines.pop(0)
                if not self.lines:
                    sampler._stop.set()
                return value

            def close(self) -> None:
                return None

        class FakeProcess:
            def __init__(self) -> None:
                self.stdout = FakeStdout()
                self.returncode: int | None = None

            def poll(self) -> int | None:
                return self.returncode

            def terminate(self) -> None:
                self.returncode = 0

            def wait(self, timeout: float | None = None) -> int:
                del timeout
                self.returncode = 0
                return 0

            def kill(self) -> None:
                self.returncode = 1

        process = FakeProcess()
        with mock.patch("m11_runtime.subprocess.Popen", return_value=process) as popen:
            sampler._run()
        self.assertGreaterEqual(len(sampler.samples), 3)
        self.assertEqual(sampler.errors, [])
        popen.assert_called_once()

    def test_quality_template_fails_closed(self) -> None:
        path = CONTRACT_PATH.with_name("quality-manifest-template.json")
        with mock.patch(
            "m11_harness.load_contract",
            return_value=read_json(CONTRACT_PATH),
        ):
            result = validate_quality_manifest(path)
        self.assertEqual(result["status"], "UNMEASURED")
        self.assertEqual(result["qualified_modes"], [])
        self.assertTrue(
            all(modes == [] for modes in result["qualified_modes_by_cell"].values())
        )
        self.assertIn("fork-best-known", read_json(path)["modes"])

    def test_quality_manifest_records_optional_helicon_absence(self) -> None:
        with self.owned_temporary_directory() as temporary:
            path = Path(temporary) / "quality.json"
            manifest = read_json(
                CONTRACT_PATH.with_name("quality-manifest-template.json")
            )
            for mode_id in (
                "strehl-common-16",
                "zerene-pmax",
                "zerene-dmap",
                "fork-best-known",
            ):
                manifest["modes"][mode_id]["availability"] = "AVAILABLE"
            for mode_id in ("helicon-a", "helicon-b", "helicon-c"):
                manifest["modes"][mode_id]["availability"] = "UNAVAILABLE"
                manifest["modes"][mode_id]["unavailable_reason"] = (
                    "not obtainable on the frozen campaign date"
                )
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch(
                "m11_harness.load_contract",
                return_value=read_json(CONTRACT_PATH),
            ):
                result = validate_quality_manifest(path)
            self.assertEqual(result["status"], "UNMEASURED")
            self.assertEqual(
                set(result["unavailable_optional_modes"]),
                {"helicon-a", "helicon-b", "helicon-c"},
            )
            self.assertEqual(
                set(result["required_modes"]),
                {"zerene-pmax", "zerene-dmap", "fork-best-known"},
            )

    def test_quality_envelope_requires_every_mandatory_comparator(self) -> None:
        available = {
            "strehl-common-16",
            "zerene-pmax",
            "zerene-dmap",
            "fork-best-known",
        }
        decisions = {
            mode_id: (
                "UNAVAILABLE"
                if mode_id in {"helicon-a", "helicon-b", "helicon-c"}
                else "QUALITY_QUALIFIED"
            )
            for mode_id in {
                *available,
                "helicon-a",
                "helicon-b",
                "helicon-c",
            }
        }
        decisions["zerene-dmap"] = "QUALITY_FAILED"
        self.assertFalse(
            quality_envelope_complete_for_cell(
                decisions=decisions,
                available_modes=available,
                qualified_comparator_modes={
                    "zerene-pmax",
                    "fork-best-known",
                },
                strehl_qualified=True,
            )
        )
        decisions["zerene-dmap"] = "QUALITY_QUALIFIED"
        self.assertTrue(
            quality_envelope_complete_for_cell(
                decisions=decisions,
                available_modes=available,
                qualified_comparator_modes={
                    "zerene-pmax",
                    "zerene-dmap",
                    "fork-best-known",
                },
                strehl_qualified=True,
            )
        )

    def test_quality_corpus_requires_structural_and_commissioned_binding(self) -> None:
        fingerprint = {
            "measured_commit": "commit",
            "binary_sha256": "A" * 64,
            "executable_bundle_sha256": "B" * 64,
            "settings_sha256": "C" * 64,
            "output_contract_sha256": "D" * 64,
        }
        evidence = {
            "schema": "m153-m11-quality-corpus-evidence-v1",
            "evidence_tag": "MEASURED",
            "verdict": "PASS",
            "mode_id": "zerene-pmax",
            "scorecard_sha256": "E" * 64,
            **fingerprint,
            "quality_outputs": [
                {
                    "capture_id": "quality-capture",
                    "input_manifest_sha256": "F" * 64,
                    "output_sha256": "1" * 64,
                    "pixel_sha256": "2" * 64,
                }
            ],
            "all_readings_hash_bound": True,
            "no_timing_cell_setting_difference": True,
            "checker_artifact": {"path": "checker.py", "sha256": "3" * 64},
            "commission_artifact": {"path": "commission.json", "sha256": "4" * 64},
        }
        payload = {
            key: value
            for key, value in evidence.items()
            if key != "commission_artifact"
        }
        commission = {
            "schema": "m153-quality-checker-commission-v1",
            "status": "PASS",
            "checker_sha256": "3" * 64,
            "checker_bundle_sha256": "5" * 64,
            "scorecard_sha256": "E" * 64,
            "evidence_schema": evidence["schema"],
            "accepted_evidence_payload_sha256": object_sha256(payload),
            "mutations_killed": 2,
            "mutations_total": 2,
            "inert_survived": 1,
        }
        checker_result = {
            "checker_bundle_sha256": "5" * 64,
            "mutations_killed": 2,
            "mutations_total": 2,
            "inert_survived": 1,
            "verdict": "PASS",
        }
        commission_binding = {
            "path": "commission.json",
            "expected_sha256": "4" * 64,
            "actual_sha256": "4" * 64,
            "verified": True,
        }
        checker_binding = {
            "path": "checker.py",
            "expected_sha256": "3" * 64,
            "actual_sha256": "3" * 64,
            "verified": True,
        }
        with (
            mock.patch(
                "m11_harness.load_bound_json",
                return_value=(commission, commission_binding),
            ),
            mock.patch(
                "m11_harness.run_commissioned_checker",
                return_value=(checker_result, [checker_binding]),
            ),
            mock.patch("m11_harness.checker_bundle_approved", return_value=True),
        ):
            valid, _ = quality_corpus_evidence_valid(
                evidence,
                evidence_path=CONTRACT_PATH,
                mode_id="zerene-pmax",
                fingerprint=fingerprint,
                scorecard_sha256="E" * 64,
            )
            self.assertTrue(valid)
            evidence["settings_sha256"] = "9" * 64
            valid, _ = quality_corpus_evidence_valid(
                evidence,
                evidence_path=CONTRACT_PATH,
                mode_id="zerene-pmax",
                fingerprint=fingerprint,
                scorecard_sha256="E" * 64,
            )
            self.assertFalse(valid)

    def test_signed_acquisition_trace_requires_commissioned_signature(self) -> None:
        trace = {
            "schema": "m153-signed-acquisition-trace-v1",
            "evidence_tag": "MEASURED",
            "verdict": "PASS",
            "capture_id": "bee-1-cpl",
            "count": 100,
            "frames": [
                {
                    "name": f"DSC{number:05d}.ARW",
                    "shutter_close_offset_seconds": (number - 1) / 10.0,
                    "file_available_offset_seconds": number / 10.0,
                }
                for number in range(1, 101)
            ],
            "owner_signature": {
                "signer": "owner",
                "algorithm": "test",
                "signature": "signed",
            },
            "checker_artifact": {"path": "checker.py", "sha256": "A" * 64},
            "commission_artifact": {"path": "commission.json", "sha256": "B" * 64},
        }
        payload = {
            key: value for key, value in trace.items() if key != "commission_artifact"
        }
        commission = {
            "schema": "m153-acquisition-signature-checker-commission-v1",
            "status": "PASS",
            "checker_sha256": "A" * 64,
            "checker_bundle_sha256": "C" * 64,
            "scorecard_sha256": "D" * 64,
            "accepted_evidence_payload_sha256": object_sha256(payload),
        }
        checker_result = {
            "checker_bundle_sha256": "C" * 64,
            "verdict": "PASS",
        }
        binding = {"verified": True}

        def validate(candidate: dict[str, object]) -> None:
            candidate_payload = {
                key: value
                for key, value in candidate.items()
                if key != "commission_artifact"
            }
            candidate_commission = {
                **commission,
                "accepted_evidence_payload_sha256": object_sha256(candidate_payload),
            }
            with (
                mock.patch(
                    "m11_harness.load_bound_json",
                    side_effect=[(candidate, binding), (candidate_commission, binding)],
                ),
                mock.patch(
                    "m11_harness.run_commissioned_checker",
                    return_value=(
                        checker_result,
                        [{"actual_sha256": "A" * 64, "verified": True}],
                    ),
                ),
                mock.patch(
                    "m11_harness.checker_bundle_approved",
                    return_value=True,
                ),
                mock.patch(
                    "m11_harness.load_contract",
                    return_value={"scorecard": {"sha256": "D" * 64}},
                ),
            ):
                validate_signed_acquisition_trace(
                    {"path": "trace.json", "sha256": "E" * 64}
                )

        validate(trace)
        invalid = {**trace, "owner_signature": {**trace["owner_signature"]}}
        invalid["owner_signature"]["signature"] = ""
        with self.assertRaisesRegex(ValueError, "signed and commissioned"):
            validate(invalid)

    def test_contract_json_is_strict_and_has_no_real_authorization(self) -> None:
        contract = json.loads(
            CONTRACT_PATH.read_text(encoding="utf-8"),
            parse_constant=lambda value: self.fail(f"non-finite JSON: {value}"),
        )
        self.assertFalse(contract["real_run_authorized"])
        self.assertEqual(
            contract["bars"]["comparative_strehl_throughput_ratio_min"],
            2.0,
        )
        self.assertEqual(
            contract["m12_bridge"]["retained_worker_ladder"],
            [1, 2, 4, 8, 16],
        )
        self.assertEqual(
            contract["m12_bridge"]["canonical_scored_repetition"],
            1,
        )
        self.assertEqual(
            contract["current_adjudication"]["comparative"],
            "UNMEASURED_COMPARATOR_QUALIFICATION",
        )
        self.assertEqual(
            contract["current_adjudication"]["absolute_timing"],
            "QUARANTINED_HOST_LOAD",
        )

    def test_commercial_execution_is_fail_closed_but_fork_is_allowed(self) -> None:
        contract = read_json(CONTRACT_PATH)
        self.assertFalse(
            commercial_comparator_execution_allowed("zerene-pmax", contract)
        )
        self.assertFalse(commercial_comparator_execution_allowed("helicon-a", contract))
        self.assertTrue(
            commercial_comparator_execution_allowed("fork-best-known", contract)
        )
        self.assertTrue(commercial_mode_role_allowed("comparator", "zerene-pmax"))
        self.assertFalse(commercial_mode_role_allowed("strehl-common", "zerene-pmax"))
        self.assertFalse(commercial_mode_role_allowed("candidate-cpu", "helicon-a"))
        with self.assertRaisesRegex(ValueError, "execution is prohibited"):
            setting_artifact_guard(
                {
                    "role": "comparator",
                    "mode_id": "zerene-pmax",
                }
            )
        for role in ("strehl-common", "candidate-cpu", "candidate-live"):
            with self.assertRaisesRegex(ValueError, "must use the comparator role"):
                setting_artifact_guard(
                    {
                        "role": role,
                        "mode_id": "zerene-pmax",
                    }
                )

    def test_timing_commission_is_blocked_by_host_load_quarantine(self) -> None:
        self.assertFalse(timing_commission_allowed(read_json(CONTRACT_PATH)))
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            output = root / "commission.json"
            work = root / "work"
            with self.assertRaisesRegex(RuntimeError, "QUARANTINED_HOST_LOAD"):
                commission(output, work, formal_scorecard_control=True)
            self.assertFalse(output.exists())
            self.assertFalse(work.exists())

    def test_measurement_units_are_operationally_separate(self) -> None:
        self.assertEqual(
            measurement_unit_for_segment("comparative-warm"),
            "comparative",
        )
        self.assertEqual(measurement_unit_for_segment("product-warm"), "product")
        self.assertEqual(measurement_unit_for_segment("product-cold"), "product")
        self.assertEqual(measurement_unit_for_segment("live"), "product")
        with self.assertRaisesRegex(ValueError, "unknown M11 segment"):
            measurement_unit_for_segment("combined")

    def test_current_adjudication_blocks_quotable_verdicts(self) -> None:
        self.assertFalse(adjudication_allows("UNMEASURED_COMPARATOR_QUALIFICATION"))
        self.assertFalse(adjudication_allows("ADJUDICABLE", "QUARANTINED_HOST_LOAD"))
        self.assertTrue(adjudication_allows("ADJUDICABLE"))
        redacted = redact_unadjudicable_bar(
            {
                "verdict": "PASS",
                "minimum_wall_seconds": 1.0,
                "dispersion": {"median": 1.1},
            },
            adjudication_status="UNMEASURED_COMPARATOR_QUALIFICATION",
        )
        self.assertEqual(
            redacted,
            {
                "verdict": "UNMEASURED",
                "adjudication_status": "UNMEASURED_COMPARATOR_QUALIFICATION",
                "timing_values_emitted": False,
            },
        )

    def test_product_only_policy_does_not_require_quality_or_hybrid(self) -> None:
        self.assertFalse(summary_quality_required({"product"}))
        self.assertTrue(summary_quality_required({"comparative"}))
        roles = {
            "candidate-cpu": [{"workers": 16}],
            "frozen-default-baseline": [{}],
            "candidate-hybrid": [],
        }
        self.assertTrue(product_warm_role_set_valid(roles))
        self.assertFalse(
            product_warm_role_set_valid(
                {
                    **roles,
                    "candidate-hybrid": [{}, {}],
                }
            )
        )
        cold_values = {
            f"product|N{count}": {"all_pairs_pass": True} for count in (33, 105, 299)
        }
        self.assertTrue(
            cold_bar_pass(
                complete=True,
                values=cold_values,
                expected_cells=3,
            )
        )
        self.assertFalse(
            cold_bar_pass(
                complete=True,
                values=cold_values,
                expected_cells=6,
            )
        )

    def test_effect_recovery_requires_correct_sign_and_interval(self) -> None:
        positive = {
            "estimate_seconds": 1.01,
            "lower_seconds": 0.98,
            "upper_seconds": 1.04,
        }
        negative = {
            "estimate_seconds": -0.99,
            "lower_seconds": -1.03,
            "upper_seconds": -0.96,
        }
        self.assertTrue(effect_recovery_pass(positive, 1.0))
        self.assertTrue(effect_recovery_pass(negative, -1.0))
        self.assertFalse(effect_recovery_pass(positive, -1.0))
        out_of_tolerance = {
            "estimate_seconds": 1.06,
            "lower_seconds": 0.95,
            "upper_seconds": 1.07,
        }
        self.assertFalse(effect_recovery_pass(out_of_tolerance, 1.0))
        crosses_zero = {**positive, "lower_seconds": -0.01}
        self.assertFalse(effect_recovery_pass(crosses_zero, 1.0))

    def test_comparative_ratio_control_must_fire_both_directions(self) -> None:
        passing = comparative_ratio_control(
            strehl_seconds=[0.4, 0.5, 0.45],
            comparator_seconds=[0.9, 1.0, 0.95],
            expected_bar_pass=True,
        )
        failing = comparative_ratio_control(
            strehl_seconds=[0.9, 1.0, 0.95],
            comparator_seconds=[0.4, 0.5, 0.45],
            expected_bar_pass=False,
        )
        wrong_direction = comparative_ratio_control(
            strehl_seconds=[0.4, 0.5, 0.45],
            comparator_seconds=[0.9, 1.0, 0.95],
            expected_bar_pass=False,
        )
        self.assertTrue(passing["pass"])
        self.assertGreaterEqual(passing["pooled_ratio"], 2.0)
        self.assertTrue(failing["pass"])
        self.assertLess(failing["pooled_ratio"], 2.0)
        self.assertFalse(wrong_direction["pass"])

    def test_cold_pairs_require_six_distinct_reboots(self) -> None:
        def records(*, duplicate_boot: bool) -> list[dict[str, object]]:
            result = []
            for repetition in range(1, 7):
                boot_id = "boot-1" if duplicate_boot else f"boot-{repetition}"
                reset = {"windows_boot_id": boot_id}
                for member, started in (("cold", 10), ("warm", 20)):
                    result.append(
                        {
                            "segment": "product-cpu-cold",
                            "stack_id": "bee-1-cpl",
                            "count": 299,
                            "setting_id": "strehl-cpu-16",
                            "role": "strehl-product-native",
                            "workers": 16,
                            "phase": "scored",
                            "repetition": repetition,
                            "accepted": True,
                            "pair_complete": True,
                            "pair_member": member,
                            "pair_id": f"pair-{repetition}",
                            "cold_reset": reset,
                            "conditions": {
                                "cache_state": (
                                    "COLD_RESET" if member == "cold" else "WARM"
                                ),
                                "guard": {"passed": True},
                            },
                            "guards": [{"passed": True}],
                            "started_qpc_ticks": started,
                            "invocation_manifest": {
                                "path": str(
                                    CONTRACT_PATH.parent
                                    / "work"
                                    / f"pair-{repetition}-{member}"
                                    / "invocation.json"
                                )
                            },
                            "settings_sha256": "A" * 64,
                            "input_manifest_sha256": "B" * 64,
                            "input_content_sha256": "C" * 64,
                            "output_contract_sha256": "D" * 64,
                        }
                    )
            return result

        with mock.patch("m11_harness.record_artifacts_intact", return_value=True):
            self.assertIsNotNone(
                complete_cold_pair_cell_records(
                    records(duplicate_boot=False),
                    segment="product-cpu-cold",
                    stack_id="bee-1-cpl",
                    count=299,
                    setting_id="strehl-cpu-16",
                    role="strehl-product-native",
                    workers=16,
                )
            )
            self.assertIsNone(
                complete_cold_pair_cell_records(
                    records(duplicate_boot=True),
                    segment="product-cpu-cold",
                    stack_id="bee-1-cpl",
                    count=299,
                    setting_id="strehl-cpu-16",
                    role="strehl-product-native",
                    workers=16,
                )
            )

    def test_live_replay_rejects_non_owned_source(self) -> None:
        spec = {
            "schema": "m153-live-replay-v1",
            "signed_acquisition_trace_verified": True,
            "frames": [
                {
                    "name": f"DSC{number:05d}.ARW",
                    "staged_path": rf"D:\personal\macro\bee-1-cpl\DSC{number:05d}.ARW",
                    "sha256": "A" * 64,
                    "shutter_close_offset_seconds": float(number - 1),
                    "file_available_offset_seconds": float(number),
                }
                for number in range(1, 101)
            ],
            "spool_dir": str(CONTRACT_PATH.parent / "work" / "spool"),
            "marker_path": str(CONTRACT_PATH.parent / "work" / "marker.json"),
            "native_input_manifest": {
                "path": str(CONTRACT_PATH),
                "sha256": sha256_file(CONTRACT_PATH),
            },
            "cadence_manifest": {
                "path": str(CONTRACT_PATH),
                "sha256": sha256_file(CONTRACT_PATH),
            },
        }
        with self.assertRaises(ValueError):
            validate_spec(CONTRACT_PATH, spec)

    def test_live_replay_accepts_bound_distinct_prefix_and_rejects_alias(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            frames = []
            for number in range(1, 101):
                path = root / f"DSC{number:05d}.ARW"
                path.write_bytes(number.to_bytes(2, "little"))
                frames.append(
                    {
                        "name": path.name,
                        "staged_path": str(path),
                        "sha256": sha256_file(path),
                        "shutter_close_offset_seconds": (number - 1) / 1000.0,
                        "file_available_offset_seconds": number / 1000.0,
                    }
                )
            native_path = root / "native.json"
            cadence_path = root / "cadence.json"

            def write_manifests() -> None:
                native_path.write_text(
                    json.dumps(
                        {
                            "files": [
                                {
                                    "name": frame["name"],
                                    "sha256": frame["sha256"],
                                }
                                for frame in frames
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                cadence_path.write_text(
                    json.dumps(
                        {
                            "schema": "m153-signed-acquisition-trace-v1",
                            "frames": [
                                {
                                    "name": frame["name"],
                                    "shutter_close_offset_seconds": frame[
                                        "shutter_close_offset_seconds"
                                    ],
                                    "file_available_offset_seconds": frame[
                                        "file_available_offset_seconds"
                                    ],
                                }
                                for frame in frames
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

            write_manifests()
            for name in ("temp", "cache", "warpmap"):
                (root / name).mkdir()
            spec = {
                "schema": "m153-live-replay-v1",
                "signed_acquisition_trace_verified": True,
                "frames": frames,
                "spool_dir": str(root / "spool"),
                "marker_path": str(root / "marker.json"),
                "allowed_stacker_directories": [
                    str(root / name) for name in ("spool", "temp", "cache", "warpmap")
                ],
                "native_input_manifest": {
                    "path": str(native_path),
                    "sha256": sha256_file(native_path),
                },
                "cadence_manifest": {
                    "path": str(cadence_path),
                    "sha256": sha256_file(cadence_path),
                },
                "stacker_argv": [sys.executable],
                "stacker_cwd": str(CONTRACT_PATH.parent),
            }
            validate_spec(root / "spec.json", spec)
            spec["stacker_argv"].append(str(root))
            with self.assertRaisesRegex(ValueError, "pre-availability"):
                validate_spec(root / "spec.json", spec)
            spec["stacker_argv"].pop()
            last = Path(frames[-1]["staged_path"])
            last.unlink()
            os.link(frames[-2]["staged_path"], last)
            frames[-1]["sha256"] = sha256_file(last)
            write_manifests()
            spec["native_input_manifest"]["sha256"] = sha256_file(native_path)
            with self.assertRaisesRegex(ValueError, "distinct staged files"):
                validate_spec(root / "spec.json", spec)

    def test_live_replay_reveals_preverified_files_by_hard_link(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            source_root = root / "sources"
            source_root.mkdir()
            for name in ("temp", "cache", "warpmap"):
                (root / name).mkdir()
            frames = []
            for number in range(1, 101):
                path = source_root / f"DSC{number:05d}.ARW"
                path.write_bytes(number.to_bytes(2, "little"))
                frames.append(
                    {
                        "name": path.name,
                        "staged_path": str(path),
                        "sha256": sha256_file(path),
                        "shutter_close_offset_seconds": (number - 1) / 10_000.0,
                        "file_available_offset_seconds": number / 10_000.0,
                    }
                )
            native = root / "native.json"
            native.write_text(
                json.dumps(
                    {
                        "files": [
                            {"name": row["name"], "sha256": row["sha256"]}
                            for row in frames
                        ]
                    }
                ),
                encoding="utf-8",
            )
            cadence = root / "cadence.json"
            cadence.write_text(
                json.dumps(
                    {
                        "schema": "m153-signed-acquisition-trace-v1",
                        "frames": [
                            {
                                "name": row["name"],
                                "shutter_close_offset_seconds": row[
                                    "shutter_close_offset_seconds"
                                ],
                                "file_available_offset_seconds": row[
                                    "file_available_offset_seconds"
                                ],
                            }
                            for row in frames
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stacker = root / "stacker.py"
            stacker.write_text(
                "import time\ntime.sleep(0.1)\n",
                encoding="utf-8",
            )
            spec = {
                "schema": "m153-live-replay-v1",
                "signed_acquisition_trace_verified": True,
                "frames": frames,
                "spool_dir": str(root / "spool"),
                "marker_path": str(root / "marker.json"),
                "allowed_stacker_directories": [
                    str(root / name) for name in ("spool", "temp", "cache", "warpmap")
                ],
                "native_input_manifest": {
                    "path": str(native),
                    "sha256": sha256_file(native),
                },
                "cadence_manifest": {
                    "path": str(cadence),
                    "sha256": sha256_file(cadence),
                },
                "stacker_argv": [sys.executable, str(stacker)],
                "stacker_cwd": str(CONTRACT_PATH.parent),
            }
            spec_path = root / "spec.json"
            write_json(spec_path, spec)
            self.assertEqual(replay(spec_path), 0)
            marker = read_json(root / "marker.json")
            self.assertTrue(marker["frame_100_source_hash_verified"])
            self.assertTrue(marker["frame_100_atomic_hardlink_reveal"])
            self.assertTrue(marker["preavailability_read_locks_enforced"])
            self.assertEqual(
                (source_root / "DSC00100.ARW").stat().st_ino,
                (root / "spool" / "DSC00100.ARW").stat().st_ino,
            )

    def test_live_availability_lock_denies_reads_until_release(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            source = root / "frame.arw"
            linked = root / "revealed.arw"
            source.write_bytes(b"frame")
            locks = AvailabilityLocks([source])
            try:
                with self.assertRaises(PermissionError):
                    source.read_bytes()
                os.link(source, linked)
                with self.assertRaises(PermissionError):
                    linked.read_bytes()
                locks.release(0)
                self.assertEqual(linked.read_bytes(), b"frame")
            finally:
                locks.close()

    def test_hash_helpers_bind_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.bin"
            path.write_bytes(b"M153")
            self.assertEqual(sha256_file(path), sha256_bytes(b"M153"))
            self.assertEqual(sha256_file_uncached(path), sha256_file(path))

    def test_strict_json_reader_rejects_nonfinite_and_duplicate_values(self) -> None:
        with self.owned_temporary_directory() as temporary:
            path = Path(temporary) / "bad.json"
            for payload in (
                '{"value": NaN}\n',
                '{"value": 1e999}\n',
                '{"value": 1, "value": 2}\n',
            ):
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_json(path)

    def test_repository_relative_artifact_is_independent_of_process_cwd(self) -> None:
        repository_root = CONTRACT_PATH.parents[2]
        relative_contract = CONTRACT_PATH.relative_to(repository_root)
        expected = sha256_file(CONTRACT_PATH)
        with tempfile.TemporaryDirectory() as temporary:
            previous = Path.cwd()
            try:
                os.chdir(temporary)
                binding = read_artifact_binding(relative_contract, expected)
            finally:
                os.chdir(previous)
        self.assertTrue(binding["verified"])
        self.assertEqual(Path(binding["path"]), CONTRACT_PATH.resolve())

    def test_command_file_arguments_resolve_against_execution_cwd(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            checker = root / "checker.py"
            checker.write_text("print('ok')\n", encoding="utf-8")
            executable = Path(sys.executable).resolve(strict=True)
            expanded = expand_argv([checker.name], {}, cwd=root)
            self.assertEqual(expanded[0], str(checker.resolve(strict=True)))
            with self.assertRaisesRegex(ValueError, "unbound file arguments"):
                require_bound_command_files(
                    [str(executable), checker.name],
                    {executable},
                    cwd=root,
                )
            require_bound_command_files(
                [str(executable), checker.name],
                {executable, checker.resolve(strict=True)},
                cwd=root,
            )

    def test_command_file_arguments_are_canonicalized_before_launch(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            trusted = root / "trusted"
            alias = root / "alias"
            trusted.mkdir()
            checker = trusted / "checker.py"
            checker.write_text("print('trusted')\n", encoding="utf-8")
            junction = subprocess.run(
                [
                    os.environ["COMSPEC"],
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(alias),
                    str(trusted),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.assertEqual(junction.returncode, 0, junction.stdout)
            argv = canonicalize_command_file_arguments(
                [str(Path(sys.executable).resolve()), str(alias / checker.name)],
                cwd=root,
            )
            self.assertEqual(argv[1], str(checker.resolve(strict=True)))
            self.assertNotIn(str(alias), argv[1])

    def test_quality_commission_binds_exact_evidence_payload(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            checker = root / "quality-checker.py"
            commission_path = root / "quality-commission.json"
            evidence_path = root / "evidence.json"
            checker.write_text(
                "\n".join(
                    [
                        "import hashlib, json, sys",
                        "path, claimed, bundle = sys.argv[1:]",
                        "data = json.loads(open(path, encoding='utf-8').read())",
                        "data.pop('commission_artifact', None)",
                        "try:",
                        "    open(__file__, 'wb').write(b'tampered')",
                        "    locked = False",
                        "except PermissionError:",
                        "    locked = True",
                        "encoded = json.dumps(data, allow_nan=False, "
                        "ensure_ascii=True, separators=(',', ':'), "
                        "sort_keys=True).encode('ascii')",
                        "actual = hashlib.sha256(encoded).hexdigest().upper()",
                        "result = {'schema': 'm153-commissioned-check-result-v1', "
                        "'status': 'PASS' if actual == claimed and locked else 'FAIL', "
                        "'artifact_payload_sha256': actual, "
                        "'checker_bundle_sha256': bundle, "
                        "'verdict': data.get('verdict'), "
                        "'mutations_killed': 3, 'mutations_total': 3, "
                        "'inert_survived': 1}",
                        "print(json.dumps(result, sort_keys=True))",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            executable = Path(sys.executable).resolve()
            checker_artifact = {
                "path": str(executable),
                "sha256": sha256_file(executable),
            }
            support_artifact = {
                "path": str(checker),
                "sha256": sha256_file(checker),
            }
            checker_bindings = [
                read_artifact_binding(
                    Path(reference["path"]),
                    reference["sha256"],
                )
                for reference in (checker_artifact, support_artifact)
            ]
            checker_bundle_sha256 = object_sha256(
                [
                    {
                        "path": binding["path"],
                        "sha256": binding["actual_sha256"],
                    }
                    for binding in checker_bindings
                ]
            )
            fingerprint = {
                "measured_commit": "A" * 40,
                "binary_sha256": "B" * 64,
                "executable_bundle_sha256": "C" * 64,
                "settings_sha256": "C" * 64,
                "input_manifest_sha256": "D" * 64,
                "output_contract_sha256": "E" * 64,
                "output_sha256": "A" * 64,
                "pixel_sha256": "B" * 64,
                "count": 299,
            }
            evidence = {
                "schema": "m153-transfer-evidence-v1",
                "evidence_tag": "MEASURED",
                "verdict": "PASS",
                "capture_id": "bee-1-cpl",
                "count": 299,
                "mode_id": "zerene-pmax",
                "scorecard_sha256": "F" * 64,
                "checker_artifact": checker_artifact,
                "checker_support_artifacts": [support_artifact],
                "result": {"exact_transfer": True},
                **fingerprint,
            }
            commission_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-quality-checker-commission-v1",
                        "status": "PASS",
                        "checker_sha256": sha256_file(executable),
                        "checker_bundle_sha256": checker_bundle_sha256,
                        "scorecard_sha256": "F" * 64,
                        "evidence_schema": "m153-transfer-evidence-v1",
                        "accepted_evidence_payload_sha256": object_sha256(evidence),
                        "verification_argv": [
                            str(executable),
                            str(checker),
                            "{artifact}",
                            "{payload_sha256}",
                            checker_bundle_sha256,
                        ],
                        "mutations_killed": 3,
                        "mutations_total": 3,
                        "inert_survived": 1,
                    }
                ),
                encoding="utf-8",
            )
            evidence["commission_artifact"] = {
                "path": str(commission_path),
                "sha256": sha256_file(commission_path),
            }
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            arguments = {
                "schema": "m153-transfer-evidence-v1",
                "capture_id": "bee-1-cpl",
                "count": 299,
                "mode_id": "zerene-pmax",
                "axis": None,
                "fingerprint": fingerprint,
                "scorecard_sha256": "F" * 64,
                "evidence_path": evidence_path,
            }
            contract = read_json(CONTRACT_PATH)
            with mock.patch("m11_harness.load_contract", return_value=contract):
                self.assertFalse(quality_evidence_valid(evidence, **arguments))
            contract["external_checkers"]["quality"] = {
                "status": "RATIFIED",
                "approved_bundle_sha256": [checker_bundle_sha256],
            }
            with mock.patch("m11_harness.load_contract", return_value=contract):
                self.assertTrue(quality_evidence_valid(evidence, **arguments))
                different_output = json.loads(json.dumps(evidence))
                different_output["output_sha256"] = "F" * 64
                self.assertFalse(quality_evidence_valid(different_output, **arguments))
                unbound_checker = root / "unbound-checker.py"
                unbound_checker.write_text(checker.read_text(encoding="utf-8"))
                substituted_commission = json.loads(
                    commission_path.read_text(encoding="utf-8")
                )
                substituted_commission["verification_argv"] = [
                    str(executable),
                    str(unbound_checker),
                    str(checker),
                    "{artifact}",
                    "{payload_sha256}",
                    checker_bundle_sha256,
                ]
                with self.assertRaisesRegex(
                    ValueError,
                    "every and only declared checker artifacts",
                ):
                    run_commissioned_checker(
                        artifact_path=evidence_path,
                        payload_sha256=object_sha256(
                            {
                                key: value
                                for key, value in evidence.items()
                                if key != "commission_artifact"
                            }
                        ),
                        checker_artifact=checker_artifact,
                        checker_support_artifacts=[support_artifact],
                        commission=substituted_commission,
                    )
                evidence["result"]["exact_transfer"] = False
                evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                self.assertFalse(quality_evidence_valid(evidence, **arguments))

    def test_quality_cell_cannot_override_mode_fingerprint(self) -> None:
        cell_id = "bee-1-cpl:N299"
        quality_data = {
            "modes": {
                "zerene-pmax": {
                    "binary_sha256": "A" * 64,
                    "settings_sha256": "B" * 64,
                    "output_contract_sha256": "C" * 64,
                    "cell_qualifications": {
                        cell_id: {
                            "input_manifest_sha256": "D" * 64,
                            "settings_sha256": "F" * 64,
                        }
                    },
                }
            }
        }
        quality_result = {
            "mode_results": {
                "zerene-pmax": {
                    "executable_bundle_sha256": "E" * 64,
                }
            }
        }
        fingerprint = comparator_quality_fingerprint(
            quality_data,
            quality_result,
            mode_id="zerene-pmax",
            cell_id=cell_id,
            count=299,
        )
        self.assertEqual(fingerprint["settings_sha256"], "B" * 64)
        self.assertNotEqual(fingerprint["settings_sha256"], "F" * 64)

    def test_measurement_receipt_detects_timing_record_rewrite(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            receipt_path = root / "measurement-receipt.json"
            record = {
                "schema": "m153-run-record-v1",
                "wall_seconds": 3.25,
                "finalized_qpc_ns": 4_250_000_000,
                "telemetry": {"external_busy_fraction": 0.01},
                "conditions": {"thermal_after_c": 45.0},
            }
            write_json(
                receipt_path,
                {
                    "schema": "m153-measurement-receipt-v1",
                    "record": record,
                },
            )
            record["measurement_receipt"] = {
                "path": str(receipt_path),
                "sha256": sha256_file(receipt_path),
            }
            self.assertTrue(measurement_receipt_valid(record))
            record["wall_seconds"] = 0.0000001
            self.assertFalse(measurement_receipt_valid(record))

    def test_live_setting_validates_executed_stacker_not_wrapper(self) -> None:
        executable = Path(sys.executable).resolve()
        setting = {
            "mode_id": "candidate-live",
            "binary_path": str(executable),
            "binary_sha256": sha256_file(executable),
            "executable_artifacts": [
                {
                    "path": str(executable),
                    "sha256": sha256_file(executable),
                }
            ],
            "argv": [
                str(executable),
                "{input_dir}",
                "{count}",
                "{output}",
            ],
            "live_replay": {
                "stacker_argv": [
                    str(CONTRACT_PATH),
                    "{spool}",
                    "{count}",
                    "{output}",
                ]
            },
            "settings_payload": {"mode": "CPU"},
            "settings_sha256": object_sha256({"mode": "CPU"}),
        }
        with self.assertRaisesRegex(ValueError, "frozen binary"):
            setting_artifact_guard(setting)

    def test_live_setting_rejects_preavailability_input_argument(self) -> None:
        executable = Path(sys.executable).resolve()
        digest = sha256_file(executable)
        payload = {"mode": "shipping-default"}
        setting = {
            "mode_id": "candidate-live",
            "binary_path": str(executable),
            "binary_sha256": digest,
            "executable_artifacts": [
                {
                    "path": str(executable),
                    "sha256": digest,
                }
            ],
            "live_replay": {
                "stacker_argv": [
                    str(executable),
                    "{spool}",
                    "{input_dir}",
                    "{count}",
                    "{output}",
                ]
            },
            "settings_payload": payload,
            "settings_sha256": object_sha256(payload),
        }
        with self.assertRaisesRegex(ValueError, "pre-availability"):
            setting_artifact_guard(setting)

    def test_product_worker_count_is_operationally_bound(self) -> None:
        executable = Path(sys.executable).resolve()
        binary_sha256 = sha256_file(executable)
        payload = {
            "build": binary_sha256,
            "acceleration_mode": "CPU",
            "common": {},
        }
        setting = {
            "arm": "product",
            "role": "candidate-cpu",
            "mode_id": "candidate-cpu-16",
            "binary_path": str(executable),
            "binary_sha256": binary_sha256,
            "executable_artifacts": [
                {
                    "path": str(executable),
                    "sha256": binary_sha256,
                }
            ],
            "argv": [
                str(executable),
                "{input_dir}",
                "{count}",
                "{acceleration_mode}",
                "{output}",
            ],
            "workers": 16,
            "worker_binding": {"kind": "argv", "flag": "--workers"},
            "environment": {},
            "settings_payload": payload,
            "settings_sha256": object_sha256(payload),
        }
        with self.assertRaisesRegex(ValueError, "worker count"):
            setting_artifact_guard(setting)
        setting["argv"][1:1] = ["--workers", "{workers}"]
        self.assertTrue(setting_artifact_guard(setting)[0]["verified"])
        common_setting = json.loads(json.dumps(setting))
        common_setting["arm"] = "comparative"
        common_setting["role"] = "strehl-common"
        common_setting["mode_id"] = "strehl-common-1"
        common_setting["workers"] = 1
        self.assertTrue(setting_artifact_guard(common_setting)[0]["verified"])
        setting["binary_sha256"] = "F" * 64
        with self.assertRaisesRegex(ValueError, "binary declaration"):
            setting_artifact_guard(setting)

    def test_owned_write_rejects_preexisting_symlink_escape(self) -> None:
        with (
            self.owned_temporary_directory() as owned,
            tempfile.TemporaryDirectory() as external,
        ):
            link = Path(owned) / "escape"
            try:
                os.symlink(external, link, target_is_directory=True)
            except OSError as error:
                created = subprocess.run(
                    [
                        os.environ["COMSPEC"],
                        "/d",
                        "/c",
                        "mklink",
                        "/J",
                        str(link),
                        external,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if created.returncode != 0:
                    self.skipTest(
                        "directory links unavailable: "
                        f"{error}; {created.stdout}{created.stderr}"
                    )
            try:
                with self.assertRaises(ValueError):
                    write_json(link / "escaped.json", {"must_not_write": True})
                self.assertFalse((Path(external) / "escaped.json").exists())
            finally:
                if link.exists():
                    os.rmdir(link)

    def test_existing_records_reject_mixed_campaign_identity(self) -> None:
        expected = {
            "campaign_sha256": "A" * 64,
            "authorization_sha256": "B" * 64,
            "contract_sha256": "C" * 64,
            "measured_commit": "D" * 40,
        }
        records = [{**expected}, {**expected, "campaign_sha256": "E" * 64}]
        self.assertFalse(records_match_campaign_identity(records, expected))

    def test_invocation_identity_binds_campaign_authorization_and_commit(self) -> None:
        record = {
            "campaign_sha256": "A" * 64,
            "authorization_sha256": "B" * 64,
            "contract_sha256": sha256_file(CONTRACT_PATH),
            "measured_commit": "D" * 40,
            "input_content_sha256": "E" * 64,
            "campaign_attempt_id": "fixture-attempt",
        }
        invocation_identity = dict(record)
        self.assertTrue(
            record_identity_matches(
                record,
                invocation_identity,
                campaign_sha256=record["campaign_sha256"],
                authorization_sha256=record["authorization_sha256"],
                measured_commit=record["measured_commit"],
            )
        )
        for field in (
            "campaign_sha256",
            "authorization_sha256",
            "contract_sha256",
            "measured_commit",
            "input_content_sha256",
            "campaign_attempt_id",
        ):
            changed = dict(record)
            changed[field] = "F" * len(str(record[field]))
            self.assertFalse(
                record_identity_matches(
                    changed,
                    invocation_identity,
                    campaign_sha256=record["campaign_sha256"],
                    authorization_sha256=record["authorization_sha256"],
                    measured_commit=record["measured_commit"],
                ),
                field,
            )

    def test_product_setting_signature_must_match_across_counts(self) -> None:
        records = [
            {
                "role": "candidate-cpu",
                "mode_id": "CPU",
                "count": count,
                "setting_id": "candidate",
                "settings_sha256": "A" * 64,
            }
            for count in (33, 105, 299)
        ]
        self.assertTrue(
            setting_signature_consistent(
                records,
                role="candidate-cpu",
                mode_id="CPU",
                counts=(33, 105, 299),
            )
        )
        records[1]["setting_id"] = "candidate-other"
        self.assertFalse(
            setting_signature_consistent(
                records,
                role="candidate-cpu",
                mode_id="CPU",
                counts=(33, 105, 299),
            )
        )

    def test_candidate_build_identity_spans_all_three_m11_arms(self) -> None:
        candidate_path = Path(sys.executable).resolve()
        candidate_hash = sha256_file(candidate_path)
        candidate_artifacts = [
            {
                "path": str(candidate_path),
                "sha256": candidate_hash,
            }
        ]
        alternate_hash = sha256_file(CONTRACT_PATH)
        baseline = {
            "role": "frozen-default-baseline",
            "arm": "product",
            "binary_path": "baseline.exe",
            "binary_sha256": "B" * 64,
            "settings_sha256": "C" * 64,
            "settings_payload": {"build": "baseline"},
        }
        campaign = {
            "schema": "m153-m11-campaign-v1",
            "status": "FROZEN",
            "baseline_frozen_before_candidate": True,
            "host": {
                "power_plan": "frozen",
            },
            "conditions": {
                "preload_sample_seconds": 60.0,
                "start_temperature_interval_c": [40.0, 70.0],
            },
            "measured_commit": "D" * 40,
            "segments": {
                "comparative-warm": {"cache_state": "WARM"},
                "comparative-cold": {"cache_state": "COLD_RESET"},
                "product-warm": {"cache_state": "WARM"},
                "product-cold": {"cache_state": "COLD_RESET"},
                "live": {"cache_state": "WARM"},
            },
            "settings": {
                "common": {
                    "role": "strehl-common",
                    "arm": "comparative",
                    "binary_path": str(candidate_path),
                    "binary_sha256": candidate_hash,
                    "executable_artifacts": candidate_artifacts,
                },
                "cpu": {
                    "role": "candidate-cpu",
                    "arm": "product",
                    "workers": 16,
                    "binary_path": str(candidate_path),
                    "binary_sha256": candidate_hash,
                    "executable_artifacts": candidate_artifacts,
                },
                "hybrid": {
                    "role": "candidate-hybrid",
                    "arm": "product",
                    "binary_path": str(candidate_path),
                    "binary_sha256": candidate_hash,
                    "executable_artifacts": candidate_artifacts,
                },
                "live": {
                    "role": "candidate-live",
                    "arm": "product",
                    "binary_path": str(CONTRACT_PATH),
                    "binary_sha256": alternate_hash,
                    "executable_artifacts": [
                        {
                            "path": str(CONTRACT_PATH),
                            "sha256": alternate_hash,
                        }
                    ],
                },
                "baseline": baseline,
            },
            "frozen_baseline": {
                key: baseline[key]
                for key in (
                    "binary_path",
                    "binary_sha256",
                    "settings_sha256",
                    "settings_payload",
                )
            },
        }
        common_setting = campaign["settings"].pop("common")
        for workers in (1, 2, 4, 8, 16):
            campaign["settings"][f"common-{workers}"] = {
                **common_setting,
                "mode_id": f"strehl-common-{workers}",
                "workers": workers,
            }
        with self.assertRaisesRegex(ValueError, "one candidate build"):
            validate_frozen_campaign(campaign)
        with self.assertRaisesRegex(ValueError, "one candidate build"):
            validate_frozen_campaign(campaign, measurement_unit="comparative")
        with self.assertRaisesRegex(ValueError, "one candidate build"):
            validate_frozen_campaign(campaign, measurement_unit="product")
        campaign["settings"]["live"]["binary_path"] = str(candidate_path)
        campaign["settings"]["live"]["binary_sha256"] = candidate_hash
        campaign["settings"]["live"]["executable_artifacts"] = candidate_artifacts
        validate_frozen_campaign(campaign)
        product_only = json.loads(json.dumps(campaign))
        product_only["enabled_units"] = ["product"]
        product_only["segments"] = {
            name: value
            for name, value in product_only["segments"].items()
            if name in {"product-warm", "product-cold", "live"}
        }
        product_only["settings"] = {
            name: value
            for name, value in product_only["settings"].items()
            if not name.startswith("common-")
        }
        validate_frozen_campaign(product_only)
        with self.assertRaisesRegex(ValueError, "does not enable comparative"):
            validate_frozen_campaign(product_only, measurement_unit="comparative")
        del product_only["settings"]["hybrid"]
        validate_frozen_campaign(product_only)
        mislabeled = json.loads(json.dumps(product_only))
        mislabeled["settings"]["cpu"]["mode_id"] = "zerene-pmax"
        with (
            mock.patch(
                "m11_harness.executable_artifact_guard",
                side_effect=AssertionError("executable artifact was accessed"),
            ) as artifact_guard,
            self.assertRaisesRegex(ValueError, "outside the comparator role"),
        ):
            validate_frozen_campaign(mislabeled, measurement_unit="product")
        artifact_guard.assert_not_called()
        comparative_only = json.loads(json.dumps(campaign))
        comparative_only["enabled_units"] = ["comparative"]
        comparative_only["segments"] = {
            name: value
            for name, value in comparative_only["segments"].items()
            if name.startswith("comparative")
        }
        comparative_only["settings"] = {
            name: value
            for name, value in comparative_only["settings"].items()
            if name.startswith("common-")
        }
        comparative_only["baseline_frozen_before_candidate"] = False
        comparative_only.pop("frozen_baseline")
        validate_frozen_campaign(comparative_only)
        campaign["segments"]["comparative-warm"]["cache_state"] = "COLD_RESET"
        with self.assertRaisesRegex(ValueError, "cache states"):
            validate_frozen_campaign(campaign)
        campaign["segments"]["comparative-warm"]["cache_state"] = "WARM"
        campaign["settings"]["common-8"]["unfrozen_tuning"] = True
        with self.assertRaisesRegex(ValueError, "may differ only in worker count"):
            validate_frozen_campaign(campaign)
        del campaign["settings"]["common-8"]["unfrozen_tuning"]
        campaign["settings"]["live"]["executable_artifacts"] = [
            *candidate_artifacts,
            {
                "path": str(CONTRACT_PATH),
                "sha256": alternate_hash,
            },
        ]
        with self.assertRaisesRegex(ValueError, "complete candidate executable bundle"):
            validate_frozen_campaign(campaign)

    def test_staged_native_file_is_checked_against_manifest(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            frame = root / "DSC00001.ARW"
            frame.write_bytes(b"first")
            manifest = {
                "volume_id": str(root.resolve().stat().st_dev),
                "files": [
                    {
                        "name": frame.name,
                        "sha256": sha256_file(frame),
                        "bytes": frame.stat().st_size,
                    }
                ],
            }
            manifest["ordered_input_sha256"] = object_sha256(
                [{"name": frame.name, "sha256": manifest["files"][0]["sha256"]}]
            )
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(
                verify_staged_input(
                    input_dir=root,
                    manifest=manifest,
                    kind="native-arw",
                )["files"][0]["name"],
                frame.name,
            )
            self.assertEqual(
                len(
                    verify_cell_input_content(
                        {
                            "input_dir": str(root),
                            "input_manifest_path": str(manifest_path),
                            "input_manifest_sha256": sha256_file(manifest_path),
                            "count": 1,
                        },
                        segment_name="product-warm",
                    )
                ),
                64,
            )
            frame.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify_staged_input(
                    input_dir=root,
                    manifest=manifest,
                    kind="native-arw",
                )
            with self.assertRaises(ValueError):
                verify_cell_input_content(
                    {
                        "input_dir": str(root),
                        "input_manifest_path": str(manifest_path),
                        "input_manifest_sha256": sha256_file(manifest_path),
                        "count": 1,
                    },
                    segment_name="product-warm",
                )

    def test_invocation_snapshot_blocks_transient_input_substitution(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            source_dir = root / "source"
            source_dir.mkdir()
            source = source_dir / "DSC00001.ARW"
            source.write_bytes(b"registered-source")
            manifest = {
                "volume_id": str(source_dir.resolve().stat().st_dev),
                "files": [
                    {
                        "name": source.name,
                        "sha256": sha256_file(source),
                        "bytes": source.stat().st_size,
                    }
                ],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            cell = {
                "input_dir": str(source_dir),
                "input_manifest_path": str(manifest_path),
                "input_manifest_sha256": sha256_file(manifest_path),
                "count": 1,
            }
            snapshot_dir, snapshot_paths = create_invocation_input_snapshot(
                cell,
                root / "invocation-input",
            )
            alias = root / "same-file-alias.ARW"
            os.link(snapshot_paths[0], alias)
            replacement = root / "replacement.ARW"
            replacement.write_bytes(b"transient-attack")
            restore = root / "restore.ARW"
            restore.write_bytes(b"registered-source")
            os.replace(replacement, source)
            with ReadOnlyFileLocks(snapshot_paths):
                expected = verify_cell_input_content(
                    cell,
                    segment_name="product-warm",
                    input_dir_override=snapshot_dir,
                )
                with self.assertRaises(PermissionError):
                    alias.write_bytes(b"transient-attack")
                snapshot_replacement = root / "snapshot-replacement.ARW"
                snapshot_replacement.write_bytes(b"transient-attack")
                with self.assertRaises(PermissionError):
                    os.replace(snapshot_replacement, snapshot_paths[0])
                self.assertEqual(source.read_bytes(), b"transient-attack")
                os.replace(restore, source)
                self.assertEqual(
                    verify_cell_input_content(
                        cell,
                        segment_name="product-warm",
                        input_dir_override=snapshot_dir,
                    ),
                    expected,
                )
            self.assertEqual(snapshot_paths[0].read_bytes(), b"registered-source")
            self.assertEqual(source.read_bytes(), b"registered-source")

    def test_native_staging_is_bound_back_to_registered_source(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            staged_root = root / "staged"
            source_root.mkdir()
            staged_root.mkdir()
            source = source_root / "DSC00001.ARW"
            staged_file = staged_root / source.name
            source.write_bytes(b"registered-source")
            staged_file.write_bytes(source.read_bytes())
            source_exif = {"Make": "Synthetic", "Model": "M153"}
            row = {
                "name": staged_file.name,
                "sha256": sha256_file(staged_file),
                "source_name": source.name,
                "source_path": str(source),
                "source_bytes": source.stat().st_size,
                "source_mtime_ns": source.stat().st_mtime_ns,
                "source_sha256": sha256_file(source),
                "source_exif": source_exif,
                "source_exif_sha256": object_sha256(source_exif),
            }
            manifest = {
                "schema": "m153-staged-input-manifest-v1",
                "contract_sha256": sha256_file(CONTRACT_PATH),
                "census_sha256": "A" * 64,
                "stack_id": "bee-1-cpl",
                "source_path": str(source_root),
                "files": [row],
            }
            staged = {
                "files": [
                    {
                        "name": staged_file.name,
                        "sha256": sha256_file(staged_file),
                    }
                ]
            }
            contract = {
                "inputs": {
                    "bee-1-cpl": {
                        "source_path": str(source_root),
                        "frame_count": 1,
                    }
                }
            }
            with mock.patch("m11_harness.load_contract", return_value=contract):
                self.assertEqual(
                    validate_input_provenance(
                        manifest=manifest,
                        staged=staged,
                        cell={"stack_id": "bee-1-cpl", "count": 1},
                        kind="native-arw",
                        census_sha256="A" * 64,
                    ),
                    [],
                )
                source.write_bytes(b"changed-source")
                with self.assertRaises(ValueError):
                    validate_input_provenance(
                        manifest=manifest,
                        staged=staged,
                        cell={"stack_id": "bee-1-cpl", "count": 1},
                        kind="native-arw",
                        census_sha256="A" * 64,
                    )

    def test_common_tiff_embeds_source_and_decoder_provenance(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            source_root.mkdir()
            source = source_root / "DSC00001.ARW"
            source.write_bytes(b"registered-source")
            converter = root / "converter.exe"
            pattern = root / "pattern.json"
            converter.write_bytes(b"converter")
            pattern.write_text('{"pattern":"RGGB"}\n', encoding="utf-8")
            converter_ref = {
                "role": "decoder-executable",
                "path": str(converter),
                "sha256": sha256_file(converter),
            }
            pattern_ref = {
                "path": str(pattern),
                "sha256": sha256_file(pattern),
            }
            settings = {"linear": True, "demosaic": False}
            source_exif = {"Make": "Synthetic"}
            row = {
                "source_name": source.name,
                "source_path": str(source),
                "source_bytes": source.stat().st_size,
                "source_mtime_ns": source.stat().st_mtime_ns,
                "source_sha256": sha256_file(source),
                "source_exif": source_exif,
                "source_exif_sha256": object_sha256(source_exif),
            }
            bindings = [
                read_artifact_binding(converter, converter_ref["sha256"]),
                read_artifact_binding(pattern, pattern_ref["sha256"]),
            ]
            decoder_artifacts_sha256 = object_sha256(
                [
                    {
                        "path": binding["path"],
                        "sha256": binding["actual_sha256"],
                    }
                    for binding in bindings
                ]
            )
            description = {
                "decoder_artifacts_sha256": decoder_artifacts_sha256,
                "decoder_settings_sha256": object_sha256(settings),
                "source_arw_sha256": sha256_file(source),
            }
            manifest = {
                "schema": "m153-staged-input-manifest-v1",
                "contract_sha256": sha256_file(CONTRACT_PATH),
                "census_sha256": "A" * 64,
                "stack_id": "bee-1-cpl",
                "source_path": str(source_root),
                "files": [row],
                "decoder": {
                    "converter_id": "synthetic-converter-v1",
                    "artifacts": [converter_ref],
                    "settings": settings,
                    "settings_sha256": object_sha256(settings),
                    "deterministic_pattern_map": pattern_ref,
                },
            }
            staged = {
                "files": [
                    {
                        "name": "DSC00001.tiff",
                        "sha256": "B" * 64,
                        "image_description": json.dumps(description),
                    }
                ]
            }
            contract = {
                "inputs": {
                    "bee-1-cpl": {
                        "source_path": str(source_root),
                        "frame_count": 1,
                    }
                }
            }
            with mock.patch("m11_harness.load_contract", return_value=contract):
                self.assertEqual(
                    len(
                        validate_input_provenance(
                            manifest=manifest,
                            staged=staged,
                            cell={"stack_id": "bee-1-cpl", "count": 1},
                            kind="common-tiff",
                            census_sha256="A" * 64,
                        )
                    ),
                    2,
                )
                saved_artifacts = manifest["decoder"]["artifacts"]
                manifest["decoder"]["artifacts"] = []
                with self.assertRaises(ValueError):
                    validate_input_provenance(
                        manifest=manifest,
                        staged=staged,
                        cell={"stack_id": "bee-1-cpl", "count": 1},
                        kind="common-tiff",
                        census_sha256="A" * 64,
                    )
                manifest["decoder"]["artifacts"] = saved_artifacts
                description["source_arw_sha256"] = "F" * 64
                staged["files"][0]["image_description"] = json.dumps(description)
                with self.assertRaises(ValueError):
                    validate_input_provenance(
                        manifest=manifest,
                        staged=staged,
                        cell={"stack_id": "bee-1-cpl", "count": 1},
                        kind="common-tiff",
                        census_sha256="A" * 64,
                    )

    def test_native_dimensions_are_bound_to_source_evidence(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            commission_path = root / "dimensions-commission.json"
            evidence_path = root / "dimensions-evidence.json"
            checker = Path(sys.executable).resolve()
            evidence = {
                "schema": "m153-native-dimensions-evidence-v1",
                "evidence_tag": "MEASURED",
                "verdict": "PASS",
                "stack_id": "bee-1-cpl",
                "source_files": [{"name": "DSC00001.ARW", "sha256": "A" * 64}],
                "active_height": 4688,
                "active_width": 7032,
                "checker_artifact": {
                    "path": str(checker),
                    "sha256": sha256_file(checker),
                },
            }
            commission = {
                "schema": "m153-dimensions-checker-commission-v1",
                "status": "PASS",
                "checker_sha256": sha256_file(checker),
                "checker_bundle_sha256": "B" * 64,
                "accepted_evidence_payload_sha256": object_sha256(evidence),
                "mutations_killed": 2,
                "mutations_total": 2,
                "inert_survived": 1,
            }
            commission_path.write_text(json.dumps(commission), encoding="utf-8")
            evidence["commission_artifact"] = {
                "path": str(commission_path),
                "sha256": sha256_file(commission_path),
            }
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            manifest = {
                "native_dimensions_evidence": {
                    "path": str(evidence_path),
                    "sha256": sha256_file(evidence_path),
                },
                "files": [
                    {
                        "source_name": "DSC00001.ARW",
                        "source_sha256": "A" * 64,
                    }
                ],
            }
            checker_result = {
                "checker_bundle_sha256": "B" * 64,
                "mutations_killed": 2,
                "mutations_total": 2,
                "inert_survived": 1,
                "verdict": "PASS",
            }
            checker_bindings = [
                {
                    "actual_sha256": sha256_file(checker),
                }
            ]
            with (
                mock.patch(
                    "m11_harness.run_commissioned_checker",
                    return_value=(checker_result, checker_bindings),
                ),
                mock.patch(
                    "m11_harness.load_contract",
                    return_value={
                        "external_checkers": {
                            "native_dimensions": {
                                "status": "RATIFIED",
                                "approved_bundle_sha256": ["B" * 64],
                            }
                        }
                    },
                ),
            ):
                self.assertEqual(
                    len(
                        validate_native_dimensions(
                            manifest=manifest,
                            stack_id="bee-1-cpl",
                            image_contract={"height": 4688, "width": 7032},
                        )
                    ),
                    3,
                )
                with self.assertRaises(ValueError):
                    validate_native_dimensions(
                        manifest=manifest,
                        stack_id="bee-1-cpl",
                        image_contract={"height": 4, "width": 4},
                    )

    def test_adapter_identity_commission_binds_exact_payload(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            checker = root / "adapter-checker.py"
            checker.write_text(
                "\n".join(
                    [
                        "import hashlib, json, sys",
                        "path, claimed, bundle = sys.argv[1:]",
                        "data = json.loads(open(path, encoding='utf-8').read())",
                        "data.pop('commission_artifact', None)",
                        "encoded = json.dumps(data, allow_nan=False, "
                        "ensure_ascii=True, separators=(',', ':'), "
                        "sort_keys=True).encode('ascii')",
                        "actual = hashlib.sha256(encoded).hexdigest().upper()",
                        "result = {'schema': 'm153-commissioned-check-result-v1', "
                        "'status': 'PASS' if actual == claimed else 'FAIL', "
                        "'artifact_payload_sha256': actual, "
                        "'checker_bundle_sha256': bundle, "
                        "'verdict': data.get('status'), "
                        "'mutations_killed': 2, 'mutations_total': 2, "
                        "'inert_survived': 1}",
                        "print(json.dumps(result, sort_keys=True))",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            executable = Path(sys.executable).resolve()
            checker_artifact = {
                "path": str(executable),
                "sha256": sha256_file(executable),
            }
            support_artifact = {
                "path": str(checker),
                "sha256": sha256_file(checker),
            }
            checker_bindings = [
                read_artifact_binding(
                    Path(reference["path"]),
                    reference["sha256"],
                )
                for reference in (checker_artifact, support_artifact)
            ]
            checker_bundle_sha256 = object_sha256(
                [
                    {
                        "path": binding["path"],
                        "sha256": binding["actual_sha256"],
                    }
                    for binding in checker_bindings
                ]
            )
            commission_path = root / "adapter-commission.json"
            identity_path = root / "adapter-identity.json"
            identity = {
                "schema": "m153-strehl-common-adapter-identity-v1",
                "status": "PASS",
                "contract_sha256": sha256_file(CONTRACT_PATH),
                "checker_artifact": checker_artifact,
                "checker_support_artifacts": [support_artifact],
                "identity_result": {"pixel_domain_identical": True},
            }
            commission_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-adapter-identity-commission-v1",
                        "status": "PASS",
                        "checker_sha256": sha256_file(executable),
                        "checker_bundle_sha256": checker_bundle_sha256,
                        "accepted_identity_payload_sha256": object_sha256(identity),
                        "verification_argv": [
                            str(executable),
                            str(checker),
                            "{artifact}",
                            "{payload_sha256}",
                            checker_bundle_sha256,
                        ],
                        "mutations_killed": 2,
                        "mutations_total": 2,
                        "inert_survived": 1,
                    }
                ),
                encoding="utf-8",
            )
            identity["commission_artifact"] = {
                "path": str(commission_path),
                "sha256": sha256_file(commission_path),
            }
            identity_path.write_text(json.dumps(identity), encoding="utf-8")
            campaign = {
                "common_tiff_adapter_identity": {
                    "path": str(identity_path),
                    "sha256": sha256_file(identity_path),
                }
            }
            contract = read_json(CONTRACT_PATH)
            with mock.patch("m11_harness.load_contract", return_value=contract):
                with self.assertRaises(ValueError):
                    load_adapter_identity(campaign)
            contract["external_checkers"]["adapter_identity"] = {
                "status": "RATIFIED",
                "approved_bundle_sha256": [checker_bundle_sha256],
            }
            with mock.patch("m11_harness.load_contract", return_value=contract):
                loaded, _bindings = load_adapter_identity(campaign)
                self.assertEqual(loaded["status"], "PASS")
                identity["identity_result"]["pixel_domain_identical"] = False
                identity_path.write_text(json.dumps(identity), encoding="utf-8")
                campaign["common_tiff_adapter_identity"]["sha256"] = sha256_file(
                    identity_path
                )
                with self.assertRaises(ValueError):
                    load_adapter_identity(campaign)

    def test_cross_worker_identity_uses_all_five_canonical_outputs(self) -> None:
        cell = {
            "complete": True,
            "output_sha256": ["A" * 64] * 6,
            "pixel_sha256": ["B" * 64] * 6,
            "settings_sha256": ["C" * 64],
            "input_manifest_sha256": ["D" * 64],
            "input_content_sha256": ["E" * 64],
        }
        ladder = {
            str(workers): json.loads(json.dumps(cell)) for workers in (1, 2, 4, 8, 16)
        }
        self.assertTrue(cross_worker_byte_identity(ladder))
        ladder["8"]["output_sha256"][2] = "C" * 64
        self.assertTrue(
            cross_worker_byte_identity(ladder),
            "a non-canonical repeat is M12-D disclosure, not the retained M12-S gate",
        )
        ladder["8"]["output_sha256"][0] = "C" * 64
        self.assertFalse(cross_worker_byte_identity(ladder))
        ladder["8"]["output_sha256"][0] = "A" * 64
        ladder["8"]["input_manifest_sha256"] = ["E" * 64]
        self.assertFalse(cross_worker_byte_identity(ladder))
        ladder["8"]["input_manifest_sha256"] = ["D" * 64]
        ladder["8"]["input_content_sha256"] = ["F" * 64]
        self.assertFalse(cross_worker_byte_identity(ladder))
        ladder["8"]["input_content_sha256"] = ["E" * 64]
        del ladder["2"]
        self.assertFalse(cross_worker_byte_identity(ladder))

    def test_product_native_miss_does_not_change_publication_verdict(self) -> None:
        bars = {
            "comparative": {"verdict": "PASS"},
            "retained_m12_cross_worker_identity": {"verdict": "PASS"},
            "native_hybrid": {"verdict": "FAIL"},
        }
        publication = m11_publication_verdict(bars)
        product_native = aggregate_verdict(["PASS", "FAIL", "PASS", "PASS", "PASS"])
        self.assertEqual(publication, "PASS")
        self.assertEqual(product_native, "FAIL")

    def test_every_timed_comparator_output_must_match_quality_output(self) -> None:
        rows = [
            {
                "wall_seconds": 2.0,
                "repetition": 1,
                "output": {
                    "output_sha256": "A" * 64,
                    "pixel_sha256": "B" * 64,
                },
            },
            {
                "wall_seconds": 1.0,
                "repetition": 2,
                "output": {
                    "output_sha256": "C" * 64,
                    "pixel_sha256": "D" * 64,
                },
            },
        ]
        qualification = {
            "output_sha256": "A" * 64,
            "pixel_sha256": "B" * 64,
        }
        self.assertFalse(all_timed_outputs_match_quality(rows, qualification))
        qualification = {
            "output_sha256": "C" * 64,
            "pixel_sha256": "D" * 64,
        }
        self.assertFalse(all_timed_outputs_match_quality(rows, qualification))
        rows[0]["output"] = dict(rows[1]["output"])
        self.assertTrue(all_timed_outputs_match_quality(rows, qualification))

    def test_complete_cell_rejects_wrong_worker_width(self) -> None:
        records = []
        for repetition in range(0, 7):
            records.append(
                {
                    "segment": "product-warm",
                    "stack_id": "bee-1-cpl",
                    "count": 33,
                    "setting_id": "candidate",
                    "role": "candidate-cpu",
                    "workers": 1,
                    "phase": "warmup" if repetition == 0 else "scored",
                    "repetition": repetition,
                    "direction": (
                        "forward" if repetition == 0 or repetition % 2 else "reverse"
                    ),
                    "accepted": True,
                    "pair_complete": True,
                    "guards": [{"passed": True}],
                    "conditions": {"guard": {"passed": True}},
                    "settings_sha256": "A" * 64,
                    "input_manifest_sha256": "B" * 64,
                }
            )
        self.assertIsNone(
            complete_cell_records(
                records,
                segment="product-warm",
                stack_id="bee-1-cpl",
                count=33,
                setting_id="candidate",
                role="candidate-cpu",
                workers=16,
            )
        )

    def test_complete_schedule_checks_observed_chronology(self) -> None:
        records = []
        for started, row in enumerate(alternating_schedule(["A", "B"], repetitions=6)):
            records.append(
                {
                    "segment": "comparative-warm",
                    "stack_id": "bee-1-cpl",
                    "count": 33,
                    "started_qpc_ns": started,
                    "accepted": True,
                    "pair_complete": True,
                    **row,
                }
            )
        self.assertTrue(
            complete_alternating_schedule(
                records,
                segment="comparative-warm",
                stack_id="bee-1-cpl",
                count=33,
                setting_ids=["A", "B"],
            )
        )
        records[2]["started_qpc_ns"], records[3]["started_qpc_ns"] = (
            records[3]["started_qpc_ns"],
            records[2]["started_qpc_ns"],
        )
        self.assertFalse(
            complete_alternating_schedule(
                records,
                segment="comparative-warm",
                stack_id="bee-1-cpl",
                count=33,
                setting_ids=["A", "B"],
            )
        )

    def test_cold_receipt_is_bound_and_cannot_be_reused(self) -> None:
        provider_path = Path(sys.executable)
        provider_sha256 = sha256_file(provider_path)
        receipt = {
            "schema": "m153-actual-reboot-receipt-v1",
            "method": "ACTUAL_REBOOT",
            "windows_boot_id": "4242",
            "reset_complete": True,
            "no_prior_m11_invocation_this_boot": True,
            "position_key": "cell-1",
            "issued_utc": "2026-01-01T00:00:00+00:00",
            "provider_sha256": provider_sha256,
            "campaign_sha256": "A" * 64,
        }
        completed = subprocess.CompletedProcess(
            [str(provider_path)],
            0,
            stdout=json.dumps(receipt),
            stderr="",
        )
        provider = {
            "path": str(provider_path),
            "sha256": provider_sha256,
            "argv": [str(provider_path)],
        }
        used = set()
        with (
            mock.patch("m11_harness.subprocess.run", return_value=completed),
            mock.patch("m11_harness.current_windows_boot_id", return_value="4242"),
        ):
            first = reset_cold_cache(
                provider=provider,
                position_key="cell-1",
                campaign_sha256="A" * 64,
                previously_used_boot_ids=used,
            )
            self.assertIn(first["windows_boot_id"], used)
            with self.assertRaises(ValueError):
                reset_cold_cache(
                    provider=provider,
                    position_key="cell-1",
                    campaign_sha256="A" * 64,
                    previously_used_boot_ids=used,
                )

    def test_host_instruments_and_observer_control_are_hash_bound(self) -> None:
        with self.owned_temporary_directory() as temporary:
            observer_path = Path(temporary) / "observer.json"
            observer_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-observer-hash-control-v1",
                        "status": "PASS",
                        "observer_on_output_sha256": "A" * 64,
                        "observer_off_output_sha256": "A" * 64,
                        "observer_on_pixel_sha256": "B" * 64,
                        "observer_off_pixel_sha256": "B" * 64,
                    }
                ),
                encoding="utf-8",
            )
            executable = Path(sys.executable)
            probe = {
                "kind": "command",
                "path": str(executable),
                "sha256": sha256_file(executable),
                "argv": [str(executable)],
            }
            gpu_probe = {
                **probe,
                "interval_seconds": 0.010,
                "output_protocol": "persistent-json-lines-v1",
                "os_display_process_allowlist": [],
            }
            campaign = {
                "host": {
                    "thermal_probe": probe,
                    "gpu_probe": gpu_probe,
                },
                "conditions": {
                    "observer_hash_control": {
                        "path": str(observer_path),
                        "sha256": sha256_file(observer_path),
                    }
                },
            }
            result = validate_host_instruments(campaign)
            self.assertEqual(result["observer_hash_control"]["status"], "PASS")
            observer_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_host_instruments(campaign)

    def test_m12_join_requires_exact_six_hash_vectors(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            bridge_path = root / "bridge.json"
            m12_path = root / "m12.json"
            output_path = root / "join.json"
            summary_path = root / "summary.json"
            records_path = root / "records.jsonl"
            quality_path = root / "quality.json"
            m12_records_path = records_path
            m12_manifest_path = root / "m12-manifest.json"
            m12_campaign_path = root / "m12-campaign.json"
            records_path.write_text("{}\n", encoding="utf-8")
            quality_path.write_text("{}\n", encoding="utf-8")
            quality_result = {
                "status": "PASS",
                "source_manifest": {
                    "path": str(quality_path),
                    "sha256": sha256_file(quality_path),
                },
            }
            summary_path.write_text(
                json.dumps(
                    {
                        "overall_m11_verdict": "PASS",
                        "quality_qualification": quality_result,
                        "records": {
                            "path": str(records_path),
                            "sha256": sha256_file(records_path),
                        },
                    }
                ),
                encoding="utf-8",
            )
            input_paths = {}
            for count in ("33", "105", "299"):
                path = root / f"input-{count}.json"
                path.write_text(json.dumps({"count": int(count)}), encoding="utf-8")
                input_paths[count] = path
            settings_sha256 = "A" * 64
            input_hashes = {
                count: sha256_file(path) for count, path in input_paths.items()
            }
            input_content_hashes = {
                count: f"{int(count) + 1000:064X}" for count in input_paths
            }
            m12_campaign_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-m12-campaign-v1",
                        "m11_joint_track": "common-merge",
                        "status": "FROZEN",
                        "measured_commit": "B" * 40,
                        "worker16_settings_sha256": {
                            count: [settings_sha256] for count in input_paths
                        },
                        "worker16_input_manifest_sha256": input_hashes,
                        "worker16_input_content_sha256": input_content_hashes,
                    }
                ),
                encoding="utf-8",
            )
            campaign_sha256 = sha256_file(m12_campaign_path)
            m12_rows = []
            for count in ("33", "105", "299"):
                for repetition in range(7):
                    output_artifact = root / f"m12-output-{count}-{repetition}.bin"
                    output_artifact.write_bytes(
                        f"{count}:{repetition}:original".encode()
                    )
                    m12_rows.append(
                        {
                            "schema": "m153-m12-run-record-v1",
                            "evidence_tag": "MEASURED",
                            "accepted": True,
                            "segment": "comparative-warm",
                            "role": "strehl-common",
                            "stack_id": (
                                "coffee-bean" if count == "105" else "bee-1-cpl"
                            ),
                            "setting_id": "candidate-cpu",
                            "campaign_sha256": campaign_sha256,
                            "measured_commit": "B" * 40,
                            "count": int(count),
                            "workers": 16,
                            "phase": "warmup" if repetition == 0 else "scored",
                            "repetition": repetition,
                            "direction": (
                                "forward"
                                if repetition == 0 or repetition % 2
                                else "reverse"
                            ),
                            "settings_sha256": settings_sha256,
                            "input_manifest_sha256": input_hashes[count],
                            "input_content_sha256": input_content_hashes[count],
                            "output_sha256": sha256_file(output_artifact),
                            "pixel_sha256": f"{int(count) + repetition:064X}",
                            "artifact_bindings": [
                                {
                                    "path": str(m12_campaign_path),
                                    "sha256": campaign_sha256,
                                },
                                {
                                    "path": str(input_paths[count]),
                                    "sha256": input_hashes[count],
                                },
                                {
                                    "path": str(output_artifact),
                                    "sha256": sha256_file(output_artifact),
                                },
                            ],
                        }
                    )

            def exported_from_rows(source_rows):
                result = {}
                for count in ("33", "105", "299"):
                    scored = sorted(
                        (
                            row
                            for row in source_rows
                            if str(row["count"]) == count and row["phase"] == "scored"
                        ),
                        key=lambda row: row["repetition"],
                    )
                    result[count] = {
                        "workers": 16,
                        "warmups": 1,
                        "scored_repetitions": 6,
                        "schedule_status": "PASS",
                        "settings_sha256": [settings_sha256],
                        "input_manifest_sha256": [input_hashes[count]],
                        "input_content_sha256": [input_content_hashes[count]],
                        "output_sha256": [row["output_sha256"] for row in scored],
                        "pixel_sha256": [row["pixel_sha256"] for row in scored],
                    }
                return result

            def write_m12_sources(source_rows, source_cells):
                m12_records_path.write_text(
                    "".join(json.dumps(row) + "\n" for row in source_rows),
                    encoding="utf-8",
                )
                summary_path.write_text(
                    json.dumps(
                        {
                            "overall_m11_verdict": "PASS",
                            "quality_qualification": quality_result,
                            "records": {
                                "path": str(records_path),
                                "sha256": sha256_file(records_path),
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                m12_manifest_path.write_text(
                    json.dumps(
                        {
                            "schema": "m153-m12-measurement-manifest-v1",
                            "m11_joint_track": "common-merge",
                            "status": "FROZEN",
                            "campaign": {
                                "path": str(m12_campaign_path),
                                "sha256": campaign_sha256,
                            },
                            "worker16_records": {
                                "path": str(m12_records_path),
                                "sha256": sha256_file(m12_records_path),
                            },
                            "worker16_settings_sha256": {
                                count: cell["settings_sha256"]
                                for count, cell in source_cells.items()
                            },
                            "input_manifests": {
                                count: {
                                    "path": str(path),
                                    "sha256": input_hashes[count],
                                }
                                for count, path in input_paths.items()
                            },
                            "worker16_input_manifest_sha256": input_hashes,
                            "worker16_input_content_sha256": input_content_hashes,
                        }
                    ),
                    encoding="utf-8",
                )

            def m12_source_artifacts():
                return [
                    {
                        "role": "campaign",
                        "path": str(m12_campaign_path),
                        "sha256": campaign_sha256,
                    },
                    {
                        "role": "measurement-manifest",
                        "path": str(m12_manifest_path),
                        "sha256": sha256_file(m12_manifest_path),
                    },
                    {
                        "role": "worker16-records",
                        "path": str(m12_records_path),
                        "sha256": sha256_file(m12_records_path),
                    },
                ]

            exported_cells = exported_from_rows(m12_rows)
            cells = {
                count: {
                    "settings_sha256": cell["settings_sha256"],
                    "input_manifest_sha256": cell["input_manifest_sha256"],
                    "input_content_sha256": cell["input_content_sha256"],
                    "output_sha256": cell["output_sha256"],
                    "pixel_sha256": cell["pixel_sha256"],
                }
                for count, cell in exported_cells.items()
            }
            write_m12_sources(m12_rows, exported_cells)
            bridge_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-m11-to-m12-bridge-v1",
                        "status": "ELIGIBLE",
                        "m11_summary": {
                            "path": str(summary_path),
                            "sha256": sha256_file(summary_path),
                            "verdict": "PASS",
                        },
                        "records": {
                            "path": str(records_path),
                            "sha256": sha256_file(records_path),
                            "matches_summary_binding": True,
                        },
                        "worker16_cells": cells,
                        "retained_m12_cross_worker_identity": {"verdict": "PASS"},
                    }
                ),
                encoding="utf-8",
            )
            m12_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-m12-worker16-export-v1",
                        "track": "common-merge",
                        "status": "COMPLETE",
                        "worker16_status": "PASS",
                        "source_artifacts": m12_source_artifacts(),
                        "worker16_cells": exported_cells,
                    }
                ),
                encoding="utf-8",
            )

            def matching_rows(*_args, **kwargs):
                cell = cells[str(kwargs["count"])]
                return [
                    {
                        "settings_sha256": cell["settings_sha256"][0],
                        "input_manifest_sha256": cell["input_manifest_sha256"][0],
                        "input_content_sha256": cell["input_content_sha256"][0],
                        "output": {
                            "output_sha256": output_hash,
                            "pixel_sha256": pixel_hash,
                        },
                    }
                    for output_hash, pixel_hash in zip(
                        cell["output_sha256"],
                        cell["pixel_sha256"],
                    )
                ]

            def recompute_bridge(
                _summary_path: Path,
                _records_path: Path,
                recomputed_path: Path,
            ) -> int:
                recomputed_path.write_text(
                    bridge_path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                return 0

            with (
                mock.patch(
                    "m11_harness.m12_bridge",
                    side_effect=recompute_bridge,
                ),
                mock.patch(
                    "m11_harness.complete_cell_records",
                    side_effect=matching_rows,
                ),
                mock.patch(
                    "m11_harness.validate_quality_manifest",
                    return_value=quality_result,
                ),
            ):
                self.assertEqual(m12_join(bridge_path, m12_path, output_path), 0)
                self.assertEqual(read_json(output_path)["status"], "PASS")

            def mismatched_recompute_bridge(
                _summary_path: Path,
                _records_path: Path,
                recomputed_path: Path,
            ) -> int:
                recomputed = read_json(bridge_path)
                recomputed["summary_integrity"] = {
                    "summary_recomputed_from_records": False
                }
                write_json(recomputed_path, recomputed)
                return 0

            with (
                mock.patch(
                    "m11_harness.m12_bridge",
                    side_effect=mismatched_recompute_bridge,
                ),
                mock.patch(
                    "m11_harness.complete_cell_records",
                    side_effect=matching_rows,
                ),
                mock.patch(
                    "m11_harness.validate_quality_manifest",
                    return_value=quality_result,
                ),
            ):
                self.assertEqual(m12_join(bridge_path, m12_path, output_path), 2)
                self.assertEqual(read_json(output_path)["status"], "UNMEASURED")
            valid_campaign_text = m12_campaign_path.read_text(encoding="utf-8")
            valid_manifest_text = m12_manifest_path.read_text(encoding="utf-8")
            valid_export_text = m12_path.read_text(encoding="utf-8")
            unrelated_input = root / "unrelated-input-33.json"
            unrelated_input.write_text(
                '{"count": 33, "source": "other"}\n', encoding="utf-8"
            )
            unrelated_hash = sha256_file(unrelated_input)
            mismatched_campaign = read_json(m12_campaign_path)
            mismatched_campaign["worker16_input_manifest_sha256"]["33"] = unrelated_hash
            m12_campaign_path.write_text(
                json.dumps(mismatched_campaign),
                encoding="utf-8",
            )
            mismatched_manifest = read_json(m12_manifest_path)
            mismatched_manifest["campaign"]["sha256"] = sha256_file(m12_campaign_path)
            mismatched_manifest["input_manifests"]["33"] = {
                "path": str(unrelated_input),
                "sha256": unrelated_hash,
            }
            mismatched_manifest["worker16_input_manifest_sha256"]["33"] = unrelated_hash
            m12_manifest_path.write_text(
                json.dumps(mismatched_manifest),
                encoding="utf-8",
            )
            mismatched_export = read_json(m12_path)
            mismatched_export["source_artifacts"][0]["sha256"] = sha256_file(
                m12_campaign_path
            )
            mismatched_export["source_artifacts"][1]["sha256"] = sha256_file(
                m12_manifest_path
            )
            m12_path.write_text(json.dumps(mismatched_export), encoding="utf-8")
            with (
                mock.patch(
                    "m11_harness.m12_bridge",
                    side_effect=recompute_bridge,
                ),
                mock.patch(
                    "m11_harness.complete_cell_records",
                    side_effect=matching_rows,
                ),
                mock.patch(
                    "m11_harness.validate_quality_manifest",
                    return_value=quality_result,
                ),
            ):
                self.assertEqual(m12_join(bridge_path, m12_path, output_path), 2)
                self.assertEqual(read_json(output_path)["status"], "UNMEASURED")
            m12_campaign_path.write_text(valid_campaign_text, encoding="utf-8")
            m12_manifest_path.write_text(valid_manifest_text, encoding="utf-8")
            m12_path.write_text(valid_export_text, encoding="utf-8")
            m12_records_path.write_text("{}\n", encoding="utf-8")
            with (
                mock.patch(
                    "m11_harness.m12_bridge",
                    side_effect=recompute_bridge,
                ),
                mock.patch(
                    "m11_harness.complete_cell_records",
                    side_effect=matching_rows,
                ),
                mock.patch(
                    "m11_harness.validate_quality_manifest",
                    return_value=quality_result,
                ),
            ):
                self.assertEqual(m12_join(bridge_path, m12_path, output_path), 2)
                self.assertEqual(read_json(output_path)["status"], "UNMEASURED")
            write_m12_sources(m12_rows, exported_cells)
            restored_export = read_json(m12_path)
            restored_export["source_artifacts"] = m12_source_artifacts()
            restored_export["schema"] = "unregistered-schema"
            m12_path.write_text(json.dumps(restored_export), encoding="utf-8")
            with (
                mock.patch(
                    "m11_harness.m12_bridge",
                    side_effect=recompute_bridge,
                ),
                mock.patch(
                    "m11_harness.complete_cell_records",
                    side_effect=matching_rows,
                ),
                mock.patch(
                    "m11_harness.validate_quality_manifest",
                    return_value=quality_result,
                ),
            ):
                self.assertEqual(m12_join(bridge_path, m12_path, output_path), 2)
                self.assertEqual(read_json(output_path)["status"], "UNMEASURED")
            broken_rows = json.loads(json.dumps(m12_rows))
            broken_artifact = root / "m12-output-33-1.bin"
            broken_artifact.write_bytes(b"changed-but-provenanced")
            broken_output_sha256 = sha256_file(broken_artifact)
            broken_row = next(
                row
                for row in broken_rows
                if row["count"] == 33 and row["repetition"] == 1
            )
            broken_row["output_sha256"] = broken_output_sha256
            broken_row["artifact_bindings"][-1]["sha256"] = broken_output_sha256
            broken_exported_cells = exported_from_rows(broken_rows)
            broken_export = restored_export
            broken_export["schema"] = "m153-m12-worker16-export-v1"
            broken_export["worker16_cells"] = broken_exported_cells
            write_m12_sources(broken_rows, broken_exported_cells)
            broken_export["source_artifacts"] = m12_source_artifacts()
            m12_path.write_text(json.dumps(broken_export), encoding="utf-8")
            with (
                mock.patch(
                    "m11_harness.m12_bridge",
                    side_effect=recompute_bridge,
                ),
                mock.patch(
                    "m11_harness.complete_cell_records",
                    side_effect=matching_rows,
                ),
                mock.patch(
                    "m11_harness.validate_quality_manifest",
                    return_value=quality_result,
                ),
            ):
                self.assertEqual(m12_join(bridge_path, m12_path, output_path), 2)
                self.assertEqual(read_json(output_path)["status"], "UNMEASURED")

    def test_m12_bridge_recomputes_m11_instead_of_trusting_pass_text(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            records_path = root / "records.jsonl"
            summary_path = root / "summary.json"
            quality_path = root / "quality.json"
            output_path = root / "bridge.json"
            records_path.write_text("{}\n", encoding="utf-8")
            quality_path.write_text("{}\n", encoding="utf-8")
            quality = {
                "status": "UNMEASURED",
                "source_manifest": {
                    "path": str(quality_path),
                    "sha256": sha256_file(quality_path),
                },
            }
            claimed = {
                "schema": "m153-m11-summary-v1",
                "overall_m11_verdict": "PASS",
                "campaign_identity_complete": True,
                "records": {
                    "path": str(records_path),
                    "sha256": sha256_file(records_path),
                    "count": 1,
                },
                "quality_qualification": quality,
                "bars": {
                    name: {"verdict": "PASS"}
                    for name in (
                        "comparative",
                        "native_cpu_16",
                        "native_hybrid",
                        "cold_overhead",
                        "live_first_100",
                        "candidate_default_baseline",
                    )
                },
            }
            summary_path.write_text(json.dumps(claimed), encoding="utf-8")

            def recompute(
                source_records: Path,
                destination: Path,
                source_quality: Path,
            ) -> int:
                self.assertEqual(source_records.resolve(), records_path.resolve())
                self.assertEqual(source_quality.resolve(), quality_path.resolve())
                write_json(
                    destination,
                    {
                        "schema": "m153-m11-summary-v1",
                        "overall_m11_verdict": "UNMEASURED",
                        "campaign_identity_complete": False,
                        "records": claimed["records"],
                        "quality_qualification": quality,
                        "bars": {},
                    },
                )
                return 0

            with (
                mock.patch("m11_harness.summarize", side_effect=recompute),
                mock.patch(
                    "m11_harness.validate_quality_manifest",
                    return_value=quality,
                ),
                mock.patch(
                    "m11_harness.campaign_attempt_history",
                    return_value={"valid": True},
                ),
            ):
                self.assertEqual(
                    m12_bridge(summary_path, records_path, output_path),
                    0,
                )
            result = read_json(output_path)
            self.assertEqual(result["status"], "UNMEASURED")
            self.assertFalse(
                result["summary_integrity"]["summary_recomputed_from_records"]
            )

    def test_summary_requires_every_qualified_comparator(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            records_path = root / "records.jsonl"
            output_path = root / "summary.json"
            records = []
            settings = [
                (
                    f"strehl-{workers}",
                    "strehl-common",
                    f"strehl-common-{workers}",
                    workers,
                    1.0,
                )
                for workers in (1, 2, 4, 8, 16)
            ]
            settings.append(("pmax", "comparator", "zerene-pmax", 16, 2.1))
            for setting_id, role, mode_id, workers, wall in settings:
                for repetition in range(1, 7):
                    records.append(
                        {
                            "segment": "comparative-warm",
                            "stack_id": "bee-1-cpl",
                            "count": 33,
                            "setting_id": setting_id,
                            "role": role,
                            "mode_id": mode_id,
                            "workers": workers,
                            "phase": "scored",
                            "repetition": repetition,
                            "wall_seconds": wall,
                            "settings_sha256": "A" * 64,
                            "input_manifest_sha256": "B" * 64,
                            "input_content_sha256": "C" * 64,
                            "output": {
                                "output_sha256": "D" * 64,
                                "pixel_sha256": "E" * 64,
                            },
                            "accepted": True,
                        }
                    )
            records_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            quality = {
                "status": "PASS",
                "qualified_modes_by_cell": {
                    "bee-1-cpl:N33": ["zerene-pmax", "zerene-dmap"],
                    "coffee-bean:N105": ["zerene-pmax"],
                    "bee-1-cpl:N299": ["zerene-pmax", "zerene-dmap"],
                },
                "envelope_complete_by_cell": {
                    "bee-1-cpl:N33": True,
                    "coffee-bean:N105": True,
                    "bee-1-cpl:N299": True,
                },
            }
            qualified = {
                "bee-1-cpl:N33": {"zerene-pmax", "zerene-dmap"},
                "coffee-bean:N105": {"zerene-pmax"},
                "bee-1-cpl:N299": {"zerene-pmax", "zerene-dmap"},
            }
            adjudicable_contract = read_json(CONTRACT_PATH)
            adjudicable_contract["current_adjudication"] = {
                "comparative": "ADJUDICABLE",
                "product_native": "ADJUDICABLE",
                "absolute_timing": "ADJUDICABLE",
            }
            with (
                mock.patch(
                    "m11_harness.load_contract",
                    return_value=adjudicable_contract,
                ),
                mock.patch(
                    "m11_harness.qualified_mode_ids",
                    return_value=(qualified, quality),
                ),
                mock.patch(
                    "m11_harness.complete_cell_records",
                    side_effect=lambda *args, **kwargs: (
                        [
                            record
                            for record in records
                            if record["setting_id"] == kwargs["setting_id"]
                        ]
                        if kwargs["segment"] == "comparative-warm"
                        else None
                    ),
                ),
            ):
                summarize(records_path, output_path, None)
            summary = read_json(output_path)
            self.assertEqual(
                summary["bars"]["comparative"]["by_count"]["33"]["status"],
                "UNMEASURED",
            )
            self.assertEqual(
                summary["bars"]["retained_m12_cross_worker_identity"]["verdict"],
                "UNMEASURED",
            )
            self.assertEqual(summary["overall_m11_verdict"], "UNMEASURED")

    def test_product_only_summary_needs_neither_quality_nor_hybrid(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            campaign_path = root / "campaign.json"
            records_path = root / "records.jsonl"
            summary_path = root / "summary.json"
            write_json(
                campaign_path,
                {
                    "enabled_units": ["product"],
                    "settings": {
                        "cpu": {"role": "candidate-cpu"},
                        "baseline": {"role": "frozen-default-baseline"},
                        "live": {"role": "candidate-live"},
                    },
                },
            )
            campaign_sha256 = sha256_file(campaign_path)
            contract_sha256 = sha256_file(CONTRACT_PATH)
            records = []
            started_qpc_ticks = 1
            for count, stack in (
                (33, "bee-1-cpl"),
                (105, "coffee-bean"),
                (299, "bee-1-cpl"),
            ):
                for scheduled in alternating_schedule(
                    ["cpu", "baseline"],
                    repetitions=6,
                ):
                    setting_id = scheduled["setting_id"]
                    role = (
                        "candidate-cpu"
                        if setting_id == "cpu"
                        else "frozen-default-baseline"
                    )
                    records.append(
                        {
                            **scheduled,
                            "accepted": True,
                            "pair_complete": True,
                            "segment": "product-warm",
                            "stack_id": stack,
                            "count": count,
                            "setting_id": setting_id,
                            "role": role,
                            "mode_id": setting_id,
                            "workers": 16,
                            "wall_seconds": 1.0,
                            "settings_sha256": (
                                "A" * 64 if setting_id == "cpu" else "B" * 64
                            ),
                            "input_manifest_sha256": f"{count:064X}",
                            "campaign_sha256": campaign_sha256,
                            "authorization_sha256": "C" * 64,
                            "contract_sha256": contract_sha256,
                            "measured_commit": "D" * 40,
                            "campaign_attempt_id": "product-fixture",
                            "guards": [{"passed": True}],
                            "conditions": {"guard": {"passed": True}},
                            "artifact_bindings": [
                                {
                                    "path": str(campaign_path),
                                    "actual_sha256": campaign_sha256,
                                }
                            ],
                            "baseline_frozen_before_candidate": True,
                            "started_qpc_ticks": started_qpc_ticks,
                        }
                    )
                    started_qpc_ticks += 1
                for scheduled in cold_pair_schedule(["cpu"], repetitions=6):
                    repetition = int(scheduled["repetition"])
                    pair_member = str(scheduled["pair_member"])
                    reset = {
                        "windows_boot_id": f"boot-{count}-{repetition}",
                    }
                    records.append(
                        {
                            **scheduled,
                            "accepted": True,
                            "pair_complete": True,
                            "segment": "product-cold",
                            "stack_id": stack,
                            "count": count,
                            "setting_id": "cpu",
                            "role": "candidate-cpu",
                            "mode_id": "cpu",
                            "workers": 16,
                            "wall_seconds": 2.0 if pair_member == "cold" else 1.0,
                            "settings_sha256": "A" * 64,
                            "input_manifest_sha256": f"{count:064X}",
                            "input_content_sha256": f"{count + 1:064X}",
                            "output_contract_sha256": "E" * 64,
                            "campaign_sha256": campaign_sha256,
                            "authorization_sha256": "C" * 64,
                            "contract_sha256": contract_sha256,
                            "measured_commit": "D" * 40,
                            "campaign_attempt_id": "product-fixture",
                            "guards": [{"passed": True}],
                            "conditions": {
                                "cache_state": (
                                    "COLD_RESET" if pair_member == "cold" else "WARM"
                                ),
                                "guard": {"passed": True},
                            },
                            "artifact_bindings": [
                                {
                                    "path": str(campaign_path),
                                    "actual_sha256": campaign_sha256,
                                }
                            ],
                            "cold_reset": reset,
                            "invocation_manifest": {
                                "path": str(
                                    root
                                    / f"{count}-{repetition}-{pair_member}"
                                    / "manifest.json"
                                )
                            },
                            "started_qpc_ticks": started_qpc_ticks,
                        }
                    )
                    started_qpc_ticks += 1
            records_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            adjudicable_contract = read_json(CONTRACT_PATH)
            adjudicable_contract["current_adjudication"] = {
                "comparative": "UNMEASURED_COMPARATOR_QUALIFICATION",
                "product_native": "ADJUDICABLE",
                "absolute_timing": "ADJUDICABLE",
            }
            with (
                mock.patch(
                    "m11_harness.load_contract",
                    return_value=adjudicable_contract,
                ),
                mock.patch(
                    "m11_harness.record_artifacts_intact",
                    return_value=True,
                ),
                mock.patch(
                    "m11_harness.campaign_attempt_history",
                    return_value={"valid": True},
                ),
            ):
                self.assertEqual(summarize(records_path, summary_path, None), 0)
            summary = read_json(summary_path)
            self.assertTrue(summary["campaign_identity_complete"])
            self.assertEqual(
                summary["quality_qualification"]["reason"],
                "no quality manifest supplied",
            )
            self.assertEqual(summary["bars"]["native_cpu_16"]["verdict"], "PASS")
            self.assertEqual(summary["bars"]["native_hybrid"]["verdict"], "UNMEASURED")
            self.assertEqual(summary["bars"]["cold_overhead"]["verdict"], "PASS")
            self.assertEqual(
                len(summary["bars"]["cold_overhead"]["bar_applies_to"]),
                3,
            )
            self.assertEqual(
                summary["bars"]["candidate_default_baseline"]["verdict"],
                "PASS",
            )

    def test_common_merge_pass_bridges_when_product_bars_are_unmeasured(
        self,
    ) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            records_path = root / "records.jsonl"
            summary_path = root / "summary.json"
            bridge_path = root / "bridge.json"
            quality_path = root / "quality.json"
            quality_path.write_text('{"fixture":"quality"}\n', encoding="utf-8")
            quality_sha256 = sha256_file(quality_path)
            quality = {
                "status": "PASS",
                "source_manifest": {
                    "path": str(quality_path),
                    "sha256": quality_sha256,
                },
                "qualified_modes_by_cell": {},
                "strehl_qualified_by_cell": {},
                "envelope_complete_by_cell": {},
                "mode_results": {
                    "zerene-pmax": {
                        "cell_results": {},
                    },
                    "strehl-common-16": {
                        "cell_results": {},
                    },
                },
            }
            campaign_path = root / "campaign.json"
            write_json(
                campaign_path,
                {
                    "quality_qualification": {
                        "path": str(quality_path),
                        "sha256": quality_sha256,
                    }
                },
            )
            campaign_sha256 = sha256_file(campaign_path)
            contract_sha256 = sha256_file(CONTRACT_PATH)
            records = []
            started_qpc_ns = 1
            for count, stack in (
                (33, "bee-1-cpl"),
                (105, "coffee-bean"),
                (299, "bee-1-cpl"),
            ):
                cell_id = f"{stack}:N{count}"
                output_sha256 = f"{count:064X}"
                pixel_sha256 = f"{count + 1:064X}"
                comparator_output_sha256 = f"{count + 2:064X}"
                comparator_pixel_sha256 = f"{count + 3:064X}"
                quality["qualified_modes_by_cell"][cell_id] = ["zerene-pmax"]
                quality["strehl_qualified_by_cell"][cell_id] = True
                quality["envelope_complete_by_cell"][cell_id] = True
                quality["mode_results"]["zerene-pmax"]["cell_results"][cell_id] = {
                    "output_sha256": comparator_output_sha256,
                    "pixel_sha256": comparator_pixel_sha256,
                }
                quality["mode_results"]["strehl-common-16"]["cell_results"][cell_id] = {
                    "output_sha256": output_sha256,
                    "pixel_sha256": pixel_sha256,
                }
                settings = [f"strehl-common-w{workers}" for workers in (1, 2, 4, 8, 16)]
                settings.append("zerene-pmax")
                for scheduled in alternating_schedule(settings, repetitions=6):
                    setting_id = scheduled["setting_id"]
                    comparator = setting_id == "zerene-pmax"
                    workers = (
                        16
                        if comparator
                        else int(setting_id.removeprefix("strehl-common-w"))
                    )
                    record = {
                        **scheduled,
                        "schema": "m153-run-record-v1",
                        "evidence_tag": "MEASURED",
                        "accepted": True,
                        "pair_complete": True,
                        "segment": "comparative-warm",
                        "stack_id": stack,
                        "count": count,
                        "setting_id": setting_id,
                        "role": "comparator" if comparator else "strehl-common",
                        "mode_id": (
                            "zerene-pmax" if comparator else f"strehl-common-{workers}"
                        ),
                        "workers": workers,
                        "wall_seconds": 2.1 if comparator else 1.0,
                        "settings_sha256": ("A" * 64 if comparator else "B" * 64),
                        "input_manifest_sha256": f"{count + 4:064X}",
                        "input_content_sha256": f"{count + 5:064X}",
                        "output": {
                            "output_sha256": (
                                comparator_output_sha256
                                if comparator
                                else output_sha256
                            ),
                            "pixel_sha256": (
                                comparator_pixel_sha256 if comparator else pixel_sha256
                            ),
                        },
                        "invocation_manifest": {
                            "sha256": f"{started_qpc_ns:064X}",
                        },
                        "process_tree": {
                            "peak_private_committed_bytes": 1,
                        },
                        "campaign_sha256": campaign_sha256,
                        "authorization_sha256": "C" * 64,
                        "contract_sha256": contract_sha256,
                        "measured_commit": "D" * 40,
                        "campaign_attempt_id": "fixture-attempt",
                        "guards": [{"passed": True}],
                        "conditions": {"guard": {"passed": True}},
                        "artifact_bindings": [
                            {
                                "path": str(campaign_path),
                                "actual_sha256": campaign_sha256,
                            }
                        ],
                        "started_qpc_ns": started_qpc_ns,
                    }
                    started_qpc_ns += 1
                    records.append(record)
            records_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            qualified = {
                cell_id: set(modes)
                for cell_id, modes in quality["qualified_modes_by_cell"].items()
            }
            adjudicable_contract = read_json(CONTRACT_PATH)
            adjudicable_contract["current_adjudication"] = {
                "comparative": "ADJUDICABLE",
                "product_native": "ADJUDICABLE",
                "absolute_timing": "ADJUDICABLE",
            }
            with (
                mock.patch(
                    "m11_harness.qualified_mode_ids",
                    return_value=(qualified, quality),
                ),
                mock.patch(
                    "m11_harness.record_artifacts_intact",
                    return_value=True,
                ),
                mock.patch(
                    "m11_harness.validate_quality_manifest",
                    return_value=quality,
                ),
                mock.patch(
                    "m11_harness.campaign_attempt_history",
                    return_value={"valid": True},
                ),
            ):
                quarantined_path = root / "quarantined-summary.json"
                self.assertEqual(
                    summarize(records_path, quarantined_path, quality_path), 0
                )
                quarantined = read_json(quarantined_path)
                self.assertEqual(quarantined["overall_m11_verdict"], "UNMEASURED")
                self.assertIsNone(
                    quarantined["computed_m11_verdict_before_adjudication"]
                )
                self.assertEqual(
                    quarantined["publication_gate_adjudication"],
                    "UNMEASURED_COMPARATOR_QUALIFICATION",
                )
                self.assertEqual(
                    quarantined["bars"]["comparative"]["verdict"],
                    "UNMEASURED",
                )
                self.assertTrue(
                    all(
                        bar["verdict"] == "UNMEASURED"
                        for bar in quarantined["bars"].values()
                    )
                )
                self.assertEqual(quarantined["evidence_tag"], "QUARANTINED")
                self.assertFalse(quarantined["timing_values_emitted"])
                self.assertEqual(quarantined["group_dispersion"], {})
                self.assertNotIn("wall_seconds", json.dumps(quarantined))
                with mock.patch(
                    "m11_harness.load_contract",
                    return_value=adjudicable_contract,
                ):
                    self.assertEqual(
                        summarize(records_path, summary_path, quality_path),
                        0,
                    )
                    summary = read_json(summary_path)
                    self.assertEqual(summary["overall_m11_verdict"], "PASS")
                    self.assertEqual(
                        summary["bars"]["comparative"]["pooled"]["ratio"],
                        2.1,
                    )
                    self.assertEqual(
                        summary["bars"]["comparative"]["pooled"]["status"],
                        "PASS",
                    )
                    self.assertEqual(
                        summary["product_native_report_verdict"],
                        "UNMEASURED",
                    )
                    self.assertEqual(
                        summary["bars"]["retained_m12_cross_worker_identity"][
                            "verdict"
                        ],
                        "PASS",
                    )
                    self.assertEqual(
                        m12_bridge(summary_path, records_path, bridge_path),
                        0,
                    )
                    quality["strehl_qualified_by_cell"]["bee-1-cpl:N33"] = False
                    unqualified_path = root / "unqualified-summary.json"
                    self.assertEqual(
                        summarize(records_path, unqualified_path, quality_path),
                        0,
                    )
                    self.assertEqual(
                        read_json(unqualified_path)["overall_m11_verdict"],
                        "UNMEASURED",
                    )
            bridge = read_json(bridge_path)
            self.assertEqual(bridge["status"], "ELIGIBLE")
            self.assertTrue(
                all(
                    cell["record_count"] == 6
                    for cell in bridge["worker16_cells"].values()
                )
            )

    def test_authorization_cannot_overwrite_wrong_campaign_hash(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            actual_contract_hash = sha256_file(CONTRACT_PATH)
            campaign_path = root / "campaign.json"
            campaign_path.write_text(
                json.dumps(
                    {
                        "status": "FROZEN",
                        "contract": {"sha256": actual_contract_hash},
                    }
                ),
                encoding="utf-8",
            )
            commission_path = root / "commission.json"
            commission_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-formal-commission-v1",
                        "status": "PASS",
                        "contract": {"sha256": actual_contract_hash},
                        "flat_null_pass": True,
                        "async_child_pass": True,
                        "formal_slowdown_seconds": 1.0,
                        "observed_slowdown_seconds": 1.0,
                        "formal_speedup_seconds": -1.0,
                        "observed_speedup_seconds": -1.0,
                        "slowdown_pass": True,
                        "speedup_pass": True,
                        "comparative_ratio_bidirectional_pass": True,
                    }
                ),
                encoding="utf-8",
            )
            authorization_path = root / "authorization.json"
            audit_path = root / "audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-build-audit-v1",
                        "status": "PASS",
                        "source_bindings_pass": True,
                        "census_internal_checks_pass": True,
                        "guard_count": len(GUARD_REGISTRY),
                        "guard_ids": sorted(GUARD_REGISTRY),
                        "contract": {"sha256": actual_contract_hash},
                        "formal_m11_verdict": "UNMEASURED",
                    }
                ),
                encoding="utf-8",
            )
            authorization_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-real-run-authorization-v1",
                        "real_run_requested": True,
                        "authorized_by": "M153_ORCHESTRATOR",
                        "contract_sha256": actual_contract_hash,
                        "campaign_sha256": "0" * 64,
                        "commission": {
                            "path": str(commission_path),
                            "artifact_sha256": sha256_file(commission_path),
                        },
                        "build_audit": {
                            "path": str(audit_path),
                            "sha256": sha256_file(audit_path),
                        },
                    }
                ),
                encoding="utf-8",
            )
            contract = read_json(CONTRACT_PATH)
            contract["real_run_authorized"] = True
            with (
                mock.patch(
                    "m11_harness.load_contract",
                    return_value=contract,
                ),
                mock.patch(
                    "m11_harness.commission_source_bindings_current",
                    return_value=True,
                ),
            ):
                with self.assertRaises(ValueError):
                    validate_authorization(
                        campaign_path,
                        read_json(campaign_path),
                        authorization_path,
                    )

    def test_build_audit_remains_valid_when_real_run_is_enabled(self) -> None:
        with self.owned_temporary_directory() as temporary:
            root = Path(temporary)
            output = root / "audit.json"
            commission_path = root / "commission.json"
            mutation_path = root / "mutations.json"
            census_path = root / "census.json"
            contract_sha256 = sha256_file(CONTRACT_PATH)
            commission_path.write_text(
                json.dumps(
                    {
                        "status": "PASS",
                        "contract": {"sha256": contract_sha256},
                        "source_bindings": {},
                        "runtime": {
                            "python_executable": {
                                "path": str(Path(sys.executable).resolve()),
                                "sha256": sha256_file(Path(sys.executable)),
                            }
                        },
                        "real_timing_authorized": False,
                        "formal_scorecard_control": {"status": "PASS"},
                    }
                ),
                encoding="utf-8",
            )
            mutation_path.write_text(
                json.dumps(
                    {
                        "status": "PASS",
                        "guard_ids": sorted(GUARD_REGISTRY),
                        "source": {
                            "sha256": sha256_file(
                                CONTRACT_PATH.with_name("m11_core.py")
                            )
                        },
                        "runtime_source": {
                            "sha256": sha256_file(
                                CONTRACT_PATH.with_name("m11_harness.py")
                            )
                        },
                        "commissioner": {
                            "sha256": sha256_file(
                                CONTRACT_PATH.with_name("mutation_commission.py")
                            )
                        },
                        "test_sources": {
                            name: {"sha256": sha256_file(CONTRACT_PATH.with_name(name))}
                            for name in ("test_m11_harness.py", "test_runtime.py")
                        },
                        "runtime": {
                            "python_executable": {
                                "path": str(Path(sys.executable).resolve()),
                                "sha256": sha256_file(Path(sys.executable)),
                            }
                        },
                        "runtime_mutation_ids": list(RUNTIME_POLICY_MUTATION_IDS),
                        "guard_substantive_killed": len(GUARD_REGISTRY),
                        "guard_substantive_total": len(GUARD_REGISTRY),
                        "runtime_substantive_killed": len(RUNTIME_POLICY_MUTATION_IDS),
                        "runtime_substantive_total": len(RUNTIME_POLICY_MUTATION_IDS),
                        "substantive_killed": len(GUARD_REGISTRY)
                        + len(RUNTIME_POLICY_MUTATION_IDS),
                        "substantive_total": len(GUARD_REGISTRY)
                        + len(RUNTIME_POLICY_MUTATION_IDS),
                        "inert_survived": 1,
                        "inert_total": 1,
                    }
                ),
                encoding="utf-8",
            )
            captures = {
                "bee-1-cpl": {
                    "path": r"D:\personal\macro\bee-1-cpl",
                    "count": 299,
                    "first": "DSC00001.ARW",
                    "last": "DSC00299.ARW",
                    "evidence_class": "HOLDOUT - PERFORMANCE",
                    "missing": [],
                    "unexpected": [],
                },
                "coffee-bean": {
                    "path": r"D:\personal\macro\coffee-bean",
                    "count": 105,
                    "first": "DSC00016.ARW",
                    "last": "DSC00120.ARW",
                    "evidence_class": "FIXED HISTORICAL BENCHMARK - NOT HOLDOUT",
                    "missing": [],
                    "unexpected": [],
                },
            }
            census_path.write_text(
                json.dumps(
                    {
                        "schema": "m153-input-census-v1",
                        "status": "PASS",
                        "evidence_tag": "VERIFIED_METADATA_ONLY",
                        "contract": {"sha256": contract_sha256},
                        "captures": captures,
                        "readonly_snapshots": {
                            stack: {
                                "before": {
                                    "sha256": "E" * 64,
                                    "file_count": capture["count"],
                                    "total_bytes": 1,
                                },
                                "after": {
                                    "sha256": "E" * 64,
                                    "file_count": capture["count"],
                                    "total_bytes": 1,
                                },
                            }
                            for stack, capture in captures.items()
                        },
                    }
                ),
                encoding="utf-8",
            )
            contract = read_json(CONTRACT_PATH)
            contract["real_run_authorized"] = True
            with (
                mock.patch("m11_harness.load_contract", return_value=contract),
                mock.patch(
                    "m11_harness.commission_source_bindings_current",
                    return_value=True,
                ),
            ):
                result = audit(
                    output,
                    commission_path,
                    mutation_path,
                    census_path,
                )
                self.assertEqual(result, 0, read_json(output)["checks"])
            self.assertTrue(read_json(output)["real_run_authorized_in_contract"])


if __name__ == "__main__":
    unittest.main()
