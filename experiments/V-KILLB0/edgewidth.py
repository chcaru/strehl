"""V-KILLB0 spatial acuity + halo, v2: erf-fitted slanted edge.

v1 FAILED ITS OWN NOISE CONTROL (planted sigma=200 DN moved the 10-90 width by
-0.103 px, i.e. the metric was partly a noise detector) and admitted only 5 of
60 sites.  Both faults came from reading crossings off a cumulative-max of the
raw binned ESF.  This version fits a model instead, which is the standard
slanted-edge construction:

    p(d) = lo + step * Phi((d - d0) / sigma)

by least squares over the whole profile.  Additive zero-mean noise perturbs the
fitted sigma symmetrically instead of biasing the crossing, and every bin
contributes, so the estimate is far more stable.  Width is reported as the
10-90 distance, 2*1.2816*sigma = 2.5631*sigma.

CLOSED-FORM BLUR PREDICTION.  Convolving with a Gaussian of width s takes
sigma -> sqrt(sigma^2 + s^2), so the planted-blur control has a number to hit
rather than merely a sign.

HALO is then the departure of the real profile from that monotone fit:
    overshoot  = max(p - model) over +0.5..+8 px, / step
    undershoot = max(model - p) over -8..-0.5 px, / step
A monotone edge of any width scores 0 on both, however soft it is, so this
separates "halo" from "blur" -- which a raw max-minus-plateau does not.

SITE ADMISSION is decided on the DEFAULT arm only and applied to both, so the
two arms are always scored on the same pixels.
"""
import sys

import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter
from scipy.optimize import least_squares
from scipy.special import erf

import bandprobe as bp

PATCH = 64
HALF = PATCH // 2
STEP = 0.25
SPAN = 20.0
MIN_STEP = 1000.0
MIN_R2 = 0.985


def find_edges(lum, k=250, minsep=90):
    g = gaussian_filter(lum, 1.5)
    mag = np.hypot(*np.gradient(g))
    m = gaussian_filter(mag, 3.0)
    b = HALF + 4
    m[:b, :] = 0; m[-b:, :] = 0; m[:, :b] = 0; m[:, -b:] = 0
    peaks = (m == maximum_filter(m, minsep)) & (m > 0)
    ys, xs = np.nonzero(peaks)
    o = np.argsort(m[ys, xs])[::-1][:k]
    return list(zip(ys[o].tolist(), xs[o].tolist()))


def profile(patch):
    gy, gx = np.gradient(gaussian_filter(patch, 1.0))
    vy, vx = gy.mean(), gx.mean()
    n = np.hypot(vy, vx)
    if n < 1e-9:
        return None
    vy, vx = vy / n, vx / n
    yy, xx = np.mgrid[0:PATCH, 0:PATCH]
    d = ((yy - HALF) * vy + (xx - HALF) * vx).ravel()
    v = patch.ravel()
    sel = np.abs(d) <= SPAN
    d, v = d[sel], v[sel]
    nb = int(2 * SPAN / STEP)
    idx = np.clip(((d + SPAN) / STEP).astype(int), 0, nb - 1)
    s = np.bincount(idx, weights=v, minlength=nb)
    c = np.bincount(idx, minlength=nb)
    ok = c >= 3
    if ok.sum() < 60:
        return None
    return (-SPAN + (np.arange(nb) + 0.5) * STEP)[ok], s[ok] / c[ok]


def model(p, d):
    lo, step, d0, sig = p
    return lo + step * 0.5 * (1.0 + erf((d - d0) / (sig * np.sqrt(2.0))))


def fit(patch):
    r = profile(patch)
    if r is None:
        return None
    d, p = r
    lo0 = float(np.percentile(p, 5)); hi0 = float(np.percentile(p, 95))
    if hi0 - lo0 < MIN_STEP:
        return None
    p0 = [lo0, hi0 - lo0, 0.0, 1.0]
    try:
        res = least_squares(lambda q: model(q, d) - p, p0,
                            bounds=([-1e5, 1.0, -6.0, 0.15], [1e6, 1e6, 6.0, 8.0]),
                            max_nfev=400)
    except Exception:
        return None
    lo, step, d0, sig = res.x
    m = model(res.x, d)
    ss = float(((p - m) ** 2).sum()); tt = float(((p - p.mean()) ** 2).sum())
    r2 = 1.0 - ss / tt if tt > 0 else 0.0
    nh = (d - d0 >= 0.5) & (d - d0 <= 8.0)
    nl = (d - d0 <= -0.5) & (d - d0 >= -8.0)
    if nh.sum() < 6 or nl.sum() < 6:
        return None
    return {"w": 2.5631 * float(sig), "sig": float(sig), "step": float(step),
            "r2": r2,
            "over": float((p - m)[nh].max() / step),
            "under": float((m - p)[nl].max() / step)}


