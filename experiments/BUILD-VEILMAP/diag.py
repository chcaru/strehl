"""Open the intermediate: what do the individual correspondences say?

Prints, for one frame, every window's matched displacement, its NCC, whether it
railed against the edge of the search box, and the residual of the similarity
fitted through them. A similarity that cannot describe the field will show up
here as structure in the residual, not as a bad scalar.
"""
import argparse
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import veilcore as vc  # noqa: E402

RAWROOT = pathlib.Path(r"D:\personal\macro")
MASTERS = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="bee-3-cpl")
    ap.add_argument("--k", type=int, default=150)
    ap.add_argument("--half", type=int, default=56)
    ap.add_argument("--pad", type=int, default=140)
    ap.add_argument("--nwin", type=int, default=35)
    ap.add_argument("--minncc", type=float, default=0.0)
    a = ap.parse_args()

    m = tifffile.imread(str(MASTERS / f"{a.subject}.tiff"))
    ref = vc.block_mean_down(m[:, :, 1].astype(np.float32), 2)
    del m
    files = sorted((RAWROOT / a.subject).glob("*.ARW"))
    g = vc.green_lattice(files[a.k])

    gf = vc.DriftFitter(ref).fit(g)
    print(f"{a.subject} f{a.k}: global FFT seed a={gf['a']:.5f} "
          f"ty={gf['ty']:.1f} tx={gf['tx']:.1f} ncc={gf['ncc']:.3f}")
    seed = (gf["a"], gf["ty"], gf["tx"])

    wins = vc.pick_windows(ref, a.nwin, a.half)
    tr = vc.TrackFitter(ref, half=a.half, pad=a.pad, minncc=a.minncc)
    rows = tr.correspond(g, wins, seed)
    sol = vc.TrackFitter.solve(rows)
    print(f"similarity through {sol['n_in']}/{sol['n_all']}: a={sol['a']:.5f} "
          f"ty={sol['ty']:.1f} tx={sol['tx']:.1f} rms={sol['rms']:.2f} "
          f"med={sol['med']:.2f} (lattice px)")

    cy, cx = ref.shape[0] / 2, ref.shape[1] / 2
    print(f"\n{'y':>6}{'x':>6}{'r':>7}{'ncc':>7}{'rail':>5}"
          f"{'dy_meas':>9}{'dx_meas':>9}{'dy_fit':>8}{'dx_fit':>8}{'resid':>8}")
    out = []
    for (y, x, qy, qx, mx, edge) in rows:
        py, px = vc.map_point(y, x, sol["a"], sol["ty"], sol["tx"])
        r = float(np.hypot(y - cy, x - cx))
        res = float(np.hypot(qy - py, qx - px))
        out.append((r, y, x, mx, edge, qy - y, qx - x, py - y, px - x, res))
    for t in sorted(out):
        print(f"{t[1]:>6}{t[2]:>6}{t[0]:7.0f}{t[3]:7.3f}"
              f"{'Y' if t[4] else '.':>5}{t[5]:9.1f}{t[6]:9.1f}"
              f"{t[7]:8.1f}{t[8]:8.1f}{t[9]:8.1f}")
    hi = [t for t in out if t[3] > 0.6 and not t[4]]
    if hi:
        print(f"\nwindows with ncc>0.6 and no rail: {len(hi)}  "
              f"median resid {np.median([t[9] for t in hi]):.2f} lattice px")
        sol2 = vc.TrackFitter.solve(
            [(t[1], t[2], t[1] + t[5], t[2] + t[6], t[3], t[4]) for t in hi])
        print(f"refit on those only: a={sol2['a']:.5f} ty={sol2['ty']:.1f} "
              f"tx={sol2['tx']:.1f} rms={sol2['rms']:.2f} "
              f"n={sol2['n_in']}/{sol2['n_all']}")


if __name__ == "__main__":
    main()
