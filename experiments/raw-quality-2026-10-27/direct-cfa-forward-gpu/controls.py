"""Root-scheduled measurement commissioning; no reconstruction or RAW I/O."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import sys
import traceback

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
CPU_PATH = HERE.parent / "joint-cfa-local-fit/band-residual/sensor-operator.py"
GPU_PATH = HERE / "measurement-gpu.py"
LOADER_PATH = HERE.parent / "dual-tree-cfa-gpu/ordered-fir.py"
CPU_SHA = "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac"
LIMIT = 8 << 30
BARS = {"forward_max": 1e-5, "forward_rms": 2e-6,
        "adjoint_max": 2e-5, "adjoint_rms": 3e-6, "dot": 3e-6}
CASES = (
    ("identity-even", (24, 28), (0, 0), 1.0, 0.0, (0.0, 0.0)),
    ("fractional-odd", (19, 31), (3, 5), 1.0, 0.0, (0.37, -0.29)),
    ("affine-rectangular", (23, 29), (5, 2), 1.035, 0.071, (-0.23, 0.41)),
)


def ref(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data)}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    # Execute these exact local bytes; never invoke a model or fit at import.
    exec(compile(Path(path).read_bytes(), str(path), "exec"), module.__dict__)
    return module


def save_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def save_array(out, name, value):
    if torch.is_tensor(value):
        value = value.detach().cpu().numpy()
    value = np.ascontiguousarray(value)
    path = out / (name + ".npy")
    with path.open("xb") as handle:
        np.save(handle, value, allow_pickle=False)
    return {**ref(path), "shape": list(value.shape), "dtype": str(value.dtype)}


def tensor(value):
    if torch.is_tensor(value):
        return value.detach().cpu().contiguous()
    return torch.from_numpy(np.ascontiguousarray(value)).to(torch.float32)


def errors(actual, expected, kind="forward"):
    a, e = tensor(actual), tensor(expected)
    if a.dtype != torch.float32 or e.dtype != torch.float32 or a.shape != e.shape:
        raise ValueError("comparison requires same-shape f32 fields")
    if not bool(torch.isfinite(a).all() & torch.isfinite(e).all()):
        raise ValueError("nonfinite measurement comparison")
    delta = a - e
    # F32 field arithmetic and reductions; Python scalars report normalized ratios.
    maximum = float(delta.abs().max())
    rms = float(torch.sqrt(torch.mean(delta * delta)))
    scale_max = max(1.0, float(e.abs().max()))
    scale_rms = max(1.0, float(torch.sqrt(torch.mean(e * e))))
    nm, nr = maximum / scale_max, rms / scale_rms
    return {"max_abs": maximum, "rms": rms, "reference_max_scale": scale_max,
            "reference_rms_scale": scale_rms, "normalized_max": nm,
            "normalized_rms": nr,
            "pass": nm <= BARS[kind + "_max"] and nr <= BARS[kind + "_rms"]}


def dot_check(x, y, ax, aty):
    x, y, ax, aty = [tensor(v) for v in (x, y, ax, aty)]
    lhs = float(torch.sum(ax * y))
    rhs = float(torch.sum(x * aty))
    norm = lambda v: float(torch.sqrt(torch.sum(v * v)))
    scale = max(1.0, norm(ax) * norm(y) + norm(x) * norm(aty))
    normalized = abs(lhs - rhs) / scale
    return {"lhs": lhs, "rhs": rhs, "normalization": scale,
            "normalized_error": normalized, "pass": normalized <= BARS["dot"]}


def geometry(hw, origin, scale, angle, shift):
    h, w = hw
    ox, oy = origin
    yy, xx = np.mgrid[:h, :w]
    xy = np.stack((xx + ox, yy + oy), axis=-1).astype(np.int32)
    a = scale * np.asarray([[math.cos(angle), -math.sin(angle)],
                            [math.sin(angle), math.cos(angle)]], dtype=np.float64)
    source_center = np.asarray([ox + (w - 1) / 2, oy + (h - 1) / 2])
    target_center = np.asarray([8 + (w - 1) / 2, 8 + (h - 1) / 2])
    b = target_center + np.asarray(shift) - a @ source_center
    affine = np.column_stack((a, b))
    return xy, affine


def nodes_from_affine(xy, affine):
    # Original sensel square is integrated BEFORE the complete affine map.
    axis = np.asarray([-math.sqrt(3 / 5) / 2, 0, math.sqrt(3 / 5) / 2])
    offsets = np.asarray([(x, y) for y in axis for x in axis], dtype=np.float64)
    source_nodes = xy.astype(np.float64)[..., None, :] + offsets
    nodes = source_nodes @ affine[:, :2].T + affine[:, 2]
    one = np.asarray([5 / 18, 4 / 9, 5 / 18], dtype=np.float64)
    weights = np.outer(one, one).reshape(9).astype(np.float32)
    return nodes, weights


def reference(cpu, xy, affine):
    nodes, weights = nodes_from_affine(xy, affine)
    cfg = cpu.Config(observed_hw=xy.shape[:2], shot4=(.15, .13, .17, .21),
                     read4=(9, 8, 11, 13), black4=(512,) * 4, saturation=15360)
    return cpu.Measurement(cpu.Query(xy, nodes, weights), cfg), nodes, weights


def check_cap():
    torch.cuda.synchronize()
    allocated = torch.cuda.max_memory_allocated()
    reserved = torch.cuda.max_memory_reserved()
    if max(allocated, reserved) > LIMIT:
        raise RuntimeError("8GiB Torch allocator/reservation cap exceeded")
    return {"peak_allocated_bytes": allocated, "peak_reserved_bytes": reserved,
            "limit_bytes": LIMIT, "whole_gpu_memory_measurement": False}


def run(out):
    dependencies = [ref(p) for p in (Path(__file__), CPU_PATH, GPU_PATH, LOADER_PATH)]
    if dependencies[1]["sha256"] != CPU_SHA:
        raise ValueError("frozen CPU Measurement identity differs")
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    torch.cuda.set_device(0)
    props = torch.cuda.get_device_properties(0)
    torch.cuda.set_per_process_memory_fraction(min(1.0, LIMIT / props.total_memory), 0)
    torch.cuda.reset_peak_memory_stats()
    cpu, gpu = load(CPU_PATH, "commission_frozen_cpu"), load(GPU_PATH, "commission_gpu")
    rows, runtimes = [], []
    all_pass = True
    for name, hw, origin, scale, angle, shift in CASES:
        case_out = out / name
        case_out.mkdir()
        xy, affine = geometry(hw, origin, scale, angle, shift)
        measurement, nodes, weights = reference(cpu, xy, affine)
        h, w = hw
        field_hw = (h + 16, w + 16)
        rect = (*origin, w, h)
        phase = ((xy[..., 1] & 1) * 2 + (xy[..., 0] & 1)).astype(np.uint8)
        channel = np.asarray([0, 1, 1, 2], dtype=np.int64)[phase]
        device = gpu.MeasurementGpu(torch, field_hw, device_limit_bytes=LIMIT)
        artifacts = {"xy": save_array(case_out, "original-xy", xy),
                     "nodes": save_array(case_out, "cpu-original-cell-nodes", nodes),
                     "weights": save_array(case_out, "footprint-weights", weights)}
        constants = []
        # Constants are first for every geometry, before structured signals.
        for label, colors in (("positive", (512., 2048., 8192.)),
                              ("signed", (-64., 0., 31.)), ("zero", (0., 0., 0.))):
            x = np.broadcast_to(np.asarray(colors, np.float32), (*field_hw, 3)).copy()
            expected = np.asarray(colors, np.float32)[channel]
            cy = measurement.forward(x)
            gy = device.forward(torch.from_numpy(x).cuda(), rect, affine)
            evidence = {"label": label, "gpu_vs_expected": errors(gy, expected),
                        "cpu_vs_expected": errors(cy, expected),
                        "gpu_vs_cpu": errors(gy, cy),
                        "output": save_array(case_out, "constant-" + label, gy)}
            evidence["pass"] = all(evidence[k]["pass"] for k in
                                   ("gpu_vs_expected", "cpu_vs_expected", "gpu_vs_cpu"))
            constants.append(evidence)
        yy, xx = np.mgrid[:field_hw[0], :field_hw[1]]
        x = np.stack((3000 + 1500 * np.sin(2 * np.pi * (.17 * xx + .05 * yy)),
                      -700 + 600 * np.cos(2 * np.pi * (.11 * xx - .13 * yy)),
                      12000 + 1900 * np.sin(2 * np.pi * (.07 * xx + .19 * yy))), axis=-1).astype(np.float32)
        y = np.random.default_rng(73242).standard_normal(hw).astype(np.float32)
        xg, yg = torch.from_numpy(x).cuda(), torch.from_numpy(y).cuda()
        cy, ca = measurement.forward(x), measurement.adjoint(y)
        gy, ga = device.forward(xg, rect, affine), device.adjoint(yg, rect, affine)
        structured = {"forward": errors(gy, cy), "adjoint": errors(ga, ca, "adjoint"),
                      "gpu_dot": dot_check(x, y, gy, ga),
                      "cpu_dot": dot_check(x, y, cy, ca)}
        for label, value in (("latent", x), ("residual", y), ("cpu-forward", cy),
                             ("gpu-forward", gy), ("cpu-adjoint", ca), ("gpu-adjoint", ga)):
            artifacts[label] = save_array(case_out, label, value)
        phases = []
        for p in range(4):
            mask = phase == p
            yp = np.where(mask, y, np.float32(0)).astype(np.float32)
            ap = device.adjoint(torch.from_numpy(yp).cuda(), rect, affine)
            cp = measurement.adjoint(yp)
            phases.append({"physical_phase": p, "sites": int(mask.sum()),
                           "forward": errors(gy.detach().cpu()[mask], cy[mask]),
                           "adjoint": errors(ap, cp, "adjoint"),
                           "dot": dot_check(x, yp, gy, ap),
                           "output": save_array(case_out, "phase-adjoint-" + str(p), ap)})
        # Four unequal rectangles retain the SAME global latent field and map.
        joined = torch.empty_like(gy)
        summed = torch.zeros((*field_hw, 3), dtype=torch.float32, device="cuda")
        partitions = []
        for y0, y1 in ((0, h // 2), (h // 2, h)):
            for x0, x1 in ((0, w // 2), (w // 2, w)):
                subrect = (origin[0] + x0, origin[1] + y0, x1 - x0, y1 - y0)
                joined[y0:y1, x0:x1] = device.forward(xg, subrect, affine)
                returned = device.adjoint(yg[y0:y1, x0:x1].contiguous(), subrect, affine, out=summed)
                if returned.data_ptr() != summed.data_ptr():
                    raise ValueError("adjoint did not accumulate into supplied global output")
                partitions.append(list(subrect))
        partition = {"rectangles": partitions, "forward": errors(joined, gy),
                     "adjoint": errors(summed, ga, "adjoint"),
                     "adjoint_cpu": errors(summed, ca, "adjoint")}
        artifacts["partition-adjoint"] = save_array(case_out, "partition-adjoint", summed)
        artifacts["partition-forward"] = save_array(case_out, "partition-forward", joined)
        # Actual producing-path interventions, evaluated by unchanged fidelity bars.
        wrong_map = affine.copy()
        wrong_map[0, 2] += .5
        wrong_coordinates = device.forward(xg, rect, wrong_map)
        wrong_device = gpu.MeasurementGpu(torch, field_hw, device_limit_bytes=LIMIT,
                                          diagnostic_channel_map=(2, 1, 1, 0))
        wrong_channels = wrong_device.forward(xg, rect, affine)
        foils = {"half_pixel_map": errors(wrong_coordinates, cy),
                 "red_blue_channel_map": errors(wrong_channels, cy)}
        foils["both_rejected"] = not foils["half_pixel_map"]["pass"] and not foils["red_blue_channel_map"]["pass"]
        artifacts["wrong-coordinates"] = save_array(case_out, "wrong-coordinates", wrong_coordinates)
        artifacts["wrong-channels"] = save_array(case_out, "wrong-channels", wrong_channels)
        refusals = []
        for edge, displacement in (("left", -8.0), ("right", 8.0)):
            bad = affine.copy()
            bad[0, 2] += displacement
            row = {"edge": edge, "cpu_refused": False, "gpu_refused": False}
            for label, action in (("cpu", lambda: reference(cpu, xy, bad)),
                                  ("gpu", lambda: device.forward(xg, rect, bad))):
                try:
                    action()
                except ValueError as exc:
                    row[label + "_refused"] = True
                    row[label + "_reason"] = str(exc)
            row["pass"] = row["cpu_refused"] and row["gpu_refused"]
            refusals.append(row)
        unchanged = torch.equal(xg.cpu(), torch.from_numpy(x)) and torch.equal(yg.cpu(), torch.from_numpy(y))
        passed = (all(r["pass"] for r in constants)
                  and all(r["pass"] for r in structured.values())
                  and all(r[k]["pass"] for r in phases for k in ("forward", "adjoint", "dot"))
                  and all(partition[k]["pass"] for k in ("forward", "adjoint", "adjoint_cpu"))
                  and foils["both_rejected"] and all(r["pass"] for r in refusals) and unchanged)
        row = {"case": name, "source_xywh": rect, "field_hw": field_hw,
               "source_to_latent": affine.tolist(), "constants_first": constants,
               "structured": structured, "physical_phases": phases, "partition": partition,
               "foils": foils, "support_refusals": refusals,
               "inputs_unchanged": unchanged, "artifacts": artifacts, "pass": bool(passed)}
        rows.append(row)
        save_json(case_out / "receipt.json", row)
        runtimes.extend([device.metadata(strict=True), wrong_device.metadata(strict=True)])
        check_cap()
        all_pass &= passed
    after = [ref(Path(row["path"])) for row in dependencies]
    preserved = dependencies == after
    return {"status": "COMPLETE_DIRECT_CFA_FORWARD_CONTROLS", "all_cases_completed": True,
            "mechanical_pass": bool(all_pass and preserved), "photographic_admission": False,
            "quality_claim": False, "reconstruction_run": False, "RAW_reads": 0,
            "bars": BARS, "cases": rows, "dependencies_before": dependencies,
            "dependencies_after": after, "dependencies_unchanged": preserved,
            "runtime": runtimes, "memory": check_cap(), "threads": torch.get_num_threads(),
            "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
            "device": props.name, "default_dtype": str(torch.get_default_dtype()),
            "tf32_matmul": torch.backends.cuda.matmul.allow_tf32,
            "tf32_cudnn": torch.backends.cudnn.allow_tf32,
            "sensor_cell_assumption": "uniform unit-square footprint; inherited model, not Sony calibration",
            "noise_model_consumed": False,
            "scope": "A and A-transpose only; no focus weighting, solver, restoration or photographic inference"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    try:
        receipt = run(out)
    except Exception as exc:
        save_json(out / "receipt.json", {"status": "INCOMPLETE_DIRECT_CFA_FORWARD_CONTROLS",
                  "all_cases_completed": False, "mechanical_pass": False,
                  "photographic_admission": False, "quality_claim": False,
                  "error": type(exc).__name__ + ": " + str(exc), "traceback": traceback.format_exc()})
        raise
    save_json(out / "receipt.json", receipt)


if __name__ == "__main__":
    main()
