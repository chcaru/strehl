"""RIM INSTRUMENT v6 -- edges SELECTED on a rim-free reference, MEASURED on the arm.

FIVE PREDECESSORS, ALL ON RECORD AS FAILURES.  This docstring is the reason the
sixth is not trusted more than it earned.

  v1  normalised by end plateaus, no step test   -> +428% on a clean image.
  v2  rim of the MEDIAN profile                  -> +0.02% on a real USM.
                                                    No power.
  v3  (V-HEADTOHEAD/rimcmp.py) per-edge excursion in units of that edge's own
      step.  Sound on `coffee-bean`.  INADMISSIBLE here: the arm reads +38.47%
      and the SAME IMAGE SMOOTHED, which has no rim by construction, reads
      +14.85%.
  v4  (rimv4.py) minimum-step gate.  REFUSED TO REPORT: at 40x the image's
      high-pass sigma a rim-free control still read +2.43%.
  v5  (rimv5.py) shoulder-flatness gate.  Drove the control to its structural
      null and FAILED COMMISSIONING ON EVERY ARM, in the most instructive way
      available:

          USM(100, r=2.0)   -> NONE, too few admissible edges
          USM(200, r=2.0)   -> NONE, too few admissible edges

      A rim IS shoulder structure.  Gating on flat shoulders therefore gates
      out exactly the defect the gauge exists to find: the admissibility
      criterion was correlated with the measurand.  Worse, the gate was chosen
      on a population that barely overlapped the one it was applied to --
      9.6% of edges admitted on the smoothed control against 0.4% on the arm.
      An instrument tuned on one population and applied to another is the
      defect this lane has now found six times in six lanes.

WHAT v6 CHANGES.  Selection and measurement are separated.

    sel = select(SMOOTHED arm)        <- computed ONCE, on a rim-free image
    measure(any image, sel)           <- the SAME pixels, every time

Selecting on a smoothed image means the criteria -- strong step, flat
shoulders, centred transition -- are properties of the SCENE, and cannot
correlate with an overshoot that smoothing has already removed.  Because the
location set is then fixed, every commissioning arm, every ladder rung and the
real measurement all sample identical pixels, so a difference between them is
a difference in the image and not in what was sampled.  v5 could not say that.

THE TEST THAT SHOWS THE FIX WORKED is not that the numbers look better: it is
that the USM arms return a number at all, on the same n as the arm itself.

THE STRUCTURAL NULL IS NOT ZERO.  `structural_null` measures what a purely
MONOTONE edge reads as a function of its own 10-90 width: 0.000% at 3 px,
-1.396% (dark) at 9 px, -2.644% at 11 px.  q reaches its plateau later on a
wide edge, so max(q[+2..+7]) falls short of 1 even though nothing overshoots.
Comparing a control against zero condemns a correct instrument on the dark axis
and flatters it by about 3 points on the bright axis.

NOISE IS MEASURED ON FLAT TILES, NOT DETAIL TILES.  v5 sized its noise ladder
from a high-pass residual over DETAIL ROIs and got strehl NOISIER than both
comparators -- the opposite of V-NOISE2's measured 1.54x-3.54x.  On detail
tiles a high-pass residual is dominated by resolved texture, so it is a
sharpness proxy wearing a noise label, and the ladder it sized added no noise
at all.  The decisive control never ran.  v6 takes sigma from the flat quartile.

INVOCATION.  Imported by rim.py.  `python rimv6.py` runs the self-test.
"""
import numpy as np
from scipy import ndimage

R = 12
TT = np.arange(-R, R + 1)
IB = np.where((TT >= 2) & (TT <= 7))[0]
ID = np.where((TT >= -7) & (TT <= -2))[0]
FLAT_CANDIDATES = (0.20, 0.15, 0.12, 0.10, 0.08, 0.06, 0.05, 0.04, 0.03)
MIN_REACH = 0.95


