"""M118 arm 2 -- the metrics, exactly as pre-registered.

Everything is computed on the BYTE-FROZEN measurement render: `strehl stack`
with no --srgb, 16-bit binned linear camera-native RGB on the plane grid. That
grid is 1:1 with --index-map and --n-eff-map, so no resampling of mine enters
any number here.

Rule 9 is discharged FIRST, not last: M2 (the flat-ROI control) is computed and
printed before M1 is quoted, because a metric that fails it invalidates every
number already computed with it.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

OUT = Path(r"C:\dev\strehl-out\M118")
HERE = Path(__file__).parent.parent
ARMS = ["nearest", "bilinear", "catmull-rom", "lanczos2", "lanczos3"]
BASELINE = "catmull-rom"

TILE = 128
BAND = (0.30, 0.48)      # cyc/px, the M95/M113 scoring band, kept for commensurability
DECILE = 0.10


def from_log(subject: str, arm: str, pat: str):
    """Pull a printed statistic out of the merge's own log.

    `mean n_eff` is printed inside the n_eff-map line ("counts 1..6, mean 1.154")
    rather than as its own field, which r1_render.py's regex missed. Reading the
    log rather than re-rendering keeps the frozen hashes frozen.
    """
    import re
    p = OUT / subject / "logs" / f"{subject}--{arm}--measure.log"
    m = re.search(pat, p.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def green(path: Path) -> np.ndarray:
    """The green plane of a binned linear render, as f64."""
    a = tifffile.imread(str(path))
    if a.ndim != 3 or a.shape[2] != 3:
        raise SystemExit(f"unexpected shape {a.shape} for {path}")
    return a[:, :, 1].astype(np.float64)


def central_half(h: int, w: int):
    return slice(h // 4, h // 4 + h // 2), slice(w // 4, w // 4 + w // 2)


def tile_origins(h: int, w: int):
    ys, xs = central_half(h, w)
    y0s = range(ys.start, ys.stop - TILE + 1, TILE)
    x0s = range(xs.start, xs.stop - TILE + 1, TILE)
    return [(y, x) for y in y0s for x in x0s]


_WIN = np.outer(np.hanning(TILE), np.hanning(TILE))
_FR = None


def _radial_freq():
    """Radial spatial frequency, in cycles per pixel, for a TILE x TILE FFT."""
    global _FR
    if _FR is None:
        f = np.fft.fftfreq(TILE)
        fy, fx = np.meshgrid(f, f, indexing="ij")
        _FR = np.sqrt(fy ** 2 + fx ** 2)
    return _FR


def band_power(tile: np.ndarray) -> float:
    """Radially-averaged power in BAND. Mean removed, Hann windowed."""
    t = tile - tile.mean()
    p = np.abs(np.fft.fft2(t * _WIN)) ** 2
    fr = _radial_freq()
    m = (fr >= BAND[0]) & (fr < BAND[1])
    return float(p[m].mean())


def tile_bandpowers(img: np.ndarray, origins) -> np.ndarray:
    return np.array([band_power(img[y:y + TILE, x:x + TILE]) for y, x in origins])


def grad_mag(img: np.ndarray) -> np.ndarray:
    gy = np.zeros_like(img)
    gx = np.zeros_like(img)
    gy[1:-1, :] = img[2:, :] - img[:-2, :]
    gx[:, 1:-1] = img[:, 2:] - img[:, :-2]
    return np.hypot(gy, gx)


def extrema_count(img: np.ndarray, mask: np.ndarray) -> int:
    """Strict 8-neighbour local extrema, counted only inside `mask`."""
    c = img[1:-1, 1:-1]
    nb = [img[:-2, :-2], img[:-2, 1:-1], img[:-2, 2:],
          img[1:-1, :-2], img[1:-1, 2:],
          img[2:, :-2], img[2:, 1:-1], img[2:, 2:]]
    hi = np.ones_like(c, dtype=bool)
    lo = np.ones_like(c, dtype=bool)
    for n in nb:
        hi &= c > n
        lo &= c < n
    return int(((hi | lo) & mask[1:-1, 1:-1]).sum())


def analyse(subject: str) -> dict:
    rec = json.loads((HERE / "out" / f"r1_{subject}.json").read_text())
    print(f"\n=== {subject}   limit={rec['limit']} gate={rec['gate']}")

    planes = {a: green(Path(rec["arms"][a]["measure"])) for a in ARMS}
    h, w = planes[BASELINE].shape
    origins = tile_origins(h, w)
    print(f"  plane {w}x{h}, {len(origins)} tiles of {TILE} px over the central half")

    # --- stratification, symmetric across arms by construction ---------------
    # Gradient is measured on the ARITHMETIC MEAN OF ALL FIVE ARMS so that no arm
    # under test chooses its own scoring region (M113 discipline 752).
    mean_img = np.mean([planes[a] for a in ARMS], axis=0)
    gm = grad_mag(mean_img)
    tile_grad = np.array([gm[y:y + TILE, x:x + TILE].mean() for y, x in origins])
    order = np.argsort(tile_grad)
    n_dec = max(1, int(len(origins) * DECILE))
    flat_idx = order[:n_dec]
    detail_idx = order[-n_dec:]
    print(f"  strata: {n_dec} flat tiles (grad {tile_grad[flat_idx].mean():.1f}), "
          f"{n_dec} detail tiles (grad {tile_grad[detail_idx].mean():.1f}), "
          f"ratio {tile_grad[detail_idx].mean() / max(tile_grad[flat_idx].mean(), 1e-9):.1f}x")

    bp = {a: tile_bandpowers(planes[a], origins) for a in ARMS}
    base = bp[BASELINE]

    res = {"subject": subject, "limit": rec["limit"], "gate": rec["gate"],
           "n_tiles": len(origins), "n_decile": n_dec,
           "grad_detail": float(tile_grad[detail_idx].mean()),
           "grad_flat": float(tile_grad[flat_idx].mean()),
           "pinned_exposure": rec.get("pinned_exposure"),
           "null_pass": rec.get("null_pass"),
           "plant_P1_distinct_hashes": rec.get("plant_P1_distinct_hashes"),
           "arms": {}}

    # --- RULE 9 FIRST: the flat-ROI control before any detail number ---------
    print("\n  -- rule 9 control FIRST: flat-ROI band gain (M2), dex vs catmull-rom")
    for a in ARMS:
        d = np.log10(bp[a][flat_idx] / base[flat_idx])
        print(f"     {a:<12} M2 = {d.mean():+.4f}  sem {d.std(ddof=1)/np.sqrt(len(d)):.4f}")

    print("\n  -- M1 detail / M2 flat / M3 discrimination / M4 flat sd / M5 extrema")
    # top-1% gradient mask, again from the cross-arm mean, for M5
    thr = np.percentile(gm, 99.0)
    edge_mask = gm >= thr
    cr_ext = extrema_count(planes[BASELINE], edge_mask)

    for a in ARMS:
        d1 = np.log10(bp[a][detail_idx] / base[detail_idx])
        d2 = np.log10(bp[a][flat_idx] / base[flat_idx])
        dall = np.log10(bp[a] / base)
        sd = float(np.mean([planes[a][y:y + TILE, x:x + TILE].std()
                            for y, x in np.array(origins)[flat_idx]]))
        ext = extrema_count(planes[a], edge_mask)
        res["arms"][a] = {
            "M1_detail_dex": float(d1.mean()),
            "M1_sem": float(d1.std(ddof=1) / np.sqrt(len(d1))),
            "M2_flat_dex": float(d2.mean()),
            "M2_sem": float(d2.std(ddof=1) / np.sqrt(len(d2))),
            "M3_discrimination_dex": float(d1.mean() - d2.mean()),
            "M1_alltiles_dex": float(dall.mean()),
            "M4_flat_sd_DN": sd,
            "M5_extrema": ext,
            "M5_ratio_vs_cr": ext / cr_ext if cr_ext else float("nan"),
            "secs": rec["arms"][a]["measure_secs"],
            "mean_n_eff": from_log(subject, a, r"counts [0-9.]+\.\.[0-9]+, mean ([0-9.]+)"),
            "coverage": from_log(subject, a, r"field of view scaled to ([0-9.]+)"),
            "resampler_printed": from_log(subject, a, r"resampler\s*:\s*(\w+)"),
        }
        r = res["arms"][a]
        # Wiring assertion: the binary must have PRINTED the kernel this arm asked
        # for. A silent fallback to the default is exactly the failure that would
        # make all five arms the same measurement, and P1's distinct hashes bound
        # it only collectively.
        want = {"nearest": "Nearest", "bilinear": "Bilinear", "catmull-rom": "CatmullRom",
                "lanczos2": "Lanczos2", "lanczos3": "Lanczos3"}[a]
        if r["resampler_printed"] != want:
            raise SystemExit(f"FATAL: {subject}/{a} printed resampler "
                             f"{r['resampler_printed']!r}, expected {want!r}")
        print(f"     {a:<12} M1 {r['M1_detail_dex']:+.4f}  M2 {r['M2_flat_dex']:+.4f}  "
              f"M3 {r['M3_discrimination_dex']:+.4f}  sd {r['M4_flat_sd_DN']:8.1f}  "
              f"extrema {r['M5_ratio_vs_cr']:.4f}x  {r['secs']:6.1f}s")

    # --- M6 + B2 / ORCH N4 ---------------------------------------------------
    print("\n  -- M6 election agreement and the N4 stratification")
    idx_cr = tifffile.imread(str(rec["arms"][BASELINE]["index"])).astype(np.int32)
    for a in ARMS:
        if a == BASELINE:
            continue
        idx_a = tifffile.imread(str(rec["arms"][a]["index"])).astype(np.int32)
        agree_map = (idx_a == idx_cr)
        agree_tile = np.array([agree_map[y:y + TILE, x:x + TILE].mean() for y, x in origins])
        gain_tile = np.log10(bp[a] / base)
        hi = agree_tile >= 0.95
        lo = agree_tile < 0.95
        entry = res["arms"][a]
        entry["M6_agreement_whole"] = float(agree_map.mean())
        entry["N4_gain_agree_ge095"] = float(gain_tile[hi].mean()) if hi.any() else None
        entry["N4_n_ge095"] = int(hi.sum())
        entry["N4_gain_agree_lt095"] = float(gain_tile[lo].mean()) if lo.any() else None
        entry["N4_n_lt095"] = int(lo.sum())
        if agree_tile.std() > 0 and gain_tile.std() > 0:
            entry["N4_corr"] = float(np.corrcoef(agree_tile, gain_tile)[0, 1])
        else:
            entry["N4_corr"] = None
        if hi.any() and lo.any():
            entry["N4_pass"] = bool(entry["N4_gain_agree_ge095"] > entry["N4_gain_agree_lt095"]
                                    and (entry["N4_corr"] or 0) > 0)
        else:
            entry["N4_pass"] = None
        print(f"     {a:<12} agree {entry['M6_agreement_whole']*100:6.2f}%   "
              f">=.95 {entry['N4_gain_agree_ge095']} (n={entry['N4_n_ge095']})   "
              f"<.95 {entry['N4_gain_agree_lt095']} (n={entry['N4_n_lt095']})   "
              f"corr {entry['N4_corr']}   N4={entry['N4_pass']}")

    # --- B6 P2: the metric plant, both directions ---------------------------
    # The null and P1 prove the WIRING moves. They cannot prove the METRIC can
    # move. Fact 1548: a bar once read 0 px and so did its broken plant.
    cr = planes[BASELINE]
    blur = gaussian_filter(cr, 0.5)
    boost = cr + 0.5 * (cr - gaussian_filter(cr, 1.0))
    for name, img in (("blur_sigma0.5", blur), ("unsharp_x1.5", boost)):
        d = np.log10(tile_bandpowers(img, origins)[detail_idx] / base[detail_idx])
        res.setdefault("plant_P2", {})[name] = float(d.mean())
        print(f"  PLANT P2  {name:<16} M1 = {d.mean():+.4f} dex")
    p2 = res["plant_P2"]
    res["plant_P2_pass"] = bool(p2["blur_sigma0.5"] < -0.05 and p2["unsharp_x1.5"] > +0.05)
    print(f"  PLANT P2  pass={res['plant_P2_pass']} "
          f"(needs blur < -0.05 dex AND unsharp > +0.05 dex)")

    (HERE / "out" / f"a1_{subject}.json").write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["flat-on-ruler-cpl", "wrapped-text-1", "bee-3-cpl"]):
        analyse(s)
