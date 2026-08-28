"""Split-half frame-choice discordance: does the merge pick by noise?

WHAT ORCH ASKED FOR
-------------------
    "if the shipped weighting is over-selecting, then the merge's per-pixel
     frame choice should disagree between two independent half-stacks at a
     rate far above what the scene justifies, and that disagreement rate
     should rise with N."

That is a good test and it is the first one tonight that discriminates the
exponent hypothesis from alignment drift, because drift moves both halves the
same way (coherent error) while selection-on-noise moves them independently.

THE TRAP, WHICH IS WHY THIS FILE IS LONGER THAN THE STATISTIC
-------------------------------------------------------------
A focus stack cannot be split into two halves that see the same thing. Each
focus position is captured exactly once, so half A holds frames at one set of
focus positions and half B holds a set interleaved between them. "Did the two
halves pick the same frame" is therefore not a well-posed question: the frame
half A picked is not in half B.

Two consequences, both of which can manufacture a confirmation:

  1. The comparison has to be made in a coordinate both halves share. That
     coordinate is the ORIGINAL frame index, which is monotone in focus
     position, and the disagreement has to be read against the sampling step
     the split itself forces. A pixel whose true focus optimum lies between
     two sampled positions will be assigned different frames by the two
     halves and NOTHING IS WRONG. `disc_step` below is the fraction that
     disagree by MORE than one step of the half-stack's own sampling, so
     quantisation is not counted as a defect.

  2. Even then the floor is not zero and is not a property of the merge. In a
     region with no focus-dependent content the optimum does not exist, so
     every estimator disagrees there, including a perfect one. The floor is
     therefore set by HOW MUCH OF THE SUBJECT IS FLAT -- a subject property.
     Comparing discordance between subjects would rank subject difficulty,
     which is the exact error the absolute blotch statistic in the print gate
     makes and the reason this lane exists. So discordance is only ever
     compared ACROSS ARMS ON THE SAME SUBJECT AND THE SAME PIXELS.

`commission_metric()` measures both of these on a synthetic scene with a KNOWN
per-pixel focus optimum and no noise, rather than asserting them.

WHAT "FAR ABOVE WHAT THE SCENE JUSTIFIES" IS MEASURED AGAINST
-------------------------------------------------------------
Two references, both derived from the subject rather than assumed:

  * FLOOR: inject extra independent noise at several amplitudes, fit
    discordance against total variance, and extrapolate to zero variance. The
    intercept is the discordance the scene alone forces. This is an
    extrapolation below the measured range and is reported as one.
  * CEILING: the noise twin (`vn_manuf.synth`), a stack whose frames share one
    latent scene, so every frame is equally good and 100% of the selection is
    noise. Its discordance is what pure selection-on-noise looks like on this
    subject at this N.

The subject's position between floor and ceiling is the answer.

COHERENCE-IMMUNITY, WHICH ORCH REQUIRED
---------------------------------------
    "Any before/after you produce must include at least one statistic that
     cannot be moved by coherence alone."

Discordance IS a coherence statistic; it is defined on two half-renders. Every
row here therefore also carries statistics computed on the SINGLE full-N
render -- band power at fine and mottle scales, and blotch -- which no
relationship between the halves can touch, because the halves do not enter
them. `commission_perverse()` plants an improvement that is visible ONLY to
the coherence statistic and shows the full-render numbers do not move, so the
reporting rule "both must move" is demonstrated rather than promised.
"""
import io
import json
import os
import sys

import numpy as np

import vn_pyr as VP
from vn_manuf import synth
from vn_ninv2 import BANDS, FINE, MOTTLE, arm_merge, band_power, pick
from vn_noise import fit_variance_paired
from vn_plateau import BETA, SHIP, blotch
from vn_snrref import flatness, load

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\split"

# Pyramid levels examined. Level k carries structure near 2^(k+1) px, so the
# 20-60 px mottle band the convictions live in is levels 3-4 and the fine
# grain is levels 0-1. Carrying both is what lets a level-dependence be seen
# instead of assumed.
LEVELS = (1, 2, 3, 4)
ARMS = ("shipping", "confidence", "argmax", "mean")
# Extra-noise multipliers for the floor extrapolation. Variance factor is
# 1 + k^2, so these span 1.0x to 3.0x total variance.
KLAD = (0.0, 0.7071, 1.0, 1.4142)


def halves(idx):
    """Interleaved split. Both halves span the SAME focus range.

    Interleaving rather than front/back matters: a front/back split gives the
    two halves DISJOINT focus ranges, so they would disagree about focus
    everywhere by construction and the statistic would read ~1.0 on any input.
    """
    return list(idx[0::2]), list(idx[1::2])


def winner_z(Wl, idx):
    """Per-pixel winning frame, expressed in ORIGINAL full-stack index units.

    Returns (z, admitted). `admitted` is false where the weight column is
    entirely zero, i.e. where the merge admitted nothing and fell through to
    its unweighted fallback. Those pixels made no choice, so scoring them as
    agreement or as disagreement would both be wrong; they are excluded and
    counted.
    """
    adm = Wl.sum(axis=0) > 0.0
    a = Wl.argmax(axis=0)
    return np.asarray(idx, dtype=np.float64)[a], adm


