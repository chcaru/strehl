"""Prospective M194g private controls, never the intended 320x240 count.

Falsifiers fixed before first execution: tangent wrongly selected; omission of
cell support or foreground radius; changed exact rational support; substituted
precombined height; missing low points/cell, duplicate cell, invalid rule mass;
strict-cap equality accepted; clocks reset between frames; aliased arrays counted
twice; missing owned storage; cached/foreign model execution; incomplete intended
population accepted. The positive controls must exercise all three branches and
both rule batches. Source pixels/radiance are trapped, not computed.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback
import types

HERE = Path(__file__).resolve().parent


def module(path, name):
    raw = path.read_bytes()
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    value = importlib.util.module_from_spec(spec)
    value.__file__ = str(path)
    sys.modules[name] = value
    exec(compile(raw, str(path), "exec"), value.__dict__)
    return value


@contextmanager
def patch(obj, name, value):
    original = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, original)


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194g-author-controls-v1", status="running", checks=[],
                  scope="small private geometry/API controls, not intended cost admission",
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  invocation=dict(orig_argv=sys.orig_argv, argv=sys.argv, xoptions=sys._xoptions,
                                  executable=sys.executable, cwd=str(Path.cwd())))
    def check(name, passed, detail=None):
        result["checks"].append(dict(name=name, passed=bool(passed), detail=detail))
        if not passed:
            raise AssertionError(name)
    def refuses(name, function, text=None):
        try:
            function()
        except Exception as exc:
            check(name, text is None or text in str(exc), repr(exc))
        else:
            check(name, False, "unexpected acceptance")
    try:
        p = module(HERE / "preflight.py", "m194g_author_preflight")
        np = p.np
        own = [HERE / name for name in ("pinned-loader.py", "geometry.py", "preflight.py", "author-controls.py")]
        bound = p.loader.load_frozen()
        m, r = bound.model, bound.render
        sources = {str(path): p.loader.checked_bytes(path)[1] for path in own}
        sources.update({v["path"]: v for v in bound.bindings.values()})
        result["sources_before"] = sources
        (output / "source").mkdir()
        for binding in sources.values():
            (output / "source" / Path(binding["path"]).name).write_bytes(Path(binding["path"]).read_bytes())
        fixture, fixture_ref = p.load_fixture()
        result["fixture"] = fixture_ref
        check("fixed fixture parsed", fixture["width"] == 320 and fixture["arms"] == ["primary", "angle-refined", "cell-refined"])
        malformed = output / "changed-fixture.json"
        malformed.write_text('{"schema":"m194g-expected-fixture-v1","width":true}', encoding="utf-8")
        refuses("changed fixture bytes refuse", lambda: p.load_fixture(malformed), "pinned source mismatch")
        refuses("candidate-selected fixture hash refuses", lambda: p.load_fixture(malformed, hashlib.sha256(malformed.read_bytes()).hexdigest()), "external fixture")

        scene = m.Scene(m.Field(20), m.Field(10), (1, 2), (1, 0), 3)
        frame = m.Frame(0, .5, 2)  # df=-1; native half-cell support .5.
        selector = p.geometry.ExactSelector(scene, frame)
        check("three branches actually occur", [selector.classify((x, 0)) for x in (0, 3, 6)] == ["background", "numerical", "foreground"])
        check("both exact tangencies fall back", all(selector.classify((x, 0)) == "numerical" for x in (1.5, 4.5)))
        check("one-ULP outward foreground live", selector.classify((math.nextafter(4.5, math.inf), 0)) == "foreground")
        check("one-ULP inward foreground fallback", selector.classify((math.nextafter(4.5, -math.inf), 0)) == "numerical")
        check("signed defocus support symmetry", [p.geometry.ExactSelector(scene, m.Frame(0, 1.5, 2)).classify((x, 0)) for x in range(7)] == [selector.classify((x, 0)) for x in range(7)])
        check("zero defocus retains cell support", p.geometry.ExactSelector(scene, m.Frame(0, 1, 2)).classify((3.25, 0)) == "numerical")
        for state, expected in (("full", "foreground"), ("absent", "background")):
            control = m.Scene(scene.foreground, scene.background, scene.depths, scene.mask_normal, scene.mask_offset, state)
            check("explicit " + state, p.geometry.ExactSelector(control, frame).classify((3, 0)) == expected)
        refuses("nonfinite coordinate refuses", lambda: selector.classify((math.nan, 0)), "finite coordinate")
        transform = m.Similarity(2, 0, (16, -8), (1, 2))
        transformed = p.geometry.ExactSelector(scene, m.Frame(0, .5, 2, transform))
        # q0.x = x/2 + 7.5 and h=q0.x-3 for this independently expanded map.
        check("nonidentity exact height", transformed.exact_height((3, 7)) == 6)
        limited = p.geometry.ExactSelector(scene, m.Frame(0, .5, 2, m.Similarity(1, 0, (2**30, 0))), bit_limit=8)
        check("bounded unsupported fallback", limited.unsupported_reason is not None and limited.classify((6, 0)) == "numerical")

        cancellation_scene = m.Scene(m.Field(20), m.Field(10), (1, 2), (1, 2), 0)
        cancellation_frame = m.Frame(0, .5, 2, m.Similarity(1, 0, (2**40, 0)))
        xy = np.array(((2**-15, 0), (-2**-15, 0)), dtype=float)
        cuts = p.point_cuts(bound, cancellation_scene, cancellation_frame, xy, p.Budget())
        exact = p.geometry.ExactSelector(cancellation_scene, cancellation_frame)
        changed = []
        for record, point in zip(cuts, xy):
            other = r.angular_cuts(float(exact.exact_height(point)), record["radius"], record["alpha"], "half-plane")
            changed.append(record["height"] == 0 and record["cuts"] != other)
        check("actual rounded-height path has signed power", all(changed), cuts)

        def trap(*_args, **_kwargs):
            raise AssertionError("radiance/integral reached by geometry-only counter")
        events = []
        with patch(m.Field, "evaluate", trap), patch(m, "evaluate_rays", trap), patch(r, "render_points", trap):
            counted = p.count_geometry(bound, scene, (frame,), 7, 3, ("primary",), p.Budget(), sink=events.append)
        cells = [e for e in events if e["kind"] == "cell"]
        points = [e for e in events if e["kind"] == "point"]
        row = counted["frames"][0]
        check("private non-square complete geometry", counted["status"] == "PASS_COST_ONLY" and len(cells) == 21 and row["branches"] == dict(foreground=6, background=6, numerical=9))
        check("both actual rule batches counted", row["low_points"] > 0 and row["high_points"] == 4 * row["low_points"] and len(points) == row["low_points"] + row["high_points"])
        check("actual stream node total", sum((len(e["cuts"])-1)*48 for e in points) == row["angular_nodes"])
        null = p.count_geometry(bound, scene, (frame,), 7, 3, ("primary",), p.Budget())
        check("sink observer byte-null", counted["ordered_stream_sha256"] == null["ordered_stream_sha256"])
        def omit(w, h):
            yield from list(p.enumerate_cells(w, h))[:-1]
        def duplicate(w, h):
            yield 0, 0
            yield from p.enumerate_cells(w, h)
        refuses("missing cell refuses", lambda: p.count_geometry(bound, scene, (frame,), 2, 1, ("primary",), p.Budget(), coordinates=omit), "incomplete coordinate")
        refuses("duplicate cell refuses", lambda: p.count_geometry(bound, scene, (frame,), 2, 1, ("primary",), p.Budget(), coordinates=duplicate), "duplicate")
        original_rule = r.triangle_rule
        def broken_rule(triangle, order, indices=()):
            values, weights = original_rule(triangle, order, indices)
            return values, weights * .5
        with patch(r, "triangle_rule", broken_rule):
            refuses("consumed mass corruption refuses", lambda: p.count_geometry(bound, scene, (frame,), 4, 1, ("primary",), p.Budget()), "mass")
        def missing_low(triangle, order, indices=()):
            values, weights = original_rule(triangle, order, indices)
            return (values[:-1], weights[:-1]) if order == 4 else (values, weights)
        with patch(r, "triangle_rule", missing_low):
            refuses("consumed missing low point refuses", lambda: p.count_geometry(bound, scene, (frame,), 4, 1, ("primary",), p.Budget()), "rule point count")

        for key, field in (("per_frame_points_strictly_below", "points"), ("per_frame_angular_nodes_strictly_below", "nodes")):
            limits = dict(p.DEFAULT_LIMITS, **{key: 10})
            budget = p.Budget(limits)
            budget.charge(**{field: 9})
            check(field + " below cap passes", True)
            refuses(field + " exact cap refuses", lambda: budget.charge(**{field: 1}), "strict per-frame")
        clock = [0.]
        budget = p.Budget(dict(p.DEFAULT_LIMITS, whole_run_cpu_seconds=2.), cpu_clock=lambda: clock[0], wall_clock=lambda: 0.)
        clock[0] = 1.5
        budget.begin_frame()
        clock[0] = 2.1
        refuses("clock persists across frame reset", budget.begin_frame, "whole-run time")
        clock[0] = 0.
        budget = p.Budget(dict(p.DEFAULT_LIMITS, whole_run_cpu_seconds=2.), cpu_clock=lambda: clock[0], wall_clock=lambda: 0.)
        full = m.Scene(scene.foreground, scene.background, scene.depths, scene.mask_normal, 0, "full")
        def advance(_record):
            clock[0] += .6
        refuses("analytic-only cells enforce time", lambda: p.count_geometry(bound, full, (frame,), 5, 1, ("primary",), budget, sink=advance), "whole-run time")
        storage = p.Budget(dict(p.DEFAULT_LIMITS, tracked_owned_ndarray_bytes=80))
        allocation = np.zeros(10)
        storage.watch(allocation, allocation[1:], allocation.reshape(2, 5))
        check("views share allocation accounting", storage.peak_bytes == 80 and storage.peak_arrays == 1)
        refuses("additional owned allocation refuses", lambda: storage.watch(np.zeros(1)), "owned-array ceiling")

        poison = types.SimpleNamespace(file_ref=trap, write_json=trap)
        previous = sys.modules.get("model")
        sys.modules["model"] = poison
        try:
            loaded = p.loader.load_frozen()
            check("foreign bare model not consumed", loaded.render.file_ref is loaded.model.file_ref and sys.modules["model"] is poison)
        finally:
            if previous is None:
                sys.modules.pop("model", None)
            else:
                sys.modules["model"] = previous
        copy_dir = output / "copied-frozen"
        copy_dir.mkdir()
        for filename, binding in bound.bindings.items():
            (copy_dir / filename).write_bytes(Path(binding["path"]).read_bytes())
        check("relocated identical frozen sources pass", p.loader.load_frozen(copy_dir).assert_unchanged())
        (copy_dir / "model.py").write_bytes((copy_dir / "model.py").read_bytes() + b"\nraise RuntimeError('must not execute')\n")
        refuses("changed frozen source refuses before execution", lambda: p.loader.load_frozen(copy_dir), "pinned source mismatch")
        refuses("private subset cannot authorize intended completion", lambda: p.validate_completion(counted, fixture, p.Budget()), "intended population")
        # Additive regression after independent run2: equality alone accepted
        # bool/float metadata. Small actual-count companion, no large stub run.
        private_fixture = dict(width=7, height=3, frame_indices=[0], arms=["primary"])
        private_budget = p.Budget()
        private_budget.frame_count = 1
        private_budget.total_points = counted["work"]["total_points"]
        private_budget.total_nodes = counted["work"]["total_angular_nodes"]
        p.validate_completion(counted, private_fixture, private_budget)
        check("typed completion companion passes", True)
        for name, mutation in (
                ("float width", lambda value: value.update(width=7.)),
                ("float complete count", lambda value: value.update(completed_cells=21.)),
                ("bool frame index", lambda value: value["frames"][0].update(frame_index=False)),
                ("float visited count", lambda value: value["frames"][0].update(visited_cells=21.))):
            changed = copy.deepcopy(counted)
            mutation(changed)
            refuses(name + " completion refuses", lambda: p.validate_completion(changed, private_fixture, private_budget), "types mismatch")

        bound.assert_unchanged()
        after = {path: p.loader.checked_bytes(path)[1] for path in sources}
        result["sources_after"] = after
        check("all owned and frozen source bytes unchanged", sources == after)
        result.update(status="PASS_AUTHOR_CONTROLS", passed=len(result["checks"]), private_count=counted)
    except Exception as exc:
        result.update(status="FAIL_AUTHOR_CONTROLS", error=repr(exc), traceback=traceback.format_exc())
    result["ended_utc"] = datetime.now(timezone.utc).isoformat()
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(dict(status=result["status"], checks=len(result["checks"]), output=str(output))), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.output)["status"] == "PASS_AUTHOR_CONTROLS" else 1)
