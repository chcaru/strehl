"""RE-CHECK under ORCH correction #4: per-band split-half signal fraction AND
per-band arm effect, at FLAT and EDGE sites separately, on ONE subject.

Why this answers the correction: V-LINEAR qualifies a band by comparing an
in-focus frame to a defocused one over CONFIRMED tiles -- i.e. tiles where the
lens demonstrably moved, which are STRUCTURED tiles. That says what a band
carries where there is structure. It does not say what the same band carries in
a flat region of the same subject. Split-half covariance measures both
populations directly on the merged master, so it needs no band label at all.

No fixed band is assumed anywhere here. Every band is reported.
All comparisons are WITHIN one subject (ORCH correction #4 item 2).
"""
import argparse, os
import numpy as np
import slopetest as st
import nscale as ns

OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def decomp(idx, be, bo, nx):
    X = np.array([t.ravel() for t in st.tiles(idx, be, nx)], dtype=np.float64)
    Y = np.array([t.ravel() for t in st.tiles(idx, bo, nx)], dtype=np.float64)
    X = X - X.mean(1, keepdims=True)
    Y = Y - Y.mean(1, keepdims=True)
    cov = (X * Y).mean(1)
    var = 0.5 * ((X * X).mean(1) + (Y * Y).mean(1))
    return cov, var - cov


ap = argparse.ArgumentParser()
ap.add_argument("--subject", required=True)
ap.add_argument("--arm", required=True)
a = ap.parse_args()

ae, cme, cfe = ns.load64(os.path.join(OUT, "%s__EVEN__A-unset.tiff" % a.subject))
ao, cmo, cfo = ns.load64(os.path.join(OUT, "%s__ODD__A-unset.tiff" % a.subject))
be_, _, cf3 = ns.load64(os.path.join(OUT, "%s__EVEN__%s.tiff" % (a.subject, a.arm)))
bo_, _, cf4 = ns.load64(os.path.join(OUT, "%s__ODD__%s.tiff" % (a.subject, a.arm)))

fl, ed, nx = st.sites(ae)          # sites frozen on the DEFAULT arm only
print("%s  arm %s   clip: A %.4f%% / %.4f%%   B %.4f%% / %.4f%%"
      % (a.subject, a.arm, 100*cfe, 100*cfo, 100*cf3, 100*cf4))
print("bands = committed contrast_ms.py SIGMAS %s" % st.SIGMAS)
print("sigfrac = Cov(EVEN,ODD)/Var on the DEFAULT arm: what that band actually carries HERE.")
print()
edges = [1.0 / (2.0 * np.pi * s) for s in st.SIGMAS]
hdr = ("%5s %14s | %9s %9s %9s | %9s %9s %9s"
       % ("band", "cyc/px", "FLAT sf", "SIGNAL x", "NOISE x", "EDGE sf", "SIGNAL x", "NOISE x"))
print(hdr); print("-" * len(hdr))
oa, ob = st.octaves(ae), st.octaves(ao)
na, nb = st.octaves(be_), st.octaves(bo_)
for j in range(len(st.SIGMAS)):
    hi = 0.5 if j == 0 else edges[j - 1]
    lo = edges[j]
    row = "%5d %14s |" % (j, "%.3f-%.3f" % (lo, hi))
    for idx in (fl, ed):
        s0, n0 = decomp(idx, oa[j], ob[j], nx)
        s1, n1 = decomp(idx, na[j], nb[j], nx)
        sf = np.median(s0 / np.maximum(s0 + n0, 1e-30))
        row += (" %9.3f %9.4f %9.4f |"
                % (sf, np.median(s1) / np.median(s0), np.median(n1) / np.maximum(np.median(n0), 1e-30)))
    print(row.rstrip("|"))
