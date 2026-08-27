"""THE HEAD-TO-HEAD, re-run with the gather flip in place.  Second construction.

WHY THERE IS A SECOND CONSTRUCTION
----------------------------------
The first (h2h2.py) compared absolute band power between arms.  Its own output
killed it.  Two defects, both visible in the log:

  1. GRADE, NOT RESOLUTION.  P_strehl/P_comp came out 0.71 (113/Zerene) and
     0.48 (cb/fork) in the 0.02-0.05 band -- 20-50 px features, which every
     stacker in this comparison resolves trivially.  A deficit there cannot be
     resolution.  It is the Lightroom development the comparators were fed
     (Contrast2012=+100 on 113MSDCF).  Per-ROI mean normalisation removes a
     scalar gain; it does not remove a contrast curve.  Any statistic reading
     absolute band power across that grade is reading the grade.

  2. FAILED REGISTRATION on cb/fork.  A single global integer offset gave a
     median correlation peak of 0.1634 with per-ROI scatter of +-24 px.
     geom.py had already said so: 5.3 px rms residual after one global shift.
     The ROIs were not looking at the same scene content.

Both are fixed here:

  1. The variable is SPECTRAL SHAPE, normalised inside each ROI by that same
     ROI's own reference band.  A tone curve acts within an ROI as a local
     slope; a slope multiplies every band of that ROI equally and therefore
     CANCELS in the ratio.  What survives is the shape of the falloff, which
     is the resolution question.  The grade-invariance is not asserted, it is
     TESTED below (GRADE ARM: a +100-contrast-like curve is applied to strehl
     and the statistic must not move).

  2. Per-ROI integer registration with a quality gate, and a NULL control:
     the same search run on deliberately mismatched ROIs, to establish what
     peak value means "no correspondence".  ROIs are partitioned into counted
     outcomes that sum to the total.

WHAT IS STILL ONE-SIDED, AND WHICH WAY
--------------------------------------
C_strehl is coherent power from disjoint half-stacks: noise contributes zero.
P_comp is total power: the comparator's signal PLUS its noise.  Normalising
both by their own coarse band makes the comparator's fine/coarse ratio an
UPPER bound on its true fine/coarse ratio, because noise is far whiter than
signal and so inflates the fine band much more than the coarse one.  So

    Cn_strehl(f) > Pn_comp(f)   =>   strehl resolves more there.  RIGOROUS.
    Cn_strehl(f) <= Pn_comp(f)  =>   INCONCLUSIVE.

and it stays conservative against strehl in the three ways named in h2h2.py:
half the frames (twice the focus step), misregistration only ever depresses C,
and the comparators got a developed TIFF while strehl reads RAW.
"""
import sys

import numpy as np
import tifffile

import h2
import rois

LIN = r"C:\dev\strehl-out\V-H2H2\lin"
T = 256
PAD = 32
REF = 1                      # index into h2.BANDS: 0.05-0.10, the reference band
PEAK_MIN = 0.30              # registration gate, justified by the NULL control

COMP = {
    "cb": dict(path=r"C:\dev\macro\out\coffee-bean\stack.tif",
               label="focus-stack fork", scale=1.0340,
               weights=(0.2627, 0.6780, 0.0593)),
    "113": dict(path=r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif",
                label="Zerene Stacker PMax", scale=1.0020,
                weights=(0.2126, 0.7152, 0.0722)),
}


def load(tag):
    return h2.Render(rf"{LIN}\{tag}.tiff", name=tag, linear=True)


class Comp:
    def __init__(self, cfg):
        a = tifffile.imread(cfg["path"])
        w = cfg["weights"]
        self.g = (w[0] * a[:, :, 0].astype(np.float64)
                  + w[1] * a[:, :, 1].astype(np.float64)
                  + w[2] * a[:, :, 2].astype(np.float64))
        self.top = float(a[:, :, :3].max())
        self.h, self.w = self.g.shape

    def crop(self, y0, x0, t):
        if y0 < 0 or x0 < 0 or y0 + t > self.h or x0 + t > self.w:
            return None, 1
        blk = self.g[y0:y0 + t, x0:x0 + t]
        nclip = int((blk >= self.top * 0.9999).sum() + (blk <= 0).sum())
        return blk, nclip


