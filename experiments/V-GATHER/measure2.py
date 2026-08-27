"""Pass 2. Three things pass 1 could not settle.

1. MATCHED SITES. In pass 1 each arm chose its own edge points from its own
   gradient percentile, so the two numbers came from different populations.
   Here the edge list is chosen ONCE from the MEAN of the two arms and both are
   profiled at exactly those points. Neither arm picks the sites it is scored on.
2. IS THE FINE BAND SIGNAL OR NOISE? Power in 0.25-0.50 cyc/px measured
   separately in the flattest tiles (noise only) and the busiest tiles
   (signal+noise). Fine-band SNR = (P_tex - P_flat) / P_flat per arm. Detail
   recovery raises it; a wider noise bandwidth does not.
3. IS THE EXTRA ENERGY CHROMA? A double demosaic makes correlated colour error.
   Measured as high-pass rms of (R-B) in the flat tiles.
"""
import sys, os, json, gc
import numpy as np
import tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instr import B_stat, step_overshoot, luma, edge_energy, boxblur

OUT = r"C:\dev\strehl-out\V-GATHER"
SUBJECTS = ["wrapped-text-1", "wrapped-text-2", "bee-1-cpl", "couch-fibers-cpl",
            "tweezers-cpl", "foam", "lavendar-cpl", "flower-bud-alone-cpl",
            "coffee-bubbles", "highly-angled-ruler-mm-cpl"]
TILE = 64
N = 2048


def edge_pts(img, half, blur, edge_pct, max_prof, seed, ds=1):
    from instr import downsample
    img = downsample(np.asarray(img, np.float64), ds)
    b = boxblur(img, blur)
    gy = np.zeros_like(b); gx = np.zeros_like(b)
    gy[1:-1, :] = (b[2:, :] - b[:-2, :]) * 0.5
    gx[:, 1:-1] = (b[:, 2:] - b[:, :-2]) * 0.5
    mag = np.hypot(gy, gx)
    m = np.zeros(mag.shape, bool)
    m[half + 2:-half - 2, half + 2:-half - 2] = True
    thr = float(np.percentile(mag[m], edge_pct))
    ys, xs = np.nonzero((mag >= thr) & m)
    rng = np.random.default_rng(seed)
    if ys.size > max_prof:
        k = rng.choice(ys.size, max_prof, replace=False)
        ys, xs = ys[k], xs[k]
    return ys, xs


