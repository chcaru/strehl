"""Adjudicate the README's leaf-2-cpl flat-ROI noise claim against the admission test.

THE CLAIM. "In a 200x200 flat patch chosen on the mean of both arms, so neither
arm selected the view, noise falls 0.006381 -> 0.000987, a ratio of 0.1546x --
equivalent to averaging 41.8 frames." Two ESTIMATOR arms, `--gate 0` (pure
selection, n_eff = 1 everywhere) against `--gate 2`, both at a fixed
`--exposure=3.19`, measured as the SD of a 3x3 Laplacian residual on the
full-resolution sRGB render.

THE SUSPICION. BUILD-PYRNOISE's admission test rejected every flat window it
found on this subject. If the claim's patch is also non-stationary across the
bracket, then `--gate 0` -- which takes each output pixel from ONE frame, and
in a flat patch from an essentially arbitrary frame -- renders a MOSAIC of
different frames' content, and that mosaic's content variance is scored as
noise. `--gate 2` averages it away along with the noise. The ratio would then
overstate the noise reduction.

THE ARITHMETIC THAT MAKES IT FALSIFIABLE. Write r for the admission ratio,
temporal/spatial, at the patch. Under the mosaic hypothesis

    sigma_gate0(observed) = r * sigma_gate0(noise only)

because temporal^2 = noise^2 + content^2 is exactly the variance a per-pixel
random draw from the bracket carries. So the noise-only ratio is

    ratio_corrected = ratio_measured * r

and it should agree with the independent, tool-reported 1/sqrt(n_eff) inside
the same patch. Three numbers -- the admission ratio, the measured sigma ratio,
and the tool's own n_eff map -- that were produced by three separate mechanisms
and must reconcile. If they do not, the hypothesis is wrong and this file says so.

DIRECTION OF FAILURE. Every step here can exonerate the claim: the patch can
pass admission, the corrected ratio can fail to reconcile with n_eff, or the
subject can turn out to have admissible patches that give the same answer. Those
outcomes are reported, not routed around.
"""

import json
import pathlib
import sys

import numpy as np
import tifffile

import admission
import pyrnoise as pn
from claim_roi import flat_patch, hp_sigma, F

CLAIM = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\claim")
RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")
SUBJECT = "leaf-2-cpl"
RNG = np.random.default_rng(20260826)


# ---------------------------------------------------------------- geometry --
def fov_scale(err_path):
    for line in pathlib.Path(err_path).read_text(encoding="utf8", errors="replace").splitlines():
        if "field of view scaled to" in line:
            return 1.0 / float(line.split("field of view scaled to")[1].split()[0])
    return 1.0


def banner(err_path, *keys):
    out = []
    for line in pathlib.Path(err_path).read_text(encoding="utf8", errors="replace").splitlines():
        if any(k in line for k in keys):
            out.append(line.rstrip())
    return out


def arm_to_plane(roi_full, full_shape, plane_shape, s):
    """Full-resolution ALIGNED arm coordinates -> binned RAW-PLANE coordinates.

    Two independent transforms, applied in this order and each stated so it can
    be checked:
      1. resolution. The sRGB render is full sensor; every other measurement in
         this investigation is the binned plane. The two grids are not an exact
         factor of two (7040 vs 2*3516 = 7032), so the ratio is applied per
         axis rather than assuming /2, and the residual is reported.
      2. alignment. The arms are magnified by `s` about the image centre so
         every frame covers every output pixel. Single unstacked frames are NOT,
         so the patch must be mapped back through 1/s to find the same scene.
    """
    x, y, w, h = roi_full
    ky = plane_shape[0] / full_shape[0]
    kx = plane_shape[1] / full_shape[1]
    xb, yb, wb, hb = x * kx, y * ky, w * kx, h * ky
    cy, cx = (plane_shape[0] - 1) / 2.0, (plane_shape[1] - 1) / 2.0
    mx = cx + (xb + wb / 2.0 - cx) / s
    my = cy + (yb + hb / 2.0 - cy) / s
    return (int(round(mx - wb / 2.0)), int(round(my - hb / 2.0)),
            int(round(wb)), int(round(hb))), (kx, ky)


