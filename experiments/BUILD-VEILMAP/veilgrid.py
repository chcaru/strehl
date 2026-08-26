"""BUILD-VEILMAP: one decode pass per subject -> per-block through-focus curves.

Emits, for one subject and several block sizes at once:

  resp_b{B}   (nframes, nby, nbx)  drift-tracked block response
  fixed_b{B}  (nframes, nby, nbx)  the same blocks with NO drift correction
  probe_*     named windows (the claw, the control, the paper null), both ways
  a/ty/tx     the per-frame similarity taken from fitdrift.py's global model
  ho_*        held-out placement error of that model, on sampled frames

Both arms come out of the same decode, so the drift control is a difference
between two columns of one run and not a comparison of two runs.

The drift model is NOT re-fitted here: run fitdrift.py first.  Per-frame fits
were tried and abandoned -- at the ends of a bracket almost every window is
defocused, so a frame may have three usable correspondences for three
parameters.  See fitdrift.py's docstring.

Usage:
  python fitdrift.py --subject bee-3-cpl
  python veilgrid.py --subject bee-3-cpl --blocks 48,96,192,384
"""
import argparse
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import veilcore as vc  # noqa: E402

RAWROOT = pathlib.Path(r"D:\personal\macro")
MASTERS = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")

# named windows in MASTER coordinates, from V-VEILCLAW/probe.py
PROBES = {
    "bee-3-cpl": [("claw", 2640, 2830, 2080, 2270),
                  ("ctl", 3120, 3450, 1880, 2250),
                  ("null", 100, 400, 6500, 6900)],
}


def parse_ks(s, n):
    if not s:
        return list(range(n))
    b, e, st = (int(v) for v in s.split(":"))
    return list(range(b, min(e, n), st))


