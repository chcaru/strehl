"""M20 verification -- Gates 3 and 5: the merge comparison, rebuilt independently.

Same STIMULUS specification as the author (so the numbers are comparable) but an
independent implementation of the forward model, the four merges, the guard and every
metric.  Adds the controls the report did not run:

  * does the guard actually differ from the unguarded estimator (numerically)?
  * tau -> 0 must recover the unguarded Wiener, tau -> inf must recover selection
  * is the refutation an artifact of cross-slab ringing?  (single-plane control)
  * fact 24 corroboration measured against a SINGLE FRAME, which is what fact 24
    actually used, not against the noise-free latent
  * scale-invariance of the sigma -> sigma_local/signal_local mapping
"""
import numpy as np
from scipy.special import j1

PITCH_UM, LAM_UM = 5.12, 0.550
NPX, KFRAMES, STEP_PX = 2048, 25, 1.0
N_EFF = 33.0                                   # marked f/11 at B = 3


def f_cut(n):
    return (PITCH_UM / LAM_UM) / n


def mtf_diff(f, n):
    u = np.clip(np.asarray(f, float) / f_cut(n), 0.0, 1.0)
    return (2.0 / np.pi) * (np.arccos(u) - u * np.sqrt(np.maximum(0.0, 1.0 - u * u)))


def mtf_disc(f, d):
    x = np.pi * abs(float(d)) * np.asarray(f, float)
    o = np.ones_like(x)
    nz = np.abs(x) > 1e-12
    o[nz] = np.abs(2.0 * j1(x[nz]) / x[nz])
    return o


