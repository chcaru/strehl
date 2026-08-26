"""Diagnose the leaf-2-cpl claim after `adjudicate.py` FALSIFIED my own mechanism.

WHAT HAPPENED. `adjudicate.py` predicted that the claim's ratio would reconcile
with the tool's own n_eff once multiplied by the admission ratio. It did not:
the correction moved the number 839% away from the prediction instead of onto
it, and the correlation between admission ratio and sigma ratio came out
POSITIVE (+0.574) when the mechanism required it to be negative. The mechanism
as I stated it to the orchestrator is wrong and this file finds out what is
actually true.

FOUR THINGS WENT WRONG AT ONCE, and they have to be separated before anything
can be concluded:

  (a) I used the WRONG PREDICTOR. The sigma of a patch whose pixels have
      differing n_eff is sqrt(mean(1/n_eff)), an RMS over the patch, NOT
      1/sqrt(mean n_eff). With 62.57% of this plane at n_eff = 1 those two
      differ enormously. `adjudicate.py` used the second. Fixed here.

  (b) THE CLAIM DOES NOT REPRODUCE ON THE PINNED BINARY. Same argv, same
      subject: the flat-patch argmin lands at y=1344 x=368 instead of y=912
      x=384, and the pinned binary's own banner reports `mean n_eff 5.229`
      where the README quotes 15.077. That is a build difference, and this
      file measures its size instead of assuming it.

  (c) The claim's statistic is a 3x3 Laplacian on a DEMOSAICED render whose own
      banner says "Interpolated -- do not measure resolution on it". Demosaic
      correlates neighbouring pixels, so the Laplacian residual is not a clean
      per-pixel noise estimate. Both arms are demosaiced, so it mostly cancels,
      but it is stated rather than ignored.

  (d) The admission test's drift search SATURATED at its +/-10 px bound on this
      subject -- unsurprising now that the banner is read: leaf-2-cpl's
      alignment held-out error is 13.227 px, above the tool's own T_usable of
      4.0. The search is widened here.

THE INSTRUMENT THAT REPLACES THE BROKEN MECHANISM. A simulated selection arm,
built from the single frames alone with NO MERGE INVOLVED: draw each output
pixel from a randomly chosen frame (a "mosaic"), and compare it against the
plain mean of the same frames. On a stationary patch that ratio must equal
1/sqrt(N) exactly, because the only thing varying between frames is noise. On a
non-stationary patch the mosaic additionally carries the frame-to-frame content
difference and the ratio falls BELOW 1/sqrt(N). The size of that shortfall is
the inflation, measured directly, on an arm-vs-arm ratio -- which is precisely
the orchestrator's question 3.
"""

import json
import pathlib
import sys

import numpy as np
import tifffile

import admission
import pyrnoise as pn
from claim_roi import flat_patch, hp_sigma, F, ORCH

CLAIM = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\claim")
RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")
SUBJECT = "leaf-2-cpl"
RNG = np.random.default_rng(20260826)

CLAIM_PATCH = (384, 912)     # x, y  -- recovered from the 925d03d renders
PINNED_PATCH = None          # filled in below, from the pinned renders


def fov_scale(err_path):
    for line in pathlib.Path(err_path).read_text(encoding="utf8", errors="replace").splitlines():
        if "field of view scaled to" in line:
            return 1.0 / float(line.split("field of view scaled to")[1].split()[0])
    return 1.0


def arm_to_plane(roi_full, full_shape, plane_shape, s):
    x, y, w, h = roi_full
    ky = plane_shape[0] / full_shape[0]
    kx = plane_shape[1] / full_shape[1]
    xb, yb, wb, hb = x * kx, y * ky, w * kx, h * ky
    cy, cx = (plane_shape[0] - 1) / 2.0, (plane_shape[1] - 1) / 2.0
    mx = cx + (xb + wb / 2.0 - cx) / s
    my = cy + (yb + hb / 2.0 - cy) / s
    return (int(round(mx - wb / 2.0)), int(round(my - hb / 2.0)),
            int(round(wb)), int(round(hb)))


def plane_to_arm(roi_plane, plane_shape, full_shape, s):
    x, y, w, h = roi_plane
    cy, cx = (plane_shape[0] - 1) / 2.0, (plane_shape[1] - 1) / 2.0
    mx = cx + (x + w / 2.0 - cx) * s
    my = cy + (y + h / 2.0 - cy) * s
    ky = full_shape[0] / plane_shape[0]
    kx = full_shape[1] / plane_shape[1]
    return (int(round((mx - w / 2.0) * kx)), int(round((my - h / 2.0) * ky)),
            int(round(w * kx)), int(round(h * ky)))


