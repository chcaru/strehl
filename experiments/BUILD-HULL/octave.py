"""Octave-resolved hull test, matched to the merge's OWN band geometry.

WHY THIS REPLACES THE FIRST DECOMPOSITION
    My first pass used a Laplacian held at full resolution (no decimation). It is
    linear, so the theorem still applied and the numbers were real -- but seven
    repeated 5-tap blurs only reach an effective sigma of about 2.6 px, so its
    "base" meant "everything coarser than ~2.6 px", NOT the merge's coarsest
    octave. Reporting that as a per-band result would have implied a
    correspondence with `pyramid.rs`'s levels that did not exist. So this builds
    a properly DECIMATED pyramid whose geometry matches what the merge logs:

        "7 Laplacian levels + 1 base, coarsest 28 x 19"

    3520x2344 -> 1760x1172 -> 880x586 -> 440x293 -> 220x147 -> 110x74
                 -> 55x37 -> 28x19.  Seven decimations, coarsest 28x19. Matches.

    Each level is hull-tested AT ITS OWN RESOLUTION, which is also how the merge
    selects. The theorem is unaffected: blur, decimate, upsample and subtract are
    all linear, so a convex combination with weights SHARED across bands stays
    inside the hull of every band. Any per-octave violation therefore proves the
    weights are not shared.

    This is still my operator, not theirs. The claim is about which OCTAVE the
    excursion occupies, not about their array indices.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from bhull2 import CHANNELS, load16

GUARD = 1.0
K = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float32)
K /= K.sum()


def blur(a):
    out = a
    for ax in (0, 1):
        pad = [(0, 0)] * a.ndim
        pad[ax] = (2, 2)
        p = np.pad(out, pad, mode="reflect")
        acc = np.zeros_like(out)
        sl = [slice(None)] * a.ndim
        for i, w in enumerate(K):
            sl[ax] = slice(i, i + out.shape[ax])
            acc += w * p[tuple(sl)]
        out = acc
    return out


def down(a):
    return blur(a)[::2, ::2]


def up(a, shape):
    h, w = shape[:2]
    o = np.zeros((h, w) + a.shape[2:], dtype=np.float32)
    o[::2, ::2] = a
    return 4.0 * blur(o)


def pyr(a, levels):
    """Decimated Laplacian pyramid: `levels` detail bands + 1 base."""
    cur = a.astype(np.float32)
    out = []
    for _ in range(levels):
        d = down(cur)
        out.append(cur - up(d, cur.shape))
        cur = d
    out.append(cur)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="warp/frames")
    ap.add_argument("--dir", default="warp")
    ap.add_argument("--n", type=int, default=205)
    ap.add_argument("--levels", type=int, default=7)
    ap.add_argument("--arms", default="W-pyramid,W-uniform,W-e1s1,W-bands1,W-estimator")
    ap.add_argument("--cache", default="warp/oct")
    a = ap.parse_args()

    fdir, mdir, cache = Path(a.frames), Path(a.dir), Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)

    if not (cache / f"olo{a.levels}.npy").exists():
        present = sorted(fdir.glob("f*.tiff"))
        missing = [k for k in range(a.n) if not (fdir / f"f{k:04d}.tiff").exists()]
        print(f"  frames requested {a.n} | present {len(present)} | missing {len(missing)}")
        assert not missing, f"refusing to fold, missing {missing[:8]}"
        lo: list = [None] * (a.levels + 1)
        hi: list = [None] * (a.levels + 1)
        for k in range(a.n):
            for b, v in enumerate(pyr(load16(fdir / f"f{k:04d}.tiff"), a.levels)):
                if lo[b] is None:
                    lo[b], hi[b] = v.copy(), v.copy()
                else:
                    np.minimum(lo[b], v, out=lo[b])
                    np.maximum(hi[b], v, out=hi[b])
            if (k + 1) % 25 == 0:
                print(f"    octave-folded {k + 1}/{a.n}", flush=True)
        for b in range(a.levels + 1):
            np.save(cache / f"olo{b}.npy", lo[b])
            np.save(cache / f"ohi{b}.npy", hi[b])
        print(f"  wrote {a.levels + 1} octave hulls to {cache}")

    los = [np.load(cache / f"olo{b}.npy") for b in range(a.levels + 1)]
    his = [np.load(cache / f"ohi{b}.npy") for b in range(a.levels + 1)]

    print("\n  octave geometry (must match the merge's '7 levels + base, coarsest 28 x 19')")
    for b in range(a.levels + 1):
        nm = "base" if b == a.levels else f"detail{b}"
        print(f"    {nm:<9} {los[b].shape[1]:>5} x {los[b].shape[0]:<5} "
              f"mean span {float((his[b] - los[b]).mean()):>9.1f} DN")

    requested = a.arms.split(",")
    scored, missing = [], []
    for arm in requested:
        (scored if (mdir / f"merge-{arm}.tiff").exists() else missing).append(arm)
    print(f"\n  arms requested {len(requested)} = scored {len(scored)} + missing {len(missing)}")
    assert len(scored) + len(missing) == len(requested), "arm partition does not sum"
    if missing:
        print(f"    MISSING (not scored): {missing}")

    for arm in scored:
        img = load16(mdir / f"merge-{arm}.tiff")
        mb = pyr(img, a.levels)
        print(f"\n=== {arm} :: per-OCTAVE hull violation ===")
        print(f"  {'octave':<10} {'ch':<3} {'samples':>10} {'inside':>10} {'below':>9} "
              f"{'above':>9} {'rate':>9} {'sum|v| DN':>14} {'share':>8} {'worst/span':>10}")
        rows = []
        for b in range(a.levels + 1):
            sp = his[b] - los[b]
            vv = np.where(mb[b] < los[b], mb[b] - los[b],
                          np.where(mb[b] > his[b], mb[b] - his[b], 0.0))
            rows.append((b, sp, vv))
        grand = sum(float(np.abs(v[np.abs(v) > GUARD]).sum()) for _, _, v in rows)
        for b, sp, vv in rows:
            nm = "base" if b == a.levels else f"detail{b}"
            for ci, cn in enumerate(CHANNELS):
                v, s = vv[..., ci], sp[..., ci]
                bad = np.abs(v) > GUARD
                tot = int(v.size)
                blw = int(np.count_nonzero(v < -GUARD))
                abv = int(np.count_nonzero(v > GUARD))
                ins = tot - int(np.count_nonzero(bad)) - int(
                    np.count_nonzero((np.abs(v) > 0) & (np.abs(v) <= GUARD)))
                gd = tot - ins - blw - abv
                assert ins + gd + blw + abv == tot, "octave partition does not sum"
                sm = float(np.abs(v[bad]).sum())
                us = bad & (s >= 1.0)
                wr = float((np.abs(v[us]) / s[us]).max()) if us.any() else 0.0
                print(f"  {nm:<10} {cn:<3} {tot:>10,} {ins:>10,} {blw:>9,} {abv:>9,} "
                      f"{100.0 * (blw + abv) / tot:>8.4f}% {sm:>14,.0f} "
                      f"{100.0 * sm / max(grand, 1e-9):>7.3f}% {wr:>10.3f}")
        # Per-octave share across all channels, the line that decides the mechanism.
        print(f"  {'--- octave shares of total |violation| ---':<44}")
        for b, sp, vv in rows:
            nm = "base" if b == a.levels else f"detail{b}"
            sm = float(np.abs(vv[np.abs(vv) > GUARD]).sum())
            net = float(vv[np.abs(vv) > GUARD].sum())
            print(f"  {nm:<10} share {100.0 * sm / max(grand, 1e-9):>7.3f}%   "
                  f"sum|v| {sm:>15,.0f} DN   net {net:>15,.0f} DN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
