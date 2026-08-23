"""M60 pass A+B — through-focus curves and their predicted noise sd, per cell.

Pass A  one cheap sweep per stack to build the through-focus mean image Ibar for
        every cell, partition each cell into boundary band / dark interior /
        pale interior on INTENSITY alone, and freeze a seeded pixel subset.
Pass B  one full sweep per stack; for every frame compute the focus response
        f_k = boxmean_R(|grad I_k|) and keep it at the frozen pixels, and run a
        Monte-Carlo of the INJECTED noise model at the same pixels to get the
        predicted sampling sd of f_k.

Nothing in pass A sees the focus volume's shape, so the labels and the pixel
selection cannot be produced by the quantity under test (discipline 358).

Output: one .npz per cell in data/curves/.
"""

import os
import sys
import time
import numpy as np
from scipy.ndimage import uniform_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402
from cells import CELLS, STACK_ISO  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(DATA, "curves")

R_PRIMARY = 2
BAND_Q, FAR_Q = 0.80, 0.40
NPIX = 12000          # per class per cell, seeded subsample
REPS = int(os.environ.get("M60_REPS", "12"))
STEP_A = 6
SEED = 6000


def focus(a, r=R_PRIMARY):
    return uniform_filter(L.sobel_mag(a), 2 * r + 1, mode="reflect")


def partition(Ibar):
    gm = uniform_filter(L.sobel_mag(Ibar), 5, mode="reflect")
    band = gm >= np.quantile(gm, BAND_Q)
    far = gm <= np.quantile(gm, FAR_Q)
    med = np.median(Ibar)
    return {"band": band, "fg": far & (Ibar < med), "bg": far & (Ibar > med)}


def pass_a(stack, cs):
    fs = L.frames(stack)[::STEP_A]
    acc = {c[1]: None for c in cs}
    for f in fs:
        P = L.load_green(f).astype(np.float32)
        for (_, name, _, y0, y1, x0, x1) in cs:
            a = P[y0:y1, x0:x1].astype(np.float64)
            acc[name] = a if acc[name] is None else acc[name] + a
    rng = np.random.default_rng(SEED)
    out = {}
    for (_, name, cls, y0, y1, x0, x1) in cs:
        Ibar = (acc[name] / len(fs)).astype(np.float32)
        m = partition(Ibar)
        sel, lab = [], []
        for j, key in enumerate(("band", "fg", "bg")):
            ii = np.flatnonzero(m[key].ravel())
            if len(ii) > NPIX:
                ii = rng.choice(ii, NPIX, replace=False)
            ii.sort()
            sel.append(ii)
            lab.append(np.full(len(ii), j, np.int8))
        out[name] = {"Ibar": Ibar, "sel": np.concatenate(sel),
                     "lab": np.concatenate(lab),
                     "shape": Ibar.shape,
                     "npx": {k: int(v.sum()) for k, v in m.items()}}
    return out


def pass_b(stack, cs, A):
    iso = STACK_ISO[stack]
    fs = L.frames(stack)
    n = len(fs)
    F = {c[1]: np.zeros((n, len(A[c[1]]["sel"])), np.float32) for c in cs}
    S = {c[1]: np.zeros((n, len(A[c[1]]["sel"])), np.float32) for c in cs}
    rng = np.random.default_rng(SEED + 1)
    t0 = time.time()
    for k, f in enumerate(fs):
        P = L.load_green(f).astype(np.float32)
        for (_, name, _, y0, y1, x0, x1) in cs:
            a = P[y0:y1, x0:x1]
            sel = A[name]["sel"]
            F[name][k] = focus(a).ravel()[sel]
            sd = L.sigma_dn(a, iso)
            s1 = np.zeros(len(sel), np.float64)
            s2 = np.zeros(len(sel), np.float64)
            for _ in range(REPS):
                v = focus(a + rng.normal(0, 1, a.shape).astype(np.float32) * sd
                          ).ravel()[sel]
                s1 += v
                s2 += v.astype(np.float64) ** 2
            var = np.maximum(s2 / REPS - (s1 / REPS) ** 2, 0.0) * REPS / (REPS - 1)
            S[name][k] = np.sqrt(var)
        if k % 40 == 0:
            print("   %s frame %d/%d  %.0fs" % (stack, k, n, time.time() - t0), flush=True)
    return F, S


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    want = set(sys.argv[1:])
    by_stack = {}
    for c in CELLS:
        if want and c[0] not in want:
            continue
        by_stack.setdefault(c[0], []).append(c)
    for stack, cs in by_stack.items():
        print("== %s : %d cells" % (stack, len(cs)), flush=True)
        t0 = time.time()
        A = pass_a(stack, cs)
        print("   pass A %.0fs" % (time.time() - t0), flush=True)
        F, S = pass_b(stack, cs, A)
        for (_, name, cls, y0, y1, x0, x1) in cs:
            np.savez_compressed(
                os.path.join(OUT, "%s__%s.npz" % (stack, name)),
                F=F[name], S=S[name], lab=A[name]["lab"], sel=A[name]["sel"],
                shape=np.array(A[name]["shape"]), Ibar=A[name]["Ibar"],
                cls=np.array([cls]), stack=np.array([stack]),
                rect=np.array([y0, y1, x0, x1]), reps=np.array([REPS]),
                npx=np.array([A[name]["npx"]["band"], A[name]["npx"]["fg"],
                              A[name]["npx"]["bg"]]))
            print("   wrote %s__%s  n=%d P=%d" % (stack, name, F[name].shape[0],
                                                  F[name].shape[1]), flush=True)
        print("   total %.0fs" % (time.time() - t0), flush=True)
