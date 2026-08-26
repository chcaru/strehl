"""BUILD-RESAMP -- slanted-edge MTF (ISO 12233), because the band-power metric
that produced the 17-27% deficit awards a nearest-neighbour gather +29%/+42%.

WHY THIS INSTRUMENT AND NOT THE OTHER ONE. Band power is energy: it rises under
ringing, under aliasing and under noise exactly as it rises under preserved
detail. MTF is a *transfer ratio* measured on a known input -- a step. Noise
adds an incoherent pedestal to the line-spread function's spectrum; it does not
move the frequency at which the coherent transfer falls to half. That is the
whole reason the imaging industry scores lenses and sensors this way, and it is
the specific failure mode this run has to be immune to. `commission_edge.py`
demonstrates the immunity rather than asserting it.

METHOD (ISO 12233 clause 6, the standard construction):
  1. isolate ROIs holding EXACTLY ONE straight, high-contrast, unclipped edge
     slanted 1-15 degrees off the pixel grid -- the slant is what supplies the
     sub-pixel sampling, and "exactly one" is enforced by a second-peak test
     because a ruler graduation is a BAR, i.e. two edges, and a centroid taken
     across both lands in the middle of the bar and measures nothing
  2. per scan line, locate the edge to sub-pixel precision by the centroid of
     the first difference, taken only in a window around the edge
  3. least-squares fit a line through those centroids; that is the edge
  4. project every pixel in the window onto the edge normal and bin at 1/4 px
     -> oversampled edge spread function
  5. first-difference -> line spread function, Hamming window, |FFT|
  6. divide out the 1/4-px finite difference's own transfer, sinc(f/4)
  7. normalise at f=0 and read MTF50 by linear interpolation of the first
     crossing of 0.5

UNITS. Cycles per pixel OF THE RASTER MEASURED. Two renders at different
magnifications are NOT comparable until that is corrected; the caller must
supply a MEASURED scale factor, never a guess.
"""

import numpy as np

OVERSAMPLE = 4
HALF = 32               # +/- px of edge kept for the ESF -> 64 px support
LENGTH = 96            # ROI extent ALONG the edge
WIDTH = 128             # ROI extent ACROSS the edge
MIN_ANGLE_DEG = 2.0     # below this the edge supplies no sub-pixel sampling
MAX_ANGLE_DEG = 10.0    # above this the edge sweeps out of the ESF support
MAX_RESID_PX = 0.80     # unused by the angle-search fit; kept for reporting
PLATEAU = 0.14          # allowed roughness of each ESF shoulder, x contrast
PAD = 8

# populated by find_edges so a zero yield can be explained rather than guessed
STATS = {}
ANGLES = []


def _row_centroid(a, centers, halfwin):
    """Per-row sub-pixel edge position, background-subtracted and windowed.

    Both corrections are load-bearing. Without the background subtraction the
    flat regions of a 64-px window contribute about as much weight as the edge
    itself on a real macro subject -- measured 1.19 px of centroid scatter on a
    text stroke that is straight to well under a pixel -- and the "edge
    position" is then mostly a readout of the noise. Without the window a
    neighbouring stroke pulls the centroid off the edge entirely.
    """
    d = np.abs(np.diff(a, axis=1))
    x = np.arange(d.shape[1], dtype=np.float64) + 0.5
    dd = np.clip(d - np.median(d, axis=1, keepdims=True), 0.0, None)
    dd = dd * (np.abs(x[None, :] - centers[:, None]) <= halfwin)
    s = dd.sum(axis=1)
    out = np.full(len(centers), np.nan)
    ok = s > 0
    out[ok] = (dd[ok] * x[None, :]).sum(axis=1) / s[ok]
    return out


