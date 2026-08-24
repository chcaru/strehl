"""E1/E2 -- Instrument A on RAW CFA planes of a SINGLE frame.

E1 (bar B1): is the colour fringing already present in one frame? If it is,
stacking is not its cause.
E2 (bar B2): does the per-channel edge displacement grow with image radius, as
lateral chromatic aberration must?

Every ROI is measured at the frame where ITS OWN green content is sharpest, so
the fit is never asked to place an edge that is defocused.
"""

import sys, os, json, time
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import decode, frames, esf_all_planes, summarise, dump, OUT
from edges import find_edge_rois, spread_by_radius, green_of

SIZE = 96          # sensel; 48 plane px per side
NBINS, PER_BIN = 8, 5


def green_focus(roi):
    g = green_of(roi).astype(np.float64)
    gy, gx = np.gradient(g)
    return float(np.mean(gx * gx + gy * gy))


def run_stack(stack, scan_frames=14, max_rois=40, min_contrast=1500.0, verbose=True):
    fs = frames(stack)
    n = len(fs)
    idx = np.unique(np.linspace(0, n - 1, scan_frames).astype(int))

    # ---- pass 1: pool candidate edge windows over frames spread through the stack
    pool = {}
    for k in idx:
        cfa, _, _ = decode(fs[k])
        H, W = cfa.shape
        for c in find_edge_rois(cfa, size=SIZE, stride=SIZE * 2, top=250,
                                min_contrast=min_contrast):
            key = (c["x0"], c["y0"])
            if key not in pool or c["score"] > pool[key]["score"]:
                pool[key] = c
    cands = sorted(pool.values(), key=lambda d: -d["score"])
    cx, cy = W / 2.0, H / 2.0
    sel = spread_by_radius(cands, cx, cy, nbins=NBINS, per_bin=PER_BIN)[:max_rois]
    if verbose:
        print(f"  {stack}: {len(cands)} candidates -> {len(sel)} ROIs "
              f"spread over {NBINS} radius bins")
    if not sel:
        return None

    # ---- pass 2: through-focus green response of every ROI, over ALL frames
    F = np.zeros((n, len(sel)))
    for k in range(n):
        cfa, _, _ = decode(fs[k])
        for j, c in enumerate(sel):
            F[k, j] = green_focus(cfa[c["y0"]:c["y0"] + SIZE, c["x0"]:c["x0"] + SIZE])
    best = F.argmax(axis=0)

    # ---- pass 3: fit Instrument A at each ROI's own best frame
    rows = []
    for kf in sorted(set(best.tolist())):
        cfa, _, _ = decode(fs[kf])
        for j, c in enumerate(sel):
            if best[j] != kf:
                continue
            roi = cfa[c["y0"]:c["y0"] + SIZE, c["x0"]:c["x0"] + SIZE]
            e = esf_all_planes(roi, x0=c["x0"], y0=c["y0"])
            if e is None:
                continue
            s = summarise(e)
            # radial unit vector at this ROI, and the edge normal
            rx, ry = c["rx"], c["ry"]
            r = float(np.hypot(rx, ry))
            u = np.array([rx, ry]) / max(r, 1e-9)
            nvec = np.array(s["normal"])
            cosang = float(abs(np.dot(u, nvec)))   # 1 = edge normal is radial
            rows.append({
                "stack": stack, "frame": int(kf), "x0": c["x0"], "y0": c["y0"],
                "radius": r, "rx": rx, "ry": ry, "cos_radial": cosang,
                "contrast": c["contrast"], "coherence": c["coherence"],
                "straight": c["straight"],
                "dR": s["dR"], "dB": s["dB"], "dRB": s["dRB"],
                "null_dG": s["null_dG"],
                "wR": s["wR"], "wB": s["wB"], "wG": s["wG"],
                "null_wG": s["null_wG"],
                "w_abs": s["w_abs"], "amp": s["amp"], "rms": s["rms"],
                "normal": s["normal"],
            })
    return rows


def report(rows, label):
    if not rows:
        print(f"{label}: no rows"); return {}
    a = {k: np.array([r[k] for r in rows], dtype=float)
         for k in ("dR", "dB", "dRB", "null_dG", "wR", "wB", "null_wG",
                   "radius", "cos_radial", "contrast")}
    # signed RADIAL component: project the per-channel displacement, which is
    # measured along the edge normal, onto the outward radial direction.
    sgn = np.sign([np.dot(np.array(r["normal"]), np.array([r["rx"], r["ry"]]))
                   for r in rows])
    rad_R, rad_B = a["dR"] * sgn, a["dB"] * sgn
    out = {
        "n": len(rows),
        "median_dR": float(np.median(a["dR"])), "median_dB": float(np.median(a["dB"])),
        "median_null_dG": float(np.median(a["null_dG"])),
        "mad_dR": float(np.median(np.abs(a["dR"] - np.median(a["dR"])))),
        "mad_null": float(np.median(np.abs(a["null_dG"] - np.median(a["null_dG"])))),
        "median_absdR": float(np.median(np.abs(a["dR"]))),
        "median_absdB": float(np.median(np.abs(a["dB"]))),
        "median_absnull": float(np.median(np.abs(a["null_dG"]))),
        "median_radial_R": float(np.median(rad_R)),
        "median_radial_B": float(np.median(rad_B)),
        "median_wR": float(np.median(a["wR"])), "median_wB": float(np.median(a["wB"])),
        "median_null_wG": float(np.median(a["null_wG"])),
    }
    print(f"\n{label}  n={out['n']}")
    print(f"  |dR| median {out['median_absdR']:.4f}   |dB| median {out['median_absdB']:.4f}"
          f"   |G1-G2 NULL| median {out['median_absnull']:.4f}  sensel")
    print(f"  signed radial: R {out['median_radial_R']:+.4f}  B {out['median_radial_B']:+.4f}")
    print(f"  width: wR {out['median_wR']:+.4f}  wB {out['median_wB']:+.4f}  "
          f"null {out['median_null_wG']:+.4f}")
    return out


if __name__ == "__main__":
    stacks = sys.argv[1:] or ["tweezers-cpl", "leaf-2-cpl", "bee-3-cpl", "wrapped-text-1"]
    allrows, summ = [], {}
    for s in stacks:
        t = time.time()
        print(f"== {s} ==")
        rows = run_stack(s)
        if rows:
            allrows.extend(rows)
            summ[s] = report(rows, s)
        print(f"  ({time.time()-t:.1f}s)")
    dump("e1_raw_edges", {"rows": allrows, "summary": summ})
