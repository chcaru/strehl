"""Root-scheduled complete-sensor A/At cost; no RAW input or reconstruction."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import os
import struct
import sys
import time
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-baseline"
ORDER = BASE / "input-order.json"
MAP = BASE / "alignment.txt"
GPU = HERE / "measurement-gpu.py"
CPU = HERE.parent / "joint-cfa-local-fit/band-residual/sensor-operator.py"
LOADER = HERE.parent / "dual-tree-cfa-gpu/ordered-fir.py"
ORDER_SHA = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f"
MAP_SHA = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225"
CPU_SHA = "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac"
WIDTH, HEIGHT = 7032, 4688
COUNT = WIDTH * HEIGHT
LIMIT = 8 << 30
SOURCE_IDS = (149, 0)


def require(value, message):
    if not value:
        raise ValueError(message)


def ref(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return {"path": str(path), "sha256": h.hexdigest(), "bytes": path.stat().st_size}


def save(path, value, replace=False):
    path = Path(path)
    target = path.with_suffix(path.suffix + ".tmp") if replace else path
    with target.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
    if replace:
        os.replace(target, path)


def f64(bits):
    return struct.unpack("<d", struct.pack("<Q", int(bits, 16)))[0]


def f64bits(value):
    return struct.pack(">d", value).hex()


def geometry():
    require(ref(ORDER)["sha256"] == ORDER_SHA and ref(MAP)["sha256"] == MAP_SHA,
            "held order or map changed")
    order = json.loads(ORDER.read_text(encoding="utf-8"))
    require(len(order) == 299, "exact299 population required")
    for i, record in enumerate(order):
        require(record["index"] == i and Path(record["path"]).name == f"DSC{i+1:05}.ARW",
                "original299 order changed")
    lines = MAP.read_text(encoding="utf-8").splitlines()
    for header in ("frames 299", "plane 3516x2344", "reference 149", "resampler catmull-rom"):
        require(header in lines, "held map header changed: " + header)
    maps = []
    for line in lines:
        words = line.split("#", 1)[0].split()
        if not words or not words[0].isdigit():
            continue
        require(len(words) == 6 and int(words[0]) == len(maps) and words[1] == "placed",
                "map source unavailable or order changed")
        ar, ai, bx, by = (f64(v) for v in words[2:])
        require(all(math.isfinite(v) for v in (ar, ai, bx, by)), "nonfinite held map")
        denominator = ar * ar + ai * ai
        require(denominator > 0, "singular held map")
        u, v = ar / denominator, ai / denominator
        # Invert p_source=C+A*(p_reference-C)+2*b, retaining stored f64 input.
        cx, cy = WIDTH / 2, HEIGHT / 2
        a = [[u, v, cx - (u * (cx + 2 * bx) + v * (cy + 2 * by))],
             [-v, u, cy - (-v * (cx + 2 * bx) + u * (cy + 2 * by))]]
        corners = [[(a[0][0] * x + a[0][1] * y) + a[0][2],
                    (a[1][0] * x + a[1][1] * y) + a[1][2]]
                   for y in (-0.5, HEIGHT - 0.5) for x in (-0.5, WIDTH - 0.5)]
        maps.append({"source_index": len(maps), "stored_f64_bits": words[2:],
                     "source_to_reference_2x3": a, "unit_footprint_corners_reference": corners})
    require(len(maps) == 299, "incomplete held placement population")
    corners = [p for m in maps for p in m["unit_footprint_corners_reference"]]
    lower = [min(p[d] for p in corners) for d in (0, 1)]
    upper = [max(p[d] for p in corners) for d in (0, 1)]
    origin = [math.floor(v) - 4 for v in lower]
    last = [math.ceil(v) + 4 for v in upper]
    field_wh = [last[d] - origin[d] + 1 for d in (0, 1)]
    require(all(8 <= v <= 8192 for v in field_wh), "global union exceeds frozen API")
    for m in maps:
        a = [r.copy() for r in m["source_to_reference_2x3"]]
        for d in (0, 1):
            a[d][2] -= origin[d]
        m["source_to_latent_2x3"] = a
        m["source_to_latent_f64_bits"] = [[f64bits(v) for v in row] for row in a]
    return {"source_count": 299, "source_wh": [WIDTH, HEIGHT], "reference": 149,
            "native_center": [WIDTH / 2, HEIGHT / 2], "reference_integer_origin": origin,
            "reference_last_lattice_point_inclusive": last, "field_wh": field_wh,
            "all_source_unit_footprint_union_bounds": [lower, upper], "maps": maps,
            "domain_policy": "union of all299 inverse-mapped full unit-cell corners; floor(min)-4 through ceil(max)+4 inclusive",
            "delivery_crop_used_as_domain": False, "stored_anchor_coerced_to_identity": False}


def rectangles():
    result = [(0, y, WIDTH, min(128, HEIGHT - y)) for y in range(0, HEIGHT, 128)]
    require(sum(w * h for _, _, w, h in result) == COUNT, "incomplete source coverage")
    require(all(w * h <= 1048576 for _, _, w, h in result), "rectangle too large")
    require(all(result[k][1] + result[k][3] == result[k+1][1]
                for k in range(len(result)-1)), "overlap or gap")
    return result


def summary(t, value):
    require(bool(t.isfinite(value).all()), "nonfinite complete output")
    flat = value.reshape(-1)
    ids = sorted(set((0, flat.numel() // 8, flat.numel() // 4, flat.numel() // 2,
                      3 * flat.numel() // 4, 7 * flat.numel() // 8, flat.numel() - 1)))
    samples = flat[t.tensor(ids, device=value.device, dtype=t.int64)].cpu().tolist()
    blob = struct.pack("<" + "f" * len(samples), *samples)
    return {"shape": list(value.shape), "elements": value.numel(), "all_finite": True,
            "min": float(value.min()), "max": float(value.max()), "mean_f32": float(value.mean()),
            "sample_flat_indices": ids, "sample_values_f32": samples,
            "sample_f32le_sha256": hashlib.sha256(blob).hexdigest(),
            "checksum_scope": "seven fixed scalar samples; not a full-array checksum"}


def fill_field(t, x, origin):
    h, w, _ = x.shape
    px = t.arange(w, device=x.device, dtype=t.float32)[None, :] + origin[0]
    py = t.arange(h, device=x.device, dtype=t.float32)[:, None] + origin[1]
    x[:, :, 0] = 0.7 * t.sin(0.009 * px) + 0.3 * t.cos(0.013 * py)
    x[:, :, 1] = -0.4 * t.cos(0.015 * px + 0.2) + 0.6 * t.sin(0.007 * py)
    x[:, :, 2] = 0.5 * t.sin(0.011 * px + 0.7) + 0.35 * t.cos(0.019 * py + 0.3)


def residual(t, rect, source):
    ox, oy, w, h = rect
    x = t.arange(ox, ox + w, device="cuda:0", dtype=t.float32)[None, :]
    y = t.arange(oy, oy + h, device="cuda:0", dtype=t.float32)[:, None]
    return (0.5 * t.sin(0.011 * x) + 0.37 * t.cos(0.017 * y)
            + 0.2 * t.sin(0.003 * (x + y) + 0.01 * source)).contiguous()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists(),
            "output must be fresh below worktree outputs")
    out.mkdir()
    started, cpu_started = time.perf_counter(), time.process_time()
    state = {"status": "STARTED_DIRECT_CFA_FORWARD_COST", "all_passes_completed": False,
             "quality_claim": False, "photographic_admission": False, "RAW_reads": 0,
             "inverse_fit_executed": False, "large_arrays_saved": False, "completed_passes": []}
    state["clock_info"] = {name: vars(time.get_clock_info(name)) for name in ("monotonic", "perf_counter")}
    producer = None
    try:
        bindings = [ref(p) for p in (Path(__file__), HERE / "cost-notes.md", HERE / "cost-brief.md",
                    GPU, CPU, LOADER, ORDER, MAP, Path(sys.executable))]
        require(ref(CPU)["sha256"] == CPU_SHA, "frozen CPU reference changed")
        save(out / "bindings.json", bindings)
        g, rects = geometry(), rectangles()
        save(out / "geometry.json", g)
        save(out / "coverage.json", {"source_ids_in_order": list(SOURCE_IDS), "source_wh": [WIDTH, HEIGHT],
             "rectangles_xywh": rects, "sensels_per_pass": COUNT, "no_gaps_or_overlaps": True})
        save(out / "progress.json", state, replace=True)
        init_start = time.perf_counter()
        import torch as t
        t.set_num_threads(4)
        t.set_num_interop_threads(1)
        t.backends.cuda.matmul.allow_tf32 = False
        t.backends.cudnn.allow_tf32 = False
        require(t.cuda.is_available(), "CUDA required")
        t.cuda.set_device(0)
        props = t.cuda.get_device_properties(0)
        t.cuda.set_per_process_memory_fraction(min(1.0, LIMIT / props.total_memory), 0)
        spec = importlib.util.spec_from_file_location("direct_cfa_cost_measurement", GPU)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        exec(compile(GPU.read_bytes(), str(GPU), "exec"), module.__dict__)
        fw, fh = g["field_wh"]
        producer = module.MeasurementGpu(t, (fh, fw), device_limit_bytes=LIMIT)
        t.cuda.synchronize()
        initialization_seconds = time.perf_counter() - init_start
        with t.inference_mode(), t.autocast(device_type="cuda", enabled=False):
            allocation_start = time.perf_counter()
            x = t.empty((fh, fw, 3), device="cuda:0", dtype=t.float32)
            accumulated = t.zeros_like(x)
            x.fill_(0.25)
            t.cuda.synchronize()
            allocation_seconds = time.perf_counter() - allocation_start
            warmup = []
            warm_rect = (64, 64, 32, 32)
            warm_affine = g["maps"][149]["source_to_latent_2x3"]
            warm_start = time.perf_counter()
            y = producer.forward(x, warm_rect, warm_affine)
            producer.adjoint(y, warm_rect, warm_affine, out=accumulated)
            t.cuda.synchronize()
            warmup.append({"field": "constant0.25", "seconds": time.perf_counter() - warm_start,
                           "forward_summary": summary(t, y)})
            generation_start = time.perf_counter()
            fill_field(t, x, g["reference_integer_origin"])
            t.cuda.synchronize()
            generation_seconds = time.perf_counter() - generation_start
            warm_start = time.perf_counter()
            y = producer.forward(x, warm_rect, warm_affine)
            producer.adjoint(y, warm_rect, warm_affine, out=accumulated)
            t.cuda.synchronize()
            warmup.append({"field": "signed independent-channel analytic", "seconds": time.perf_counter() - warm_start,
                           "forward_summary": summary(t, y)})
            del y
            save(out / "initialization.json", {"initialization_including_compile_seconds": initialization_seconds,
                 "producer_compile_seconds": producer.compile_seconds, "field_allocation_constant_fill_seconds": allocation_seconds,
                 "analytic_field_generation_seconds": generation_seconds, "warmup": warmup,
                 "warmup_rectangle": warm_rect, "warmup_source": 149, "field_summary": summary(t, x),
                 "torch": t.__version__, "cuda": t.version.cuda, "gpu": props.name,
                 "workers": t.get_num_threads(), "interop_workers": t.get_num_interop_threads(),
                 "tf32_matmul": t.backends.cuda.matmul.allow_tf32, "tf32_cudnn": t.backends.cudnn.allow_tf32,
                 "gpu_allocator_cap_bytes": LIMIT})
            for source in SOURCE_IDS:
                affine = g["maps"][source]["source_to_latent_2x3"]
                for operation in ("forward", "adjoint"):
                    zero_seconds = 0.0
                    if operation == "adjoint":
                        zstart = time.perf_counter()
                        accumulated.zero_()
                        t.cuda.synchronize()
                        zero_seconds = time.perf_counter() - zstart
                    records, call_seconds, generated_seconds = [], 0.0, 0.0
                    t.cuda.synchronize()
                    pass_start = time.perf_counter()
                    journal = out / f"source-{source:03}-{operation}-rectangles.jsonl"
                    with journal.open("x", encoding="utf-8", newline="\n") as log:
                        for index, rect in enumerate(rects):
                            generated = 0.0
                            if operation == "adjoint":
                                begin = time.perf_counter()
                                y = residual(t, rect, source)
                                t.cuda.synchronize()
                                generated = time.perf_counter() - begin
                            t.cuda.synchronize()
                            begin = time.perf_counter()
                            if operation == "forward":
                                y = producer.forward(x, rect, affine)
                            else:
                                result = producer.adjoint(y, rect, affine, out=accumulated)
                                require(result.data_ptr() == accumulated.data_ptr(), "adjoint changed destination")
                            t.cuda.synchronize()
                            elapsed = time.perf_counter() - begin
                            record = {"ordinal": index, "source_xywh": rect, "sensels": rect[2] * rect[3],
                                      "synchronized_operator_seconds": elapsed,
                                      "residual_generation_seconds": generated,
                                      "summary_role": "forward output" if operation == "forward" else "adjoint input residual",
                                      "summary": summary(t, y)}
                            log.write(json.dumps(record, allow_nan=False) + "\n")
                            log.flush()
                            records.append(record)
                            call_seconds += elapsed
                            generated_seconds += generated
                            del y
                    t.cuda.synchronize()
                    pass_seconds = time.perf_counter() - pass_start
                    require(len(records) == len(rects) and sum(r["sensels"] for r in records) == COUNT,
                            "complete pass coverage failed")
                    record = {"source_index": source, "operation": operation,
                              "rectangles": len(records), "sensels": COUNT, "complete_sensor": True,
                              "synchronized_whole_pass_loop_seconds": pass_seconds,
                              "synchronized_operator_calls_seconds": call_seconds,
                              "residual_generation_seconds": generated_seconds,
                              "adjoint_zeroing_before_timer_seconds": zero_seconds,
                              "journal": ref(journal), "all_finite": True}
                    if operation == "adjoint":
                        record["complete_accumulator_summary"] = summary(t, accumulated)
                    state["completed_passes"].append(record)
                    save(out / f"source-{source:03}-{operation}.json", record)
                    save(out / "progress.json", state, replace=True)
                    print(json.dumps({k: v for k, v in record.items() if k not in ("journal", "complete_accumulator_summary")} ), flush=True)
            measured = []
            for source in SOURCE_IDS:
                pair = {r["operation"]: r for r in state["completed_passes"] if r["source_index"] == source}
                a = pair["forward"]["synchronized_whole_pass_loop_seconds"]
                at = pair["adjoint"]["synchronized_whole_pass_loop_seconds"]
                call_a = pair["forward"]["synchronized_operator_calls_seconds"]
                call_at = pair["adjoint"]["synchronized_operator_calls_seconds"]
                measured.append({"source_index": source, "forward_seconds": a, "adjoint_seconds": at,
                     "forward_operator_calls_seconds": call_a, "adjoint_operator_calls_seconds": call_at,
                     "hypothetical_one_A_At_per_step_64x299_seconds": 64 * 299 * (a + at),
                     "frozen_64cap_plus_deflation_132A_133At_x299_seconds": 299 * (132 * a + 133 * at),
                     "operator_calls_only_hypothetical_one_A_At_per_step_64x299_seconds": 64 * 299 * (call_a + call_at),
                     "operator_calls_only_frozen_64cap_plus_deflation_132A_133At_x299_seconds": 299 * (132 * call_a + 133 * call_at)})
            state["extrapolation"] = {"per_source_geometry_scenarios": measured,
                "frozen_solver_call_counts": {"forward_stack_passes": 132, "adjoint_stack_passes": 133},
                "primary_practicality_basis": "operator_calls_only_frozen_64cap_plus_deflation_132A_133At_x299_seconds",
                "meaning": "Two measured geometry scenarios, not a fitted stack-cost distribution. Operator-calls-only is the primary practicality basis and excludes fake residual generation, diagnostic reductions and journaling. Unsuffixed scenarios use the whole measurement loop including those costs. Both exclude adjoint global zeroing, initial compilation/allocation/field generation, final full-adjoint inspection, Haar/noise/projection arithmetic, source I/O, solver vector updates and delivery. No64-step solve executed."}
            state["producer"] = producer.metadata(strict=True)
        for binding in bindings:
            require(ref(binding["path"]) == binding, "bound file changed: " + binding["path"])
        state.update(status="COMPLETE_DIRECT_CFA_FORWARD_COST", all_passes_completed=True,
                     mechanical_pass=True, source_bindings_unchanged=True,
                     total_wall_seconds=time.perf_counter()-started, process_cpu_seconds=time.process_time()-cpu_started,
                     host_load_scope="Root-owned process.json/host observation supplies job and host-load accounting; local process CPU excludes GPU work.")
        save(out / "receipt.json", state)
    except BaseException as error:
        state.update(status="REFUSED_DIRECT_CFA_FORWARD_COST", mechanical_pass=False,
                     error=repr(error), traceback=traceback.format_exc(),
                     total_wall_seconds=time.perf_counter()-started, process_cpu_seconds=time.process_time()-cpu_started)
        save(out / "failure.json", state)
        raise


if __name__ == "__main__":
    main()
