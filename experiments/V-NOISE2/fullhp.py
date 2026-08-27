"""fullhp -- route 1: total band amplitude on the FULL merges, no half-stack.

THE QUESTION.  On `119MSDCF`, `C` -- the coherence statistic behind the
README's own headline -- reads `enfuse` at 2.017x strehl's detail amplitude at
0.20-0.25 cyc/px.  `C` is a cross-power between two HALF-stacks: it counts only
structure CORRELATED across them.  A merge that selects different source frames
in half A than in half B delivers detail in the full render that is nonetheless
incoherent across the halves, and `C` charges it as absent.

So the 2.017 has two readings that cut opposite ways:

  TRUE DETAIL LOSS       we are genuinely half as sharp as `enfuse` here, and
                         the project's central quality claim is broken.
  HALF-STACK INCOHERENCE the detail is present in the DELIVERED image and the
                         instrument cannot see it; the 2.017 is an artifact, and
                         our published noise figures are biased AGAINST us,
                         because incoherent detail lands in the half-difference
                         and is counted as noise.

The second is a hypothesis under which this project looks better, so it gets the
hostile handling: see HOSTILE READING at the bottom of the output, printed
whether or not the flattering branch wins.

THE SIDESTEP.  The half-split exists to estimate NOISE.  Detail does not need
it.  Measure total band amplitude on the FULL merges -- ours against `enfuse`'s,
same band, same scene content.  That counts detail whether or not it is coherent
across halves.  No half-stack is read anywhere in this file.

--------------------------------------------------------------------------------
WHICH TERMS ARE BAND-LIMITED, stated before any two are combined, because this
lane has already shipped one statistic that subtracted a FULL-BAND noise term
from a HIGH-PASS total (V-NOISE2 sec.5) and that defect reached M127's published
table.  Let B = [0.20, 0.25) cyc/px, and B_c = s * B for the comparator, whose
content is scaled by s (see BANDSHIFT below).

    bp(tile)     Parseval-normalised contrast^2 in the annulus   BAND-LIMITED
    F(L)         median bp over FLAT tiles AT LEVEL L            BAND-LIMITED
    S_d          bp(d) - F(level of d), per DETAIL tile d        BAND-LIMITED
    S_X          median over d of S_d                            BAND-LIMITED
    ratio        sqrt(S_enfuse / S_strehl)                       amplitude

Every term is band-limited to the same annulus.  There is no full-band quantity
anywhere in this file.  `h2.contrast_fft` divides by the tile mean, so exposure
and white point cancel and bp is in contrast^2 units.

THE KNOWN FAILURE MODE, which is why F exists.  Total band power counts NOISE as
detail: a noisier merge scores HIGHER.  `enfuse` is measured at 3.04x strehl's
luma noise on this subject, so the uncorrected reading is biased towards
`enfuse`, and the correction moves in strehl's favour -- the flattering
direction.  The uncorrected reading is therefore ALWAYS printed beside the
corrected one.

--------------------------------------------------------------------------------
THREE DEFECTS FOUND AND FIXED, all by arms whose answers were known in advance.
Recorded because two of them would have biased the verdict invisibly.

DEFECT 1 -- THE PLACEMENT SEARCH SILENTLY DROPPED A THIRD OF THE FRAME.
`Placer.place`'s bounds test read

    if (yb + b > self.rb.shape[0] or xb + b > self.mb.shape[0]
            or xb + b > self.rb.shape[1] or yb + b > self.mb.shape[1]):

-- the x index tested against the ROW count and the y index against the COLUMN
count.  With rb.shape = (1172, 1758) at 4x block means, `xb + b > 1172` rejects
every tile with x > 4432 in a 7032-px-wide frame.  It changed the tile
POPULATION rather than erroring, so it moved the medians and nothing complained.
Caught by the SCALE-PATH arm: with s = 1.0000 the search returned correlation
peak exactly 1.0000 and offset exactly 0/0 on every surviving tile -- literally
the same pixels as the baseline -- and yet S moved by 12%.  Identical pixels
cannot give a different answer, so the population had to have changed.

DEFECT 2 -- THE TWO ARMS WERE READ AT DIFFERENT TILE SIZES.  Matching the scene
AREA meant strehl at 256 px and the comparator at round(256/s) = 255 px.
MEASURED on strehl against itself, that one-pixel change moves S by +4.5%, and
t = 250 by +10.0%: the annulus is a discrete bin set and its membership is not
stable under tile size.  The comparator was the arm read at 255, so it was
inflated by ~4.5% -- against this project, but wrong either way.  Both arms are
now read at t = 256 and the comparator's BAND is scaled instead (BANDSHIFT),
which needs no resampling of any measured pixel.

DEFECT 3 -- A1 WAS FALSE, AND CATASTROPHICALLY SO.  The first design subtracted
the FLAT population median from the DETAIL population median, assuming equal
noise power in both.  MEASURED (leveldiag.py): FLAT tiles sit at luma 6302 and
DETAIL tiles at 10316.  Fitting bp ~ L^p over the FLAT population gives
p = -1.145 [-1.346, -0.947] for strehl and -0.920 [-0.984, -0.863] for enfuse --
both consistent with p = -1, which is exactly shot-noise-limited behaviour in
contrast units, and is what a linear sensor image must give.  Under the assumed
p = 0 the correction over-subtracted so hard that `enfuse`'s scene term
collapsed to 1.1e-07 against a total of 4.4e-05, and the ratio would have
printed 0.089 -- an absurdly flattering number this lane came within one failed
arm of reporting.

The repair does not model p.  It removes the need for one: each DETAIL tile is
matched to FLAT tiles at the SAME LEVEL, so whatever the level dependence is, it
cancels.  NOISE-ABS below plants noise whose level dependence is p = -2 by
construction and the matched estimator must still return 1.000; the unmatched
one does not, and both are printed so the repair is visible rather than claimed.

--------------------------------------------------------------------------------
COMMISSIONING -- every arm's answer is fixed before it is run, and a failure
blocks the verdict (the script returns 1 and prints no reading).

  IDENT-BITWISE  X against itself.  Exactly 1.000.  Determinism only: a
                 statistic compared with its own input returns 1 by arithmetic
                 and that is not evidence.  Reported and discounted.
  IDENT-PATH     k = 1.00 through the real plant.  1.000, with potency proven on
                 the k != 1 rungs rather than asserted.
  SCALE-PATH     strehl through the comparator's PLACEMENT path at s, same band.
                 1.000 -- same image, same band, and the search must return the
                 same pixels.  This is the arm that caught DEFECT 1.
  k=1.30         companion SHARPER.  Must return > 1.  A statistic bounded below
                 at parity passes a degradation ladder trivially, and this
                 project has already shipped a gauge perverse on its own arm.
  k=0.95..0.50   degradation ladder.  Must recover k.
  NOISE-PROP     THE ARM ORCH REQUIRED.  Gaussian noise at sigma = BETA * tile
                 mean, so added contrast power is identical at every level.  NO
                 detail change whatsoever.  The CORRECTED statistic must not
                 rise; the UNCORRECTED one MUST rise, or the plant is inert and
                 the arm proves nothing.  Both are printed.
  NOISE-ABS      the same noise at constant ABSOLUTE sigma -- level dependence
                 p = -2 by construction.  The level-matched estimator must
                 return 1.000 anyway.  The unmatched estimator is printed beside
                 it to show what the repair bought.
  NOISE+DETAIL   noise AND k = 0.70 together.  Must still recover 0.70.  The arm
                 that resembles the real comparison, where `enfuse` is both
                 noisier and possibly different in detail.

    python fullhp.py [key=119] [nboot=400]
"""
import json
import os
import sys

