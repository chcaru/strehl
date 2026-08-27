"""COMMISSIONING.  Twelve arms whose right answer is known before the run.

The rule this exists to obey: "a statistic that has only ever been shown to
succeed is not evidence."  So this file does two things at once.

  1. It runs the CANDIDATE statistics against arms that must move them in a
     stated direction, INCLUDING an arm that is a real improvement -- because a
     suite of only-degradations cannot tell a metric that is BLIND to a defect
     from one that is PERVERSE on it.
  2. It runs the RETRACTED statistic through the identical code path.  If the
     battery does not FAIL the statistic that was already shown to be wrong,
     the battery has no power and nothing else in this file means anything.

THE THREE STATISTICS
  P(f)      = mean of the two halves' band power.  This IS the retracted
              statistic: single-image band power.  Planted to fail.
  C(f)      = <Re A B*>, coherent power between two half-stacks built from
              DISJOINT frames.  Independent noise contributes zero in
              expectation, so C cannot be inflated by adding noise.
  gamma(f)  = C / sqrt(P_A P_B).  The fraction of band power that is
              reproducible structure.  gamma has an EXACT invariance that is
              the whole reason it is here:

                  A -> H.A and B -> H.B  =>  C -> |H|^2 C,  P -> |H|^2 P,
                  so gamma is UNCHANGED for ANY filter H applied to both.

              A sharpen, a halo, an unsharp mask -- anything a renderer could
              do after the fact to flatter itself -- moves C and CANNOT move
              gamma.  That is the answer to the defect this project shipped
              before: a sharpness statistic bounded below by zero that could
              never charge for a halo.  Here the halo moves one number and
              provably not the other, and the two-dimensional signature
              separates "captured more" from "amplified what was there".
              The invariance is a CLAIM, and arms SHARP/BLUR08/BLUR10 test it.

PRE-REGISTERED EXPECTATIONS are in EXPECT below, written before the run.
Each is a direction, a threshold, and the statistic it applies to.  Arms marked
DISCLOSE have no pass/fail: they exist to put a measured magnitude on a known
way to fool the instrument, which is more useful than a claim of immunity.
"""
import sys

import numpy as np
from scipy import ndimage

import h2
import rois

LIN = r"C:\dev\strehl-out\V-H2H2\lin"
T = 256
PAD = 32
FULL = T + 2 * PAD


def load(tag):
    return h2.Render(rf"{LIN}\{tag}.tiff", name=tag, linear=True)


def ctr(x):
    return x[PAD:PAD + T, PAD:PAD + T]


# ---------------------------------------------------------------- arms
def a_null(a, b, rng):
    return a, b


def a_blur(sig):
    def f(a, b, rng):
        return (ndimage.gaussian_filter(a, sig, mode="reflect"),
                ndimage.gaussian_filter(b, sig, mode="reflect"))
    return f


def a_down2(a, b, rng):
    def one(x):
        d = ndimage.zoom(x, 0.5, order=1, prefilter=False)
        return ndimage.zoom(d, np.array(x.shape) / np.array(d.shape), order=3)
    return one(a), one(b)


def _rescale(x, s, order):
    y = ndimage.zoom(x, s, order=order, prefilter=(order > 1))
    n = x.shape[0]
    o = (y.shape[0] - n) // 2
    return y[o:o + n, o:o + n]


def a_nn(a, b, rng):
    return _rescale(a, 1.031, 0), _rescale(b, 1.031, 0)


def a_cr(a, b, rng):
    return _rescale(a, 1.031, 3), _rescale(b, 1.031, 3)


def a_scale_fork(a, b, rng):
    """The fork's measured raster: 0.9596x in x, 0.9539x in y."""
    def one(x):
        y = ndimage.zoom(x, (0.9539, 0.9596), order=3)
        y = ndimage.zoom(y, (x.shape[0] / y.shape[0], x.shape[1] / y.shape[1]),
                         order=3)
        return y
    return one(a), one(b)


