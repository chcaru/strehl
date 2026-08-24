from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULT = json.loads((HERE / "out" / "result.json").read_text(encoding="utf-8"))
ITEM1 = json.loads(
    (ROOT / "experiments" / "M76b-reconciliations" / "out" / "item1.json")
    .read_text(encoding="utf-8")
)

checks = 0


def check(condition: bool, label: str) -> None:
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1
    print(f"PASS {checks:02d}: {label}")


flat = RESULT["flat"]
dark = RESULT["dark"]
scene = RESULT["scene"]
controls = RESULT["controls"]
decision = RESULT["decision"]
kappa = RESULT["constants"]["kappa"]
rows = ITEM1["rows"]
sum_r = sum(row["remainder_dn2"] for row in rows)
sum_s2 = sum(row["level_dn"] ** 2 for row in rows)

matrix = np.asarray(flat["pair_patch_values"])
check(matrix.shape == (5, 24), "all five flat pairs and 24 patches are present")
check(math.isclose(float(matrix.mean()), flat["v_flat"], rel_tol=1e-14),
      "V_flat is the unrectified 5 x 24 arithmetic mean")
check(np.allclose(matrix.mean(axis=1), flat["pair_values"], rtol=0, atol=1e-18),
      "reported exposure-pair values reproduce from the patch matrix")

rng = np.random.default_rng(76003)
boot = np.empty(10_000)
for draw in range(10_000):
    pair_indices = rng.integers(0, 5, 5)
    values = []
    for pair in pair_indices:
        patch_indices = rng.integers(0, 24, 24)
        values.append(float(matrix[pair, patch_indices].mean()))
    boot[draw] = np.mean(values)
check(np.allclose(np.percentile(boot, [2.5, 97.5]), flat["v_flat_ci95"],
                  rtol=0, atol=1e-18),
      "registered two-level flat bootstrap reproduces exactly")

expected_f = max(flat["v_flat"] - kappa**2, 0.0) * sum_s2 / sum_r
check(math.isclose(expected_f, flat["f_mult"], rel_tol=1e-14),
      "multiplicative remainder share reproduces from exact M76b rows")
check(all(controls[name] for name in
          ("plant_pass", "independent_pass", "shift_pass")),
      "all three mandatory Arm-A controls pass")

for entry in dark["iso"].values():
    check(math.isclose(np.mean(entry["patch_values"]), entry["v_dark"],
                       rel_tol=1e-14),
          f"ISO {entry['folder']} dark point is its 24-patch mean")
check(not dark["control_pass"],
      "registered dark control fails rather than being silently relaxed")

check(math.isclose(np.median(list(scene["same"].values())),
                   scene["same_median"], rel_tol=1e-14),
      "same-subject median reproduces")
check(not scene["scene_control_pass"],
      "registered scene-sensitivity control fails")

post = decision["post_fixed_rows"]
positive = [(row["level_dn"], row["remainder_dn2"]) for row in post
            if row["remainder_dn2"] > 0]
lx = np.log([x for x, _ in positive])
ly = np.log([y for _, y in positive])
slope, intercept = np.polyfit(lx, ly, 1)
predicted = intercept + slope * lx
r2 = 1 - float(np.sum((ly - predicted) ** 2)
                 / np.sum((ly - ly.mean()) ** 2))
check(math.isclose(slope, decision["post_fixed_exponent"], rel_tol=1e-14)
      and math.isclose(r2, decision["post_fixed_r2"], rel_tol=1e-14),
      "post-fixed-term exponent and R-squared reproduce")

check(decision["verdict"] == "INCONCLUSIVE",
      "failed mandatory Arm-B control forces the registered verdict")
check(not decision["m77_flag"]
      and decision["sigma_move_upper_at_8000"] < 0.02,
      "registered M77 re-denomination threshold does not bind")

print(f"\n{checks}/{checks} checks passed")
