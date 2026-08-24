"""M84b step 12 - the registered tick localiser and projective plane fit.

Implements pre-registration sections 3.1, 3.2, 4.1 and 4.2 exactly.

Two streaming passes over a stack:

  pass 1  column-aggregated focus response over the graduation band, giving
          n_star(x): the best-focus frame for each image column. The statistic
          is a mean over >= 180 rows, not a per-pixel argmax (rule 4).
  pass 2  a column-wise best-focus INTENSITY image: column x is taken from the
          frame nearest n_star(x). Ticks are then located in that image.

Outputs `12-<tag>.json` with tick centroids, the Huber-IRLS projective fit
(A, B, C), a 1000-sample bootstrap over ticks, and the residual statistics that
the pre-registration's bars L1/L2/L3 and Z1/Z2/Z3 are read from.

Reads READ-ONLY from D:\\personal\\macro.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import rawpy
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")

# Registered configuration. Bands are ABSOLUTE quad-grid pixel coordinates.
CONFIG = {
    "flat": {
        "stack": "flat-on-ruler-cpl",
        # registered F-COMB = 0,1980,3514,364
        "x0": 0,
        "x1": 3512,
        "comb_y0": 1980,
        "comb_y1": 2344,
        "min_run": 8,
        "frac": 0.35,
    },
    "ang": {
        "stack": "highly-angled-ruler-mm-cpl",
        # strictly inside registered A-RULE = 1100,900,1900,900
        "x0": 1100,
        "x1": 3000,
        "comb_y0": 1620,
        "comb_y1": 1800,
        "min_run": 3,
        "frac": 0.35,
    },
}

BG_MEDIAN_QUAD = 601  # registered background median-filter width, quad px
LOCALMAX_HALFWIN = 200  # registered local-max half-window, quad px


def quad_green(path: pathlib.Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = int(np.max(raw.black_level_per_channel))
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    return 0.5 * (g1 + g2) - black


def peak_frame(curve: np.ndarray) -> tuple[float, float]:
    """Registered peak estimator: centroid over the contiguous above-half-max
    region around the discrete argmax. Returns (n_star, prominence)."""
    base = float(np.median(curve))
    c = curve - base
    j = int(np.argmax(c))
    if c[j] <= 0:
        return float("nan"), 0.0
    half = 0.5 * c[j]
    lo = j
    while lo > 0 and c[lo - 1] >= half:
        lo -= 1
    hi = j
    while hi < len(c) - 1 and c[hi + 1] >= half:
        hi += 1
    seg = c[lo : hi + 1]
    idx = np.arange(lo, hi + 1, dtype=np.float64)
    if seg.sum() <= 0:
        return float(j), 0.0
    return float((idx * seg).sum() / seg.sum()), float(c[j] / (np.std(c) + 1e-12))


def pass1_focus(cfg: dict, frames: list[pathlib.Path]):
    n = len(frames)
    w = cfg["x1"] - cfg["x0"]
    colprof = np.zeros((n, w), np.float32)
    t0 = time.time()
    for i, fp in enumerate(frames):
        plane = quad_green(fp)
        sub = np.ascontiguousarray(
            plane[cfg["comb_y0"] : cfg["comb_y1"], cfg["x0"] : cfg["x1"]]
        )
        del plane
        np.clip(sub, 1.0, None, out=sub)
        gx = ndimage.sobel(sub, axis=1)
        gy = ndimage.sobel(sub, axis=0)
        e = gx * gx + gy * gy
        lvl = ndimage.uniform_filter(sub, 33)
        colprof[i] = (ndimage.uniform_filter(e, 33) / (lvl * lvl)).mean(axis=0)
        if i % 60 == 0:
            print(f"    pass1 frame {i:3d}  {time.time() - t0:5.1f}s")
    nstar = np.zeros(w)
    prom = np.zeros(w)
    for x in range(w):
        nstar[x], prom[x] = peak_frame(colprof[:, x].astype(np.float64))
    return nstar, prom, colprof


def pass2_compose(
    cfg: dict, frames: list[pathlib.Path], nstar_s: np.ndarray
) -> np.ndarray:
    n = len(frames)
    h = cfg["comb_y1"] - cfg["comb_y0"]
    w = cfg["x1"] - cfg["x0"]
    want = np.clip(np.rint(nstar_s).astype(int), 0, n - 1)
    comp = np.zeros((h, w), np.float32)
    t0 = time.time()
    for i in range(n):
        cols = np.flatnonzero(want == i)
        if cols.size == 0:
            continue
        plane = quad_green(frames[i])
        sub = plane[cfg["comb_y0"] : cfg["comb_y1"], cfg["x0"] : cfg["x1"]]
        comp[:, cols] = sub[:, cols]
        del plane, sub
    print(f"    pass2 {time.time() - t0:5.1f}s, {len(np.unique(want))} frames used")
    return comp


def find_ticks(prof: np.ndarray, min_run: int, frac: float) -> list[dict]:
    """Registered localiser, pre-registration section 3.1."""
    bg = ndimage.median_filter(prof, size=BG_MEDIAN_QUAD, mode="nearest")
    dark = np.maximum(bg - prof, 0.0)
    locmax = ndimage.maximum_filter1d(dark, size=2 * LOCALMAX_HALFWIN + 1, mode="nearest")
    mask = dark > frac * locmax
    lab, nlab = ndimage.label(mask)
    ticks = []
    for s in ndimage.find_objects(lab):
        a, b = s[0].start, s[0].stop
        if b - a < min_run:
            continue
        if a == 0 or b == len(prof):
            continue
        pk = a + int(np.argmax(dark[a:b]))
        hm = 0.5 * dark[pk]
        lo = pk
        while lo > 0 and dark[lo - 1] >= hm:
            lo -= 1
        hi = pk
        while hi < len(prof) - 1 and dark[hi + 1] >= hm:
            hi += 1
        seg = dark[lo : hi + 1]
        idx = np.arange(lo, hi + 1, dtype=np.float64)
        if seg.sum() <= 0:
            continue
        ticks.append(
            {
                "x": float((idx * seg).sum() / seg.sum()),
                "run": [int(a), int(b)],
                "fwhm": float(hi - lo + 1),
                "depth": float(dark[pk]),
            }
        )
    return ticks


def fit_projective(k: np.ndarray, x: np.ndarray, seed_c: float = 0.0) -> dict:
    """x(k) = (A + B k)/(1 + C k) by Huber IRLS on the exact linearisation
    x = A + B k - C x k, weighted by 1/(1 + C k). Pre-registration section 4.2."""
    A = B = C = 0.0
    C = seed_c
    prev = np.array([np.inf, np.inf, np.inf])
    it = 0
    w = np.ones_like(x)
    for it in range(1, 201):
        v = 1.0 / np.maximum(1.0 + C * k, 1e-6)
        M = np.column_stack([np.ones_like(k), k, -x * k])
        ww = w * v
        sw = np.sqrt(ww)
        sol, *_ = np.linalg.lstsq(M * sw[:, None], x * sw, rcond=None)
        A, B, C = sol
        pred = (A + B * k) / (1.0 + C * k)
        r = x - pred
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-12
        c = 1.345 * s
        w = np.where(np.abs(r) <= c, 1.0, c / np.maximum(np.abs(r), 1e-12))
        cur = np.array([A, B, C])
        if np.all(np.abs(cur - prev) <= 1e-10 * np.maximum(np.abs(cur), 1e-12)):
            break
        prev = cur
    pred = (A + B * k) / (1.0 + C * k)
    r = x - pred
    return {
        "A": float(A),
        "B": float(B),
        "C": float(C),
        "iters": it,
        "converged": bool(it < 200),
        "resid_rms": float(np.sqrt(np.mean(r**2))),
        "resid_mad": float(1.4826 * np.median(np.abs(r - np.median(r)))),
        "resid_max": float(np.max(np.abs(r))),
        "n": int(len(k)),
    }


def fit_multi_init(k: np.ndarray, x: np.ndarray) -> dict:
    """Registered: three distinct initialisations must agree to 1e-6 relative."""
    fits = [fit_projective(k, x, c) for c in (0.0, -0.02, 0.02)]
    cs = np.array([f["C"] for f in fits])
    agree = float(np.max(np.abs(cs - cs[0])) / max(abs(cs[0]), 1e-12))
    out = dict(fits[0])
    out["init_agreement_rel"] = agree
    out["init_agree_ok"] = bool(agree < 1e-6)
    out["all_C"] = cs.tolist()
    return out


def bootstrap(k: np.ndarray, x: np.ndarray, n_boot: int = 1000, seed: int = 0x4D84B001):
    rng = np.random.default_rng(seed)
    m = len(k)
    keep = {"A": [], "B": [], "C": []}
    for _ in range(n_boot):
        j = rng.integers(0, m, m)
        if len(np.unique(k[j])) < 4:
            continue
        f = fit_projective(k[j], x[j])
        for key in keep:
            keep[key].append(f[key])
    return {key: (float(np.mean(v)), float(np.std(v))) for key, v in keep.items()}


def analyse(tag: str) -> dict:
    cfg = CONFIG[tag]
    frames = sorted((CORPUS / cfg["stack"]).glob("*.ARW"))
    print(f"  {cfg['stack']}: {len(frames)} frames")
    nstar, prom, colprof = pass1_focus(cfg, frames)

    # Registered smoothing of n_star(x) before it selects frames: a 101-px
    # running median, which cannot invent structure finer than a tick.
    nstar_s = ndimage.median_filter(np.nan_to_num(nstar, nan=0.0), size=101, mode="nearest")
    comp = pass2_compose(cfg, frames, nstar_s)

    prof = comp.mean(axis=0)
    ticks = find_ticks(prof, cfg["min_run"], cfg["frac"])
    xs = np.array([t["x"] for t in ticks])
    print(f"    ticks found: {len(xs)}")
    if len(xs) < 6:
        return {"tag": tag, "n_ticks": int(len(xs)), "fatal": "too few ticks"}

    gaps = np.diff(xs)
    kk = np.arange(len(xs), dtype=np.float64)
    fit = fit_multi_init(kk, xs)
    boot = bootstrap(kk, xs)
    lin = np.polyfit(kk, xs, 1)
    lin_r = xs - np.polyval(lin, kk)

    res = {
        "tag": tag,
        "stack": cfg["stack"],
        "config": cfg,
        "n_frames": len(frames),
        "n_ticks": int(len(xs)),
        "tick_x": xs.tolist(),
        "tick_fwhm": [t["fwhm"] for t in ticks],
        "tick_depth": [t["depth"] for t in ticks],
        "gaps": gaps.tolist(),
        "gap_median": float(np.median(gaps)),
        "gap_min": float(np.min(gaps)),
        "gap_max": float(np.max(gaps)),
        "gap_ratio_first_last": float(gaps[0] / gaps[-1]),
        "projective": fit,
        "bootstrap": boot,
        "similarity_resid_rms": float(np.sqrt(np.mean(lin_r**2))),
        "similarity_slope": float(lin[0]),
        "nstar_span": [float(np.nanmin(nstar_s)), float(np.nanmax(nstar_s))],
        "prom_median": float(np.median(prom)),
    }
    np.save(OUT / f"12-comp-{tag}.npy", comp)
    np.save(OUT / f"12-prof-{tag}.npy", prof)
    np.save(OUT / f"12-nstar-{tag}.npy", nstar)
    np.save(OUT / f"12-colprof-{tag}.npy", colprof)
    return res


def main(argv: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    tags = argv[1:] or ["flat", "ang"]
    for tag in tags:
        print(f"[{tag}]")
        r = analyse(tag)
        (OUT / f"12-{tag}.json").write_text(json.dumps(r, indent=1))
        print(f"    n_ticks {r.get('n_ticks')}  gap_med {r.get('gap_median')}")
        if "projective" in r:
            p = r["projective"]
            print(
                f"    A {p['A']:.3f}  B {p['B']:.4f}  C {p['C']:.6e}  "
                f"resid_rms {p['resid_rms']:.3f} px  conv {p['converged']} "
                f"init_ok {p['init_agree_ok']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