def crop(y):
    cy, cx = y.shape[0] // 2, y.shape[1] // 2
    return y[cy - N // 2:cy + N // 2, cx - N // 2:cx + N // 2]


def band_power_tiles(y, mask, lo, hi, t=256):
    """Mean power in [lo,hi) cyc/px over the selected t-px tiles."""
    h, w = y.shape[0] // t * t, y.shape[1] // t * t
    v = y[:h, :w].reshape(h // t, t, w // t, t)
    wnd = np.hanning(t)
    W2 = wnd[:, None] * wnd[None, :]
    fy = np.fft.fftfreq(t)[:, None]; fx = np.fft.rfftfreq(t)[None, :]
    r = np.hypot(fy, fx); sel = (r >= lo) & (r < hi)
    out = []
    iy, ix = np.nonzero(mask)
    for a, b in zip(iy.tolist(), ix.tolist()):
        c = v[a, :, b, :]
        c = (c - c.mean()) * W2
        F = np.abs(np.fft.rfft2(c)) ** 2
        out.append(float(F[sel].mean()))
    return float(np.mean(out)) if out else float("nan")


rows = []
for subj in SUBJECTS:
    im = {a: tifffile.imread(os.path.join(OUT, f"{subj}-q-g{a}.tiff"))[:, :, :3].astype(np.float64)
          for a in ("0", "1")}
    y = {a: luma(im[a]) for a in ("0", "1")}
    chroma = {a: im[a][:, :, 0] - im[a][:, :, 2] for a in ("0", "1")}
    for a in ("0", "1"):
        del im[a]
    gc.collect()
    mean = 0.5 * (y["0"] + y["1"])

    # matched edge sites, chosen once on the mean image
    ptsC = edge_pts(mean, 24, 5, 99.5, 4000, 0, ds=1)
    ptsA = edge_pts(mean, 100, 9, 99.5, 4000, 0, ds=2)

    # tiles chosen once on the mean image, at 256 px so the FFT band is resolved
    t = 256
    h, w = mean.shape[0] // t * t, mean.shape[1] // t * t
    ts = mean[:h, :w].reshape(h // t, t, w // t, t).std(axis=(1, 3))
    q15, q85 = np.percentile(ts, (15, 85))
    flat, tex = ts <= q15, ts >= q85

    rec = {"subject": subj, "n_flat": int(flat.sum()), "n_tex": int(tex.sum())}
    for a in ("0", "1"):
        cA = step_overshoot(y[a], half=100, band=(8, 90), ds=2, pts_override=ptsA)
        cC = step_overshoot(y[a], half=24, band=(1, 4), ds=1, blur=5, pts_override=ptsC)
        cS = step_overshoot(y[a], half=24, band=(1, 4), ds=1, blur=5, seed=11, shuffle=True)
        rec[f"Am_{a}"], rec[f"AmN_{a}"] = cA["over"], cA["n"]
        rec[f"Cm_{a}"], rec[f"CmN_{a}"] = cC["over"], cC["n"]
        rec[f"Csh_{a}"] = cS["over"]
        rec[f"Pfine_flat_{a}"] = band_power_tiles(y[a], flat, 0.25, 0.50, t)
        rec[f"Pfine_tex_{a}"] = band_power_tiles(y[a], tex, 0.25, 0.50, t)
        rec[f"Pmid_flat_{a}"] = band_power_tiles(y[a], flat, 0.10, 0.20, t)
        rec[f"Pmid_tex_{a}"] = band_power_tiles(y[a], tex, 0.10, 0.20, t)
        hpc = chroma[a] - boxblur(chroma[a], 5)
        hc = hpc[:h, :w].reshape(h // t, t, w // t, t).std(axis=(1, 3))
        rec[f"chroma_flat_{a}"] = float(np.sqrt((hc[flat] ** 2).mean()))
    for k in ("fine", "mid"):
        for a in ("0", "1"):
            f, x = rec[f"P{k}_flat_{a}"], rec[f"P{k}_tex_{a}"]
            rec[f"snr_{k}_{a}"] = (x - f) / f
    rows.append(rec)
    print(f"{subj:28s} Am {rec['Am_0']:+8.4f}->{rec['Am_1']:+8.4f} (n={rec['AmN_0']}/{rec['AmN_1']})"
          f"  Cm {rec['Cm_0']:+8.4f}->{rec['Cm_1']:+8.4f} (n={rec['CmN_0']}/{rec['CmN_1']})"
          f"  Cshuf {rec['Csh_0']:+7.4f}/{rec['Csh_1']:+7.4f}", flush=True)
    del y, mean, chroma; gc.collect()

json.dump(rows, open(os.path.join(OUT, "measure2.json"), "w"), indent=1)

print()
print("=" * 132)
print("FINE-BAND (0.25-0.50 cyc/px) SIGNAL-TO-NOISE.  P_flat is noise only; P_tex is signal+noise.")
print("SNR = (P_tex - P_flat)/P_flat.  Detail recovery RAISES it. A wider noise bandwidth alone does not.")
print("=" * 132)
print(f"{'subject':28s} {'Pflat g0':>11s} {'Pflat g1':>11s} {'x':>6s} {'Ptex g0':>11s} {'Ptex g1':>11s} {'x':>6s} "
      f"{'SNR g0':>9s} {'SNR g1':>9s} {'SNR x':>7s}")
for r in rows:
    print(f"{r['subject']:28s} {r['Pfine_flat_0']:11.1f} {r['Pfine_flat_1']:11.1f} "
          f"{r['Pfine_flat_1']/r['Pfine_flat_0']:6.2f} {r['Pfine_tex_0']:11.1f} {r['Pfine_tex_1']:11.1f} "
          f"{r['Pfine_tex_1']/r['Pfine_tex_0']:6.2f} {r['snr_fine_0']:9.2f} {r['snr_fine_1']:9.2f} "
          f"{r['snr_fine_1']/r['snr_fine_0'] if r['snr_fine_0'] else float('nan'):7.3f}")

print()
print("=" * 132)
print("MID-BAND (0.10-0.20 cyc/px) control -- well inside BOTH arms' passband, so it should barely move")
print("=" * 132)
print(f"{'subject':28s} {'SNR g0':>10s} {'SNR g1':>10s} {'ratio':>8s}   {'Pflat x':>9s} {'Ptex x':>9s}")
for r in rows:
    print(f"{r['subject']:28s} {r['snr_mid_0']:10.2f} {r['snr_mid_1']:10.2f} "
          f"{r['snr_mid_1']/r['snr_mid_0'] if r['snr_mid_0'] else float('nan'):8.3f}   "
          f"{r['Pmid_flat_1']/r['Pmid_flat_0']:9.3f} {r['Pmid_tex_1']/r['Pmid_tex_0']:9.3f}")

print()
print("=" * 132)
print("CHROMA high-pass rms in flat tiles (R-B). A double demosaic shows up here.")
print("=" * 132)
for r in rows:
    print(f"{r['subject']:28s} {r['chroma_flat_0']:9.3f} -> {r['chroma_flat_1']:9.3f} "
          f"({100*(r['chroma_flat_1']/r['chroma_flat_0']-1):+7.2f}%)")
