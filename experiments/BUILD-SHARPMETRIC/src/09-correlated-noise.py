"""The limit of my own repair: Immerkaer assumes WHITE noise. Raw noise is not.

Script 08 settled the photometric question -- S0 falls x0.24 under a monotone
remap, S2 moves x0.98 -- but left a residual. S2 reads about 0.53 against real
sources where script 07 showed that blurring the master by k=4 only reaches
0.82. Something non-photometric and non-blur is still driving it.

The suspect is my own commissioning arm. Script 05 and script 07 both tested S2
against rng.normal(), i.e. WHITE noise, and S2 passed exactly (1.0012, 1.0024,
1.0031, 1.0034). But S2's noise subtraction uses Immerkaer's 3x3 mask, whose
derivation ASSUMES the noise is spatially independent. A demosaiced raw frame's
noise is not: the demosaic interpolates missing colour samples from neighbours,
which low-passes the noise and correlates it across pixels. Immerkaer applied to
correlated noise UNDER-estimates sigma, so S2 under-subtracts, so the source
keeps residual noise energy in its fine band and the master/source ratio is
pushed down.

If that is right then my white-noise arm is unrepresentative of the real input
in precisely the way I accused the original commission's latent of being, and I
should say so in those words rather than hoping nobody checks.

Two measurements:
  A. Plant CORRELATED noise of known amplitude in a real master and see whether
     S2 goes perverse where it was immune to white noise of the same sigma.
  B. Measure the actual spatial autocorrelation of the noise in a real source,
     so the claim "raw noise is correlated" is a number and not an assertion.
"""
import glob
import os
import sys

import numpy as np
import rawpy
import tifffile

OUT_ROOT, SRC_ROOT, ARM = r"C:\dev\strehl-out", r"D:\personal\macro", "SHIP-V4"
CROP, PATCH, PATCH_FLOOR = 560, 70, 50.0
IMM = np.array([[1., -2., 1.], [-2., 4., -2.], [1., -2., 1.]])


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float64)


def fine_abs(y):
    return float(np.mean(np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])))


def conv3(a, k):
    o = np.zeros((a.shape[0] - 2, a.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            o += k[i, j] * a[i:i + a.shape[0] - 2, j:j + a.shape[1] - 2]
    return o


def sigma_imm(y):
    return float(np.sqrt(np.pi / 2.0) * np.mean(np.abs(conv3(y, IMM))) / 6.0)


def S0(y):
    return fine_abs(y)


def S2(y):
    s = sigma_imm(y)
    dx, dy = np.diff(y, axis=1)[:-1, :], np.diff(y, axis=0)[:, :-1]
    f = float(np.mean(dx * dx + dy * dy))
    k = 0.25 * (y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2])
    cx, cy = np.diff(k, axis=1)[:-1, :], np.diff(k, axis=0)[:, :-1]
    c = float(np.mean(cx * cx + cy * cy))
    fs, cs = f - 4.0 * s * s, c - s * s
    return float(np.sqrt(fs / cs)) if fs > 0 and cs > 0 else float("nan")


def med_ratio(stat, ref, src):
    n = ref.shape[0] // PATCH
    v = []
    for py in range(n):
        for px in range(n):
            sl = (slice(py * PATCH, (py + 1) * PATCH), slice(px * PATCH, (px + 1) * PATCH))
            if fine_abs(ref[sl]) < PATCH_FLOOR and fine_abs(src[sl]) < PATCH_FLOOR:
                continue
            a, b = stat(ref[sl]), stat(src[sl])
            if np.isfinite(a) and np.isfinite(b) and b > 0:
                v.append(a / b)
    return float(np.median(v)) if v else float("nan")


def correlated_noise(rng, shape, sigma, k):
    """Gaussian noise low-passed by a kxk box, renormalised to the same sigma."""
    n = rng.normal(0, 1, shape)
    if k > 1:
        c = np.cumsum(np.pad(n, ((0, 0), (k, k)), mode="wrap"), axis=1)
        n = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
        c = np.cumsum(np.pad(n, ((k, k), (0, 0)), mode="wrap"), axis=0)
        n = (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)
    return n * (sigma / n.std())


def main():
    subs = sys.argv[1:] or ["wrapped-text-1", "bee-3-cpl", "coffee-bean", "lavendar-cpl"]
    rng = np.random.default_rng(23)

    print("A. PLANTED NOISE, white vs correlated, identical true sigma=400")
    print("   source = master + noise. A sharpness statistic should read ~1.000.")
    print("%-22s %10s %10s %10s %10s" % ("subject", "S2 white", "S2 corr2", "S2 corr3", "S0 corr2"))
    print("-" * 68)
    rowsA = []
    for sub in subs:
        cand = glob.glob(os.path.join(OUT_ROOT, "acceptance", ARM, sub + "*.tiff"))
        if not cand:
            continue
        img = luma(tifffile.imread(cand[0])[..., :3].astype(np.float64))
        h, w = img.shape
        m = img[h // 2 - CROP // 2:h // 2 + CROP // 2, w // 2 - CROP // 2:w // 2 + CROP // 2]
        r = (med_ratio(S2, m, m + correlated_noise(rng, m.shape, 400.0, 1)),
             med_ratio(S2, m, m + correlated_noise(rng, m.shape, 400.0, 2)),
             med_ratio(S2, m, m + correlated_noise(rng, m.shape, 400.0, 3)),
             med_ratio(S0, m, m + correlated_noise(rng, m.shape, 400.0, 2)))
        rowsA.append(r)
        print("%-22s %10.4f %10.4f %10.4f %10.4f" % ((sub[:22],) + r))
    if rowsA:
        a = np.array(rowsA)
        print("%-22s %10.4f %10.4f %10.4f %10.4f" % (("MEDIAN",) + tuple(np.median(a, 0))))

    print("\nB. MEASURED NOISE AUTOCORRELATION of a real demosaiced source")
    print("   lag-1 correlation of the high-pass residual. 0.0 => white.")
    print("%-22s %10s %10s %10s" % ("subject", "lag1 x", "lag1 y", "sigma_imm"))
    print("-" * 58)
    for sub in subs[:2]:
        arw = sorted(glob.glob(os.path.join(SRC_ROOT, sub, "*.ARW")))
        if not arw:
            continue
        with rawpy.imread(arw[len(arw) // 2]) as r:
            s = luma(r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                                   use_camera_wb=True, output_bps=16).astype(np.float64))
        h, w = s.shape
        p = s[h // 2 - CROP // 2:h // 2 + CROP // 2, w // 2 - CROP // 2:w // 2 + CROP // 2]
        hp = conv3(p, IMM)
        hp = hp - hp.mean()
        d = float((hp * hp).mean())
        lx = float((hp[:, :-1] * hp[:, 1:]).mean() / d)
        ly = float((hp[:-1, :] * hp[1:, :]).mean() / d)
        print("%-22s %10.4f %10.4f %10.1f" % (sub[:22], lx, ly, sigma_imm(p)))
        wn = np.random.default_rng(5).normal(0, 1, p.shape)
        hw = conv3(wn, IMM); hw = hw - hw.mean(); dw = float((hw * hw).mean())
        print("%-22s %10.4f %10.4f %10s"
              % ("  (white ref)", float((hw[:, :-1] * hw[:, 1:]).mean() / dw),
                 float((hw[:-1, :] * hw[1:, :]).mean() / dw), "-"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
