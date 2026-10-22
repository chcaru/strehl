"""Strict FP32 V4 export parity on validation fixtures, with optional CPU timings.

This does not evaluate photographic quality, infer semantic masks, or read test
labels. Every validation group/mask-variant combination supplies a fixture.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
import onnx
import onnxruntime as ort
import torch


def import_file(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V4 = import_file(Path(__file__).with_name("student-v4.py"), "strehl_student_v4_export")
INPUT = import_file(Path(__file__).with_name("input-contract.py"), "strehl_v4_input_export")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_shapes(batch: int = 1) -> dict:
    return {**{key: (batch, 16, 96, 128) for key in V4.GAIN_KEYS},
            **{key: (batch, 3, 32, 32, 32) for key in V4.LUT_KEYS},
            **{key: (batch, 1) for key in V4.EXPOSURE_KEYS}}


def validate_outputs(values: dict, batch: int = 1) -> None:
    if set(values) != set(V4.OUTPUT_NAMES):
        raise ValueError("output head set differs")
    for key, shape in expected_shapes(batch).items():
        value = values[key]
        if value.dtype != np.float32 or value.shape != shape or not np.isfinite(value).all():
            raise ValueError(f"{key}: finite FP32 exact shape {shape} required")
        if key in V4.GAIN_KEYS and not (value > 0).all():
            raise ValueError(f"{key}: positive gains required")


def load_v4(path: Path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    student = V4.StudentV4(V4.V4Config(**checkpoint["config"]))
    student.load_state_dict(checkpoint["state_dict"], strict=True)
    if student.config.input_size != (384, 512) or student.config.gain_size != (96, 128):
        raise ValueError("only the full teacher input/output contract is exportable here")
    for value in student.state_dict().values():
        if value.is_floating_point() and (value.dtype != torch.float32 or not torch.isfinite(value).all()):
            raise ValueError("checkpoint must contain finite FP32 floating-point state")
    return student.eval(), checkpoint


def assert_checkpoint_input(checkpoint: dict, descriptor: dict) -> None:
    recorded = checkpoint.get("model_input_contract_sha256")
    if recorded is None and descriptor["domain"] == INPUT.LEGACY_DOMAIN:
        return  # Explicit legacy-only migration; never infer a new linear domain.
    if recorded != INPUT.contract_sha256(descriptor) or checkpoint.get("model_input_contract") != descriptor:
        raise ValueError("checkpoint and selected cache predictor-input contracts differ")


class Export(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, inputs):
        values = self.model(inputs)
        return tuple(values[key] for key in V4.OUTPUT_NAMES)


class PortableGroupNorm(torch.nn.GroupNorm):
    """Same normalization with short, centered FP32 reductions for export.

    Flattening a large spatial plane into one InstanceNormalization reduction
    loses precision in some CPU runtimes. Keep the channel/spatial axes separate
    and reduce each in turn after subtracting one group-local anchor. The anchor
    prevents a constant offset from accumulating reduction error. This changes
    neither parameters nor epsilon. The
    untouched PyTorch model remains the independent conversion reference.
    """

    def forward(self, value):
        grouped = value.reshape(value.shape[0], self.num_groups,
                                value.shape[1] // self.num_groups, *value.shape[2:])

        def average(tensor):
            for axis in range(tensor.ndim - 1, 1, -1):
                tensor = tensor.mean(axis, keepdim=True)
            return tensor

        anchor = (slice(None), slice(None)) + (slice(0, 1),) * (grouped.ndim - 2)
        shifted = grouped - grouped[anchor]
        centered = shifted - average(shifted)
        normalized = centered / (average(centered.square()) + self.eps).sqrt()
        result = normalized.reshape_as(value)
        affine_shape = (1, -1) + (1,) * (value.ndim - 2)
        if self.weight is not None:
            result = result * self.weight.reshape(affine_shape)
        if self.bias is not None:
            result = result + self.bias.reshape(affine_shape)
        return result


def portable_model(student):
    """Copy before substitution: conversion must not change its own reference."""
    result = copy.deepcopy(student)

    def replace(parent):
        for name, child in list(parent.named_children()):
            if isinstance(child, torch.nn.GroupNorm):
                replacement = PortableGroupNorm(child.num_groups, child.num_channels,
                                                child.eps, child.affine)
                replacement.load_state_dict(child.state_dict(), strict=True)
                replacement.train(child.training)
                setattr(parent, name, replacement)
            else:
                replace(child)

    replace(result)
    return result


def session(path: Path, threads: int):
    options = ort.SessionOptions()
    options.intra_op_num_threads, options.inter_op_num_threads = threads, 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.add_session_config_entry("session.intra_op.allow_spinning", "0")
    start = time.perf_counter()
    runtime = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
    inputs = runtime.get_inputs()
    if len(inputs) != 1 or inputs[0].name != "input" or inputs[0].type != "tensor(float)" or inputs[0].shape != [1, 5, 384, 512]:
        raise ValueError("runtime input contract differs from fixed FP32 batch-one input")
    declared = {value.name: value for value in runtime.get_outputs()}
    if set(declared) != set(V4.OUTPUT_NAMES):
        raise ValueError("runtime output names differ")
    for key, shape in expected_shapes().items():
        if declared[key].type != "tensor(float)" or tuple(declared[key].shape) != shape:
            raise ValueError(f"runtime output declaration differs: {key}")
    return runtime, time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--timing-fixtures", type=int, default=8)
    args = parser.parse_args()
    if min(args.threads, args.repeats, args.timing_fixtures) < 1:
        parser.error("counts must be positive")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output must be new or empty")
    torch.set_num_threads(args.threads)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    student, checkpoint = load_v4(args.checkpoint)
    manifest_path = args.cache / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest["records"]
    input_contract = INPUT.select_manifest_contract(manifest, sha256(manifest_path))
    assert_checkpoint_input(checkpoint, input_contract)
    inputs = np.load(args.cache / "inputs.npy", mmap_mode="r", allow_pickle=False)
    if inputs.shape != (len(records), 5, 384, 512) or inputs.dtype not in (np.uint8, np.float32):
        raise ValueError("cache input header differs")
    chosen = {}
    for index, record in enumerate(records):
        if record["split"] == "validation":
            chosen.setdefault((record["group_id"], str(record.get("variant", 0))), index)
    if not chosen:
        raise ValueError("no validation fixtures")
    fixtures = []
    for group_variant, index in sorted(chosen.items()):
        value = INPUT.prepare_numpy(inputs[index:index + 1], input_contract)
        if not np.isfinite(value).all() or not ((value >= -2e-6) & (value <= 1 + 2e-6)).all():
            raise ValueError("fixture violates provisional normalized input contract")
        fixtures.append(({"cache_index": index, "group": group_variant[0], "variant": group_variant[1]}, value))
    # Exercise masks that may be absent in a particular validation cache; parity
    # of a deliberately artificial fixture does not establish its visual quality.
    for name, subject, sky in (("both_zero", 0, 0), ("subject_one", 1, 0), ("sky_one", 0, 1), ("both_one", 1, 1)):
        value = fixtures[0][1].copy()
        value[:, 3], value[:, 4] = subject, sky
        fixtures.append(({"synthetic_mask": name}, value))
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "adaptive-student-v4.onnx"
    torch.onnx.export(Export(portable_model(student)), torch.from_numpy(fixtures[0][1]), str(path),
                      input_names=["input"], output_names=list(V4.OUTPUT_NAMES), opset_version=17,
                      dynamo=False, do_constant_folding=True)
    onnx.checker.check_model(onnx.load(str(path)), full_check=True)
    runtime, load_seconds = session(path, args.threads)
    parity, details = {key: 0.0 for key in V4.OUTPUT_NAMES}, []
    with torch.inference_mode():
        for identity, fixture in fixtures:
            reference = {key: value.numpy() for key, value in student(torch.from_numpy(fixture)).items()}
            prediction = dict(zip(V4.OUTPUT_NAMES, runtime.run(list(V4.OUTPUT_NAMES), {"input": fixture})))
            validate_outputs(reference)
            validate_outputs(prediction)
            errors = {}
            for key in V4.OUTPUT_NAMES:
                np.testing.assert_allclose(prediction[key], reference[key], rtol=2e-4, atol=2e-5,
                                           equal_nan=False, err_msg=f"{identity}: {key}")
                errors[key] = float(np.max(np.abs(prediction[key] - reference[key])))
                parity[key] = max(parity[key], errors[key])
            details.append({**identity, "max_absolute_errors": errors})
    timing = []
    real_fixtures = fixtures[:-4]
    timing_ids = list(dict.fromkeys(int(index) for index in np.linspace(0, len(real_fixtures) - 1,
                      min(args.timing_fixtures, len(real_fixtures)), dtype=np.int64)))
    # Every actual cache mask variant participates even if the requested timing
    # budget is smaller; parity still covers every group/variant combination.
    variants = {}
    for index, (identity, _) in enumerate(real_fixtures):
        variants.setdefault(identity["variant"], index)
    timing_ids = sorted(set(timing_ids) | set(variants.values()))
    selected = [real_fixtures[index][1] for index in timing_ids]
    for repeat in range(args.repeats):
        for fixture in selected[::1 if repeat % 2 == 0 else -1]:
            start = time.perf_counter()
            runtime.run(list(V4.OUTPUT_NAMES), {"input": fixture})
            timing.append((time.perf_counter() - start) * 1000)
    report = {"scope": "FP32 conversion parity and forward inference only; no rendering or photographic quality claims",
              "checkpoint_sha256": sha256(args.checkpoint), "checkpoint_step": checkpoint.get("step"),
              "checkpoint_weights_only_load": True, "cache_manifest_sha256": sha256(manifest_path),
              "model_input_contract": input_contract, "model_input_contract_sha256": INPUT.contract_sha256(input_contract),
              "normalization_export": "anchored-centered-sequential-spatial-reductions-v1",
              "parity_reference": "unchanged checkpoint with native PyTorch GroupNorm",
              "export_implementation_sha256": sha256(Path(__file__)),
              "student_implementation_sha256": sha256(Path(__file__).with_name("student-v4.py")),
              "input_contract_implementation_sha256": INPUT.implementation_sha256(),
              "output_bytes": path.stat().st_size, "output_sha256": sha256(path), "model": student.describe(),
              "provider": "CPUExecutionProvider", "threads": args.threads, "onnxruntime": ort.__version__,
              "load_seconds": load_seconds, "max_absolute_errors": parity, "fixtures": details,
              "warm_inference": {"min_ms": min(timing), "median_ms": float(np.median(timing)),
                                 "p95_ms": float(np.quantile(timing, .95)), "runs": len(timing)},
              "timing_fixtures": [real_fixtures[index][0] for index in timing_ids],
              "raw_milliseconds": timing, "reserved_test_rows_read": False}
    (args.output / "export-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in ("fixtures", "raw_milliseconds", "model")}, indent=2))


if __name__ == "__main__":
    main()
