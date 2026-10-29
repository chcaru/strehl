"""Train-only model ablation on frozen seed probes; never a production fitter."""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np


def solve(points, residual, similarity):
    if len(points) < 4:
        return None
    if not similarity:
        return 0j, np.mean(residual)
    # Independent real-valued least squares, fixed unit weights, no pruning.
    x, y = points.real, points.imag
    design = np.empty((2 * len(x), 4))
    design[0::2] = np.column_stack([x, -y, np.ones(len(x)), np.zeros(len(x))])
    design[1::2] = np.column_stack([y, x, np.zeros(len(x)), np.ones(len(x))])
    values = np.empty(2 * len(x))
    values[0::2], values[1::2] = residual.real, residual.imag
    beta, _, rank, _ = np.linalg.lstsq(design, values, rcond=None)
    if rank != 4:
        return None
    return complex(*beta[:2]), complex(*beta[2:])


def controls():
    train = np.array([-63-63j, 63-63j, 0j, -63+63j, 63+63j])
    held = np.array([-63j, -63+0j, 63+0j, 63j])
    for delta in [0j, .12-.27j]:
        for similarity in [False, True]:
            a, b = solve(train, np.full(5, delta), similarity)
            assert np.max(np.abs(a*held+b-delta)) < 1e-12
    truth = .002+.001j
    a, b = solve(train, truth*train+.2j, True)
    assert np.max(np.abs(a*held+b-(truth*held+.2j))) < 1e-12
    a, b = solve(train, truth*train+.2j, False)
    assert np.min(2*np.abs(a*held+b-(truth*held+.2j))) > .15
    # Curvature invisible at the training checkerboard must fail held points.
    curved = lambda z: 1e-4*(z.real*z.real-z.imag*z.imag)
    for similarity in [False, True]:
        a, b = solve(train, curved(train).astype(complex), similarity)
        assert np.min(2*np.abs(a*held+b-curved(held))) > .15
    poisoned = np.full(4, 500+700j)
    for similarity in [False, True]:
        before = solve(train, truth*train+.2j, similarity)
        assert before == solve(train, truth*train+.2j, similarity)
        assert np.min(np.abs(before[0]*held+before[1]-poisoned)) > 100
    assert solve(train[:3], np.ones(3), True) is None
    assert solve(np.zeros(4, complex), np.ones(4), True) is None
    return {"constant_translation_positive": True, "scale_rotation_foil": True,
            "curvature_foil": True, "held_values_not_fit_inputs": True, "rank_and_count": True}


def solve_affine(points, residual):
    if len(points) < 4:
        return None
    design = np.column_stack([points.real, points.imag, np.ones(len(points))])
    beta, _, rank, _ = np.linalg.lstsq(design, residual, rcond=None)
    return beta if rank == 3 else None


def affine_controls():
    train = np.array([-63-63j, 63-63j, 0j, -63+63j, 63+63j])
    held = np.array([-63j, -63+0j, 63+0j, 63j])
    predict = lambda beta, p: beta[0]*p.real + beta[1]*p.imag + beta[2]
    for truth in [lambda p: np.full(len(p), .12-.27j),
                  lambda p: (.003+.001j)*p.real + (.004-.002j)*p.imag + .2-.3j]:
        beta = solve_affine(train, truth(train))
        assert np.max(np.abs(predict(beta, held)-truth(held))) < 1e-12
    truth = lambda p: (.003+.001j)*p.real + (.004-.002j)*p.imag + .2-.3j
    a, b = solve(train, truth(train), True)
    assert np.max(2*np.abs(a*held+b-truth(held))) > .15
    curved = lambda p: 1e-4*(p.real*p.real-p.imag*p.imag)
    beta = solve_affine(train, curved(train).astype(complex))
    assert np.min(2*np.abs(predict(beta, held)-curved(held))) > .15
    beta = solve_affine(train, truth(train))
    # These are correspondence-error foils, not image-level PSF validation.
    for error in [np.array([0, 0, 3., 0]), np.array([.3, -.3, .3, -.3])]:
        assert np.max(2*np.abs(predict(beta, held)-truth(held)-error)) > .15
    assert solve_affine(train[:3], truth(train[:3])) is None
    assert solve_affine(np.arange(5).astype(complex), np.ones(5)) is None
    return dict(known_affine_positive=True, similarity_anisotropy_foil=True,
                nonlinear_correspondence_foil=True, wrong_period_correspondence_foil=True,
                alternating_correspondence_bias_foil=True, rank_count_refusal=True,
                scope='Coordinate-fit controls only; no image-level PSF or photon-independence certificate.')


def plane_pull(pull, color):
    a, b = complex(*pull["a"]), complex(*pull["b"])
    site = {"Red": -.25-.25j, "GreenLuma": 0j, "Blue": .25+.25j}[color]
    return a, b+a*site-site


