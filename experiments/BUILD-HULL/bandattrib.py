"""Attribute the TOTAL excursion magnitude by band.

The per-band table gives rates and means, but rate alone is misleading: the fine
bands violate OFTEN in green while carrying almost no DN. The question that
decides the mechanism is where the MAGNITUDE lives, so this sums |violation| in
DN per band and reports each band's share of the whole.

It also states each band's own scale (hull span) so a band cannot look innocent
merely because its coefficients are small.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from bhull2 import BBOX, CHANNELS, bands_of, load16

GUARD = 1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="warp/cache")
    ap.add_argument("--dir", default="warp")
    ap.add_argument("--levels", type=int, default=7)
    ap.add_argument("--arms", default="W-pyramid,W-uniform,W-e1s1,W-estimator")
    a = ap.parse_args()
    cache, mdir = Path(a.cache), Path(a.dir)

    lo = np.load(cache / "lo.npy").astype(np.float32)
    hi = np.load(cache / "hi.npy").astype(np.float32)

    for arm in a.arms.split(","):
        p = mdir / f"merge-{arm}.tiff"
        if not p.exists():
            print(f"\n=== {arm}: MISSING, not scored ===")
            continue
        img = load16(p)
        m = img.astype(np.float32)
        wv = np.where(m < lo, m - lo, np.where(m > hi, m - hi, 0.0))
        whole_abs = float(np.abs(wv).sum())
        whole_net = float(wv.sum())

        print(f"\n=== {arm} :: where does the excursion MAGNITUDE live? ===")
        print(f"  whole-image  sum|viol| = {whole_abs:,.0f} DN   net = {whole_net:,.0f} DN")
        print(f"  {'band':<14} {'sum|viol| DN':>16} {'share':>8} {'net DN':>16} "
              f"{'mean span':>10} {'viol px':>10}")

        mb = bands_of(img, a.levels)
        tot = []
        for b in range(a.levels + 1):
            blo = np.load(cache / f"blo{b}.npy")
            bhi = np.load(cache / f"bhi{b}.npy")
            vv = np.where(mb[b] < blo, mb[b] - blo,
                          np.where(mb[b] > bhi, mb[b] - bhi, 0.0))
            bad = np.abs(vv) > GUARD
            tot.append((float(np.abs(vv[bad]).sum()), float(vv[bad].sum()),
                        float((bhi - blo).mean()), int(np.count_nonzero(bad))))
        grand = sum(t[0] for t in tot)
        for b in range(a.levels + 1):
            nm = "base(coarse)" if b == a.levels else f"detail{b}" + ("=finest" if b == 0 else "")
            s, net, sp, n = tot[b]
            print(f"  {nm:<14} {s:>16,.0f} {100.0 * s / max(grand, 1e-9):>7.3f}% "
                  f"{net:>16,.0f} {sp:>10.1f} {n:>10,}")
        print(f"  {'SUM OF BANDS':<14} {grand:>16,.0f} {100.0:>7.3f}%")
        # The bands are a linear decomposition but |violation| is not linear, so
        # the band sum need not equal the whole-image sum. Stating the ratio
        # keeps that honest rather than implying an identity that does not hold.
        print(f"  band-sum / whole-image ratio = {grand / max(whole_abs, 1e-9):.3f} "
              f"(not expected to be 1: |.| is not linear)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
