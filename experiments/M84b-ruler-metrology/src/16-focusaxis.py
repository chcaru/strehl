"""M84b step 16 - the focus axis in microns per frame, and its constancy.

Pre-registration section 6. Inputs are the column-aggregated response cube from
step 12 (299 x 1900 for the angled stack: each entry is a mean over 180 rows,
so it is the spatially aggregated statistic of section 6.1 and NOT a per-pixel
argmax, rule 4), the graduation positions from step 13 and the geometry from
step 15.

Reported:
  * per-graduation best-focus frame n*(k), by the registered half-max centroid
    and by a 3-point parabolic fit;
  * dk/dn by robust fit, hence dZ/dn = P sin(theta) dk/dn microns per frame;
  * the registered five-segment constancy test;
  * the registered permuted-frame-axis placebo, seed 0x4d840001;
  * the photometric disclosure: correlation of the UN-normalised response with
    the frame mean.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
PLACEBO_SEED = 0x4D840001


def peak_frame(curve: np.ndarray) -> tuple[float, float, float]:
    """Registered: centroid of (curve - median) over the contiguous above-half-
    max region around the discrete argmax. Also returns a 3-point parabolic
    peak and the peak prominence in units of the curve's own sd."""
    c = curve - np.median(curve)
    j = int(np.argmax(c))
    if c[j] <= 0:
        return float("nan"), float("nan"), 0.0
    half = 0.5 * c[j]
    lo = hi = j
    while lo > 0 and c[lo - 1] >= half:
        lo -= 1
    while hi < len(c) - 1 and c[hi + 1] >= half:
        hi += 1
    seg = c[lo : hi + 1]
    idx = np.arange(lo, hi + 1, dtype=float)
    cen = float((idx * seg).sum() / seg.sum()) if seg.sum() > 0 else float(j)
    if 0 < j < len(c) - 1:
        y0, y1, y2 = c[j - 1], c[j], c[j + 1]
        d = y0 - 2 * y1 + y2
        par = float(j + 0.5 * (y0 - y2) / d) if d != 0 else float(j)
    else:
        par = float(j)
    return cen, par, float(c[j] / (np.std(c) + 1e-12))


def robust_line(x, y):
    """Huber IRLS straight line. Returns slope, intercept, resid."""
    w = np.ones_like(x)
    m = b = 0.0
    for _ in range(100):
        M = np.column_stack([x, np.ones_like(x)])
        sw = np.sqrt(w)
        sol, *_ = np.linalg.lstsq(M * sw[:, None], y * sw, rcond=None)
        m, b = sol
        r = y - (m * x + b)
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-12
        c = 1.345 * s
        w = np.where(np.abs(r) <= c, 1.0, c / np.maximum(np.abs(r), 1e-12))
    return float(m), float(b), y - (m * x + b)