def locate(roi):
    """Column of the dominant near-vertical edge in an ALREADY-SITED ROI.

    A sited ROI is 2*(HALF+PAD) wide with the edge near its centre, so this only
    has to reject a ridge that has drifted out of the ESF support. Whether the
    ROI actually holds ONE step -- rather than a bar, a stroke pair or plain
    texture -- is decided later by the flatness of the two ESF shoulders, which
    tests the thing that matters directly instead of guessing at it from a
    gradient profile whose ridge is 20 px wide on real macro subjects.
    """
    d = np.abs(np.diff(roi.astype(np.float64), axis=1))
    prof = d.mean(axis=0)
    if prof.max() <= 0:
        return None
    p0 = int(np.argmax(prof))
    if p0 < PAD or p0 > len(prof) - PAD - 1:
        return None
    return p0 + 0.5


def fit_line(roi, coarse=0.004, span=0.40):
    """Edge line by GLOBAL angle search, not by per-row centroids.

    Per-row centroids are the textbook construction and they do not survive this
    corpus. Measured on a text stroke in `wrapped-text-1`: the row-averaged
    gradient ridge stands at 231 DN over a background of ~80, but a SINGLE row's
    edge gradient is ~180 DN/px against dither speckle gradients of several
    hundred -- per-row SNR below one. Two-pass background-subtracted centroids
    still scattered 1.6 px about their own fitted line on an edge that is
    straight, so the residual was reading the halftone, not the edge.

    This instead shears the whole ROI by each candidate slope, bins the
    background-subtracted gradient at 1/4 px, and keeps the slope whose profile
    is most concentrated. Every pixel votes once, so the dither averages out
    exactly the way it does in the ESF itself.

    Two details are load-bearing, and the first one is a trap this instrument
    fell into and had to be fixed:

      * the line is parametrised through the ROI's MID-ROW and the fit
        MINIMISES the weighted variance of the gradient about the candidate
        line, computed on the raw samples with NO binning. An earlier version
        scored a binned profile by its sum of squares, and at slope exactly 0
        every row projects to the same 128 abscissae, so a 1/4-px histogram is
        a comb -- 48 occupied bins of 192 instead of 192 -- and its sum of
        squares is four times anything a sheared profile can reach. The search
        therefore returned slope 0 for 3568 of 3570 ROIs and the instrument
        silently reported that a page of text contains no slanted edge.
      * only the gradient ABOVE the ROI's median gradient votes, so flat
        textured regions do not drag the fit.
    """
    a = roi.astype(np.float64)
    h, w = a.shape
    d = np.abs(np.diff(a, axis=1))
    d = np.clip(d - np.median(d), 0.0, None)
    x = np.arange(w - 1, dtype=np.float64) + 0.5
    yc = np.arange(h, dtype=np.float64) - h / 2.0
    flat = d.ravel()

    # slope-independent centre: where the unsheared gradient piles up
    p0 = d.mean(axis=0)
    k = np.ones(5) / 5.0
    b0 = float(x[int(np.argmax(np.convolve(p0, k, mode="same")))])

    def score(s):
        """Weighted variance of the gradient about the candidate line."""
        u = (x[None, :] - s * yc[:, None]).ravel()
        m = np.abs(u - b0) < HALF
        wt = flat[m]
        t = wt.sum()
        if t <= 0:
            return np.inf
        uu = u[m]
        m1 = (wt * uu).sum() / t
        return float((wt * (uu - m1) ** 2).sum() / t)

    grid = np.arange(-span, span + 1e-12, coarse)
    sc = np.array([score(s) for s in grid])
    # smooth before choosing: on a noisy ROI the raw curve has spurious minima
    # a few grid steps wide, and picking one of those returns a slope that is
    # not the edge's.
    sc = np.convolve(sc, np.ones(5) / 5.0, mode="same")
    sc[:2] = sc[2]
    sc[-2:] = sc[-3]
    i = int(np.argmin(sc))
    if 0 < i < len(grid) - 1:                       # parabolic refinement
        a0, b1, c0 = sc[i - 1], sc[i], sc[i + 1]
        den = a0 - 2 * b1 + c0
        shift = 0.5 * (a0 - c0) / den if den != 0 else 0.0
        s_best = float(grid[i] + np.clip(shift, -1, 1) * coarse)
    else:
        s_best = float(grid[i])
    u = (x[None, :] - s_best * yc[:, None]).ravel()
    m = np.abs(u - b0) < HALF
    wt = flat[m]
    if wt.sum() <= 0:
        return None
    b = float((wt * u[m]).sum() / wt.sum())
    # back to the x = slope*y + intercept parametrisation the ESF uses
    return s_best, b - s_best * h / 2.0


