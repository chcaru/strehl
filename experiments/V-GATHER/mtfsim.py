"""BUILD-SHARP 5.1's 1.50x, tested three ways on one controlled instrument.

(1) Port restore.rs::gather_mtf EXACTLY and check 0.9402 / 0.6251.
(2) Simulate the two gather orders on a signal with GROUND TRUTH, and read out
    BOTH the passband amplitude (what gather_mtf models) AND the rms fidelity
    (what build-resamp-mtf.rs's own docs say the amplitude statistic is blind to).
(3) Read band correlation off the SAME data, to see whether it maps onto MTF.

The two gather orders, in the units align_cmd.rs actually uses:
  OLD  warp_frame_in_place_plane   : source lattice pitch 2 (CFA quad plane)
  NEW  warp_frame_in_place_fullres : source lattice pitch 1 (demosaiced), and
                                     sample_checked(src, 2.0*sxp, 2.0*syp)
Both write one value per CFA site. A feature at f cycles per FULL-RES pixel is
therefore at 2f cyc/sample for OLD and 1f cyc/sample for NEW.
"""
from __future__ import annotations
import math
import numpy as np

PHASE_SAMPLES = 64

def tap_cr(t):
    a = abs(t)
    if a < 1.0:  return 1.5*a**3 - 2.5*a**2 + 1.0
    if a < 2.0:  return -0.5*a**3 + 2.5*a**2 - 4.0*a + 2.0
    return 0.0

def tap_nearest(t):
    return 1.0 if abs(t) < 0.5 else 0.0

def tap_lanczos3(t):
    a = abs(t)
    if a >= 3.0: return 0.0
    if a < 1e-12: return 1.0
    pt = math.pi * t
    return (math.sin(pt)/pt) * (math.sin(pt/3.0)/(pt/3.0))

KERN = {"nearest": (tap_nearest, 1), "catmull-rom": (tap_cr, 2), "lanczos3": (tap_lanczos3, 3)}

def gather_mtf(name, f):
    """EXACT port of crates/strehl-core/src/restore.rs:172-196."""
    tap, sup = KERN[name]
    acc = 0.0
    for p in range(PHASE_SAMPLES):
        phi = (p + 0.5) / PHASE_SAMPLES
        w = [(n - phi, tap(n - phi)) for n in range(-sup + 1, sup + 1)]
        s = sum(v for _, v in w)
        if abs(s) < 1e-12: continue
        re = sum(v/s * math.cos(2*math.pi*f*d) for d, v in w)
        im = sum(v/s * math.sin(2*math.pi*f*d) for d, v in w)
        acc += math.hypot(re, im)
    return acc / PHASE_SAMPLES

print("=== (1) gather_mtf, independent Python port vs restore.rs:952 unit test ===")
print(f"{'f (cyc/sample)':>15} {'CR port':>10} {'asserted':>10} {'|diff|':>10}")
for f, want in ((0.25, 0.9402), (0.35, 0.8211), (0.40, 0.7425), (0.50, 0.6251)):
    got = gather_mtf("catmull-rom", f)
    print(f"{f:15.2f} {got:10.6f} {want:10.4f} {abs(got-want):10.2e}")
print(f"\n  5.1's ratio from the model: {gather_mtf('catmull-rom',0.25)/gather_mtf('catmull-rom',0.50):.4f}x"
      f"   (published 1.50x)")

# ---------------------------------------------------------------- simulation
def sample1d(sig, x, name):
    """Faithful port of the gather: 2*sup taps, normalised, clamped at edges."""
    tap, sup = KERN[name]
    i = math.floor(x); phi = x - i
    num = den = 0.0
    for n in range(-sup + 1, sup + 1):
        w = tap(n - phi)
        j = min(max(i + n, 0), len(sig) - 1)
        num += w * sig[j]; den += w
    return num / den if abs(den) > 1e-12 else 0.0

