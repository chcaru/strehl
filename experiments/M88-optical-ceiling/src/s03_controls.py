"""s03: the control battery.  SYNTHETIC ONLY -- no real capture is read.

C1  positive control        : recover a planted cutoff, four values, two of
                              them ABOVE the 48.8 cy/mm Nyquist of a single
                              CFA colour plane and one above sensor Nyquist.
C1b reach proof             : the model-free bound alone must exceed
                              48.83 cy/mm on the high-cutoff plants.
C2  bookkeeping self-test   : the same plant measured on G1 and G2, and as a
                              vertical edge, must give the same cutoff.  A
                              factor-of-two error in the frequency axis is
                              exactly the error that would fake the answer.
C3  mis-specification       : extra blur as a DEFOCUS DISC, which the fit does
                              not model, at several diameters.
C4  negative control (flat) : no edge at all -- pure noise on a flat field.
C5  negative control (phase): the real d-coordinates shuffled, destroying the
                              edge while preserving every sample value.
C6  defocus placebo         : a heavily defocused plant must NOT report a
                              cutoff near the diffraction value.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out"
GAIN = 100.0 / 436.8
RN_E = 1.2392

BIN_UM = 0.64
HALF_UM = 192.0
TAPER = 0.10
F_LO, F_HI = 10.0, 150.0
NB1 = (150.0, 190.0)
NB2 = (250.0, 380.0)
Z_DETECT = 3.0
RUN_LEN = 3


def run_plant(img, seed, which="G1", axis="horizontal"):
    rng = np.random.default_rng(seed)
    noisy = L.add_sensor_noise(img, GAIN, RN_E, rng)
    h, w = img.shape
    res = L.measure_sfr(noisy, (0, 0, h, w), which, axis, BIN_UM, HALF_UM,
                        taper_frac=TAPER)
    f, mtf = res["freq_cymm"], res["mtf"]
    fl1 = L.noise_floor_mtf(f, mtf, NB1)
    fl2 = L.noise_floor_mtf(f, mtf, NB2)
    fit = L.fit_fc(f, mtf, F_LO, F_HI)
    bound = L.signal_bound(f, mtf, fl2, Z_DETECT, RUN_LEN)
    return res, dict(floor_nb1=fl1, floor_nb2=fl2, bound=bound, **fit)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = {}

    print("=== C1 / C1b  positive control + reach proof ===")
    print(f"{'fc_true':>8} {'seed':>5} {'fc_fit':>8} {'err%':>7} {'sig':>6} "
          f"{'amp':>6} {'bound':>7} {'nb1':>8} {'nb2':>8}")
    c1 = []
    for fc_true in (60.0, 86.3, 110.0, 140.0):
        img = L.synth_edge_frame2(260, 1800, fc_true, 2.7, 200.0, 4000.0,
                                  sub=6)
        for seed in (11, 12, 13, 14, 15):
            _, r = run_plant(img, seed)
            r["fc_true"] = fc_true
            r["seed"] = seed
            r["err_pct"] = 100 * (r["fc_cymm"] - fc_true) / fc_true
            c1.append(r)
            print(f"{fc_true:8.1f} {seed:5d} {r['fc_cymm']:8.3f} "
                  f"{r['err_pct']:+7.2f} {r['sigma_um']:6.3f} {r['amp']:6.3f} "
                  f"{r['bound']:7.1f} {r['floor_nb1']:8.5f} "
                  f"{r['floor_nb2']:8.5f}")
    log["C1"] = c1
    for fc_true in (110.0, 140.0):
        b = [r["bound"] for r in c1 if r["fc_true"] == fc_true]
        print(f"  C1b reach: fc_true={fc_true}: model-free bound "
              f"{min(b):.1f}-{max(b):.1f} cy/mm vs plane-Nyquist "
              f"{L.CFA_PLANE_NYQUIST_CYMM:.2f}  -> "
              f"{'PASS' if min(b) > L.CFA_PLANE_NYQUIST_CYMM else 'FAIL'}")

    print("\n=== C2  bookkeeping self-test (lattice and orientation) ===")
    c2 = []
    imgh = L.synth_edge_frame2(260, 1800, 110.0, 2.7, 200.0, 4000.0, sub=6)
    imgv = L.synth_edge_frame2(1800, 260, 110.0, 2.7, 200.0, 4000.0, sub=6,
                               axis="vertical")
    for tag, img, which, axis in (("G1 horiz", imgh, "G1", "horizontal"),
                                  ("G2 horiz", imgh, "G2", "horizontal"),
                                  ("G1 vert", imgv, "G1", "vertical"),
                                  ("G2 vert", imgv, "G2", "vertical")):
        _, r = run_plant(img, 21, which, axis)
        r["tag"] = tag
        c2.append(r)
        print(f"  {tag:9s} fc = {r['fc_cymm']:8.3f}  "
              f"(planted 110.0, err {100*(r['fc_cymm']-110)/110:+.2f}%)")
    log["C2"] = c2
    sp = max(x["fc_cymm"] for x in c2) / min(x["fc_cymm"] for x in c2)
    print(f"  spread across lattice/orientation = {sp:.4f}x "
          f"-> {'PASS' if sp < 1.10 else 'FAIL'} (a factor-2 axis error "
          f"would read 2.00x)")

    print("\n=== C3  mis-specification: extra blur is a DISC, model is Gaussian ===")
    c3 = []
    for fc_true in (86.3, 110.0):
        for disc in (0.0, 4.0, 8.0, 16.0):
            img = L.synth_edge_frame2(260, 1800, fc_true, 2.7, 200.0, 4000.0,
                                      disc_um=disc, sub=6)
            _, r = run_plant(img, 31)
            r.update(fc_true=fc_true, disc_um=disc,
                     err_pct=100 * (r["fc_cymm"] - fc_true) / fc_true)
            c3.append(r)
            print(f"  fc_true={fc_true:6.1f} disc={disc:5.1f}um  "
                  f"fc={r['fc_cymm']:8.3f} ({r['err_pct']:+6.2f}%)  "
                  f"sigma_fit={r['sigma_um']:6.3f}  bound={r['bound']:6.1f}")
    log["C3"] = c3

    print("\n=== C4  negative control: flat field, no edge ===")
    rng = np.random.default_rng(41)
    flat = np.full((260, 1800), 2100.0)
    try:
        _, r = run_plant(flat, 41)
        print(f"  fc_fit = {r['fc_cymm']:.3f}  bound = {r['bound']}  "
              f"floor_nb2 = {r['floor_nb2']:.4f}  amp = {r['amp']:.4f}")
        log["C4"] = r
        ok = (not np.isfinite(r["bound"])) or r["bound"] < 50.0
        print(f"  -> {'PASS' if ok else 'FAIL'} "
              f"(must not report a bound near the diffraction cutoff)")
    except L.EdgeFitError as e:
        print(f"  instrument refused: {e}  -> PASS")
        log["C4"] = {"refused": str(e)}

    print("\n=== C5  phase-destroying placebo on a real-shaped plant ===")
    img = L.synth_edge_frame2(260, 1800, 110.0, 2.7, 200.0, 4000.0, sub=6)
    rng = np.random.default_rng(51)
    noisy = L.add_sensor_noise(img, GAIN, RN_E, rng)
    sub_, xs, ys = L.green_sites(noisy, "G1")
    line = L.fit_edge_line(sub_, xs, ys, axis="horizontal")
    XX, YY = np.meshgrid(xs, ys)
    vals = sub_.ravel().copy()
    perm = np.random.default_rng(52).permutation(vals.size)
    r5 = L.sfr_from_sites(vals[perm], XX.ravel(), YY.ravel(), line,
                          BIN_UM, HALF_UM, TAPER)
    fl2 = L.noise_floor_mtf(r5["freq_cymm"], r5["mtf"], NB2)
    b5 = L.signal_bound(r5["freq_cymm"], r5["mtf"], fl2, Z_DETECT, RUN_LEN)
    print(f"  shuffled-value placebo: bound = {b5}  floor = {fl2:.4f}")
    log["C5"] = {"bound": b5, "floor_nb2": fl2}
    ok5 = (not np.isfinite(b5)) or b5 < 50.0
    print(f"  -> {'PASS' if ok5 else 'FAIL'}")

    print("\n=== C6  defocus placebo: heavily defocused plant ===")
    c6 = []
    for disc in (30.0, 60.0):
        img = L.synth_edge_frame2(260, 1800, 110.0, 2.7, 200.0, 4000.0,
                                  disc_um=disc, sub=6)
        _, r = run_plant(img, 61)
        r["disc_um"] = disc
        c6.append(r)
        print(f"  disc={disc:5.1f}um  fc_fit={r['fc_cymm']:8.3f}  "
              f"bound={r['bound']:6.1f}  sigma_fit={r['sigma_um']:6.2f}")
    log["C6"] = c6

    (OUT / "s03_controls.json").write_text(json.dumps(log, indent=1,
                                                      default=float),
                                           encoding="utf-8")
    print("\nwrote out/s03_controls.json")


if __name__ == "__main__":
    main()
