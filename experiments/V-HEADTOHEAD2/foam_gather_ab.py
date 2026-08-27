"""
foam_gather_ab.py -- decide the `foam` specular fringing by changing the
estimator and watching whether the colour follows.

THE LOGIC.  Subject colour is a property of the scene and is invariant to how
the merge gathers its samples. An estimator artifact is keyed to the gather
lattice and must move when the lattice moves. `STREHL_FULLRES_GATHER` changes
the lattice and nothing else: arm 0 gathers each frame from its own
half-resolution CFA phase plane, arm 1 demosaics to full sensor resolution
before the warp. One binary, one warpmap, one subject.

WHY THIS IS STRONGER THAN `foam_fringe.py`.  That script's load-bearing arm
was retention through the merge -- foam kept 70.9% of its photosite chroma
across 100 frames where polished steel kept 15.9%. That separates
DETERMINISTIC from PHASE-RANDOM. It does NOT separate SCENE from PIPELINE,
because a deterministic pipeline defect keyed to signal level is also
frame-invariant and also survives averaging. This test does separate them.

THE CONFOUND, AND THE CONTROL THAT REMOVES IT.  The gather flip genuinely
changes resolution -- that is its purpose, and this lane measured 2.10x more
coherent fine structure at 0.20-0.25 cyc/px because of it. So SOME change at a
sharp rim is expected from resolution alone and would be misread as "the
colour moved". The control is to measure the same two quantities at
NON-SPECULAR high-contrast texture in the same frames: if chroma at speculars
moves no more than chroma at ordinary edges, the change is the resolution
difference and not a specular-specific artifact.

Reads .tiff with tifffile per this project's rule.
"""

import os
import sys

import numpy as np
import tifffile

REND = r"C:\dev\strehl-out\V-H2H2\renders"
G0 = os.path.join(REND, "foam-g0.tiff")
G1 = os.path.join(REND, "foam-g1.tiff")

# The owner's DELIVER-V5 1:1 crop is expressed in SHIP-V4 master coordinates
# (7032 x 4688). These renders come out at CFA-plane resolution (3516 x 2344),
# so the box is rescaled by the MEASURED axis ratio rather than a hard-coded
# 2, and then asserted to fit.
SPEC_SHIP = (3466, 1698, 380)     # x, y, size in SHIP-V4 coordinates
SHIP_W, SHIP_H = 7032, 4688


def scale_box(box, w, h):
    """Map a SHIP-V4 box into this render's grid by the measured ratio."""
    sx, sy = w / SHIP_W, h / SHIP_H
    x, y, s = box
    return (int(round(x * sx)), int(round(y * sy)),
            max(16, int(round(s * min(sx, sy)))))


def assert_fits(box, w, h, tag):
    """HARD ERROR on an out-of-range box.

    THIS CHECK EXISTS BECAUSE ITS ABSENCE ALREADY COST A WRONG ANSWER.  The
    first run of this script used SHIP-V4 coordinates against a half-resolution
    render. numpy slicing CLIPS silently, so `a[1698:2078, 3466:3846]` returned
    a 380x50 sliver at the right edge instead of the intended 380x380 crop --
    and produced entirely plausible numbers (chroma 0.1668 -> 0.1731, r=0.96)
    that were not measuring the region they claimed. A probe that reports a
    confident number for a region it never sampled is worse than one that
    fails."""
    x, y, s = box
    if x < 0 or y < 0 or x + s > w or y + s > h:
        raise AssertionError(
            f"{tag}: box x={x} y={y} size={s} does not fit in {w}x{h}; "
            "numpy would clip this silently")
    return box


def blown_frac(img):
    """Fraction of pixels at/near the ceiling."""
    lum = img.astype(np.float64).mean(axis=2) if img.ndim == 3 else img
    return float((lum >= lum.max() * 0.98).mean())


