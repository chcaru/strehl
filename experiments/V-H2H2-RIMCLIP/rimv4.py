"""RIM INSTRUMENT v4 -- per-edge, with an ADMISSIBILITY GATE on the edge step.

WHY THERE IS A v4.  v3 (V-HEADTOHEAD/rimcmp.py) is a good instrument on the
subject it was commissioned against and it is INADMISSIBLE on this one.
Measured, on `113MSDCF` strehl, by this file's own `diagnose`:

    strehl as-is                          bright rim  +38.47%
    the same image SMOOTHED (no rim
      by construction)                    bright rim  +14.85%

A rim-free image cannot carry a +14.85% rim.  That is v1's failure -- "+428% on
a clean image ... it was measuring its own denominator" -- reappearing in v3 on
a different subject.  The mechanism is visible when the rim is conditioned on
the edge step, in units of the image's own high-pass sigma:

    step 5.1 sigma   bright rim +112.07%
    step 7.5 sigma   bright rim  +49.10%
    step 10.6 sigma  bright rim  +39.79%
    step 14.5 sigma  bright rim  +24.15%
    step 20.2 sigma  bright rim   -1.68%

v3 normalises each excursion by that edge's own step and takes a MAX over six
samples.  On `coffee-bean` -- a bright subject with real silhouette steps --
the steps are large and the max is dominated by the rim.  `113MSDCF` is a dark
LINEAR render (median tile mean 0.032, hp sigma 0.0055), its 99th-percentile
gradients are mostly low-contrast texture, and there the max over six noisy
samples divided by a small step is mostly noise over a small denominator.

WHAT v4 CHANGES, AND THE ONE THING IT MUST NOT DO.  v4 is v3's profile
construction and v3's arithmetic, unchanged, plus a minimum-step gate.  The
gate threshold is chosen ON THE NEGATIVE CONTROL -- the lowest step at which a
rim-free image scores approximately zero -- and NOT by looking at the arm
comparison.  Choosing it from the arm comparison would be a selection effect
with no error bar, which is the same defect this lane audited `vh2_sweep.py`
for.  The threshold is fixed once, on strehl, and then applied identically to
every arm.

THE GATE IS ON ABSOLUTE STEP, NOT STEP-IN-SIGMA.  A sigma-relative gate would
admit a different amount of scene contrast from each arm, because the arms
differ in noise by up to 3.9x; the noisier arm would be gated harder and would
have its noisy excursions removed for free.  An absolute gate admits the same
scene contrast from every arm and leaves the noise bias where it can be
measured -- by the noise ladder -- instead of hiding it inside the gate.

INVOCATION.  Imported by rim.py.  `python rimv4.py` runs the self-test.
"""
import numpy as np
from scipy import ndimage

R = 12
TT = np.arange(-R, R + 1)
IB = np.where((TT >= 2) & (TT <= 7))[0]
ID = np.where((TT >= -7) & (TT <= -2))[0]


def edges(g, clip, rois, T, nmax_per_roi=300, seed=11):
    """v3's edge walk, returning PER-EDGE values instead of medians.

    Every acceptance test below is v3's, in v3's order, with v3's constants:
    the 99th-percentile gradient selection, the positive-step test, the
    plateau-flatness test at 0.20*step, and the centred-transition test at
    0.35.  The only addition is that `step` is returned alongside the
    excursions so admissibility can be conditioned on it.
    """
    rng = np.random.default_rng(seed)
    ov, un, st, prof = [], [], [], []
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
            prof.append(q)
    if not ov:
        return None
    return (np.array(ov), np.array(un), np.array(st), np.array(prof))


def gated(e, min_step):
    """Median bright/dark rim over edges whose step clears `min_step`."""
    if e is None:
        return None
    ov, un, st, prof = e
    m = st >= min_step
    if m.sum() < 30:
        return None
    return dict(n=int(m.sum()),
                bright=float(np.median(ov[m])),
                dark=float(np.median(un[m])),
                bright_p90=float(np.percentile(ov[m], 90)),
                dark_p90=float(np.percentile(un[m], 90)),
                step_median=float(np.median(st[m])))


def boot_ci(e, min_step, nboot=2000, seed=17):
    """Bootstrap CI over EDGES for the gated bright and dark rim."""
    if e is None:
        return None
    ov, un, st, _ = e
    m = st >= min_step
    if m.sum() < 30:
        return None
    o, u = ov[m], un[m]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(o), size=(nboot, len(o)))
    bo = np.median(o[idx], axis=1)
    bu = np.median(u[idx], axis=1)
    return (float(np.percentile(bo, 2.5)), float(np.percentile(bo, 97.5)),
            float(np.percentile(bu, 2.5)), float(np.percentile(bu, 97.5)))


def choose_gate(g, clip, rois, T, sigma, candidates=None, tol=0.02):
    """Pick the minimum-step gate ON THE NEGATIVE CONTROL.

    The control is the image SMOOTHED -- a raster with no rim by construction.
    The gate is the smallest candidate at which that control's bright rim falls
    within `tol` of zero.  The arm comparison is never consulted.

    Returns (min_step, table) where table is every candidate and the control's
    reading at it, so the choice is auditable rather than asserted.
    """
    if candidates is None:
        candidates = [c * sigma for c in (0, 5, 10, 15, 20, 25, 30, 40)]
    ctrl = ndimage.gaussian_filter(g, 3.0).astype(np.float32)
    e = edges(ctrl, clip, rois, T)
    table, chosen = [], None
    for c in candidates:
        r = gated(e, c)
        table.append((float(c), float(c / sigma) if sigma else float("nan"),
                      None if r is None else r["bright"],
                      None if r is None else r["n"]))
        if chosen is None and r is not None and abs(r["bright"]) <= tol:
            chosen = float(c)
    del ctrl
    return chosen, table


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(__doc__)
    print("SELF-TEST: a synthetic step edge with a KNOWN planted overshoot.")
    rng = np.random.default_rng(0)
    for planted in (0.00, 0.05, 0.20):
        img = np.zeros((512, 512), np.float32)
        img[:, 256:] = 0.5
        img = ndimage.gaussian_filter(img, 1.5)
        if planted:
            img = img + planted * (img - ndimage.gaussian_filter(img, 3.0))
        img = img.astype(np.float32)
        e = edges(img, np.zeros(img.shape, bool), [(0, 0)], 512)
        r = gated(e, 0.0)
        got = float("nan") if r is None else r["bright"] * 100
        print(f"  planted overshoot {planted*100:5.1f}%  ->  measured "
              f"{got:+7.3f}%   n={0 if r is None else r['n']}")
    print("\n  A monotone edge scores 0 by construction; only an over/undershoot")
    print("  scores.  The gate is irrelevant here because the synthetic step is")
    print("  clean -- this test checks the ARITHMETIC, not the admissibility.")
