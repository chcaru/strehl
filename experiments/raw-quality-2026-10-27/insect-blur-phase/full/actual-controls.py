"""Independent, pixel-free original-green geometry/combiner commission."""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRODUCER = HERE / "actual.py"
PRODUCER_SHA = "e3ce897a8b2adcf225e18d262d713d50ba8ebcf8434fccb5ac57a7fd79f1fb9c"
C = (3516.0, 2344.0)
GEOMETRY_BAR, OBSERVATION_BAR = 1e-9, 2e-5


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mapped(point, transform, inverse=False):
    a, b = transform
    matrix = ((a.real, -a.imag), (a.imag, a.real))
    q = [point[k] - C[k] for k in (0, 1)]
    shift = (2 * b.real, 2 * b.imag)
    if inverse:
        q = [q[k] - shift[k] for k in (0, 1)]
        det = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
        matrix = ((matrix[1][1] / det, -matrix[0][1] / det),
                  (-matrix[1][0] / det, matrix[0][0] / det))
        shift = (0, 0)
    return [C[k] + sum(matrix[k][j] * q[j] for j in (0, 1)) + shift[k] for k in (0, 1)]


def nearest_even(value):
    lo = math.floor(value)
    return lo + int(value - lo > 0.5 or (value - lo == 0.5 and lo % 2 != 0))


def expected(mi, mj, tile):
    result = {}
    for name, offset in (("G1", (1, 0)), ("G2", (0, 1))):
        oi = [2 * tile[k] + offset[k] for k in (0, 1)]
        center = [x + 127 for x in oi]
        pred = mapped(mapped(center, mi, inverse=True), mj)
        oj = [offset[k] + 2 * nearest_even((pred[k] - 127 - offset[k]) / 2) for k in (0, 1)]
        result[name] = dict(oi=oi, oj=oj, center=center, pred=pred,
                            supported=all(0 <= o[k] and o[k] + 254 < (7032, 4688)[k]
                                          for o in (oi, oj) for k in (0, 1)))
    return result


def geometry_score(got, truth):
    errors, exact = [], True
    for name, e in truth.items():
        g = got[name]
        exact &= (g["reference_origin_native_xy"] == e["oi"] and
                  g["moving_origin_native_xy"] == e["oj"] and
                  (g["support_status"] == "SUPPORTED") == e["supported"])
        for key, target in (("centroid_native_xy", e["center"]),
                            ("held_predicted_centroid_native_xy", e["pred"]),
                            ("held_displacement_native_xy", [e["pred"][k] - e["center"][k] for k in (0, 1)])):
            errors.extend(abs(g[key][k] - target[k]) for k in (0, 1))
        rem = [e["pred"][k] - e["oj"][k] - 127 for k in (0, 1)]
        errors.extend(abs(g["held_patch_remainder_native_xy"][k] - rem[k]) for k in (0, 1))
        errors.extend(abs(g["held_relative_correction_interval_native_xy"][k][j] - ((-2, 2)[j] - rem[k]))
                      for k in (0, 1) for j in (0, 1))
    return {"pass": bool(exact and max(errors) <= GEOMETRY_BAR), "exact_lattice_and_support": bool(exact),
            "maximum_native_error": max(errors)}


def observations(got, truth):
    for name, e in truth.items():
        # Construct a reader's TOTAL displacement from origins plus its local shift.
        local = [e["pred"][k] - e["center"][k] + (0.125, -0.0625)[k] -
                 (e["oj"][k] - e["oi"][k]) for k in (0, 1)]
        total = [got[name]["moving_origin_native_xy"][k] - got[name]["reference_origin_native_xy"][k] + local[k]
                 for k in (0, 1)]
        got[name]["reader"] = {f"p{p}": dict(accepted=True, refusals=[], displacement_native_xy=total, score=0.75)
                               for p in (1, 2)}
    return got


