"""Root-only complete generated-sensor weighted-normal cost; no RAW or fit."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import struct
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT / "outputs/raw-quality-2026-10-27/direct-cfa-forward-cost-precise-1/output"
BASE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-baseline"
WIDTH, HEIGHT = 7032, 4688
FIELD_HW = (4743, 7109)
IDS = (149, 0)
LIMIT = 8 << 30
CEILING = 7200.0
EXPECTED = {
    PRIOR / "geometry.json": "a48f5970205e9b4f1afd83f00f4659c0e39909f4ebfc7be2c00f91835af06672",
    PRIOR / "bindings.json": "4d26a81b727db6edebe56e24149c9553fb32141a09f475725696586c8fc1b99e",
    PRIOR / "receipt.json": "8858a1c5506c01161efad53249b338d1d52f70ff426cda1a917c3a127014dcea",
    BASE / "input-order.json": "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f",
    BASE / "alignment.txt": "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225",
    HERE.parent / "direct-cfa-forward-gpu/measurement-gpu.py": "8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84",
    HERE.parent / "joint-cfa-local-fit/band-residual/sensor-operator.py": "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac",
}


def require(value, message):
    if not value:
        raise ValueError(message)


def reference(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return dict(path=str(path), sha256=h.hexdigest(), bytes=path.stat().st_size)


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(Path(path).read_bytes(), str(path), "exec"), module.__dict__)
    return module


def array_hash(array):
    view = memoryview(array).cast("B")
    h = hashlib.sha256()
    for start in range(0, len(view), 1 << 20):
        h.update(view[start:start + (1 << 20)])
    return h.hexdigest()


def make_codes(np, source_id):
    # Original sensor coordinates; storage never becomes a per-source RGB field.
    output = np.empty((HEIGHT, WIDTH), dtype=np.uint16)
    bases = (1800, 2700, 2400, 1500)
    low_amplitudes = (310, 450, 390, 260)
    high_amplitudes = (230, 190, 270, 330)
    for y0 in range(0, HEIGHT, 128):
        y1 = min(y0 + 128, HEIGHT)
        for phase in range(4):
            dy, dx = divmod(phase, 2)
            x = np.arange(dx, WIDTH, 2, dtype=np.float32)[None, :]
            y = np.arange(y0 + dy, y1, 2, dtype=np.float32)[:, None]
            low = np.sin(np.float32(.007 + .001 * phase) * x
                         + np.float32(.011 - .001 * phase) * y
                         + np.float32(source_id * .013))
            high = np.cos(np.float32(.43 + .09 * phase) * x
                          - np.float32(.61 - .07 * phase) * y
                          + np.float32(source_id * .021))
            value = (np.float32(512 + bases[phase])
                     + np.float32(low_amplitudes[phase]) * low
                     + np.float32(high_amplitudes[phase]) * high)
            require(value.dtype == np.float32 and bool(np.isfinite(value).all()),
                    "generated sensor arithmetic must be finite f32")
            output[y0 + dy:y1:2, dx::2] = np.floor(value + np.float32(.5)).astype(np.uint16)
    output[2304:2320, 3456:3472] = np.uint16(16383)
    output.flags.writeable = False
    return output


def source_summary(np, source_id, array):
    phases = []
    for phase, name in enumerate(("R", "G1", "G2", "B")):
        dy, dx = divmod(phase, 2)
        values = array[dy::2, dx::2]
        phases.append(dict(phase=name, minimum=int(values.min()), maximum=int(values.max()),
                           clipped_at_15360=int(np.count_nonzero(values >= 15360))))
    return dict(source_id=source_id, shape=list(array.shape), dtype=str(array.dtype),
                bytes=array.nbytes, sha256=array_hash(array), writeable=array.flags.writeable,
                phase_order=["R", "G1", "G2", "B"], phase_statistics=phases,
                clipped_block_xywh=[3456, 2304, 16, 16], clipped_code=16383)


def tensor_summary(t, value):
    finite = bool(t.isfinite(value).all())
    require(finite, "nonfinite complete global output")
    h, w, _ = value.shape
    coordinates = ((0, 0), (0, w - 1), (h // 2, w // 2), (h - 1, 0), (h - 1, w - 1))
    return dict(shape=list(value.shape), dtype=str(value.dtype), finite=True,
                minimum=float(value.min()), maximum=float(value.max()), mean_f32=float(value.mean()),
                samples=[dict(y=y, x=x, rgb=value[y, x].tolist()) for y, x in coordinates])


def timed(t, function):
    t.cuda.synchronize(0)
    start = time.perf_counter()
    value = function()
    t.cuda.synchronize(0)
    return value, time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / "outputs").resolve()), "output must be inside workspace outputs")
    require(not out.exists(), "fresh output directory required")
    out.mkdir(parents=True)
    started = time.perf_counter()
    state = dict(status="STARTED", complete=False, mechanical_pass=False, quality_claim=False,
                 photographic_admission=False, admission=False, RAW_reads=0, source_ids=list(IDS))
    try:
        paths = list(EXPECTED) + [Path(__file__), HERE / "full-cost-notes.md", HERE / "cost-brief.md",
            HERE / "normal-operator.py", HERE / "bands-gpu.py", HERE / "measurement-paired.py",
            HERE.parent / "dual-tree-cfa-gpu/ordered-fir.py"]
        bindings = [reference(p) for p in paths]
        for row in bindings:
            expected = EXPECTED.get(Path(row["path"]))
            require(expected is None or row["sha256"] == expected, "frozen input changed: " + row["path"])
        save(out / "bindings.json", bindings)
        geometry = json.loads((PRIOR / "geometry.json").read_text(encoding="utf-8"))
        require(geometry["source_count"] == 299 and geometry["source_wh"] == [WIDTH, HEIGHT]
                and geometry["field_wh"] == list(reversed(FIELD_HW)) and geometry["reference"] == 149
                and geometry["reference_integer_origin"] == [-34, -22]
                and not geometry["stored_anchor_coerced_to_identity"], "fixed global geometry changed")
        require(len(geometry["maps"]) == 299, "all299 geometry required")
        selected = [geometry["maps"][i] for i in IDS]
        for source_id, row in zip(IDS, selected):
            require(row["source_index"] == source_id, "selected source identity mismatch")
            require([[struct.pack(">d", v).hex() for v in r] for r in row["source_to_latent_2x3"]]
                    == row["source_to_latent_f64_bits"], "held affine f64 bits changed")
        save(out / "geometry.json", dict(field_hw=list(FIELD_HW), source_wh=[WIDTH, HEIGHT],
            original_source_count=299, selected_source_count=2, reference=149,
            reference_integer_origin=geometry["reference_integer_origin"], maps=selected,
            domain_policy=geometry["domain_policy"], delivery_crop_used_as_domain=False))
        clocks = {name: vars(time.get_clock_info(name)) for name in ("monotonic", "perf_counter")}
        require(clocks["perf_counter"]["monotonic"] and clocks["perf_counter"]["resolution"] <= 1e-6,
                "precise monotonic QPC interval clock required")
        import numpy as np
        import torch as t
        t.set_num_threads(4)
        t.set_num_interop_threads(1)
        t.backends.cuda.matmul.allow_tf32 = False
        t.backends.cudnn.allow_tf32 = False
        require(t.cuda.is_available(), "CUDA required")
        total = t.cuda.get_device_properties(0).total_memory
        require(total >= LIMIT, "fixed8GiB device allocation allowance required")
        t.cuda.set_per_process_memory_fraction(LIMIT / total, 0)
        t.cuda.reset_peak_memory_stats(0)
        environment = dict(torch=t.__version__, cuda=t.version.cuda, numpy=np.__version__,
            python=sys.version, device=t.cuda.get_device_name(0), device_total_bytes=total,
            device_allocation_limit_bytes=LIMIT, workers=4, interop_workers=1,
            matmul_tf32=False, cudnn_tf32=False, autocast=False, clocks=clocks)
        save(out / "environment.json", environment)
        normal = load(HERE / "normal-operator.py", "full_cost_streamed_normal")
        paired = load(HERE / "measurement-paired.py", "full_cost_paired_measurement")
        measurement, initialize_seconds = timed(t, lambda: paired.PairedMeasurementGpu(
            t, FIELD_HW, device_limit_bytes=LIMIT))
        save(out / "initialization.json", dict(seconds=initialize_seconds,
            meaning="module/NVRTC/context setup before weighted-normal construction; excluded from scenario"))
        generation_start = time.perf_counter()
        codes = {i: make_codes(np, i) for i in IDS}
        input_before = [source_summary(np, i, codes[i]) for i in IDS]
        generation_seconds = time.perf_counter() - generation_start
        save(out / "generated-inputs.json", dict(sources=input_before, seconds=generation_seconds,
            equations="full-cost-notes.md; original-coordinate independent physical phase signals",
            optical_scene_truth=False, acquisition_noise_injected=False))
        gain = np.float32(np.float32(100) / np.float32(436.8))
        read_e = np.float32(4.2)
        read_dn = np.float32(read_e * gain)
        read_variance = np.float32(read_dn * read_dn)
        noise = normal.Noise((float(gain),) * 4, (float(read_variance),) * 4, (512.,) * 4, 15360)
        f32bits = lambda v: struct.pack(">f", float(v)).hex()
        save(out / "noise.json", dict(iso=100, shot4=list(noise.shot4), read4=list(noise.read4),
            black4=list(noise.black4), saturation=noise.saturation,
            gain_bits=f32bits(gain), read_e_bits=f32bits(read_e), read_dn_bits=f32bits(read_dn),
            read_variance_bits=f32bits(read_variance),
            operation_order="gain=f32(f32(100)/f32(436.8)); read_dn=f32(f32(4.2)*gain); read4=f32(read_dn*read_dn)",
            quantization_variance_added=False, private_noise_estimate=False))
        loads = {i: 0 for i in IDS}
        def loader(i):
            loads[i] += 1
            require(not codes[i].flags.writeable, "generated original became writable")
            return codes[i]
        sources = [normal.Source(i, (0, 0, WIDTH, HEIGHT), row["source_to_latent_2x3"],
                   lambda i=i: loader(i)) for i, row in zip(IDS, selected)]
        with t.inference_mode(), t.autocast(device_type="cuda", enabled=False):
            problem, constructor_seconds = timed(t, lambda: normal.StreamedProblem(
                t, FIELD_HW, sources, noise, measurement=measurement, device_limit_bytes=LIMIT))
            constructor_metadata = problem.metadata()
            save(out / "constructor.json", dict(seconds=constructor_seconds, metadata=constructor_metadata,
                loader_calls=dict(loads), meaning="actual qmax, Haar/factors, constants, G and projected RHS construction"))
            require(problem.paired, "paired measurement was not selected")
            # One global signed input only, never one RGB latent per source.
            field = t.empty((*FIELD_HW, 3), dtype=t.float32, device="cuda:0")
            x = t.arange(FIELD_HW[1], dtype=t.float32, device="cuda:0")[None, :] - 34
            for y0 in range(0, FIELD_HW[0], 128):
                y1 = min(y0 + 128, FIELD_HW[0])
                y = t.arange(y0, y1, dtype=t.float32, device="cuda:0")[:, None] - 22
                for c in range(3):
                    field[y0:y1, :, c] = (1500 * t.sin((.013 + .003*c)*x + (.017 - .002*c)*y)
                                          + 275 * t.cos((.31 + .07*c)*x - (.27 + .05*c)*y))
            del x, y
            input_field_summary = tensor_summary(t, field)
            result, normal_seconds = timed(t, lambda: problem.normal(field))
            normal_summary = tensor_summary(t, result)
            normal_metadata = problem.metadata()
            save(out / "normal.json", dict(seconds=normal_seconds, input=input_field_summary,
                output=normal_summary, metadata=normal_metadata, loader_calls=dict(loads)))
            require(normal_metadata["calls"]["paired_forward_rectangles"]
                    > constructor_metadata["calls"]["paired_forward_rectangles"], "normal did not consume paired calls")
            del result, field
            rhs, rhs_seconds = timed(t, problem.rhs)
            rhs_summary = tensor_summary(t, rhs)
            save(out / "rhs-retrieval.json", dict(seconds=rhs_seconds, output=rhs_summary,
                meaning="clone of projected RHS already built in constructor; no new source pass"))
            del rhs
        input_after = [source_summary(np, i, codes[i]) for i in IDS]
        require(input_after == input_before, "generated original bytes/metadata changed")
        after_bindings = [reference(p) for p in paths]
        require(after_bindings == bindings, "bound source/geometry changed during checkpoint")
        metadata = problem.metadata()
        require(metadata["source_count"] == 2 and metadata["source_ids"] == list(IDS)
                and metadata["original_sensel_count"] == 2 * WIDTH * HEIGHT,
                "full two-source coverage not represented")
        peak_allocated = t.cuda.max_memory_allocated(0)
        require(peak_allocated <= LIMIT, "fixed device allocation bound exceeded")
        constructor_projection = constructor_seconds * 299 / 2
        normal_projection = normal_seconds * 64 * 299 / 2
        projected = constructor_projection + normal_projection
        scenario = dict(kind="DERIVED two-source aggregate linear-source-count scenario",
            formula="constructor_seconds*299/2 + normal_seconds*64*299/2", steps=64, source_count=299,
            constructor_seconds=constructor_projection, normal_seconds=normal_projection,
            total_seconds=projected, research_observation_ceiling_seconds=CEILING,
            within_research_observation_ceiling=projected <= CEILING,
            release=False, production_speed_acceptance=False,
            caveats=["Global vector/dot work does not scale exactly with source count.",
                "Generated admission/clipping and two selected maps do not measure actual299 source heterogeneity.",
                "Original source access/export, solve vector updates, final evaluation and development are unmeasured.",
                "RHS retrieval is separately measured; RHS construction is already included in constructor.",
                "Inherited separate measurement timers use coarse monotonic; headline uses external synchronized QPC."])
        save(out / "scenario.json", scenario)
        state.update(status="COMPLETE_DIRECT_CFA_WEIGHTED_NORMAL_COST", complete=True, mechanical_pass=True,
            all_passes_completed=True, source_shape=[HEIGHT, WIDTH], field_hw=list(FIELD_HW),
            constructor_seconds=constructor_seconds, normal_seconds=normal_seconds,
            rhs_retrieval_seconds=rhs_seconds, initialization_seconds=initialize_seconds,
            generated_input_seconds=generation_seconds, elapsed_seconds=time.perf_counter()-started,
            generated_originals_unchanged=True, bound_files_unchanged=True, source_metadata=metadata,
            loader_calls=loads, scenario=scenario, gpu_peak_allocated_bytes=peak_allocated,
            gpu_peak_reserved_bytes=t.cuda.max_memory_reserved(0),
            host_peak="root-owned bounded Job receipt", driver_allocation_included=False,
            output_field_exported=False, reconstruction_fit_executed=False)
        save(out / "receipt.json", state)
    except BaseException as error:
        state.update(status="INCOMPLETE_WEIGHTED_NORMAL_COST", elapsed_seconds=time.perf_counter()-started,
                     error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
        save(out / "failure.json", state)
        raise


if __name__ == "__main__":
    main()