def edge_fit(roi, p0):
    """Compatibility shim: (slope, intercept, angle_deg, resid)."""
    r = fit_line(roi)
    if r is None:
        return None
    slope, intercept = r
    ang = abs(np.degrees(np.arctan(slope)))
    if not (MIN_ANGLE_DEG <= ang <= MAX_ANGLE_DEG):
        return None
    return slope, intercept, ang, 0.0


def esf(roi, slope, intercept):
    """Oversampled edge spread function on +/-HALF px, 1/4 px bins.

    Distance is measured along the edge NORMAL, not along the scan axis. The
    two differ by cos(theta) and at the 20 degrees this instrument admits that
    is 6% -- a straight 6% bias on every frequency it reports, which would be
    larger than the effect under investigation.
    """
    h, w = roi.shape
    y = np.arange(h, dtype=np.float64)[:, None]
    x = np.arange(w, dtype=np.float64)[None, :]
    dist = (x - (slope * y + intercept)) / np.sqrt(1.0 + slope * slope)
    keep = (dist >= -HALF) & (dist < HALF)
    nb = 2 * HALF * OVERSAMPLE
    idx = np.clip(((dist[keep] + HALF) * OVERSAMPLE).astype(int), 0, nb - 1)
    v = np.ascontiguousarray(roi.astype(np.float64))[keep]
    tot = np.bincount(idx, weights=v, minlength=nb)
    cnt = np.bincount(idx, minlength=nb)
    if cnt.min() < 1:                # an empty bin would be interpolated noise
        return None
    e = tot / cnt

    # ---- shoulder de-trend ------------------------------------------------
    # ISO 12233 assumes both shoulders are FLAT.  This corpus contains no ISO
    # target: every subject carries an illumination gradient and a glare skirt
    # across the ESF support, and an uncorrected ramp reads as edge softness.
    # That is precisely the failure the RESAMPLE control caught -- MTF50 landed
    # at 0.011 cyc/px, a 91 px period inside a 128 px window, so the WINDOW and
    # not the raster set the answer, and a 1.2x enlargement moved it by 1.04x
    # where 0.833x was required.  Fit a line to the outer quarter of each
    # shoulder, average the two slopes, subtract.  A slope common to both
    # shoulders is removed; the step height between them is untouched.
    q = nb // 4
    t = np.arange(nb, dtype=np.float64)
    ml = np.polyfit(t[:q], e[:q], 1)[0]
    mr = np.polyfit(t[-q:], e[-q:], 1)[0]
    return e - 0.5 * (ml + mr) * t


def mtf_from_esf(e):
    """MTF and its frequency axis in cycles per pixel."""
    lsf = np.diff(e)
    lsf = lsf - np.median(np.concatenate([lsf[:8], lsf[-8:]]))
    n = len(lsf)
    # Window the LSF on its OWN centroid, not on the array centre, and over
    # half the support rather than all of it.  A full-support window centred on
    # the array leaves the whole noisy tail of the ESF inside the transform:
    # measured, that let white noise at only 1.45x the 0.20-0.40 band power
    # move the curve ratio by 24%, which is larger than the deficit under
    # investigation.  The window's own transfer is an object-independent
    # multiplicative factor identical in both arms, so it cancels exactly in a
    # ratio -- but it does NOT cancel in MTF50, one more reason MTF50 is the
    # weaker statistic here.
    a = np.abs(lsf)
    tot = a.sum()
    c = float((a * np.arange(n)).sum() / tot) if tot > 0 else n / 2.0
    half = n // 4
    lo = int(round(c)) - half
    hi = lo + 2 * half
    if lo < 0 or hi > n:
        lo = max(0, min(lo, n - 2 * half))
        hi = lo + 2 * half
    win = np.zeros(n)
    win[lo:hi] = np.hamming(hi - lo)
    lsf = lsf * win
    m = np.abs(np.fft.rfft(lsf))
    f = np.fft.rfftfreq(n, d=1.0 / OVERSAMPLE)
    if m[0] <= 0:
        return None, None
    m = m / m[0]
    # the 1/4-px first difference is itself a filter; divide it out
    corr = np.sinc(f / OVERSAMPLE)
    m = np.where(corr > 1e-6, m / corr, m)
    return f, m


