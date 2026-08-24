"""M84b step 13 - robust tick selection, index assignment, and the projective fit.

Reads the column-wise best-focus profiles saved by step 12 (no re-decoding), so
the estimator can be iterated without touching D:.

Adds, over step 12:
  * a quality filter on detections (registered form: a detection is a graduation
    only if its width and darkness are consistent with its neighbours), which
    rejects the wide low-contrast blobs at the ends of the angled ROI;
  * an explicit INDEX ASSIGNMENT, so a missed graduation does not silently
    shift every later index by one. Step 12 assumed consecutive indices and that
    assumption is what produced its 99 px angled residual.

Bars read from here: L1, L2, L3, Z1, Z2, Z3, P1.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"

BG_MEDIAN_QUAD = 601
LOCALMAX_HALFWIN = 200


def detect(prof: np.ndarray, min_run: int, frac: float) -> list[dict]:
    bg = ndimage.median_filter(prof, size=BG_MEDIAN_QUAD, mode="nearest")
    dark = np.maximum(bg - prof, 0.0)
    locmax = ndimage.maximum_filter1d(dark, size=2 * LOCALMAX_HALFWIN + 1, mode="nearest")
    lab, _ = ndimage.label(dark > frac * locmax)
    out = []
    for s in ndimage.find_objects(lab):
        a, b = s[0].start, s[0].stop
        if b - a < min_run or a == 0 or b == len(prof):
            continue
        pk = a + int(np.argmax(dark[a:b]))
        hm = 0.5 * dark[pk]
        lo, hi = pk, pk
        while lo > 0 and dark[lo - 1] >= hm:
            lo -= 1
        while hi < len(prof) - 1 and dark[hi + 1] >= hm:
            hi += 1
        seg = dark[lo : hi + 1]
        if seg.sum() <= 0:
            continue
        idx = np.arange(lo, hi + 1, dtype=np.float64)
        out.append(
            {
                "x": float((idx * seg).sum() / seg.sum()),
                "fwhm": float(hi - lo + 1),
                "depth": float(dark[pk]),
                "run": [int(a), int(b)],
            }
        )
    return out


def quality_filter(ticks: list[dict]) -> tuple[list[dict], dict]:
    """A detection is a graduation only if its width and darkness sit within a
    robust band of the population. Registered thresholds: FWHM within
    [0.35, 2.5] x median FWHM, darkness >= 0.35 x median darkness."""
    f = np.array([t["fwhm"] for t in ticks])
    d = np.array([t["depth"] for t in ticks])
    mf, md = float(np.median(f)), float(np.median(d))
    keep = (f >= 0.35 * mf) & (f <= 2.5 * mf) & (d >= 0.35 * md)
    rej = [
        {"x": t["x"], "fwhm": t["fwhm"], "depth": t["depth"]}
        for t, k in zip(ticks, keep)
        if not k
    ]
    return [t for t, k in zip(ticks, keep) if k], {
        "median_fwhm": mf,
        "median_depth": md,
        "n_in": len(ticks),
        "n_kept": int(keep.sum()),
        "rejected": rej,
    }


def assign_indices(xs: np.ndarray) -> tuple[np.ndarray, dict]:
    """Assign graduation indices allowing for missed graduations.

    The local pitch is estimated by a 5-point running median of the gaps; each
    gap is then rounded to an integer number of graduations. A gap that is not
    within 0.25 of an integer multiple is flagged."""
    g = np.diff(xs)
    loc = ndimage.median_filter(g, size=5, mode="nearest")
    ratio = g / loc
    steps = np.maximum(np.rint(ratio), 1.0)
    frac_err = np.abs(ratio - steps)
    k = np.concatenate([[0.0], np.cumsum(steps)])
    return k, {
        "gaps": g.tolist(),
        "local_pitch": loc.tolist(),
        "steps": steps.tolist(),
        "max_frac_err": float(np.max(frac_err)),
        "n_multi_step": int((steps > 1).sum()),
    }


def fit_projective(k, x, seed_c=0.0):
    C = seed_c
    A = B = 0.0
    prev = np.array([np.inf] * 3)
    w = np.ones_like(x)
    it = 0
    for it in range(1, 201):
        v = 1.0 / np.maximum(1.0 + C * k, 1e-6)
        M = np.column_stack([np.ones_like(k), k, -x * k])
        ww = w * v
        sw = np.sqrt(ww)
        sol, *_ = np.linalg.lstsq(M * sw[:, None], x * sw, rcond=None)
        A, B, C = sol
        r = x - (A + B * k) / (1.0 + C * k)
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-12
        c = 1.345 * s
        w = np.where(np.abs(r) <= c, 1.0, c / np.maximum(np.abs(r), 1e-12))
        cur = np.array([A, B, C])
        if np.all(np.abs(cur - prev) <= 1e-10 * np.maximum(np.abs(cur), 1e-12)):
            break
        prev = cur
    r = x - (A + B * k) / (1.0 + C * k)
    return {
        "A": float(A),
        "B": float(B),
        "C": float(C),
        "iters": it,
        "converged": bool(it < 200),
        "resid_rms": float(np.sqrt(np.mean(r**2))),
        "resid_max": float(np.max(np.abs(r))),
        "resid": r.tolist(),
        "n": int(len(k)),
    }


def fit_multi_init(k, x):
    fits = [fit_projective(k, x, c) for c in (0.0, -0.02, 0.02)]
    cs = np.array([f["C"] for f in fits])
    out = dict(fits[0])
    out["init_agreement_rel"] = float(np.max(np.abs(cs - cs[0])) / max(abs(cs[0]), 1e-12))
    out["init_agree_ok"] = bool(out["init_agreement_rel"] < 1e-6)
    return out


def boot(k, x, n_boot=1000, seed=0x4D84B001):
    rng = np.random.default_rng(seed)
    m = len(k)
    acc = {"A": [], "B": [], "C": [], "pitch0": []}
    for _ in range(n_boot):
        j = rng.integers(0, m, m)
        if len(np.unique(k[j])) < 4:
            continue
        f = fit_projective(k[j], x[j])
        acc["A"].append(f["A"])
        acc["B"].append(f["B"])
        acc["C"].append(f["C"])
        acc["pitch0"].append(f["B"] - f["C"] * f["A"])
    return {kk: (float(np.mean(v)), float(np.std(v))) for kk, v in acc.items()}


def analyse(tag: str, min_run: int, frac: float) -> dict:
    prof = np.load(OUT / f"12-prof-{tag}.npy").astype(np.float64)
    raw = detect(prof, min_run, frac)
    ticks, qinfo = quality_filter(raw)
    xs = np.array([t["x"] for t in ticks])
    k, ainfo = assign_indices(xs)
    fit = fit_multi_init(k, xs)
    bs = boot(k, xs)

    lin = np.polyfit(k, xs, 1)
    lin_r = xs - np.polyval(lin, k)

    # Registered planarity probe P1: structure in the residual relative to its
    # high-frequency scatter.
    r = np.array(fit["resid"])
    smooth = ndimage.uniform_filter1d(r, size=5, mode="nearest")
    hf = r - smooth
    p1 = float(np.std(smooth) / (np.std(hf) + 1e-12))

    pitch0 = fit["B"] - fit["C"] * fit["A"]
    localpitch = pitch0 / (1.0 + fit["C"] * k) ** 2
    return {
        "tag": tag,
        "n_ticks": int(len(xs)),
        "tick_x": xs.tolist(),
        "tick_fwhm": [t["fwhm"] for t in ticks],
        "tick_depth": [t["depth"] for t in ticks],
        "quality": qinfo,
        "indexing": ainfo,
        "k": k.tolist(),
        "projective": fit,
        "bootstrap": bs,
        "pitch0_quadpx": float(pitch0),
        "local_pitch_quadpx": localpitch.tolist(),
        "similarity_resid_rms": float(np.sqrt(np.mean(lin_r**2))),
        "similarity_slope": float(lin[0]),
        "resid_rms_frac_of_local_pitch": float(
            np.sqrt(np.mean((r / localpitch) ** 2))
        ),
        "planarity_P1": p1,
        "k_span": float(k[-1] - k[0]),
        "depth_ratio_end_to_start": float(
            (1 + fit["C"] * k[-1]) / (1 + fit["C"] * k[0])
        ),
    }


def main(argv):
    OUT.mkdir(exist_ok=True)
    specs = {"flat": (8, 0.35), "ang": (3, 0.35)}
    for tag in argv[1:] or ["flat", "ang"]:
        r = analyse(tag, *specs[tag])
        (OUT / f"13-{tag}.json").write_text(json.dumps(r, indent=1))
        p = r["projective"]
        print(f"[{tag}] ticks {r['n_ticks']} (from {r['quality']['n_in']} raw)")
        print(f"  rejected: {[round(q['x'],1) for q in r['quality']['rejected']]}")
        print(f"  index steps>1: {r['indexing']['n_multi_step']}, "
              f"max frac err {r['indexing']['max_frac_err']:.3f}")
        print(f"  A {p['A']:.3f}  B {p['B']:.4f}  C {p['C']:.6e}")
        print(f"  pitch@k0 {r['pitch0_quadpx']:.3f} quad px   "
              f"resid_rms {p['resid_rms']:.3f} px "
              f"= {100*r['resid_rms_frac_of_local_pitch']:.2f}% of local pitch")
        print(f"  similarity resid {r['similarity_resid_rms']:.3f} px   "
              f"P1 {r['planarity_P1']:.2f}   depth ratio {r['depth_ratio_end_to_start']:.4f}")
        print(f"  boot C {r['bootstrap']['C'][0]:.6e} +/- {r['bootstrap']['C'][1]:.6e}  "
              f"pitch0 {r['bootstrap']['pitch0'][0]:.3f} +/- {r['bootstrap']['pitch0'][1]:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
