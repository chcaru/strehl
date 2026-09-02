"""Is the aperture trend residual defocus? The focus stacks can answer it.

Amendment 9 left one thing open: the apparent `B` falls as the aperture closes,
+0.1157 by route A and +0.11 by route B, and three candidates explain it equally
well - residual defocus, lens aberration, vibration. They share a sign, so the two
in-band apertures cannot separate them, and section 34 of docs/captures-needed.md
asks for two more.

But one of the three is separable WITHOUT a new capture, because only one of them
varies from frame to frame inside a stack. Defocus does. Aberration and vibration
are properties of the lens and the rig and are the same in every frame.

The survey already picks each cell's own best-focus frame, so the measurement is
at a per-ROI focus optimum already. That is not the same as being defocus-free:
focus is quantised by the stack's step, the true optimum lies somewhere inside a
step, and depth of field is SHALLOWER at f/14 than at f/18, so an identical
residual step costs more defocus at the wider aperture. That is exactly the
direction of the observed trend, which makes it the candidate to shoot at first.

METHOD. Walk each cell's focus offset from -3 to +3 frames, refit `B` at every
offset by the route-A model fit, and fit a parabola in `B` against offset. The
vertex is a sub-frame estimate of best focus and the `B` there is the
defocus-corrected value.

REGISTERED BEFORE THE FIRST RUN.

P8  `B` RISES AWAY FROM FOCUS. The parabola opens upward at both apertures.
    Falsifier: negative curvature at either aperture, which would mean the focus
    map is not locating the optimum of this statistic and every `B` in Amendment 9
    is measured at an arbitrary point on the focus curve rather than at its best.
    That would be a worse problem than the one being investigated.

P9  IT RISES FASTER AT THE WIDER APERTURE. Curvature at f/14 exceeds curvature at
    f/18. Defocus optical path difference scales as 1/N^2 for a given focus error,
    so the same step in frames buys more aberration at f/14. Falsifier: f/18 is
    steeper, which would leave defocus unable to produce the observed sign.

P10 THE DECISIVE ONE. Corrected to their vertices, the f/14 minus f/18 gap in `B`
    falls below 0.05 - the same threshold Amendment 9 registered for "a single `B`
    is tenable". PASS means residual defocus explains the trend, the capture in
    section 34 drops in urgency, and the fix is finer focus steps. FAIL means
    defocus is excluded and the remaining candidates are the lens and the rig.

    I do not know which way this goes. The survey already sits at a per-ROI
    optimum, so there may be very little residual defocus left to find, in which
    case P10 fails and defocus is cleanly excluded. That is a perfectly good
    result and it is why the test is worth running either way.

C1  CONTROL, and it guards the whole thing. The parabola vertex must land within
    one frame of the focus map's own choice. If the two disagree by more, they are
    not measuring the same optimum and the offsets cannot be interpreted.
"""

import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
M5 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m5-diffraction")
sys.path.insert(0, M5)

