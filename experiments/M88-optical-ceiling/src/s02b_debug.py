"""s02b: debug dump of one synthetic case."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

rng = np.random.default_rng(7)
H, W = 240, 1600
FC = 86.3
img = L.synth_edge_frame(H, W, FC, 2.0, 200.0, 4000.0, sigma_um=0.0,
                         sub=4, axis="horizontal")
print("clean img range", img.min(), img.max())
noisy = L.add_sensor_noise(img, 100.0 / 436.8, 1.2392, rng)

for tag, arr in (("clean", img), ("noisy", noisy)):
    res = L.measure_sfr(arr, (0, 0, H, W), "G1", "horizontal", 1.28, 96.0,
                        taper_frac=0.25)
    line = res["line"]
    print(f"\n--- {tag} ---")
    print("  line angle_deg", round(line["angle_deg"], 4),
          "resid_sd_px", round(line["resid_sd_px"], 4),
          "rows", line["n_rows_used"])
    print("  normal", round(line["nx"], 5), round(line["ny"], 5))
    print("  contrast", round(res["contrast"], 1))
    print("  bin counts min/med/max",
          int(res["count"].min()), int(np.median(res["count"])),
          int(res["count"].max()))
    e = res["esf"]
    print("  esf[:4]", np.round(e[:4], 1), " esf[-4:]", np.round(e[-4:], 1))
    f, m = res["freq_cymm"], res["mtf"]
    true = (L.mtf_diffraction(f, FC) * L.mtf_pixel(f))
    for ft in (10, 20, 40, 60, 80, 86, 100, 120, 150, 180):
        i = int(np.argmin(np.abs(f - ft)))
        print(f"   f={f[i]:7.2f}  meas={m[i]: .5f}   true={true[i]: .5f}")
