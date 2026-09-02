"""Best-focus INDEX MAP across the whole frame, one decode pass per aperture.

Motivation. `focus_survey.py` found that a 512-sample GQ ROI at the frame centre is
not planar at f/18: its four quadrants reach best focus 5 frames apart. That is
registered threat T1 (depth of field / subject tilt) showing up as a real, measured
effect rather than a worry. The question it raises is not "is there tilt" but "how
large may an ROI be before the tilt across it matters, and where is the subject
flattest".

Answering that by re-running the survey at several sizes would decode the stack once
per size. Instead this decodes each frame ONCE and scores a contiguous grid of small
patches, producing a map of best-focus index over the field. From that map both
questions are answered offline and for free:

  * the local gradient of the index map gives the tilt in focus steps per mm;
  * thresholding the map gives the largest window anywhere that stays inside one
    focus step, which is the largest defensible ROI.

It also records mean level per patch, which exposes illumination fall-off, and the
peak sharpness, which exposes patches with no texture to focus on.

Quotes no cutoff frequency. See focus_survey.py's header for why.
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

ROOT = r"D:\personal\macro\requests\7-aperture-pairs"

# Below every candidate cutoff at every aperture in the ladder, so the focus
# measure cannot be contaminated by the diffraction roll-off it is used to find.
NARROW = (0.04, 0.09)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aperture")
    ap.add_argument("--size", type=int, default=128,
                    help="GQ samples per patch side (footprint is 2x this in "
                         "sensor px)")
    ap.add_argument("--step", type=int, default=1, help="decode every Nth frame")
    ap.add_argument("--margin", type=int, default=64,
                    help="sensor px kept clear of the active-area edge")
    args = ap.parse_args()

    foot = 2 * args.size  # sensor pixels spanned by one GQ patch
    rcs = list(range(args.margin + foot // 2, L.ACTIVE_H - args.margin - foot // 2,
                     foot))
    ccs = list(range(args.margin + foot // 2, L.ACTIVE_W - args.margin - foot // 2,
                     foot))
    rcs = [r - (r % 2) for r in rcs]
    ccs = [c - (c % 2) for c in ccs]

    files = sorted(glob.glob(os.path.join(
        ROOT, f"fabric-weave-{args.aperture}-sw5-cpl", "*.ARW")))
    if not files:
        print(f"no frames for {args.aperture}")
        return 1
    sel = files[::args.step]
    print(f"{args.aperture}: {len(sel)} frames x {len(rcs)}x{len(ccs)} patches "
          f"of {args.size} GQ ({foot} sensor px)")

    nfr, nr, nc = len(sel), len(rcs), len(ccs)
    score = np.zeros((nfr, nr, nc))
    level = np.zeros((nfr, nr, nc))

    for i, path in enumerate(sel):
        a = L.load_active(path)
        for ir, rc in enumerate(rcs):
            for ic, cc in enumerate(ccs):
                patch = L.crop_lattice(a, "GQ", rc, cc, args.size)
                level[i, ir, ic] = patch.mean()
                f, p, _ = L.spectrum(patch, "GQ", tile=args.size, window="hann")
                score[i, ir, ic] = L.focus_score(f, p, band=NARROW)
        if i % 10 == 0:
            print(f"  [{i + 1}/{nfr}] {os.path.basename(path)}")

    best = np.argmax(score, axis=0)                       # frame index per patch
    peak = np.max(score, axis=0)
    med = np.median(score, axis=0)
    contrast = peak / np.maximum(med, 1e-12)              # is there a real peak?

    print("\nbest-focus index map (rows = image top to bottom):")
    for ir in range(nr):
        print("  " + " ".join(f"{best[ir, ic]:3d}" for ic in range(nc)))

    print("\npeak/median focus-score contrast (a weak peak means no texture):")
    for ir in range(nr):
        print("  " + " ".join(f"{min(contrast[ir, ic], 9999):4.0f}"
                              for ic in range(nc)))

    ok = contrast > 10.0
    print(f"\npatches with a decisive focus peak: {int(ok.sum())}/{ok.size}")
    if ok.sum():
        b = best[ok]
        print(f"  best-index range over those patches: {b.min()} .. {b.max()} "
              f"({b.max() - b.min()} focus steps)")
        print(f"  median {int(np.median(b))}, IQR "
              f"{int(np.percentile(b, 25))} .. {int(np.percentile(b, 75))}")

    # Largest square window of patches whose best index spans <= tol steps.
    print("\nlargest flat window, by tolerance (side in patches, "
          f"1 patch = {foot} sensor px = {foot * L.PITCH_UM / 1000:.2f} mm):")
    flat = {}
    for tol in (0, 1, 2, 3):
        bestside, bestpos = 0, None
        for side in range(1, min(nr, nc) + 1):
            found = None
            for ir in range(nr - side + 1):
                for ic in range(nc - side + 1):
                    w = best[ir:ir + side, ic:ic + side]
                    m = ok[ir:ir + side, ic:ic + side]
                    if not m.all():
                        continue
                    if w.max() - w.min() <= tol:
                        found = (ir, ic)
                        break
                if found:
                    break
            if found is None:
                break
            bestside, bestpos = side, found
        flat[tol] = {"side_patches": bestside, "pos": bestpos}
        if bestpos:
            ir, ic = bestpos
            r0 = rcs[ir] - foot // 2
            c0 = ccs[ic] - foot // 2
            ctr = (r0 + bestside * foot // 2, c0 + bestside * foot // 2)
            flat[tol]["centre_rc_cc"] = [int(ctr[0]), int(ctr[1])]
            flat[tol]["gq_size"] = int(bestside * foot // 2)
            print(f"  tol {tol} step(s): {bestside}x{bestside} patches, "
                  f"centre ({ctr[0]},{ctr[1]}), usable GQ size "
                  f"{bestside * foot // 2}")
        else:
            print(f"  tol {tol} step(s): none")

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest = os.path.join(here, "out", f"focusmap-{args.aperture}.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump({"aperture": args.aperture, "size": args.size, "foot": foot,
                   "step": args.step, "rcs": rcs, "ccs": ccs,
                   "files": [os.path.basename(p) for p in sel],
                   "band": NARROW,
                   "best": best.tolist(), "contrast": contrast.tolist(),
                   "level": level[best.max() // 2].tolist(),
                   "flat": flat}, fh, indent=2)
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