import m5_lib as L  # noqa: E402
from snr_survey import load_rois, load_maps, ROOT  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
INBAND = ["f14", "f18"]
EXACT_N = {"f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}
OFFSETS = list(range(-3, 4))
M = 2.7198


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, default=2)
    ap.add_argument("--tile", type=int, default=128)
    args = ap.parse_args()

    doc = load_rois(args.w)
    rois = doc["rois"]
    maps = load_maps()
    ref = next(iter(maps.values()))
    rcs, ccs = np.array(ref["rcs"]), np.array(ref["ccs"])

    print("apparent B against focus offset")
    print("=" * 78)
    print(f"  offsets {OFFSETS}, route-A model fit at each")
    cells = []
    for t in INBAND:
        files = sorted(glob.glob(os.path.join(
            ROOT, f"fabric-weave-{t}-sw5-cpl", "*.ARW")))
        print(f"\n  {t}: {len(files)} frames")
        print(f"    {'ROI':>4} {'best':>5} " +
              " ".join(f"{d:>+7}" for d in OFFSETS) +
              f" {'vertex':>7} {'B*':>7} {'curv':>8}")
        for i, roi in enumerate(rois):
            ir = int(np.argmin(np.abs(rcs - roi["rc"])))
            ic = int(np.argmin(np.abs(ccs - roi["cc"])))
            j0 = min(int(np.array(maps[t]["best"], float)[ir, ic]), len(files) - 1)
            xs, bs = [], []
            for d in OFFSETS:
                j = j0 + d
                if j < 0 or j >= len(files):
                    continue
                a = L.load_active(files[j])
                patch = L.crop_lattice(a, "GQ", roi["rc"], roi["cc"],
                                       roi["gq_size"])
                f, p, c = L.spectrum(patch, "GQ", tile=args.tile, window="hann")
                m = L.knee_model_fit(f, p, c)
                if not m["ok"] or not m["f_c"] or m["above_reach"]:
                    continue
                xs.append(d)
                bs.append(L.PITCH_UM / (L.LAMBDA_UM * EXACT_N[t] * m["f_c"]))
            if len(xs) < 4:
                print(f"    {i:>4} {j0:5d}   too few usable offsets")
                continue
            co = np.polyfit(np.array(xs, float), np.array(bs, float), 2)
            vert = -co[1] / (2 * co[0]) if co[0] != 0 else float("nan")
            vert = float(np.clip(vert, min(xs), max(xs)))
            bstar = float(np.polyval(co, vert))
            shown = {d: b for d, b in zip(xs, bs)}
            cells.append({"aperture": t, "roi": i, "best": j0, "offsets": xs,
                          "B": [float(x) for x in bs], "curv": float(co[0]),
                          "vertex": vert, "B_vertex": bstar})
            print(f"    {i:>4} {j0:5d} " +
                  " ".join((f"{shown[d]:7.3f}" if d in shown else f"{'--':>7}")
                           for d in OFFSETS) +
                  f" {vert:+7.2f} {bstar:7.3f} {co[0]:+8.4f}")

    print("\nresults")
    print("=" * 78)
    agg = {}
    for t in INBAND:
        r = [c for c in cells if c["aperture"] == t]
        b0 = np.array([np.interp(0.0, c["offsets"], c["B"]) for c in r])
        bv = np.array([c["B_vertex"] for c in r])
        cu = np.array([c["curv"] for c in r])
        ve = np.array([c["vertex"] for c in r])
        agg[t] = {"n": len(r), "B0": float(b0.mean()),
                  "B0_sem": float(b0.std(ddof=1) / np.sqrt(len(b0))),
                  "Bv": float(bv.mean()),
                  "Bv_sem": float(bv.std(ddof=1) / np.sqrt(len(bv))),
                  "curv": float(cu.mean()),
                  "curv_sem": float(cu.std(ddof=1) / np.sqrt(len(cu))),
                  "vertex": float(ve.mean()),
                  "vertex_absmax": float(np.abs(ve).max())}
    print(f"  {'ap':>6} {'n':>3} {'B at offset 0':>14} {'B at vertex':>13} "
          f"{'curvature':>12} {'mean vertex':>12}")
    for t in INBAND:
        a = agg[t]
        print(f"  {t:>6} {a['n']:3d} {a['B0']:8.4f} +-{a['B0_sem']:.4f} "
              f"{a['Bv']:8.4f} +-{a['Bv_sem']:.4f} "
              f"{a['curv']:+8.4f} +-{a['curv_sem']:.4f} {a['vertex']:+12.2f}")

    p8 = all(agg[t]["curv"] > 0 for t in INBAND)
    p9 = agg["f14"]["curv"] > agg["f18"]["curv"]
    g0 = agg["f14"]["B0"] - agg["f18"]["B0"]
    gv = agg["f14"]["Bv"] - agg["f18"]["Bv"]
    p10 = abs(gv) < 0.05
    c1 = max(agg[t]["vertex_absmax"] for t in INBAND) <= 1.0

    print()
    print(f"  P8  curvature positive at both       -> "
          f"{'PASS' if p8 else 'FAIL (FALSIFIER: the focus map is not at this optimum)'}")
    print(f"  P9  f/14 steeper than f/18           -> "
          f"{'PASS' if p9 else 'FAIL (defocus cannot make the observed sign)'}")
    print(f"  P10 gap at offset 0 {g0:+.4f}, at vertex {gv:+.4f}")
    print(f"      gap below 0.05 after correction  -> "
          f"{'PASS, residual defocus explains the trend' if p10 else 'FAIL, defocus is excluded'}")
    print(f"  C1  worst vertex {max(agg[t]['vertex_absmax'] for t in INBAND):+.2f} "
          f"frames from the focus map's choice -> "
          f"{'ok' if c1 else 'VOID: the two disagree about where focus is'}")

    if not c1:
        print("\n  C1 failed, so P8-P10 are not interpretable and are not claimed.")

    payload = {"cells": cells, "agg": agg, "gap0": g0, "gap_vertex": gv,
               "P8": bool(p8), "P9": bool(p9), "P10": bool(p10), "C1": bool(c1),
               "offsets": OFFSETS, "tile": args.tile, "m": M}
    with open(os.path.join(OUT, "defocus-b.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print("\nwrote out/defocus-b.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
