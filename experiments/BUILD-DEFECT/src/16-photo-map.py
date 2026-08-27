"""Build the dust map from the PHOTOGRAPHS, because the flats' map is mis-placed.

Script 15 commissioned a local-null procedure in the region where all four
flats-nominated motes live (planted 2.5% disc RED at p = 0.0025; unplanted GREEN
at p = 0.9676 and 0.2893; a +2.5% BRIGHTENED disc moves the other way at
p = 1.0000 in every arm) and then scored the four nominated footprints in twelve
real subject stacks.  The result kills the flats-derived map:

  flats  396 quads at (3192, 109)  ->  +0.2001%, p = 0.9900   NOT THERE
  flats  127 quads at (3210, 136)  ->  +0.1571%, p = 0.9501   NOT THERE
  flats   66 quads at (3440,2281)  ->  +0.5398%, p = 1.0000   NOT THERE
  flats   29 quads at (3209, 116)  ->  -3.1952%, p = 0.0025   there

but re-locating each to the deepest 8-quad disc within +-40 quads finds:

  (3192, 109) -> (3202, 121)  -3.6303%, p = 0.0025   moved 16 quads
  (3210, 136) -> (3202, 120)  -3.6303%, p = 0.0025   moved 18 quads
  (3209, 116) -> (3201, 122)  -3.6272%, p = 0.0025   moved 10 quads
  (3440,2281) -> (3434,2305)  -8.2359%, p = 0.0025   moved 25 quads

Two facts follow.  First, the first three flats components are three
mis-registered fragments of ONE mote at quad (3202,121): a deep mote produces a
dark core and a bright high-pass ring, the ring fragments the component at a
-0.5% seed, and the fragments' centroids land on the ring instead of the core.
Second, the deepest defect on this sensor is at (3434,2305) at -8.24%, and the
flats put their component 25 quads away at a place the photographs read
+0.5398% at p = 1.0000 -- correcting there would brighten clean pixels beside an
uncorrected mote.

So the map is rebuilt here from the pooled twelve-subject photograph residual,
seeded at the re-located cores and grown in the photographs.  Every emitted
component must clear the local null at p <= 0.0025.  This is a TARGETED map: the
flats nominate, the photographs confirm, relocate and measure.  It is explicitly
NOT an exhaustive dust census, because scripts 10-12 established that a blind
search of these photographs cannot be commissioned at all -- every setting
sensitive enough to recover a 2.5% plant has a roll null returning 22 to 434
false components, and every setting with a clean null is blind to the plant.
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


CAMERA = "ILCE-7CM2"
SENSOR_W, SENSOR_H = 7032, 4688
COVERED_W, COVERED_H = 7028, 4688
APERTURE = 5.6
CORE_RADIUS = 8
GROW_FLOOR = 0.010
MIN_COMPONENT = 12
ANNULUS_IN, ANNULUS_OUT = 60, 400
N_LOCAL_NULL = 400
P_BAR = 0.0025
MAX_GAIN = 1.25
CORE_SEARCH = 40

NOMINATED = [(3192, 109), (3210, 136), (3440, 2281), (3209, 116)]


def disc(D, cy, cx, r):
    h, w = D.shape
    y0, y1 = max(0, cy - r), min(h, cy + r + 1)
    x0, x1 = max(0, cx - r), min(w, cx + r + 1)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    return D[y0:y1, x0:x1][(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r]


def local_null(D, cy, cx, r, rng, n=N_LOCAL_NULL):
    h, w = D.shape
    out, got = np.empty(n), 0
    while got < n:
        a = rng.uniform(0, 2 * np.pi)
        d = rng.uniform(ANNULUS_IN, ANNULUS_OUT)
        oy, ox = int(cy + d * np.sin(a)), int(cx + d * np.cos(a))
        if not (r < oy < h - r and r < ox < w - r):
            continue
        out[got] = np.median(disc(D, oy, ox, r))
        got += 1
    return out


def main():
    rng = np.random.default_rng(6180339887)
    z = np.load(OUT / "15-stacks.npz")
    S = z["plain"]
    k = S.shape[0]
    D = np.median(S, axis=0)
    h, w = D.shape
    log(f"pooled photograph residual: k={k}, {h}x{w}, rms {np.std(D) * 100:.4f}%")

    # Re-locate each nomination, then merge nominations that land on the same
    # core.  Three of the four collapse onto one mote, which is the point.
    cores = []
    for cx, cy in NOMINATED:
        best = (np.inf, cy, cx)
        for y in range(cy - CORE_SEARCH, cy + CORE_SEARCH + 1, 2):
            for x in range(cx - CORE_SEARCH, cx + CORE_SEARCH + 1, 2):
                v = float(np.median(disc(D, y, x, CORE_RADIUS)))
                if v < best[0]:
                    best = (v, y, x)
        v, ry, rx = best
        merged = next((c for c in cores if np.hypot(c["cx"] - rx, c["cy"] - ry) < 20), None)
        if merged:
            merged["from"].append([cx, cy])
            log(f"  ({cx},{cy}) -> ({rx},{ry}) {v * 100:+.4f}%  MERGED into ({merged['cx']},{merged['cy']})")
        else:
            cores.append(dict(cx=rx, cy=ry, core_pct=100 * v, **{"from": [[cx, cy]]}))
            log(f"  ({cx},{cy}) -> ({rx},{ry}) {v * 100:+.4f}%  new core")

    # Grow each core in the photographs, and gate on the local null.
    lab, _ = ndimage.label(D <= -GROW_FLOOR, structure=np.ones((3, 3)))
    emitted, refused = [], []
    counts = dict(nominated=len(NOMINATED), cores=len(cores), too_small=0, failed_null=0, kept=0)
    for c in cores:
        i = lab[c["cy"], c["cx"]]
        sel = (lab == i) if i else np.zeros_like(lab, bool)
        area = int(sel.sum())
        null = local_null(D, c["cy"], c["cx"], CORE_RADIUS, rng)
        below = int((null <= c["core_pct"] / 100).sum())
        p = (below + 1) / (N_LOCAL_NULL + 1)
        c.update(area=area, p_value=p, null_p1_pct=100 * float(np.percentile(null, 1)))
        if area < MIN_COMPONENT:
            counts["too_small"] += 1
            refused.append(dict(**{kk: c[kk] for kk in ("cx", "cy", "area", "p_value")}, why="too small"))
            log(f"  core ({c['cx']},{c['cy']}): area {area} < {MIN_COMPONENT}, REFUSED")
            continue
        if p > P_BAR:
            counts["failed_null"] += 1
            refused.append(dict(**{kk: c[kk] for kk in ("cx", "cy", "area", "p_value")}, why="local null"))
            log(f"  core ({c['cx']},{c['cy']}): p={p:.4f} > {P_BAR}, REFUSED")
            continue
        counts["kept"] += 1
        ys, xs = np.nonzero(sel)
        gains = np.clip(1.0 / (1.0 + D[ys, xs]), 1.0, MAX_GAIN)
        emitted.append(dict(core=c, ys=ys, xs=xs, gains=gains))
        log(
            f"  core ({c['cx']},{c['cy']}): area {area}, core {c['core_pct']:+.4f}%, "
            f"p={p:.4f}, gain median {np.median(gains):.6f} max {gains.max():.6f}  KEPT"
        )

    assert counts["too_small"] + counts["failed_null"] + counts["kept"] == counts["cores"]
    n_quads = sum(len(e["ys"]) for e in emitted)
    log(f"partition: {counts}; {n_quads} dust quads emitted")

    hot_lines = [
        ln
        for ln in (OUT / "defect-map-ILCE-7CM2.txt").read_text(encoding="utf-8").splitlines()
        if ln.startswith(("hot ", "h "))
    ]

    L = [
        "strehl-defect-map 1",
        f"camera {CAMERA}",
        f"sensor {SENSOR_W} {SENSOR_H}",
        f"covered {COVERED_W} {COVERED_H}",
        f"aperture {APERTURE}",
        f"# built {time.strftime('%Y-%m-%dT%H:%M:%S')} by experiments/BUILD-DEFECT/src/16-photo-map.py",
        "# hot: carried verbatim from defect-map-ILCE-7CM2.txt (242 darks, 11 ISO",
        "# hot: groups, 6-sigma neighbour excess, recurrence >= 6/11). Ships OFF:",
        "# hot: M101 measured the arm immaterial on this body.",
        "# dust: DERIVED FROM PHOTOGRAPHS, not from flat fields. 12 real subject",
        f"# dust: stacks x 8 frames, pooled median of the per-frame high-pass residual.",
        "# dust: The flat-field map (defect-map-ILCE-7CM2.txt) is MIS-REGISTERED:",
        "# dust: three of its four components are fragments of one mote and its",
        "# dust: deepest component sits 25 quads from the real core, at a place",
        "# dust: the photographs read +0.5398% at p = 1.0000. DO NOT SHIP IT.",
        "# dust: procedure commissioned in this region of the frame -- a planted",
        "# dust: 2.5% disc reads p = 0.0025, unplanted p = 0.9676 / 0.2893, and a",
        "# dust: BRIGHTENED +2.5% disc moves the other way at p = 1.0000.",
        "# dust: NOT commissioned mid-frame (planted 2.5% reads p = 0.1197 there),",
        "# dust: so this is a TARGETED map and NOT an exhaustive dust census.",
        f"# dust: every component clears a 400-draw local null at p <= {P_BAR}.",
        f"# geometry: rawler active {SENSOR_W}x{SENSOR_H}; rawpy visible {COVERED_W}x{COVERED_H}.",
        "# geometry: the last 4 sensor columns are UNMEASURED, not clean.",
    ]
    for e in emitted:
        c = e["core"]
        L.append(
            f"# mote: {c['area']} quads at quad ({c['cx']},{c['cy']}), core "
            f"{c['core_pct']:+.4f}%, p={c['p_value']:.4f}, nominated by flats at "
            + " ".join(f"({a},{b})" for a, b in c["from"])
        )
    L += hot_lines
    L.append(f"dust {n_quads}")
    for e in emitted:
        for y, x, g in zip(e["ys"], e["xs"], e["gains"]):
            L.append(f"d {x} {y} {g:.6f}")

    L.append("end")
    path = OUT / "defect-map-ILCE-7CM2-photo.txt"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    log(f"wrote {path.name} ({path.stat().st_size / 1e6:.3f} MB)")

    (DATA / "16-photo-map.json").write_text(
        json.dumps(
            dict(
                k=k,
                counts=counts,
                dust_quads=n_quads,
                emitted=[
                    dict(
                        quad=[e["core"]["cx"], e["core"]["cy"]],
                        area=e["core"]["area"],
                        core_pct=e["core"]["core_pct"],
                        p_value=e["core"]["p_value"],
                        gain_median=float(np.median(e["gains"])),
                        gain_max=float(e["gains"].max()),
                        nominated_by=e["core"]["from"],
                    )
                    for e in emitted
                ],
                refused=refused,
            ),
            indent=1,
        ),
        encoding="utf-8",
    )
    log("wrote data/16-photo-map.json")


if __name__ == "__main__":
    main()
