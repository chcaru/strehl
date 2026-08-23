"""M55 E10 -- PR23 (is S a stable statistic?) and PR22 verification.

PRE-REGISTERED as PR23 before this file ran.  PR22's verification is a
derivation check, not a new test.

NOTE: e8_canonical_plant.py has no __main__ guard, so importing it re-runs it.
This file therefore re-implements canon() locally rather than importing, so E10
runs standalone.  (That import side effect is why out/e9_split.log contains
E8's output as well -- recorded, not hidden.)
"""
import os, sys, glob, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
M46OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m46-detail-metric", "out")
M46SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m46-detail-metric", "src")
M41SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m41-r3-kill", "src")
for p in (M46SRC, M41SRC):
    if p not in sys.path:
        sys.path.insert(0, p)
import m46lib as M
import m41lib as L1

NBIN, PAD, G, RN_E = 64, 32, 1.14469, 1.47


def _rings(n, nbin=NBIN):
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    e = np.linspace(0, n // 2, nbin + 1)
    out = []
    for i in range(nbin):
        m = (rr >= e[i]) & (rr < e[i + 1])
        if int(m.sum()) < 8:
            continue
        out.append((m, int(m.sum()), 0.5 * (e[i] + e[i + 1]) / n))
    return out


def _spec(a):
    n = a.shape[0]
    w1 = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1))
    return np.fft.fftshift(np.fft.fft2((a - a.mean()) * np.outer(w1, w1)))


def _sel(n):
    rs = _rings(n)
    j = int(np.argmin([abs(c - M.F_SIG) for (_, _, c) in rs]))
    return rs[j][0], rs[j][1]


def canon(a, b):
    m, cnt = _sel(a.shape[0])
    A, B = _spec(a)[m], _spec(b)[m]
    return float(np.real(np.sum(A * np.conj(B))) / cnt)


res, t0 = {}, time.time()

# =========================================================== PR23
print("=" * 78)
print("M55 E10 (PR23) -- is the separation score S a stable statistic?")
print("=" * 78)
with open(os.path.join(M46OUT, "b1_results.json")) as fh:
    b1 = json.load(fh)
z = np.load(os.path.join(M46OUT, "b1_merges.npz"))
det = z["d112"][32:-32, 32:-32].astype(np.float32)
g, rn_e = b1["rois"]["g"], b1["rois"]["rn_e"]
sig_d = float(np.sqrt(M.noise_var_dn(float(np.median(det)), g, rn_e)))
ne_d, ne_f = b1["n_eff"]["112_detail"], b1["n_eff"]["112_flat"]
rho = b1["twocap"]["flat"]["at_fsig"] / (1 - b1["twocap"]["flat"]["at_fsig"]) / ne_f
sigma = sig_d / np.sqrt(ne_d)
fpn = M.make_fpn(det.shape, 46046, np.sqrt(rho) * sig_d)


def draw(seed, sb=0.0, k=1.0):
    rng = np.random.default_rng(seed)
    return [(M.blur(det, sb) + fpn +
             rng.standard_normal(det.shape).astype(np.float32) * (sigma / k)).astype(np.float32)
            for _ in range(2)]


SB = 0.04959   # from PR15, held fixed so only REPS varies
print(f"   matched blur held FIXED at sb = {SB} px (from PR15) so only REPS moves.")
print("   d_blur and d_smooth are means over REPS independent seed pairs.\n")
print("     REPS    d_blur      d_smooth    se(d_smooth)   d_smooth/se    S(canon)")
per = {"base": [], "blur": [], "smooth": []}
MAXR = 64
for r in range(MAXR):
    s = 1 + 1000 * r + 7
    per["base"].append(canon(*draw(s)))
    per["blur"].append(canon(*draw(s, sb=SB)))
    per["smooth"].append(canon(*draw(s, k=np.sqrt(2))))
pr23 = {}
for R in (1, 2, 4, 8, 16, 32, 64):
    bb = np.mean(per["base"][:R]); bl = np.mean(per["blur"][:R]); sm = np.mean(per["smooth"][:R])
    db, ds = (bb - bl) / abs(bb), (bb - sm) / abs(bb)
    dsi = (np.array(per["base"][:R]) - np.array(per["smooth"][:R])) / abs(bb)
    se = float(np.std(dsi, ddof=1) / np.sqrt(R)) if R > 1 else float("nan")
    S = abs(db) / (abs(db) + abs(ds))
    print(f"     {R:4d}  {db:+9.5f}   {ds:+9.5f}   {se:11.5f}   {ds/se if R>1 else float('nan'):11.2f}"
          f"    {S:8.3f}")
    pr23[R] = dict(d_blur=db, d_smooth=ds, se=se, S=S)
res["pr23"] = pr23
smin = min(v["S"] for v in pr23.values() if v["S"] == v["S"])
smax = max(v["S"] for v in pr23.values() if v["S"] == v["S"])
print(f"\n   S(canon) ranges {smin:.3f} .. {smax:.3f} across REPS with the SAME plant,")
print(f"   SAME seeds and SAME blur.  Author reports 0.995; my PR15 read 0.976.")
print(f"   d_smooth at REPS=8 is {pr23[8]['d_smooth']/pr23[8]['se']:.2f} standard errors from zero.")

