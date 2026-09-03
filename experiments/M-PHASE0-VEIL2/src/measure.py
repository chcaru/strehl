"""Execute the frozen M-PHASE0-VEIL2 real-capture measurement.

The product binary owns every numerical master and single-frame reference.
This script only validates those products, registers references with the
product sidecars, evaluates the commissioned statistics, and applies the
preregistered lookup table.
"""

from __future__ import annotations

import gc
import json
import math
import platform
import re
import sys
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
import rawpy
import scipy
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from site_select import raw_green  # noqa: E402
from veil2lib import (  # noqa: E402
    BOOT_REPS,
    BOOT_SEED,
    channel_float,
    crop,
    detrended_wander_jackknife,
    exact_cover_scale,
    geometry_gate,
    layer_truth_gate,
    paper_normalize,
    paper_null_gate,
    parse_warpmap,
    pyramid_base,
    read_tiff,
    remap_similarity,
    remap_similarity_catmull,
    score_site,
    sha256,
    spatial_blocks,
    tone_locality_gate,
    write_json,
)

PAPER_ROI = (50, 200, 3250, 3450)
EXPECTED_BINARY = "2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7"
EXPECTED_SOURCE = "6af834dac08d6605aee7ea3ad75809fdf6313770"
CHANNELS = {0: "red", 1: "green", 2: "blue"}


