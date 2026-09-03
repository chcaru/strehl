"""Cross-check M-PHASE0-VEIL2 records without carrying its verdict.

The checker derives theta, gate states, and the verdict from recorded
components. It also commissions itself with four in-memory corruptions; each
must make the corresponding validation go RED.
"""

from __future__ import annotations

import copy
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parent.parent
sys.path.insert(0, str(HERE))

from veil2lib import sha256, write_json  # noqa: E402


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def interval_class(score: dict) -> str:
    if not math.isfinite(score["denominator"]) or score["denominator"] < 0.15:
        return "UNMEASURABLE"
    lo, hi = score["theta_ci95"]
    if lo >= 0.50:
        return "STRONG"
    if lo > 0.25:
        return "POSITIVE"
    if hi <= 0.25:
        return "NULL"
    return "INDETERMINATE"


def validate_manifest(manifest: dict, *, hash_raws: bool = True) -> list[str]:
    errors = []
    sites = manifest.get("sites", [])
    if len(sites) != 3:
        errors.append("manifest does not contain three chia sites")
    for site in sites:
        roi = site.get("roi", [])
        if len(roi) != 4 or roi[1] - roi[0] != 96 or roi[3] - roi[2] != 96:
            errors.append(f"{site.get('name')}: ROI is not 96x96")
        for key in ("foreground_frames", "background_frames"):
            run = [int(v) for v in site.get(key, [])]
            if len(run) < 4 or any(b - a != 1 for a, b in zip(run, run[1:])):
                errors.append(f"{site.get('name')}: {key} is not >=4 contiguous")
        f = [int(v) for v in site.get("foreground_frames", [])]
        b = [int(v) for v in site.get("background_frames", [])]
        if f and b and min(abs(x - y) for x in f for y in b) < 15:
            errors.append(f"{site.get('name')}: frame runs are less than 15 apart")
    if hash_raws:
        files = sorted(Path(manifest["stack"]).glob("*.ARW"))
        for raw_index, record in manifest.get("raw_frames", {}).items():
            index = int(raw_index)
            if index >= len(files) or files[index].name != record["name"]:
                errors.append(f"raw frame {index}: identity mismatch")
            elif sha256(files[index]) != record["sha256"]:
                errors.append(f"raw frame {index}: hash mismatch")
    return errors


def validate_commission(commission: dict) -> list[str]:
    errors = []
    rows = commission.get("rows", [])
    controls = sum(bool(r.get("control_pass")) for r in rows)
    reds = sum(bool(r.get("plant_red")) for r in rows)
    if len(rows) != 8:
        errors.append("commission does not contain eight paired checks")
    if controls != len(rows) or commission.get("controls_passed") != controls:
        errors.append("not every commissioning control passes")
    if reds != len(rows) or commission.get("plants_red") != reds:
        errors.append("not every commissioning plant is RED")
    if commission.get("status") != "COMMISSIONED":
        errors.append("commission status is not COMMISSIONED")
    return errors


def derived_gates(measurement: dict, commission: dict) -> dict:
    primary = measurement["bee"]["primary"]
    primary_class = interval_class(primary)
    chia = measurement["chia"]["sites"]
    provenance = measurement["provenance"]
    return {
        "commissioning": not validate_commission(commission),
        "render_provenance": all(
            bool(z.get("pass")) for z in provenance.get("renders", [])
        ),
        "coverage_matches_manifest": bool(
            measurement["required_gates"]["coverage_matches_manifest"]
        ),
        "positive_denominators_at_least_0.15": primary["denominator"] >= 0.15
        and all(z["score"]["denominator"] >= 0.15 for z in chia),
        "primary_detail_identity": primary["detail_margin_ci95"][0] > 0.30,
        "paper_null": bool(measurement["bee"]["paper_null"]["pass"]),
        "tone_locality": bool(measurement["bee"]["tone_locality"]["pass"]),
        "geometry": bool(measurement["bee"]["geometry"]["pass"]),
        "layer_truth": bool(measurement["bee"]["layer_truth"]["pass"])
        and all(bool(z["layer_truth"]["pass"]) for z in chia),
        "channels_stay_in_class": all(
            interval_class(z["score"]) == primary_class
            for z in measurement["bee"]["channels"].values()
        ),
        "sensitivities_stay_in_class": all(
            interval_class(z["score"]) == primary_class
            for z in measurement["bee"]["sensitivities"].values()
        ),
        "independent_decoder_stays_in_class": interval_class(
            measurement["bee"]["independent_decoder"]["score"]
        )
        == primary_class,
    }


def derived_verdict(measurement: dict, gates: dict) -> str:
    primary = measurement["bee"]["primary"]
    lo, hi = primary["theta_ci95"]
    chia_lo = measurement["chia"]["hierarchical"]["theta_ci95"][0]
    if not all(gates.values()):
        return "NOT ROBUST"
    if lo >= 0.50 and chia_lo >= 0.25 and len(measurement["chia"]["sites"]) == 3:
        return "SURVIVE"
    if lo > 0.25:
        return "NARROWED"
    if hi <= 0.25:
        return "KILL"
    return "NOT ROBUST"