def select(ref, clip, rois, T, max_flat, min_step=0.0,
           nmax_per_roi=300, seed=11, min_reach=MIN_REACH):
    """Choose edge locations on `ref`, which MUST be a rim-free image.

    Returns a list of (tile_y, tile_x, yy, xx, dy, dx): the ROI, the edge
    pixel inside it, and the unit gradient direction.  Nothing about the arm
    under test is consulted, so the selection cannot be correlated with that
    arm's rim.

    `min_reach` is the ISOLATION criterion, added after 119MSDCF failed to
    commission.  The bright reading is max(q) over t=+2..+7, which is only a
    rim measurement if the profile HAS a plateau inside that zone.  An edge
    that is still climbing at t=+7 reads negative by construction and no
    structural null derived from an ISOLATED step can describe it.
    rimdiag119.py measured the difference directly on the rim-free reference:

        subject 113   q(+7) = 0.9794   plateaued by t=+7: 70.91% of edges
        subject 119   q(+7) = 0.9277   plateaued by t=+7: 24.65% of edges

    and 119's residual was consequently pinned near -4.3% at EVERY cut, so
    the flatness knob could not reach it.  Note 119's median step is 0.204
    against 113's 0.070: these are HIGH-contrast features, not soft ones.
    They are simply not isolated at the +/-7 px scale.

    This is a validity domain, stated rather than tuned: the instrument
    measures rims on ISOLATED occluding edges.  It is evaluated on the
    rim-free reference, where by construction no rim exists, so it can
    select neither for nor against the quantity being measured -- which is
    the rule that v5 broke.
    """
    rng = np.random.default_rng(seed)
    sel = []
    for (y, x) in rois:
        t = ref[y:y + T, x:x + T]
        if clip[y:y + T, x:x + T].any():
            continue
        sm = ndimage.uniform_filter(t, 3)
        gy, gx = np.gradient(sm)
        mag = np.hypot(gx, gy)
        ys, xs = np.nonzero(mag > np.percentile(mag, 99.0))
        keep = (ys > R + 2) & (ys < T - R - 2) & (xs > R + 2) & (xs < T - R - 2)
        ys, xs = ys[keep], xs[keep]
        if len(ys) == 0:
            continue
        if len(ys) > nmax_per_roi:
            i = rng.choice(len(ys), nmax_per_roi, replace=False)
            ys, xs = ys[i], xs[i]
        for yy, xx in zip(ys, xs):
            d = np.array([gx[yy, xx], gy[yy, xx]])
            n = np.hypot(*d)
            if n < 1e-12:
                continue
            d /= n
            p = t[np.round(yy + d[1] * TT).astype(int),
                  np.round(xx + d[0] * TT).astype(int)]
            lo, hi = p[:4].mean(), p[-4:].mean()
            step = hi - lo
            if step <= min_step:
                continue
            if max(p[:5].std(), p[-5:].std()) > max_flat * step:
                continue
            q = (p - lo) / step
            if abs(q[R] - 0.5) > 0.35:
                continue
            if q[R + 7] < min_reach or q[R - 7] > 1.0 - min_reach:
                continue
            sel.append((y, x, int(yy), int(xx), float(d[1]), float(d[0])))
    return sel


def measure(g, sel, T):
    """Read the rim at PRE-SELECTED locations.  No acceptance test runs here:
    every test already ran on the rim-free reference.  A test applied at this
    point could reject an edge BECAUSE it has a rim, which is v5's defect."""
    if not sel:
        return None
    ov, un, st, prof = [], [], [], []
    for (y, x, yy, xx, dy, dx) in sel:
        t = g[y:y + T, x:x + T]
        p = t[np.round(yy + dy * TT).astype(int),
              np.round(xx + dx * TT).astype(int)]
        lo, hi = p[:4].mean(), p[-4:].mean()
        step = hi - lo
        if step <= 1e-9:
            continue
        q = (p - lo) / step
        ov.append(q[IB].max() - 1.0)
        un.append(-q[ID].min())
        st.append(step)
        prof.append(q)
    if not ov:
        return None
    return dict(ov=np.array(ov), un=np.array(un), st=np.array(st),
                prof=np.array(prof), sel=len(sel))


