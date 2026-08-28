r"""The STREHL_GATE_FLOOR A/B: rim and sharpness on the same pixels.

Partition is self-summing per axis: N = PASS + FAIL + REFUSED + NOT EXAMINED.
A REFUSED must never read as a PASS, so subjects whose edges cannot be
isolated are counted separately and named.
"""
import json
import os
import re
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

import gf_measure as M

OUT = r"C:\dev\strehl-out\V-GATHER\gatefloor"
# Measured in gf_commission.py BLUR arm: the gauge's response to a pure
# deformation of the edge, with no rim present. Two DIFFERENT images closer
# than this cannot be told apart on the rim axis.
DEFORM_FLOOR = 0.0039
SUBJECTS = ["leaf-2-cpl", "coffee-bean", "113MSDCF", "flat-on-ruler-cpl",
            "112MSDCF", "wrapped-text-1", "109MSDCF", "119MSDCF"]


def band0(subject, arm):
    """The gate's band-0 averaging percentage, read from the render log."""
    f = os.path.join(OUT, "%s--%s.log" % (subject, arm))
    if not os.path.exists(f):
        return None
    for line in open(f, encoding="utf-8", errors="replace"):
        if line.startswith("averaged"):
            m = re.findall(r"([\d.]+)%", line)
            if m:
                return float(m[0])
    return None


def floor_ratio(subject):
    f = os.path.join(OUT, "%s--measured.log" % subject)
    if not os.path.exists(f):
        return None
    for line in open(f, encoding="utf-8", errors="replace"):
        if "x white" in line:
            m = re.findall(r"([\d.]+)", line)
            if m:
                return float(m[0])
    return None


def main():
    rows = []
    examined = 0
    for s in SUBJECTS:
        fw = os.path.join(OUT, "%s--white.tiff" % s)
        fm = os.path.join(OUT, "%s--measured.tiff" % s)
        if not (os.path.exists(fw) and os.path.exists(fm)):
            rows.append({"subject": s, "state": "NOT EXAMINED",
                         "why": "render missing"})
            continue
        examined += 1
        gw = M.luma(tifffile.imread(fw))
        gm = M.luma(tifffile.imread(fm))
        if gw.shape != gm.shape:
            rows.append({"subject": s, "state": "REFUSED",
                         "why": "shape %s vs %s" % (gw.shape, gm.shape)})
            continue
        shift, err = M.int_shift(gw, gm)
        # Sites frozen ONCE on a rim-free reference built from BOTH arms, so
        # neither arm's population is privileged.
        ref = gaussian_filter(0.5 * (gw + gm), 2.0)
        sites = M.select(ref)
        rw, offw, kw = M.rim(gw, sites)
        rm, offm, km = M.rim(gm, sites)
        aw, am = M.acuity(gw), M.acuity(gm)
        iso = (kw / offw) if offw else 0.0
        if not (np.isfinite(rw) and np.isfinite(rm)):
            state, why = "REFUSED", "no isolated edge survived (n=%d)" % kw
        elif shift != (0, 0):
            state, why = "REFUSED", "arms not pixel-aligned %s" % (shift,)
        else:
            d = rm - rw
            if abs(d) < DEFORM_FLOOR:
                state = "UNRESOLVED"
                why = "|delta| %.4f < deformation floor %.4f" % (abs(d),
                                                                DEFORM_FLOOR)
            elif d > 0:
                state, why = "FAIL", "rim WORSE by %+.4f" % d
            else:
                state, why = "PASS", "rim better by %+.4f" % d
        rows.append({"subject": s, "state": state, "why": why,
                     "rim_white": rw, "rim_measured": rm,
                     "acuity_white": aw, "acuity_measured": am,
                     "acuity_ratio": (am / aw) if aw else float("nan"),
                     "n_isolated": kw, "n_offered": offw, "isolated_frac": iso,
                     "shift": list(shift), "shift_mse": err,
                     "avg_b0_white": band0(s, "white"),
                     "avg_b0_measured": band0(s, "measured"),
                     "floor_x_white": floor_ratio(s)})
        del gw, gm, ref
    if examined == 0:
        raise SystemExit("REFUSING to report: 0 subjects examined. "
                         "A partition that sums 0 == 0 is not a result.")

    print("\nSTREHL_GATE_FLOOR: white (pin behaviour) -> measured (shipping default)")
    print("acuity ratio > 1 means the DEFAULT is sharper; < 1 means it is SOFTER.\n")
    hdr = ("%-22s %9s %9s %9s %8s %8s %7s  %s"
           % ("subject", "rim wht", "rim meas", "d rim", "acuity",
              "b0 wht", "b0 meas", "verdict"))
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if r["state"] in ("NOT EXAMINED",):
            print("%-22s %-56s %s" % (r["subject"], r["why"], r["state"]))
            continue
        if r["state"] == "REFUSED" and "rim_white" not in r:
            print("%-22s %-56s %s" % (r["subject"], r["why"], r["state"]))
            continue
        print("%-22s %+8.4f %+8.4f %+8.4f %7.4f %7.1f%% %6.1f%%  %s"
              % (r["subject"], r["rim_white"], r["rim_measured"],
                 r["rim_measured"] - r["rim_white"], r["acuity_ratio"],
                 r["avg_b0_white"] or float("nan"),
                 r["avg_b0_measured"] or float("nan"), r["state"]))
    n = len(SUBJECTS)
    counts = {k: sum(1 for r in rows if r["state"] == k)
              for k in ("PASS", "FAIL", "UNRESOLVED", "REFUSED",
                        "NOT EXAMINED")}
    tot = sum(counts.values())
    print("\npartition: %d = %s" % (
        n, " + ".join("%d %s" % (v, k) for k, v in counts.items())))
    assert tot == n, "partition does not sum: %d != %d" % (tot, n)
    print("sums correctly: %s" % (tot == n))
    for r in rows:
        if r["state"] in ("REFUSED", "UNRESOLVED"):
            print("  %-22s %s -- %s" % (r["subject"], r["state"], r["why"]))
    json.dump(rows, open("gatefloor.json", "w"), indent=1)
    print("\nwrote gatefloor.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
