"""Look at what the matcher matched. Contact sheet of template vs match.

V-VEILCLAW's first attempt failed because nobody opened the window it was
measuring. Same rule here: every correspondence that feeds the drift model gets
dumped as a pair -- master template on the left, the patch it locked onto on
the right -- labelled with NCC and with the residual against the fitted
similarity.
"""
import argparse
import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import veilcore as vc  # noqa: E402

RAWROOT = pathlib.Path(r"D:\personal\macro")
MASTERS = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")


def grade(a):
    lo, hi = np.percentile(a, [1.0, 99.0])
    x = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
    return (np.power(x, 1 / 2.2) * 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="bee-3-cpl")
    ap.add_argument("--k", type=int, default=150)
    ap.add_argument("--half", type=int, default=56)
    ap.add_argument("--pad", type=int, default=90)
    ap.add_argument("--nwin", type=int, default=35)
    ap.add_argument("--sigmas", default="3")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    m = tifffile.imread(str(MASTERS / f"{a.subject}.tiff"))
    ref = vc.block_mean_down(m[:, :, 1].astype(np.float32), 2)
    del m
    files = sorted((RAWROOT / a.subject).glob("*.ARW"))
    g = vc.green_lattice(files[a.k])

    gf = vc.DriftFitter(ref).fit(g)
    seed = (gf["a"], gf["ty"], gf["tx"])
    wins = vc.pick_windows(ref, a.nwin, a.half)
    tr = vc.TrackFitter(ref, half=a.half, pad=a.pad,
                        sigmas=tuple(float(s) for s in a.sigmas.split(",")),
                        minncc=0.0)
    rows = tr.correspond(g, wins, seed)
    sol = vc.TrackFitter.solve(rows) or dict(a=seed[0], ty=seed[1], tx=seed[2], n_in=0, n_all=len(rows), rms=float("nan"))
    print(f"f{a.k} seed a={seed[0]:.5f}  fit a={sol['a']:.5f} "
          f"n_in={sol['n_in']}/{sol['n_all']} rms={sol['rms']:.2f}")

    h = a.half
    tile = 2 * h
    cols = 6
    rowsn = (len(rows) + cols - 1) // cols
    img = np.full((rowsn * (tile + 16), cols * (2 * tile + 6)), 255, np.uint8)
    for i, (y, x, qy, qx, mx, edge, extra) in enumerate(rows):
        t = grade(ref[y - h:y + h, x - h:x + h])
        yy = int(np.clip(qy, h, g.shape[0] - h))
        xx = int(np.clip(qx, h, g.shape[1] - h))
        c = grade(g[yy - h:yy + h, xx - h:xx + h])
        py, px = vc.map_point(y, x, sol["a"], sol["ty"], sol["tx"])
        res = float(np.hypot(qy - py, qx - px))
        r, cc = divmod(i, cols)
        oy, ox = r * (tile + 16) + 16, cc * (2 * tile + 6)
        img[oy:oy + tile, ox:ox + tile] = t
        img[oy:oy + tile, ox + tile + 3:ox + 2 * tile + 3] = c
        rows[i] = (y, x, qy, qx, mx, edge, res)
    im = Image.fromarray(img).convert("RGB")
    d = ImageDraw.Draw(im)
    for i, t in enumerate(rows):
        r, cc = divmod(i, cols)
        oy, ox = r * (tile + 16), cc * (2 * tile + 6)
        col = (0, 140, 0) if t[6] < 4 else ((200, 120, 0) if t[6] < 16
                                            else (210, 0, 0))
        d.text((ox + 2, oy + 2),
               f"({t[0]},{t[1]}) ncc{t[4]:.2f} r{t[6]:.0f}"
               + (" RAIL" if t[5] else ""), fill=col)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    im.save(a.out)
    print(f"wrote {a.out}")
    good = sum(1 for t in rows if t[6] < 4)
    print(f"green (resid<4 lattice px): {good}/{len(rows)}")


if __name__ == "__main__":
    main()
