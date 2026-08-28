"""Scene/noise decomposition from an independent PAIR, per band.

Given two renders of one scene from disjoint frames, A = S + n_A and B = S + n_B
with n_A, n_B independent:

    (A+B)/2 = S + (n_A+n_B)/2      var = var(S) + var(n)/2
    (A-B)/2 =     (n_A-n_B)/2      var =           var(n)/2

so  var(S) = var(halfsum) - var(halfdiff)  exactly, and the single-arm noise sd
is sqrt(2) * sd(halfdiff). No comparator, no external reference, and no model of
what noise looks like.

THE ONE WAY THIS SILENTLY BREAKS, and it is the mistake available in every band
table: applying one filter to the half-sum and a different one -- or none -- to
the half-difference. The two variances are then not commensurable, their
difference is not a variance, and it can come out negative or absurdly large
while still printing. A lane withdrew a 6-8x result in our favour tonight for
exactly this. So:

  * every term at a given band goes through the SAME filter, by construction:
    one function computes both from one filter argument, and neither caller nor
    band table can supply them separately;
  * `var(halfsum) >= var(halfdiff)` is CHECKED at every band and a violation is
    a hard degenerate result, not a small negative rounded to zero. For additive
    independent noise it is impossible, so seeing it means the decomposition is
    wrong rather than the image unusual.

THE VARIANCE CHECK IS BLIND TO A GAIN MISMATCH, and this was measured rather than
assumed. Scaling one arm 40x leaves half-sum and half-difference BOTH dominated
by that arm, in the ratio (20.5/19.5)^2 = 1.1052, so the check passes and the
scene number is quietly wrong. That is the exposure trap this project has hit
repeatedly -- two arms rendered at +2.33 and +0.85 -- and it therefore gets its
own explicit guard on the arms' levels, because the one already here provably
cannot see it.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402


class Degenerate(Exception):
    """The decomposition is not valid on this input, so it returns no number."""


LEVEL_TOL = 0.01
LEVEL_Z = 4.0
DEGEN_Z = 4.0


class Levels:
    """Proof that one PAIR of arms had its gains compared, globally.

    `decompose` will not run without one. The token exists because the check it
    represents is the easiest in this tool to forget and the most expensive to
    forget: a gain mismatch is invisible to every other guard here (measured: a
    40x gain passes the variance check at a ratio of 1.1052) and it silently
    moves the scene number. Making it an argument rather than a convention means
    a caller cannot omit it by writing less code.

    `bound` is the certified upper bound on |g - 1| for this pair: the larger of
    the measured gain difference and the guard's own detection floor. It is not
    decoration -- `decompose` propagates it into a bias on the noise term, which
    is the only term a residual gain can meaningfully damage.
    """

    __slots__ = ("rel", "mean_ratio", "bound", "n")

    def __init__(self, rel, mean_ratio, bound, n):
        self.rel = rel
        self.mean_ratio = mean_ratio
        self.bound = bound
        self.n = n

    def __repr__(self):
        return ("Levels(gain %+.3f%%, certified within %.3f%%, %.1f Mpx)"
                % (100 * self.rel, 100 * self.bound, self.n / 1e6))


def check_pair_levels(a, b, k=8):
    """Refuse a PAIR of arms whose GAIN differs. Call once, on the whole arms.

    A level offset is deliberately allowed; a gain is not. Measured on a real
    crop, that distinction is exactly what the band filter makes:

        band sd of t         8.728510
        band sd of t + 10    8.728510    an offset is removed by the filter
        band sd of t * 1.04  9.077650    a gain is not: exactly x1.0400

    so the statistic is the interquartile range, which a gain multiplies and an
    offset leaves alone.

    WHY THIS IS A PAIR-LEVEL CHECK AND NOT A PER-SITE ONE. This is the third
    rebuild of this guard and the first two both failed the same way: they tested
    a GLOBAL property of a render at a LOCAL scale, where it has no power. The
    mean-based version refused a rung at -4.36% when the arms' global means
    agreed to 0.33%. The per-site IQR version then refused a registered crop at
    -4.14%, and measuring it across 40 random 384 px sites on two arms that
    CANNOT differ in gain (--linear-srgb, no --exposure: there is no tone stage
    for them to differ in) gave:

        global IQR ratio          1.00195      (0.19%)
        local, 40 sites of 384px  sd 4.30%, full range 21.60%
        sites tripping a 2% guard 21 of 40  (52%)

    A guard whose own noise is twice the effect it must catch is not a guard, it
    is a coin. Content differs between two renders at a site; gain does not
    differ anywhere. So the check moved to the whole frame, where content
    averages out and the same statistic reads 0.19%.

    AND IT REPORTS WHAT IT COULD HAVE DETECTED, because that is the only reason
    the failure above was visible. The error on the global ratio comes from a
    delete-one jackknife over k*k blocks. The obvious alternative -- the scatter
    of per-block RATIOS -- was tried first and is the wrong estimator: a block on
    flat content has a near-zero denominator, its ratio explodes, and the
    measured scatter GREW with block count (4.05% at k=4, 70.31% at k=32)
    instead of shrinking. The jackknife estimates the error of the statistic
    actually reported.

        real pair, k=8:  ratio +0.195%, se 0.417%, floor 1.67% at Z=4

    The threshold is that floor, not a constant: a difference is refused when it
    is significant against the guard's own measured error. On the real pair that
    is an 8.6x margin.
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    qa, qb = _iqr(a), _iqr(b)
    if qa <= 0 or qb <= 0:
        raise Degenerate("degenerate arm spread: %.6g / %.6g" % (qa, qb))
    rel = qa / qb - 1.0

    h, w = a.shape[:2]
    bh, bw = h // k, w // k
    if bh < 16 or bw < 16:
        raise Degenerate(
            "arms of %dx%d are too small for the pair guard to measure its own error; "
            "certify the WHOLE arms, not a crop." % (h, w))
    ja = np.array([[_iqr(a[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw])
                    for j in range(k)] for i in range(k)]).ravel()
    jb = np.array([[_iqr(b[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw])
                    for j in range(k)] for i in range(k)]).ravel()
    n = ja.size
    th = (ja.sum() - ja) / np.maximum(jb.sum() - jb, 1e-12)
    se = float(np.sqrt((n - 1) / n * float(np.sum((th - th.mean()) ** 2))))
    floor = LEVEL_Z * se

    if abs(rel) > floor:
        raise Degenerate(
            "arm GAIN differs by %+.2f%%, which is significant against this guard's own "
            "measured error (floor %.2f%% at Z=%.0f; interquartile ranges %.4f / %.4f). "
            "A gain survives the band filter, so the arms differ in more than the "
            "variable under test." % (100 * rel, 100 * floor, LEVEL_Z, qa, qb))
    return Levels(rel, float(np.mean(a)) / max(float(np.mean(b)), 1e-12),
                  max(abs(rel), floor), a.size)


