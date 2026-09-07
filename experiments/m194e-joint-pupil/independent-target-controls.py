"""Released amendment4 actual target/mass controls; never float authority."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import traceback
import numpy as np
from scipy.special import j1
import scipy

HERE = Path(__file__).resolve().parent
MODEL_SHA = "a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8"
LEGACY_SHA = "a22d49fd43a1bc8d0f807fc1d4417104d5b9ffe1d771b418be58d276d7804460"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def bits(value, receipt):
    return struct.pack("<dd", value, receipt["value_error_indicator_e"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render-sha256", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194e-independent-target-controls-v1", status="RUNNING", command=sys.orig_argv,
                  executable=sys.executable, xoptions=sys._xoptions, python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
                  numerical_threads=2, sources={}, checks=[], standalone=[], target_calls=[], weight_faults=[])
    try:
        if sha(HERE / "model.py") != MODEL_SHA or sha(HERE / "render.py") != args.render_sha256:
            raise ValueError("externally pinned current numerical sources differ")
        for name in ("model.py", "render.py", "independent-target-controls.py", "independent-amendment-4-review.md", "independent-target-api-binding.md"):
            shutil.copyfile(HERE / name, args.output / name)
            result["sources"][name] = sha(HERE / name)
        legacy_path = HERE / "independent-author-api-5/render.py"
        if sha(legacy_path) != LEGACY_SHA:
            raise ValueError("archived a22d numerical source differs")
        shutil.copyfile(legacy_path, args.output / "legacy-render.py")
        result["legacy_sha256"] = LEGACY_SHA
        sys.path.insert(0, str(args.output.resolve()))
        import model as m
        import render as r
        legacy = module("independent_target_legacy", args.output / "legacy-render.py")

        def check(name, passed, **values):
            result["checks"].append(dict(name=name, passed=bool(passed), **values))
            if not passed:
                raise ValueError("control failed: " + name)

        def rejects(name, callback, *, fragments=(), classes=None):
            classes = classes or (r.NumericalFailure, ValueError)
            try:
                callback()
            except classes as exc:
                check(name, not fragments or any(v in str(exc).lower() for v in fragments), refusal=str(exc))
            else:
                check(name, False)

        scene = m.Scene(m.Field(8000.), m.Field(10000., waves=(m.Wave(2700., (.11, .073), .47),)),
                        (1.3, 2.5), (1., 0.), 0., "absent")
        frame = m.Frame(0, .71, 13.)
        points = ((11.375, 7.625), (3.125, 9.875), (19.625, 2.375), (6.875, 17.125))
        result["fixture"] = dict(scene=asdict(scene), frame=asdict(frame), points=points)
        config = r.Integrator()
        # Flat/null first, using the same public point and cell consumers.
        flat = replace(scene, background=m.Field(10000.))
        flat_point, flat_receipt = r.render_point(flat, frame, points[0])
        flat_cell, flat_cell_receipt = r.render_cell(flat, frame, points[0])
        check("flat-point-first", abs(flat_point-10000.) < 1e-8)
        check("flat-cell-first", abs(flat_cell-10000.) < 1e-8)
        db = 13. * (.71 - 1/2.5)
        angular_frequency = 2 * math.pi * abs(db) * math.hypot(.11, .073)
        attenuation = 2 * float(j1(angular_frequency)) / angular_frequency
        def analytic(xy):
            return 10000 + 2700 * math.cos(2*math.pi*(.11*xy[0]+.073*xy[1])+.47) * attenuation
        for i, xy in enumerate(points):
            old_value, old_receipt = legacy.render_point(scene, frame, xy)
            value, receipt = r.render_point(scene, frame, xy)
            meter = r.Meter(config)
            explicit_value, explicit_error = r.render_points(scene, frame, np.array([xy]), config, meter, point_tolerance=config.pupil_tolerance)
            check(f"standalone-{i}-old-byte-null", bits(value, receipt) == bits(old_value, old_receipt))
            check(f"standalone-{i}-explicit-default-byte-null", bits(value, receipt) == struct.pack("<dd", float(explicit_value[0]), float(explicit_error[0])))
            check(f"standalone-{i}-independent-disc-integral", abs(value-analytic(xy)) <= .02, value=value, expected=analytic(xy))
            result["standalone"].append(dict(xy=xy, value=value, receipt=receipt, old_receipt=old_receipt))
        strict_meter = r.Meter(config)
        try:
            value, error = r.render_points(scene, frame, np.array([points[0]]), config, strict_meter, point_tolerance=1e-18)
        except r.NumericalFailure as exc:
            check("strict-point-target-real-refusal", "angular" in str(exc).lower() or "point result/error" in str(exc).lower(), refusal=str(exc))
            result["strict_target"] = dict(status="REFUSED", refusal=str(exc), work=strict_meter.receipt())
        else:
            work = strict_meter.receipt()
            check("strict-point-target-more-actual-nodes", work["angular_nodes"] > result["standalone"][0]["receipt"]["work"]["angular_nodes"], work=work)
            check("strict-point-target-analytic-integral", abs(float(value[0])-analytic(points[0])) <= .02)
            result["strict_target"] = dict(status="RETURNED", value=float(value[0]), indicator=float(error[0]), work=work)

        class TargetBindingError(RuntimeError):
            pass
        def cell_call(arm, observer="count", missing=None):
            cfg = r.integrator_for(arm)
            meter = r.Meter(cfg, observer)
            real_points = r.render_points
            calls, hook_calls = [], 0
            target = .000046875 / (4 if arm == "angle-refined" else 1)
            def observed_points(sc, fr, xy, integrator, measure, **kwargs):
                nonlocal hook_calls
                batch = "low" if len(xy) == cfg.cell_low**2 else "high" if len(xy) == cfg.cell_high**2 else "unknown"
                actual = dict(kwargs)
                if batch == missing:
                    actual.pop("point_tolerance", None)
                returned = real_points(sc, fr, xy, integrator, measure, **actual)
                if observer != "off":
                    hook_calls += 1
                if observer == "count":
                    calls.append(dict(batch=batch, points=len(xy), target=actual.get("point_tolerance")))
                if actual.get("point_tolerance") != target:
                    raise TargetBindingError("actual " + batch + " batch used missing/wrong inner target")
                return returned
            r.render_points = observed_points
            try:
                value, receipt = r.render_cell(scene, frame, points[0], cfg, meter)
            finally:
                r.render_points = real_points
            return dict(arm=arm, observer=observer, calls=calls, hook_calls=hook_calls, value=value, receipt=receipt)
        target_nulls = {}
        for arm in ("primary", "angle-refined", "cell-refined"):
            runs = [cell_call(arm, mode) for mode in ("off", "count", "placebo")]
            result["target_calls"].extend(runs)
            check(arm + "-target-observer-byte-null", len({bits(v["value"], v["receipt"]) for v in runs}) == 1)
            count = runs[1]
            check(arm + "-both-actual-batches-observed", {v["batch"] for v in count["calls"]} == {"low", "high"})
            check(arm + "-count-placebo-hook-power", runs[0]["hook_calls"] == 0 and count["hook_calls"] > 0 and runs[2]["hook_calls"] == count["hook_calls"] and not runs[2]["calls"])
            target_nulls[arm] = {v["target"] for v in count["calls"]}
        check("actual-family-target-isolation", target_nulls["primary"] == target_nulls["cell-refined"] == {.000046875} and target_nulls["angle-refined"] == {.00001171875})
        for batch in ("low", "high"):
            rejects("missing-actual-" + batch + "-batch-binding", lambda batch=batch: cell_call("primary", missing=batch), fragments=(batch,), classes=(TargetBindingError,))

        # Actual new cell and the preserved old-policy failure, no new reference.
        ref_result = HERE / "independent-reference-1/result.json"
        if sha(ref_result) != "8791700cdc969847ff75f9fbd9205739ee2135ac4bbbdbe445d00b6664c7eccc":
            raise ValueError("frozen reference changed")
        ref_record = next(v for v in json.loads(ref_result.read_text())["frames"] if v["arm"] == "refined" and v["index"] == 2)
        ref_path = ref_result.parent / ref_record["array"]["path"]
        if sha(ref_path) != ref_record["array"]["sha256"]:
            raise ValueError("frozen scalar reference changed")
        expected = float(np.load(ref_path, allow_pickle=False)[0, 4])
        cfg = r.integrator_for("cell-refined")
        actual, receipt = r.render_cell(m.primary_scene(), m.primary_frames()[2], (4., 0.), cfg)
        check("actual-full3-failed-cell-new-policy", abs(actual-expected) <= .004 and receipt["cell_indicator_e"] <= .0001875 and receipt["weighted_high_pupil_indicator_e"] <= .00025, value=actual, reference=expected, receipt=receipt)
        rejects("archived-full3-cell-refusal", lambda: legacy.render_cell(m.primary_scene(), m.primary_frames()[2], (4., 0.), legacy.integrator_for("cell-refined")), fragments=("depth/global-error",), classes=(legacy.NumericalFailure,))
        real_points = r.render_points
        def old_target(sc, fr, xy, integrator, meter, **kwargs):
            return real_points(sc, fr, xy, integrator, meter)
        r.render_points = old_target
        try:
            old_value, old_receipt = r.render_cell(m.primary_scene(), m.primary_frames()[2], (4., 0.), cfg)
        except r.NumericalFailure as exc:
            result["same_source_old_target_ablation"] = dict(status="REFUSED", refusal=str(exc))
        else:
            result["same_source_old_target_ablation"] = dict(status="RETURNED", value=old_value, receipt=old_receipt)
        finally:
            r.render_points = real_points
        check("old-target-ablation-disposition-recorded", "status" in result["same_source_old_target_ablation"])

        triangles = {"normal": np.array(((2.25, -1.5), (4.25, -2.25), (3.25, 0.))),
                     "tiny": np.array(((0., 0.), (1., 0.), (1., 2.**-50)))}
        # Fixed affine radiance is evaluated only on these bounded domains.
        affine = replace(flat, background=m.Field(10000., affine=(3., -2.)))
        real_rule = r.triangle_rule
        def leaf_call(tri, source, corrupt=None):
            hits = []
            def changed_rule(t, order, indices=()):
                xy, weights = real_rule(t, order, indices)
                if corrupt and (order == config.cell_high if corrupt == "high-overmass" else order == config.cell_low):
                    weights = weights.copy()
                    if corrupt == "negative":
                        weights[0] = -weights[0]
                    elif corrupt == "zero":
                        weights[0] = 0.
                    elif corrupt == "nan":
                        weights[0] = np.nan
                    elif corrupt == "infinite":
                        weights[0] = np.inf
                    elif corrupt == "low-halfmass":
                        weights *= .5
                    elif corrupt == "high-overmass":
                        weights *= 1 + 2.**-20
                    hits.append(order)
                return xy, weights
            r.triangle_rule = changed_rule
            try:
                value = r.evaluate_cell_leaf(source, frame, tri.copy(), (0,), config, r.Meter(config))
            finally:
                r.triangle_rule = real_rule
                if corrupt:
                    result["weight_faults"].append(dict(fault=corrupt, actual_orders=hits, area=float(r.triangle_area(tri))))
                    if not hits:
                        raise ValueError("weight fault did not reach actual rule")
            return value
        for name, tri in triangles.items():
            for kind, source in (("constant", flat), ("affine", affine)):
                got = leaf_call(tri, source)
                area = float(r.triangle_area(tri))
                centroid = tri.mean(axis=0)
                expected_integral = area * (10000. if kind == "constant" else 10000.+3*centroid[0]-2*centroid[1])
                check(name + "-" + kind + "-valid-mass-consumption", abs(got.high/area-expected_integral/area) <= .02)
            for fault in ("negative", "zero", "nan", "infinite", "low-halfmass", "high-overmass"):
                rejects(name + "-actual-weight-" + fault, lambda tri=tri, fault=fault: leaf_call(tri, flat, fault), fragments=("weight", "mass", "quadrature"))
        for name, value in (("negative", -1.), ("zero", 0.), ("nan", float("nan")), ("infinite", float("inf")), ("false", False), ("true", True)):
            rejects("config-inner-target-" + name, lambda value=value: replace(config, cell_point_tolerance=value), fragments=("target", "tolerance", "positive", "finite"))
            rejects("actual-point-target-" + name, lambda value=value: r.render_points(scene, frame, np.array([points[0]]), config, r.Meter(config), point_tolerance=value), fragments=("target", "tolerance", "positive", "finite", "cap"))
        rejects("actual-point-target-above-cap", lambda: r.render_points(scene, frame, np.array([points[0]]), config, r.Meter(config), point_tolerance=.0003), fragments=("target", "tolerance", "cap"))
        rejects("cell-inner-target-above-quarter-cell-cap", lambda: r.render_cell(scene, frame, points[0], replace(config, cell_point_tolerance=.0002)), fragments=("target", "tolerance", "cap", "quarter"))
        check("valid-inner-target-companion", math.isfinite(r.render_cell(scene, frame, points[0], replace(config, cell_point_tolerance=.000046875))[0]))
        result["status"] = "PASS_TARGET_MASS_COMPONENTS_ONLY"
    except Exception as exc:
        result["status"] = "UNCOMMISSIONED_TARGET_CONTROLS"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    result["source_unchanged"] = all(sha(HERE / name) == digest for name, digest in result["sources"].items())
    if not result["source_unchanged"]:
        result["status"] = "UNCOMMISSIONED_TARGET_CONTROLS"
    (args.output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps(dict(status=result["status"], checks=len(result["checks"]), error=result.get("error"))))
    return 0 if result["status"] == "PASS_TARGET_MASS_COMPONENTS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
