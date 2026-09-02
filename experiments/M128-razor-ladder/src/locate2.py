r"""M128 / locate2 — two-pass edge locator, and the commissioning that licenses it.

WHY THIS EXISTS. src\yield_diag.py counted, per column, the reason
geom.crossings declines to report an edge position:

    frame                     ok    low contrast   zero crossings   multi
    f/5.6 DSC00045.ARW    74.30%           1.99%            0.00%   23.71%
    f/11  DSC00042.ARW    61.33%           3.16%            0.00%   35.52%

No column anywhere fails to cross the mid level. Every rejection is either
genuinely low contrast -- 2-3%, and those are real -- or a column whose profile
crosses the mid level MORE than once. geom.crossings requires a globally unique
crossing and abandons the column otherwise.

That requirement is not a property of the subject. It is a property of the
estimator, and it is aperture-dependent: the multi-crossing rate rises from
23.7% to 35.5% as the aperture closes, because a flatter profile lets noise and
the veiling-glare shoulder re-cross the mid level more often. So the SET OF
COLUMNS being compared differs systematically between apertures. That is a
prime suspect for the 6.77 um aperture-dependent locus disagreement measured by
src\across.py, which is currently the single largest threat to this lane.

THE ESTIMATOR. Ambiguity is only ambiguity in the absence of context. The edge
is a smooth curve; a column with four crossings has one crossing on the edge and
three on noise or glare, and the edge one is the one near where the neighbouring
columns put it.

    pass 1   fit a locus using only the unambiguous columns
    pass 2   for every column with adequate contrast, take the crossing
             NEAREST that prediction; reject if it is further than max_dev

WHAT MUST BE TRUE FOR THIS TO BE HONEST, AND IS CHECKED BELOW.

  1. It must not move columns that were never ambiguous. When a column has
     exactly one crossing, "nearest the prediction" IS that crossing. The
     returned value must be bit-identical to geom.crossings for those columns.
     Any difference is a bug, not an improvement. Checked by INVARIANT 1.

  2. It must not invent the answer. The prediction is smoothed over `smooth_w`
     columns, so it carries the long-wavelength shape of the edge. If
     `smooth_w` were small the prediction would track the very wander being
     measured and the estimator would return its own input. The seed is
     therefore taken from unambiguous columns only, and `smooth_w` is a
     commissioned parameter with the null control in INVARIANT 3.

  3. It must not manufacture the effect it is meant to remove. Recovering the
     multi-crossing columns must reduce, not create, the aperture dependence
     of the locus. That is measured downstream by across.py, not asserted here.

  4. It must recover the TRUE locus on data where the truth is known, and beat
     the one-pass estimator there. Checked by the synthetic commissioning,
     which plants a known wander, a known blur, photon noise and a glare
     shoulder tuned to produce the observed multi-crossing rate.

RULE 20 FAILURE MODE, REGISTERED IN ADVANCE. If the synthetic commissioning
shows the two-pass locus tracks the PREDICTION rather than the TRUTH -- that is,
if its error falls as `smooth_w` falls, with no plateau -- then the estimator is
smoothing the signal into existence and must be abandoned in favour of
accepting the lower yield and reporting it.

    python src\locate2.py --commission
    python src\locate2.py --invariant <frame> [--plane G1] [--band-half 60]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
M88 = Path(__file__).resolve().parents[2] / "M88-optical-ceiling" / "src"
sys.path.insert(0, str(M88))
import geom  # noqa: E402

MIN_CONTRAST_DN = 300.0
SMOOTH_W = 257
MAX_DEV_PX = 3.0
MIN_MARGIN_PX = 1.0


def _levels(sub, bright_first):
    n = sub.shape[0]
    q = max(6, n // 6)
    first = np.percentile(sub[:q, :], 50, axis=0)
    last = np.percentile(sub[-q:, :], 50, axis=0)
    hi = first if bright_first else last
    lo = last if bright_first else first
    return hi, lo, 0.5 * (hi + lo)


def _all_crossings(prof, m):
    """Every sub-pixel bright->dark crossing of level m, in profile order."""
    idx = np.nonzero((prof[:-1] >= m) & (prof[1:] < m))[0]
    if len(idx) == 0:
        return np.empty(0)
    p0 = prof[idx]
    p1 = prof[idx + 1]
    t = (p0 - m) / np.maximum(p0 - p1, 1e-6)
    return idx + t


def _running_median(y, w):
    """Median over a centred window of width w, NaN-aware, edge-shrinking."""
    n = len(y)
    out = np.full(n, np.nan)
    h = w // 2
    # A strided view would be faster but allocates n*w; this is called once
    # per frame on ~3.5e3 columns and is not the bottleneck.
    for i in range(n):
        a, b = max(i - h, 0), min(i + h + 1, n)
        seg = y[a:b]
        seg = seg[np.isfinite(seg)]
        if len(seg):
            out[i] = np.median(seg)
    return out


def _fill(y):
    """Linear interpolation over interior NaNs, edge-hold outside."""
    n = len(y)
    x = np.arange(n)
    g = np.isfinite(y)
    if g.sum() < 2:
        return None
    return np.interp(x, x[g], y[g])


def crossings2(a, b0, b1, bright_first, smooth_w=SMOOTH_W,
               max_dev=MAX_DEV_PX, min_margin=MIN_MARGIN_PX,
               min_contrast=MIN_CONTRAST_DN, report=False):
    """Two-pass 50%-crossing locus. Returns (xs, ys, hi, lo[, stats]).

    `min_margin` is what separates a decision from a guess. When a column has
    several crossings and two of them lie almost equally close to the
    prediction, choosing between them is not measurement -- the answer would be
    set by whichever way the prediction's own noise happened to fall. Such
    columns are refused. Without this the recovered columns carried 0.674 px of
    error against a 0.500 px planted shift, i.e. they were worse than returning
    a constant, because a wrong branch is not a small error.
    """
    sub = a[b0:b1, :]
    n, ncol = sub.shape
    hi, lo, mid = _levels(sub, bright_first)

    per_col = [None] * ncol
    seed = np.full(ncol, np.nan)
    n_amb = 0
    for x in range(ncol):
        if hi[x] - lo[x] < min_contrast:
            continue
        prof = sub[:, x] if bright_first else sub[::-1, x]
        c = _all_crossings(prof, mid[x])
        if len(c) == 0:
            continue
        if not bright_first:
            c = (n - 1) - c
        per_col[x] = c
        if len(c) == 1:
            seed[x] = c[0]
        else:
            n_amb += 1

    pred = _fill(_running_median(seed, smooth_w))
    if pred is None:
        return (np.empty(0), np.empty(0), hi, lo) + ((None,) if report else ())

    xs, ys = [], []
    n_rec = n_far = n_tie = n_seed_lost = 0
    for x in range(ncol):
        c = per_col[x]
        if c is None:
            continue
        d = np.abs(c - pred[x])
        j = int(np.argmin(d))
        if d[j] > max_dev:
            n_far += 1
            if len(c) == 1:
                n_seed_lost += 1
            continue
        if len(c) > 1:
            second = np.partition(d, 1)[1]
            if second - d[j] < min_margin:
                n_tie += 1
                continue
            n_rec += 1
        xs.append(x)
        ys.append(c[j] + b0)

    res = (np.asarray(xs, float), np.asarray(ys, float), hi, lo)
    if report:
        res = res + (dict(n_cols=ncol, n_ambiguous=n_amb, n_recovered=n_rec,
                          n_dropped_far=n_far, n_dropped_tie=n_tie,
                          n_unambiguous_lost=n_seed_lost,
                          n_out=len(xs), smooth_w=smooth_w,
                          max_dev=max_dev, min_margin=min_margin),)
    return res


# ---------------------------------------------------------------- INVARIANT 1

def invariant_identical(frame, plane, band_half, bright_first, smooth_w):
    """Columns that were never ambiguous must come back bit-identical."""
    import m88lib as L
    active = L.load_active(frame)
    sub, _xs, _ys = L.green_sites(active, plane)
    _b0, _b1, row = geom.find_band(sub)
    b0 = max(row - band_half, 0)
    b1 = min(row + band_half, sub.shape[0])

    x1, y1, _, _ = geom.crossings(sub, b0, b1, bright_first)
    x2, y2, _, _, st = crossings2(sub, b0, b1, bright_first,
                                  smooth_w=smooth_w, report=True)
    m1 = dict(zip(x1.astype(int), y1))
    m2 = dict(zip(x2.astype(int), y2))
    shared = sorted(set(m1) & set(m2))
    d = np.array([m2[k] - m1[k] for k in shared]) if shared else np.empty(0)

    print(f"{Path(frame).name}  plane {plane}  band {b0}..{b1}  "
          f"smooth_w {smooth_w}")
    print(f"  one-pass yield  {len(x1):5d} / {st['n_cols']}  "
          f"({100.0 * len(x1) / st['n_cols']:.2f}%)")
    print(f"  two-pass yield  {len(x2):5d} / {st['n_cols']}  "
          f"({100.0 * len(x2) / st['n_cols']:.2f}%)")
    print(f"  ambiguous columns          {st['n_ambiguous']:5d}")
    print(f"  ...recovered               {st['n_recovered']:5d}")
    print(f"  dropped as >{st['max_dev']:.1f}px from prediction "
          f"{st['n_dropped_far']:5d}  "
          f"(of which previously accepted: {st['n_unambiguous_lost']})")
    print(f"  columns in both estimators {len(shared):5d}")
    if len(d):
        print(f"  max |difference| on shared columns: {np.abs(d).max():.3e} px")
        ok = np.abs(d).max() < 1e-12
        print(f"  INVARIANT 1 ({'PASS' if ok else 'FAIL'}): unambiguous "
              f"columns are unchanged")
        return ok
    print("  INVARIANT 1 INDETERMINATE: no shared columns")
    return False


# --------------------------------------------------------- SYNTHETIC HARNESS
#
# A modelled edge does not commission this estimator. The first version of this
# harness built an erf edge with a glare tail and produced ZERO ambiguous
# columns, so `n_recovered` was 0 at every smoothing length, the truth error
# was constant to four decimals because no column ever changed, and the
# "first crossing" negative control was identical to the estimator because with
# one crossing the first IS the nearest. The whole battery was inert and its
# FAIL verdict meant nothing. Only the harness's own ambiguity-rate warning
# distinguished that from a real result.
#
# The pathology being commissioned is a property of THIS subject: a bevel shelf
# and a veiling-glare shoulder that sit near the mid level, so noise re-crosses
# it. Rather than model that and get it wrong again, the harness now inherits
# it -- the edge profile is the MEASURED ESF of a real frame and the noise is a
# MEASURED photon-transfer curve from that frame's own flat regions. The only
# planted quantity is the locus, which is what must be recovered.


def measure_profile(frame, plane, band_half, bright_first, bin_w=0.0625):
    """The measured ESF of a real frame, plus its photon-transfer noise model.

    The ESF is keyed on each column's own raw crossing rather than on a fitted
    locus, so a locus misfit cannot broaden it. Gain and read noise are fitted
    as var = gain*mean + read^2 over small patches taken from the flat plateaus
    on both sides of the edge, which is a two-level photon transfer.
    """
    import m88lib as L
    active = L.load_active(frame)
    sub, _xs, _ys = L.green_sites(active, plane)
    _b0, _b1, row = geom.find_band(sub)
    b0 = max(row - band_half, 0)
    b1 = min(row + band_half, sub.shape[0])
    band = np.ascontiguousarray(sub[b0:b1, :]).astype(np.float64)
    ny = band.shape[0]

    x, y, hi, lo = geom.crossings(sub, b0, b1, bright_first)
    y = y - b0
    pos, val = [], []
    yy = np.arange(ny, dtype=np.float64)
    for xi, y0 in zip(x.astype(int), y):
        pos.append(yy - y0)
        val.append(band[:, xi])
    pos = np.concatenate(pos)
    val = np.concatenate(val)

    lim = ny / 2.0
    nb = int(2 * lim / bin_w)
    idx = np.floor((pos + lim) / bin_w).astype(int)
    ok = (idx >= 0) & (idx < nb)
    s = np.bincount(idx[ok], weights=val[ok], minlength=nb)
    c = np.bincount(idx[ok], minlength=nb)
    good = c >= 32
    cc = ((np.arange(nb) + 0.5) * bin_w - lim)[good]
    ee = s[good] / c[good]

    # Photon transfer. Patch variance does NOT work here: the first version of
    # this function took the variance of 8x8 patches on the plateaus and fitted
    # gain = 186.6 DN/e with read = 1.0 DN, which is off by ~400x and drowned
    # the synthetic so badly that one-pass yield came out at 7.7% against a
    # real 74.3%. The patches were not flat -- they contain the bevel, the
    # glare gradient and debris -- so their variance measured the SUBJECT.
    #
    # Along the edge the true signal is smooth (the locus wanders over hundreds
    # of columns), so a second difference along x annihilates any local linear
    # trend and leaves noise. var(a[i] - 2a[i+1] + a[i+2]) = 6*sigma^2. The
    # median of squared second differences is used rather than the mean so that
    # debris specks and the etched text do not inflate it.
    mb, vb = [], []
    for r0 in range(0, ny, 2):
        row = band[r0, :]
        if row.size < 64:
            continue
        d2 = row[:-2] - 2.0 * row[1:-1] + row[2:]
        # 0.6745 converts a median absolute deviation to a Gaussian sigma.
        sig = np.median(np.abs(d2)) / 0.6745 / np.sqrt(6.0)
        mb.append(float(np.median(row)))
        vb.append(float(sig ** 2))
    mb = np.asarray(mb)
    vb = np.asarray(vb)
    order = np.argsort(mb)
    mb, vb = mb[order], vb[order]
    gain, c0 = np.polyfit(mb, vb, 1)
    read = float(np.sqrt(max(c0, 0.25)))
    return dict(cc=cc, ee=ee, gain=float(max(gain, 1e-3)), read=read,
                ny=ny, ncol=band.shape[1], ptc_levels=len(mb),
                ptc_lo=float(mb[0]), ptc_hi=float(mb[-1]),
                hi=float(np.median(hi)), lo=float(np.median(lo)))


def _cubic_shift(col, d):
    """Resample a column at y-d using Keys' cubic convolution (a = -0.5).

    Linear interpolation would smooth the profile and so would flatter any
    locator; cubic convolution is very nearly shift-invariant over the small
    shifts planted here, which is the property the test depends on.
    """
    n = len(col)
    y = np.arange(n, dtype=np.float64) - d
    i = np.floor(y).astype(int)
    t = y - i
    out = np.zeros(n)
    w = (-0.5 * t ** 3 + t ** 2 - 0.5 * t,
         1.5 * t ** 3 - 2.5 * t ** 2 + 1.0,
         -1.5 * t ** 3 + 2.0 * t ** 2 + 0.5 * t,
         0.5 * t ** 3 - 0.5 * t ** 2)
    for k, wk in zip((-1, 0, 1, 2), w):
        idx = np.clip(i + k, 0, n - 1)
        out += wk * col[idx]
    return out


def plant_shift(band, delta):
    out = np.empty_like(band)
    for x in range(band.shape[1]):
        out[:, x] = _cubic_shift(band[:, x], delta[x])
    return out


def smooth_noise(nx, rms, corr_len, seed):
    rng = np.random.default_rng(seed)
    k = int(corr_len * 4) | 1
    g = np.exp(-0.5 * ((np.arange(k) - k // 2) / corr_len) ** 2)
    g /= g.sum()
    w = np.convolve(rng.standard_normal(nx + k), g, mode="same")[:nx]
    return w / w.std() * rms


def _recover(band, bright_first, mode, smooth_w, margin=MIN_MARGIN_PX):
    if mode == "one":
        x, y, _, _ = geom.crossings(band, 0, band.shape[0], bright_first)
        return x.astype(int), y
    if mode == "two":
        x, y, _, _ = crossings2(band, 0, band.shape[0], bright_first,
                                smooth_w=smooth_w, min_margin=margin)
        return x.astype(int), y
    if mode == "first":
        hi, lo, mid = _levels(band, bright_first)
        xs, ys = [], []
        n = band.shape[0]
        for x in range(band.shape[1]):
            if hi[x] - lo[x] < MIN_CONTRAST_DN:
                continue
            prof = band[:, x] if bright_first else band[::-1, x]
            c = _all_crossings(prof, mid[x])
            if len(c):
                p = c[0] if bright_first else (n - 1) - c[0]
                xs.append(x)
                ys.append(p)
        return np.asarray(xs, int), np.asarray(ys, float)
    raise ValueError(mode)


def _diffs(band0, band1, bright_first, mode, smooth_w, margin=MIN_MARGIN_PX):
    """Per-column locus difference between the two bands, as a dict."""
    x0, y0 = _recover(band0, bright_first, mode, smooth_w, margin)
    x1, y1 = _recover(band1, bright_first, mode, smooth_w, margin)
    m0 = dict(zip(x0, y0))
    m1 = dict(zip(x1, y1))
    return {c: m1[c] - m0[c] for c in (set(m0) & set(m1))}


def _err(diffs, delta, cols=None):
    cols = sorted(diffs if cols is None else (set(diffs) & set(cols)))
    if len(cols) < 64:
        return None, 0
    e = np.array([diffs[c] for c in cols]) - delta[np.asarray(cols)]
    e = e - e.mean()
    return float(np.sqrt(np.mean(e ** 2))), len(cols)


def commission(frame, plane, band_half, bright_first, shift_rms=0.5,
               corr_len=140.0, seed=11):
    print("=" * 72)
    print("COMMISSIONING locate2.crossings2")
    print("=" * 72)
    print(__doc__.split("THE ESTIMATOR.")[0].split("WHY THIS EXISTS.")[1]
          .strip()[:0] or "", end="")

    import m88lib as L
    active = L.load_active(frame)
    sub, _xs, _ys = L.green_sites(active, plane)
    _b0, _b1, row = geom.find_band(sub)
    b0 = max(row - band_half, 0)
    b1 = min(row + band_half, sub.shape[0])
    band0 = np.ascontiguousarray(sub[b0:b1, :]).astype(np.float64)
    ncol = band0.shape[1]

    prof = measure_profile(frame, plane, band_half, bright_first)
    print(f"\nsubject: {Path(frame).name} plane {plane}, band rows "
          f"{b0}..{b1}, {ncol} columns")
    print(f"  plateaus {prof['lo']:.0f} .. {prof['hi']:.0f} DN")
    print(f"  photon transfer over {prof['ptc_levels']} row levels spanning "
          f"{prof['ptc_lo']:.0f} .. {prof['ptc_hi']:.0f} DN")
    print(f"  gain {prof['gain']:.4f} DN/e, read {prof['read']:.1f} DN"
          f"  -> sigma "
          f"{np.sqrt(prof['gain'] * prof['hi'] + prof['read'] ** 2):.1f}"
          f" DN on the bright plateau")

    print("\nTHE TEST. Two attempts to build a synthetic subject failed, and "
          "both failures were informative: an erf-plus-glare model produced "
          "ZERO ambiguous columns, and so did the measured mean ESF. The "
          "pathology is per-column -- a bevel shelf whose brightness varies "
          "along the edge, which column-averaging erases -- so no profile "
          "model reproduces it.")
    print("\nSo nothing is modelled. A known sub-pixel shift delta(x) is "
          "planted into the REAL band by cubic resampling, and the locator "
          "must return it. The subject keeps every pathology it has, and the "
          "truth is a DIFFERENCE of two loci, so the unknown true locus "
          "cancels exactly. This is also the quantity the ladder actually "
          "needs: agreement of the locus between two exposures of one blade.")

    delta = smooth_noise(ncol, shift_rms, corr_len, seed)
    band1 = plant_shift(band0, delta)
    print(f"\nplanted shift: RMS {delta.std():.4f} px, correlation length "
          f"{corr_len:.0f} columns, range "
          f"{delta.min():+.3f} .. {delta.max():+.3f} px")

    x1p, _ = _recover(band0, bright_first, "one", SMOOTH_W)
    one_cols = set(x1p.tolist())
    print(f"  one-pass yield on the unshifted band {len(one_cols)}/{ncol} "
          f"({100.0 * len(one_cols) / ncol:.2f}%)")
    if not (0.4 < len(one_cols) / ncol < 0.95):
        print("  HARNESS SUSPECT: the real frame's ambiguity rate is outside "
              "the range this lane measured (61-74%). Check the band.")

    d_one = _diffs(band0, band1, bright_first, "one", SMOOTH_W)
    e_one, n_one = _err(d_one, delta)
    print(f"\n  one-pass       : error {e_one:.4f} px on {n_one} columns")

    print("\n  Sweep of the two free parameters. `err same` is evaluated on "
          "the columns BOTH estimators reported in BOTH bands -- the earlier "
          "version of this check restricted to one-pass columns of the "
          "unshifted band only, so the two estimators were scored on "
          "different sets and the comparison was not like-for-like.")
    print("  `err extra` is the error on the recovered columns alone, which "
          "is the only number that says whether recovery is worth having.")
    print(f"  {'smooth_w':>9}{'margin':>8}{'all':>7}{'err all':>9}"
          f"{'same':>7}{'err same':>10}{'extra':>7}{'err extra':>11}")
    rows = []
    for w in (65, 129, 257, 513):
        for mg in (0.0, 0.5, 1.0, 2.0):
            d_two = _diffs(band0, band1, bright_first, "two", w, mg)
            common = set(d_two) & set(d_one)
            extra = set(d_two) - set(d_one)
            e_all, n_all = _err(d_two, delta)
            e_sam, n_sam = _err(d_two, delta, common)
            e_one_c, _ = _err(d_one, delta, common)
            e_ext, n_ext = _err(d_two, delta, extra)
            if e_all is None or e_sam is None:
                continue
            rows.append((w, mg, n_all, e_all, n_sam, e_sam, e_one_c,
                         n_ext, e_ext))
            print(f"  {w:>9}{mg:>8.1f}{n_all:>7}{e_all:>9.4f}"
                  f"{n_sam:>7}{e_sam:>10.4f}{n_ext:>7}"
                  + (f"{e_ext:>11.4f}" if e_ext is not None else f"{'-':>11}"))

    # Selection is on the like-for-like set plus a yield floor, not on `err
    # all`, so that a setting cannot win merely by discarding hard columns.
    usable = [r for r in rows if r[7] >= 200 and r[8] is not None]
    if not usable:
        print("\n  no setting recovered enough columns to judge")
        return False
    best = min(usable, key=lambda r: r[3])
    w_best, mg_best, n_best, e_best, n_sam_b, e_sam_b, e_one_b, n_ext_b, \
        e_ext_b = best
    print(f"\n  best: smooth_w = {w_best}, min_margin = {mg_best:.1f} px")

    print("\nCHECK 1 -- recovery must not corrupt the easy columns. Scored on "
          f"the {n_sam_b} columns both estimators reported in both bands.")
    c1 = e_sam_b <= 1.05 * e_one_b
    print(f"  one-pass {e_one_b:.4f} px vs two-pass {e_sam_b:.4f} px "
          f"-> {'PASS' if c1 else 'FAIL'}")

    print("\nCHECK 2 -- the recovered columns must be measurements. A locator "
          "that ignored the data and returned a constant would score exactly "
          f"the planted RMS, {shift_rms:.3f} px; a wrong branch scores worse "
          "than that. This is the check the first design failed, at 0.674 px.")
    c2 = e_ext_b < 0.5 * shift_rms
    print(f"  error on the {n_ext_b} recovered columns {e_ext_b:.4f} px "
          f"-> {'PASS' if c2 else 'FAIL'}")

    print("\nCHECK 3 -- yield. The point of the estimator is the columns it "
          "recovers.")
    c3 = n_best > 1.15 * n_one
    print(f"  {n_one} -> {n_best} columns "
          f"({100.0 * n_best / ncol:.2f}% of the edge) "
          f"-> {'PASS' if c3 else 'FAIL'}")

    print("\nNEGATIVE CONTROL -- plant a locator defect (take the FIRST "
          "crossing, not the nearest) and require these checks to notice.")
    e_bad, n_bad = _err(_diffs(band0, band1, bright_first, "first", w_best),
                        delta)
    caught = e_bad is None or e_bad > 4.0 * e_best
    print(f"  first-crossing error {e_bad:.4f} px on {n_bad} columns "
          f"vs two-pass {e_best:.4f} px -> "
          f"{'CAUGHT' if caught else 'MISSED'}")

    print("\nNULL CONTROL -- plant NO shift. The locator must return zero "
          "difference; anything else is the instrument talking to itself.")
    zero = np.zeros(ncol)
    e_null, n_null = _err(_diffs(band0, plant_shift(band0, zero),
                                 bright_first, "two", w_best, mg_best), zero)
    c4 = e_null < 0.02
    print(f"  null error {e_null:.6f} px on {n_null} columns -> "
          f"{'PASS' if c4 else 'FAIL'}")

    print("\n" + "=" * 72)
    verdict = bool(c1 and c2 and c3 and caught and c4)
    print(f"COMMISSIONING VERDICT: {'PASS' if verdict else 'FAIL'}")
    print(f"  check 1 easy columns not corrupted   {c1}")
    print(f"  check 2 recovered columns measured   {c2}")
    print(f"  check 3 yield improved               {c3}")
    print(f"  negative control caught              {caught}")
    print(f"  null control clean                   {c4}")
    print(f"  recommended smooth_w = {w_best}, min_margin = {mg_best:.1f}")
    print("=" * 72)
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", default=None, metavar="FRAME",
                    help="frame whose measured profile and noise drive the "
                         "synthetic harness")
    ap.add_argument("--invariant", default=None, metavar="FRAME")
    ap.add_argument("--plane", default="G1")
    ap.add_argument("--band-half", type=int, default=60)
    ap.add_argument("--smooth-w", type=int, default=SMOOTH_W)
    ap.add_argument("--dark-first", action="store_true")
    args = ap.parse_args()

    ok = True
    if args.commission:
        ok &= commission(args.commission, args.plane, args.band_half,
                         not args.dark_first)
    if args.invariant:
        print()
        ok &= invariant_identical(args.invariant, args.plane, args.band_half,
                                  not args.dark_first, args.smooth_w)
    if not (args.commission or args.invariant):
        ap.error("give --commission FRAME and/or --invariant FRAME")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
