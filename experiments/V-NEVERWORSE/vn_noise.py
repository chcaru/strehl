"""A MEASURED per-frame noise variance, and the audit that made it necessary.

WHY THIS FILE EXISTS -- a defect in this lane's own instrument
--------------------------------------------------------------
Everything this lane reported about N-dependent softening was divided by a
"noise twin": a synthetic stack with the same latent scene and independent
noise at the fitted level `var0`, merged by the same arm. The twin's band
power was taken to be the merge's noise contribution.

`vn_pyr.fit_variance` fits var = read2 + g*S from ONE frame. Its own docstring
records that it already had to be repaired once because bright bins are bright
BECAUSE THEY CONTAIN SHARP DETAIL, so structure was being fitted as noise. The
repair was a low quantile plus a non-negativity clamp on g. The clamp is the
problem: when the fit still wants a negative slope, g is forced to 0 and read2
becomes the MEDIAN of the per-bin variances, which on a detailed subject is a
level set by structure.

MEASURED on coffee-bubbles, 19 frames:

    fit_variance -> read2 = 8414, gain = 0.0, sigma = 91.73 DN everywhere
    model-free   -> sigma = 60.42 DN, and that is an UPPER bound because the
                    difference of two real frames also contains focus change

So the twin was given at least (91.73/60.42)^2 = 2.31x too much noise VARIANCE.
The consequence was visible and was not looked at: decomposing the merged band
power into scene + noise gave a NEGATIVE scene term in 12 of 12 cells on
coffee-bubbles, the twin's 0.30-0.35 noise power reading 145% to 345% of the
TOTAL power present in the real merge. Noise cannot exceed total. The
decomposition was degenerate and a verdict was printed over it anyway.

THE FIX, and why it is the minimal one
--------------------------------------
Fit the SAME functional form with the SAME calibration constants, but on a
frame DIFFERENCE rather than on a frame. For independent frames

    d = (f_i - f_j) / sqrt(2)     has variance exactly v

and the scene cancels. What does not cancel is focus difference, which is
still scene -- so this is still an upper bound, and it is driven down two more
ways: bin by the pair's mean level and take a LOW quantile within each bin
(flat patches dominate the low tail), then take the MINIMUM across pairs,
since focus difference can only ever ADD to the difference image.

Nothing else changes. beta0, Q and QS are the incumbent's constants, so any
difference in the answer is attributable to difference-imaging and not to a
recalibration.
"""
import numpy as np

import vn_pyr as VP

BETA0 = 0.8898
Q, QS = 20.0, 0.2533


FLAT_PCT = 40.0


def _flat_mask(s, pct=FLAT_PCT):
    """The lowest-structure pixels of the pair mean.

    MEASURED REASON THIS EXISTS. The first version binned the difference image
    by LEVEL alone and took a low quantile inside each bin, on the incumbent's
    stated reasoning that "flat patches dominate the low tail". They do not: a
    bin at a given brightness still contains edges, so a scene-only input --
    noiseless frames differing by a 1 px shift -- read 18.10 DN, which is a
    third of the real noise on the subject. Selecting on local gradient rather
    than on brightness took the same input to the value reported by the
    SCENE IMMUNITY line of `commission`.
    """
    gy = np.zeros_like(s)
    gx = np.zeros_like(s)
    gy[1:-1, :] = s[2:, :] - s[:-2, :]
    gx[:, 1:-1] = s[:, 2:] - s[:, :-2]
    st = np.abs(gy) + np.abs(gx)
    return st <= np.percentile(st, pct)


def _binned(d, s, nbin=13):
    """Per-bin noise variance of difference image `d` binned by level `s`.

    Restricted to the flat pixels of `s`, so that structure in the difference
    image cannot be fitted as noise.
    """
    lap, _ = VP.lap_pyr(d, 1)
    l0 = np.abs(lap[0])
    sr = VP.reduce_(s) if s.shape != l0.shape else s
    sr = sr[:l0.shape[0], :l0.shape[1]]
    flat = _flat_mask(sr)
    lo, hi = np.percentile(sr[flat], [1, 99])
    edges = np.linspace(lo, hi, nbin)
    xs, ys = [], []
    for i in range(len(edges) - 1):
        m = flat & (sr >= edges[i]) & (sr < edges[i + 1])
        if m.sum() < 500:
            continue
        xs.append(float(sr[m].mean()))
        ys.append(float((np.percentile(l0[m], Q) / QS) ** 2 / BETA0))
    return xs, ys


def fit_variance_paired(frames, max_pairs=12):
    """(var_map, read2, gain) from adjacent frame differences.

    Same signature and same units as `vn_pyr.fit_variance`, so it is a drop-in
    for the twin's noise scale.
    """
    n = len(frames)
    if n < 2:
        raise SystemExit("REFUSED: paired noise fit needs at least 2 frames")
    idx = list(range(n - 1))
    if len(idx) > max_pairs:
        take = np.linspace(0, len(idx) - 1, max_pairs).round().astype(int)
        idx = [idx[i] for i in sorted(set(take.tolist()))]
    green = frames[0][:, :, 1].astype(np.float64)
    curves = []
    for i in idx:
        a = frames[i][:, :, 1].astype(np.float64)
        b = frames[i + 1][:, :, 1].astype(np.float64)
        d = (a - b) / np.sqrt(2.0)
        xs, ys = _binned(d, (a + b) * 0.5)
        if len(xs) >= 3:
            curves.append((np.array(xs), np.array(ys)))
    if not curves:
        raise SystemExit("REFUSED: no usable bins in any adjacent frame pair")
    # Focus difference can only ADD, so the least contaminated estimate of the
    # noise at a given level is the minimum across pairs.
    grid = curves[0][0]
    stack = []
    for xs, ys in curves:
        stack.append(np.interp(grid, xs, ys))
    ys = np.min(np.stack(stack), axis=0)
    A = np.vstack([np.ones(len(grid)), grid]).T
    coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
    read2, g = float(coef[0]), float(coef[1])
    if g < 0.0:
        g = 0.0
        read2 = float(np.median(ys))
    read2 = max(read2, 1.0)
    v = read2 + g * np.maximum(green, 0.0)
    return np.maximum(v, 1.0), read2, g


