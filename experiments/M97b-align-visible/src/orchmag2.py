"""Scale-aware edge width: the confound removed WITHOUT resampling either arm.

Why this file exists. `orchmag.py` tried to remove the magnification confound
by resampling one arm onto the other's scale and then measuring edge width.
Its own B3 plant killed it: rescaling the null by 1.4% should change widths by
1.4%, and it changed them by 20% (0.7962 against a theoretical 1.0139). The
missing 19% is interpolation blur. Resampling one arm and not the other makes
the resampled arm measure blunter, so every "scale-matched" width number in
`orchmag.py` -- including its 1.2003 verdict -- is inflated and I withdraw it.
The plant caught the defect before the number was reported. That is the point
of the plant.

The fix is not a better interpolator. It is to stop resampling images at all.
An isotropic scale is a change of COORDINATES, so it can be absorbed into WHERE
each profile is sampled instead of into a new image:

    a point p in aligned coords corresponds to  q(p) = c + (p - d - c) / s
    a step of t pixels along n in aligned coords is a step of t/s along n in
    null coords, because an isotropic scale preserves directions

So the null is sampled at q(p) + (t/s)*n while the aligned arm is sampled at
p + t*n. Each arm gets exactly ONE bilinear sample per profile point, at
comparably non-integer offsets. The interpolation cost is now identical on both
sides, and the returned widths are already in the same units, so they can be
divided.

Pre-registered bars, written before the first run:

  C1 PLACEBO. Arm against itself with s=1, d=0 must be exactly 1.000000.
  C2 COMPENSATION IS WIRED IN. Feeding a deliberately wrong scale (s * 1.03)
     must move the ratio by about 3%. A compensation that cannot be detuned is
     a compensation that is not connected -- this is the disconnected-probe
     check, and 0.000 change would mean the scale argument does nothing.
  C3 DIRECTION. Blurring the aligned arm by sigma=1.0 must push the
     null/aligned ratio clearly below 1.0.
  C4 SWAP. Exchanging numerator and denominator must return the reciprocal to
     within 1e-3.
  C5 VERDICT ON SECTION 10. FAILING VALUE STATED IN ADVANCE: if the
     scale-compensated null/aligned width ratio is <= 1.0050, section 10's
     edge-width result is a magnification artefact and I withdraw it, exactly
     as the orchestrator withdrew their crops. Above 1.0050 it survives.

  C6 WHERE THE EDGES ARE. Section 10 paired edges between two arms that differ
     in scale by 1.4% using a +/-8 px re-centring window. A 1.4% scale displaces
     a feature at radius r by 0.0139*r px, which exceeds 8 px beyond r = 575 px.
     So section 10's surviving pairs were concentrated near the centre -- where
     residual misregistration is zero by construction. This run reports the
     ratio in radial annuli so that concentration is visible instead of hidden.

  C7 SELECTION SYMMETRY -- added after the first run failed C3.
     The first run picked edges only where the ALIGNED arm had its strongest
     gradients and got 1.3216, with a sigma=1.0 blur of the aligned arm barely
     denting it (1.2406, C3 FAIL) and a 3% scale detune moving the answer by
     21% (C2, a 7x over-response). Both symptoms are one cause: choosing
     locations by one arm's extremes makes the other arm regress to the mean
     there, so the comparison is rigged before any physics enters. Section 10
     avoided this by selecting on the MEAN of two co-located arms; that option
     died when the arms turned out not to be co-located. I withdraw 1.3216.
     The fix is to select on the UNION of each arm's own strong edges and to
     report the two halves separately:
        ratio_A  -- locations chosen by the aligned arm, biased FOR aligned
        ratio_Z  -- locations chosen by the null arm,    biased FOR null
     Under a symmetric bias the geometric mean sqrt(ratio_A * ratio_Z) is
     unbiased, and the two halves bracket it. STATED IN ADVANCE:
       * if ratio_A > 1 and ratio_Z < 1 and their geometric mean is inside
         [0.995, 1.005], the whole effect is selection bias and section 10's
         edge-width result is withdrawn;
       * only if the GEOMETRIC MEAN exceeds 1.0050 does section 10 survive.
     C5 is now judged on the geometric mean, not on ratio_A.
"""

import json
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, map_coordinates

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from width import HALF, TS, widths  # noqa: E402  (same instrument as section 10)

ALIGNED = r"C:\dev\strehl-out\M86-align\bee-3-ALIGNED.tif"
ZOOMNULL = r"C:\dev\strehl-out\M86-align\bee3-zoomnull.tif"
IN_JSON = r"C:\dev\strehl-out\M97\orchmag.json"
OUT = r"C:\dev\strehl-out\M97\orchmag2.json"

