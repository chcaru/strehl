"""B12: is the NON-clipping-coupled part of the residual radial?

Registered in PREREGISTRATION.md addendum B12 before this file was written.

B10 disqualified itself: its eligibility denominator had no radial lever arm.
B11 showed why -- the partial-clip population is confined to a narrow annulus,
zero pixels in 11 of 20 bins -- and split the residual in two:

  72.5 %  clipping-coupled, confined to r 0.52-0.88
  27.5 %  NOT clipping-coupled, in annuli with ZERO eligible pixels, spread
          across r 0.02-0.93

Only the second can be lateral CA, and only the second spans field height. B12
asks the radial question about it against a denominator that also spans the
frame: luminance EDGE pixels. Chromatic aberration acts on high-contrast edges,
and edges exist at every field height.

Read-only. Renders nothing.
"""

import sys

import cv2
import numpy as np

from magenta import load, magenta_mask

OUT = r"C:\dev\strehl-out\M109"
AFTER = rf"{OUT}\marker-argmax-e024-after.tif"

NBINS = 20
MIN_DENOM = 5000
SUPPORT_MIN = 5000
INNER_MAX_R, OUTER_MIN_R = 0.50, 0.85

EDGE_PCT = 99.0     # gradient percentile defining an edge
LUMA_MIN = 0.15     # an edge in near-black has no colour to fringe

NULL_RHO_MAX, NULL_RATIO_LO, NULL_RATIO_HI = 0.5, 0.7, 1.4
POS_RHO_MIN, POS_RATIO_MIN = 0.8, 2.0
RADIAL_RHO, RADIAL_RATIO = 0.7, 2.0
FLAT_RHO, FLAT_RATIO = 0.3, 1.5


def spearman(x, y):
    def rank(v):
        order = np.argsort(v, kind="mergesort")
        rk = np.empty(len(v), float)
        rk[order] = np.arange(len(v), dtype=float)
        _, inv, cnt = np.unique(v, return_inverse=True, return_counts=True)
        sums = np.zeros(len(cnt))
        np.add.at(sums, inv, rk)
        return (sums / cnt)[inv]
    a, b = rank(np.asarray(x, float)), rank(np.asarray(y, float))
    a -= a.mean()
    b -= b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def profile(numer, denom, idx):
    nd = np.bincount(idx[denom], minlength=NBINS).astype(float)
    nn = np.bincount(idx[numer], minlength=NBINS).astype(float)
    return nd, nn


def summarise(mid, nd, nn):
    keep = nd >= MIN_DENOM
    if keep.sum() < 4:
        return None
    m, d = mid[keep], nn[keep] / nd[keep]
    inner, outer = d[m < 0.25], d[m > 0.75]
    if not len(inner) or not len(outer) or inner.mean() <= 0:
        return None
    return spearman(m, d), float(outer.mean() / inner.mean()), m, d


def show(name, mid, nd, nn):
    print(f"\n--- {name}")
    keep = nd >= MIN_DENOM
    print(f"    annuli kept {int(keep.sum())} of {NBINS}   numer {int(nn.sum())}   denom {int(nd.sum())}")
    print("    r      density(ppm)     numer      denom")
    for i in np.flatnonzero(keep):
        print(f"    {mid[i]:.3f}  {nn[i] / nd[i] * 1e6:12.1f}  {int(nn[i]):9d}  {int(nd[i]):9d}")
    s = summarise(mid, nd, nn)
    if s is None:
        print("    NOT SUMMARISABLE (fewer than 4 annuli, or no inner/outer support)")
        return None
    print(f"    spearman rho = {s[0]:+.4f}   outer/inner = {s[1]:.4f}")
    return s


