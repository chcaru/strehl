"""Commission all M-PHASE0-VEIL2 gates before real measurement.

Each control has a paired planted defect.  A plant is successful only when the
named check reads RED; merely obtaining green controls is insufficient.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from veil2lib import (  # noqa: E402
    Similarity,
    detrended_wander_jackknife,
    expand5,
    exact_cover_scale,
    geometry_gate,
    layer_truth_gate,
    paper_null_gate,
    pyramid_base,
    reduce5,
    remap_similarity,
    remap_similarity_catmull,
    score_site,
    tone_locality_gate,
    write_json,
)


def fixture(n: int = 1024) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int, int]]:
    """Analytic fixed-base planes; no pyramid function participates."""
    yy, xx = np.indices((n, n))
    checker = np.where(((xx + yy) & 1) == 0, 1.0, -1.0).astype(np.float32)
    stripe = np.where((xx % 8) < 4, 1.0, -1.0).astype(np.float32)
    background = np.float32(0.40) + np.float32(0.08) * checker
    foreground = np.float32(0.80) + np.float32(0.02) * stripe
    roi = (n // 4, 3 * n // 4, n // 4, 3 * n // 4)
    return background, foreground, roi


def master_at(theta: float, background: np.ndarray, foreground: np.ndarray) -> np.ndarray:
    # The base is mixed analytically; the detail is copied from the background.
    # This is independent of the P7 implementation being checked.
    detail = background - np.float32(0.40)
    base = np.float32((1.0 - theta) * 0.40 + theta * 0.80)
    return base + detail


def slow_reduce(a: np.ndarray) -> np.ndarray:
    """Tiny independent loop implementation for the fixed external predicate."""
    k = [1 / 16, 4 / 16, 6 / 16, 4 / 16, 1 / 16]
    h, w = a.shape
    oh, ow = (h + 1) // 2, (w + 1) // 2
    tmp = np.empty((h, ow), np.float32)
    for y in range(h):
        for x in range(ow):
            tmp[y, x] = sum(
                k[t] * a[y, min(max(2 * x + t - 2, 0), w - 1)]
                for t in range(5)
            )
    out = np.empty((oh, ow), np.float32)
    for y in range(oh):
        for x in range(ow):
            out[y, x] = sum(
                k[t] * tmp[min(max(2 * y + t - 2, 0), h - 1), x]
                for t in range(5)
            )
    return out


def slow_expand(a: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Independent loop form of Rust's explicit even/odd EXPAND phases."""
    sh, sw = a.shape
    dh, dw = shape
    tmp = np.empty((sh, dw), np.float32)
    for y in range(sh):
        for x in range(dw):
            c = x // 2
            if x % 2 == 0:
                tmp[y, x] = (
                    0.125 * a[y, max(c - 1, 0)]
                    + 0.75 * a[y, c]
                    + 0.125 * a[y, min(c + 1, sw - 1)]
                )
            else:
                tmp[y, x] = 0.5 * (a[y, c] + a[y, min(c + 1, sw - 1)])
    out = np.empty((dh, dw), np.float32)
    for y in range(dh):
        c = y // 2
        for x in range(dw):
            if y % 2 == 0:
                out[y, x] = (
                    0.125 * tmp[max(c - 1, 0), x]
                    + 0.75 * tmp[c, x]
                    + 0.125 * tmp[min(c + 1, sh - 1), x]
                )
            else:
                out[y, x] = 0.5 * (
                    tmp[c, x] + tmp[min(c + 1, sh - 1), x]
                )
    return out


def row(cid: str, control: dict, plant: dict, reading: object) -> dict:
    return {
        "id": cid,
        "control_pass": bool(control["pass"]),
        "plant_red": not bool(plant["pass"]),
        "control": control,
        "plant": plant,
        "reading": reading,
    }


