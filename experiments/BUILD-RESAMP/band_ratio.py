"""BUILD-RESAMP -- band-ratio A/B between two renders that differ only in the
gather kernel.

Both arms come from one binary, one subject, one backend, and differ in exactly
one argv token. There is therefore no grade difference between them; the
per-arm normalisation by each arm's own 0.02-0.05 band is kept anyway, because
it is the statistic V-HEADTOHEAD used and keeping it makes the numbers
comparable to that report's table.

WHAT THIS METRIC CAN BE FOOLED BY (rule 18). It is band power. Band power rises
when a kernel rings, when a kernel aliases, and when a merge passes more noise,
exactly as it rises when detail is preserved. `nearest` -- the worst gather in
the enum -- tops it. So it is admissible as a *comparison between two kernels
whose ringing is separately bounded*, and inadmissible on its own as evidence
of quality. Two controls are printed with every run and neither is optional:

  * FLAT ROIs (rule 9). If the ratio on featureless ROIs matches the ratio on
    detail ROIs, the statistic is reading the noise transfer of the kernel and
    not its detail transfer.
  * BAND COMPOSITION. For each band, the share of a detail ROI's power that is
    NOT present in a flat ROI of the same render. A band whose composition is
    mostly floor cannot carry a resolution claim -- this is the test
    `ORCH-kernel-decision.md` amendment 3 requires before the decision reopens.

Green channel only: green is the channel the alignment plane is built from, it
is the one bit-identical across builds, and the lateral-CA correction moves red
against green so measuring green keeps the CA correction out of the comparison.
"""

import argparse
import json
import sys

import numpy as np
import tifffile

# Cycles per OUTPUT pixel of the rendered raster. These are the bands
# V-HEADTOHEAD reported against two external comparators.
BANDS = [
    ("0.02-0.05", 0.02, 0.05),
    ("0.05-0.10", 0.05, 0.10),
    ("0.10-0.20", 0.10, 0.20),
    ("0.20-0.30", 0.20, 0.30),
    ("0.30-0.40", 0.30, 0.40),
    ("0.40-0.48", 0.40, 0.48),
]
NORM = "0.02-0.05"
TILE = 256
BORDER = 96  # keep the fit off the coverage boundary


def green(path):
    a = tifffile.imread(path)
    if a.ndim != 3 or a.shape[2] < 3:
        raise SystemExit(f"{path}: expected HxWx3, got {a.shape}")
    return a[:, :, 1].astype(np.float64)


def tiles(h, w, border=BORDER):
    ys = range(border, h - border - TILE + 1, TILE)
    xs = range(border, w - border - TILE + 1, TILE)
    return [(y, x) for y in ys for x in xs]


def band_masks(scale=1.0):
    """Band masks in cycles per output pixel.

    `scale` exists for the coverage-upscale arms only. A render whose field of
    view was scaled to k occupies 1/k more pixels per scene feature, so a scene
    frequency f lands at f*k in that raster. Reading such an arm with
    scale=k compares the two arms at the same SCENE frequency instead of at the
    same raster frequency -- without it the geometric magnification alone would
    be scored as a resampling loss. For same-k arms (every kernel A/B here)
    scale is 1.0 on both sides and the masks are bit-identical.
    """
    fy = np.fft.fftfreq(TILE)[:, None]
    fx = np.fft.rfftfreq(TILE)[None, :]
    r = np.sqrt(fy**2 + fx**2)
    return {n: (r >= lo * scale) & (r < hi * scale) for n, lo, hi in BANDS}


def roi_bands(img, pos, masks, win):
    """Band POWER per ROI, one row per ROI, one column per band."""
    out = np.zeros((len(pos), len(BANDS)))
    for i, (y, x) in enumerate(pos):
        t = img[y : y + TILE, x : x + TILE]
        t = (t - t.mean()) * win
        p = np.abs(np.fft.rfft2(t)) ** 2
        for j, (n, _, _) in enumerate(BANDS):
            out[i, j] = p[masks[n]].mean()
    return out