def main() -> None:
    a = load(AFTER)
    resid = magenta_mask(a)
    h, w = a.shape[:2]

    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / np.hypot(cy, cx)
    edges = np.linspace(0.0, 1.0, NBINS + 1)
    mid = 0.5 * (edges[:-1] + edges[1:])
    idx = np.clip(np.digitize(r, edges) - 1, 0, NBINS - 1)

    nsat = (a >= 1.0).sum(axis=2)
    eligible = (nsat >= 1) & (nsat <= 2)
    numer = resid & ~eligible          # the non-clipping-coupled subset

    luma = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float32)
    gx = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    gm = cv2.magnitude(gx, gy)
    thr = float(np.percentile(gm, EDGE_PCT))
    denom = (gm >= thr) & (luma > LUMA_MIN)

    print(f"frame {w}x{h}")
    print(f"residual {int(resid.sum())}   clipping-coupled {int((resid & eligible).sum())}"
          f"   NON-coupled (numerator) {int(numer.sum())}")
    print(f"edge threshold p{EDGE_PCT} = {thr:.5f}   edge px {int(denom.sum())} "
          f"({100 * denom.mean():.3f} %)   numerator on edges {int((numer & denom).sum())}")

    nd, nn = profile(numer & denom, denom, idx)

    # Print the denominator profile BEFORE the support gate, so an
    # UNDECIDABLE verdict comes with the evidence for it rather than an
    # assertion. The decision rule below is untouched by this.
    print("\n--- denominator support (edge px per annulus)")
    print("    r        edge px    numer px")
    for i in range(NBINS):
        print(f"    {mid[i]:.3f} {int(nd[i]):10d} {int(nn[i]):11d}")

    inner_ok = bool(((mid < INNER_MAX_R) & (nd >= SUPPORT_MIN)).any())
    outer_ok = bool(((mid > OUTER_MIN_R) & (nd >= SUPPORT_MIN)).any())
    print(f"support below r={INNER_MAX_R}: {inner_ok}   above r={OUTER_MIN_R}: {outer_ok}")
    if not (inner_ok and outer_ok):
        print("\n=== verdict ===\nUNDECIDABLE-BY-SUPPORT (edge denominator does not span field height)")
        sys.exit(4)

    real = show("NON-CLIPPING-COUPLED RESIDUAL per edge pixel  <-- THE BAR", mid, nd, nn)

    rng = np.random.default_rng(20260824)
    di = np.flatnonzero(denom.ravel())
    k = int((numer & denom).sum())

    pick = rng.choice(di, size=k, replace=False)
    nullm = np.zeros(resid.size, bool)
    nullm[pick] = True
    ndn, nnn = profile(nullm.reshape(resid.shape), denom, idx)
    nul = show("B12-null  uniform random edge pixels", mid, ndn, nnn)

    rr = r.ravel()[di]
    pick = rng.choice(di, size=k, replace=False, p=rr / rr.sum())
    posm = np.zeros(resid.size, bool)
    posm[pick] = True
    ndp, nnp = profile(posm.reshape(resid.shape), denom, idx)
    pos = show("B12-pos   planted, P(pick) proportional to r", mid, ndp, nnp)

    print("\n=== controls ===")
    if real is None or nul is None or pos is None:
        print("INSTRUMENT NOT QUALIFIED -- a profile was not summarisable.")
        sys.exit(4)
    null_ok = abs(nul[0]) < NULL_RHO_MAX and NULL_RATIO_LO <= nul[1] <= NULL_RATIO_HI
    pos_ok = pos[0] > POS_RHO_MIN and pos[1] > POS_RATIO_MIN
    print(f"B12-null  |rho|={abs(nul[0]):.4f} < {NULL_RHO_MAX}, ratio={nul[1]:.4f} "
          f"in [{NULL_RATIO_LO},{NULL_RATIO_HI}]  -> {'PASS' if null_ok else 'FAIL'}")
    print(f"B12-pos   rho={pos[0]:+.4f} > {POS_RHO_MIN}, ratio={pos[1]:.4f} > {POS_RATIO_MIN}"
          f"  -> {'PASS' if pos_ok else 'FAIL'}")
    if not (null_ok and pos_ok):
        print("\nINSTRUMENT NOT QUALIFIED -- the real reading may NOT be quoted.")
        sys.exit(4)

    rho, ratio = real[0], real[1]
    print("\n=== verdict ===")
    if rho > RADIAL_RHO and ratio > RADIAL_RATIO:
        v = "RADIAL -- consistent with lateral CA; expect M107 to clear it"
    elif rho < FLAT_RHO or ratio < FLAT_RATIO:
        v = "NOT RADIAL -- M107's fix should not be expected to clear this residual"
    else:
        v = "EQUIVOCAL -- registered band; not resolved by re-analysis"
    print(f"rho={rho:+.4f}  outer/inner={ratio:.4f}  ->  {v}")
    print("Consistent-with, never identification. Says nothing about whether")
    print("M107's own defect is real. Not coordinated with M107.")


if __name__ == "__main__":
    main()
