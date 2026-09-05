"""Focused unit tests for the M171 fail-closed admission evaluator."""

from __future__ import annotations

import base64
import builtins
import copy
import contextlib
import hashlib
import io
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

import numpy as np

import admission
import commission
import synthetic
import verify as independent_verify


HERE = pathlib.Path(__file__).resolve().parent
with (HERE / "contract.json").open("r", encoding="utf-8") as _stream:
    CONTRACT = json.load(_stream)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _complex_json(values: np.ndarray) -> list:
    array = np.asarray(values, dtype=np.complex128)
    return np.stack((array.real, array.imag), axis=-1).tolist()


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _embedded_case_record(payload: bytes, case: str = "baseline") -> dict:
    compressed = commission._deterministic_gzip(payload)
    payload_sha256 = hashlib.sha256(payload).hexdigest().upper()
    return {
        "case": case,
        "claim_scope": CONTRACT["claim_scope"],
        "evidence_sha256": payload_sha256,
        "embedded_evidence": {
            "schema": independent_verify.EMBEDDED_EVIDENCE_SCHEMA,
            "encoding": "base64",
            "compression": "gzip",
            "compression_level": 9,
            "gzip_mtime": 0,
            "identity": {
                "case": case,
                "evidence_schema": CONTRACT["schemas"]["evidence"],
                "claim_scope": CONTRACT["claim_scope"],
            },
            "uncompressed_length_bytes": len(payload),
            "uncompressed_sha256": payload_sha256,
            "compressed_length_bytes": len(compressed),
            "compressed_sha256": hashlib.sha256(compressed)
            .hexdigest()
            .upper(),
            "payload": base64.b64encode(compressed).decode("ascii"),
        },
    }


def _complex_normal(
    rng: np.random.Generator, shape: tuple[int, ...], sigma: float = 1.0
) -> np.ndarray:
    return (
        sigma
        * (rng.normal(size=shape) + 1j * rng.normal(size=shape))
        / np.sqrt(2.0)
    )


def _make_evidence(
    *,
    vector_reference_transfer: tuple[float, float] = (1.5, 1.5),
) -> dict:
    rng = np.random.default_rng(17120260904)
    site_count = int(CONTRACT["sample_contract"]["site_count"])
    sites = []
    for session in range(4):
        for burst in range(2):
            for site in range(8):
                sites.append(
                    {
                        "site_id": f"site-{session}-{burst}-{site}",
                        "session_id": f"session-{session}",
                        "burst_id": f"burst-{session}-{burst}",
                    }
                )
    assert len(sites) == site_count

    lineage_names = (
        "evidence_generation_sha256",
        "claim_scope_sha256",
        "sampling_sha256",
        "focus_known_input_sha256",
        "raw_response_known_input_sha256",
        "split_sha256",
        "geometry_sha256",
        "resampler_sha256",
        "nonperiodic_sha256",
        "featureless_control_sha256",
        "flat_control_sha256",
        "dark_control_sha256",
        "R1_source_sha256",
        "R2_source_sha256",
        "S1_source_sha256",
        "S2_source_sha256",
        "R1_calibration_sha256",
        "R2_calibration_sha256",
        "S1_calibration_sha256",
        "S2_calibration_sha256",
    )
    lineage = {name: _hash(f"m171:{name}") for name in lineage_names}

    cells = []
    focus_gains = np.asarray([0.7, 1.0, 1.5, 1.0, 0.7])
    for cell_definition in CONTRACT["cells"]:
        dimension = int(cell_definition["dimension"])
        latent = _complex_normal(rng, (site_count, dimension))
        if dimension == 2:
            reference_transfer = np.asarray(vector_reference_transfer)
        else:
            reference_transfer = np.asarray([1.5])
        scored_transfer = np.full(dimension, 0.8)
        coefficients = {
            "R1": latent * reference_transfer
            + _complex_normal(rng, latent.shape, 0.04),
            "R2": latent * reference_transfer
            + _complex_normal(rng, latent.shape, 0.04),
            "S1": latent * scored_transfer
            + _complex_normal(rng, latent.shape, 0.22),
            "S2": latent * scored_transfer
            + _complex_normal(rng, latent.shape, 0.22),
        }
        controls = {}
        for control_name in ("featureless", "flat", "dark"):
            controls[control_name] = {
                path_name: _complex_json(
                    _complex_normal(rng, (site_count, dimension), 0.003)
                )
                for path_name in ("R1", "R2", "S1", "S2")
            }

        transfer = np.empty(
            (site_count, 5, dimension, dimension), dtype=np.complex128
        )
        for site_index in range(site_count):
            for focus_index, gain in enumerate(focus_gains):
                matrix = np.eye(dimension, dtype=np.complex128) * (
                    gain + 0.002 * rng.normal()
                )
                if dimension == 2:
                    matrix[0, 1] = 0.001 * rng.normal()
                    matrix[1, 0] = 0.001 * rng.normal()
                transfer[site_index, focus_index] = matrix

        split_pairs = {}
        for split_name in (
            "odd_even",
            "contiguous_halves",
            "alternating_four_frame_blocks",
        ):
            first = latent + _complex_normal(rng, latent.shape, 0.01)
            second = (
                1.01
                * np.exp(0.01j)
                * latent
                + _complex_normal(rng, latent.shape, 0.01)
            )
            split_controls = {}
            for control_name in ("featureless", "flat", "dark"):
                split_controls[control_name] = {
                    "first": _complex_json(
                        _complex_normal(rng, (site_count, dimension), 0.003)
                    ),
                    "second": _complex_json(
                        _complex_normal(rng, (site_count, dimension), 0.003)
                    ),
                }
            split_pairs[split_name] = {
                "first": _complex_json(first),
                "second": _complex_json(second),
                "controls": split_controls,
            }

        kernel_a = latent + _complex_normal(rng, latent.shape, 0.01)
        cells.append(
            {
                "id": cell_definition["id"],
                "frequency": cell_definition["frequency"],
                "orientation": cell_definition["orientation"],
                "dimension": dimension,
                "coefficients": {
                    name: _complex_json(value)
                    for name, value in coefficients.items()
                },
                "controls": controls,
                "focus": {
                    "known_input": True,
                    "positions": [-2.0, -1.0, 0.0, 1.0, 2.0],
                    "transfer": _complex_json(transfer),
                    "cross_cell_leakage": [0.01] * site_count,
                },
                "split_pairs": split_pairs,
                "resampler": {
                    "kernel_a": _complex_json(kernel_a),
                    "kernel_b": _complex_json(1.005 * kernel_a),
                },
            }
        )

    levels = np.linspace(0.0, 1.0, 33)
    return {
        "schema": "m171-reference-admission-evidence-v1",
        "claim_scope": "GX_REFERENCE_CONDITIONAL",
        "sites": sites,
        "lineage": lineage,
        "reductions": {
            path_name: {
                "complete": True,
                "candidate_blind": True,
                "linear": True,
                "source_sha256": lineage[f"{path_name}_source_sha256"],
                "calibration_sha256": lineage[
                    f"{path_name}_calibration_sha256"
                ],
                "reduction_sha256": _hash(f"m171:{path_name}:reduction"),
            }
            for path_name in ("S1", "S2")
        },
        "sampling": {
            "input_only": True,
            "reference_magnification": (
                2.30 + rng.normal(0.0, 0.015, site_count)
            ).tolist(),
            "scored_magnification": [1.0] * site_count,
        },
        "cells": cells,
        "raw_response": {
            "known_input": True,
            "input_levels": levels.tolist(),
            "output_levels": (0.1 + 2.0 * levels).tolist(),
            "low_rail_hits": 0,
            "high_rail_hits": 0,
        },
        "geometry": {
            "input_only": True,
            "scored_pixels_native": True,
            "reference_only_resampling": True,
            "scale_disagreement_percent": rng.normal(
                0.0, 0.01, site_count
            ).tolist(),
            "rotation_disagreement_deg": rng.normal(
                0.0, 0.002, site_count
            ).tolist(),
            "nontranslation_rms_native_px": np.abs(
                rng.normal(0.03, 0.005, site_count)
            ).tolist(),
            "planted_transform_sign": [1] * site_count,
            "estimated_transform_sign": [1] * site_count,
        },
        "nonperiodic": {
            "concealed": True,
            "lineage_sha256": lineage["nonperiodic_sha256"],
            "site_ids": [site["site_id"] for site in sites],
        },
    }


