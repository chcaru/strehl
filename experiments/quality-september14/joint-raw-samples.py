"""Retain nine original CFA patches for a bounded, native 1x joint reconstruction.

No demosaic, resampling, focus election, or source-file writes. Geometry is the
existing reference149 map, not asserted ground truth. The selected contiguous
window is prospective; equal focus is not assumed to have been established.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "joint-raw-samples-2"
FRAMES = list(range(145, 154))
ORIGIN = (1332, 1104)
SHAPE = (392, 392)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def child():
    import numpy as np
    import rawpy
    clib = module("joint_raw_map", ROOT / "experiments/M-PHASE0-PHASE/src/clib.py")
    map_path = HERE / "chip-baseline-1/chip.warpmap.txt"
    warp = clib.parse_warpmap(str(map_path))
    assert warp["reference_index"] == 149 and warp["plane"] == (3516, 2344)
    old = json.loads((HERE / "matched-chip-on-1/receipt.json").read_text())
    independent = json.loads((HERE / "chip-source-review-1/receipt.json").read_text())
    libraw_shape = tuple(independent["decoder"]["visible_shape"])
    assert libraw_shape == (4688, 7028)  # Four columns narrower than rawler; same crop coordinates, checked below.
    directory = Path(old["configuration"]["dir"])
    decoder = ROOT / "experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe"
    center = complex(3516, 2344)  # Full native coordinates: W/2, H/2.
    x, y = ORIGIN
    h, w = SHAPE
    corners = np.array([complex(x, y), complex(x+w-1, y),
                        complex(x, y+h-1), complex(x+w-1, y+h-1)])
    records = []
    for index in FRAMES:
        a, b = warp["placements"][index]
        mapped = center + a * (corners-center) + 2*b
        x0 = 2*int(np.floor((mapped.real.min()-8)/2))
        y0 = 2*int(np.floor((mapped.imag.min()-8)/2))
        x1 = 2*int(np.ceil((mapped.real.max()+9)/2))
        y1 = 2*int(np.ceil((mapped.imag.max()+9)/2))
        assert 0 <= x0 < x1 <= libraw_shape[1] and 0 <= y0 < y1 <= libraw_shape[0]
        source = directory / f"DSC{index+1:05d}.ARW"
        before = (source.stat().st_size, source.stat().st_mtime_ns)
        with rawpy.imread(str(source)) as raw:
            assert raw.raw_image_visible.shape == libraw_shape
            assert raw.raw_pattern.tolist() == [[0, 1], [3, 2]]
            patch = raw.raw_image_visible[y0:y1, x0:x1].copy()
            black = list(raw.black_level_per_channel)
            metadata = dict(black=black, white=raw.white_level,
                            camera_wb=raw.camera_whitebalance)
            assert black == [512]*4 and raw.white_level == 16383
        np.save(OUT/f"frame-{index}-cfa.npy", patch, allow_pickle=False)
        result = subprocess.run([str(decoder), str(source), str(OUT), str(index),
                                 str(y0), str(x0), str(y1-y0), str(x1-x0)],
                                capture_output=True, text=True, timeout=30, check=True)
        (OUT/f"frame-{index}-secondary.log").write_text(result.stdout+result.stderr, encoding="utf-8")
        blob = (OUT/f"rawler-{index}.bin").read_bytes()
        assert struct.unpack("<4I", blob[:16]) == (y0, x0, y1-y0, x1-x0)
        other = np.frombuffer(blob, dtype="<u2", offset=16).reshape(patch.shape)
        different = int(np.count_nonzero(patch != other))
        assert different == 0, "independent RAW decoder mismatch"
        assert (source.stat().st_size, source.stat().st_mtime_ns) == before
        records.append(dict(index=index, source=str(source), bytes=before[0], mtime_ns=before[1],
                            source_xywh=[x0, y0, x1-x0, y1-y0],
                            a=[a.real, a.imag], b_plane=[b.real, b.imag],
                            raw_u16_sha256=hashlib.sha256(patch.tobytes()).hexdigest(),
                            independently_decoded_different_sensels=different,
                            exact_16383=int(np.count_nonzero(patch == 16383)), metadata=metadata))
        print(f"frame {index}: original CFA retained; independent decoder exact", flush=True)
    gain = np.float32(100)/np.float32(436.8)
    read_e = np.float32(4.20)
    save(OUT/"receipt.json", dict(status="ORIGINAL_CFA_PATCHES_READY", frames=records,
        reference_index=149, target_origin_native=list(ORIGIN), target_shape=list(SHAPE),
        native_sensor_shape=[4688, 7032], libraw_visible_shape=list(libraw_shape),
        wb_bits=old["wb_bits"], levels=old["levels"],
        map_sha256=hashlib.sha256(map_path.read_bytes()).hexdigest(),
        noise=dict(provenance="Shipping A7C2 profile, ISO100, Corrections::SHIPPED; injected once",
                   gain_dn_per_e=float(gain), read_noise_e=float(read_e),
                   read_noise_dn=float(read_e*gain),
                   source="crates/strehl-core/src/profile.rs::A7C2/noise_model; noise.rs::variance",
                   profile_sha256=hashlib.sha256((ROOT/"crates/strehl-core/src/profile.rs").read_bytes()).hexdigest()),
        scope="Nine fixed contiguous observations; original CFA only. No equal-focus or registration-accuracy claim. No CA correction; reference149 native sensor gauge. No 2x output.",
        rawpy=rawpy.__version__, libraw=list(rawpy.libraw_version),
        source_metadata_unchanged=True))
    assert sum(p.stat().st_size for p in OUT.iterdir() if p.is_file()) < 16 << 20


def main():
    if "--child" in sys.argv:
        child()
        return
    OUT.mkdir(exist_ok=False)
    bounded = module("joint_raw_bounded", ROOT / "experiments/m193c-output-grid/bounded-process.py")
    env, _ = bounded.clean_environment(dict(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                                           RAYON_NUM_THREADS="1").items())
    api = bounded.load_job_api(bounded.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    command = [sys.executable, "-I", "-B", "-X", "faulthandler", str(Path(__file__)), "--child"]
    result = bounded.run(command, env, ROOT, OUT/"process.log", api=api,
                         wall_seconds=120, cpu_seconds=90, log_bytes=1 << 20, committed_bytes=2 << 30)
    save(OUT/"process.json", dict(command=command, result=result))
    print(json.dumps(dict(exit_code=result["exit_code"], error=result["error"],
                          accounting=result["job_accounting"])))
    assert result["exit_code"] == 0 and result["error"] is None and result["terminal_job_accounting"]


if __name__ == "__main__":
    main()