def soft_z(Wl, idx):
    """Weighted centroid of focus position -- the SOFT frame choice.

    MEASURED REASON THIS EXISTS, and it is a finding rather than a detail.
    The hard winner is `argmax_i (r_i/SNR_REF)^p`, and x -> x^p is monotone
    increasing for every p > 0, so THE WINNER DOES NOT DEPEND ON THE
    EXPONENT AT ALL. Commissioning measured exactly that: at exponents 1.0,
    2.0 and 4.0 the argmax discordance on coffee-bubbles was 0.6191,
    0.6191 and 0.6191 -- bit-identical -- while n_eff moved 3.91 -> 2.08 ->
    2.03 and blotch moved 0.03019 -> 0.03464 -> 0.03660.

    So a statistic built on "which frame did it pick" is BLIND to the knob
    the fix in flight turns. The exponent does not change who wins, it
    changes how much the winner is worth. The quantity that responds is the
    centroid: as p rises the centroid collapses onto the winner, and as p
    falls it relaxes toward the mean of the admitted frames.
    """
    s = Wl.sum(axis=0)
    adm = s > 0.0
    z = np.asarray(idx, dtype=np.float64)[:, None, None]
    num = (Wl * z).sum(axis=0)
    return np.where(adm, num / np.maximum(s, 1e-30), np.nan), adm


def disc_stats(Wa, Wb, ia, ib, level, mask=None):
    """Discordance between two half-stacks at one pyramid level.

    `disc_rank` is the naive statistic -- did the two halves pick the same
    RANK within their own half. It is reported because it is what a direct
    reading of the brief produces, and because the synthetic commissioning
    shows it reads 0.4946 on a NOISE-FREE scene whose answer is perfectly
    determined, so it cannot go to zero even in principle.

    `disc_step` is the hard-winner version, disagreement larger than one step
    of the half-stack's own sampling, so the offset the split itself forces is
    not counted. It is exponent-invariant (see `soft_z`) and is reported as a
    control rather than as the measurement.

    `disc_soft` is the reported statistic: the same "beyond one step" rule
    applied to the WEIGHTED CENTROID of focus position, which does respond to
    selectivity.
    """
    za, aa = winner_z(Wa[level], ia)
    zb, ab = winner_z(Wb[level], ib)
    sa, _ = soft_z(Wa[level], ia)
    sb, _ = soft_z(Wb[level], ib)
    h = min(za.shape[0], zb.shape[0])
    w = min(za.shape[1], zb.shape[1])
    za, zb, aa, ab = za[:h, :w], zb[:h, :w], aa[:h, :w], ab[:h, :w]
    sa, sb = sa[:h, :w], sb[:h, :w]
    ra = Wa[level].argmax(axis=0)[:h, :w]
    rb = Wb[level].argmax(axis=0)[:h, :w]
    m = aa & ab
    if mask is not None:
        m = m & mask[:h, :w]
    tot = int(m.sum())
    if tot < 64:
        return None
    step = float(np.mean(np.diff(np.asarray(ia, dtype=np.float64)))) \
        if len(ia) > 1 else 1.0
    d = np.abs(za - zb)[m]
    ds = np.abs(sa - sb)[m]
    return dict(level=level, px=tot,
                both_admitted=float(m.sum()) / float(m.size),
                step=step,
                disc_rank=float(np.mean(ra[m] != rb[m])),
                disc_step=float(np.mean(d > step + 1e-9)),
                disc_soft=float(np.mean(ds > step + 1e-9)),
                med_soft=float(np.median(ds) / max(step, 1e-9)),
                med_steps=float(np.median(d) / max(step, 1e-9)),
                mean_steps=float(np.mean(d) / max(step, 1e-9)))


def recoh(reca, recb, level, mask=None):
    """Reproducibility of the OUTPUT, band by band.

    The two half-renders are two independent estimates of the same latent
    scene. Writing a = s + e_a and b = s + e_b with e independent between
    halves, the correlation of their band-`level` Laplacian coefficients is
    var(s)/(var(s)+var(e)). So `r` is the fraction of the band's variance
    that is REPRODUCIBLE and 1-r is the fraction that is manufactured by the
    merge's own choices.

    This is the statistic that speaks to the conviction directly. Mid-scale
    structure that is not reproducible across two independent halves of the
    same stack is not scene, whatever else it is.
    """
    la, _ = VP.lap_pyr(reca[:, :, 1].astype(np.float64), level + 1)
    lb, _ = VP.lap_pyr(recb[:, :, 1].astype(np.float64), level + 1)
    a, b = la[level], lb[level]
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    a, b = a[:h, :w], b[:h, :w]
    if mask is not None:
        m = mask[:h, :w]
        if m.sum() < 64:
            return None
        a, b = a[m], b[m]
    a = a.ravel() - a.mean()
    b = b.ravel() - b.mean()
    den = float(np.sqrt((a * a).sum() * (b * b).sum()))
    if den <= 0:
        return None
    return float((a * b).sum() / den)


