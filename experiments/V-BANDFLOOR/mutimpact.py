"""Does either MISSED mutation change a number I reported to ORCH?

A harness that cannot detect a mutation is a defect in the harness. It is only
a defect in the RESULT if the mutation also moves the result. Tested, not assumed.

Reported numbers under test:
  bee1     band-0 FLAT signal fraction   reported 0.001
  bee1     band-0 EDGE SIGNAL ratio      reported 1.0015
  112MSDCF band-0 EDGE SIGNAL ratio      reported 0.8211  (the kill)
"""
import os
import numpy as np
import slopetest as st
import nscale as ns

OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def decomp(idx, be, bo, nx, mode):
    X = np.array([t.ravel() for t in st.tiles(idx, be, nx)], dtype=np.float64)
    Y = np.array([t.ravel() for t in st.tiles(idx, bo, nx)], dtype=np.float64)
    if mode != "NODEMEAN":
        X = X - X.mean(1, keepdims=True)
        Y = Y - Y.mean(1, keepdims=True)
    cov = (X * Y).mean(1)
    var = 0.5 * ((X * X).mean(1) + (Y * Y).mean(1))
    if mode == "ABSCOV":
        cov = np.abs(cov)
    return cov, var - cov


for subj, arm in (("bee1", "F4"), ("112MSDCF", "F4")):
    ae, _, _ = ns.load64(os.path.join(OUT, "%s__EVEN__A-unset.tiff" % subj))
    ao, _, _ = ns.load64(os.path.join(OUT, "%s__ODD__A-unset.tiff" % subj))
    be_, _, _ = ns.load64(os.path.join(OUT, "%s__EVEN__%s.tiff" % (subj, arm)))
    bo_, _, _ = ns.load64(os.path.join(OUT, "%s__ODD__%s.tiff" % (subj, arm)))
    fl, ed, nx = st.sites(ae)
    oa, ob = st.octaves(ae)[0], st.octaves(ao)[0]
    na, nb = st.octaves(be_)[0], st.octaves(bo_)[0]
    print("\n%s  band 0, arm %s" % (subj, arm))
    print("  %-10s %14s %14s %14s" % ("mutation", "FLAT sf", "EDGE SIGNAL x", "FLAT SIGNAL x"))
    for mode in ("NULL", "NODEMEAN", "ABSCOV"):
        s0f, n0f = decomp(fl, oa, ob, nx, mode)
        s1f, _ = decomp(fl, na, nb, nx, mode)
        s0e, n0e = decomp(ed, oa, ob, nx, mode)
        s1e, _ = decomp(ed, na, nb, nx, mode)
        sf = np.median(s0f / np.maximum(s0f + n0f, 1e-30))
        print("  %-10s %14.4f %14.4f %14.4f"
              % (mode, sf, np.median(s1e) / np.median(s0e),
                 np.median(s1f) / np.median(s0f)))
    neg = (decomp(fl, oa, ob, nx, "NULL")[0] < 0).sum()
    print("  (flat tiles with NEGATIVE cov, which |cov| would inflate: %d of %d)"
          % (neg, len(fl)))