def resolve(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_record(name: str) -> dict:
    return load_json(ROOT / "out" / "run-records" / f"{name}.json")


def coverage_from_record(record: dict) -> float:
    m = re.search(r"coverage\s+:\s+field of view scaled to ([0-9.]+)", record["output_text"])
    if not m:
        raise ValueError(f"{record['name']}: no coverage in product banner")
    return float(m.group(1))


def validate_render(
    name: str,
    expected_frame: int | None,
    expected_base: str = "plain mean across frames",
    expected_shape: tuple[int, int, int] = (2344, 3516, 3),
) -> dict:
    r = run_record(name)
    problems: list[str] = []
    if r.get("status") != "OK" or r.get("exit_code") != 0:
        problems.append("render status/exit code")
    if r.get("binary_sha256") != EXPECTED_BINARY:
        problems.append("binary hash")
    if r.get("source_commit") != EXPECTED_SOURCE:
        problems.append("source commit")
    if r.get("only_frame_zero_based") != expected_frame:
        problems.append("frame index")
    artifact = r.get("artifact", {})
    path = Path(artifact.get("path", ""))
    if not path.exists():
        problems.append("missing artifact")
    elif artifact.get("sha256") != sha256(path):
        problems.append("artifact hash")
    text = r.get("output_text", "")
    for needle in (
        "merge backend   : pyramid",
        f"base band       : {expected_base}",
        "colour          : camera RGB -> LINEAR sRGB",
        "no transfer curve",
    ):
        if needle not in text:
            problems.append(f"banner missing {needle!r}")
    arr = read_tiff(path) if path.exists() else None
    if arr is not None and arr.shape != expected_shape:
        problems.append(f"shape {arr.shape}")
    return {
        "name": name,
        "frame": expected_frame,
        "path": str(path),
        "bytes": artifact.get("bytes"),
        "sha256": artifact.get("sha256"),
        "pass": not problems,
        "problems": problems,
    }


def normalized_master(path: Path, channel: int) -> tuple[np.ndarray, float]:
    a = channel_float(read_tiff(path), channel)
    return paper_normalize(a, PAPER_ROI)


def aligned_reference(
    path: Path,
    channel: int,
    transform,
    coverage: float,
    *,
    interpolation: int | None = None,
) -> tuple[np.ndarray, float]:
    a = channel_float(read_tiff(path), channel)
    fitted = transform.fitted(coverage)
    if interpolation is None:
        a = remap_similarity_catmull(a, fitted)
    else:
        a = remap_similarity(a, fitted, interpolation)
    return paper_normalize(a, PAPER_ROI)


def aligned_product_set(
    prefix: str,
    frames: Sequence[int],
    channel: int,
    transforms: dict,
    coverage: float,
    *,
    interpolation: int | None = None,
) -> tuple[list[np.ndarray], dict[str, float]]:
    out = []
    anchors = {}
    for frame in frames:
        width = 3 if prefix == "chia" else 0
        label = f"{frame:0{width}d}" if width else str(frame)
        name = f"{prefix}-f{label}"
        path = ROOT / "out" / "renders" / f"{name}-linear.tiff"
        a, anchor = aligned_reference(
            path,
            channel,
            transforms[frame],
            coverage,
            interpolation=interpolation,
        )
        out.append(a)
        anchors[str(frame)] = anchor
    return out, anchors


def interval_class(score: dict) -> str:
    if not math.isfinite(score["denominator"]) or score["denominator"] < 0.15:
        return "UNMEASURABLE"
    lo, hi = score["theta_ci95"]
    if lo >= 0.50:
        return "STRONG"
    if lo > 0.25:
        return "POSITIVE"
    if hi <= 0.25:
        return "NULL"
    return "INDETERMINATE"


def shifted(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    matrix = np.asarray([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)
    return cv2.warpAffine(
        a,
        matrix,
        (a.shape[1], a.shape[0]),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def geometry_measurement(
    master: np.ndarray,
    background: Sequence[np.ndarray],
    windows: Sequence[Sequence[int]],
    bands: int = 7,
) -> dict:
    hm = master - pyramid_base(master, bands)
    b = np.median(np.stack(background), axis=0)
    hb = b - pyramid_base(b, bands)
    estimates = []
    for roi in windows:
        x = np.asarray(crop(hm, roi), dtype=np.float32)
        y = np.asarray(crop(hb, roi), dtype=np.float32)
        hann = cv2.createHanningWindow((x.shape[1], x.shape[0]), cv2.CV_32F)
        (dx, dy), response = cv2.phaseCorrelate(x, y, hann)
        estimates.append({"dy": float(dy), "dx": float(dx), "response": float(response)})
    gate = geometry_gate([[z["dy"], z["dx"]] for z in estimates])
    gate["windows"] = [[int(v) for v in r] for r in windows]
    gate["estimates"] = estimates
    return gate


def theta_components(
    master: np.ndarray,
    foreground: Sequence[np.ndarray],
    background: Sequence[np.ndarray],
    roi: Sequence[int],
    bands: int = 7,
) -> dict:
    bm = crop(pyramid_base(master, bands), roi)
    bf = [crop(pyramid_base(z, bands), roi) for z in foreground]
    bb = [crop(pyramid_base(z, bands), roi) for z in background]
    blocks = spatial_blocks(bm.shape, 16)
    return {
        "master": np.asarray([float(bm[s].mean()) for s in blocks]),
        "foreground": np.asarray(
            [[float(z[s].mean()) for s in blocks] for z in bf]
        ),
        "background": np.asarray(
            [[float(z[s].mean()) for s in blocks] for z in bb]
        ),
        "blocks": len(blocks),
    }


def hierarchical_chia(
    inputs: Sequence[tuple[np.ndarray, Sequence[np.ndarray], Sequence[np.ndarray], Sequence[int]]],
    point_scores: Sequence[dict],
) -> dict:
    components = [theta_components(*z) for z in inputs]
    rng = np.random.default_rng(BOOT_SEED)
    draws = np.empty(BOOT_REPS, dtype=np.float64)
    nsites = len(components)
    for i in range(BOOT_REPS):
        site_values = []
        for site_index in rng.integers(0, nsites, nsites):
            c = components[int(site_index)]
            nf = c["foreground"].shape[0]
            nb = c["background"].shape[0]
            ns = c["blocks"]
            fi = rng.integers(0, nf, nf)
            bi = rng.integers(0, nb, nb)
            si = rng.integers(0, ns, ns)
            fm = np.median(c["foreground"][fi], axis=0)[si].mean()
            bg = np.median(c["background"][bi], axis=0)[si].mean()
            mm = c["master"][si].mean()
            site_values.append((mm - bg) / (fm - bg) if fm != bg else np.nan)
        draws[i] = np.nanmedian(site_values)
    finite = draws[np.isfinite(draws)]
    if len(finite) < 0.99 * BOOT_REPS:
        raise ValueError("too many non-finite hierarchical chia replicates")
    return {
        "theta": float(np.median([z["theta"] for z in point_scores])),
        "theta_se": float(finite.std(ddof=1)),
        "theta_ci95": [float(v) for v in np.percentile(finite, [2.5, 97.5])],
        "bootstrap": {
            "seed": BOOT_SEED,
            "reps": BOOT_REPS,
            "sites_resampled": nsites,
            "frame_runs_resampled": True,
            "spatial_blocks_resampled": True,
        },
    }


def rawpy_decoder_arm(
    master: np.ndarray,
    product_foreground: Sequence[np.ndarray],
    product_background: Sequence[np.ndarray],
    rawdir: Path,
    foreground_frames: Sequence[int],
    background_frames: Sequence[int],
    transforms: dict,
    coverage: float,
    target_roi: Sequence[int],
    anchor_rois: Sequence[Sequence[int]],
) -> dict:
    files = sorted(rawdir.glob("*.ARW"))
    all_frames = list(foreground_frames) + list(background_frames)
    raw_images = []
    raw_hashes = {}
    for frame in all_frames:
        source = files[frame]
        raw_hashes[str(frame)] = {"name": source.name, "sha256": sha256(source)}
        a = raw_green(source)
        a = remap_similarity_catmull(a, transforms[frame].fitted(coverage))
        a, _ = paper_normalize(a, PAPER_ROI)
        raw_images.append(a)

    # Camera-green and linear-sRGB green are different linear combinations.
    # Calibrate that scale only on the three frozen off-target anchors. The
    # target pixels remain entirely rawpy/LibRaw data.
    product = list(product_foreground) + list(product_background)
    x = []
    y = []
    for raw, rendered in zip(raw_images, product):
        rb = pyramid_base(raw, 7)
        pb = pyramid_base(rendered, 7)
        for roi in anchor_rois:
            x.append(float(crop(rb, roi).mean()))
            y.append(float(crop(pb, roi).mean()))
    design = np.column_stack([x, np.ones(len(x), dtype=np.float64)])
    slope, intercept = np.linalg.lstsq(design, np.asarray(y), rcond=None)[0]
    mapped = [np.asarray(slope * z + intercept, dtype=np.float32) for z in raw_images]
    nf = len(foreground_frames)
    score = score_site(
        master,
        mapped[:nf],
        mapped[nf:],
        target_roi,
        bands=7,
        reps=BOOT_REPS,
        seed=BOOT_SEED,
    )
    return {
        "decoder": "rawpy/LibRaw raw_image_visible, direct two-green bin",
        "target_pixels_used_for_calibration": False,
        "calibration_rois": [[int(v) for v in r] for r in anchor_rois],
        "calibration_slope": float(slope),
        "calibration_intercept": float(intercept),
        "raw_frames": raw_hashes,
        "score": score,
        "class": interval_class(score),
    }


def flower_wander(manifest: dict) -> dict:
    roi = manifest["flower_flat_wander"]["roi"]
    result = {"roi": roi, "channels": {}}
    mean = read_tiff(ROOT / "out" / "renders" / "flower-mean-linear.tiff")
    weighted = read_tiff(ROOT / "out" / "renders" / "flower-weighted-linear.tiff")
    for channel, name in CHANNELS.items():
        delta = crop(
            weighted[:, :, channel].astype(np.float64)
            - mean[:, :, channel].astype(np.float64),
            roi,
        )
        result["channels"][name] = detrended_wander_jackknife(delta)
    result["pass_green"] = result["channels"]["green"]["pass"]
    return result


def main() -> int:
    manifest = load_json(ROOT / "roi-manifest.json")
    commission = load_json(ROOT / "out" / "commission.json")
    bee = manifest["bee"]
    bee_fg = [int(v) for v in bee["foreground_frames"]]
    bee_bg = [int(v) for v in bee["background_frames"]]
    final_chia_frames = sorted(
        {
            int(v)
            for site in manifest["sites"]
            for key in ("foreground_frames", "background_frames")
            for v in site[key]
        }
    )

    required = [
        ("bee-3-mean", None, "plain mean across frames", (2344, 3516, 3)),
        ("bee-3-f149", 149, "plain mean across frames", (2344, 3516, 3)),
        *[
            (f"bee-3-f{i}", i, "plain mean across frames", (2344, 3516, 3))
            for i in bee_fg + bee_bg
        ],
        ("chia-mean", None, "plain mean across frames", (2344, 3516, 3)),
        *[
            (f"chia-f{i:03d}", i, "plain mean across frames", (2344, 3516, 3))
            for i in final_chia_frames
        ],
        ("flower-mean", None, "plain mean across frames", (2344, 3520, 3)),
        (
            "flower-weighted",
            None,
            "weighted by the coarsest band's weight, reduced once onto the base grid",
            (2344, 3520, 3),
        ),
    ]
    provenance = [
        validate_render(name, frame, base, shape)
        for name, frame, base, shape in required
    ]
    provenance_pass = all(z["pass"] for z in provenance)

    bee_record = run_record("bee-3-mean")
    chia_record = run_record("chia-mean")
    bee_banner_coverage = coverage_from_record(bee_record)
    chia_banner_coverage = coverage_from_record(chia_record)
    bee_meta, bee_warps = parse_warpmap(resolve(bee["warpmap"]))
    chia_meta, chia_warps = parse_warpmap(resolve(manifest["warpmap"]))
    bee_coverage = exact_cover_scale(tuple(bee_meta["plane"]), bee_warps.values())
    chia_coverage = exact_cover_scale(tuple(chia_meta["plane"]), chia_warps.values())
    coverage_pass = (
        abs(bee_coverage - float(bee["coverage"])) <= 1e-12
        and abs(chia_coverage - float(manifest["coverage"])) <= 1e-12
        and abs(bee_coverage - bee_banner_coverage) <= 5e-5
        and abs(chia_coverage - chia_banner_coverage) <= 5e-5
    )

    bee_master_path = resolve(bee["master"])
    bee_channels = {}
    primary_images = None
    primary_anchors = None
    for channel, channel_name in CHANNELS.items():
        master, master_anchor = normalized_master(bee_master_path, channel)
        fg, fg_anchors = aligned_product_set(
            "bee-3", bee_fg, channel, bee_warps, bee_coverage
        )
        bg, bg_anchors = aligned_product_set(
            "bee-3", bee_bg, channel, bee_warps, bee_coverage
        )
        score = score_site(
            master,
            fg,
            bg,
            bee["roi"],
            bands=7,
            reps=BOOT_REPS,
            seed=BOOT_SEED,
        )
        bee_channels[channel_name] = {
            "score": score,
            "class": interval_class(score),
            "paper_anchors_dn": {
                "master": master_anchor,
                "foreground": fg_anchors,
                "background": bg_anchors,
            },
        }
        if channel == 1:
            primary_images = (master, fg, bg)
            primary_anchors = {
                "master": master_anchor,
                "foreground": fg_anchors,
                "background": bg_anchors,
            }
        else:
            del master, fg, bg
            gc.collect()

    assert primary_images is not None
    master_g, foreground_g, background_g = primary_images
    primary = bee_channels["green"]["score"]
    primary_class = bee_channels["green"]["class"]
    common_anchor = float(primary_anchors["master"])
    no_per_frame_master = np.asarray(master_g, dtype=np.float32)
    no_per_frame_fg = [
        np.asarray(
            z * float(primary_anchors["foreground"][str(frame)]) / common_anchor,
            dtype=np.float32,
        )
        for z, frame in zip(foreground_g, bee_fg)
    ]
    no_per_frame_bg = [
        np.asarray(
            z * float(primary_anchors["background"][str(frame)]) / common_anchor,
            dtype=np.float32,
        )
        for z, frame in zip(background_g, bee_bg)
    ]
    no_per_frame_score = score_site(
        no_per_frame_master,
        no_per_frame_fg,
        no_per_frame_bg,
        bee["roi"],
        bands=7,
        reps=BOOT_REPS,
        seed=BOOT_SEED,
    )

    bm = pyramid_base(master_g, 7)
    bb_image = np.median(np.stack(background_g), axis=0)
    bb = pyramid_base(bb_image, 7)
    tone = tone_locality_gate(
        bb,
        bm,
        bee["roi"],
        [bee["paper_roi"], bee["midtone_anchor_roi"], bee["dark_anchor_roi"]],
    )
    paper = paper_null_gate(master_g, bb_image, bee["paper_roi"], 7)
    geometry = geometry_measurement(
        master_g, background_g, bee["geometry_windows"], 7
    )
    layer_truth = layer_truth_gate(
        distinct_contents_observed=True,
        separated_frame_runs=(min(bee_bg) - max(bee_fg) >= 15),
        peak_count=2,
    )

    sensitivities: dict[str, dict] = {}

    def add_sensitivity(name: str, score: dict) -> None:
        sensitivities[name] = {
            "score": score,
            "class": interval_class(score),
            "same_class_as_primary": interval_class(score) == primary_class,
        }

    for bands in (6, 8):
        add_sensitivity(
            f"bands-{bands}",
            score_site(
                master_g,
                foreground_g,
                background_g,
                bee["roi"],
                bands=bands,
                reps=BOOT_REPS,
                seed=BOOT_SEED,
            ),
        )
    y0, y1, x0, x1 = [int(v) for v in bee["roi"]]
    for name, roi in {
        "roi-eroded-8": [y0 + 8, y1 - 8, x0 + 8, x1 - 8],
        "roi-dilated-8": [y0 - 8, y1 + 8, x0 - 8, x1 + 8],
    }.items():
        add_sensitivity(
            name,
            score_site(
                master_g,
                foreground_g,
                background_g,
                roi,
                bands=7,
                reps=BOOT_REPS,
                seed=BOOT_SEED,
            ),
        )
    add_sensitivity(
        "single-frame-180-288",
        score_site(
            master_g,
            [foreground_g[1]],
            [background_g[1]],
            bee["roi"],
            bands=7,
            reps=BOOT_REPS,
            seed=BOOT_SEED,
        ),
    )
    linear_fg, _ = aligned_product_set(
        "bee-3",
        bee_fg,
        1,
        bee_warps,
        bee_coverage,
        interpolation=cv2.INTER_LINEAR,
    )
    linear_bg, _ = aligned_product_set(
        "bee-3",
        bee_bg,
        1,
        bee_warps,
        bee_coverage,
        interpolation=cv2.INTER_LINEAR,
    )
    add_sensitivity(
        "bilinear-registration",
        score_site(
            master_g,
            linear_fg,
            linear_bg,
            bee["roi"],
            bands=7,
            reps=BOOT_REPS,
            seed=BOOT_SEED,
        ),
    )
    del linear_fg, linear_bg
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            fg_shift = [paper_normalize(shifted(z, dy, dx), PAPER_ROI)[0] for z in foreground_g]
            bg_shift = [paper_normalize(shifted(z, dy, dx), PAPER_ROI)[0] for z in background_g]
            add_sensitivity(
                f"registration-dy{dy:+d}-dx{dx:+d}",
                score_site(
                    master_g,
                    fg_shift,
                    bg_shift,
                    bee["roi"],
                    bands=7,
                    reps=BOOT_REPS,
                    seed=BOOT_SEED,
                ),
            )
            del fg_shift, bg_shift
            gc.collect()

    decoder = rawpy_decoder_arm(
        master_g,
        foreground_g,
        background_g,
        Path(bee["stack"]),
        bee_fg,
        bee_bg,
        bee_warps,
        bee_coverage,
        bee["roi"],
        [bee["paper_roi"], bee["midtone_anchor_roi"], bee["dark_anchor_roi"]],
    )
    decoder["same_class_as_primary"] = decoder["class"] == primary_class

    # Chia is green-primary and hierarchical across the three pre-frozen sites.
    chia_master, chia_master_anchor = normalized_master(resolve(manifest["master"]), 1)
    chia_cache = {}
    chia_anchor_cache = {}
    for frame in final_chia_frames:
        values, anchors = aligned_product_set(
            "chia", [frame], 1, chia_warps, chia_coverage
        )
        chia_cache[frame] = values[0]
        chia_anchor_cache[str(frame)] = anchors[str(frame)]
    chia_sites = []
    hierarchical_inputs = []
    chia_no_per_frame_sites = []
    chia_no_per_frame_inputs = []
    for site in manifest["sites"]:
        fg = [chia_cache[int(i)] for i in site["foreground_frames"]]
        bg = [chia_cache[int(i)] for i in site["background_frames"]]
        score = score_site(
            chia_master,
            fg,
            bg,
            site["roi"],
            bands=7,
            reps=BOOT_REPS,
            seed=BOOT_SEED,
        )
        separation = min(
            abs(int(a) - int(b))
            for a in site["foreground_frames"]
            for b in site["background_frames"]
        )
        truth = layer_truth_gate(
            distinct_contents_observed=True,
            separated_frame_runs=separation >= 15,
            peak_count=2,
        )
        chia_sites.append(
            {
                "name": site["name"],
                "score": score,
                "class": interval_class(score),
                "minimum_frame_separation": separation,
                "layer_truth": truth,
            }
        )
        hierarchical_inputs.append((chia_master, fg, bg, site["roi"]))
        fg_dn = [
            np.asarray(
                chia_cache[int(i)]
                * chia_anchor_cache[str(int(i))]
                / float(chia_master_anchor),
                dtype=np.float32,
            )
            for i in site["foreground_frames"]
        ]
        bg_dn = [
            np.asarray(
                chia_cache[int(i)]
                * chia_anchor_cache[str(int(i))]
                / float(chia_master_anchor),
                dtype=np.float32,
            )
            for i in site["background_frames"]
        ]
        master_dn = np.asarray(chia_master, dtype=np.float32)
        no_norm_score = score_site(
            master_dn,
            fg_dn,
            bg_dn,
            site["roi"],
            bands=7,
            reps=BOOT_REPS,
            seed=BOOT_SEED,
        )
        chia_no_per_frame_sites.append(
            {
                "name": site["name"],
                "score": no_norm_score,
                "class": interval_class(no_norm_score),
            }
        )
        chia_no_per_frame_inputs.append((master_dn, fg_dn, bg_dn, site["roi"]))
    chia_summary = hierarchical_chia(
        hierarchical_inputs, [z["score"] for z in chia_sites]
    )
    chia_no_per_frame_summary = hierarchical_chia(
        chia_no_per_frame_inputs,
        [z["score"] for z in chia_no_per_frame_sites],
    )

    wander = flower_wander(manifest)

    commission_pass = (
        commission.get("status") == "COMMISSIONED"
        and commission.get("controls_passed") == commission.get("controls_total")
        and commission.get("plants_red") == commission.get("plants_total")
        and commission.get("controls_total") == 11
    )
    sensitivity_pass = all(
        z["same_class_as_primary"] for z in sensitivities.values()
    )
    channels_pass = all(
        bee_channels[name]["class"] == primary_class for name in CHANNELS.values()
    )
    denominator_pass = (
        primary["denominator"] >= 0.15
        and all(z["score"]["denominator"] >= 0.15 for z in chia_sites)
    )
    detail_pass = primary["detail_margin_ci95"][0] > 0.30
    required_gates = {
        "commissioning": commission_pass,
        "render_provenance": provenance_pass,
        "coverage_matches_manifest": coverage_pass,
        "positive_denominators_at_least_0.15": denominator_pass,
        "primary_detail_identity": detail_pass,
        "paper_null": bool(paper["pass"]),
        "tone_locality": bool(tone["pass"]),
        "geometry": bool(geometry["pass"]),
        "layer_truth": bool(layer_truth["pass"])
        and all(z["layer_truth"]["pass"] for z in chia_sites),
        "channels_stay_in_class": channels_pass,
        "sensitivities_stay_in_class": sensitivity_pass,
        "independent_decoder_stays_in_class": bool(decoder["same_class_as_primary"]),
    }

    lo, hi = primary["theta_ci95"]
    chia_lo = chia_summary["theta_ci95"][0]
    if not all(required_gates.values()):
        verdict = "NOT ROBUST"
    elif lo >= 0.50 and chia_lo >= 0.25 and len(chia_sites) == 3:
        verdict = "SURVIVE"
    elif lo > 0.25:
        verdict = "NARROWED"
    elif hi <= 0.25:
        verdict = "KILL"
    else:
        verdict = "NOT ROBUST"

    result = {
        "verdict": verdict,
        "claim": "A2 stack-induced depth-boundary base-band pedestal",
        "not_optical_glare": True,
        "bootstrap": {"seed": BOOT_SEED, "reps": BOOT_REPS},
        "bee": {
            "primary_channel": "green",
            "primary": primary,
            "primary_class": primary_class,
            "channels": bee_channels,
            "paper_null": paper,
            "tone_locality": tone,
            "geometry": geometry,
            "layer_truth": layer_truth,
            "sensitivities": sensitivities,
            "independent_decoder": decoder,
            "paper_anchors_dn": primary_anchors,
        },
        "chia": {
            "master_paper_anchor_dn": chia_master_anchor,
            "reference_paper_anchors_dn": chia_anchor_cache,
            "sites": chia_sites,
            "hierarchical": chia_summary,
        },
        "flower_weighted_minus_mean": wander,
        "adversarial_falsification": {
            "purpose": "Test whether removing the preregistered per-image paper normalization can recover the predecessor's flattering conclusion. This arm was added only to try to break the filed result and is not used by the verdict lookup.",
            "bee_no_per_frame_normalization": {
                "score": no_per_frame_score,
                "class": interval_class(no_per_frame_score),
            },
            "chia_no_per_frame_normalization": {
                "sites": chia_no_per_frame_sites,
                "hierarchical": chia_no_per_frame_summary,
            },
        },
        "required_gates": required_gates,
        "provenance": {
            "pass": provenance_pass and coverage_pass,
            "binary_sha256": EXPECTED_BINARY,
            "source_commit": EXPECTED_SOURCE,
            "bee_coverage": bee_coverage,
            "chia_coverage": chia_coverage,
            "bee_banner_coverage": bee_banner_coverage,
            "chia_banner_coverage": chia_banner_coverage,
            "renders": provenance,
        },
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "opencv": cv2.__version__,
            "tifffile": tifffile.__version__,
            "rawpy": rawpy.__version__,
        },
    }
    write_json(ROOT / "out" / "measurement.json", result)
    print(f"VERDICT: {verdict}")
    print(
        "bee theta: "
        f"{primary['theta']:.6f} "
        f"95% [{primary['theta_ci95'][0]:.6f}, {primary['theta_ci95'][1]:.6f}]"
    )
    print(
        "chia median theta: "
        f"{chia_summary['theta']:.6f} "
        f"95% [{chia_summary['theta_ci95'][0]:.6f}, "
        f"{chia_summary['theta_ci95'][1]:.6f}]"
    )
    failed = [name for name, ok in required_gates.items() if not ok]
    print("failed gates:", failed if failed else "none")
    print(ROOT / "out" / "measurement.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