N, MARGIN = 400, 16
def run(f_out, kern, phases=PHASE_SAMPLES):
    """f_out in cycles per FULL-RES pixel. Returns dict of stats per arm."""
    L = N + 2*MARGIN
    x_full = np.arange(L*2, dtype=float)              # pitch-1 lattice
    full = np.cos(2*math.pi*f_out*x_full)             # the scene
    out = {}
    for arm, pitch in (("OLD plane (pitch 2)", 2.0), ("NEW fullres (pitch 1)", 1.0)):
        src = full[::int(pitch)]                      # the lattice the gather reads
        amps, rmss, corrs = [], [], []
        for p in range(phases):
            sh = (p + 0.5)/phases                     # shift, in FULL-RES pixels
            # destination is one value per CFA site; sample the source lattice
            got = np.array([sample1d(src, (MARGIN + i)*(2.0/pitch) + sh*(1.0/pitch)*2.0/2.0*(2.0/pitch)/(2.0/pitch), kern)
                            for i in range(N)]) if False else None
            # explicit and readable: destination site k sits at full-res coord
            # 2k (one site per quad); source index = (2k + shift)/pitch
            ks = np.arange(N) + MARGIN
            got = np.array([sample1d(src, (2*k + sh)/pitch, kern) for k in ks])
            truth = np.cos(2*math.pi*f_out*(2*ks + sh))
            th = 2*math.pi*(f_out*2)*np.arange(N)     # site lattice = pitch 2
            a = 2*abs((got*np.exp(-1j*th)).sum())/N
            amps.append(a)
            rmss.append(float(np.sqrt(((got-truth)**2).mean())))
            g, t = got-got.mean(), truth-truth.mean()
            corrs.append(float((g*t).sum()/math.sqrt((g*g).sum()*(t*t).sum())) if (g*g).sum()>0 else 0.0)
        out[arm] = dict(amp=float(np.mean(amps)), amp_min=float(np.min(amps)),
                        amp_max=float(np.max(amps)), rms=float(np.mean(rmss)),
                        corr=float(np.mean(corrs)))
    return out

print("\n=== (2) CONTROLS ===")
z = run(0.25, "catmull-rom", phases=1)
zz = {k: run(0.25, "catmull-rom", phases=1) for k in [0]}
# null: zero shift must be an exact identity
for arm, pitch in (("OLD plane (pitch 2)", 2.0), ("NEW fullres (pitch 1)", 1.0)):
    L = N + 2*MARGIN
    full = np.cos(2*math.pi*0.25*np.arange(L*2, dtype=float))
    src = full[::int(pitch)]
    ks = np.arange(N) + MARGIN
    got = np.array([sample1d(src, (2*k + 0.0)/pitch, "catmull-rom") for k in ks])
    truth = np.cos(2*math.pi*0.25*(2*ks))
    print(f"  NULL shift=0 {arm:24s} max|got-truth| = {np.abs(got-truth).max():.3e}")

print("\n=== (3) THE TEST: phase-averaged, f_out = 0.25 cyc per FULL-RES pixel ===")
for kern in ("catmull-rom", "nearest"):
    r = run(0.25, kern)
    o, n = r["OLD plane (pitch 2)"], r["NEW fullres (pitch 1)"]
    print(f"\n  kernel = {kern}")
    print(f"    {'arm':<24} {'amplitude':>10} {'[min':>8} {'max]':>8} {'rms err':>9} {'corr':>8}")
    for k, v in r.items():
        print(f"    {k:<24} {v['amp']:10.4f} {v['amp_min']:8.4f} {v['amp_max']:8.4f} "
              f"{v['rms']:9.4f} {v['corr']:8.4f}")
    print(f"    5.1 predicts OLD={gather_mtf(kern,0.50):.4f} NEW={gather_mtf(kern,0.25):.4f} "
          f"ratio={gather_mtf(kern,0.25)/gather_mtf(kern,0.50):.4f}x")
    print(f"    MEASURED ratio (amplitude) = {n['amp']/o['amp']:.4f}x   "
          f"(fidelity: rms {o['rms']:.4f} -> {n['rms']:.4f}, "
          f"corr {o['corr']:.4f} -> {n['corr']:.4f})")

print("\n=== (4) sweep: is the amplitude ratio the whole story? ===")
print(f"{'f_out':>7} {'OLD amp':>9} {'NEW amp':>9} {'ratio':>7} {'5.1 pred':>9} "
      f"{'OLD rms':>9} {'NEW rms':>9} {'OLD corr':>9} {'NEW corr':>9}")
for f_out in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45):
    r = run(f_out, "catmull-rom")
    o, n = r["OLD plane (pitch 2)"], r["NEW fullres (pitch 1)"]
    fp = 2*f_out
    pred = (gather_mtf("catmull-rom", f_out)/gather_mtf("catmull-rom", fp)) if fp <= 0.5 else float("nan")
    print(f"{f_out:7.2f} {o['amp']:9.4f} {n['amp']:9.4f} {n['amp']/o['amp']:7.3f} {pred:9.3f} "
          f"{o['rms']:9.4f} {n['rms']:9.4f} {o['corr']:9.4f} {n['corr']:9.4f}")