def validate_artifacts(measurement: dict) -> list[str]:
    errors = []
    binary = Path(r"C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe")
    if not binary.exists() or sha256(binary) != measurement["provenance"]["binary_sha256"]:
        errors.append("pinned binary hash mismatch")
    for record in measurement["provenance"].get("renders", []):
        path = Path(record["path"])
        if not path.exists():
            errors.append(f"{record['name']}: artifact missing")
        elif sha256(path) != record["sha256"]:
            errors.append(f"{record['name']}: artifact hash mismatch")
    return errors


def validate_measurement(measurement: dict, commission: dict) -> list[str]:
    errors = []
    primary = measurement["bee"]["primary"]
    means = primary["means"]
    den = means["foreground"] - means["background"]
    theta = (means["master"] - means["background"]) / den
    if not math.isclose(den, primary["denominator"], rel_tol=0, abs_tol=2e-7):
        errors.append("primary denominator does not match recorded means")
    if not math.isclose(theta, primary["theta"], rel_tol=0, abs_tol=2e-7):
        errors.append("primary theta does not match recorded means")
    for label, score in [
        ("primary", primary),
        *[
            (f"channel-{name}", z["score"])
            for name, z in measurement["bee"]["channels"].items()
        ],
        *[
            (f"sensitivity-{name}", z["score"])
            for name, z in measurement["bee"]["sensitivities"].items()
        ],
        *[
            (f"chia-{z['name']}", z["score"])
            for z in measurement["chia"]["sites"]
        ],
    ]:
        lo, hi = score["theta_ci95"]
        if not all(math.isfinite(v) for v in (score["theta"], lo, hi)):
            errors.append(f"{label}: non-finite theta record")
        if lo > hi:
            errors.append(f"{label}: inverted confidence interval")
    gates = derived_gates(measurement, commission)
    if gates != measurement.get("required_gates"):
        errors.append("required gate map is not derivable from components")
    verdict = derived_verdict(measurement, gates)
    if verdict != measurement.get("verdict"):
        errors.append("verdict does not follow frozen lookup")
    for name, z in measurement["bee"]["channels"].items():
        if z.get("class") != interval_class(z["score"]):
            errors.append(f"channel {name}: stale class")
    for name, z in measurement["bee"]["sensitivities"].items():
        if z.get("class") != interval_class(z["score"]):
            errors.append(f"sensitivity {name}: stale class")
    decoder = measurement["bee"]["independent_decoder"]
    if decoder.get("class") != interval_class(decoder["score"]):
        errors.append("independent decoder: stale class")
    return errors


def validate_report(measurement: dict, report: str) -> list[str]:
    errors = []
    m = re.search(r"\*\*Verdict:\*\*\s+\*\*([^*]+)\*\*", report)
    if not m or m.group(1).strip() != measurement["verdict"]:
        errors.append("report verdict does not match measurement")
    theta_token = f"{measurement['bee']['primary']['theta']:.4f}"
    if theta_token not in report:
        errors.append("report does not contain rounded primary theta")
    if "Nothing changes in Rust." not in report:
        errors.append("report omits explicit Rust consequence")
    return errors


def main() -> int:
    manifest = load(ROOT / "roi-manifest.json")
    commission = load(ROOT / "out" / "commission.json")
    measurement = load(ROOT / "out" / "measurement.json")
    report_path = REPO / "docs" / "research" / "M-PHASE0-VEIL2.md"
    report = report_path.read_text(encoding="utf-8")

    errors = (
        validate_manifest(manifest)
        + validate_commission(commission)
        + validate_measurement(measurement, commission)
        + validate_artifacts(measurement)
        + validate_report(measurement, report)
    )

    plants = []

    bad = copy.deepcopy(measurement)
    bad["bee"]["primary"]["theta"] += 1.0
    plants.append(
        {
            "name": "theta-arithmetic",
            "red": bool(validate_measurement(bad, commission)),
        }
    )

    bad = copy.deepcopy(measurement)
    bad["verdict"] = "SURVIVE" if measurement["verdict"] != "SURVIVE" else "KILL"
    plants.append(
        {
            "name": "verdict-lookup",
            "red": bool(validate_measurement(bad, commission)),
        }
    )

    bad_manifest = copy.deepcopy(manifest)
    bad_manifest["sites"][0]["foreground_frames"] = bad_manifest["sites"][0][
        "foreground_frames"
    ][:3]
    plants.append(
        {
            "name": "site-run-length",
            "red": bool(validate_manifest(bad_manifest, hash_raws=False)),
        }
    )

    bad_report = report.replace(
        f"**Verdict:** **{measurement['verdict']}**",
        "**Verdict:** **SURVIVE**",
        1,
    )
    plants.append(
        {
            "name": "report-result-mismatch",
            "red": bool(validate_report(measurement, bad_report)),
        }
    )

    self_commissioned = all(z["red"] for z in plants)
    result = {
        "status": "PASS" if not errors and self_commissioned else "FAIL",
        "errors": errors,
        "self_commissioning": {
            "plants_red": sum(z["red"] for z in plants),
            "plants_total": len(plants),
            "all_plants_red": self_commissioned,
            "plants": plants,
        },
        "derived_verdict": derived_verdict(
            measurement, derived_gates(measurement, commission)
        ),
    }
    write_json(ROOT / "out" / "check.json", result)
    print(f"checker: {result['status']}")
    print(
        "self-plants: "
        f"{result['self_commissioning']['plants_red']}/"
        f"{result['self_commissioning']['plants_total']} RED"
    )
    for error in errors:
        print(f"ERROR: {error}")
    print(ROOT / "out" / "check.json")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
