"""Prospectively fixed amendment2 component/predicate and actual-cell controls."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
from dataclasses import replace
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent
MODEL_SHA = "a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8"
LEGACY_SHA = "ef52c45d28ec2dda5aa897cfd57dacc4b4a3e300d3a581c35f305c76e2dd03f8"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render-sha256", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194e-independent-map-controls-v1", status="RUNNING", command=sys.argv, sources={}, checks=[])
    try:
        if sha(HERE / "model.py") != MODEL_SHA or sha(HERE / "render.py") != args.render_sha256:
            raise ValueError("external final numerical source binding differs")
        for name in ("model.py", "render.py", "independent-model.py", "independent-map-controls.py", "independent-amendment-2-review.md"):
            shutil.copyfile(HERE / name, args.output / name)
            result["sources"][name] = sha(HERE / name)
        legacy_path = HERE / "independent-author-api-3/render.py"
        if sha(legacy_path) != LEGACY_SHA:
            raise ValueError("retained old-rule source binding differs")
        shutil.copyfile(legacy_path, args.output / "legacy-render.py")
        result["legacy_render_sha256"] = LEGACY_SHA
        sys.path.insert(0, str(args.output.resolve()))
        import model as m
        import render as r
        legacy = module("independent_legacy_duffy", args.output / "legacy-render.py")
        reference = module("independent_map_fourier_reference", args.output / "independent-model.py")

        def check(name, passed, **values):
            result["checks"].append(dict(name=name, passed=bool(passed), **values))
            if not passed:
                raise ValueError("control failed: " + name)

        def close(name, value, expected, tolerance):
            check(name, abs(value - expected) <= tolerance, value=float(value), expected=float(expected), tolerance=tolerance)

        triangle = np.array(((2.25, -1.5), (4.25, -2.25), (3.25, 0.)), dtype=np.float64)
        n = (.75, 2.)
        frame = m.Frame(0, .5, 6 / math.hypot(*n))
        scene = m.Scene(m.Field(10000), m.Field(10000), (1., 2.), n, 1.6875)
        k = np.array((.31, -.17))
        exact_fourier = reference.polygon_fourier([tuple(v) for v in triangle], tuple(k))
        permutations = list(itertools.permutations(range(3)))
        for perm in permutations:
            tri = triangle[list(perm)].copy()
            before = tri.tobytes()
            label = "perm-" + "".join(map(str, perm))
            for kind, original_indices in (("edge", (0, 1)), ("vertex", (2,))):
                indices = tuple(perm.index(i) for i in original_indices)
                xy, weights = r.triangle_rule(tri, 4, indices)
                close(label + "-" + kind + "-area", float(weights.sum()), 15 / 8, 1e-10)
                close(label + "-" + kind + "-affine", float(weights @ (10000 + 3 * xy[:, 0] - 2 * xy[:, 1])), 18772.96875, 1e-8)
                lc = (.75 * xy[:, 0] + 2 * xy[:, 1] + 1.3125) / 3.75
                lb = (1.5 * (xy[:, 0] - 2.25) - (xy[:, 1] + 1.5)) / 3.75
                check(label + "-" + kind + "-positive-inside", bool(np.all(weights >= 0) and np.min(lc) >= -1e-12 and np.min(lb) >= -1e-12 and np.min(1 - lc - lb) >= -1e-12))
                lam = lc if kind == "edge" else 1 - lc
                expected = 3 / 7 if kind == "edge" else 15 / 14
                close(label + "-" + kind + "-cusp", float(weights @ lam ** 1.5), expected, 1e-10)
                old_xy, old_weights = legacy.triangle_rule(tri, 4)
                old_lc = (.75 * old_xy[:, 0] + 2 * old_xy[:, 1] + 1.3125) / 3.75
                old_lam = old_lc if kind == "edge" else 1 - old_lc
                error = float(old_weights @ old_lam ** 1.5) - expected
                check(label + "-" + kind + "-linear-destroyer-rejected", abs(error) > 1e-10, error=error)
                check(label + "-" + kind + "-wrong-Jacobian-rejected", abs(float((weights * .5).sum()) - 15 / 8) > 1e-10)
            for kind, offset, wanted in (("edge", 1.6875, (0, 1)), ("vertex", -.5625, (2,))):
                for delta in (0., 2. ** -45, -(2. ** -45), 2. ** -34, -(2. ** -34)):
                    selected = r.tangent_indices(tri, replace(scene, mask_offset=offset + delta), frame)
                    expected_indices = {perm.index(i) for i in wanted} if abs(delta) <= 2. ** -45 else set()
                    prefix = label + "-" + kind + "-delta-" + str(delta)
                    check(prefix + "-predicate", set(selected) == expected_indices, indices=list(selected))
                    xy, weights = r.triangle_rule(tri, 8, selected)
                    close(prefix + "-area", float(weights.sum()), 15 / 8, 1e-10)
                    close(prefix + "-affine", float(weights @ (10000 + 3 * xy[:, 0] - 2 * xy[:, 1])), 18772.96875, 1e-8)
                    value = weights @ np.exp(1j * (xy @ k))
                    close(prefix + "-Fourier", abs(value - exact_fourier), 0., 1e-8)
                    if not selected:
                        old_xy, old_weights = legacy.triangle_rule(tri, 8)
                        check(prefix + "-old-rule-byte-null", xy.tobytes() == old_xy.tobytes() and weights.tobytes() == old_weights.tobytes())
            coalesced = replace(frame, K=2 * (2. ** -60) / math.hypot(*n))
            selected = r.tangent_indices(tri, replace(scene, mask_offset=2.4375), coalesced)
            check(label + "-coalesced-deterministic", set(selected) == {perm.index(2)})
            xy, weights = r.triangle_rule(tri, 4, selected)
            close(label + "-coalesced-area", float(weights.sum()), 15 / 8, 1e-10)
            for name, sc, fr in (("R0", scene, replace(frame, K=0.)), ("full", replace(scene, mask_state="full"), frame), ("absent", replace(scene, mask_state="absent"), frame)):
                selected = r.tangent_indices(tri, sc, fr)
                check(label + "-" + name + "-old-path", not selected)
                xy, weights = r.triangle_rule(tri, 4, selected)
                old_xy, old_weights = legacy.triangle_rule(tri, 4)
                check(label + "-" + name + "-byte-null", xy.tobytes() == old_xy.tobytes() and weights.tobytes() == old_weights.tobytes())
            check(label + "-coordinates-unchanged", tri.tobytes() == before)
        tiny = np.array(((0., 0.), (1., 0.), (1., 2. ** -50)))
        tiny_scene = replace(scene, mask_normal=(0., 1.), mask_offset=1.)
        tiny_frame = replace(frame, K=2.)
        selected = r.tangent_indices(tiny, tiny_scene, tiny_frame)
        check("three-near-candidates-closest-edge", set(selected) == {0, 1})
        xy, weights = r.triangle_rule(tiny, 4, selected)
        close("three-near-candidates-retain-area-ratio", float(weights.sum()) / (2. ** -51), 1., 1e-12)
        check("three-near-candidates-positive", bool(np.all(weights >= 0) and weights.sum() > 0))
        for bad_value in (np.inf, np.nan):
            invalid = triangle.copy()
            invalid[0, 0] = bad_value
            try:
                r.tangent_indices(invalid, scene, frame)
            except (ValueError, r.NumericalFailure) as exc:
                check("nonfinite-predicate-refusal-" + str(bad_value), True, refusal=str(exc))
            else:
                check("nonfinite-predicate-refusal-" + str(bad_value), False)
        ref_result = HERE / "independent-reference-1/result.json"
        if sha(ref_result) != "8791700cdc969847ff75f9fbd9205739ee2135ac4bbbdbe445d00b6664c7eccc":
            raise ValueError("frozen whole-cell reference result changed")
        ref_record = next(v for v in json.loads(ref_result.read_text())["frames"] if v["arm"] == "refined" and v["index"] == 3)
        ref_path = ref_result.parent / ref_record["array"]["path"]
        if sha(ref_path) != ref_record["array"]["sha256"]:
            raise ValueError("frozen whole-cell reference array changed")
        expected = float(np.load(ref_path, allow_pickle=False)[4, 30])
        subject_scene, subject_frame = m.primary_scene(), m.primary_frames()[3]
        value, receipt = r.render_cell(subject_scene, subject_frame, (30., 4.))
        close("actual-formerly-refused-cell", value, expected, .004)
        real_rule = r.triangle_rule
        counts = {0: 0, 1: 0, 2: 0}

        def observed_rule(tri, order, indices=()):
            counts[len(indices)] += 1
            return real_rule(tri, order, indices)

        r.triangle_rule = observed_rule
        try:
            observed, observed_receipt = r.render_cell(subject_scene, subject_frame, (30., 4.))
        finally:
            r.triangle_rule = real_rule
        check("actual-map-observer-byte-null", struct.pack("<d", value) == struct.pack("<d", observed))
        check("actual-both-map-branches-powered", counts[1] > 0 and counts[2] > 0, counts=counts)
        result["actual_cell"] = dict(value_e=value, reference_e=expected, receipt=receipt, observed_receipt=observed_receipt, selected_rule_calls=counts,
                                     scalar_sha256=hashlib.sha256(struct.pack("<d", value)).hexdigest())
        r.triangle_rule = lambda tri, order, indices=(): real_rule(tri, order, ())
        try:
            r.render_cell(subject_scene, subject_frame, (30., 4.))
        except r.NumericalFailure as exc:
            check("same-source-linear-map-ablation-refuses", "cell depth/error ceiling" in str(exc), refusal=str(exc))
        else:
            check("same-source-linear-map-ablation-refuses", False)
        finally:
            r.triangle_rule = real_rule
        result["status"] = "PASS_MAP_COMPONENTS_ONLY"
    except Exception as exc:
        result["status"] = "UNCOMMISSIONED_MAP_CONTROLS"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    result["source_unchanged"] = all(sha(HERE / n) == v for n, v in result["sources"].items())
    if not result["source_unchanged"]:
        result["status"] = "UNCOMMISSIONED_MAP_CONTROLS"
    (args.output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps(dict(status=result["status"], checks=len(result["checks"]), error=result.get("error"))))
    return 0 if result["status"] == "PASS_MAP_COMPONENTS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
