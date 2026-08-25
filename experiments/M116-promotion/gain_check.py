"""The gain confound on the campaign-6 photometric result, and M120's statistic.

Why this exists. ORCH's invariant is merged Laplacian RMS divided by the
Laplacian RMS of the noisiest SINGLE input frame. The singles are not
photometrically normalised; the P1 arm's output is. The Laplacian is a linear
operator, so scaling an image by k scales its Laplacian RMS by k exactly. The
instrument's own docstring calls hf_energy "insensitive to level and ramp" --
true for an ADDITIVE offset, false for a MULTIPLICATIVE gain.

So a photometric correction that merely rescales the output would move ORCH's
ratio without touching a single structural property of the image, and it would
move it in the direction that looks like success. This script asks whether the
-0.0130 measured in score_arms.py is that.

The test: per window, compare the ratio of Laplacian RMS between the arms
against the ratio of LEVEL between the same arms. If they agree, the movement
is gain and nothing else. Whatever survives after dividing gain out is
structure.

Dividing gain out gives q = lapRMS / level, which is exactly the gain-invariant
estimator M120 section 36.2 used to measure --photometric at 1.0946 (+9.5
percent HARM, 12 of 12 windows) on this same stack. So the same computation
also puts my result and M120's on one estimator and settles whether we
disagree.

Windows and their coordinates are parsed from the instrument's own per-window
table, so this scores the identical pixels the instrument scored -- not a
re-derivation of the window rule that could drift from it.

Writes C:/dev/strehl-out/M116/invariant/gain.json. Reads nothing on D:.
"""

import json
import os
import re
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M116\invariant"
S = 256  # window size, from patchwork_invariant.py

# The instrument's per-window table row:
#   x  y  kurt(mrg)  hf(mrg)  hf min  hf MAX  vs.min  vs.MAX
ROW = re.compile(
    r"^(\d+)\s+(\d+)\s+(-?[0-9.]+|nan)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+"
    r"([0-9.]+)\s+([0-9.]+)\s*$")


def guard(cond, msg):
    if not cond:
        print("GUARD: " + msg)
        sys.exit(3)


def load_lum(path):
    """Luminance exactly as patchwork_invariant.load computes it: plain mean of
    the first three channels. Not a weighted luminance -- matching the
    instrument matters more than being photometrically correct here."""
    a = tifffile.imread(path)
    guard(a.dtype == np.uint16,
          "%s read as %s, expected uint16 (fact 1615)" % (os.path.basename(path), a.dtype))
    return a[..., :3].astype(np.float64).mean(axis=2)


def hf_energy(win):
    """Byte-for-byte the instrument's estimator, copied so the two agree."""
    lap = (-4 * win[1:-1, 1:-1] + win[:-2, 1:-1] + win[2:, 1:-1]
           + win[1:-1, :-2] + win[1:-1, 2:])
    return float(np.sqrt((lap ** 2).mean()))


def windows_from_log(path):
    guard(os.path.exists(path), "missing instrument log " + path)
    with open(path) as fh:
        text = fh.read()
    wins, denom = [], {}
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            wins.append((x, y))
            denom[(x, y)] = (float(m.group(4)), float(m.group(6)))  # hf(mrg), hf MAX
    guard(len(wins) == 12,
          "parsed %d windows from %s, expected 12" % (len(wins), os.path.basename(path)))
    return wins, denom