import numpy as np
from scipy.ndimage import zoom

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
import h2                                                        # noqa: E402
from h2h2b import Comp, T                                        # noqa: E402

import hd2                                                       # noqa: E402
from ladder import LP, plant                                     # noqa: E402

BAND = (0.2, 0.25)
W = (0.2126, 0.7152, 0.0722)
REG_D = 4                    # placement registration on 4x block means
REG_WIN = 8                  # +/- 8 blocks = +/- 32 px placement search
# BETA -- the noise plants' amplitude, sigma = BETA * level.  MEASURED choice,
# not a taste: noisediag.py swept it over 0.005-0.040 and found the estimator
# unbiased (mean within 2 standard errors of 1.000) at every value up to
# BETA = 0.020, where the plant already exceeds the signal it is planted on by
# 2.16x and raises the UNCORRECTED statistic to 1.48-1.67 -- unambiguously
# potent.  At BETA = 0.040 the plant is 8.65x the signal and BOTH noise arms
# acquire a real +12-16% bias.  A plant can be too potent to be informative:
# past a few times the signal the scene term is a difference of two large
# nearly-equal numbers and the arm measures the estimator's variance instead of
# its correctness.  AS_MAX below refuses any real reading that sits outside the
# range actually commissioned.
BETA = 0.020
NSEED = 8                    # noise arms are read over this many realisations
# AS_MAX -- the largest noise-to-signal ratio at which the noise arms have
# actually been MEASURED unbiased.  The reading below refuses to run outside it.
# noisediag.py mapped the onset: NOISE-PROP is clean to a/S = 4.24 and biased
# +5.5% at 5.53; NOISE-ABS -- the adversarial arm, whose plant is level-
# INDEPENDENT and so violates the fitted level dependence on purpose -- is clean
# at 2.16, +4.1% at 2.43, +7.5% at 3.11.  2.43 is the largest potency at which
# BOTH arms are still inside the 5% gate, so it is the limit.
AS_MAX = 2.43
# The residual systematic at that potency, [NOISE-PROP, NOISE-ABS] = [-0.3%,
# +4.1%], is DISCLOSED rather than corrected, and its direction is stated with
# it: the bias inflates the scene term of whichever arm carries more noise.
AS_BIAS = (-0.003, 0.041)
LOGTOL = 0.15                # level match: tricube kernel bandwidth in log level
KMIN = 3                     # a DETAIL tile needs this many FLAT tiles to match


