"""s04: instrument specification.  SYNTHETIC ONLY.

Produces the bias/precision table that the pre-registration freezes, using the
frequency-dependent noise floor.  Run before any real capture is measured.
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
BIN_UM, HALF_UM, TAPER = 0.64, 192.0, 0.10
F_LO, F_HI = 10.0, 150.0
NB = (250.0, 380.0)
Z, RUN = 3.0, 3


def analyse(res):
    f, mtf = res["freq_cymm"], res["mtf"]
    fl, flat = L.noise_floor_curve(f, mtf, BIN_UM, NB)
    fit = L.fit_fc(f, mtf, F_LO, F_HI)
    bound = L.signal_bound_curve(f, mtf, fl, Z, RUN)
    return dict(bound=bound, flat=flat, **fit)


def plant(fc, seed, disc=0.0, angle=2.7, h=260, w=1800):
    img = L.synth_edge_frame2(h, w, fc, angle, 200.0, 4000.0, disc_um=disc,
                              sub=6)
    noisy = L.add_sensor_noise(img, GAIN, RN_E, np.random.default_rng(seed))
    return L.measure_sfr(noisy, (0, 0, h, w), "G1", "horizontal", BIN_UM,
                         HALF_UM, taper_frac=TAPER)


def main():
    log = {}
    print("=== instrument calibration: bias and precision of E1 (fit) and "
          "E2 (model-free bound) ===")
    print(f"{'fc_true':>8} {'E1 mean':>9} {'E1 sd':>7} {'bias%':>7} "
          f"{'sd%':>6} {'E2 mean':>9} {'E2/true':>8} {'sig_fit':>8}")
    tab = {}
    for fc in (60.0, 86.3, 110.0, 140.0):
        rs = [analyse(plant(fc, s)) for s in range(101, 111)]
        e1 = np.array([r["fc_cymm"] for r in rs])
        e2 = np.array([r["bound"] for r in rs], float)
        sg = np.array([r["sigma_um"] for r in rs])
        tab[str(fc)] = dict(e1=e1.tolist(), e2=e2.tolist(), sigma=sg.tolist())
        print(f"{fc:8.1f} {e1.mean():9.3f} {e1.std(ddof=1):7.3f} "
              f"{100*(e1.mean()-fc)/fc:+7.2f} {100*e1.std(ddof=1)/fc:6.2f} "
              f"{np.nanmean(e2):9.1f} {np.nanmean(e2)/fc:8.3f} "
              f"{sg.mean():8.3f}")
    log["calibration"] = tab

    all_bias = []
    for fc in (60.0, 86.3, 110.0, 140.0):
        e1 = np.array(tab[str(fc)]["e1"])
        all_bias.append(100 * (e1 - fc) / fc)
    ab = np.concatenate(all_bias)
    print(f"\npooled E1 relative error over 60-140 cy/mm: "
          f"mean {ab.mean():+.2f}%  sd {ab.std(ddof=1):.2f}%  "
          f"range {ab.min():+.2f}% to {ab.max():+.2f}%")
    log["pooled"] = dict(mean_pct=ab.mean(), sd_pct=ab.std(ddof=1),
                         min_pct=ab.min(), max_pct=ab.max())

    print("\n=== reach proof with the frequency-dependent floor ===")
    for fc in (110.0, 140.0):
        e2 = np.array(tab[str(fc)]["e2"], float)
        print(f"  planted {fc}: E2 = {np.nanmin(e2):.1f}-{np.nanmax(e2):.1f} "
              f"cy/mm  vs CFA-plane Nyquist {L.CFA_PLANE_NYQUIST_CYMM:.2f} "
              f"-> {'PASS' if np.nanmin(e2) > L.CFA_PLANE_NYQUIST_CYMM else 'FAIL'}")

    print("\n=== sigma-gate check: does sigma_fit flag the unreliable cases? ===")
    for disc in (0.0, 8.0, 16.0, 30.0, 60.0):
        r = analyse(plant(110.0, 201, disc=disc))
        gate = "REPORT" if r["sigma_um"] < 3.0 else "ABSTAIN"
        print(f"  disc={disc:5.1f}um  fc_fit={r['fc_cymm']:8.2f} "
              f"sigma_fit={r['sigma_um']:6.2f}  E2={r['bound']:7.1f}  -> {gate}")
        log[f"disc_{disc}"] = r

    print("\n=== negative controls with the frequency-dependent floor ===")
    rng = np.random.default_rng(301)
    flat = np.full((260, 1800), 2100.0)
    try:
        noisy = L.add_sensor_noise(flat, GAIN, RN_E, rng)
        r = analyse(L.measure_sfr(noisy, (0, 0, 260, 1800), "G1",
                                  "horizontal", BIN_UM, HALF_UM,
                                  taper_frac=TAPER))
        print(f"  flat field: E1={r['fc_cymm']:.1f} E2={r['bound']} "
              f"-> {'PASS' if not np.isfinite(r['bound']) or r['bound'] < 50 else 'FAIL'}")
        log["neg_flat"] = r
    except L.EdgeFitError as e:
        print(f"  flat field: instrument refused ({e}) -> PASS")
        log["neg_flat"] = {"refused": str(e)}

    (OUT / "s04_instrument_spec.json").write_text(
        json.dumps(log, indent=1, default=float), encoding="utf-8")
    print("\nwrote out/s04_instrument_spec.json")


if __name__ == "__main__":
    main()
