"""M92 -- library for the null-averaging experiment.

QUESTION.  M57 section 11 item 2 (Q-b): the independent-noise null, whose truth
is EXACTLY 0 px, scatters by up to 0.343 px per 512^2 ROI.  Does that scatter
average down across DISJOINT ROIs?

WHAT IS IMPORTED AND NOT TOUCHED
  m57lib   dsig (K1), RingStats, merge_subset, splits, rings/sectors geometry,
           gain_dn_per_e, read_noise_e.  Imported unmodified.  This milestone
           must not reimplement dsig: a reimplementation would confound the
           averaging result with an implementation difference.
  m41lib   focus_fields, hp_sd (frozen under rule 15)
  m46lib   blur, noise_var_dn

WHAT IS NEW HERE
  ROI grids whose PADDED footprints are disjoint, a loader that decodes each
  RAW once and scatters it to every ROI, a cached half-merge cell store, and
  the averaging / correlation / exponent harness.

RULE NOTES
  rule 7   raw_image_visible only; the quad plane is 2344 x 3514.
  rule 9   hp_sd is recorded for every ROI and the low-texture half is reported
           first.
  rule 10  the injected sigma is the merged TEMPORAL sigma from the calibrated
           model, never a spatial sd of the scene.  The one spatial sd used
           anywhere is the scale of a DARK DIFFERENCE, which contains no scene
           and whose fixed pattern has cancelled -- stated at its use site.
  rule 32  rawpy buffers are copied inside the `with`.
  rule 39  every reported number has a null and that null's error bar comes
           from REPETITION, never the jackknife (M57 S7 PR19).
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_EXP, "m57-shape-metric", "src"),
           os.path.join(_EXP, "m46-detail-metric", "src"),
           os.path.join(_EXP, "m41-r3-kill", "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import m57lib as K  # noqa: E402  -- the instrument, unmodified

OUT = os.path.join(os.path.dirname(_HERE), "out")
CACHE = os.path.join(OUT, "cache")
os.makedirs(OUT, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

ROOT = r"D:\personal\macro"
DARKS = r"D:\macro-dark-frames"
PAD = 32
ROI_N = 512
RN_E_FOCUS = 1.47          # m41lib's frozen operator value (rule 15)
GATE_SHIPPED = 0.50
GATE_SELECTOR = 0.99

# PREREGISTRATION section 3 -- frozen before any arm ran.
DISJOINT_X = (32, 608, 1184, 1760, 2336, 2912)
DISJOINT_Y = (32, 608, 1184, 1760)
OVERLAP_X = (32, 160, 288, 416, 544, 672)
OVERLAP_Y = (32, 160, 288, 416)

# PREREGISTRATION section 8.
STACKS = {
    "112MSDCF": dict(lo=6, hi=68, iso=500),
    "109MSDCF": dict(lo=0, hi=22, iso=160),
    "wrapped-text-1": dict(lo=0, hi=130, iso=100),
}

# M57 S7's own three cells, for the reproduction control.
M57_CELLS = [
    ("112MSDCF", "flat", (2747, 32), 6, 68),
    ("112MSDCF", "detail", (1671, 1373), 6, 68),
    ("109MSDCF", "centre", (916, 1501), 0, 22),
]

N_LADDER = (1, 2, 3, 4, 6, 8, 12, 16, 24)


def grid(kind):
    xs, ys = (DISJOINT_X, DISJOINT_Y) if kind == "disjoint" else (OVERLAP_X, OVERLAP_Y)
    return [(int(x), int(y)) for y in ys for x in xs]


def footprints_disjoint(coords, n=ROI_N, pad=PAD):
    """Asserted, not assumed: the PADDED footprints do not intersect."""
    boxes = [(x - pad, y - pad, x + n + pad, y + n + pad) for (x, y) in coords]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            ax0, ay0, ax1, ay1 = boxes[i]
            bx0, by0, bx1, by1 = boxes[j]
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                return False
    return True


# ------------------------------------------------------------------ loading
def quad_plane(path):
    """Green-quad plane of one RAW.  Rule 32: allocate AND copy inside `with`."""
    import rawpy
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g1 = v[0::2, 1::2].astype(np.float32)
        g2 = v[1::2, 0::2].astype(np.float32)
    return 0.5 * (g1 + g2) - K.BLACK


def stack_files(name):
    import glob
    cfg = STACKS[name]
    f = sorted(glob.glob(os.path.join(ROOT, name, "*.ARW")))
    return f[cfg["lo"]:cfg["hi"]]


def load_full(files, progress=None):
    """One decode per frame into a full quad-plane cube."""
    p0 = quad_plane(files[0])
    cube = np.empty((len(files),) + p0.shape, np.float32)
    cube[0] = p0
    for i in range(1, len(files)):
        cube[i] = quad_plane(files[i])
        if progress and i % 20 == 0:
            progress(i, len(files))
    return cube


def cell_from_cube(cube, xy, g, gates=(GATE_SHIPPED, GATE_SELECTOR),
                   n=ROI_N, pad=PAD):
    """Half-merges of one ROI at each gate.  Identical operator to M57 S5/S7."""
    x, y = xy
    sub = np.ascontiguousarray(cube[:, y - pad:y + n + pad, x - pad:x + n + pad])
    fine, coarse, reg = K.L1.focus_fields(sub, g, RN_E_FOCUS)
    ia, ib = K.splits(sub.shape[0])["parity"]
    out = {}
    for gt in gates:
        ma, nea = K.merge_subset(sub, coarse, reg, ia, pad=pad, gate=gt)
        mb, neb = K.merge_subset(sub, coarse, reg, ib, pad=pad, gate=gt)
        out[gt] = dict(ma=ma, mb=mb, n_eff=0.5 * (nea + neb),
                       n_eff_a=nea, n_eff_b=neb)
    del sub, fine, coarse, reg
    return out


def merged_sigma(level_dn, iso, n_eff):
    """Merged TEMPORAL sigma (rule 10), from the calibrated profile model."""
    s1 = float(np.sqrt(K.M.noise_var_dn(level_dn, K.gain_dn_per_e(iso),
                                        K.read_noise_e(iso))))
    return s1 / np.sqrt(max(n_eff, 1.0)), s1


# ------------------------------------------------------- averaging harness
def subset_index(n_roi, ladder=N_LADDER, nsub=200, seed=92, repeat_one=None):
    """Frozen subset draw, shared by the point estimate and every bootstrap.

    `repeat_one` is NC2: instead of N DISTINCT ROIs, the SAME ROI repeated N
    times, pushed through the identical averaging code path.  Registered
    expectation is Null(N) == Null(1) exactly.
    """
    rng = np.random.default_rng(seed)
    out = {}
    for N in ladder:
        if repeat_one is not None:
            out[N] = np.full((1, N), repeat_one, dtype=np.int64)
        elif N > n_roi:
            continue
        elif N == n_roi:
            out[N] = np.arange(n_roi, dtype=np.int64)[None, :]
        else:
            out[N] = np.stack([rng.choice(n_roi, size=N, replace=False)
                               for _ in range(nsub)]).astype(np.int64)
    return out


def _rms_for(d, fin, idx, strict=True):
    """Vectorised: mean over the ROI axis, then RMS about ZERO.

    `strict` (pre-registered primary) drops any (subset, draw) with a NaN
    member.  That is a selection on the outcome, so the non-strict variant --
    average whatever is finite -- is computed alongside it as the mandatory
    sensitivity check.  A disagreement between them is reportable, not
    resolvable in favour of the nicer number.
    """
    sub = d[idx]                       # (nsub, N, R)
    f = fin[idx]
    if strict:
        ok = f.all(1)                  # (nsub, R)
        if not ok.any():
            return np.nan, np.nan, np.nan, 0, 1.0
        v = sub.mean(1)[ok]
        drop = float(1.0 - ok.mean())
    else:
        ok = f.any(1)
        if not ok.any():
            return np.nan, np.nan, np.nan, 0, 1.0
        with np.errstate(invalid="ignore"):
            v = np.nanmean(sub, axis=1)[ok]
        drop = float(1.0 - ok.mean())
    return (float(np.sqrt((v ** 2).mean())), float(v.mean()),
            float(v.std(ddof=1)) if v.size > 1 else np.nan, int(v.size), drop)


def null_rms(d, index, strict=True):
    fin = np.isfinite(d)
    res = {}
    for N, idx in index.items():
        rms, mean, sd, n, drop = _rms_for(d, fin, idx, strict)
        res[N] = dict(rms=rms, mean=mean, sd=sd, n=n, drop_frac=drop)
    return res


def null_rms_boot(d, index, seed=92, nboot=2000, strict=True):
    """Bootstrap over DRAWS (rule 39 / M57 D-b: repetition, never a jackknife)."""
    base = null_rms(d, index, strict)
    R = d.shape[1]
    rng = np.random.default_rng(seed + 1)
    fin = np.isfinite(d)
    boots = {N: np.empty(nboot) for N in base}
    for t in range(nboot):
        sel = rng.integers(0, R, R)
        db, fb = d[:, sel], fin[:, sel]
        for N, idx in index.items():
            boots[N][t] = _rms_for(db, fb, idx, strict)[0]
    for N in base:
        b = boots[N][np.isfinite(boots[N])]
        base[N]["ci_lo"] = float(np.percentile(b, 2.5)) if b.size else np.nan
        base[N]["ci_hi"] = float(np.percentile(b, 97.5)) if b.size else np.nan
    return base


def exponent(res):
    """OLS of -log10 Null(N) on log10 N.  alpha = 0.5 is exact independence."""
    Ns = sorted(res)
    x = np.log10(np.array(Ns, float))
    y = -np.log10(np.array([res[N]["rms"] for N in Ns], float))
    if not np.all(np.isfinite(y)):
        return np.nan, np.nan
    xm = x - x.mean()
    a = float((xm * (y - y.mean())).sum() / (xm * xm).sum())
    pred = y.mean() + a * xm
    ss = float(((y - pred) ** 2).sum())
    sst = float(((y - y.mean()) ** 2).sum())
    return a, (1.0 - ss / sst if sst > 0 else np.nan)


def exponent_ci(d, index, seed=92, nboot=600, strict=True):
    rng = np.random.default_rng(seed + 7)
    R = d.shape[1]
    fin = np.isfinite(d)
    vals = []
    for _ in range(nboot):
        sel = rng.integers(0, R, R)
        db, fb = d[:, sel], fin[:, sel]
        res = {N: dict(rms=_rms_for(db, fb, idx, strict)[0])
               for N, idx in index.items()}
        a, _ = exponent(res)
        if np.isfinite(a):
            vals.append(a)
    v = np.array(vals)
    if v.size < 10:
        return np.nan, np.nan, np.nan
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)),
            float(v.std(ddof=1)))


def pair_corr(d):
    """Mean off-diagonal Pearson r of the per-ROI estimate across DRAWS.

    This is the crux: if the per-ROI estimates share a common-mode component
    the null cannot average down, and the mean off-diagonal r sets the floor at
    Null(1)*sqrt(rbar).
    """
    empty = dict(rbar=np.nan, rmed=np.nan, rmin=np.nan, rmax=np.nan,
                 n_pair=0, n_roi=0, se_rbar=np.nan)
    ok = np.isfinite(d).all(1)
    x = d[ok]
    if x.shape[0] < 2:
        return empty
    xc = x - x.mean(1, keepdims=True)
    sd = xc.std(1, ddof=1)
    good = sd > 0
    xc, sd = xc[good], sd[good]
    if xc.shape[0] < 2:
        return empty
    C = (xc @ xc.T) / (x.shape[1] - 1) / np.outer(sd, sd)
    m = C.shape[0]
    iu = np.triu_indices(m, 1)
    r = C[iu]
    return dict(rbar=float(r.mean()), rmed=float(np.median(r)),
                rmin=float(r.min()), rmax=float(r.max()),
                n_pair=int(len(r)), n_roi=int(m),
                se_rbar=float(r.std(ddof=1) / np.sqrt(len(r)))
                if len(r) > 1 else np.nan)


def pair_corr_pairwise(d):
    """Same statistic on PAIRWISE-COMPLETE observations.

    `pair_corr` drops any ROI with a single NaN across draws, which at high
    injection levels silently selects the ROIs.  This variant keeps every ROI
    and, for each pair, uses only the draws on which BOTH are finite.  Pairs
    with fewer than 16 joint-finite draws are skipped and counted.
    """
    m, R = d.shape
    fin = np.isfinite(d)
    rs, skipped = [], 0
    for i in range(m):
        for j in range(i + 1, m):
            ok = fin[i] & fin[j]
            if ok.sum() < 16:
                skipped += 1
                continue
            a, b = d[i, ok], d[j, ok]
            sa, sb = a.std(ddof=1), b.std(ddof=1)
            if sa <= 0 or sb <= 0:
                skipped += 1
                continue
            rs.append(float(((a - a.mean()) * (b - b.mean())).sum()
                            / ((ok.sum() - 1) * sa * sb)))
    if not rs:
        return dict(rbar=np.nan, n_pair=0, n_skipped=skipped)
    r = np.array(rs)
    return dict(rbar=float(r.mean()), rmed=float(np.median(r)),
                rmin=float(r.min()), rmax=float(r.max()),
                n_pair=int(r.size), n_skipped=int(skipped), n_roi=int(m))


def corr_boot(d, nboot=1000, seed=92):
    """Bootstrap `rbar` over DRAWS, not over pairs.

    The pairs share ROIs, so the across-pair standard error understates the
    uncertainty.  Resampling draws is the honest interval and is what
    PREREGISTRATION section 5 requires (empirical repetition only).
    """
    R = d.shape[1]
    rng = np.random.default_rng(seed + 11)
    vals = []
    for _ in range(nboot):
        sel = rng.integers(0, R, R)
        c = pair_corr(d[:, sel])
        if np.isfinite(c.get("rbar", np.nan)):
            vals.append(c["rbar"])
    v = np.array(vals)
    if v.size < 10:
        return dict(lo=np.nan, hi=np.nan, sd=np.nan, n=int(v.size))
    return dict(lo=float(np.percentile(v, 2.5)), hi=float(np.percentile(v, 97.5)),
                sd=float(v.std(ddof=1)), n=int(v.size))


def implied_floor(null1, rbar):
    """Null(1)*sqrt(rbar) -- the asymptotic floor of an equicorrelated average."""
    if not np.isfinite(rbar) or rbar <= 0:
        return 0.0
    return float(null1 * np.sqrt(rbar))


def n_eff_rois(N, rbar):
    if not np.isfinite(rbar):
        return np.nan
    return float(N / (1.0 + (N - 1) * rbar))


def fmt(v, w=9, p=5):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return " " * (w - 3) + "n/a"
    return f"{v:+{w}.{p}f}"
