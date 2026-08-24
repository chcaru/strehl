"""M113 K7 - THE DISAMBIGUATION. Is the end-to-end dex gain the KERNEL, or is it
the RE-ELECTION the kernel causes?

8.084% of quads elect a different frame between the two arms (K5). The resampler
runs before the focus field (merge_cmd.rs `field_for`), so it is upstream of the
election and of the gate; the binary's own log confirms the gate moved (mean
n_eff 55.321 -> 53.674). Wherever the election moved, the two renders show
DIFFERENT PHOTOGRAPHS, not the same photograph differently interpolated, and any
dex difference there is not attributable to the kernel.

The election map makes the split observable. Score only those tiles where EVERY
quad elected the SAME frame in both arms: there the kernel is genuinely the only
variable. Compare against the tiles where it moved.

`--index-map` is on the plane grid, half linear resolution, one election per 2x2
quad, so tile (y,x,T) in the render maps to (y/2, x/2, T/2) in the map.
"""
import json
import os
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "experiments", "M95-resample", "src"))
import x2_pairs as X  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
R2 = r"C:\dev\strehl-out\M113\render2"


def luma(p):
    a = tifffile.imread(p).astype(np.float32)
    return 0.25 * a[..., 0] + 0.50 * a[..., 1] + 0.25 * a[..., 2]


def main():
    cr = luma(os.path.join(R2, "lin-cr.tif"))
    l3 = luma(os.path.join(R2, "lin-l3.tif"))
    ic = tifffile.imread(os.path.join(R2, "idx-cr.tif")).astype(np.int32)
    il = tifffile.imread(os.path.join(R2, "idx-l3.tif")).astype(np.int32)
    same = ic == il
    h, w = cr.shape
    print(f"renders {cr.shape}   election maps {ic.shape}   "
          f"quads with identical election: {100*same.mean():.3f}%")
    res = {}
    for T in (256, 128, 64):
        q = T // 2
        tiles = [(y, x) for y in range(0, h - T + 1, T) for x in range(0, w - T + 1, T)]
        rows = []
        for y, x in tiles:
            f = float(same[y // 2:y // 2 + q, x // 2:x // 2 + q].mean())
            a = X.band_ratio(cr[y:y + T, x:x + T], 1.0)
            b = X.band_ratio(l3[y:y + T, x:x + T], 1.0)
            rows.append((f, b - a))
        rows = np.array(rows)
        pure = rows[rows[:, 0] == 1.0, 1]
        moved = rows[rows[:, 0] < 0.99, 1]
        allt = rows[:, 1]
        print(f"\n  tile {T}px  ({len(tiles)} tiles over the WHOLE frame)")
        print(f"    {'stratum':38s} {'n':>6s} {'mean gain':>10s} {'sem':>8s}")

        def line(lab, v):
            if v.size < 2:
                print(f"    {lab:38s} {v.size:6d}      -- too few --")
                return None
            s = float(v.std(ddof=1) / np.sqrt(v.size))
            print(f"    {lab:38s} {v.size:6d} {v.mean():+10.4f} {s:8.4f}")
            return dict(n=int(v.size), mean=float(v.mean()), sem=s)

        r = dict(T=T,
                 all=line("all tiles", allt),
                 pure=line("election IDENTICAL in every quad", pure),
                 moved=line("election moved in >1% of quads", moved))
        res[f"T{T}"] = r
        if r["pure"] and r["moved"]:
            d = r["moved"]["mean"] - r["pure"]["mean"]
            se = np.hypot(r["moved"]["sem"], r["pure"]["sem"])
            print(f"    difference (moved - pure) = {d:+.4f} dex, se {se:.4f}, "
                  f"{abs(d)/se:.1f} sigma")
    print("\n  READ: if 'election IDENTICAL' still carries the gain, the KERNEL earns it.")
    print("        if the gain concentrates in 'election moved', the re-election earns it.")
    json.dump(res, open(os.path.join(OUT, "k7_election_split.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k7_election_split.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