def immune(rec, W, level=2, flat=None):
    """Statistics computed on ONE render, which coherence cannot move.

    Nothing here reads the halves. A change that only makes the two halves
    agree with each other leaves every one of these numbers exactly where it
    was, which is the point.

    `flat_l3` answers ORCH's caveat directly. If the incoherent mid-scale
    component were real scene detail merely landing incoherently, it would be
    PRESENT in the delivered image and a flat region would carry no more
    mid-scale variance than the scene has. If instead the merge is inventing
    it, the flat region's mid-scale variance rises above what an unweighted
    average of the same frames shows. That comparison is made on a single
    render per arm and is therefore immune to every coherence effect.
    """
    bp = band_power(rec)
    if W is None:
        ne = float("nan")
    else:
        nrm = W[level] / np.maximum(W[level].sum(axis=0, keepdims=True), 1e-30)
        s = W[level].sum(axis=0) > 0
        ne = np.where(s, 1.0 / np.maximum((nrm ** 2).sum(axis=0), 1e-30),
                      float(W[level].shape[0])).mean()
    out = dict(fine=bp["%.2f-%.2f" % FINE], mot=bp["%.2f-%.2f" % MOTTLE],
               blotch=float(blotch(rec)[0]), neff=float(ne),
               level_dn=float(rec[:, :, 1].mean()))
    if flat is not None:
        lp, _ = VP.lap_pyr(rec[:, :, 1].astype(np.float64), 4)
        for L in (1, 3):
            a = lp[L]
            m = flat[L][:a.shape[0], :a.shape[1]]
            out["flatvar_L%d" % L] = float(np.var(a[m]))
    return out


def run_pair(frames, idx, var0, arm, nb=7, mask=None, want_immune=True,
             flat=None):
    """Merge both halves and the full stack.

    Returns (row, Wa, Wb, ia, ib) so the caller can stratify off the SAME
    weight fields rather than merging again per stratum -- four levels times
    two half-merges was the first version and it tripled the run for nothing.
    """
    ia, ib = halves(idx)
    ra_, Wa = arm_merge(arm, [frames[i] for i in ia], var0, nb=nb)
    rb_, Wb = arm_merge(arm, [frames[i] for i in ib], var0, nb=nb)
    out = dict(arm=arm, N=len(idx), na=len(ia), nb_=len(ib))
    if arm == "mean":
        # Every weight is zero by construction, so there is no frame choice to
        # compare. Refusing the CHOICE statistics is the honest answer;
        # electing argmax of an all-zero column would return frame 0
        # everywhere and read as perfect agreement, which is the abstention
        # contamination this lane has already been bitten by once. The OUTPUT
        # reproducibility is still well defined and is kept, because it is the
        # anti-blur reference: a plain mean is maximally reproducible and must
        # still lose on detail.
        out["refused"] = "no frame choice exists under a plain mean"
        out["recoh"] = {str(L): recoh(ra_, rb_, L) for L in LEVELS}
        if want_immune:
            rec, W = arm_merge(arm, [frames[i] for i in idx], var0, nb=nb)
            out["immune"] = immune(rec, W, flat=flat)
        return out, Wa, Wb, ia, ib, ra_, rb_
    out["disc"] = [d for d in (disc_stats(Wa, Wb, ia, ib, L, mask)
                               for L in LEVELS) if d is not None]
    out["recoh"] = {str(L): recoh(ra_, rb_, L) for L in LEVELS}
    if want_immune:
        rec, W = arm_merge(arm, [frames[i] for i in idx], var0, nb=nb)
        out["immune"] = immune(rec, W, flat=flat)
    return out, Wa, Wb, ia, ib, ra_, rb_


def at(row, level, key="disc_step"):
    for d in row.get("disc", []):
        if d["level"] == level:
            return d[key]
    return None


# --------------------------------------------------------------------------
# COMMISSIONING
# --------------------------------------------------------------------------

def _blur(a, s):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, s)


def synth_focus(h=256, w=256, n=13, seed=3, flat_frac=0.5, noise=0.0):
    """A stack with a KNOWN per-pixel focus optimum and controllable flatness.

    The left `flat_frac` of the frame is a constant field: no focus-dependent
    content, so no estimator can determine a winner there. The right part
    carries texture whose best focus ramps top to bottom, so the true optimum
    is known per pixel and varies smoothly.

    Returns (frames, zstar, textured_mask).
    """
    rng = np.random.default_rng(seed)
    tex = rng.normal(0.0, 300.0, (h, w))
    tex = _blur(tex, 1.0)
    ys = np.arange(h)[:, None] / max(h - 1, 1)
    zstar = ys * (n - 1) + np.zeros((1, w))
    xcut = int(w * flat_frac)
    textured = np.zeros((h, w), dtype=bool)
    textured[:, xcut:] = True
    frames = []
    for t in range(n):
        # Spatially varying blur, done exactly by compositing a small set of
        # uniformly blurred versions and picking per pixel.
        sig = np.abs(zstar - t) * 0.55 + 0.35
        levels = np.unique(np.clip(np.round(sig / 0.35), 1, 24)) * 0.35
        acc = np.zeros((h, w))
        for s in levels:
            b = _blur(tex, s)
            sel = np.abs(sig - s) <= 0.35 / 2 + 1e-9
            acc = np.where(sel, b, acc)
        f = 1200.0 + np.where(textured, acc, 0.0)
        if noise > 0.0:
            f = f + rng.normal(0.0, noise, (h, w))
        frames.append(np.repeat(f[:, :, None], 3, axis=2))
    return frames, zstar, textured


