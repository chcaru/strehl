"""Phase A/B analysis -- select background patches by measurement, then decide
whether the drift is a scalar per frame or a field, and whether the alignment
solve's own scale ladder predicts it.

Patch admission (measured, not by eye):
  1. Never clipped and never near black in any frame.
  2. SMOOTH IN EVERY FRAME: the within-patch relative MAD stays below a
     threshold in all frames. Subject structure is sharp in some frames and
     blurred in others but is never smooth in all of them, so this excludes the
     bee's wing without anyone having to look at it.
  3. Spatially spread: greedy farthest-point selection over the admitted set,
     so the retained patches are not all in one corner.

Everything downstream uses only admitted patches.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A patch is "smooth" if its green photosites' MAD is under this fraction of
# its median. Out-of-focus background on this rig sits near 1-2%; anything
# carrying structure is far above.
SMOOTH_MAX = 0.045
LEVEL_MIN, LEVEL_MAX = 0.02, 0.85
N_PATCH = 12


def load(stack):
    z = np.load(os.path.join(HERE, "data", "levels-%s.npz" % stack),
                allow_pickle=True)
    return z


def shutter(stack, files):
    import csv
    path = os.path.join(HERE, "data", "shutter-%s.csv" % stack)
    m = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            m[r["file"]] = float(r["exposure_s"])
    return np.array([m[f] for f in files])


def farthest_point(centres, admitted, n):
    """Greedy spread over admitted candidates, seeded at the centroid."""
    idx = list(np.flatnonzero(admitted))
    if not idx:
        return []
    pts = centres[idx]
    mid = pts.mean(axis=0)
    first = idx[int(np.argmin(np.sum((pts - mid) ** 2, axis=1)))]
    chosen = [first]
    while len(chosen) < min(n, len(idx)):
        d = np.min(np.sum((centres[idx][:, None, :]
                           - centres[chosen][None, :, :]) ** 2, axis=2), axis=1)
        chosen.append(idx[int(np.argmax(d))])
    return chosen


def analyse(stack, verbose=True):
    z = load(stack)
    scene = z["scene"]          # (nf, np) median level, scene-fixed
    smad = z["scene_mad"]       # (nf, np) within-patch relative MAD
    sensor = z["sensor"]        # (nf, np) median level, sensor-fixed
    centres = z["centres"]
    a = z["a"]
    ref = int(z["ref"])
    files = [str(x) for x in z["files"]]
    idx = z["idx"]
    nf, npa = scene.shape

    ok_finite = np.isfinite(scene).all(axis=0) & np.isfinite(smad).all(axis=0)
    ok_level = ((scene > LEVEL_MIN).all(axis=0)
                & (scene < LEVEL_MAX).all(axis=0))
    ok_smooth = (smad < SMOOTH_MAX).all(axis=0)
    admitted = ok_finite & ok_level & ok_smooth
    chosen = farthest_point(centres, admitted, N_PATCH)

    t = shutter(stack, files)[idx]

    if verbose:
        print("=" * 74)
        print("%s  %d frames x %d candidate patches" % (stack, nf, npa))
        print("  finite in every frame : %3d" % ok_finite.sum())
        print("  level in [%.2f,%.2f]   : %3d" % (LEVEL_MIN, LEVEL_MAX,
                                                  (ok_finite & ok_level).sum()))
        print("  smooth (relMAD<%.3f) in EVERY frame : %3d"
              % (SMOOTH_MAX, admitted.sum()))
        print("  retained after spread selection      : %3d" % len(chosen))
        if len(chosen):
            worst = smad[:, chosen].max()
            print("  worst within-patch relMAD over all retained patch-frames: %.4f"
                  % worst)

    if len(chosen) < 4:
        print("  !! fewer than 4 admissible patches; stack unusable for PR-2")
        return None

    S = scene[:, chosen]        # (nf, P)
    Sn = sensor[:, chosen]
    E = S / t[:, None]          # exposure-normalised

    # Global level = across-patch median, so one odd patch cannot drive it.
    g_scene = np.median(S, axis=1)
    g_sensor = np.median(Sn, axis=1)
    g_exp = np.median(E, axis=1)

    r_scene = g_scene.max() / g_scene.min()
    r_sensor = g_sensor.max() / g_sensor.min()
    r_exp = g_exp.max() / g_exp.min()

    if verbose:
        print("  -- PR-1 --")
        print("  sensor-fixed  max/min = %.4f  (%.4f stops)   [confounded]"
              % (r_sensor, np.log2(r_sensor)))
        print("  scene-fixed   max/min = %.4f  (%.4f stops)"
              % (r_scene, np.log2(r_scene)))
        print("  scene-fixed / exposure-normalised max/min = %.4f  (%.4f stops)"
              % (r_exp, np.log2(r_exp)))
        print("  PR-1 verdict on this stack: %s (bar 1.02)"
              % ("REAL" if r_exp >= 1.02 else "NEGLIGIBLE"))

    # ---- PR-2: rank-1 (one scalar per frame) or a field? -------------------
    L = np.log(E)
    L = L - L.mean(axis=0, keepdims=True)   # remove each patch's own offset
    # Best rank-1 with a constant patch loading is the row mean; the general
    # best rank-1 is the leading singular triple. Report both.
    row = L.mean(axis=1, keepdims=True)
    f_row = 1.0 - np.sum((L - row) ** 2) / np.sum(L ** 2)
    sv = np.linalg.svd(L, compute_uv=False)
    f1 = sv[0] ** 2 / np.sum(sv ** 2)
    if verbose:
        print("  -- PR-2 --")
        print("  variance of log-level explained by a frame-only scalar : %.4f"
              % f_row)
        print("  variance explained by the leading singular component   : %.4f"
              % f1)
        print("  PR-2 verdict: %s (bar 0.90 on the frame-only scalar)"
              % ("GLOBAL" if f_row >= 0.90 else "FIELD"))
        spread = (E / E[0:1, :]).max(axis=1) - (E / E[0:1, :]).min(axis=1)
        print("  inter-patch spread of E/E[0], max over frames: %.4f" % spread.max())

    return {
        "stack": stack, "chosen": [int(c) for c in chosen],
        "centres": centres[chosen].tolist(),
        "t": t.tolist(), "a": a.tolist(), "ref": ref, "idx": idx.tolist(),
        "g_scene": g_scene.tolist(), "g_sensor": g_sensor.tolist(),
        "g_exp": g_exp.tolist(),
        "E": E.tolist(),
        "r_scene": float(r_scene), "r_sensor": float(r_sensor),
        "r_exp": float(r_exp),
        "f_row": float(f_row), "f1": float(f1),
        "n_admitted": int(admitted.sum()),
    }


if __name__ == "__main__":
    stacks = sys.argv[1:] or ["bee-3-cpl", "lavendar-cpl", "leaf-2-cpl",
                              "bee-2-cpl"]
    out = {}
    for s in stacks:
        r = analyse(s)
        if r:
            out[s] = r
        print()
    with open(os.path.join(HERE, "data", "phaseA.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f)
    print("wrote data/phaseA.json for %d stacks" % len(out))
