"""Independent polygon-domain integral of the actual refused leaf; diagnostic only."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
import cmath
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import traceback
import warnings
from scipy.integrate import quad, IntegrationWarning
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m194e_frozen_independent_model", HERE / "independent-model.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def polygon_integral(scene, frame, native_poly, *, eps, budget):
    m.validate(scene, frame)
    centre = tuple(sum(v[j] for v in native_poly) / len(native_poly) for j in range(2))
    poly = [(v[0] - centre[0], v[1] - centre[1]) for v in native_poly]
    if m.moments(poly)[0] < 0:
        poly.reverse()
    full_area, full_moment = m.moments(poly)
    q0 = frame.transform(centre)
    n = frame.pull(scene.normal)
    length = math.hypot(*n)
    normal = (n[0] / length, n[1] / length)
    tangent = (-normal[1], normal[0])
    chief = (m.dot(scene.normal, q0) - scene.offset) / length
    df = frame.K * (frame.inverse_focus - 1 / scene.foreground_depth)
    prepared = []
    for rad, depth in ((scene.foreground, scene.foreground_depth), (scene.background, scene.background_depth)):
        d = frame.K * (frame.inverse_focus - 1 / depth)
        waves = [(a, frame.pull((2 * math.pi * fx, 2 * math.pi * fy)), phase + 2 * math.pi * (fx * q0[0] + fy * q0[1])) for a, fx, fy, phase in rad.waves]
        prepared.append((d, rad.constant + m.dot(rad.affine, q0), frame.pull(rad.affine), waves))
    full_fourier = {k: m.polygon_fourier(poly, k) for _, _, _, waves in prepared for _, k, _ in waves}

    def at_t(t):
        budget.tick()
        chord = math.sqrt(max(0., 1 - t * t))
        fg_poly = m.clip(poly, normal, -chief - df * t)
        fg_area, fg_moment = m.moments(fg_poly)
        fg_fourier = {k: m.polygon_fourier(fg_poly, k) for k in full_fourier}
        value = 0.
        for index, (d, base, gradient, waves) in enumerate(prepared):
            area = fg_area if index == 0 else full_area - fg_area
            moment = fg_moment if index == 0 else tuple(full_moment[j] - fg_moment[j] for j in range(2))
            value += 2 * chord * ((base + d * m.dot(gradient, normal) * t) * area + m.dot(gradient, moment))
            for amplitude, k, phase in waves:
                fourier = fg_fourier[k] if index == 0 else full_fourier[k] - fg_fourier[k]
                value += amplitude * 2 * chord * m.sinc(d * m.dot(k, tangent) * chord) * (fourier * cmath.exp(1j * (phase + d * m.dot(k, normal) * t))).real
        return value

    breaks = [-1., 1.]
    if df != 0:
        breaks += [(-chief - m.dot(normal, p)) / df for p in poly if -1 < (-chief - m.dot(normal, p)) / df < 1]
    breaks = sorted(set(breaks))
    total = error = 0.
    for left, right in zip(breaks[:-1], breaks[1:]):
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always", IntegrationWarning)
            value, indicator = quad(at_t, left, right, epsabs=eps * math.pi / (len(breaks) - 1), epsrel=0, limit=128)
        if seen:
            raise ValueError("diagnostic reference quadrature warning: " + str(seen[0].message))
        total += value / math.pi
        error += indicator / math.pi
    if not math.isfinite(total) or total < 0 or error > eps:
        raise ValueError("diagnostic reference bound failed")
    return dict(integral_e_pixel2=total, indicator_e_pixel2=error, area_pixel2=full_area, request_e_pixel2=eps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194e-independent-cell-diagnosis-v1", status="RUNNING", command=sys.argv, sources={}, checks=[])
    budget = m.Budget()
    try:
        for name in ("independent-model.py", "independent-cell-diagnosis.py", "independent-cell-diagnosis-preregister.md"):
            shutil.copyfile(HERE / name, args.output / name)
            result["sources"][name] = sha(HERE / name)
        if result["sources"]["independent-model.py"] != "0cd8ea2331b269e65befdee110560cbc345e89c12348cbe1dc3144f7c04443f0":
            raise ValueError("frozen independent model changed")

        def check(name, value, expected, tolerance=1e-8):
            passed = abs(value - expected) <= tolerance
            result["checks"].append(dict(name=name, value=value, expected=expected, tolerance=tolerance, passed=passed))
            if not passed:
                raise ValueError("control failed: " + name)

        tri = [(0., 0.), (1., 0.), (0., 1.)]
        for name, field, expected in (("triangle-constant", m.Radiance(10000), 5000), ("triangle-affine", m.Radiance(12000, (3., -2.)), 6000 + 1 / 6)):
            scene = m.Scene(1., 2., (1., 0.), .25, field, field)
            value = polygon_integral(scene, m.Frame(.875, 12.), tri, eps=1e-9, budget=budget)
            check(name, value["integral_e_pixel2"], expected)
        scene = m.Scene(1., 2., (1., 0.), .25, m.Radiance(30), m.Radiance(10))
        check("clipped-triangle-area", polygon_integral(scene, m.Frame(.875, 0.), tri, eps=1e-9, budget=budget)["integral_e_pixel2"], 10.625)
        k = (1.2, -.7)
        analytic = m.polygon_fourier(tri, k)
        real = quad(lambda x: quad(lambda y: math.cos(k[0] * x + k[1] * y), 0, 1 - x, epsabs=1e-12)[0], 0, 1, epsabs=1e-12)[0]
        imag = quad(lambda x: quad(lambda y: math.sin(k[0] * x + k[1] * y), 0, 1 - x, epsabs=1e-12)[0], 0, 1, epsabs=1e-12)[0]
        check("triangle-fourier-real", analytic.real, real, 1e-12)
        check("triangle-fourier-imag", analytic.imag, imag, 1e-12)
        diagnosis_path = HERE / "cell-diagnosis-1/result.json"
        diagnosis = json.loads(diagnosis_path.read_text())
        result["author_diagnosis"] = dict(path=str(diagnosis_path), sha256=sha(diagnosis_path))
        leaf = diagnosis["triangles"][-1]
        if leaf["depth"] != 6 or leaf["indicator"] <= leaf["allocated_budget"]:
            raise ValueError("actual terminal failing leaf required")
        scene, frame = m.intended_scene(), m.Frame(.875, 12.)
        primary = polygon_integral(scene, frame, leaf["triangle"], eps=1e-9, budget=budget)
        refined = polygon_integral(scene, frame, leaf["triangle"], eps=6.25e-11, budget=budget)
        check("leaf-reference-refinement", primary["integral_e_pixel2"], refined["integral_e_pixel2"], 1e-8)
        result["leaf"] = dict(author=leaf, independent_primary=primary, independent_refined=refined,
                              author_low_error_e_pixel2=leaf["low"] - refined["integral_e_pixel2"],
                              author_high_error_e_pixel2=leaf["high"] - refined["integral_e_pixel2"])
        result["whole_cell_frozen_reference_e"] = float(np.load(HERE / "independent-reference-1/refined-3.npy")[4, 30])
        result["status"] = "DIAGNOSED_CAMPAIGN_REMAINS_UNCOMMISSIONED"
    except Exception as exc:
        result["status"] = "DIAGNOSTIC_INVALID_CAMPAIGN_UNCOMMISSIONED"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    result["budget"] = budget.receipt()
    result["source_unchanged"] = all(sha(HERE / n) == v for n, v in result["sources"].items())
    (args.output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps(dict(status=result["status"], checks=len(result["checks"]), error=result.get("error"), leaf=result.get("leaf"))))
    return 0 if result["status"] == "DIAGNOSED_CAMPAIGN_REMAINS_UNCOMMISSIONED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