def _metric_arm(noise, sig_var):
    frames, _, textured = synth_focus(noise=noise)
    idx = list(range(len(frames)))
    var0 = np.full(frames[0].shape[:2], sig_var)
    ia, ib = halves(idx)
    ra_, Wa = arm_merge("shipping", [frames[i] for i in ia], var0)
    rb_, Wb = arm_merge("shipping", [frames[i] for i in ib], var0)
    out = {}
    for name, msk in (("textured", textured), ("flat", ~textured)):
        for L in (2, 3):
            m = msk
            for _ in range(L):
                m = m[::2, ::2]
            d = disc_stats(Wa, Wb, ia, ib, L, m)
            d["recoh"] = recoh(ra_, rb_, L, m)
            out["%s_L%d" % (name, L)] = d
    return out


def commission_metric():
    """Measure the two structural claims instead of asserting them.

    PLANTED DETERMINACY (an improvement): on the textured half the focus
    optimum exists, is known, and the frames carry no noise, so a sound
    statistic must read near zero there.

    PLANTED INDETERMINACY (a defect): a flat region carrying only noise has no
    focus optimum at all, so a sound statistic must read HIGH there -- and it
    must do so with the merge behaving perfectly, which is the whole point. A
    statistic that cannot tell these apart is ranking subject difficulty, not
    merge quality.

    MEASURED REASON THE FLAT ARM CARRIES NOISE. The first version made the
    flat half a literal constant. A constant has zero Laplacian, so the merge
    admits nothing there, and the statistic scored 275 boundary pixels instead
    of the region -- it read 0.1055 and passed a bar it should have failed. A
    real flat region is not signal-free, it is signal-free AND noisy, and the
    admission decisions there are exactly what the hypothesis is about.
    """
    print("  [metric] synthetic scene with a KNOWN per-pixel focus optimum")
    sig = 40.0
    a0 = _metric_arm(0.0, 1.0)
    a1 = _metric_arm(sig, sig * sig)
    res = {}
    for tag, a in (("noisefree", a0), ("noisy", a1)):
        for kk, d in a.items():
            res["%s_%s" % (tag, kk)] = d
            print("    %-9s %-12s soft %.4f  hard %.4f  rank %.4f  "
                  "recoh %s  med %.2f steps  admitted %.3f  px %d"
                  % (tag, kk, d["disc_soft"], d["disc_step"], d["disc_rank"],
                     "%.4f" % d["recoh"] if d["recoh"] is not None else " n/a",
                     d["med_steps"], d["both_admitted"], d["px"]))
    ok = True
    for L in (2, 3):
        t = res["noisefree_textured_L%d" % L]["disc_soft"]
        if t > 0.05:
            print("    FAIL determinacy L%d: noise-free textured soft %.4f "
                  "> 0.05" % (L, t))
            ok = False
        rc = res["noisefree_textured_L%d" % L]["recoh"]
        if rc is None or rc < 0.95:
            print("    FAIL determinacy L%d: noise-free output "
                  "reproducibility %s < 0.95" % (L, rc))
            ok = False
    for L in (2, 3):
        f = res["noisy_flat_L%d" % L]["disc_soft"]
        t = res["noisy_textured_L%d" % L]["disc_soft"]
        if f < 3.0 * max(t, 0.05):
            print("    FAIL responsiveness L%d: noisy flat soft %.4f not "
                  ">= 3x noisy textured %.4f" % (L, f, t))
            ok = False
        rf = res["noisy_flat_L%d" % L]["recoh"]
        rt = res["noisy_textured_L%d" % L]["recoh"]
        if rf is None or rt is None or not rf < rt:
            print("    FAIL responsiveness L%d: flat reproducibility %s not "
                  "below textured %s" % (L, rf, rt))
            ok = False
    # THE TRAP, ON RECORD. `disc_rank` is what a direct reading of the brief
    # produces. It is reported next to the defensible statistic precisely
    # because it does NOT go to zero on a noise-free determinate scene, and a
    # test that cannot read zero when the answer is perfect cannot fail.
    naive = res["noisefree_textured_L2"]["disc_rank"]
    res["naive_on_perfect_input"] = naive
    print("    naive rank statistic on a noise-free determinate scene: "
          "%.4f  <- this is why it is not the reported number" % naive)
    if naive < 0.2:
        print("    NOTE: naive statistic was near zero here; the structural "
              "objection to it does not reproduce on this input")
    res["ok"] = ok
    print("    metric commissioning: %s" % ("ok" if ok else "FAILED"))
    return res


MIN_MARGIN = 0.01


