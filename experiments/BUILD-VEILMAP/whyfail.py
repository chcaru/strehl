"""Why does a subject yield no correspondences? Look at the seed and the gates.

Prints, for a few frames of a subject: the whole-frame FFT seed, then every
window's best match with its NCC, its lapratio and whether each gate passed.
A subject that yields nothing is either badly seeded (the true match is
outside the search pad) or legitimately ungateable (nothing is near its own
focus in that window).  These are different failures and the fix differs.
"""
import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import veilcore as vc  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--ks", default="")
    ap.add_argument("--nwin", type=int, default=20)
    ap.add_argument("--half", type=int, default=56)
    ap.add_argument("--pad", type=int, default=90)
    a = ap.parse_args()

    files = vc.frames(a.subject)
    n = len(files)
    ks = ([int(v) for v in a.ks.split(",")] if a.ks
          else [n // 4, n // 2, 3 * n // 4])
    g0 = vc.green_lattice(files[n // 2])
    ref = vc.load_ref(a.subject, g0.shape)
    print(f"{a.subject}: {n} frames, lattice {g0.shape}, ref {ref.shape}")
    wins = vc.pick_windows(ref, a.nwin, a.half)
    ff = vc.DriftFitter(ref)
    open_tr = vc.TrackFitter(ref, half=a.half, pad=a.pad, minncc=-1.0,
                             lap_lo=0.0, lap_hi=1e9)
    gated = vc.TrackFitter(ref, half=a.half, pad=a.pad)

    for k in ks:
        g = vc.green_lattice(files[k])
        r = ff.fit(g)
        rows = open_tr.correspond(g, wins, (r["a"], r["ty"], r["tx"]))
        gr = gated.correspond(g, wins, (r["a"], r["ty"], r["tx"]))
        lr = np.array([t[6] for t in rows]) if rows else np.zeros(0)
        nc = np.array([t[4] for t in rows]) if rows else np.zeros(0)
        print(f"\nf{k:03d} seed a={r['a']:.5f} ty={r['ty']:.1f} "
              f"tx={r['tx']:.1f} ncc={r['ncc']:.3f}")
        print(f"  ungated {len(rows)} -> gated {len(gr)}")
        if len(rows):
            print(f"  ncc      min/med/max {nc.min():.3f} {np.median(nc):.3f}"
                  f" {nc.max():.3f}  (gate >= {gated.minncc})")
            print(f"  lapratio min/med/max {lr.min():.3f} {np.median(lr):.3f}"
                  f" {lr.max():.3f}  (gate {gated.lap_lo}..{gated.lap_hi})")
            print(f"  rejected by ncc {int((nc < gated.minncc).sum())}, "
                  f"by lapratio {int(((lr < gated.lap_lo) | (lr > gated.lap_hi)).sum())}")
            d = np.array([np.hypot(t[2] - (r['a'] * t[0] + r['ty']),
                                   t[3] - (r['a'] * t[1] + r['tx']))
                          for t in rows])
            print(f"  |q - seed| lattice px  med {np.median(d):.1f} "
                  f"max {d.max():.1f}  (pad {a.pad}: "
                  f"{int((d >= a.pad - 1).sum())} pinned at the search edge)")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
