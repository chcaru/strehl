"""BUILD-RESAMP -- what IS the ESF fit residual made of?

The per-render commissioning found the fork's ESF fit residual is 2.54x ours
(0.3793 vs 0.1495 of contrast).  That is not a resolution comparison and this
file does not make one.  It asks what the residual is MADE of, separately
inside each image, because a render whose edges are 2.5x less well described by
an edge model is saying something about its own pipeline.

The decomposition.  A slanted-edge ROI is assumed to be a 1-D function of
distance along the edge normal.  If the physical edge at row y is displaced by
delta_y from the fitted straight line, a sample at normal distance d reads

    E(d + delta_y)  ~=  E(d) + delta_y . E'(d)

so, over a bin at distance d, with independent per-pixel noise sigma_n,

    residual^2(d)  =  sigma_n^2  +  var(delta) . E'(d)^2

which is a STRAIGHT LINE in E'(d)^2.  Its intercept is the image's own noise
floor and its slope is the variance of edge-position jitter, in px^2.  Both
come from inside one image.  The intercept is also an independent estimate of
something measurable another way -- the per-pixel scatter in the flat ESF
shoulders -- so the fit carries its own consistency check.

WHY THIS IS COMMISSIONED ACROSS BLUR WIDTH.  The estimator leans on E'(d), and
E' is sharpness.  Every instrument that touched the sharpness variable tonight
failed a comparison of sharpness: a band-power ratio ranked nearest-neighbour
first, a plateau shape test went blind past 4.33 px, and a slanted-edge MTF50
inflated 1.45x at 18 px.  A soft edge has small E' everywhere, which costs the
regression its leverage.  So the plant here is swept over the SAME 1.9-18 px
range, and if jitter recovery degrades with edge width then this estimator is
bounded by the same variable and must be abandoned like the others.

Nulls first.  A plant is large by construction and survives a broken
instrument; a null that is not exactly zero is what catches a defect big enough
to swallow the plant.

Usage:  python residual_anatomy.py                       (commission only)
        python residual_anatomy.py <a.tif> <b.tif> ...   (commission, then measure)
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slanted_edge as se  # noqa: E402
from commission_per_render import load_linear  # noqa: E402

ERF = np.vectorize(math.erf)
SLOPE = math.tan(math.radians(5.0))
CONTRAST = 20000.0
PEDESTAL = 5000.0


def synth(sigma, noise=0.0, jitter=0.0, h=se.LENGTH, w=se.WIDTH, seed=11):
    """Slanted Gaussian step with a KNOWN per-row displacement and noise."""
    rng = np.random.default_rng(seed)
    y = np.arange(h, dtype=np.float64)[:, None]
    x = np.arange(w, dtype=np.float64)[None, :]
    icept = w / 2.0 - SLOPE * (h - 1) / 2.0
    d = (x - (SLOPE * y + icept)) / math.sqrt(1.0 + SLOPE * SLOPE)
    if jitter > 0.0:
        # displace each ROW of the edge by a known amount, normal to the edge
        d = d - rng.normal(0.0, jitter, (h, 1))
    img = PEDESTAL + CONTRAST * 0.5 * (1.0 + ERF(d / (sigma * math.sqrt(2.0))))
    if noise > 0.0:
        img = img + rng.normal(0.0, noise, img.shape)
    return img


def anatomy(roi, line=None):
    """Split one ROI's ESF residual into a noise floor and an edge jitter.

    Returns DN for the noise floor and px for the jitter, both absolute, plus
    the shoulder-noise cross-check and the fit quality of the decomposition.
    """
    r = se.measure_roi(roi, line=line)
    if r is None:
        return None
    slope, icept = r["slope"], r["icept"]
    h, w = roi.shape
    yy = np.arange(h, dtype=np.float64)[:, None]
    xx = np.arange(w, dtype=np.float64)[None, :]
    dist = (xx - (slope * yy + icept)) / math.sqrt(1.0 + slope * slope)
    keep = (dist >= -se.HALF) & (dist < se.HALF)
    nb = 2 * se.HALF * se.OVERSAMPLE
    idx = np.clip(((dist[keep] + se.HALF) * se.OVERSAMPLE).astype(int), 0, nb - 1)
    raw = np.ascontiguousarray(roi.astype(np.float64))[keep]

    cnt = np.bincount(idx, minlength=nb)
    tot = np.bincount(idx, weights=raw, minlength=nb)
    model = tot / np.maximum(cnt, 1)
    resid = raw - model[idx]
    # per-bin mean square residual, de-biased for fitting the bin's own mean
    ss = np.bincount(idx, weights=resid**2, minlength=nb)
    good = cnt >= 8
    if good.sum() < 16:
        return None
    ms = np.zeros(nb)
    ms[good] = ss[good] / (cnt[good] - 1)

    # E'(d) in DN per px, from the binned ESF.
    #
    # NOT smoothed.  Differentiating a noisy model does put noise into the
    # regressor, and the plant caught the consequence -- 300 DN of planted
    # noise leaked 0.356 px into a jitter term that should have been zero.
    # But a 1 px boxcar is not the fix: it was tried, and because ms(d) is
    # proportional to the RAW E'(d)^2, smoothing only the regressor destroys
    # the correspondence.  R2 fell from 0.99988 to 0.00010, jitter pinned to
    # exactly zero at every blur level, and the whole residual moved into the
    # noise term.  Both states are recorded in the README; this is the one
    # with an interpretable null.
    dE = np.gradient(model) * se.OVERSAMPLE

    X = (dE[good]) ** 2
    Y = ms[good]
    if X.max() <= 0:
        return None
    A = np.vstack([np.ones_like(X), X]).T
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    c0, c1 = float(coef[0]), float(coef[1])
    pred = A @ coef
    ssr = float(np.sum((Y - pred) ** 2))
    sst = float(np.sum((Y - Y.mean()) ** 2))
    r2 = 1.0 - ssr / sst if sst > 0 else np.nan

    # The NULL exposed a floor: with no noise and no jitter planted, this
    # returned 0.0729 px at EVERY blur level.  Binning to 1/OVERSAMPLE px
    # spreads each bin's samples over that width, so the ESF's own slope
    # inside a bin contributes a variance of (1/OVERSAMPLE)^2 / 12 -- i.e.
    # sqrt(1/12)/OVERSAMPLE = 0.072169 px, which is what came back.  It is a
    # known additive term and it comes off in quadrature.
    quant = 1.0 / (se.OVERSAMPLE * math.sqrt(12.0))
    jitter = math.sqrt(max(c1 - quant * quant, 0.0))

    # independent noise estimate: per-pixel scatter in the flat shoulders only
    n = se.OVERSAMPLE * 6
    sh = np.concatenate([np.arange(0, n), np.arange(nb - n, nb)])
    shg = sh[cnt[sh] >= 8]
    sh_noise = math.sqrt(float(np.mean(ms[shg]))) if len(shg) else np.nan

    return {
        "noise_dn": math.sqrt(max(c0, 0.0)),
        "jitter_px": jitter,
        "shoulder_noise_dn": sh_noise,
        "r2": r2,
        "contrast": r["contrast"],
        "esf_resid": r["esf_resid"],
    }


def med(rows, k):
    v = np.array([r[k] for r in rows if r is not None and np.isfinite(r[k])])
    return float(np.median(v)) if len(v) else np.nan


# --------------------------------------------------------------------------
# commissioning
# --------------------------------------------------------------------------

def commission():
    print("commissioning residual_anatomy.py")
    print(f"  synthetic slant 5 deg, contrast {CONTRAST:.6g} DN, "
          f"pedestal {PEDESTAL:.6g} DN, linear")

    print("\n  NULL   no noise, no jitter -- both terms must be ~0")
    for sigma in (1.0, 3.0, 6.0):
        a = anatomy(synth(sigma))
        print(f"    blur sigma {sigma:>4.2f}  w10-90 {2.563103*sigma:>7.4g} px"
              f"   noise {a['noise_dn']:>11.6g} DN"
              f"   jitter {a['jitter_px']:>11.6g} px   R2 {a['r2']:>8.5f}")

    print("\n  NULL   the same ROI twice must be bit-identical")
    a = anatomy(synth(2.0, noise=300.0, jitter=0.4))
    b = anatomy(synth(2.0, noise=300.0, jitter=0.4))
    dn = abs(a["noise_dn"] - b["noise_dn"])
    dj = abs(a["jitter_px"] - b["jitter_px"])
    print(f"    max |d noise| = {dn:.6e} DN   max |d jitter| = {dj:.6e} px   "
          f"{'PASS' if dn == 0.0 and dj == 0.0 else 'FAIL'}")

    print("\n  PLANT  known noise, no jitter")
    for nz in (100.0, 300.0, 900.0):
        a = anatomy(synth(2.0, noise=nz))
        if a is None:
            print(f"    planted {nz:>6.1f} DN   REJECTED by measure_roi")
            continue
        print(f"    planted {nz:>6.1f} DN   recovered {a['noise_dn']:>9.6g} DN"
              f"   ({a['noise_dn']/nz:>7.5g}x)   shoulder "
              f"{a['shoulder_noise_dn']:>9.6g} DN"
              f"   jitter leak {a['jitter_px']:>9.6g} px")

    print("\n  PLANT  known jitter, no noise")
    for jt in (0.10, 0.30, 1.00):
        a = anatomy(synth(2.0, jitter=jt))
        if a is None:
            print(f"    planted {jt:>6.3f} px   REJECTED by measure_roi")
            continue
        print(f"    planted {jt:>6.3f} px   recovered {a['jitter_px']:>9.6g} px"
              f"   ({a['jitter_px']/jt:>7.5g}x)"
              f"   noise leak {a['noise_dn']:>9.6g} DN")

    print("\n  SWEEP  the same planted jitter 0.300 px across edge width --")
    print("         does this estimator survive the variable that killed the")
    print("         other three?")
    print(f"    {'sigma':>7}{'w10-90 px':>12}{'jitter px':>12}{'x true':>10}"
          f"{'noise leak':>13}{'R2':>10}")
    worst = 0.0
    for sigma in (0.74, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.02):
        a = anatomy(synth(sigma, jitter=0.30))
        if a is None:
            print(f"    {sigma:>7.4g}{2.563103*sigma:>12.6g}{'REJECTED':>12}")
            worst = 9.99
            continue
        rr = a["jitter_px"] / 0.30
        worst = max(worst, abs(rr - 1.0))
        print(f"    {sigma:>7.4g}{2.563103*sigma:>12.6g}"
              f"{a['jitter_px']:>12.6g}{rr:>10.5g}"
              f"{a['noise_dn']:>13.6g}{a['r2']:>10.5f}")
    print(f"    worst |recovered/true - 1| = {worst:.5g}   "
          f"{'PASS -- not bounded by sharpness' if worst < 0.15 else 'FAIL -- bounded by sharpness, abandon it'}")
    return worst


# --------------------------------------------------------------------------

def measure(path):
    g, _ = load_linear(path)
    sites = se.dedup(se.find_edges(g))[:300]
    rows = [anatomy(se.cut(g, s), line=s["line"]) for s in sites]
    ok = [r for r in rows if r is not None]
    print(f"\n=== {os.path.basename(path)} ===")
    print(f"  raster {g.shape[1]} x {g.shape[0]}, {len(ok)} / {len(sites)} sites")
    c = med(ok, "contrast")
    nz = med(ok, "noise_dn")
    sh = med(ok, "shoulder_noise_dn")
    jt = med(ok, "jitter_px")
    print(f"  edge contrast          {c:>12.6g} DN (normalised scale)")
    print(f"  noise floor, from fit  {nz:>12.6g} DN  = {100*nz/c:>7.4g}% of contrast")
    print(f"  noise floor, shoulders {sh:>12.6g} DN  = {100*sh/c:>7.4g}%   "
          f"(independent cross-check, ratio {nz/sh:.5g})")
    print(f"  edge position jitter   {jt:>12.6g} px")
    print(f"  decomposition R2       {med(ok,'r2'):>12.5f}")
    print(f"  total ESF residual     {med(ok,'esf_resid'):>12.6g} of contrast")
    # what each term contributes to the total residual, INSIDE this image
    tot = med(ok, "esf_resid") * c
    print(f"  -> of the {tot:.6g} DN total residual, noise explains "
          f"{100*min(nz/tot,1.0):.4g}%")


def main():
    worst = commission()
    if worst >= 0.15:
        print("\n  COMMISSIONING FAILED -- not measuring anything with this.")
        return
    for p in sys.argv[1:]:
        measure(p)


if __name__ == "__main__":
    main()
