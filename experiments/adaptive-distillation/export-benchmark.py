"""Export a supplied student checkpoint and benchmark explicit local ONNX models.

No teacher is discovered, recovered, downloaded, or bundled. A teacher benchmark
is optional and requires --teacher. All timing excludes image decoding/rendering.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import onnx
import onnxruntime as ort
import torch

from student import AdaptiveStudent, StudentConfig, OUTPUT_NAMES, output_shapes


class Export(torch.nn.Module):
    def __init__(self, model: AdaptiveStudent) -> None:
        super().__init__()
        self.model = model

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, ...]:
        values = self.model(x)
        return tuple(values[key] for key in OUTPUT_NAMES)


def session(path: Path, threads: int) -> tuple[ort.InferenceSession, float]:
    options = ort.SessionOptions()
    options.intra_op_num_threads, options.inter_op_num_threads = threads, 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.add_session_config_entry("session.intra_op.allow_spinning", "0")
    start = time.perf_counter()
    model = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
    if len(model.get_inputs()) != 1 or model.get_inputs()[0].name != "input":
        raise ValueError("ONNX model must expose exactly one input named input")
    input_info = model.get_inputs()[0]
    if input_info.type != "tensor(float)" or len(input_info.shape) != 4 or input_info.shape[1:] != [5, 384, 512]:
        raise ValueError("ONNX input must be FP32 [batch,5,384,512]")
    if isinstance(input_info.shape[0], int) and input_info.shape[0] != 1:
        raise ValueError("ONNX model must accept batch one")
    if set(output.name for output in model.get_outputs()) != set(OUTPUT_NAMES):
        raise ValueError("ONNX model must expose the ten documented output names")
    expected = output_shapes()
    for output in model.get_outputs():
        if output.type != "tensor(float)" or tuple(output.shape[1:]) != expected[output.name][1:]:
            raise ValueError(f"ONNX output {output.name} has a different dtype/shape contract")
        if isinstance(output.shape[0], int) and output.shape[0] != 1:
            raise ValueError(f"ONNX output {output.name} must have batch one")
    return model, time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new or empty export directory")
    parser.add_argument("--teacher", type=Path, help="optional user-supplied compatible ONNX model")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=12)
    parser.add_argument("--fixtures", type=int, default=8)
    args = parser.parse_args()
    if min(args.threads, args.repeats, args.fixtures) < 1:
        parser.error("threads, repeats, and fixtures must be positive")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output directory must be empty")
    torch.set_num_threads(args.threads)
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    student = AdaptiveStudent(StudentConfig(**checkpoint["config"])).eval()
    student.load_state_dict(checkpoint["state_dict"])
    manifest = json.loads((args.cache / "manifest.json").read_text(encoding="utf-8"))
    indices = [i for i, record in enumerate(manifest["records"]) if record["split"] == "validation"]
    if not indices:
        raise ValueError("cache has no validation fixtures")
    inputs = np.load(args.cache / "inputs.npy", mmap_mode="r", allow_pickle=False)
    if inputs.dtype not in (np.uint8, np.float32) or tuple(inputs.shape[1:]) != (5, 384, 512):
        raise ValueError("inputs.npy must be uint8 or FP32 [N,5,384,512]")
    if len(inputs) != len(manifest["records"]):
        raise ValueError("manifest/input row count differs")
    # Endpoint-inclusive spacing avoids always selecting variant zero when the
    # cache repeats a fixed number of mask variants per photograph.
    chosen = [indices[int(offset)] for offset in np.linspace(
        0, len(indices) - 1, min(args.fixtures, len(indices)), dtype=np.int64,
    )]
    divisor = 255.0 if inputs.dtype == np.uint8 else 1.0
    fixtures = [inputs[index:index + 1].astype(np.float32) / divisor for index in chosen]
    if not all(np.isfinite(fixture).all() for fixture in fixtures):
        raise ValueError("non-finite validation fixture")
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "adaptive-student.onnx"
    torch.onnx.export(Export(student), torch.from_numpy(fixtures[0]), str(path),
                      input_names=["input"], output_names=list(OUTPUT_NAMES), opset_version=17,
                      dynamo=False, do_constant_folding=True)
    onnx.checker.check_model(onnx.load(str(path)), full_check=True)
    runtime, student_load = session(path, args.threads)
    models, load_seconds = {"student": runtime}, {"student": student_load}
    if args.teacher:
        models["teacher"], load_seconds["teacher"] = session(args.teacher, args.threads)
    parity = {key: 0.0 for key in OUTPUT_NAMES}
    with torch.no_grad():
        for fixture in fixtures:
            reference = student(torch.from_numpy(fixture))
            predictions = runtime.run(list(OUTPUT_NAMES), {"input": fixture})
            for key, prediction in zip(OUTPUT_NAMES, predictions):
                expected_value = reference[key].numpy()
                if prediction.shape != expected_value.shape or prediction.dtype != expected_value.dtype:
                    raise ValueError(f"{key}: exported dtype/shape differs from PyTorch")
                if not np.isfinite(prediction).all() or not np.isfinite(expected_value).all():
                    raise ValueError(f"{key}: non-finite export/reference output")
                parity[key] = max(parity[key], float(np.max(np.abs(prediction - expected_value))))
                np.testing.assert_allclose(prediction, expected_value, rtol=2e-4, atol=2e-5,
                                           equal_nan=False, err_msg=key)
    expected_shapes = output_shapes()
    for model in models.values():
        # Contract checks and warm-up are outside the timed loop for both models.
        for fixture in fixtures:
            outputs = model.run(list(OUTPUT_NAMES), {"input": fixture})
            for key, value in zip(OUTPUT_NAMES, outputs):
                if value.dtype != np.float32 or value.shape != expected_shapes[key] or not np.isfinite(value).all():
                    raise ValueError(f"{key}: ONNX runtime output violates the finite FP32 contract")
    timings = {name: [] for name in models}
    for repeat in range(args.repeats):
        order = list(models.items())
        if repeat % 2:
            order.reverse()
        for name, model in order:
            for fixture in fixtures:
                start = time.perf_counter()
                model.run(list(OUTPUT_NAMES), {"input": fixture})
                timings[name].append((time.perf_counter() - start) * 1000)
    summary = {name: {"min_ms": float(np.min(values)), "median_ms": float(np.median(values)),
                      "p95_ms": float(np.quantile(values, .95)), "runs": len(values)}
               for name, values in timings.items()}
    report = {
        "scope": "Forward inference only; excludes image decoding, semantic masks, color rendering, and app display",
        "provider": "CPUExecutionProvider", "threads": args.threads, "runtime_version": ort.__version__,
        "checkpoint_step": checkpoint.get("step"), "student_bytes": path.stat().st_size,
        "student_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "student_parameters": student.describe(),
        "export_max_absolute_parity_error": parity, "load_seconds": load_seconds,
        "warm_inference": summary, "raw_milliseconds": timings, "validation_fixture_indices": chosen,
    }
    if args.teacher:
        report.update({"teacher_bytes": args.teacher.stat().st_size,
                       "teacher_sha256": hashlib.sha256(args.teacher.read_bytes()).hexdigest(),
                       "median_speed_ratio": summary["teacher"]["median_ms"] / summary["student"]["median_ms"],
                       "file_size_ratio": args.teacher.stat().st_size / path.stat().st_size})
    (args.output / "export-benchmark.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("raw_milliseconds", "student_parameters")}, indent=2))


if __name__ == "__main__":
    main()
