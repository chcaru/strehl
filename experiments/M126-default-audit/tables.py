"""M126-default-audit — turn scores.json into the report's tables.

Reads C:\\dev\\strehl-out\\M126\\scores.json (written by score.py) and applies
the bars registered in PREREG.md section 5. It adds no metric and no arm; it
only tabulates and applies the pre-registered rules.

    python experiments\\M126-default-audit\\tables.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\strehl-out\M126")

# PREREG section 5.
POWER_FLOOR = 0.50      # Q(A0) below this => the subject cannot carry a verdict.
B1_DD = -0.010          # detail must not fall by more than this.
B2_DQ = +0.010          # two-band quality must rise by at least this.
B3_IMPROVED = 0.50      # more than half the detail tiles must improve.
INSTRUMENT_DD = 0.010   # the perturbation control must read at least this.

SUBJECTS = ["bee-3-cpl", "lead-1-cpl", "leaf-2-cpl", "coffee-bean", "tweezers-cpl"]
DRIFT = {  # M122's measured Dpp %, used as the stratifier so it cannot be tuned here.
    "bee-3-cpl": 1.629, "lead-1-cpl": 2.026, "leaf-2-cpl": 5.315,
    "coffee-bean": 12.065, "tweezers-cpl": 13.765,
}
GATES = [
    ("G1-ca", "STREHL_FIX_CA"),
    ("G2-robust", "STREHL_ROBUST_ELECTION"),
    ("G3-smooth", "STREHL_SMOOTH"),
    ("G4-softgate", "STREHL_SOFT_GATE"),
    ("G5-photometric", "STREHL_PHOTOMETRIC / --photometric"),
    ("G6-halo", "STREHL_FIX_HALO"),
]
CONTROLS = ["N1-rerun", "P1-placebo", "P2-ungated", "PC-nearest",
            "PC2-nearest-solved", "M0-gate0"]


def main() -> int:
    d = json.loads((ROOT / "scores.json").read_text())
    powered = {}

    print("## Power floor (PREREG 5): a subject carries a verdict only if Q(A0) >= 0.50 dex\n")
    print(f"| subject | drift Dpp % | Q(A0) | powered |")
    print(f"|---|---|---|---|")
    for s in SUBJECTS:
        q = d[s]["aligned"]["arms"]["A0-default"]["Q"]
        powered[s] = q >= POWER_FLOOR
        print(f"| `{s}` | {DRIFT[s]:.3f} | {q:.4f} | {'YES' if powered[s] else '**NO**'} |")
    npow = sum(powered.values())
    print(f"\n{npow} of {len(SUBJECTS)} subjects are powered.\n")

    print("## Instrument checks (PREREG 5, rule 20)\n")
    print("| control | " + " | ".join(f"`{s}`" for s in SUBJECTS) + " | reads |")
    print("|---" * (len(SUBJECTS) + 2) + "|")
    for c in CONTROLS:
        row, vals = [], []
        for s in SUBJECTS:
            a = d[s]["aligned"]["arms"].get(c)
            if not a:
                row.append("--")
                continue
            ref = d[s]["aligned"]["arms"]["A0-default"]
            dd = a["D"] - ref["D"]
            vals.append(abs(dd))
            row.append(f"{dd:+.5f}")
        verdict = ("NULL" if max(vals) < 1e-9 else
                   "PERTURBS" if min(vals) >= INSTRUMENT_DD else "weak")
        print(f"| `{c}` | " + " | ".join(row) + f" | {verdict} |")

    print("\n## Degenerate baselines (PREREG 4): merge vs sharpest single frame, "
          "both STREHL_ALIGN=0, masks from M0u\n")
    print("| subject | drift | D(B1u)-D(B0) | Q(B1u) | Q(B0) | Q(B1u)-Q(B0) | who wins on Q |")
    print("|---|---|---|---|---|---|---|")
    for s in SUBJECTS:
        u = d[s]["unaligned"]["arms"]
        if "B0-single" not in u or "B1u-noalign" not in u:
            continue
        m, b = u["B1u-noalign"], u["B0-single"]
        dq = m["Q"] - b["Q"]
        print(f"| `{s}` | {DRIFT[s]:.3f} | {m['D'] - b['D']:+.5f} | {m['Q']:.5f} | "
              f"{b['Q']:.5f} | {dq:+.5f} | {'merge' if dq > 0 else '**single frame**'} |")

    for arm_label, title in (("A0-default", "the aligned default A0"),):
        print(f"\n## And the same contrast against {title} "
              "(different mask grid -- see the report's caveat)\n")
        print("| subject | Q(A0) | Q(B0) | Q(A0)-Q(B0) |")
        print("|---|---|---|---|")
        for s in SUBJECTS:
            u = d[s]["unaligned"]["arms"]
            if "B0-single" not in u:
                continue
            a = d[s]["aligned"]["arms"][arm_label]
            b = u["B0-single"]
            print(f"| `{s}` | {a['Q']:.5f} | {b['Q']:.5f} | {a['Q'] - b['Q']:+.5f} |")

    print("\n## Per-gate results, each gate ALONE against A0\n")
    for arm, env in GATES:
        print(f"\n### `{env}` -- arm `{arm}`\n")
        print("| subject | powered | dN | dD | dQ | detail tiles improved | B1 dD>=-0.010 | "
              "B2 dQ>=+0.010 | B3 >50% |")
        print("|---|---|---|---|---|---|---|---|---|")
        passes = 0
        for s in SUBJECTS:
            a = d[s]["aligned"]["arms"].get(arm)
            if not a:
                print(f"| `{s}` | -- | -- | -- | -- | -- | -- | -- | -- |")
                continue
            ref = d[s]["aligned"]["arms"]["A0-default"]
            dn, dd, dq = a["N"] - ref["N"], a["D"] - ref["D"], a["Q"] - ref["Q"]
            imp = a["tiles_detail"].get("improved_frac", float("nan"))
            b1, b2, b3 = dd >= B1_DD, dq >= B2_DQ, imp > B3_IMPROVED
            if powered[s] and b1 and b2 and b3:
                passes += 1
            print(f"| `{s}` | {'yes' if powered[s] else 'no'} | {dn:+.5f} | {dd:+.5f} | "
                  f"{dq:+.5f} | {100.0 * imp:.1f}% | {'PASS' if b1 else 'FAIL'} | "
                  f"{'PASS' if b2 else 'FAIL'} | {'PASS' if b3 else 'FAIL'} |")
        print(f"\nClears all three bars on **{passes} of {npow} powered subjects**.")

    print("\n## The combination: all five composable gates on, and drop-one-out\n")
    print("| arm | " + " | ".join(f"`{s}` dQ / dD / imp" for s in SUBJECTS) + " |")
    print("|---" * (len(SUBJECTS) + 1) + "|")
    for arm in ["ALL-on", "D1-noca", "D2-norobust", "D3-nosmooth",
                "D4-nosoftgate", "D5-nophotometric"]:
        row = []
        for s in SUBJECTS:
            a = d[s]["aligned"]["arms"].get(arm)
            ref = d[s]["aligned"]["arms"]["A0-default"]
            if not a:
                row.append("--")
                continue
            row.append(f"{a['Q'] - ref['Q']:+.5f} / {a['D'] - ref['D']:+.5f} / "
                       f"{100.0 * a['tiles_detail']['improved_frac']:.1f}%")
        print(f"| `{arm}` | " + " | ".join(row) + " |")

    print("\n## The chromatic metric (PREREG 3c) -- the only instrument that can see CA\n")
    print("| subject | band | X_R(A0) | X_R(G1) | dX_R | X_B(A0) | X_B(G1) | dX_B |")
    print("|---|---|---|---|---|---|---|---|")
    for s in SUBJECTS:
        a0 = d[s]["aligned"]["arms"]["A0-default"]["chromatic"]
        g1 = d[s]["aligned"]["arms"]["G1-ca"]["chromatic"]
        for band in ("outer", "inner"):
            if "X_R" not in a0.get(band, {}):
                continue
            print(f"| `{s}` | {band} | {a0[band]['X_R']:.5f} | {g1[band]['X_R']:.5f} | "
                  f"{g1[band]['X_R'] - a0[band]['X_R']:+.5f} | {a0[band]['X_B']:.5f} | "
                  f"{g1[band]['X_B']:.5f} | {g1[band]['X_B'] - a0[band]['X_B']:+.5f} |")

    print("\n## Plane-level identity against A0 (green / red / blue bitwise equal?)\n")
    print("| arm | " + " | ".join(f"`{s}`" for s in SUBJECTS) + " |")
    print("|---" * (len(SUBJECTS) + 1) + "|")
    for arm, _ in GATES:
        row = []
        for s in SUBJECTS:
            a = d[s]["aligned"]["arms"].get(arm)
            if not a:
                row.append("--")
                continue
            row.append("".join([
                "G" if a["green_identical_to_ref"] else "-",
                "R" if a["red_identical_to_ref"] else "-",
                "B" if a["blue_identical_to_ref"] else "-",
                "  (whole file identical)" if a["sha_equals_ref"] else ""]))
        print(f"| `{arm}` | " + " | ".join(row) + " |")

    return 0


if __name__ == "__main__":
    sys.exit(main())