def plane_to_arm(roi_plane, plane_shape, full_shape, s):
    """The inverse, for evaluating the claim's statistic at a patch chosen on
    the plane."""
    x, y, w, h = roi_plane
    cy, cx = (plane_shape[0] - 1) / 2.0, (plane_shape[1] - 1) / 2.0
    mx = cx + (x + w / 2.0 - cx) * s
    my = cy + (y + h / 2.0 - cy) * s
    ky = full_shape[0] / plane_shape[0]
    kx = full_shape[1] / plane_shape[1]
    return (int(round((mx - w / 2.0) * kx)), int(round((my - h / 2.0) * ky)),
            int(round(w * kx)), int(round(h * ky)))


# ------------------------------------------------------- drift compensation --
def drift_shifts(imgs, frames, roi, search=10):
    """Integer shift per frame that best matches the reference, by NCC.

    THE CONFOUND THIS REMOVES. The admission test reads single unstacked frames,
    which are NOT registered; the arms it is being used to judge ARE. Camera
    drift would therefore inflate the temporal estimate for a reason the arms
    never see, and a rejection caused by drift alone would be an artifact of the
    instrument rather than a property of the subject. Re-cutting each frame at
    its own best-matching offset removes translation. What survives is content.
    """
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


def admission_shifted(imgs, frames, roi, shifts):
    x, y, w, h = roi
    stack, sp = [], []
    for f in frames:
        dx, dy = shifts[f]
        stack.append(imgs[f][y + dy:y + dy + h, x + dx:x + dx + w].astype(np.float64))
        sp.append(pn.hp_sd(imgs[f][y + dy - pn.BOX:y + dy + h + pn.BOX,
                                   x + dx - pn.BOX:x + dx + w + pn.BOX]))
    temporal = float(np.stack(stack).std(axis=0, ddof=1).mean())
    spatial = float(np.mean(sp))
    return temporal / spatial, temporal, spatial


# ------------------------------------------- independent corroboration -------
def lag1_autocorr(imgs, frames, roi):
    """Lag-1 correlation of each pixel's value along the FRAME ORDER.

    An instrument that shares nothing with the admission test. Shot noise is
    independent between exposures, so after removing each pixel's own temporal
    mean (which also removes fixed-pattern noise) a stationary region reads ~0.
    A region whose content sweeps through focus reads strongly positive, because
    consecutive frames resemble each other and distant ones do not.

    Fails in the direction that matters: it cannot manufacture correlation from
    noise, so a high reading cannot be an artifact of a noisy subject.
    """
    a = np.stack([pn.crop(imgs[f], roi) for f in frames]).astype(np.float64)
    a -= a.mean(axis=0, keepdims=True)
    num = (a[:-1] * a[1:]).sum(axis=0)
    den = np.sqrt((a[:-1] ** 2).sum(axis=0) * (a[1:] ** 2).sum(axis=0)) + 1e-12
    return float((num / den).mean())


