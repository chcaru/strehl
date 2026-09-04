from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import tifffile


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
OUT = LANE / "out"
REPORT = ROOT / "docs" / "research" / "M-COVER-NATIVE.md"
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
BASELINE = ROOT / "experiments" / "SCORECARD-BASELINE"
METHOD_COMMIT = "b3215162"
NATIVE_H, NATIVE_W = 4688, 7032
COMMON_Y, COMMON_X, COMMON_H, COMMON_W = 40, 58, 4608, 6912


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


def close(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


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
    result = read_json(OUT / "SCORECARD-Q1-CONFIRMATION.json")
    manifest = read_json(OUT / "RENDER-MANIFEST.json")
    report = REPORT.read_text(encoding="utf-8")
    scorecard_lines = SCORECARD.read_text(encoding="utf-8").splitlines()

    require(result["status"] == "SCORECARD_Q1_CONFIRMATION", "result status moved")
    instrument = result["instrument"]
    expected_hashes = {
        "audit_geometry.py": sha256(BASELINE / "audit_geometry.py"),
        "measure.py": sha256(BASELINE / "measure.py"),
    }
    require(instrument["hashes"] == expected_hashes, "frozen reader hashes moved")
    commission = instrument["commissioning"]
    require(commission["commissioned"], "commission is not admitted")
    require(commission["null_stayed_green"], "commission null moved RED")
    require(commission["plant_went_red"], "commission plant moved GREEN")

    scale = result["native_scale_confirmation"]
    require(scale["arm"] == "m2-second-first16", "confirmation arm moved")
    require(scale["scorecard_scale_pass"], "scale confirmation moved RED")
    require(scale["scorecard_rotation_pass"], "rotation confirmation moved RED")
    require(
        close(scale["scale_disagreement_percent"], 0.021415847315986447),
        "scale confirmation value moved",
    )
    require(
        close(scale["rotation_deg"], 1.0165566713092892e-06),
        "rotation confirmation value moved",
    )
    render_path = OUT / "renders" / f"{scale['arm']}.tiff"
    require(sha256(render_path) == scale["render_sha256"], "confirmation TIFF moved")

    census = result["no_inset_field_of_view"]
    require(census["native_shape_hxw"] == [NATIVE_H, NATIVE_W], "native shape moved")
    require(
        census["frozen_common_rect_yxhw"] == [COMMON_Y, COMMON_X, COMMON_H, COMMON_W],
        "common rectangle moved",
    )
    records = {record["name"]: record for record in manifest["crop_records"]}
    rows = census["rows"]
    require(len(rows) == 8 and len({row["arm"] for row in rows}) == 8, "arm set moved")

    native_values = []
    common_values = []
    for row in rows:
        arm = row["arm"]
        require(arm in records, f"{arm}: missing manifest record")
        path = OUT / "renders" / f"{arm}.tiff"
        with tifffile.TiffFile(path) as image:
            require(len(image.pages) == 1, f"{arm}: TIFF page count moved")
            shape = list(image.pages[0].shape)
        require(shape == row["output_shape_hwc"], f"{arm}: TIFF header moved")
        require(shape == records[arm]["shape"], f"{arm}: manifest header moved")

        height, width, channels = [int(value) for value in shape]
        require(channels == 3, f"{arm}: output is not RGB")
        rect = row["crop_rect_fullres_yxhw"]
        crop_y, crop_x, crop_h, crop_w = [int(value) for value in rect]
        require((height, width) == (crop_h, crop_w), f"{arm}: Crop rectangle moved")

        native = 100.0 * height * width / (NATIVE_H * NATIVE_W)
        common = (
            100.0
            * intersection_area(
                crop_y,
                crop_x,
                crop_h,
                crop_w,
                COMMON_Y,
                COMMON_X,
                COMMON_H,
                COMMON_W,
            )
            / (COMMON_H * COMMON_W)
        )
        require(
            close(native, row["native_plane_retained_percent"]),
            f"{arm}: native arithmetic moved",
        )
        require(
            close(common, row["frozen_common_overlap_retained_percent"]),
            f"{arm}: common-overlap arithmetic moved",
        )
        require(native >= 99.0 and common >= 99.0, f"{arm}: FOV gate moved RED")
        native_values.append(native)
        common_values.append(common)

    require(
        close(min(native_values), census["minimum_native_plane_retained_percent"]),
        "minimum native retention moved",
    )
    require(
        close(
            min(common_values), census["minimum_frozen_common_overlap_retained_percent"]
        ),
        "minimum common-overlap retention moved",
    )
    require(census["all_native_plane_fov_pass"], "native-plane aggregate moved RED")
    require(
        census["all_frozen_common_overlap_fov_pass"],
        "common-overlap aggregate moved RED",
    )

    require(
        scorecard_lines[224]
        == "- Outputs must retain native scale. Resize is a hard invalidation.",
        "scorecard line 225 moved",
    )
    require(
        scorecard_lines[225]
        == "- Crops are fixed from the common-input overlap before outputs exist. Retained field of",
        "scorecard line 226 moved",
    )
    require(
        scorecard_lines[226] == "  view must be `>=99.0%` of that overlap.",
        "scorecard line 227 moved",
    )

    for required in (
        "0.021415847%",
        "99.035321708%",
        "100.000000000%",
        "No current scorecard clause independently fires from that number.",
        "does **not** make M1/M2 immediately measurable",
    ):
        require(required in report, f"report omits: {required}")

    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", METHOD_COMMIT, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    require(ancestor.returncode == 0, "method commit is not an ancestor")

    print(
        "scorecard Q1 verification passed: "
        "scale 0.021415847%, no-inset FOV 99.035321708%/100.000000000%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