def gather(s, ye, xe, hh, ww):
    """Block means for a full grid from a SAT, given mapped edge arrays."""
    y = np.clip(np.rint(ye).astype(np.int64), 0, hh)
    x = np.clip(np.rint(xe).astype(np.int64), 0, ww)
    y0, y1 = y[:-1, None], y[1:, None]
    x0, x1 = x[None, :-1], x[None, 1:]
    tot = s[y1, x1] - s[y0, x1] - s[y1, x0] + s[y0, x0]
    n = np.maximum((y1 - y0) * (x1 - x0), 1)
    return (tot / n).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--blocks", default="48,96,192,384",
                    help="block sizes in MASTER px")
    ap.add_argument("--ks", default="")
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-VEILMAP")
    ap.add_argument("--nho", type=int, default=12, help="held-out windows")
    ap.add_argument("--hostep", type=int, default=12, help="check every Nth")
    ap.add_argument("--half", type=int, default=56)
    ap.add_argument("--pad", type=int, default=90)
    a = ap.parse_args()

    t_start = time.time()
    blocks = [int(v) for v in a.blocks.split(",")]
    out = pathlib.Path(a.out) / "tensors"
    out.mkdir(parents=True, exist_ok=True)

    dz = np.load(pathlib.Path(a.out) / "drift" / f"{a.subject}.npz")
    A, Ty, Tx = dz["a"], dz["ty"], dz["tx"]

    files = vc.frames(a.subject)
    assert len(files) == len(A), f"{len(files)} frames vs drift model {len(A)}"
    ks = parse_ks(a.ks, len(files))
    nk = len(ks)
    lat_h, lat_w = vc.green_lattice(files[ks[0]]).shape
    ref = vc.load_ref(a.subject, (lat_h, lat_w))

    who = vc.pick_windows(ref, a.nho, a.half)
    print(f"{a.subject}: {nk} frames, ref {ref.shape}, blocks {blocks}, "
          f"drift deg={int(dz['deg'])} a {A[0]:.5f}->{A[-1]:.5f}, "
          f"{len(who)} held-out windows every {a.hostep} frames")
    tracker = vc.TrackFitter(ref, half=a.half, pad=a.pad)

    G = {}                                   # grids in reference (master/2) px
    for B in blocks:
        b = B // 2
        ys = np.arange(0, ref.shape[0] - b + 1, b, dtype=np.int64)
        xs = np.arange(0, ref.shape[1] - b + 1, b, dtype=np.int64)
        G[B] = dict(b=b, ys=ys, xs=xs, ok=np.ones((len(ys), len(xs)), bool),
                    resp=np.zeros((nk, len(ys), len(xs)), np.float32),
                    fixed=np.zeros((nk, len(ys), len(xs)), np.float32))

    probes = PROBES.get(a.subject, [])
    pr = np.zeros((nk, len(probes)), np.float32)
    pf = np.zeros((nk, len(probes)), np.float32)
    arr = {k: np.full(nk, np.nan) for k in
           ("a", "ty", "tx", "gmean", "ho_med", "ho_nocorr", "ho_n")}

    lat_h = lat_w = None
    for j, k in enumerate(ks):
        g = vc.green_lattice(files[k])
        if lat_h is None:
            lat_h, lat_w = g.shape
        model = (float(A[k]), float(Ty[k]), float(Tx[k]))
        arr["a"][j], arr["ty"][j], arr["tx"][j] = model

        if j % a.hostep == 0:
            d, d0 = [], []
            for t in tracker.correspond(g, who, model):
                if t[5]:
                    continue
                py, px = vc.map_point(t[0], t[1], *model)
                d.append(np.hypot(t[2] - py, t[3] - px))
                d0.append(np.hypot(t[2] - t[0], t[3] - t[1]))
            arr["ho_n"][j] = len(d)
            if d:
                arr["ho_med"][j] = 2.0 * np.median(d)
                arr["ho_nocorr"][j] = 2.0 * np.median(d0)

        L = vc.abs_lap(g)
        arr["gmean"][j] = float(L[1:-1, 1:-1].mean())
        S = vc.sat(L)
        hh, ww = g.shape
        for B in blocks:
            d = G[B]
            ye = np.append(d["ys"], d["ys"][-1] + d["b"]).astype(np.float64)
            xe = np.append(d["xs"], d["xs"][-1] + d["b"]).astype(np.float64)
            mye, mxe = model[0] * ye + model[1], model[0] * xe + model[2]
            d["resp"][j] = gather(S, mye, mxe, hh, ww)
            d["fixed"][j] = gather(S, ye, xe, hh, ww)
            d["ok"] &= (((mye[:-1] >= 0) & (mye[1:] <= hh))[:, None]
                        & ((mxe[:-1] >= 0) & (mxe[1:] <= ww))[None, :]
                        & ((ye[:-1] >= 0) & (ye[1:] <= hh))[:, None]
                        & ((xe[:-1] >= 0) & (xe[1:] <= ww))[None, :])
        for i, (_, y0, y1, x0, x1) in enumerate(probes):
            py0, px0 = vc.map_point(y0 / 2, x0 / 2, *model)
            py1, px1 = vc.map_point(y1 / 2, x1 / 2, *model)
            pr[j, i] = gather(S, np.array([py0, py1]), np.array([px0, px1]),
                              hh, ww)[0, 0]
            pf[j, i] = gather(S, np.array([y0 / 2, y1 / 2]),
                              np.array([x0 / 2, x1 / 2]), hh, ww)[0, 0]
        if (j + 1) % 50 == 0 or j == nk - 1:
            print(f"  {j + 1}/{nk} f{k:03d} a={model[0]:.5f} "
                  f"[{time.time() - t_start:.0f}s]")
            sys.stdout.flush()

    z = dict(subject=a.subject, ks=np.array(ks), blocks=np.array(blocks),
             ref_shape=np.array(ref.shape), lat_shape=np.array([lat_h, lat_w]),
             probe_names=np.array([p[0] for p in probes]),
             probe_boxes=np.array([p[1:] for p in probes],
                                  np.int64).reshape(len(probes), 4),
             probe_resp=pr, probe_fixed=pf, drift_deg=int(dz["deg"]))
    z.update(arr)
    for B in blocks:
        d = G[B]
        z[f"resp_b{B}"], z[f"fixed_b{B}"], z[f"ok_b{B}"] = (
            d["resp"], d["fixed"], d["ok"])
        z[f"gy_b{B}"], z[f"gx_b{B}"] = d["ys"], d["xs"]
    p = out / f"{a.subject}.npz"
    np.savez_compressed(p, **z)

    fin = np.isfinite(arr["ho_med"])
    if fin.any():
        print(f"\nheld-out placement of the smooth model, master px: median "
              f"{np.median(arr['ho_med'][fin]):.1f}  p90 "
              f"{np.percentile(arr['ho_med'][fin], 90):.1f}  max "
              f"{np.max(arr['ho_med'][fin]):.1f}   (over "
              f"{int(fin.sum())} sampled frames)")
        print(f"same windows with NO drift correction:      median "
              f"{np.median(arr['ho_nocorr'][fin]):.1f}  p90 "
              f"{np.percentile(arr['ho_nocorr'][fin], 90):.1f}  max "
              f"{np.max(arr['ho_nocorr'][fin]):.1f}")
    print(f"wrote {p}  [{time.time() - t_start:.0f}s]")


if __name__ == "__main__":
    main()