def main(argv) -> int:
    OUT.mkdir(exist_ok=True)
    colprof = np.load(OUT / "12-colprof-ang.npy").astype(np.float64)  # (N, W)
    fit13 = json.loads((OUT / "13-ang.json").read_text())
    clo = json.loads((OUT / "15-closure.json").read_text())
    meta = json.loads((OUT / "11-meta-ang.json").read_text())

    n_frames, width = colprof.shape
    # Step 12 saved this profile in ROI-relative coordinates; step 15 now
    # publishes its fits in ABSOLUTE quad coordinates (its ROI bug fix), so the
    # ROI origin has to be added before the projective law is applied. Getting
    # this wrong silently corrupts only the DENSE per-column inversion, which is
    # how the step-18 control caught it.
    roi_x0 = float(json.loads((OUT / "12-ang.json").read_text())["config"]["x0"])
    xs = np.array(fit13["tick_x"]) + roi_x0
    kk = np.array(fit13["k"], float)
    n_kept = clo["fits_absolute"]["ang"]["n_kept"]
    xs, kk = xs[:n_kept], kk[:n_kept]  # step 15 rejected only the trailing one
    A = clo["fits_absolute"]["ang"]["A"]
    B = clo["fits_absolute"]["ang"]["B"]
    C = clo["fits_absolute"]["ang"]["C"]
    assert A > roi_x0, "step-15 ang fit is not in absolute quad coordinates"
    dZ_per_grad_um = clo["solution"]["dZ_per_grad_ang_um"]

    # ---- per-graduation through-focus curves, support = +/- 1 local pitch ----
    local_pitch = (B - C * A) / (1 + C * kk) ** 2
    rows = []
    for i, (x, k, lp) in enumerate(zip(xs, kk, local_pitch)):
        lo = int(max(round(x - roi_x0 - lp), 0))
        hi = int(min(round(x - roi_x0 + lp) + 1, width))
        curve = colprof[:, lo:hi].mean(axis=1)
        cen, par, prom = peak_frame(curve)
        rows.append({"k": float(k), "x": float(x), "support": [lo, hi],
                     "n_centroid": cen, "n_parabolic": par, "prominence": prom})
    kv = np.array([r["k"] for r in rows])
    nv = np.array([r["n_centroid"] for r in rows])
    npar = np.array([r["n_parabolic"] for r in rows])
    good = np.isfinite(nv)

    slope, icept, resid = robust_line(kv[good], nv[good])  # frames per graduation
    dk_dn = 1.0 / slope
    um_per_frame = dZ_per_grad_um * dk_dn
    r_real = float(np.corrcoef(kv[good], nv[good])[0, 1])

    # monotonicity bar
    mono = float(np.mean(np.diff(nv[good]) > 0))

    # ---- dense per-column version, for the drift shape ----
    x_lo, x_hi = int(round(xs[0])), int(round(xs[-1]))
    cols = np.arange(x_lo, x_hi + 1)  # absolute quad x
    kcol = np.array([(cx - A) / (B - C * cx) for cx in cols])  # invert x(k)
    ncol = np.array(
        [peak_frame(colprof[:, int(c - roi_x0)])[0] for c in cols]
    )
    okc = np.isfinite(ncol)

    # ---- registered five-segment constancy test ----
    segs = np.array_split(np.flatnonzero(okc), 5)
    seg_slopes, seg_um = [], []
    for s in segs:
        if len(s) < 8:
            continue
        sl, _, _ = robust_line(kcol[s], ncol[s])
        seg_slopes.append(sl)
        seg_um.append(dZ_per_grad_um / sl)
    seg_um = np.array(seg_um)
    const_ratio = float(seg_um.max() / seg_um.min()) if len(seg_um) else float("nan")

    # ---- registered placebo: permute the frame axis ----
    # The pre-registration bar was |r| < 0.2 for ONE permutation. With 13
    # graduations the null sd of r is about 1/sqrt(10) = 0.32, so a single draw
    # inside +/-0.2 happens only about half the time even under a perfect null:
    # the registered bar was mis-scaled. The single registered draw is reported
    # verbatim, and a 1000-permutation null distribution is reported alongside
    # it so the comparison is calibrated rather than anecdotal.
    rng = np.random.default_rng(PLACEBO_SEED)
    perm = rng.permutation(n_frames)
    prof_p = colprof[perm, :]
    nv_p = []
    for r in rows:
        lo, hi = r["support"]
        nv_p.append(peak_frame(prof_p[:, lo:hi].mean(axis=1))[0])
    nv_p = np.array(nv_p)
    gp = np.isfinite(nv_p)
    r_placebo = float(np.corrcoef(kv[gp], nv_p[gp])[0, 1])

    null_rs = []
    for _ in range(1000):
        pp = rng.permutation(n_frames)
        pr = colprof[pp, :]
        vals = []
        for r in rows:
            lo, hi = r["support"]
            vals.append(peak_frame(pr[:, lo:hi].mean(axis=1))[0])
        vals = np.array(vals)
        g2 = np.isfinite(vals)
        if g2.sum() >= 5 and np.std(vals[g2]) > 0:
            null_rs.append(float(np.corrcoef(kv[g2], vals[g2])[0, 1]))
    null_rs = np.array(null_rs)

    # ---- photometric disclosure ----
    levels = np.array(meta["levels"], float)
    resp_mean = colprof[:, int(x_lo - roi_x0) : int(x_hi - roi_x0) + 1].mean(axis=1)
    r_level = float(np.corrcoef(levels, resp_mean)[0, 1])

    out = {
        "n_frames": n_frames,
        "dZ_per_grad_um": dZ_per_grad_um,
        "per_graduation": rows,
        "frames_per_graduation": slope,
        "graduations_per_frame": dk_dn,
        "um_per_frame": um_per_frame,
        "fit_resid_frames_rms": float(np.sqrt(np.mean(resid**2))),
        "pearson_real": r_real,
        "pearson_placebo": r_placebo,
        "placebo_null_n": int(len(null_rs)),
        "placebo_null_mean": float(np.mean(null_rs)),
        "placebo_null_sd": float(np.std(null_rs)),
        "placebo_null_abs_p95": float(np.percentile(np.abs(null_rs), 95)),
        "placebo_null_max_abs": float(np.max(np.abs(null_rs))),
        "real_exceeds_all_nulls": bool(abs(r_real) > np.max(np.abs(null_rs))),
        "placebo_seed": hex(PLACEBO_SEED),
        "monotone_fraction": mono,
        "centroid_minus_parabolic_frames": float(
            np.nanmedian(np.abs(nv - npar))
        ),
        "nstar_span_frames": [float(np.nanmin(nv)), float(np.nanmax(nv))],
        "segment_um_per_frame": seg_um.tolist(),
        "constancy_ratio_max_over_min": const_ratio,
        "constancy_verdict": (
            "CONSTANT" if const_ratio < 1.25 else "DRIFTS"
        ),
        "dense_k": kcol[okc].tolist(),
        "dense_nstar": ncol[okc].tolist(),
        "level_response_pearson": r_level,
        "frame_level_first_last": [float(levels[0]), float(levels[-1])],
        "um_per_frame_uncertainty": {
            "note": "combines the bootstrap sd of dZ_per_grad with the "
                    "robust-line slope sd from a graduation bootstrap",
        },
    }

    # bootstrap um_per_frame over graduations and over dZ_per_grad
    rng2 = np.random.default_rng(0x4D84B016)
    dz_sd = clo["bootstrap"]["dZ_per_grad_ang_um"]["sd"]
    dz_mu = clo["bootstrap"]["dZ_per_grad_ang_um"]["mean"]
    acc = []
    ivals = np.flatnonzero(good)
    for _ in range(2000):
        j = rng2.choice(ivals, len(ivals), replace=True)
        if len(np.unique(kv[j])) < 4:
            continue
        sl, _, _ = robust_line(kv[j], nv[j])
        acc.append(rng2.normal(dz_mu, dz_sd) / sl)
    out["um_per_frame_uncertainty"].update(
        {"mean": float(np.mean(acc)), "sd": float(np.std(acc)),
         "p2.5": float(np.percentile(acc, 2.5)),
         "p97.5": float(np.percentile(acc, 97.5))}
    )

    (OUT / "16-focusaxis.json").write_text(json.dumps(out, indent=1))

    print(f"graduations {len(kv)}, n* span {out['nstar_span_frames']}")
    print(f"  n*(k) slope {slope:.4f} frames/graduation "
          f"(resid rms {out['fit_resid_frames_rms']:.3f} frames)")
    print(f"  um per frame = {um_per_frame:.4f}  "
          f"boot {out['um_per_frame_uncertainty']['mean']:.4f} "
          f"+/- {out['um_per_frame_uncertainty']['sd']:.4f}")
    print(f"  pearson real {r_real:.4f}   placebo {r_placebo:.4f}  "
          f"(bars: real > 0.9, |placebo| < 0.2)")
    print(f"  placebo null over {len(null_rs)} perms: mean {np.mean(null_rs):+.4f} "
          f"sd {np.std(null_rs):.4f}  p95|r| {np.percentile(np.abs(null_rs), 95):.4f}  "
          f"max|r| {np.max(np.abs(null_rs)):.4f}  "
          f"real beats every null: {abs(r_real) > np.max(np.abs(null_rs))}")
    print(f"  monotone fraction {mono:.3f} (bar >= 0.80)")
    print(f"  centroid vs parabolic median |diff| "
          f"{out['centroid_minus_parabolic_frames']:.3f} frames")
    print(f"  segment um/frame {np.round(seg_um, 4).tolist()}")
    print(f"  constancy ratio {const_ratio:.4f} -> {out['constancy_verdict']} "
          f"(bar < 1.25)")
    print(f"  photometric: frame mean {levels[0]:.0f} -> {levels[-1]:.0f}, "
          f"corr(level, normalised response) = {r_level:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

