"""Retain all fixed patch outcomes, separated by stage, color, role and pass."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("source", type=Path)
p.add_argument("out", type=Path)
a = p.parse_args()
r = json.loads(a.source.read_text())["measurement"]
pairs = r["patch_diagnostics"]["pairs"]


def condition(probe):
    if probe is None:
        return "no_fitted_model"
    if not probe["reference_derivatives_supported"]:
        return "reference_derivative_footprint_unsupported"
    if not probe["original_search_supported"]:
        return "original_search_footprint_unsupported"
    info = probe["information"]
    if not info["accepted"]:
        if info["minimum_eigenvalue"] <= info["minimum_eigenvalue_required"]:
            return "insufficient_gradient_magnitude"
        return "insufficient_two_dimensional_information"
    assert probe["ncc"] is not None
    return "ncc_" + probe["ncc"]["status"]


rows = []
for cross in [False, True]:
    for color in ["Red", "GreenLuma", "Blue"]:
        for training in [False, True]:
            selected = [t for pair in pairs
                        if (pair["acquisitions"][0] < 299 <= pair["acquisitions"][1]) == cross
                        and pair["color"] == color
                        for t in pair["tiles"] if t["training"] == training]
            rows.append({"cross_pass": cross, "color": color, "training": training,
                         "tiles": len(selected), "retained_heldout": sum(t["retained_heldout"] for t in selected),
                         "seed": dict(Counter(condition(t["seed"]) for t in selected)),
                         "fitted": dict(Counter(condition(t["fitted"]) for t in selected))})
assert sum(row["tiles"] for row in rows) == 675
detail = []
for pair in pairs:
    if pair["acquisitions"] == [110, 400]:
        detail.append({"color": pair["color"], "acquisitions": pair["acquisitions"], "held_tiles": [
            {"index": t["index"], "origin_crop_quad": t["reference_origin_crop_quad"],
             "seed": condition(t["seed"]), "fitted": condition(t["fitted"]),
             "retained_heldout": t["retained_heldout"],
             "seed_peak": (t["seed"]["ncc"] or {}).get("peak"),
             "fitted_peak": ((t["fitted"] or {}).get("ncc") or {}).get("peak")}
            for t in pair["tiles"] if not t["training"]]})
report = {"source": str(a.source), "source_sha256": hashlib.sha256(a.source.read_bytes()).hexdigest(),
          "scope": "All predefined patches. Post-estimator diagnostics never enter the returned certificate; causes are ordered for a census and raw simultaneous conditions remain in the source.",
          "rows": rows, "example": detail}
with a.out.open("x") as f:
    json.dump(report, f, indent=2)
    f.write("\n")
print(json.dumps(report, indent=2))
