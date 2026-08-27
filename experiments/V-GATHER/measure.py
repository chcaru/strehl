"""V-GATHER: measure the two arms on real masters with commissioned instruments.

Files are --linear-srgb --demosaic: the camera matrix applied, NO transfer curve,
so DN are comparable between arms and no tone-scaling stage is crossed. Both arms
come from ONE pinned binary; both renders are bit-exactly reproducible.
"""
import sys, os, json, gc
import numpy as np
import tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instr import A_stat, B_stat, C_stat, step_overshoot, luma, edge_energy, boxblur

OUT = r"C:\dev\strehl-out\V-GATHER"
SUBJECTS = ["wrapped-text-1", "wrapped-text-2", "bee-1-cpl", "couch-fibers-cpl",
            "tweezers-cpl", "foam", "lavendar-cpl", "flower-bud-alone-cpl",
            "coffee-bubbles", "highly-angled-ruler-mm-cpl"]
TILE = 64


def load(subject, arm):
    a = tifffile.imread(os.path.join(OUT, f"{subject}-q-g{arm}.tiff"))
    return luma(a[:, :, :3].astype(np.float64))


def tile_std(y, t=TILE):
    h, w = y.shape[0] // t * t, y.shape[1] // t * t
    v = y[:h, :w].reshape(h // t, t, w // t, t)
    return v.std(axis=(1, 3))


def hp(y):
    return y - boxblur(y, 5)


def band_power(y, bands):
    """Radial power spectrum of a centred 2048^2 crop, Hann-windowed."""
    n = 2048
    cy, cx = y.shape[0] // 2, y.shape[1] // 2
    c = y[cy - n // 2:cy + n // 2, cx - n // 2:cx + n // 2]
    c = c - c.mean()
    wnd = np.hanning(n)
    c = c * wnd[:, None] * wnd[None, :]
    F = np.abs(np.fft.rfft2(c)) ** 2
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    r = np.hypot(fy, fx)
    return {f"{a}-{b}": float(F[(r >= a) & (r < b)].mean()) for a, b in bands}


BANDS = [(0.05, 0.15), (0.15, 0.25), (0.25, 0.35), (0.35, 0.50)]

rows = []
for subj in SUBJECTS:
    rec = {"subject": subj}
    y = {}
    for arm in ("0", "1"):
        y[arm] = load(subj, arm)
    # flat / textured tiles chosen from the MEAN of the two arms so neither
    # arm's own statistic picks the sites it will then be scored on.
    m = 0.5 * (y["0"] + y["1"])
    ts = tile_std(m)
    q10, q90 = np.percentile(ts, (10, 90))
    flat = ts <= q10
    tex = ts >= q90
    for arm in ("0", "1"):
        yy = y[arm]
        d = hp(yy)
        ds = tile_std(d)
        rec[f"edge_{arm}"] = edge_energy(yy)
        rec[f"B_{arm}"] = B_stat(yy)
        a = A_stat(yy); rec[f"A_{arm}"] = a["over"]; rec[f"An_{arm}"] = a["n"]
        c = C_stat(yy); rec[f"C_{arm}"] = c["over"]; rec[f"Cn_{arm}"] = c["n"]
        rec[f"hp_flat_{arm}"] = float(np.sqrt((ds[flat] ** 2).mean()))
        rec[f"hp_tex_{arm}"] = float(np.sqrt((ds[tex] ** 2).mean()))
        rec[f"mean_{arm}"] = float(yy.mean())
        rec.update({f"P{k}_{arm}": v for k, v in band_power(yy, BANDS).items()})
        del yy, d, ds; gc.collect()
    rows.append(rec)
    print(f"{subj:28s} edge {rec['edge_0']:7.3f}->{rec['edge_1']:7.3f} "
          f"({100*(rec['edge_1']/rec['edge_0']-1):+6.2f}%)  "
          f"A {rec['A_0']:+7.4f}->{rec['A_1']:+7.4f}  "
          f"C {rec['C_0']:+7.4f}->{rec['C_1']:+7.4f}  "
          f"B {100*rec['B_0']:6.3f}%->{100*rec['B_1']:6.3f}%  "
          f"noise(flat) {rec['hp_flat_0']:6.2f}->{rec['hp_flat_1']:6.2f} "
          f"({100*(rec['hp_flat_1']/rec['hp_flat_0']-1):+6.2f}%)", flush=True)
    del y, m; gc.collect()

json.dump(rows, open(os.path.join(OUT, "measure.json"), "w"), indent=1)

print()
print("=" * 130)
print("BAND POWER RATIO g1/g0, 2048^2 centred crop, Hann window (cyc/full-res px)")
print("=" * 130)
print(f"{'subject':28s}" + "".join(f"{f'{a}-{b}':>14s}" for a, b in BANDS))
for r in rows:
    print(f"{r['subject']:28s}" + "".join(
        f"{r[f'P{a}-{b}_1'] / r[f'P{a}-{b}_0']:14.4f}" for a, b in BANDS))

print()
print("=" * 130)
print("TEXTURE vs NOISE: rms of the 5px high-pass, in the flattest 10% and busiest 10% of 64px tiles")
print("=" * 130)
print(f"{'subject':28s} {'flat g0':>9s} {'flat g1':>9s} {'flat %':>8s} "
      f"{'tex g0':>9s} {'tex g1':>9s} {'tex %':>8s} {'tex/flat gain':>14s}")
for r in rows:
    f0, f1, t0, t1 = r["hp_flat_0"], r["hp_flat_1"], r["hp_tex_0"], r["hp_tex_1"]
    print(f"{r['subject']:28s} {f0:9.3f} {f1:9.3f} {100*(f1/f0-1):+8.2f} "
          f"{t0:9.3f} {t1:9.3f} {100*(t1/t0-1):+8.2f} {(t1/t0)/(f1/f0):14.4f}")