def a_noise_ind(a, b, rng):
    """Independent noise per half at 3% of the mean -- the arm that killed the
    retracted statistic."""
    s = 0.03 * a.mean()
    return a + rng.normal(0, s, a.shape), b + rng.normal(0, s, b.shape)


def a_noise_common(a, b, rng):
    """The SAME field added to both.  DISCLOSE: this is what PRNU, dust and hot
    pixels look like to C, because both halves are the same silicon."""
    s = 0.03 * a.mean()
    n = rng.normal(0, s, a.shape)
    return a + n, b + n


def a_sharp(a, b, rng):
    def one(x):
        lo = ndimage.gaussian_filter(x, 2.0, mode="reflect")
        return x + 1.0 * (x - lo)
    return one(a), one(b)


_OTF = {}


def _gauss_otf(n, sig):
    if (n, sig) not in _OTF:
        fy = np.fft.fftfreq(n)[:, None]
        fx = np.fft.fftfreq(n)[None, :]
        _OTF[(n, sig)] = np.exp(-2 * (np.pi * sig) ** 2 * (fy ** 2 + fx ** 2))
    return _OTF[(n, sig)]


def a_deconv(a, b, rng):
    """A KNOWN IMPROVEMENT: blur by a known Gaussian, then Wiener-deconvolve
    with that exact kernel.  Must score BETTER than the blur it undoes, and
    must NOT score better than the unblurred original -- a deconvolution can
    recover, it cannot create."""
    sig, lam = 1.0, 2e-3
    def one(x):
        m = x.mean()
        H = _gauss_otf(x.shape[0], sig)
        Y = np.fft.fft2(np.fft.ifft2(np.fft.fft2(x - m) * H).real)
        return m + np.real(np.fft.ifft2(Y * H / (H * H + lam)))
    return one(a), one(b)


def a_blur_then(a, b, rng):
    """The baseline DECONV must beat: the same blur, not undone."""
    sig = 1.0
    def one(x):
        m = x.mean()
        H = _gauss_otf(x.shape[0], sig)
        return m + np.real(np.fft.ifft2(np.fft.fft2(x - m) * H))
    return one(a), one(b)


def a_lowpass_noise(a, b, rng):
    """Brick-wall at 0.20 cyc/px, then INDEPENDENT noise.  There is provably no
    scene content above 0.20 afterwards.  Anything a statistic credits above
    0.20 here is an artefact of the statistic."""
    def one(x, seed):
        m = x.mean()
        F = np.fft.fft2(x - m)
        F[h2.radial(x.shape[0]) >= 0.20] = 0
        y = m + np.real(np.fft.ifft2(F))
        return y + seed
    s = 0.03 * a.mean()
    return one(a, rng.normal(0, s, a.shape)), one(b, rng.normal(0, s, b.shape))


ARMS = [
    ("NULL",        a_null,          "identity, recomputed"),
    ("BLUR03",      a_blur(0.3),     "gaussian sigma=0.3 px, both halves"),
    ("BLUR08",      a_blur(0.8),     "gaussian sigma=0.8 px, both halves"),
    ("BLUR10",      a_blur_then,     "gaussian sigma=1.0 px (DECONV baseline)"),
    ("DECONV",      a_deconv,        "BLUR10 undone by Wiener with the TRUE kernel"),
    ("DOWN2",       a_down2,         "0.5x down then bicubic up"),
    ("NN",          a_nn,            "1.031x rescale, nearest neighbour"),
    ("CR",          a_cr,            "1.031x rescale, bicubic (NN's control)"),
    ("NOISE_IND",   a_noise_ind,     "independent gaussian, 3% of mean, per half"),
    ("NOISE_COM",   a_noise_common,  "the SAME gaussian field added to both"),
    ("SHARP",       a_sharp,         "unsharp mask, amount 1.0, radius 2 px"),
    ("SCALE_FORK",  a_scale_fork,    "0.9596x / 0.9539x (the fork's raster)"),
    ("LOWPASS20",   a_lowpass_noise, "brick-wall at 0.20 + independent noise"),
]

