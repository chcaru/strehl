"""s02c: instrument calibration sweep on SYNTHETIC data only.

Chooses bin width, ESF half-width, taper and fitting band BEFORE any real
capture's cutoff is computed.  Nothing here reads a real file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

GAIN = 100.0 / 436.8
RN_E = 1.2392


def one(fc_true, angle, sigma_um, seed, bin_um, half_um, taper, f_lo, f_hi,
        h=260, w=1800, lo=200.0, hi=4000.0, sub=6):
    rng = np.random.default_rng(seed)
    img = L.synth_edge_frame(h, w, fc_true, angle, lo, hi, sigma_um=sigma_um,
                             sub=sub, axis="horizontal")
    noisy = L.add_sensor_noise(img, GAIN, RN_E, rng)
    res = L.measure_sfr(noisy, (0, 0, h, w), "G1", "horizontal", bin_um,
                        half_um, taper_frac=taper)
    f, mtf = res["freq_cymm"], res["mtf"]
    floor = L.noise_floor_mtf(f, mtf)
    fit = L.fit_fc(f, mtf, f_lo, f_hi)
    bound = L.signal_bound(f, mtf, floor)
    return res, floor, fit, bound


def main():
    print("A. geometry sweep, fc=86.3, sigma=0, angle=2, seed=11")
    print(f"{'bin':>5} {'half':>6} {'taper':>6} {'fhi':>5} {'fc':>8} "
          f"{'err%':>7} {'sig':>7} {'amp':>6} {'floor':>8} {'minbin':>7}")
    for bin_um, half_um in ((1.28, 96.0), (0.64, 192.0), (0.64, 128.0),
                            (0.6, 192.0), (0.8, 192.0)):
        for taper in (0.10, 0.25):
            for f_hi in (120.0, 150.0):
                try:
                    res, floor, fit, bound = one(86.3, 2.0, 0.0, 11, bin_um,
                                                 half_um, taper, 10.0, f_hi)
                except L.EdgeFitError as e:
                    print(f"{bin_um:5.2f} {half_um:6.1f} {taper:6.2f} "
                          f"{f_hi:5.0f}  FAIL {e}")
                    continue
                err = 100 * (fit["fc_cymm"] - 86.3) / 86.3
                print(f"{bin_um:5.2f} {half_um:6.1f} {taper:6.2f} {f_hi:5.0f} "
                      f"{fit['fc_cymm']:8.3f} {err:+7.2f} {fit['sigma_um']:7.3f} "
                      f"{fit['amp']:6.3f} {floor:8.5f} "
                      f"{int(res['count'].min()):7d}")

    print("\nB. planted-cutoff ladder at the chosen geometry "
          "(bin 0.64, half 192, taper 0.10, band 10-150)")
    print(f"{'fc_true':>8} {'sig_t':>6} {'ang':>5} {'fc':>8} {'err%':>7} "
          f"{'sig':>7} {'amp':>6} {'bound':>7} {'floor':>8}")
    for fc_true in (60.0, 86.3, 110.0, 140.0):
        for sigma_um in (0.0, 2.0, 4.0):
            for angle in (2.0, 5.0):
                res, floor, fit, bound = one(fc_true, angle, sigma_um, 11,
                                             0.64, 192.0, 0.10, 10.0, 150.0)
                err = 100 * (fit["fc_cymm"] - fc_true) / fc_true
                print(f"{fc_true:8.1f} {sigma_um:6.1f} {angle:5.1f} "
                      f"{fit['fc_cymm']:8.3f} {err:+7.2f} {fit['sigma_um']:7.3f} "
                      f"{fit['amp']:6.3f} {bound:7.1f} {floor:8.5f}")


if __name__ == "__main__":
    main()
