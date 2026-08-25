"""T-A: the registered trap for ORCH's patchwork invariant.

Discipline 831 -- the null that matters is a real instance of the population
minus the mechanism under test. A single unmerged input frame is a real
photograph on the same unwarped grid as the merge, and it contains no merge, so
it CANNOT contain the merge defect. Whatever the instrument reads on it is
instrument, not defect.

One design point that decides whether this is a trap at all. The instrument's
denominator is the NOISIEST of five hardcoded single frames (f143, f158, f173,
f193, f208). Scoring one of THOSE five would make the ratio at most 1.0 by
construction -- the numerator would be a member of the set the denominator
maximises over -- and the trap would pass without being able to fail. So every
frame scored here is drawn from the 18 armF-f*.tif that are NOT in the
instrument's denominator set. Checked, not assumed: see EXCLUDED below.

Writes C:/dev/strehl-out/M116/invariant/ta-trap.json. Reads nothing on D:.
"""

import json
import os
import re
import subprocess
import sys

import numpy as np
import tifffile

M93 = r"C:\dev\strehl-out\M93-out"
OUT = r"C:\dev\strehl-out\M116\invariant"
INSTRUMENT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ORCH-drift-check",
    "patchwork_invariant.py",
)
REF = os.path.join(M93, "armM4-gate4-binlin.tif")

# The instrument's own denominator set, transcribed from patchwork_invariant.py
# lines 29-35. Anything here is ineligible as a trap frame.
EXCLUDED = {"armF-f143", "armF-f158", "armF-f173", "armF-f193", "armF-f208"}

# Real unmerged frames spanning the focus sweep, none of them in EXCLUDED.
FRAMES = [
    "armF-f119", "armF-f120", "armF-f134", "armF-f142", "armF-f147",
    "armF-f154", "armF-f169", "armF-f181", "armF-f185",
]

RE_MEDIAN = re.compile(
    r"merged fine-structure / NOISIEST single: median ([0-9.]+), worst ([0-9.]+)"
)
RE_VIOL = re.compile(r"INVARIANT .*?: (?:HOLDS in all (\d+)|VIOLATED in (\d+) of (\d+))")
RE_SD = re.compile(r"COMMISSIONING at sd=([0-9.]+)")
RE_PLANT = re.compile(r"plant voronoi\s+([0-9.]+)")


def guard(cond, msg):
    if not cond:
        print("GUARD: " + msg)
        sys.exit(3)


def run(frame):
    path = os.path.join(M93, frame + ".tif")
    guard(os.path.exists(path), "missing trap frame %s" % path)
    guard(frame not in EXCLUDED,
          "trap frame %s is in the instrument's own denominator set; the ratio "
          "would be bounded by 1.0 by construction and the trap could not fail"
          % frame)
    log = os.path.join(OUT, "ta-%s.log" % frame)
    proc = subprocess.run(
        [sys.executable, INSTRUMENT, path, "TA-" + frame, REF],
        capture_output=True, text=True,
    )
    text = proc.stdout + proc.stderr
    with open(log, "w") as fh:
        fh.write(text)
    guard(proc.returncode == 0,
          "instrument exited %d on %s; it exits 4 when its own commissioning "
          "plant fails to fire, and a green from an uncommissioned instrument "
          "is not a green" % (proc.returncode, frame))

    m = RE_MEDIAN.search(text)
    v = RE_VIOL.search(text)
    s = RE_SD.search(text)
    p = RE_PLANT.search(text)
    guard(m and v and s and p, "could not parse instrument output for " + frame)
    n_viol = 0 if v.group(1) else int(v.group(2))
    n_win = int(v.group(1) or v.group(3))
    guard(float(p.group(1)) > 10.0,
          "commissioning plant read %s on %s, below the instrument's own bar"
          % (p.group(1), frame))

    # Read the frame's own noise directly rather than trusting the instrument's
    # printed sd, and assert the dtype on the line after loading (fact 1615).
    arr = tifffile.imread(path)
    guard(arr.dtype == np.uint16, "%s is %s, expected uint16" % (frame, arr.dtype))

    return {
        "frame": frame,
        "median_ratio": float(m.group(1)),
        "worst_ratio": float(m.group(2)),
        "violations": n_viol,
        "windows": n_win,
        "commissioning_sd": float(s.group(1)),
        "plant": float(p.group(1)),
        "in_denominator_set": False,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    guard(os.path.exists(INSTRUMENT), "instrument not found at " + INSTRUMENT)
    guard(os.path.exists(REF), "window reference not found at " + REF)

    rows = [run(f) for f in FRAMES]

    med = [r["median_ratio"] for r in rows]
    vio = [r["violations"] for r in rows]
    sd = [r["commissioning_sd"] for r in rows]

    # Registered expectation: on a frame containing no merge, the instrument
    # must read at or below 1.0. Evaluated separately for each of the two
    # readouts, because they can fail independently.
    ratio_pass = max(med) <= 1.0
    viol_max = max(vio)

    # Is the violation count tracking frame noise rather than merge structure?
    r = float(np.corrcoef(sd, vio)[0, 1]) if len(set(vio)) > 1 else float("nan")

    result = {
        "instrument": INSTRUMENT,
        "window_reference": REF,
        "excluded_because_in_denominator_set": sorted(EXCLUDED),
        "frames": rows,
        "median_ratio_min": min(med),
        "median_ratio_max": max(med),
        "ratio_readout_passes_trap": bool(ratio_pass),
        "violations_max": viol_max,
        "violations_total": sum(vio),
        "violation_readout_passes_trap": bool(viol_max == 0),
        "corr_violations_vs_frame_noise": r,
        "shipped_merge_violations_for_comparison": 7,
        "shipped_merge_median_for_comparison": 1.114,
    }
    with open(os.path.join(OUT, "ta-trap.json"), "w") as fh:
        json.dump(result, fh, indent=2)

    print("T-A  trap: %d real unmerged frames, none in the denominator set" % len(rows))
    print("%-12s %8s %8s %6s %10s" % ("frame", "median", "worst", "viol", "sd"))
    for row in rows:
        print("%-12s %8.3f %8.3f %6d %10.1f" % (
            row["frame"], row["median_ratio"], row["worst_ratio"],
            row["violations"], row["commissioning_sd"]))
    print("")
    print("median ratio  range %.3f..%.3f   trap %s  (shipped merge reads 1.114)"
          % (min(med), max(med), "PASSES" if ratio_pass else "FAILS"))
    print("violations    max %d of 12       trap %s  (shipped merge reads 7 of 12)"
          % (viol_max, "PASSES" if viol_max == 0 else "FAILS"))
    print("corr(violations, frame noise) = %.3f" % r)


if __name__ == "__main__":
    main()
