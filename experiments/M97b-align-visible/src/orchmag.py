"""Does the aligned-vs-zoomnull ratio measure sharpness, or magnification?

The orchestrator retracted fact 1235 (and discipline 605) after measuring that
`bee-3-ALIGNED.tif` is ~1.25% more magnified than `bee3-zoomnull.tif`, so the
crops both of us judged by eye were not comparing like with like. I accept the
magnification measurement -- I re-derive it here independently -- but the
retraction stops one step short of the thing that decides it.

The missing step is a PLANT. "The arms differ in magnification" does not by
itself tell you what that difference DOES to a given metric. Two metrics can be
confounded by the same 1.25% in OPPOSITE directions:

  * Tenengrad is a gradient ENERGY per pixel. Magnify a scene by s and the same
    intensity rise is spread over s x more pixels, so |grad| per pixel falls as
    1/s and mean |grad|^2 falls as 1/s^2. The MORE magnified arm scores LOWER.
    The aligned arm is the more magnified one. So magnification alone pushes
    the aligned/null Tenengrad ratio BELOW 1 -- toward the null everyone has
    been reporting.

  * Edge width is a DISTANCE in pixels. Magnify by s and every width grows by
    s. The MORE magnified arm measures WIDER, i.e. blunter. So magnification
    alone pushes the null/aligned width ratio BELOW 1 too -- but section 10
    measured it ABOVE 1, at 1.0179. A confound that runs against a result
    cannot be the explanation of that result.

So this script measures, for each metric, the pure-magnification response R_mag
by rescaling ONE arm and comparing it with itself -- zero registration content,
the confound in isolation -- and divides it out. Residual = measured / R_mag.

Pre-registered bars, written before the first run:

  B1 PLACEBO. metric(X) vs metric(X) must be exactly 1.000000. Any deviation
     means the harness is not comparing what it claims to.
  B2 IDENTITY RESAMPLE. rescale(X, 1.0) must return metric ratios inside the
     placebo band. This proves the resampler is wired in and is a no-op at
     s = 1, so a non-unit R_mag at s = 1.0125 is the scale and not the plumbing.
  B3 MAGNIFICATION PLANT, SIGNED PREDICTION. Stated before running:
        Tenengrad  R_mag  <  1  (expect ~1/s^2 = 0.9754)
        Edge width R_mag  <  1  for null/aligned orientation (expect ~1/s)
     If either comes back on the wrong side of 1, my reasoning above is wrong
     and I report that, not a repaired story.
  B4 VERDICT ON SECTION 10. After dividing out R_mag, the scale-matched
     null/aligned edge-width ratio must stay above 1.0 for section 10 to
     survive. FAILING VALUE STATED IN ADVANCE: if the scale-matched ratio is
     <= 1.0050 I withdraw section 10's edge-width result as a magnification
     artefact, exactly as the orchestrator withdrew their crops.
  B5 RESAMPLER HAZARD. Nearest-neighbour cannot add blur -- that is true and it
     is why the orchestrator chose it -- but at a non-integer scale it
     duplicates and drops whole pixel columns, which ADDS high-frequency
     gradient energy. For a gradient-energy metric that is fatal. So R_mag is
     computed with BOTH nearest-neighbour and a smooth interpolator. If the two
     disagree for Tenengrad by more than the placebo band, then any
     NN-scale-matched Tenengrad number is contaminated and must not be quoted.

Everything is measured on a central window, away from the frame boundary and
the coverage margin, because a fill boundary is the artefact that read a fake
1.4565x for M86 and it has no business inside this measurement.
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
OUT = r"C:\dev\strehl-out\M97\orchmag.json"

WIN = 4000          # central window side for all metric work
SWIN = 1400         # central window side for the scale search (matches ORCH)
N_EDGES = 40000     # candidate edges before validity culling


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    g = a[:, :, 1] if a.ndim == 3 else a
    return g.astype(np.float32)


def centre_win(img, side):
    h, w = img.shape
    y0, x0 = (h - side) // 2, (w - side) // 2
    return img[y0:y0 + side, x0:x0 + side]


def rescale(img, s, order):
    """Resample `img` by factor `s` about its own centre, same output shape.

    A destination pixel at radius r from the centre reads the source at radius
    r / s, so s > 1 magnifies. order=0 is nearest-neighbour, order=3 is a cubic
    spline; both are exercised because B5 says the choice can matter.
    """
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yy = cy + (yy - cy) / s
    xx = cx + (xx - cx) / s
    return map_coordinates(img, [yy, xx], order=order, mode="nearest").astype(np.float32)


def ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def best_shift(a, b):
    """Translation of `b` relative to `a` by FFT cross-correlation."""
    fa = np.fft.rfft2(a - a.mean())
    fb = np.fft.rfft2(b - b.mean())
    c = np.fft.irfft2(fa * np.conj(fb), s=a.shape)
    k = np.unravel_index(np.argmax(c), c.shape)
    dy = k[0] - (a.shape[0] if k[0] > a.shape[0] // 2 else 0)
    dx = k[1] - (a.shape[1] if k[1] > a.shape[1] // 2 else 0)
    return int(dy), int(dx)


def shift_int(img, dy, dx):
    return np.roll(np.roll(img, dy, axis=0), dx, axis=1)


def find_scale(aligned, null, lo, hi, n):
    """Scale s such that magnifying `null` by s best matches `aligned`.

    Translation is removed at each rung by an INTEGER FFT shift only: a
    sub-pixel shift resamples, and resampling adds blur to the arm that gets
    shifted, which would bias exactly the quantity under test.
    """
    a = centre_win(aligned, SWIN)
    z = centre_win(null, SWIN)
    grid = np.linspace(lo, hi, n)
    best = (-2.0, None)
    curve = []
    for s in grid:
        zs = rescale(z, float(s), order=3)
        dy, dx = best_shift(a, zs)
        v = ncc(a, shift_int(zs, dy, dx))
        curve.append((float(s), v, dy, dx))
        if v > best[0]:
            best = (v, float(s))
    railed = best[1] in (float(grid[0]), float(grid[-1]))
    return best[1], best[0], railed, curve


def tenengrad(img):
    gy, gx = np.gradient(img)
    return float(np.mean(gy * gy + gx * gx))


def pick_edges(ref, n_want, seed=97, margin=HALF + 6):
    s = gaussian_filter(ref, 2.0)
    gy, gx = np.gradient(s)
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, 99.5)
    ys, xs = np.nonzero(mag > thr)
    keep = ((ys > margin) & (ys < ref.shape[0] - margin) &
            (xs > margin) & (xs < ref.shape[1] - margin))
    ys, xs = ys[keep], xs[keep]
    rng = np.random.default_rng(seed)
    if ys.size > n_want:
        i = rng.choice(ys.size, n_want, replace=False)
        ys, xs = ys[i], xs[i]
    d = mag[ys, xs]
    return ys, xs, gy[ys, xs] / d, gx[ys, xs] / d


def profiles(img, ys, xs, ny, nx):
    yy = ys[:, None] + ny[:, None] * TS[None, :]
    xx = xs[:, None] + nx[:, None] * TS[None, :]
    v = map_coordinates(img, [yy.ravel(), xx.ravel()], order=1, mode="nearest")
    return v.reshape(len(ys), len(TS))


def width_ratio(num, den, ys, xs, ny, nx):
    """median(width(num)) / median(width(den)) over edges valid in BOTH."""
    wn = widths(profiles(num, ys, xs, ny, nx))
    wd = widths(profiles(den, ys, xs, ny, nx))
    both = np.isfinite(wn) & np.isfinite(wd)
    if both.sum() < 100:
        return float("nan"), int(both.sum())
    return float(np.median(wn[both]) / np.median(wd[both])), int(both.sum())


def main():
    out = {"bars": {"B4_withdraw_if_scale_matched_width_le": 1.0050}}

    aligned = load(ALIGNED)
    null = load(ZOOMNULL)
    assert aligned.shape == null.shape, (aligned.shape, null.shape)
    out["shape"] = list(aligned.shape)
    print(f"shape {aligned.shape}", flush=True)

    # ---- independent scale measurement, coarse then fine, with a rail check
    s0, v0, rail0, _ = find_scale(aligned, null, 0.960, 1.040, 33)
    s, v, rail, curve = find_scale(aligned, null, s0 - 0.005, s0 + 0.005, 41)
    out["scale"] = {"coarse": s0, "coarse_ncc": v0, "coarse_railed": rail0,
                    "s_null_to_aligned": s, "ncc": v, "railed": rail}
    print(f"scale null->aligned = {s:.6f} at NCC {v:.4f} "
          f"(coarse {s0:.6f}/{v0:.4f}, railed {rail0}/{rail})", flush=True)

    # ---- self-check on the scale finder: plant a known magnification
    for plant in (1.0200, 0.9800):
        zp = rescale(centre_win(null, SWIN), plant, order=3)
        big = np.zeros_like(null)
        h, w = null.shape
        y0, x0 = (h - SWIN) // 2, (w - SWIN) // 2
        big[y0:y0 + SWIN, x0:x0 + SWIN] = zp
        got, gv, _, _ = find_scale(big, null, plant - 0.010, plant + 0.010, 41)
        out.setdefault("scale_plants", {})[f"{plant:.4f}"] = {
            "recovered": got, "err": got - plant, "ncc": gv}
        print(f"  scale plant {plant:.4f} -> {got:.6f} "
              f"(err {got - plant:+.2e}, NCC {gv:.4f})", flush=True)

    a = centre_win(aligned, WIN)
    z = centre_win(null, WIN)
    del aligned, null

    # Remove the residual whole-window translation between the arms with an
    # integer roll before any metric is taken, so that a pure offset cannot be
    # read as a difference in edge shape.
    zs3 = rescale(z, s, order=3)
    zs0 = rescale(z, s, order=0)
    dy, dx = best_shift(a, zs3)
    zs3 = shift_int(zs3, dy, dx)
    zs0 = shift_int(zs0, dy, dx)
    out["match_shift"] = [dy, dx]
    print(f"match shift dy={dy} dx={dx}", flush=True)

    ys, xs, ny, nx = pick_edges((a + z) / 2.0, N_EDGES)
    out["n_edge_candidates"] = int(ys.size)

    T = {"aligned": tenengrad(a), "null": tenengrad(z),
         "null_scaled_cubic": tenengrad(zs3), "null_scaled_nn": tenengrad(zs0)}
    out["tenengrad"] = T

    # ---- B1 placebo
    wr_placebo, n_pl = width_ratio(a, a, ys, xs, ny, nx)
    out["B1_placebo"] = {"tenengrad": T["aligned"] / T["aligned"],
                         "width": wr_placebo, "n": n_pl,
                         "pass": abs(wr_placebo - 1.0) < 5e-4}

    # ---- B2 identity resample
    z_id = rescale(z, 1.0, order=3)
    wr_id, n_id = width_ratio(z_id, z, ys, xs, ny, nx)
    out["B2_identity_resample"] = {
        "tenengrad": tenengrad(z_id) / T["null"], "width": wr_id, "n": n_id,
        "pass": abs(wr_id - 1.0) < 5e-3}

    # ---- B3 magnification plant: the confound in isolation
    # Orientation matches the reported ratios: Tenengrad aligned/null, where
    # "aligned" is the MORE magnified arm; width null/aligned, where "aligned"
    # is again the more magnified arm (so it is the denominator).
    rmag_ten_cubic = tenengrad(zs3) / T["null"]
    rmag_ten_nn = tenengrad(zs0) / T["null"]
    rmag_w_cubic, n_rc = width_ratio(z, zs3, ys, xs, ny, nx)
    rmag_w_nn, n_rn = width_ratio(z, zs0, ys, xs, ny, nx)
    out["B3_magnification_plant"] = {
        "s": s,
        "tenengrad_cubic": rmag_ten_cubic, "tenengrad_nn": rmag_ten_nn,
        "tenengrad_theory_1_over_s2": 1.0 / (s * s),
        "width_cubic": rmag_w_cubic, "width_nn": rmag_w_nn, "n": [n_rc, n_rn],
        "width_theory_1_over_s": 1.0 / s,
        "pass_signs": bool(rmag_ten_cubic < 1.0 and rmag_w_cubic < 1.0)}

    # ---- measured ratios, raw and scale-matched
    m_ten_raw = T["aligned"] / T["null"]
    m_ten_matched = T["aligned"] / tenengrad(zs3)
    m_w_raw, n_raw = width_ratio(z, a, ys, xs, ny, nx)
    m_w_matched, n_mat = width_ratio(zs3, a, ys, xs, ny, nx)
    m_w_matched_nn, n_mnn = width_ratio(zs0, a, ys, xs, ny, nx)
    out["measured"] = {
        "tenengrad_raw": m_ten_raw, "tenengrad_matched_cubic": m_ten_matched,
        "tenengrad_matched_nn": T["aligned"] / tenengrad(zs0),
        "width_raw_null_over_aligned": m_w_raw, "n_raw": n_raw,
        "width_matched_cubic": m_w_matched, "n_matched": n_mat,
        "width_matched_nn": m_w_matched_nn, "n_matched_nn": n_mnn}

    out["residual_after_dividing_out_magnification"] = {
        "tenengrad": m_ten_raw / rmag_ten_cubic,
        "width": m_w_raw / rmag_w_cubic}

    # ---- B4 verdict on section 10
    out["B4_section10_verdict"] = {
        "scale_matched_width": m_w_matched,
        "withdraw_if_le": 1.0050,
        "survives": bool(m_w_matched > 1.0050)}

    # ---- B5 resampler hazard
    out["B5_resampler_hazard"] = {
        "tenengrad_nn_minus_cubic": rmag_ten_nn - rmag_ten_cubic,
        "contaminated": bool(abs(rmag_ten_nn - rmag_ten_cubic) > 5e-3)}

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    print("\n--- pre-registered bars ---", flush=True)
    print(f"B1 placebo width      {wr_placebo:.6f}   pass={out['B1_placebo']['pass']}")
    print(f"B2 identity resample  {wr_id:.6f}   pass={out['B2_identity_resample']['pass']}")
    print(f"B3 R_mag tenengrad    cubic {rmag_ten_cubic:.4f}  nn {rmag_ten_nn:.4f}"
          f"   theory 1/s^2 {1.0 / (s * s):.4f}")
    print(f"B3 R_mag width        cubic {rmag_w_cubic:.4f}  nn {rmag_w_nn:.4f}"
          f"   theory 1/s {1.0 / s:.4f}   signs pass="
          f"{out['B3_magnification_plant']['pass_signs']}")
    print("\n--- measured ---", flush=True)
    print(f"tenengrad aligned/null      raw {m_ten_raw:.4f}   "
          f"scale-matched {m_ten_matched:.4f}")
    print(f"width null/aligned          raw {m_w_raw:.4f} (n={n_raw})   "
          f"scale-matched {m_w_matched:.4f} (n={n_mat})")
    print(f"residual after /R_mag       tenengrad {m_ten_raw / rmag_ten_cubic:.4f}   "
          f"width {m_w_raw / rmag_w_cubic:.4f}")
    print(f"\nB4 section 10 survives = {out['B4_section10_verdict']['survives']}"
          f"  (scale-matched width {m_w_matched:.4f} vs bar 1.0050)")
    print(f"B5 NN contaminates tenengrad = {out['B5_resampler_hazard']['contaminated']}"
          f"  (nn - cubic = {rmag_ten_nn - rmag_ten_cubic:+.4f})")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
