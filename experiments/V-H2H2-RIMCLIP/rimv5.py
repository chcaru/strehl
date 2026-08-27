"""RIM INSTRUMENT v5 -- admissibility on SHOULDER FLATNESS, not on step size.

THE FOURTH VERSION.  Three predecessors are on record as failures and this
docstring exists so the fourth is not trusted more than it earned.

  v1  normalised by end plateaus with no step test  -> +428% on a clean image.
  v2  took the rim OF THE MEDIAN PROFILE            -> +0.02% on a real USM.
      No power.
  v3  (V-HEADTOHEAD/rimcmp.py) per-edge excursion in units of that edge's own
      step.  Sound on `coffee-bean`.  INADMISSIBLE here: measured by rim.py on
      `113MSDCF`, the arm as-is reads +38.47% and the SAME IMAGE SMOOTHED --
      which has no rim by construction -- reads +14.85%.
  v4  (rimv4.py) added a minimum-step gate.  It REFUSED TO REPORT, which is the
      correct behaviour and not a success: swept to 40x the image's high-pass
      sigma the rim-free control still read +2.43% on 294 surviving edges.
      Raising a threshold until a control looks acceptable, with no account of
      why it was wrong, is fitting the instrument to the answer.

WHAT THE DIAGNOSIS FOUND (rimdiag.py, on the rim-free control, 16559 edges).
Step magnitude is not the discriminator; shoulder flatness is.

    shoulder flatness cut     surviving edges     control bright rim
      0.20*step  (v3's)             16559               +14.848%
      0.10*step                     11335                +7.491%
      0.05*step                      6327                +1.525%
      0.05*step over 5 px            5279                +0.117%

The mechanism: v3's flatness test allows a shoulder standard deviation of a
FIFTH of the step, and the statistic then takes a MAX over six samples.  An
edge sitting in texture has competing structure inside its own shoulders, so
the max exceeds a plateau that was never a plateau.  That is v1's failure --
"measuring its own denominator" -- surviving into v3 in a milder form, invisible
on a subject whose silhouette steps are large and clean.

A DISCRIMINATOR THAT DID NOT WORK, RECORDED BECAUSE IT WAS TRIED.  A monotone
core test -- requiring the profile to rise across t=-2..+2 -- moved the control
from +14.848% to +14.843%.  Inert.  It is not in v5.

THE SELECTION EFFECT THIS GATE INTRODUCES, AND WHY IT IS NOT HIDDEN.  Flatness
is measured in units of step, so a noisier arm has less flat shoulders and is
admitted less often.  That cuts BOTH ways and neither direction is obviously
dominant: noise inflates a max-based excursion (favouring a finding of rims in
the noisier comparators, i.e. favouring this project), while gating on flatness
removes exactly those noisy edges (favouring the opposite).  The gate therefore
cannot be argued to be safe, and it is not argued to be.  It is bracketed
instead, by three things rim.py reports beside every number: the per-arm
ADMISSION RATE, the per-arm step distribution of admitted edges, and a NOISE
LADDER that adds noise to the quiet arm up to each comparator's measured sigma.
If the ladder moves the quiet arm by more than the arm gap, there is no result.

THE CONTROL FLOOR IS PART OF THE READING, AND THE NULL IS NOT ZERO.  A rim-free
control does not read zero and must not be asked to.  `structural_null` measures
what a purely MONOTONE edge reads as a function of its own 10-90 width: 0.000%
at 3 px, -1.396% (dark) at 9 px, -2.644% at 11 px.  q reaches its plateau later
on a wide edge, so max(q[+2..+7]) falls short of 1 even though nothing
overshoots.  An earlier form of `choose_gate` compared the control to zero and
so declared every cut a failure on the dark axis while flattering the bright
axis by about 3 points.  The residual against the correct null is reported as
the instrument's FLOOR, and an arm gap smaller than the floor is reported as
unresolved rather than as a win.

INVOCATION.  Imported by rim.py.  `python rimv5.py` runs the self-test.
"""
import numpy as np
from scipy import ndimage

R = 12
TT = np.arange(-R, R + 1)
IB = np.where((TT >= 2) & (TT <= 7))[0]
ID = np.where((TT >= -7) & (TT <= -2))[0]
FLAT_CANDIDATES = (0.20, 0.15, 0.12, 0.10, 0.08, 0.07, 0.06,
                   0.05, 0.04, 0.03, 0.02)


