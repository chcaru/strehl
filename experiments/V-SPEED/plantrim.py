"""What can this lane's halo detector actually see, and does the clamp remove it?

ORCH, after V-REVIEW adjudicated all four HALO verdicts as false positives:

    "if you want to justify a halo fix, the justification has to come from a
     plant you can see, not from the current statistic. If your clamp removes
     a planted 9000 DN broad rim that the instrument misses, that is a real
     result and I want it."

    halo_profile.py's measured floor: ~4500 DN for a NARROW rim, via the
    `bump` statistic only; a BROAD rim stayed at bump 0.0 and read CLEAN at
    9000 DN.

TWO QUESTIONS, because the ask as phrased contains one that cannot be answered
the way it is written.

Q1 -- CAN ANSWER. What is aura.py's detection floor for each rim shape? This
lane built aura.py precisely because halo_profile.py's `overshoot` is a HEIGHT
rather than a PROMINENCE and never asks for background on both sides. If
aura.py sees a broad rim that halo_profile.py misses at 9000 DN, that is a
real instrument result and it bounds the residual risk ORCH placed on 11
subjects. If aura.py is ALSO blind to it, that is worth more: it would mean
neither instrument in this project can see the shape the owner complained
about, and the risk is unbounded rather than bounded.

Q2 -- CANNOT ANSWER AS PHRASED, and saying so is the point. A rim planted into
a FINISHED master cannot be removed by a MERGE-TIME clamp; the clamp ran
hundreds of seconds before the plant existed. Asking whether STREHL_HULL
removes a planted rim is asking whether an earlier stage can undo a later one.
What CAN be measured, and is measured below, is the honest version: run the
detector across the hull modes on the SAME real subject and ask whether the
clamp changes the rim statistic at all. If `unclamped` and the default read
the same rim, the clamp is not doing halo work on that subject, and no halo
justification for it survives regardless of what any plant shows.

PLANT INTEGRITY. A plant that never landed and an instrument that is blind
produce the same clean reading. Every plant here is verified to have moved the
image's own radial profile by the intended amplitude at the intended radius
before its detection result is allowed to count; a plant that fails that check
is reported as PLANT-FAILED, never as a clean detection.
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from aura import SUB, luma, measure, segment  # noqa: E402

OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")
HULLDIR = pathlib.Path(r"D:\strehl-out\V-SPEED-HALO\hullcommission")

# halo_profile.py's floors, quoted from ORCH's adjudication message. Not
# re-derived here -- that instrument is V-REVIEW's and this lane does not
# edit or run it.
THEIRS = {"narrow": 4500.0, "wide": None, "broad": None}  # None == missed at 9000 DN

# ORCH's HALO threshold on the overshoot statistic, reused so the comparison
# is like for like rather than against a gate of this lane's choosing.
DETECT_DN = 200.0

SHAPES = {
    # name:   (centre radius px, sigma px)  -- sigma is the Gaussian scale, so
    # the feature spans roughly 6*sigma.
    #
    # aura.py's EDGES run 2 -> 420 px CONTINUOUSLY (2,4,6,9,12,16,20,26,32,40,
    # 50,62,80,100,120,150,185,230,280,340,420). That matters here: ORCH's
    # mechanism for halo_profile.py's false positives is that it walks 2-120 px
    # and then takes its far field at 400-900 px, so nothing between 120 and
    # 400 px is ever measured. This instrument samples that entire gap, which
    # is why it independently called flat-on-ruler-cpl a 172 px arch and
    # lavendar-cpl a 124 px arch rather than halos.
    #
    # But a 420 px field has its own limit, and it is the opposite one: a
    # feature broad enough to fill the field leaves no room for the outer
    # shoulder `prominence` needs, so a VERY broad rim must under-report here.
    # "broad" below is deliberately chosen to exceed the field so that limit is
    # measured rather than assumed, and "wide" sits inside it.
    "narrow": (30.0, 12.0),    # rim hugging the subject, ~70 px wide
    "wide": (120.0, 60.0),     # ~360 px, fits inside the 420 px field
    "broad": (120.0, 150.0),   # ~900 px, deliberately EXCEEDS the field
}

AMPS = [250.0, 500.0, 1000.0, 2000.0, 4500.0, 9000.0]


def plant(y, dist, amp, r0, sigma):
    """Add a Gaussian rim of amplitude `amp` DN centred at radius `r0`."""
    return y + amp * np.exp(-0.5 * ((dist - r0) / sigma) ** 2)


def profile_delta(y0, y1, dist, r0, sigma):
    """How much the image's own radial profile actually moved at the plant.

    This is the plant-integrity check. It reads the IMAGE, not the detector,
    so a detector that is blind cannot make a plant look absent.
    """
    core = (dist >= r0 - sigma) & (dist <= r0 + sigma)
    far = dist >= r0 + 4.0 * sigma
    if core.sum() < 1000 or far.sum() < 1000:
        return None
    d_core = float(np.median(y1[core]) - np.median(y0[core]))
    d_far = float(np.median(y1[far]) - np.median(y0[far]))
    return d_core - d_far


def load(path):
    return luma(tifffile.imread(str(path)))[::SUB, ::SUB]


def sweep(master):
    y0 = load(master)
    subj = segment(y0)
    dist = distance_transform_edt(~subj) * SUB
    base = measure(y0, subj)
    if base is None:
        print("BASELINE UNMEASURABLE -- cannot run the sweep")
        return []
    base_rim = base["rim_dn"]
    print(f"baseline rim {base_rim:.1f} DN at {base['rim_at_px']:.0f} px "
          f"(field {base['field_px']:.0f} px, {base['nbands']} bands)\n")

    rows = []
    for shape, (r0, sigma) in SHAPES.items():
        print(f"--- {shape} rim: centre {r0:.0f} px, sigma {sigma:.0f} px "
              f"(spans ~{6 * sigma:.0f} px) ---")
        for amp in AMPS:
            y1 = plant(y0, dist, amp, r0, sigma)
            landed = profile_delta(y0, y1, dist, r0, sigma)
            m = measure(y1, subj)
            if m is None:
                print(f"  {amp:7.0f} DN  PLANT-FAILED: unmeasurable")
                rows.append({"shape": shape, "amp": amp, "status": "PLANT-FAILED"})
                continue
            # The plant must have moved the image by at least half its nominal
            # amplitude at the plant radius, or the detection result below is
            # about a plant that is not there.
            if landed is None or landed < 0.5 * amp:
                print(f"  {amp:7.0f} DN  PLANT-FAILED: profile moved "
                      f"{landed if landed is not None else float('nan'):.0f} DN, "
                      f"want >= {0.5 * amp:.0f}")
                rows.append({"shape": shape, "amp": amp, "status": "PLANT-FAILED",
                             "landed_dn": landed})
                continue
            rise = m["rim_dn"] - base_rim
            seen = rise >= DETECT_DN
            print(f"  {amp:7.0f} DN  landed {landed:7.0f}  rim {m['rim_dn']:8.1f} "
                  f"at {m['rim_at_px']:5.0f} px  w {m['rim_w_px']:6.1f}  "
                  f"rise {rise:+8.1f}  {'DETECTED' if seen else 'missed'}")
            rows.append({"shape": shape, "amp": amp, "status": "SCORED",
                         "landed_dn": round(landed, 1),
                         "rim_dn": m["rim_dn"], "rim_at_px": m["rim_at_px"],
                         "rim_w_px": m["rim_w_px"], "rise_dn": round(rise, 1),
                         "detected": bool(seen)})
        floor = [r["amp"] for r in rows
                 if r["shape"] == shape and r.get("detected")]
        f = min(floor) if floor else None
        t = THEIRS[shape]
        print(f"  aura.py floor for a {shape} rim: "
              f"{f'{f:.0f} DN' if f else f'NOT DETECTED up to {max(AMPS):.0f} DN'}"
              f"   |   halo_profile.py: "
              f"{f'{t:.0f} DN' if t else 'missed at 9000 DN'}\n")
    return rows


def hull_modes():
    """Does the clamp change the rim statistic on a real subject at all?"""
    print("--- does STREHL_HULL change the rim on a real render? ---")
    print("(109MSDCF, stack --srgb, the four hull arms from hullcommission)")
    out = []
    for tag in ["unset1", "inputrange", "perlevel", "unclamped"]:
        p = HULLDIR / f"{tag}.tiff"
        if not p.exists():
            print(f"  {tag:12s} SKIPPED: {p.name} not present")
            out.append({"arm": tag, "status": "SKIPPED"})
            continue
        y = load(p)
        m = measure(y, segment(y))
        if m is None:
            print(f"  {tag:12s} SKIPPED: unmeasurable")
            out.append({"arm": tag, "status": "SKIPPED"})
            continue
        print(f"  {tag:12s} rim {m['rim_dn']:8.1f} DN at {m['rim_at_px']:5.0f} px"
              f"   aura {m['aura_dn']:8.1f} DN at {m['aura_at_px']:5.0f} px")
        out.append({"arm": tag, "status": "SCORED", "rim_dn": m["rim_dn"],
                    "rim_at_px": m["rim_at_px"], "aura_dn": m["aura_dn"]})
    scored = [o for o in out if o["status"] == "SCORED"]
    if len(scored) >= 2:
        rims = [o["rim_dn"] for o in scored]
        spread = max(rims) - min(rims)
        print(f"\n  rim spread across hull modes: {spread:.1f} DN")
        print("  " + ("The clamp does NOT move the rim statistic on this "
                      "subject, so no\n  halo justification for it survives here."
                      if spread < DETECT_DN else
                      "The clamp DOES move the rim statistic; worth pursuing."))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=str(
        pathlib.Path(r"D:\strehl-out\V-SPEED-HALO\sweep\tweezers-cpl\baseline.tiff")))
    a = ap.parse_args()
    print("aura.py detection floor vs halo_profile.py, and what the clamp moves")
    print(f"master: {a.master}\n")
    rows = sweep(pathlib.Path(a.master))
    print()
    hull = hull_modes()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plantrim.json").write_text(
        json.dumps({"sweep": rows, "hull": hull}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())



