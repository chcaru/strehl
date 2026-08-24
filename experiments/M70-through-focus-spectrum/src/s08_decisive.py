"""M70 s08 - the decisive characterisation.

Runs on the corrected (unclipped) estimator from s07, whose controls pass:
static burst 40.1/41, flat-noise negative control -0.9 to -0.2, plant recovery
0.977-1.011 across a 16x step-density sweep.

Five things, in the order they bear on the charter:

  A. HOW MANY FRAMES carry mid-band signal distinguishably above the noise
     floor. A direct count, not a weighted proxy: the per-frame band-power
     estimator's own sampling sd is measured by Monte Carlo at the exact patch
     and tile geometry, and frames are counted at z = 3.

  B. A REAL-DATA rule-20 discharge. The low band (0.025-0.050 cyc/px) is nearly
     focus-invariant, so on real corpus data n_eff there should approach K. If
     it does, the estimator demonstrably reports "nearly every frame carries
     signal" when that is true of real frames - not only of a synthetic plant.

  C. WHERE THE SUM SATURATES. n_eff and the matched-filter gain are recomputed
     with the frame window clamped to +-W for W = 1,2,3,5,10,20,inf. The window
     also bounds how much noise-model error can accumulate: the unwindowed sum
     accumulates K times the per-frame model error, which is why s07's +-25%
     sigma sweep was unstable on the deep stacks.

  D. SIGMA SENSITIVITY at the MEASURED uncertainty of the noise model
     (fact 29: floor/model 0.950-1.093x; M70's own reproduction 0.977-0.996x)
     as well as at the pre-registered +-25%. The pre-registered result stands
     as reported; this is a declared post-hoc refinement.

  E. THE APERTURE SPLIT. Six of twelve stacks are at marked f/5.6, three at
     f/8 and three at f/11 - so the brief's f/11 framing covers a quarter of
     the corpus. b6 (0.2762-0.3400 cyc/px) is above the f/11 diffraction cutoff
     and inside the f/5.6 and f/8 passbands, and is reported per aperture.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
from m70lib import L  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402

OUT = A5.OUT
STACKS = S7.STACKS
APERTURE = S7.APERTURE
Z = 3.0
MC = 400


def band_sd_units():
    """Sampling sd of the band-power estimate, in units of sigma^2, at the
    exact patch/tile geometry used by s04. Measured, not assumed."""
    rng = np.random.default_rng(8008)
    acc = {b[0]: [] for b in M.BANDS}
    for _ in range(MC):
        img = 1000.0 + rng.normal(0.0, 1.0, (256, 256))
        f, p, c = L.spectrum(img, "GQ", tile=128, window="hann", sector="iso")
        ba = M.band_average(f, p, c)
        for name, _lo, _hi in M.BANDS:
            acc[name].append(ba[name][0])
    return {k: float(np.std(v)) for k, v in acc.items()}, {
        k: float(np.mean(v)) for k, v in acc.items()
    }


def windowed(s, W):
    ssm = M.smooth3(s)
    i = int(np.argmax(ssm))
    den = max(float(ssm[i]), 1e-30)
    if W is None:
        sel = s
    else:
        sel = s[max(0, i - W): min(s.size, i + W + 1)]
    n_eff = float(sel.sum() / den)
    tot = float(sel.sum())
    out = {"n_eff": n_eff}
    for m in (1, 2, 3, 5):
        top = np.sort(sel)[::-1][:m]
        d = float(np.sqrt(np.clip(top, 0.0, None)).sum())
        out[f"g{m}"] = float(np.sqrt(max(tot, 0.0)) * np.sqrt(m) / d) if d > 0 else np.nan
    return out


def main() -> None:
    sd_u, mean_u = band_sd_units()
    print("=" * 104)
    print("0. THE BAND-POWER ESTIMATOR'S OWN SAMPLING SD (Monte Carlo, "
          f"{MC} noise realisations, 256-sample GQ patch, tile 128)")
    print("=" * 104)
    for name, lo, hi in M.BANDS:
        print(f"  {name:18s} {lo:.4f}-{hi:.4f} cyc/px   mean {mean_u[name]:7.4f} sigma^2"
              f"   sd {sd_u[name]:7.4f} sigma^2")
    print("  (mean ~1.000 confirms m5_lib.welch_psd2's absolute normalisation on this "
          "geometry.)")

    rows = []
    for st in STACKS:
        d = A5.load(st)
        s, nvar = A5.signal(d)
        tex, _ = A5.classify(d, s, nvar)
        K = s.shape[0]
        r = {"stack": st, "K": K, "F": APERTURE[st], "iso": d["iso"],
             "n_tex": int(tex.sum())}

        # A. direct count of frames above the noise floor at z = 3
        for b in M.MID_BANDS + ("b1_low", "b6_above_f11_cut"):
            j = d["bands"].index(b)
            thr = Z * sd_u[b] * nvar  # (K, P) DN^2
            cnt = [(s[:, p, j] > thr[:, p]).sum() for p in range(s.shape[1])]
            r[f"cnt_{b}"] = A5.med([cnt[p] for p in range(len(cnt)) if tex[p]])
            r[f"cntfrac_{b}"] = r[f"cnt_{b}"] / K
        r["cnt_mid"] = float(np.mean([r[f"cnt_{b}"] for b in M.MID_BANDS]))
        r["cntfrac_mid"] = r["cnt_mid"] / K

        # B. real-data rule-20 discharge: the near-focus-invariant low band
        jl = d["bands"].index("b1_low")
        r["low_n_eff"] = A5.med([S7.tf_stats_uc(s[:, p, jl])["n_eff_uc"]
                                 for p in range(s.shape[1]) if tex[p]])
        r["low_n_eff_frac"] = r["low_n_eff"] / K
        r["low_rel_amp_1"] = A5.med([S7.tf_stats_uc(s[:, p, jl])["rel_amp_1"]
                                     for p in range(s.shape[1]) if tex[p]])

        # C. window sweep
        for W in (1, 2, 3, 5, 10, 20, None):
            key = "inf" if W is None else str(W)
            ne, g3, g1 = [], [], []
            for b in M.MID_BANDS:
                j = d["bands"].index(b)
                vals = [windowed(s[:, p, j], W) for p in range(s.shape[1]) if tex[p]]
                ne.append(A5.med([v["n_eff"] for v in vals]))
                g3.append(A5.med([v["g3"] for v in vals]))
                g1.append(A5.med([v["g1"] for v in vals]))
            r[f"w{key}_n_eff"] = float(np.mean(ne))
            r[f"w{key}_g3"] = float(np.mean(g3))
            r[f"w{key}_g1"] = float(np.mean(g1))
        rows.append(r)

    print()
    print("=" * 116)
    print(f"A. FRAMES CARRYING MID-BAND SIGNAL ABOVE THE NOISE FLOOR (z = {Z}), "
          "median over textured patches")
    print("=" * 116)
    print(f"{'stack':16s} {'K':>4s} {'F':>5s} {'cnt_mid':>8s} {'frac':>6s} "
          f"{'b3':>6s} {'b4':>6s} {'b5':>6s} {'b1_low':>7s} {'lowfrac':>8s} {'b6':>6s}")
    for r in rows:
        print(f"{r['stack']:16s} {r['K']:4d} {r['F']:5.1f} {r['cnt_mid']:8.1f} "
              f"{r['cntfrac_mid']:6.3f} {r['cnt_b3_mid']:6.1f} {r['cnt_b4_mid']:6.1f} "
              f"{r['cnt_b5_mid']:6.1f} {r['cnt_b1_low']:7.1f} "
              f"{r['cntfrac_b1_low']:8.3f} {r['cnt_b6_above_f11_cut']:6.1f}")

    print()
    print("=" * 116)
    print("B. REAL-DATA RULE-20 DISCHARGE - the near-focus-invariant low band")
    print("=" * 116)
    print(f"{'stack':16s} {'K':>4s} {'low n_eff':>10s} {'/K':>6s} {'low relA1':>10s} "
          f"{'mid n_eff':>10s} {'ratio':>6s}")
    for r in rows:
        print(f"{r['stack']:16s} {r['K']:4d} {r['low_n_eff']:10.2f} "
              f"{r['low_n_eff_frac']:6.3f} {r['low_rel_amp_1']:10.3f} "
              f"{r['winf_n_eff']:10.2f} {r['winf_n_eff'] / max(r['low_n_eff'], 1e-9):6.3f}")
    print("  If the low band returns a large fraction of K on REAL frames while the")
    print("  mid band does not, the estimator is demonstrably able to report a wide")
    print("  through-focus response on real data and is not doing so at mid band.")

    print()
    print("=" * 116)
    print("C. WHERE THE MATCHED FILTER'S SUM SATURATES - n_eff and gain vs frame window")
    print("=" * 116)
    hdr = f"{'stack':16s} {'K':>4s}"
    for w in ("1", "2", "3", "5", "10", "20", "inf"):
        hdr += f" {'+-' + w:>7s}"
    print(hdr + "     | gain over the single best frame, sqrt(n_eff)")
    for r in rows:
        line = f"{r['stack']:16s} {r['K']:4d}"
        for w in ("1", "2", "3", "5", "10", "20", "inf"):
            line += f" {r[f'w{w}_n_eff']:7.2f}"
        line += "     |"
        for w in ("3", "5", "inf"):
            line += f" {np.sqrt(max(r[f'w{w}_n_eff'], 0)):5.2f}"
        print(line)

    print()
    print(f"{'stack':16s} {'K':>4s}  gain over averaging the best 3 frames, by window")
    for r in rows:
        line = f"{r['stack']:16s} {r['K']:4d}"
        for w in ("3", "5", "10", "20", "inf"):
            line += f" {'+-' + w + ':':>6s}{r[f'w{w}_g3']:6.3f}"
        print(line)

    print()
    print("=" * 116)
    print("D. SIGMA SENSITIVITY at the MEASURED model uncertainty (declared post-hoc)")
    print("=" * 116)
    print("  fact 29: floor/photon-transfer-model 0.950-1.093x over n=15.")
    print("  M70's own reproduction on 109MSDCF: 0.977-0.996x over 22 frames.")
    print(f"{'sigma scale':>12s} {'med mid n_eff (inf)':>20s} {'med n_eff (+-5)':>17s} "
          f"{'med g3 (+-5)':>13s} {'med relA1':>10s} {'med relA2':>10s}")
    sens = {}
    for sc in (0.75, 0.91, 0.95, 1.0, 1.05, 1.09, 1.25):
        ne_inf, ne_5, g3_5, a1, a2 = [], [], [], [], []
        for st in STACKS:
            d = A5.load(st)
            s, nvar = A5.signal(d, sc)
            tex, _ = A5.classify(d, s, nvar)
            vi, v5, vg, va1, va2 = [], [], [], [], []
            for b in M.MID_BANDS:
                j = d["bands"].index(b)
                idx = [p for p in range(s.shape[1]) if tex[p]]
                vi.append(A5.med([windowed(s[:, p, j], None)["n_eff"] for p in idx]))
                w5 = [windowed(s[:, p, j], 5) for p in idx]
                v5.append(A5.med([w["n_eff"] for w in w5]))
                vg.append(A5.med([w["g3"] for w in w5]))
                st5 = [S7.tf_stats_uc(s[:, p, j]) for p in idx]
                va1.append(A5.med([x["rel_amp_1"] for x in st5]))
                va2.append(A5.med([x["rel_amp_2"] for x in st5]))
            ne_inf.append(np.mean(vi))
            ne_5.append(np.mean(v5))
            g3_5.append(np.mean(vg))
            a1.append(np.mean(va1))
            a2.append(np.mean(va2))
        sens[sc] = {"n_eff_inf": float(np.median(ne_inf)), "n_eff_5": float(np.median(ne_5)),
                    "g3_5": float(np.median(g3_5)), "relA1": float(np.median(a1)),
                    "relA2": float(np.median(a2)),
                    "n_eff_inf_all": [float(x) for x in ne_inf],
                    "n_eff_5_all": [float(x) for x in ne_5],
                    "g3_5_all": [float(x) for x in g3_5],
                    "relA2_all": [float(x) for x in a2]}
        print(f"{sc:12.2f} {sens[sc]['n_eff_inf']:20.3f} {sens[sc]['n_eff_5']:17.3f} "
              f"{sens[sc]['g3_5']:13.3f} {sens[sc]['relA1']:10.3f} {sens[sc]['relA2']:10.3f}")

    print()
    print("  Criteria re-scored at each sigma, using the +-5-frame window (which bounds")
    print("  accumulated model error to 11 frames instead of K):")
    for sc in (0.75, 0.91, 0.95, 1.0, 1.05, 1.09, 1.25):
        v = sens[sc]
        n = len(STACKS)
        a_sup = sum(1 for x in v["relA2_all"] if x >= 0.30)
        b_core = sum(1 for x in v["n_eff_5_all"] if np.sqrt(max(x, 0)) >= 1.50)
        b_plug = sum(1 for x in v["n_eff_5_all"] if np.sqrt(max(x, 0)) <= 1.25)
        c_core = sum(1 for x in v["g3_5_all"] if x >= 1.30)
        c_plug = sum(1 for x in v["g3_5_all"] if x <= 1.10)
        A = "SUPPORTS" if a_sup >= 6 else ("REFUTES" if (n - a_sup) >= 9 else "INDET")
        B = "CORE" if b_core >= 7 else ("PLUGIN" if b_plug >= 7 else "INDET")
        C = "CORE" if c_core >= 7 else ("PLUGIN" if c_plug >= 7 else "INDET")
        print(f"    sigma x{sc:.2f}:  A {A:9s} ({a_sup}/{n})   B {B:6s} "
              f"(core {b_core}, plug {b_plug})   C {C:6s} (core {c_core}, plug {c_plug})")

    print()
    print("=" * 116)
    print("E. APERTURE SPLIT - b6 (0.2762-0.3400 cyc/px) is ABOVE the f/11 diffraction")
    print("   cutoff and INSIDE the f/5.6 and f/8 passbands (fact 27/28, B=3)")
    print("=" * 116)
    for ap in (5.6, 8.0, 11.0):
        sel = [r for r in rows if r["F"] == ap]
        fc = M.f_cutoff_sensor(ap)
        print(f"  f/{ap:<4.1f} n={len(sel)}  predicted cutoff {fc:.4f} cyc/px "
              f"({'inside' if fc < 0.3536 else 'ABOVE'} the GQ reach 0.3536)")
        print(f"          mid-band frames above floor {np.median([r['cnt_mid'] for r in sel]):6.1f}"
              f"   b6 frames above floor {np.median([r['cnt_b6_above_f11_cut'] for r in sel]):6.1f}"
              f"   n_eff(+-5) {np.median([r['w5_n_eff'] for r in sel]):5.2f}")

    with open(os.path.join(OUT, "s08_decisive.json"), "w", encoding="utf-8") as fh:
        json.dump({"band_sd_sigma2_units": sd_u, "band_mean_sigma2_units": mean_u,
                   "rows": rows, "sigma_sensitivity": {str(k): v for k, v in sens.items()}},
                  fh, indent=1)
    print("\nwrote out/s08_decisive.json")


if __name__ == "__main__":
    main()