def stats(e, nmin=30):
    if e is None or len(e["ov"]) < nmin:
        return None
    return dict(n=int(len(e["ov"])), sel=int(e["sel"]),
                bright=float(np.median(e["ov"])),
                dark=float(np.median(e["un"])),
                bright_p90=float(np.percentile(e["ov"], 90)),
                dark_p90=float(np.percentile(e["un"], 90)),
                step_median=float(np.median(e["st"])))


def boot_ci(e, nboot=2000, seed=17, nmin=30):
    """Bootstrap over EDGES -- the independent unit here.  Resampling pixels
    would understate the interval by roughly the profile length."""
    if e is None or len(e["ov"]) < nmin:
        return None
    o, u = e["ov"], e["un"]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(o), size=(nboot, len(o)))
    bo, bu = np.median(o[idx], axis=1), np.median(u[idx], axis=1)
    return (float(np.percentile(bo, 2.5)), float(np.percentile(bo, 97.5)),
            float(np.percentile(bu, 2.5)), float(np.percentile(bu, 97.5)))


def boot_diff(ea, eb, nboot=2000, seed=23, nmin=30):
    """CI on the DIFFERENCE, comparator minus reference, on BOTH axes.

    Both, deliberately.  An earlier form returned the bright axis only, and on
    `113MSDCF` the bright axis is level while the dark axis separates cleanly
    -- reporting one would have shown no difference where there is one, and in
    the direction that happens to flatter this project on one comparator and
    not the other.  A gauge reported on the axis its author expected to move is
    the same defect as a gate that can only convict in one direction.

    Unpaired: the two arms have their own selections, because a 1.005x raster
    scale drifts 1.3 px across a 256 px tile and correcting it would mean
    resampling, which adds blur to the quantity being measured.  Unpaired is
    the wider, conservative choice.

    Returns dict with `bright` and `dark`, each (median, lo, hi).
    """
    if ea is None or eb is None:
        return None
    if len(ea["ov"]) < nmin or len(eb["ov"]) < nmin:
        return None
    rng = np.random.default_rng(seed)
    out = {}
    for axis, ka, kb in (("bright", ea["ov"], eb["ov"]),
                         ("dark", ea["un"], eb["un"])):
        da = np.median(ka[rng.integers(0, len(ka), size=(nboot, len(ka)))],
                       axis=1)
        db = np.median(kb[rng.integers(0, len(kb), size=(nboot, len(kb)))],
                       axis=1)
        d = da - db
        out[axis] = (float(np.median(d)), float(np.percentile(d, 2.5)),
                     float(np.percentile(d, 97.5)))
    return out


def edge_width(e):
    """Median 10-90 width in px, from the CENTRAL SLOPE of the median profile.

    Not from the index at which q crosses 0.1 and 0.9: that is quantised to
    whole pixels, and the structural null is steep in width.  A quantised width
    made a 1 px change swing the null by 3.9 points and failed an arm on the
    lookup rather than on its image.  For a normalised profile rising 0 to 1
    the 10-90 width is 0.8 divided by the slope at the centre, which is
    continuous.
    """
    if e is None or not len(e["prof"]):
        return None
    q = np.median(e["prof"], axis=0)
    slope = 0.5 * (q[R + 1] - q[R - 1])
    if slope <= 1e-9:
        return None
    return float(0.8 / slope)


def _synth(blur, sigma=0.0, seed=5):
    rng = np.random.default_rng(seed)
    img = np.zeros((512, 512), np.float32)
    img[:, 256:] = 0.25
    img = ndimage.gaussian_filter(img, blur)
    if sigma:
        img = img + rng.normal(0.0, sigma, img.shape)
    return img.astype(np.float32)


_NULL_CACHE = {}
_NULL_DROPPED = {}


