"""Choose the ROIs the ladder will actually measure, jointly across all five apertures.

The maps say the subject is tilted by about 1 to 4 focus steps per mm depending on
aperture, and that a plane leaves 3 to 11 steps of residual relief. Neither number is
uniform over the field, so the ROIs must be CHOSEN rather than assumed, and chosen
once for all apertures, because the camera did not move between stacks (established
by the 1/N control in planarity.py) and so a sensor position denotes a fixed patch of
subject.

Selection criteria, all registered in PREREGISTRATION.md section 4 as T1 controls:

  flat      small spread of best-focus index across the window, at EVERY aperture.
            Compared in physical units rather than frames: the map's step is not the
            same size at different apertures, so a spread of 3 frames at f/18 is a
            larger physical depth than 3 frames at f/5.6. Converted with the
            exponent gamma measured in planarity.py rather than assumed to be 1.

  textured  a decisive focus peak at every aperture, so the ROI has structure to
            measure and the best-focus frame is not being picked out of noise.

  unclipped checked directly on the selected frames, since the registered gate T5
            rejects any ROI whose 99.9th percentile exceeds 15000 DN and f/5.6 is
            known from the smoke test to clip somewhere in the frame.

  spread out  non-overlapping, so the ROIs are independent replicates rather than
            one measurement quoted several times.

A NOTE ON SIZE, which is a real tension and is resolved by measurement rather than
by taste. A larger ROI averages more spectral tiles and so estimates the cutoff more
precisely, but it spans more tilt and so blurs it. Registered condition A5 requires
the recovered cutoff to be independent of ROI area while the confound is shown to
depend on it, so this script emits a ladder of sizes rather than one size, and the
sweep is the control.

Quotes no cutoff frequency: selection uses only best-focus INDEX and contrast.
Read-only with respect to D:\\personal\\macro.
"""

import argparse
import glob
import json
import os
import sys

import numpy as np

M5 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "m5-diffraction")
sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
ROOT = r"D:\personal\macro\requests\7-aperture-pairs"

