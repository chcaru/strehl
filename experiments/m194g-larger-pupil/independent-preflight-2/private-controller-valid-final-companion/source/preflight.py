"""Geometry-only nominal cost counter. No radiance, Bessel, noise or pixels."""
from __future__ import annotations
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "2"
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import traceback
import weakref

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m194g_pinned_loader", HERE / "pinned-loader.py")
loader = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = loader
# Execute this local dependency from the same bytes recorded below, not pycache.
raw = (HERE / "pinned-loader.py").read_bytes()
exec(compile(raw, str(HERE / "pinned-loader.py"), "exec"), loader.__dict__)
LOADER_IMPORT_SHA = hashlib.sha256(raw).hexdigest()
geometry = loader.execute_bytes(HERE / "geometry.py", "m194g_geometry")
FIXTURE_HASH = "fc36b5f252c5efeda1cba753312dd061ebf5583856ec45466f61b0f66dc31ef2"
PREREG_HASH = "d0c570ec892a2c3e40b90c0f7eef2a9ff0649dd53bc34adee6b6bc65280f14c8"
DEFAULT_LIMITS = dict(whole_run_cpu_seconds=60., whole_run_wall_seconds=120.,
                      tracked_owned_ndarray_bytes=32 * 1024 * 1024,
                      per_frame_points_strictly_below=8_000_000,
                      per_frame_angular_nodes_strictly_below=1_200_000_000)


class CostFailure(RuntimeError):
    pass


def fail(message):
    raise CostFailure("UNCOMMISSIONED_COST: " + message)


class Budget:
    """One clock; per-frame work only resets. Reachable-owned-array scope, not RSS.

    Tracks root/returned rule arrays, Gauss caches, coordinate transforms and
    coverage by unique ndarray backing allocation at wrapper checkpoints.
    Python objects, allocator overhead and transient expressions internal to
    the frozen helpers/library are excluded and must not be called measured.
    """
    def __init__(self, limits=None, *, cpu_clock=time.process_time, wall_clock=time.monotonic,
                 started_cpu=None, started_wall=None):
        self.limits = dict(DEFAULT_LIMITS if limits is None else limits)
        if set(self.limits) != set(DEFAULT_LIMITS):
            raise ValueError("exact budget keys required")
        for key, value in self.limits.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError("positive finite budget required")
            if "seconds" not in key and type(value) is not int:
                raise ValueError("integer work/storage budget required")
        self.cpu_clock, self.wall_clock = cpu_clock, wall_clock
        self.started_cpu = cpu_clock() if started_cpu is None else started_cpu
        self.started_wall = wall_clock() if started_wall is None else started_wall
        self.points = self.nodes = self.total_points = self.total_nodes = 0
        self.frame_count = self.check_calls = self.peak_bytes = self.peak_arrays = 0
        self.arrays = {}
        self.check()

    def check(self):
        self.check_calls += 1
        cpu, wall = self.cpu_clock() - self.started_cpu, self.wall_clock() - self.started_wall
        if not math.isfinite(cpu) or not math.isfinite(wall) or cpu < 0 or wall < 0:
            fail("invalid elapsed clock")
        if cpu > self.limits["whole_run_cpu_seconds"] or wall > self.limits["whole_run_wall_seconds"]:
            fail("whole-run time ceiling")
        if self.points >= self.limits["per_frame_points_strictly_below"] or self.nodes >= self.limits["per_frame_angular_nodes_strictly_below"]:
            fail("strict per-frame work ceiling")

    def watch(self, *values):
        self.check()
        for value in values:
            if isinstance(value, np.ndarray):
                base = value
                while isinstance(base.base, np.ndarray):
                    base = base.base
                self.arrays[id(base)] = (weakref.ref(base), base.nbytes)
        self.arrays = {key: item for key, item in self.arrays.items() if item[0]() is not None}
        size = sum(item[1] for item in self.arrays.values())
        self.peak_bytes = max(self.peak_bytes, size)
        self.peak_arrays = max(self.peak_arrays, len(self.arrays))
        if size > self.limits["tracked_owned_ndarray_bytes"]:
            fail("tracked owned-array ceiling")

    def begin_frame(self):
        self.check()
        self.points = self.nodes = 0
        self.frame_count += 1

    def charge(self, *, points=0, nodes=0):
        if type(points) is not int or type(nodes) is not int or points < 0 or nodes < 0:
            raise ValueError("nonnegative integer work charges required")
        self.points += points
        self.nodes += nodes
        self.total_points += points
        self.total_nodes += nodes
        self.check()

    def receipt(self):
        return dict(limits=self.limits, cpu_seconds=self.cpu_clock() - self.started_cpu,
                    wall_seconds=self.wall_clock() - self.started_wall,
                    frame_points=self.points, frame_angular_nodes=self.nodes,
                    total_points=self.total_points, total_angular_nodes=self.total_nodes,
                    frame_count=self.frame_count, check_calls=self.check_calls,
                    tracked_peak_ndarray_bytes=self.peak_bytes, tracked_peak_ndarrays=self.peak_arrays,
                    array_scope="unique reachable wrapper-owned ndarray backing allocations; excludes Python objects/RSS/frozen-helper transient temporaries")


