"""Fit the whole bracket's drift: sparse direct fits, then ONE global solve.

Why not per-frame: at the ends of a 299-frame bracket almost every window is
defocused. `veilcore.TrackFitter` gates on `lapratio` so a window only votes
when it is near its own focus, which is what makes the correspondences usable
at all -- but it also means a single end frame may only have two or three
voters. Three parameters on three observations is not a fit.

So, exactly as AGENTS rule 6 prescribes for this situation: compose nothing,
take a sparse set of DIRECT per-frame fits, keep only their RANSAC inliers, and
run ONE global least squares for a smooth model over the pooled set,

    q_y = A(u)*p_y + Ty(u)     q_x = A(u)*p_x + Tx(u),   u = 2k/(n-1) - 1

with A, Ty, Tx polynomials in u -- linear in its coefficients. Breathing is
smooth and monotone (measured: ORCH-drift-check/drift-v2.json), so the frames
that can be fitted carry the frames that cannot.

Reported, all as observed output:
  * held-out inlier fraction, on windows and frames the solve never saw;
  * agreement with the direct per-frame fits on frames where those are
    well-determined -- the number that says the smoothing did not invent a
    track;
  * degree chosen by held-out, not by looking at the answer.
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


def design(u, py, px, deg):
    P = np.stack([u ** j for j in range(deg + 1)], 1)
    z = np.zeros_like(P)
    return (np.concatenate([P * py[:, None], P, z], 1),
            np.concatenate([P * px[:, None], z, P], 1))


def evaluate(coef, u, deg):
    P = np.stack([u ** j for j in range(deg + 1)], 1)
    k = deg + 1
    return P @ coef[:k], P @ coef[k:2 * k], P @ coef[2 * k:]


def solve_poly(u, py, px, qy, qx, deg, delta=4.0, iters=6):
    Ay, Ax = design(u, py, px, deg)
    A = np.concatenate([Ay, Ax], 0)
    b = np.concatenate([qy, qx], 0)
    w = np.ones(len(b))
    coef = None
    for _ in range(iters):
        sw = np.sqrt(w)
        coef, *_ = np.linalg.lstsq(A * sw[:, None], b * sw, rcond=None)
        r = b - A @ coef
        rad = np.hypot(r[:len(qy)], r[len(qy):])
        w2 = np.where(rad <= delta, 1.0, delta / np.maximum(rad, 1e-9))
        w = np.concatenate([w2, w2])
    r = b - A @ coef
    return coef, np.hypot(r[:len(qy)], r[len(qy):])


def resid_master(coef, deg, u, py, px, qy, qx):
    A, Ty, Tx = evaluate(coef, u, deg)
    return np.hypot(qy - (A * py + Ty), qx - (A * px + Tx)) * 2.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-VEILMAP")
    ap.add_argument("--nsample", type=int, default=44)
    ap.add_argument("--nwin", type=int, default=44)
    ap.add_argument("--half", type=int, default=56)
    ap.add_argument("--pad", type=int, default=90)
    ap.add_argument("--degs", default="1,2,3,4,5")
    ap.add_argument("--thresh", type=float, default=8.0, help="lattice px")
    ap.add_argument("--minin", type=int, default=5,
                    help="min RANSAC inliers to accept a frame's direct fit")
    a = ap.parse_args()

    t0 = time.time()
    files = sorted((RAWROOT / a.subject).glob("*.ARW"))
    n = len(files)
    g0 = vc.green_lattice(files[n // 2])
    ref = vc.load_ref(a.subject, g0.shape)
    ks = sorted({int(round(t)) for t in
                 np.linspace(0, n - 1, min(a.nsample, n))})
    wins = vc.pick_windows(ref, a.nwin, a.half)
    wtest = {i for i in range(3, len(wins), 4)}
    ktest = set(ks[2::5])
    wtrain = {w for i, w in enumerate(wins) if i not in wtest}
    print(f"{a.subject}: {n} frames, ref {ref.shape}, sampling {len(ks)}, "
          f"{len(wins)} windows ({len(wtest)} held out), "
          f"{len(ktest)} held-out frames")

    ff = vc.DriftFitter(ref)
    tr = vc.TrackFitter(ref, half=a.half, pad=a.pad)
    obs, direct = [], []
    for i, k in enumerate(ks):
        g = vc.green_lattice(files[k])
        r = ff.fit(g)
        rows = tr.correspond(g, wins, (r["a"], r["ty"], r["tx"]))
        tro = [t for t in rows if (t[0], t[1]) in wtrain and not t[5]]
        sol = vc.TrackFitter.solve(tro, thresh=a.thresh)
        nin = 0
        if sol is not None and tro:
            p = np.array([[t[0], t[1]] for t in tro], np.float64)
            q = np.array([[t[2], t[3]] for t in tro], np.float64)
            res = np.hypot(*(q - (sol["a"] * p
                                  + np.array([sol["ty"], sol["tx"]]))).T)
            keep = res <= a.thresh
            nin = int(keep.sum())
            if nin >= a.minin:
                direct.append((k, sol["a"], sol["ty"], sol["tx"], nin))
                for t, ok in zip(tro, keep):
                    if ok:
                        obs.append((k, t[0], t[1], t[2], t[3], 1))
        for t in rows:                       # held-out windows, ungated
            if (t[0], t[1]) in wtrain or t[5]:
                continue
            obs.append((k, t[0], t[1], t[2], t[3], 0))
        if (i + 1) % 10 == 0 or i == len(ks) - 1:
            print(f"  {i + 1}/{len(ks)} f{k:03d} corr={len(rows)} "
                  f"direct_in={nin} pooled={len(obs)} [{time.time() - t0:.0f}s]")
            sys.stdout.flush()

    obs = np.array(obs, np.float64)
    direct = np.array(direct, np.float64)
    if obs.ndim != 2 or len(direct) < 2:
        raise SystemExit(f"ABORT: only {len(obs)} correspondences and "
                         f"{len(direct)} directly-fitted frames -- refusing "
                         f"to publish a drift model fitted on nothing.")
    tr_m = (obs[:, 5] == 1) & ~np.isin(obs[:, 0].astype(int), list(ktest))
    ho_m = obs[:, 5] == 0
    print(f"\npooled inliers {int(tr_m.sum())} from "
          f"{len(direct)}/{len(ks)} directly-fitted frames; "
          f"held-out correspondences {int(ho_m.sum())}")
    if int(tr_m.sum()) < 40 or len(direct) < 6:
        print("WEAK: too few pooled inliers or directly-fitted frames. The "
              "smooth model is UNVERIFIED for this subject; its drift-tracked "
              "arm should not carry a headline number.")
    if int(tr_m.sum()) < 8:
        raise SystemExit("ABORT: fewer than 8 pooled inliers -- refusing to "
                         "publish a drift model fitted on nothing.")

    u = 2.0 * obs[:, 0] / max(n - 1, 1) - 1.0
    py, px, qy, qx = obs[:, 1], obs[:, 2], obs[:, 3], obs[:, 4]
    ud = 2.0 * direct[:, 0] / max(n - 1, 1) - 1.0
    cy, cx = ref.shape[0] / 2.0, ref.shape[1] / 2.0

    print(f"\n{'deg':>4}{'train med':>11}{'HELD frac<16':>14}"
          f"{'HELD frac<32':>14}{'vs direct med':>15}   (master px)")
    best = None
    for deg in [int(v) for v in a.degs.split(",")]:
        if deg + 1 > len(direct) or deg + 1 > int(tr_m.sum()) // 4:
            continue
        coef, _ = solve_poly(u[tr_m], py[tr_m], px[tr_m], qy[tr_m], qx[tr_m],
                             deg)
        res = resid_master(coef, deg, u, py, px, qy, qx)
        Ad, Tyd, Txd = evaluate(coef, ud, deg)
        dd = 2.0 * np.hypot((Ad - direct[:, 1]) * cy + (Tyd - direct[:, 2]),
                            (Ad - direct[:, 1]) * cx + (Txd - direct[:, 3]))
        f16 = float((res[ho_m] < 16).mean()) if ho_m.any() else float("nan")
        f32 = float((res[ho_m] < 32).mean()) if ho_m.any() else float("nan")
        print(f"{deg:>4}{np.median(res[tr_m]):11.1f}{f16:14.3f}{f32:14.3f}"
              f"{np.median(dd):15.1f}")
        if best is None or f16 > best[0]:
            best = (f16, deg, coef)
    if best is None:                     # too few frames for any listed degree
        coef, _ = solve_poly(u[tr_m], py[tr_m], px[tr_m], qy[tr_m], qx[tr_m], 1)
        best = (float("nan"), 1, coef)
        print("no listed degree was supportable; forced degree 1")
    _, deg, coef = best
    print(f"chosen degree {deg} by held-out fraction within 16 master px")

    kk = np.arange(n, dtype=np.float64)
    uu = 2.0 * kk / max(n - 1, 1) - 1.0
    A, Ty, Tx = evaluate(coef, uu, deg)
    res = resid_master(coef, deg, u, py, px, qy, qx)
    Ad, Tyd, Txd = evaluate(coef, ud, deg)
    dd = 2.0 * np.hypot((Ad - direct[:, 1]) * cy + (Tyd - direct[:, 2]),
                        (Ad - direct[:, 1]) * cx + (Txd - direct[:, 3]))
    strong = direct[:, 4] >= 10
    print(f"\ntrain residual median {np.median(res[tr_m]):.1f} master px")
    print(f"held-out within 16 / 32 master px: {(res[ho_m] < 16).mean():.3f}"
          f" / {(res[ho_m] < 32).mean():.3f}  (n={int(ho_m.sum())}; the "
          f"remainder mixes model error with wrong locks, so this is a floor)")
    print(f"smooth vs direct per-frame fit: median {np.median(dd):.1f} master "
          f"px over {len(dd)} frames; on the {int(strong.sum())} frames with "
          f">=10 direct inliers, median "
          f"{np.median(dd[strong]) if strong.any() else float('nan'):.1f}")
    print(f"a: {A[0]:.5f} -> {A[-1]:.5f}  ({100 * abs(A[0] - A[-1]):.2f}% "
          f"breathing; {abs(A[0] - A[-1]) * np.hypot(*ref.shape):.0f} master "
          f"px corner to corner)")

    out = pathlib.Path(a.out) / "drift"
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{a.subject}.npz"
    np.savez_compressed(
        p, subject=a.subject, n=n, deg=deg, coef=coef, a=A, ty=Ty, tx=Tx,
        ks=np.array(ks), obs=obs, resid_master_px=res, direct=direct,
        ref_shape=np.array(ref.shape), wins=np.array(wins),
        wtest=np.array(sorted(wtest)), ktest=np.array(sorted(ktest)),
        smooth_vs_direct=dd)
    print(f"wrote {p}  [{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
