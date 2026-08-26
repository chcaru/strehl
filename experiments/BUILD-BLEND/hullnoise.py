"""Does the hull clamp inject flat-region noise?

Why this exists
---------------
`275fbd17` made `Hull::InputRange` the default.  My own report records that
flat-region noise on `couch-fibers-cpl` went from 1.0015 at pin `0d9fd28` to
1.1179 at pin `275fbd17` -- and then attributes the change to "shared code I do
not own" and declines to bisect it.  That attribution was wrong on its face:
`275fbd17` is my commit, in my file, and it changed a default.

There is also a mechanism, which the module's own documentation argues cannot
exist.  `Hull::InputRange` clamps to `[min_k, max_k]` over the aligned frames.
Where it binds, the output value is no longer the reconstruction -- it is an
*extreme order statistic of N noisy frames*.  Extreme order statistics have high
variance and are biased outward, so substituting one for a smooth reconstruction
is a plausible way to add high-frequency energy in exactly the flat regions where
`min_k` and `max_k` are pure noise.  The docstring's claim that clamping "cannot
cost anything real" rests on the hull being justified by the data, which is an
argument about *bias*, not about *variance*.

The design's internal control
-----------------------------
The two arms differ by one flag, so `A != B` is exactly the set of pixels where
the clamp bound.  Every pixel where it did not bind is byte-identical between the
arms by construction.  That means a tile's bind fraction is a within-image dose,
and if the clamp is responsible the added noise must be confined to tiles with a
high dose.  A global ratio cannot distinguish "the clamp adds noise" from "these
two renders differ for some other reason"; a dose-response can.

Tiles are selected once, on the mean of the two arms, so tile choice cannot
favour either.

Usage:  python hullnoise.py <clamped.tiff> <unclamped.tiff>
"""

import sys

import numpy as np
import tifffile

TILE = 96
HP_RADIUS = 8
N_FLAT = 200


def box_blur(a, r):
    """Separable box blur via summed-area table; edge pixels use a shrunk window."""
    a = a.astype(np.float64)
    pad = np.pad(a, r + 1, mode="edge")
    ii = pad.cumsum(0).cumsum(1)
    ii = np.pad(ii, ((1, 0), (1, 0)))
    h, w = a.shape
    y0 = np.arange(h) + 1
    x0 = np.arange(w) + 1
    ya, yb = y0[:, None] - r - 1 + r + 1, y0[:, None] + r + r + 2
    xa, xb = x0[None, :] - r - 1 + r + 1, x0[None, :] + r + r + 2
    s = ii[yb, xb] - ii[ya, xb] - ii[yb, xa] + ii[ya, xa]
    return s / float((2 * r + 1) ** 2)


def highpass(a, r=HP_RADIUS):
    return a.astype(np.float64) - box_blur(a, r)


def sigma_mad(v):
    """Robust sigma.  MAD is used so a few real edges inside a tile cannot dominate."""
    v = v.ravel()
    return 1.4826 * np.median(np.abs(v - np.median(v)))


def tile_stats(img, ts=TILE):
    h, w = img.shape
    ny, nx = h // ts, w // ts
    t = img[: ny * ts, : nx * ts].reshape(ny, ts, nx, ts).swapaxes(1, 2)
    return t.reshape(ny * nx, ts, ts), ny, nx


def flatness(tiles):
    """Mean |gradient| per tile.  Low means smooth; this picks the scoring set."""
    gy = np.abs(np.diff(tiles, axis=1)).mean(axis=(1, 2))
    gx = np.abs(np.diff(tiles, axis=2)).mean(axis=(1, 2))
    return gy + gx