def null_table(blurs=None):
    """(width, bright, dark) for purely MONOTONE edges over a fine blur grid.

    Cached: it is the same table on every call and it is consulted once per
    candidate cut per arm.
    """
    if blurs is None:
        blurs = tuple(np.round(np.arange(0.6, 5.01, 0.2), 2))
    if blurs in _NULL_CACHE:
        return _NULL_CACHE[blurs]
    rows, dropped = [], []
    for b in blurs:
        img = _synth(b)
        s = select(img, np.zeros(img.shape, bool), [(0, 0)], 512, 1e9)
        e = measure(img, s, 512)
        r, w = stats(e), edge_width(e)
        if r is None or w is None:
            dropped.append(float(b))
            continue
        rows.append((float(w), r["bright"], r["dark"], float(b)))
    rows.sort()
    _NULL_CACHE[blurs] = rows
    _NULL_DROPPED[blurs] = dropped
    return rows


def structural_null(width):
    """What a purely MONOTONE edge of a given 10-90 width reads, by
    construction.  INTERPOLATED in width, not nearest-neighbour: the null is
    steep in width, and a nearest-neighbour lookup over a coarse grid failed an
    arm on the lookup rather than on its image.

    Zero for a sharp edge and growing with width, which is what identifies it
    as geometry rather than a defect: q reaches its plateau later on a wide
    edge, so max(q[+2..+7]) falls short of 1 even though nothing overshoots.

    RAISES outside the table's covered width range rather than clamping.
    `np.interp` returns the endpoint value for any width beyond the grid, so
    the previous form answered confidently for widths it had never evaluated
    -- and the isolation criterion truncates the grid, because a synthetic
    step too wide to plateau by t=+7 is rejected exactly as a real one is.
    That is the same defect this lane routed to the CLI: a bound that
    NARROWS SILENTLY cannot be caught downstream, because everything
    downstream is well-formed.
    """
    t = null_table()
    if not t:
        raise ValueError("structural_null: the null table is empty")
    w = np.array([r[0] for r in t])
    if not (w.min() <= width <= w.max()):
        raise ValueError(
            f"structural_null: width {width:.2f} px is outside the covered "
            f"range [{w.min():.2f}, {w.max():.2f}] px. The measured edges are "
            f"outside this instrument's validity domain; widen the zone or "
            f"report nothing, but do not clamp.")
    return (float(np.interp(width, w, [r[1] for r in t])),
            float(np.interp(width, w, [r[2] for r in t])), t)


def null_range():
    t = null_table()
    w = [r[0] for r in t]
    return (min(w), max(w)) if t else (None, None)


def try_null(width):
    """`structural_null` or None when the width is outside the covered range.

    Exists so that a caller which must keep going -- a cut sweep, a per-arm
    table -- has to handle the out-of-domain case EXPLICITLY, by name, and
    cannot get there by clamping.  `structural_null` itself still raises.
    """
    try:
        return structural_null(width)
    except ValueError:
        return None


def noise_floor(sigma, blur=1.5):
    """Noise ALONE on a rim-free synthetic step: the fooling direction v3's own
    docstring names, isolated from any scene."""
    img = _synth(blur, sigma)
    s = select(_synth(blur), np.zeros(img.shape, bool), [(0, 0)], 512, 1e9)
    return stats(measure(img, s, 512))