N_EDGES = 60000
MARGIN = HALF + 8


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    g = a[:, :, 1] if a.ndim == 3 else a
    return g.astype(np.float32)


def pick_edges(ref, n_want, seed=97):
    s = gaussian_filter(ref, 2.0)
    gy, gx = np.gradient(s)
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, 99.5)
    ys, xs = np.nonzero(mag > thr)
    keep = ((ys > MARGIN) & (ys < ref.shape[0] - MARGIN) &
            (xs > MARGIN) & (xs < ref.shape[1] - MARGIN))
    ys, xs = ys[keep], xs[keep]
    rng = np.random.default_rng(seed)
    if ys.size > n_want:
        i = rng.choice(ys.size, n_want, replace=False)
        ys, xs = ys[i], xs[i]
    d = mag[ys, xs]
    return (ys.astype(np.float64), xs.astype(np.float64),
            gy[ys, xs] / d, gx[ys, xs] / d)


def sample(img, cy, cx, ny, nx, step):
    """One profile per edge, sampled along n at spacing `step` source px.

    `step` is the source-pixel distance corresponding to one unit of TS, so a
    profile taken with step = 1/s in an arm magnified by s covers the same
    physical extent as step = 1 in the reference arm.
    """
    yy = cy[:, None] + ny[:, None] * (TS[None, :] * step)
    xx = cx[:, None] + nx[:, None] * (TS[None, :] * step)
    v = map_coordinates(img, [yy.ravel(), xx.ravel()], order=1, mode="nearest")
    return v.reshape(len(cy), len(TS))


def ratio(num_img, num_c, num_step, den_img, den_c, den_step, ny, nx):
    wn = widths(sample(num_img, num_c[0], num_c[1], ny, nx, num_step))
    wd = widths(sample(den_img, den_c[0], den_c[1], ny, nx, den_step))
    both = np.isfinite(wn) & np.isfinite(wd)
    if both.sum() < 200:
        return float("nan"), int(both.sum()), None
    return (float(np.median(wn[both]) / np.median(wd[both])),
            int(both.sum()), both)


