from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
OUT = LANE / "out"
RENDERS = OUT / "renders"
WORK = LANE / "work" / "geometry-census-commission"
RENDER_MANIFEST = OUT / "RENDER-MANIFEST.json"
COMMISSION_PATH = OUT / "GEOMETRY-CENSUS-COMMISSION.json"
CENSUS_PATH = OUT / "GEOMETRY-CENSUS.json"

ARMS = (
    "m1-bright-a12",
    "m1-bright-b12",
    "m1-second-a12",
    "m1-second-b12",
    "m2-bright-first16",
    "m2-bright-second16",
    "m2-second-first16",
    "m2-second-second16",
)

NATIVE_WIDTH = 7032
NATIVE_HEIGHT = 4688
NATIVE_AREA = NATIVE_WIDTH * NATIVE_HEIGHT
COMMON_RECT_YXHW = (40, 58, 4608, 6912)

SYNTHETIC_NATIVE_WIDTH = 12
SYNTHETIC_NATIVE_HEIGHT = 8
SYNTHETIC_SMALLER_WIDTH = 10
SYNTHETIC_SMALLER_HEIGHT = 6


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path, block: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(block):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def percent(numerator: int, denominator: int) -> str:
    value = Decimal(numerator) * Decimal(100) / Decimal(denominator)
    return f"{value:.9f}"


def inspect_tiff_header(path: Path) -> dict[str, Any]:
    import tifffile

    with tifffile.TiffFile(path) as tiff:
        require(len(tiff.pages) == 1, f"{path}: expected one TIFF page")
        page = tiff.pages[0]
        return {
            "width": int(page.imagewidth),
            "height": int(page.imagelength),
            "shape": list(page.shape),
            "dtype": str(page.dtype),
        }


def classify_dimensions(
    width: int,
    height: int,
    *,
    native_width: int,
    native_height: int,
) -> dict[str, Any]:
    width_lost = native_width - width
    height_lost = native_height - height
    require(width_lost >= 0, "observed width exceeds the fixed native width")
    require(height_lost >= 0, "observed height exceeds the fixed native height")
    native_size = width_lost == 0 and height_lost == 0
    return {
        "native_width": native_width,
        "native_height": native_height,
        "width": width,
        "height": height,
        "width_pixels_lost": width_lost,
        "height_pixels_lost": height_lost,
        "native_size": native_size,
        "verdict": "GREEN" if native_size else "RED",
    }


def commission() -> dict[str, Any]:
    import numpy as np
    import tifffile

    null_path = WORK / "matching-null.tiff"
    smaller_path = WORK / "known-smaller.tiff"
    cases: list[dict[str, Any]] = []
    WORK.mkdir(parents=True, exist_ok=True)
    try:
        tifffile.imwrite(
            null_path,
            np.zeros(
                (SYNTHETIC_NATIVE_HEIGHT, SYNTHETIC_NATIVE_WIDTH),
                dtype=np.uint8,
            ),
        )
        tifffile.imwrite(
            smaller_path,
            np.zeros(
                (SYNTHETIC_SMALLER_HEIGHT, SYNTHETIC_SMALLER_WIDTH),
                dtype=np.uint8,
            ),
        )

        null_header = inspect_tiff_header(null_path)
        null_result = classify_dimensions(
            null_header["width"],
            null_header["height"],
            native_width=SYNTHETIC_NATIVE_WIDTH,
            native_height=SYNTHETIC_NATIVE_HEIGHT,
        )
        null_pass = (
            null_result["verdict"] == "GREEN"
            and null_result["width_pixels_lost"] == 0
            and null_result["height_pixels_lost"] == 0
        )
        cases.append(
            {
                "name": "matching_dimensions_null",
                "header": null_header,
                "classification": null_result,
                "expected_verdict": "GREEN",
                "passed": null_pass,
            }
        )

        smaller_header = inspect_tiff_header(smaller_path)
        smaller_result = classify_dimensions(
            smaller_header["width"],
            smaller_header["height"],
            native_width=SYNTHETIC_NATIVE_WIDTH,
            native_height=SYNTHETIC_NATIVE_HEIGHT,
        )
        smaller_pass = (
            smaller_result["verdict"] == "RED"
            and smaller_result["width_pixels_lost"] == 2
            and smaller_result["height_pixels_lost"] == 2
        )
        cases.append(
            {
                "name": "known_smaller_crop",
                "header": smaller_header,
                "classification": smaller_result,
                "expected_verdict": "RED",
                "passed": smaller_pass,
            }
        )
    finally:
        for path in (null_path, smaller_path):
            path.unlink(missing_ok=True)
        if WORK.exists():
            shutil.rmtree(WORK)

    result = {
        "status": "COMMISSIONED",
        "script_sha256": sha256(Path(__file__)),
        "actual_headers_observed_in_phase_a": True,
        "census_kind": "deterministic_header_census_not_blinded_discovery",
        "synthetic_native_width": SYNTHETIC_NATIVE_WIDTH,
        "synthetic_native_height": SYNTHETIC_NATIVE_HEIGHT,
        "cases": cases,
        "all_passed": all(case["passed"] for case in cases),
        "temporary_files_removed": not WORK.exists(),
    }
    require(result["all_passed"], "geometry-census commissioning failed")
    require(result["temporary_files_removed"], "commissioning files were not removed")
    write_json(COMMISSION_PATH, result)
    return result


