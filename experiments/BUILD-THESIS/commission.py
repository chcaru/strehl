"""Commission the three detail statistics before letting any of them vote.

This project has shipped a self-test that divided by the quantity it then
checked and returned GREEN on a wrong kernel. So nothing here is assumed.

Every statistic faces four trials on every tile:

  PLANT-BLUR    a Gaussian-blurred copy of a real tile. The unblurred original
                is known-sharper by construction, so the statistic MUST be
                higher on it. This is ORCH's control, applied to all three.

  PLANT-SYNTH   a synthetic radial chirp with ground-truth blur. Known sharp
                vs known soft, no subject property involved at all.

  NULL-GAUSS    the same tile plus white Gaussian noise. Noise is not detail.
                The statistic MUST NOT rise. `argmax-baseline` ships 1.253x the
                noise of one frame and the merge 0.890x, so a statistic that
                rewards noise would hand the win to selection for free.

  NULL-IMPULSE  the same tile with 0.05% of pixels replaced by impulses --
                the measured index-speckle rate of the selection arm on
                flat-on-ruler-cpl. Speckle is a DEFECT of the selection arm.
                A statistic that scores it as detail is scoring the defect.

A statistic that fails PLANT is inert. A statistic that fails NULL is worse
than inert: it is an argument for whichever arm is noisiest.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from stats import STATS  # noqa: E402

RNG = np.random.default_rng(20260826)
TILE = 800
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS")


def synth_chirp(n=TILE, blur=0.0):
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    cx = cy = n / 2
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    # frequency sweeps 0.02 -> 0.40 cyc/px with radius
    ph = 2 * np.pi * (0.02 * r + (0.40 - 0.02) / (2 * n / 2) * r * r)
    a = 2000.0 + 1200.0 * np.sin(ph)
    if blur > 0:
        a = gaussian_filter(a, blur)
    return a


def gauss_noise(t, frac):
    return t + RNG.normal(0.0, frac * t.std(), t.shape)


def impulse_noise(t, rate=0.0005, amp=0.05):
    out = t.copy()
    n = out.size
    k = max(int(round(rate * n)), 1)
    idx = RNG.choice(n, size=k, replace=False)
    span = float(t.max() - t.min())
    sign = RNG.choice([-1.0, 1.0], size=k)
    out.ravel()[idx] += sign * amp * span
    return out


def load_tiles(paths, per_file=2):
    tiles = []
    for p in paths:
        img = tifffile.imread(str(p))
        assert img.dtype == np.uint16, f"{p} is {img.dtype}, expected uint16"
        g = img[:, :, 1].astype(np.float64)
        _, y, x = best_tile_multi(g, TILE, per_file)
        for (yy, xx) in _:
            tiles.append((f"{p.parent.name}/{p.stem}@{xx},{yy}", g[yy:yy + TILE, xx:xx + TILE]))
    return tiles


def best_tile_multi(g, tile, k, margin=64):
    h, w = g.shape
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
    step = tile
    cands = []
    for y in range(margin, max(h - tile - margin, margin + 1), step):
        for x in range(margin, max(w - tile - margin, margin + 1), step):
            cands.append((float(lap[y:y + tile, x:x + tile].mean()), y, x))
    cands.sort(reverse=True)
    return [(y, x) for _, y, x in cands[:k]], 0, 0


def main():
    srcs = [pathlib.Path(p) for p in sys.argv[1:]]
    if not srcs:
        print(__doc__)
        return 2
    tiles = load_tiles(srcs)
    tiles.append(("synth-chirp-sharp", synth_chirp(blur=0.0)))

    rows = []
    fails = []
    for name, t in tiles:
        base = {k: fn(t) for k, fn in STATS.items()}
        trials = {
            "PLANT-BLUR-0.8": gaussian_filter(t, 0.8),
            "PLANT-BLUR-1.5": gaussian_filter(t, 1.5),
            "NULL-GAUSS-1pct": gauss_noise(t, 0.01),
            "NULL-GAUSS-5pct": gauss_noise(t, 0.05),
            "NULL-GAUSS-15pct": gauss_noise(t, 0.15),
            "NULL-IMPULSE-0.05pct": impulse_noise(t),
        }
        for tn, tv in trials.items():
            got = {k: fn(tv) for k, fn in STATS.items()}
            for k in STATS:
                b, g = base[k], got[k]
                ratio = g / b if b else float("nan")
                if tn.startswith("PLANT"):
                    ok = ratio < 0.98    # blurred must score CLEARLY LOWER
                else:
                    ok = ratio <= 1.02   # noise must not inflate it materially
                rows.append(dict(tile=name, trial=tn, stat=k, base=b, got=g,
                                 ratio=ratio, pass_=bool(ok)))
                if not ok:
                    fails.append((name, tn, k, b, g, ratio))

    # synthetic ground truth: known-sharp must beat known-soft
    sharp, soft = synth_chirp(blur=0.0), synth_chirp(blur=1.2)
    for k, fn in STATS.items():
        a, b = fn(sharp), fn(soft)
        ok = (b / a) < 0.98
        rows.append(dict(tile="synth-chirp", trial="PLANT-SYNTH-groundtruth", stat=k,
                         base=a, got=b, ratio=b / a, pass_=bool(ok)))
        if not ok:
            fails.append(("synth-chirp", "PLANT-SYNTH-groundtruth", k, a, b, b / a))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "commission.json").write_text(json.dumps(rows, indent=1), encoding="utf8")

    print(f"{'trial':<24}{'stat':<10}{'n':>4}{'worst ratio':>13}  verdict")
    by = {}
    for r in rows:
        by.setdefault((r["trial"], r["stat"]), []).append(r)
    for (tn, k), rs in sorted(by.items()):
        bad = [r for r in rs if not r["pass_"]]
        if tn.startswith("PLANT"):
            worst = max(r["ratio"] for r in rs)     # want << 1
        else:
            worst = max(r["ratio"] for r in rs)     # want <= 1
        v = "PASS" if not bad else f"FAIL ({len(bad)}/{len(rs)})"
        print(f"{tn:<24}{k:<10}{len(rs):>4}{worst:>13.4f}  {v}")

    print()
    if fails:
        print(f"COMMISSIONING FAILED on {len(fails)} trial(s):")
        for f in fails[:20]:
            print(f"   {f[0]:<40} {f[1]:<22} {f[2]:<9} {f[3]:.5g} -> {f[4]:.5g}  ({f[5]:.4f}x)")
        return 1
    print(f"COMMISSIONING PASSED: {len(rows)} trials, {len(tiles)} tiles.")
    print("Every statistic fell on blur and none rose on noise or on speckle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
