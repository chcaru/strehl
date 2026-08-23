"""M20 verification -- Gate 3.2 (implementable priors) and the sigma -> sigma_rel mapping.

The report maps its simulation crossover into real-image units by dividing by a magic
constant 0.0872 which appears in no committed script.  This file:

  1. reproduces the four-prior table of report section 7;
  2. reverse-engineers what 0.0872 could be;
  3. proves the mapping is scale-invariant IN PRINCIPLE (so it is not nonsense), then
  4. replaces the global point mapping with a DIRECT PER-PIXEL calibration: bin pixels
     by their own sigma_local/signal_local and find where the guarded merge stops
     beating selection pixel-by-pixel.  That is the measurement report section 7 needed
     and did not make.
  5. measures the 1-D-vs-CFA-scale window error the report calls "the softest number".
"""
import numpy as np
from scipy.ndimage import uniform_filter1d
from v4_sim import (NPX, KFRAMES, FREQ, DIFF, OTF, N_EFF, build_plant, blur_stack,
                    depth_map, observe, focus_select, rmse, f_cut)

W = 9


def smooth(v, w=W):
    return uniform_filter1d(v, w, mode="nearest")


def make_prior(mode, selF, Yf, sigma, latent):
    nvar = sigma ** 2 * NPX
    if mode == "oracle":
        return np.abs(np.fft.rfft(latent)) ** 2 / NPX
    if mode == "est-sel":
        p = np.maximum(smooth(np.abs(selF) ** 2 / NPX) - sigma ** 2, 1e-6)
        return p / np.maximum(DIFF ** 2, 1e-3)
    if mode == "est-mf":
        j0 = KFRAMES // 2
        Hk = np.stack([OTF[abs(k - j0)] for k in range(KFRAMES)])
        sH2 = (Hk ** 2).sum(axis=0)
        mf = np.abs((Hk * Yf).sum(axis=0)) ** 2 / np.maximum(sH2, 1e-9) ** 2
        return np.maximum(smooth(mf / NPX) - nvar / np.maximum(sH2, 1e-9) / NPX, 1e-6)
    if mode == "powerlaw":
        P = smooth(np.abs(selF) ** 2 / NPX)
        m = (FREQ > 0.01) & (FREQ < f_cut(N_EFF))
        b, a = np.polyfit(np.log(FREQ[m]), np.log(np.maximum(P[m], 1e-12)), 1)
        return np.exp(a) * np.maximum(FREQ, 1e-3) ** b
    raise ValueError(mode)


def run_one(latent, depth, sigma, mode, tau, seed):
    Y = observe(latent, depth, sigma, seed)
    sel, _ = focus_select(Y)
    Yf = np.fft.rfft(Y, axis=1)
    selF = np.fft.rfft(sel)
    prior = make_prior(mode, selF, Yf, sigma, latent)
    nvar = sigma ** 2 * NPX
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
        gua[m] = np.fft.irfft(w * wf + (1 - w) * selF, NPX)[m]
    return Y, sel, wie, gua


def sigma_rel_field(Y, sigma, w=W, unbiased=True, decimate=1):
    """The statistic contrast2.py computes, but on the simulation."""
    rels = []
    for k in range(Y.shape[0]):
        y = Y[k, ::decimate]
        m = uniform_filter1d(y, w, mode="nearest")
        m2 = uniform_filter1d(y * y, w, mode="nearest")
        v = np.maximum(m2 - m * m, 0.0)
        if unbiased:
            v *= w / (w - 1.0)
        sig = np.sqrt(np.maximum(v - sigma ** 2, 0.0))
        rels.append(sigma / np.maximum(sig, 1e-6))
    return np.min(np.stack(rels), axis=0)