def commission_arms(frames, var0, idx, masks):
    """Planted defect and planted improvement, on real data, PER STATISTIC.

    DEFECT: double the selection exponent. More selectivity on the same noisy
    quantity must make the soft choice less reproducible, must lower the
    output's reproducibility, and must also show up in the coherence-immune
    statistics.

    IMPROVEMENT: halve it. Everything must move the other way, or the
    statistic is not measuring selectivity.

    WHY THE GATE IS A MARGIN AND NOT A DIRECTION. The first version of this
    function asked only `defect > base`, and it was a coin flip. Whole-frame
    `recoh` moved by 1.3e-4 under a 4x exponent range on `coffee-bubbles`
    (0.7408 -> 0.7407, PASSED) and by 1.0e-4 the wrong way on `112MSDCF`
    (0.9780 -> 0.9781, FAILED). Those are the same null result and a boolean
    test reported them as opposite verdicts. A statistic that cannot resolve
    the largest plant available to me cannot resolve the 10-35% effects this
    section reports, so each side of the plant must now move its statistic by
    at least MIN_MARGIN in relative terms, and the margin is recorded so a
    reader can see how much headroom each number had.

    WHY ADMISSION IS PER STATISTIC. Refusing the whole subject because one of
    six statistics has no headroom would throw away five commissioned ones.
    `vn_lib.py` already admits per statistic for the same reason. A statistic
    that fails here is refused FOR THIS SUBJECT and every table marks it
    REFUSED; it is not silently omitted and not quietly reported.

    A PLANTED BLUR, because the exponent plant cannot commission the anti-blur
    denominator. Blurring the delivered render is the trade ORCH warned about
    -- it improves every raw mottle number. `fine` must fall, and the ratio
    var/fine must get WORSE, or my blur-immune statistic is not blur-immune
    and the whole anti-blur argument in this section is decoration.

    AND A PREDICTION THAT CAN FAIL. The hard argmax discordance must be
    EXACTLY equal across all three exponents, because x -> x^p is monotone and
    cannot reorder the frames. If that equality breaks, the claim in `soft_z`
    about why the naive test is blind is wrong, and this run must refuse
    rather than report a soft statistic justified by a false premise.
    """
    print("  [arms] planted defect (2x exponent) and improvement (0.5x)")
    ia, ib = halves(idx)
    flat = {L: masks[L]["flat"] for L in (1, 3)}
    out = {}
    for tag, mult in (("base", 1.0), ("defect", 2.0), ("improve", 0.5)):
        cfg = dict(SHIP)
        cfg["exponent"] = SHIP["exponent"] * mult
        cfg["_clamp"] = {}
        ra_, Wa = VP.merge([frames[i] for i in ia], cfg, BETA, var0)
        rb_, Wb = VP.merge([frames[i] for i in ib], cfg, BETA, var0)
        rec, W = VP.merge([frames[i] for i in idx], cfg, BETA, var0)
        d = disc_stats(Wa, Wb, ia, ib, 3)
        im = immune(rec, W, flat=flat)
        v = dict(soft=d["disc_soft"],
                 recoh_all=recoh(ra_, rb_, 3),
                 recoh_flat=recoh(ra_, rb_, 3, masks[3]["flat"]),
                 recoh_detail=recoh(ra_, rb_, 3, masks[3]["detail"]),
                 blotch=im["blotch"],
                 flatvar=im.get("flatvar_L3"),
                 fine=im["fine"])
        out[tag] = dict(disc=d, immune=im, stats=v)
        if tag == "base":
            out["_base_render"] = rec
        print("    %-8s p=%.2f  soft %.4f  hard %.4f  recohA %.4f  "
              "recohF %.4f  blotch %.5f  flatvar %.1f  neff %.2f"
              % (tag, cfg["exponent"], v["soft"], d["disc_step"],
                 v["recoh_all"], v["recoh_flat"], v["blotch"],
                 v["flatvar"], im["neff"]))

    # Direction each statistic must move under MORE selectivity.
    UP = ("soft", "blotch", "flatvar")
    DOWN = ("recoh_all", "recoh_flat", "recoh_detail")
    admit, margins = {}, {}
    print("    %-12s %10s %10s %10s   %s"
          % ("statistic", "defect", "improve", "min margin", "admitted"))
    for k in UP + DOWN:
        b = out["base"]["stats"][k]
        dfc = out["defect"]["stats"][k]
        imp = out["improve"]["stats"][k]
        sgn = 1.0 if k in UP else -1.0
        md = sgn * (dfc - b) / abs(b)
        mi = -sgn * (imp - b) / abs(b)
        ok = (md >= MIN_MARGIN) and (mi >= MIN_MARGIN)
        admit[k], margins[k] = bool(ok), [float(md), float(mi)]
        print("    %-12s %+9.4f%% %+9.4f%% %9.2f%%   %s"
              % (k, 100 * md, 100 * mi, 100 * MIN_MARGIN,
                 "yes" if ok else "REFUSED"))

    # The planted blur: commissions `fine` and the blur-immune ratio.
    #
    # SWEPT, because the first version used a single sigma=1.2 and that plant
    # was too strong to be informative: it removed 100.00% of the fine band
    # and drove var/fine to +2.06e6%, which any statistic that reads the fine
    # band at all would have passed. A gate whose plant is far larger than the
    # effect being reported cannot distinguish a sensitive instrument from a
    # crude one. The fix under test costs ~28% of the fine band, so the plant
    # must fire well below that, and the smallest sigma at which it still
    # fires is published next to the gate rather than assumed.
    from scipy.ndimage import gaussian_filter
    rec = out.pop("_base_render")
    b0 = out["base"]["stats"]
    e0 = b0["flatvar"] / b0["fine"]
    sweep, fired = [], None
    for sg in (0.10, 0.15, 0.20, 0.30, 0.50, 0.80, 1.20):
        bl = np.stack([gaussian_filter(rec[..., c], sg)
                       for c in range(rec.shape[2])], axis=2)
        bim = immune(bl, None, flat=flat)
        d_fine = (bim["fine"] - b0["fine"]) / b0["fine"]
        d_var = (bim["flatvar_L3"] - b0["flatvar"]) / b0["flatvar"]
        d_eff = (bim["flatvar_L3"] / bim["fine"] - e0) / e0
        hit = (d_fine < -MIN_MARGIN) and (d_var < 0.0) and (d_eff > MIN_MARGIN)
        sweep.append(dict(sigma=sg, d_fine=float(d_fine), d_var=float(d_var),
                          d_eff=float(d_eff), fires=bool(hit)))
        print("    [blur plant] sigma %.2f  fine %+8.2f%%  flat mid-band var "
              "%+7.2f%%  var/fine %+10.2f%%  %s"
              % (sg, 100 * d_fine, 100 * d_var, 100 * d_eff,
                 "fires" if hit else "-"))
        if hit and fired is None:
            fired = sg
    blur_ok = fired is not None
    print("    blur plant: %s (smallest sigma that fires: %s)"
          % ("ok" if blur_ok else "FAILED",
             "%.2f px" % fired if fired else "none"))
    admit["fine"] = bool(blur_ok)
    admit["efficiency"] = bool(blur_ok)
    margins["blur_sweep"] = sweep
    margins["blur_breakdown_sigma"] = fired

    hard = [out[t]["disc"]["disc_step"] for t in ("base", "defect", "improve")]
    inv = max(hard) - min(hard)
    out["hard_spread"] = float(inv)
    print("    hard-winner spread across a 4x exponent range: %.2e   "
          "<- predicted to be exactly 0" % inv)
    ok = True
    if inv > 1e-12:
        print("    FAIL: the argmax statistic moved with the exponent; the "
              "stated reason for replacing it is wrong")
        ok = False
    if not any(admit.values()):
        print("    FAIL: no statistic survived its own plant")
        ok = False
    out["admit"] = admit
    out["margins"] = margins
    out["ok"] = bool(ok)
    print("    arm commissioning: %s (%d of %d statistics admitted)"
          % ("ok" if ok else "FAILED", sum(admit.values()), len(admit)))
    return out


