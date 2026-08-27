"""The payoff: S0 against S2 on real subjects, and the corrected multiple.

WHY THE COMMISSION'S NOISE ARM AND ITS RECONSTRUCT ARM AGREE TO 0.03%

Script 02 found that adding N(0,1500) to a master that merely SELECTS reads
3.4855, against the published "perfect reconstruction" arm of 3.4867. That
looked like a coincidence. It is not. The commission's latent is

    rng.normal(8000, 1500, (CROP, CROP)) + 4000*sin(x/3)

i.e. WHITE NOISE of standard deviation 1500 plus one sinusoid. The sources are
box-blurred copies of it. So "the detail a perfect reconstruction restores" IS
white noise of standard deviation ~1500 -- the identical signal the noise arm
adds. On that target the two arms are not similar, they are THE SAME
EXPERIMENT, and no statistic of any kind could separate them. Script 05
confirms it from the other side: S2, which subtracts an estimated noise floor,
FAILS the improvement arm on the white target (non-monotonic 1.000 0.961 0.942
0.941 0.959) and PASSES it on a 1/f target (1.000 1.043 1.176 1.308 1.414) --
because on the white target the thing being "restored" is, to any noise-aware
statistic, noise.

That is the root cause of sec 105.3 item 2, and it is upstream of the metric:
the commissioning TARGET is degenerate, so the RECONSTRUCT arm was never
measuring reconstruction.

WHAT THIS SCRIPT DOES

Runs S0 (shipped) and S2 (gain-invariant, noise-corrected) over the same real
subjects on the same sites with the same registration, and reports both. The
gap between them is the part of the published multiple that was photometric
scale and noise rather than detail.

Every patch is accounted for: measured, skipped-featureless, or unmeasurable
(signal did not survive the noise subtraction). A "corrected multiple" computed
over an unstated number of patches is not a measurement.
"""
import glob
import json
import os
import sys

import numpy as np
import rawpy
import tifffile

OUT_ROOT = r"C:\dev\strehl-out"
SRC_ROOT = r"D:\personal\macro"
ARM = "SHIP-V4"

CROP = 560
PATCH = 70
PATCH_FLOOR = 50.0
SEARCH = 48
CORR_MIN = 0.50
SITE_SHARE = 0.25
SITE_CLIP_MAX = 0.05
IMM = np.array([[1., -2., 1.], [-2., 4., -2.], [1., -2., 1.]])


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1]
            + 0.114 * rgb[..., 2]).astype(np.float64)


def bands_abs(y):
    f = np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])
    k = y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2]
    c = np.abs(np.diff(k, axis=1)[:-1, :]) + np.abs(np.diff(k, axis=0)[:, :-1])
    return float(np.mean(f)), float(np.mean(c) / 4.0)


