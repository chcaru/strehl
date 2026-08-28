# Score a knob sweep on BOTH axes at once: halo and sharpness, on the same
# pixels, for every arm.
#
# THE ONE THING THIS FILE MUST GET RIGHT. The textured sites and the subject
# mask are computed ONCE, from the BASELINE render, and reused unchanged for
# every arm. If each arm segmented itself, a softer arm would move its own
# measurement window -- its subject mask would grow as the edge softened and
# its "most textured decile" would slide to whatever it still had -- and a
# change in the reported number could be a change in the image or a change in
# where it was read. Fixing the window makes the comparison about the pixels.
#
# This is the same defect class as an earlier lane's: a self-test that
# asserted only the mean of a field whose defect was at the borders. A
# measurement that chooses its own support can hide anything.

import argparse
import json
import os
import pathlib
import sys

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from aura import SUB, luma, measure as aura_measure, segment, verdict  # noqa
from sharp import sharpness, subject_mask, textured  # noqa

OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--baseline", default="baseline")
    ap.add_argument("--tag", default="sweep")
    a = ap.parse_args()

    d = pathlib.Path(a.dir)
    files = sorted(d.glob("*.tiff"))
    if not files:
        print("no tiffs in %s" % d)
        return 1
    base = d / (a.baseline + ".tiff")
    if not base.exists():
        print("no baseline %s" % base)
        return 1

    # Fix the windows once, from the baseline.
    yb_full = luma(tifffile.imread(str(base)))
    sites = textured(yb_full, subject_mask(yb_full))
    sub_full = subject_mask(yb_full)
    sub_b = segment(yb_full[::SUB, ::SUB])
    s_base = sharpness(yb_full, sites)
    # TONE, because the sharpness metric cannot see the damage this sweep is
    # most likely to do. `stack --help` warns that a shallow pyramid "keeps
    # acuity but loses the darkest densities -- grey ink instead of black".
    # That is a LOW frequency failure, and a high-pass statistic is blind to
    # it by construction, so an arm could hold sharpness exactly while turning
    # the blacks grey and this sweep would call it free. Black is the 1st
    # percentile inside the subject; white the 99th of the background.
    black_base = float(np.percentile(yb_full[sub_full], 1.0))
    white_base = float(np.percentile(yb_full[~sub_full], 99.0))
    del yb_full

    print("scoring %d arms in %s" % (len(files), d))
    print("sharpness sites and subject mask FIXED from arm '%s' (%d sites)\n"
          % (a.baseline, int(sites.sum())))
    print("%-14s %8s %6s %8s %6s %-11s %9s %8s %8s %8s"
          % ("arm", "aura", "@px", "rim", "@px", "verdict", "sharp",
             "vs base", "black", "white"))
    print("-" * 104)

    rows = []
    for f in files:
        y = luma(tifffile.imread(str(f)))
        r = aura_measure(y[::SUB, ::SUB], sub_b)
        s = sharpness(y, sites)
        blk = float(np.percentile(y[sub_full], 1.0))
        wht = float(np.percentile(y[~sub_full], 99.0))
        del y
        r["arm"] = f.stem
        r["sharp_dn"] = round(s, 3)
        r["sharp_ratio"] = round(s / s_base, 4)
        r["black_dn"] = round(blk, 1)
        r["white_dn"] = round(wht, 1)
        r["black_delta"] = round(blk - black_base, 1)
        r["white_delta"] = round(wht - white_base, 1)
        r["verdict"] = verdict(r)
        rows.append(r)
        print("%-14s %8.1f %6.0f %8.1f %6.0f %-11s %9.2f %7.3fx %+8.1f %+8.1f"
              % (f.stem, r["aura_dn"], r["aura_at_px"], r["rim_dn"],
                 r["rim_at_px"], r["verdict"], r["sharp_dn"],
                 r["sharp_ratio"], r["black_delta"], r["white_delta"]))
    print("-" * 104)
    print("black/white are DELTAS vs baseline in DN. A POSITIVE black delta is")
    print("blacks going grey, which no sharpness statistic can see.")

    b = [r for r in rows if r["arm"] == a.baseline][0]
    worst_b = max(b["aura_dn"], b["rim_dn"])
    print("baseline halo %.1f DN, sharpness %.2f DN\n" % (worst_b, b["sharp_dn"]))
    print("arms that reduce the halo, with what they cost:")
    got = False
    for r in sorted(rows, key=lambda r: max(r["aura_dn"], r["rim_dn"])):
        if r["arm"] == a.baseline:
            continue
        w = max(r["aura_dn"], r["rim_dn"])
        if w < worst_b:
            got = True
            print("  %-14s halo %7.1f DN (%+6.1f%%)  sharp %+5.1f%%  black %+7.1f DN"
                  % (r["arm"], w, 100.0 * (w - worst_b) / worst_b,
                     100.0 * (r["sharp_ratio"] - 1.0), r["black_delta"]))
    if not got:
        print("  NONE. No swept knob reduced the halo on this subject.")

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / ("sweep-%s.json" % a.tag)
    p.write_text(json.dumps(rows, indent=1))
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
