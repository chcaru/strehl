"""Why does the forward model under-predict the measured cutoff?

ladder.py's first run rejected BOTH hypotheses. H3 fitted better (chi2 170 against
1307) but its own residuals were +8.97 and +9.37 sigma at f/14 and f/18: the real
cutoffs sit 10% to 14% ABOVE what the model says the estimator would report. A
systematic trend of one sign, growing toward the apertures that carry the
measurement, is a defect in the model and not noise in the data.

THE SUSPECT, NAMED BEFORE IT IS TESTED. The forward model matched each synthetic
scene to its aperture's measured LOW-band SNR, because equalise.equalise_to is
written to target the low band. But the crossing happens at the knee, and
snr_survey.py's own comment says so in as many words: the knee band "is where the
crossing actually lands, so this is the SNR that governs the bias". Matching the
wrong band would leave the synthetic scenes with the wrong amount of noise exactly
where it decides the answer. If the synthetic knee-band SNR comes out LOWER than
the real one, the synthetic estimator crosses sooner, the prediction is too low,
and every residual is positive -- which is what was observed.

THE ALTERNATIVE, WHICH WOULD BE WORSE. The real fabric may hold power past the
diffraction cutoff that a pure power law does not -- a broad weave shoulder rather
than the sharp harmonic T6 tested for and retired. T6's rule looked for a bin
RE-EMERGING above the floor after the spectrum first reached it. A shoulder that
merely delays the approach to the floor never re-emerges and would pass that test
untouched. If that is the cause, the measured cutoff is not a diffraction cutoff at
all and the lane is in real trouble.

The two are distinguishable: the first predicts the synthetic and real spectra
differ in FLOOR LEVEL near the knee, the second predicts they differ in the SHAPE
of the signal above it. This script measures both.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
M5 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m5-diffraction")
sys.path.insert(0, M5)

import m5_lib as L  # noqa: E402
from equalise import _scene, low_snr, equalise_to, floor_and_scene  # noqa: E402
from bias_ladder import HYP, PRIMARY, NYQ_SENSOR, N, TILE  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
TAGS = ["f5.6", "f8", "f11", "f14", "f18"]
EXACT_N = {"f5.6": 2 ** 2.5, "f8": 8.0, "f11": 2 ** 3.5,
           "f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}
KNEE_BAND = (0.150, 0.230)
LOW_BAND = (0.040, 0.090)


def band_snr(f, p, band):
    top = f >= 0.8 * f[-1]
    floor = float(np.median(p[top]))
    sel = (f >= band[0]) & (f <= band[1])
    if not sel.any() or floor <= 0:
        return float("nan"), floor
    return (float(np.mean(p[sel])) - floor) / floor, floor


def synth(fc, slope, target_low, seed, nrep=8):
    """Build the same scenes the forward model builds, and measure BOTH bands."""
    ks, ls, spec = [], [], []
    for k in range(nrep):
        rng = np.random.default_rng(seed + 977 * k)
        s = _scene(N, slope, fc * L.LATTICE_PITCH_PX["GQ"], rng)
        patch, _ = equalise_to(s + rng.normal(0.0, 5.0, (N, N)), target_low, rng,
                               tile=TILE)
        f, p, c = L.spectrum(patch, "GQ", tile=TILE, window="hann")
        kb, _ = band_snr(f, p, KNEE_BAND)
        lb, _ = band_snr(f, p, LOW_BAND)
        ks.append(kb)
        ls.append(lb)
        spec.append(p)
    return (float(np.median(ks)), float(np.median(ls)), f,
            np.median(np.array(spec), axis=0))


def main():
    with open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    with open(os.path.join(OUT, "slope-object.json"), encoding="utf-8") as fh:
        so = json.load(fh)
    recs = d["records"]

    print("does the forward model reproduce the real spectrum where it matters?")
    print("=" * 74)
    print("\n(1) the SNR the model matched, and the SNR that decides the answer")
    print(f"  {'ap':>6} {'real low':>10} {'real knee':>10} | "
          f"{'H2 low':>9} {'H2 knee':>9} | {'H3 low':>9} {'H3 knee':>9}")
    rows = []
    for t in TAGS:
        rl = float(np.median([r["bands"]["low"]["snr"] for r in recs
                              if r["aperture"] == t]))
        rk = float(np.median([r["bands"]["knee"]["snr"] for r in recs
                              if r["aperture"] == t]))
        cell = {"tag": t, "real_low": rl, "real_knee": rk}
        s = f"  {t:>6} {rl:10.1f} {rk:10.2f} |"
        for hname in ("H2", "H3"):
            fc = L.f_cutoff_sensor(HYP[hname]["B"] * EXACT_N[t], L.LAMBDA_UM)
            if fc >= NYQ_SENSOR:
                s += f" {'--':>9} {'--':>9} |"
                cell[f"{hname}_low"] = None
                cell[f"{hname}_knee"] = None
                continue
            kb, lb, _, _ = synth(fc, so["object"][hname][t], rl,
                                 71000 + int(97 * EXACT_N[t]))
            cell[f"{hname}_low"] = lb
            cell[f"{hname}_knee"] = kb
            s += f" {lb:9.1f} {kb:9.2f} |"
        rows.append(cell)
        print(s)

    print("\n  If the synthetic knee-band SNR is far BELOW the real one, the model's")
    print("  scenes are noisier than the data exactly where the crossing happens,")
    print("  the synthetic estimator crosses too early, and every residual comes")
    print("  out positive. That is the whole of the suspected defect.")
    for c in rows:
        if c["H3_knee"] is None:
            continue
        r = c["real_knee"] / c["H3_knee"] if c["H3_knee"] else float("nan")
        print(f"  {c['tag']:>6} real knee SNR is {r:6.2f}x the H3 synthetic")

    print("\n(2) the shape of the real spectrum against the model's, near the knee")
    print("=" * 74)
    print("  each spectrum divided by its own low-band mean, so only SHAPE is")
    print("  compared and the level difference measured in (1) cannot masquerade")
    print("  as a shape difference")
    shape = []
    for t in PRIMARY:
        rl = float(np.median([r["bands"]["low"]["snr"] for r in recs
                              if r["aperture"] == t]))
        fc = L.f_cutoff_sensor(HYP["H3"]["B"] * EXACT_N[t], L.LAMBDA_UM)
        _, _, fs, ps = synth(fc, so["object"]["H3"][t], rl,
                             71000 + int(97 * EXACT_N[t]))
        rr = [r for r in recs if r["aperture"] == t]
        fr = np.array(rr[0]["f"], float)
        pr = np.median(np.array([r["psd"] for r in rr], float), axis=0)

        def norm(f, p):
            sel = (f >= LOW_BAND[0]) & (f <= LOW_BAND[1])
            return p / float(np.mean(p[sel]))

        nr, ns = norm(fr, pr), norm(fs, ps)
        print(f"\n  {t}, H3 cutoff {fc:.4f}")
        print(f"    {'f':>8} {'cy/mm':>7} {'real':>11} {'synth H3':>11} "
              f"{'real/synth':>11}")
        for lo, hi in ((0.10, 0.13), (0.13, 0.16), (0.16, 0.19), (0.19, 0.22),
                       (0.22, 0.25), (0.25, 0.28), (0.28, 0.32)):
            a = (fr >= lo) & (fr < hi)
            b = (fs >= lo) & (fs < hi)
            if not a.any() or not b.any():
                continue
            va, vb = float(np.mean(nr[a])), float(np.mean(ns[b]))
            shape.append({"tag": t, "lo": lo, "hi": hi, "real": va, "synth": vb,
                          "ratio": va / vb if vb else float("nan")})
            print(f"    {0.5 * (lo + hi):8.3f} {0.5 * (lo + hi) * 1000 / L.PITCH_UM:7.1f} "
                  f"{va:11.3e} {vb:11.3e} {va / vb:11.2f}")

    print("\n  A ratio that is flat and above 1 means the real spectrum sits higher")
    print("  everywhere -- a level or floor difference, the (1) explanation. A ratio")
    print("  that GROWS with frequency means the real subject holds power the model")
    print("  does not, which would be the weave shoulder and a far worse problem.")

    with open(os.path.join(OUT, "ladder-diag.json"), "w", encoding="utf-8") as fh:
        json.dump({"snr": rows, "shape": shape}, fh, indent=1)
    print("\nwrote out/ladder-diag.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