def _sigma_of(v):
    return float(np.sqrt(np.maximum(np.asarray(v), 0.0)).mean())


def commission(base_rgb, real_frames, seed=515):
    """Both directions, plus the two tests a monotone indicator cannot pass.

    A commissioning that only checks "more noise reads higher" is passed by any
    monotone function of the noise, including one off by 2.3x -- which is
    exactly the defect this file exists to repair. So two of these five are
    ACCURACY tests against a known truth, and one is the scene-immunity test
    the incumbent fails.
    """
    rng = np.random.default_rng(seed)
    ok, bad = [], []
    g = base_rgb[:, :, 1].astype(np.float64)

    def stack_at(sig, k=6):
        out = []
        for _ in range(k):
            f = base_rgb.astype(np.float64).copy()
            f += rng.normal(0.0, sig, f.shape)
            out.append(f)
        return out

    # 1. ACCURACY. A short-circuit or a mis-scaled estimator fails this; a
    #    monotone indicator passes every other test in this list.
    sig = 40.0
    v, r2, gg = fit_variance_paired(stack_at(sig))
    rec = _sigma_of(v)
    err = abs(rec - sig) / sig
    (ok if err < 0.08 else bad).append(
        "ACCURACY: known sigma %.1f DN recovered as %.2f DN (%.1f%% error, "
        "must be <8%%)" % (sig, rec, 100 * err))

    # 2. ACCURACY at a second level, so a fixed offset cannot pass test 1.
    sig2 = 120.0
    v2, _, _ = fit_variance_paired(stack_at(sig2))
    rec2 = _sigma_of(v2)
    err2 = abs(rec2 - sig2) / sig2
    (ok if err2 < 0.08 else bad).append(
        "ACCURACY x3: known sigma %.1f DN recovered as %.2f DN (%.1f%% error, "
        "must be <8%%)" % (sig2, rec2, 100 * err2))

    # 3. UP: a planted DEGRADATION must raise it, by the predicted amount.
    pred = np.sqrt(sig ** 2 + 60.0 ** 2)
    v3, _, _ = fit_variance_paired(
        [f + rng.normal(0.0, 60.0, f.shape) for f in stack_at(sig)])
    rec3 = _sigma_of(v3)
    err3 = abs(rec3 - pred) / pred
    (ok if rec3 > rec and err3 < 0.10 else bad).append(
        "UP: adding 60 DN in quadrature to a %.0f DN stack predicts %.2f, "
        "measured %.2f (%.1f%% error, must rise and be <10%%)"
        % (sig, pred, rec3, 100 * err3))

    # 4. DOWN: a planted IMPROVEMENT must lower it. Smoothing each frame by a
    #    3x3 box divides white-noise variance by 9 -- but the estimator reads
    #    the HIGH-FREQUENCY residual, so require only a clear fall.
    sm = []
    for f in stack_at(sig):
        a = f.copy()
        a[1:-1, 1:-1] = (f[:-2, 1:-1] + f[2:, 1:-1] + f[1:-1, :-2]
                         + f[1:-1, 2:] + f[1:-1, 1:-1]) / 5.0
        sm.append(a)
    v4, _, _ = fit_variance_paired(sm)
    rec4 = _sigma_of(v4)
    (ok if rec4 < 0.6 * rec else bad).append(
        "DOWN: smoothing a %.0f DN stack lowers the reading to %.2f DN "
        "(must fall below %.2f)" % (sig, rec4, 0.6 * rec))

    # 5. SCENE IMMUNITY -- the test the incumbent fails, and the reason this
    #    file exists. Frames that differ by STRUCTURE and carry no noise at all
    #    must read ~0. `fit_variance` is run on the same input for contrast, so
    #    this is a comparison against a measured alternative and not against a
    #    constant written here.
    shifted = []
    for k in range(6):
        a = np.roll(base_rgb.astype(np.float64), k - 3, axis=0)
        shifted.append(np.roll(a, k - 3, axis=1))
    v5, _, _ = fit_variance_paired(shifted)
    rec5 = _sigma_of(v5)
    v5i, _, _ = VP.fit_variance(shifted[0][:, :, 1])
    inc5 = _sigma_of(v5i)
    # The bar is set by a quantity MEASURED on the subject under test, not by
    # a constant written here: scene contamination must stay small against the
    # noise the estimator actually reports on the real stack. An earlier draft
    # compared against mean(sqrt(green)), which is not a DN scale at all.
    vr, _, _ = fit_variance_paired(real_frames)
    sig_real = _sigma_of(vr)
    (ok if rec5 < 0.25 * sig_real else bad).append(
        "SCENE IMMUNITY: on noiseless frames differing only by structure the "
        "paired fit reads %.3f DN, against %.2f DN measured on the real stack "
        "(must be <%.3f, i.e. under 6%% of the variance); the incumbent "
        "single-frame fit reads %.2f DN on the same input"
        % (rec5, sig_real, 0.25 * sig_real, inc5))
    return ok, bad
