"""M60 controls B1 and P1.

B1 (fact 73, run first)
   Is the frozen focus operator -- box mean of Sobel magnitude -- able to see
   defocus AT AN EDGE at all? Fact 73 says the box mean of |grad| is exactly
   invariant under blur on a monotone edge, because blur conserves total
   variation. An occluding edge IS an edge. If the operator is blind there, a
   flat through-focus curve at occluding edges is a property of the instrument
   and says nothing about the scene.

P1 (positive control)
   The reviewer's own model, planted:  I_k = a_k*(F conv PSF_k) + (1-a_k)*(B conv PSF_k)
   with a_k the foreground matte carried through the same PSF. Two layers at
   frames kF and kB, separation D swept. The plant can express failure: at D = 0
   there is one depth and the detector must not fire.

   The plant validates the detector's response to two-layer geometry. It cannot
   validate the noise model's absolute calibration, because it draws its noise
   from that same model (AGENTS rule 34 / fact 599). The headline number is read
   off the detection-rate-versus-D curve, never asserted from the planted
   constant (fact 738).
"""

import os
import sys
import json
import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
FIG = os.path.abspath(os.path.join(HERE, "..", "fig"))
R = 2
ISO = 100.0
SEED = 1373


def focus(a):
    return uniform_filter(L.sobel_mag(a), 2 * R + 1, mode="reflect")