EXACT_N = {"f5.6": 2 ** 2.5, "f8": 8.0, "f11": 2 ** 3.5,
           "f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}
MIN_CONTRAST = 20.0
P999_MAX = 15000.0     # registered gate T5


def load_maps():
    maps = {}
    for path in sorted(glob.glob(os.path.join(OUT, "focusmap-f*.json"))):
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        maps[d["aperture"]] = d
    if not maps:
        raise SystemExit("no focusmap-*.json; run focus_map.py first")
    ref = next(iter(maps.values()))
    for a, d in maps.items():
        assert d["rcs"] == ref["rcs"] and d["ccs"] == ref["ccs"], \
            f"{a} was mapped on a different grid; cannot compare positions"
        assert d["size"] == ref["size"], f"{a} used a different patch size"
    return maps, ref


def gamma_from_planarity():
    p = os.path.join(OUT, "planarity.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        g = d.get("q4_gamma")
        if g:
            return float(np.mean([v["gamma"] for v in g.values()]))
    print("  (planarity.json has no gamma; falling back to 1.0)")
    return 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, default=2, help="window side, in patches")
    ap.add_argument("--k", type=int, default=6, help="how many ROIs to select")
    ap.add_argument("--verify-clip", action="store_true",
                    help="decode the best-focus frame per ROI and apply gate T5")
    args = ap.parse_args()

    maps, ref = load_maps()
    tags = [t for t in EXACT_N if t in maps]
    rcs, ccs = ref["rcs"], ref["ccs"]
    foot = ref["foot"]
    nr, nc = len(rcs), len(ccs)
    gamma = gamma_from_planarity()
    print(f"apertures {tags}, grid {nr}x{nc}, patch footprint {foot} sensor px, "
          f"gamma {gamma:.3f}\n")

    best = {t: np.array(maps[t]["best"], float) for t in tags}
    con = {t: np.array(maps[t]["contrast"], float) for t in tags}
    w = args.w

    # relief[ir,ic] = worst physical relief over apertures, in arbitrary but common
    # units (frames scaled by N^gamma, which removes the differing step size).
    relief = np.full((nr - w + 1, nc - w + 1), np.inf)
    mincon = np.zeros_like(relief)
    per_ap = {t: np.full_like(relief, np.nan) for t in tags}
    for ir in range(nr - w + 1):
        for ic in range(nc - w + 1):
            vals, cons = [], []
            for t in tags:
                b = best[t][ir:ir + w, ic:ic + w]
                c = con[t][ir:ir + w, ic:ic + w]
                spread = float(b.max() - b.min())
                per_ap[t][ir, ic] = spread
                vals.append(spread * EXACT_N[t] ** gamma)
                cons.append(float(c.min()))
            relief[ir, ic] = max(vals)
            mincon[ir, ic] = min(cons)

    usable = mincon >= MIN_CONTRAST
    print(f"windows of {w}x{w} patches (GQ size {w * foot // 2}, "
          f"{w * foot * L.PITCH_UM / 1000:.2f} mm): {usable.sum()}/{usable.size} "
          f"pass the contrast floor {MIN_CONTRAST:g}")
    r = relief[usable]
    print(f"  worst-aperture relief over those: min {r.min():.0f}, "
          f"median {np.median(r):.0f}, max {r.max():.0f} (frames x N^gamma)\n")

    # Greedy: take the flattest usable window, then forbid anything overlapping it.
    taken = np.zeros((nr, nc), bool)
    chosen = []
    order = np.argsort(relief.ravel())
    for flat_idx in order:
        if len(chosen) >= args.k:
            break
        ir, ic = np.unravel_index(flat_idx, relief.shape)
        if not usable[ir, ic]:
            continue
        if taken[ir:ir + w, ic:ic + w].any():
            continue
        taken[ir:ir + w, ic:ic + w] = True
        r0, c0 = rcs[ir] - foot // 2, ccs[ic] - foot // 2
        centre_r = r0 + w * foot // 2
        centre_c = c0 + w * foot // 2
        chosen.append({
            "rc": int(centre_r - (centre_r % 2)),
            "cc": int(centre_c - (centre_c % 2)),
            "gq_size": int(w * foot // 2),
            "relief_scaled": float(relief[ir, ic]),
            "min_contrast": float(mincon[ir, ic]),
            "spread_frames": {t: float(per_ap[t][ir, ic]) for t in tags},
        })

    print(f"selected {len(chosen)} non-overlapping ROIs, flattest first:\n")
    hdr = "  #   rc    cc   GQ   relief   mincon  " + "".join(
        f"{t:>7}" for t in tags)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for i, roi in enumerate(chosen):
        print(f"  {i}  {roi['rc']:5d} {roi['cc']:5d} {roi['gq_size']:4d} "
              f"{roi['relief_scaled']:8.0f} {roi['min_contrast']:8.0f}  " +
              "".join(f"{roi['spread_frames'][t]:7.0f}" for t in tags))
    print("\n  the five right-hand columns are the best-focus index spread across")
    print("  the window IN FRAMES at each aperture. They should fall roughly as")
    print("  1/N^gamma for a fixed physical relief; that they do is a per-ROI")
    print("  repeat of the global control in planarity.py.")

    if args.verify_clip and chosen:
        print(f"\napplying registered gate T5 (99.9th percentile <= {P999_MAX:g} DN)")
        print("on the best-focus frame of each ROI at each aperture:\n")
        for i, roi in enumerate(chosen):
            worst = 0.0
            for t in tags:
                files = sorted(glob.glob(os.path.join(
                    ROOT, f"fabric-weave-{t}-sw5-cpl", "*.ARW")))
                # best-focus frame for this ROI, from the map's own patch grid
                ir = int(np.argmin(np.abs(np.array(rcs) - roi["rc"])))
                ic = int(np.argmin(np.abs(np.array(ccs) - roi["cc"])))
                j = int(best[t][ir, ic])
                a = L.load_active(files[min(j, len(files) - 1)])
                patch = L.crop_lattice(a, "GQ", roi["rc"], roi["cc"],
                                       roi["gq_size"])
                p999 = float(np.percentile(patch + L.BLACK_LEVEL, 99.9))
                worst = max(worst, p999)
                roi.setdefault("p999", {})[t] = p999
            roi["passes_T5"] = bool(worst <= P999_MAX)
            print(f"  ROI {i}: worst p99.9 = {worst:8.1f} DN  "
                  f"{'PASS' if roi['passes_T5'] else 'REJECT'}")
        npass = sum(1 for r in chosen if r.get("passes_T5"))
        print(f"\n  T5: {npass} pass, {len(chosen) - npass} rejected "
              f"(rejection count is required in the report)")

    dest = os.path.join(OUT, f"rois-w{w}.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump({"w": w, "gq_size": int(w * foot // 2), "gamma": gamma,
                   "apertures": tags, "min_contrast": MIN_CONTRAST,
                   "p999_max": P999_MAX, "rois": chosen}, fh, indent=2)
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