def enumerate_cells(width, height):
    for y in range(height):
        for x in range(width):
            yield x, y


def point_cuts(bound, scene, frame, xy, budget):
    """Actual consumer cut geometry; returns one record per point, in order."""
    budget.check()
    xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
    if not np.isfinite(xy).all():
        raise ValueError("finite point coordinates required")
    n, _offset = bound.render.native_mask(scene, frame)
    df, _db = frame.defocus(scene)
    radius = abs(df) * math.hypot(*n)
    q0 = frame.forward_similarity.inverse(xy)
    heights = q0[:, 0] * scene.mask_normal[0] + q0[:, 1] * scene.mask_normal[1] - scene.mask_offset
    alpha = math.atan2(n[1] * df, n[0] * df) if df else math.atan2(n[1], n[0])
    budget.watch(xy, n, q0, heights)
    if not np.isfinite(heights).all() or not math.isfinite(radius) or not math.isfinite(alpha):
        fail("nonfinite cut geometry")
    records = []
    for point, height in zip(xy, heights):
        cuts = bound.render.angular_cuts(float(height), radius, alpha, scene.mask_state)
        if len(cuts) < 2 or any(not math.isfinite(value) for value in cuts) or any(b <= a for a, b in zip(cuts, cuts[1:])):
            fail("invalid nonempty angular partition")
        records.append(dict(xy=[float(point[0]), float(point[1])], height=float(height),
                            radius=float(radius), alpha=float(alpha), cuts=cuts))
    budget.check()
    return records


def _stream(digest, sink, record):
    kind = record["kind"]
    if kind == "cell":
        payload = struct.pack("<BIIIB", 0, record["frame_index"], *record["xy"],
                              {"foreground": 0, "background": 1, "numerical": 2}[record["branch"]])
    else:
        cuts = record["cuts"]
        payload = struct.pack("<BIIIBI5dI", 1, record["frame_index"], *record["cell_xy"],
                              0 if record["rule"] == "low" else 1, record["root_index"],
                              *record["xy"], record["height"], record["radius"], record["alpha"], len(cuts))
        payload += struct.pack("<" + "d" * len(cuts), *cuts)
    digest.update(record["arm"].encode("ascii") + b"\0" + payload)
    if sink is not None:
        sink(record)