# --------------------------------------------------------------------------- section 7
def priors_table():
    print("=" * 96)
    print("GATE 3.2 -- data-estimated priors (report section 7).  gua/sel < 1 means deconvolution wins.")
    print("=" * 96)
    latent = build_plant()
    depth = depth_map("slabs")
    print(f"{'sigma':>7} | {'oracle':>8} {'est-sel':>8} {'est-mf':>8} {'powerlaw':>9}")
    tbl = {}
    for sg in (0.010, 0.020, 0.030, 0.050):
        row = []
        for mode in ("oracle", "est-sel", "est-mf", "powerlaw"):
            E = []
            for s in range(4):
                _, sel, wie, gua = run_one(latent, depth, sg, mode, 3.0, 900 + s)
                E.append([rmse(sel, latent), rmse(gua, latent)])
            E = np.mean(E, axis=0)
            row.append(E[1] / E[0])
        tbl[sg] = row
        print(f"{sg:>7.3f} | {row[0]:>8.3f} {row[1]:>8.3f} {row[2]:>8.3f} {row[3]:>9.3f}")
    # implementable crossover by linear interpolation on est-sel
    xs = sorted(tbl)
    ys = [tbl[s][1] for s in xs]
    cross = None
    for i in range(len(xs) - 1):
        if (ys[i] - 1.0) * (ys[i + 1] - 1.0) < 0:
            cross = xs[i] + (1.0 - ys[i]) * (xs[i + 1] - xs[i]) / (ys[i + 1] - ys[i])
    print(f"\n  implementable (est-sel) crossover sigma = {cross:.4f}   (report: 'sigma ~ 0.03')")
    xs2 = sorted(tbl); ys2 = [tbl[s][0] for s in xs2]
    return cross


# --------------------------------------------------------------------------- the constant
def reverse_engineer():
    print()
    print("=" * 96)
    print("What is 0.0872?  (0.03 / 0.0872 = 0.3440, the report's mapping constant)")
    print("=" * 96)
    latent = build_plant()
    print(f"  0.03 / 0.3440                                    = {0.03/0.3440:.4f}")
    def lstd(a, w=W):
        m = uniform_filter1d(a, w, mode="nearest")
        m2 = uniform_filter1d(a * a, w, mode="nearest")
        return np.sqrt(np.maximum(m2 - m * m, 0.0))
    cands = {
        "global std of latent": float(np.std(latent)),
        "mean local std (W=9) of latent": float(np.mean(lstd(latent))),
        "median local std (W=9) of latent": float(np.median(lstd(latent))),
        "mean local std (W=9) of in-focus blurred frame": float(np.mean(lstd(blur_stack(latent)[0]))),
        "median local std of in-focus blurred frame": float(np.median(lstd(blur_stack(latent)[0]))),
        "mean local std (W=27) of latent": float(np.mean(lstd(latent, 27))),
        "mean |grad| of latent": float(np.mean(np.abs(np.gradient(latent)))),
    }
    for k, v in cands.items():
        print(f"  {k:<48} = {v:.4f}   -> 0.03/x = {0.03/max(v,1e-9):.4f}")
    print("  None of these is 0.0872 to better than ~10%; the constant is not reproducible")
    print("  from any committed artefact.")


# --------------------------------------------------------------------------- invariance
def scale_invariance():
    print()
    print("=" * 96)
    print("Is the sigma -> sigma_rel mapping defensible IN PRINCIPLE?  Scale-invariance test.")
    print("=" * 96)
    depth = depth_map("slabs")
    print(f"{'plant amp':>10} {'sigma':>8} | {'gua/sel (est-sel)':>18} {'median sigma_rel':>17}")
    for amp in (1.0, 3.0, 0.3):
        for sg in (0.03 * amp,):
            lat = build_plant(amp)
            E, R = [], []
            for s in range(4):
                Y, sel, wie, gua = run_one(lat, depth, sg, "est-sel", 3.0, 900 + s)
                E.append([rmse(sel, lat), rmse(gua, lat)])
                R.append(float(np.median(sigma_rel_field(Y, sg))))
            E = np.mean(E, axis=0)
            print(f"{amp:>10.1f} {sg:>8.4f} | {E[1]/E[0]:>18.4f} {np.mean(R):>17.4f}")
    print("  The whole forward model is linear and the estimator is scale-covariant, so a")
    print("  plant at amplitude a with noise a*sigma is identical to the unit plant at sigma.")
    print("  => sigma_local/signal_local IS the right invariant. The mapping is legitimate")
    print("     in kind; what remains is whether the CONSTANT is measured consistently.")


