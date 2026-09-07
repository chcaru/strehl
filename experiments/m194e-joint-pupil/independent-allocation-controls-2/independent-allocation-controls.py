"""Released amendment3 controls of actual frontier/queue APIs; no float authority."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
from dataclasses import replace
import hashlib
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


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render-sha256", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194e-independent-allocation-controls-v1", status="RUNNING", command=sys.argv, sources={}, checks=[], runs=[])
    try:
        if sha(HERE / "model.py") != MODEL_SHA or sha(HERE / "render.py") != args.render_sha256:
            raise ValueError("externally pinned numerical sources differ")
        for name in ("model.py", "render.py", "independent-allocation-controls.py", "independent-amendment-3-review.md"):
            shutil.copyfile(HERE / name, args.output / name)
            result["sources"][name] = sha(HERE / name)
        sys.path.insert(0, str(args.output.resolve()))
        import model as m
        import render as r
        config = r.Integrator()
        roots = [np.array(((0., 0.), (1., 0.), (1., 1.))), np.array(((0., 0.), (1., 1.), (0., 1.)))]

        def check(name, passed, **values):
            result["checks"].append(dict(name=name, passed=bool(passed), **values))
            if not passed:
                raise ValueError("control failed: " + name)

        def reject(name, callback, fragment=None):
            try:
                callback()
            except r.NumericalFailure as exc:
                check(name, fragment is None or fragment in str(exc), refusal=str(exc))
            else:
                check(name, False)

        def leaf(tri, path, delta=0., pl=0., ph=0.):
            return r.CellLeaf(path, tri, 10000., 10000. + delta, pl, ph)

        def aggregate(leaves, areas=(.5, .5)):
            return r.aggregate_frontier(leaves, areas, config)

        def acceptable(s):
            return s["cell_error"] <= config.cell_tolerance and s["pupil_error"] <= config.pupil_tolerance

        def run(name, law, *, observer="count", triangles=None, meter=None, reverse_storage=False):
            tris = [t.copy() for t in (roots if triangles is None else triangles)]
            meter = meter or r.Meter(config, observer)
            trace, accepted = [], []
            original_observe = meter.observe_cell
            def observe(leaves):
                accepted.extend(dict(path=list(v.path), area=v.area, indicator=v.indicator, depth=v.depth) for v in leaves)
                original_observe(leaves)
            meter.observe_cell = observe
            def evaluate(tri, path):
                trace.append(list(path))
                return law(tri, path)
            real_aggregate = r.aggregate_frontier
            def shuffled(leaves, areas, cfg):
                leaves.reverse()
                return real_aggregate(leaves, areas, cfg)
            if reverse_storage:
                r.aggregate_frontier = shuffled
            try:
                value, receipt = r.integrate_frontier(tris, evaluate, config, meter)
            finally:
                r.aggregate_frontier = real_aggregate
                meter.observe_cell = original_observe
            item = dict(name=name, value=value, receipt=receipt, evaluation_paths=trace, accepted=accepted)
            result["runs"].append(item)
            return item, meter

        # Flat/null is first: complete exact records admit without any split.
        flat, _ = run("flat-null-first", lambda t, p: leaf(t, p))
        check("flat-complete-no-split", flat["evaluation_paths"] == [[0], [1]] and flat["receipt"]["value_error_indicator_e"] == 0.)
        signed = [leaf(roots[0], (0,), .0006), leaf(roots[1], (1,), -.0006)]
        s = aggregate(signed)
        check("signed-cancellation-does-not-admit", not acceptable(s) and math.fsum(v.high-v.low for v in signed) == 0., aggregate=s)
        check("signed-half-size-valid-companion", acceptable(aggregate([leaf(roots[0], (0,), .0003), leaf(roots[1], (1,), -.0003)])))
        pupil_terms = [leaf(roots[0], (0,), .0004, .0002, .0002), leaf(roots[1], (1,))]
        check("both-pupil-errors-in-cell-total", not acceptable(aggregate(pupil_terms)), aggregate=aggregate(pupil_terms))
        check("pupil-errors-valid-companion", acceptable(aggregate([leaf(roots[0], (0,), .0002, .0001, .0001), leaf(roots[1], (1,))])))
        high = aggregate([leaf(roots[0], (0,), ph=.0003), leaf(roots[1], (1,))])
        check("separate-high-pupil-limit", high["cell_error"] < .00075 and not acceptable(high), aggregate=high)
        high_ok = aggregate([leaf(roots[0], (0,), ph=.0002), leaf(roots[1], (1,))])
        check("separate-pupil-valid-companion", acceptable(high_ok))
        high_run, _ = run("pupil-receipt", lambda t, p: leaf(t, p, ph=.0002 if p == (0,) else 0.))
        check("final-indicator-keeps-repeated-high-pupil", high_run["receipt"]["value_error_indicator_e"] == .0004)

        # Two disjoint triangles partition one area-one triangular component.
        small = np.array(((0., 0.), (.125, 0.), (0., 1.)))
        remainder = np.array(((.125, 0.), (2., 0.), (0., 1.)))
        over, _ = run("global-overallocation-valid", lambda t, p: leaf(t, p, .0001 if p == (0,) else .00005), triangles=[small, remainder])
        check("local-overallocation-global-pass", over["receipt"]["cell_indicator_e"] < .00075 and over["accepted"][0]["indicator"] > .00075 / 16)
        # The two synthetic roots have prescribed areas; no optical/spatial claim.
        def capped_law(t, p):
            if p[0] == 0:
                d = .0007 if all(v == 0 for v in p[1:]) else 0.
            else:
                d = .0001 if len(p) == 1 else .00001
            return leaf(t, p, d)
        cap, _ = run("capped-largest-stays-while-other-splits", capped_law)
        check("capped-depth6-retained", any(v["depth"] == 6 and v["indicator"] > .00069 for v in cap["accepted"]))
        check("other-root-refined-after-cap", cap["evaluation_paths"][-2:] == [[1, 0], [1, 1]] and abs(cap["receipt"]["cell_indicator_e"] - .00072) < 1e-10)
        reject("all-capped-excess-refuses", lambda: run("all-capped-excess", lambda t, p: leaf(t, p, .0008 * float(r.triangle_area(t)))), "depth/global-error")
        def increasing(t, p):
            if p[0] == 1:
                d = 0.
            elif len(p) == 1:
                d = .001
            elif len(p) == 2:
                d = .0007
            else:
                d = .00001
            return leaf(t, p, d)
        inc, _ = run("nonmonotone-parent-indicator", increasing)
        check("increase-does-not-abort", inc["evaluation_paths"][-2:] == [[0, 0, 0], [0, 0, 1]] and abs(inc["receipt"]["cell_indicator_e"] - .00072) < 1e-10)
        tie_law = lambda t, p: leaf(t, p, .0006 if len(p) == 1 else 0.)
        tie, _ = run("canonical-tie", tie_law)
        shuffled, _ = run("reversed-storage-tie", tie_law, reverse_storage=True)
        check("canonical-priority-tie", tie["evaluation_paths"] == [[0], [1], [0, 0], [0, 1]])
        check("storage-order-invariance", tie["evaluation_paths"] == shuffled["evaluation_paths"] and tie["value"] == shuffled["value"] and tie["receipt"]["value_error_indicator_e"] == shuffled["receipt"]["value_error_indicator_e"])

        valid = [leaf(roots[0], (0,)), leaf(roots[1], (1,))]
        check("fault-valid-frontier-companion", acceptable(aggregate(valid)))
        for field in ("pupil_low", "pupil_high"):
            for label, bad in (("negative", -1.), ("nan", float("nan")), ("infinite", float("inf"))):
                reject(field + "-" + label, lambda field=field, bad=bad: aggregate([replace(valid[0], **{field: bad}), valid[1]]), "indicator")
        for field in ("low", "high"):
            for label, bad in (("nan", float("nan")), ("infinite", float("inf"))):
                reject(field + "-" + label, lambda field=field, bad=bad: aggregate([replace(valid[0], **{field: bad}), valid[1]]), "indicator")
        reject("missing-root", lambda: aggregate(valid[:1]), "coverage")
        reject("missing-child", lambda: aggregate([replace(valid[0], path=(0, 0)), valid[1]]), "coverage")
        reject("duplicate-path", lambda: aggregate(valid + valid[:1]), "overlapping")
        reject("parent-with-descendant", lambda: aggregate(valid + [replace(valid[0], path=(0, 0))]), "overlapping")
        reject("depth-seven", lambda: aggregate([replace(valid[0], path=(0, 0, 0, 0, 0, 0, 0, 0)), valid[1]]), "path/depth")
        biased = roots[0].copy()
        biased[1, 0] += .001
        reject("biased-area", lambda: aggregate([replace(valid[0], triangle=biased), valid[1]]), "area coverage")
        # Geometry is enforced by actual evaluator boundary, beyond aggregate area.
        saved_child = []
        def duplicated_half(t, p):
            if p == (0, 0):
                saved_child.append(t.copy())
            if p == (0, 1):
                return leaf(saved_child[0], p)
            return tie_law(t, p)
        reject("duplicated-spatial-half-real-boundary", lambda: run("duplicate-spatial-half", duplicated_half), "changed geometry/path")
        def changed_in_place(t, p):
            t[0, 0] += .01
            return leaf(t, p)
        reject("in-place-geometry-mutation", lambda: run("in-place-geometry", changed_in_place), "changed geometry/path")
        reject("callback-path-mutation", lambda: run("path-mutation", lambda t, p: leaf(t, p + (0,))), "changed geometry/path")
        expired = r.Meter(config)
        expired.started_wall -= config.wall_limit + 1
        reject("work-wall-exhaustion", lambda: run("expired", lambda t, p: leaf(t, p), meter=expired), "time ceiling")
        exhausted = r.Meter(config)
        exhausted.points = config.point_limit + 1
        reject("work-point-exhaustion", lambda: run("exhausted", lambda t, p: leaf(t, p), meter=exhausted), "evaluation ceiling")
        check("work-valid-companion", run("work-valid", lambda t, p: leaf(t, p))[0]["receipt"]["leaf_triangles"] == 2)

        # Count actual accepted frontiers, including a constant first cell.
        null_bytes = []
        zero = dict(cells=0, leaves=0, minimum_depth=0, maximum_depth=0, locally_overallocated_leaves=0, cells_with_locally_overallocated_leaves=0)
        for mode in ("off", "count", "placebo"):
            meter = r.Meter(config, mode)
            check(mode + "-before-completion-zero", meter.cell_allocation == zero)
            first, _ = run(mode + "-constant-first", lambda t, p: leaf(t, p), meter=meter)
            second, _ = run(mode + "-refined-second", capped_law, meter=meter)
            null_bytes.append(struct.pack("<dddd", first["value"], first["receipt"]["value_error_indicator_e"], second["value"], second["receipt"]["value_error_indicator_e"]))
            if mode == "count":
                all_leaves = first["accepted"] + second["accepted"]
                per_cell = [first["accepted"], second["accepted"]]
                expected = dict(cells=2, leaves=len(all_leaves), minimum_depth=min(v["depth"] for v in all_leaves), maximum_depth=max(v["depth"] for v in all_leaves),
                                locally_overallocated_leaves=sum(v["indicator"] > .00075*v["area"] for v in all_leaves),
                                cells_with_locally_overallocated_leaves=sum(any(v["indicator"] > .00075*v["area"] for v in group) for group in per_cell))
                check("count-matches-actual-frontiers", meter.cell_allocation == expected, actual=meter.cell_allocation, expected=expected)
                check("count-depth-extrema-powered", expected["minimum_depth"] == 0 and expected["maximum_depth"] == 6 and expected["locally_overallocated_leaves"] > 0)
            else:
                check(mode + "-allocation-counters-zero", meter.cell_allocation == zero)
            check(mode + "-optional-hook-disposition", (meter.optional_hook_calls == 0) == (mode == "off"))
            meter.new_frame()
            check(mode + "-new-frame-reset", meter.cell_allocation == zero)
        check("allocation-observer-original-on-placebo-byte-null", len(set(null_bytes)) == 1, sha256=hashlib.sha256(null_bytes[0]).hexdigest())
        # Real model cells and frozen whole-cell reference, no leaf truth claim.
        refpath = HERE / "independent-reference-1/result.json"
        if sha(refpath) != "8791700cdc969847ff75f9fbd9205739ee2135ac4bbbdbe445d00b6664c7eccc":
            raise ValueError("frozen reference changed")
        record = next(v for v in json.loads(refpath.read_text())["frames"] if v["arm"] == "refined" and v["index"] == 3)
        array_path = refpath.parent / record["array"]["path"]
        if sha(array_path) != record["array"]["sha256"]:
            raise ValueError("frozen reference bytes changed")
        reference = np.load(array_path, allow_pickle=False)
        for x, y in ((30, 4), (31, 7)):
            meter = r.Meter(config)
            seen = []
            real_observe = meter.observe_cell
            def observe_real(leaves):
                seen.extend(dict(path=list(v.path), depth=v.depth, area=v.area, indicator=v.indicator) for v in leaves)
                real_observe(leaves)
            meter.observe_cell = observe_real
            value, receipt = r.render_cell(m.primary_scene(), m.primary_frames()[3], (x, y), config, meter)
            check(f"actual-cell-{x}-{y}-unchanged-bars", abs(value-reference[y, x]) <= .004 and receipt["cell_indicator_e"] <= .00075 and receipt["weighted_high_pupil_indicator_e"] <= .00025, value=value, reference=float(reference[y, x]), receipt=receipt, accepted=seen)
            check(f"actual-cell-{x}-{y}-count-frontier", meter.cell_allocation["leaves"] == len(seen) and meter.cell_allocation["minimum_depth"] == min(v["depth"] for v in seen) and meter.cell_allocation["maximum_depth"] == max(v["depth"] for v in seen))
        result["status"] = "PASS_ALLOCATION_COMPONENTS_ONLY"
    except Exception as exc:
        result["status"] = "UNCOMMISSIONED_ALLOCATION_CONTROLS"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    result["source_unchanged"] = all(sha(HERE / name) == digest for name, digest in result["sources"].items())
    if not result["source_unchanged"]:
        result["status"] = "UNCOMMISSIONED_ALLOCATION_CONTROLS"
    (args.output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps(dict(status=result["status"], checks=len(result["checks"]), error=result.get("error"))))
    return 0 if result["status"] == "PASS_ALLOCATION_COMPONENTS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