def count_geometry(bound, scene, frames, width, height, arms, budget, *, coordinates=None, sink=None,
                   progress=None, result=None):
    if type(width) is not int or type(height) is not int or not 0 < width <= 320 or not 0 < height <= 240:
        raise ValueError("bounded positive native extent required")
    frames, arms = tuple(frames), tuple(arms)
    if not frames or not arms or len(frames) > 5 or len(set(arms)) != len(arms):
        raise ValueError("nonempty unique bounded frame/arm population required")
    indices = [frame.index for frame in frames]
    if len(set(indices)) != len(indices) or any(type(i) is not int or not 0 <= i < 5 for i in indices):
        raise ValueError("unique original indices0..4 required")
    enumerator = enumerate_cells if coordinates is None else coordinates
    result = {} if result is None else result
    result.update(status="running", width=width, height=height, frame_indices=indices,
                  arms=list(arms), frames=[], completed_frames=0, completed_cells=0)
    digest = hashlib.sha256()
    try:
        for arm in arms:
            config = bound.render.integrator_for(arm)
            for frame in frames:
                budget.begin_frame()
                selector = geometry.ExactSelector(scene, frame, budget=budget)
                visited = np.zeros(width * height, dtype=np.uint8)
                budget.watch(visited)
                row = dict(arm=arm, frame_index=frame.index, visited_cells=0,
                           branches=dict(foreground=0, background=0, numerical=0), roots=0,
                           low_points=0, high_points=0, angular_nodes=0, maximum_intervals=0,
                           unsupported_selector_reason=selector.unsupported_reason,
                           integrator=asdict(config), status="running")
                result["frames"].append(row)
                for coordinate in enumerator(width, height):
                    budget.check()
                    if len(coordinate) != 2 or any(type(v) is not int for v in coordinate):
                        fail("integer coordinate enumeration required")
                    x, y = coordinate
                    row["last_coordinate"] = [x, y]
                    if not 0 <= x < width or not 0 <= y < height or visited[y * width + x]:
                        fail("duplicate or out-of-range coordinate coverage")
                    visited[y * width + x] = 1
                    branch = selector.classify(coordinate)
                    if branch not in row["branches"]:
                        fail("unknown selector branch")
                    row["branches"][branch] += 1
                    _stream(digest, sink, dict(kind="cell", arm=arm, frame_index=frame.index, xy=[x, y], branch=branch))
                    if branch == "numerical":
                        triangles = bound.render.cell_triangles(scene, frame, coordinate)
                        budget.watch(*triangles)
                        area = sum(bound.render.triangle_area(t) for t in triangles)
                        if not math.isfinite(area) or abs(area - 1) > 1e-11 or not triangles:
                            fail("cell root area coverage")
                        row["roots"] += len(triangles)
                        for root_index, triangle in enumerate(triangles):
                            budget.check()
                            selected = bound.render.tangent_indices(triangle, scene, frame)
                            low_xy, low_weights = bound.render.triangle_rule(triangle, config.cell_low, selected)
                            budget.watch(low_xy, low_weights)
                            high_xy, high_weights = bound.render.triangle_rule(triangle, config.cell_high, selected)
                            budget.watch(low_xy, low_weights, high_xy, high_weights,
                                         *bound.render.gauss(config.cell_low), *bound.render.gauss(config.cell_high))
                            for label, order, xy, weights in (("low", config.cell_low, low_xy, low_weights),
                                                            ("high", config.cell_high, high_xy, high_weights)):
                                budget.check()
                                if xy.shape != (order * order, 2) or weights.shape != (order * order,):
                                    fail("consumed cell rule point count")
                                bound.render.validate_cell_rule(triangle, weights)
                                budget.charge(points=len(xy))
                                row[label + "_points"] += len(xy)
                                records = point_cuts(bound, scene, frame, xy, budget)
                                if len(records) != len(xy):
                                    fail("missing consumed point cut")
                                for record in records:
                                    intervals = len(record["cuts"]) - 1
                                    nodes = intervals * (config.angle_low + config.angle_high)
                                    budget.charge(nodes=nodes)
                                    row["angular_nodes"] += nodes
                                    row["maximum_intervals"] = max(row["maximum_intervals"], intervals)
                                    _stream(digest, sink, dict(kind="point", arm=arm, frame_index=frame.index,
                                                              cell_xy=[x, y], root_index=root_index, rule=label, **record))
                            del low_xy, low_weights, high_xy, high_weights, xy, weights, records
                        del triangles
                    row["visited_cells"] += 1
                    result["completed_cells"] += 1
                    budget.check()
                    if progress is not None and (x == width - 1):
                        progress(result, budget)
                if row["visited_cells"] != width * height or not np.all(visited == 1):
                    fail("incomplete coordinate coverage")
                row["status"] = "complete"
                result["completed_frames"] += 1
                del visited
                budget.check()
        bound.assert_unchanged()
        result.update(status="PASS_COST_ONLY", ordered_stream_sha256=digest.hexdigest(), work=budget.receipt())
    except Exception as exc:
        result.update(status="UNCOMMISSIONED_COST", error=repr(exc), traceback=traceback.format_exc(),
                      ordered_partial_stream_sha256=digest.hexdigest(), work=budget.receipt())
        if isinstance(exc, CostFailure):
            raise
        raise CostFailure("UNCOMMISSIONED_COST: " + str(exc)) from exc
    return result


def load_fixture(path=HERE / "fixture.json", expected_hash=FIXTURE_HASH):
    if expected_hash != FIXTURE_HASH:
        raise ValueError("external fixture binding differs from registered fixture")
    raw, binding = loader.checked_bytes(path, FIXTURE_HASH)
    value = json.loads(raw)
    if value["schema"] != "m194g-expected-fixture-v1":
        raise ValueError("fixture schema mismatch")
    return value, binding


def fixture_models(bound, fixture):
    m = bound.model
    def field(value):
        return m.Field(value["constant"], tuple(value["affine"]),
                       tuple(m.Wave(w["amplitude"], tuple(w["frequency"]), w["phase"]) for w in value["waves"]))
    s = fixture["scene"]
    scene = m.Scene(field(s["foreground"]), field(s["background"]), tuple(s["depths"]),
                    tuple(s["mask_normal"]), s["mask_offset"], s["mask_state"])
    t = fixture["forward_similarity"]
    transform = m.Similarity(t["scale"], t["rotation"], tuple(t["centre"]), tuple(t["translation"]))
    frames = tuple(m.Frame(i, focus, fixture["K"], transform)
                   for i, focus in zip(fixture["frame_indices"], fixture["inverse_foci"], strict=True))
    return scene, frames


def source_bindings():
    paths = [*HERE.glob("*.py"), HERE / "fixture.json", HERE / "preregister.md",
             HERE / "design-sources.json", HERE / "independent-preflight-design-review.md"]
    paths += list(HERE.glob("independent*preregister*.md"))
    paths += list(HERE.glob("independent*design*.md"))
    return {str(path.resolve()): loader.checked_bytes(path)[1] for path in sorted(set(paths))}