# =========================================================== PR22
print("\n" + "=" * 78)
print("M55 E10 (PR22 verification) -- why the old form's swap asymmetry is 26 %")
print("=" * 78)
print("   DERIVED: old = FRC * mean|A|^2, and FRC is swap-symmetric, so")
print("   old(a,b)/old(b,a) = P_a/P_b exactly.  Confirming on the author's own")
print("   configuration: 112MSDCF frames 6..68, detail ROI, parity split.")
import rawpy
x, y, w, h = 1671, 1373, 512, 512
x0, y0, x1, y1 = x - PAD, y - PAD, x + w + PAD, y + h + PAD
files = sorted(glob.glob(r"D:\personal\macro\112MSDCF\*.ARW"))[6:68]
cube = np.empty((len(files), y1 - y0, x1 - x0), np.float32)
for i, f in enumerate(files):
    with rawpy.imread(f) as r:
        v = r.raw_image_visible
        g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
        g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
    cube[i] = 0.5 * (g1 + g2) - M.BLACK
fine, coarse, reg = L1.focus_fields(cube, G, RN_E)


def mg(idx):
    c, cf, rg = cube[idx], coarse[idx], reg[idx]
    wsel = np.argmax(rg, axis=0)
    pk = np.take_along_axis(cf, wsel[None], 0)[0]
    acc = cf >= (0.5 * pk)[None]
    acc[wsel, np.arange(c.shape[1])[:, None], np.arange(c.shape[2])[None]] = True
    nn = acc.sum(0).astype(np.float32)
    return ((c * acc).sum(0) / np.maximum(nn, 1.0))[PAD:-PAD, PAD:-PAD].astype(np.float32)


idx = np.arange(len(files))
a, b = mg(idx[0::2]), mg(idx[1::2])
m, cnt = _sel(a.shape[0])
A, B = _spec(a)[m], _spec(b)[m]
Pa, Pb = float(np.mean(np.abs(A) ** 2)), float(np.mean(np.abs(B) ** 2))
fr = float(np.real(np.sum(A * np.conj(B))) / np.sqrt(np.sum(np.abs(A) ** 2) * np.sum(np.abs(B) ** 2)))
oab, oba = M.frc_at(a, b) * Pa, M.frc_at(b, a) * Pb
print(f"     P_a {Pa:.6e}   P_b {Pb:.6e}   P_a/P_b {Pa/Pb:.6f}")
print(f"     FRC(a,b) {M.frc_at(a,b):.8f}   FRC(b,a) {M.frc_at(b,a):.8f}  (symmetric)")
print(f"     old(a,b) {oab:.6e}   old(b,a) {oba:.6e}")
print(f"     relative to the mean: {abs(oab-oba)/abs(0.5*(oab+oba)):.4e}")
print(f"     relative to old(a,b): {abs(oab-oba)/abs(oab):.4e}")
print(f"     A.0.2 reports 1.96e-02.  canonical swap difference: "
      f"{abs(canon(a,b)-canon(b,a))/abs(canon(a,b)):.4e}")
res["pr22"] = dict(Pa=Pa, Pb=Pb, ratio=Pa / Pb, old_ab=oab, old_ba=oba,
                   rel_mean=abs(oab - oba) / abs(0.5 * (oab + oba)))

# =========================================================== leverage summary
print("\n" + "=" * 78)
print("M55 E10 -- LEVERAGE: what moves canonical sigpow, and by how much")
print("=" * 78)
print("   All as |d| on the author's own stack and ROI, canonical form.")
print(f"     halving noise variance (k=sqrt2), on the PLANT        {abs(pr23[64]['d_smooth']):.5f}")
print(f"     a 0.05 px optical blur, on the PLANT                  {abs(pr23[64]['d_blur']):.5f}")
print( "     a 0.15 % photometric gain                             0.00300  (PR20)")
print( "     block-4 instead of parity split                       0.35870  (PR18, = 1-0.6413)")
print( "     contiguous instead of parity split                    0.99530  (PR18, = 1-0.0047)")
print( "     PM_M: destroy detail to MTF 0.007 + common structure   1.03306  (PR16, NEGATIVE d)")
lev = abs(0.359) / abs(pr23[64]["d_blur"])
lev2 = abs(0.359) / abs(pr23[64]["d_smooth"])
print(f"\n   Split choice has {lev:.0f}x the leverage of the blur signal the metric")
print(f"   exists to detect, and {lev2:.0f}x the leverage of the noise term it is")
print( "   supposed to be blind to.")
res["leverage"] = dict(split_vs_blur=lev, split_vs_noise=lev2)

with open(os.path.join(OUT, "e10_stability.json"), "w") as fh:
    json.dump(res, fh, indent=2, default=float)
print(f"\nwrote out/e10_stability.json  ({time.time()-t0:.1f}s)")
