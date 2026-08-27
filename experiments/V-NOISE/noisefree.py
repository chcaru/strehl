"""THE NOISE HALF OF THE FREE-FIELD HEAD-TO-HEAD.

Everything measurable here is fixed in advance by
experiments/V-NOISE/PREREGISTRATION.md, committed as d29074e2 BEFORE any of
these numbers existed.  That document also discloses, in its sec.0, that the
registration is NOT blind: noisesplit.py's FLAT/DETAIL ratios had already been
seen, so the sign of the result was suspected.  Read it before this.

WHY THESE ARMS ARE COMPARABLE AT ALL.  Every arm is built from strehl's OWN
linear TIFFs (--linear-srgb --demosaic, pinned binary sha256 15EA7346..82A7B0).
Demosaic and white balance are therefore identical on every side, so the only
remaining difference is the stacking algorithm.  That is the same property that
makes the sharpness table in V-LINEAR2 sec.9 trustworthy; it costs nothing to
reuse it for noise.

REUSED, NOT REBUILT.  Geometry scales come from h2free.FREE, measured by
geomfree.py.  The 4x4-block tone fit is gradetest.fit_map/apply_map, imported
unmodified.  Band edges are h2.BANDS.  This file adds an RGB loader only
because h2h2b.Comp collapses to luma at load time and chroma is half the
question.

A NOTE ON WHY THIS STATISTIC IS ROBUST WHERE THE SHARPNESS ONE WAS FRAGILE.
Local residual sigma is translation-invariant, so the 1.319 px half-stack
disagreement that destroyed 41 of 64 regions in the coherence work cannot touch
it.  Registration accuracy is not on the critical path for this measurement.

COMMISSIONING (PREREGISTRATION.md sec.4) -- no number is reported unless these
pass.  Two of them have outcomes fixed by construction, which is the point:
    NULL     an image against itself.  Must be 1.000.
    QUANT8   strehl requantised to 8 bits.  The added variance is ANALYTIC,
             1/(255^2 * 12), so this arm's true answer is known before it runs.
             It exists because focus-stack 1.5 emits 8-bit and its noise floor
             may be quantisation rather than algorithm.
    POTENCY  planted Gaussian noise at two levels; measured must match the
             analytic prediction within 10%.  A metric that cannot detect
             planted noise cannot certify its absence.
    TONE     the 4x4-block tone fit applied to strehl.  If it reproduces >=50%
             of the noise gap the comparison is a TONE MEASUREMENT and is
             withdrawn, exactly as V-HEADTOHEAD2's fine-scale table was.

INVOCATION (rule 47).  Reads the arms listed in ARMS below plus
C:\\dev\\strehl-out\\V-NOISE\\census.npz (census_src.py).  Writes nothing.

    python noisefree.py [nboot=2000]
"""
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
sys.path.insert(0, os.path.join(_HERE, "..", "V-LINEAR2"))
import h2                                                        # noqa: E402
from gradetest import fit_map, apply_map                         # noqa: E402
from h2free import FREE                                          # noqa: E402

LIN = r"C:\dev\strehl-out\V-H2H2\lin"
CACHE = r"C:\dev\strehl-out\V-NOISE\census.npz"

T = 256
HP = 9                       # local-mean window; matches census_src.py
EDGE = 8                     # discard filter edge effects inside each tile
W709 = np.array([0.2126, 0.7152, 0.0722])
KVAR = 1.0 - 1.0 / (HP * HP)   # residual keeps this fraction of white variance

# PRE-REGISTERED sec.2 item 4 was "max >= 0.98 or min <= 0.02, any channel".
# DEVIATION, argued from measurement and not from convenience (clipdiag.py):
# these are LINEAR renders, and in linear light the featureless quartile is
# also the DARK quartile -- median tile mean 0.0134, p95 max 0.164.  So
# "min <= 0.02" is not a clipping test at all, it is a test of whether the tile
# contains shadow, and it rejected 110 of 110 tiles while "max >= 0.98"
# rejected 0.  The guard is restated as HARD clipping only: a sample sitting
# exactly on the encoding floor or ceiling.  That is what the guard was for.
#
# Both tile sets are reported below -- STRICT (guard applied) and FULL (guard
# dropped) -- because a pre-registration deviation should be shown to change
# nothing rather than asserted to.
CLIP_HI = 0.98
CLIP_LO = 0.02               # retained only so clipdiag.py can quote it

