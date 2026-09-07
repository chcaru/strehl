"""Affected M194g elapsed/input controls only; never an intended cost population."""
from __future__ import annotations
import argparse
import ast
import copy
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E_DIR = HERE.parent / "m194e-joint-pupil"
OLD_COMMIT = "0e125df2eb0319982a0cbf97c9f85608d68ab01e"
AMENDMENT = "amendment-1-counter-budget.md"
PINS = {
    HERE / "preflight.py": "c162c2651b1fd3e8345f08c0c9cd5edf5e100d94d7958c5dedde1d791a18763c",
    HERE / "fixture.json": "e84f0bbbda9bef039da86616c9f051d416929f4dbe78477cc5b3fc21206856bb",
    HERE / AMENDMENT: "205ba1ac42e8325eb7d1ede41e05399776eddf7d80a99ecb3ba12b1931f73a99",
    HERE / "geometry.py": "24b812071b8b6189423b9792a22c55abd9a4f4a78921a9d558ab24489f1923b3",
    HERE / "pinned-loader.py": "222fab4a932fe236c120d8a48e4521747474e2ef57ba58781bf5c59f644f4f76",
    E_DIR / "model.py": "a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8",
    E_DIR / "render.py": "487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def module(path, name):
    raw = Path(path).read_bytes()
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    value = importlib.util.module_from_spec(spec)
    value.__file__ = str(path)
    sys.modules[name] = value
    exec(compile(raw, str(path), "exec"), value.__dict__)
    return value


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class Audit:
    def __init__(self, output):
        self.output, self.rows = output, []

    def record(self, name, passed, **detail):
        row = dict(name=name, passed=bool(passed), detail=detail)
        self.rows.append(row)
        write(self.output / "checks.json", self.rows)
        print(json.dumps(row, allow_nan=False), flush=True)

    def outcome(self, name, call, *, refusal=False):
        try:
            returned = call()
        except (ValueError, RuntimeError, OSError) as error:
            self.record(name, refusal, error=repr(error))
            return None
        self.record(name, not refusal, outcome="returned")
        return returned


def old_bytes(name):
    return subprocess.check_output(["git", "show", OLD_COMMIT + ":experiments/m194g-larger-pupil/" + name], cwd=ROOT)


def equivalence(audit):
    old_raw, new_raw = old_bytes("preflight.py"), (HERE / "preflight.py").read_bytes()
    old = old_raw.decode("utf-8").replace("\r\n", "\n")
    new = new_raw.decode("utf-8").replace("\r\n", "\n")
    edits = [
        ('FIXTURE_HASH = "fc36b5f252c5efeda1cba753312dd061ebf5583856ec45466f61b0f66dc31ef2"',
         'FIXTURE_HASH = "' + PINS[HERE / "fixture.json"] + '"'),
        ('PREREG_HASH = "d0c570ec892a2c3e40b90c0f7eef2a9ff0649dd53bc34adee6b6bc65280f14c8"\n',
         'PREREG_HASH = "d0c570ec892a2c3e40b90c0f7eef2a9ff0649dd53bc34adee6b6bc65280f14c8"\nAMENDMENT_HASH = "' + PINS[HERE / AMENDMENT] + '"\n'),
        ('DEFAULT_LIMITS = dict(whole_run_cpu_seconds=60., whole_run_wall_seconds=120.,',
         'DEFAULT_LIMITS = dict(whole_run_cpu_seconds=180., whole_run_wall_seconds=240.,'),
        ('HERE / "design-sources.json", HERE / "independent-preflight-design-review.md"]',
         'HERE / "design-sources.json", HERE / "independent-preflight-design-review.md",\n             HERE / "amendment-1-counter-budget.md"]'),
        ('        loader.checked_bytes(HERE / "preregister.md", PREREG_HASH)\n',
         '        loader.checked_bytes(HERE / "preregister.md", PREREG_HASH)\n        loader.checked_bytes(HERE / "amendment-1-counter-budget.md", AMENDMENT_HASH)\n'),
    ]
    expected = old
    for before, after in edits:
        assert expected.count(before) == 1
        expected = expected.replace(before, after, 1)
    audit.record("whole-source-exact-allowlist", new == expected, named_replacements=len(edits))
    if new != expected:
        raise AssertionError("unreleased source change")
    (audit.output / "old-preflight.py.txt").write_bytes(old_raw)
    (audit.output / "source-diff.txt").write_text("".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile="old", tofile="candidate")), encoding="utf-8")
    old_tree, new_tree = ast.parse(old), ast.parse(new)
    old_defs = {n.name: n for n in old_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    new_defs = {n.name: n for n in new_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert set(old_defs) == set(new_defs)
    unchanged = []
    for name in old_defs:
        if name in ("source_bindings", "run"):
            continue
        assert ast.dump(old_defs[name], include_attributes=False) == ast.dump(new_defs[name], include_attributes=False)
        assert ast.get_source_segment(old, old_defs[name]) == ast.get_source_segment(new, new_defs[name])
        unchanged.append(name)
    audit.record("unchanged-actual-function-and-class-bodies", True, symbols=unchanged)
    old_fixture = json.loads(old_bytes("fixture.json"))
    new_fixture = json.loads((HERE / "fixture.json").read_bytes())
    expected_fixture = copy.deepcopy(old_fixture)
    expected_fixture["preflight_limits"].update(whole_run_cpu_seconds=180.0, whole_run_wall_seconds=240.0)
    audit.record("fixture-only-two-elapsed-fields", new_fixture == expected_fixture)
    assert new_fixture == expected_fixture
    for name in ("geometry.py", "pinned-loader.py", "preregister.md"):
        audit.record("unchanged-original-" + name, old_bytes(name) == (HERE / name).read_bytes())
    write(audit.output / "old-fixture.json", old_fixture)
    return new_fixture


def direct_limits(audit, p, fixture):
    audit.record("actual-defaults-match-new-external-fixture", p.DEFAULT_LIMITS == fixture["preflight_limits"])
    for axis, values in (("cpu", (179.999, 180.0, 180.001)), ("wall", (239.999, 240.0, 240.001))):
        for value in values:
            def check_value():
                cpu, wall = Clock(), Clock()
                budget = p.Budget(cpu_clock=cpu, wall_clock=wall)
                (cpu if axis == "cpu" else wall).value = value
                budget.check()
            audit.outcome("actual-budget-" + axis + "-" + str(value), check_value, refusal=value == values[-1])
            def constructor_value():
                cpu, wall = Clock(), Clock()
                (cpu if axis == "cpu" else wall).value = value
                p.Budget(cpu_clock=cpu, wall_clock=wall, started_cpu=0.0, started_wall=0.0)
            audit.outcome("actual-constructor-" + axis + "-" + str(value), constructor_value, refusal=value == values[-1])
        companion = 90.0 if axis == "cpu" else 180.0
        for old_policy in (False, True):
            def policy_check():
                cpu, wall = Clock(), Clock()
                limits = dict(p.DEFAULT_LIMITS)
                if old_policy:
                    limits.update(whole_run_cpu_seconds=60.0, whole_run_wall_seconds=120.0)
                budget = p.Budget(limits, cpu_clock=cpu, wall_clock=wall)
                (cpu if axis == "cpu" else wall).value = companion
                budget.check()
            audit.outcome(("old-policy-refuses-" if old_policy else "new-policy-admits-") + axis + "-companion", policy_check, refusal=old_policy)
    for key, cap in (("points", 8_000_000), ("nodes", 1_200_000_000)):
        for value in (cap - 1, cap):
            def work_check():
                cpu, wall = Clock(), Clock()
                budget = p.Budget(cpu_clock=cpu, wall_clock=wall)
                budget.charge(**{key: value})
            audit.outcome("strict-" + key + "-" + str(value), work_check, refusal=value == cap)
    owner = np.empty(128, dtype=np.float64)
    clock = Clock()
    budget = p.Budget(cpu_clock=clock, wall_clock=clock)
    budget.watch(owner, owner[:96], owner[32:])
    audit.record("unchanged-storage-valid-shared-owner", budget.peak_bytes == 1024 and budget.peak_arrays == 1)
    def small_storage():
        budget = p.Budget(dict(p.DEFAULT_LIMITS, tracked_owned_ndarray_bytes=1023), cpu_clock=clock, wall_clock=clock)
        budget.watch(owner)
    audit.outcome("actual-storage-check-private-1023-cap-refuses", small_storage, refusal=True)


def traversal_limits(audit, p):
    bound = p.loader.load_frozen()
    m = bound.model
    scene = m.Scene(m.Field(15000), m.Field(12000), (1, 2), (1, .25), 2, "full")
    transform = m.Similarity(2, 0, (.5, -.5), (1.25, -.75))
    frames = tuple(m.Frame(i, focus, 2, transform) for i, focus in enumerate((.5, .75)))
    arms = ("primary", "angle-refined")
    def traversal(name, axis=None, values=(), boundary="first-cell"):
        cpu, wall = Clock(), Clock()
        budget = p.Budget(cpu_clock=cpu, wall_clock=wall)
        count, seen, applied, forbidden = {}, [], [], []
        def trap(*args, **kwargs):
            forbidden.append("unexpected geometry/radiance")
            raise AssertionError("full-mask fixture called numerical/radiance helper")
        def sink(row):
            assert row["kind"] == "cell"
            seen.append((row["arm"], row["frame_index"], *row["xy"]))
            trigger = ((boundary == "first-cell" and len(seen) == 1)
                       or (boundary == "cells" and row["arm"] == "primary" and row["frame_index"] == 0)
                       or (boundary == "frames" and row["arm"] == "primary" and row["xy"] == [1, 0])
                       or (boundary == "arms" and row["frame_index"] == 1 and row["xy"] == [1, 0]))
            if axis is not None and trigger:
                value = values[len(applied)]
                (cpu if axis == "cpu" else wall).value = value
                applied.append(value)
        try:
            with patch.object(bound.render, "triangle_rule", side_effect=trap), patch.object(p, "point_cuts", side_effect=trap), patch.object(m.Field, "evaluate", side_effect=trap):
                p.count_geometry(bound, scene, frames, 2, 1, arms, budget, sink=sink, result=count)
            assert len(seen) == len(set(seen)) == 8
            assert count["completed_cells"] == 8 and count["completed_frames"] == 4
            assert all(row["branches"] == dict(foreground=2, background=0, numerical=0) for row in count["frames"])
            assert budget.total_points == budget.total_nodes == 0 and not forbidden
            return count
        finally:
            write(audit.output / (name + ".json"), dict(fixture_only=True, result=count, observed_cells=seen, clock_values=applied, forbidden_calls=forbidden))
    for axis, values in (("cpu", (179.999, 180.0, 180.001)), ("wall", (239.999, 240.0, 240.001))):
        for value in values:
            name = "actual-traversal-" + axis + "-" + str(value)
            audit.outcome(name, lambda n=name, a=axis, v=value: traversal(n, a, (v,)), refusal=value == values[-1])
        accumulation = (90.0005, 180.001) if axis == "cpu" else (120.0005, 240.001)
        for boundary in ("cells", "frames", "arms"):
            name = "nonreset-" + axis + "-across-" + boundary
            audit.outcome(name, lambda n=name, a=axis, v=accumulation, b=boundary: traversal(n, a, v, b), refusal=True)
    complete = audit.outcome("actual-eight-analytic-cells-valid-final-companion", lambda: traversal("valid-final-traversal"))
    audit.record("analytic-actual-population-complete", complete is not None and complete["completed_cells"] == 8)
    bound.assert_unchanged()


def entry_controls(audit):
    names = ("preflight.py", "pinned-loader.py", "geometry.py", "fixture.json", "preregister.md", "design-sources.json",
             "independent-preflight-design-review.md", AMENDMENT)
    def entry(name, fault=None):
        base = audit.output / ("entry-" + name)
        local = base / "experiments/m194g-larger-pupil"
        local.mkdir(parents=True)
        frozen = base / "experiments/m194e-joint-pupil"
        frozen.mkdir()
        for source_name in names:
            shutil.copyfile(HERE / source_name, local / source_name)
        for source_name in ("model.py", "render.py"):
            shutil.copyfile(E_DIR / source_name, frozen / source_name)
        if fault == "missing-amendment":
            (local / AMENDMENT).unlink()
        elif fault == "changed-amendment":
            (local / AMENDMENT).write_bytes((local / AMENDMENT).read_bytes() + b"\nPRIVATE CHANGED AMENDMENT\n")
        elif fault == "old-fixture":
            (local / "fixture.json").write_bytes(old_bytes("fixture.json"))
        elif fault == "changed-fixture":
            value = json.loads((local / "fixture.json").read_bytes())
            value["preflight_limits"]["whole_run_cpu_seconds"] = 181.0
            write(local / "fixture.json", value)
        p = module(local / "preflight.py", "m194g_budget_private_" + name.replace("-", "_"))
        attempted = []
        original_sources = p.source_bindings
        captures = []
        def source_capture():
            captures.append(True)
            if fault == "secondary-source-error" and len(captures) > 1:
                raise OSError("PRIVATE_SECONDARY_SOURCE_CAPTURE_ERROR")
            return original_sources()
        def sentinel(*args, **kwargs):
            attempted.append(True)
            if fault == "change-after-start":
                with (local / AMENDMENT).open("ab") as stream:
                    stream.write(b"\nPRIVATE AFTER START\n")
            raise RuntimeError("PRIVATE_NO_INTENDED_COUNT_SENTINEL")
        with patch.object(p, "count_geometry", side_effect=sentinel), patch.object(p, "source_bindings", side_effect=source_capture):
            result = p.run(base / "result", local / "fixture.json")
        saved = json.loads((base / "result/result.json").read_bytes())
        assert result == saved and result["status"] == "UNCOMMISSIONED_COST"
        write(base / "independent-entry-observation.json", dict(fixture_only=True, count_sentinel_calls=len(attempted), source_capture_calls=len(captures), error=result["error"]))
        return result, attempted, p, local
    valid, called, _, _ = entry("valid-original-companion")
    audit.record("copied-actual-run-reaches-only-private-sentinel", len(called) == 1 and "PRIVATE_NO_INTENDED_COUNT_SENTINEL" in valid["error"])
    for name in ("missing-amendment", "changed-amendment", "old-fixture", "changed-fixture"):
        result, called, p, local = entry(name, name)
        audit.record("actual-entry-" + name + "-refuses-before-count", not called and "PRIVATE_NO_INTENDED_COUNT_SENTINEL" not in result["error"], error=result["error"])
        if name == "changed-fixture":
            audit.outcome("rehash-altered-fixture-cannot-select-policy", lambda: p.load_fixture(local / "fixture.json", sha(local / "fixture.json")), refusal=True)
    changed, called, _, local = entry("source-changed-after-start", "change-after-start")
    amendment_key = str((local / AMENDMENT).resolve())
    audit.record("actual-amendment-in-both-source-ledgers", amendment_key in changed["sources_before"] and amendment_key in changed["sources_after"])
    audit.record("after-start-amendment-change-recorded", len(called) == 1 and changed["sources_before"][amendment_key] != changed["sources_after"][amendment_key]
                 and "PRIVATE_NO_INTENDED_COUNT_SENTINEL" in changed["error"], scope="actual changed bytes recorded; sentinel remains deciding refusal")
    secondary, called, _, _ = entry("original-and-capture-errors", "secondary-source-error")
    audit.record("original-private-error-retained-with-secondary-source-error", len(called) == 1
                 and "PRIVATE_NO_INTENDED_COUNT_SENTINEL" in secondary["error"]
                 and "PRIVATE_SECONDARY_SOURCE_CAPTURE_ERROR" in secondary.get("sources_after_error", ""))
    final, called, _, _ = entry("valid-final-companion")
    audit.record("copied-entry-valid-final-companion", len(called) == 1 and "PRIVATE_NO_INTENDED_COUNT_SENTINEL" in final["error"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    audit = Audit(output)
    files = list(PINS) + [Path(__file__).resolve(), HERE / "independent-budget-controls-design.md", HERE / "preregister.md"]
    before = {str(path): sha(path) for path in files}
    failure = None
    started = time.monotonic()
    try:
        assert all(before[str(path)] == pin for path, pin in PINS.items())
        for path in files:
            target = output / "source" / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
        fixture = equivalence(audit)
        p = module(HERE / "preflight.py", "m194g_independent_budget_candidate")
        direct_limits(audit, p, fixture)
        traversal_limits(audit, p)
        entry_controls(audit)
    except Exception as error:
        failure = dict(error=repr(error), traceback=traceback.format_exc())
        print(failure["traceback"], flush=True)
    after = {str(path): sha(path) for path in files}
    passed = failure is None and bool(audit.rows) and all(row["passed"] for row in audit.rows) and before == after
    result = dict(schema="m194g-independent-budget-controls-v1", passed=passed, checks=audit.rows,
                  check_count=len(audit.rows), failure=failure, sources_before=before, sources_after=after,
                  source_unchanged=before == after, pins={str(k): v for k, v in PINS.items()}, old_commit=OLD_COMMIT,
                  orig_argv=sys.orig_argv, executable=sys.executable, xoptions=sys._xoptions,
                  versions=dict(python=sys.version, numpy=np.__version__),
                  environment={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
                  wall_seconds=time.monotonic() - started,
                  scope="affected elapsed/entry/source controls; injected clocks; no intended count or radiance authority")
    write(output / "result.json", result)
    print(json.dumps(dict(passed=passed, checks=len(audit.rows), result_sha256=sha(output / "result.json"))), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
