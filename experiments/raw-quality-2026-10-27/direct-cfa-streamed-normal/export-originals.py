"""Root-authorized sequential original-u16 export; never align or develop samples."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import time
import traceback


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "outputs/raw-quality-2026-10-26"
ORDER = BASE / "weevil-107-baseline/input-order.json"
MAP = BASE / "weevil-107-baseline/alignment.txt"
METADATA = BASE / "weevil-107-tiff-export/receipt.json"
SENSOR_METADATA = BASE / "weevil-107-sensor-ca-off/sensor-master.tiff.json"
NATIVE = Path("C:/dev/blog/death-of-software/projects/strehl/experiments/m61-ptc-high-iso/decode-check")
EXE = NATIVE / "target/release/m61-decode-check.exe"
NATIVE_SOURCE = NATIVE / "src/main.rs"
WIDTH, HEIGHT, BLACK, WHITE = 7032, 4688, 512, 15360
EXPECTED = {
    ORDER: "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f",
    MAP: "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225",
    METADATA: "461ecb3a8e44a82005ed6883718aa85276a74a2ebfca31fb0628809c4ba315a0",
    SENSOR_METADATA: "e22ad2fad5ac7307a4560ccee4b0ad232edf1dc9449fdce7057022bff9341f21",
    EXE: "ecf20e1b1e639fc3b86fe82d26a3e3ca02fd326549aa6353e80ad4480682d89d",
    NATIVE_SOURCE: "62343abc6f479353a198d73762991ea4f0b5de71274fa546e875a3aa27805fcb",
}
INDEPENDENT_CACHE_SHA = {
    0: "1936869702bcbf8ae01ff4437dac0b2c715609edeaeb7ed442b2f32f4683c474",
    149: "15c33bdd558df9b4f9a303b294e3a6504ba14f1ef4d71cf8c52888111c50667f",
    298: "c1e9c537dae84fad843fd9eaf80ba1dc15f1316bd436c04d1ed2f9ea8d87f2ca",
}
PHASES = (("R", 0, 0), ("G1", 1, 0), ("G2", 0, 1), ("B", 1, 1))


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


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def original_identity(record, hash_content):
    path = Path(record["path"])
    s = path.stat()
    require(s.st_size == record["bytes"] and s.st_mtime_ns == record["mtime_ns"],
            "original metadata changed: " + str(path))
    if hash_content:
        require(ref(path)["sha256"] == record["sha256"], "original content changed: " + str(path))
        after = path.stat()
        require(after.st_size == s.st_size and after.st_mtime_ns == s.st_mtime_ns,
                "original metadata changed during hash: " + str(path))
    return {**record, "metadata_verified": True, "content_hash_verified": hash_content}


def validate_metadata(order):
    require(len(order) == 299, "exact299 originals required")
    previous = json.loads(METADATA.read_text(encoding="utf-8"))
    require(previous["status"] == "299_UNALIGNED_NATIVE_RGB16_DEVELOPED"
            and previous["input_content_and_metadata_unchanged"] is True
            and previous["input_order_sha256"] == EXPECTED[ORDER]
            and previous["active_wh"] == [WIDTH, HEIGHT]
            and previous["levels"] == [BLACK, WHITE]
            and len(previous["frames"]) == 299, "prior native metadata evidence differs")
    for index, record in enumerate(order):
        require(record["index"] == index and Path(record["path"]).name == f"DSC{index+1:05}.ARW",
                "source identity/order differs")
        old = previous["frames"][index]
        require(old["ordinal"] == index and old["input"] == record
                and old["raw_active_xywh"] == [0, 0, WIDTH, HEIGHT]
                and old["raw_buffer_wh"] == [7168, 5120]
                and old["input_wb_bits"] == previous["wb_bits"], "prior per-source metadata binding differs")
    return previous


def phase_statistics(np, data):
    result = []
    for name, px, py in PHASES:
        plane = data[py::2, px::2]
        result.append({"phase": name, "offset_xy": [px, py], "samples": int(plane.size),
                       "min_code": int(plane.min()), "max_code": int(plane.max()),
                       "codes_below_black": int(np.count_nonzero(plane < BLACK)),
                       "codes_at_or_above_working_white": int(np.count_nonzero(plane >= WHITE)),
                       "codes_equal_16383": int(np.count_nonzero(plane == 16383)),
                       "codes_above_16383": int(np.count_nonzero(plane > 16383))})
    return result


def overlap_check(np, index, data, original, cache_bindings):
    folder = ROOT / f"experiments/raw-quality-2026-10-26/photo-review/source-{index}"
    path, receipt_path = folder / "active-cfa-u16.npy", folder / "decode-receipt.json"
    evidence = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(evidence["index"] == index and evidence["original"] == original
            and evidence["active_shape"] == [HEIGHT, 7028]
            and evidence["metadata"]["pattern"] == [[0, 1], [3, 2]]
            and evidence["metadata"]["color_desc"] == "RGBG"
            and evidence["independent_decode"]["differing_sensels"] == 0,
            "independent RawPy evidence differs")
    reference = np.load(path, mmap_mode="r", allow_pickle=False)
    try:
        require(reference.dtype == np.dtype("<u2") and reference.shape == (HEIGHT, 7028),
                "independent cache type/shape differs")
        native_hash, reference_hash, differing = hashlib.sha256(), hashlib.sha256(), 0
        for y in range(0, HEIGHT, 128):
            a, b = data[y:y+128, :7028], reference[y:y+128]
            differing += int(np.count_nonzero(a != b))
            native_hash.update(a.tobytes(order="C"))
            reference_hash.update(b.tobytes(order="C"))
        result = {"index": index, "comparison_xywh": [0, 0, 7028, HEIGHT],
                  "native_overlap_pixel_sha256": native_hash.hexdigest(),
                  "rawpy_overlap_pixel_sha256": reference_hash.hexdigest(), "differing_sensels": differing,
                  "rawpy_cache": cache_bindings[index][0], "rawpy_receipt": cache_bindings[index][1],
                  "new_RAW_reads_for_independent_check": 0,
                  "extra_columns_xywh": [7028, 0, 4, HEIGHT], "extra_columns_independently_verified": False}
        require(differing == 0 and native_hash.digest() == reference_hash.digest()
                and reference_hash.hexdigest() == evidence["cfa_pixel_sha256"],
                "native export differs from independent original cache")
        return result
    finally:
        reference._mmap.close()


def validate_log(text, expected_path):
    patterns = (r"^camera\s*:\s*ILCE-7CM2\s*$", r"^stride\s*:\s*7168\s*$",
                r"^buffer h\s*:\s*5120\s*$", r"^active\s*:\s*7032x4688 at \(0,0\)\s*$",
                r"^levels\s*:\s*black 512 white 15360\s*$")
    for pattern in patterns:
        require(re.search(pattern, text, flags=re.MULTILINE) is not None,
                "native decoder log violates metadata contract: " + pattern)
    written = re.findall(r"^wrote\s*:\s*(.+)$", text, flags=re.MULTILINE)
    require(len(written) == 1 and Path(written[0].strip()).resolve() == expected_path.resolve(),
            "native output path differs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / "outputs").resolve()) and not out.exists(),
            "output must be fresh below worktree outputs")
    out.mkdir()
    started = time.perf_counter()
    records = []
    try:
        import numpy as np
        bindings = [ref(p) for p in (Path(__file__), HERE / "export-notes.md", HERE / "brief.md",
                                    *EXPECTED.keys())]
        for path, expected in EXPECTED.items():
            require(ref(path)["sha256"] == expected, "frozen producer/evidence changed: " + str(path))
        cache_bindings = {}
        for index, expected in INDEPENDENT_CACHE_SHA.items():
            folder = ROOT / f"experiments/raw-quality-2026-10-26/photo-review/source-{index}"
            pair = [ref(folder / "active-cfa-u16.npy"), ref(folder / "decode-receipt.json")]
            require(pair[0]["sha256"] == expected, "independent RawPy cache changed")
            cache_bindings[index] = pair
            bindings.extend(pair)
        save(out / "source-bindings.json", bindings)
        order = json.loads(ORDER.read_text(encoding="utf-8"))
        metadata = validate_metadata(order)
        preflight_started = time.perf_counter()
        before = [original_identity(r, True) for r in order]
        save(out / "originals-before.json", before)
        preflight_seconds = time.perf_counter() - preflight_started
        frames, logs = out / "frames", out / "logs"
        frames.mkdir()
        logs.mkdir()
        for index, original in enumerate(order):
            frame_started = time.perf_counter()
            original_identity(original, False)
            output = frames / f"rawler-{index:03}.bin"
            require(not output.exists(), "refusing to overwrite original-CFA cache")
            command = [str(EXE), original["path"], str(frames), f"{index:03}", "0", "0", str(HEIGHT), str(WIDTH)]
            save(logs / f"source-{index:03}-invocation.json", {"command": command, "timeout_seconds": 30,
                 "single_decoder": True, "source": original, "executable_sha256": EXPECTED[EXE]})
            decode_started = time.perf_counter()
            result = subprocess.run(command, capture_output=True, timeout=30, check=False)
            decode_seconds = time.perf_counter() - decode_started
            (logs / f"source-{index:03}-stdout.txt").write_bytes(result.stdout)
            (logs / f"source-{index:03}-stderr.txt").write_bytes(result.stderr)
            save(logs / f"source-{index:03}-exit.json", {"exit_code": result.returncode,
                 "seconds": decode_seconds, "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr)})
            require(result.returncode == 0, "native decoder failed at source " + str(index))
            require(len(result.stdout) + len(result.stderr) <= 65536, "unexpected native decoder log size")
            validate_log(result.stdout.decode("utf-8", errors="strict"), output)
            require(output.stat().st_size == 16 + WIDTH * HEIGHT * 2, "wrong native cache byte count")
            with output.open("rb") as f:
                header = struct.unpack("<4I", f.read(16))
            require(header == (0, 0, HEIGHT, WIDTH), "wrong original-sensor cache header")
            data = np.memmap(output, dtype="<u2", mode="r", offset=16, shape=(HEIGHT, WIDTH))
            try:
                statistics = phase_statistics(np, data)
                require(sum(p["samples"] for p in statistics) == WIDTH * HEIGHT, "phase census incomplete")
                extra = phase_statistics(np, data[:, 7028:])
                independent = overlap_check(np, index, data, original, cache_bindings) if index in cache_bindings else None
            finally:
                data._mmap.close()
            original_identity(original, False)
            record = {"index": index, "source_id": index, "original": original,
                "cache": {**ref(output), "header_u32le_yxhw": list(header), "payload_offset_bytes": 16,
                          "dtype": "<u2", "shape": [HEIGHT, WIDTH], "row_stride_samples": WIDTH,
                          "original_active_xywh": [0, 0, WIDTH, HEIGHT]},
                "phase_statistics": statistics, "extra_native_columns_statistics": extra,
                "extra_native_columns_origin_xy": [7028, 0], "independent_overlap": independent,
                "native_log": ref(logs / f"source-{index:03}-stdout.txt"),
                "native_exit": ref(logs / f"source-{index:03}-exit.json"),
                "decode_seconds": decode_seconds, "total_source_seconds": time.perf_counter() - frame_started}
            save(out / f"source-{index:03}.json", record)
            records.append(record)
            print(json.dumps({"completed": len(records), "source_id": index,
                  "codes_at_or_above_working_white": sum(p["codes_at_or_above_working_white"] for p in statistics),
                  "seconds": record["total_source_seconds"]}), flush=True)
        postflight_started = time.perf_counter()
        after = [original_identity(r, True) for r in order]
        save(out / "originals-after.json", after)
        postflight_seconds = time.perf_counter() - postflight_started
        require(before == after and len(records) == 299, "incomplete or modified original population")
        for binding in bindings:
            require(ref(binding["path"]) == binding, "bound input/producer changed: " + binding["path"])
        # Preserve the injected native f32 profile operation order, not a private estimate.
        gain = np.float32(np.float32(100.0) / np.float32(436.8))
        read_e = np.float32(4.2)
        read_dn = np.float32(read_e * gain)
        read_variance = np.float32(read_dn * read_dn)
        bits = lambda v: int(np.asarray(v, dtype="<f4").view("<u4"))
        noise = {"phase_order": [p[0] for p in PHASES], "iso": 100, "provenance": "Profile",
                 "gain_dn_per_e4": [float(gain)] * 4, "gain_bits4": [bits(gain)] * 4,
                 "read_noise_e4": [float(read_e)] * 4, "read_noise_e_bits4": [bits(read_e)] * 4,
                 "read_variance_dn2_4": [float(read_variance)] * 4,
                 "read_variance_bits4": [bits(read_variance)] * 4,
                 "black4": [BLACK] * 4, "white": WHITE, "prnu": None,
                 "formula": "gain*max(code-black,0)+(read_e*gain)^2; native f32; no quantization addition"}
        receipt = {"schema": 1, "status": "COMPLETE299_ORIGINAL_NATIVE_CFA_EXPORT", "complete": True,
                   "mechanical_pass": True, "quality_claim": False, "photographic_admission": False,
                   "source_count": 299, "RAW_decodes": 299, "decoder_parallelism": 1,
                   "input_order": ref(ORDER), "held_map": ref(MAP), "metadata_evidence": ref(METADATA),
                   "sources_before": ref(out / "originals-before.json"), "sources_after": ref(out / "originals-after.json"),
                   "original_bytes_and_metadata_unchanged": True, "source_bindings_unchanged": True,
                   "original_sensor_codes_preserved": True, "unaligned": True, "developed": False,
                   "no_mask_or_clipping_applied_to_cache": True, "no_new_independent_RAW_decodes": True,
                   "physical_phase_order": [p[0] for p in PHASES], "physical_phase_offsets_xy": [[p[1], p[2]] for p in PHASES],
                   "measurement_channel_map": [0, 1, 1, 2], "active_wh": [WIDTH, HEIGHT], "active_origin_xy": [0, 0],
                   "levels": [BLACK, WHITE], "noise": noise, "wb_bits": metadata["wb_bits"],
                   "xyz_to_cam_bits": metadata["xyz_to_cam_bits"], "records": records,
                   "independent_overlap_indices": list(INDEPENDENT_CACHE_SHA),
                   "extra_four_columns_independent_verification": False,
                   "statistics_meaning": "codes>=working white mark planned omitted observations, not proof of the physical clipping mechanism; stored codes are untouched",
                   "all_cache_bytes": sum(r["cache"]["bytes"] for r in records),
                   "preflight_hash_seconds": preflight_seconds, "postflight_hash_seconds": postflight_seconds,
                   "wall_seconds": time.perf_counter() - started, "clock": vars(time.get_clock_info("perf_counter")),
                   "numpy": np.__version__, "python": sys.version,
                   "scope": "Original-sensor storage bridge only; no alignment, MHC, RGB conversion, noise fitting or reconstruction."}
        save(out / "receipt.json", receipt)
    except BaseException as error:
        save(out / "failure.json", {"status": "FAILED_ORIGINAL_NATIVE_CFA_EXPORT", "complete": False,
             "quality_claim": False, "completed_sources": len(records), "error": repr(error),
             "traceback": traceback.format_exc(), "wall_seconds": time.perf_counter() - started,
             "partial_outputs_retained": True})
        raise


if __name__ == "__main__":
    main()