NAMES = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]
LO = np.array([b[0] for b in h2.BANDS])
HI = np.array([b[1] for b in h2.BANDS])


class Arm:
    """Native-grid RGB reader.  Crops are addressed in STREHL coordinates and
    divided by the measured geometry scale, exactly as h2h2b.Comp does, so an
    arm is never resampled by this instrument -- its own pixels are measured."""

    def __init__(self, path, scale, bits, label):
        self.a = tifffile.imread(path)
        self.scale = float(scale)
        self.den = float(2 ** bits - 1)
        self.bits = bits
        self.label = label
        self.h, self.w = self.a.shape[0], self.a.shape[1]

    def rgb(self, y, x, t=T):
        s = self.scale
        ys, xs = int(round(y / s)), int(round(x / s))
        ts = int(round(t / s))
        if ys < 0 or xs < 0 or ys + ts > self.h or xs + ts > self.w:
            return None
        return self.a[ys:ys + ts, xs:xs + ts, :3].astype(np.float64) / self.den


def opponent(rgb):
    """Rec.709 linear luma plus two opponent chroma axes (sec.3.1)."""
    Y = rgb @ W709
    return Y, rgb[:, :, 0] - Y, rgb[:, :, 2] - Y


def sigmas(rgb):
    """(sigma_Y, sigma_C1, sigma_C2, level) -- residual sigma after removing a
    local mean, normalised by the tile's own luma level so an exposure
    difference between arms cannot masquerade as noise."""
    Y, c1, c2 = opponent(rgb)
    lvl = float(Y.mean())
    if lvl <= 1e-6:
        return None
    out = []
    for ch in (Y, c1, c2):
        r = ch - uniform_filter(ch, HP)
        out.append(float(r[EDGE:-EDGE, EDGE:-EDGE].std()) / lvl)
    return out + [lvl]


def band_noise(rgb):
    """Radial power of the luma residual, binned into h2.BANDS on the arm's OWN
    pixel grid.  sec.3.3: for a noise question 0.30-0.48 cyc/px is SIGNAL."""
    Y, _, _ = opponent(rgb)
    r = Y - uniform_filter(Y, HP)
    r = r[EDGE:-EDGE, EDGE:-EDGE]
    n = r.shape[0]
    win = np.hanning(n)[:, None] * np.hanning(n)[None, :]
    p = np.abs(np.fft.fftshift(np.fft.fft2(r * win))) ** 2
    f = np.fft.fftshift(np.fft.fftfreq(n))
    rad = np.hypot(f[:, None], f[None, :])
    lvl = float(Y.mean())
    return np.array([p[(rad >= a) & (rad < b)].mean()
                     for a, b in zip(LO, HI)]) / (lvl * lvl)


def boot(num, den, nboot, rng):
    """Median of paired per-ROI ratios, with a bootstrap CI over ROIs."""
    num, den = np.asarray(num), np.asarray(den)
    ok = den > 0
    ratio = num[ok] / den[ok]
    n = len(ratio)
    if n < 4:
        return float("nan"), float("nan"), float("nan"), n
    idx = rng.integers(0, n, size=(nboot, n))
    bs = np.median(ratio[idx], axis=1)
    return (float(np.median(ratio)), float(np.percentile(bs, 2.5)),
            float(np.percentile(bs, 97.5)), n)


def collect(arm, cells):
    """Per-ROI sigmas and band powers, plus the common clip mask."""
    sig, bands, keep = [], [], []
    for (y, x) in cells:
        blk = arm.rgb(y, x)
        if blk is None:
            keep.append(False)
            sig.append([np.nan] * 4)
            bands.append(np.full(len(LO), np.nan))
            continue
        keep.append(not (blk.max() >= 1.0 - 1e-9 or blk.min() <= 1e-9))
        s = sigmas(blk)
        sig.append(s if s else [np.nan] * 4)
        bands.append(band_noise(blk))
    return np.array(sig), np.array(bands), np.array(keep)


