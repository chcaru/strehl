"""Commission S2 on REAL image content, because script 06 looks pinned.

Script 06 reported S2 below 1.0 for 8 of 8 subjects, with seven of the eight
inside 0.496..0.630 -- a bee, a lavender floret, a pencil tip and a coffee bean
all reading about the same number. Nearly-constant output across wildly
different inputs is the signature of a statistic that has stopped responding,
and "the merge loses detail" is far too strong a claim to publish on the back
of it. So: plant known answers into REAL photographs and check S2 returns them.

The arms below use a real master as the image and SYNTHESISE the source from it,
so the true answer is known exactly and no raw decode or registration is
involved. That deliberately removes every confound script 06 has, which means a
failure here is a failure of the statistic itself and not of the harness.

The load-bearing arm is IDENTITY. If source == master the ratio must be exactly
1.0000 by construction, for any statistic, on any image. A statistic that
cannot return 1.0 when handed the same array twice is not measuring sharpness;
it is measuring an asymmetry in its own implementation. That arm costs nothing
and it is the one arm the original commission never ran.
"""
import glob
import os
import sys

import numpy as np
import tifffile

OUT_ROOT = r"C:\dev\strehl-out"
ARM = "SHIP-V4"
CROP, PATCH, PATCH_FLOOR = 560, 70, 50.0
IMM = np.array([[1., -2., 1.], [-2., 4., -2.], [1., -2., 1.]])


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float64)


def blur(y, k):
    if k <= 1:
        return y.copy()
    c = np.cumsum(np.pad(y, ((0, 0), (k, k)), mode="edge"), axis=1)
    y = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
    c = np.cumsum(np.pad(y, ((k, k), (0, 0)), mode="edge"), axis=0)
    return (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)


def fine_abs(y):
    return float(np.mean(np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])))


def conv3(a, k):
    o = np.zeros((a.shape[0] - 2, a.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            o += k[i, j] * a[i:i + a.shape[0] - 2, j:j + a.shape[1] - 2]
    return o


def sigma_immerkaer(y):
    return float(np.sqrt(np.pi / 2.0) * np.mean(np.abs(conv3(y, IMM))) / 6.0)


def S0(y):
    return fine_abs(y)


def S2_parts(y):
    s = sigma_immerkaer(y)
    dx, dy = np.diff(y, axis=1)[:-1, :], np.diff(y, axis=0)[:, :-1]
    f = float(np.mean(dx * dx + dy * dy))
    k = 0.25 * (y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2])
    cx, cy = np.diff(k, axis=1)[:-1, :], np.diff(k, axis=0)[:, :-1]
    c = float(np.mean(cx * cx + cy * cy))
    return s, f, c, f - 4.0 * s * s, c - s * s


def S2(y):
    _, _, _, fs, cs = S2_parts(y)
    if fs <= 0 or cs <= 0:
        return float("nan")
    return float(np.sqrt(fs / cs))


def ratio(stat, master, source):
    n = master.shape[0] // PATCH
    vals, unmeas = [], 0
    for py in range(n):
        for px in range(n):
            sl = (slice(py * PATCH, (py + 1) * PATCH), slice(px * PATCH, (px + 1) * PATCH))
            if fine_abs(master[sl]) < PATCH_FLOOR and fine_abs(source[sl]) < PATCH_FLOOR:
                continue
            a, b = stat(master[sl]), stat(source[sl])
            if not (np.isfinite(a) and np.isfinite(b)) or b <= 0:
                unmeas += 1
                continue
            vals.append(a / b)
    return (float(np.median(vals)) if vals else float("nan")), len(vals), unmeas


def main():
    subs = sys.argv[1:] or ["wrapped-text-1", "bee-3-cpl", "coffee-bean", "lavendar-cpl"]
    rng = np.random.default_rng(11)
    print("REAL-CONTENT COMMISSION. source synthesised from the master, answer known.")
    print("%-22s %-26s %9s %9s %6s %6s" % ("subject", "arm", "S0", "S2", "n", "unmeas"))
    print("-" * 86)
    fails = []
    for sub in subs:
        cand = glob.glob(os.path.join(OUT_ROOT, "acceptance", ARM, sub + "*.tiff"))
        if not cand:
            print("%-22s (master not found)" % sub)
            continue
        img = luma(tifffile.imread(cand[0])[..., :3].astype(np.float64))
        h, w = img.shape
        m = img[h // 2 - CROP // 2:h // 2 + CROP // 2, w // 2 - CROP // 2:w // 2 + CROP // 2]
        s, f, c, fs, cs = S2_parts(m)
        print("%-22s sigma=%.1f fine=%.0f coarse=%.0f  after-sub fine=%.0f coarse=%.0f"
              % (sub[:22], s, f, c, fs, cs))
        arms = [
            ("IDENTITY  (must be 1.000)", m, 1.0, "eq"),
            ("source=blur(master,2)", blur(m, 2), 1.0, "gt"),
            ("source=blur(master,4)", blur(m, 4), 1.0, "gt"),
            ("source=master+N(0,400)", m + rng.normal(0, 400, m.shape), 1.0, "near"),
        ]
        for name, src, _, kind in arms:
            r0, n0, u0 = ratio(S0, m, src)
            r2, n2, u2 = ratio(S2, m, src)
            print("%-22s %-26s %9.4f %9.4f %6d %6d" % ("", name, r0, r2, n2, u2))
            if kind == "eq" and abs(r2 - 1.0) > 1e-9:
                fails.append("%s IDENTITY S2=%.6f" % (sub, r2))
            if kind == "gt" and not r2 > 1.02:
                fails.append("%s %s S2=%.4f not >1.02" % (sub, name, r2))
        # inverted: a KNOWN-WORSE master against the true image
        r0, _, _ = ratio(S0, blur(m, 4), m)
        r2, n2, u2 = ratio(S2, blur(m, 4), m)
        print("%-22s %-26s %9.4f %9.4f %6d %6d" % ("", "master=blur(4) (must be <1)", r0, r2, n2, u2))
        if not r2 < 0.98:
            fails.append("%s inverted S2=%.4f not <0.98" % (sub, r2))
        print()
    print("=" * 86)
    if fails:
        print("FAILURES (%d):" % len(fails))
        for f_ in fails:
            print("   " + f_)
        return 1
    print("all real-content arms PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
