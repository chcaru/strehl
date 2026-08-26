"""Is the multi-peak map organised by RADIUS, or by the subject?

This is the drift control that does not depend on knowing the tracker's error
magnitude, and it is the one to believe.

Magnification breathing is a scale about the optical centre. Its differential
shift is therefore exactly zero at the centre and grows linearly with radius --
the corpus records >150 px of variation within one frame, "growing with
distance from the optical centre".  So bimodality manufactured by drift MUST
be radially organised: absent in the middle, saturating at the corners.  The
synthetic plant shows precisely that, and shows it as a picture.

Bimodality caused by occlusion has no reason to care where the optical centre
is.  It sits where one depth layer crosses in front of another, which is a
fact about the subject.

So: bin blocks by radius, report the MULTI fraction per bin, and report the
slope.  A real subject whose radial profile is flat -- or which peaks somewhere
other than the corners -- is not measuring breathing, whatever the absolute
fraction is and whatever the tracker's residual is.
"""
import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from classify import MULTI, peaks_topo, run_grid  # noqa: E402


def profile(cls, ys, xs, b, shape, nbin=6):
    cy, cx = shape[0] / 2.0, shape[1] / 2.0
    yy = (ys[:, None] + b / 2.0 - cy)
    xx = (xs[None, :] + b / 2.0 - cx)
    r = np.hypot(np.broadcast_to(yy, cls.shape), np.broadcast_to(xx, cls.shape))
    r = r / np.hypot(cy, cx)
    ok = cls >= 0
    resp = ok & (cls != 0)          # blocks that responded at all
    edges = np.linspace(0, 1.0, nbin + 1)
    rows = []
    for i in range(nbin):
        m = resp & (r >= edges[i]) & (r < edges[i + 1] + (1e-9 if i == nbin - 1
                                                          else 0))
        n = int(m.sum())
        rows.append((edges[i], edges[i + 1], n,
                     float((cls[m] == MULTI).mean()) if n else float("nan")))
    fm = resp & np.isfinite(r)
    rr, mm = r[fm], (cls[fm] == MULTI).astype(float)
    slope = float(np.polyfit(rr, mm, 1)[0]) if len(rr) > 2 else float("nan")
    corr = float(np.corrcoef(rr, mm)[0, 1]) if mm.std() > 0 else float("nan")
    return rows, slope, corr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", required=True)
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-VEILMAP")
    ap.add_argument("--block", type=int, default=96)
    ap.add_argument("--arms", default="resp,fixed")
    ap.add_argument("--nbin", type=int, default=6)
    a = ap.parse_args()

    outd = pathlib.Path(a.out)
    B = a.block
    print(f"MULTI as a fraction of RESPONDING blocks (FLAT excluded, so a "
          f"subject that does not fill the frame is not scored for its empty "
          f"corners),\nby radius from the optical centre (r=1 is the corner), "
          f"block {B} master px, topographic prominence\n")
    hdr = "  ".join(f"{i / a.nbin:.2f}-{(i + 1) / a.nbin:.2f}"
                    for i in range(a.nbin))
    print(f"{'subject':<28}{'arm':<6}  {hdr}   {'slope':>7} {'corr':>6}")
    for s in a.subjects.split(","):
        p = outd / "tensors" / f"{s}.npz"
        if not p.exists():
            print(f"{s:<28}  -- no tensor")
            continue
        z = np.load(p)
        if f"resp_b{B}" not in z:
            print(f"{s:<28}  -- no block {B}")
            continue
        ok = z[f"ok_b{B}"]
        for arm in a.arms.split(","):
            t = z[f"{arm}_b{B}"].astype(np.float64)
            cls, _, _ = run_grid(t, ok, peaks_topo, z["ks"])
            rows, slope, corr = profile(cls, z[f"gy_b{B}"], z[f"gx_b{B}"],
                                        B // 2, z["lat_shape"], a.nbin)
            cells = "  ".join(f"{r[3]:9.3f}" for r in rows)
            print(f"{s:<28}{arm:<6}  {cells}   {slope:7.3f} {corr:6.3f}")
            sys.stdout.flush()
    print("\nslope is d(MULTI fraction)/d(normalised radius); a drift artefact "
          "is forced to be strongly positive, an occlusion signal is not.")


if __name__ == "__main__":
    main()