def require_commission() -> dict[str, Any]:
    require(COMMISSION_PATH.is_file(), "run geometry_census.py --commission first")
    result = read_json(COMMISSION_PATH)
    require(result["status"] == "COMMISSIONED", "commission status moved")
    require(result["all_passed"], "commission controls did not all pass")
    require(result["temporary_files_removed"], "commission temporary files remain")
    require(
        result["script_sha256"] == sha256(Path(__file__)),
        "geometry_census.py changed after commissioning; recommission",
    )
    return result


def committed_render_manifest() -> tuple[dict[str, Any], str, str]:
    relative = RENDER_MANIFEST.relative_to(ROOT).as_posix()
    committed = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    committed_data = json.loads(committed)
    require(
        read_json(RENDER_MANIFEST) == committed_data,
        "working RENDER-MANIFEST.json differs from committed Phase A content",
    )
    require(
        subprocess.run(
            ["git", "diff", "--quiet", "--", relative],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0,
        "working RENDER-MANIFEST.json has an uncommitted change",
    )
    blob = subprocess.run(
        ["git", "rev-parse", f"HEAD:{relative}"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    return committed_data, blob, sha256_bytes(committed)


def intersection_area(
    first_yxhw: tuple[int, int, int, int],
    second_yxhw: tuple[int, int, int, int],
) -> int:
    first_y, first_x, first_h, first_w = first_yxhw
    second_y, second_x, second_h, second_w = second_yxhw
    y0 = max(first_y, second_y)
    x0 = max(first_x, second_x)
    y1 = min(first_y + first_h, second_y + second_h)
    x1 = min(first_x + first_w, second_x + second_w)
    return max(0, y1 - y0) * max(0, x1 - x0)


def census_row(record: dict[str, Any]) -> dict[str, Any]:
    name = record["name"]
    path = RENDERS / f"{name}.tiff"
    require(path.is_file(), f"{name}: Crop TIFF is missing")
    require(
        Path(record["output"]).resolve() == path.resolve(),
        f"{name}: manifest output path moved",
    )

    header = inspect_tiff_header(path)
    actual_sha256 = sha256(path)
    require(actual_sha256 == record["sha256"], f"{name}: TIFF hash moved")
    require(header["shape"] == record["shape"], f"{name}: TIFF shape moved")
    require(header["dtype"] == record["dtype"], f"{name}: TIFF dtype moved")

    width = header["width"]
    height = header["height"]
    require(header["shape"][:2] == [height, width], f"{name}: shape/header mismatch")
    crop = record["coverage"]["rect_plane"]
    require(
        width == 2 * crop["width"] and height == 2 * crop["height"],
        f"{name}: TIFF dimensions are not twice the banner Crop rectangle",
    )

    full_plane = record["coverage"]["full_plane"]
    require(
        2 * full_plane["width"] == NATIVE_WIDTH
        and 2 * full_plane["height"] == NATIVE_HEIGHT,
        f"{name}: manifest full plane is not the fixed native plane",
    )

    dimensions = classify_dimensions(
        width,
        height,
        native_width=NATIVE_WIDTH,
        native_height=NATIVE_HEIGHT,
    )
    left_lost = 2 * crop["x"]
    top_lost = 2 * crop["y"]
    right_lost = NATIVE_WIDTH - left_lost - width
    bottom_lost = NATIVE_HEIGHT - top_lost - height
    require(
        left_lost + right_lost == dimensions["width_pixels_lost"],
        f"{name}: horizontal loss arithmetic disagrees",
    )
    require(
        top_lost + bottom_lost == dimensions["height_pixels_lost"],
        f"{name}: vertical loss arithmetic disagrees",
    )

    retained_area = width * height
    area_lost = NATIVE_AREA - retained_area
    crop_rect_yxhw = (top_lost, left_lost, height, width)
    common_area = COMMON_RECT_YXHW[2] * COMMON_RECT_YXHW[3]
    common_retained = intersection_area(crop_rect_yxhw, COMMON_RECT_YXHW)

    return {
        "arm": name,
        "tiff": str(path.relative_to(ROOT).as_posix()),
        "tiff_header": header,
        "manifest_sha256": record["sha256"],
        "actual_sha256": actual_sha256,
        "manifest_header_hash_agree": True,
        "scale_native_width": NATIVE_WIDTH,
        "scale_native_height": NATIVE_HEIGHT,
        "crop_width": width,
        "crop_height": height,
        "width_pixels_lost": dimensions["width_pixels_lost"],
        "height_pixels_lost": dimensions["height_pixels_lost"],
        "left_pixels_lost": left_lost,
        "right_pixels_lost": right_lost,
        "top_pixels_lost": top_lost,
        "bottom_pixels_lost": bottom_lost,
        "percent_width_loss": percent(
            dimensions["width_pixels_lost"], NATIVE_WIDTH
        ),
        "percent_height_loss": percent(
            dimensions["height_pixels_lost"], NATIVE_HEIGHT
        ),
        "retained_area_pixels": retained_area,
        "area_pixels_lost": area_lost,
        "percent_area_loss": percent(area_lost, NATIVE_AREA),
        "retained_area_percent": percent(retained_area, NATIVE_AREA),
        "crop_rect_plane_xywh": [
            crop["x"],
            crop["y"],
            crop["width"],
            crop["height"],
        ],
        "crop_rect_fullres_yxhw": list(crop_rect_yxhw),
        "dimensions_equal_twice_banner_crop_rect": True,
        "native_size_verdict": dimensions["verdict"],
        "common_overlap_area_pixels": common_area,
        "common_overlap_retained_pixels": common_retained,
        "common_overlap_geometric_retention_percent": percent(
            common_retained, common_area
        ),
        "contains_entire_common_overlap": common_retained == common_area,
        "common_overlap_is_geometric_not_clean_site_admission": True,
    }


def build_census() -> dict[str, Any]:
    commission_result = require_commission()
    manifest, manifest_blob, manifest_sha256 = committed_render_manifest()
    records = manifest["crop_records"]
    names = [record["name"] for record in records]
    require(names == list(ARMS), "render manifest does not contain the exact eight arms")
    require(manifest["crop_interpretable"], "Phase A Crop manifest is not interpretable")

    rows = [census_row(record) for record in records]
    worst = max(rows, key=lambda row: row["area_pixels_lost"])
    require(
        worst["arm"] == "m2-second-first16",
        "m2-second-first16 is no longer the worst field-loss arm",
    )
    require(
        all(row["native_size_verdict"] == "RED" for row in rows),
        "native-size failure is not 8/8",
    )
    require(
        all(row["contains_entire_common_overlap"] for row in rows),
        "a Crop arm no longer geometrically contains the frozen common overlap",
    )

    return {
        "status": "Q3_COMPLETE",
        "evidence": {
            "headers_dimensions_and_hashes": "VERIFIED",
            "loss_percentages": "DERIVED_FROM_FIXED_INTEGER_DIMENSIONS",
            "common_overlap": "GEOMETRIC_CONTAINMENT_NOT_CLEAN_SITE_ADMISSION",
            "non_translation_residual": "UNMEASURED_NOT_READ_BY_THIS_CENSUS",
        },
        "commission_artifact": str(COMMISSION_PATH.relative_to(ROOT).as_posix()),
        "commission_artifact_sha256": sha256(COMMISSION_PATH),
        "commission_script_sha256": commission_result["script_sha256"],
        "render_manifest": str(RENDER_MANIFEST.relative_to(ROOT).as_posix()),
        "render_manifest_git_blob": manifest_blob,
        "render_manifest_sha256": manifest_sha256,
        "native_scale_output_width": NATIVE_WIDTH,
        "native_scale_output_height": NATIVE_HEIGHT,
        "native_scale_array_shape_hxw": [NATIVE_HEIGHT, NATIVE_WIDTH],
        "native_area_pixels": NATIVE_AREA,
        "frozen_common_rect_yxhw": list(COMMON_RECT_YXHW),
        "percent_fields": "fixed decimal strings with 9 places",
        "arms": list(ARMS),
        "rows": rows,
        "row_count": len(rows),
        "native_size_fail_count": sum(
            row["native_size_verdict"] == "RED" for row in rows
        ),
        "all_manifest_header_hash_agree": all(
            row["manifest_header_hash_agree"] for row in rows
        ),
        "all_dimensions_equal_twice_banner_crop_rect": all(
            row["dimensions_equal_twice_banner_crop_rect"] for row in rows
        ),
        "all_common_overlap_geometric_retention_percent": "100.000000000",
        "worst_field_loss_arm": worst["arm"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commission",
        action="store_true",
        help="run the fixed tiny-TIFF null and known-smaller failure input",
    )
    args = parser.parse_args()
    if args.commission:
        result = commission()
        print(
            "geometry census commissioned: "
            f"{len(result['cases'])}/{len(result['cases'])} controls passed"
        )
        return 0

    result = build_census()
    write_json(CENSUS_PATH, result)
    print(
        "geometry census complete: "
        f"{result['row_count']} rows, "
        f"native-size RED {result['native_size_fail_count']}/8, "
        f"worst {result['worst_field_loss_arm']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