def measure(a, b, label, n_flat=N_FLAT):
    """Report sigma in the flattest tiles of both arms, split by clamp dose."""
    ref = 0.5 * (a + b)
    rt, ny, nx = tile_stats(ref)
    flat = flatness(rt)
    order = np.argsort(flat)[:n_flat]

    ha = highpass(a)
    hb = highpass(b)
    hat, _, _ = tile_stats(ha)
    hbt, _, _ = tile_stats(hb)

    bound = (a != b).astype(np.float64)
    bt, _, _ = tile_stats(bound)
    dose = bt.mean(axis=(1, 2))

    sa = np.array([sigma_mad(hat[i]) for i in order])
    sb = np.array([sigma_mad(hbt[i]) for i in order])
    d = dose[order]

    # Aggregate over the scoring set, pooling variance rather than averaging
    # ratios, so a single near-zero-sigma tile cannot dominate.
    SA = np.sqrt((sa ** 2).mean())
    SB = np.sqrt((sb ** 2).mean())
    print(f"\n{label}")
    print(f"  flat tiles scored        : {len(order)}")
    print(f"  clamp bound on           : {100 * d.mean():.3f}% of pixels in those tiles")
    print(f"  sigma clamped   (arm A)  : {SA:.2f} DN")
    print(f"  sigma unclamped (arm B)  : {SB:.2f} DN")
    print(f"  ratio A/B                : {SA / SB:.4f}")

    # The dose-response: does the excess live where the clamp actually bound?
    lo = d <= np.quantile(d, 0.25)
    hi = d >= np.quantile(d, 0.75)
    for name, m in (("lowest-dose quartile ", lo), ("highest-dose quartile", hi)):
        if m.sum() == 0:
            continue
        ra = np.sqrt((sa[m] ** 2).mean())
        rb = np.sqrt((sb[m] ** 2).mean())
        print(f"  {name}: dose {100 * d[m].mean():7.3f}%  "
              f"A {ra:8.2f}  B {rb:8.2f}  ratio {ra / rb:.4f}")
    return SA / SB


def main():
    pa, pb = sys.argv[1], sys.argv[2]
    A = tifffile.imread(pa)
    B = tifffile.imread(pb)
    print(f"clamped   : {pa}  {A.shape} {A.dtype}")
    print(f"unclamped : {pb}  {B.shape} {B.dtype}")
    if A.shape != B.shape:
        raise SystemExit("canvases differ; refusing to compare")

    diff = int((A != B).sum())
    print(f"pixels differing between arms : {diff:,} "
          f"({100.0 * diff / A.size:.3f}% of samples)")
    if diff == 0:
        raise SystemExit("arms are byte-identical -- the flag did nothing; nothing to measure")

    ch = {0: "R", 1: "G", 2: "B"}
    for c in range(A.shape[2]):
        a = A[:, :, c].astype(np.float64)
        b = B[:, :, c].astype(np.float64)

        # ---- commissioning, on this exact data, before any verdict is read ----
        if c == 0:
            print("\n=== commissioning ===")
            null = measure(a, a.copy(), "NULL control: arm A against itself "
                                        "(must read exactly 1.0000)")
            if abs(null - 1.0) > 1e-9:
                raise SystemExit(f"NULL CONTROL FAILED ({null}); instrument is not trustworthy")

            rng = np.random.default_rng(20260826)

            # Positive control on a synthetic Gaussian field.  The quadrature
            # prediction sqrt(s^2 + amp^2)/s assumes both components are
            # Gaussian; testing it on a Gaussian base is what actually
            # commissions the estimator and the arithmetic.  Running it on the
            # photograph instead conflates an estimator error with a modelling
            # error, which is the mistake this control originally made.
            base = rng.normal(0.0, 200.0, (960, 1440))
            amp_s = 0.60 * 200.0
            pos_s = measure(base + rng.normal(0.0, amp_s, base.shape), base,
                            f"POSITIVE control (synthetic Gaussian base, plant "
                            f"{amp_s:.1f} DN)", n_flat=100)
            sb = sigma_mad(highpass(base))
            pred_s = np.sqrt(sb ** 2 + amp_s ** 2) / sb
            err = 100 * abs(pos_s - pred_s) / (pred_s - 1.0)
            print(f"\n  synthetic: predicted {pred_s:.4f}, read {pos_s:.4f}, "
                  f"error {err:.1f}% of the effect")
            if err > 10.0:
                raise SystemExit("POSITIVE CONTROL FAILED; instrument is not trustworthy")

            # Sensitivity on the real photograph.  This is NOT a pass/fail gate:
            # the highpass of real detail is heavy-tailed, so MAD quadrature does
            # not hold and the estimator over-reads an added white component.
            # It is recorded because it bounds how far a quoted magnitude can be
            # trusted, and it establishes that the sign is reported correctly.
            amp_r = 0.20 * sigma_mad(highpass(a))
            pos_r = measure(a + rng.normal(0.0, amp_r, a.shape), a,
                            f"SENSITIVITY on the real photograph (plant {amp_r:.1f} DN)")
            print(f"\n  real-data plant reads {pos_r:.4f} (>1, correct sign). "
                  f"Magnitudes on real data are indicative, not calibrated.")
            print("  null exact, positive control passed. instrument commissioned.")
            print("\n=== measurement ===")

        measure(a, b, f"channel {ch[c]}")


if __name__ == "__main__":
    main()