def boot_ci(v, reps=4000, seed=12345):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(reps, len(v)))
    med = np.median(v[idx], axis=1)
    return float(np.percentile(med, 2.5)), float(np.percentile(med, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="numerator render (the candidate)")
    ap.add_argument("--b", required=True, help="denominator render (the default)")
    ap.add_argument("--label", default="")
    ap.add_argument("--scale-a", type=float, default=1.0,
                    help="coverage k of arm A; band edges are read at f*k in that arm")
    ap.add_argument("--scale-b", type=float, default=1.0)
    ap.add_argument("--border", type=int, default=BORDER,
                    help="pixels excluded on every side; must exceed any uncovered margin")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    a = green(args.a)
    b = green(args.b)
    if a.shape != b.shape:
        raise SystemExit(f"shape mismatch {a.shape} vs {b.shape}")
    h, w = a.shape

    identical = np.array_equal(a, b)
    pos = tiles(h, w, args.border)
    masks_a = band_masks(args.scale_a)
    masks_b = band_masks(args.scale_b)
    wy = np.hanning(TILE)[:, None]
    wx = np.hanning(TILE)[None, :]
    win = wy * wx

    pa = roi_bands(a, pos, masks_a, win)
    pb = roi_bands(b, pos, masks_b, win)

    ni = [n for n, _, _ in BANDS].index(NORM)
    # Shape statistic: each arm normalised by its OWN low band, so any scalar
    # gain cancels exactly and only the spectrum's shape survives.
    sa = pa / pa[:, ni : ni + 1]
    sb = pb / pb[:, ni : ni + 1]

    # ROI classification, done on the DENOMINATOR arm only so the split is not a
    # function of the thing under test.
    detail_score = pb[:, 3] + pb[:, 4]
    lo = np.percentile(detail_score, 25)
    hi = np.percentile(detail_score, 75)
    flat = detail_score <= lo
    det = detail_score >= hi

    print(f"# {args.label}")
    print(f"  A (candidate) : {args.a}")
    print(f"  B (default)   : {args.b}")
    print(f"  raster        : {w} x {h}, green channel, {len(pos)} ROIs of {TILE}px")
    print(f"  byte-identical: {identical}")
    print()
    print(f"  {'band':<12}{'ALL ROIs':>10}{'95% CI':>20}{'DETAIL':>10}{'FLAT':>10}"
          f"{'detail share of B':>20}")
    rows = {}
    for j, (n, _, _) in enumerate(BANDS):
        if j == ni:
            continue
        r_all = np.sqrt(sa[:, j] / sb[:, j])          # amplitude ratio
        r_det = np.sqrt(sa[det, j] / sb[det, j])
        r_flat = np.sqrt(sa[flat, j] / sb[flat, j])
        ci = boot_ci(r_all)
        # Band composition: how much of a detail ROI's power in this band is
        # absent from a flat ROI of the SAME render. Uses raw power, not the
        # shape statistic, because the floor is an absolute quantity.
        d_pow = np.median(pb[det, j])
        f_pow = np.median(pb[flat, j])
        share = max(0.0, (d_pow - f_pow) / d_pow)
        print(f"  {n:<12}{np.median(r_all):>10.4f}"
              f"{f'[{ci[0]:.4f}, {ci[1]:.4f}]':>20}"
              f"{np.median(r_det):>10.4f}{np.median(r_flat):>10.4f}{share:>20.4f}")
        rows[n] = {
            "all": float(np.median(r_all)),
            "ci": ci,
            "detail": float(np.median(r_det)),
            "flat": float(np.median(r_flat)),
            "detail_share": float(share),
        }
    print()
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(
                {"a": args.a, "b": args.b, "label": args.label,
                 "identical": bool(identical), "rois": len(pos), "bands": rows},
                f, indent=1,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
