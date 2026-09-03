"""Commission the RAW loader contract without measuring sharpness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rawpy


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
OUT = ROOT / "out"
STACK = Path(
    r"D:\personal\macro\requests\30-calibration-grid"
    r"\calibration-grid-1-sw4-cpl"
)
EXPECTED_RAWPY = {
    "shape": [4688, 7028],
    "dtype": "uint16",
    "pattern": [[0, 1], [3, 2]],
    "color_desc": "RGBG",
    "black_levels": [512.0, 512.0, 512.0, 512.0],
    "container_white": 16383.0,
}


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(memoryview(np.ascontiguousarray(array))).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> tuple[np.ndarray, dict]:
    with rawpy.imread(str(path)) as raw:
        mosaic = np.array(raw.raw_image_visible, copy=True)
        pattern = (
            None
            if raw.raw_pattern is None
            else np.array(raw.raw_pattern, copy=True).tolist()
        )
        metadata = {
            "shape": list(mosaic.shape),
            "dtype": str(mosaic.dtype),
            "pattern": pattern,
            "color_desc": bytes(raw.color_desc)
            .decode("ascii", errors="replace")
            .rstrip("\x00"),
            "black_levels": [float(x) for x in raw.black_level_per_channel],
            "container_white": float(raw.white_level),
        }
    return mosaic, metadata


def plane_summaries(mosaic: np.ndarray) -> dict:
    names = {
        "R": mosaic[0::2, 0::2],
        "G1": mosaic[0::2, 1::2],
        "G2": mosaic[1::2, 0::2],
        "B": mosaic[1::2, 1::2],
    }
    return {
        name: {
            "mean": float(np.mean(plane)),
            "sd": float(np.std(plane)),
            "min": int(np.min(plane)),
            "max": int(np.max(plane)),
        }
        for name, plane in names.items()
    }


def rawpy_contract(metadata: dict) -> bool:
    return metadata == EXPECTED_RAWPY


def main() -> None:
    files = sorted(STACK.glob("*.ARW"))
    if not files:
        raise SystemExit(f"no ARWs in {STACK}")
    first = files[0]
    a, ma = load(first)
    b, mb = load(first)
    ha = array_sha256(a)
    hb = array_sha256(b)
    rawpy_pass = ma == mb == EXPECTED_RAWPY and ha == hb

    binary = REPO / "target" / "release" / "strehl.exe"
    completed = subprocess.run(
        [str(binary), "probe", str(STACK), "--limit", "1"],
        cwd=REPO,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout = completed.stdout
    rawler_pass = (
        completed.returncode == 0
        and "camera          : ILCE-7CM2" in stdout
        and "iso             : 100" in stdout
        and "active area     : 7032 x 4688" in stdout
        and "levels          : black 512, white 15360" in stdout
        and "decoded         : 1 ok, 0 failed" in stdout
    )

    padded = dict(ma)
    padded["shape"] = [5120, 7168]
    plant_red = not rawpy_contract(padded)
    result = {
        "schema_version": 1,
        "role": "loader commissioning only; no sharpness statistic computed",
        "file": str(first),
        "file_sha256": file_sha256(first),
        "rawpy": {
            "status": "PASS" if rawpy_pass else "FAIL",
            "metadata_first": ma,
            "metadata_second": mb,
            "pixel_sha256_first": ha,
            "pixel_sha256_second": hb,
            "plane_summaries": plane_summaries(a),
        },
        "rawler": {
            "status": "PASS" if rawler_pass else "FAIL",
            "binary": str(binary),
            "binary_sha256": file_sha256(binary),
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": completed.stderr,
        },
        "known_representation_difference": {
            "rawpy_visible_width": ma["shape"][1],
            "rawler_active_width": 7032,
            "difference_sensor_columns": 7032 - ma["shape"][1],
            "rawpy_container_white": ma["container_white"],
            "rawler_linear_white": 15360,
            "interpretation": (
                "both committed contracts reproduced; verdict coordinates use "
                "only rawpy visible pixels and clipping uses 15360"
            ),
        },
        "padded_shape_plant": {
            "planted_shape": padded["shape"],
            "status": "RED" if plant_red else "MISSED",
            "criterion": "padded 5120x7168 shape must fail rawpy visible contract",
        },
        "tally": {
            "known_answer_pass": int(rawpy_pass) + int(rawler_pass),
            "known_answer_total": 2,
            "plants_red": int(plant_red),
            "plants_total": 1,
        },
        "not_verified": (
            "strehl probe exposes no pixel checksum or per-plane moments, so "
            "the two decoders were not compared pixel by pixel"
        ),
        "invocation": (
            "PYTHONIOENCODING=utf-8; "
            "python experiments\\M-PHASE0-ASTIG\\src\\loader_check.py"
        ),
        "source_sha256": file_sha256(Path(__file__)),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "loader-check.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"rawpy={result['rawpy']['status']} "
        f"rawler={result['rawler']['status']} "
        f"padded-plant={result['padded_shape_plant']['status']}"
    )
    print(f"wrote {target}")
    if not rawpy_pass or not rawler_pass or not plant_red:
        raise SystemExit(1)


if __name__ == "__main__":
    sys.exit(main())
