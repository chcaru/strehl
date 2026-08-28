"""Is my "+22.6% signal recovered" real, or is it noise leaking into the signal channel?

speccheck.py measured a NONZERO leak: independent noise at NOISE x1.6814 still
produced SIGNAL x1.0454. My L4 headline was SIGNAL x1.2262 at NOISE x5.3978. A
first-order extrapolation (0.045 leak per 0.68 noise) predicts ~0.29 of leak at
+4.40 of noise -- which would swallow the entire +0.226 I reported.

Extrapolating is not measuring. This calibrates directly: inject PURE
INDEPENDENT noise, sweep amplitude until the NOISE channel reads ~5.40 like the
real arm, and read what the SIGNAL channel does. Pure independent noise contains
zero recoverable signal BY CONSTRUCTION, so whatever SIGNAL x it produces is
pure leak and is the floor my +22.6% must clear.
"""
import ast as _ast, os
import numpy as np, tifffile
import slopetest as st
_src = open("bandarm.py", encoding="utf-8").read()
_fn = [n for n in _ast.parse(_src).body if isinstance(n, _ast.FunctionDef) and n.name == "decomp"][0]
_ns = {"np": np, "st": st}; exec(_ast.get_source_segment(_src, _fn), _ns); decomp = _ns["decomp"]
N = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"
def lum(p):
    a = np.asarray(tifffile.imread(p), np.float64)
    return 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2] if a.ndim == 3 else a
E = lum(os.path.join(N, "leaf-2-cpl__EVEN__A-unset.tiff"))
O = lum(os.path.join(N, "leaf-2-cpl__ODD__A-unset.tiff"))
fl, ed, nx = st.sites(E)
oa0, ob0 = st.octaves(E), st.octaves(O)
b0 = {nm: decomp(idx, oa0[0], ob0[0], nx) for nm, idx in (("FLAT", fl), ("EDGE", ed))}
amp = 0.01 * np.median(E)
print("PURE-NOISE leak calibration, band 0 (noise contains NO signal by construction)")
print("  %-10s %10s %10s | %10s %10s" % ("amp", "EDGE sig x", "EDGE noi x", "FLAT sig x", "FLAT noi x"))
for k in (3.0, 5.0, 7.63, 10.0, 14.0):
    rng = np.random.default_rng(101)
    Ex = E + rng.normal(0, amp*k, E.shape); Ox = O + rng.normal(0, amp*k, O.shape)
    oa, ob = st.octaves(Ex), st.octaves(Ox)
    r = []
    for nm, idx in (("EDGE", ed), ("FLAT", fl)):
        s0, n0 = b0[nm]; s1, n1 = decomp(idx, oa[0], ob[0], nx)
        r += [np.median(s1)/np.median(s0), np.median(n1)/max(np.median(n0),1e-30)]
    print("  amp*%-6.2f %10.4f %10.4f | %10.4f %10.4f" % (k, r[0], r[1], r[2], r[3]))
print()
print("REAL ARM L4 for comparison:  EDGE sig x1.0448 noi x1.1875 | FLAT sig x1.2262 noi x5.3978")
