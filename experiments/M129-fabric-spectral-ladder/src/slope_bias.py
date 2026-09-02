"""How does the crossing estimator's bias depend on the texture's spectral slope?

WHY THIS IS NOT OPTIONAL. A1' requires the bias to be measured "as a function of
planted f_c, signal-to-noise ratio and texture spectral slope, across the range this
ladder actually uses". Every synthetic test in this lane so far -- xspec.py's test 4,
equalise.py's part (b) -- planted a slope of 2.2, because 2.2 is a common value for
natural texture and not because anything had been measured. slope_survey.py then
measured the fabric at alpha = 3.126, sd 0.294 over thirty ROI-by-aperture pairs.
That is well outside anything commissioned, so every bias figure quoted so far is an
extrapolation in a variable nobody has swept.

THE DIRECTION, STATED BEFORE MEASURING IT (rule 18). A steeper texture spectrum
carries less power near the cutoff relative to the low band. The diffraction roll-off
therefore disappears into the noise floor at a LOWER frequency, so the last detectable
bin sits lower, so f_c is underestimated MORE. Predicted: the bias becomes more
negative as alpha grows. Magnitude unknown; a factor of two would matter and a few
tenths of a point would not.

If that prediction is right, the real bias is worse than every synthetic figure this
lane has quoted, and the correction A1' demands is larger than it looked.

WHAT IS HELD FIXED. The planted cutoff, and the LOW-BAND signal-to-noise ratio, which
is the quantity Amendment 6 equalises on. Holding the low-band SNR fixed rather than
the noise variance is the point: it isolates the slope's effect from the SNR effect
already measured, and it asks the question in the coordinates the ladder will actually
use.

Read-only with respect to D:\\personal\\macro; touches no raw file.
"""

import json
import os
import sys

import numpy as np

M5 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "m5-diffraction")
sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from equalise import LOW_BAND, low_snr, equalise_to, _scene, _fc  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")

N = 256
TILE = 128
FC_LAT = 0.18
NREP = 16
TARGET_SNR = 2000.0     # low-band power ratio, inside the real ladder's 965-5546


def main():
    truth = FC_LAT / L.LATTICE_PITCH_PX["GQ"]
    print("CROSSING BIAS AGAINST TEXTURE SPECTRAL SLOPE")
    print()
    print(f"planted f_c {truth:.4f} sensor cyc/px "
          f"({truth * 1000 / L.PITCH_UM:.1f} cy/mm), {NREP} replicates per slope")
    print(f"low-band SNR held at {TARGET_SNR:.0f} by adding noise, so the only")
    print(f"variable is the slope. The fabric measures alpha = 3.126.")
    print()
    print("PREDICTION, MADE BEFORE RUNNING: bias becomes MORE NEGATIVE as alpha")
    print("grows, because a steeper spectrum reaches the floor at a lower frequency.")
    print()
    print(f"  {'alpha':>7} {'low SNR':>9} {'bias %':>9} {'sd':>7} {'n':>4}")
    rows = []
    for alpha in (2.0, 2.2, 2.6, 3.0, 3.126, 3.4, 3.8):
        biases, snrs = [], []
        for k in range(NREP):
            r = np.random.default_rng(9000 + 137 * k + int(alpha * 1000))
            s = _scene(N, alpha, FC_LAT, r)
            # Start well above the target so equalise_to can only ever add noise.
            patch = s + r.normal(0, 1.0, (N, N))
            patch, _ = equalise_to(patch, TARGET_SNR, r)
            sn, _, _ = low_snr(patch)
            snrs.append(sn)
            fc = _fc(patch, TILE)
            if fc:
                biases.append((fc - truth) / truth * 100)
        b = float(np.mean(biases)) if biases else float("nan")
        rows.append({"alpha": alpha, "snr": float(np.mean(snrs)), "bias": b,
                     "sd": float(np.std(biases)) if biases else float("nan"),
                     "n": len(biases)})
        print(f"  {alpha:7.3f} {np.mean(snrs):9.0f} {b:+9.2f} "
              f"{np.std(biases):7.2f} {len(biases):4d}")

    a = np.array([r["alpha"] for r in rows])
    b = np.array([r["bias"] for r in rows])
    good = np.isfinite(b)
    slope = float(np.polyfit(a[good], b[good], 1)[0])
    print()
    print(f"  bias moves {slope:+.2f} points per unit of alpha")
    at22 = float(np.interp(2.2, a[good], b[good]))
    at31 = float(np.interp(3.126, a[good], b[good]))
    print(f"  at alpha 2.2  (what every synthetic test so far planted): {at22:+.2f}%")
    print(f"  at alpha 3.126 (what the fabric actually is)            : {at31:+.2f}%")
    print(f"  difference {at31 - at22:+.2f} points")
    print()
    confirmed = slope < 0
    print(f"  PREDICTION {'CONFIRMED' if confirmed else 'REFUTED'}: the bias is "
          f"{'more' if confirmed else 'LESS'} negative on a steeper texture.")
    if not confirmed:
        print("  The reasoning in this module's docstring is wrong and must be")
        print("  rewritten, not quietly dropped.")
    print()
    print("  CONSEQUENCE FOR THE LANE. Every bias figure this lane has quoted was")
    print("  measured at alpha 2.2 and the subject is alpha 3.126, so all of them")
    print(f"  are wrong by about {at31 - at22:+.1f} points in the "
          f"{'pessimistic' if confirmed else 'optimistic'} direction. The")
    print("  commissioning battery must sweep alpha over at least 2.8 to 3.5 -- the")
    print("  fabric's measured mean plus and minus one ROI-to-ROI sd -- or its bias")
    print("  correction is an extrapolation in the one variable that was never swept.")

    dest = os.path.join(OUT, "slope-bias.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump({"planted_fc": truth, "nrep": NREP, "target_snr": TARGET_SNR,
                   "rows": rows, "points_per_alpha": slope,
                   "bias_at_2p2": at22, "bias_at_fabric": at31,
                   "difference": at31 - at22,
                   "prediction_confirmed": bool(confirmed)}, fh, indent=2)
    print()
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