def main():
    p0 = os.path.join(OUT, "bee-3-cpl__P0-default.tif")
    p1 = os.path.join(OUT, "bee-3-cpl__P1-photometric.tif")
    log0 = os.path.join(OUT, "score-P0-default.log")

    wins, denom = windows_from_log(log0)
    L0, L1 = load_lum(p0), load_lum(p1)
    guard(L0.shape == L1.shape, "arms differ in shape: %s vs %s" % (L0.shape, L1.shape))

    rows = []
    for (x, y) in wins:
        w0 = L0[y:y + S, x:x + S]
        w1 = L1[y:y + S, x:x + S]
        h0, h1 = hf_energy(w0), hf_energy(w1)
        m0, m1 = float(np.median(w0)), float(np.median(w1))
        guard(m0 > 0 and m1 > 0, "non-positive level in window %d,%d" % (x, y))

        # Cross-check: the hf I compute here must match what the instrument
        # printed for the same window on the same arm. If it does not, I am not
        # measuring the pixels the instrument measured. The instrument prints
        # this column with %10.1f, so the tightest honest tolerance is half a
        # printed unit -- anything tighter tests its formatter, not my maths.
        guard(abs(h0 - denom[(x, y)][0]) <= 0.05,
              "hf mismatch at %d,%d: mine %.6f, instrument printed %.1f"
              % (x, y, h0, denom[(x, y)][0]))

        rows.append({
            "x": x, "y": y,
            "hf_p0": h0, "hf_p1": h1, "hf_ratio": h1 / h0,
            "level_p0": m0, "level_p1": m1, "level_ratio": m1 / m0,
            "q_p0": h0 / m0, "q_p1": h1 / m1, "q_ratio": (h1 / m1) / (h0 / m0),
            "hf_max_single": denom[(x, y)][1],
        })

    hf_r = np.array([r["hf_ratio"] for r in rows])
    lv_r = np.array([r["level_ratio"] for r in rows])
    q_r = np.array([r["q_ratio"] for r in rows])

    # How much of the raw movement is gain? The raw effect is (median hf_ratio
    # - 1); the part that survives gain removal is (median q_ratio - 1).
    raw = float(np.median(hf_r)) - 1.0
    gain = float(np.median(lv_r)) - 1.0
    resid = float(np.median(q_r)) - 1.0
    explained = (gain / raw) if abs(raw) > 1e-12 else float("nan")

    result = {
        "windows": rows,
        "median_hf_ratio_p1_over_p0": float(np.median(hf_r)),
        "median_level_ratio_p1_over_p0": float(np.median(lv_r)),
        "median_q_ratio_p1_over_p0": float(np.median(q_r)),
        "raw_effect": raw, "gain_effect": gain, "residual_after_gain": resid,
        "fraction_of_raw_effect_explained_by_gain": explained,
        "q_windows_harmed": int((q_r > 1.0).sum()),
        "q_windows_helped": int((q_r < 1.0).sum()),
        "m120_s36_2_q_ratio_for_comparison": 1.0946,
        "m122_b12_for_comparison": 1.0638,
    }
    with open(os.path.join(OUT, "gain.json"), "w") as fh:
        json.dump(result, fh, indent=2)

    print("%-6s %-6s %10s %10s %10s" % ("x", "y", "hf P1/P0", "lvl P1/P0", "q P1/P0"))
    for r in rows:
        print("%-6d %-6d %10.4f %10.4f %10.4f"
              % (r["x"], r["y"], r["hf_ratio"], r["level_ratio"], r["q_ratio"]))
    print("")
    print("median Laplacian-RMS ratio P1/P0 : %.4f   (raw effect %+.2f%%)"
          % (np.median(hf_r), 100 * raw))
    print("median LEVEL ratio        P1/P0 : %.4f   (gain      %+.2f%%)"
          % (np.median(lv_r), 100 * gain))
    print("median gain-invariant q   P1/P0 : %.4f   (residual  %+.2f%%)"
          % (np.median(q_r), 100 * resid))
    print("")
    print("fraction of the raw movement explained by gain alone: %.1f%%" % (100 * explained))
    print("on the gain-invariant statistic, --photometric harms %d of 12 windows "
          "and helps %d" % ((q_r > 1.0).sum(), (q_r < 1.0).sum()))
    print("M120 s36.2 measured 1.0946 on this statistic; M122 measured B12 = 1.0638")


if __name__ == "__main__":
    main()