def edges(g, clip, rois, T, nmax_per_roi=300, seed=11):
    """v3's edge walk and v3's arithmetic, returning PER-EDGE values.

    v3's acceptance tests are kept verbatim and in v3's order: 99th-percentile
    gradient selection, positive step, plateau flatness at 0.20*step, centred
    transition at 0.35.  v5 adds no test HERE -- it returns `flat` so that
    admissibility can be applied afterwards, which is what lets one gate be
    chosen on a control and then applied identically to every arm.

    Also returns `seen`, the number of edges that reached the acceptance tests,
    so the admission rate can be reported per arm rather than assumed equal.
    """
    rng = np.random.default_rng(seed)
    ov, un, st, fl, prof = [], [], [], [], []
    seen = 0
    for (y, x) in rois:
        t = g[y:y + T, x:x + T]
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
            seen += 1
            lo, hi = p[:4].mean(), p[-4:].mean()
            step = hi - lo
            if step <= 0:
                continue
            if p[:4].std() > 0.20 * step or p[-4:].std() > 0.20 * step:
                continue
            q = (p - lo) / step
            if abs(q[R] - 0.5) > 0.35:
                continue
            ov.append(q[IB].max() - 1.0)
            un.append(-q[ID].min())
            st.append(step)
            fl.append(max(p[:5].std(), p[-5:].std()) / step)
            prof.append(q)
    if not ov:
        return None
    return dict(ov=np.array(ov), un=np.array(un), st=np.array(st),
                fl=np.array(fl), prof=np.array(prof), seen=int(seen))


def _mask(e, max_flat, min_step):
    return (e["fl"] <= max_flat) & (e["st"] >= min_step)


def gated(e, max_flat, min_step=0.0, nmin=30):
    """Median bright/dark rim over ADMISSIBLE edges."""
    if e is None:
        return None
    m = _mask(e, max_flat, min_step)
    if m.sum() < nmin:
        return None
    return dict(n=int(m.sum()), seen=int(e["seen"]),
                admit=float(m.sum() / max(e["seen"], 1)),
                bright=float(np.median(e["ov"][m])),
                dark=float(np.median(e["un"][m])),
                bright_p90=float(np.percentile(e["ov"][m], 90)),
                dark_p90=float(np.percentile(e["un"][m], 90)),
                step_median=float(np.median(e["st"][m])))


def boot_ci(e, max_flat, min_step=0.0, nboot=2000, seed=17, nmin=30):
    """Bootstrap CI over EDGES.  Resamples edges, not pixels: the edge is the
    independent unit here and treating pixels as independent would understate
    the interval by roughly the profile length."""
    if e is None:
        return None
    m = _mask(e, max_flat, min_step)
    if m.sum() < nmin:
        return None
    o, u = e["ov"][m], e["un"][m]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(o), size=(nboot, len(o)))
    bo, bu = np.median(o[idx], axis=1), np.median(u[idx], axis=1)
    return (float(np.percentile(bo, 2.5)), float(np.percentile(bo, 97.5)),
            float(np.percentile(bu, 2.5)), float(np.percentile(bu, 97.5)))


def boot_diff(ea, eb, max_flat, min_step=0.0, nboot=2000, seed=23, nmin=30):
    """CI on the DIFFERENCE between two arms.

    The arms do not share edges -- they cannot, since a 1.005x scale puts
    up to 1.3 px of drift across a 256 px tile and correcting it would mean
    resampling, which adds blur to the quantity being measured.  So this is an
    unpaired bootstrap: each arm's edges are resampled independently.  That is
    wider than a paired interval would be, which is the conservative direction.
    """
    if ea is None or eb is None:
        return None
    ma, mb = _mask(ea, max_flat, min_step), _mask(eb, max_flat, min_step)
    if ma.sum() < nmin or mb.sum() < nmin:
        return None
    a, b = ea["ov"][ma], eb["ov"][mb]
    rng = np.random.default_rng(seed)
    da = np.median(a[rng.integers(0, len(a), size=(nboot, len(a)))], axis=1)
    db = np.median(b[rng.integers(0, len(b), size=(nboot, len(b)))], axis=1)
    d = da - db
    return (float(np.median(d)), float(np.percentile(d, 2.5)),
            float(np.percentile(d, 97.5)))


def floor(sigma=0.0, blur=1.5, seed=5):
    """The reading a rim-free image gives when there is NO texture to confuse
    it -- a synthetic blurred step, optionally with noise.

    This is the STRUCTURAL NULL, and it is not zero.  For a monotone edge the
    bright statistic is max(q[+2..+7]) - 1, and q does not reach 1 until the
    profile reaches its plateau, so a wider edge reads MORE NEGATIVE on both
    bright and dark purely from its own width.  The correct null for a rim-free
    control is therefore this value at the control's own blur, not zero, and
    `choose_gate` compares against it rather than against zero.  Quoting zero
    would make a correct instrument look broken on the dark rim and would make
    the bright rim look about 3 points better than it is.
    """
    rng = np.random.default_rng(seed)
    img = np.zeros((512, 512), np.float32)
    img[:, 256:] = 0.25
    img = ndimage.gaussian_filter(img, blur)
    if sigma:
        img = img + rng.normal(0.0, sigma, img.shape)
    e = edges(img.astype(np.float32), np.zeros(img.shape, bool), [(0, 0)], 512)
    return gated(e, 1e9, 0.0)


