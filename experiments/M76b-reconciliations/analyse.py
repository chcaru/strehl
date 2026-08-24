from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"

ROWS = [
    ("109MSDCF", 1570.2, 106.02),
    ("112MSDCF", 122.7, 0.86),
    ("coffee-bean", 4762.1, 1104.45),
    ("bee-1", 2200.5, 115.77),
    ("bee-2", 2296.8, 158.27),
    ("bee-3", 2574.1, 113.77),
]
KAPPA = 0.003096


def slope(level: np.ndarray, value: np.ndarray) -> tuple[float, float]:
    x = np.log(level)
    y = np.log(value)
    return float(np.polyfit(x, y, 1)[0]), float(np.corrcoef(x, y)[0, 1] ** 2)


def main() -> None:
    m71 = json.loads(
        (ROOT / "experiments/M71-flat-fields/data/05-kappa.json").read_text(
            encoding="utf-8"
        )
    )
    ptc = json.loads(
        (ROOT / "experiments/M71-flat-fields/data/03-ptc.json").read_text(
            encoding="utf-8"
        )
    )

    level = np.array([r[1] for r in ROWS])
    e_flat = np.array([r[2] for r in ROWS])
    v_prnu = (KAPPA * level) ** 2
    fraction = v_prnu / e_flat
    remainder = e_flat - v_prnu
    exponent, r2 = slope(level, e_flat)
    rem_exponent, rem_r2 = slope(level, remainder)

    print("M76b ITEM 1 — M70 e_flat against M71 PRNU")
    print(f"kappa primary = {100*KAPPA:.4f}%")
    print(
        f"M71 pair range = {100*m71['kappa_min']:.4f}%"
        f"..{100*m71['kappa_max']:.4f}%"
    )
    print()
    print(
        f"{'stack':14s} {'level':>9s} {'e_flat':>10s} {'V_PRNU':>10s}"
        f" {'fraction':>10s} {'remainder':>11s} {'k_rem':>9s}"
    )
    rows_out = []
    for (name, lev, ef), vp, frac, rem in zip(
        ROWS, v_prnu, fraction, remainder
    ):
        k_rem = np.sqrt(rem) / lev
        print(
            f"{name:14s} {lev:9.1f} {ef:10.2f} {vp:10.2f}"
            f" {100*frac:9.1f}% {rem:11.2f} {100*k_rem:8.4f}%"
        )
        rows_out.append(
            {
                "stack": name,
                "level_dn": lev,
                "e_flat_dn2": ef,
                "v_prnu_dn2": float(vp),
                "fraction": float(frac),
                "remainder_dn2": float(rem),
                "remainder_equivalent_kappa": float(k_rem),
            }
        )

    ratio_sums = float(v_prnu.sum() / e_flat.sum())
    median_fraction = float(np.median(fraction))
    print()
    print(f"original exponent = {exponent:.4f}, R2 = {r2:.4f}")
    print(f"remainder exponent = {rem_exponent:.4f}, R2 = {rem_r2:.4f}")
    print(
        f"PRNU/e_flat ratio of sums = {100*ratio_sums:.2f}%"
        f"; median = {100*median_fraction:.2f}%"
        f"; range = {100*fraction.min():.2f}%..{100*fraction.max():.2f}%"
    )
    print(
        f"aggregate remainder = {remainder.sum():.2f} DN^2"
        f" of {e_flat.sum():.2f} DN^2"
    )

    envelopes = {}
    for label, k in (
        ("m71_pair_min", m71["kappa_min"]),
        ("m71_pair_max", m71["kappa_max"]),
    ):
        v = (k * level) ** 2
        envelopes[label] = {
            "kappa": k,
            "ratio_of_sums": float(v.sum() / e_flat.sum()),
            "cell_fraction_min": float((v / e_flat).min()),
            "cell_fraction_max": float((v / e_flat).max()),
        }
        print(
            f"{label}: ratio of sums {100*envelopes[label]['ratio_of_sums']:.2f}%"
            f", cell range {100*envelopes[label]['cell_fraction_min']:.2f}%"
            f"..{100*envelopes[label]['cell_fraction_max']:.2f}%"
        )

    g_meas = 0.5 * (ptc["G1"]["g"] + ptc["G2"]["g"])
    g_profile = 0.2289377
    sigma0 = 0.961538

    def shipped_error(signal: float) -> float:
        shipped = np.sqrt(g_profile * signal + sigma0**2)
        truth = np.sqrt(g_meas * signal + sigma0**2 + (KAPPA * signal) ** 2)
        return float(shipped / truth - 1)

    fact_1064 = {
        "g_measured": g_meas,
        "g_profile": g_profile,
        "sigma0": sigma0,
        "crossover_dn": float((g_profile - g_meas) / KAPPA**2),
        "shipped_error_at_8000": shipped_error(8000.0),
    }
    print()
    print(
        "M71 model check:"
        f" crossover {fact_1064['crossover_dn']:.1f} DN,"
        f" shipped error at 8000 {100*fact_1064['shipped_error_at_8000']:+.3f}%"
    )

    result = {
        "kappa_primary": KAPPA,
        "rows": rows_out,
        "original_exponent": exponent,
        "original_r2": r2,
        "remainder_exponent": rem_exponent,
        "remainder_r2": rem_r2,
        "ratio_of_sums": ratio_sums,
        "median_fraction": median_fraction,
        "fraction_range": [float(fraction.min()), float(fraction.max())],
        "aggregate_remainder_dn2": float(remainder.sum()),
        "aggregate_e_flat_dn2": float(e_flat.sum()),
        "kappa_envelopes": envelopes,
        "fact_1064_reproduction": fact_1064,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "item1.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
