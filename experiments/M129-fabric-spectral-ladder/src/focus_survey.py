"""Per-aperture, per-ROI focus survey and planarity check.

This is SUBJECT CHARACTERISATION, not measurement. It answers "which frame, and is
the ROI flat enough to use", and it deliberately quotes no cutoff frequency. No `f_c`
from real data may be believed until `commission.py` has measured the estimator's
bias (PREREGISTRATION.md Amendment 1, condition A1').

Three things it produces, all registered as controls in PREREGISTRATION.md section 4:

  T1(b) the best-focus frame index PER APERTURE, since a shared index would be wrong
        for a focus stack;
  T1(c) the same index computed independently on sub-patches, so that a non-planar
        ROI shows up as disagreement between them;
  T5    the clipping fraction per frame, so the registered gate can be applied.

AND ONE THREAT THIS SCRIPT EXISTS TO CONTROL, WHICH IS NOT IN THE ORIGINAL
PREREGISTRATION AND IS RAISED HERE:

  `m5_lib.focus_score`'s default band is 0.05 to 0.14 sensor cyc/px, i.e. 9.8 to
  27.3 cy/mm. Its docstring calls that "well below every candidate cutoff", which was
  true for M5's apertures. It is NOT true here. At f/18 the registered hypotheses put
  `f_c` at 32.83 (H2) and 42.05 (H3) cy/mm, so the band's top edge sits at 0.83 and
  0.65 of the cutoff respectively. A focus score whose band overlaps the roll-off
  will preferentially select frames with a HIGHER cutoff, which biases toward H3 --
  the same direction as the depth-of-field confound T1, so the two would compound
  rather than cancel.

  The control is to compute the focus score in several bands, including ones strictly
  below every candidate cutoff, and to check that the selected frame does not depend
  on the choice. If it does depend on it, the selection is contaminated and must be
  made in the narrow band.

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

# Focus bands in sensor cyc/px. "narrow" is chosen to sit below the LOWEST candidate
# cutoff at the LARGEST aperture number, so it cannot be contaminated by the roll-off
# at any aperture in the ladder.
BANDS = {
    "m5default": (0.05, 0.14),   # 9.8 - 27.3 cy/mm, m5_lib's own default
    "narrow": (0.04, 0.09),      # 7.8 - 17.6 cy/mm, below every candidate cutoff
    "wide": (0.05, 0.20),        # 9.8 - 39.1 cy/mm, deliberately contaminated
}


def aperture_dir(tag):
    return os.path.join(ROOT, f"fabric-weave-{tag}-sw5-cpl")


def scores_for_frame(path, rc, cc, size, tile, sub):
    """Return focus scores in every band for the ROI and for four sub-patches,
    plus the clipping fraction and mean level."""
    a = L.load_active(path)
    out = {}

    clipped = float(np.mean(a >= L.WHITE_LEVEL))
    out["clipped_frac"] = clipped
    out["p999"] = float(np.percentile(a, 99.9))

    patch = L.crop_lattice(a, "GQ", rc, cc, size)
    out["mean_dn"] = float(patch.mean())
    f, p, counts = L.spectrum(patch, "GQ", tile=tile, window="hann")
    out["bands"] = {k: float(L.focus_score(f, p, band=b)) for k, b in BANDS.items()}

    # Sub-patches for the planarity check. Centres are offset by `size` sensor
    # pixels, which is half the ROI's sensor footprint, so they tile it.
    subs = {}
    half = size // 2
    for name, (dr, dc) in (("nw", (-half, -half)), ("ne", (-half, half)),
                           ("sw", (half, -half)), ("se", (half, half))):
        try:
            sp = L.crop_lattice(a, "GQ", rc + dr, cc + dc, sub)
            sf, spw, scount = L.spectrum(sp, "GQ", tile=min(tile, sub), window="hann")
            subs[name] = {k: float(L.focus_score(sf, spw, band=b))
                          for k, b in BANDS.items()}
        except Exception as e:
            subs[name] = {"error": f"{type(e).__name__}: {e}"}
    out["sub"] = subs
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aperture", help="one of f5.6 f8 f11 f14 f18")
    ap.add_argument("--rc", type=int, default=L.ACTIVE_H // 2)
    ap.add_argument("--cc", type=int, default=L.ACTIVE_W // 2)
    ap.add_argument("--size", type=int, default=512, help="GQ samples per side")
    ap.add_argument("--sub", type=int, default=256)
    ap.add_argument("--tile", type=int, default=256)
    ap.add_argument("--step", type=int, default=1, help="decode every Nth frame")
    ap.add_argument("--tag", default="", help="suffix for the output filename")
    args = ap.parse_args()

    rc = args.rc - (args.rc % 2)
    cc = args.cc - (args.cc % 2)

    files = sorted(glob.glob(os.path.join(aperture_dir(args.aperture), "*.ARW")))
    if not files:
        print(f"no frames for {args.aperture}")
        return 1
    sel = files[::args.step]
    print(f"{args.aperture}: {len(files)} frames, surveying {len(sel)} "
          f"(step {args.step}) at ROI centre ({rc},{cc}) size {args.size} GQ")

    recs = []
    for i, path in enumerate(sel):
        try:
            r = scores_for_frame(path, rc, cc, args.size, args.tile, args.sub)
        except Exception as e:
            print(f"  {os.path.basename(path)}: ERROR {type(e).__name__}: {e}")
            continue
        r["file"] = os.path.basename(path)
        r["index"] = files.index(path)
        recs.append(r)
        if i % 10 == 0:
            print(f"  [{i + 1}/{len(sel)}] {r['file']} mean {r['mean_dn']:7.0f} DN  "
                  f"m5default {r['bands']['m5default']:12.1f}  "
                  f"clipped {r['clipped_frac'] * 100:.4f}%")

    if not recs:
        print("no usable frames")
        return 1

    # --- best frame per band, and whether the choice is band-dependent --------
    print("\nbest-focus frame by band:")
    best = {}
    for b in BANDS:
        vals = [r["bands"][b] for r in recs]
        j = int(np.argmax(vals))
        best[b] = {"file": recs[j]["file"], "index": recs[j]["index"],
                   "score": vals[j]}
        print(f"  {b:>10}  {recs[j]['file']}  frame index {recs[j]['index']:3d}  "
              f"score {vals[j]:.1f}")
    idxs = {best[b]["index"] for b in BANDS}
    band_stable = len(idxs) == 1
    print(f"  band-independent selection: {band_stable}"
          + ("" if band_stable else f"  <-- CONTAMINATED, indices {sorted(idxs)}"))

    # --- planarity: does each quadrant peak at the same frame? ---------------
    print("\nplanarity check (best frame index per sub-patch, 'narrow' band):")
    sub_best = {}
    for name in ("nw", "ne", "sw", "se"):
        vals = [r["sub"].get(name, {}).get("narrow") for r in recs]
        good = [(v, r["index"]) for v, r in zip(vals, recs) if v is not None]
        if not good:
            print(f"  {name}: no data")
            continue
        v, idx = max(good, key=lambda t: t[0])
        sub_best[name] = idx
        print(f"  {name}: frame index {idx}")
    if sub_best:
        spread = max(sub_best.values()) - min(sub_best.values())
        print(f"  spread across quadrants: {spread} frames "
              f"(step width 5 in this capture)")
    else:
        spread = None

    out = {"aperture": args.aperture, "roi": {"rc": rc, "cc": cc, "size": args.size,
                                              "sub": args.sub, "tile": args.tile},
           "n_frames_total": len(files), "n_surveyed": len(recs),
           "bands": BANDS, "best": best, "band_stable": band_stable,
           "sub_best": sub_best, "sub_spread": spread, "records": recs}
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    name = f"focus-{args.aperture}{args.tag}.json"
    dest = os.path.join(here, "out", name)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
