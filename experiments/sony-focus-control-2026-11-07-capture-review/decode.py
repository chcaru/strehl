"""Decode all frames read-only, cache original G1 CFA samples, and cross-check two decodes."""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import rawpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/sony-focus-control-capture-review"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    inventory = json.loads((OUT / "inventory.json").read_text())
    cache = OUT / "green-cfa"
    cache.mkdir(exist_ok=True)
    rows, checks = [], []
    for run_index, run in enumerate(inventory["sessions"], 1):
        for frame in run["frames"]:
            ordinal = frame["ordinal"]
            target = cache / f"run-{run_index}-{ordinal:02d}.npy"
            with rawpy.imread(frame["path"]) as raw:
                visible = raw.raw_image_visible.copy()
                assert visible.dtype == np.uint16
                assert raw.raw_pattern.tolist() == [[0, 1], [3, 2]]
                assert list(raw.black_level_per_channel) == [512] * 4
                info = {"raw_sizes": raw.sizes._asdict(), "black": list(raw.black_level_per_channel),
                        "libraw_white": raw.white_level, "camera_wb": raw.camera_whitebalance}
            if ordinal == 1:
                independent = OUT / f"run-{run_index}-independent.u16"
                command = [str(OUT / "raw-check.exe"), frame["path"], str(independent)]
                result = subprocess.run(command, capture_output=True, text=True, check=True)
                shape = json.loads(result.stdout)
                other = np.memmap(independent, mode="r", dtype="<u2", shape=(shape["height"], shape["width"]))
                h, w = visible.shape
                equal = np.array_equal(visible, other[:h, :w])
                checks.append({"run": run_index, "command": command, "stdout": result.stdout,
                               "stderr": result.stderr, "rawpy_shape": [h, w], "strehl_shape": shape,
                               "common_active_samples": visible.size, "all_equal": equal,
                               "executable_sha256": sha(OUT / "raw-check.exe")})
                assert equal, "Independent decoders disagree in the common active area"
            green = visible[0::2, 1::2].copy()
            np.save(target, green, allow_pickle=False)
            rows.append({"run": run_index, "ordinal": ordinal, "cache": str(target), **info,
                         "minimum": int(visible.min()), "maximum": int(visible.max()),
                         "at_or_above_sony_white": int(np.count_nonzero(visible >= 15360)),
                         "green_mean_dn": float(green.mean(dtype=np.float32))})
            if ordinal % 12 == 0 or ordinal == 73:
                print(f"Run {run_index}: decoded {ordinal}/73", flush=True)
    result = {"source_sha256": sha(Path(__file__)), "independent_decode": checks,
              "cfa_phase": "G1: active x=1+2*u, y=2*v; no white balance or demosaic",
              "frames": rows}
    (OUT / "decode.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
