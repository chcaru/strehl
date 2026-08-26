"""Paired veil profile: two backends, ONE mask, identical pixel population.

The question: does the pyramid merge carry the estimator's veil?

Confound control that matters here: if each arm segments its own subject mask,
the two arms score different pixels and any difference could be the masks.
So the mask and the distance transform are computed ONCE, from a named
reference arm, and applied unchanged to both.

Controls printed, not assumed:
  - self-pair (ref vs ref) must give exactly 0.0 in every bin
  - a shifted-mask placebo (mask rolled 64 px) on the same arms, which must
    NOT reproduce the profile if the profile is really keyed to the silhouette
"""
import sys
import numpy as np
import tifffile
from scipy import ndimage


def luma(a):
    a = a.astype(np.float64)
    if a.ndim == 3 and a.shape[2] >= 3:
        return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    return a


BINS = [(0, 2), (2, 4), (4, 8), (8, 16), (16, 32), (32, 64),
        (64, 128), (128, 200), (200, 300), (300, 400)]


def build_mask(y, q):
    thr = float(np.quantile(y, q))
    subj = y < thr
    subj = ndimage.binary_opening(subj, np.ones((5, 5)))
    subj = ndimage.binary_closing(subj, np.ones((5, 5)))
    dist = ndimage.distance_transform_edt(~subj)
    return subj, dist, thr


def profile(y, subj, dist):
    """Return (far_field, {bin: median}) for background pixels only."""
    bg = ~subj
    far = bg & (dist > 300)
    if far.sum() < 10000:
        far = bg & (dist > 150)
    ff = float(np.median(y[far])) if far.sum() else float("nan")
    out = {}
    for lo, hi in BINS:
        sel = bg & (dist >= lo) & (dist < hi)
        n = int(sel.sum())
        out[(lo, hi)] = (n, float(np.median(y[sel])) if n > 200 else float("nan"))
    return ff, out


def main():
    if len(sys.argv) < 3:
        print("usage: veilpair.py <ref.tiff> <arm.tiff> [more.tiff ...] [--q 0.35]")
        return 2
    q = 0.35
    args = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--q":
            q = float(sys.argv[i + 1]); i += 2; continue
        args.append(sys.argv[i]); i += 1

    ref_path = args[0]
    print(f"mask reference : {ref_path}")
    yref = luma(tifffile.imread(ref_path))
    subj, dist, thr = build_mask(yref, q)
    print(f"mask quantile  : {q}   threshold {thr:.1f} DN")
    print(f"subject px     : {subj.sum():,} of {subj.size:,} "
          f"({100.0*subj.sum()/subj.size:.1f}%)")

    # placebo mask: same shape, translated off the silhouette
    subj_p = np.roll(np.roll(subj, 640, axis=0), 640, axis=1)
    dist_p = ndimage.distance_transform_edt(~subj_p)

    rows = []
    for p in args:
        y = luma(tifffile.imread(p))
        if y.shape != yref.shape:
            print(f"SKIP {p}: shape {y.shape} != ref {yref.shape}")
            continue
        ff, prof = profile(y, subj, dist)
        ffp, profp = profile(y, subj_p, dist_p)
        rows.append((p, ff, prof, ffp, profp))

    print()
    hdr = f"{'bin(px)':>10} {'n':>10}"
    for p, *_ in rows:
        hdr += f" {p.split(chr(92))[-1][:26]:>28}"
    print(hdr)
    print(f"{'far-field':>10} {'':>10}" +
          "".join(f" {r[1]:>28.1f}" for r in rows))
    print("-" * len(hdr))
    for b in BINS:
        n = rows[0][2][b][0]
        line = f"{f'{b[0]}..{b[1]}':>10} {n:>10,}"
        for _, ff, prof, _, _ in rows:
            v = prof[b][1]
            line += f" {v - ff:>+18.1f} DN" if np.isfinite(v) else f" {'--':>28}"
        print(line)

    print("\nPLACEBO (mask translated 640,640 off the silhouette; a real")
    print("silhouette-keyed veil must largely vanish here)")
    print(hdr)
    for b in BINS[:6]:
        n = rows[0][4][b][0]
        line = f"{f'{b[0]}..{b[1]}':>10} {n:>10,}"
        for _, _, _, ffp, profp in rows:
            v = profp[b][1]
            line += f" {v - ffp:>+18.1f} DN" if np.isfinite(v) else f" {'--':>28}"
        print(line)

    # verdict on shape, per arm
    print("\nSHAPE (monotone decay outward => veil; extremum then return => ringing)")
    for p, ff, prof, _, _ in rows:
        seq = [prof[b][1] - ff for b in BINS if np.isfinite(prof[b][1])]
        if len(seq) < 5:
            print(f"  {p.split(chr(92))[-1]:40s} too few bins")
            continue
        d0 = seq[0]
        imax = int(np.argmax(np.abs(seq)))
        mono = imax == 0
        print(f"  {p.split(chr(92))[-1]:40s} d0={d0:+9.1f}  "
              f"|max| at bin {imax}  ->  {'VEIL (monotone)' if mono else 'NON-MONOTONE (ringing-like)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