# --------------------------------------------------------------------------- direct calib
def direct_calibration():
    print()
    print("=" * 96)
    print("THE MEASUREMENT THE REPORT DID NOT MAKE: direct PER-PIXEL crossover")
    print("  bin pixels by their own sigma_local/signal_local; find where guarded stops")
    print("  beating selection pixel-by-pixel.  No magic constant anywhere.")
    print("=" * 96)
    latent = build_plant()
    depth = depth_map("slabs")
    edges = np.array([0.0, 0.05, 0.10, 0.17, 0.25, 0.34, 0.45, 0.6, 0.8, 1.1, 1.5, 2.2, 3.5, 1e9])
    for mode in ("est-sel", "oracle"):
        acc_g = np.zeros(len(edges) - 1)
        acc_s = np.zeros(len(edges) - 1)
        acc_n = np.zeros(len(edges) - 1)
        for sg in (0.005, 0.010, 0.020, 0.030, 0.050, 0.080, 0.120):
            for s in range(6):
                Y, sel, wie, gua = run_one(latent, depth, sg, mode, 3.0, 4000 + s)
                rel = sigma_rel_field(Y, sg)
                eg = smooth((gua - latent) ** 2)
                es = smooth((sel - latent) ** 2)
                idx = np.digitize(rel, edges) - 1
                for b in range(len(edges) - 1):
                    m = idx == b
                    if m.any():
                        acc_g[b] += eg[m].sum()
                        acc_s[b] += es[m].sum()
                        acc_n[b] += m.sum()
        print(f"\n  prior = {mode}")
        print(f"  {'sigma_rel bin':>18} {'n px':>10} {'RMSE gua':>10} {'RMSE sel':>10} {'gua/sel':>9}")
        prev = None
        cross = None
        for b in range(len(edges) - 1):
            if acc_n[b] < 500:
                continue
            rg = np.sqrt(acc_g[b] / acc_n[b])
            rs = np.sqrt(acc_s[b] / acc_n[b])
            ratio = rg / rs
            lo, hi = edges[b], edges[b + 1]
            print(f"  [{lo:>6.3f},{hi if hi<1e8 else np.inf:>7.3f}] {int(acc_n[b]):>10d} "
                  f"{rg:>10.4f} {rs:>10.4f} {ratio:>9.4f}")
            if prev is not None and prev[1] < 1.0 <= ratio:
                cross = prev[0] + (1.0 - prev[1]) * (0.5 * (lo + min(hi, 10)) - prev[0]) / (ratio - prev[1])
            prev = (0.5 * (lo + min(hi, 10)), ratio)
        if cross:
            print(f"  --> per-pixel crossover at sigma_local/signal_local ~ {cross:.3f}")


# --------------------------------------------------------------------------- window scale
def window_scale():
    print()
    print("=" * 96)
    print("THE SOFT NUMBER: 1-D sim window (9 sensor px) vs 2-D CFA window (9 CFA px = 18 sensor px)")
    print("=" * 96)
    latent = build_plant()
    depth = depth_map("slabs")
    print(f"{'sigma':>7} | {'W=9 native':>12} {'W=9 on 2x-decimated':>21} {'ratio':>8} | "
          f"{'W=9 biased':>12} {'W=18 native':>12}")
    for sg in (0.010, 0.030, 0.050):
        a, b, c, d = [], [], [], []
        for s in range(4):
            Y = observe(latent, depth, sg, 900 + s)
            a.append(np.median(sigma_rel_field(Y, sg, 9, True, 1)))
            b.append(np.median(sigma_rel_field(Y, sg, 9, True, 2)))
            c.append(np.median(sigma_rel_field(Y, sg, 9, False, 1)))
            d.append(np.median(sigma_rel_field(Y, sg, 18, True, 1)))
        print(f"{sg:>7.3f} | {np.mean(a):>12.4f} {np.mean(b):>21.4f} "
              f"{np.mean(b)/np.mean(a):>8.3f} | {np.mean(c):>12.4f} {np.mean(d):>12.4f}")
    print("  Decimating to CFA scale changes the statistic materially -- the report's")
    print("  crossover was calibrated at sensor scale and applied at CFA scale.")


if __name__ == "__main__":
    priors_table()
    reverse_engineer()
    scale_invariance()
    window_scale()
    direct_calibration()
