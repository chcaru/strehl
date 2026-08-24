"""B10: is the residual fringe that survives the M109 fix spatially RADIAL?

Registered in PREREGISTRATION.md addendum B10 before this file was written.

Lateral chromatic aberration is zero at the optical centre and grows with field
height. If the residual's density rises toward the corners it is M107's object
and the two fixes compose; if it is flat, M107's fix will not clear it.

Read-only. Uses artefacts already on disk; renders nothing.

THE CONFOUND, handled rather than mentioned: raw area-normalised density is
confounded by where the SUBJECT is. Specular highlights occur on the marker, not
uniformly. If the marker sits centrally, raw density falls toward the corners
for lack of subject, and a real radial effect reads as flat. So the bar is the
density per ELIGIBLE pixel -- per partially-clipped pixel, ORCH's D8 population
-- which removes the subject's placement from the denominator. The area-
normalised profile is reported beside it as the confounded comparison.

Both controls are mandatory (discipline 706). A flat reading is uninterpretable
unless the instrument is shown able to read non-flat, so a planted radial
population must fire and a uniform one must not.
"""

import sys

import numpy as np

from magenta import load, magenta_mask

OUT = r"C:\dev\strehl-out\M109"
AFTER = rf"{OUT}\marker-argmax-e024-after.tif"
BEFORE = rf"{OUT}\marker-argmax-e024-before.tif"

NBINS = 20
MIN_DENOM = 5000

