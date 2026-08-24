"""M114 R3 -- re-derive M107's fringe numbers, then test whether the decile
instrument can go red.

PART A  reproduce W1/W3/W4 from my own renders (independent binary, same bytes).
PART B  absolute magnitudes: decile 1 in sRGB units and in 16-bit DN.
PART C  THE NULL M107 NEVER RAN.  Deciles are taken of |R-Y| in the OFF arm --
        i.e. the pixels are SELECTED on the outcome variable.  Regression to
        the mean then guarantees decile 1 rises and decile 10 falls under ANY
        perturbation, correcting or not.  Three controls:
          C-sym   define the deciles on the ON arm instead and measure the
                  change to OFF.  A real correction is not symmetric; pure
                  regression to the mean is.
          C-wrong a render-domain placebo: scale the RED channel of the OFF arm
                  radially by the WRONG SIGN, +704.5e-6.  This is the arm M107
                  itself measured as 7.2% worse in the CFA domain.
          C-noise a render-domain placebo: add zero-mean noise to RED with the
                  same rms as the real |on-off| difference.  Cannot correct
                  anything by construction.
        BAR:  the top-decile fall must be MATERIALLY LARGER for the real
              correction than for C-wrong and C-noise.  If the placebos also
              fall ~50%, the decile profile is an artefact of the binning and
              carries no evidence about correction.
PART D  a stratification that is NOT selected on the outcome: bin by the
        luminance-gradient decile of the OFF arm, and by radius.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
OUTJ = r"C:\dev\strehl-out\M114-ca-verify\r3.json"

EPS = -704.5e-6
CHROMA_T = 0.06
EDGE_Q = 0.99
NEAR = 3
rng = np.random.default_rng(20260824)
res = {}


def load(p):
    a = tifffile.imread(p)
    return a.astype(np.float32) / np.float32(65535.0)


def ydev(r, g, b):
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return y


def radial_scale_red(r_chan, eps):
    """Pull-resample the red channel by s = 1+eps about the image centre."""
    h, w = r_chan.shape
    cx, cy = w * 0.5, h * 0.5
    s = 1.0 + eps
    out = np.empty_like(r_chan)
    step = 256
    xs = (np.arange(w, dtype=np.float64) - cx) * s + cx
    for y0 in range(0, h, step):
        y1 = min(y0 + step, h)
        ys = (np.arange(y0, y1, dtype=np.float64) - cy) * s + cy
        yy, xx = np.meshgrid(ys, xs, indexing="ij")
        out[y0:y1] = ndimage.map_coordinates(
            r_chan, [yy, xx], order=3, mode="nearest").astype(np.float32)
    return out


print("loading", OFF, flush=True)
a0 = load(OFF)
r0, g0, b0 = a0[..., 0], a0[..., 1], a0[..., 2]
y0 = ydev(r0, g0, b0)
print("loading", ON, flush=True)
a1 = load(ON)
r1, g1, b1 = a1[..., 0], a1[..., 1], a1[..., 2]
y1 = ydev(r1, g1, b1)
H, W = y0.shape
print("shape", a0.shape, flush=True)

gy, gx = np.gradient(y0)
gm = np.hypot(gx, gy)
gq = np.quantile(gm, EDGE_Q)
edge = gm >= gq
near = ndimage.distance_transform_edt(~edge) <= NEAR
dist = None
print("near-edge px = %d (%.2f%% of frame)" % (near.sum(), 100 * near.mean()), flush=True)

# ---------------- PART A -----------------------------------------------
d0 = (r0 - y0)[near].astype(np.float64)
d1 = (r1 - y1)[near].astype(np.float64)
e0 = (b0 - y0)[near].astype(np.float64)
e1 = (b1 - y1)[near].astype(np.float64)
A0, A1 = np.abs(d0), np.abs(d1)

c0 = np.maximum(np.abs(r0 - y0), np.abs(b0 - y0))
c1 = np.maximum(np.abs(r1 - y1), np.abs(b1 - y1))
area0 = int((near & (c0 > CHROMA_T)).sum())
area1 = int((near & (c1 > CHROMA_T)).sum())
print("\n=== PART A -- M107's W1/W3/W4 re-derived ===")
print("W1 fringe area      off=%d  on=%d   %+.2f%%" %
      (area0, area1, 100 * (area1 - area0) / area0))
print("W3 mean |R-Y| near  off=%.6f on=%.6f  %+.2f%%" %
      (A0.mean(), A1.mean(), 100 * (A1.mean() - A0.mean()) / A0.mean()))
print("W4 mean |B-Y| near  off=%.6f on=%.6f  %+.2f%%" %
      (np.abs(e0).mean(), np.abs(e1).mean(),
       100 * (np.abs(e1).mean() - np.abs(e0).mean()) / np.abs(e0).mean()))
flip = np.sign(d0) != np.sign(d1)
fell = A1 < A0
keep = float(((fell) & (~flip)).sum() / max(fell.sum(), 1))
print("W3 bar: of pixels whose |R-Y| fell, %.1f%% kept sign (bar was >90%%)" % (100 * keep))
res["A"] = dict(area_off=area0, area_on=area1,
                w3_off=float(A0.mean()), w3_on=float(A1.mean()),
                w4_off=float(np.abs(e0).mean()), w4_on=float(np.abs(e1).mean()),
                keep_sign=keep, flip_rate=float(flip.mean()))

# ---------------- PART B -----------------------------------------------
qs = np.quantile(A0, np.linspace(0, 1, 11))


def decile_table(base, other, label, quants=None):
    q = quants if quants is not None else np.quantile(base, np.linspace(0, 1, 11))
    rows = []
    for i in range(10):
        m = (base >= q[i]) & (base < q[i + 1]) if i < 9 else (base >= q[i])
        if m.sum() == 0:
            continue
        mo, mn = base[m].mean(), other[m].mean()
        rows.append(dict(decile=i + 1, lo=float(q[i]), hi=float(q[i + 1]),
                         n=int(m.sum()), mean_base=float(mo), mean_other=float(mn),
                         pct=float(100 * (mn - mo) / max(mo, 1e-12)),
                         dn_base=float(mo * 65535), dn_other=float(mn * 65535),
                         dn_delta=float((mn - mo) * 65535)))
    print("\n  %s" % label)
    print("   dec  range(sRGB)          n        base      other     change     "
          "base_DN  other_DN   dDN")
    for r in rows:
        print("   %3d  %.5f-%.5f %9d  %.6f  %.6f  %+8.2f%%  %8.1f %8.1f %+7.1f"
              % (r["decile"], r["lo"], r["hi"], r["n"], r["mean_base"],
                 r["mean_other"], r["pct"], r["dn_base"], r["dn_other"],
                 r["dn_delta"]))
    return rows


print("\n=== PART B -- decile profile with ABSOLUTE magnitudes ===")
print("  (base = |R-Y| OFF, other = |R-Y| ON; DN are 16-bit sRGB output units)")
rows_real = decile_table(A0, A1, "REAL correction, deciles of OFF", qs)
res["B_real"] = rows_real

# ---------------- PART C -----------------------------------------------
print("\n=== PART C -- can the decile instrument go red? ===")
qs_on = np.quantile(A1, np.linspace(0, 1, 11))
rows_sym = decile_table(A1, A0, "C-sym: deciles of ON, change to OFF", qs_on)
res["C_sym"] = rows_sym

print("\n  building render-domain placebos ...", flush=True)
rp_wrong = radial_scale_red(r0, -EPS)          # WRONG SIGN
yw = ydev(rp_wrong, g0, b0)
Aw = np.abs((rp_wrong - yw)[near]).astype(np.float64)
del rp_wrong, yw
rms = float(np.sqrt(np.mean(((r1 - r0)[near]).astype(np.float64) ** 2)))
print("  rms |R_on - R_off| on near-edge px = %.6f sRGB (%.1f DN)" % (rms, rms * 65535))
rp_noise = r0 + rng.normal(0.0, rms, size=r0.shape).astype(np.float32)
yn = ydev(rp_noise, g0, b0)
An = np.abs((rp_noise - yn)[near]).astype(np.float64)
del rp_noise, yn

rows_wrong = decile_table(A0, Aw, "C-wrong: RED scaled by +704.5e-6 (wrong sign)", qs)
rows_noise = decile_table(A0, An, "C-noise: RED + white noise of matched rms", qs)
res["C_wrong"] = rows_wrong
res["C_noise"] = rows_noise

print("\n  TOP-DECILE COMPARISON (the number M107 headlines)")
print("    real correction   : %+.2f%%" % rows_real[-1]["pct"])
print("    C-sym  (on->off)  : %+.2f%%" % rows_sym[-1]["pct"])
print("    C-wrong (bad sign): %+.2f%%" % rows_wrong[-1]["pct"])
print("    C-noise (garbage) : %+.2f%%" % rows_noise[-1]["pct"])
print("    DECILE 1")
print("    real correction   : %+.2f%%" % rows_real[0]["pct"])
print("    C-wrong           : %+.2f%%" % rows_wrong[0]["pct"])
print("    C-noise           : %+.2f%%" % rows_noise[0]["pct"])

# ---------------- PART D -----------------------------------------------
print("\n=== PART D -- stratifiers NOT selected on the outcome ===")
gnear = gm[near].astype(np.float64)
gq10 = np.quantile(gnear, np.linspace(0, 1, 11))
print("\n  by |grad Y|_off decile (fixed population, arm-independent bins)")
print("   dec   n         mean|R-Y|off  mean|R-Y|on   change      off_DN  on_DN")
strat_g = []
for i in range(10):
    m = (gnear >= gq10[i]) & (gnear < gq10[i + 1]) if i < 9 else (gnear >= gq10[i])
    if m.sum() == 0:
        continue
    mo, mn = A0[m].mean(), A1[m].mean()
    strat_g.append(dict(decile=i + 1, n=int(m.sum()), off=float(mo), on=float(mn),
                        pct=float(100 * (mn - mo) / mo)))
    print("   %3d  %9d   %.6f     %.6f    %+7.2f%%   %7.1f %7.1f"
          % (i + 1, m.sum(), mo, mn, 100 * (mn - mo) / mo, mo * 65535, mn * 65535))
res["D_grad"] = strat_g

yy, xx = np.mgrid[0:H, 0:W]
cx, cy = W * 0.5, H * 0.5
rad = np.hypot(xx - cx, yy - cy).astype(np.float32) / float(np.hypot(cx, cy))
del yy, xx
rnear = rad[near].astype(np.float64)
print("\n  by normalised radius (support_r_max = 0.788 marked)")
print("   r-bin            n        mean|R-Y|off  mean|R-Y|on   change   area_off area_on")
edges = [0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.788, 0.85, 0.9, 0.95, 1.05]
cnear0 = c0[near].astype(np.float64)
cnear1 = c1[near].astype(np.float64)
strat_r = []
for i in range(len(edges) - 1):
    m = (rnear >= edges[i]) & (rnear < edges[i + 1])
    if m.sum() == 0:
        continue
    mo, mn = A0[m].mean(), A1[m].mean()
    ao = int((cnear0[m] > CHROMA_T).sum())
    an = int((cnear1[m] > CHROMA_T).sum())
    tag = "  <= support" if edges[i + 1] <= 0.788 else "  PAST SUPPORT"
    strat_r.append(dict(lo=edges[i], hi=edges[i + 1], n=int(m.sum()),
                        off=float(mo), on=float(mn),
                        pct=float(100 * (mn - mo) / mo), area_off=ao, area_on=an))
    print("   %.3f-%.3f %10d   %.6f     %.6f   %+7.2f%%  %8d %8d%s"
          % (edges[i], edges[i + 1], m.sum(), mo, mn, 100 * (mn - mo) / mo,
             ao, an, tag))
res["D_radius"] = strat_r

with open(OUTJ, "w") as fh:
    json.dump(res, fh, indent=2)
print("\nwrote", OUTJ)