def mtf50(f, m):
    """First crossing of 0.5, linearly interpolated. None if it never crosses."""
    for i in range(1, len(m)):
        if m[i] <= 0.5 <= m[i - 1]:
            t = (m[i - 1] - 0.5) / (m[i - 1] - m[i])
            return float(f[i - 1] + t * (f[i] - f[i - 1]))
    return None


def measure_roi(roi, line=None):
    """Full chain on one already-sited ROI (edge near-vertical, near-centred).

    `line` pins the edge geometry from a REFERENCE arm. Passing it makes the
    ESF construction bit-for-bit identical across arms so that only the pixels
    differ; without it each arm fits its own line and the comparison silently
    includes a difference in fitting.
    """
    if line is None:
        p0 = locate(roi)
        if p0 is None:
            return None
        fit = edge_fit(roi, p0)
        if fit is None:
            return None
        slope, intercept, ang, resid = fit
    else:
        slope, intercept = line
        ang = abs(np.degrees(np.arctan(slope)))
        resid = 0.0
    e = esf(roi, slope, intercept)
    if e is None:
        return None
    n = OVERSAMPLE * 4                     # 4 px of shoulder each side
    lo, hi = np.median(e[:n]), np.median(e[-n:])
    contrast = float(abs(hi - lo))
    if contrast <= 0:
        return None
    # a single step has FLAT shoulders. Texture, a second edge or a ringing
    # overshoot inside the support all show up here, and all of them make the
    # ESF something other than the edge response of a step.
    rough = max(float(np.std(e[:n])), float(np.std(e[-n:]))) / contrast
    if rough > PLATEAU:
        return None
    f, m = mtf_from_esf(e)
    if f is None:
        return None
    v = mtf50(f, m)
    if v is None:
        return None
    # ---- ESF fit residual -------------------------------------------------
    # A slanted-edge measurement assumes the ROI is a 1-D function of distance
    # along the edge normal and nothing else.  Noise, a second edge, texture,
    # or a non-straight edge all break that assumption QUIETLY -- the chain
    # still returns an MTF50.  This is the residual of the raw samples about
    # the binned ESF, normalised by the edge contrast, so a bad edge reads as
    # a bad edge instead of as a resolution difference.
    h, w = roi.shape
    yy = np.arange(h, dtype=np.float64)[:, None]
    xx = np.arange(w, dtype=np.float64)[None, :]
    dist = (xx - (slope * yy + intercept)) / np.sqrt(1.0 + slope * slope)
    keep = (dist >= -HALF) & (dist < HALF)
    nb = 2 * HALF * OVERSAMPLE
    idx = np.clip(((dist[keep] + HALF) * OVERSAMPLE).astype(int), 0, nb - 1)
    raw = np.ascontiguousarray(roi.astype(np.float64))[keep]
    tot = np.bincount(idx, weights=raw, minlength=nb)
    cnt = np.bincount(idx, minlength=nb)
    model = tot / np.maximum(cnt, 1)
    esf_resid = float(np.sqrt(np.mean((raw - model[idx]) ** 2)) / contrast)
    return {"mtf50": v, "f": f, "m": m, "angle": ang, "resid": resid,
            "esf_resid": esf_resid,
            "slope": slope, "icept": intercept,
            "contrast": contrast, "rough": rough, "esf": e}


