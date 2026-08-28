"""Score the per-band gate-floor scale sweep at HEAD.

STREHL_GATE_FLOOR_SCALE multiplies the measured noise floor per Laplacian
band, band 0 first. Every arm here holds band 0 at 1.0 and raises the coarse
bands, which is the move `--pyramid-gate` cannot express because it takes a
single number.

BASELINE. The null arm `1,1,1,1,1,1,1` was verified pixel-identical to the
existing G200 masters -- 0 of 98,898,048 pixels differing on two subjects,
with the comparator potency-checked on a pair that must differ (96.3% / 95.7%
differing). G200 is therefore used directly as the baseline rather than
re-rendered.

COLUMNS, all on the same masters and the same sites:

  blotch     sigma_mid, 20-60 px, at FLAT sites. The mottle statistic.
  grain      sigma_hp, same sites.
  sharp/tex  band 0.20-0.25 cyc/px at TEXTURED sites. Textured, because on
             flat sites this column correlates 0.985-0.997 with grain and is a
             second noise column wearing a sharpness label.
  r(sharp,grain)  per subject across arms. Without it a grain move reads as a
             sharpness move, which is the error this lane already made once
             and had to retract.

`averaged` is deliberately NOT scored. It is a duty cycle: it says the knob
turned, not that the image improved.
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
import tifffile                                                   # noqa: E402
from ceiling import pick_sites                                    # noqa: E402
from blotch_sweep import fine_on                                  # noqa: E402

SCALE = r"C:\dev\strehl-out\BUILD-GATE\scale\ab"
BASE = r"C:\dev\strehl-out\BUILD-GATE\head\ab\G200"

ARMS = ["S04", "S08", "S16", "SRAMP", "S32", "B1ONLY", "NOB1"]
SCALES = {
    "S04": "1,4,4,4,4,4,4",
    "S08": "1,8,8,8,8,8,8",
    "S16": "1,16,16,16,16,16,16",
    "SRAMP": "1,1,4,16,32,32,32",
    "S32": "1,32,32,32,32,32,32",
    # Complementary pair decomposing S32 across band 1.
    "B1ONLY": "1,32,1,1,1,1,1",
    "NOB1": "1,1,32,32,32,32,32",
}
SUBJECTS = ["bee-1-cpl", "flower-bud-alone-cpl", "119MSDCF",
            "109MSDCF", "coffee-bubbles"]

# The one subject whose sharpness column is not a restatement of its grain
# column, and therefore the only one where "flat sharpness, falling blotch"
# is distinguishable from "less grain".
DECOUPLED = "bee-1-cpl"


def arm_path(arm, subject):
    if arm == "NULL":
        return os.path.join(BASE, subject + ".tiff")
    return os.path.join(SCALE, arm, subject + ".tiff")


def measure(path, flat, tex):
    mid, hp = [], []
    for (y, x) in flat:
        c = bl.codes(path, y, x)
        mid.append(np.mean([bl.sigma_mid(c[..., k]) for k in range(3)]))
        hp.append(np.mean([bl.sigma_hp(c[..., k]) for k in range(3)]))
    ft = [fine_on(bl.codes(path, y, x)) for (y, x) in tex]
    return float(np.mean(mid)), float(np.mean(hp)), float(np.mean(ft))


def score(subject):
    ref = arm_path("NULL", subject)
    if not os.path.exists(ref):
        return None, 0
    flat, _, _ = bl.pick_flat_sites(ref)
    tex, _ = pick_sites(tifffile.imread(ref)[..., :3].astype(np.float64))
    rows = {"NULL": measure(ref, flat, tex)}
    have = 0
    for arm in ARMS:
        p = arm_path(arm, subject)
        if not os.path.exists(p):
            continue
        rows[arm] = measure(p, flat, tex)
        have += 1
    return rows, have


def main():
    print("Per-band gate-floor scale sweep, HEAD binary "
          "5915316B95E21446 (strehl 0.0.0 5e914c5f4fa2).")
    print("Baseline NULL = the G200 masters, verified pixel-identical to "
          "STREHL_GATE_FLOOR_SCALE=1,1,1,1,1,1,1.")
    print("All arms hold band 0 at 1.0; only coarse bands move.\n")

    for s in SUBJECTS:
        rows, have = score(s)
        if not rows:
            print("%s: baseline missing\n" % s)
            continue
        b = rows["NULL"]
        tag = "   <-- DECOUPLED SUBJECT" if s == DECOUPLED else ""
        print("%s  N=%d%s" % (s, bl.NFRAMES[s], tag))
        print("  %-6s %-22s | %9s %9s %11s"
              % ("arm", "scale", "blotch x", "grain x", "sharp/tex x"))
        print("  %-6s %-22s | %9.4f %9.4f %11.4f"
              % ("NULL", "1,1,1,1,1,1,1", 1.0, 1.0, 1.0))
        for a in ARMS:
            if a not in rows:
                continue
            r = rows[a]
            print("  %-6s %-22s | %9.4f %9.4f %11.4f"
                  % (a, SCALES[a], r[0] / b[0], r[1] / b[1], r[2] / b[2]))
        if have < len(ARMS):
            print("  INCOMPLETE: %d/%d arms rendered; correlation withheld "
                  "(a partial r is not the sweep's r).\n" % (have, len(ARMS)))
            continue
        av = [rows["NULL"]] + [rows[a] for a in ARMS]
        g = np.array([x[1] for x in av])
        t = np.array([x[2] for x in av])
        m = np.array([x[0] for x in av])
        rsg = np.corrcoef(g, t)[0, 1]
        print("  r(sharp/tex, grain) = %+.4f    r(blotch, grain) = %+.4f"
              % (rsg, np.corrcoef(g, m)[0, 1]))
        if abs(rsg) > 0.9:
            print("  NOTE: |r| > 0.9 -- the sharpness column is not "
                  "independent evidence on this subject.")
        print()


if __name__ == "__main__":
    main()