def write_json(path, value):
    with Path(path).open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_completion(result, fixture, budget):
    """Intended-population boundary; private count_geometry may use subsets."""
    pairs = [(arm, i) for arm in fixture["arms"] for i in fixture["frame_indices"]]
    cells = fixture["width"] * fixture["height"]
    if (result.get("status") != "PASS_COST_ONLY"
            or result.get("width") != fixture["width"] or result.get("height") != fixture["height"]
            or result.get("frame_indices") != fixture["frame_indices"] or result.get("arms") != fixture["arms"]
            or result.get("completed_frames") != len(pairs) or result.get("completed_cells") != cells * len(pairs)
            or budget.frame_count != len(pairs)):
        fail("intended population completion mismatch")
    rows = result.get("frames", [])
    if [(row.get("arm"), row.get("frame_index")) for row in rows] != pairs:
        fail("intended frame/arm order mismatch")
    for row in rows:
        if (row.get("status") != "complete" or row.get("visited_cells") != cells
                or set(row.get("branches", {})) != {"foreground", "background", "numerical"}
                or any(type(v) is not int or v < 0 for v in row["branches"].values())
                or sum(row["branches"].values()) != cells):
            fail("intended frame coverage mismatch")
    if (sum(row["low_points"] + row["high_points"] for row in rows) != budget.total_points
            or sum(row["angular_nodes"] for row in rows) != budget.total_nodes):
        fail("intended total work mismatch")


def run(output, fixture_path=HERE / "fixture.json"):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194g-geometry-preflight-v1", status="running", scope="cost only; no numerical/radiance authority",
                  invocation=dict(orig_argv=sys.orig_argv, argv=sys.argv, xoptions=sys._xoptions,
                                  executable=sys.executable, cwd=str(Path.cwd())),
                  started_utc=datetime.now(timezone.utc).isoformat())
    budget = None
    try:
        budget = Budget(started_cpu=ENTRY_CPU, started_wall=ENTRY_WALL)
        fixture, fixture_ref = load_fixture(fixture_path)
        loader.checked_bytes(HERE / "preregister.md", PREREG_HASH)
        if fixture["preflight_limits"] != budget.limits:
            fail("registered limits mismatch")
        before = source_bindings()
        if before[str((HERE / "pinned-loader.py").resolve())]["sha256"] != LOADER_IMPORT_SHA:
            fail("actual loader import changed")
        if before[str((HERE / "geometry.py").resolve())] != geometry.__checked_source__:
            fail("actual selector import changed")
        bound = loader.load_frozen()
        budget.check()
        result.update(fixture=fixture_ref, fixture_record=fixture, sources_before=before,
                      frozen_imports=bound.bindings, local_imports=dict(loader_sha256=LOADER_IMPORT_SHA,
                      geometry=geometry.__checked_source__), versions=dict(python=sys.version, numpy=np.__version__),
                      thread_environment={key: os.environ.get(key) for key in
                      ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
        snapshots = output / "source"
        snapshots.mkdir()
        for binding in [*before.values(), *bound.bindings.values()]:
            raw, checked = loader.checked_bytes(binding["path"], binding["sha256"])
            if checked != binding:
                fail("snapshot binding changed")
            (snapshots / Path(binding["path"]).name).write_bytes(raw)
        scene, frames = fixture_models(bound, fixture)
        budget.check()
        def progress(current, current_budget):
            current["work"] = current_budget.receipt()
            write_json(output / "progress.json", current)
        count_geometry(bound, scene, frames, fixture["width"], fixture["height"], fixture["arms"], budget,
                       progress=progress, result=result)
        validate_completion(result, fixture, budget)
        after = source_bindings()
        result["sources_after"] = after
        if before != after or fixture_ref != load_fixture(fixture_path)[1]:
            fail("source/config changed during preflight")
        budget.check()
        result["work"] = budget.receipt()
    except Exception as exc:
        result.update(status="UNCOMMISSIONED_COST", error=repr(exc), traceback=traceback.format_exc())
        if budget is not None:
            result["work"] = budget.receipt()
        try:
            result["sources_after"] = source_bindings()
        except Exception as snapshot_exc:
            result["sources_after_error"] = repr(snapshot_exc)
            result["sources_after_traceback"] = traceback.format_exc()
    result["ended_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(output / "result.json", result)
    print(json.dumps(dict(status=result["status"], output=str(output)), allow_nan=False), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, default=HERE / "fixture.json")
    args = parser.parse_args()
    raise SystemExit(0 if run(args.output, args.fixture)["status"] == "PASS_COST_ONLY" else 1)
