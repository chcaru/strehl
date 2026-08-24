"""s09: regression + repair control for the per-wing ESF deramp.

The repair is only admissible if (a) it recovers a planted cutoff on an edge
that carries planted wing ramps, where the unrepaired instrument fails, and
(b) it does not disturb the recovery on a clean edge.  Both arms are run here
on synthetic data, and the failing input is written down first.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out"
GAIN = 50.0 / 436.8
RN_E = 1.2392
BIN_UM, TAPER = 0.64, 0.10
F_LO, F_HI = 10.0, 150.0
NB = (250.0, 380.0)


def plant_with_ramps(h, w, fc, angle, lo, hi, slope_l, slope_r, sub=6):
    """Edge plus a DIFFERENT linear brightness ramp either side of it.

    slope_* are in DN per um of normal distance, matching the shape measured
    on 119MSDCF A1 (dark wing -3.43 DN/um, bright wing +5.39 DN/um).
    """
    img = L.synth_edge_frame2(h, w, fc, angle, lo, hi, sub=sub)
    a = np.radians(angle)
    nx, ny = -np.sin(a), np.cos(a)
    yy, xx = np.mgrid[0:h, 0:w]
    d_um = ((xx - 0.5 * w) * nx + (yy - 0.5 * h) * ny) * L.PITCH_UM
    return img + np.where(d_um < 0, slope_l * d_um, slope_r * d_um)


def run(img, seed, half_um, deramp, core_um=48.0):
    noisy = L.add_sensor_noise(np.maximum(img, 1.0), GAIN, RN_E,
                               np.random.default_rng(seed))
    s, xs, ys = L.green_sites(noisy, "G1")
    line = L.fit_edge_line(s, xs, ys, axis="horizontal")
    XX, YY = np.meshgrid(xs, ys)
    r = L.sfr_from_sites2(s.ravel().astype(float), XX.ravel(), YY.ravel(),
                          line, BIN_UM, half_um, TAPER, core_um=core_um,
                          deramp=deramp)
    f, mtf = r["freq_cymm"], r["mtf"]
    fl, flat = L.noise_floor_curve(f, mtf, BIN_UM, NB)
    fit = L.fit_fc(f, mtf, F_LO, F_HI)
    b = L.signal_bound_curve(f, mtf, fl, 3.0, 3)
    i40 = int(np.argmin(np.abs(f - 40.0)))
    return dict(fc=fit["fc_cymm"], sigma=fit["sigma_um"], amp=fit["amp"],
                bound=b, flat=flat, mtf40=float(mtf[i40]),
                slope_l=r["slope_l"], slope_r=r["slope_r"])


def main():
    log = {}
    print("The failing input, written down first (rule 20): an edge whose two")
    print("wings carry different linear brightness ramps.  With the single")
    print("constant pedestal the instrument must under-report the cutoff and")
    print("over-report sigma; with the per-wing deramp it must recover both.")
    print()
    print("=== R1  planted ramps, matched to what 119MSDCF A1 actually shows ===")
    print(f"{'fc_true':>8} {'half':>5} {'deramp':>7} {'fc':>8} {'err%':>7} "
          f"{'sigma':>6} {'amp':>6} {'mtf40':>7} {'floor':>8}")
    r1 = []
    for fc in (86.3, 110.0):
        img = plant_with_ramps(300, 1800, fc, 2.1, 1000.0, 3600.0,
                               -3.43, 5.39)
        for half in (192.0, 64.0):
            for dr in (False, True):
                d = run(img, 11, half, dr)
                d.update(fc_true=fc, half=half, deramp=dr,
                         err=100 * (d["fc"] - fc) / fc)
                r1.append(d)
                print(f"{fc:8.1f} {half:5.0f} {str(dr):>7} {d['fc']:8.2f} "
                      f"{d['err']:+7.2f} {d['sigma']:6.2f} {d['amp']:6.3f} "
                      f"{d['mtf40']:7.4f} {d['flat']:8.5f}")
    log["R1"] = r1

    print("\n=== R2  regression: clean edge, no ramps, deramp must not harm ===")
    print(f"{'fc_true':>8} {'half':>5} {'deramp':>7} {'fc':>8} {'err%':>7} "
          f"{'sigma':>6} {'amp':>6} {'mtf40':>7}")
    r2 = []
    for fc in (60.0, 86.3, 110.0, 140.0):
        img = L.synth_edge_frame2(300, 1800, fc, 2.1, 1000.0, 3600.0, sub=6)
        for half in (192.0, 64.0):
            for dr in (False, True):
                d = run(img, 12, half, dr)
                d.update(fc_true=fc, half=half, deramp=dr,
                         err=100 * (d["fc"] - fc) / fc)
                r2.append(d)
                print(f"{fc:8.1f} {half:5.0f} {str(dr):>7} {d['fc']:8.2f} "
                      f"{d['err']:+7.2f} {d['sigma']:6.2f} {d['amp']:6.3f} "
                      f"{d['mtf40']:7.4f}")
    log["R2"] = r2

    print("\n=== R3  can the deramp manufacture an edge?  Flat field + ramps ===")
    yy, xx = np.mgrid[0:300, 0:1800]
    a = np.radians(2.1)
    nx, ny = -np.sin(a), np.cos(a)
    d_um = ((xx - 900) * nx + (yy - 150) * ny) * L.PITCH_UM
    flat = 2300.0 + np.where(d_um < 0, -3.43 * d_um, 5.39 * d_um)
    try:
        d = run(flat, 13, 64.0, True)
        print(f"   fc={d['fc']:.2f} sigma={d['sigma']:.2f} amp={d['amp']:.3f} "
              f"bound={d['bound']} mtf40={d['mtf40']:.4f}")
        ok = (not np.isfinite(d["bound"])) or d["bound"] < 50.0
        print(f"   -> {'PASS' if ok else 'FAIL'} (no cutoff may be reported "
              f"from ramps alone)")
        log["R3"] = d
    except L.EdgeFitError as e:
        print(f"   instrument refused: {e} -> PASS")
        log["R3"] = {"refused": str(e)}

    (OUT / "s09_deramp_control.json").write_text(
        json.dumps(log, indent=1, default=float), encoding="utf-8")
    print("\nwrote out/s09_deramp_control.json")


if __name__ == "__main__":
    main()
