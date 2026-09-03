"""Cross-implementation stop gate for the slanted-edge USM transfer."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Mapping


SCHEMA = "V-HEADTOHEAD3-SHARPENING-TRANSFER-ADJUDICATION-1"
AUTHOR_SCHEMA = "V-HEADTOHEAD3-SHARPENING-TRANSFER-AUTHOR-1"
CHECKER_SCHEMA = "V-HEADTOHEAD3-SHARPENING-TRANSFER-CHECK-1"
STATUS = "MEASURED_PENDING_CROSSCHECK"
LABEL = "PRESENTATION_SENSITIVITY_NOT_RESOLUTION"
UNLICENSED = "UNLICENSED_GT_0.25"
SITE_DIGEST = "B3A2F5279069A3CC85FB42F49F6FDA39397423D9A65565CAB88CCF8E627679F6"
SYNTHETIC_TRANSFER = 5.560744
EXPECTED_HASHES = {
    "strehl": "4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F",
    "pmax0": "B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0",
    "pmax40": "4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E",
}
EXPECTED_SITES = (
    (2048, 3072),
    (3584, 3584),
    (512, 4608),
    (3072, 4096),
    (3584, 5632),
    (3072, 6144),
    (1536, 5632),
    (2048, 6144),
    (1024, 4096),
    (512, 5632),
    (4096, 6144),
    (4096, 5120),
    (512, 5120),
    (1024, 5632),
    (3072, 2560),
    (1024, 4608),
    (3584, 2048),
    (512, 6144),
    (1536, 4096),
    (4096, 4608),
    (3584, 5120),
    (4096, 5632),
    (3584, 6144),
    (3072, 4608),
)
QUANTITIES = ("T0", "M40", "TS", "S40", "R0", "O40")


class StopAdjudication(RuntimeError):
    """The preregistered cross-implementation stop."""


def frozen_verdict(
    t0: Mapping[str, float],
    m40: Mapping[str, float],
) -> str:
    if t0["ci_low"] > 1.05 and m40["ci_low"] > 1.0:
        return "REAL_TRANSFER_SUFFICIENT"
    if t0["ci_low"] > 1.05 and m40["ci_high"] < 1.0:
        return "REAL_TRANSFER_PARTIAL"
    if t0["ci_low"] >= 0.95 and t0["ci_high"] <= 1.05:
        return "NO_REAL_TRANSFER"
    return "UNRESOLVED"


def _valid_interval(row: Mapping) -> bool:
    try:
        n = int(row["n"])
        point = float(row["point"])
        low = float(row["ci_low"])
        high = float(row["ci_high"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        n >= 12
        and math.isfinite(point)
        and math.isfinite(low)
        and math.isfinite(high)
        and 0.0 < low <= point <= high
    )


def _hash_map(document: Mapping) -> dict[str, str]:
    hashes = document.get("provenance", {}).get("hashes", {})
    if not isinstance(hashes, Mapping):
        return {}
    return {
        str(name): str(value).upper()
        for name, value in hashes.items()
    }


def _operator_ok(document: Mapping) -> bool:
    return document.get("operator") == {
        "sigma": 1.0,
        "amount": 0.5,
        "truncate": 6.0,
        "radius": 6,
        "boundary": "nearest",
        "clipping": False,
    }


def _band_ok(document: Mapping) -> bool:
    return document.get("licensed_band") == {
        "low_inclusive": 0.20,
        "high_exclusive": 0.25,
        "unit": "cycles_per_native_pixel",
    }


def adjudicate(author: Mapping, checker: Mapping) -> dict:
    failures: list[str] = []
    if author.get("schema") != AUTHOR_SCHEMA:
        failures.append("author schema")
    if checker.get("schema") != CHECKER_SCHEMA:
        failures.append("checker schema")
    for name, document, bootstrap_seed in (
        ("author", author, 20260906),
        ("checker", checker, 20260919),
    ):
        if document.get("status") != STATUS:
            failures.append(f"{name} status")
        if document.get("label") != LABEL:
            failures.append(f"{name} label")
        if document.get("unlicensed") != UNLICENSED:
            failures.append(f"{name} cap sentinel")
        if document.get("provenance", {}).get("site_digest") != SITE_DIGEST:
            failures.append(f"{name} site digest")
        if _hash_map(document) != EXPECTED_HASHES:
            failures.append(f"{name} hashes")
        if not _operator_ok(document):
            failures.append(f"{name} operator")
        if not _band_ok(document):
            failures.append(f"{name} band")
        if int(document.get("retained_count", 0)) < 12:
            failures.append(f"{name} retained sites")
        try:
            frozen_sites = tuple(
                tuple(map(int, site))
                for site in document.get("frozen_sites", ())
            )
        except (TypeError, ValueError):
            frozen_sites = ()
        if frozen_sites != EXPECTED_SITES:
            failures.append(f"{name} frozen sites")
        if document.get("bootstrap") != {
            "draws": 10_000,
            "seed": bootstrap_seed,
            "paired_site_indices": True,
        }:
            failures.append(f"{name} bootstrap")
        if set(document.get("quantities", {})) != set(QUANTITIES):
            failures.append(f"{name} quantities")

    geometry_comparison = {}
    for comparator in ("pmax0", "pmax40"):
        try:
            a_geometry = author["geometry"][comparator]
            c_geometry = checker["geometry"][comparator]
            a_scale = float(a_geometry["scale"])
            c_scale = float(c_geometry["scale"])
            disagreement = max(a_scale / c_scale, c_scale / a_scale) - 1.0
            interior = all(
                bool(row["coarse_interior"]) and bool(row["fine_interior"])
                for row in (a_geometry, c_geometry)
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            failures.append(f"{comparator} geometry")
            continue
        geometry_comparison[comparator] = {
            "author_scale": a_scale,
            "checker_scale": c_scale,
            "relative_disagreement": disagreement,
        }
        if not interior or disagreement > 0.005:
            failures.append(f"{comparator} geometry agreement")

    quantity_comparison = {}
    for name in QUANTITIES:
        try:
            a = author["quantities"][name]
            c = checker["quantities"][name]
        except (KeyError, TypeError):
            failures.append(f"{name} missing")
            continue
        if not _valid_interval(a) or not _valid_interval(c):
            failures.append(f"{name} invalid interval")
            continue
        overlap_low = max(float(a["ci_low"]), float(c["ci_low"]))
        overlap_high = min(float(a["ci_high"]), float(c["ci_high"]))
        cross_contained = (
            float(c["ci_low"]) <= float(a["point"]) <= float(c["ci_high"])
            and float(a["ci_low"]) <= float(c["point"]) <= float(a["ci_high"])
        )
        quantity_comparison[name] = {
            "author": {
                key: a[key] for key in ("point", "ci_low", "ci_high", "n")
            },
            "checker": {
                key: c[key] for key in ("point", "ci_low", "ci_high", "n")
            },
            "intervals_overlap": overlap_low <= overlap_high,
            "points_cross_contained": cross_contained,
        }
        if overlap_low > overlap_high or not cross_contained:
            failures.append(f"{name} cross-implementation agreement")

    try:
        author_verdict = frozen_verdict(
            author["quantities"]["T0"],
            author["quantities"]["M40"],
        )
        checker_verdict = frozen_verdict(
            checker["quantities"]["T0"],
            checker["quantities"]["M40"],
        )
    except (KeyError, TypeError):
        failures.append("verdict inputs")
        author_verdict = checker_verdict = "INVALID"
    if author.get("candidate_verdict") != author_verdict:
        failures.append("author candidate verdict")
    if checker.get("candidate_verdict") != checker_verdict:
        failures.append("checker candidate verdict")
    if author_verdict != checker_verdict:
        failures.append("candidate verdict disagreement")

    try:
        a_t0 = float(author["quantities"]["T0"]["point"])
        c_t0 = float(checker["quantities"]["T0"]["point"])
        transfer_comparison = {
            "synthetic_reference": SYNTHETIC_TRANSFER,
            "author_T0_over_synthetic": a_t0 / SYNTHETIC_TRANSFER,
            "checker_T0_over_synthetic": c_t0 / SYNTHETIC_TRANSFER,
            "author_log_fraction": math.log(a_t0)
            / math.log(SYNTHETIC_TRANSFER),
            "checker_log_fraction": math.log(c_t0)
            / math.log(SYNTHETIC_TRANSFER),
        }
    except (KeyError, TypeError, ValueError):
        failures.append("synthetic transfer comparison")
        transfer_comparison = {}
    if failures:
        raise StopAdjudication(
            "cross-implementation gate failed: " + ", ".join(failures)
        )
    return {
        "schema": SCHEMA,
        "status": "GREEN",
        "label": LABEL,
        "site_digest": SITE_DIGEST,
        "geometry_comparison": geometry_comparison,
        "quantity_comparison": quantity_comparison,
        "transfer_vs_synthetic": transfer_comparison,
        "unlicensed": UNLICENSED,
        "verdict": author_verdict,
    }


def _fixture(schema: str) -> dict:
    quantities = {
        name: {
            "n": 24,
            "point": point,
            "ci_low": low,
            "ci_high": high,
        }
        for name, point, low, high in (
            ("T0", 1.20, 1.10, 1.30),
            ("M40", 1.10, 1.01, 1.20),
            ("TS", 1.15, 1.08, 1.22),
            ("S40", 0.98, 0.90, 1.06),
            ("R0", 0.99, 0.91, 1.07),
            ("O40", 1.09, 1.02, 1.16),
        )
    }
    return {
        "schema": schema,
        "status": STATUS,
        "label": LABEL,
        "provenance": {
            "site_digest": SITE_DIGEST,
            "hashes": dict(EXPECTED_HASHES),
        },
        "operator": {
            "sigma": 1.0,
            "amount": 0.5,
            "truncate": 6.0,
            "radius": 6,
            "boundary": "nearest",
            "clipping": False,
        },
        "licensed_band": {
            "low_inclusive": 0.20,
            "high_exclusive": 0.25,
            "unit": "cycles_per_native_pixel",
        },
        "geometry": {
            name: {
                "scale": scale,
                "coarse_interior": True,
                "fine_interior": True,
            }
            for name, scale in (("pmax0", 1.002), ("pmax40", 1.003))
        },
        "bootstrap": {
            "draws": 10_000,
            "seed": 20260906 if schema == AUTHOR_SCHEMA else 20260919,
            "paired_site_indices": True,
        },
        "frozen_sites": [list(site) for site in EXPECTED_SITES],
        "retained_count": 24,
        "quantities": quantities,
        "unlicensed": UNLICENSED,
        "candidate_verdict": "REAL_TRANSFER_SUFFICIENT",
    }


def commission() -> dict:
    author = _fixture(AUTHOR_SCHEMA)
    checker = _fixture(CHECKER_SCHEMA)
    baseline = adjudicate(author, checker)
    controls = {
        "valid_fixture_green": baseline["status"] == "GREEN",
        "literal_sufficient": baseline["verdict"]
        == "REAL_TRANSFER_SUFFICIENT",
    }
    mutants = {}

    def rejected(change) -> bool:
        a = copy.deepcopy(author)
        c = copy.deepcopy(checker)
        change(a, c)
        try:
            adjudicate(a, c)
            return False
        except StopAdjudication:
            return True

    changes = (
        (
            "scale_disagreement",
            lambda a, c: c["geometry"]["pmax0"].__setitem__("scale", 1.02),
        ),
        (
            "scale_disagreement_boundary",
            lambda a, c: c["geometry"]["pmax0"].__setitem__(
                "scale",
                a["geometry"]["pmax0"]["scale"] * 1.005001,
            ),
        ),
        (
            "disjoint_intervals",
            lambda a, c: c["quantities"]["T0"].update(
                {"point": 1.60, "ci_low": 1.50, "ci_high": 1.70}
            ),
        ),
        (
            "point_not_cross_contained",
            lambda a, c: c["quantities"]["R0"].update(
                {"point": 1.08, "ci_low": 1.06, "ci_high": 1.20}
            ),
        ),
        (
            "candidate_verdict",
            lambda a, c: c.__setitem__(
                "candidate_verdict",
                "NO_REAL_TRANSFER",
            ),
        ),
        (
            "site_digest",
            lambda a, c: a["provenance"].__setitem__(
                "site_digest",
                "0" * 64,
            ),
        ),
        (
            "input_hash",
            lambda a, c: a["provenance"]["hashes"].__setitem__(
                "pmax0",
                "0" * 64,
            ),
        ),
        (
            "swapped_hash_names",
            lambda a, c: c["provenance"].__setitem__(
                "hashes",
                {
                    "strehl": c["provenance"]["hashes"]["strehl"],
                    "pmax0": c["provenance"]["hashes"]["pmax40"],
                    "pmax40": c["provenance"]["hashes"]["pmax0"],
                },
            ),
        ),
        (
            "frozen_site_coordinate",
            lambda a, c: c["frozen_sites"][0].__setitem__(
                0,
                c["frozen_sites"][0][0] + 1,
            ),
        ),
        (
            "bootstrap_contract",
            lambda a, c: c.__setitem__(
                "bootstrap",
                {
                    "draws": 1,
                    "seed": 0,
                    "paired_site_indices": False,
                },
            ),
        ),
        (
            "above_cap_number",
            lambda a, c: c.__setitem__("unlicensed", 0.28125),
        ),
        (
            "too_few_sites",
            lambda a, c: a.__setitem__("retained_count", 11),
        ),
        (
            "operator_amount",
            lambda a, c: a["operator"].__setitem__("amount", 0.6),
        ),
    )
    for name, change in changes:
        mutants[name] = rejected(change)
    green = all(controls.values()) and all(mutants.values())
    return {
        "schema": SCHEMA + "-COMMISSION",
        "status": "GREEN" if green else "RED",
        "green": green,
        "controls": controls,
        "caught_red_mutants": mutants,
        "control_count": len(controls),
        "mutant_count": len(mutants),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commission", action="store_true")
    parser.add_argument("--author", type=Path)
    parser.add_argument("--checker", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.commission:
        if any((args.author, args.checker, args.output)):
            parser.error("--commission accepts no outcome paths")
        result = commission()
        code = 0 if result["green"] else 2
    else:
        if args.author is None or args.checker is None:
            parser.error("outcome mode requires --author and --checker")
        try:
            author = json.loads(args.author.read_text(encoding="utf-8"))
            checker = json.loads(args.checker.read_text(encoding="utf-8"))
            result = adjudicate(author, checker)
            code = 0
        except (OSError, json.JSONDecodeError, StopAdjudication) as exc:
            result = {
                "schema": SCHEMA,
                "status": "STOPPED",
                "reason": str(exc),
            }
            code = 2
    if args.output is not None:
        args.output.write_text(
            json.dumps(result, indent=2, allow_nan=False),
            encoding="utf-8",
        )
    print(
        "SHARPENING_TRANSFER_ADJUDICATION_JSON="
        + json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