def _gate(result: dict, gate_id: str) -> dict:
    return next(gate for gate in result["gates"] if gate["id"] == gate_id)


class _CountingBytesIO(io.BytesIO):
    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.read_count = 0

    def read(self, *args, **kwargs) -> bytes:
        self.read_count += 1
        return super().read(*args, **kwargs)


class SealedInputTests(unittest.TestCase):
    def test_read_once_hashes_and_parses_the_same_bytes(self) -> None:
        payload = b'{"value": 17}'
        stream = _CountingBytesIO(payload)
        expected = hashlib.sha256(payload).hexdigest()
        with mock.patch.object(builtins, "open", return_value=stream) as opener:
            loaded = admission.load_sealed_json("sealed.json", expected)
        self.assertEqual(loaded["value"], 17)
        self.assertEqual(opener.call_count, 1)
        self.assertEqual(stream.read_count, 1)
        self.assertEqual(loaded.sealed_bytes, payload)
        self.assertEqual(loaded.sealed_sha256, expected.upper())
        with self.assertRaises(AttributeError):
            loaded.sealed_bytes = b"mutated"

    def test_hash_mismatch_is_harness_error(self) -> None:
        payload = b'{"value": 17}'
        stream = _CountingBytesIO(payload)
        with mock.patch.object(builtins, "open", return_value=stream):
            with self.assertRaisesRegex(admission.HarnessError, "mismatch"):
                admission.load_sealed_json("sealed.json", "0" * 64)
        self.assertEqual(stream.read_count, 1)

    def test_json_nan_is_rejected(self) -> None:
        payload = b'{"value": NaN}'
        expected = hashlib.sha256(payload).hexdigest()
        stream = _CountingBytesIO(payload)
        with mock.patch.object(builtins, "open", return_value=stream):
            with self.assertRaisesRegex(admission.HarnessError, "non-finite"):
                admission.load_sealed_json("sealed.json", expected)

    def test_cli_maps_harness_error_to_exit_code_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_path = pathlib.Path(directory) / "evidence.json"
            evidence_path.write_bytes(b"{}")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = admission.main(
                    [str(evidence_path), "0" * 64, "--contract", str(HERE / "contract.json")]
                )
        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "HARNESS_ERROR")


class AmendmentThreeIntegrityTests(unittest.TestCase):
    def test_v4_contract_and_source_hash_bindings(self) -> None:
        contract_payload = (HERE / "contract.json").read_bytes()
        self.assertEqual(
            hashlib.sha256(contract_payload).hexdigest().upper(),
            admission.FROZEN_CONTRACT_SHA256,
        )
        self.assertEqual(
            admission.FROZEN_CONTRACT_SHA256,
            independent_verify.FROZEN_CONTRACT_SHA256,
        )
        self.assertEqual(
            CONTRACT["schema"],
            "m171-reference-admission-contract-v4",
        )
        self.assertEqual(
            CONTRACT["schemas"],
            {
                "evidence": "m171-reference-admission-evidence-v1",
                "result": "m171-reference-admission-result-v4",
                "commission": "m171-reference-admission-commission-v4",
                "verification": "m171-reference-admission-verification-v4",
            },
        )
        expected_sources = {
            "admission.py": (
                independent_verify.FROZEN_ADMISSION_SOURCE_SHA256
            ),
            "commission.py": (
                independent_verify.FROZEN_COMMISSION_SOURCE_SHA256
            ),
            "synthetic.py": (
                independent_verify.FROZEN_SYNTHETIC_SOURCE_SHA256
            ),
        }
        for name, expected in expected_sources.items():
            with self.subTest(source=name):
                self.assertEqual(
                    hashlib.sha256((HERE / name).read_bytes())
                    .hexdigest()
                    .upper(),
                    expected,
                )

    def test_experiment_text_bytes_are_lf_without_bom(self) -> None:
        paths = (
            HERE / ".gitattributes",
            HERE / "PREREGISTRATION.md",
            HERE / "admission.py",
            HERE / "commission.py",
            HERE / "synthetic.py",
            HERE / "test_admission.py",
            HERE / "verify.py",
            HERE / "contract.json",
            HERE / "out" / "commission.json",
            HERE / "out" / "verification.json",
        )
        for path in paths:
            with self.subTest(path=path.name):
                payload = path.read_bytes()
                self.assertFalse(payload.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", payload)
                payload.decode("utf-8")

    def test_lane_attributes_force_lf_for_every_experiment_text(self) -> None:
        repository = HERE.parents[1]
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "check-attr",
                "-z",
                "text",
                "eol",
                "--",
                *independent_verify.ATTRIBUTE_PATHS,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr.decode("utf-8", errors="replace"),
        )
        fields = completed.stdout.split(b"\0")
        if fields and fields[-1] == b"":
            fields.pop()
        self.assertEqual(len(fields) % 3, 0)
        observed = {}
        for index in range(0, len(fields), 3):
            path = fields[index].decode("utf-8")
            attribute = fields[index + 1].decode("ascii")
            value = fields[index + 2].decode("ascii")
            observed.setdefault(path, {})[attribute] = value
        self.assertEqual(set(observed), set(independent_verify.ATTRIBUTE_PATHS))
        for path in independent_verify.ATTRIBUTE_PATHS:
            with self.subTest(path=path):
                self.assertEqual(
                    observed[path],
                    {"text": "set", "eol": "lf"},
                )

    def test_crlf_transcoded_contract_fails_raw_sha(self) -> None:
        contract_path = HERE / "contract.json"
        payload = contract_path.read_bytes()
        loaded = admission.load_sealed_json(
            contract_path,
            admission.FROZEN_CONTRACT_SHA256,
        )
        self.assertEqual(
            loaded["schema"],
            "m171-reference-admission-contract-v4",
        )
        with tempfile.TemporaryDirectory() as directory:
            transcoded = pathlib.Path(directory) / "contract.json"
            transcoded.write_bytes(payload.replace(b"\n", b"\r\n"))
            with self.assertRaisesRegex(admission.HarnessError, "mismatch"):
                admission.load_sealed_json(
                    transcoded,
                    admission.FROZEN_CONTRACT_SHA256,
                )

    def test_crlf_transcoded_commission_fails_raw_sha(self) -> None:
        artifact_path = HERE / "out" / "commission.json"
        payload = artifact_path.read_bytes()
        expected = hashlib.sha256(payload).hexdigest().upper()
        loaded, retained, actual = (
            independent_verify._read_sealed_json_once(
                artifact_path,
                expected,
                "commission test artifact",
            )
        )
        self.assertEqual(
            loaded["schema"],
            "m171-reference-admission-commission-v4",
        )
        self.assertEqual(retained, payload)
        self.assertEqual(actual, expected)
        with tempfile.TemporaryDirectory() as directory:
            transcoded = pathlib.Path(directory) / "commission.json"
            transcoded.write_bytes(payload.replace(b"\n", b"\r\n"))
            with self.assertRaisesRegex(
                independent_verify.HarnessError,
                "SHA-256 mismatch",
            ):
                independent_verify._read_sealed_json_once(
                    transcoded,
                    expected,
                    "commission test artifact",
                )