def neff_predict(nm, roi_arm):
    """The tool's OWN prediction of sigma_gate2 / sigma_gate0 inside a patch.

    Variance adds, so a patch whose pixels average different numbers of frames
    has sigma ratio sqrt(mean(1/n_eff)) -- an RMS -- and an EQUIVALENT FRAME
    COUNT of 1/mean(1/n_eff), the harmonic mean. Using 1/sqrt(mean n_eff)
    instead, as `adjudicate.py` did, badly overstates the reduction whenever the
    patch is a mixture: 62.57% of this plane sits at n_eff = 1, contributing
    the full single-frame variance no matter how large the rest of the map is.
    """
    x, y, w, h = roi_arm
    t = nm[y // 2:(y + h) // 2, x // 2:(x + w) // 2]
    if t.size == 0:
        return np.nan, np.nan, np.nan, 0.0
    inv = 1.0 / np.clip(t, 1.0, None)
    return (float(np.sqrt(inv.mean())), float(1.0 / inv.mean()),
            float(t.mean()), float((t <= 1.0).mean() * 100.0))


def drift_shifts(imgs, frames, roi, search=24):
    """Integer NCC shift per frame. Widened from +/-10 to +/-24 because the
    +/-10 search SATURATED on this subject and the run's own banner explains
    why: `held-out err : 13.227 px`, above the tool's T_usable of 4.0 px."""
    x, y, w, h = roi
    ref = pn.crop(imgs[frames[len(frames) // 2]], roi).astype(np.float64)
    ref = (ref - ref.mean()) / (ref.std() + 1e-12)
    out = {}
    for f in frames:
        best, bxy = -2.0, (0, 0)
        for dy in range(-search, search + 1):
            for dx in range(-search, search + 1):
                t = imgs[f][y + dy:y + dy + h, x + dx:x + dx + w].astype(np.float64)
                t = (t - t.mean()) / (t.std() + 1e-12)
                c = float((ref * t).mean())
                if c > best:
                    best, bxy = c, (dx, dy)
        out[f] = bxy
    return out


def mosaic_vs_mean(imgs, frames, roi, shifts=None, block=1, trials=5):
    """THE REPLACEMENT INSTRUMENT. Simulated selection against a plain mean,
    built from single frames only. No merge, no build, no n_eff.

    `block` is the spatial coherence of the winner field. The real `--gate 0`
    winner field is spatially coherent (neighbouring pixels usually elect the
    same frame), so block=1 (independent per pixel) is the WORST CASE for the
    content-mosaic effect and block=8 a milder one. Both are reported so the
    real arm is bracketed rather than guessed at.

    Returns (ratio, sigma_mosaic, sigma_mean, 1/sqrt(N)).
    """
    pad = pn.BOX
    x, y, w, h = roi
    cut = []
    for f in frames:
        dx, dy = shifts[f] if shifts else (0, 0)
        cut.append(imgs[f][y + dy - pad:y + dy + h + pad,
                           x + dx - pad:x + dx + w + pad].astype(np.float64))
    a = np.stack(cut)
    n = len(frames)
    mean_img = a.mean(axis=0)
    s_mean = pn.hp_sd(mean_img)
    rs = []
    for _ in range(trials):
        if block == 1:
            idx = RNG.integers(0, n, size=a.shape[1:])
        else:
            small = RNG.integers(0, n, size=(a.shape[1] // block + 1,
                                             a.shape[2] // block + 1))
            idx = np.kron(small, np.ones((block, block), dtype=int))[:a.shape[1], :a.shape[2]]
        mos = np.take_along_axis(a, idx[None], axis=0)[0]
        rs.append(s_mean / pn.hp_sd(mos))
    return float(np.mean(rs)), float(np.mean([pn.hp_sd(
        np.take_along_axis(a, RNG.integers(0, n, size=a.shape[1:])[None], axis=0)[0])])), \
        s_mean, 1.0 / np.sqrt(n)


def main():
    print("=" * 78)
    print("DIAGNOSIS -- WHY THE FIRST MECHANISM FAILED, AND WHAT IS ACTUALLY TRUE")
    print("=" * 78)

    old_a = tifffile.imread(ORCH / "leaf-2-cpl-selection-gate0.tif").astype(np.float32) / 65535.0
    old_b = tifffile.imread(ORCH / "leaf-2-cpl-estimation-gate2.tif").astype(np.float32) / 65535.0
    new_a = tifffile.imread(CLAIM / "gate0.tif").astype(np.float32) / 65535.0
    new_b = tifffile.imread(CLAIM / "gate2.tif").astype(np.float32) / 65535.0
    ny, nx = flat_patch(0.5 * (new_a + new_b))
    oy, ox = flat_patch(0.5 * (old_a + old_b))
    print(f"\nA. THE FLAT-PATCH ARGMIN MOVES BETWEEN BUILDS")
    print(f"   925d03d renders (the claim's own) : y={oy} x={ox}")
    print(f"   b9b6921e pinned shipping binary   : y={ny} x={nx}   (same argv)")

    print(f"\nB. THE CLAIM'S STATISTIC, BOTH PATCHES x BOTH BUILDS")
    print(f"   {'build':<10} {'patch':<16} {'gate0':>10} {'gate2':>10} {'ratio':>9} {'equiv N':>9}")
    grid = {}
    for bl, (A, B) in (("925d03d", (old_a, old_b)), ("b9b6921e", (new_a, new_b))):
        for pl, (py, px) in (("claim (912,384)", (oy, ox)), (f"pinned ({ny},{nx})", (ny, nx))):
            sa, sb = hp_sigma(A, py, px), hp_sigma(B, py, px)
            grid[(bl, pl)] = (sa, sb, sb / sa)
            print(f"   {bl:<10} {pl:<16} {sa:10.6f} {sb:10.6f} {sb / sa:8.4f}x {(sa / sb) ** 2:9.2f}")
    print(f"   README quotes                       0.006381   0.000987   0.1546x     41.82")

    print(f"\nC. THE TOOL'S OWN n_eff MAP -- AND THE RIGHT WAY TO READ IT")
    nm = tifffile.imread(CLAIM / "neff.tif")
    print(f"   dtype {nm.dtype}, shape {nm.shape}, range {nm.min()}..{nm.max()}")
    nmf = nm.astype(np.float64)
    print(f"   NULL: map mean {nmf.mean():.3f} vs the run's own banner 'mean n_eff 5.229'"
          f"   {'PASS' if abs(nmf.mean() - 5.229) < 0.02 else 'FAIL'}")
    print(f"   NULL: n_eff==1 share {100.0 * (nmf <= 1).mean():.2f}% vs banner 'n_eff=1 % 62.57'"
          f"   {'PASS' if abs(100.0 * (nmf <= 1).mean() - 62.57) < 0.1 else 'FAIL'}")
    print(f"   README quotes 'mean n_eff 15.077' at 925d03d -- the pinned binary reports"
          f" {nmf.mean():.3f},")
    print(f"   a {15.077 / nmf.mean():.2f}x difference between builds on the same argv and subject.")
    for pl, (py, px) in (("claim", (oy, ox)), ("pinned", (ny, nx))):
        rms, eqn, mn, one = neff_predict(nmf, (px, py, F, F))
        print(f"   at the {pl:<7} patch: mean n_eff {mn:7.2f}   n_eff=1 {one:5.1f}%"
              f"   -> predicted ratio sqrt(mean 1/n) = {rms:.4f}x, equivalent N = {eqn:.2f}")
        print(f"     (the naive 1/sqrt(mean n) would say {1.0 / np.sqrt(mn):.4f}x / {mn:.2f} frames"
              f" -- that is the error adjudicate.py made)")

    # ---- single frames, drift-compensated at BOTH patches --------------------
    d = RENDERS / SUBJECT
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    imgs = {f: pn.green(d / f"{f}.tif") for f in frames}
    plane_shape = imgs[frames[0]].shape
    s = fov_scale(CLAIM / "gate2.err")
    print(f"\nD. ADMISSION AND THE MOSAIC SIMULATION, AT THE CLAIM'S OWN PATCH")
    print(f"   {len(frames)} single frames of 182; alignment magnification {s:.6f};")
    print(f"   the run's own banner reports held-out alignment error 13.227 px "
          f"(T_usable 4.0).")
    out_rows = {}
    for pl, (py, px) in (("claim", (oy, ox)), ("pinned", (ny, nx))):
        roi = arm_to_plane((px, py, F, F), new_a.shape[:2], plane_shape, s)
        r0, t0, sp0, _ = admission.admission(imgs, frames, roi)
        sh = drift_shifts(imgs, frames, roi)
        dxs = [v[0] for v in sh.values()]
        dys = [v[1] for v in sh.values()]
        st = np.stack([imgs[f][roi[1] + sh[f][1]:roi[1] + sh[f][1] + roi[3],
                               roi[0] + sh[f][0]:roi[0] + sh[f][0] + roi[2]] for f in frames])
        t1 = float(st.std(axis=0, ddof=1).mean())
        sp1 = float(np.mean([pn.hp_sd(imgs[f][roi[1] + sh[f][1] - pn.BOX:roi[1] + sh[f][1] + roi[3] + pn.BOX,
                                              roi[0] + sh[f][0] - pn.BOX:roi[0] + sh[f][0] + roi[2] + pn.BOX])
                             for f in frames]))
        print(f"\n   -- {pl} patch, plane ROI {roi} --")
        print(f"      admission as measured        {r0:6.3f}   (temporal {t0:7.2f} / spatial {sp0:6.2f})")
        print(f"      admission drift-compensated  {t1 / sp1:6.3f}   (temporal {t1:7.2f} / spatial {sp1:6.2f})"
              f"   shifts dx[{min(dxs)},{max(dxs)}] dy[{min(dys)},{max(dys)}] of +/-24")
        for blk in (1, 8):
            rr, sm, sme, ideal = mosaic_vs_mean(imgs, frames, roi, sh, block=blk)
            print(f"      mosaic(block {blk})/mean       {rr:6.4f}x   against 1/sqrt({len(frames)})"
                  f" = {ideal:.4f}x  -> inflation {ideal / rr:.2f}x")
        out_rows[pl] = {"roi": roi, "adm": r0, "adm_drift": t1 / sp1}

    # ---- the correlation study that decides whether admission is diagnostic --
    print(f"\nE. IS ADMISSION DIAGNOSTIC? measured vs the tool's own prediction, over the plane")
    w = h = 100
    H, W = plane_shape
    rows = []
    for yy in range(160, H - h - 160, 128):
        for xx in range(160, W - w - 160, 128):
            roi = (xx, yy, w, h)
            rr = admission.admission(imgs, frames, roi)[0]
            fr = plane_to_arm(roi, plane_shape, new_a.shape[:2], s)
            if not (0 <= fr[0] and fr[0] + fr[2] <= new_a.shape[1]
                    and 0 <= fr[1] and fr[1] + fr[3] <= new_a.shape[0]):
                continue
            sa = hp_sigma(new_a, fr[1], fr[0], fr[2])
            sb = hp_sigma(new_b, fr[1], fr[0], fr[2])
            pred, eqn, mn, one = neff_predict(nmf, fr)
            if not np.isfinite(pred) or sa <= 0:
                continue
            rows.append((rr, sb / sa, pred, mn, one, xx, yy))
    A = np.array([r[0] for r in rows])
    M = np.array([r[1] for r in rows])
    P = np.array([r[2] for r in rows])
    dev = np.log(M / P)
    print(f"   {len(rows)} windows. 'dev' = log(measured / tool-predicted); 0 means the")
    print(f"   Laplacian statistic is reading exactly the noise the merge says it removed.")
    print(f"     corr(admission, measured ratio)      {np.corrcoef(A, M)[0, 1]:+.3f}")
    print(f"     corr(admission, dev)                 {np.corrcoef(A, dev)[0, 1]:+.3f}")
    print(f"     corr(tool prediction, measured)      {np.corrcoef(P, M)[0, 1]:+.3f}")
    for lo, hi in ((0.0, 1.3), (1.3, 2.0), (2.0, 3.0), (3.0, 99.0)):
        k = (A >= lo) & (A < hi)
        if k.sum() == 0:
            continue
        print(f"     admission [{lo:4.1f},{hi:4.1f})  n={k.sum():4d}   measured median"
              f" {np.median(M[k]):.4f}x   tool-predicted median {np.median(P[k]):.4f}x"
              f"   dev median {np.median(dev[k]):+.3f}")

    json.dump({"old_patch": [oy, ox], "new_patch": [ny, nx],
               "grid": {f"{k[0]}|{k[1]}": v for k, v in grid.items()},
               "neff_mean": float(nmf.mean()),
               "neff_one_pct": float(100.0 * (nmf <= 1).mean()),
               "rows": rows, "patches": out_rows},
              open(CLAIM / "_diagnosis.json", "w"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())
