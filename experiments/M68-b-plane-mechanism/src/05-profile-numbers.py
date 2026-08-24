"""M68 step 05 - the numbers the report quotes for a profile.rs correction.

DESCRIPTIVE ONLY. This script does not touch crates/. It converts the
measured per-plane dark statistics into the two knobs `PlaneNoise` actually
has - `gain_dn_per_e` and `read_noise_e` - so the report can state what a
corrected model would say without anyone having to redo the algebra.

`profile.rs`'s DARK_SIGMA_RMS_DN is defined (module header) as a pooled RMS
temporal sigma over 20 dark frames with NO defect exclusion, so the ladder
is printed on the `none` arm to match that definition, and on `r6` for the
physics.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("m68", HERE / "src" / "01-dark-iso-sweep.py")
m68 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m68)

S_PTC, S_ERR = 0.8396, 0.0112       # M61 fact 22, B conversion gain / green
R_PTC = 0.985                        # M61, R conversion gain / green


def main() -> int:
    blob = json.loads((HERE / "data" / "01-dark-iso-sweep.json").read_text())
    isos = sorted(int(i) for i in blob["isos"])
    g = np.maximum(np.array(isos, float), m68.BASE_ISO)
    mode = (np.array(isos) >= 400).astype(int)

    def col(arm, plane, key):
        rows = {int(r["iso"]): r for r in blob["rows"][arm][plane]}
        return np.array([rows[i][key] for i in isos], float)

    for arm in ("none", "r6"):
        print(f"\n=== dark sigma ratios to pooled green, arm '{arm}' ===")
        gp = np.sqrt(0.5 * (col(arm, "G1", "var") + col(arm, "G2", "var")))
        print(f"{'ISO':>5s} {'sigma_Gpool':>12s} " +
              " ".join(f"{p + '/Gp':>9s}" for p in ("R", "B")))
        for i, iso in enumerate(isos):
            print(f"{iso:5d} {gp[i]:12.5f} " +
                  " ".join(f"{np.sqrt(col(arm, p, 'var'))[i] / gp[i]:9.5f}"
                           for p in ("R", "B")))
        vg = 0.5 * (col(arm, "G1", "var") + col(arm, "G2", "var"))
        fg = m68.fit_alpha_delta(g, mode, vg)
        for p in ("R", "B"):
            fp = m68.fit_alpha_delta(g, mode, col(arm, p, "var"))
            ra = fp["alpha_high"] / fg["alpha_high"]
            print(f"  {p}: alpha ratio {ra:.5f} -> asymptotic sigma ratio "
                  f"{np.sqrt(ra):.5f}")

    print("\n=== what a corrected PlaneNoise would carry (arm r6, alpha domain) ===")
    vg = 0.5 * (col("r6", "G1", "var") + col("r6", "G2", "var"))
    fg = m68.fit_alpha_delta(g, mode, vg)
    jkg = m68.jackknife(g, mode, vg)["alpha_high"]
    for p, ptc, ptc_e in (("R", R_PTC, 0.0), ("B", S_PTC, S_ERR)):
        v = col("r6", p, "var")
        f = m68.fit_alpha_delta(g, mode, v)
        ra = f["alpha_high"] / fg["alpha_high"]
        e = ra * np.hypot(m68.jackknife(g, mode, v)["alpha_high"] / f["alpha_high"],
                          jkg / fg["alpha_high"])
        sr = np.sqrt(ra)
        rn = sr / ptc
        print(f"\n  plane {p}")
        print(f"    gain_dn_per_e scale (M61 PTC, signal domain) : {ptc:.4f}")
        print(f"    dark sigma scale  (M68, alpha domain)        : {sr:.5f}"
              f" +/- {0.5 * e / sr:.5f}")
        print(f"    => read_noise_e scale = dark_sigma / gain    : {rn:.5f}")
        print(f"    shipped model uses 1.0000 for both.")
        print(f"    shipped predicted dark sigma / truth         : "
              f"{1.0 / sr:.4f}  ({100 * (1.0 / sr - 1):+.1f}%)")
        print(f"    'scale the gain only' fix, sigma / truth     : "
              f"{ptc / sr:.4f}  ({100 * (ptc / sr - 1):+.1f}%)")

    print("\n=== spatial residual left by a single per-plane constant ===")
    print("  from 04's 32 row bands, alpha_high ratio to same-parity green:")
    print("    B/G2 spans 0.8181 .. 0.8918 about a mean of 0.85235")
    for lo, hi, m in ((0.8181, 0.8918, 0.85235),):
        print(f"    -> in sigma: {np.sqrt(lo):.4f} .. {np.sqrt(hi):.4f} about "
              f"{np.sqrt(m):.4f}, i.e. {100 * (np.sqrt(lo) / np.sqrt(m) - 1):+.1f}%"
              f" .. {100 * (np.sqrt(hi) / np.sqrt(m) - 1):+.1f}%")
    print("    R/G1 spans 0.9537 .. 1.0267 about a mean of 0.98833")
    print(f"    -> in sigma: {np.sqrt(0.9537):.4f} .. {np.sqrt(1.0267):.4f} about "
          f"{np.sqrt(0.98833):.4f}, i.e. "
          f"{100 * (np.sqrt(0.9537 / 0.98833) - 1):+.1f}% .. "
          f"{100 * (np.sqrt(1.0267 / 0.98833) - 1):+.1f}%")

    print("\n=== position statistic f (WITHDRAWN as a point estimate by D1) ===")
    for lab, ra in (("array mean", 0.85235), ("top band", 0.8918),
                    ("bottom band", 0.8181)):
        print(f"  {lab:>12s}: alpha ratio {ra:.4f} -> f = "
              f"{(1 - ra) / (1 - S_PTC**2):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
