"""Independent small geometry-counter controls; never the intended preflight."""
from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
from types import ModuleType
from unittest.mock import patch
from fractions import Fraction

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
E_DIR = HERE.parent / "m194e-joint-pupil"
FIXTURE_SHA = "fc36b5f252c5efeda1cba753312dd061ebf5583856ec45466f61b0f66dc31ef2"
E_SOURCES = {
    "model.py": "a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8",
    "render.py": "487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


class Audit:
    def __init__(self, output):
        self.output = output
        self.rows = []

    def record(self, name, passed, **detail):
        row = dict(name=name, passed=bool(passed), detail=detail)
        self.rows.append(row)
        print(json.dumps(row, allow_nan=False), flush=True)
        write(self.output / "checks.json", self.rows)

    def refuses(self, name, call):
        try:
            result = call()
        except (ValueError, RuntimeError, OSError) as error:
            self.record(name, True, refusal=type(error).__name__ + ": " + str(error))
            return
        self.record(name, False, unexpected_acceptance=repr(result))


class Clock:
    """Explicit private clock; no sleeping or performance measurement."""
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


def private_scene(bound, *, mask_state="half-plane"):
    m = bound.model
    scene = m.Scene(m.Field(15000), m.Field(12000), (1, 2), (1, .25), 2,
                    mask_state=mask_state)
    similarity = m.Similarity(scale=2, rotation=0, centre=(.5, -.5),
                              translation=(1.25, -.75))
    frames = tuple(m.Frame(i, focus, 2, similarity)
                   for i, focus in enumerate((.5, .75, 1, 1.25, 1.5)))
    return scene, frames


def private_branch(x, y, frame):
    """Independent exact dyadic reduction for the declared9x6 private map."""
    # q=(x/2-3/8,y/2+1/8); normal=(1,1/4), offset2.
    h = Fraction(x, 2) + Fraction(y, 8) - Fraction(75, 32)
    half_cell = Fraction(5, 16)
    df = 2 * (Fraction.from_float(frame.inverse_focus) - 1)
    radius_squared = df * df * Fraction(17, 64)
    if h - half_cell > 0 and (h - half_cell) ** 2 > radius_squared:
        return "foreground"
    if -h - half_cell > 0 and (-h - half_cell) ** 2 > radius_squared:
        return "background"
    return "numerical"


def private_nominal_reference(bound, scene, frames, width=9, height=6):
    """Independent loop and classifier; frozen geometry supplies actual rules.

    Radiance is never evaluated. This is a small control reference, not the
    intended preflight and not Zeno's independent spatial integral.
    """
    r = bound.render
    rows = []
    for arm, low, high, angles in (("primary", 4, 8, 48),
                                   ("angle-refined", 4, 8, 96),
                                   ("cell-refined", 8, 16, 48)):
        for frame in frames:
            counts = dict(foreground=0, background=0, numerical=0)
            roots = low_points = high_points = nodes = max_intervals = 0
            n, _ = r.native_mask(scene, frame)
            df, _ = frame.defocus(scene)
            radius = abs(df) * math.hypot(n[0], n[1])
            alpha = math.atan2(n[1] * df, n[0] * df) if df else math.atan2(n[1], n[0])
            for y in range(height):
                for x in range(width):
                    branch = private_branch(x, y, frame)
                    counts[branch] += 1
                    if branch != "numerical":
                        continue
                    triangles = r.cell_triangles(scene, frame, (x, y))
                    roots += len(triangles)
                    for triangle in triangles:
                        indices = r.tangent_indices(triangle, scene, frame)
                        for order in (low, high):
                            xy, weights = r.triangle_rule(triangle, order, indices)
                            r.validate_cell_rule(triangle, weights)
                            if order == low:
                                low_points += len(xy)
                            else:
                                high_points += len(xy)
                            q = frame.forward_similarity.inverse(xy)
                            heights = q[:, 0] + .25 * q[:, 1] - 2
                            for point_height in heights:
                                cuts = r.angular_cuts(point_height, radius, alpha, scene.mask_state)
                                intervals = sum(b > a for a, b in zip(cuts, cuts[1:]))
                                nodes += angles * intervals
                                max_intervals = max(max_intervals, intervals)
            rows.append(dict(arm=arm, index=frame.index, visited=width * height,
                             branches=counts, roots=roots, low_points=low_points,
                             high_points=high_points, nodes=nodes, max_intervals=max_intervals))
    return rows


def fixture_literal_controls(audit):
    path = HERE / "fixture.json"
    value = json.loads(path.read_bytes())
    audit.record("intended-fixture-external-pin", sha(path) == FIXTURE_SHA, sha256=sha(path))
    audit.record("intended-shape-frame-arm-consumer", value["schema"] == "m194g-expected-fixture-v1"
                 and (value["width"], value["height"]) == (320, 240)
                 and value["dtype"] == "<f8" and value["cell"] == "integer-centre-unit-square"
                 and value["frame_indices"] == [0, 1, 2, 3, 4]
                 and value["inverse_foci"] == [.5, .625, .75, .875, 1]
                 and value["arms"] == ["primary", "angle-refined", "cell-refined"]
                 and value["reference_index"] == 2 and value["K"] == 12,
                 scope="literal preregistration consistency; not optical evidence")
    audit.record("intended-geometry-and-limits", value["scene"]["mask_normal"] == [1, -.15]
                 and value["scene"]["mask_offset"] == 142 and value["scene"]["depths"] == [1, 2]
                 and value["forward_similarity"] == dict(scale=1, rotation=0, centre=[0, 0], translation=[0, 0])
                 and value["selector_intermediate_bit_limit"] == 4096
                 and value["preflight_limits"] == dict(whole_run_cpu_seconds=60,
                     whole_run_wall_seconds=120, tracked_owned_ndarray_bytes=33554432,
                     per_frame_points_strictly_below=8000000,
                     per_frame_angular_nodes_strictly_below=1200000000),
                 scope="fixed input identity and resource contract")
    return value


def loader_controls(audit, loader):
    sentinel = ModuleType("model")
    sentinel.__file__ = str(audit.output / "foreign-model-not-imported.py")
    sentinel.file_ref = lambda *args: (_ for _ in ()).throw(AssertionError("foreign model used"))
    sentinel.write_json = sentinel.file_ref
    with patch.dict(sys.modules, {"model": sentinel}):
        bound = loader.load_frozen()
        audit.record("frozen-loader-restores-existing-bare-model", sys.modules["model"] is sentinel)
        audit.record("actual-render-imports-actual-pinned-model",
                     bound.render.file_ref is bound.model.file_ref
                     and bound.render.write_json is bound.model.write_json
                     and Path(bound.model.__file__).resolve() == (E_DIR / "model.py").resolve()
                     and Path(bound.render.__file__).resolve() == (E_DIR / "render.py").resolve(),
                     model_path=bound.model.__file__, render_path=bound.render.__file__)
        bound.assert_unchanged()
        audit.record("loaded-original-source-hashes-current",
                     all(sha(E_DIR / name) == pin for name, pin in E_SOURCES.items()))
        folder = audit.output / "private-frozen-copy"
        folder.mkdir()
        for name in E_SOURCES:
            (folder / name).write_bytes((E_DIR / name).read_bytes())
        companion = loader.load_frozen(directory=folder)
        companion.assert_unchanged()
        audit.record("unchanged-private-source-copy-companion",
                     companion.render.file_ref is companion.model.file_ref)
        for name in E_SOURCES:
            path = folder / name
            original = path.read_bytes()
            path.write_bytes(original + b"\n# private source-binding mutation\n")
            audit.refuses("changed-" + name + "-before-import", lambda: loader.load_frozen(directory=folder))
            audit.refuses("changed-" + name + "-after-import", companion.assert_unchanged)
            audit.record("failed-load-restores-bare-model-" + name, sys.modules["model"] is sentinel)
            path.write_bytes(original)
            companion.assert_unchanged()
        missing = folder / "model.py"
        held = folder / "model.py.private-held"
        missing.rename(held)
        try:
            audit.refuses("missing-model-before-import", lambda: loader.load_frozen(directory=folder))
            audit.record("missing-source-error-preserves-bare-model", sys.modules["model"] is sentinel)
        finally:
            held.rename(missing)
        companion.assert_unchanged()
        audit.record("restored-source-copy-final-companion", True)
    return bound


def budget_controls(audit, counter, fixture):
    # The actual Budget methods enforce resource predicates; these injected
    # clocks avoid sleeping and confer no runtime estimate.
    original = fixture["preflight_limits"]
    for field, charge in (("per_frame_points_strictly_below", "points"),
                          ("per_frame_angular_nodes_strictly_below", "nodes")):
        limits = copy.deepcopy(original)
        limits[field] = 17
        clock = Clock()
        budget = counter.Budget(limits, cpu_clock=clock, wall_clock=clock)
        budget.begin_frame()
        budget.charge(**{charge: 16})
        audit.record("actual-budget-" + charge + "-just-below", True, consumed=16, strict_limit=17)
        audit.refuses("actual-budget-" + charge + "-equality", lambda: budget.charge(**{charge: 1}))
    for field, clock_name in (("whole_run_cpu_seconds", "cpu"), ("whole_run_wall_seconds", "wall")):
        limits = copy.deepcopy(original)
        limits[field] = 1.0
        cpu, wall = Clock(), Clock()
        budget = counter.Budget(limits, cpu_clock=cpu, wall_clock=wall)
        budget.begin_frame()
        live = cpu if clock_name == "cpu" else wall
        live.value = .6
        budget.check()
        budget.begin_frame()
        live.value = 1.2
        audit.refuses("actual-budget-" + clock_name + "-does-not-reset-with-frame", budget.check)
    limits = copy.deepcopy(original)
    limits["tracked_owned_ndarray_bytes"] = 1024
    clock = Clock()
    budget = counter.Budget(limits, cpu_clock=clock, wall_clock=clock)
    backing = np.arange(128, dtype=np.float64)
    left, right = backing[:96], backing[32:]
    budget.watch(left, right)
    audit.record("actual-budget-two-views-one-1024-byte-owner", True, backing_bytes=backing.nbytes)
    duplicate = backing.copy()
    audit.refuses("actual-budget-second-owned-allocation-refuses", lambda: budget.watch(left, duplicate))
    del backing, left, right, duplicate
    gc.collect()
    budget.watch()
    replacement = np.zeros(128, dtype=np.float64)
    budget.watch(replacement)
    audit.record("actual-budget-released-owner-no-longer-live", True, live_bytes=replacement.nbytes)


def fixture_boundary_controls(audit, counter, fixture):
    loaded, binding = counter.load_fixture()
    audit.record("actual-intended-fixture-load-companion", loaded == fixture and binding["sha256"] == FIXTURE_SHA)
    changes = [("wrong-schema", lambda v: v.update(schema="m194e-float-bundle-v1")),
               ("unknown-field", lambda v: v.update(candidate=True)),
               ("missing-scene", lambda v: v.pop("scene")),
               ("bool-width", lambda v: v.update(width=True)),
               ("float-width", lambda v: v.update(width=320.0)),
               ("duplicate-frame", lambda v: v["frame_indices"].__setitem__(4, 3)),
               ("duplicate-arm", lambda v: v["arms"].__setitem__(2, "primary")),
               ("changed-scene-phase", lambda v: v["scene"]["foreground"]["waves"][0].update(phase=.71))]
    for name, edit in changes:
        mutant = copy.deepcopy(fixture)
        edit(mutant)
        path = audit.output / (name + ".json")
        write(path, mutant)
        audit.refuses(name + "-stale-fixture-pin", lambda: counter.load_fixture(path))
        audit.refuses(name + "-rehashed-unregistered-fixture", lambda: counter.load_fixture(path, sha(path)))
    audit.refuses("wrong-external-fixture-pin", lambda: counter.load_fixture(expected_hash="0" * 64))
    # The literal whole-file pin is the intended-schema authority. These are
    # not claims that arbitrary private dictionaries receive the same schema.


def count_controls(audit, counter, bound, fixture):
    scene, frames = private_scene(bound)
    limits = fixture["preflight_limits"]
    arms = ("primary", "angle-refined", "cell-refined")
    reference = private_nominal_reference(bound, scene, frames)
    write(audit.output / "private-reference.json", reference)
    observed = []
    calls = dict(rule_orders=[], cut_batches=0, cut_points=0, radiance=0)
    original_rule, original_cuts = bound.render.triangle_rule, counter.point_cuts
    def spy_rule(triangle, order, indices=()):
        calls["rule_orders"].append(order)
        return original_rule(triangle, order, indices)
    def spy_cuts(*args, **kwargs):
        result = original_cuts(*args, **kwargs)
        calls["cut_batches"] += 1
        calls["cut_points"] += len(result)
        return result
    def sink(event):
        if event["kind"] == "cell":
            observed.append((event["arm"], event["frame_index"], *event["xy"], event["branch"]))
    def forbidden(*args, **kwargs):
        calls["radiance"] += 1
        raise AssertionError("radiance was invoked by geometry-only preflight")
    clock = Clock()
    budget = counter.Budget(limits, cpu_clock=clock, wall_clock=clock)
    with patch.object(bound.render, "triangle_rule", side_effect=spy_rule), \
         patch.object(counter, "point_cuts", side_effect=spy_cuts), \
         patch.object(bound.model.Field, "evaluate", side_effect=forbidden), \
         patch.object(bound.model, "evaluate_rays", side_effect=forbidden), \
         patch.object(bound.render, "render_points", side_effect=forbidden), \
         patch.object(bound.render, "angular_integrand", side_effect=forbidden), \
         patch.object(bound.render, "render_cell", side_effect=forbidden):
        actual = counter.count_geometry(bound, scene, frames, 9, 6, arms, budget, sink=sink)
    write(audit.output / "private-actual.json", actual)
    expected_cells = {(arm, f.index, x, y, private_branch(x, y, f)) for arm in arms
                      for f in frames for y in range(6) for x in range(9)}
    audit.record("actual-private-exact-coverage-and-branch-oracle", actual["status"] == "PASS_COST_ONLY"
                 and len(observed) == len(set(observed)) == 810 and set(observed) == expected_cells,
                 cells=len(observed), distinct_cells=len(set(observed)))
    totals = {name: sum(row["branches"][name] for row in actual["frames"])
              for name in ("foreground", "background", "numerical")}
    audit.record("private-fixture-all-branches-and-defocus-signs-occur",
                 all(v > 0 for v in totals.values())
                 and {int(np.sign(f.defocus(scene)[0])) for f in frames} == {-1, 0, 1}, branches=totals)
    normalized = [dict(arm=row["arm"], index=row["frame_index"], visited=row["visited_cells"],
                       branches=row["branches"], roots=row["roots"], low_points=row["low_points"],
                       high_points=row["high_points"], nodes=row["angular_nodes"],
                       max_intervals=row["maximum_intervals"]) for row in actual["frames"]]
    audit.record("actual-low-high-root-cut-counts-match-independent-loop", normalized == reference,
                 frame_rows=len(normalized), reference="private-reference.json", actual="private-actual.json")
    point_total = sum(row["low_points"] + row["high_points"] for row in reference)
    audit.record("actual-counter-consumes-live-rules-and-point-helper", calls["cut_points"] == point_total
                 and calls["cut_batches"] == len(calls["rule_orders"]) > 0
                 and set(calls["rule_orders"]) == {4, 8, 16} and calls["radiance"] == 0,
                 cut_points=calls["cut_points"], cut_batches=calls["cut_batches"], radiance_calls=calls["radiance"])
    write(audit.output / "private-observed-cells.json", observed)

    full_scene, short_frames = private_scene(bound, mask_state="full")
    short_frames = short_frames[:2]
    def small(name, *, coordinates=None, sink=None, supplied_frames=short_frames,
              supplied_arms=("primary",), supplied_scene=full_scene, custom_limits=None,
              cpu=None, wall=None, width=2, height=1):
        cpu, wall = cpu or Clock(), wall or Clock()
        budget = counter.Budget(custom_limits or limits, cpu_clock=cpu, wall_clock=wall)
        result = {}
        try:
            counter.count_geometry(bound, supplied_scene, supplied_frames, width, height,
                                   supplied_arms, budget, coordinates=coordinates, sink=sink, result=result)
            return result
        finally:
            write(audit.output / (name + ".json"), result)
    normal = small("small-valid")
    reversed_result = small("small-reversed", coordinates=lambda w, h: reversed(list(counter.enumerate_cells(w, h))))
    semantic_rows = lambda rows: [{key: value for key, value in row.items() if key != "last_coordinate"}
                                  for row in rows]
    audit.record("reordered-valid-coverage-counts-not-order-digest", normal["status"] == reversed_result["status"] == "PASS_COST_ONLY"
                 and semantic_rows(normal["frames"]) == semantic_rows(reversed_result["frames"])
                 and normal["ordered_stream_sha256"] != reversed_result["ordered_stream_sha256"],
                 normal_last=[row["last_coordinate"] for row in normal["frames"]],
                 reversed_last=[row["last_coordinate"] for row in reversed_result["frames"]],
                 scope="counts/geometry equal; actual final coordinate and ordered digest legitimately differ")
    for name, coords in [("missing-last-cell", lambda w, h: [(0, 0)]),
                         ("duplicate-replaces-missing-cell", lambda w, h: [(0, 0), (0, 0)]),
                         ("outside-grid", lambda w, h: [(0, 0), (2, 0)]),
                         ("bool-coordinate", lambda w, h: [(False, 0), (1, 0)]),
                         ("float-coordinate", lambda w, h: [(0.0, 0), (1, 0)])]:
        audit.refuses(name, lambda n=name, c=coords: small(n, coordinates=c))
    audit.refuses("duplicate-original-frame-index", lambda: small("duplicate-frame", supplied_frames=(short_frames[0],) * 2))
    audit.refuses("duplicate-arm", lambda: small("duplicate-arm", supplied_arms=("primary", "primary")))

    for which in ("cpu", "wall"):
        for transition in ("cells", "frames", "arms"):
            cpu, wall = Clock(), Clock()
            live = cpu if which == "cpu" else wall
            ls = copy.deepcopy(limits)
            ls["whole_run_" + which + "_seconds"] = 1.0
            def advance(event, transition=transition, live=live):
                if event["kind"] == "cell" and (transition == "cells" or event["xy"] == [1, 0]):
                    live.value += .6
            fs = short_frames if transition == "frames" else short_frames[:1]
            ars = arms if transition == "arms" else ("primary",)
            name = "actual-analytic-" + which + "-limit-across-" + transition
            audit.refuses(name, lambda n=name, fs=fs, ars=ars, ls=ls, cpu=cpu, wall=wall, adv=advance:
                          small(n, supplied_frames=fs, supplied_arms=ars, custom_limits=ls,
                                cpu=cpu, wall=wall, sink=adv))

    numerical_xy = next((x, y) for y in range(6) for x in range(9)
                        if private_branch(x, y, frames[0]) == "numerical")
    # Offset one legal cell onto the selected private numerical coordinate while
    # preserving the source-defined model by translating its similarity.
    t = frames[0].forward_similarity
    moved = bound.model.Similarity(t.scale, t.rotation, t.centre,
                                  (t.translation[0] - numerical_xy[0], t.translation[1] - numerical_xy[1]))
    numerical_frame = bound.model.Frame(0, frames[0].inverse_focus, frames[0].K, moved)
    original_triangles = bound.render.cell_triangles
    for name, replacement in [
        ("actual-missing-root-refuses", lambda *a: original_triangles(*a)[1:]),
    ]:
        with patch.object(bound.render, "cell_triangles", side_effect=replacement):
            audit.refuses(name, lambda n=name: small(n, supplied_frames=(numerical_frame,), supplied_scene=scene, width=1))
    def wrong_mass(triangle, order, indices=()):
        xy, weights = original_rule(triangle, order, indices)
        return xy, weights * (1 + 1e-6)
    def missing_low(triangle, order, indices=()):
        xy, weights = original_rule(triangle, order, indices)
        return (xy[:-1], weights[:-1]) if order == 4 else (xy, weights)
    for name, replacement in (("actual-rule-mass-refuses", wrong_mass), ("actual-low-point-omission-refuses", missing_low)):
        with patch.object(bound.render, "triangle_rule", side_effect=replacement):
            audit.refuses(name, lambda n=name: small(n, supplied_frames=(numerical_frame,), supplied_scene=scene, width=1))
    with patch.object(counter, "point_cuts", side_effect=lambda *a, **kw: original_cuts(*a, **kw)[:-1]):
        audit.refuses("actual-point-cut-omission-refuses", lambda: small("missing-point-cut", supplied_frames=(numerical_frame,), supplied_scene=scene, width=1))
    for field, threshold in (("per_frame_points_strictly_below", 1),
                             ("per_frame_angular_nodes_strictly_below", 1),
                             ("tracked_owned_ndarray_bytes", 1)):
        ls = copy.deepcopy(limits)
        ls[field] = threshold
        audit.refuses("actual-count-" + field + "-crossing", lambda ls=ls, field=field:
                      small("actual-limit-" + field, supplied_frames=(numerical_frame,), supplied_scene=scene,
                            custom_limits=ls, width=1))


def guard_controls(audit, counter, bound):
    scene, frames = private_scene(bound)
    records = bound.model.scene_record(scene)
    unsupported = counter.geometry.ExactSelector(scene, frames[0], bit_limit=1)
    dispositions = [unsupported.classify((x, y)) for x, y in ((0, 0), (8, 5), (4, 2))]
    audit.record("actual-insufficient-rational-budget-falls-back-unchanged",
                 dispositions == ["numerical"] * 3 and bool(unsupported.unsupported_reason)
                 and records == bound.model.scene_record(scene), dispositions=dispositions,
                 reason=unsupported.unsupported_reason)
    for invalid in (0, -1, True, 4097, 8.0):
        audit.refuses("invalid-rational-budget-" + repr(invalid),
                      lambda invalid=invalid: counter.geometry.ExactSelector(scene, frames[0], bit_limit=invalid))


def controller_controls(audit, counter, fixture):
    """Explicit synthetic completion records; no intended geometry traversed."""
    original_bindings = counter.source_bindings
    original_budget = counter.Budget
    def case(name, *, mutate=None, original_failure=False, final_capture_failure=False,
             changed_source=False):
        directory = audit.output / ("private-controller-" + name)
        state = dict(count_called=False)
        cpu, wall = Clock(), Clock()
        def budget_factory(*args, **kwargs):
            return original_budget(fixture["preflight_limits"], cpu_clock=cpu, wall_clock=wall)
        def completion(bound, scene, frames, width, height, arms, budget, *, result=None, **kwargs):
            state["count_called"] = True
            if original_failure:
                raise counter.CostFailure("PRIVATE_ORIGINAL_COUNTER_FAILURE")
            n = width * height
            rows = [dict(arm=arm, frame_index=frame.index, status="complete", visited_cells=n,
                         branches=dict(foreground=n, background=0, numerical=0), roots=0,
                         low_points=0, high_points=0, angular_nodes=0)
                    for arm in arms for frame in frames]
            budget.frame_count = len(rows)
            result.update(status="PASS_COST_ONLY", fixture_only=True,
                          scope="private synthetic completion stub; no intended geometry counted",
                          width=width, height=height, frame_indices=[f.index for f in frames],
                          arms=list(arms), frames=rows, completed_frames=len(rows),
                          completed_cells=n * len(rows), ordered_stream_sha256="0" * 64,
                          work=budget.receipt())
            if mutate:
                mutate(result, budget)
            return result
        def sources():
            if state["count_called"] and final_capture_failure:
                raise OSError("PRIVATE_FINAL_SOURCE_CAPTURE_FAILURE")
            value = original_bindings()
            if state["count_called"] and changed_source:
                key = str((HERE / "geometry.py").resolve())
                value[key]["sha256"] = "0" * 64
            return value
        with patch.object(counter, "count_geometry", side_effect=completion), \
             patch.object(counter, "Budget", side_effect=budget_factory), \
             patch.object(counter, "source_bindings", side_effect=sources):
            result = counter.run(directory)
        retained = json.loads((directory / "result.json").read_bytes())
        return result, retained, state
    result, retained, state = case("valid-companion")
    audit.record("private-controller-valid-completion-companion",
                 result["status"] == "PASS_COST_ONLY" and result == retained and state["count_called"],
                 fixture_only=True)
    for name, mutate in [
        ("omitted-frame", lambda r, b: r["frames"].pop()),
        ("omitted-arm", lambda r, b: (r["frames"].__delitem__(slice(10, 15)), r["arms"].pop())),
        ("duplicate-frame-replaces-missing", lambda r, b: r["frames"].__setitem__(14, copy.deepcopy(r["frames"][13]))),
        ("wrong-shape", lambda r, b: r.update(width=319)),
        ("wrong-completed-cell-count", lambda r, b: r.update(completed_cells=r["completed_cells"] - 1)),
        ("missing-visited-cell", lambda r, b: r["frames"][7].update(visited_cells=76799)),
        ("wrong-live-budget-frame-count", lambda r, b: setattr(b, "frame_count", 14)),
        ("omitted-low-work-from-total", lambda r, b: r["frames"][7].update(low_points=16)),
        ("float-width", lambda r, b: r.update(width=320.0)),
        ("float-completed-cell-count", lambda r, b: r.update(completed_cells=float(r["completed_cells"]))),
        ("bool-frame-index", lambda r, b: r["frames"][1].update(frame_index=True)),
        ("float-row-visited", lambda r, b: r["frames"][7].update(visited_cells=76800.0)),
        ("bool-top-frame-index", lambda r, b: r["frame_indices"].__setitem__(0, False)),
        ("float-row-low-count", lambda r, b: r["frames"][7].update(low_points=0.0)),
        ("cancelling-negative-work", lambda r, b: r["frames"][7].update(low_points=-16, high_points=16)),
    ]:
        result, retained, state = case(name, mutate=mutate)
        audit.record("private-controller-" + name + "-refuses", result["status"] == "UNCOMMISSIONED_COST"
                     and result == retained, fixture_only=True, error=result.get("error"))
    result, retained, state = case("source-changed-after", changed_source=True)
    audit.record("private-controller-current-source-change-refuses", result["status"] == "UNCOMMISSIONED_COST"
                 and result == retained, error=result.get("error"))
    result, retained, state = case("final-source-capture-failure", final_capture_failure=True)
    audit.record("private-controller-final-source-capture-failure-retained",
                 result["status"] == "UNCOMMISSIONED_COST" and result == retained
                 and "PRIVATE_FINAL_SOURCE_CAPTURE_FAILURE" in result.get("error", "")
                 and "PRIVATE_FINAL_SOURCE_CAPTURE_FAILURE" in result.get("sources_after_error", ""))
    result, retained, state = case("original-and-source-capture-failures", original_failure=True, final_capture_failure=True)
    audit.record("private-controller-original-error-not-overwritten-by-capture-failure",
                 result["status"] == "UNCOMMISSIONED_COST" and result == retained
                 and "PRIVATE_ORIGINAL_COUNTER_FAILURE" in result.get("error", "")
                 and "PRIVATE_FINAL_SOURCE_CAPTURE_FAILURE" in result.get("sources_after_error", ""))
    result, retained, state = case("valid-final-companion")
    audit.record("private-controller-valid-final-companion", result["status"] == "PASS_COST_ONLY"
                 and result == retained, fixture_only=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    audit = Audit(output)
    names = [Path(__file__), HERE / "independent-preflight-controls-design.md", HERE / "preregister.md",
             HERE / "fixture.json", HERE / "pinned-loader.py", HERE / "geometry.py", HERE / "preflight.py",
             E_DIR / "model.py", E_DIR / "render.py"]
    before = {str(path.relative_to(ROOT)): sha(path) for path in names}
    snapshots = output / "sources"
    for path in names:
        target = snapshots / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    started_wall, started_cpu = time.monotonic(), time.process_time()
    failure = None
    try:
        fixture = fixture_literal_controls(audit)
        counter = module(HERE / "preflight.py", "m194g_independent_actual_counter")
        bound = loader_controls(audit, counter.loader)
        fixture_boundary_controls(audit, counter, fixture)
        budget_controls(audit, counter, fixture)
        guard_controls(audit, counter, bound)
        count_controls(audit, counter, bound, fixture)
        controller_controls(audit, counter, fixture)
    except Exception as error:
        import traceback
        failure = dict(error=repr(error), traceback=traceback.format_exc())
        print(failure["traceback"], flush=True)
    after = {str(path.relative_to(ROOT)): sha(path) for path in names}
    passed = failure is None and all(row["passed"] for row in audit.rows) and before == after
    result = dict(schema="m194g-independent-preflight-controls-v1", passed=passed,
                  scope="private small geometry/source/resource controls; no intended preflight or radiance authority",
                  check_count=len(audit.rows), checks=audit.rows, failure=failure,
                  source_before=before, source_after=after, source_unchanged=before == after,
                  orig_argv=sys.orig_argv, argv=sys.argv, xoptions=sys._xoptions,
                  executable=sys.executable, python=sys.version, numpy=np.__version__,
                  thread_environment={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
                  wall_seconds=time.monotonic() - started_wall, cpu_seconds=time.process_time() - started_cpu)
    write(output / "result.json", result)
    print(json.dumps(dict(passed=passed, checks=len(audit.rows), result_sha256=sha(output / "result.json"))), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