def bandpower(crop, lo=BAND[0], hi=BAND[1]):
    """Parseval-normalised contrast^2 carried by the annulus [lo, hi) cyc/px.
    BAND-LIMITED by construction: nothing outside the annulus is summed."""
    t = crop.shape[0]
    f = h2.contrast_fft(crop)
    if f is None:
        return None
    r = h2.radial(t)
    norm = (t * t) ** 2 * (h2.window(t) ** 2).mean()
    p = (np.abs(f) ** 2) / norm
    return float(p[(r >= lo) & (r < hi)].sum())


def block_mean(a, d):
    h, w = a.shape[0] // d * d, a.shape[1] // d * d
    return a[:h, :w].reshape(h // d, d, w // d, d).mean((1, 3))


class Placer:
    """Per-tile integer placement of a comparator crop against strehl's.

    V-HEADTOHEAD2 sec.7: geometry is re-derived, not trusted.  geomfull.py
    measures ONE global offset for the pair; this refines it per tile, because a
    single global number is exactly the assumption sec.7 says not to make.

    The search runs on REG_D-fold block means, so the comparator is resampled
    only to FIND the placement.  The measured crop is always native pixels --
    sub-pixel resampling adds blur to the very quantity under test.
    """

    def __init__(self, ref, mov, scale):
        self.s = float(scale)
        self.rb = block_mean(ref.g, REG_D)
        mb = block_mean(mov.g, REG_D)
        self.mb = zoom(mb, self.s, order=3) if abs(self.s - 1.0) > 1e-9 else mb

    def place(self, y, x, t):
        """(y0, x0, peak, dy_px, dx_px) in the comparator's pixels, or None."""
        s = self.s
        b = t // REG_D
        yb, xb = y // REG_D, x // REG_D
        # DEFECT 1 was here: the axes were crossed, which silently dropped every
        # tile in the right third of the frame instead of raising.
        if yb + b > self.rb.shape[0] or xb + b > self.rb.shape[1]:
            return None
        R = self.rb[yb:yb + b, xb:xb + b]
        R = R - R.mean()
        rn = float(np.sqrt((R * R).sum()))
        if rn <= 0:
            return None
        best, bdy, bdx = -2.0, None, None
        for dy in range(-REG_WIN, REG_WIN + 1):
            ay = yb + dy
            if ay < 0 or ay + b > self.mb.shape[0]:
                continue
            for dx in range(-REG_WIN, REG_WIN + 1):
                ax = xb + dx
                if ax < 0 or ax + b > self.mb.shape[1]:
                    continue
                M = self.mb[ay:ay + b, ax:ax + b]
                M = M - M.mean()
                mn = float(np.sqrt((M * M).sum()))
                if mn <= 0:
                    continue
                c = float((R * M).sum()) / (rn * mn)
                if c > best:
                    best, bdy, bdx = c, dy, dx
        if bdy is None:
            return None
        # the offset is found in STREHL block units, because mb was zoomed onto
        # strehl's grid; converting to the comparator's own pixels divides it out
        y0 = int(round((y + bdy * REG_D) / s))
        x0 = int(round((x + bdx * REG_D) / s))
        return y0, x0, best, bdy * REG_D, bdx * REG_D


def tiles(comp, cells, band, placer=None, mutate=None, rng=None):
    """(levels, band powers) over a tile population.  Both arms are read at the
    SAME tile size T (DEFECT 2); the comparator's BAND is scaled instead."""
    lv, bp = [], []
    for (y, x) in cells:
        if placer is None:
            y0, x0 = int(y), int(x)
        else:
            pl = placer.place(int(y), int(x), T)
            if pl is None:
                continue
            y0, x0 = pl[0], pl[1]
        c, nc = comp.crop(y0, x0, T)
        if c is None or nc:
            continue
        if mutate is not None:
            c = mutate(c, rng)
        b = bandpower(c, band[0], band[1])
        if b is None or not np.isfinite(b) or b <= 0:
            continue
        lv.append(float(c.mean()))
        bp.append(b)
    return np.array(lv), np.array(bp)


def noise_at(L, lvF, bpF, bw=LOGTOL):
    """Noise band power expected at luma level L, estimated from FLAT tiles by
    weighted LOCAL LINEAR REGRESSION of band power on log(level), tricube
    kernel of bandwidth bw.

    DEFECT 3's repair, third iteration, and the two earlier ones are recorded
    because each was refuted by an arm rather than by taste.

      (a) median over a +/-16% level window     NOISE-ABS  +23.0%
          Noise going as L^-2 varies by a factor 1.8 across that window and the
          neighbours are not centred on the tile being corrected.
      (b) local linear fit in LOG-LOG           NOISE-ABS  -0.6%, PROP  +15.1%
          Exact for a pure power law, so it fixed NOISE-ABS -- but an added
          constant noise floor is not in the span of a log-space linear model,
          so NOISE-PROP broke in the opposite direction.  Two arms erring
          oppositely is what identified the basis as the fault.
      (c) this: band power LINEAR, level in log.  An added constant is in the
          span, so NOISE-PROP is exact by construction; a power law is a smooth
          curve the local fit tracks to first order over the window.

    Both noise arms are checked on every run, so neither repair can be adopted
    on the strength of the arm it was designed to pass.
    """
    x = np.log(lvF)
    x0 = float(np.log(L))
    u = (x - x0) / bw
    w = np.where(np.abs(u) < 1.0, (1.0 - np.abs(u) ** 3) ** 3, 0.0)
    m = w > 0
    if int(m.sum()) < KMIN:
        return None
    xs, ys, ws = x[m] - x0, bpF[m], w[m]
    sw = ws.sum()
    mx = (ws * xs).sum() / sw
    my = (ws * ys).sum() / sw
    vx = (ws * (xs - mx) ** 2).sum()
    if vx <= 0:
        return float(my)
    b = (ws * (xs - mx) * (ys - my)).sum() / vx
    return float(my + b * (0.0 - mx))


def scene_matched(lvD, bpD, lvF, bpF):
    """Per-DETAIL-tile scene power, with the noise estimated from FLAT tiles AT
    THE SAME LEVEL.  Whatever the level dependence of the noise is, evaluating
    the FLAT relation at the tile's own level cancels it without modelling it.

    Returns (per-tile S array, n_matched, n_dropped)."""
    if len(lvF) == 0:
        return np.array([]), 0, len(lvD)
    out, drop = [], 0
    for L, b in zip(lvD, bpD):
        n = noise_at(L, lvF, bpF)
        if n is None:
            drop += 1
            continue
        out.append(b - n)
    return np.array(out), len(out), drop


def scene_unmatched(bpD, bpF):
    """The estimator DEFECT 3 replaced: population medians, no level match.
    Kept only so the repair is visible in the NOISE-ABS arm."""
    return float(np.median(bpD) - np.median(bpF))


def ratio_of(sS, sE):
    if sS is None or sE is None or sS <= 0 or sE <= 0:
        return float("nan")
    return float(np.sqrt(sE / sS))


def boot_ratio(dS, dE, nboot, rng):
    """Bootstrap over the per-tile scene values of each arm."""
    out = []
    for _ in range(nboot):
        a = np.median(dS[rng.integers(0, len(dS), len(dS))])
        b = np.median(dE[rng.integers(0, len(dE), len(dE))])
        if a > 0 and b > 0:
            out.append(np.sqrt(b / a))
    if not out:
        return (float("nan"), float("nan"))
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


# ------------------------------------------------------------------ mutations
def mut_plant(k):
    return lambda c, rng: plant(c, k)


def mut_noise_prop(beta):
    return lambda c, rng: c + rng.normal(0.0, beta * float(c.mean()), c.shape)


def mut_noise_abs(sig):
    return lambda c, rng: c + rng.normal(0.0, sig, c.shape)


def mut_both(k, beta):
    def f(c, rng):
        p = plant(c, k)
        return p + rng.normal(0.0, beta * float(p.mean()), p.shape)
    return f


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    nboot = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    arm = os.path.join(hd2.ROOT, key, "arms")
    sp = os.path.join(arm, "strehl-full.tiff")
    ep = os.path.join(arm, "coh-enfuse-full.tif")
    for p in (sp, ep):
        if not os.path.exists(p):
            raise SystemExit(f"missing {p} -- run build_full.ps1 first")
    with open(os.path.join(hd2.ROOT, key, "geom-full.json"), encoding="utf-8") as fh:
        g = json.load(fh)
    for c in ("strehl-full_vs_strehl-A", "enfuse-full_vs_enfuse-A"):
        if not g[c].get("control_pass"):
            raise SystemExit(f"geomfull canvas control {c} FAILED -- refusing")
    s = float(g["strehl-full_vs_enfuse-full"]["scale"])
    BAND_C = (BAND[0] * s, BAND[1] * s)

    z = np.load(os.path.join(hd2.ROOT, key, "census.npz"))
    cells, emax = z["cells"], z["emax"]
    flat = [int(i) for i in z["flat"]]
    det = [int(i) for i in np.argsort(emax)[-len(flat):]]
    DET = [tuple(cells[i]) for i in det]
    FLAT = [tuple(cells[i]) for i in flat]

    S = Comp(dict(path=sp, weights=W))
    E = Comp(dict(path=ep, weights=W))
    rng = np.random.default_rng(20260827)

    print("=" * 104)
    print(f"FULLHP -- route 1: total band amplitude on the FULL merges, {key}")
    print("=" * 104)
    print(f"  strehl  {sp}")
    print(f"  enfuse  {ep}")
    print(f"  band {BAND[0]:.4f}-{BAND[1]:.4f} cyc/px on strehl; "
          f"{BAND_C[0]:.4f}-{BAND_C[1]:.4f} on enfuse (BANDSHIFT: content scale "
          f"{s:.4f},")
    print(f"  re-derived by geomfull.py with both canvas controls PASSing).  "
          f"Same SCENE frequencies, both arms")
    print(f"  read at t={T} native pixels -- no measured pixel is ever resampled.")
    print(f"  {len(DET)} DETAIL tiles, {len(FLAT)} FLAT tiles; noise matched on "
          f"level within {LOGTOL:.2f} in log, >= {KMIN} neighbours required.")
    print("  NO HALF-STACK IS READ ANYWHERE IN THIS FILE.")

    # BANDSHIFT magnitude, measured on strehl so its size is known not argued
    lvS, bpS = tiles(S, DET, BAND)
    _, bpS_c = tiles(S, DET, BAND_C)
    print(f"\n  BANDSHIFT magnitude, MEASURED on strehl's own DETAIL tiles: "
          f"reading band B_c instead of B")
    print(f"  changes median band power by "
          f"{np.median(bpS_c)/np.median(bpS) - 1:+.2%} "
          f"({np.sqrt(np.median(bpS_c)/np.median(bpS)) - 1:+.2%} in amplitude).")

    # -------------------------------------------------------- commissioning
    print()
    print("-" * 104)
    print("COMMISSIONING -- strehl-full against a mutated copy of ITSELF; "
          "every answer fixed in advance")
    print("-" * 104)
    lvF, bpF = tiles(S, FLAT, BAND)
    base_d, nm, nd = scene_matched(lvS, bpS, lvF, bpF)
    base_S = float(np.median(base_d))
    print(f"  strehl base: median bp DETAIL {np.median(bpS):.4e}  "
          f"FLAT {np.median(bpF):.4e}  level-matched S {base_S:.4e}")
    print(f"  level match: {nm}/{len(lvS)} DETAIL tiles matched, {nd} dropped "
          f"for having < {KMIN} FLAT tiles within {LOGTOL:.2f} in log level")
    print(f"  {'arm':16s} {'true':>7s} {'corrected':>11s} {'err':>8s} "
          f"{'uncorrected':>12s} {'UNMATCHED':>11s}  note")

    arms = [("IDENT-BITWISE", 1.0, None),
            ("IDENT-PATH", 1.0, mut_plant(1.0)),
            ("SHARPER k=1.30", 1.30, mut_plant(1.30)),
            ("k=0.95", 0.95, mut_plant(0.95)),
            ("k=0.85", 0.85, mut_plant(0.85)),
            ("k=0.70", 0.70, mut_plant(0.70)),
            ("k=0.50", 0.50, mut_plant(0.50))]
    noise_arms = [("NOISE-PROP", 1.0, lambda: mut_noise_prop(BETA)),
                  ("NOISE-ABS", 1.0,
                   lambda: mut_noise_abs(BETA * float(np.median(lvS)))),
                  ("NOISE+DETAIL", 0.70, lambda: mut_both(0.70, BETA))]
    comm, fails = {}, []
    base_un = scene_unmatched(bpS, bpF)
    for label, true, mut in arms:
        if mut is None:
            mlv, mbp, mlvF, mbpF = lvS, bpS, lvF, bpF
        else:
            mlv, mbp = tiles(S, DET, BAND, mutate=mut, rng=np.random.default_rng(7))
            mlvF, mbpF = tiles(S, FLAT, BAND, mutate=mut, rng=np.random.default_rng(8))
        md, _, _ = scene_matched(mlv, mbp, mlvF, mbpF)
        corr = ratio_of(base_S, float(np.median(md)))
        unc = float(np.sqrt(np.median(mbp) / np.median(bpS)))
        unm = ratio_of(base_un, scene_unmatched(mbp, mbpF))
        note = "determinism only; discounted" if label == "IDENT-BITWISE" else ""
        err = corr / true - 1 if np.isfinite(corr) else float("nan")
        if label != "IDENT-BITWISE" and not (abs(err) <= 0.10):
            fails.append(label)
        if label == "SHARPER k=1.30" and not (corr > 1.0):
            fails.append("SHARPER-perverse")
            note = "PERVERSE: bounded at parity"
        print(f"  {label:16s} {true:7.3f} {corr:11.4f} {err:+7.1%} "
              f"{unc:12.4f} {unm:11.4f}  {note}")
        comm[label] = {"true": true, "corrected": corr, "uncorrected": unc,
                       "unmatched": unm}

    # The noise arms are STOCHASTIC, so they are read over NSEED realisations
    # and judged against their own sampling spread.  A single draw compared
    # against a fixed gate cannot tell a broken estimator from a noisy one --
    # this arm read -4.9%, +15.1% and +20.3% under three estimators before
    # noisediag.py established that most of that was variance.
    for label, true, mkmut in noise_arms:
        vs, us, ns_ = [], [], []
        for sd in range(NSEED):
            mut = mkmut()
            mlv, mbp = tiles(S, DET, BAND, mutate=mut,
                             rng=np.random.default_rng(1000 + sd))
            mlvF, mbpF = tiles(S, FLAT, BAND, mutate=mut,
                               rng=np.random.default_rng(2000 + sd))
            md, _, _ = scene_matched(mlv, mbp, mlvF, mbpF)
            vs.append(ratio_of(base_S, float(np.median(md))))
            us.append(float(np.sqrt(np.median(mbp) / np.median(bpS))))
            ns_.append(ratio_of(base_un, scene_unmatched(mbp, mbpF)))
        v = np.array(vs, float)
        v = v[np.isfinite(v)]
        mu, sdv = float(v.mean()), float(v.std(ddof=1))
        se2 = 2 * sdv / np.sqrt(len(v))
        unc = float(np.mean(us))
        unm = float(np.nanmean(ns_)) if np.any(np.isfinite(ns_)) else float("nan")
        note = f"{len(v)} seeds, 2se {se2:.3f}"
        if unc <= 1.005:
            note = "INERT PLANT -- uncorrected did not rise, arm proves nothing"
            fails.append(label)
        if not (abs(mu / true - 1) <= 0.05):
            fails.append(label)
        print(f"  {label:16s} {true:7.3f} {mu:11.4f} {mu/true - 1:+7.1%} "
              f"{unc:12.4f} {unm:11.4f}  {note}")
        comm[label] = {"true": true, "corrected": mu, "sd": sdv, "2se": se2,
                       "uncorrected": unc, "unmatched": unm, "nseed": len(v)}

    # SCALE-PATH -- strehl through the comparator's PLACEMENT path, same band.
    Pself = Placer(S, S, s)
    plv, pbp = tiles(S, DET, BAND, placer=Pself)
    plvF, pbpF = tiles(S, FLAT, BAND, placer=Pself)
    pd, _, _ = scene_matched(plv, pbp, plvF, pbpF)
    sc_r = ratio_of(base_S, float(np.median(pd)))
    print(f"  {'SCALE-PATH':16s} {1.0:7.3f} {sc_r:11.4f} {sc_r - 1:+7.1%} "
          f"{'':>12s} {'':>11s}  placement path only, s={s:.4f}; "
          f"{len(pbp)}/{len(DET)} tiles")
    comm["SCALE-PATH"] = {"true": 1.0, "corrected": sc_r}
    if not (abs(sc_r - 1.0) <= 0.10):
        fails.append("SCALE-PATH")

    ok = not fails
    print(f"\n  COMMISSIONING: "
          f"{'PASS' if ok else 'FAIL -- ' + ', '.join(sorted(set(fails)))}")
    if not ok:
        print("  The instrument is not fit to answer the question.  "
              "Refusing to print a verdict.")
        return 1

    # ------------------------------------------------------------ the reading
    print()
    print("-" * 104)
    print("THE READING -- strehl-full vs enfuse-full")
    print("-" * 104)
    P = Placer(S, E, s)
    elv, ebp = tiles(E, DET, BAND_C, placer=P)
    elvF, ebpF = tiles(E, FLAT, BAND_C, placer=P)
    ed, enm, end_ = scene_matched(elv, ebp, elvF, ebpF)
    eS = float(np.median(ed))
    unc_ratio = float(np.sqrt(np.median(ebp) / np.median(bpS)))
    cor_ratio = ratio_of(base_S, eS)
    lo, hi = boot_ratio(base_d, ed, nboot, rng)

    # Does the REAL reading sit inside the regime the noise arms commissioned?
    # noisediag.py measured the estimator unbiased up to a noise-to-signal ratio
    # of AS_MAX and biased by +12-16% at 8.65.  Extrapolating past what was
    # commissioned is the thing this lane refuses to do, so it is a gate.
    as_s = (float(np.median(bpS)) - base_S) / base_S if base_S > 0 else np.inf
    as_e = (float(np.median(ebp)) - eS) / eS if eS > 0 else np.inf
    print(f"  {'':8s} {'bp DETAIL':>13s} {'bp FLAT':>13s} {'S (matched)':>13s} "
          f"{'lvl D':>8s} {'lvl F':>8s} {'n':>5s} {'drop':>5s} {'noise/S':>8s}")
    print(f"  {'strehl':8s} {np.median(bpS):13.4e} {np.median(bpF):13.4e} "
          f"{base_S:13.4e} {np.median(lvS):8.0f} {np.median(lvF):8.0f} "
          f"{nm:5d} {nd:5d} {as_s:8.2f}")
    print(f"  {'enfuse':8s} {np.median(ebp):13.4e} {np.median(ebpF):13.4e} "
          f"{eS:13.4e} {np.median(elv):8.0f} {np.median(elvF):8.0f} "
          f"{enm:5d} {end_:5d} {as_e:8.2f}")
    if max(as_s, as_e) > AS_MAX:
        print(f"\n  REFUSING: noise/S reaches {max(as_s, as_e):.2f}, outside "
              f"the {AS_MAX:.2f} the noise arms commissioned.")
        print(f"  Extend the commissioning before reading this pair.")
        return 1
    noisier = "enfuse" if as_e > as_s else "strehl"
    print(f"\n  potency check: both arms inside the commissioned "
          f"{AS_MAX:.2f}.  {noisier} carries the more noise "
          f"({max(as_s, as_e):.2f} vs {min(as_s, as_e):.2f}), so the measured")
    print(f"  residual systematic of [{AS_BIAS[0]:+.1%}, {AS_BIAS[1]:+.1%}] at "
          f"this potency inflates {noisier}'s scene term, i.e. it acts "
          f"{'AGAINST' if noisier == 'enfuse' else 'FOR'} strehl.")
    print()
    print(f"  enfuse detail amplitude / strehl's, UNCORRECTED "
          f"(counts noise as detail): {unc_ratio:.3f}")
    print(f"  enfuse detail amplitude / strehl's, CORRECTED  "
          f"(noise matched on level): {cor_ratio:.3f} [{lo:.3f}, {hi:.3f}] "
          f"95% CI, {nboot} bootstraps")

    # ---------------------------------------------------------- the verdict
    print()
    print("=" * 104)
    print("VERDICT -- against the branches registered in PREREGISTRATION.md "
          "sec.9 before any reading existed")
    print("=" * 104)
    ref = 2.017
    print(f"  half-stack C, same subject / band / arm:  {ref:.3f}")
    print(f"  full-render band amplitude, same:         {cor_ratio:.3f} "
          f"[{lo:.3f}, {hi:.3f}]")
    if np.isfinite(cor_ratio) and 0.90 <= cor_ratio <= 1.11 and lo <= 1.0 <= hi:
        branch, verdict = "LEVEL", (
            "LEVEL on the full render.  The 2.017 is NOT visible once the "
            "half-split is removed, so on this subject it is half-stack "
            "incoherence, not absent detail.")
    elif np.isfinite(cor_ratio) and cor_ratio >= 1.5:
        branch, verdict = "CONFIRMED", (
            "CONFIRMED on the full render.  The detail is genuinely absent "
            "from the delivered image; the incoherence story is dead.")
    else:
        branch, verdict = "PARTIAL", (
            "PARTIAL.  Neither pre-registered branch is satisfied; the gap is "
            "real but smaller than C reports.")
    print(f"  -> {branch}: {verdict}")

    print()
    print("  HOSTILE READING -- printed unconditionally, because LEVEL is the "
          "branch that flatters this project:")
    print(f"    1. the correction carries the answer: {unc_ratio:.3f} "
          f"uncorrected -> {cor_ratio:.3f} corrected.  The noise subtraction, "
          f"not the raw")
    print(f"       band power, is what produces this verdict.")
    print(f"    2. S is a difference of comparable numbers: FLAT/DETAIL band "
          f"power is {np.median(bpF)/np.median(bpS):.3f} for strehl and "
          f"{np.median(ebpF)/np.median(ebp):.3f} for enfuse.")
    print(f"       enfuse is 3.04x noisier here, so most of its DETAIL-tile "
          f"band power is its own noise, and the estimate is correspondingly "
          f"fragile.")
    print(f"    3. FLAT tiles are the bottom quartile of high-pass energy, not "
          f"zero, so S UNDER-states scene power in BOTH arms.  This biases the "
          f"ratio only if")
    print(f"       the two arms carry different scene power in flat regions.")
    print(f"    4. one subject, one band, one comparator.  Nothing here "
          f"generalises without being re-run.")

    out = {"key": key, "band": list(BAND), "band_comparator": list(BAND_C),
           "scale": s, "commissioning": comm, "commissioning_pass": ok,
           "strehl": {"bp_detail": float(np.median(bpS)),
                      "bp_flat": float(np.median(bpF)), "S": base_S,
                      "n_matched": nm, "n_dropped": nd},
           "enfuse": {"bp_detail": float(np.median(ebp)),
                      "bp_flat": float(np.median(ebpF)), "S": eS,
                      "n_matched": enm, "n_dropped": end_},
           "uncorrected_ratio": unc_ratio, "corrected_ratio": cor_ratio,
           "ci": [lo, hi], "half_stack_C": ref, "branch": branch,
           "verdict": verdict}
    dst = os.path.join(hd2.ROOT, f"fullhp-{key}.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  written {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
