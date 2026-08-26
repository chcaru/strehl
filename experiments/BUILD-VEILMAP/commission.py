"""Commission the drift fitter before it is allowed to produce a number.

Three tests, in the order that matters:

  NULL   the reference against itself must return a=1, t=0. On its own this is
         worthless -- a disconnected probe returns the same thing -- which is
         why the plant is mandatory (ORCH drift.py, discipline 598).
  PLANT  a known (a, ty, tx) applied to the reference must come back, and a
         planted BLOCK must land where the recovered model says it lands. The
         second half is the part that catches a sign error, because a sign
         error survives a scalar plant on a centred image.
  REAL   the per-frame scale recovered on bee-3-cpl against the master must
         agree with ORCH-drift-check/drift-v2.json, which was measured by a
         different method (frame-0 reference, ladder of resampled targets, no
         master involved). Two implementations, one number, or neither counts.
"""
import argparse
import json
import pathlib
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import veilcore as vc  # noqa: E402

RAWROOT = pathlib.Path(r"D:\personal\macro")
MASTERS = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")
ORCHDRIFT = (pathlib.Path(__file__).resolve().parents[1]
             / "ORCH-drift-check" / "drift-v2.json")


def master_ref(subject):
    m = tifffile.imread(str(MASTERS / f"{subject}.tiff"))
    assert m.dtype == np.uint16, f"master is {m.dtype}, corpus requires uint16"
    g = m[:, :, 1].astype(np.float32)
    return vc.block_mean_down(g, 2)


def warp_known(img, a, ty, tx):
    """Synthesise a frame in which ref point p appears at a*p + t."""
    m = np.array([[a, 0.0, tx], [0.0, a, ty]], np.float32)
    return cv2.warpAffine(img, m, (img.shape[1], img.shape[0]),
                          flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REFLECT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="bee-3-cpl")
    ap.add_argument("--frames", type=int, default=15,
                    help="how many real frames to cross-check")
    a = ap.parse_args()

    ref = master_ref(a.subject)
    print(f"reference  = master green / 2  shape {ref.shape}  "
          f"(subject {a.subject})")
    fit = vc.DriftFitter(ref)

    print("\n--- NULL " + "-" * 62)
    r = fit.fit(ref)
    print(f"ref vs itself       a={r['a']:.5f}  ty={r['ty']:+8.2f}  "
          f"tx={r['tx']:+8.2f}  ncc={r['ncc']:.4f}")
    ok_null = abs(r["a"] - 1) < 2e-3 and abs(r["ty"]) < 2 and abs(r["tx"]) < 2
    print("NULL: " + ("PASS" if ok_null else "FAIL"))

    print("\n--- PLANT " + "-" * 61)
    ok_plant = True
    for (pa, pty, ptx) in ((0.9400, 40.0, -25.0), (1.0300, -60.0, 15.0),
                           (0.8700, 0.0, 0.0)):
        syn = warp_known(ref, pa, pty, ptx)
        r = fit.fit(syn)
        # where does a known reference point actually land?
        py, px = 900.0, 1400.0
        ty_true, tx_true = vc.map_point(py, px, pa, pty, ptx)
        ty_est, tx_est = vc.map_point(py, px, r["a"], r["ty"], r["tx"])
        err = float(np.hypot(ty_true - ty_est, tx_true - tx_est))
        print(f"plant a={pa:.4f} t=({pty:+.1f},{ptx:+.1f}) -> "
              f"a={r['a']:.5f} t=({r['ty']:+8.2f},{r['tx']:+8.2f})  "
              f"da={r['a'] - pa:+.5f}  point err {err:6.2f} lattice px "
              f"({2 * err:6.2f} master px)  ncc={r['ncc']:.4f}")
        ok_plant &= err < 3.0
    print("PLANT: " + ("PASS" if ok_plant else "FAIL"))

    print("\n--- REAL (cross-check vs ORCH-drift-check/drift-v2.json) " + "-" * 14)
    files = sorted((RAWROOT / a.subject).glob("*.ARW"))
    orch = json.loads(ORCHDRIFT.read_text(encoding="utf-8"))
    orows = {int(x["k"]): float(x["scale"]) for x in orch["rows"]}
    ks = [0] + sorted(orows)[:a.frames]
    got = {}
    seed = None
    for k in ks:
        g = vc.green_lattice(files[k])
        r = fit.fit(g, seed=seed)
        seed = r["a"]
        got[k] = r
        print(f"f{k:03d}  a={r['a']:.5f}  ty={r['ty']:+8.2f}  "
              f"tx={r['tx']:+8.2f}  ncc={r['ncc']:.4f}")
    a0 = got[0]["a"]
    print(f"\n{'k':>5}{'ours a/a0':>12}{'ORCH scale':>12}{'diff':>10}"
          f"{'corner px (master)':>20}")
    diffs = []
    rc = 0.5 * float(np.hypot(ref.shape[0], ref.shape[1])) * 2.0
    for k in sorted(orows):
        if k not in got:
            continue
        ours = got[k]["a"] / a0
        d = ours - orows[k]
        diffs.append(abs(d))
        print(f"{k:>5}{ours:12.5f}{orows[k]:12.5f}{d:+10.5f}"
              f"{abs(d) * rc:20.1f}")
    ok_real = bool(diffs) and max(diffs) < 0.004
    print(f"max |diff| = {max(diffs):.5f}  "
          f"({max(diffs) * rc:.1f} master px at the corner)")
    print("REAL: " + ("PASS" if ok_real else "FAIL"))

    print("\nCOMMISSION: " + ("PASS" if (ok_null and ok_plant and ok_real)
                              else "FAIL"))
    return 0 if (ok_null and ok_plant and ok_real) else 1


if __name__ == "__main__":
    raise SystemExit(main())