def build_plant(amp=1.0):
    x = np.arange(NPX)
    lat = np.zeros(NPX)
    for c, w in [(300, 40), (700, 8), (1100, 4), (1500, 2), (1900, 60)]:
        lat[c - w // 2: c + w // 2] = 1.0
    lat = lat + 0.15 * np.sin(2 * np.pi * x / 17)
    return amp * lat


FREQ = np.fft.rfftfreq(NPX)
DIFF = mtf_diff(FREQ, N_EFF)
OTF = np.stack([mtf_disc(FREQ, d * STEP_PX) * DIFF for d in range(KFRAMES)])   # OTF[d]


def blur_stack(latent):
    Lf = np.fft.rfft(latent)
    return np.stack([np.fft.irfft(Lf * OTF[d], NPX) for d in range(KFRAMES)])


def depth_map(kind):
    x = np.arange(NPX)
    if kind == "slabs":
        return np.clip(x // (NPX // 5), 0, 4) * (KFRAMES - 1) // 4
    if kind == "ramp":
        return (x / NPX * (KFRAMES - 1)).astype(int)
    if kind == "plane":
        return np.zeros(NPX, int)
    raise ValueError(kind)


def observe(latent, depth, sigma, seed):
    PL = blur_stack(latent)
    x = np.arange(NPX)
    r = np.random.default_rng(seed)
    return np.stack([PL[np.abs(k - depth), x] + r.normal(0.0, sigma, NPX)
                     for k in range(KFRAMES)])


def focus_select(Y, win=27):
    """argmax of a box-smoothed |gradient| -- the shipped focus-measure shape."""
    fm = np.stack([np.convolve(np.abs(np.gradient(y)), np.ones(win) / win, mode="same")
                   for y in Y])
    return Y[np.argmax(fm, axis=0), np.arange(NPX)], np.argmax(fm, axis=0)


def merges(Y, depth, sigma, prior, tau=3.0, per_slab_sel=False):
    """Return (selection, mean, unguarded wiener, guarded wiener)."""
    sel, _ = focus_select(Y)
    mean = Y.mean(axis=0)
    Yf = np.fft.rfft(Y, axis=1)
    selF = np.fft.rfft(sel)
    nvar = sigma ** 2 * NPX                      # noise PSD on this FFT normalisation
    wie = np.zeros(NPX)
    gua = np.zeros(NPX)
    for j in np.unique(depth):
        m = depth == j
        Hk = np.stack([OTF[abs(k - j)] for k in range(KFRAMES)])
        sH2 = (Hk ** 2).sum(axis=0)
        num = (Hk * Yf).sum(axis=0)
        nt = nvar / np.maximum(prior, 1e-12)
        wf = num / (sH2 + nt)
        wie[m] = np.fft.irfft(wf, NPX)[m]
        w = sH2 / (sH2 + tau * nt)
        base = np.fft.rfft(np.where(m, sel, 0.0)) if per_slab_sel else selF
        gua[m] = np.fft.irfft(w * wf + (1.0 - w) * base, NPX)[m]
    return sel, mean, wie, gua


def rmse(a, latent):
    return float(np.sqrt(np.mean((a - latent) ** 2)))


def mgrad(a):
    return float(np.mean(np.abs(np.gradient(a))))


def gcorr(a, latent):
    da, dl = np.gradient(a), np.gradient(latent)
    return float(np.dot(da, dl) / np.sqrt(np.dot(da, da) * np.dot(dl, dl)))


def true_prior(latent):
    return np.abs(np.fft.rfft(latent)) ** 2 / NPX


# ----------------------------------------------------------------------------- gate 3.1
def gate31():
    print("=" * 92)
    print("GATE 3.1 -- unguarded Wiener vs argmax selection.  Oracle depth, oracle prior.")
    print("=" * 92)
    latent = build_plant()
    S = true_prior(latent)
    depth = depth_map("slabs")
    print(f"latent mean|grad| = {mgrad(latent):.4f}   (report: 0.0392)")
    print(f"{'sigma':>7} | {'sel':>8} {'mean':>8} {'wiener':>8} {'guarded':>8} | {'wie/sel':>8} "
          f"{'gua/sel':>8} | winner")
    got = {}
    for sg in (0.002, 0.010, 0.020, 0.030, 0.050):
        E = []
        for s in range(4):
            Y = observe(latent, depth, sg, 500 + s)
            E.append([rmse(a, latent) for a in merges(Y, depth, sg, S)])
        E = np.mean(E, axis=0)
        got[sg] = E
        w = ["sel", "mean", "wiener", "guarded"][int(np.argmin(E))]
        print(f"{sg:>7.3f} | {E[0]:>8.4f} {E[1]:>8.4f} {E[2]:>8.4f} {E[3]:>8.4f} | "
              f"{E[2]/E[0]:>8.3f} {E[3]/E[0]:>8.3f} | {w}")
    worst = max(got[s][2] / got[s][0] for s in got)
    print(f"\n  worst unguarded penalty vs selection: {(worst-1)*100:.1f}%   (report: 'up to 31%')")
    return got


# ----------------------------------------------------------------------------- gate 3.4
def gate_guard_identity():
    print()
    print("=" * 92)
    print("GATE 3.4 -- is the committed guard a GENUINE change, or a null one?")
    print("=" * 92)
    latent = build_plant()
    S = true_prior(latent)
    depth = depth_map("slabs")
    Y = observe(latent, depth, 0.03, 777)
    sel, mean, wie, gua = merges(Y, depth, 0.03, S, tau=3.0)
    d = np.max(np.abs(gua - wie))
    print(f"  max|guarded - unguarded| at tau=3, sigma=0.03 : {d:.6f}"
          f"   (rms of latent = {np.sqrt(np.mean(latent**2)):.4f})")
    print(f"  max|guarded - selection|                      : {np.max(np.abs(gua-sel)):.6f}")
    for tau in (1e-6, 0.1, 1.0, 3.0, 100.0, 1e6):
        _, _, w2, g2 = merges(Y, depth, 0.03, S, tau=tau)
        print(f"    tau={tau:>9.0e}: |gua-wie|max {np.max(np.abs(g2-w2)):.6f}   "
              f"|gua-sel|max {np.max(np.abs(g2-sel)):.6f}   RMSE {rmse(g2, latent):.4f}")
    print("  -> tau->0 recovers the unguarded estimator, tau->inf recovers selection.")
    print("     It is a genuine one-parameter family, NOT a restatement.")


# ----------------------------------------------------------------------------- tau sweep
def gate_tau():
    print()
    print("=" * 92)
    print("GATE 3.5 -- tau sweep: tuned, or broad and flat?")
    print("=" * 92)
    latent = build_plant()
    S = true_prior(latent)
    depth = depth_map("slabs")
    print(f"{'sigma':>7} | " + " ".join(f"{t:>7.1f}" for t in (0.5, 1, 2, 3, 6, 12, 24, 48)))
    for sg in (0.01, 0.03, 0.05):
        row = []
        for tau in (0.5, 1, 2, 3, 6, 12, 24, 48):
            E = []
            for s in range(3):
                Y = observe(latent, depth, sg, 300 + s)
                a = merges(Y, depth, sg, S, tau=tau)
                E.append([rmse(a[0], latent), rmse(a[3], latent)])
            E = np.mean(E, axis=0)
            row.append(E[1] / E[0])
        print(f"{sg:>7.3f} | " + " ".join(f"{v:>7.3f}" for v in row))
    print("  (values are guarded/selection; < 1.0 means the guarded merge wins)")


# ----------------------------------------------------------------------------- depth model
def gate_depth():
    print()
    print("=" * 92)
    print("GATE 3.6 -- does cross-slab ringing drive the refutation?  (single-plane control)")
    print("=" * 92)
    latent = build_plant()
    S = true_prior(latent)
    print(f"{'depth model':>26} {'sigma':>7} | {'sel':>8} {'wiener':>8} {'guarded':>8} | "
          f"{'wie/sel':>8} {'gua/sel':>8}")
    for kind in ("plane", "slabs", "ramp"):
        depth = depth_map(kind)
        for sg in (0.010, 0.030):
            E = []
            for s in range(4):
                Y = observe(latent, depth, sg, 500 + s)
                E.append([rmse(a, latent) for a in merges(Y, depth, sg, S)])
            E = np.mean(E, axis=0)
            print(f"{kind:>26} {sg:>7.3f} | {E[0]:>8.4f} {E[2]:>8.4f} {E[3]:>8.4f} | "
                  f"{E[2]/E[0]:>8.3f} {E[3]/E[0]:>8.3f}")
    print("  -> if the single-plane row still shows wiener/sel > 1, the loss is NOT")
    print("     an artifact of the piecewise-constant depth approximation.")


# ----------------------------------------------------------------------------- gate 5
def gate5():
    print()
    print("=" * 92)
    print("GATE 5 -- mean|grad| is one-sided;  and the fact-24 corroboration, re-based")
    print("=" * 92)
    latent = build_plant()
    S = true_prior(latent)
    depth = depth_map("slabs")
    gl = mgrad(latent)
    print(f"ground-truth latent mean|grad| = {gl:.4f}")
    print(f"{'sigma':>7} | {'g sel':>8} {'g mean':>8} {'g wie':>8} {'g gua':>8} | "
          f"{'c sel':>7} {'c wie':>7} {'c gua':>7} | {'g1frame':>8} {'mean/1fr':>9} {'mean/lat':>9}")
    for sg in (0.002, 0.010, 0.020, 0.030, 0.050):
        G, C, one = [], [], []
        for s in range(4):
            Y = observe(latent, depth, sg, 800 + s)
            sel, mean, wie, gua = merges(Y, depth, sg, S)
            G.append([mgrad(sel), mgrad(mean), mgrad(wie), mgrad(gua)])
            C.append([gcorr(sel, latent), gcorr(wie, latent), gcorr(gua, latent)])
            # fact 24's actual baseline: a SINGLE observed frame (the best-focus one here)
            one.append(mgrad(Y[KFRAMES // 2]))
        G = np.mean(G, axis=0); C = np.mean(C, axis=0); one = float(np.mean(one))
        print(f"{sg:>7.3f} | {G[0]:>8.4f} {G[1]:>8.4f} {G[2]:>8.4f} {G[3]:>8.4f} | "
              f"{C[0]:>7.4f} {C[1]:>7.4f} {C[2]:>7.4f} | {one:>8.4f} "
              f"{(G[1]/one-1)*100:>8.1f}% {(G[1]/gl-1)*100:>8.1f}%")
    print()
    print("  'g1frame' = mean|grad| of one observed frame -- fact 24's ACTUAL baseline")
    print("  (fact 24: 11.89 -> 5.02 = -58%, 18.58 -> 8.81 = -53%, mean vs ONE FRAME).")
    print("  The report compares its mean against the noise-free LATENT instead.")


if __name__ == "__main__":
    gate31()
    gate_guard_identity()
    gate_tau()
    gate_depth()
    gate5()