# ---- pre-registered.  (stat, arm) -> (band predicate, rule, text)
HI = lambda f0: (lambda b: b[0] >= f0)
EXPECT = [
    ("C", "NULL",      lambda b: True,  lambda r: r == 1.0,        "== 1 exactly (floor)"),
    ("C", "BLUR08",    HI(0.10),        lambda r: r < 0.98,        "< 0.98 above 0.10"),
    ("C", "BLUR03",    HI(0.25),        lambda r: r < 0.98,        "< 0.98 above 0.25 (POTENCY)"),
    ("C", "DOWN2",     HI(0.20),        lambda r: r < 0.50,        "< 0.50 above 0.20"),
    ("C", "NOISE_IND", lambda b: True,  lambda r: r < 1.05,        "< 1.05 (noise must not pay)"),
    ("C", "DECONV",    HI(0.05),        lambda r: r > 1.05,        "> 1.05 vs BLUR10 (improvement)"),
    ("C", "DECONV_V_NULL", HI(0.05),    lambda r: r < 1.05,        "< 1.05 vs NULL (cannot create)"),
    ("C", "LOWPASS20", HI(0.25),        lambda r: r < 0.05,        "< 0.05 above 0.20 (nothing there)"),
    ("C", "NN_V_CR",   HI(0.20),        lambda r: r < 1.05,        "< 1.05 (NN must not beat bicubic)"),
    ("P", "NOISE_IND", lambda b: True,  lambda r: r < 1.05,        "< 1.05 -- P IS EXPECTED TO FAIL"),
    ("P", "DOWN2",     HI(0.20),        lambda r: r < 0.50,        "< 0.50 above 0.20"),
    ("P", "LOWPASS20", HI(0.25),        lambda r: r < 0.05,        "< 0.05 above 0.20"),
    ("P", "NN_V_CR",   HI(0.20),        lambda r: r < 1.05,        "< 1.05"),
    ("g", "NULL",      lambda b: True,  lambda r: r == 1.0,        "== 1 exactly (floor)"),
    ("g", "BLUR08",    HI(0.05),        lambda r: 0.97 < r < 1.03, "INVARIANT to a filter on both"),
    ("g", "SHARP",     HI(0.05),        lambda r: 0.97 < r < 1.03, "INVARIANT to a sharpen"),
    ("g", "NOISE_IND", HI(0.05),        lambda r: r < 0.98,        "< 0.98 (noise must cost)"),
]
DISCLOSE = {"NOISE_COM", "SHARP", "SCALE_FORK", "CR", "BLUR10"}


