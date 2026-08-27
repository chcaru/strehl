"""05-border-and-recurrence.py -- two things 04 got wrong, measured.

1. THE BORDER IS NOT `hp_radius`.  The high-pass is THREE passes of a box of
   half-width 30, so its support half-width is 90, not 30.  Any quad within 90
   of an edge has a smoothed denominator fitted partly to a reflection of
   itself.  04 excluded 31 and kept a component 45 quads from the bottom edge.
   Measure the contaminated width instead of guessing it.

2. THE RECURRENCE SEED MAY BE THE WRONG INSTRUMENT.  02 saw dozens of motes in
   the band-passed median; 04 kept ONE component.  Find out which bar removed
   them, and whether the removal is right.

Nothing here writes a map.  It decides two numbers that 06 will use.
"""

import json
import pathlib
import time

import numpy as np
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


HP_RADIUS, BP_RADIUS = 30, 2
SEED_DEPTH, RECURRENCE = 0.010, 15
FLOOR_DEPTH, MIN_COMPONENT = 0.0075, 25
CROSS = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])


def main():
    med = np.load(OUT / "dust-median-residual.npy")
    band = np.load(OUT / "dust-band.npy")
    seen = np.load(OUT / "dust-seen.npy")
    h, w = med.shape
    log(f"{w} x {h} quads")

    # ---- 1. how far in does the edge artefact reach? ---------------------
    # The residual of a CLEAN field is zero everywhere in the interior.  Near
    # an edge, edge-replication biases the denominator, so the median residual
    # over a whole ring at distance d is a direct readout of the artefact:
    # real dust is sparse and cannot move a ring median.
    yy, xx = np.mgrid[0:h, 0:w]
    dist = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    log("ring median of the median residual, by distance from the nearest edge")
    prof = []
    for d in [0, 2, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 200, 300, 500]:
        m = dist == d
        v = float(np.median(med[m]) * 100)
        q = float(np.percentile(med[m], 1) * 100)
        frac = float((seen[m] >= RECURRENCE).mean() * 100)
        prof.append(dict(d=d, ring_median_pct=v, ring_p1_pct=q, recurrent_pct=frac))
        log(f"    d={d:4d}  ring median {v:+7.4f}%   1st pct {q:+7.3f}%   "
            f"recurrent {frac:6.2f}%")

    # the border is where the ring median falls inside the noise of the deep
    # interior, and stays there.
    deep_rings = [p["ring_median_pct"] for p in prof if p["d"] >= 300]
    interior_level = float(np.mean(deep_rings))
    interior_sd = float(np.std([p["ring_median_pct"] for p in prof if p["d"] >= 200]))
    bar = abs(interior_level) + 5 * max(interior_sd, 1e-4)
    border = None
    for p in prof:
        if abs(p["ring_median_pct"] - interior_level) <= bar and p["d"] >= 30:
            border = p["d"]
            break
    log(f"    interior level {interior_level:+.5f}% (sd {interior_sd:.5f}); "
        f"first ring within 5sd at d={border}")

    # ---- 2. which bar removed the motes? ---------------------------------
    for b in (31, 60, 90, 120, 150):
        inside = np.zeros((h, w), bool)
        inside[b:h - b, b:w - b] = True
        rec = (seen >= RECURRENCE) & inside
        dep = band <= -FLOOR_DEPTH
        both = rec & dep & inside
        depth_only = dep & inside
        lab1, n1 = ndimage.label(both, structure=CROSS)
        s1 = np.bincount(lab1.ravel())
        k1 = [i for i in range(1, n1 + 1) if s1[i] >= MIN_COMPONENT]
        lab2, n2 = ndimage.label(depth_only, structure=CROSS)
        s2 = np.bincount(lab2.ravel())
        k2 = [i for i in range(1, n2 + 1) if s2[i] >= MIN_COMPONENT]
        log(f"    border {b:4d}: recurrent {int(rec.sum()):7d}  "
            f"deep {int(depth_only.sum()):7d}  both {int(both.sum()):7d}  |  "
            f"components(both) {len(k1):3d}/{n1:4d}  "
            f"components(depth only) {len(k2):3d}/{n2:4d}")

    # ---- 3. the depth-only components at the measured border, examined ----
    b = 90
    inside = np.zeros((h, w), bool)
    inside[b:h - b, b:w - b] = True
    dep = (band <= -FLOOR_DEPTH) & inside
    lab, n = ndimage.label(dep, structure=CROSS)
    sizes = np.bincount(lab.ravel())
    keep = [i for i in range(1, n + 1) if sizes[i] >= MIN_COMPONENT]
    log(f"depth-only components at border {b}: {len(keep)} of {n} pass the "
        f"{MIN_COMPONENT}-quad floor")
    rows = []
    for cid in sorted(keep, key=lambda i: -sizes[i]):
        m = lab == cid
        ys, xs = np.nonzero(m)
        rows.append(dict(
            area=int(sizes[cid]), cx=float(xs.mean()), cy=float(ys.mean()),
            depth_med_pct=float(np.median(med[m]) * 100),
            depth_min_pct=float(med[m].min() * 100),
            seen_med=float(np.median(seen[m])),
            seen_max=int(seen[m].max()),
            edge_dist=int(dist[m].min()),
        ))
    for r in rows[:25]:
        log(f"    area {r['area']:5d} at ({r['cx']:6.0f},{r['cy']:6.0f})  "
            f"edge {r['edge_dist']:4d}  median {r['depth_med_pct']:+6.2f}%  "
            f"worst {r['depth_min_pct']:+6.2f}%  seen med {r['seen_med']:4.1f} "
            f"max {r['seen_max']:2d}")
    log(f"    ... {len(rows)} components total; "
        f"areas {[r['area'] for r in rows[:8]]}")
    log(f"    seen-median distribution over components: "
        f"{np.percentile([r['seen_med'] for r in rows], [0, 25, 50, 75, 100]).tolist()}")

    (DATA / "05-border.json").write_text(json.dumps(
        dict(profile=prof, interior_level=interior_level,
             interior_sd=interior_sd, chosen_border=border,
             depth_only_components=rows), indent=1), encoding="utf-8")
    log("wrote data/05-border.json")


if __name__ == "__main__":
    main()