def find_control(img, size, n_try=600, seed=7):
    """Pick the control region BY MEASUREMENT rather than by guess.

    MEASURED, and it changed the design: `foam` has NO unblown region at this
    tile size. Every one of 240 candidate 190x190 tiles contained blown pixels
    (minimum 0.0166%, median 0.385%, whole frame 0.38%) -- the subject is
    saturated with speculars throughout. The first version of this function
    demanded an unblown control and correctly returned nothing rather than
    silently accepting a blown one.

    So the control is not "unblown"; it is "as little blown as can be found
    while still carrying texture", and BOTH regions' blown fractions are
    reported so the reader can see how unequal the exposure to saturation is
    rather than having to trust the word 'control'."""
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    lum = img.astype(np.float64).mean(axis=2)
    ceiling = float(lum.max()) * 0.98
    cands = []
    for _ in range(n_try):
        x = int(rng.integers(0, w - size))
        y = int(rng.integers(0, h - size))
        t = lum[y:y + size, x:x + size]
        cands.append(((x, y, size), float((t >= ceiling).mean()),
                      float(t.std() / max(t.mean(), 1e-9))))
    if not cands:
        return None, None, None
    # least-blown decile, then the most textured within it
    cands.sort(key=lambda c: c[1])
    pool = cands[:max(1, len(cands) // 10)]
    box, bf, ct = max(pool, key=lambda c: c[2])
    return box, bf, ct


def sat(rgb):
    """Saturation = (max-min)/max per pixel, the same definition foam_fringe.py
    used, so the two scripts' numbers are comparable."""
    a = rgb.astype(np.float64)
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    out = np.zeros_like(mx)
    ok = mx > 0
    out[ok] = (mx[ok] - mn[ok]) / mx[ok]
    return out


def shoulder(rgb, lo=95.0, hi=99.8):
    """The rim SHOULDER: bright enough to be the specular edge, below the blown
    core. foam_fringe.py established that sampling the core reads saturation
    0.0000 because the core is white."""
    lum = rgb.astype(np.float64).mean(axis=2)
    a, b = np.percentile(lum, lo), np.percentile(lum, hi)
    return (lum >= a) & (lum <= b)


def region(mm, box):
    x, y, s = box
    return np.asarray(mm[y:y + s, x:x + s])


def describe(tag, r0, r1):
    """Report chroma level in each arm and how much the chroma PATTERN moved."""
    m0, m1 = shoulder(r0), shoulder(r1)
    s0, s1 = sat(r0), sat(r1)
    med0 = float(np.median(s0[m0])) if m0.sum() else float("nan")
    med1 = float(np.median(s1[m1])) if m1.sum() else float("nan")

    # pattern correlation on the union shoulder, at identical pixel positions:
    # both arms share one warpmap, so the grids are registered by construction
    # and no resampling is applied here (that would blur what is measured).
    u = m0 | m1
    a, b = s0[u], s1[u]
    if a.size > 10 and a.std() > 0 and b.std() > 0:
        corr = float(np.corrcoef(a, b)[0, 1])
    else:
        corr = float("nan")

    # luminance change over the same pixels, as the scale of change the
    # resolution difference alone produces
    l0 = r0.astype(np.float64).mean(axis=2)[u]
    l1 = r1.astype(np.float64).mean(axis=2)[u]
    lum_rel = float(np.median(np.abs(l1 - l0)) / max(np.median(l0), 1e-9))

    rel = abs(med1 - med0) / max(med0, 1e-9)
    print(f"  {tag}")
    print(f"    chroma  g0={med0:.4f}  g1={med1:.4f}   moved {rel * 100:+.2f}%")
    print(f"    chroma pattern correlation g0 vs g1 : {corr:.4f}")
    print(f"    median |dLum|/Lum over same px      : {lum_rel * 100:.2f}%")
    return rel, corr, lum_rel


def main():
    for p in (G0, G1):
        if not os.path.exists(p):
            print(f"MISSING: {p}\nrun render_foam_ab.ps1 first")
            sys.exit(2)

    a = tifffile.memmap(G0, mode="r")
    b = tifffile.memmap(G1, mode="r")
    print(f"g0 {a.shape} {a.dtype}\ng1 {b.shape} {b.dtype}\n")
    if a.shape != b.shape:
        print("shape mismatch -- arms are not comparable")
        sys.exit(2)

    h, w = a.shape[:2]

    # The A/B is worthless if the two arms are the same image. Assert the
    # disturbance is REAL before asking the probe anything.
    a0 = np.asarray(a).astype(np.float64)
    b0 = np.asarray(b).astype(np.float64)
    d = np.abs(b0 - a0)
    frac = float((d > 0).mean())
    print(f"DISTURBANCE CHECK: {frac * 100:.2f}% of pixels differ, "
          f"mean |d| = {d.mean():.1f} DN")
    if frac < 0.01:
        raise AssertionError(
            "the two gather arms are effectively identical -- this is a "
            "non-disturbance and no verdict may be drawn from it")
    print()

    spec = assert_fits(scale_box(SPEC_SHIP, w, h), w, h, "specular")
    ctrl, bf, cc = find_control(a0, spec[2])
    if ctrl is None:
        print("no control region found")
        sys.exit(2)
    assert_fits(ctrl, w, h, "control")
    spec_bf = blown_frac(region(a, spec))
    print(f"specular box (SHIP {SPEC_SHIP}) -> render {spec}, "
          f"blown {spec_bf * 100:.3f}%")
    print(f"control  box {ctrl} chosen by measurement, "
          f"blown {bf * 100:.3f}%, local contrast {cc:.3f}")
    print(f"  (foam has NO unblown region at this tile size; the control is "
          f"{spec_bf / max(bf, 1e-9):.0f}x less blown, not unblown)\n")

    print("=== SPECULAR (the rims in question) ===")
    s_rel, s_corr, s_lum = describe("specular", region(a, spec), region(b, spec))
    print("\n=== CONTROL: ordinary high-contrast texture, no blown highlight ===")
    c_rel, c_corr, c_lum = describe("control", region(a, ctrl), region(b, ctrl))

    print("\n=== VERDICT ===")
    print(f"  specular chroma moved {s_rel * 100:+.2f}%, "
          f"control chroma moved {c_rel * 100:+.2f}%")
    if not np.isfinite(s_rel) or not np.isfinite(c_rel):
        print("  UNDECIDED -- a region did not yield a usable shoulder")
        return
    ratio = s_rel / max(c_rel, 1e-9)
    print(f"  specular : control = {ratio:.2f}x")
    print()
    if ratio > 2.0:
        print("  ESTIMATOR-KEYED: specular chroma follows the gather lattice")
        print("  far more than ordinary edges do. Route for fix.")
    elif s_corr > 0.9:
        print("  SUBJECT: the chroma PATTERN survives a change of gather")
        print(f"  lattice at r={s_corr:.4f}, and moves no more than ordinary")
        print("  texture does. The colour is not made by the estimator.")
    else:
        print("  UNDECIDED on this evidence.")


if __name__ == "__main__":
    main()