def commission_perverse(frames, var0, idx):
    """An improvement visible ONLY to the coherence statistic.

    Feed both "halves" the SAME frames. Discordance collapses to zero because
    the two weight fields are identical -- and not one thing about the
    delivered image has changed, because the full-N render never touched the
    halves. This is the failure mode ORCH warned the two lanes closest to the
    fix about, built deliberately so the reporting rule can be checked rather
    than promised.

    The zero is a suspiciously round number, so it is followed by a variant
    that perturbs one copy with independent noise. If that also returned zero
    the statistic would be short-circuiting rather than predicting.
    """
    print("  [perverse] coherence-only improvement")
    ia, _ = halves(idx)
    ra_, Wa = arm_merge("shipping", [frames[i] for i in ia], var0)
    d_same = disc_stats(Wa, Wa, ia, ia, 3)
    rc_same = recoh(ra_, ra_, 3)
    rng = np.random.default_rng(7)
    sig = float(np.sqrt(np.maximum(var0, 0.0)).mean())
    pert = [frames[i] + rng.normal(0.0, sig, frames[i].shape) for i in ia]
    rp_, Wp = arm_merge("shipping", pert, var0)
    d_pert = disc_stats(Wa, Wp, ia, ia, 3)
    rc_pert = recoh(ra_, rp_, 3)
    rec, W = arm_merge("shipping", [frames[i] for i in idx], var0)
    im = immune(rec, W)
    print("    same frames both sides : soft %.4f  recoh %.4f   "
          "<- coherence-only 'improvement'"
          % (d_same["disc_soft"], rc_same))
    print("    one side re-noised     : soft %.4f  recoh %.4f   "
          "<- proves both are predictions, not short circuits"
          % (d_pert["disc_soft"], rc_pert))
    print("    full-render blotch     : %.5f  fine %.3e   "
          "<- unchanged by either, by construction"
          % (im["blotch"], im["fine"]))
    ok = (d_same["disc_soft"] < 1e-9 and rc_same > 1.0 - 1e-9
          and d_pert["disc_soft"] > 0.02 and rc_pert < 0.999)
    if not ok:
        print("    FAIL: perverse control did not behave as specified")
    print("    perverse commissioning: %s" % ("ok" if ok else "FAILED"))
    return dict(same=d_same, pert=d_pert, recoh_same=rc_same,
                recoh_pert=rc_pert, immune=im, ok=bool(ok))


# --------------------------------------------------------------------------
# FLOOR AND CEILING
# --------------------------------------------------------------------------

def noise_floor(frames, idx, var0, arm="shipping", level=3, seed=11):
    """Extrapolate discordance to zero noise variance.

    Independent extra noise at k*sigma raises total variance by (1+k^2). If
    discordance is driven by noise it must fall with the added noise removed;
    the intercept of a straight-line fit is the discordance the SCENE forces.

    Reported as an extrapolation below the measured range, because it is one.
    """
    rng = np.random.default_rng(seed)
    ia, ib = halves(idx)
    sig = np.sqrt(np.maximum(var0, 0.0))
    xs, ys = [], []
    for k in KLAD:
        fa = [frames[i] if k == 0.0 else
              frames[i] + rng.normal(0.0, 1.0, frames[i].shape) * (k * sig)[:, :, None]
              for i in ia]
        fb = [frames[i] if k == 0.0 else
              frames[i] + rng.normal(0.0, 1.0, frames[i].shape) * (k * sig)[:, :, None]
              for i in ib]
        _, Wa = arm_merge(arm, fa, var0 * (1.0 + k * k))
        _, Wb = arm_merge(arm, fb, var0 * (1.0 + k * k))
        d = disc_stats(Wa, Wb, ia, ib, level)
        xs.append(1.0 + k * k)
        ys.append(d["disc_soft"])
        print("    var x%.2f  soft %.4f  hard %.4f"
              % (1.0 + k * k, d["disc_soft"], d["disc_step"]))
    A = np.vstack([np.ones(len(xs)), np.array(xs)]).T
    coef, res_, *_ = np.linalg.lstsq(A, np.array(ys), rcond=None)
    pred = A @ coef
    ss = float(np.sum((np.array(ys) - pred) ** 2))
    tot = float(np.sum((np.array(ys) - np.mean(ys)) ** 2))
    return dict(var_factors=xs, disc=ys, intercept=float(coef[0]),
                slope=float(coef[1]),
                r2=float(1.0 - ss / tot) if tot > 0 else None,
                level=level, arm=arm)


