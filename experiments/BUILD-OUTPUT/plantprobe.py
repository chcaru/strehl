"""Probe: what d_floor does a given plant factor actually produce, and how many
cells survive classification? Arm C failed on `lead-1-cpl` with 1 tested cell
and arm F never landed, and both are questions about the PLANT, not the clause.
Guessing a new factor and re-running the commissioning would be tuning against
the outcome; measuring the plant first is not.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "BUILD-RECERT"))
from recertlib import classify, display_crop, measure_crop  # noqa: E402
from commission_bands import plant_band_noise  # noqa: E402

SHIP = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
CROPS = [(1200, 1200), (2400, 3600), (3600, 2000), (1600, 4800), (2800, 2400),
         (2000, 2800), (3200, 4000), (1400, 3000), (2600, 1600), (3000, 3400)]

for subj in ["lead-1-cpl", "coffee-bubbles"]:
    p = next(iter(sorted(SHIP.glob(f"{subj}*.tiff"))), None)
    if p is None:
        print(f"{subj}: no master")
        continue
    arr = tifffile.imread(str(p)).astype(np.float32)
    print(f"\n=== {subj}  shape {arr.shape} ===")
    for (y, x) in CROPS:
        try:
            d = display_crop(arr, y, x, (0, 0), [1.0] * 3, [0.0] * 3, 1.0,
                             already_srgb=True)
        except ValueError:
            print(f"  ({y},{x}) crop off image")
            continue
        b = measure_crop(d)["mottle"]
        flags = []
        if b["degenerate"]:
            flags.append("DEGENERATE")
        if not b["structure_detectable"]:
            flags.append("NO-STRUCT")
        line = (f"  ({y:5d},{x:5d}) floor {b['floor']:8.4f} peak {b['peak']:8.4f} "
                f"struct {b['structure']:8.4f} npr {b['noise_peak_ratio']:.2f} "
                f"{' '.join(flags)}")
        # what each factor does, run as arm C does it (base=noisy, cand=clean)
        for f in (1.02, 1.05, 1.10, 1.20, 1.5, 3.0):
            noisy, clean, landed = plant_band_noise(d, "mottle", factor=f)
            c = classify(measure_crop(noisy)["mottle"], measure_crop(clean)["mottle"])
            df = c["d_floor"]
            line += (f"\n      f={f:<4} landed={str(landed)[:1]} "
                     f"d_floor {('%+.4f' % df) if df is not None else '    -   '} "
                     f"refused={str(c['refused'])[:1]} {c['verdict'][:46]}")
        print(line)
    del arr