def coarse(a, d=4):
    t = a.shape[0] // d * d
    return a[:t, :t].reshape(t // d, d, t // d, d).mean((1, 3))


def band_power(crop, lo, hi):
    t = crop.shape[0]
    f = h2.contrast_fft(crop)
    if f is None:
        return None
    r = h2.radial(t)
    norm = (t * t) ** 2 * (h2.window(t) ** 2).mean()
    p = (np.abs(f) ** 2) / norm
    return np.array([p[(r >= a) & (r < b)].sum() for a, b in zip(lo, hi)])


def cross_bands(ca, cb):
    fa = h2.contrast_fft(ca)
    fb = h2.contrast_fft(cb)
    if fa is None or fb is None:
        return None
    _, _, C = h2.pair_bands(fa, fb, h2.band_masks(ca.shape[0]), ca.shape[0])
    return C


def grade(x, k=2.2):
    """A contrast grade of roughly the shape Lightroom's Contrast2012=+100
    applies: an S-curve about the midpoint, in display space.  Used ONLY as a
    disturbance to test that the statistic is blind to it."""
    m = np.median(x)
    if m <= 0:
        return x
    v = np.clip(x / (2.0 * m), 1e-6, 1.0) ** (1 / 2.2)
    v = v + (k - 1.0) * 0.25 * np.sin(2 * np.pi * v) / (2 * np.pi)
    return (v ** 2.2) * 2.0 * m


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "113"
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    cfg = COMP[subj]
    S = cfg["scale"]
    TC = int(round(T / S))
    lo = np.array([b[0] for b in h2.BANDS])
    hi = np.array([b[1] for b in h2.BANDS])
    names = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]

    print("=" * 104)
    print(f"HEAD-TO-HEAD v2 (grade-invariant) : {subj}  strehl vs {cfg['label']}")
    print("=" * 104)
    print(f"  scale {S:.4f} (measured by geom.py, interior maximum) -> strehl "
          f"box {T}px, comparator box {TC}px: same scene area")
    print(f"  reference band = {names[REF]} cyc/strehl-px.  Every arm is "
          f"divided by its OWN value there, inside each ROI.")

    A = load(f"{subj}-A-g1"); B = load(f"{subj}-B-g1")
    F1 = load(f"{subj}-full-g1"); F0 = load(f"{subj}-full-g0")
    A0 = load(f"{subj}-A-g0"); B0 = load(f"{subj}-B-g0")
    X = Comp(cfg)

    detail, flat, counts = rois.census(F1, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(7)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    # ---------------- registration, per ROI, with a NULL control -------------
    print("\n--- per-ROI integer registration (nothing resampled) ---")
    null_pk = []
    for i, (y, x) in enumerate(det[:24]):
        cs, _ = F1.crop(y, x, T)
        yj, xj = det[(i + 7) % len(det)]          # a DIFFERENT part of the scene
        cx, ncl = X.crop(int(round(yj / S)), int(round(xj / S)), TC)
        if cx is None:
            continue
        a = coarse(cs); b = coarse(cx)
        n = min(a.shape[0], b.shape[0])
        _, _, pk = h2.integer_shift(a[:n, :n], b[:n, :n], maxshift=6)
        null_pk.append(pk)
    null_pk = np.array(null_pk)
    print(f"  NULL control ({len(null_pk)} deliberately mismatched ROI pairs): "
          f"peak median {np.median(null_pk):.4f}, 95th pct "
          f"{np.percentile(null_pk,95):.4f}, max {null_pk.max():.4f}")
    print(f"  gate PEAK_MIN = {PEAK_MIN:.2f}  "
          f"({'ABOVE' if PEAK_MIN > null_pk.max() else 'NOT ABOVE'} the null max"
          f" -> a passing ROI is {'not' if PEAK_MIN > null_pk.max() else 'MAYBE'}"
          f" explicable as chance)")

    # ---------------- the measurement ---------------------------------------
    acc = {k: [] for k in ("C1", "C0", "P1", "P0", "PX", "PG")}
    used = drop_clip_s = drop_clip_x = drop_reg = drop_fft = 0
    peaks = []
    for (y, x) in det:
        ca, na = A.crop(y, x, T); cb, nb = B.crop(y, x, T)
        ca0, na0 = A0.crop(y, x, T); cb0, nb0 = B0.crop(y, x, T)
        c1, n1 = F1.crop(y, x, T); c0, n0 = F0.crop(y, x, T)
        if na or nb or na0 or nb0 or n1 or n0:
            drop_clip_s += 1
            continue
        y0 = int(round(y / S)); x0 = int(round(x / S))
        cx, ncl = X.crop(y0, x0, TC)
        if cx is None or ncl:
            drop_clip_x += 1
            continue
        aa = coarse(c1); bb = coarse(cx)
        n = min(aa.shape[0], bb.shape[0])
        dy, dx, pk = h2.integer_shift(aa[:n, :n], bb[:n, :n], maxshift=6)
        if pk < PEAK_MIN:
            drop_reg += 1
            continue
        cx, ncl = X.crop(y0 + dy * 4, x0 + dx * 4, TC)
        if cx is None or ncl:
            drop_clip_x += 1
            continue
        C1 = cross_bands(ca, cb); C0 = cross_bands(ca0, cb0)
        P1 = band_power(c1, lo, hi); P0 = band_power(c0, lo, hi)
        PX = band_power(cx, lo * S, hi * S)
        PG = band_power(grade(c1), lo, hi)
        if any(v is None for v in (C1, C0, P1, P0, PX, PG)):
            drop_fft += 1
            continue
        for k, v in zip(("C1", "C0", "P1", "P0", "PX", "PG"),
                        (C1, C0, P1, P0, PX, PG)):
            acc[k].append(v)
        peaks.append(pk)
        used += 1

    tot = len(det)
    print(f"\n  ROI partition (must sum to {tot}):")
    print(f"    used                                   {used}")
    print(f"    dropped, strehl clipped                {drop_clip_s}")
    print(f"    dropped, comparator clipped/off-frame  {drop_clip_x}")
    print(f"    dropped, registration below gate       {drop_reg}")
    print(f"    dropped, FFT degenerate                {drop_fft}")
    s = used + drop_clip_s + drop_clip_x + drop_reg + drop_fft
    print(f"    ---- total                             {s}   "
          f"{'OK' if s == tot else 'MISMATCH'}")
    assert s == tot
    if used < 8:
        print("\n  FEWER THAN 8 USABLE ROIs -- this pairing is ABANDONED, "
              "not reported as a result.")
        return 0
    peaks = np.array(peaks)
    print(f"  registration peak on used ROIs: median {np.median(peaks):.4f} "
          f"min {peaks.min():.4f}  (null max {null_pk.max():.4f})")

    for k in acc:
        acc[k] = np.array(acc[k])

    def norm(v):
        """Divide each ROI by its own reference band, then average over ROIs."""
        r = v[:, REF]
        ok = r > 0
        return (v[ok] / r[ok, None]).mean(0), int(ok.sum())

    n1, _ = norm(acc["C1"]); n0, _ = norm(acc["C0"])
    p1, _ = norm(acc["P1"]); p0, _ = norm(acc["P0"])
    px, _ = norm(acc["PX"]); pg, _ = norm(acc["PG"])

    hdr = " ".join(nm.center(11) for nm in names)
    print(f"\n  {'':<34} {hdr}")

    def prow(label, v, fmt="{:11.4e}"):
        print(f"  {label:<34} " + " ".join(fmt.format(z) for z in v))

    print("\n=== GRADE ARM: the statistic must not move under a contrast curve ===")
    prow("strehl P, normalised", p1)
    prow("strehl P after S-curve grade", pg)
    prow("ratio (1.0000 == grade-invariant)", pg / p1, "{:11.4f}")
    gmax = np.abs(pg / p1 - 1).max()
    print(f"  worst deviation {100*gmax:.2f}%.  Absolute band power under the "
          f"same grade moves by {100*abs(acc['PG'][:,REF].mean()/acc['P1'][:,REF].mean()-1):.1f}% "
          f"in the reference band alone, so the disturbance is real.")
    print(f"  VERDICT: {'PASS' if gmax < 0.10 else 'FAIL'} "
          f"(pass = under 10% in every band)")

    print("\n=== normalised spectra (each divided by its own "
          f"{names[REF]} band) ===")
    prow("strehl Cn  POST-flip (noise-free)", n1)
    prow("strehl Cn  PRE-flip  (noise-free)", n0)
    prow("strehl Pn  POST-flip (with noise)", p1)
    prow("strehl Pn  PRE-flip  (with noise)", p0)
    prow(f"{cfg['label'][:26]} Pn", px)

    print("\n=== THE RIGOROUS ONE-SIDED BOUND (grade-invariant) ===")
    prow("Cn_strehl_postflip / Pn_comp", n1 / px, "{:11.4f}")
    prow("Cn_strehl_preflip  / Pn_comp", n0 / px, "{:11.4f}")
    win = [nm for nm, r in zip(names, n1 / px) if r > 1]
    print(f"  rigorous strehl wins (>1): {win if win else 'NONE'}")
    print("  <=1 is INCONCLUSIVE, not a loss: the comparator's fine-band power")
    print("  has its own noise in it and this cannot separate them.")

    print("\n=== best-effort (NOT rigorous: both sides carry their own noise) ===")
    prow("Pn_strehl_postflip / Pn_comp", p1 / px, "{:11.4f}")
    prow("Pn_strehl_preflip  / Pn_comp", p0 / px, "{:11.4f}")
    prow("what the flip did: post/pre", p1 / p0, "{:11.4f}")

    print("\n=== the flip, on the statistic that cannot be fooled by noise ===")
    num = acc["C1"] / np.maximum(acc["C1"][:, REF:REF + 1], 1e-30)
    den = acc["C0"] / np.maximum(acc["C0"][:, REF:REF + 1], 1e-30)
    for i, nm in enumerate(names):
        r, loq, hiq = h2.bootstrap_ratio(num[:, i], den[:, i])
        star = "*" if (loq > 1 or hiq < 1) else " "
        print(f"    {nm:>11}  Cn_post/Cn_pre = {r:7.3f} "
              f"[{loq:6.3f},{hiq:6.3f}]{star}")
    print("    * = 95% CI excludes 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