class OutputProtectionTests(unittest.TestCase):
    @staticmethod
    def _sha256(path: pathlib.Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @classmethod
    def _lane_targets(cls) -> tuple[pathlib.Path, ...]:
        return tuple(
            (HERE / relative).resolve(strict=False)
            for relative in synthetic._PROTECTED_OUTPUT_RELATIVE_PATHS
        )

    @classmethod
    def _snapshot(cls) -> dict[pathlib.Path, str]:
        return {
            path: cls._sha256(path) for path in cls._lane_targets()
        }

    def _assert_snapshot(self, expected: dict[pathlib.Path, str]) -> None:
        self.assertEqual(self._snapshot(), expected)

    @staticmethod
    def _short_alias(path: pathlib.Path) -> str | None:
        if os.name != "nt":
            return None
        import ctypes

        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(
            os.fspath(path),
            buffer,
            len(buffer),
        )
        if length == 0 or length >= len(buffer):
            return None
        value = buffer.value
        return value if value.casefold() != os.fspath(path).casefold() else None

    @classmethod
    def _aliases(cls, path: pathlib.Path) -> list[tuple[str, str]]:
        resolved = path.resolve(strict=False)
        relative_parent = os.path.relpath(
            resolved.parent, pathlib.Path.cwd()
        )
        aliases = [
            ("direct", os.fspath(resolved)),
            (
                "relative",
                os.path.join(
                    relative_parent,
                    "_nonexistent_alias_parent",
                    "..",
                    resolved.name,
                ),
            ),
        ]
        if os.name == "nt":
            aliases.extend(
                (
                    ("case", os.fspath(resolved).swapcase()),
                    ("extended", "\\\\?\\" + os.fspath(resolved)),
                    ("trailing-dot", os.fspath(resolved) + "."),
                    ("trailing-space", os.fspath(resolved) + " "),
                )
            )
            short = cls._short_alias(resolved)
            if short is not None:
                aliases.append(("8.3", short))
        return aliases

    def _assert_generator_refused(self, output_path: str) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(
                synthetic,
                "build_evidence",
            ) as generator,
            mock.patch.object(
                synthetic, "write_sealed_evidence"
            ) as writer,
            contextlib.redirect_stdout(output),
        ):
            exit_code = synthetic.main(
                [
                    "--contract",
                    os.fspath(HERE / "contract.json"),
                    "--case",
                    "baseline",
                    "--output",
                    output_path,
                ]
            )
        self.assertEqual(exit_code, 2)
        generator.assert_not_called()
        writer.assert_not_called()
        self.assertEqual(
            json.loads(output.getvalue())["status"],
            "HARNESS_ERROR",
        )

    def _assert_commissioner_refused(self, output_path: str) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(commission, "commission") as campaign,
            mock.patch.object(
                commission, "_write_output"
            ) as writer,
            contextlib.redirect_stdout(output),
        ):
            exit_code = commission.main(
                [
                    "--contract",
                    os.fspath(HERE / "contract.json"),
                    "--output",
                    output_path,
                ]
            )
        self.assertEqual(exit_code, 2)
        campaign.assert_not_called()
        writer.assert_not_called()
        self.assertEqual(
            json.loads(output.getvalue())["status"],
            "HARNESS_ERROR",
        )

    def _assert_verifier_refused(self, output_path: str) -> None:
        error = io.StringIO()
        with (
            mock.patch.object(
                independent_verify, "verify"
            ) as verifier,
            mock.patch.object(
                independent_verify, "_write_json"
            ) as writer,
            contextlib.redirect_stderr(error),
        ):
            exit_code = independent_verify.main(
                [
                    "--contract",
                    os.fspath(HERE / "contract.json"),
                    "--commission",
                    os.fspath(HERE / "out" / "commission.json"),
                    "--expected-commission-sha256",
                    "0" * 64,
                    "--output",
                    output_path,
                ]
            )
        self.assertEqual(exit_code, 2)
        verifier.assert_not_called()
        writer.assert_not_called()
        self.assertEqual(
            json.loads(error.getvalue())["status"],
            "HARNESS_ERROR",
        )

    def test_protected_sets_cover_all_sources_and_active_inputs(
        self,
    ) -> None:
        frozen_and_source = {
            ".gitattributes",
            "PREREGISTRATION.md",
            "contract.json",
            "admission.py",
            "synthetic.py",
            "commission.py",
            "test_admission.py",
            "verify.py",
        }
        self.assertEqual(
            set(synthetic._PROTECTED_OUTPUT_RELATIVE_PATHS),
            frozen_and_source
            | {"out/commission.json", "out/verification.json"},
        )
        self.assertEqual(
            set(commission._PROTECTED_OUTPUT_RELATIVE_PATHS),
            frozen_and_source | {"out/verification.json"},
        )
        self.assertEqual(
            set(independent_verify._PROTECTED_OUTPUT_RELATIVE_PATHS),
            frozen_and_source | {"out/commission.json"},
        )

    def test_generator_refuses_all_protected_alias_spellings_before_work(
        self,
    ) -> None:
        before = self._snapshot()
        for target in self._lane_targets():
            for alias_name, alias in self._aliases(target):
                with self.subTest(target=target.name, alias=alias_name):
                    self._assert_generator_refused(alias)
        self._assert_snapshot(before)

    def test_commissioner_refuses_all_protected_alias_spellings_before_work(
        self,
    ) -> None:
        before = self._snapshot()
        targets = (
            (commission.HERE / relative).resolve(strict=False)
            for relative in commission._PROTECTED_OUTPUT_RELATIVE_PATHS
        )
        for target in targets:
            for alias_name, alias in self._aliases(target):
                with self.subTest(target=target.name, alias=alias_name):
                    self._assert_commissioner_refused(alias)
        self._assert_snapshot(before)

    def test_verifier_refuses_all_protected_alias_spellings_before_work(
        self,
    ) -> None:
        before = self._snapshot()
        contract_path = (HERE / "contract.json").resolve(strict=False)
        commission_path = (
            HERE / "out" / "commission.json"
        ).resolve(strict=False)
        targets = {
            path.resolve(strict=False)
            for path, _ in independent_verify._protected_output_paths(
                contract_path,
                commission_path,
            )
        }
        for target in sorted(targets):
            for alias_name, alias in self._aliases(target):
                with self.subTest(target=target.name, alias=alias_name):
                    self._assert_verifier_refused(alias)
        self._assert_snapshot(before)

    def test_samefile_hardlink_aliases_refuse_before_work(self) -> None:
        before = self._snapshot()
        with tempfile.TemporaryDirectory() as directory:
            alias = pathlib.Path(directory) / "admission-hardlink.py"
            os.link(HERE / "admission.py", alias)
            self.assertNotEqual(
                synthetic._path_key(alias),
                synthetic._path_key(HERE / "admission.py"),
            )
            self.assertTrue(
                os.path.samefile(alias, HERE / "admission.py")
            )
            self._assert_generator_refused(os.fspath(alias))
            self._assert_commissioner_refused(os.fspath(alias))
            self._assert_verifier_refused(os.fspath(alias))
        self._assert_snapshot(before)

    def test_junction_or_symlink_aliases_refuse_before_work(self) -> None:
        before = self._snapshot()
        with tempfile.TemporaryDirectory() as directory:
            alias_root = pathlib.Path(directory) / "lane-alias"
            if os.name == "nt":
                completed = subprocess.run(
                    [
                        "cmd",
                        "/d",
                        "/c",
                        "mklink",
                        "/J",
                        os.fspath(alias_root),
                        os.fspath(HERE),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if completed.returncode != 0:
                    self.skipTest("directory junctions are not supported")
            else:
                try:
                    alias_root.symlink_to(HERE, target_is_directory=True)
                except OSError:
                    self.skipTest("directory symlinks are not supported")
            alias = alias_root / "admission.py"
            self.assertTrue(
                os.path.samefile(alias, HERE / "admission.py")
            )
            original_samefile = os.path.samefile
            with mock.patch.object(
                os.path, "samefile", wraps=original_samefile
            ) as samefile:
                self._assert_generator_refused(os.fspath(alias))
                self._assert_commissioner_refused(os.fspath(alias))
                self._assert_verifier_refused(os.fspath(alias))
            self.assertGreater(samefile.call_count, 0)
        self._assert_snapshot(before)

    def test_prefix_fallback_and_identity_errors_fail_closed(self) -> None:
        before = self._snapshot()
        modules_and_errors = (
            (synthetic, synthetic.SyntheticError),
            (commission, admission.HarnessError),
            (independent_verify, independent_verify.HarnessError),
        )
        if os.name == "nt":
            plain_unc = r"\\server\share\protected.json"
            extended_unc = (
                r"\\?\UNC\server\share\folder\..\protected.json"
            )
            for module, _ in modules_and_errors:
                with self.subTest(module=module.__name__, alias="UNC"):
                    self.assertEqual(
                        module._path_key(extended_unc),
                        module._path_key(plain_unc),
                    )
        target = (HERE / "admission.py").resolve(strict=False)
        extended = (
            "\\\\?\\" + os.fspath(target)
            if os.name == "nt"
            else os.fspath(target)
        )
        with tempfile.TemporaryDirectory() as directory:
            hardlink = pathlib.Path(directory) / "admission-hardlink.py"
            os.link(target, hardlink)
            for module, error_type in modules_and_errors:
                with self.subTest(
                    module=module.__name__, alias="samefile-error"
                ):
                    with mock.patch.object(
                        os.path,
                        "samefile",
                        side_effect=OSError("identity probe"),
                    ):
                        self.assertTrue(
                            module._paths_identical(extended, target)
                        )
                        with self.assertRaises(error_type):
                            module._paths_identical(hardlink, target)
        self._assert_snapshot(before)

    def test_mutated_generator_directory_allows_evidence_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            script = root / "synthetic.py"
            script.write_bytes((HERE / "synthetic.py").read_bytes())
            output_path = root / "evidence.json"
            with mock.patch.object(synthetic, "__file__", os.fspath(script)):
                resolved = synthetic._safe_evidence_output(
                    output_path,
                    HERE / "contract.json",
                )
            self.assertEqual(
                resolved,
                output_path.resolve(strict=False),
            )

    def test_generator_allows_external_temporary_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_path = pathlib.Path(directory) / "evidence.json"
            output = io.StringIO()
            with (
                mock.patch.object(
                    synthetic,
                    "build_evidence",
                    return_value={},
                ),
                contextlib.redirect_stdout(output),
            ):
                exit_code = synthetic.main(
                    [
                        "--contract",
                        os.fspath(HERE / "contract.json"),
                        "--case",
                        "baseline",
                        "--output",
                        os.fspath(output_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(output_path.read_bytes(), b"{}\n")
            seal = json.loads(output.getvalue())
            self.assertEqual(seal["schema"], synthetic.SEAL_SCHEMA)
            self.assertEqual(seal["capture_reads"], 0)

    def test_commissioner_allows_active_and_external_outputs(self) -> None:
        commissioned = {
            "schema": CONTRACT["schemas"]["commission"],
            "status": "COMMISSIONED",
        }
        active_output = HERE / "out" / "commission.json"
        with (
            mock.patch.object(
                commission,
                "commission",
                return_value=commissioned,
            ),
            mock.patch.object(commission, "_write_output") as writer,
        ):
            exit_code = commission.main(
                [
                    "--contract",
                    os.fspath(HERE / "contract.json"),
                    "--output",
                    os.fspath(active_output),
                ]
            )
        self.assertEqual(exit_code, 0)
        writer.assert_called_once()
        with tempfile.TemporaryDirectory() as directory:
            external = pathlib.Path(directory) / "commission.json"
            with (
                mock.patch.object(
                    commission,
                    "commission",
                    return_value=commissioned,
                ),
                mock.patch.object(
                    commission,
                    "_write_output",
                ) as external_writer,
            ):
                exit_code = commission.main(
                    [
                        "--contract",
                        os.fspath(HERE / "contract.json"),
                        "--output",
                        os.fspath(external),
                    ]
                )
            self.assertEqual(exit_code, 0)
            external_writer.assert_called_once()

    def test_verifier_allows_active_and_external_outputs(self) -> None:
        result = {
            "schema": CONTRACT["schemas"]["verification"],
            "status": "PASS",
        }
        common_arguments = [
            "--contract",
            os.fspath(HERE / "contract.json"),
            "--commission",
            os.fspath(HERE / "out" / "commission.json"),
            "--expected-commission-sha256",
            "0" * 64,
        ]
        active_output = HERE / "out" / "verification.json"
        with (
            mock.patch.object(
                independent_verify,
                "verify",
                return_value=result,
            ),
            mock.patch.object(
                independent_verify,
                "_write_json",
            ) as writer,
        ):
            exit_code = independent_verify.main(
                [
                    *common_arguments,
                    "--output",
                    os.fspath(active_output),
                ]
            )
        self.assertEqual(exit_code, 0)
        writer.assert_called_once()
        with tempfile.TemporaryDirectory() as directory:
            external = pathlib.Path(directory) / "verification.json"
            with (
                mock.patch.object(
                    independent_verify,
                    "verify",
                    return_value=result,
                ),
                mock.patch.object(
                    independent_verify,
                    "_write_json",
                ) as external_writer,
            ):
                exit_code = independent_verify.main(
                    [
                        *common_arguments,
                        "--output",
                        os.fspath(external),
                    ]
                )
            self.assertEqual(exit_code, 0)
            external_writer.assert_called_once()


class SealedEvidenceRetentionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = (
            b'{"claim_scope":"GX_REFERENCE_CONDITIONAL",'
            b'"schema":"m171-reference-admission-evidence-v1"}\n'
        )
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.loaded = admission._SealedJSON(
            {
                "schema": CONTRACT["schemas"]["evidence"],
                "claim_scope": CONTRACT["claim_scope"],
            },
            self.digest,
            self.payload,
        )

    def test_commission_uses_one_public_load_and_same_loaded_object(self) -> None:
        evaluator_result = {"schema": CONTRACT["schemas"]["result"]}
        policy_result = {
            "schema": CONTRACT["schemas"]["result"],
            "profile": "production",
        }
        with (
            mock.patch.object(
                admission,
                "load_sealed_json",
                return_value=self.loaded,
            ) as loader,
            mock.patch.object(
                admission,
                "evaluate_evidence",
                side_effect=(evaluator_result, policy_result),
            ) as evaluator,
        ):
            result, embedded, policy_probe = (
                commission._load_evaluate_and_embed(
                    evidence_path=pathlib.Path("evidence.json"),
                    expected_sha256=self.digest,
                    contract=CONTRACT,
                    case="baseline",
                    production_digital_k_probe=True,
                )
            )
        loader.assert_called_once_with(
            pathlib.Path("evidence.json"), self.digest
        )
        self.assertEqual(evaluator.call_count, 2)
        first_call, policy_call = evaluator.call_args_list
        self.assertIs(first_call.args[0], self.loaded)
        self.assertIs(first_call.args[1], CONTRACT)
        self.assertEqual(
            first_call.kwargs,
            {"profile": "synthetic_commission"},
        )
        self.assertIs(policy_call.args[1], CONTRACT)
        self.assertEqual(policy_call.args[0]["claim_scope"], "DIGITAL_K")
        self.assertEqual(policy_call.kwargs, {"profile": "production"})
        self.assertIs(policy_probe, policy_result)
        self.assertEqual(result["evidence_sha256"], self.digest.upper())
        self.assertEqual(
            embedded["uncompressed_sha256"], self.digest.upper()
        )

    def test_embedding_is_deterministic_and_retains_exact_bytes(self) -> None:
        first = commission._embedded_evidence_record(
            "baseline", self.loaded
        )
        second = commission._embedded_evidence_record(
            "baseline", self.loaded
        )
        self.assertEqual(first, second)
        compressed = base64.b64decode(first["payload"], validate=True)
        self.assertEqual(compressed[4:8], b"\x00\x00\x00\x00")
        self.assertEqual(len(compressed), first["compressed_length_bytes"])
        self.assertEqual(
            hashlib.sha256(compressed).hexdigest().upper(),
            first["compressed_sha256"],
        )
        decompressed = independent_verify._gunzip_embedded(
            compressed,
            first["uncompressed_length_bytes"],
            "baseline",
        )
        self.assertEqual(decompressed, self.payload)

    def test_independent_sealed_reader_reads_once(self) -> None:
        payload = b'{"value":17}'
        stream = _CountingBytesIO(payload)
        expected = hashlib.sha256(payload).hexdigest()
        with mock.patch.object(
            pathlib.Path, "open", return_value=stream
        ) as opener:
            value, retained, digest = (
                independent_verify._read_sealed_json_once(
                    pathlib.Path("sealed.json"),
                    expected,
                    "test seal",
                )
            )
        self.assertEqual(value, {"value": 17})
        self.assertEqual(retained, payload)
        self.assertEqual(digest, expected.upper())
        self.assertEqual(opener.call_count, 1)
        self.assertEqual(stream.read_count, 1)

    def test_verifier_rejects_compressed_payload_tamper(self) -> None:
        case = _embedded_case_record(self.payload)
        compressed = bytearray(
            base64.b64decode(
                case["embedded_evidence"]["payload"], validate=True
            )
        )
        compressed[-9] ^= 1
        case["embedded_evidence"]["payload"] = base64.b64encode(
            compressed
        ).decode("ascii")
        with self.assertRaisesRegex(
            independent_verify.HarnessError,
            "compressed SHA-256 mismatch",
        ):
            independent_verify._decode_embedded_evidence(case, CONTRACT)

    def test_verifier_rejects_duplicate_nonfinite_and_wrong_schema(self) -> None:
        invalid_payloads = (
            (
                b'{"schema":"m171-reference-admission-evidence-v1",'
                b'"schema":"m171-reference-admission-evidence-v1",'
                b'"claim_scope":"GX_REFERENCE_CONDITIONAL"}',
                "duplicate JSON member",
            ),
            (
                b'{"schema":"m171-reference-admission-evidence-v1",'
                b'"claim_scope":"GX_REFERENCE_CONDITIONAL","value":NaN}',
                "non-finite JSON number",
            ),
            (
                b'{"schema":"m171-reference-admission-evidence-v0",'
                b'"claim_scope":"GX_REFERENCE_CONDITIONAL"}',
                "payload identity is wrong",
            ),
        )
        for payload, message in invalid_payloads:
            with self.subTest(message=message):
                case = _embedded_case_record(payload)
                with self.assertRaisesRegex(
                    independent_verify.HarnessError, message
                ):
                    independent_verify._decode_embedded_evidence(
                        case, CONTRACT
                    )


class SchemaAndProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = _make_evidence()

    def test_wrong_shape_is_harness_error(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        del evidence["cells"][0]["coefficients"]["R1"][-1]
        with self.assertRaisesRegex(admission.HarnessError, "shape"):
            admission.evaluate_evidence(evidence, CONTRACT)

    def test_duplicate_identifier_is_harness_error(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["sites"][1]["site_id"] = evidence["sites"][0]["site_id"]
        with self.assertRaisesRegex(admission.HarnessError, "duplicate site_id"):
            admission.evaluate_evidence(evidence, CONTRACT)

    def test_missing_required_member_is_harness_error(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        del evidence["geometry"]["input_only"]
        with self.assertRaisesRegex(admission.HarnessError, "missing required"):
            admission.evaluate_evidence(evidence, CONTRACT)

    def test_bool_is_not_accepted_as_a_number(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["sampling"]["reference_magnification"][0] = True
        with self.assertRaisesRegex(admission.HarnessError, "not boolean"):
            admission.evaluate_evidence(evidence, CONTRACT)

    def test_wrong_schema_is_harness_error(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["schema"] = "m171-reference-admission-evidence-v0"
        with self.assertRaisesRegex(admission.HarnessError, "unsupported"):
            admission.evaluate_evidence(evidence, CONTRACT)

    def test_production_never_uses_synthetic_defaults(self) -> None:
        result = admission.evaluate_evidence(
            self.evidence, CONTRACT, profile="production"
        )
        self.assertEqual(result["counts"], {"PASS": 0, "UNMEASURED": 8, "total": 8})
        for gate in result["gates"]:
            self.assertEqual(gate["status"], "UNMEASURED")
            self.assertIn(
                "PRODUCTION_CALIBRATION_MANIFEST_ABSENT",
                gate["reason_codes"],
            )
            self.assertFalse(gate["diagnostics"]["synthetic_defaults_used"])

    def test_incomplete_hash_bound_production_manifest_is_unmeasured(self) -> None:
        manifest = {
            "schema": "m171-reference-admission-production-calibration-v1",
            "contract_sha256": admission.FROZEN_CONTRACT_SHA256,
            "production_thresholds": {
                "licensed_cells": [cell["id"] for cell in CONTRACT["cells"]]
            },
        }
        result = admission.evaluate_evidence(
            self.evidence,
            CONTRACT,
            profile="production",
            calibration_manifest=manifest,
            calibration_manifest_sha256=_canonical_hash(manifest),
        )
        self.assertEqual(result["counts"]["UNMEASURED"], 8)
        for gate in result["gates"]:
            self.assertIn(
                "PRODUCTION_CALIBRATION_MANIFEST_INCOMPLETE",
                gate["reason_codes"],
            )


class ScientificGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline_evidence = _make_evidence()
        cls.baseline_result = admission.evaluate_evidence(
            cls.baseline_evidence, CONTRACT
        )

    def test_exact_eight_gate_partition(self) -> None:
        result = self.baseline_result
        self.assertEqual(len(result["gates"]), 8)
        self.assertEqual(
            result["counts"]["PASS"] + result["counts"]["UNMEASURED"], 8
        )
        self.assertEqual(result["counts"]["total"], 8)
        self.assertEqual(
            {gate["status"] for gate in result["gates"]} - {"PASS", "UNMEASURED"},
            set(),
        )
        for gate in result["gates"]:
            self.assertTrue(gate["evaluated"])
            self.assertEqual(gate["reason_codes"] == [], gate["status"] == "PASS")
            self.assertFalse(isinstance(gate["claim_value"], (int, float)))
        self.assertEqual(result["counts"]["PASS"], 8)
        json.dumps(result, allow_nan=False)

    def test_max_t_lower_bound_uses_frozen_direction_and_quantile(self) -> None:
        observed = np.asarray([10.0, 20.0])
        bootstrap = np.asarray(
            [
                [9.0, 19.8],
                [9.5, 19.9],
                [10.2, 20.1],
                [11.5, 20.4],
                [13.0, 22.0],
            ]
        )
        lower, diagnostics = admission._simultaneous_lcb(
            observed, bootstrap
        )
        standard_error = np.std(bootstrap, axis=0, ddof=1)
        studentized = (
            bootstrap - observed[np.newaxis, :]
        ) / standard_error
        expected_critical = float(
            np.quantile(
                np.max(studentized, axis=1),
                0.975,
                method="higher",
            )
        )
        self.assertEqual(
            diagnostics["studentized_numerator"],
            "bootstrap_minus_observed",
        )
        self.assertEqual(diagnostics["quantile_probability"], 0.975)
        self.assertEqual(diagnostics["quantile_method"], "higher")
        self.assertEqual(diagnostics["critical_value"], expected_critical)
        np.testing.assert_allclose(
            lower,
            observed - expected_critical * standard_error,
            rtol=0.0,
            atol=0.0,
        )

    def test_common_mode_upper_uses_distinct_asymmetric_root(self) -> None:
        observed = np.asarray([10.0, 20.0])
        bootstrap = np.asarray(
            [
                [0.0, 19.0],
                [8.0, 19.5],
                [9.0, 19.8],
                [9.5, 20.1],
                [10.1, 20.2],
            ]
        )
        lower, lower_diagnostics = admission._simultaneous_lcb(
            observed,
            bootstrap,
        )
        upper, diagnostics = admission._simultaneous_upper(
            observed,
            bootstrap,
            0.025,
        )
        self.assertIsNotNone(lower)
        self.assertIsNotNone(upper)
        standard_error = np.std(bootstrap, axis=0, ddof=1)
        studentized = (
            observed[np.newaxis, :] - bootstrap
        ) / standard_error
        expected_critical = float(
            np.quantile(
                np.max(studentized, axis=1),
                0.975,
                method="higher",
            )
        )
        self.assertEqual(
            diagnostics["studentized_numerator"],
            "observed_minus_bootstrap",
        )
        self.assertEqual(
            diagnostics["upper_bound"],
            "observed_plus_critical_times_standard_error",
        )
        self.assertEqual(diagnostics["quantile_probability"], 0.975)
        self.assertEqual(diagnostics["quantile_method"], "higher")
        self.assertEqual(diagnostics["critical_value"], expected_critical)
        self.assertGreater(
            diagnostics["critical_value"],
            lower_diagnostics["critical_value"] + 1.0,
        )
        np.testing.assert_allclose(
            upper,
            observed + expected_critical * standard_error,
            rtol=0.0,
            atol=0.0,
        )

    def test_independent_upper_helper_uses_asymmetric_raw_formula(
        self,
    ) -> None:
        observed = np.asarray([10.0, 20.0])
        bootstrap = np.asarray(
            [
                [0.0, 19.0],
                [8.0, 19.5],
                [9.0, 19.8],
                [9.5, 20.1],
                [10.1, 20.2],
            ]
        )
        upper, diagnostics = (
            independent_verify._raw_simultaneous_upper(
                observed,
                bootstrap,
                0.025,
            )
        )
        self.assertIsNotNone(upper)
        standard_error = np.std(bootstrap, axis=0, ddof=1)
        correct_root = (
            observed[np.newaxis, :] - bootstrap
        ) / standard_error
        inverted_root = (
            bootstrap - observed[np.newaxis, :]
        ) / standard_error
        expected_critical = float(
            np.quantile(
                np.max(correct_root, axis=1),
                0.975,
                method="higher",
            )
        )
        inverted_critical = float(
            np.quantile(
                np.max(inverted_root, axis=1),
                0.975,
                method="higher",
            )
        )
        self.assertGreater(expected_critical, inverted_critical + 1.0)
        self.assertEqual(
            diagnostics["studentized_numerator"],
            "observed_minus_bootstrap",
        )
        self.assertEqual(
            diagnostics["upper_bound"],
            "observed_plus_critical_times_standard_error",
        )
        np.testing.assert_allclose(
            upper,
            observed + expected_critical * standard_error,
            rtol=0.0,
            atol=0.0,
        )

    def test_left_skewed_nonnegative_common_mode_cannot_understate_ucb(
        self,
    ) -> None:
        observed = np.asarray([10.0])
        bootstrap = np.asarray([[0.0], [8.0], [9.0], [9.5], [10.1]])
        upper, _ = admission._simultaneous_upper(
            observed,
            bootstrap,
            0.025,
        )
        self.assertIsNotNone(upper)
        standard_error = np.std(bootstrap, axis=0, ddof=1)
        inverted_critical = float(
            np.quantile(
                np.max(
                    (
                        bootstrap - observed[np.newaxis, :]
                    )
                    / standard_error,
                    axis=1,
                ),
                0.975,
                method="higher",
            )
        )
        inverted_upper = observed + inverted_critical * standard_error
        self.assertTrue(np.all(bootstrap >= 0.0))
        self.assertEqual(float(upper[0]), 20.0)
        self.assertGreater(float(upper[0]), float(inverted_upper[0]) + 5.0)
        self.assertGreaterEqual(float(upper[0]), float(observed[0]))

    def test_g2_reports_log_coordinate_without_raw_scale_fallback(self) -> None:
        gate = _gate(self.baseline_result, "G2")
        diagnostics = gate["diagnostics"]
        self.assertEqual(
            diagnostics["inference_coordinate"],
            "natural_log_reference_snr",
        )
        self.assertEqual(
            diagnostics["reported_bound"],
            "exp_coordinate_lower_bound",
        )
        critical = diagnostics["max_t"]["critical_value"]
        errors = diagnostics["max_t"]["standard_error"]
        for index, cell_definition in enumerate(CONTRACT["cells"]):
            cell = diagnostics["cells"][cell_definition["id"]]
            self.assertNotIn("lcb", cell)
            self.assertAlmostEqual(cell["log_snr"], np.log(cell["snr"]))
            self.assertAlmostEqual(
                cell["log_snr_lcb"],
                cell["log_snr"] - critical * errors[index],
            )
            self.assertAlmostEqual(
                cell["snr_lcb"], np.exp(cell["log_snr_lcb"])
            )

    def test_resealed_raw_tamper_disagrees_with_retained_diagnostics(self) -> None:
        evidence = copy.deepcopy(self.baseline_evidence)
        evidence["raw_response"]["output_levels"][15] += 0.2
        payload = (
            json.dumps(
                evidence,
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        case = _embedded_case_record(payload)
        decoded, retained, _ = independent_verify._decode_embedded_evidence(
            case, CONTRACT
        )
        self.assertEqual(retained, payload)
        prepared = independent_verify._prepare_evidence(decoded, CONTRACT)
        rederived = independent_verify._raw_gate_g4(
            prepared,
            independent_verify._raw_thresholds(CONTRACT),
        )
        context = independent_verify.CheckContext()
        independent_verify._compare_rederived_tree(
            context,
            _gate(self.baseline_result, "G4"),
            rederived,
            "G4 resealed tamper",
        )
        self.assertTrue(context.errors)

    def test_nonpositive_hostile_charge_is_not_clipped(self) -> None:
        evidence = copy.deepcopy(self.baseline_evidence)
        cell = evidence["cells"][0]
        rng = np.random.default_rng(9127)
        common = _complex_normal(rng, (64, 1), 1.2)
        cell["controls"]["featureless"]["S1"] = _complex_json(common)
        cell["controls"]["featureless"]["S2"] = _complex_json(common)
        result = admission.evaluate_evidence(evidence, CONTRACT)
        gate = _gate(result, "G8")
        self.assertEqual(gate["status"], "UNMEASURED")
        self.assertIn("NONPOSITIVE_HOSTILE_CHARGE", gate["reason_codes"])
        charged_noise = gate["diagnostics"]["cells"][cell["id"]]["charged"][
            "noise_S"
        ]["minimum_eigenvalue"]
        self.assertLessEqual(charged_noise, 0.0)

    def test_vector_uses_smallest_eigenvalue_not_favorable_average(self) -> None:
        evidence = _make_evidence(vector_reference_transfer=(2.0, 0.7))
        result = admission.evaluate_evidence(evidence, CONTRACT)
        gate = _gate(result, "G8")
        vector_id = CONTRACT["cells"][-1]["id"]
        vector_diagnostics = gate["diagnostics"]["cells"][vector_id]
        self.assertGreater(
            np.mean(
                vector_diagnostics["charged"]["signal_R"]["eigenvalues"]
            ),
            np.mean(
                vector_diagnostics["charged"]["signal_S"]["eigenvalues"]
            ),
        )
        self.assertLess(vector_diagnostics["transfer_ratio"], 1.0)
        self.assertEqual(gate["status"], "UNMEASURED")
        self.assertIn("TRANSFER_NOT_DOMINANT", gate["reason_codes"])
        self.assertEqual(
            vector_diagnostics["vector_rule"],
            "SMALLEST_GENERALIZED_EIGENVALUE",
        )

    def test_digital_k_with_absent_q_uses_frozen_refusal(self) -> None:
        evidence = copy.deepcopy(self.baseline_evidence)
        evidence["claim_scope"] = "DIGITAL_K"
        result = admission.evaluate_evidence(evidence, CONTRACT)
        gate = _gate(result, "G8")
        self.assertEqual(gate["status"], "UNMEASURED")
        self.assertEqual(gate["claim_value"], None)
        self.assertEqual(
            gate["reason_codes"],
            ["DIGITAL_K_IDENTIFICATION_NOT_COMMISSIONED"],
        )
        self.assertFalse(result["all_gates_pass"])
        self.assertFalse(
            gate["diagnostics"]["digital_k_policy"][
                "q_matrix_alone_sufficient"
            ]
        )
        self.assertFalse(
            gate["diagnostics"]["digital_k_policy"]["q_payload_present"]
        )


class QBaselineBindingTests(unittest.TestCase):
    def _digital_k_evidence(self, *, zero: bool = False) -> dict:
        evidence = _make_evidence()
        evidence["claim_scope"] = "DIGITAL_K"
        payload = {
            "cell_ids": [cell["id"] for cell in CONTRACT["cells"]],
            "q": {
                cell["id"]: _complex_json(
                    np.zeros(
                        (int(cell["dimension"]), int(cell["dimension"]))
                    )
                    if zero
                    else np.eye(int(cell["dimension"]))
                )
                for cell in CONTRACT["cells"]
            },
        }
        evidence["q_baseline"] = {
            "schema": "m171-q-baseline-v1",
            "payload": payload,
            "payload_sha256": _canonical_hash(payload),
        }
        return evidence

    def _assert_frozen_refusal(self, evidence: dict) -> None:
        result = admission.evaluate_evidence(evidence, CONTRACT)
        gate = _gate(result, "G8")
        self.assertEqual(gate["status"], "UNMEASURED")
        self.assertEqual(
            gate["reason_codes"],
            ["DIGITAL_K_IDENTIFICATION_NOT_COMMISSIONED"],
        )
        self.assertFalse(result["all_gates_pass"])
        self.assertTrue(
            gate["diagnostics"]["digital_k_policy"]["q_payload_present"]
        )
        self.assertFalse(
            gate["diagnostics"]["digital_k_policy"][
                "q_matrix_alone_sufficient"
            ]
        )

    def _assert_production_missing_manifest_refusal(
        self, evidence: dict, *, q_payload_present: bool
    ) -> None:
        result = admission.evaluate_evidence(
            evidence,
            CONTRACT,
            profile="production",
        )
        definitions = {
            definition["id"]: definition
            for definition in CONTRACT["gate_definitions"]
        }
        for gate in result["gates"]:
            expected_reasons = [
                "PRODUCTION_CALIBRATION_MANIFEST_ABSENT",
                definitions[gate["id"]]["production_missing_reason"],
            ]
            if gate["id"] == "G8":
                expected_reasons.append(
                    "DIGITAL_K_IDENTIFICATION_NOT_COMMISSIONED"
                )
            self.assertEqual(gate["status"], "UNMEASURED")
            self.assertIsNone(gate["claim_value"])
            self.assertEqual(gate["reason_codes"], expected_reasons)
            self.assertEqual(
                len(gate["reason_codes"]),
                len(set(gate["reason_codes"])),
            )
        self.assertFalse(result["all_gates_pass"])
        gate = _gate(result, "G8")
        diagnostics = gate["diagnostics"]["digital_k_policy"]
        self.assertEqual(diagnostics["status"], "UNMEASURED")
        self.assertEqual(
            diagnostics["reason"],
            "DIGITAL_K_IDENTIFICATION_NOT_COMMISSIONED",
        )
        self.assertEqual(
            diagnostics["q_payload_present"], q_payload_present
        )
        self.assertFalse(diagnostics["q_matrix_alone_sufficient"])
        self.assertEqual(
            diagnostics["production_manifest_failure_additional_reason"],
            "PRODUCTION_CALIBRATION_MANIFEST_ABSENT",
        )

    def test_valid_identity_q_is_not_commissioned(self) -> None:
        self._assert_frozen_refusal(self._digital_k_evidence())

    def test_all_zero_q_is_not_commissioned(self) -> None:
        self._assert_frozen_refusal(self._digital_k_evidence(zero=True))

    def test_production_missing_manifest_with_absent_q_refuses_digital_k(
        self,
    ) -> None:
        evidence = _make_evidence()
        evidence["claim_scope"] = "DIGITAL_K"
        self._assert_production_missing_manifest_refusal(
            evidence,
            q_payload_present=False,
        )

    def test_production_missing_manifest_with_identity_q_refuses_digital_k(
        self,
    ) -> None:
        self._assert_production_missing_manifest_refusal(
            self._digital_k_evidence(),
            q_payload_present=True,
        )

    def test_production_missing_manifest_with_zero_q_refuses_digital_k(
        self,
    ) -> None:
        self._assert_production_missing_manifest_refusal(
            self._digital_k_evidence(zero=True),
            q_payload_present=True,
        )

    def test_supplied_q_payload_is_independently_hash_bound(self) -> None:
        evidence = self._digital_k_evidence()
        evidence["q_baseline"]["payload"]["q"][CONTRACT["cells"][0]["id"]][0][0][
            0
        ] += 0.25
        with self.assertRaisesRegex(admission.HarnessError, "payload SHA-256"):
            admission.evaluate_evidence(evidence, CONTRACT)


if __name__ == "__main__":
    unittest.main()