def main():
    with open(IN_JSON, encoding="utf-8") as fh:
        prev = json.load(fh)
    s = prev["scale"]["s_null_to_aligned"]
    # `signcheck.py` later falsified the global-similarity model these numbers
    # assume (per-tile radius ratios spread by 6.5% where a planted global
    # scale spreads by 0.17%). M97_S lets the whole measurement be repeated
    # under a different global scale so the answer's sensitivity to a model we
    # know to be wrong can be reported instead of hidden.
    import os
    if os.environ.get("M97_S"):
        s = float(os.environ["M97_S"])
        print(f"M97_S override: s={s:.6f}", flush=True)
        globals()["OUT"] = OUT.replace(".json", f"-s{s:.5f}.json")
    # orchmag.py measured d on a centred 4000 px window; the mapping below is
    # expressed in full-frame coordinates about the frame centre, and the
    # translation is the same because the window was centred.
    dy, dx = prev["match_shift"]
    print(f"using s={s:.6f}  d=({dy},{dx})  [null is 1/s = "
          f"{1.0 / s:.6f}x the aligned magnification]", flush=True)

    a = load(ALIGNED)
    z = load(ZOOMNULL)
    h, w = a.shape
    cy0, cx0 = (h - 1) / 2.0, (w - 1) / 2.0

    def to_null(py, px, scale):
        return (cy0 + (py - dy - cy0) / scale,
                cx0 + (px - dx - cx0) / scale)

    def to_aligned(qy, qx, scale):
        return (cy0 + (qy - cy0) * scale + dy,
                cx0 + (qx - cx0) * scale + dx)

    # C7: select on the union of each arm's own strong edges. Locations chosen
    # in the null are mapped into aligned coordinates so both halves live in
    # one coordinate system; the null is never resampled, only re-indexed.
    ys, xs, ny, nx = pick_edges(a, N_EDGES)
    zy, zx, zny, znx = pick_edges(z, N_EDGES)
    zy, zx = to_aligned(zy, zx, s)
    inb = ((zy > MARGIN) & (zy < h - MARGIN) & (zx > MARGIN) & (zx < w - MARGIN))
    zy, zx, zny, znx = zy[inb], zx[inb], zny[inb], znx[inb]
    print(f"selection: {ys.size} aligned-chosen, {zy.size} null-chosen",
          flush=True)

    rad = np.hypot(ys - cy0, xs - cx0)
    out = {"s_null_to_aligned": s, "d": [dy, dx],
           "n_edge_candidates": int(ys.size),
           "n_null_chosen": int(zy.size),
           "bars": {"C5_withdraw_if_le": 1.0050}}

    # ---- C1 placebo
    r_pl, n_pl, _ = ratio(a, (ys, xs), 1.0, a, (ys, xs), 1.0, ny, nx)
    out["C1_placebo"] = {"ratio": r_pl, "n": n_pl,
                         "pass": abs(r_pl - 1.0) < 1e-6}

    # ---- treatment: null/aligned, scale compensated, no image resampled.
    # Computed twice -- once on aligned-chosen locations, once on null-chosen --
    # so the selection bias is bracketed rather than hidden (C7).
    def arm(py, px, pny, pnx):
        qy, qx = to_null(py, px, s)
        return ratio(z, (qy, qx), 1.0 / s, a, (py, px), 1.0, pny, pnx)

    r_A, n_A, _ = arm(ys, xs, ny, nx)
    r_Z, n_Z, _ = arm(zy, zx, zny, znx)
    r_geo = float(np.sqrt(r_A * r_Z))
    qy, qx = to_null(ys, xs, s)
    out["treatment"] = {"ratio_aligned_chosen": r_A, "n_A": n_A,
                        "ratio_null_chosen": r_Z, "n_Z": n_Z,
                        "geometric_mean": r_geo,
                        "brackets_one": bool((r_A - 1.0) * (r_Z - 1.0) < 0)}
    print(f"C1 placebo {r_pl:.6f}", flush=True)
    print(f"C7 ratio_A (aligned-chosen) {r_A:.4f} (n={n_A})", flush=True)
    print(f"C7 ratio_Z (null-chosen)    {r_Z:.4f} (n={n_Z})", flush=True)
    print(f"C7 geometric mean           {r_geo:.4f}", flush=True)

    # ---- C2 detune: a wrong scale must move the answer, on the unbiased
    # estimator, and by an amount commensurate with the detune (not 7x it).
    det = {}
    for k in (1.03, 0.97):
        qa, xa = to_null(ys, xs, s * k)
        r2a, _, _ = ratio(z, (qa, xa), 1.0 / (s * k), a, (ys, xs), 1.0, ny, nx)
        qb, xb = to_null(zy, zx, s * k)
        r2b, _, _ = ratio(z, (qb, xb), 1.0 / (s * k), a, (zy, zx), 1.0, zny, znx)
        r2 = float(np.sqrt(r2a * r2b))
        det[f"x{k:.2f}"] = {"geo": r2, "delta": r2 - r_geo}
        print(f"C2 detune s*{k:.2f} -> geo {r2:.4f} (delta {r2 - r_geo:+.4f})",
              flush=True)
    moved = max(abs(v["delta"]) for v in det.values())
    out["C2_detune"] = {"runs": det, "max_abs_delta": moved,
                        "pass": moved > 0.005}

    # ---- C3 direction plant, on the unbiased estimator
    ab = gaussian_filter(a, 1.0)
    d1, _, _ = ratio(z, (qy, qx), 1.0 / s, ab, (ys, xs), 1.0, ny, nx)
    qz, xz = to_null(zy, zx, s)
    d2, _, _ = ratio(z, (qz, xz), 1.0 / s, ab, (zy, zx), 1.0, zny, znx)
    r_dir = float(np.sqrt(d1 * d2))
    out["C3_direction"] = {"geo": r_dir, "ratio_A": d1, "ratio_Z": d2,
                           "pass": bool(r_dir < 1.0)}
    print(f"C3 blur(aligned) -> geo {r_dir:.4f}  pass={r_dir < 1.0}", flush=True)

    # ---- C4 swap
    r_sw, n_sw, _ = ratio(a, (ys, xs), 1.0, z, (qy, qx), 1.0 / s, ny, nx)
    out["C4_swap"] = {"ratio": r_sw, "product": r_sw * r_A,
                      "pass": abs(r_sw * r_A - 1.0) < 1e-3}
    print(f"C4 swap {r_sw:.4f}  product {r_sw * r_A:.6f}", flush=True)

    # ---- C6 radial annuli, on the unbiased estimator.
    # A similarity has zero residual at its own centre by construction, so a
    # genuine registration effect must GROW with radius. That is a falsifiable
    # shape, and it needs its own control: the sigma=1.0 uniform blur of C3 is
    # applied everywhere, so its radial profile must be FLAT. A rising
    # treatment profile against a flat plant profile is registration; two
    # rising profiles would mean the instrument itself has a radial trend and
    # the finding is withdrawn. (I struck an earlier radial claim in section 6
    # for want of exactly this control.)
    ann = []
    radz = np.hypot(zy - cy0, zx - cx0)
    qzy, qzx = to_null(zy, zx, s)
    edges = [0, 500, 1000, 1500, 2000, 2500, 3000, 4300]
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (rad >= lo) & (rad < hi)
        mz = (radz >= lo) & (radz < hi)
        if m.sum() < 300 or mz.sum() < 300:
            continue
        r_a, n_a, _ = ratio(z, (qy[m], qx[m]), 1.0 / s,
                            a, (ys[m], xs[m]), 1.0, ny[m], nx[m])
        r_b, n_b, _ = ratio(z, (qzy[mz], qzx[mz]), 1.0 / s,
                            a, (zy[mz], zx[mz]), 1.0, zny[mz], znx[mz])
        p_a, _, _ = ratio(z, (qy[m], qx[m]), 1.0 / s,
                          ab, (ys[m], xs[m]), 1.0, ny[m], nx[m])
        p_b, _, _ = ratio(z, (qzy[mz], qzx[mz]), 1.0 / s,
                          ab, (zy[mz], zx[mz]), 1.0, zny[mz], znx[mz])
        g = float(np.sqrt(r_a * r_b)) if np.isfinite(r_a * r_b) else float("nan")
        gp = float(np.sqrt(p_a * p_b)) if np.isfinite(p_a * p_b) else float("nan")
        ann.append({"r_lo": lo, "r_hi": hi, "ratio_A": r_a, "ratio_Z": r_b,
                    "geo": g, "geo_blur_plant": gp, "n": [n_a, n_b]})
        print(f"    annulus {lo:5d}-{hi:5d}  A {r_a:.4f}  Z {r_b:.4f}  "
              f"geo {g:.4f}   blur-plant {gp:.4f}", flush=True)
    out["C6_annuli"] = ann
    good = [x for x in ann if np.isfinite(x["geo"]) and np.isfinite(x["geo_blur_plant"])]
    if len(good) >= 3:
        tr_span = good[-1]["geo"] - good[0]["geo"]
        pl_span = good[-1]["geo_blur_plant"] - good[0]["geo_blur_plant"]
        out["C6_radial_control"] = {
            "treatment_span": tr_span, "blur_plant_span": pl_span,
            "pass": bool(tr_span > 0 and abs(pl_span) < abs(tr_span) / 2)}
        print(f"C6 radial span: treatment {tr_span:+.4f}  "
              f"uniform-blur plant {pl_span:+.4f}  "
              f"pass={out['C6_radial_control']['pass']}", flush=True)

    # ---- C5 verdict, judged on the geometric mean per C7
    out["C5_verdict"] = {"geometric_mean": r_geo, "withdraw_if_le": 1.0050,
                         "survives": bool(r_geo > 1.0050)}

    # ---- analytic Tenengrad correction (no resampling, so no aliasing)
    t_a = prev["tenengrad"]["aligned"]
    t_z = prev["tenengrad"]["null"]
    out["tenengrad_analytic"] = {
        "raw_aligned_over_null": t_a / t_z,
        "corrected_aligned_over_null": (t_a / t_z) * (s * s),
        "note": "null is 1/s more magnified, so its mean |grad|^2 is depressed "
                "by s^2; multiplying by s^2 puts both arms at one magnification"}

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    print("\n--- verdict ---")
    print(f"C1 placebo      {r_pl:.6f}  pass={out['C1_placebo']['pass']}")
    print(f"C2 detune       {moved:.4f}  pass={out['C2_detune']['pass']}")
    print(f"C3 direction    {r_dir:.4f}  pass={out['C3_direction']['pass']}")
    print(f"C4 swap product {r_sw * r_A:.6f}  pass={out['C4_swap']['pass']}")
    print(f"C7 ratio_A {r_A:.4f}  ratio_Z {r_Z:.4f}  brackets 1.0 = "
          f"{out['treatment']['brackets_one']}")
    print(f"C5 width null/aligned, scale + selection corrected = {r_geo:.4f}  "
          f"survives={out['C5_verdict']['survives']}")
    print(f"tenengrad raw {t_a / t_z:.4f} -> corrected "
          f"{(t_a / t_z) * s * s:.4f}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