# ---------------------------------------------------------------- B1
def b1():
    print("B1  fact-73 blindness check: box mean of |grad| across a blurred edge")
    print("    monotone step, box entirely containing the step")
    H = W = 129
    prof = np.zeros(W, np.float64)
    prof[W // 2:] = 1000.0
    rows = []
    for sig in (0.0, 1.0, 2.0, 3.0, 6.0, 12.0):
        a = np.tile(prof, (H, 1))
        if sig > 0:
            a = gaussian_filter(a, sig, mode="nearest")
        gm = L.sobel_mag(a)
        whole = float(gm[H // 2].sum())
        big = float(uniform_filter(gm, 121, mode="constant")[H // 2, W // 2])
        small = float(uniform_filter(gm, 2 * R + 1, mode="reflect")[H // 2, W // 2])
        off = float(uniform_filter(gm, 2 * R + 1, mode="reflect")[H // 2, W // 2 + 12])
        rows.append((sig, whole, big, small, off))
        print("    sigma %5.1f   sum|grad| across the edge %12.6f   box121 %12.6f"
              "   box%d at edge %10.4f   box%d 12px off %10.4f"
              % (sig, whole, big, 2 * R + 1, small, 2 * R + 1, off))
    spread = max(r[1] for r in rows) - min(r[1] for r in rows)
    print("    total variation across the edge varies by %.6g over sigma 0..12"
          "  -> conserved" % spread)
    print("    box radius %d at the edge varies %.4f -> %.4f  (ratio %.3f)"
          % (R, rows[0][3], rows[-1][3], rows[-1][3] / max(rows[0][3], 1e-9)))
    return rows


# ---------------------------------------------------------------- P1
def make_layers(rng, H, W, bg_texture=True):
    """Foreground: an opaque bar with its own texture. Background: broadband texture."""
    yy, xx = np.mgrid[0:H, 0:W]
    alpha = (xx < W * 0.42).astype(np.float64)
    fg = 900.0 + 260.0 * gaussian_filter(rng.normal(0, 1, (H, W)), 1.1)
    if bg_texture:
        bg = 2600.0 + 620.0 * gaussian_filter(rng.normal(0, 1, (H, W)), 1.1)
    else:
        bg = np.full((H, W), 2600.0)
    return alpha, fg, bg


def render(alpha, fg, bg, sig_f, sig_b):
    """Two-layer composite with the matte carried through the foreground's own PSF."""
    a = gaussian_filter(alpha, sig_f, mode="nearest") if sig_f > 0 else alpha
    F = gaussian_filter(fg, sig_f, mode="nearest") if sig_f > 0 else fg
    B = gaussian_filter(bg, sig_b, mode="nearest") if sig_b > 0 else bg
    return a * F + (1.0 - a) * B


def p1_stack(rng, n, kF, kB, rate, H=96, W=192, bg_texture=True, reps=12):
    alpha, fg, bg = make_layers(rng, H, W, bg_texture)
    F = np.zeros((n, H, W), np.float32)
    S = np.zeros((n, H, W), np.float32)
    for k in range(n):
        img = render(alpha, fg, bg, abs(k - kF) * rate, abs(k - kB) * rate)
        sd = L.sigma_dn(img.astype(np.float32), ISO)
        obs = img + rng.normal(0, 1, img.shape) * sd
        F[k] = focus(obs.astype(np.float32))
        s1 = np.zeros((H, W)); s2 = np.zeros((H, W))
        for _ in range(reps):
            v = focus((obs + rng.normal(0, 1, img.shape) * sd).astype(np.float32))
            s1 += v; s2 += v * v
        S[k] = np.sqrt(np.maximum(s2 / reps - (s1 / reps) ** 2, 0) * reps / (reps - 1))
    return F, S, alpha


def p1_null(rng, n, kF, rate, H=96, W=192, reps=12):
    """D = 0: one depth. The plant's own falsifier."""
    return p1_stack(rng, n, kF, kF, rate, H, W, True, reps)


def run_detector(F, S):
    n, H, W = F.shape
    V = F.reshape(n, -1, 1)
    res = L.second_peak(V)
    z, prom, den, kd = L.prominence_z(V, S.reshape(n, -1, 1), res)
    return (z.reshape(H, W), np.asarray(res["k1"]).reshape(H, W),
            np.asarray(res["k2"]).reshape(H, W), prom.reshape(H, W),
            den.reshape(H, W))


if __name__ == "__main__":
    out = {}
    out["b1"] = b1()

    print("\nP1  two-layer plant.  n=120 frames, kF=40, defocus rate swept,")
    print("    veil zone = the 24 px of background nearest the silhouette")
    rng = np.random.default_rng(SEED)
    n, kF, W = 120, 40, 192
    veil = slice(int(W * 0.42), int(W * 0.42) + 24)
    far = slice(int(W * 0.42) + 60, W - 4)
    recs = []
    for rate in (0.25, 0.5):
        # z* from the D = 0 plant, matched population, 1% FPR
        Fz, Sz, alpha = p1_null(rng, n, kF, rate)
        zz, _, _, _, _ = run_detector(Fz, Sz)
        zstar = float(np.percentile(zz[:, veil], 99))
        null_hit = float(np.mean(zz[:, veil] > zstar))
        print("    rate %.2f  D=0 null: z* (1%% FPR) = %.2f  npx=%d"
              % (rate, zstar, zz[:, veil].size))
        for D in (0, 5, 10, 20, 40, 60):
            Fp, Sp, alpha = p1_stack(rng, n, kF, kF + D, rate)
            z, k1, k2, prom, den = run_detector(Fp, Sp)
            hit = float(np.mean(z[:, veil] > zstar))
            hit_far = float(np.mean(z[:, far] > zstar))
            fired = z[:, veil] > zstar
            sep = np.abs(k2[:, veil].astype(float) - k1[:, veil])
            sep_hit = float(np.median(sep[fired])) if fired.any() else float("nan")
            rec = dict(rate=rate, D=D, zstar=zstar, hit_veil=hit, hit_far=hit_far,
                       sep_median_when_fired=sep_hit,
                       z_med_veil=float(np.median(z[:, veil])),
                       prom_med=float(np.median(prom[:, veil])),
                       den_med=float(np.median(den[:, veil])))
            recs.append(rec)
            print("      D=%3d  veil hit %6.1f%%   far-bg hit %6.1f%%   "
                  "median |k2-k1| when fired %6.1f   z_med %6.2f"
                  % (D, 100 * hit, 100 * hit_far, sep_hit, rec["z_med_veil"]))
    out["p1"] = recs

    print("\nP1b  same but with an UNTEXTURED background (fact 73's case)")
    recs_b = []
    for D in (0, 20, 60):
        Fp, Sp, alpha = p1_stack(rng, n, kF, kF + D, 0.5, bg_texture=False)
        z, k1, k2, prom, den = run_detector(Fp, Sp)
        zstar = [r for r in recs if r["rate"] == 0.5 and r["D"] == 0][0]["zstar"]
        hit = float(np.mean(z[:, veil] > zstar))
        recs_b.append(dict(D=D, hit_veil=hit, z_med=float(np.median(z[:, veil]))))
        print("      D=%3d  veil hit %6.1f%%   z_med %6.2f" % (D, 100 * hit, np.median(z[:, veil])))
    out["p1b"] = recs_b

    with open(os.path.join(DATA, "13-plant.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote data/13-plant.json")
