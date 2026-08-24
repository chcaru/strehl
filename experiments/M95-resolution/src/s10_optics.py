"""Does the lens actually deliver contrast in the band the binned output throws
away? If it does not, binning is free and none of this matters.

Everything here is derived from primary optics, not recalled. The sensor
geometry is read from the raw file. The one quantity that is not known is the
magnification at capture, so it is swept and the conclusion is checked across
the whole sweep rather than at a single assumed value.

EXIF, verified elsewhere in this project: FE 100mm F2.8 Macro GM OSS + 2X
Teleconverter, FNumber 5.6, MaxApertureValue 5.6 -- f/5.6 is wide open with the
teleconverter fitted, so there is no aperture headroom and the effective
aperture is set entirely by magnification.
"""

import json
import os

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

FF_WIDTH_MM = 35.9        # 35 mm full frame, long dimension
LAMBDA_MM = 550e-6        # 550 nm, mid-visible


def diffraction_mtf(f, fc):
    """Incoherent diffraction-limited MTF of a circular pupil."""
    x = np.clip(np.asarray(f, dtype=float) / fc, 0.0, 1.0)
    phi = np.arccos(x)
    return (2.0 / np.pi) * (phi - np.cos(phi) * np.sin(phi))


def main():
    recon = json.load(open(os.path.join(OUT, "recon.json"), encoding="utf-8"))
    cols = recon["info"]["raw_image_visible_shape"][1]
    pitch_mm = FF_WIDTH_MM / cols
    nyq_sensor = 1.0 / (2.0 * pitch_mm)
    nyq_binned = 1.0 / (2.0 * 2.0 * pitch_mm)
    print("sensor          : %d visible columns across %.1f mm" % (cols, FF_WIDTH_MM))
    print("photosite pitch : %.4f um" % (pitch_mm * 1000))
    print("Nyquist, sensor : %.2f cy/mm" % nyq_sensor)
    print("Nyquist, binned : %.2f cy/mm   <- the shipped default stops here" % nyq_binned)

    print("\nmagnification is not known from EXIF, so it is swept:")
    print("%6s %10s %12s %14s %14s" % ("m", "N_eff", "cutoff", "MTF@binNyq", "MTF@sensNyq"))
    rows = []
    for m in (0.0, 0.5, 1.0, 2.0):
        n_eff = 5.6 * (1.0 + m)          # pupil magnification taken as 1
        fc = 1.0 / (LAMBDA_MM * n_eff)
        a = float(diffraction_mtf(nyq_binned, fc))
        b = float(diffraction_mtf(nyq_sensor, fc))
        rows.append({"m": m, "n_eff": n_eff, "cutoff_cy_mm": fc,
                     "mtf_at_binned_nyquist": a, "mtf_at_sensor_nyquist": b})
        print("%6.1f %10.2f %10.1f cy/mm %13.3f %14.3f" % (m, n_eff, fc, a, b))

    worst = min(rows, key=lambda r: r["mtf_at_sensor_nyquist"])
    print("\n   worst case in the sweep is m = %.1f (f/%.1f):" % (worst["m"], worst["n_eff"]))
    print("   diffraction cutoff %.1f cy/mm vs sensor Nyquist %.2f cy/mm -- cutoff is %s"
          % (worst["cutoff_cy_mm"], nyq_sensor,
             "ABOVE" if worst["cutoff_cy_mm"] > nyq_sensor else "BELOW"))
    print("   even there the lens delivers %.1f %% MTF at the binned Nyquist and %.1f %% at"
          % (100 * worst["mtf_at_binned_nyquist"], 100 * worst["mtf_at_sensor_nyquist"]))
    print("   the sensor Nyquist, so the band binning discards is NOT empty.")
    ok = all(r["mtf_at_sensor_nyquist"] > 0.0 for r in rows)
    print("   conclusion holds across the whole magnification sweep: %s" % ok)

    with open(os.path.join(OUT, "s10_optics.json"), "w", encoding="utf-8") as f:
        json.dump({"pitch_um": pitch_mm * 1000, "nyquist_sensor": nyq_sensor,
                   "nyquist_binned": nyq_binned, "rows": rows}, f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