def conv3(a, k):
    out = np.zeros((a.shape[0] - 2, a.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            out += k[i, j] * a[i:i + a.shape[0] - 2, j:j + a.shape[1] - 2]
    return out


def sigma_immerkaer(y):
    if y.shape[0] < 3 or y.shape[1] < 3:
        return 0.0
    return float(np.sqrt(np.pi / 2.0) * np.mean(np.abs(conv3(y, IMM))) / 6.0)


def S0(y):
    return bands_abs(y)[0]


def S2(y):
    s = sigma_immerkaer(y)
    dx = np.diff(y, axis=1)[:-1, :]
    dy = np.diff(y, axis=0)[:, :-1]
    f = float(np.mean(dx * dx + dy * dy))
    k = 0.25 * (y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2])
    cx = np.diff(k, axis=1)[:-1, :]
    cy = np.diff(k, axis=0)[:, :-1]
    c = float(np.mean(cx * cx + cy * cy))
    fs, cs = f - 4.0 * s * s, c - 1.0 * s * s
    if cs <= 0 or fs <= 0:
        return float("nan")
    return float(np.sqrt(fs / cs))


def best_site(my, n=3):
    h, w = my.shape
    best = []
    for y in range(SEARCH, h - CROP - SEARCH, CROP):
        for x in range(SEARCH, w - CROP - SEARCH, CROP):
            best.append((bands_abs(my[y:y + CROP:4, x:x + CROP:4])[0], y, x))
    best.sort(reverse=True)
    out = []
    for d, y, x in best:
        if all(abs(y - yy) > CROP or abs(x - xx) > CROP for _, yy, xx in out):
            out.append((d, y, x))
        if len(out) >= n:
            break
    return out


def register(ref, mov):
    rf = ref - ref.mean()
    den0 = (rf * rf).sum()
    best, bc = (0, 0), -2.0
    for dy in range(-SEARCH, SEARCH + 1, 4):
        for dx in range(-SEARCH, SEARCH + 1, 4):
            m = mov[SEARCH + dy:SEARCH + dy + CROP, SEARCH + dx:SEARCH + dx + CROP]
            if m.shape != ref.shape:
                continue
            mm = m - m.mean()
            den = np.sqrt(den0 * (mm * mm).sum())
            c = float((rf * mm).sum() / den) if den > 0 else -2.0
            if c > bc:
                bc, best = c, (dy, dx)
    dy0, dx0 = best
    for dy in range(dy0 - 3, dy0 + 4):
        for dx in range(dx0 - 3, dx0 + 4):
            if not (-SEARCH <= dy <= SEARCH and -SEARCH <= dx <= SEARCH):
                continue
            m = mov[SEARCH + dy:SEARCH + dy + CROP, SEARCH + dx:SEARCH + dx + CROP]
            if m.shape != ref.shape:
                continue
            mm = m - m.mean()
            den = np.sqrt(den0 * (mm * mm).sum())
            c = float((rf * mm).sum() / den) if den > 0 else -2.0
            if c > bc:
                bc, best = c, (dy, dx)
    return best, bc


def patch_pairs(ref, regs):
    """Yield per-patch (master_crop, [source_crops]) with full accounting."""
    n = ref.shape[0] // PATCH
    got, skipped = [], 0
    for py in range(n):
        for px in range(n):
            sl = (slice(py * PATCH, (py + 1) * PATCH),
                  slice(px * PATCH, (px + 1) * PATCH))
            if bands_abs(ref[sl])[0] < PATCH_FLOOR and \
               max((bands_abs(c[sl])[0] for c in regs), default=0.0) < PATCH_FLOOR:
                skipped += 1
                continue
            got.append((ref[sl], [c[sl] for c in regs]))
    return got, skipped


def run_subject(subject, nsrc=8):
    cand = glob.glob(os.path.join(OUT_ROOT, "acceptance", ARM, subject + "*.tiff"))
    if not cand:
        return None
    m = tifffile.imread(cand[0])[..., :3].astype(np.float64)
    my = luma(m)
    scored = []
    for _, y, x in best_site(my):
        crop = my[y:y + CROP, x:x + CROP]
        scored.append((bands_abs(crop)[0],
                       float((m[y:y + CROP, x:x + CROP] >= 65000).mean()), y, x))
    top = max(d for d, _, _, _ in scored) if scored else 0.0
    sites = [(y, x) for d, cf, y, x in scored
             if cf <= SITE_CLIP_MAX and top and d / top >= SITE_SHARE]
    if not sites:
        return None
    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    if not arw:
        return None
    idx = np.linspace(0, len(arw) - 1, min(nsrc, len(arw))).astype(int)
    srcs = []
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            s = r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        srcs.append(luma(s.astype(np.float64)))

    r0, r2, nskip, nunmeas, nreg = [], [], 0, 0, 0
    for (y, x) in sites:
        ref = my[y:y + CROP, x:x + CROP]
        regs = []
        for sy in srcs:
            if (y + CROP + SEARCH > sy.shape[0]) or (x + CROP + SEARCH > sy.shape[1]):
                continue
            pad = sy[y - SEARCH:y + CROP + SEARCH, x - SEARCH:x + CROP + SEARCH]
            if pad.shape[0] < CROP + 2 * SEARCH or pad.shape[1] < CROP + 2 * SEARCH:
                continue
            (dy, dx), c = register(ref, pad)
            if c < CORR_MIN:
                continue
            regs.append(sy[y + dy:y + dy + CROP, x + dx:x + dx + CROP])
        if not regs:
            continue
        nreg += 1
        pairs, sk = patch_pairs(ref, regs)
        nskip += sk
        for mc, scs in pairs:
            a = S0(mc)
            b = max(S0(c) for c in scs)
            if b > 0:
                r0.append(a / b)
            u = S2(mc)
            vs = [S2(c) for c in scs]
            vs = [v for v in vs if np.isfinite(v)]
            if np.isfinite(u) and vs and max(vs) > 0:
                r2.append(u / max(vs))
            else:
                nunmeas += 1
    if not r0:
        return None
    return dict(subject=subject, sites=len(sites), registered=nreg,
                s0=float(np.median(r0)), s2=float(np.median(r2)) if r2 else float("nan"),
                n0=len(r0), n2=len(r2), skipped=nskip, unmeasurable=nunmeas)


def main():
    subs = sys.argv[1:] or ["wrapped-text-1", "tweezers-cpl", "leaf-2-cpl",
                            "bee-3-cpl", "lavendar-cpl", "pencil-steep-angle-cpl",
                            "dry-erase-marker-head-cpl", "coffee-bean",
                            "flower-bud-alone-cpl"]
    print("S0 (shipped, fine-band magnitude) vs S2 (gain-invariant, noise-corrected)")
    print("arm %s   sources rawpy gamma=(2.222,4.5) no_auto_bright=True\n" % ARM)
    print("%-28s %9s %9s %8s %7s %7s %7s %7s"
          % ("subject", "S0", "S2", "S0/S2", "n(S0)", "n(S2)", "skip", "unmeas"))
    print("-" * 92)
    rows = []
    for s in subs:
        r = run_subject(s)
        if not r:
            print("%-28s  (no usable site)" % s)
            continue
        rows.append(r)
        print("%-28s %9.3f %9.3f %8.2f %7d %7d %7d %7d"
              % (s[:28], r["s0"], r["s2"], r["s0"] / r["s2"] if r["s2"] else float("nan"),
                 r["n0"], r["n2"], r["skipped"], r["unmeasurable"]))
    if not rows:
        print("nothing measured")
        return 1
    a0 = np.array([r["s0"] for r in rows])
    a2 = np.array([r["s2"] for r in rows])
    print()
    print("=" * 92)
    print("S0  median %.3f   range %.3f .. %.3f   (published sec105 median 4.120)"
          % (np.median(a0), a0.min(), a0.max()))
    print("S2  median %.3f   range %.3f .. %.3f" % (np.median(a2), a2.min(), a2.max()))
    print("inflation factor S0/S2, median %.2fx" % np.median(a0 / a2))
    print()
    above = int((a2 > 1.0).sum())
    print("subjects with S2 > 1.0 (merge RECONSTRUCTS): %d of %d" % (above, len(rows)))
    print("subjects with S2 < 1.0 (merge loses detail): %d of %d"
          % (int((a2 < 1.0).sum()), len(rows)))
    with open(os.path.join("out", "06-real.json"), "w") as f:
        json.dump(rows, f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
