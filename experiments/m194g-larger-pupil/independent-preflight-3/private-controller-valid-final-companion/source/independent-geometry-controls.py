"""Independent M194g selector and consumed point-cut controls; no radiance."""
from __future__ import annotations

import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "2"

import argparse
from contextlib import contextmanager, ExitStack
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import time
import traceback

import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STEPS = (-4, -2, -1, 0, 1, 2, 4)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_checked(path, name, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("externally pinned source mismatch: " + str(path))
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def ratio(x):
    return x if isinstance(x, F) else F(x if isinstance(x, int) else float(x))


def dec(x):
    x = ratio(x)
    return Decimal(x.numerator) / Decimal(x.denominator)


def frac_record(x):
    x = ratio(x)
    return dict(numerator=str(x.numerator), denominator=str(x.denominator))


def inverse_coefficients(sim):
    """Reconstruct finite coefficients, without invoking the author's helper."""
    cosine, sine = math.cos(sim.rotation), math.sin(sim.rotation)
    return ((ratio(cosine / sim.scale), ratio(sine / sim.scale)),
            (ratio(-sine / sim.scale), ratio(cosine / sim.scale)))


def support(scene, frame, xy):
    matrix = inverse_coefficients(frame.forward_similarity)
    c = tuple(map(ratio, frame.forward_similarity.centre))
    t = tuple(map(ratio, frame.forward_similarity.translation))
    xy = tuple(map(ratio, xy))
    normal = tuple(map(ratio, scene.mask_normal))
    q = tuple(c[i] + sum(matrix[i][j] * (xy[j] - c[j] - t[j]) for j in range(2))
              for i in range(2))
    pulled = tuple(sum(normal[i] * matrix[i][j] for i in range(2)) for j in range(2))
    # These are the declared finite defocus coefficients, recomputed from input.
    df = ratio(frame.K * (frame.inverse_focus - 1 / scene.depths[0]))
    h = sum(normal[i] * q[i] for i in range(2)) - ratio(scene.mask_offset)
    corners = [pulled[0] * sx / 2 + pulled[1] * sy / 2
               for sx in (-1, 1) for sy in (-1, 1)]
    return dict(h=h, half=max(corners), radius2=df * df * sum(a * a for a in pulled),
                q=q, pulled=pulled, df=df)


def oracle(scene, frame, xy, precision=100):
    s = support(scene, frame, xy)
    if scene.mask_state != "half-plane":
        return ("foreground" if scene.mask_state == "full" else "background"), s
    with localcontext() as ctx:
        ctx.prec = precision
        lo = dec(s["h"]) - dec(s["half"]) - dec(s["radius2"]).sqrt()
        hi = dec(s["h"]) + dec(s["half"]) + dec(s["radius2"]).sqrt()
        result = "foreground" if lo > 0 else "background" if hi < 0 else "numerical"
    return result, s


def next_steps(value, steps):
    for _ in range(abs(steps)):
        value = math.nextafter(value, math.inf if steps > 0 else -math.inf)
    return value


def extremes(bound, scene, frame, xy, suite):
    """Record the actual rounded ray heights, not an exact visibility proof."""
    s = support(scene, frame, xy)
    native_n = tuple(map(float, s["pulled"]))
    length = math.hypot(*native_n)
    df = float(s["df"])
    normal_array = np.array(native_n)
    direction = normal_array / length
    native_xy = np.array(xy, dtype=np.float64)
    rays = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cell = native_xy + (.5 * sx, .5 * sy)
            for sign in (-1, 1):
                pupil = sign * direction
                q = frame.forward_similarity.inverse(cell + df * pupil)
                suite.watch(normal_array, direction, native_xy, cell, pupil, q)
                height = q[0] * scene.mask_normal[0] + q[1] * scene.mask_normal[1] - scene.mask_offset
                rays.append(dict(corner=[sx, sy], pupil_sign=sign, height=float(height)))
    return rays


class Suite:
    def __init__(self):
        self.checks = []
        self.started_cpu, self.started_wall = time.process_time(), time.monotonic()
        self.peak_owned_array_bytes = 0

    def check_budget(self):
        if time.process_time() - self.started_cpu > 60 or time.monotonic() - self.started_wall > 120:
            raise RuntimeError("independent geometry control CPU/wall ceiling")

    def check(self, name, passed, **evidence):
        self.check_budget()
        self.checks.append(dict(name=name, passed=bool(passed), evidence=evidence))

    def watch(self, *arrays):
        self.check_budget()
        backings = {}
        for array in arrays:
            while isinstance(array.base, np.ndarray):
                array = array.base
            backings[id(array)] = array.nbytes
        self.peak_owned_array_bytes = max(self.peak_owned_array_bytes, sum(backings.values()))
        if self.peak_owned_array_bytes > 32 * 1024 * 1024:
            raise RuntimeError("independent explicit named-array ceiling")

    def group(self, name, function):
        try:
            function()
        except Exception as exc:
            self.checks.append(dict(name=name + "-exception", passed=False,
                                    evidence=dict(exception=str(exc), traceback=traceback.format_exc())))


@contextmanager
def substitute(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield original
    finally:
        setattr(owner, name, original)


def make_scene(model, offset, normal=(3., 4.), state="half-plane"):
    return model.Scene(model.Field(15000.), model.Field(9000.), (1., 2.), normal, offset, state)


def base_maps(model):
    return (model.Similarity(), model.Similarity(2., 0., (1., -2.), (.5, -.25)))


def selector_tangencies(suite, geometry, bound):
    model = bound.model
    emitted = 0
    for map_index, sim in enumerate(base_maps(model)):
        for side, tangent in (("foreground", (46.5, 20.5)[map_index]),
                              ("background", (83.5, 39.)[map_index])):
            for multiplier in (1., 8.):
                for shifted in (False, True):
                    shift = (2. ** 20, -2. ** 19) if shifted else (0., 0.)
                    actual_sim = replace(sim,
                                         centre=tuple(sim.centre[i] + shift[i] for i in range(2)),
                                         translation=tuple(sim.translation[i] - shift[i] for i in range(2)))
                    frame = model.Frame(0, 5 / 8, 8., actual_sim)
                    normal = (3 * multiplier, 4 * multiplier)
                    offset0 = (tangent + 3 * shift[0] + 4 * shift[1]) * multiplier
                    for step in STEPS:
                        scene = make_scene(model, next_steps(offset0, step), normal)
                        expected = side if ((side == "foreground" and step < 0) or
                                             (side == "background" and step > 0)) else "numerical"
                        selector = geometry.ExactSelector(scene, frame)
                        actual = selector.classify((7, 11))
                        alternate, s = oracle(scene, frame, (7, 11))
                        suite.check(f"tangent-{map_index}-{side}-m{multiplier}-shift{shifted}-step{step}",
                                    actual == expected == alternate and selector.exact_height((7, 11)) == s["h"],
                                    expected=expected, actual=actual, independent=alternate,
                                    exact_height=frac_record(s["h"]), half=frac_record(s["half"]),
                                    radius_squared=frac_record(s["radius2"]),
                                    rounded_extremes=extremes(bound, scene, frame, (7, 11), suite))
                        # Both optimized integer and rational-coordinate branches must agree.
                        suite.check(f"tangent-coordinate-type-{emitted}", selector.classify((7., 11.)) == actual)
                        emitted += 1
    suite.check("complete-literal-tangent-population", emitted == 112, records=emitted)


def bracket_tangent(scene, frame, sign, precision):
    s = support(scene, frame, (7, 11))
    with localcontext() as ctx:
        ctx.prec = precision
        target = dec(s["h"] + ratio(scene.mask_offset)) + sign * (dec(s["half"]) + dec(s["radius2"]).sqrt())
        rounded = float(target)
        lo, hi = rounded, rounded
        if Decimal.from_float(rounded) < target:
            hi = math.nextafter(rounded, math.inf)
        elif Decimal.from_float(rounded) > target:
            lo = math.nextafter(rounded, -math.inf)
        return lo, hi


def rotated_and_lattice(suite, geometry, bound):
    model = bound.model
    sim = model.Similarity(.8, math.atan2(4, 3), (2.25, -1.5), (.375, -.625))
    frame = model.Frame(0, 5 / 8, 8., sim)
    scene0 = make_scene(model, 0.)
    for sign in (-1, 1):
        lo, hi = bracket_tangent(scene0, frame, sign, 100)
        suite.check(f"rotated-bracket-refinement-{sign}", (lo, hi) == bracket_tangent(scene0, frame, sign, 200),
                    low=lo, high=hi)
        for index, offset in enumerate((math.nextafter(lo, -math.inf), lo, hi, math.nextafter(hi, math.inf))):
            scene = replace(scene0, mask_offset=offset)
            expected, s = oracle(scene, frame, (7, 11), 200)
            selector = geometry.ExactSelector(scene, frame)
            suite.check(f"rotated-branch-{sign}-{index}", selector.classify((7, 11)) == expected,
                        offset=offset, expected=expected, actual=selector.classify((7, 11)),
                        exact_height=frac_record(s["h"]), rounded_extremes=extremes(bound, scene, frame, (7, 11), suite))
    cells = 0
    for map_index, sim in enumerate(base_maps(model)):
        observed = set()
        scene = make_scene(model, (51., 22.75)[map_index])
        for frame_index, focus in enumerate((5 / 8, 1., 9 / 8)):
            frame = model.Frame(frame_index, focus, 8., sim)
            selector = geometry.ExactSelector(scene, frame)
            records = []
            for y in range(13):
                for x in range(19):
                    expected, _ = oracle(scene, frame, (x, y))
                    actual = selector.classify((x, y))
                    records.append([x, y, expected, actual])
                    observed.add(actual)
                    cells += 1
            suite.check(f"complete-19x13-{map_index}-{frame_index}",
                        all(row[2] == row[3] for row in records), records=records)
        suite.check(f"three-branches-live-{map_index}", observed == {"foreground", "background", "numerical"},
                    observed=sorted(observed))
    suite.check("complete-independent-lattice", cells == 1482, cells=cells)


def branch_faults(suite, geometry, bound):
    model = bound.model
    frame = model.Frame(0, 5 / 8, 8.)
    for h in (-30., -18.5, -16., -12., 0., 12., 16., 18.5, 30.):
        scene = make_scene(model, 65 - h)
        expected, _ = oracle(scene, frame, (7, 11))
        selector = geometry.ExactSelector(scene, frame)
        actual = selector.classify((7, 11))
        suite.check(f"literal-height-{h}", actual == expected, expected=expected, actual=actual)
        if abs(h) == 12:
            original = model.Frame.defocus
            def background_as_foreground(self, scene):
                _, db = original(self, scene)
                return db, db
            with substitute(model.Frame, "defocus", background_as_foreground):
                wrong = geometry.ExactSelector(scene, frame).classify((7, 11))
            suite.check(f"actual-wrong-radius-{h}", actual == "numerical" and wrong == ("foreground" if h > 0 else "background"),
                        baseline=actual, changed=wrong)
            suite.check(f"restored-radius-null-{h}", geometry.ExactSelector(scene, frame).classify((7, 11)) == actual)
        if abs(h) == 16:
            # Deliberate test-only instance fault in both actual classify branches.
            selector._coefficients["half"] = F(0)
            selector._ints = (*selector._ints[:3], 0)
            expected_wrong = "foreground" if h > 0 else "background"
            wrong = [selector.classify((7, 11)), selector.classify((7., 11.))]
            suite.check(f"actual-missing-cell-support-{h}", actual == "numerical" and wrong == [expected_wrong] * 2,
                        baseline=actual, changed=wrong)
            suite.check(f"restored-cell-support-null-{h}", geometry.ExactSelector(scene, frame).classify((7, 11)) == actual)
    for state, expected in (("full", "foreground"), ("absent", "background")):
        scene = make_scene(model, 65, state=state)
        suite.check(f"explicit-mask-{state}", geometry.ExactSelector(scene, frame).classify((7, 11)) == expected)
    sim = model.Similarity(1., 0., (2. ** 42, 0.), (0., 0.))
    frame = replace(frame, forward_similarity=sim)
    scene = make_scene(model, 0.)
    small, normal = geometry.ExactSelector(scene, frame, bit_limit=8), geometry.ExactSelector(scene, frame)
    suite.check("finite-unsupported-limit-fallback", small.classify((7, 11)) == "numerical" and bool(small.unsupported_reason),
                reason=small.unsupported_reason)
    suite.check("finite-supported-limit-companion", normal.classify((7, 11)) == "foreground" and normal.unsupported_reason is None)
    for index, xy in enumerate(((math.nan, 0.), (0., math.inf), (-math.inf, 1.))):
        try:
            result = normal.classify(xy)
            suite.check(f"nonfinite-coordinate-refusal-{index}", False, returned=result)
        except ValueError as exc:
            suite.check(f"nonfinite-coordinate-refusal-{index}", True, refusal=str(exc))


def crossing_oracle(height, radius, alpha, state):
    """Solve line/circle crossings with acos, rather than author's asin ladder."""
    start, end = alpha - math.pi / 2, alpha - math.pi / 2 + 2 * math.pi
    cuts = [start, end]
    if state == "half-plane" and radius and abs(height) < radius:
        cuts.append(start + math.pi)
        if height:
            for j in range(33):
                level = 2. ** -j
                projection = -height / (radius * level)
                if abs(projection) < 1:
                    angle = math.acos(projection)
                    cuts.extend(start + ((theta - start) % (2 * math.pi))
                                for theta in (alpha - angle, alpha + angle))
    return sorted(set(cuts))


def same_cuts(actual, expected):
    return len(actual) == len(expected) and all(abs(a - b) <= 1e-12 for a, b in zip(actual, expected))


def validate_point_record(record, point, height, radius, alpha, state):
    expected = crossing_oracle(height, radius, alpha, state)
    keys = {"xy", "height", "radius", "alpha", "cuts"}
    return (set(record) == keys and record["xy"] == list(point)
            and record["height"] == height and record["radius"] == radius
            and record["alpha"] == alpha and same_cuts(record["cuts"], expected))


def cut_controls(suite, preflight, bound):
    model = bound.model
    heights = (-15., -7.5, -15 / 8, -15 / 64, 0., 15 / 64, 15 / 8, 7.5, 15.)
    points = [(h / 3, 0.) for h in heights]
    budget = preflight.Budget(started_cpu=suite.started_cpu, started_wall=suite.started_wall)
    count = 0
    for focus in (5 / 8, 1., 11 / 8):
        frame = model.Frame(0, focus, 8.)
        df = 8 * (focus - 1)
        radius = abs(df) * 5
        alpha = math.atan2(4 * df, 3 * df) if df else math.atan2(4, 3)
        for state in ("half-plane", "full", "absent"):
            scene = make_scene(model, 0., state=state)
            records = preflight.point_cuts(bound, scene, frame, points, budget)
            suite.check(f"point-count-{focus}-{state}", len(records) == 9)
            for index, (record, point, height) in enumerate(zip(records, points, heights)):
                passed = validate_point_record(record, point, height, radius, alpha, state)
                suite.check(f"point-cut-{focus}-{state}-{index}", passed,
                            actual=record, independent_cuts=crossing_oracle(height, radius, alpha, state))
                count += 1
    suite.check("complete-literal-point-population", count == 81, records=count)

    scene = make_scene(model, 0.)
    frame = model.Frame(0, 5 / 8, 8.)
    mixed_points = [(-2.5, 0.), (2.5, 0.)]
    alpha = math.atan2(-12., -9.)
    null = preflight.point_cuts(bound, scene, frame, mixed_points, budget)
    original_cuts = bound.render.angular_cuts
    def omit_negative(height, radius, alpha, mask_state, include_ladder=True):
        returned = original_cuts(height, radius, alpha, mask_state, include_ladder)
        return [returned[0], returned[-1]] if height < 0 else returned
    with substitute(bound.render, "angular_cuts", omit_negative):
        wrong = preflight.point_cuts(bound, scene, frame, mixed_points, budget)
    suite.check("actual-negative-cut-omission-detected",
                not validate_point_record(wrong[0], mixed_points[0], -7.5, 15., alpha, "half-plane"),
                null=null[0], changed=wrong[0])
    suite.check("positive-cut-omission-companion", wrong[1] == null[1])
    suite.check("restored-cut-null", preflight.point_cuts(bound, scene, frame, mixed_points, budget) == null)
    def valid_association(records):
        return len(records) == 2 and all(validate_point_record(rec, xy, h, 15., alpha, "half-plane")
                                        for rec, xy, h in zip(records, mixed_points, (-7.5, 7.5)))
    suite.check("actual-point-association-null", valid_association(null))
    suite.check("reader-omitted-point-fault", not valid_association(null[1:]))
    suite.check("reader-duplicated-point-fault", not valid_association([null[0], null[0]]))

    frame = replace(frame, forward_similarity=model.Similarity(1., 0., (2. ** 42, 0.), (0., 0.)))
    cancellation_points = [(2. ** -12, 0.), (-2. ** -12, 0.)]
    original = preflight.point_cuts(bound, scene, frame, cancellation_points, budget)
    def precombined_inverse(self, xy):
        matrix = self.inverse_matrix()
        c, t = np.array(self.centre), np.array(self.translation)
        intercept = c - matrix @ c - matrix @ t
        return np.asarray(xy, dtype=np.float64) @ matrix.T + intercept
    with substitute(model.Similarity, "inverse", precombined_inverse):
        changed = preflight.point_cuts(bound, scene, frame, cancellation_points, budget)
    for index, point in enumerate(cancellation_points):
        exact_h = float(support(scene, frame, point)["h"])
        suite.check(f"rounded-cancellation-null-{index}",
                    validate_point_record(original[index], point, 0., 15., alpha, "half-plane")
                    and len(original[index]["cuts"]) == 3,
                    record=original[index], exact_affine_height=exact_h)
        suite.check(f"actual-precombined-height-fault-{index}",
                    changed[index]["height"] == exact_h and exact_h != 0
                    and same_cuts(changed[index]["cuts"], crossing_oracle(exact_h, 15., alpha, "half-plane"))
                    and not same_cuts(changed[index]["cuts"], original[index]["cuts"]),
                    changed=changed[index], original=original[index])
    suite.check("restored-cancellation-null",
                preflight.point_cuts(bound, scene, frame, cancellation_points, budget) == original)
    suite.check("point-helper-budget-visited", budget.check_calls > 0, receipt=budget.receipt())
    suite.peak_owned_array_bytes = max(suite.peak_owned_array_bytes, budget.peak_bytes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    for name in ("loader", "geometry", "preflight"):
        ap.add_argument(f"--{name}-sha256", required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    suite = Suite()
    result = dict(schema="m194g-independent-geometry-controls-v1", status="RUNNING",
                  interpreter_argv=sys.orig_argv, argv=sys.argv, executable=sys.executable,
                  python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
                  environment={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
                  started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  sources_before={}, sources_after={}, checks=suite.checks)
    paths = [Path(__file__).resolve(), HERE / "independent-geometry-preregister.md", HERE / "preregister.md",
             HERE / "pinned-loader.py", HERE / "geometry.py", HERE / "preflight.py",
             HERE.parent / "m194e-joint-pupil" / "model.py", HERE.parent / "m194e-joint-pupil" / "render.py"]
    try:
        (args.out / "source").mkdir()
        for path in paths:
            key = path.relative_to(ROOT).as_posix()
            result["sources_before"][key] = digest(path)
            destination = args.out / "source" / key
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        loader = load_checked(HERE / "pinned-loader.py", "m194g_independent_pinned_loader", args.loader_sha256)
        geometry = load_checked(HERE / "geometry.py", "geometry", args.geometry_sha256)
        preflight = load_checked(HERE / "preflight.py", "m194g_independent_preflight_subject", args.preflight_sha256)
        bound = loader.load_frozen()
        suite.check("preflight-imported-source-binding",
                    preflight.LOADER_IMPORT_SHA == args.loader_sha256
                    and preflight.geometry.__checked_source__["sha256"] == args.geometry_sha256)
        def forbidden(*args, **kwargs):
            raise RuntimeError("radiance execution forbidden in geometry commission")
        with ExitStack() as traps:
            for owner, name in ((bound.model.Field, "evaluate"),
                                (bound.render, "render_points"), (bound.render, "render_cell"),
                                (bound.render, "angular_integrand")):
                traps.enter_context(substitute(owner, name, forbidden))
            suite.group("selector-tangencies", lambda: selector_tangencies(suite, geometry, bound))
            suite.group("rotated-and-lattice", lambda: rotated_and_lattice(suite, geometry, bound))
            suite.group("branch-faults", lambda: branch_faults(suite, geometry, bound))
            suite.group("point-cuts", lambda: cut_controls(suite, preflight, bound))
        suite.check("frozen-imports-unchanged", bound.assert_unchanged())
        result["status"] = "PASS_GEOMETRY_COMPONENTS_ONLY" if all(c["passed"] for c in suite.checks) else "UNCOMMISSIONED_GEOMETRY"
    except Exception as exc:
        result.update(status="INSTRUMENT_INVALID", exception=str(exc), traceback=traceback.format_exc())
    finally:
        result["sources_after"] = {p.relative_to(ROOT).as_posix(): digest(p) for p in paths if p.exists()}
        result["source_unchanged"] = result["sources_before"] == result["sources_after"]
        if not result["source_unchanged"]:
            result["status"] = "INSTRUMENT_INVALID"
        result.update(check_count=len(suite.checks), passed_count=sum(c["passed"] for c in suite.checks),
                      cpu_seconds=time.process_time() - suite.started_cpu,
                      wall_seconds=time.monotonic() - suite.started_wall,
                      tracked_owned_array_bytes=suite.peak_owned_array_bytes,
                      array_scope="named explicit arrays at independent checkpoints and actual point-helper Budget; excludes Python objects/RSS/transient expressions",
                      ended_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        (args.out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf8")
        print(json.dumps({k: result[k] for k in ("status", "check_count", "passed_count", "source_unchanged")}))
    return 0 if result["status"] == "PASS_GEOMETRY_COMPONENTS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
