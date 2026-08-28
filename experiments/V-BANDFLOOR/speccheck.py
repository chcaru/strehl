"""Commission the SIGNAL/NOISE channel carrying my headline -- SPECIFICITY and
DELETION, which my earlier mutate.py did not cover.

MY HEADLINE: on leaf-2-cpl, lowering the band-0 floor gives SIGNAL x1.2262 and
NOISE x5.3978 -- "recovers 23% more reproducible content at 4.4 units of noise
per unit of signal". If the SIGNAL channel can be inflated by INDEPENDENT noise,
that entire conclusion is void.

Uses bandarm.py's exact decomp() source (extracted by AST, not reimplemented)
and slopetest's sites()/octaves(), with bandarm's own median-over-tiles ratio.

ARMS (applied to the real EVEN/ODD leaf-2 masters):
  NULL         untouched                        -> ratios exactly 1.0000
  INDEP-NOISE  DIFFERENT noise in each half     -> SIGNAL must NOT rise (SPECIFICITY)
  COMMON-SIG   SAME structure added to both     -> SIGNAL must RISE     (sensitivity)
  DELETION     correlated content attenuated    -> SIGNAL must FALL     (deletion)
"""
import ast as _ast, os
import numpy as np, tifffile
import slopetest as st

_src = open("bandarm.py", encoding="utf-8").read()
_fn = [n for n in _ast.parse(_src).body
       if isinstance(n, _ast.FunctionDef) and n.name == "decomp"][0]
_ns = {"np": np, "st": st}
exec(_ast.get_source_segment(_src, _fn), _ns)      # exact shipped function body
decomp = _ns["decomp"]

N = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"
def lum(p):
    a = np.asarray(tifffile.imread(p), np.float64)
    return 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2] if a.ndim == 3 else a

E = lum(os.path.join(N, "leaf-2-cpl__EVEN__A-unset.tiff"))
O = lum(os.path.join(N, "leaf-2-cpl__ODD__A-unset.tiff"))
fl, ed, nx = st.sites(E)
print("leaf-2-cpl EVEN/ODD %s   flat sites %d  edge sites %d" % (E.shape, len(fl), len(ed)))
rng = np.random.default_rng(11)
amp = 0.01 * np.median(E)
struct = np.asarray(st.octaves(E)[0], np.float64) * 0.15     # real correlated structure

oa0, ob0 = st.octaves(E), st.octaves(O)
base = {}
for j in range(4):
    for nm, idx in (("FLAT", fl), ("EDGE", ed)):
        base[(j, nm)] = decomp(idx, oa0[j], ob0[j], nx)

def arm(tag, Ex, Ox):
    oa, ob = st.octaves(Ex), st.octaves(Ox)
    sr, nr = [], []
    for j in range(4):
        s0, n0 = base[(j, "EDGE")]
        s1, n1 = decomp(ed, oa[j], ob[j], nx)
        sr.append(np.median(s1) / np.median(s0))
        nr.append(np.median(n1) / max(np.median(n0), 1e-30))
    print("  %-24s SIGNAL x %s   NOISE x %s"
          % (tag, " ".join("%7.4f" % v for v in sr), " ".join("%7.4f" % v for v in nr)))
    return np.array(sr), np.array(nr)

print("\nEDGE sites, bands 0-3, ratio vs untouched pair")
s_nul, n_nul = arm("NULL untouched",      E.copy(), O.copy())
s_noi, n_noi = arm("INDEP-NOISE (SPEC)",  E + rng.normal(0, amp*3, E.shape),
                                          O + rng.normal(0, amp*3, O.shape))
s_com, n_com = arm("COMMON-SIG (sens)",   E + struct, O + struct)
s_del, n_del = arm("DELETION",            E - 0.30*struct, O - 0.30*struct)

print("\n--- commissioning verdict, band 0 ---")
chk = [("NULL exactly 1.0000",              abs(s_nul[0] - 1.0) < 1e-9),
       ("INDEP-NOISE does NOT raise SIGNAL", s_noi[0] < 1.05),
       ("INDEP-NOISE DOES raise NOISE",      n_noi[0] > 1.20),
       ("COMMON-SIG raises SIGNAL",          s_com[0] > 1.05),
       ("DELETION lowers SIGNAL",            s_del[0] < 0.95)]
for k, v in chk: print("   %-36s %s" % (k, "PASS" if v else "*** FAIL ***"))
print("   COMMISSIONED %d/5" % sum(v for _, v in chk))