def pair(lumA, lumB, sites, admit=None):
    out = []
    for (y, x) in sites:
        a = fit(lumA[y - HALF:y + HALF, x - HALF:x + HALF])
        if a is None or a["r2"] < MIN_R2 or a["step"] < MIN_STEP:
            continue
        if admit is not None and (y, x) not in admit:
            continue
        b = fit(lumB[y - HALF:y + HALF, x - HALF:x + HALF])
        if b is None:
            continue
        out.append((y, x, a, b))
    return out


def show(rows, label):
    if len(rows) < 5:
        return f"   {label}: only {len(rows)} admitted sites -- NOT REPORTABLE"
    wa = np.array([r[2]["w"] for r in rows]); wb = np.array([r[3]["w"] for r in rows])
    oa = np.array([r[2]["over"] for r in rows]); ob = np.array([r[3]["over"] for r in rows])
    ua = np.array([r[2]["under"] for r in rows]); ub = np.array([r[3]["under"] for r in rows])
    d = wb - wa; do = ob - oa; du = ub - ua
    j = int(np.argmax(do))
    return (f"   {label}  n={len(rows)}  median step {np.median([r[2]['step'] for r in rows]):.0f} DN\n"
            f"     10-90 width   A {wa.mean():.4f} px  B {wb.mean():.4f} px  "
            f"delta {d.mean():+.4f} px ({100*(wb.mean()/wa.mean()-1):+.2f}%)  "
            f"median {np.median(d):+.4f}  wider at {(d>0).sum()}/{len(d)}\n"
            f"     overshoot     A {oa.mean():+.4f}  B {ob.mean():+.4f}  "
            f"delta {do.mean():+.4f}  p90 {np.percentile(do,90):+.4f}  "
            f"worst {do[j]:+.4f} @y={rows[j][0]} x={rows[j][1]}  worse {(do>0).sum()}/{len(do)}\n"
            f"     undershoot    A {ua.mean():+.4f}  B {ub.mean():+.4f}  "
            f"delta {du.mean():+.4f}  p90 {np.percentile(du,90):+.4f}  "
            f"worse {(du>0).sum()}/{len(du)}")


def main():
    A, B, label = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")
    la = bp.channels(bp.load(A))["L"]
    lb = bp.channels(bp.load(B))["L"]
    assert la.shape == lb.shape
    sites = find_edges(la)
    print(f"== EDGE/HALO {label}   {len(sites)} candidate edges", flush=True)

    r0 = pair(la, la, sites)
    admit = {(y, x) for (y, x, _, _) in r0}
    dn = np.array([x[3]["w"] - x[2]["w"] for x in r0]) if r0 else np.array([9.0])
    dh = np.array([x[3]["over"] - x[2]["over"] for x in r0]) if r0 else np.array([9.0])
    c0 = len(r0) >= 5 and np.abs(dn).max() == 0.0 and np.abs(dh).max() == 0.0
    print(f"  [C0 NULL ] {len(r0)} admitted sites, A vs A: max|dw|={np.abs(dn).max():.2e} "
          f"max|dover|={np.abs(dh).max():.2e}  {'PASS' if c0 else 'FAIL'}")

    for s in (0.4, 0.8):
        rb = pair(la, gaussian_filter(la, s), sites, admit)
        sa = np.array([x[2]["sig"] for x in rb]); sb = np.array([x[3]["sig"] for x in rb])
        pred = np.sqrt(sa ** 2 + s ** 2)
        rel = float(np.mean(sb / pred)) if len(rb) else 0.0
        ok = 0.9 < rel < 1.1
        print(f"  [C1 BLUR ] planted sigma={s}: fitted sigma {sa.mean():.4f} -> "
              f"{sb.mean():.4f}, closed form predicts {pred.mean():.4f}, "
              f"meas/pred {rel:.4f}  {'PASS' if ok else 'FAIL'}")
        if s == 0.4:
            c1 = ok

    rng = np.random.default_rng(5)
    rn = pair(la, la + rng.normal(0, 200.0, la.shape), sites, admit)
    dz = np.array([x[3]["w"] - x[2]["w"] for x in rn]) if rn else np.array([9.0])
    c2 = abs(dz.mean()) < 0.05
    print(f"  [C2 NOISE] planted sigma=200 DN: mean d width {dz.mean():+.5f} px "
          f"(want |.| < 0.05)  {'PASS' if c2 else 'FAIL'}")
    if not (c0 and c1 and c2):
        print("  INSTRUMENT NOT COMMISSIONED -- results below are void")

    print(show(pair(la, lb, sites, admit), "A=default  B=arm"), flush=True)


if __name__ == "__main__":
    main()