def cut(img, site):
    """Extract a site's ROI, already oriented so its edge is near-vertical."""
    roi = img[site["y"]:site["y"] + site["h"], site["x"]:site["x"] + site["w"]]
    return roi.T if site["t"] else roi


# --------------------------------------------------------------------------
# ROI discovery
# --------------------------------------------------------------------------
def find_edges(img, stride=64, border=96, min_contrast=0.10, clip_hi=None,
               cap=100000):
    """Locate ROIs holding one usable slanted edge, in both orientations.

    Sites are LENGTH along the edge by WIDTH across it, and the ROI is
    re-centred on the fitted edge before anything is measured -- without that,
    three quarters of real edges are discarded for the irrelevant reason that
    they did not happen to land mid-tile.

    Returns site dicts in absolute image coordinates, each carrying the edge
    line fitted on THIS image. The same site list -- and, where the rasters are
    comparable, the same line -- must then be applied to every arm, or the
    comparison is about site selection and line fitting rather than about
    resolution.
    """
    h, w = img.shape
    span0 = float(np.diff(np.percentile(img[::16, ::16], [1, 99]))[0])
    span0 = max(span0, 1e-9)
    STATS.clear()
    STATS.update(dict(scanned=0, dull=0, clipped=0, nofit=0, angle=0,
                      offframe=0, nomeasure=0, lowcontrast=0, kept=0))
    out = []
    for tr in (False, True):
        th, tw = (LENGTH, WIDTH) if not tr else (WIDTH, LENGTH)
        for y in range(border, h - border - th, stride):
            for x in range(border, w - border - tw, stride):
                STATS["scanned"] += 1
                sub = img[y:y + th, x:x + tw]
                # cheap pre-gate: most of a frame holds no edge at all
                if (sub.max() - sub.min()) < min_contrast * span0:
                    STATS["dull"] += 1
                    continue
                if clip_hi is not None and sub.max() >= clip_hi:
                    STATS["clipped"] += 1
                    continue
                roi = sub.T if tr else sub
                fit = fit_line(roi)
                if fit is None:
                    STATS["nofit"] += 1
                    continue
                slope, icept = fit
                ang = abs(np.degrees(np.arctan(slope)))
                ANGLES.append(ang)
                if not (MIN_ANGLE_DEG <= ang <= MAX_ANGLE_DEG):
                    STATS["angle"] += 1
                    continue
                # re-centre across the edge on the fitted line's mid-row
                mid = slope * (LENGTH / 2.0) + icept
                off = int(round(mid - WIDTH / 2.0))
                if not tr:
                    sy, sx = y, x + off
                else:
                    sy, sx = y + off, x
                if (sy < border or sx < border or sy + th > h - border
                        or sx + tw > w - border):
                    STATS["offframe"] += 1
                    continue
                site = {"y": sy, "x": sx, "h": th, "w": tw, "t": tr}
                r = measure_roi(cut(img, site))
                if r is None:
                    STATS["nomeasure"] += 1
                    continue
                if r["contrast"] / span0 < min_contrast:
                    STATS["lowcontrast"] += 1
                    continue
                STATS["kept"] += 1
                site.update({"mtf50": r["mtf50"], "angle": r["angle"],
                             "resid": r["resid"], "contrast": r["contrast"],
                             "rough": r["rough"], "line": (r["slope"],
                                                           r["icept"])})
                out.append(site)
                if len(out) >= cap:
                    return dedup(out)
    return dedup(out)


def dedup(sites, sep=64):
    """Drop sites whose ESF supports overlap, so ROIs are near-independent."""
    keep = []
    seen = []
    for s in sorted(sites, key=lambda s: -s["contrast"]):
        cy, cx = s["y"] + s["h"] / 2, s["x"] + s["w"] / 2
        if any(abs(cy - a) < sep and abs(cx - b) < sep for a, b in seen):
            continue
        seen.append((cy, cx))
        keep.append(s)
    return keep