def main() -> int:
    out = ROOT / "out" / "commission.json"
    bg, fg, roi = fixture()
    rows: list[dict] = []

    # C1: known theta ladder, plus an external slow-loop check on REDUCE.
    ladder = {}
    c1_pass = True
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        s = score_site(
            master_at(t, bg, fg),
            [fg, fg, fg],
            [bg, bg, bg],
            roi,
            bands=7,
            reps=300,
        )
        ladder[str(t)] = s["theta"]
        c1_pass &= abs(s["theta"] - t) <= 0.02
    small = np.arange(17 * 19, dtype=np.float32).reshape(17, 19) / 37.0
    fast = reduce5(small)
    slow = slow_reduce(small)
    reduce_error = float(np.max(np.abs(fast - slow)))
    fast_up = expand5(fast, small.shape)
    slow_up = slow_expand(slow, small.shape)
    expand_error = float(np.max(np.abs(fast_up - slow_up)))
    c1_pass &= reduce_error <= 2e-6 and expand_error <= 2e-6
    c1 = {
        "pass": c1_pass,
        "theta_ladder": ladder,
        "reduce_max_abs": reduce_error,
        "expand_max_abs": expand_error,
    }
    zero = score_site(
        master_at(0.0, bg, fg), [fg] * 3, [bg] * 3, roi, bands=7, reps=300
    )
    p1 = {"pass": zero["theta_ci95"][0] >= 0.50, "theta": zero["theta"]}
    rows.append(row("C1-known-theta", c1, p1, "analytic theta and slow REDUCE"))

    # C2: polarity/label order.
    den = float(pyramid_base(fg, 7)[roi[0]:roi[1], roi[2]:roi[3]].mean()
                - pyramid_base(bg, 7)[roi[0]:roi[1], roi[2]:roi[3]].mean())
    c2 = {"pass": den > 0.15, "denominator": den}
    p2 = {"pass": -den > 0.15, "denominator": -den}
    rows.append(row("C2-layer-sign", c2, p2, den))

    # C3: copying background detail passes; blur is not a pedestal win.
    base_score = score_site(
        master_at(0.70, bg, fg), [fg] * 3, [bg] * 3, roi, bands=7, reps=300
    )
    blurred = cv2.GaussianBlur(master_at(0.70, bg, fg), (0, 0), 1.5)
    blur_score = score_site(
        blurred, [fg] * 3, [bg] * 3, roi, bands=7, reps=300
    )
    c3 = {
        "pass": (
            base_score["detail_margin_ci95"][0] > 0.30
            and base_score["detail"]["projection_background"] >= 0.98
        ),
        "margin": base_score["detail"]["corr_margin"],
        "projection": base_score["detail"]["projection_background"],
    }
    p3 = {
        "pass": (
            blur_score["detail_margin_ci95"][0] > 0.30
            and blur_score["detail"]["projection_background"] >= 0.98
        ),
        "margin": blur_score["detail"]["corr_margin"],
        "projection": blur_score["detail"]["projection_background"],
    }
    rows.append(row("C3-detail-not-blur", c3, p3, "sigma=1.5 at full effect"))

    # C4: an ROI-only correction is local; a global gamma is not.
    baseline = np.full((512, 512), 0.58, np.float32)
    target = (192, 320, 192, 320)
    anchors = [(16, 112, 16, 112), (16, 112, 400, 496), (400, 496, 16, 112)]
    local = baseline.copy()
    local[target[0]:target[1], target[2]:target[3]] -= 0.10
    gamma = np.power(baseline, 1.40).astype(np.float32)
    c4 = tone_locality_gate(baseline, local, target, anchors)
    p4 = tone_locality_gate(baseline, gamma, target, anchors)
    rows.append(row("C4-tone-locality", c4, p4, p4["max_anchor_fraction"]))

    # C5: paper null is independently untouched, then receives +0.06.
    paper = np.ones((1024, 1024), np.float32)
    paper_roi = (128, 384, 640, 896)
    c5 = paper_null_gate(paper, paper, paper_roi, 7)
    shifted = paper.copy()
    shifted[paper_roi[0]:paper_roi[1], paper_roi[2]:paper_roi[3]] += 0.06
    p5 = paper_null_gate(shifted, paper, paper_roi, 7)
    rows.append(row("C5-paper-null", c5, p5, p5["median"]))

    # C6: disjoint geometry estimates must agree; exactly one pixel must fail.
    c6 = geometry_gate([(0.10, -0.20), (0.15, -0.15)])
    p6 = geometry_gate([(0.10, -0.20), (1.10, -0.20)])
    rows.append(row("C6-geometry", c6, p6, p6["disagreement_px"]))

    # C7: a plane is removable; an 835-DN radial bowl is not.
    yy, xx = np.indices((512, 512), dtype=np.float64)
    plane = 17.0 + 0.03 * xx - 0.02 * yy
    c7 = detrended_wander_jackknife(plane)
    rr = ((xx - 255.5) ** 2 + (yy - 255.5) ** 2)
    rr /= rr.max()
    bowl = 835.0 * rr
    p7 = detrended_wander_jackknife(plane + bowl)
    p7["pass"] = p7["ci95_jackknife"][0] <= 400.0
    rows.append(
        row(
            "C7-flat-wander",
            c7,
            p7,
            {
                "point_dn": p7["p95_p05_dn"],
                "lower95_dn": p7["ci95_jackknife"][0],
            },
        )
    )

    # C8: an external content label, not the response generator, establishes
    # layer truth. A single-depth curve is allowed to have two peaks and fails.
    c8 = layer_truth_gate(
        distinct_contents_observed=True, separated_frame_runs=True, peak_count=2
    )
    p8 = layer_truth_gate(
        distinct_contents_observed=False, separated_frame_runs=False, peak_count=2
    )
    rows.append(row("C8-layer-truth", c8, p8, "same peak count, opposite predicate"))

    # C9: Rust gathers with Catmull-Rom a=-1/2, not OpenCV's a=-3/4 cubic.
    impulse = np.zeros((8, 8), dtype=np.float32)
    impulse[3, 2] = 1.0
    half_pixel = Similarity(1.0, 0.0, 0.5, 0.0)
    expected = -1.0 / 16.0
    catmull_read = float(remap_similarity_catmull(impulse, half_pixel)[3, 3])
    opencv_read = float(
        remap_similarity(impulse, half_pixel, interpolation=cv2.INTER_CUBIC)[3, 3]
    )
    c9 = {
        "pass": abs(catmull_read - expected) <= 1e-7,
        "expected_external": expected,
        "reading": catmull_read,
    }
    p9 = {
        "pass": abs(opencv_read - expected) <= 1e-7,
        "expected_external": expected,
        "reading": opencv_read,
    }
    rows.append(row("C9-catmull-gather", c9, p9, opencv_read))

    # C10: a translated 100x100 plane has an analytic 3-pixel cover bound.
    # Using the four-decimal console banner instead of the sidecar is the plant.
    expected_cover = 36.0 / 49.0
    cover_read = exact_cover_scale(
        (100, 100),
        [Similarity(1.0, 0.0, 0.0, 0.0), Similarity(1.0, 0.0, 10.0, 0.0)],
    )
    rounded_cover = round(cover_read, 4)
    c10 = {
        "pass": abs(cover_read - expected_cover) <= 1e-12,
        "expected_external": expected_cover,
        "reading": cover_read,
    }
    p10 = {
        "pass": abs(rounded_cover - expected_cover) <= 1e-12,
        "expected_external": expected_cover,
        "reading": rounded_cover,
    }
    rows.append(row("C10-exact-cover-scale", c10, p10, rounded_cover))

    # C11: frame-run resampling must widen the detail interval when one of
    # three directly generated frames has the opposite detail sign.
    small_bg, small_fg, small_roi = fixture(256)
    detail_master = master_at(0.70, small_bg, small_fg)
    detail_background = [small_bg, small_bg, np.float32(0.80) - small_bg]
    detail_foreground = [small_fg, small_fg, small_fg]
    resampled = score_site(
        detail_master,
        detail_foreground,
        detail_background,
        small_roi,
        bands=7,
        reps=2000,
        resample_frame_runs=True,
    )
    fixed_frames = score_site(
        detail_master,
        detail_foreground,
        detail_background,
        small_roi,
        bands=7,
        reps=2000,
        resample_frame_runs=False,
    )
    resampled_width = (
        resampled["detail_margin_ci95"][1] - resampled["detail_margin_ci95"][0]
    )
    fixed_width = (
        fixed_frames["detail_margin_ci95"][1]
        - fixed_frames["detail_margin_ci95"][0]
    )
    c11 = {
        "pass": resampled_width >= 1.50,
        "detail_ci95": resampled["detail_margin_ci95"],
        "width": resampled_width,
    }
    p11 = {
        "pass": fixed_width >= 1.50,
        "detail_ci95": fixed_frames["detail_margin_ci95"],
        "width": fixed_width,
    }
    rows.append(
        row("C11-detail-frame-bootstrap", c11, p11, fixed_width)
    )

    controls = sum(r["control_pass"] for r in rows)
    reds = sum(r["plant_red"] for r in rows)
    ok = controls == len(rows) and reds == len(rows)
    result = {
        "status": "COMMISSIONED" if ok else "NOT COMMISSIONED",
        "controls_passed": controls,
        "controls_total": len(rows),
        "plants_red": reds,
        "plants_total": len(rows),
        "all_plants_red": reds == len(rows),
        "rows": rows,
        "versions": {
            "numpy": np.__version__,
            "opencv": cv2.__version__,
        },
    }
    write_json(out, result)
    print(f"controls: {controls}/{len(rows)} PASS")
    print(f"plants  : {reds}/{len(rows)} RED")
    for r in rows:
        print(
            f"{r['id']:<22} control={'PASS' if r['control_pass'] else 'FAIL'} "
            f"plant={'RED' if r['plant_red'] else 'MISSED'}"
        )
    print(result["status"])
    print(out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
