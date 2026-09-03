"""Author outcome runner for the preregistered cover-mode comparison."""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import math
import sys
from pathlib import Path
from types import ModuleType

import tifffile

import cover_core as cc


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("cover_author_frozen", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import frozen site module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guards(rows: list[dict], shape: tuple[int, int]) -> tuple[list[float], bool]:
    quadrants: list[float] = []
    for qy in (0, 1):
        for qx in (0, 1):
            chosen = [
                row
                for row in rows
                if (row["centre"][0] >= shape[0] / 2) == bool(qy)
                and (row["centre"][1] >= shape[1] / 2) == bool(qx)
            ]
            if chosen:
                quadrants.append(
                    math.exp(
                        sum(
                            math.log(row["crop_q"][2] / row["scale_q"][2])
                            for row in chosen
                        )
                        / len(chosen)
                    )
                )
    loo_reversal = False
    for omit in range(len(rows)):
        remaining = [
            math.log(row["crop_q"][2] / row["scale_q"][2])
            for index, row in enumerate(rows)
            if index != omit
        ]
        if remaining and math.exp(sum(remaining) / len(remaining)) <= 1.0:
            loo_reversal = True
            break
    return quadrants, loo_reversal


def coverage_payload(
    scale_path: Path,
    crop_path: Path,
    provenance: dict,
) -> dict:
    scale_shape = tuple(tifffile.memmap(scale_path).shape)
    crop_shape = tuple(tifffile.memmap(crop_path).shape)
    scale_h, scale_w = scale_shape[:2]
    crop_h, crop_w = crop_shape[:2]
    crop_facts = provenance["arms"]["crop"]["facts"]
    return {
        "scale_shape": list(scale_shape),
        "crop_shape": list(crop_shape),
        "crop_origin_plane_yx": crop_facts["plane_origin"],
        "crop_plane_dimensions_yx": crop_facts["plane_dimensions"],
        "full_plane_dimensions_yx": crop_facts["full_plane_dimensions"],
        "k": crop_facts["k"],
        "retained_width_fraction": crop_w / scale_w,
        "retained_height_fraction": crop_h / scale_h,
        "retained_pixel_fraction": (crop_w * crop_h) / (scale_w * scale_h),
        "scale_print_inches_300dpi": [scale_w / 300.0, scale_h / 300.0],
        "crop_print_inches_300dpi": [crop_w / 300.0, crop_h / 300.0],
    }


def measure(
    crop_path: Path,
    scale_path: Path,
    pmax_path: Path,
    frozen_path: Path,
    provenance_path: Path,
) -> dict:
    frozen = load_module(frozen_path)
    sites = list(frozen.SITES)
    digest = cc.site_digest(sites)
    if digest != str(frozen.SITE_DIGEST).upper():
        raise RuntimeError("frozen site digest mismatch")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    cc.validate_provenance(
        provenance,
        crop_path,
        scale_path,
        pmax_path,
        str(frozen.PMAX_SHA256).upper(),
        str(frozen.SCALE_SHA256).upper(),
        str(frozen.SUBJECT),
    )
    scale_geometry = cc.fit_geometry(scale_path, pmax_path)
    crop_geometry = cc.fit_geometry(crop_path, pmax_path)
    for name, geometry in (
        ("scale", scale_geometry),
        ("crop", crop_geometry),
    ):
        if not geometry["coarse_interior"] or not geometry["fine_interior"]:
            raise RuntimeError(f"{name} scale optimum is not interior")
    frozen_scale = float(frozen.AUTHOR_GEOMETRY["scale"])
    if abs(scale_geometry["scale"] / frozen_scale - 1.0) > 0.005:
        raise RuntimeError("scale geometry no longer agrees with frozen fit")

    scale = cc.green(scale_path)
    crop = cc.green(crop_path)
    pmax = cc.green(pmax_path)
    losses = {
        "scale": collections.Counter(),
        "crop": collections.Counter(),
    }
    retained: list[dict] = []
    clearances: list[int] = []
    for site in sites:
        centre = site["centre"]
        scale_row = cc.map_site(
            scale,
            pmax,
            centre,
            scale_geometry,
        )
        crop_row = cc.map_site(
            crop,
            pmax,
            centre,
            crop_geometry,
            require_border=True,
        )
        losses["scale"][scale_row["reason"] or "eligible"] += 1
        losses["crop"][crop_row["reason"] or "eligible"] += 1
        if scale_row["reason"] is not None or crop_row["reason"] is not None:
            continue
        if scale_row["pmax_q"] != crop_row["pmax_q"]:
            raise RuntimeError("paired arms did not use identical PMax pixels")
        retained.append(
            {
                "centre": centre,
                "label": site["label"],
                "scale_q": scale_row["arm_q"],
                "crop_q": crop_row["arm_q"],
                "pmax_q": scale_row["pmax_q"],
            }
        )
        clearances.append(int(crop_row["border_clearance"]))

    counts = collections.Counter(row["label"] for row in retained)
    if counts["detail"] < 12 or counts["flat"] < 6:
        raise RuntimeError(
            f"coverage gate failed: {counts['detail']} detail, {counts['flat']} flat"
        )
    if not clearances or min(clearances) < cc.BORDER:
        raise RuntimeError("crop border gate failed")
    detail = [row for row in retained if row["label"] == "detail"]
    flat = [row for row in retained if row["label"] == "flat"]
    detail_bands = cc.bootstrap(detail, cc.SEED)
    flat_bands = cc.bootstrap(flat, cc.SEED + 1)
    primary = detail_bands[2]
    if isinstance(primary, str):
        verdict = cc.UNLICENSED
        quadrant_effects: list[float] = []
        loo_reversal = False
    else:
        quadrant_effects, loo_reversal = guards(detail, pmax.shape)
        verdict = cc.cover_verdict(
            primary["scale_over_pmax"]["class"],
            primary["crop_over_pmax"]["class"],
            primary["crop_over_scale"]["ci_low"],
            primary["crop_over_scale"]["ci_high"],
            quadrant_effects,
            loo_reversal,
        )
    return {
        "status": "GREEN",
        "site_digest": digest,
        "hashes": {
            "scale": cc.sha256(scale_path),
            "crop": cc.sha256(crop_path),
            "pmax": cc.sha256(pmax_path),
        },
        "geometry": {
            "scale": scale_geometry,
            "crop": crop_geometry,
        },
        "coverage": {
            **coverage_payload(scale_path, crop_path, provenance),
            "frozen": dict(collections.Counter(site["label"] for site in sites)),
            "retained": dict(counts),
            "loss_reasons": {
                name: dict(counter) for name, counter in losses.items()
            },
            "minimum_crop_border": min(clearances),
        },
        "bands": {
            name: {
                "detail": detail_bands[index],
                "flat": flat_bands[index],
            }
            if not isinstance(detail_bands[index], str)
            and not isinstance(flat_bands[index], str)
            else cc.UNLICENSED
            for index, name in enumerate(cc.BAND_NAMES)
        }
        | {"gt_0.25": cc.UNLICENSED},
        "primary": {
            "verdict": verdict,
            "quadrant_effects": quadrant_effects,
            "loo_reversal": loo_reversal,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop", type=Path, required=True)
    parser.add_argument("--scale", type=Path, required=True)
    parser.add_argument("--pmax", type=Path, required=True)
    parser.add_argument("--frozen-sites", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = measure(
            args.crop,
            args.scale,
            args.pmax,
            args.frozen_sites,
            args.provenance,
        )
        code = 0
    except Exception as exc:
        payload = {
            "status": "STOP",
            "reason": f"{type(exc).__name__}: {exc}",
            "bands": {
                **{name: cc.UNLICENSED for name in cc.BAND_NAMES},
                "gt_0.25": cc.UNLICENSED,
            },
        }
        code = 2
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    sys.exit(main())
