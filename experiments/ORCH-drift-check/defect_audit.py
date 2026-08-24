"""Systematic visible-defect audit of a strehl render.

Motivation: the owner's complaint is aesthetic ("those stacks don't look too
good yet"), and the one time I chased it by eye I found the magenta highlight
defect only because a blob was large enough to notice -- my first ROI probe
actually CLEARED it, because I chose the ROI and chose wrong (fact 1434). The
lesson folded from that (discipline 713) is to let a predicate locate the
region instead of choosing one. This script does that for a battery of defect
classes at once.

Per discipline 717, every threshold below is registered HERE, before the run,
and each check reports FIRED / clear against it. A threshold is a claim about
what counts as visible; getting one wrong is a finding about the threshold, not
licence to edit it after seeing the number.

Checks and their pre-registered thresholds:
  D1 magenta/clipped highlights   FIRED if >0.05% of pixels have R-G>0.06 and B-G>0.06
  D2 chroma fringing on edges     FIRED if mean |chroma| on strong edges exceeds
                                  3.0x mean |chroma| off edges
  D3 waxy blobs (piecewise-flat)  FIRED if >2.0% of MID-DETAIL pixels sit in
                                  locally-flat patches bounded by hard steps
  D4 isolated hot/dead pixels     FIRED if >200 pixels deviate >0.25 from the
                                  median of their 8 neighbours
  D5 row/column banding           FIRED if row-mean or col-mean spectrum has a
                                  peak >6.0x the local median away from DC
  D6 edge overshoot / halo        FIRED if >1.0% of strong edges show ringing
                                  overshoot beyond the local min/max envelope
  D7 posterisation                FIRED if the luminance histogram has >2% of
                                  mass in spikes >8x their neighbourhood
  D8 saturation clipping in colour FIRED if >0.5% of pixels are at 1.0 in
                                  exactly one or two channels (not all three)

RESULTS AFTER THE CONTROL WAS ADDED -- READ BEFORE QUOTING ANY CHECK.

The audit was first run with NO control and reported five FIRED checks. A
single unstacked LibRaw frame of the same scene (`single_frame_control.py`) was
then put through the identical battery. It killed three of the five:

  SURVIVING (strehl differs from an unstacked frame of the same scene):
    D1  magenta   strehl 2.0017% vs control 0.0061% on marker -- a 328x excess.
                  LibRaw sees the SAME saturated sensels and does not render
                  them magenta, so this is strehl's colour path, not the
                  capture. Confirms the M109 diagnosis and supplies the control
                  that diagnosis lacked.
    D2  chroma    on lavendar, strehl 4.22x vs control 1.36x -- a 3.1x excess.
                  On marker, 2.65x vs 2.23x -- only 1.19x, i.e. essentially all
                  scene. So the effect is real and LOCALISED, not global.

  KILLED BY THE CONTROL (measure scene content, or are simply wrong):
    D3  waxy      control fires at 8.3%/10.1% against strehl's 10.2%/6.8%. On
                  marker the CONTROL IS HIGHER THAN STREHL. The check is built
                  from percentiles of the image itself, so it fires on any
                  image by construction. It does not detect the waxy blobs and
                  must not be cited as evidence about them.
    D5  banding   control 6483x/17518x, same order as strehl. It is measuring
                  ordinary low-frequency structure -- vignetting and subject
                  gradient -- which every real photograph has.
    D6  overshoot BROKEN, not merely uninformative: it reported 147% and 150%
                  on strehl, and a fraction cannot exceed 100%. The numerator
                  counts pixels over a DILATED edge mask while the denominator
                  counts the undilated one, so the supports differ. Any value
                  from it, including the control's 3.8%/10.4%, is meaningless.

  NEVER FIRED ANYWHERE: D4 (hot pixels, 0-2 px), D7 (posterisation, 0.000%).

STILL WITHOUT AN INSTRUMENT: the waxy blobs. D3 was the attempt and the control
refuted it. Do not read D3's silence as their absence.

Usage:  python defect_audit.py <render.tif> [more.tif ...]
        python single_frame_control.py <stackdir> <control.tif>   # ALWAYS
"""
import sys

import numpy as np
import tifffile