def synthetic_stationary(imgs, frames, roi, n=None):
    """A stationary bracket built FROM THIS SUBJECT'S OWN PIXELS.

    One real frame, replicated, plus independent noise matched to the measured
    single-frame level. Same scene, same levels, same sensor character, same
    patch -- everything the real bracket has EXCEPT frame-to-frame content
    change. If the admission test rejects this too, the rejection is a property
    of the test or of the subject's noise, not of non-stationarity, and the
    verdict on leaf-2-cpl is void.
    """
    n = n or len(frames)
    base = pn.crop(imgs[frames[len(frames) // 2]], roi).astype(np.float64)
    sd = pn.hp_sd(pn.crop(imgs[frames[len(frames) // 2]], roi, pn.BOX))
    pad = pn.BOX
    big = imgs[frames[len(frames) // 2]].astype(np.float64)
    x, y, w, h = roi
    core = big[y - pad:y + h + pad, x - pad:x + w + pad]
    fake = {f"s{i:03d}": core + RNG.normal(0.0, sd, core.shape) for i in range(n)}
    return fake, list(fake), (pad, pad, w, h), sd


# ------------------------------------------------------------------- main ---
def main():
    print("=" * 78)
    print("ADJUDICATING THE README'S leaf-2-cpl FLAT-ROI NOISE CLAIM")
    print("=" * 78)

    # --- 1. reproduce the claim on the PINNED binary ------------------------
    for tag in ("gate0", "gate2", "gate2_neff"):
        for ln in banner(CLAIM / f"{tag}.err", "merge backend", "alignment ", "field of view scaled"):
            print(f"  {tag:<11} {ln.strip()}")
    a = tifffile.imread(CLAIM / "gate0.tif").astype(np.float32) / 65535.0
    b = tifffile.imread(CLAIM / "gate2.tif").astype(np.float32) / 65535.0
    fy, fx = flat_patch(0.5 * (a + b))
    sa, sb = hp_sigma(a, fy, fx), hp_sigma(b, fy, fx)
    ratio = sb / sa
    print(f"\n1. THE CLAIM, RE-RUN ON THE PINNED BINARY  (shape {a.shape})")
    print(f"   patch chosen on the mean of both arms : y={fy} x={fx} ({F}x{F})")
    print(f"   gate0 sigma {sa:.6f}   gate2 sigma {sb:.6f}   ratio {ratio:.4f}x"
          f"   equiv frames {(sa / sb) ** 2:.2f}")
    print(f"   README (at 925d03d)                   : 0.006381 / 0.000987 / 0.1546x / 41.8")

    # --- 2. map the patch onto the raw plane -------------------------------
    d = RENDERS / SUBJECT
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    imgs = {f: pn.green(d / f"{f}.tif") for f in frames}
    plane_shape = imgs[frames[0]].shape
    s = fov_scale(CLAIM / "gate2.err")
    roi, (kx, ky) = arm_to_plane((fx, fy, F, F), a.shape[:2], plane_shape, s)
    print(f"\n2. THE SAME PATCH ON THE RAW PLANE")
    print(f"   full-res arm {a.shape[1]}x{a.shape[0]} -> plane {plane_shape[1]}x{plane_shape[0]}"
          f"   (kx {kx:.6f}, ky {ky:.6f})")
    print(f"   alignment magnification from the run's own banner: {s:.6f}")
    print(f"   claim's patch on the plane            : {roi}")
    print(f"   single frames available               : {len(frames)} of 182")

    # --- 3. admission at the CLAIM'S OWN patch ------------------------------
    print(f"\n3. ADMISSION AT THE CLAIM'S OWN PATCH  (bar {admission.BAR})")
    r0, t0, sp0, ok0 = admission.admission(imgs, frames, roi)
    print(f"   as measured        temporal {t0:8.3f} / spatial {sp0:8.3f} = {r0:6.3f}"
          f"   {'PASS' if ok0 else 'FAIL'}")
    sh = drift_shifts(imgs, frames, roi)
    rng_dx = [v[0] for v in sh.values()]
    rng_dy = [v[1] for v in sh.values()]
    r1, t1, sp1 = admission_shifted(imgs, frames, roi, sh)
    print(f"   drift-compensated  temporal {t1:8.3f} / spatial {sp1:8.3f} = {r1:6.3f}"
          f"   {'PASS' if r1 <= admission.BAR else 'FAIL'}")
    print(f"     per-frame shift removed: dx [{min(rng_dx)}, {max(rng_dx)}] "
          f"dy [{min(rng_dy)}, {max(rng_dy)}] px")

    # sensitivity to the 4 px grid ambiguity between the two render sizes
    jitter = [admission.admission(imgs, frames, (roi[0] + dx, roi[1] + dy, roi[2], roi[3]))[0]
              for dx in (-4, 0, 4) for dy in (-4, 0, 4)]
    print(f"   patch offset +/-4 px : {min(jitter):.3f} .. {max(jitter):.3f}"
          f"   (covers the {a.shape[1]} vs {2 * plane_shape[1]} grid ambiguity)")

    # --- 4. is the TEST wrong? --------------------------------------------
    print(f"\n4. IS THE ADMISSION TEST THE THING THAT IS WRONG?")
    fake, ffr, froi, fsd = synthetic_stationary(imgs, frames, roi)
    rf, tf, spf = admission.admission(fake, ffr, froi)[:3]
    print(f"   S1 synthetic stationary bracket from THIS subject's own pixels,")
    print(f"      one real frame + independent noise at the measured {fsd:.2f} DN:")
    print(f"      ratio {rf:6.3f}   {'PASS -- the test admits a stationary leaf-2-cpl patch' if rf <= admission.BAR else 'FAIL -- the test is broken or the subject is'}")
    ac_leaf = lag1_autocorr(imgs, frames, roi)
    print(f"   S2 lag-1 temporal autocorrelation along the frame order (an instrument")
    print(f"      that shares NOTHING with the admission test; pure noise reads ~0):")
    print(f"      leaf-2-cpl claim patch : {ac_leaf:+.4f}")
    ac_fake = lag1_autocorr(fake, ffr, froi)
    print(f"      synthetic stationary   : {ac_fake:+.4f}")
    d9 = RENDERS / "109MSDCF"
    f9 = sorted(p.stem for p in d9.glob("frame*.tif"))
    i9 = {f: pn.green(d9 / f"{f}.tif") for f in f9}
    ac_109 = lag1_autocorr(i9, f9, (1416, 264, 256, 256))
    r109 = admission.admission(i9, f9, (1416, 264, 256, 256))[0]
    print(f"      109MSDCF admitted patch: {ac_109:+.4f}   (its admission ratio {r109:.3f})")

    # --- 5. does the subject have ANY admissible patch? --------------------
    print(f"\n5. DOES leaf-2-cpl HAVE ANY ADMISSIBLE PATCH?")
    w = h = roi[2]
    H, W = plane_shape
    cands = []
    for yy in range(120, H - h - 120, 96):
        for xx in range(120, W - w - 120, 96):
            rr = admission.admission(imgs, frames, (xx, yy, w, h))[0]
            cands.append((rr, xx, yy))
    cands.sort()
    n_ok = sum(1 for c in cands if c[0] <= admission.BAR)
    print(f"   scanned {len(cands)} windows of {w}x{h} across the whole plane")
    print(f"   admissible (<= {admission.BAR}) : {n_ok} of {len(cands)}")
    print(f"   best 5   : " + "  ".join(f"{c[0]:.2f}@({c[1]},{c[2]})" for c in cands[:5]))
    print(f"   worst    : {cands[-1][0]:.2f}@({cands[-1][1]},{cands[-1][2]})")
    print(f"   median   : {np.median([c[0] for c in cands]):.2f}")

    # --- 6. the claim's statistic at the best-behaved patches --------------
    print(f"\n6. THE CLAIM'S OWN STATISTIC, AT PATCHES ORDERED BY ADMISSION")
    print(f"   {'admission':>10} {'plane patch':>16} {'gate0 sigma':>12} {'gate2 sigma':>12} "
          f"{'ratio':>8} {'equiv N':>8}")
    rows = []
    probe = cands[:6] + cands[len(cands) // 2:len(cands) // 2 + 2] + cands[-2:]
    for rr, xx, yy in probe:
        fr = plane_to_arm((xx, yy, w, h), plane_shape, a.shape[:2], s)
        if not (0 <= fr[0] and fr[0] + fr[2] <= a.shape[1]
                and 0 <= fr[1] and fr[1] + fr[3] <= a.shape[0]):
            continue
        pa, pb = hp_sigma(a, fr[1], fr[0], fr[2]), hp_sigma(b, fr[1], fr[0], fr[2])
        rows.append((rr, xx, yy, pa, pb, pb / pa))
        print(f"   {rr:10.3f} {f'({xx},{yy})':>16} {pa:12.6f} {pb:12.6f} "
              f"{pb / pa:7.4f}x {(pa / pb) ** 2:8.2f}")
    if len(rows) >= 4:
        A = np.array([r[0] for r in rows])
        B = np.array([r[5] for r in rows])
        print(f"   correlation(admission ratio, sigma ratio) = {np.corrcoef(A, B)[0, 1]:+.3f}")
        print(f"     a NEGATIVE correlation means: the less stationary the patch, the")
        print(f"     LOWER the claimed noise ratio -- i.e. the claim is largest exactly")
        print(f"     where the statistic is least valid.")

    # --- 7. reconcile with the tool's own n_eff ---------------------------
    print(f"\n7. RECONCILIATION WITH THE TOOL'S OWN n_eff MAP")
    npath = CLAIM / "neff.tif"
    if npath.exists():
        nm = tifffile.imread(npath).astype(np.float64)
        print(f"   n_eff map {nm.shape}, plane coordinates, range {nm.min():.0f}..{nm.max():.0f}")
        ny, nx = nm.shape[0], nm.shape[1]
        # the n_eff map is written on the merge's own grid; locate the claim's
        # patch on it by the same proportional mapping used for the render.
        pr = (int(round(fx * nx / a.shape[1])), int(round(fy * ny / a.shape[0])),
              max(1, int(round(F * nx / a.shape[1]))), max(1, int(round(F * ny / a.shape[0]))))
        tile = nm[pr[1]:pr[1] + pr[3], pr[0]:pr[0] + pr[2]]
        neff = float(tile.mean())
        print(f"   claim's patch on the n_eff map : {pr}   mean n_eff {neff:.2f}"
              f"   (whole map mean {nm.mean():.2f})")
        pred = 1.0 / np.sqrt(neff) if neff > 0 else float("nan")
        print(f"\n   the three independent numbers that must reconcile:")
        print(f"     measured sigma ratio                       {ratio:.4f}x")
        print(f"     admission ratio at the same patch          {r0:.3f}")
        print(f"     corrected = measured * admission           {ratio * r0:.4f}x")
        print(f"     tool's own prediction from n_eff, 1/sqrt(n){pred:.4f}x")
        print(f"     |corrected - 1/sqrt(n)| / (1/sqrt(n))      "
              f"{abs(ratio * r0 - pred) / pred * 100:.1f}%")
        print(f"     |measured  - 1/sqrt(n)| / (1/sqrt(n))      "
              f"{abs(ratio - pred) / pred * 100:.1f}%")
    else:
        neff = float("nan")
        print("   n_eff map not present -- run render_claim.ps1 first")

    out = {"claim_patch_full": [fx, fy, F, F], "claim_patch_plane": list(roi),
           "sigma_gate0": sa, "sigma_gate2": sb, "ratio": ratio,
           "admission": r0, "admission_drift_compensated": r1,
           "admission_jitter": [min(jitter), max(jitter)],
           "synthetic_stationary": rf, "lag1_leaf": ac_leaf,
           "lag1_synth": ac_fake, "lag1_109": ac_109, "adm_109": r109,
           "n_admissible": n_ok, "n_windows": len(cands),
           "best_windows": cands[:5], "probe_rows": rows,
           "fov_scale": s, "n_frames": len(frames)}
    (CLAIM / "_adjudication.json").write_text(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
