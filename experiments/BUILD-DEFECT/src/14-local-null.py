"""Score the footprints against a LOCAL null, and find the true cores.

Script 13's control tile at quad (1600,1000) -- a location with no nominated
mote -- is full of structure, including a core at or below -4%.  That is a
confound I have to kill rather than argue away: the four nominated motes sit at
x = 3192..3440, near the right edge, where a macro subject's out-of-focus
background is smooth in every one of the twelve stacks, while the control sits
mid-frame where subjects have detail.  A whole-sensor location null (script 09)
draws its footprints from both kinds of place, so it cannot tell "this is dust"
from "this corner of the frame is quiet".

The correct control is LOCAL: draw the null footprints from an annulus around
the candidate itself, so the null sees the same subject smoothness the candidate
does and the only thing left that distinguishes them is the sensor.

Script 13 also showed the flats' components are mis-centred.  The 396-quad
component reads +0.2926% over its own footprint but -3.6668% at its deepest, and
its tile shows one small compact blob; the 127-quad component reads -0.3009% at
its deepest and its tile shows the SAME blob, outside its own mask.  Three of
the four flats components are overlapping mis-registered attempts at one real
mote near quad (3200,113).  So this also re-locates the core by searching the
neighbourhood of each nominated footprint for the actual minimum, and reports
where the flats put it against where the photographs put it.

Commissioning rides along: the same local-null procedure is run on a KNOWN
planted 2.5% disc and on a KNOWN-CLEAN location, and both must read the right
way or the procedure is not measuring what it claims.
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


ANNULUS_IN, ANNULUS_OUT = 60, 400
N_LOCAL_NULL = 400
CORE_SEARCH = 40  # quads either way when re-locating a core
CORE_RADIUS = 8  # the disc that defines "the core", in quads
PLANT_AT = (1200, 1400)
CLEAN_AT = (700, 2600)


def disc(D, cy, cx, r):
    h, w = D.shape
    y0, y1 = max(0, cy - r), min(h, cy + r + 1)
    x0, x1 = max(0, cx - r), min(w, cx + r + 1)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    return D[y0:y1, x0:x1][m]


def local_null(D, cy, cx, r, rng, n=N_LOCAL_NULL):
    """Median of an r-disc at n random offsets in an annulus around (cy,cx)."""
    h, w = D.shape
    out = np.empty(n)
    got = 0
    while got < n:
        a = rng.uniform(0, 2 * np.pi)
        d = rng.uniform(ANNULUS_IN, ANNULUS_OUT)
        oy, ox = int(cy + d * np.sin(a)), int(cx + d * np.cos(a))
        if not (r < oy < h - r and r < ox < w - r):
            continue
        out[got] = np.median(disc(D, oy, ox, r))
        got += 1
    return out


def relocate(D, cy, cx, span=CORE_SEARCH, r=CORE_RADIUS):
    """The deepest r-disc within +-span quads of (cy,cx)."""
    best = (np.inf, cy, cx)
    for y in range(cy - span, cy + span + 1, 2):
        for x in range(cx - span, cx + span + 1, 2):
            v = float(np.median(disc(D, y, x, r)))
            if v < best[0]:
                best = (v, y, x)
    return best


def score(D, cy, cx, rng, label, r=CORE_RADIUS):
    real = float(np.median(disc(D, cy, cx, r)))
    null = local_null(D, cy, cx, r, rng)
    below = int((null <= real).sum())
    p = (below + 1) / (N_LOCAL_NULL + 1)
    log(
        f"  {label:34s} core {real * 100:+.4f}%  local null median "
        f"{np.median(null) * 100:+.4f}% p1 {np.percentile(null, 1) * 100:+.4f}%  "
        f"{below:3d}/{N_LOCAL_NULL} at least as deep  p={p:.4f}"
    )
    return dict(
        quad=[cx, cy],
        core_pct=100 * real,
        null_median_pct=100 * float(np.median(null)),
        null_p1_pct=100 * float(np.percentile(null, 1)),
        n_at_least_as_deep=below,
        p_value=p,
    )


def main():
    rng = np.random.default_rng(577215664)
    S = np.load(OUT / "12-subject-stack.npy")
    P = np.load(OUT / "12-plant-stack.npy")
    D = np.median(S, axis=0)
    Dp = np.median(P, axis=0)
    k = S.shape[0]
    log(f"k={k}, pooled rms {np.std(D) * 100:.4f}%")

    # -- commissioning first, so the procedure is trusted before it is used ---
    log("COMMISSIONING the local-null procedure:")
    arm_plant = score(Dp, PLANT_AT[0], PLANT_AT[1], rng, "PLANTED 2.5% disc (must be RED)")
    arm_unplanted = score(D, PLANT_AT[0], PLANT_AT[1], rng, "same place, UNPLANTED (must be GREEN)")
    arm_clean = score(D, CLEAN_AT[0], CLEAN_AT[1], rng, "arbitrary clean spot (must be GREEN)")
    # An improvement arm: brighten a disc by 2.5% and require the score to move
    # the OTHER way.  A metric that charges for a defect but also charges for a
    # repair is perverse, and only this arm can see that.
    h, w = D.shape
    yy, xx = np.ogrid[:h, :w]
    bright = np.where((yy - PLANT_AT[0]) ** 2 + (xx - PLANT_AT[1]) ** 2 <= 121, 0.025, 0.0)
    arm_bright = score(D + bright, PLANT_AT[0], PLANT_AT[1], rng, "same place, BRIGHTENED +2.5%")
    ok = (
        arm_plant["p_value"] <= 0.01
        and arm_unplanted["p_value"] > 0.05
        and arm_clean["p_value"] > 0.05
        and arm_bright["core_pct"] > arm_unplanted["core_pct"]
    )
    log(f"  commissioning: {'PASS' if ok else 'FAIL'}")
    if not ok:
        log("  REFUSING to report candidates: the procedure is not commissioned.")
        (DATA / "14-local-null.json").write_text(
            json.dumps(
                dict(
                    commissioned=False,
                    plant=arm_plant,
                    unplanted=arm_unplanted,
                    clean=arm_clean,
                    brightened=arm_bright,
                ),
                indent=1,
            ),
            encoding="utf-8",
        )
        return

    # -- the four flats-nominated components ---------------------------------
    txt = (OUT / "defect-map-ILCE-7CM2.txt").read_text(encoding="utf-8")
    m = np.zeros((h, w), bool)
    for line in txt.splitlines():
        if line.startswith("d "):
            _, px, py, _g = line.split()
            m[int(py), int(px)] = True
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    comps = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        comps.append((int(ys.size), int(round(xs.mean())), int(round(ys.mean()))))
    comps.sort(key=lambda c: -c[0])

    log("")
    log("THE FOUR FLATS-NOMINATED COMPONENTS, at the centroid the flats chose:")
    at_flats = [score(D, cy, cx, rng, f"flats {a:4d} quads ({cx},{cy})") for a, cx, cy in comps]

    log("")
    log("RE-LOCATED: the deepest 8-quad disc within +-40 quads of each centroid:")
    relocated = []
    for a, cx, cy in comps:
        v, ry, rx = relocate(D, cy, cx)
        s = score(D, ry, rx, rng, f"flats {a:4d} -> ({rx},{ry})")
        s["moved_by_quads"] = int(round(np.hypot(rx - cx, ry - cy)))
        s["from"] = [cx, cy]
        s["flats_area"] = a
        relocated.append(s)
        log(f"      moved {s['moved_by_quads']} quads from the flats centroid")

    result = dict(
        commissioned=True,
        k=k,
        plant=arm_plant,
        unplanted=arm_unplanted,
        clean=arm_clean,
        brightened=arm_bright,
        at_flats_centroid=at_flats,
        relocated=relocated,
    )
    (DATA / "14-local-null.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    log("")
    log("wrote data/14-local-null.json")


if __name__ == "__main__":
    main()