# Registered decision thresholds. Not editable after the fact.
NULL_RHO_MAX, NULL_RATIO_LO, NULL_RATIO_HI = 0.5, 0.7, 1.4
POS_RHO_MIN, POS_RATIO_MIN = 0.8, 2.0
RADIAL_RHO, RADIAL_RATIO = 0.7, 2.0
FLAT_RHO, FLAT_RATIO = 0.3, 1.5


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Rank correlation, written out so the script has no scipy dependency."""
    def rank(v):
        order = np.argsort(v, kind="mergesort")
        r = np.empty(len(v), float)
        r[order] = np.arange(len(v), dtype=float)
        # average ties
        _, inv, cnt = np.unique(v, return_inverse=True, return_counts=True)
        sums = np.zeros(len(cnt))
        np.add.at(sums, inv, r)
        return (sums / cnt)[inv]
    a, b = rank(x), rank(y)
    a -= a.mean()
    b -= b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def radial(numer: np.ndarray, denom: np.ndarray, r: np.ndarray):
    """Density of `numer` within `denom`, binned by normalised radius `r`."""
    edges = np.linspace(0.0, 1.0, NBINS + 1)
    idx = np.clip(np.digitize(r, edges) - 1, 0, NBINS - 1)
    nd = np.bincount(idx[denom], minlength=NBINS).astype(float)
    nn = np.bincount(idx[numer], minlength=NBINS).astype(float)
    keep = nd >= MIN_DENOM
    mid = 0.5 * (edges[:-1] + edges[1:])
    dens = np.divide(nn, nd, out=np.zeros(NBINS), where=nd > 0)
    return mid[keep], dens[keep], nd[keep], nn[keep]


def summarise(mid, dens):
    rho = spearman(mid, dens)
    inner = dens[mid < 0.25]
    outer = dens[mid > 0.75]
    ratio = float(outer.mean() / inner.mean()) if len(inner) and len(outer) and inner.mean() > 0 else float("nan")
    return rho, ratio


def report(name, mid, dens, nd, nn):
    rho, ratio = summarise(mid, dens)
    print(f"\n--- {name}")
    print(f"    annuli kept {len(mid)} of {NBINS}   fringe px {int(nn.sum())}   denom px {int(nd.sum())}")
    print("    r      density(ppm)   numer     denom")
    for m, d, a, b in zip(mid, dens, nn, nd):
        print(f"    {m:.3f}  {d * 1e6:12.1f}  {int(a):8d}  {int(b):9d}")
    print(f"    spearman rho = {rho:+.4f}   outer/inner = {ratio:.4f}")
    return rho, ratio


def main() -> None:
    a = load(AFTER)
    resid = magenta_mask(a)

    h, w = a.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    r /= np.hypot(cy, cx)  # centre-to-corner = 1.0

    at1 = a >= 1.0
    nsat = at1.sum(axis=2)
    eligible = (nsat >= 1) & (nsat <= 2)  # ORCH's D8 population

    print(f"frame {w}x{h}   residual fringe {int(resid.sum())} px "
          f"({100 * resid.mean():.4f} %)   eligible {int(eligible.sum())} px "
          f"({100 * eligible.mean():.4f} %)")
    print(f"fringe inside eligible: {int((resid & eligible).sum())} px "
          f"({100 * (resid & eligible).sum() / max(1, resid.sum()):.1f} % of fringe)")

    allpx = np.ones_like(resid)
    m1, d1, nd1, nn1 = radial(resid, allpx, r)
    report("AREA-NORMALISED (confounded by subject placement)", m1, d1, nd1, nn1)

    m2, d2, nd2, nn2 = radial(resid & eligible, eligible, r)
    rho, ratio = report("PER ELIGIBLE PIXEL  <-- THE BAR", m2, d2, nd2, nn2)

    # ---- controls, on the same denominator as the bar ----------------------
    rng = np.random.default_rng(20260824)
    ei = np.flatnonzero(eligible.ravel())
    k = int((resid & eligible).sum())

    pick = rng.choice(ei, size=k, replace=False)
    null = np.zeros(resid.size, bool)
    null[pick] = True
    mn, dn, ndn, nnn = radial(null.reshape(resid.shape), eligible, r)
    nrho, nratio = report("B10-null  uniform random eligible pixels", mn, dn, ndn, nnn)

    rr = r.ravel()[ei]
    p = rr / rr.sum()
    pick = rng.choice(ei, size=k, replace=False, p=p)
    pos = np.zeros(resid.size, bool)
    pos[pick] = True
    mp, dp, ndp, nnp = radial(pos.reshape(resid.shape), eligible, r)
    prho, pratio = report("B10-pos   planted population, P(pick) proportional to r", mp, dp, ndp, nnp)

    # ---- verdicts, against thresholds fixed before the run -----------------
    print("\n=== controls ===")
    null_ok = abs(nrho) < NULL_RHO_MAX and NULL_RATIO_LO <= nratio <= NULL_RATIO_HI
    pos_ok = prho > POS_RHO_MIN and pratio > POS_RATIO_MIN
    print(f"B10-null  |rho|={abs(nrho):.4f} < {NULL_RHO_MAX} and "
          f"ratio={nratio:.4f} in [{NULL_RATIO_LO},{NULL_RATIO_HI}]  -> {'PASS' if null_ok else 'FAIL'}")
    print(f"B10-pos   rho={prho:+.4f} > {POS_RHO_MIN} and "
          f"ratio={pratio:.4f} > {POS_RATIO_MIN}  -> {'PASS' if pos_ok else 'FAIL'}")

    print("\n=== verdict ===")
    if not (null_ok and pos_ok):
        print("INSTRUMENT NOT QUALIFIED -- a control failed. The real reading")
        print("above may NOT be quoted. This is the registered consequence.")
        sys.exit(4)

    if rho > RADIAL_RHO and ratio > RADIAL_RATIO:
        v = "RADIAL -- consistent with lateral CA; expect M107 to clear it"
    elif rho < FLAT_RHO or ratio < FLAT_RATIO:
        v = "NOT RADIAL -- M107's fix will not clear this residual"
    else:
        v = "EQUIVOCAL -- registered band; not resolved by re-analysis"
    print(f"rho={rho:+.4f}  outer/inner={ratio:.4f}  ->  {v}")
    print("Consistent-with, never identification: vignetting and corner softening")
    print("share the radial signature. Not coordinated with M107.")


if __name__ == "__main__":
    main()
