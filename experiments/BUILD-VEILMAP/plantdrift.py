"""Synthetic drift plant: a bracket with the real breathing and NO focus change.

The drift null in its strongest form.  Take the all-in-focus master, warp it by
the similarity this subject's bracket actually has -- `a_k`, `ty_k`, `tx_k`
straight out of fitdrift.py -- and emit a frame stack in which every pixel of
scene content is identical at every k and only the geometry moves.  There is no
occlusion, no defocus, no second depth layer, nothing whatever for a
through-focus curve to have two peaks about.

So any MULTI-PEAK this produces is drift artefact and nothing else, and the
fraction it produces is the floor under which a real subject's number means
nothing.  The `fixed` arm is the one that matters: it is the uncorrected
measurement, sweeping fixed pixel boxes across content that is magnifying past
them, which is exactly the confound.  The `resp` arm re-gathers each block at
its own `a_k` and should return an essentially flat curve; whatever it does
produce is the residual of resampling plus the model's own placement error.

Using the master rather than a real frame is deliberate and is the harder
test: the master is sharp everywhere, so every block has texture available to
sweep through it and the artefact is maximally expressible.  A real defocused
frame would understate it.

Output is written in veilgrid.py's tensor format, so classify.py consumes it
with no special case and the plant is scored by the identical instrument.
"""
import argparse
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import veilcore as vc  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="bee-3-cpl")
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-VEILMAP")
    ap.add_argument("--blocks", default="48,96,192,384")
    ap.add_argument("--noise", type=float, default=0.0,
                    help="sd of additive gaussian noise, DN")
    ap.add_argument("--jitter", type=float, default=0.0,
                    help="master px of SMOOTH model error added to the gather")
    ap.add_argument("--jkind", default="both",
                    choices=("both", "scale", "trans"),
                    help="which part of the similarity to perturb")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    import cv2

    t0 = time.time()
    blocks = [int(v) for v in a.blocks.split(",")]
    outd = pathlib.Path(a.out)
    dz = np.load(outd / "drift" / f"{a.subject}.npz")
    A, Ty, Tx = dz["a"], dz["ty"], dz["tx"]
    n = len(A)

    files = vc.frames(a.subject)
    lat = vc.green_lattice(files[n // 2])
    ref = vc.load_ref(a.subject, lat.shape)
    hh, ww = lat.shape
    name = f"PLANT-{a.subject}" + (f"-{a.tag}" if a.tag else "")
    print(f"{name}: {n} synthetic frames, lattice {lat.shape}, blocks {blocks}")
    print(f"warping the master by the measured similarity, a "
          f"{A[0]:.5f} -> {A[-1]:.5f}; no focus change, no occlusion")

    G = {}
    # Model error, added to the GATHER only. The plant is warped by the true
    # (a, ty, tx) and re-gathered at a slightly wrong one, so the floor is
    # measured against a tracker as imperfect as the real one. It is smooth in
    # k, not white: the fitted model's error is a low-order polynomial
    # mismatch, and a white jitter would be removed by smooth(v, 7) and
    # understate the floor. Magnitude is in master px of corner displacement.
    #
    # --jkind matters and the two parts are not equivalent. A similarity fit
    # determines its translation far better than its scale -- translation is
    # two of the three free parameters and every inlier constrains it directly
    # -- so a translation error of tens of px is not a realistic model failure,
    # while a scale error of the same corner magnitude is. `scale` is therefore
    # the honest arm; `both` is an adversarial upper bound and is labelled so.
    u = 2.0 * np.arange(n) / max(n - 1, 1) - 1.0
    R = float(np.hypot(*[s / 2 for s in ref.shape]))
    J = a.jitter / 2.0                                   # master px -> lattice
    dA = (J / R) * np.sin(2 * np.pi * u) * (0.5 if a.jkind == "both" else 1.0)
    dTy = J * 0.5 * np.sin(np.pi * u)
    dTx = J * 0.5 * np.cos(0.5 * np.pi * u)
    if a.jkind == "scale":
        dTy = dTx = np.zeros(n)
    elif a.jkind == "trans":
        dA = np.zeros(n)
        dTy, dTx = dTy * 2, dTx * 2
    if a.jitter > 0:
        corner = 2.0 * np.abs(dA * R + np.hypot(dTy, dTx))
        print(f"gather model error ({a.jkind}): smooth, corner displacement "
              f"median {np.median(corner):.1f} max {corner.max():.1f} master px")
    for B in blocks:
        b = B // 2
        ys = np.arange(0, ref.shape[0] - b + 1, b, dtype=np.int64)
        xs = np.arange(0, ref.shape[1] - b + 1, b, dtype=np.int64)
        G[B] = dict(b=b, ys=ys, xs=xs, ok=np.ones((len(ys), len(xs)), bool),
                    resp=np.zeros((n, len(ys), len(xs)), np.float32),
                    fixed=np.zeros((n, len(ys), len(xs)), np.float32))
    arr = {k: np.full(n, np.nan) for k in
           ("a", "ty", "tx", "gmean", "ho_med", "ho_nocorr", "ho_n")}
    rng = np.random.default_rng(20260607)

    for k in range(n):
        M = np.array([[A[k], 0.0, Tx[k]], [0.0, A[k], Ty[k]]], np.float64)
        g = cv2.warpAffine(ref, M, (ww, hh), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REFLECT)
        if a.noise > 0:
            g = g + rng.normal(0.0, a.noise, g.shape).astype(np.float32)
        arr["a"][k], arr["ty"][k], arr["tx"][k] = A[k], Ty[k], Tx[k]
        L = vc.abs_lap(g)
        arr["gmean"][k] = float(L[1:-1, 1:-1].mean())
        S = vc.sat(L)
        for B in blocks:
            d = G[B]
            ye = np.append(d["ys"], d["ys"][-1] + d["b"]).astype(np.float64)
            xe = np.append(d["xs"], d["xs"][-1] + d["b"]).astype(np.float64)
            ga = A[k] + dA[k]
            mye, mxe = ga * ye + Ty[k] + dTy[k], ga * xe + Tx[k] + dTx[k]
            d["resp"][k] = _gather(S, mye, mxe, hh, ww)
            d["fixed"][k] = _gather(S, ye, xe, hh, ww)
            d["ok"] &= (((mye[:-1] >= 0) & (mye[1:] <= hh))[:, None]
                        & ((mxe[:-1] >= 0) & (mxe[1:] <= ww))[None, :]
                        & ((ye[:-1] >= 0) & (ye[1:] <= hh))[:, None]
                        & ((xe[:-1] >= 0) & (xe[1:] <= ww))[None, :])
        if (k + 1) % 100 == 0 or k == n - 1:
            print(f"  {k + 1}/{n} [{time.time() - t0:.0f}s]")
            sys.stdout.flush()

    z = dict(subject=name, ks=np.arange(n), blocks=np.array(blocks),
             ref_shape=np.array(ref.shape), lat_shape=np.array([hh, ww]),
             probe_names=np.array([], dtype="<U8"),
             probe_boxes=np.zeros((0, 4), np.int64),
             probe_resp=np.zeros((n, 0), np.float32),
             probe_fixed=np.zeros((n, 0), np.float32), drift_deg=int(dz["deg"]))
    z.update(arr)
    for B in blocks:
        d = G[B]
        z[f"resp_b{B}"], z[f"fixed_b{B}"], z[f"ok_b{B}"] = (
            d["resp"], d["fixed"], d["ok"])
        z[f"gy_b{B}"], z[f"gx_b{B}"] = d["ys"], d["xs"]
    p = outd / "tensors" / f"{name}.npz"
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, **z)
    print(f"wrote {p}  [{time.time() - t0:.0f}s]")
    print(f"now: python classify.py --subject {name} --maps fixed/plain")


def _gather(s, ye, xe, hh, ww):
    from veilgrid import gather
    return gather(s, ye, xe, hh, ww)


if __name__ == "__main__":
    main()