def measure(A, B, roiset, arms, seed=17):
    """Every arm on every ROI, accumulated.  Returns arm -> (P, C, g) per band."""
    masks = h2.band_masks(T)
    nb = len(h2.BANDS)
    acc = {name: [np.zeros(nb), np.zeros(nb), np.zeros(nb)] for name, _, _ in arms}
    used = 0
    drop_clip = 0
    for k, (y, x) in enumerate(roiset):
        ca, na = A.crop(y - PAD, x - PAD, FULL)
        cb, nb_ = B.crop(y - PAD, x - PAD, FULL)
        if na or nb_:
            drop_clip += 1
            continue
        used += 1
        for name, fn, _ in arms:
            rng = np.random.default_rng(seed + 1000 * k)
            pa, pb = fn(ca, cb, rng)
            fa = h2.contrast_fft(ctr(pa))
            fb = h2.contrast_fft(ctr(pb))
            PA, PB, C = h2.pair_bands(fa, fb, masks, T)
            acc[name][0] += PA
            acc[name][1] += PB
            acc[name][2] += C
    out = {}
    for name in acc:
        PA, PB, C = acc[name]
        out[name] = dict(P=0.5 * (PA + PB), C=C,
                         g=C / np.sqrt(np.maximum(PA * PB, 1e-300)))
    return out, used, drop_clip


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "113"
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    A = load(f"{subj}-A-g1")
    B = load(f"{subj}-B-g1")
    print(f"COMMISSIONING on {A.name} / {B.name}  ({A.w}x{A.h}, linear sRGB, "
          f"no transfer curve)")
    detail, flat, counts = rois.census(A, t=T, pad=PAD)
    rng = np.random.default_rng(7)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]
    fl = [flat[i] for i in rng.permutation(len(flat))[:nroi]]

    res, used, dropped = measure(A, B, det, ARMS)
    print(f"\nDETAIL ROIs: {len(det)} = used {used} + clipped {dropped}")
    base = res["NULL"]
    bands = h2.BANDS

    hdr = "  ".join(f"{a:.2f}-{b:.2f}" for a, b in bands)
    for stat in ("C", "P", "g"):
        print(f"\n=== statistic {stat} : ratio to NULL, by band ===")
        print(f"  {'arm':<12} {hdr}")
        for name, _, desc in ARMS:
            r = res[name][stat] / np.where(np.abs(base[stat]) > 0,
                                           base[stat], np.nan)
            cells = "  ".join(f"{v:9.4f}" for v in r)
            tag = " (DISCLOSE)" if name in DISCLOSE else ""
            print(f"  {name:<12} {cells}{tag}")

    # derived comparisons
    derived = {
        "DECONV": ("DECONV", "BLUR10"),
        "DECONV_V_NULL": ("DECONV", "NULL"),
        "NN_V_CR": ("NN", "CR"),
    }
    print("\n=== derived arms ===")
    for key, (a, b) in derived.items():
        for stat in ("C", "P"):
            r = res[a][stat] / res[b][stat]
            print(f"  {key:<14} {stat}  " +
                  "  ".join(f"{v:9.4f}" for v in r))

    print("\n=== PRE-REGISTERED VERDICTS ===")
    npass = nfail = 0
    for stat, arm, pred, rule, text in EXPECT:
        if arm in derived:
            a, b = derived[arm]
            r = res[a][stat] / res[b][stat]
        else:
            r = res[arm][stat] / base[stat]
        sel = [i for i, b in enumerate(bands) if pred(b)]
        vals = [r[i] for i in sel]
        ok = all(rule(v) for v in vals)
        worst = max(vals, key=lambda v: 0 if rule(v) else abs(v)) if vals else float("nan")
        if ok:
            npass += 1
        else:
            nfail += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {stat:<2} {arm:<14} {text:<38} "
              f"worst={worst:.4f}")
    print(f"  {npass} pass + {nfail} fail = {npass + nfail} pre-registered checks")

    # the flat-ROI control: the arm that exposed the retracted statistic
    resf, usedf, dropf = measure(A, B, fl, ARMS)
    print(f"\n=== FLAT vs DETAIL: NOISE_IND ratio (flat ROIs: {len(fl)} = "
          f"used {usedf} + clipped {dropf}) ===")
    print("  A statistic that measures noise power gains MORE on flat ROIs.")
    for stat in ("C", "P", "g"):
        rd = res["NOISE_IND"][stat] / res["NULL"][stat]
        rf = resf["NOISE_IND"][stat] / resf["NULL"][stat]
        print(f"  {stat}: detail " + " ".join(f"{v:7.4f}" for v in rd))
        print(f"  {stat}: flat   " + " ".join(f"{v:7.4f}" for v in rf))
        bad = int(np.sum(rf > rd + 0.01))
        print(f"     bands where FLAT gains more than DETAIL: {bad} of {len(bands)}"
              f"  {'<-- measures noise' if bad > len(bands)//2 else ''}")


if __name__ == "__main__":
    sys.exit(main())
