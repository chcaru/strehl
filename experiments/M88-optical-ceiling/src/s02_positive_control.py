"""s02: POSITIVE CONTROL.  Can the instrument recover a planted cutoff, and
can it see past the 48.8 cy/mm Nyquist of a single CFA colour plane?

Everything here is synthetic.  No real capture is read.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out"

# sensor constants for the noise plant (ISO 50 low-gain, from the project
# profile: g = ISO/436.8 with the ISO-50 pull reading out at base gain)
GAIN_DN_PER_E = 100.0 / 436.8
READ_NOISE_E = 1.2392


def run_case(fc_true, angle_deg, h, w, lo, hi, sigma_um, seed,
             bin_um, half_um, f_lo, f_hi, taper=0.25, sub=4):
    rng = np.random.default_rng(seed)
    img = L.synth_edge_frame(h, w, fc_true, angle_deg, lo, hi,
                             sigma_um=sigma_um, sub=sub, axis="horizontal")
    noisy = L.add_sensor_noise(img, GAIN_DN_PER_E, READ_NOISE_E, rng)
    res = L.measure_sfr(noisy, (0, 0, h, w), "G1", "horizontal",
                        bin_um, half_um, taper_frac=taper, n_segments=4)
    f, mtf = res["freq_cymm"], res["mtf"]
    floor = L.noise_floor_mtf(f, mtf)
    fit = L.fit_fc(f, mtf, f_lo, f_hi)
    bound = L.signal_bound(f, mtf, floor)
    return res, dict(fc_true=fc_true, sigma_true=sigma_um, angle=angle_deg,
                     contrast=res["contrast"], floor=floor, bound=bound,
                     **fit)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    BIN, HALF = 1.28, 96.0
    F_LO, F_HI = 10.0, 150.0
    rows = []
    print(f"{'fc_true':>8} {'sig_t':>6} {'ang':>5} {'fc_fit':>8} {'err%':>7} "
          f"{'sig_fit':>8} {'bound':>7} {'floor':>8} {'rms':>7}")
    for fc_true in (60.0, 86.3, 110.0, 140.0):
        for sigma_um in (0.0, 2.0):
            for angle in (2.0, 5.0):
                res, r = run_case(fc_true, angle, 240, 1600, 200.0, 4000.0,
                                  sigma_um, 12345, BIN, HALF, F_LO, F_HI)
                err = 100.0 * (r["fc_cymm"] - fc_true) / fc_true
                r["err_pct"] = err
                rows.append(r)
                print(f"{fc_true:8.1f} {sigma_um:6.1f} {angle:5.1f} "
                      f"{r['fc_cymm']:8.2f} {err:+7.2f} {r['sigma_um']:8.3f} "
                      f"{r['bound']:7.1f} {r['floor']:8.5f} "
                      f"{r['rms_resid']:7.4f}")
    (OUT / "s02_positive_control.json").write_text(
        json.dumps(rows, indent=1), encoding="utf-8")

    # seed repeats at the operating point, for a spread
    print("\nseed repeats at fc=86.3, sigma=0, angle=2 deg")
    vals = []
    for seed in range(8):
        _, r = run_case(86.3, 2.0, 240, 1600, 200.0, 4000.0, 0.0, 1000 + seed,
                        BIN, HALF, F_LO, F_HI)
        vals.append(r["fc_cymm"])
        print(f"  seed {seed}: fc = {r['fc_cymm']:.3f}  sigma = {r['sigma_um']:.3f}")
    v = np.array(vals)
    print(f"  mean {v.mean():.3f}  sd {v.std(ddof=1):.4f}  "
          f"bias {100*(v.mean()-86.3)/86.3:+.3f}%")


if __name__ == "__main__":
    main()
