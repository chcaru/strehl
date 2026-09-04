from __future__ import annotations

import copy
import math
import unittest

import m11_core as core


HASH_A = "A" * 64
HASH_B = "B" * 64
COMMIT = "C" * 40


def valid_g01() -> dict:
    return {
        "path": str(core.LANE_ROOT / "out" / "result.json"),
        "lane_root": str(core.LANE_ROOT),
    }


def valid_g02() -> dict:
    return {
        "captures": {
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
    }


def valid_g03() -> dict:
    return {
        "before": {"sha256": HASH_A, "file_count": 2, "total_bytes": 20},
        "after": {"sha256": HASH_A, "file_count": 2, "total_bytes": 20},
    }


def valid_g04() -> dict:
    return {
        "artifacts": [
            {
                "expected_sha256": HASH_A,
                "actual_sha256": HASH_A,
                "verified": True,
            }
        ]
    }


def valid_g05() -> dict:
    return {
        "status": "QUALITY_QUALIFIED",
        "criterion_id": core.QUALITY_CRITERION_ID,
        "criterion_status": "SCORECARD_DEFINED",
        "mode_id": "zerene-pmax",
        "capture_id": "bee-1-cpl",
        "measured_commit": COMMIT,
        "binary_sha256": HASH_A,
        "executable_bundle_sha256": HASH_B,
        "settings_sha256": HASH_B,
        "input_manifest_sha256": HASH_A,
        "output_contract_sha256": HASH_B,
        "count": 299,
        "output_sha256": HASH_A,
        "pixel_sha256": HASH_B,
        "input_output_transfer": "PASS",
        "geometry_and_site_retention": "PASS",
        "quality_gates": {gate: "PASS" for gate in core.REQUIRED_QUALITY_GATES},
        "replacement_m1": {
            "instrument_status": "ADMITTED",
            "decision": "PASS",
            "artifact_sha256": HASH_A,
        },
        "retained_flat_power": {
            "population_counts": {
                "medication-pill": 84,
                "bee": 83,
                "foam": 83,
            },
            "invalid_tile_count": 0,
            "capture_median_q_flat": {
                "medication-pill": 1.0,
                "bee": 1.0,
                "foam": 1.0,
            },
            "pooled_median_q_flat": 1.0,
            "eligible_site_channel_count": 750,
            "transfer_failed_site_channels": 0,
            "gain_min": 0.995,
            "gain_max": 1.005,
            "residual_max": 0.005,
            "same_output_joint_tuple_verified": True,
            "artifact_sha256": HASH_B,
        },
        "quality_corpus_verified": True,
        "evidence_output_sha256": {
            evidence_id: HASH_A
            for evidence_id in (
                "transfer",
                "geometry",
                *core.REQUIRED_QUALITY_GATES,
            )
        },
        "evidence_pixel_sha256": {
            evidence_id: HASH_B
            for evidence_id in (
                "transfer",
                "geometry",
                *core.REQUIRED_QUALITY_GATES,
            )
        },
        "bound_artifacts_verified": True,
    }


def valid_g06() -> dict:
    shared = {
        "input_manifest_sha256": HASH_A,
        "ordered_input_sha256": HASH_B,
        "volume_id": "D-VOLUME-1",
        "dimensions": [10, 20, 3],
        "bit_depth": 16,
        "icc_sha256": HASH_A,
        "compression": "NONE",
    }
    return {"modes": [{**shared, "id": "a"}, {**shared, "id": "b"}]}


def valid_g07() -> dict:
    return {
        "stack_id": "bee-1-cpl",
        "count": 33,
        "ordered_names": [f"DSC{number:05d}.ARW" for number in range(1, 34)],
        "ordered_sha256": [HASH_A] * 33,
    }


def valid_g08() -> dict:
    fingerprint = {
        "mode_id": "zerene-pmax",
        "binary_sha256": HASH_A,
        "executable_bundle_sha256": HASH_B,
        "settings_sha256": HASH_B,
        "input_manifest_sha256": HASH_A,
        "output_contract_sha256": HASH_B,
        "count": 299,
    }
    return {"timed": fingerprint, "qualified": dict(fingerprint)}


def valid_g09() -> dict:
    return {
        "qpc_frequency": 10_000_000,
        "job_assigned_before_resume": True,
        "root_returncode": 0,
        "active_processes_final": 0,
        "process_images_preverified_before_timing": True,
        "process_count_total": 2,
        "sample_count": 10,
        "sample_interval_ms": 10,
        "missed_intervals": 0,
        "max_gap_ms": 10.0,
        "process_lifetimes": [
            {"image_path": "a.exe", "image_sha256": HASH_A},
            {"image_path": "b.exe", "image_sha256": HASH_B},
        ],
        "root_exit_qpc_ticks": 100,
        "drained_qpc_ticks": 200,
        "child_expected": True,
    }


def valid_g10() -> dict:
    return {
        "qpc_frequency": 10_000_000,
        "exclusive_open_succeeded": True,
        "output_flush_succeeded": True,
        "manifest_flush_succeeded": True,
        "manifest_structurally_valid": True,
        "tiff_valid": True,
        "highest_precision": True,
        "compression": "NONE",
        "output_sha256": HASH_A,
        "pixel_sha256": HASH_B,
        "manifest_sha256": HASH_A,
        "process_drained_qpc_ticks": 100,
        "finalized_qpc_ticks": 200,
    }


def valid_g11() -> dict:
    return {
        "wall_seconds": 1.0,
        "process_tree_cpu_seconds": 0.2,
        "process_tree_counter_failures": 0,
        "observer_cpu_seconds": 0.1,
        "system_times_start": {"busy_100ns": 1_000_000},
        "system_times_end": {"busy_100ns": 6_000_000},
        "logical_processor_count": 10,
        "busy_fraction": 0.02,
        "external_busy_fraction": 0.03,
        "read_bytes": 10,
        "write_bytes": 20,
        "sample_count": 10,
        "sample_interval_ms": 10,
        "missed_intervals": 0,
        "cpu_samples": [
            {
                "qpc_ticks": value,
                "qpc_frequency": 10_000_000,
                "idle_100ns": value,
                "kernel_100ns": value,
                "user_100ns": value,
            }
            for value in range(10)
        ],
        "gpu_source": "bound-provider",
        "gpu_utilization_percent": [0.0, 25.0],
        "hardware_samples": [
            {
                "qpc_ticks": value,
                "qpc_frequency": 10_000_000,
                "thermal_c": 60.0,
                "hardware_throttle": False,
                "gpu_processes": [],
            }
            for value in range(2)
        ],
        "synthetic_telemetry": True,
        "hardware_throttle_observed": False,
        "unapproved_gpu_processes": [],
        "gpu_process_allowlist_pass": True,
        "stage_banners": ["load", "register", "stack", "color", "write"],
        "required_stages": ["load", "register", "stack", "color", "write"],
        "numeric_stage_timings_required": ["load", "stack", "write"],
        "stage_measurements": [
            {
                "stage": stage,
                "wall_seconds": 0.1,
                "cpu_seconds": 0.1,
                "source": "test",
            }
            for stage in ("load", "register", "stack", "color", "write")
        ],
    }


def valid_g12() -> dict:
    return {
        "preload_quiet_pass": True,
        "preload_duration_seconds": 60.0,
        "preload_elapsed_seconds": 60.0,
        "preload_cpu_formula": (
            "(DeltaKernel-DeltaIdle+DeltaUser)/(DeltaKernel+DeltaUser)"
        ),
        "external_busy_fraction": 0.1,
        "external_busy_max": 0.1,
        "power_plan_before": "high-performance",
        "power_plan_after": "high-performance",
        "thermal_before_c": 60.0,
        "thermal_after_c": 61.0,
        "thermal_delta_max_c": 2.0,
        "start_temperature_min_c": 55.0,
        "start_temperature_max_c": 65.0,
        "telemetry_sample_interval_ms": 10,
        "hardware_throttle_observed": False,
        "gpu_process_allowlist_pass": True,
        "cache_state": "WARM",
        "input_preflight_io": "BUFFERED",
        "executable_preflight_io": "BUFFERED",
        "observer_hash_control": "PASS",
    }


def valid_g13() -> dict:
    records = [
        {**row, "accepted": True, "pair_complete": True}
        for row in core.alternating_schedule(["A", "B"], repetitions=6)
    ]
    return {"settings": ["A", "B"], "repetitions": 6, "records": records}


def valid_g14() -> dict:
    return {
        "strehl_wall_seconds": [5.0, 5.1, 5.2, 5.3, 5.4, 5.5],
        "qualified_comparator_wall_seconds": {
            "slow": [12.0, 12.1, 12.2, 12.3, 12.4, 12.5],
            "fast": [10.0, 10.1, 10.2, 10.3, 10.4, 10.5],
        },
        "comparator_identity": {
            "slow": {
                "product_id": "zerene-stacker",
                "mode_id": "zerene-dmap",
            },
            "fast": {
                "product_id": "zerene-stacker",
                "mode_id": "zerene-pmax",
            },
        },
        "candidate_wall_seconds": [6.0, 6.1, 6.2, 6.3, 6.4, 6.5],
        "baseline_wall_seconds": [4.0, 4.1, 4.2, 4.3, 4.4, 4.5],
        "selected_fastest_comparator": "fast",
        "strehl_throughput_ratio": 2.0,
        "candidate_default_wall_ratio": 1.5,
        "headline_statistic": "minimum_of_six",
        "dispersion_reported": True,
    }


def valid_g15() -> dict:
    return {
        "receipt_sha256": HASH_A,
        "previously_used_boot_ids": [],
        "current_windows_boot_id": "4242",
        "position_key": "cold:n33:r1:a",
        "campaign_sha256": HASH_B,
        "receipt": {
            "schema": "m153-actual-reboot-receipt-v1",
            "method": "ACTUAL_REBOOT",
            "windows_boot_id": "4242",
            "reset_complete": True,
            "no_prior_m11_invocation_this_boot": True,
            "position_key": "cold:n33:r1:a",
            "issued_utc": "2026-09-04T00:00:00Z",
            "provider_sha256": HASH_A,
            "campaign_sha256": HASH_B,
        },
    }


def valid_g16() -> dict:
    return {
        "count": 100,
        "signed_acquisition_trace_verified": True,
        "frame_100_source_hash_verified": True,
        "frame_100_atomic_hardlink_reveal": True,
        "preavailability_read_locks_enforced": True,
        "cadence_manifest_sha256": HASH_A,
        "qpc_frequency": 10_000_000,
        "marker_qpc_frequency": 10_000_000,
        "process_started_qpc_ticks": 50,
        "frame_100_shutter_close_qpc_ticks": 100,
        "frame_100_available_qpc_ticks": 5_000_100,
        "finalized_qpc_ticks": 20_000_100,
        "latency_seconds": 2.0,
    }


def valid_g17() -> dict:
    cells = {
        count: {
            "settings_sha256": [HASH_A],
            "input_manifest_sha256": [HASH_B],
            "input_content_sha256": [HASH_A],
            "output_sha256": [HASH_B] * 6,
            "pixel_sha256": [HASH_A] * 6,
        }
        for count in ("33", "105", "299")
    }
    return {
        "bridge_status": "ELIGIBLE",
        "m11": {
            "verdict": "PASS",
            "cross_worker_identity_verdict": "PASS",
            "worker16_cells": copy.deepcopy(cells),
        },
        "m12": {"worker16_cells": copy.deepcopy(cells)},
    }


def valid_g18() -> dict:
    return {
        "real_run_requested": True,
        "authorized_by": "M153_ORCHESTRATOR",
        "actual_contract_sha256": HASH_A,
        "authorized_contract_sha256": HASH_A,
        "actual_campaign_sha256": HASH_B,
        "authorized_campaign_sha256": HASH_B,
        "contract_allows_real_run": True,
        "commission": {
            "schema": "m153-formal-commission-v1",
            "status": "PASS",
            "contract": {"sha256": HASH_A},
            "flat_null_pass": True,
            "async_child_pass": True,
            "formal_slowdown_seconds": 1.0,
            "observed_slowdown_seconds": 1.0,
            "formal_speedup_seconds": -1.0,
            "observed_speedup_seconds": -1.0,
            "slowdown_pass": True,
            "speedup_pass": True,
            "comparative_ratio_bidirectional_pass": True,
            "artifact_sha256": HASH_A,
        },
        "build_audit": {
            "schema": "m153-build-audit-v1",
            "status": "PASS",
            "source_bindings_pass": True,
            "census_internal_checks_pass": True,
            "guard_count": len(core.GUARD_REGISTRY),
            "contract": {"sha256": HASH_A},
            "formal_m11_verdict": "UNMEASURED",
            "artifact_sha256": HASH_B,
        },
    }


def valid_g19() -> dict:
    return {
        "comparison": "comparative",
        "changed_factor_groups": ["program-and-frozen-mode"],
        "held_fixed_sha256": [HASH_A, HASH_A],
        "confounds": [],
    }


def valid_g20() -> dict:
    return {
        "statistic_kind": "live",
        "latency_seconds": [8.0, 8.5, 9.0, 9.5, 9.9, 10.0],
        "maximum_seconds": 10.0,
        "all_replays_pass": True,
    }


class GuardMutationTests(unittest.TestCase):
    def assert_guard(self, guard_id: str, valid: dict, invalid: dict) -> None:
        self.assertTrue(core.evaluate_guard(guard_id, valid).passed)
        self.assertFalse(core.evaluate_guard(guard_id, invalid).passed)

    def test_g01_owned_output(self) -> None:
        invalid = valid_g01()
        invalid["path"] = r"D:\personal\macro\forbidden.json"
        self.assert_guard("G01-owned-output", valid_g01(), invalid)

    def test_g02_capture_contract(self) -> None:
        invalid = valid_g02()
        invalid["captures"]["bee-1-cpl"]["count"] = 298
        self.assert_guard("G02-capture-contract", valid_g02(), invalid)

    def test_g03_readonly_snapshot(self) -> None:
        invalid = valid_g03()
        invalid["after"]["sha256"] = HASH_B
        self.assert_guard("G03-readonly-snapshot", valid_g03(), invalid)

    def test_g04_artifact_binding(self) -> None:
        invalid = valid_g04()
        invalid["artifacts"][0]["actual_sha256"] = HASH_B
        self.assert_guard("G04-artifact-binding", valid_g04(), invalid)

    def test_g05_quality_qualified(self) -> None:
        invalid = valid_g05()
        invalid["replacement_m1"]["instrument_status"] = "INSTRUMENT_UNBOUND"
        self.assert_guard("G05-quality-qualified", valid_g05(), invalid)

    def test_g05_accepts_quality_qualified_strehl_denominator(self) -> None:
        payload = valid_g05()
        payload["mode_id"] = core.STREHL_QUALITY_MODE_ID
        self.assertTrue(core.evaluate_guard("G05-quality-qualified", payload).passed)

    def test_g05_requires_retained_flat_power(self) -> None:
        invalid = valid_g05()
        del invalid["retained_flat_power"]
        self.assert_guard("G05-quality-qualified", valid_g05(), invalid)

    def test_g05_accepts_exact_flat_power_ceiling(self) -> None:
        valid = valid_g05()
        valid["retained_flat_power"]["pooled_median_q_flat"] = 1.0
        self.assertTrue(core.evaluate_guard("G05-quality-qualified", valid).passed)
        valid["retained_flat_power"]["pooled_median_q_flat"] = 1.000001
        self.assertFalse(core.evaluate_guard("G05-quality-qualified", valid).passed)

    def test_g05_requires_full_retained_m4_population_and_transfer(self) -> None:
        invalid = valid_g05()
        invalid["retained_flat_power"]["population_counts"]["foam"] = 82
        self.assertFalse(core.evaluate_guard("G05-quality-qualified", invalid).passed)
        invalid = valid_g05()
        invalid["retained_flat_power"]["gain_min"] = 0.994999
        self.assertFalse(core.evaluate_guard("G05-quality-qualified", invalid).passed)
        invalid = valid_g05()
        invalid["retained_flat_power"]["residual_max"] = 0.005001
        self.assertFalse(core.evaluate_guard("G05-quality-qualified", invalid).passed)

    def test_g05_does_not_require_disclosure_axes(self) -> None:
        valid = valid_g05()
        self.assertEqual(core.REQUIRED_QUALITY_GATES, ("M1", "M2", "M3", "M8"))
        self.assertEqual(
            set(valid["quality_gates"]),
            set(core.REQUIRED_QUALITY_GATES),
        )
        self.assertTrue(core.evaluate_guard("G05-quality-qualified", valid).passed)

    def test_g05_rejects_quality_evidence_from_different_output(self) -> None:
        invalid = valid_g05()
        invalid["evidence_output_sha256"]["M8"] = HASH_B
        self.assert_guard("G05-quality-qualified", valid_g05(), invalid)

    def test_g06_common_input_identity(self) -> None:
        invalid = valid_g06()
        invalid["modes"][1]["ordered_input_sha256"] = HASH_A
        self.assert_guard("G06-common-input-identity", valid_g06(), invalid)

    def test_g07_native_prefix(self) -> None:
        invalid = valid_g07()
        invalid["ordered_names"][0], invalid["ordered_names"][1] = (
            invalid["ordered_names"][1],
            invalid["ordered_names"][0],
        )
        self.assert_guard("G07-native-prefix", valid_g07(), invalid)

    def test_g08_settings_fingerprint(self) -> None:
        invalid = valid_g08()
        invalid["timed"]["settings_sha256"] = HASH_A
        self.assert_guard("G08-settings-fingerprint", valid_g08(), invalid)

    def test_g08_rejects_quality_from_another_count(self) -> None:
        invalid = valid_g08()
        invalid["qualified"]["count"] = 33
        self.assert_guard("G08-settings-fingerprint", valid_g08(), invalid)

    def test_g09_process_tree_drained(self) -> None:
        invalid = valid_g09()
        invalid["active_processes_final"] = 1
        self.assert_guard("G09-process-tree-drained", valid_g09(), invalid)

    def test_g09_rejects_process_tree_sampling_gap(self) -> None:
        invalid = valid_g09()
        invalid["max_gap_ms"] = 19.0
        self.assert_guard("G09-process-tree-drained", valid_g09(), invalid)

    def test_g10_deliverable_finalized(self) -> None:
        invalid = valid_g10()
        invalid["manifest_flush_succeeded"] = False
        self.assert_guard("G10-deliverable-finalized", valid_g10(), invalid)

    def test_g11_telemetry_complete(self) -> None:
        invalid = valid_g11()
        invalid["gpu_utilization_percent"] = []
        self.assert_guard("G11-telemetry-complete", valid_g11(), invalid)

    def test_g11_external_busy_does_not_subtract_observer_cpu(self) -> None:
        invalid = valid_g11()
        invalid["external_busy_fraction"] = 0.02
        self.assert_guard("G11-telemetry-complete", valid_g11(), invalid)

    def test_g12_controlled_conditions(self) -> None:
        invalid = valid_g12()
        invalid["external_busy_fraction"] = 0.100001
        self.assert_guard("G12-controlled-conditions", valid_g12(), invalid)
        cold = valid_g12()
        cold["cache_state"] = "COLD_RESET"
        self.assertFalse(core.evaluate_guard("G12-controlled-conditions", cold).passed)
        cold["input_preflight_io"] = "WINDOWS_NO_BUFFERING"
        cold["executable_preflight_io"] = "WINDOWS_NO_BUFFERING"
        self.assertTrue(core.evaluate_guard("G12-controlled-conditions", cold).passed)

    def test_g13_schedule_complete(self) -> None:
        invalid = valid_g13()
        invalid["records"].pop()
        self.assert_guard("G13-schedule-complete", valid_g13(), invalid)

    def test_g14_statistic_direction(self) -> None:
        invalid = valid_g14()
        invalid["strehl_throughput_ratio"] = 0.5
        self.assert_guard("G14-statistic-direction", valid_g14(), invalid)

    def test_g15_cold_receipt(self) -> None:
        invalid = valid_g15()
        invalid["previously_used_boot_ids"] = ["4242"]
        self.assert_guard("G15-cold-receipt", valid_g15(), invalid)

    def test_g15_rejects_equivalent_cache_reset(self) -> None:
        invalid = valid_g15()
        invalid["receipt"]["method"] = "MACHINE_WIDE_CACHE_RESET"
        self.assertFalse(core.evaluate_guard("G15-cold-receipt", invalid).passed)

    def test_g16_live_epoch(self) -> None:
        invalid = valid_g16()
        invalid["latency_seconds"] = 1.0
        self.assert_guard("G16-live-epoch", valid_g16(), invalid)

    def test_g17_m12_joint(self) -> None:
        invalid = valid_g17()
        invalid["m11"]["verdict"] = "UNMEASURED"
        self.assert_guard("G17-m12-joint", valid_g17(), invalid)

    def test_g18_commissioning_required(self) -> None:
        invalid = valid_g18()
        invalid["commission"]["observed_slowdown_seconds"] = 0.949
        self.assert_guard("G18-commissioning-required", valid_g18(), invalid)
        wrong_sign = valid_g18()
        wrong_sign["commission"]["observed_speedup_seconds"] = 1.0
        self.assertFalse(
            core.evaluate_guard("G18-commissioning-required", wrong_sign).passed
        )

    def test_g19_arm_symmetry(self) -> None:
        invalid = valid_g19()
        invalid["changed_factor_groups"].append("input")
        self.assert_guard("G19-arm-symmetry", valid_g19(), invalid)

    def test_g20_aggregate_reduction(self) -> None:
        invalid = valid_g20()
        invalid["maximum_seconds"] = 8.0
        self.assert_guard("G20-aggregate-reduction", valid_g20(), invalid)


class CoreBehaviorTests(unittest.TestCase):
    def test_registry_has_exactly_the_mutated_guards(self) -> None:
        self.assertEqual(
            sorted(core.GUARD_REGISTRY),
            [
                "G01-owned-output",
                "G02-capture-contract",
                "G03-readonly-snapshot",
                "G04-artifact-binding",
                "G05-quality-qualified",
                "G06-common-input-identity",
                "G07-native-prefix",
                "G08-settings-fingerprint",
                "G09-process-tree-drained",
                "G10-deliverable-finalized",
                "G11-telemetry-complete",
                "G12-controlled-conditions",
                "G13-schedule-complete",
                "G14-statistic-direction",
                "G15-cold-receipt",
                "G16-live-epoch",
                "G17-m12-joint",
                "G18-commissioning-required",
                "G19-arm-symmetry",
                "G20-aggregate-reduction",
            ],
        )

    def test_schedule_has_one_warmup_and_six_alternating_sweeps(self) -> None:
        rows = core.alternating_schedule(["A", "B", "C"])
        self.assertEqual(len(rows), 21)
        self.assertEqual(
            [row["setting_id"] for row in rows[3:6]],
            ["A", "B", "C"],
        )
        self.assertEqual(
            [row["setting_id"] for row in rows[6:9]],
            ["C", "B", "A"],
        )

    def test_schedule_rejects_duplicate_settings(self) -> None:
        with self.assertRaises(ValueError):
            core.alternating_schedule(["A", "A"])

    def test_single_setting_schedule_still_has_six_repetitions(self) -> None:
        rows = core.alternating_schedule(["live"])
        self.assertEqual(len(rows), 7)
        self.assertEqual([row["repetition"] for row in rows], list(range(7)))

    def test_cold_schedule_has_six_ordered_pairs_without_warmup(self) -> None:
        rows = core.cold_pair_schedule(["A", "B"], repetitions=6)
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(row["phase"] == "scored" for row in rows))
        for index in range(0, len(rows), 2):
            cold, warm = rows[index : index + 2]
            self.assertEqual(
                (cold["pair_member"], warm["pair_member"]), ("cold", "warm")
            )
            self.assertEqual(cold["pair_id"], warm["pair_id"])
            self.assertEqual(cold["setting_id"], warm["setting_id"])

    def test_describe_reports_dispersion_separately_from_minimum(self) -> None:
        result = core.describe([1.0, 2.0, 4.0])
        self.assertEqual(result["minimum"], 1.0)
        self.assertEqual(result["median"], 2.0)
        self.assertEqual(result["range"], 3.0)
        self.assertGreater(result["sample_sd"], 0.0)

    def test_paired_null_interval_covers_zero(self) -> None:
        result = core.paired_mean_interval([-0.01, 0.01, -0.02, 0.02, 0.0, 0.0])
        self.assertTrue(result["covers_no_difference"])

    def test_paired_plant_interval_has_correct_sign(self) -> None:
        result = core.paired_mean_interval([0.079, 0.081, 0.08, 0.082, 0.078, 0.08])
        self.assertGreater(result["lower_seconds"], 0.0)
        self.assertLessEqual(result["lower_seconds"], 0.08)
        self.assertGreaterEqual(result["upper_seconds"], 0.08)

    def test_quality_threshold_boundary_is_inclusive(self) -> None:
        self.assertTrue(
            core.evaluate_guard("G05-quality-qualified", valid_g05()).passed
        )

    def test_statistic_threshold_boundaries_are_exact(self) -> None:
        self.assertTrue(
            core.evaluate_guard("G14-statistic-direction", valid_g14()).passed
        )

    def test_fastest_comparator_tie_breaks_by_product_then_mode(self) -> None:
        payload = valid_g14()
        payload["qualified_comparator_wall_seconds"]["slow"] = list(
            payload["qualified_comparator_wall_seconds"]["fast"]
        )
        payload["comparator_identity"]["slow"] = {
            "product_id": "best-known-source-fork",
            "mode_id": "fork-best-known",
        }
        payload["selected_fastest_comparator"] = "slow"
        self.assertTrue(core.evaluate_guard("G14-statistic-direction", payload).passed)
        payload["selected_fastest_comparator"] = "fast"
        self.assertFalse(core.evaluate_guard("G14-statistic-direction", payload).passed)

    def test_comparative_aggregate_guard_recomputes_capture_and_pool_ratios(
        self,
    ) -> None:
        payload = {
            "statistic_kind": "comparative",
            "capture_minima": {
                "33": {
                    "strehl_minimum_wall_seconds": 1.0,
                    "selected_comparator_minimum_wall_seconds": 2.0,
                },
                "105": {
                    "strehl_minimum_wall_seconds": 2.0,
                    "selected_comparator_minimum_wall_seconds": 4.0,
                },
                "299": {
                    "strehl_minimum_wall_seconds": 3.0,
                    "selected_comparator_minimum_wall_seconds": 6.0,
                },
            },
            "capture_ratios": {"33": 2.0, "105": 2.0, "299": 2.0},
            "pooled_ratio": 2.0,
            "all_bars_pass": True,
        }
        self.assertTrue(core.evaluate_guard("G20-aggregate-reduction", payload).passed)
        payload["pooled_ratio"] = 1.999
        self.assertFalse(core.evaluate_guard("G20-aggregate-reduction", payload).passed)

    def test_cold_aggregate_guard_uses_each_paired_difference(self) -> None:
        payload = {
            "statistic_kind": "cold",
            "cold_wall_seconds": [22.0, 24.0, 26.0, 28.0, 30.0, 41.0],
            "warm_wall_seconds": [2.0, 4.0, 6.0, 8.0, 10.0, 20.0],
            "paired_cold_minus_warm_seconds": [20.0] * 5 + [21.0],
            "maximum_seconds": 21.0,
            "all_pairs_pass": False,
        }
        self.assertTrue(core.evaluate_guard("G20-aggregate-reduction", payload).passed)
        payload["all_pairs_pass"] = True
        self.assertFalse(core.evaluate_guard("G20-aggregate-reduction", payload).passed)

    def test_live_aggregate_guard_uses_maximum_of_six(self) -> None:
        payload = valid_g20()
        self.assertTrue(core.evaluate_guard("G20-aggregate-reduction", payload).passed)
        payload["latency_seconds"][-1] = 10.001
        payload["maximum_seconds"] = 10.001
        payload["all_replays_pass"] = True
        self.assertFalse(core.evaluate_guard("G20-aggregate-reduction", payload).passed)

    def test_nan_cannot_pass_numeric_guards(self) -> None:
        invalid = valid_g12()
        invalid["external_busy_fraction"] = math.nan
        self.assertFalse(
            core.evaluate_guard("G12-controlled-conditions", invalid).passed
        )

    def test_formal_telemetry_requires_full_interval_coverage(self) -> None:
        payload = valid_g11()
        payload.update(
            {
                "wall_seconds": 0.1,
                "qpc_frequency": 1_000,
                "started_qpc_ticks": 100,
                "finalized_qpc_ticks": 200,
                "synthetic_telemetry": False,
                "busy_fraction": 0.2,
                "external_busy_fraction": 0.3,
            }
        )
        samples = [
            {
                "qpc_ticks": tick,
                "qpc_frequency": 1_000,
                "idle_100ns": tick,
                "kernel_100ns": tick,
                "user_100ns": tick,
            }
            for tick in range(100, 201, 10)
        ]
        payload["cpu_samples"] = samples
        payload["sample_count"] = len(samples)
        payload["hardware_samples"] = [
            {
                "qpc_ticks": tick,
                "qpc_frequency": 1_000,
                "thermal_c": 60.0,
                "hardware_throttle": False,
                "gpu_processes": [],
            }
            for tick in range(100, 201, 10)
        ]
        payload["gpu_utilization_percent"] = [0.0] * len(samples)
        self.assertTrue(core.evaluate_guard("G11-telemetry-complete", payload).passed)
        payload["hardware_samples"] = payload["hardware_samples"][:-3]
        payload["gpu_utilization_percent"] = payload["gpu_utilization_percent"][:-3]
        self.assertFalse(core.evaluate_guard("G11-telemetry-complete", payload).passed)

    def test_formal_telemetry_rejects_one_missing_interior_sample(self) -> None:
        payload = valid_g11()
        payload.update(
            {
                "wall_seconds": 0.1,
                "qpc_frequency": 1_000,
                "started_qpc_ticks": 100,
                "finalized_qpc_ticks": 200,
                "synthetic_telemetry": False,
                "busy_fraction": 0.2,
                "external_busy_fraction": 0.3,
            }
        )
        cpu_samples = [
            {
                "qpc_ticks": tick,
                "qpc_frequency": 1_000,
                "idle_100ns": tick,
                "kernel_100ns": tick,
                "user_100ns": tick,
            }
            for tick in range(100, 201, 10)
            if tick != 150
        ]
        hardware_samples = [
            {
                "qpc_ticks": sample["qpc_ticks"],
                "qpc_frequency": 1_000,
                "thermal_c": 60.0,
                "hardware_throttle": False,
                "gpu_processes": [],
            }
            for sample in cpu_samples
        ]
        payload["cpu_samples"] = cpu_samples
        payload["sample_count"] = len(cpu_samples)
        payload["hardware_samples"] = hardware_samples
        payload["gpu_utilization_percent"] = [0.0] * len(hardware_samples)
        self.assertFalse(core.evaluate_guard("G11-telemetry-complete", payload).passed)

    def test_unknown_guard_is_a_hard_error(self) -> None:
        with self.assertRaises(KeyError):
            core.evaluate_guard("G99-not-real", {})

    def test_native_prefix_is_case_normalized(self) -> None:
        value = valid_g07()
        value["ordered_names"] = [name.lower() for name in value["ordered_names"]]
        self.assertTrue(core.evaluate_guard("G07-native-prefix", value).passed)

    def test_object_hash_is_key_order_independent(self) -> None:
        self.assertEqual(
            core.object_sha256({"a": 1, "b": 2}),
            core.object_sha256({"b": 2, "a": 1}),
        )


if __name__ == "__main__":
    unittest.main()