def choose_cut(g, clip, rois, T, nmin_edges=1000, candidates=FLAT_CANDIDATES):
    """Pick the flatness cut used at SELECTION time, on the rim-free control.

    The cut MINIMISES the control's departure from its structural null among
    cuts leaving at least `nmin_edges` edges.  There is no tolerance, so there
    is no tolerance to choose favourably; the residual at the chosen cut is
    reported as the instrument's FLOOR instead, and no arm gap smaller than the
    floor is claimed.  The arm comparison is never consulted.
    """
    ctrl = ndimage.gaussian_filter(g, 3.0).astype(np.float32)
    table, best, best_cost = [], None, None
    for c in candidates:
        s = select(ctrl, clip, rois, T, c)
        e = measure(ctrl, s, T)
        r = stats(e)
        if r is None:
            table.append((float(c), None, None, 0, None, None, None))
            continue
        w = edge_width(e)
        nn = try_null(w) if w else None
        if nn is None:
            table.append((float(c), r["bright"], r["dark"], r["n"],
                          float(w) if w else None, None, None))
            continue
        nb, nd, _ = nn
        rb, rd = r["bright"] - nb, r["dark"] - nd
        table.append((float(c), r["bright"], r["dark"], r["n"],
                      float(w) if w else None, float(rb), float(rd)))
        if r["n"] >= nmin_edges and (best_cost is None or abs(rb) < best_cost):
            best, best_cost = float(c), abs(rb)
    del ctrl
    fl = None
    if best is not None:
        row = [t for t in table if t[0] == best][0]
        fl = dict(cut=best, bright_residual=row[5], dark_residual=row[6],
                  width=row[4], n=row[3])
    return best, table, fl


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(__doc__)
    print("SELF-TEST 1 -- planted overshoot on a synthetic step.")
    print("  Selection runs on the UNMODIFIED step; the planted rim is then")
    print("  measured at those same locations.  n must NOT fall as the rim")
    print("  grows: that is the v5 failure this version exists to remove.")
    base = _synth(1.5)
    s = select(base, np.zeros(base.shape, bool), [(0, 0)], 512, 1e9)
    for planted in (0.00, 0.05, 0.20, 0.50):
        img = base if not planted else (
            base + planted * (base - ndimage.gaussian_filter(base, 3.0))
        ).astype(np.float32)
        r = stats(measure(img, s, 512))
        print(f"  planted {planted*100:5.1f}%  ->  {r['bright']*100:+7.3f}%"
              f"   n={r['n']}  (selected {r['sel']})")

    print("\nSELF-TEST 2 -- noise alone, on an image with no rim.")
    for sg in (0.0, 0.002, 0.005, 0.010):
        r = noise_floor(sg)
        print(f"  noise sigma {sg:.3f}   bright {r['bright']*100:+7.3f}%"
              f"   dark {r['dark']*100:+7.3f}%   n={r['n']}")

    print("\nSELF-TEST 3 -- the structural null against edge width.")
    print("  Interpolated, not nearest-neighbour: a coarse lookup swung the")
    print("  null by 3.9 points across one pixel of width and failed an arm on")
    print("  the lookup rather than on its image.")
    lo_w, hi_w = null_range()
    print(f"  COVERED RANGE {lo_w:.2f} .. {hi_w:.2f} px.  Outside it this")
    print("  RAISES rather than clamping: np.interp would answer with the")
    print("  endpoint value for a width it never evaluated.")
    for w in (3.0, 5.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0):
        try:
            br, dk, _ = structural_null(w)
            print(f"  width {w:>5.1f} px   bright {br*100:+7.3f}%"
                  f"   dark {dk*100:+7.3f}%")
        except ValueError:
            print(f"  width {w:>5.1f} px   REFUSED -- outside the covered "
                  f"range, correctly")

    print("\nSELF-TEST 4 -- the scale arm's sign is ARM-DEPENDENT.")
    print("  A downsample+cubic-upsample both ADDS ringing and REMOVES")
    print("  resolution.  Which dominates depends on how sharp the source was,")
    print("  so 'resampling must raise the reading' is not a universal test and")
    print("  is reported as a diagnostic rather than a pass/fail.")
    for tag, src in (("sharp (USM 100, r=2.0)",
                      np.clip(base + 1.0 * (base -
                              ndimage.gaussian_filter(base, 2.0)),
                              0, None).astype(np.float32)),
                     ("as-is", base),
                     ("blurred (sigma 2.0)",
                      ndimage.gaussian_filter(base, 2.0).astype(np.float32))):
        b0 = stats(measure(src, s, 512))["bright"]
        up = ndimage.zoom(src[::2, ::2], 2.0, order=3).astype(np.float32)
        up = up[:512, :512]
        b1 = stats(measure(up, s, 512))["bright"]
        print(f"  source {tag:<24} {b0*100:+7.3f}% -> {b1*100:+7.3f}%"
              f"   delta {(b1-b0)*100:+7.3f}%")