def edge_width(e, max_flat, min_step=0.0):
    """Median 10-90 width, in px, of the ADMITTED edges.

    The structural null above depends on edge width, so a comparison between
    two arms only cancels it if the arms present edges of similar width.  That
    is an assumption, so it is measured and reported rather than assumed.
    """
    if e is None:
        return None
    m = _mask(e, max_flat, min_step)
    if m.sum() < 1:
        return None
    q = e["prof"][m]
    w = []
    for row in q:
        lo_i = np.where(row <= 0.1)[0]
        hi_i = np.where(row >= 0.9)[0]
        if len(lo_i) and len(hi_i):
            a, b = lo_i[lo_i <= R], hi_i[hi_i >= R]
            if len(a) and len(b):
                w.append(float(b[0] - a[-1]))
    return float(np.median(w)) if w else None


def structural_null(width, blurs=(0.6, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)):
    """The rim a MONOTONE edge of a given 10-90 width reads, by construction.

    Measured here, not asserted:

        blur 0.6  width  3 px   bright  +0.000%   dark  +0.000%
        blur 3.0  width  9 px   bright  -0.576%   dark  -1.396%
        blur 4.0  width 11 px   bright  -4.430%   dark  -2.644%

    It is zero for a sharp edge and grows with width, which is what identifies
    it as geometry rather than a defect: q reaches its plateau later on a wide
    edge, so max(q[+2..+7]) falls short of 1 and min(q[-7..-2]) sits above 0
    even though nothing overshoots.  A rim-free control therefore SHOULD read
    negative, and comparing it against zero would condemn a correct instrument
    on the dark axis while flattering it by about 3 points on the bright axis.

    Returns (bright, dark, table).
    """
    table = []
    for b in blurs:
        img = np.zeros((512, 512), np.float32)
        img[:, 256:] = 0.25
        img = ndimage.gaussian_filter(img, b).astype(np.float32)
        e = edges(img, np.zeros(img.shape, bool), [(0, 0)], 512)
        r = gated(e, 1e9, 0.0)
        w = edge_width(e, 1e9)
        if r is None or w is None:
            continue
        table.append((float(b), float(w), r["bright"], r["dark"]))
    if not table:
        return 0.0, 0.0, table
    i = int(np.argmin([abs(t[1] - width) for t in table]))
    return table[i][2], table[i][3], table


def choose_gate(g, clip, rois, T, nmin_edges=2000,
                candidates=FLAT_CANDIDATES):
    """Pick the flatness cut ON THE NEGATIVE CONTROL, against its OWN null.

    The control is the image SMOOTHED: a raster with no rim by construction.
    The chosen cut MINIMISES the control's departure from the structural null
    at the control's own measured edge width, among cuts leaving at least
    `nmin_edges` edges.

    THERE IS NO TOLERANCE TO PICK.  An earlier form of this function accepted
    any cut inside a tolerance, which invites choosing the tolerance that
    passes -- the same defect as choosing a threshold from the arm comparison.
    Minimising a stated objective has no such freedom, and what would have been
    a pass/fail becomes something more useful: the residual at the chosen cut
    is reported as the instrument's FLOOR, and no arm difference smaller than
    that floor is claimed.

    The arm comparison is never consulted.  Returns (cut, table, floor).
    """
    ctrl = ndimage.gaussian_filter(g, 3.0).astype(np.float32)
    e = edges(ctrl, clip, rois, T)
    del ctrl
    table, best, best_cost = [], None, None
    for c in candidates:
        r = gated(e, c)
        if r is None:
            table.append((float(c), None, None, 0, None, None, None))
            continue
        w = edge_width(e, c)
        nb, nd, _ = structural_null(w if w else 9.0)
        rb, rd = r["bright"] - nb, r["dark"] - nd
        table.append((float(c), r["bright"], r["dark"], r["n"],
                      float(w) if w else None, float(rb), float(rd)))
        if r["n"] >= nmin_edges and (best_cost is None or abs(rb) < best_cost):
            best, best_cost = float(c), abs(rb)
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
    print("SELF-TEST 1 -- a synthetic step with a KNOWN planted overshoot.")
    print("  Checks the ARITHMETIC.  The synthetic step is clean, so")
    print("  admissibility is not exercised here.")
    for planted in (0.00, 0.05, 0.20):
        img = np.zeros((512, 512), np.float32)
        img[:, 256:] = 0.5
        img = ndimage.gaussian_filter(img, 1.5)
        if planted:
            img = img + planted * (img - ndimage.gaussian_filter(img, 3.0))
        e = edges(img.astype(np.float32), np.zeros(img.shape, bool),
                  [(0, 0)], 512)
        r = gated(e, 1e9)
        print(f"  planted {planted*100:5.1f}%  ->  measured "
              f"{r['bright']*100:+7.3f}%   n={r['n']}")

    print("\nSELF-TEST 2 -- the floor, with and without noise.")
    print("  A rim-free synthetic step.  Any reading here is the instrument.")
    for s in (0.0, 0.002, 0.005, 0.010):
        r = floor(s)
        print(f"  noise sigma {s:.3f}  bright {r['bright']*100:+7.3f}%   "
              f"dark {r['dark']*100:+7.3f}%   n={r['n']}")
    print("\n  The noise rows are the fooling direction stated in v3's own")
    print("  docstring, isolated: noise ALONE, on an image with no rim.")
