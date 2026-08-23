"""M55 E7 -- two cheap controls that decide how to read E6.

PR12 (pre-registered before this file ran).  MECHANISM: FRC is a normalised
     correlation and is invariant to a gain applied to both images; ring power
     is quadratic in that gain.  OBSERVABLE: multiply BOTH real half-stack
     merges by g in {0.90 .. 1.10} and read sigpow, FRC, hp_sd.  Reported with
     no expected direction.  Falsifier of the DERIVED claim sigpow ~ g^2:
     if the measured exponent d(log sigpow)/d(log g) is not 2.000 +- 0.01.

PR13  Decompose the E6b gate sweep into its two factors, FRC(gate) and
     P_ring(gate), to say which one carries the monotonicity.
"""
import os, sys, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
M46SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m46-detail-metric", "src")
M41SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m41-r3-kill", "src")
for p in (M46SRC, M41SRC):
    if p not in sys.path:
        sys.path.insert(0, p)
import m46lib as M
import m41lib as L1

N, NBIN = 512, 64
STACK = r"D:\personal\macro\112MSDCF"
ROIS = {"detail": (1671, 1373, 512, 512), "flat": (2747, 32, 512, 512)}
PAD, NFR, G, RN_E = 32, 72, 1.14469, 1.47
W = np.outer(np.hanning(N), np.hanning(N))
_yy, _xx = np.mgrid[0:N, 0:N]
_rr = np.sqrt((_yy - N // 2) ** 2 + (_xx - N // 2) ** 2)
_e = np.linspace(0, N // 2, NBIN + 1)
_c = 0.5 * (_e[:-1] + _e[1:]) / N
I = int(np.argmin(np.abs(_c - M.F_SIG)))
MASK = (_rr >= _e[I]) & (_rr < _e[I + 1])


def ring_power(a):
    A = np.abs(np.fft.fftshift(np.fft.fft2((a - a.mean()) * W))) ** 2
    return float(A[MASK].mean())


def load_cube(files, roi, pad):
    import rawpy
    x, y, w, h = roi
    x0, y0, x1, y1 = x - pad, y - pad, x + w + pad, y + h + pad
    out = np.empty((len(files), y1 - y0, x1 - x0), np.float32)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
            g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
        out[i] = 0.5 * (g1 + g2) - M.BLACK
    return out


res = {}
files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))[:NFR]
print("=" * 78)
print("M55 E7 (PR12) -- is sigpow invariant to photometric scale?")
print("=" * 78)
cube = load_cube(files, ROIS["detail"], PAD)
halves = [cube[0::2], cube[1::2]]
ms = []
for h in halves:
    fine, coarse, reg = L1.focus_fields(h, G, RN_E)
    m, _, _ = L1.arm_A(h, coarse, reg)
    ms.append(m[PAD:-PAD, PAD:-PAD].astype(np.float32))
del cube, halves
print("   real disjoint half-stack merges of 112MSDCF, 36 frames each, gate 0.5")
print("       gain g     FRC(f_sig)      P_ring       sigpow    sigpow/sigpow(1)")
gs = [0.90, 0.95, 0.98, 1.00, 1.02, 1.05, 1.10]
rows = {}
for g in gs:
    a, b = ms[0] * g, ms[1] * g
    fr, pr = M.frc_at(a, b), ring_power(a)
    rows[g] = dict(frc=fr, p_ring=pr, sigpow=fr * pr)
for g in gs:
    print(f"     {g:8.3f}   {rows[g]['frc']:10.6f}  {rows[g]['p_ring']:11.5g}"
          f"  {rows[g]['sigpow']:11.5g}   {rows[g]['sigpow']/rows[1.00]['sigpow']:12.5f}")
lg = np.log(np.array(gs))
ls = np.log(np.array([rows[g]["sigpow"] for g in gs]))
slope = float(np.polyfit(lg, ls, 1)[0])
frc_spread = max(rows[g]["frc"] for g in gs) - min(rows[g]["frc"] for g in gs)
print(f"\n   d(log sigpow)/d(log gain) = {slope:.6f}   (DERIVED prediction 2)")
print(f"   FRC total spread over the gain sweep = {frc_spread:.3e}  (predicted 0)")
print(f"   PR12 falsifier |slope-2| > 0.01 -> {'FAILS' if abs(slope-2)>0.01 else 'holds'}")
res["pr12"] = dict(rows=rows, slope=slope, frc_spread=frc_spread)

print("\n" + "=" * 78)
print("M55 E7 (PR13) -- which factor carries the E6b gate monotonicity?")
print("=" * 78)
with open(os.path.join(OUT, "e6_gate.json")) as fh:
    e6 = json.load(fh)
for rname, rows6 in e6["pr11"].items():
    print(f"\n   ROI {rname}")
    print("      gate     n_eff    FRC(f_sig)    P_ring/P(0.5)   sigpow/sig(0.5)")
    ref = rows6["0.5"]
    for gk in sorted(rows6, key=float):
        r = rows6[gk]
        frc = r["sigpow"] / r["p_ring"]
        print(f"      {float(gk):5.2f}  {np.mean(r['neff']):7.3f}   {frc:9.4f}"
              f"     {r['p_ring']/ref['p_ring']:12.4f}    {r['sigpow']/ref['sigpow']:12.4f}")
    res.setdefault("pr13", {})[rname] = {gk: rows6[gk]["sigpow"] / rows6[gk]["p_ring"]
                                         for gk in rows6}
with open(os.path.join(OUT, "e7_gain.json"), "w") as fh:
    json.dump(res, fh, indent=2, default=float)
print("\nwrote out/e7_gain.json")
