"""Frozen-population original-green pair observations; root schedules execution."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import time
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT26 = ROOT / "outputs/raw-quality-2026-10-26"
OUT27 = ROOT / "outputs/raw-quality-2026-10-27"
PHASE = HERE.parent / "phase.py"
MANIFEST = OUT27 / "direct-cfa-streamed-originals-1/output/receipt.json"
ORDER = OUT26 / "weevil-107-baseline/input-order.json"
MAP = OUT26 / "weevil-107-baseline/alignment.txt"
OBSERVER = OUT27 / "insect-placement-observe-1/output/receipt.json"
PAIRS = OBSERVER.parent / "pairs.jsonl"
PINS = {
    PHASE: "99bca095aa6c203ff248184f6c4b08801682565e65c03afabed5e9d5585f9410",
    MANIFEST: "057b50d7b311d9ff88e818a8d2376a00aac5abf07ab091afea37dd7627c56669",
    ORDER: "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f",
    MAP: "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225",
    OBSERVER: "ce59a284196bc9d7705f9f660357c12393b721b5f6b8a1c76248e8f4649c2f0b",
    PAIRS: "7b1e840342398dee21ba0125986c8b1dc7608d45a74464b42d6791423f8deda3",
}
SPANS = (1, 2, 4, 8, 16, 32, 64, 96, 128)
COST_PAIRS = {(0, 1), (0, 128), (104, 105), (148, 149), (149, 181), (170, 298)}
WIDTH, HEIGHT = 7032, 4688
CENTER = complex(3516, 2344)
GPU_LIMIT = 6 << 30
AGREEMENT_NATIVE = 0.20
PHASE_OFFSETS = {"G1": (1, 0), "G2": (0, 1)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def reference(path):
    p = Path(path).resolve()
    before = p.stat()
    digest = sha(p)
    after = p.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            f"file changed while hashing: {p}")
    return {"path": str(p), "bytes": before.st_size, "mtime_ns": before.st_mtime_ns,
            "sha256": digest}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def line(stream, value):
    stream.write(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n")


def f32(value):
    value = struct.unpack("<f", struct.pack("<f", float(value)))[0]
    require(math.isfinite(value), "nonfinite observation interface")
    return value


def mean_f32(a, b):
    return f32(f32(f32(a) + f32(b)) * 0.5)


def tile_grid():
    return [(96 + 3196 * x // 11, 96 + 2024 * y // 7)
            for y in range(8) for x in range(12)]


def load_map():
    text = MAP.read_text(encoding="utf-8")
    for header in ("strehl-warpmap 1", "frames 299", "plane 3516x2344",
                   "reference 149", "resampler catmull-rom"):
        require(header in text.splitlines(), f"missing exact map header: {header}")
    maps = []
    for row in text.splitlines():
        fields = row.split("#", 1)[0].split()
        if not fields or not fields[0].isdigit():
            continue
        require(len(fields) == 6 and int(fields[0]) == len(maps) and fields[1] == "placed",
                "map source order/state mismatch")
        values = [struct.unpack(">d", bytes.fromhex(s))[0] for s in fields[2:]]
        require(all(math.isfinite(v) for v in values), "nonfinite held map")
        a, b = complex(*values[:2]), complex(*values[2:])
        require(abs(a) > 0, "singular held map")
        maps.append((a, b))
    require(len(maps) == 299, "incomplete held map")
    return maps


def pair_geometry(map_i, map_j, tile_origin):
    """Pure f64 map algebra; returned origins are physical original-sensor sites."""
    ai, bi = map_i
    aj, bj = map_j
    a = aj / ai
    b = 2 * bj - a * (2 * bi)
    tx, ty = tile_origin
    phases = {}
    for phase, offset in PHASE_OFFSETS.items():
        oi = (2 * tx + offset[0], 2 * ty + offset[1])
        c = complex(oi[0] + 127, oi[1] + 127)
        predicted = CENTER + a * (c - CENTER) + b
        oj = (offset[0] + 2 * round((predicted.real - 127 - offset[0]) / 2),
              offset[1] + 2 * round((predicted.imag - 127 - offset[1]) / 2))
        remainder = (predicted.real - oj[0] - 127, predicted.imag - oj[1] - 127)
        require(max(abs(v) for v in remainder) <= 1.0 + 1e-10,
                "even-origin proposal no longer leaves at most one native pixel")
        supported = all(0 <= o[0] and o[0] + 254 < WIDTH and
                        0 <= o[1] and o[1] + 254 < HEIGHT for o in (oi, oj))
        phases[phase] = {
            "phase": phase, "reference_origin_native_xy": list(oi),
            "moving_origin_native_xy": list(oj), "centroid_native_xy": [c.real, c.imag],
            "held_predicted_centroid_native_xy": [predicted.real, predicted.imag],
            "held_displacement_native_xy": [predicted.real - c.real, predicted.imag - c.imag],
            "held_patch_remainder_native_xy": list(remainder), "reader_seed_native_xy": [0, 0],
            "held_relative_correction_interval_native_xy": [[-2.0 - r, 2.0 - r] for r in remainder],
            "support_status": "SUPPORTED" if supported else "OUT_OF_ORIGINAL_SUPPORT",
            "reader": None,
        }
    return phases


def combine_tile(phases, power):
    """Same actual combination path for controls and the compact Rust interface."""
    key = f"p{power}"
    reasons, residuals, estimates, centers = [], {}, [], []
    for phase in ("G1", "G2"):
        item = phases[phase]
        reader = item["reader"]
        centers.append(item["centroid_native_xy"])
        if reader is None:
            reasons.append(f"{phase}:OUT_OF_ORIGINAL_SUPPORT")
            continue
        arm = reader[key]
        d = arm["displacement_native_xy"]
        residuals[phase] = [d[k] - item["held_displacement_native_xy"][k] for k in (0, 1)]
        estimates.append(arm)
        if not arm["accepted"]:
            reasons.extend(f"{phase}:{reason}" for reason in arm["refusals"])
            require(bool(arm["refusals"]), "reader refused without a retained reason")
    disagreement = None
    if len(residuals) == 2:
        disagreement = math.hypot(*(residuals["G1"][k] - residuals["G2"][k] for k in (0, 1)))
        if disagreement > AGREEMENT_NATIVE:
            reasons.append("GREEN_PHASE_DISAGREEMENT")
    observation = None
    if not reasons:
        require(len(estimates) == 2, "both accepted green phases required")
        pc = [(centers[0][k] + centers[1][k]) * 0.5 for k in (0, 1)]
        d = [mean_f32(estimates[0]["displacement_native_xy"][k],
                      estimates[1]["displacement_native_xy"][k]) for k in (0, 1)]
        observation = {"ux": f32((pc[0] - CENTER.real) * 0.5),
                       "uy": f32((pc[1] - CENTER.imag) * 0.5),
                       "dx": f32(d[0] * 0.5), "dy": f32(d[1] * 0.5),
                       "score": mean_f32(estimates[0]["score"], estimates[1]["score"])}
    return {"accepted": observation is not None,
            "status": "ACCEPTED_TWO_GREEN_OBSERVATION" if observation is not None else "REFUSED",
            "refusals": reasons, "held_relative_phase_residuals_native_xy": residuals,
            "phase_disagreement_native": disagreement, "observation": observation,
            "physical_error_identified": False}


def read_population():
    # The retained observer serializes pair traces in lexicographic (i,j) order.
    expected = sorted((i, i + span) for span in SPANS for i in range(299 - span))
    require(len(expected) == 2340, "fixed pair census drift")
    population = []
    grid = tile_grid()
    with PAIRS.open(encoding="utf-8") as stream:
        for ordinal, raw in enumerate(stream):
            row = json.loads(raw)
            require(ordinal < len(expected) and row["ordinal"] == ordinal and
                    (row["i"], row["j"]) == expected[ordinal], "observer pair order differs")
            core = row["core"]
            passes = core["fine_passes"]
            require(len(passes) == 1 and passes[0]["index"] == 0,
                    "frozen observer no longer has exactly the original fine-grid pass")
            tiles = passes[0]["tiles"]
            require(len(tiles) == 96, "observer tile census differs")
            for k, tile in enumerate(tiles):
                require(tile["ordinal"] == k and tuple(tile["origin"]) == grid[k] and
                        tile["size"] == 128, "observer grid/order differs")
                require([v["value"] for v in tile["fit_center"]] ==
                        [grid[k][0] + 64.0, grid[k][1] + 64.0], "observer center differs")
            population.append({"ordinal": ordinal, "i": row["i"], "j": row["j"],
                               "old_unavailable": row["unavailable"],
                               "old_termination": core["termination"],
                               "old_selected_fine_pass": core["selected_fine_pass"],
                               "old_tile_statuses": [t["status"] for t in tiles]})
    require(len(population) == 2340, "truncated observer population")
    return population


def validate_sources(manifest, order):
    require(manifest["status"] == "COMPLETE299_ORIGINAL_NATIVE_CFA_EXPORT" and
            manifest["complete"] and manifest["original_sensor_codes_preserved"] and
            manifest["source_count"] == 299 and manifest["active_wh"] == [WIDTH, HEIGHT] and
            manifest["active_origin_xy"] == [0, 0] and manifest["levels"] == [512, 15360],
            "original-cache provenance/geometry mismatch")
    require(manifest["physical_phase_order"] == ["R", "G1", "G2", "B"], "CFA phase order differs")
    require(len(order) == 299 and len(manifest["records"]) == 299, "source count differs")
    cache_root = (MANIFEST.parent / "frames").resolve()
    for i, (record, original) in enumerate(zip(manifest["records"], order)):
        require(record["index"] == i and record["source_id"] == i and original["index"] == i and
                record["original"] == original, "cache/original identity join differs")
        require(Path(original["path"]).name == f"DSC{i + 1:05d}.ARW", "original filename order differs")
        cache = record["cache"]
        require(Path(cache["path"]).resolve() == cache_root / f"rawler-{i:03d}.bin" and
                cache["bytes"] == 16 + WIDTH * HEIGHT * 2 and
                cache["header_u32le_yxhw"] == [0, 0, HEIGHT, WIDTH] and
                cache["payload_offset_bytes"] == 16 and cache["dtype"] == "<u2" and
                cache["shape"] == [HEIGHT, WIDTH] and cache["row_stride_samples"] == WIDTH and
                cache["original_active_xywh"] == [0, 0, WIDTH, HEIGHT], "cache format differs")
    noise = manifest["noise"]
    require(noise["phase_order"] == ["R", "G1", "G2", "B"] and noise["iso"] == 100 and
            noise["provenance"] == "Profile" and noise["prnu"] is None and
            noise["gain_bits4"] == [1047162535] * 4 and
            noise["read_variance_bits4"] == [1064087478] * 4 and
            noise["black4"] == [512] * 4 and noise["white"] == 15360, "injected noise contract differs")
    for key, bits in (("gain_dn_per_e4", 1047162535), ("read_variance_dn2_4", 1064087478)):
        require(all(struct.unpack("<I", struct.pack("<f", v))[0] == bits for v in noise[key]),
                "noise numeric values differ from declared f32 bits")


def input_snapshot(manifest, order):
    originals, caches = [], []
    for record, expected in zip(manifest["records"], order):
        p = Path(expected["path"])
        stat = p.stat()
        require(stat.st_size == expected["bytes"] and stat.st_mtime_ns == expected["mtime_ns"],
                f"original metadata changed: {p}")
        originals.append({"index": expected["index"], "path": str(p), "bytes": stat.st_size,
                          "mtime_ns": stat.st_mtime_ns,
                          "export_recorded_sha256_not_rehashed_here": expected["sha256"]})
        cache = record["cache"]
        ref = reference(cache["path"])
        require(ref["sha256"] == cache["sha256"] and ref["bytes"] == cache["bytes"],
                f"original-cache content differs: {cache['path']}")
        with Path(cache["path"]).open("rb") as stream:
            require(struct.unpack("<4I", stream.read(16)) == (0, 0, HEIGHT, WIDTH),
                    "original-cache header differs")
        caches.append({"index": record["index"], **ref})
    return {"original_metadata": originals, "cache_content_and_metadata": caches,
            "original_RAW_rehashed": False, "original_RAW_decoded": False}


def import_phase():
    spec = importlib.util.spec_from_file_location("insect_blur_phase_frozen_reader", PHASE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def process_pair(np, reader, noises, maps, manifest, pair):
    started = time.perf_counter()
    i, j = pair["i"], pair["j"]
    frames = [np.memmap(manifest["records"][index]["cache"]["path"], dtype="<u2", mode="r",
                        offset=16, shape=(HEIGHT, WIDTH)) for index in (i, j)]
    tiles, calls = [], 0
    try:
        for k, origin in enumerate(tile_grid()):
            tiles.append({"ordinal": k, "origin_guide_xy": list(origin),
                          "old_tile_status": pair["old_tile_statuses"][k],
                          "phases": pair_geometry(maps[i], maps[j], origin)})
        for phase in ("G1", "G2"):
            supported = [k for k, tile in enumerate(tiles)
                         if tile["phases"][phase]["support_status"] == "SUPPORTED"]
            for start in range(0, len(supported), 32):
                indices = supported[start:start + 32]
                geometries = [tiles[k]["phases"][phase] for k in indices]
                batches = []
                for frame, origin_key in zip(frames, ("reference_origin_native_xy", "moving_origin_native_xy")):
                    patches = []
                    for geometry in geometries:
                        x, y = geometry[origin_key]
                        patch = np.array(frame[y:y + 256:2, x:x + 256:2], dtype=np.uint16, copy=True)
                        require(patch.shape == (128, 128), "unexpected original phase patch shape")
                        patches.append(patch)
                    batches.append(np.stack(patches))
                records = reader.compare_batch(
                    batches[0], batches[1], noises[phase], phase=phase, seed_native_xy=(0, 0),
                    reference_origin_native_xy=[g["reference_origin_native_xy"] for g in geometries],
                    moving_origin_native_xy=[g["moving_origin_native_xy"] for g in geometries],
                    return_surfaces=False)
                require(len(records) == len(indices), "reader batch census differs")
                for index, result in zip(indices, records):
                    tiles[index]["phases"][phase]["reader"] = result
                calls += 1
        compact = []
        for tile in tiles:
            tile["combined"] = {f"p{power}": combine_tile(tile["phases"], power) for power in (1, 2)}
            compact.append({"ordinal": tile["ordinal"],
                            **{arm: tile["combined"][arm]["observation"] for arm in ("p1", "p2")}})
        base = {"schema": 1, "ordinal": pair["ordinal"], "i": i, "j": j}
        rich = {**base, "old_unavailable": pair["old_unavailable"],
                "old_termination": pair["old_termination"],
                "old_selected_fine_pass": pair["old_selected_fine_pass"],
                "tiles": tiles, "reader_batch_calls": calls,
                "elapsed_seconds": time.perf_counter() - started}
        return rich, {**base, "tiles": compact}
    finally:
        for frame in frames:
            frame._mmap.close()


def run(args):
    started = time.perf_counter()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    try:
        dependencies = list(PINS) + [Path(__file__).resolve(), HERE / "brief.md",
                                    HERE / "actual-reader-notes.md"]
        bindings = [reference(p) for p in dependencies]
        for ref in bindings:
            expected = PINS.get(Path(ref["path"]))
            require(expected is None or ref["sha256"] == expected, f"pinned source/input changed: {ref['path']}")
        manifest, order = (json.loads(p.read_text(encoding="utf-8")) for p in (MANIFEST, ORDER))
        validate_sources(manifest, order)
        observer = json.loads(OBSERVER.read_text(encoding="utf-8"))
        require(observer["status"] == "COMPLETE299_INSECT_PLACEMENT_OBSERVATION" and
                observer["pair_count"] == 2340 and observer["fine_tile_count"] == 224640 and
                observer["spans"] == list(SPANS), "observer receipt census differs")
        maps, population = load_map(), read_population()
        selected = [p for p in population if args.mode == "full" or (p["i"], p["j"]) in COST_PAIRS]
        require(len(selected) == (2340 if args.mode == "full" else 6), "selected fixed population differs")
        save(out / "population.json", {"complete_observer_pair_count": len(population), "spans": SPANS,
             "mode": args.mode, "selected": [{k: p[k] for k in ("ordinal", "i", "j")} for p in selected],
             "tile_origins_guide_xy": tile_grid(), "selection_uses_old_fit_outcome": False})
        before = input_snapshot(manifest, order)
        save(out / "inputs-before.json", before)
        binding_seconds = time.perf_counter() - started

        # Imports and all numerical work occur only when root executes this worker.
        import numpy as np
        import torch
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        require(torch.cuda.is_available(), "CUDA required for bounded full graph")
        device = torch.cuda.current_device()
        properties = torch.cuda.get_device_properties(device)
        require(properties.total_memory >= GPU_LIMIT, "device is smaller than fixed6GiB limit")
        torch.cuda.set_per_process_memory_fraction(GPU_LIMIT / properties.total_memory, device)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.cuda.reset_peak_memory_stats(device)
        phase_module = import_phase()
        reader = phase_module.Reader(torch, device="cuda")
        noise = manifest["noise"]
        noises = {phase: phase_module.PhaseNoise(noise["gain_dn_per_e4"][k],
                  noise["read_variance_dn2_4"][k], noise["black4"][k], noise["white"])
                  for phase, k in (("G1", 1), ("G2", 2))}
        census = {"phase_support": Counter(), "phase_arm_status": Counter(),
                  "phase_arm_refusal": Counter(), "combined_status": Counter(),
                  "combined_refusal": Counter()}
        pair_times, batch_count = [], 0
        campaign_start = time.perf_counter()
        with (out / "pairs.jsonl").open("x", encoding="utf-8", newline="\n") as rich_file, \
                (out / "observations.jsonl").open("x", encoding="utf-8", newline="\n") as observations:
            for completed, pair in enumerate(selected, 1):
                rich, compact = process_pair(np, reader, noises, maps, manifest, pair)
                for tile in rich["tiles"]:
                    for phase, item in tile["phases"].items():
                        census["phase_support"][f"{phase}:{item['support_status']}"] += 1
                        for arm in ("p1", "p2"):
                            r = item["reader"][arm] if item["reader"] is not None else {
                                "status": "OUT_OF_ORIGINAL_SUPPORT", "refusals": ["OUT_OF_ORIGINAL_SUPPORT"]}
                            census["phase_arm_status"][f"{phase}:{arm}:{r['status']}"] += 1
                            for reason in r["refusals"]:
                                census["phase_arm_refusal"][f"{phase}:{arm}:{reason}"] += 1
                    for arm, result in tile["combined"].items():
                        census["combined_status"][f"{arm}:{result['status']}"] += 1
                        for reason in result["refusals"]:
                            census["combined_refusal"][f"{arm}:{reason}"] += 1
                line(rich_file, rich)
                line(observations, compact)
                rich_file.flush()
                observations.flush()
                pair_times.append({"ordinal": pair["ordinal"], "i": pair["i"], "j": pair["j"],
                                   "seconds": rich["elapsed_seconds"]})
                batch_count += rich["reader_batch_calls"]
                require(torch.cuda.max_memory_allocated(device) <= GPU_LIMIT and
                        torch.cuda.max_memory_reserved(device) <= GPU_LIMIT, "GPU memory high-water exceeds bound")
                print(json.dumps({"event": "pair_complete", "completed": completed, "total": len(selected),
                      **pair_times[-1]}, allow_nan=False), flush=True)
        torch.cuda.synchronize(device)
        campaign_seconds = time.perf_counter() - campaign_start
        after = input_snapshot(manifest, order)
        save(out / "inputs-after.json", after)
        after_bindings = [reference(p) for p in dependencies]
        require(before == after and bindings == after_bindings, "input or source binding changed during campaign")
        total = len(selected) * 96
        require(sum(census["phase_support"].values()) == total * 2 and
                sum(census["phase_arm_status"].values()) == total * 4 and
                sum(census["combined_status"].values()) == total * 2, "output census incomplete")
        receipt = {
            "schema": 1, "status": "COMPLETE_INSECT_BLUR_PHASE_ACTUAL", "complete": True,
            "mode": args.mode, "source_count": 299,
            "used_source_count": len({p[k] for p in selected for k in ("i", "j")}),
            "pair_count": len(selected), "tile_count": total, "phase_slot_count": total * 2,
            "phase_arm_record_count": total * 4, "reader_batch_count": batch_count,
            "census": census, "pair_timings": pair_times,
            "binding_before_seconds": binding_seconds, "pair_campaign_seconds": campaign_seconds,
            "total_seconds": time.perf_counter() - started,
            "reader": reader.metadata(), "injected_noise": noise,
            "initializer": "held global map; independently rounded physical phase origins; zero local seed",
            "green_agreement_native": AGREEMENT_NATIVE,
            "observation_gauge": "source-i mean physical green centroid; centered native/2; f32 guide displacements",
            "combined_score_role": "equal phase-score mean, diagnostic only; not a fit weight",
            "all_original_pair_ordinals_preserved": True, "all_original_tile_ordinals_preserved": True,
            "old_refusals_used_to_select": False, "held_edges_inserted": False,
            "source_rgb": False, "interpolation": False, "aligned_frame_volume": False,
            "RAW_reads": 0, "RAW_decodes": 0, "original_RAW_content_rehashed": False,
            "original_RAW_metadata_unchanged": True,
            "export_receipt_original_RAW_content_verification_reused": True,
            "retained_input_bytes_and_metadata_unchanged": True, "source_bindings_unchanged": True,
            "worker_count": 4, "interop_threads": 1, "gpu_device": properties.name,
            "torch_version": torch.__version__, "numpy_version": np.__version__,
            "gpu_limit_bytes": GPU_LIMIT, "peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(device),
            "source_bindings": bindings, "source_bindings_after": after_bindings,
            "artifacts": [reference(out / name) for name in
                          ("population.json", "inputs-before.json", "inputs-after.json", "pairs.jsonl", "observations.jsonl")],
            "physical_error_identified": False, "quality_claim": False, "photographic_admission": False,
        }
        save(out / "receipt.json", receipt)
        return receipt
    except BaseException as error:
        save(out / "error.json", {"schema": 1, "complete": False, "mode": args.mode,
             "exception": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
             "elapsed_seconds": time.perf_counter() - started, "quality_claim": False})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("cost", "full"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    result = run(arguments)
    print(json.dumps({"status": result["status"], "mode": result["mode"],
                      "pair_count": result["pair_count"], "complete": True}), flush=True)
