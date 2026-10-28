"""Bounded original source inspection, explicitly no sharpness-selected frame."""
from pathlib import Path
import hashlib
import json
import subprocess
import struct
import sys

import numpy as np
import rawpy


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-baseline"
SECONDARY = Path("C:/dev/blog/death-of-software/projects/strehl/experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = int(sys.argv[1])
    assert index == 149, "only the non-sharpness-selected alignment anchor is allocated by this script"
    out = HERE / f"source-{index}"
    out.mkdir(exist_ok=False)
    original = json.loads((BASE / "input-order.json").read_text())[index]
    source = Path(original["path"])
    assert sha(source) == original["sha256"]
    assert source.stat().st_mtime_ns == original["mtime_ns"]
    with rawpy.imread(str(source)) as raw:
        cfa = raw.raw_image_visible.copy()
        metadata = {"pattern": raw.raw_pattern.tolist(), "color_desc": raw.color_desc.decode("ascii"),
                    "black": list(raw.black_level_per_channel), "white": raw.white_level,
                    "camera_wb": list(raw.camera_whitebalance),
                    "daylight_wb": list(raw.daylight_whitebalance),
                    "sizes": str(raw.sizes), "rawpy_version": rawpy.__version__,
                    "libraw_version": list(rawpy.libraw_version)}
    assert cfa.dtype == np.uint16
    np.save(out / "active-cfa-u16.npy", cfa, allow_pickle=False)
    h, w = cfa.shape
    command = [str(SECONDARY), str(source), str(out), str(index), "0", "0", str(h), str(w)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    (out / "secondary.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    rawler = out / f"rawler-{index}.bin"
    blob = rawler.read_bytes()
    assert struct.unpack("<4I", blob[:16]) == (0, 0, h, w)
    independent = np.frombuffer(blob, dtype="<u2", offset=16).reshape(h, w)
    differing = int(np.count_nonzero(cfa != independent))
    assert differing == 0, f"independent decode differs at {differing} pixels"
    assert sha(source) == original["sha256"] and source.stat().st_mtime_ns == original["mtime_ns"]
    receipt = {"index": index, "selection": "Alignment anchor149 chosen before original sensor pixels were viewed; not a focus maximum.",
               "original": original, "raw_decodes_unique_originals_this_lane": 1,
               "active_shape": [h, w], "metadata": metadata,
               "persisted_cfa": {"path": str(out / "active-cfa-u16.npy"), "sha256": sha(out / "active-cfa-u16.npy")},
               "cfa_pixel_sha256": hashlib.sha256(cfa.astype("<u2").tobytes()).hexdigest(),
               "independent_decode": {"command": command, "exit_code": result.returncode,
                                      "executable_sha256": sha(SECONDARY), "differing_sensels": differing},
               "script_sha256": sha(Path(__file__).resolve()), "original_hash_and_mtime_unchanged": True}
    (out / "decode-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"index": index, "active_shape": [h, w], "metadata": metadata, "independent_differing_sensels": differing}))


if __name__ == "__main__":
    main()