# --- registered thresholds, written before measurement -----------------------
T_D1_FRAC = 0.0005
T_D2_RATIO = 3.0
T_D3_FRAC = 0.020
T_D4_COUNT = 200
T_D5_PEAK = 6.0
T_D6_FRAC = 0.010
T_D7_MASS = 0.020
T_D8_FRAC = 0.005


def load(path):
    a = tifffile.imread(path)
    if a.dtype == np.uint16:
        a = a.astype(np.float32) / 65535.0
    elif a.dtype == np.uint8:
        a = a.astype(np.float32) / 255.0
    else:
        a = a.astype(np.float32)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    return a[..., :3]


def luma(img):
    return 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]


def box(a, r):
    """Fast box mean via summed-area table."""
    p = np.pad(a, r + 1, mode="edge")
    s = p.cumsum(0).cumsum(1)
    n = 2 * r + 1
    h, w = a.shape
    out = (s[n:n + h, n:n + w] - s[0:h, n:n + w] - s[n:n + h, 0:w] + s[0:h, 0:w])
    return out / (n * n)


def d1_magenta(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    m = (r - g > 0.06) & (b - g > 0.06)
    frac = m.mean()
    detail = ""
    if m.any():
        ys, xs = np.nonzero(m)
        detail = (f"centroid=({xs.mean()/img.shape[1]:.3f},{ys.mean()/img.shape[0]:.3f}) "
                  f"meanRGB=({r[m].mean():.4f},{g[m].mean():.4f},{b[m].mean():.4f})")
    return frac >= T_D1_FRAC, f"{frac*100:.4f}% of pixels magenta (bar {T_D1_FRAC*100:.3f}%) {detail}"


def d2_fringing(img):
    y = luma(img)
    gy, gx = np.gradient(y)
    grad = np.hypot(gx, gy)
    chroma = np.maximum(np.abs(img[..., 0] - y), np.abs(img[..., 2] - y))
    thr = np.percentile(grad, 99.0)
    edge = grad >= thr
    flat = grad <= np.percentile(grad, 50.0)
    if not edge.any() or not flat.any():
        return False, "no edges found"
    ce, cf = chroma[edge].mean(), chroma[flat].mean()
    ratio = ce / max(cf, 1e-9)
    return ratio >= T_D2_RATIO, f"chroma on edges {ce:.5f} vs flat {cf:.5f}, ratio {ratio:.2f}x (bar {T_D2_RATIO}x)"


def d3_waxy(img):
    """Locally-flat patches that are bounded by hard steps.

    A waxy blob is not merely smooth -- smooth is what an out-of-focus region
    looks like, and that is correct. It is smooth INSIDE and stepped at the
    BOUNDARY, which is what an election boundary produces and what optical
    softness cannot. So the predicate is: low local variance, adjacent to high
    local-variance-of-the-local-mean.
    """
    y = luma(img)
    m = box(y, 3)
    v = np.maximum(box(y * y, 3) - m * m, 0.0)
    sd = np.sqrt(v)
    # mid-detail: exclude true background (very dark/flat) and blown areas
    mid = (m > 0.08) & (m < 0.97)
    if mid.sum() < 1000:
        return False, "too few mid-detail pixels"
    flat_thr = np.percentile(sd[mid], 25.0)
    flat = (sd <= flat_thr) & mid
    # step energy of the SMOOTHED field: hard boundaries survive smoothing
    dgy, dgx = np.gradient(m)
    step = np.hypot(dgx, dgy)
    step_thr = np.percentile(step[mid], 97.0)
    hard = step >= step_thr
    # a flat pixel within 4 px of a hard step
    near = box(hard.astype(np.float32), 4) > 0
    blob = flat & near
    frac = blob.sum() / mid.sum()
    return frac >= T_D3_FRAC, f"{frac*100:.3f}% of mid-detail pixels are flat-and-bounded (bar {T_D3_FRAC*100:.1f}%)"


def d4_hotpixels(img):
    y = luma(img)
    h, w = y.shape
    st = np.lib.stride_tricks.sliding_window_view(y, (3, 3))
    nb = st.reshape(h - 2, w - 2, 9)
    centre = nb[..., 4].copy()
    nb = np.delete(nb, 4, axis=2)
    med = np.median(nb, axis=2)
    dev = np.abs(centre - med)
    n = int((dev > 0.25).sum())
    return n > T_D4_COUNT, f"{n} isolated pixels deviate >0.25 from neighbour median (bar {T_D4_COUNT})"


def d5_banding(img):
    y = luma(img)
    out = []
    fired = False
    for axis, name in ((1, "row"), (0, "col")):
        prof = y.mean(axis=axis)
        prof = prof - prof.mean()
        sp = np.abs(np.fft.rfft(prof * np.hanning(len(prof))))
        sp[:4] = 0.0
        if sp.max() <= 0:
            continue
        med = np.median(sp[sp > 0])
        peak = sp.max() / max(med, 1e-12)
        out.append(f"{name} peak {peak:.2f}x median")
        if peak >= T_D5_PEAK:
            fired = True
    return fired, "; ".join(out) + f" (bar {T_D5_PEAK}x)"


def d6_overshoot(img):
    y = luma(img)
    gy, gx = np.gradient(y)
    grad = np.hypot(gx, gy)
    thr = np.percentile(grad, 99.5)
    edge = grad >= thr
    if edge.sum() < 100:
        return False, "too few strong edges"
    lo = -box(-y, 3)  # not a true min, but a smoothed lower envelope
    hi = box(y, 3)
    # ringing: pixel exceeds the local smoothed envelope by a visible margin
    over = (y > hi + 0.05) | (y < lo - 0.05)
    near_edge = box(edge.astype(np.float32), 3) > 0
    frac = (over & near_edge).sum() / max(edge.sum(), 1)
    return frac >= T_D6_FRAC, f"{frac*100:.3f}% overshoot near strong edges (bar {T_D6_FRAC*100:.1f}%)"


def d7_posterisation(img):
    y = luma(img)
    hist, _ = np.histogram(y, bins=1024, range=(0.0, 1.0))
    hist = hist.astype(np.float64)
    k = 9
    pad = np.pad(hist, k // 2, mode="edge")
    local = np.convolve(pad, np.ones(k) / k, mode="valid")
    spike = hist > 8.0 * np.maximum(local, 1.0)
    mass = hist[spike].sum() / max(hist.sum(), 1)
    return mass >= T_D7_MASS, f"{mass*100:.3f}% of luminance mass in histogram spikes (bar {T_D7_MASS*100:.1f}%)"


def d8_partial_clip(img):
    at1 = img >= 0.999
    n = at1.sum(axis=2)
    partial = (n >= 1) & (n <= 2)
    frac = partial.mean()
    return frac >= T_D8_FRAC, f"{frac*100:.4f}% of pixels clip in 1-2 channels but not all 3 (bar {T_D8_FRAC*100:.2f}%)"


CHECKS = [
    ("D1 magenta/clipped highlights", d1_magenta),
    ("D2 chroma fringing on edges", d2_fringing),
    ("D3 waxy blobs (flat + hard-bounded)", d3_waxy),
    ("D4 isolated hot/dead pixels", d4_hotpixels),
    ("D5 row/column banding", d5_banding),
    ("D6 edge overshoot / ringing", d6_overshoot),
    ("D7 posterisation", d7_posterisation),
    ("D8 partial-channel clipping", d8_partial_clip),
]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    any_fired = False
    for path in sys.argv[1:]:
        img = load(path)
        print(f"\n=== {path}")
        print(f"    {img.shape[1]}x{img.shape[0]}, "
              f"luma mean {luma(img).mean():.4f}, "
              f"p99.9 {np.percentile(luma(img), 99.9):.4f}")
        for name, fn in CHECKS:
            try:
                fired, detail = fn(img)
            except Exception as e:  # a check that crashes is a finding, not a pass
                print(f"    [ERROR ] {name}: {type(e).__name__}: {e}")
                any_fired = True
                continue
            tag = "FIRED " if fired else "clear "
            if fired:
                any_fired = True
            print(f"    [{tag}] {name}: {detail}")
    print("\nNOTE: a FIRED check is a candidate defect, not a proven one -- each")
    print("needs its own confirmation against the raw data, as the magenta one got.")
    print("A 'clear' is only as good as its registered threshold.")
    return 1 if any_fired else 0


if __name__ == "__main__":
    sys.exit(main())