def noise_ceiling(frames, idx, var0, arm="shipping", level=3):
    """Discordance when 100% of the selection is noise.

    `synth` builds a stack whose frames share ONE latent scene, so no frame is
    genuinely better than another and every admission decision is noise. This
    is the top of the scale on this subject at this N.
    """
    syn = synth([frames[i] for i in idx], var0)
    ja = list(range(0, len(idx), 2))
    jb = list(range(1, len(idx), 2))
    ra_, Wa = arm_merge(arm, [syn[j] for j in ja], var0)
    rb_, Wb = arm_merge(arm, [syn[j] for j in jb], var0)
    d = disc_stats(Wa, Wb, [idx[j] for j in ja], [idx[j] for j in jb], level)
    d["recoh"] = recoh(ra_, rb_, level)
    return d


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = {}
    for i, a in enumerate(sys.argv[1:]):
        if a == "--px":
            opts["crop"] = int(sys.argv[i + 2])
    subj = args[0] if args else "coffee-bubbles"
    crop = opts.get("crop", int(args[1]) if len(args) > 1 else 0)
    frames = load(subj)
    if crop:
        h, w = frames[0].shape[:2]
        y0, x0 = (h - crop) // 2, (w - crop) // 2
        frames = [f[y0:y0 + crop, x0:x0 + crop] for f in frames]
    n = len(frames)
    print("SPLIT-HALF DISCORDANCE  %s  n=%d  %dx%d"
          % (subj, n, frames[0].shape[0], frames[0].shape[1]))

    var0, read2, g = fit_variance_paired(frames)
    print("  sigma %.3f DN (paired fit; read2 %.1f gain %.5f)"
          % (float(np.sqrt(var0).mean()), read2, g))

    # Flatness stratification. The hypothesis says the excess lives where the
    # focus response is flat, so this is the conditional test rather than a
    # decoration. Built BEFORE commissioning because the arm gate has to test
    # the flat-restricted statistic that the conviction actually quotes, not
    # a whole-frame one diluted by detail pixels.
    fl, _ = flatness(frames)
    masks = {}
    for L in LEVELS:
        f = fl
        for _ in range(L):
            f = VP.reduce_(f)
        q = np.quantile(f, [0.25, 0.75])
        masks[L] = dict(flat=f <= q[0], detail=f >= q[1])

    print("\nCOMMISSIONING")
    cm = commission_metric()
    idx_full = pick(n, n)
    ca = commission_arms(frames, var0, idx_full, masks)
    cp = commission_perverse(frames, var0, idx_full)
    if not (cm["ok"] and ca["ok"] and cp["ok"]):
        print("\nREFUSED: commissioning failed; no measurement reported")
        return 2

    ks = sorted({n, max(2, n // 2), max(2, n // 4)}, reverse=True)
    rows, refused = [], 0
    print("\nLADDER")
    for arm in ARMS:
        for k in ks:
            idx = pick(n, k)
            r, Wa, Wb, ia, ib, ra_, rb_ = run_pair(
                frames, idx, var0, arm, flat={L: masks[L]["flat"]
                                              for L in (1, 3)})
            strat = {}
            for L in LEVELS:
                for tag in ("flat", "detail"):
                    rc = recoh(ra_, rb_, L, masks[L][tag])
                    if rc is not None:
                        strat["recoh_%s_L%d" % (tag, L)] = rc
                    if "refused" in r:
                        continue
                    d = disc_stats(Wa, Wb, ia, ib, L, masks[L][tag])
                    if d is not None:
                        strat["%s_L%d" % (tag, L)] = d["disc_soft"]
                        strat["adm_%s_L%d" % (tag, L)] = d["both_admitted"]
            r["strat"] = strat
            rows.append(r)
            if "refused" in r:
                # Refused for the CHOICE statistics only. The output
                # reproducibility is still defined and is kept, because a
                # plain mean is the anti-blur reference: it is maximally
                # reproducible and must still lose on detail.
                refused += 1
                print("  %-11s N=%-3d REFUSED choice | recohL3 %.4f "
                      "flat %.4f det %.4f | blotch %.5f fine %.3e"
                      % (arm, k, r["recoh"]["3"],
                         strat.get("recoh_flat_L3", float("nan")),
                         strat.get("recoh_detail_L3", float("nan")),
                         r["immune"]["blotch"], r["immune"]["fine"]))
                continue
            print("  %-11s N=%-3d soft L1 %.4f L2 %.4f L3 %.4f L4 %.4f | "
                  "recohL3 %.4f flat %.4f det %.4f | adm %.3f | "
                  "blotch %.5f fine %.3e"
                  % (arm, k, at(r, 1, "disc_soft"), at(r, 2, "disc_soft"),
                     at(r, 3, "disc_soft"), at(r, 4, "disc_soft"),
                     r["recoh"]["3"],
                     strat.get("recoh_flat_L3", float("nan")),
                     strat.get("recoh_detail_L3", float("nan")),
                     at(r, 3, "both_admitted"),
                     r["immune"]["blotch"], r["immune"]["fine"]))

    print("\nFLOOR (extrapolate to zero noise variance), shipping, L3, N=%d"
          % ks[0])
    fl_ = noise_floor(frames, pick(n, ks[0]), var0)
    print("  intercept %.4f  slope %.4f/var  r2 %s"
          % (fl_["intercept"], fl_["slope"],
             "%.4f" % fl_["r2"] if fl_["r2"] is not None else "n/a"))

    print("\nCEILING (noise twin: 100%% of selection is noise), L3")
    print("  The N-ladder confounds two things: raising N raises the number "
          "of near-ties AND\n  the number of frames in each half. The twin "
          "carries the SAME half sizes and the\n  same sampling step at every "
          "rung, so obs/ceiling is the half-size-controlled\n  reading and "
          "the raw ladder is not.")
    ce = {}
    for k in ks:
        c = noise_ceiling(frames, pick(n, k), var0)
        ce[str(k)] = c
        ship = [r for r in rows if r["arm"] == "shipping" and r["N"] == k][0]
        obs = at(ship, 3, "disc_soft")
        print("  N=%-3d twin soft %.4f  recoh %.4f | shipping %.4f  "
              "obs/ceiling %.4f"
              % (k, c["disc_soft"], c["recoh"], obs,
                 obs / max(c["disc_soft"], 1e-9)))
        ce[str(k)]["obs_over_ceiling"] = float(
            obs / max(c["disc_soft"], 1e-9))

    print("\nMANUFACTURED MID-SCALE FRACTION (flat pixels, L3) AND WHAT THE "
          "FIX REMOVES")
    print("  1 - recoh is the share of the band's variance that is NOT "
          "reproducible across\n  two independent halves of the same stack. "
          "Fine-band power is carried on the same\n  pixels so a reduction "
          "bought by blurring is visible in the same row.")
    summ = {}
    for k in ks:
        base = None
        print("  N=%d" % k)
        for arm in ARMS:
            rr = [r for r in rows if r["arm"] == arm and r["N"] == k]
            if not rr:
                continue
            rr = rr[0]
            rc = rr["strat"].get("recoh_flat_L3")
            if rc is None:
                continue
            man = 1.0 - rc
            if arm == "shipping":
                base = man
            rem = (base - man) / base if base and base > 0 else float("nan")
            summ["%s_N%d" % (arm, k)] = dict(
                manufactured=float(man), removed=float(rem),
                fine=rr["immune"]["fine"], blotch=rr["immune"]["blotch"],
                flatvar_L3=rr["immune"].get("flatvar_L3"),
                flatvar_L1=rr["immune"].get("flatvar_L1"))
            print("    %-11s manufactured %.4f  removed vs shipping %+.1f%%"
                  "  fine %.3e (%+.1f%%)  blotch %.5f  "
                  "flatvar L3 %.4g L1 %.4g"
                  % (arm, man, 100.0 * rem, rr["immune"]["fine"],
                     100.0 * (rr["immune"]["fine"]
                              / summ["shipping_N%d" % k]["fine"] - 1.0),
                     rr["immune"]["blotch"],
                     rr["immune"].get("flatvar_L3", float("nan")),
                     rr["immune"].get("flatvar_L1", float("nan"))))
        mn = summ.get("mean_N%d" % k)
        sh = summ.get("shipping_N%d" % k)
        if mn and sh and mn["flatvar_L3"]:
            # Coherence-immune, single render per arm, same pixels. In a flat
            # region every frame is equally informative, so the unweighted
            # mean is the minimum-variance combination and its flat mid-band
            # variance is the floor. Anything above that floor is structure
            # the weighting put there.
            print("    -> shipping flat mid-band variance is %.2fx the plain "
                  "mean's on the SAME pixels" % (sh["flatvar_L3"]
                                                 / mn["flatvar_L3"]))
            summ["excess_over_mean_N%d" % k] = float(
                sh["flatvar_L3"] / mn["flatvar_L3"])

    measured = len(rows) - refused
    print("\n%d examined = %d measured + %d refused"
          % (len(rows), measured, refused))

    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, "%s.json" % subj), "w",
                 encoding="utf-8") as f:
        json.dump(dict(subject=subj, n=n, ks=ks,
                       shape=list(frames[0].shape[:2]),
                       sigma=float(np.sqrt(var0).mean()),
                       rows=rows, floor=fl_, ceiling=ce, summary=summ,
                       commission=dict(metric=cm, arms=ca, perverse=cp),
                       counts=dict(examined=len(rows), measured=measured,
                                   refused=refused)), f, indent=1)
    print("wrote %s" % os.path.join(OUT, "%s.json" % subj))
    return 0


if __name__ == "__main__":
    sys.exit(main())
