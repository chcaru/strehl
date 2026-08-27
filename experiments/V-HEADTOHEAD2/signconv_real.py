"""signconv_real.py -- prove the sign repair on the ACTUAL comparator pair.

signconv.py settled the convention on synthetic self-crops, where the true
displacement is known exactly because the moving crop is the same image taken
at a known offset.  That is the right way to establish a convention, but it is
not the data the published comparator numbers were computed on.

The repair moves published figures -- notably grade-113's 0.25-0.30 band, where
strehl-under-the-fitted-map vs Zerene went from 0.037147/0.037138 (a 0.02%
match) to 0.038106/0.036095 (5.6%).  A number that moves because of a one-line
sign change must not be accepted on the strength of a synthetic test.  So:
measure alignment quality directly on the real strehl/Zerene and strehl/fork
pairs, both ways, and let the data say which crop is aligned.

Usage:  python signconv_real.py [113|cb]
"""
import sys

import numpy as np

import h2
import h2h2
import rois

T = h2h2.T
PAD = h2h2.PAD


def resid(a, b):
    x = a - a.mean()
    y = b - b.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum()) + 1e-30
    return float((x * y).sum() / d)


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "113"
    cfg = h2h2.COMP[subj]
    S = cfg["scale"]
    TC = int(round(T / S))
    F = h2h2.load(f"{subj}-full-g1")
    C = h2h2.Comp(cfg)
    print("=" * 78)
    print(f"SIGN CONVENTION ON REAL DATA: {subj}  strehl vs {cfg['label']}")
    print("=" * 78)

    detail, _f, _c = rois.census(F, t=T, pad=PAD, flat_frac=0.10, verbose=False)
    rng = np.random.default_rng(7)
    probe = [detail[i] for i in rng.permutation(len(detail))[:24]]

    d = 4
    plus, minus, n = [], [], 0
    for (y, x) in probe:
        cs, _ = F.crop(y, x, T)
        cc, _ = C.crop(int(round(y / S)), int(round(x / S)), TC)
        if cs is None or cc is None:
            continue
        ta, tb = T // d * d, TC // d * d
        a = cs[:ta, :ta].reshape(ta // d, d, ta // d, d).mean((1, 3))
        b2 = cc[:tb, :tb].reshape(tb // d, d, tb // d, d).mean((1, 3))
        m = min(a.shape[0], b2.shape[0])
        gy, gx, pk = h2.integer_shift(a[:m, :m], b2[:m, :m], maxshift=6)
        gy, gx = gy * d, gx * d
        # both candidate re-crops of the COMPARATOR, in comparator pixels
        for sgn, acc in ((+1, plus), (-1, minus)):
            cc2, _ = C.crop(int(round(y / S)) + sgn * gy,
                            int(round(x / S)) + sgn * gx, TC)
            if cc2 is None:
                continue
            tb2 = TC // d * d
            b3 = cc2[:tb2, :tb2].reshape(tb2 // d, d, tb2 // d, d).mean((1, 3))
            mm = min(a.shape[0], b3.shape[0])
            acc.append(resid(a[:mm, :mm], b3[:mm, :mm]))
        n += 1

    mp, mm_ = float(np.mean(plus)), float(np.mean(minus))
    print(f"  {n} probe ROIs, coarse block means (integer, no resampling)")
    print(f"  re-crop comparator at ORIGIN + returned shift : {mp:.6f}")
    print(f"  re-crop comparator at ORIGIN - returned shift : {mm_:.6f}")
    print(f"  unregistered (origin as-is) baseline          : ", end="")
    base = []
    for (y, x) in probe:
        cs, _ = F.crop(y, x, T)
        cc, _ = C.crop(int(round(y / S)), int(round(x / S)), TC)
        if cs is None or cc is None:
            continue
        ta, tb = T // d * d, TC // d * d
        a = cs[:ta, :ta].reshape(ta // d, d, ta // d, d).mean((1, 3))
        b2 = cc[:tb, :tb].reshape(tb // d, d, tb // d, d).mean((1, 3))
        m = min(a.shape[0], b2.shape[0])
        base.append(resid(a[:m, :m], b2[:m, :m]))
    mb = float(np.mean(base))
    print(f"{mb:.6f}")

    win = "+" if mp > mm_ else "-"
    print(f"\n  the aligned crop is ORIGIN {win} returned shift "
          f"({max(mp, mm_):.6f} vs {min(mp, mm_):.6f})")
    # The arm that makes this a test rather than a comparison: registration
    # must BEAT doing nothing. If neither candidate improves on the
    # unregistered baseline, the probe is not measuring alignment at all and
    # neither column may be quoted.
    ok = max(mp, mm_) > mb
    print(f"  registration beats no registration: {max(mp, mm_):.6f} > "
          f"{mb:.6f}  [{'OK' if ok else 'PROBE IS NOT MEASURING ALIGNMENT'}]")
    print(f"  and the WRONG sign is worse than doing nothing: "
          f"{min(mp, mm_):.6f} < {mb:.6f}  "
          f"[{'as expected' if min(mp, mm_) < mb else 'UNEXPECTED'}]")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