def main():
    nboot = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    if not os.path.exists(CACHE):
        print(f"missing {CACHE} -- run `python census_src.py` first")
        return 2
    z = np.load(CACHE)
    cells = [tuple(c) for c in z["cells"][z["flat"]]]
    print("=" * 100)
    print("V-NOISE -- noise half of the free-field head-to-head")
    print("  pre-registration d29074e2, committed before any of this ran")
    print(f"  {len(cells)} FLAT tiles, bottom {0.25:.0%} of "
          f"{len(z['cells'])} by max-over-{int(z['nframes'])}-frames "
          f"high-pass variance, measured on the SOURCE frames")
    print("=" * 100)

    arms = {"strehl": Arm(rf"{LIN}\113-full-g1.tiff", 1.0, 16,
                          "strehl (this project)")}
    for tag in ("enfuse", "fs15"):
        cfg = FREE[tag]
        if not os.path.exists(cfg["path"]):
            print(f"  MISSING {tag}: {cfg['path']}")
            continue
        arms[tag] = Arm(cfg["path"], cfg["scale"], cfg["bits"], cfg["label"])

    res = {}
    for k, a in arms.items():
        res[k] = collect(a, cells)
        print(f"  loaded {k:8s} {a.w}x{a.h} {a.bits}-bit scale {a.scale:.4f}"
              f"  {a.label}")

    keep = np.ones(len(cells), bool)
    for k in arms:
        keep &= res[k][2]
    finite = np.all(np.isfinite(res["strehl"][0]), axis=1)
    keep &= finite
    full = finite.copy()
    n = int(keep.sum())
    print(f"\nCLIP GUARD (hard floor/ceiling in any arm; see the DEVIATION "
          f"note in the source): {n} of {len(cells)} tiles survive")
    print("  clipdiag.py: fs15 (8-bit) puts samples on the black floor in "
          "48/110 tiles, strehl and enfuse in 1/110.")
    if n < 8:
        print("  too few tiles survive; reporting nothing rather than "
              "reporting a fragile number")
        return 1

    rng = np.random.default_rng(11)
    lab = ["luma  Y", "chroma R-Y", "chroma B-Y"]

    for mask, mlabel in ((keep, f"STRICT n={int(keep.sum())}"),
                         (full, f"FULL   n={int(full.sum())}")):
        print(f"\n{'=' * 100}\nTILE SET: {mlabel}\n{'=' * 100}")
        print("--- ABSOLUTE noise, median over tiles, sigma/level ---")
        print(f"{'arm':10s} " + " ".join(f"{l:>12s}" for l in lab) + "   level")
        for k, a in arms.items():
            s = res[k][0][mask]
            print(f"{k:10s} " + " ".join(f"{np.nanmedian(s[:, i]):12.5f}"
                                         for i in range(3))
                  + f"   {np.nanmedian(s[:, 3]):.4f}")

        print("\n--- RATIO vs strehl (>1 means the comparator is NOISIER) ---")
        print(f"{'arm':10s} " + " ".join(f"{l:>26s}" for l in lab))
        for k in arms:
            if k == "strehl":
                continue
            row = f"{k:10s} "
            for i in range(3):
                m, lo, hi, _ = boot(res[k][0][mask, i],
                                    res["strehl"][0][mask, i], nboot, rng)
                row += f"  {m:7.3f} [{lo:6.3f},{hi:6.3f}]"
            print(row)
        print(f"    (medians of paired per-ROI ratios; 95% CI from {nboot} "
              f"bootstrap resamples over ROIs)")

        print("\n--- BAND-RESOLVED luma noise power, ratio vs strehl ---")
        print("  sec.3.3: for a NOISE question 0.30-0.48 cyc/px is SIGNAL,")
        print("  not contamination.  It is where noise lives.")
        print(f"{'arm':10s} " + " ".join(f"{nm:>11s}" for nm in NAMES))
        for k in arms:
            if k == "strehl":
                continue
            row = f"{k:10s} "
            for i in range(len(LO)):
                m, _, _, _ = boot(res[k][1][mask, i],
                                  res["strehl"][1][mask, i], nboot, rng)
                row += f"{m:11.3f} "
            print(row)

    # ---------------- commissioning ----------------
    print("\n" + "=" * 100)
    print("COMMISSIONING (PREREGISTRATION.md sec.4)")
    print("=" * 100)

    st = arms["strehl"]
    base = res["strehl"][0][keep]

    m, lo, hi, _ = boot(base[:, 0], base[:, 0], nboot, rng)
    ok_null = abs(m - 1.0) <= 0.005
    print(f"NULL     identity floor            {m:.6f}  "
          f"[{lo:.4f},{hi:.4f}]   {'PASS' if ok_null else 'FAIL'} "
          f"(threshold |r-1| <= 0.005)")

    # QUANT8 -- true answer fixed by construction before the run.  It exists
    # because fs15 emits 8-bit and clipdiag.py measured the quantiser step at
    # 29.2% of the median FLAT tile level, so its noise floor may be its
    # container rather than its algorithm.  Measured on ALL THREE channels,
    # because chroma sigma here is smaller than the quantiser step and is
    # therefore the channel most at risk of being a format artifact.
    qs = []
    for (y, x) in [cells[i] for i in np.where(keep)[0]]:
        blk = st.rgb(y, x)
        s = sigmas(np.round(blk * 255.0) / 255.0)
        qs.append(s[:3] if s else [np.nan] * 3)
    qs = np.array(qs)
    print("QUANT8   strehl requantised to 8 bits -- the one arm whose answer")
    print("         is fixed by construction, not by this project's opinion")
    q_ratio = []
    for i, nm in enumerate(lab):
        m_q, lo_q, hi_q, _ = boot(qs[:, i], base[:, i], nboot, rng)
        q_ratio.append(m_q)
        print(f"         {nm:11s} {m_q:6.4f} [{lo_q:.4f},{hi_q:.4f}]  "
              f"-> 8-bit output alone inflates this channel by "
              f"{(m_q - 1) * 100:5.2f}%")
    var_q = (1.0 / 255.0) ** 2 / 12.0 * float((W709 ** 2).sum()) * KVAR
    lvl = float(np.median(base[:, 3]))
    pred_q = float(np.median(np.sqrt((base[:, 0] * lvl) ** 2 + var_q) / lvl
                             / base[:, 0]))
    print(f"         analytic luma prediction {pred_q:.4f} vs measured "
          f"{q_ratio[0]:.4f}.  The uniform-quantiser model q^2/12 OVERSTATES")
    print(f"         it here because the luma sigma "
          f"({float(np.median(base[:, 0])) * lvl:.5f}) is BELOW the quantiser")
    print(f"         step ({1 / 255:.5f}), so the error is signal-correlated,")
    print("         not uniform.  The measured value is the one used below.")

    print("\n         FORMAT-CORRECTED fs15, DERIVED by removing the measured")
    print("         quantisation variance in quadrature (not measured "
          "directly):")
    for i, nm in enumerate(lab):
        m, _, _, _ = boot(res["fs15"][0][keep, i], base[:, i], nboot, rng)
        resid = m * m - (q_ratio[i] ** 2 - 1.0)
        corr = float(np.sqrt(resid)) if resid > 0 else float("nan")
        print(f"         {nm:11s} raw {m:6.3f}  ->  {corr:6.3f} "
              f"after removing 8-bit output quantisation")

    # POTENCY -- planted noise at two pre-registered levels.
    ok_pot = True
    wsum = float((W709 ** 2).sum())
    for mult in (0.5, 2.0):
        meas, pred = [], []
        rg = np.random.default_rng(4242)
        for j, (y, x) in enumerate([cells[i] for i in np.where(keep)[0]]):
            blk = st.rgb(y, x)
            s0 = base[j, 0] * base[j, 3]          # absolute luma sigma
            sa = mult * s0 / np.sqrt(wsum * KVAR)  # per-channel sigma to plant
            noisy = blk + rg.normal(0.0, sa, blk.shape)
            s = sigmas(noisy)
            meas.append(s[0] * s[3])
            pred.append(np.sqrt(s0 ** 2 + wsum * KVAR * sa ** 2))
        r = float(np.median(np.array(meas) / np.array(pred)))
        good = abs(r - 1.0) <= 0.10
        ok_pot &= good
        print(f"POTENCY  planted {mult:.1f}x sigma        measured/predicted "
              f"{r:.4f}   {'PASS' if good else 'FAIL'} (threshold 10%)")

    # TONE -- the confound this project keeps being bitten by.
    ok_tone = True
    print("\nTONE     4x4-block tone fit applied to strehl, sigma re-measured")
    print("         gap explained = (sigma_toned - sigma_strehl) / "
          "(sigma_comp - sigma_strehl)")
    for k in arms:
        if k == "strehl":
            continue
        xs, ys = [], []
        idx = [cells[i] for i in np.where(keep)[0]]
        for (y, x) in idx:
            a = arms["strehl"].rgb(y, x)
            b = arms[k].rgb(y, x)
            ya, _, _ = opponent(a)
            yb, _, _ = opponent(b)
            xs.append(coarse4(ya).ravel())
            ys.append(coarse4(yb).ravel())
        mp = fit_map(np.concatenate(xs), np.concatenate(ys))
        tn = []
        for (y, x) in idx:
            a = arms["strehl"].rgb(y, x)
            ya, c1, c2 = opponent(a)
            yt = apply_map(mp, ya)
            r = yt - uniform_filter(yt, HP)
            lv = float(yt.mean())
            tn.append(float(r[EDGE:-EDGE, EDGE:-EDGE].std()) / lv
                      if lv > 1e-6 else np.nan)
        tn = np.array(tn)
        s_st = float(np.median(base[:, 0]))
        s_cp = float(np.median(res[k][0][keep, 0]))
        s_tn = float(np.nanmedian(tn))
        gap = s_cp - s_st
        frac = (s_tn - s_st) / gap if abs(gap) > 1e-12 else float("nan")
        good = frac < 0.50
        ok_tone &= good
        print(f"         {k:8s} strehl {s_st:.5f} -> toned {s_tn:.5f}  "
              f"comparator {s_cp:.5f}   explained {frac * 100:7.2f}%   "
              f"{'PASS' if good else 'FAIL -- TONE MEASUREMENT'}")

    # CHROMAGAIN -- the chroma analogue of the tone confound.  Added after the
    # first run, because chroma turned out to carry the headline and the tone
    # arm only guards luma.  A stacker that renders more saturated chroma
    # raises chroma SIGMA without being noisier, exactly as a contrast slider
    # raises luma sigma.  Measured as the ratio of COARSE (4x4-block) chroma
    # spread, which is scene chroma rather than noise.
    print("\nCHROMAGAIN  is the chroma advantage just a saturation "
          "difference?")
    print("         coarse 4x4-block chroma spread = scene chroma, not noise.")
    ok_cg = True
    cg_st = {0: [], 1: []}
    for (y, x) in idx:
        _, c1, c2 = opponent(arms["strehl"].rgb(y, x))
        cg_st[0].append(float(coarse4(c1).std()))
        cg_st[1].append(float(coarse4(c2).std()))
    for k in arms:
        if k == "strehl":
            continue
        for i, nm in ((0, "R-Y"), (1, "B-Y")):
            vs = []
            for (y, x) in idx:
                _, c1, c2 = opponent(arms[k].rgb(y, x))
                vs.append(float(coarse4(c1 if i == 0 else c2).std()))
            g, glo, ghi, _ = boot(vs, cg_st[i], nboot, rng)
            ns, _, _, _ = boot(res[k][0][keep, 1 + i], base[:, 1 + i],
                               nboot, rng)
            expl = (g - 1.0) / (ns - 1.0) if abs(ns - 1.0) > 1e-9 else np.nan
            good = bool(expl < 0.50)
            ok_cg &= good
            print(f"         {k:8s} {nm}  chroma gain {g:6.3f} "
                  f"[{glo:.3f},{ghi:.3f}]  vs noise ratio {ns:6.3f}  "
                  f"-> explains {expl * 100:6.1f}%   "
                  f"{'PASS' if good else 'FAIL -- SATURATION MEASUREMENT'}")

    print("\n" + "=" * 100)
    allok = ok_null and ok_pot and ok_tone and ok_cg
    print(f"COMMISSIONING: {'ALL PASS -- the ratios above may be quoted'
                           if allok else 'FAILED -- ratios withdrawn'}")
    print("=" * 100)
    return 0 if allok else 1


def coarse4(a, d=4):
    t = a.shape[0] // d * d
    u = a.shape[1] // d * d
    return a[:t, :u].reshape(t // d, d, u // d, d).mean((1, 3))


if __name__ == "__main__":
    sys.exit(main())