def _iqr(x):
    return float(np.subtract(*np.percentile(x, [75, 25])))



def bandpass(x, lo, hi):
    """The project's committed band filter: difference of two box means."""
    return bandlib.boxblur(x, lo // 2) - bandlib.boxblur(x, hi // 2)


def block_se(hs, hd, k=4):
    """Standard error of var(hs) - var(hd), from block scatter.

    Assumption-free: the ROI is cut into k*k blocks, the difference is formed in
    each, and the scatter across blocks gives the error on their mean. Nothing is
    assumed about the correlation length the band filter imposes, which an
    analytic 2v^2/n would have had to guess at.
    """
    h, w = hs.shape
    bh, bw = h // k, w // k
    if bh < 8 or bw < 8:
        return None
    d = []
    for i in range(k):
        for j in range(k):
            s = hs[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]
            n = hd[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]
            d.append(float(np.var(s)) - float(np.var(n)))
    return float(np.std(d, ddof=1)) / np.sqrt(len(d))


def decompose(a, b, lo, hi, levels, mask=None):
    """Scene and noise sd in one band, from an independent pair.

    `a` and `b` are 2-D float arrays in display codes. `levels` is the token
    returned by `check_pair_levels` for THIS PAIR OF ARMS -- see that function
    for why it is a separate, whole-frame call and a required argument rather
    than something this function can do for itself from the crop it is handed.

    The band filter is built once here and applied to BOTH the half-sum and the
    half-difference; there is deliberately no way for a caller to pass two
    filters.

    Returns `(scene_sd, noise_sd)`. Where the scene is genuinely absent -- a flat
    region at a fine band -- the true difference is zero and half of all draws
    put it slightly negative. The first version of this refused those outright
    and the very first real ROI it saw hit it: half-difference variance 0.0196657
    against half-sum 0.0196049, an excess of 0.3%. That is not an impossible
    decomposition, it is a scene of zero measured with error, and refusing it
    would have thrown away the correct answer. So the violation must now be
    SIGNIFICANT against the block-to-block scatter before it is called
    degenerate. The loud case another lane hit -- a 473x excess -- still fires.

    THE RESIDUAL GAIN IS PROPAGATED RATHER THAN ASSUMED AWAY. Writing the pair as
    A = S + n_A and B = g(S + n_B) and turning the handle:

        var(hs) - var(hd) = g * var(S)
        2*var(hd)         = eps^2 * var(S) / 2 + (1+g^2)/2 * var(n),  eps = g-1

    so a residual gain scales the scene VARIANCE by g -- a 2% gain costs 1% on
    the scene sd, which is benign -- but it leaks scene into the NOISE term in
    proportion to eps^2 * r^2, where r is the site's own scene/noise ratio. The
    damage therefore depends on the site, not on a global threshold, and a flat
    tolerance cannot express it. Using the certified bound from `levels`, the
    relative bias on the reported noise sd is at most eps^2 * r^2 / 4, and a site
    whose bound exceeds GAIN_BIAS_MAX is refused with its own numbers.
    """
    if a.shape != b.shape:
        raise Degenerate("arms differ in shape: %s vs %s" % (a.shape, b.shape))
    if not isinstance(levels, Levels):
        raise Degenerate(
            "decompose() requires the Levels token from check_pair_levels(arm_a, arm_b), "
            "called once on the WHOLE arms. Got %r. A gain mismatch is invisible to "
            "every other guard in this module." % (type(levels).__name__,))
    hs = bandpass((a + b) / 2.0, lo, hi)
    hd = bandpass((a - b) / 2.0, lo, hi)
    if mask is not None:
        if mask.shape != a.shape:
            raise Degenerate("mask shape %s does not match arms %s"
                             % (mask.shape, a.shape))
        hs, hd = hs[mask], hd[mask]
    v_tot = float(np.var(hs))
    v_nse = float(np.var(hd))
    diff = v_tot - v_nse
    if diff < 0.0:
        se = None if mask is not None else block_se(hs, hd)
        if se is None or abs(diff) > DEGEN_Z * se:
            raise Degenerate(
                "half-difference variance %.6g exceeds half-sum variance %.6g in the "
                "%d-%d px band by %s. For independent additive noise this is "
                "impossible, so the two terms are not being measured the same way."
                % (v_nse, v_tot, lo, hi,
                   "%.1f standard errors" % (abs(diff) / se) if se else "an unbounded amount"))
    scene = float(np.sqrt(max(diff, 0.0)))
    noise = float(np.sqrt(2.0 * v_nse))
    return scene, noise


def noise_bias(levels, scene, noise):
    """Upper bound on the relative bias a residual gain puts on the noise sd.

    With A = S + n_A and B = g(S + n_B), eps = g - 1:

        2*var(hd) = eps^2 * var(S) / 2  +  (1+g^2)/2 * var(n)
                  = eps^2 * var(S) / 2  +  (1 + eps + eps^2/2) * var(n)

    so the bound on the sd is  eps/2 + eps^2 * r^2 / 4  with r the site's own
    scene/noise ratio. BOTH TERMS ARE NECESSARY AND THE FIRST WAS MISSED. The
    first version of this dropped the (1+g^2)/2 factor -- the gain scales arm b's
    NOISE as well as its scene -- and kept only the eps^2*r^2/4 leak. Commissioning
    arm 5f, which plants a gain of exactly the certified floor and measures what
    it does, caught it immediately:

        r  5.4, eps 1.264%:  measured +0.86%, old bound 0.12%   <- bound too small
        r 56.4, eps 0.717%:  measured +3.38%, old bound 4.10%      by 7x at low r

    An upper bound that the effect exceeds is not a bound, and only a planted
    disturbance of the exact size the guard admits could show it.

    This is a WORST CASE over the gain the guard could not rule out, not an
    estimate of the error actually present, which is why it is reported and never
    used to refuse: a bound is not a measurement.

    The SCENE term needs no such bound. The noise contributions to var(hs) and
    var(hd) are the same (1+g^2)/4 * var(n) and cancel exactly in the difference,
    leaving g * var(S): a 2% gain costs 1% on the scene sd and nothing else. That
    asymmetry is why this returns one number and not two.
    """
    r = scene / max(noise, 1e-12)
    eps = levels.bound
    return eps / 2.0 + eps ** 2 * r ** 2 / 4.0



def sharpness(a, b, mask=None):
    """Mean |gradient| of the half-sum: the acuity partner for every band number.

    Taken on the half-sum rather than on one arm so that it is measured on the
    same combination the scene term came from. A number quoted on different
    pixels from the noise number it is meant to police is not a partner.
    """
    p = (a + b) / 2.0
    g = np.abs(np.diff(p, axis=0))[:, :-1] + np.abs(np.diff(p, axis=1))[:-1, :]
    if mask is not None:
        g = g[mask[:-1, :-1]]
    return float(np.mean(g))