def gauge_control():
    full = 3516+2344j
    physical_center = full+.5+.5j
    originals = [((1.003+.0007j), (-.2+.3j)), ((.998-.0004j), (1.7-.6j))]
    origins = [934+996j, 936+996j]
    half = 96+96j
    for color, offset in [("Red", 0j), ("GreenLuma", .5+.5j), ("Blue", 1+1j)]:
        pp = [plane_pull({"a": [v[0].real, v[0].imag], "b": [v[1].real, v[1].imag]}, color) for v in originals]
        linear = pp[1][0]/pp[0][0]
        translation = pp[1][1]-linear*pp[0][1]
        local_b = linear*(origins[0]+half-full/2)+translation-(origins[1]+half-full/2)
        for q in [10+73j, 73+10j, 136+73j, 73+136j]:
            sensor0 = 2*(origins[0]+q)+offset
            anchor = (sensor0-physical_center-2*originals[0][1])/originals[0][0]+physical_center
            sensor1 = originals[1][0]*(anchor-physical_center)+2*originals[1][1]+physical_center
            oracle = (sensor1-offset)/2-origins[1]
            assert abs(linear*(q-half)+local_b+half-oracle) < 1e-10
    return True


def eligible(tile):
    p = tile["seed"]
    return p["original_search_supported"] and p["information"] is not None and p["information"]["accepted"] and p["ncc"]["status"] == "Ok"


p = argparse.ArgumentParser()
p.add_argument("--source", type=Path)
p.add_argument("--out", type=Path, required=True)
p.add_argument("--affine", action="store_true")
a = p.parse_args()
checks = controls()  # Always before reading any real measurement.
checks["independent_absolute_sensor_gauge"] = gauge_control()
if a.affine:
    checks['affine'] = affine_controls()
report = {"command": sys.argv, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "controls": checks, "rows": [],
          "scope": "DERIVED on fixed measured seed NCC observations. Unit-weight two/four-parameter fits use training only. Neither arm changes production or certifies a source; repeated fit/probe sampling and original-photon independence would require separate commissioning."}
if a.affine:
    report['scope'] += ' Predeclared six-parameter affine arm uses the identical eligible training sites and all eligible held sites; no residual pruning or best-of-model selection.'
if a.source:
    r = json.loads(a.source.read_text())["measurement"]
    report["source_sha256"] = hashlib.sha256(a.source.read_bytes()).hexdigest()
    evidence = {(tuple(x["acquisitions"]), x["color"]): x for x in r["pair_measurements"]}
    half = r["native_window_side_sensor"] / 4
    center = complex(*r["full_geometry_quad"]) / 2
    for pair in r["patch_diagnostics"]["pairs"]:
        old = evidence[(tuple(pair["acquisitions"]), pair["color"])]
        p0, p1 = [plane_pull(v, pair["color"]) for v in old["input_color_pulls"]]
        global_a, global_b = p1[0]/p0[0], p1[1]-(p1[0]/p0[0])*p0[1]
        origin0, origin1 = map(lambda v: complex(*v), pair["original_crop_origins_quad"])
        local_b = global_a*(origin0+half*(1+1j)-center)+global_b-(origin1+half*(1+1j)-center)
        tile_half = r["policy"]["tile_quad"] / 2
        points = np.array([complex(*t["reference_origin_crop_quad"])+tile_half*(1+1j)-half*(1+1j) for t in pair["tiles"]])
        delta = np.full(len(points), complex(np.nan, np.nan))
        train, held = [], []
        for i, t in enumerate(pair["tiles"]):
            if eligible(t):
                displacement = complex(*t["seed"]["ncc"]["displacement_quad"])
                delta[i] = points[i]+displacement-(global_a*points[i]+local_b)
                (train if t["training"] else held).append(i)
        row = {"acquisitions": pair["acquisitions"], "color": pair["color"],
               "training_count": len(train), "held_count": len(held), "models": {}}
        for model in ["residual_translation", "residual_similarity"] + (["residual_affine"] if a.affine else []):
            if model == 'residual_affine':
                beta = solve_affine(points[train], delta[train])
                if beta is None:
                    row['models'][model] = None
                    continue
                fitted_delta = beta[0]*points[held].real + beta[1]*points[held].imag + beta[2]
                residual = 2*(delta[held]-fitted_delta)/p1[0]
                row['models'][model] = dict(
                    beta_real_imag=[[v.real, v.imag] for v in beta],
                    held_sensor_vectors=np.column_stack([residual.real, residual.imag]).tolist(),
                    held_max_sensor=float(np.abs(residual).max()) if len(held) else None,
                    at_least_four_held_consistent_015=len(held)>=4 and bool(np.all(np.abs(residual)<=.15)))
                continue
            fitted = solve(points[train], delta[train], model == "residual_similarity")
            if fitted is None:
                row["models"][model] = None
                continue
            da, db = fitted
            residual = 2*(delta[held]-(da*points[held]+db))/p1[0]
            errors = np.abs(residual)
            row["models"][model] = {
                "delta_linear": [da.real, da.imag], "delta_translation_quad": [db.real, db.imag],
                "held_sensor_vectors": np.column_stack([residual.real, residual.imag]).tolist(),
                "held_max_sensor": float(errors.max()) if len(errors) else None,
                "all_four_held_consistent_015": len(held) == 4 and bool(np.all(errors <= .15)),
                "at_least_four_held_consistent_015": len(held) >= 4 and bool(np.all(errors <= .15)),
            }
        report["rows"].append(row)
with a.out.open("x") as f:
    json.dump(report, f, indent=2, allow_nan=False)
    f.write("\n")
print(json.dumps({"controls": checks, "rows": len(report["rows"]), "out": str(a.out)}))