def observation_score(result, truth):
    pc = [sum(e["center"][k] for e in truth.values()) / 2 for k in (0, 1)]
    d = [sum(e["pred"][k] - e["center"][k] for e in truth.values()) / 2 + (0.125, -0.0625)[k] for k in (0, 1)]
    target = dict(ux=(pc[0] - C[0]) / 2, uy=(pc[1] - C[1]) / 2, dx=d[0] / 2, dy=d[1] / 2, score=0.75)
    error = max(abs(result["observation"][k] - v) for k, v in target.items()) if result["accepted"] else None
    return {"pass": bool(error is not None and error <= OBSERVATION_BAR), "maximum_guide_error": error, "expected": target}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    before = {str(p): digest(p) for p in (Path(__file__).resolve(), PRODUCER, HERE / "full-control-plan.md")}
    assert before[str(PRODUCER)] == PRODUCER_SHA, "producer changed before independent commission"
    spec = importlib.util.spec_from_file_location("insect_phase_actual_geometry", PRODUCER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)  # stdlib only; main(), pixels and Torch are not invoked.
    cases = [("identity", (1+0j, 0j), (1+0j, 0j), (96, 96)),
             ("ties-even", (1+0j, 0j), (1+0j, complex(0.5, -0.5)), (96, 96)),
             ("noncentral", (complex(1.007, 0.003), complex(2.25, -1.75)),
              (complex(0.994, -0.004), complex(-3.125, 2.5)), (2000, 1200)),
             ("unsupported", (1+0j, 0j), (1+0j, 0j), (3400, 2200))]
    records = []
    for name, mi, mj, tile in cases:
        truth, got = expected(mi, mj, tile), m.pair_geometry(mi, mj, tile)
        row = {"name": name, "geometry": geometry_score(got, truth)}
        if name != "unsupported":
            observations(got, truth)
            row["p1"] = observation_score(m.combine_tile(got, 1), truth)
            row["p2"] = observation_score(m.combine_tile(got, 2), truth)
        else:
            row["no_fallback"] = all(m.combine_tile(got, p)["observation"] is None for p in (1, 2))
        records.append(row)
    _, mi, mj, tile = cases[2]
    truth = expected(mi, mj, tile)
    good = observations(m.pair_geometry(mi, mj, tile), truth)
    inverse = geometry_score(m.pair_geometry(mj, mi, tile), truth)
    pitch = geometry_score(m.pair_geometry((mi[0], mi[1]/2), (mj[0], mj[1]/2), tile), truth)
    origin = copy.deepcopy(good)
    origin["G1"]["moving_origin_native_xy"][0] += 1
    origin_score = geometry_score(origin, truth)
    observations(origin, truth)
    origin_displacement = observation_score(m.combine_tile(origin, 1), truth)
    centroid = copy.deepcopy(good)
    for item in centroid.values():
        item["centroid_native_xy"] = [v + 0.5 for v in item["centroid_native_xy"]]
    center_score = observation_score(m.combine_tile(centroid, 1), truth)
    refused = copy.deepcopy(good)
    refused["G2"]["reader"]["p1"].update(accepted=False, refusals=["INJECTED_REFUSAL"])
    disagree = copy.deepcopy(good)
    disagree["G2"]["reader"]["p1"]["displacement_native_xy"][0] += 0.25
    missing = copy.deepcopy(good)
    missing["G2"]["reader"] = None
    nulls = {name: m.combine_tile(value, 1) for name, value in (("refused", refused), ("disagreement", disagree), ("missing_reader", missing))}
    try:
        m.combine_tile({"G1": good["G1"]}, 1)
        missing_phase_refused = False
    except (KeyError, ValueError):
        missing_phase_refused = True
    foils = dict(wrong_inverse=inverse, wrong_native_pitch=pitch, wrong_origin=origin_score,
                 wrong_total_origin=origin_displacement, wrong_centroid=center_score)
    passed = (all(r["geometry"]["pass"] and r.get("no_fallback", True) and
                  all(r[k]["pass"] for k in ("p1", "p2") if k in r) for r in records) and
              all(not row["pass"] for row in foils.values()) and missing_phase_refused and
              all(not row["accepted"] and row["observation"] is None for row in nulls.values()))
    unchanged = before == {p: digest(p) for p in before}
    receipt = dict(status="COMPLETE_INSECT_PHASE_ACTUAL_CONTROLS", complete=True,
                   controls_pass=bool(passed and unchanged), geometry_native_bar=GEOMETRY_BAR,
                   observation_guide_bar=OBSERVATION_BAR, cases=records, foils=foils,
                   refusal_cases=nulls, missing_phase_refused=missing_phase_refused,
                   source_bindings=before, source_bindings_unchanged=unchanged,
                   original_pixels_read=0, torch_imported=False, quality_claim=False, photographic_admission=False)
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
