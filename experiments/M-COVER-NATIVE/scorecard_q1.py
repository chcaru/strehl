from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


for name in (
    "RAYON_NUM_THREADS",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[name] = "6"
os.environ["PYTHONIOENCODING"] = "utf-8"


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
BASELINE = ROOT / "experiments" / "SCORECARD-BASELINE"
BASELINE_WORK = BASELINE / "work"
OUT = LANE / "out"
RENDERS = OUT / "renders"
ARM = "m2-second-first16"
REFERENCE = "second_second16.npy"
NATIVE_H, NATIVE_W = 4688, 7032
COMMON_Y, COMMON_X, COMMON_H, COMMON_W = 40, 58, 4608, 6912

EXPECTED = {
    "audit_geometry.py": "be1ec143f3d391e7eb0ab4a927c4744aa18283f4992e82d3f975354163a357fd",
    "measure.py": "7c0d1175c76ffdab7adc3ab799831cbbd63debcdcb31dc5f9b80372e4ceb51b5",
    f"{ARM}.tiff": "a0b38ce9cab2cd0c1030da21d8d44dc5832055045c03dc89c5d45e27a893ee1c",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def intersection_area(
    a_y: int,
    a_x: int,
    a_h: int,
    a_w: int,
    b_y: int,
    b_x: int,
    b_h: int,
    b_w: int,
) -> int:
    height = max(0, min(a_y + a_h, b_y + b_h) - max(a_y, b_y))
    width = max(0, min(a_x + a_w, b_x + b_w) - max(a_x, b_x))
    return height * width


def main() -> int:
    instrument = BASELINE / "audit_geometry.py"
    luma_reader = BASELINE / "measure.py"
    render = RENDERS / f"{ARM}.tiff"

    hashes = {
        "audit_geometry.py": sha256(instrument),
        "measure.py": sha256(luma_reader),
    }
    for name, value in hashes.items():
        require(value == EXPECTED[name], f"{name} hash moved")

    sys.path.insert(0, str(BASELINE))
    import audit_geometry
    import cv2
    import measure
    import numpy as np
    import tifffile

    cv2.setNumThreads(6)
    commissioning = audit_geometry.commission()
    require(commissioning["commissioned"], "frozen ECC reader did not commission")

    render_hash = sha256(render)
    require(render_hash == EXPECTED[f"{ARM}.tiff"], "Crop TIFF hash moved")
    reference = np.load(BASELINE_WORK / "input-cache" / REFERENCE, mmap_mode="r")
    moving = measure.output_luma(render)
    estimate = audit_geometry.estimate(reference, moving)

    manifest = read_json(OUT / "RENDER-MANIFEST.json")
    rows = []
    for record in manifest["crop_records"]:
        path = RENDERS / f"{record['name']}.tiff"
        with tifffile.TiffFile(path) as image:
            require(len(image.pages) == 1, f"{record['name']}: expected one TIFF page")
            shape = list(image.pages[0].shape)
        require(shape == record["shape"], f"{record['name']}: header moved")
        height, width, channels = [int(value) for value in shape]
        require(channels == 3, f"{record['name']}: expected RGB")

        rect = record["coverage"]["rect_plane"]
        crop_y = 2 * int(rect["y"])
        crop_x = 2 * int(rect["x"])
        crop_h = 2 * int(rect["height"])
        crop_w = 2 * int(rect["width"])
        require((height, width) == (crop_h, crop_w), f"{record['name']}: crop moved")

        native_retained = 100.0 * height * width / (NATIVE_H * NATIVE_W)
        common_retained = 100.0 * intersection_area(
            crop_y,
            crop_x,
            crop_h,
            crop_w,
            COMMON_Y,
            COMMON_X,
            COMMON_H,
            COMMON_W,
        ) / (COMMON_H * COMMON_W)
        rows.append(
            {
                "arm": record["name"],
                "output_shape_hwc": shape,
                "crop_rect_fullres_yxhw": [crop_y, crop_x, crop_h, crop_w],
                "native_plane_retained_percent": native_retained,
                "frozen_common_overlap_retained_percent": common_retained,
                "native_plane_fov_pass": native_retained >= 99.0,
                "frozen_common_overlap_fov_pass": common_retained >= 99.0,
            }
        )

    result = {
        "status": "SCORECARD_Q1_CONFIRMATION",
        "scope": (
            "One unchanged frozen-ECC repeat plus deterministic no-inset TIFF-header "
            "census; no render and no COVER border remeasurement"
        ),
        "instrument": {
            "description": (
                "Frozen whole-image 8x-downsampled affine ECC; not literal discrete "
                "input-derived landmarks"
            ),
            "hashes": hashes,
            "opencv_threads": cv2.getNumThreads(),
            "commissioning": commissioning,
        },
        "native_scale_confirmation": {
            "arm": ARM,
            "reference": REFERENCE,
            "render_sha256": render_hash,
            **estimate,
        },
        "no_inset_field_of_view": {
            "native_shape_hxw": [NATIVE_H, NATIVE_W],
            "frozen_common_rect_yxhw": [COMMON_Y, COMMON_X, COMMON_H, COMMON_W],
            "rows": rows,
            "minimum_native_plane_retained_percent": min(
                row["native_plane_retained_percent"] for row in rows
            ),
            "minimum_frozen_common_overlap_retained_percent": min(
                row["frozen_common_overlap_retained_percent"] for row in rows
            ),
            "all_native_plane_fov_pass": all(
                row["native_plane_fov_pass"] for row in rows
            ),
            "all_frozen_common_overlap_fov_pass": all(
                row["frozen_common_overlap_fov_pass"] for row in rows
            ),
        },
    }
    write_json(OUT / "SCORECARD-Q1-CONFIRMATION.json", result)
    print(
        f"{ARM}: scale disagreement="
        f"{estimate['scale_disagreement_percent']:.9f}%, "
        f"rotation={estimate['rotation_deg']:.9f} deg"
    )
    print(
        "no inset: minimum native-plane retention="
        f"{result['no_inset_field_of_view']['minimum_native_plane_retained_percent']:.9f}%, "
        "minimum frozen-common-overlap retention="
        f"{result['no_inset_field_of_view']['minimum_frozen_common_overlap_retained_percent']:.9f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
