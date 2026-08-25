"""M120 step 7 — the battery: R4, the placebo, the shipped arm, the rival
metrics, item 1 (coincidence) and item 2 (tiling geometry).

ROI is the one fixed in 06b: crop coords rows 146:274 cols 292:420.
All arms share it. Nothing below re-chooses an ROI.
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage as ndi
from scipy import stats

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
HERE = Path(__file__).resolve().parent

ROI_ABS = (1200, 1900, 300, 1400)
MARGIN = 22
BOX = (ROI_ABS[0] - MARGIN, ROI_ABS[1] + MARGIN, ROI_ABS[2] - MARGIN, ROI_ABS[3] + MARGIN)
TIGHT = (330, 610, 150, 570)
R = (146, 274, 292, 420)          # ROI in TIGHT-crop coords, fixed by 06b
BANDS = [(1.0, 4.0), (2.0, 8.0), (4.0, 16.0), (8.0, 32.0)]
SHIFT = 64


def bp(a, s):
    a = np.asarray(a, np.float32)
    return ndi.gaussian_filter(a, s[0]) - ndi.gaussian_filter(a, s[1])


def rms(a, m):
    return float(np.sqrt((a[m] ** 2).mean()))


def lap_kurt(a, m):
    v = ndi.laplace(ndi.gaussian_filter(np.asarray(a, np.float32), 2.0))[m]
    return float(stats.kurtosis(v, fisher=False))


def flat_components(a, m, tol):
    """count of connected locally-flat regions per 10k px -- rival metric."""
    a = ndi.gaussian_filter(np.asarray(a, np.float32), 2.0)
    g = np.hypot(*np.gradient(a))
    lab, k = ndi.label((g < tol) & m)
    if k == 0:
        return 0.0
    sz = np.bincount(lab.ravel())[1:]
    return float((sz >= 64).sum() * 1e4 / m.sum())


def main() -> int:
    y0, y1, x0, x1 = TIGHT
    h, w = y1 - y0, x1 - x0
    m = np.zeros((h, w), bool)
    m[R[0]:R[1], R[2]:R[3]] = True

    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    n = cube.shape[0]
    frames = np.empty((n, h, w), np.float32)
    for k in range(n):
        frames[k] = np.array(cube[k, y0:y1, x0:x1], np.float32)
    lev = frames.reshape(n, -1)[:, m.ravel()].mean(1)
    gl = float(lev.mean())

    arg = np.load(M87 / "bee3-leg-argbest.npy")[y0:y1, x0:x1].astype(np.int32)
    sel = np.load(M87 / "bee3-leg-sel.npy")[y0:y1, x0:x1].astype(np.float32)
    g2 = np.load(M87 / "bee3-leg-g2.npy")[y0:y1, x0:x1].astype(np.float32)
    mean = frames.mean(0)

    def gather(idx, cube3):
        return np.take_along_axis(cube3, idx[None], 0)[0]

    assert np.allclose(gather(arg, frames), sel, atol=1e-3), "argbest does not reproduce sel"
    print("check: gather(argbest, cube) reproduces bee3-leg-sel exactly -- OK")

    # R4: per-frame photometric normalisation, additive and multiplicative
    add = frames - lev[:, None, None] + gl
    mul = frames * (gl / lev)[:, None, None]
    sel_add, sel_mul = gather(arg, add), gather(arg, mul)

    # NULL-3 placebo: identical index-field statistics, decoupled from the
    # focus response at each pixel (rule 11: a different rule on the same data)
    argsh = np.roll(np.roll(arg, SHIFT, 0), SHIFT, 1)
    sel_sh = gather(argsh, frames)
    # NULL-4: an i.i.d. index field with the same marginal distribution
    rng = np.random.default_rng(4242)
    argiid = rng.choice(arg.ravel(), size=arg.shape).astype(np.int32)
    sel_iid = gather(argiid, frames)

    pr = np.random.default_rng(7)
    ref = frames[n // 2].copy()
    sy, sx = pr.integers(0, h, 40), pr.integers(0, w, 40)
    yy, xx = np.mgrid[0:h, 0:w]
    cid = ((yy[None] - sy[:, None, None]) ** 2 + (xx[None] - sx[:, None, None]) ** 2).argmin(0)
    pos = ref + pr.normal(0.0, float(lev.std()), 40).astype(np.float32)[cid]

    arms = {
        "gate0 argmax (brief's image)": sel,
        "gate2": g2,
        "R4 gate0, per-frame level removed (additive)": sel_add,
        "R4 gate0, per-frame gain removed (multiplicative)": sel_mul,
        "NULL-3 placebo: index field shifted 64,64": sel_sh,
        "NULL-4 placebo: i.i.d. index, same marginal": sel_iid,
        "NULL-1 plain mean (constant weights)": mean,
        "NULL-2 single frame": ref,
        "POS planted patchwork": pos,
    }
    dens = {b: max(rms(bp(f, b), m) for f in frames) for b in BANDS}

    print(f"\n=== Q = ||B I||_ROI / max_k ||B f_k||_ROI   (ROI {R}, {int(m.sum())} px) ===")
    print(f"{'arm':52s}" + "".join(f"{b[0]:g}-{b[1]:g}".rjust(10) for b in BANDS)
          + "   lapkurt   flatcc")
    out = {}
    tol = float(np.percentile(np.hypot(*np.gradient(ndi.gaussian_filter(mean, 2.0)))[m], 50))
    for name, img in arms.items():
        qs = [rms(bp(img, b), m) / dens[b] for b in BANDS]
        lk, fc = lap_kurt(img, m), flat_components(img, m, tol)
        out[name] = {"Q": {f"{b[0]:g}-{b[1]:g}": round(q, 4) for b, q in zip(BANDS, qs)},
                     "lap_kurtosis": round(lk, 3), "flat_cc_per_10k": round(fc, 2)}
        print(f"{name:52s}" + "".join(f"{q:10.3f}" for q in qs) + f"{lk:10.2f}{fc:9.2f}")
    print(f"{'  frame-population median Q':52s}"
          + "".join(f"{np.median([rms(bp(f,b),m) for f in frames])/dens[b]:10.3f}" for b in BANDS))
    print(f"{'  (denominator max_k, DN)':52s}" + "".join(f"{dens[b]:10.2f}" for b in BANDS))
    print(f"  per-frame ROI level sd = {lev.std():.1f} DN over {lev.min():.0f}..{lev.max():.0f} DN")

    # ---------- shipped arm: unit-free contrast, different grid ------------
    ship = tifffile.imread(M87 / "ship-before-linear.tif")[:, :, 1].astype(np.float32)
    dy, dx = (int(v) for v in np.load(OUT / "pc1_offset.npy"))
    sy0, sx0 = BOX[0] + dy + y0 + R[0], BOX[2] + dx + x0 + R[2]
    sr = ship[sy0: sy0 + (R[1] - R[0]), sx0: sx0 + (R[3] - R[2])]
    print(f"\n=== shipped render, same ROI via offset (dy={dy},dx={dx}) ===")
    print(f"  shipped ROI slice rows {sy0}:{sy0+128} cols {sx0}:{sx0+128}  "
          f"mean {sr.mean():.0f} sd {sr.std():.0f} DN")
    print(f"{'arm':44s}" + "".join(f"{b[0]:g}-{b[1]:g}".rjust(11) for b in BANDS))
    mm = np.ones(sr.shape, bool)
    ship_c = {b: rms(bp(sr, b), mm) / sr.mean() for b in BANDS}
    contrast = {
        "SHIPPED strehl (gate 4)": ship_c,
        "gate0 argmax": {b: rms(bp(sel[R[0]:R[1], R[2]:R[3]], b), mm) / sel[m].mean() for b in BANDS},
        "gate2": {b: rms(bp(g2[R[0]:R[1], R[2]:R[3]], b), mm) / g2[m].mean() for b in BANDS},
        "plain mean": {b: rms(bp(mean[R[0]:R[1], R[2]:R[3]], b), mm) / mean[m].mean() for b in BANDS},
    }
    fr_c = {b: np.array([rms(bp(f[R[0]:R[1], R[2]:R[3]], b), mm) / f[m].mean() for f in frames])
            for b in BANDS}
    for name, d in contrast.items():
        print(f"{name:44s}" + "".join(f"{1e4*d[b]:11.2f}" for b in BANDS))
    print(f"{'single frames: median':44s}" + "".join(f"{1e4*np.median(fr_c[b]):11.2f}" for b in BANDS))
    print(f"{'single frames: MAX over 299':44s}" + "".join(f"{1e4*fr_c[b].max():11.2f}" for b in BANDS))
    print("  (units: band-pass RMS / ROI mean level, x1e4 -- unit-free, so grids may differ)")
    print(f"{'Q_contrast SHIPPED / max frame':44s}"
          + "".join(f"{ship_c[b]/fr_c[b].max():11.3f}" for b in BANDS))
    print(f"{'Q_contrast gate0   / max frame':44s}"
          + "".join(f"{contrast['gate0 argmax'][b]/fr_c[b].max():11.3f}" for b in BANDS))

    # ---------- item 1: coincidence, with nulls ---------------------------
    print("\n=== item 1: does |grad elected-index| coincide with |grad luma|? ===")

    def gm(a):
        return np.hypot(*np.gradient(ndi.gaussian_filter(np.asarray(a, np.float32), 1.0)))

    ga = gm(arg)[m]

    def coin(img, tag, offs=(0, 0)):
        gi = gm(np.roll(np.roll(img, offs[0], 0), offs[1], 1))[m]
        r = stats.spearmanr(ga, gi)
        hi = gi[ga >= np.percentile(ga, 90)].mean()
        lo = gi[ga <= np.percentile(ga, 50)].mean()
        print(f"  {tag:44s} spearman rho={r.statistic:+.4f} p={r.pvalue:.2e}  "
              f"ratio(top10% edge / bottom50%)={hi/max(lo,1e-9):.3f}")
        return {"rho": float(r.statistic), "p": float(r.pvalue), "ratio": float(hi / max(lo, 1e-9))}

    co = {
        "gate0 render vs its own index": coin(sel, "gate0 render vs its own index"),
        "gate0, index shifted by 64": coin(sel, "gate0, index shifted 64 (null)", (SHIFT, SHIFT)),
        "gate2 vs the SAME index": coin(g2, "gate2 vs the SAME index"),
        "plain mean vs the index (decoupled)": coin(mean, "plain mean vs the index (decoupled)"),
        "single frame vs the index (decoupled)": coin(ref, "single frame vs the index (decoupled)"),
    }
    gs = gm(sr)
    rs = stats.spearmanr(ga, gs.ravel())
    print(f"  {'SHIPPED render vs the index':44s} spearman rho={rs.statistic:+.4f} "
          f"p={rs.pvalue:.2e}   (coarse registration only -- weak evidence)")
    co["shipped vs index (coarse reg)"] = {"rho": float(rs.statistic), "p": float(rs.pvalue)}

    # ---------- item 2: tiling geometry -----------------------------------
    print("\n=== item 2 (R2): are the polygon edges axis-aligned / on a pitch? ===")
    a = ndi.gaussian_filter(arg[R[0]:R[1], R[2]:R[3]].astype(np.float32), 1.0)
    gy, gx = np.gradient(a)
    mag = np.hypot(gy, gx)
    sel_e = mag > np.percentile(mag, 90)
    th = (np.degrees(np.arctan2(gy[sel_e], gx[sel_e])) + 180.0) % 180.0
    hist, edges = np.histogram(th, bins=18, range=(0, 180))
    frac = hist / hist.sum()
    axis = frac[[0, 8, 9, 17]].sum()          # within 10 deg of 0 or 90
    print("  edge-orientation histogram (10 deg bins, top-decile gradient):")
    print("   " + "  ".join(f"{int(edges[i]):3d}:{100*frac[i]:4.1f}%" for i in range(18)))
    print(f"  fraction within 10 deg of axis-aligned: {100*axis:.1f}%  "
          f"(uniform would be {100*4/18:.1f}%)")
    F = np.abs(np.fft.fftshift(np.fft.fft2((mag - mag.mean()) * np.hanning(mag.shape[0])[:, None]
                                           * np.hanning(mag.shape[1])[None, :])))
    c = np.array(F.shape) // 2
    prof = {}
    for name, line in (("horizontal (vertical edges)", F[c[0], :]), ("vertical (horizontal edges)", F[:, c[1]])):
        k = np.arange(len(line)) - len(line) // 2
        ok = np.abs(k) >= 4
        pk = np.argmax(line[ok])
        kk = k[ok][pk]
        pitch = len(line) / abs(kk) if kk else np.inf
        z = (line[ok][pk] - line[ok].mean()) / line[ok].std()
        prof[name] = {"pitch_px": float(pitch), "z": float(z)}
        print(f"  1-D spectrum {name:28s} strongest peak at pitch {pitch:6.1f} px, z={z:+.2f}")
    print("  (a genuine tiling artifact would give z >> 5 at an integer pitch on BOTH axes)")

    (HERE / "battery.json").write_text(json.dumps(
        {"roi_crop_coords": list(R), "arms": out,
         "denominators_dn": {f"{b[0]:g}-{b[1]:g}": round(float(v), 3) for b, v in dens.items()},
         "frame_level_sd_dn": float(lev.std()),
         "shipped_roi_slice": [int(sy0), int(sy0 + 128), int(sx0), int(sx0 + 128)],
         "shipped_contrast_x1e4": {k: {f"{b[0]:g}-{b[1]:g}": round(1e4 * float(v), 3) for b, v in d.items()}
                                   for k, d in contrast.items()},
         "frame_contrast_max_x1e4": {f"{b[0]:g}-{b[1]:g}": round(1e4 * float(fr_c[b].max()), 3) for b in BANDS},
         "coincidence": co, "axis_aligned_fraction": float(axis), "spectrum": prof},
        indent=2), encoding="utf-8")
    for nm, im in (("index", arg), ("gate0", sel), ("gate2", g2), ("shipped", sr)):
        a2 = np.asarray(im, np.float32)[R[0]:R[1], R[2]:R[3]] if nm != "shipped" else sr
        lo2, hi2 = np.percentile(a2, (0.5, 99.5))
        Image.fromarray(np.kron(np.clip(255 * (a2 - lo2) / max(hi2 - lo2, 1e-6), 0, 255).astype(np.uint8),
                                np.ones((3, 3), np.uint8))).save(OUT / f"BATT-{nm}.png")
    print(f"\nwrote {HERE / 'battery.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
