"""Independent complete-cost artifact read and reused row-boundary oracle; no counter/integrator import."""
import ast
from datetime import datetime
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMMIT = "44d2670dc30de10e2f4d2b8ca277c5278732c1eb"
PINS = {
    "cost-release-2.json": "7214addd5905a0f238a51554b7bd7add67ba6aa8c2b1c5abb8135159117aabbf",
    "preflight-2/result.json": "c9e9154fd395a06a5d1cbb28123ac84f92ee1ac61b1a97216f8904b8b6261677",
    "preflight-1/result.json": "f23b5b1d24ba3e9516b246dce452c336749a3824c373484018a63c68ba66d010",
    "independent-cost-1-read.py": "da31e6fba6d5aa1eb1d5becd83f7e2e903d1918b294742e4e3fd41138ca91ff7",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def current(ref):
    path = Path(ref["path"])
    if not path.is_absolute():
        path = ROOT / path
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ref["sha256"] and len(raw) == ref["bytes"]
    return path.resolve()


def git_bytes(path):
    return subprocess.check_output(["git", "show", COMMIT + ":" + str(path).replace("\\", "/")], cwd=ROOT)


def main():
    for name, digest in PINS.items():
        assert sha(HERE / name) == digest
    release = read(HERE / "cost-release-2.json")
    result, previous = read(HERE / "preflight-2/result.json"), read(HERE / "preflight-1/result.json")
    fixture = read(HERE / "fixture.json")
    assert result["fixture_record"] == fixture and current(result["fixture"]) == (HERE / "fixture.json").resolve()
    assert result["schema"] == "m194g-geometry-preflight-v1" and result["status"] == "PASS_COST_ONLY"
    assert not any(k in result for k in ("error", "traceback", "ordered_partial_stream_sha256", "sources_after_error"))
    assert result["sources_before"] == result["sources_after"]
    bound = {**result["sources_before"], **{ref["path"]: ref for ref in result["frozen_imports"].values()}}
    released = {str(current(ref)): ref for ref in release["files"]}
    assert len(result["sources_before"]) == 19 and len(bound) == len(released) == 21
    assert set(bound) == set(released)
    source_dir = HERE / "preflight-2/source"
    assert {p.name for p in source_dir.iterdir()} == {Path(k).name for k in bound}
    assert len({Path(k).name for k in bound}) == 21
    for path, ref in bound.items():
        actual = current(ref)
        assert (ref["sha256"], ref["bytes"]) == (released[path]["sha256"], released[path]["bytes"])
        assert (source_dir / actual.name).read_bytes() == actual.read_bytes()
        historical = git_bytes(actual.relative_to(ROOT))
        assert hashlib.sha256(historical).hexdigest() == ref["sha256"] and len(historical) == ref["bytes"]
    amendment_key = str(HERE / "amendment-1-counter-budget.md")
    assert bound[amendment_key]["sha256"] == "205ba1ac42e8325eb7d1ede41e05399776eddf7d80a99ecb3ba12b1931f73a99"
    assert result["local_imports"]["geometry"] == bound[str(HERE / "geometry.py")]
    assert result["local_imports"]["loader_sha256"] == bound[str(HERE / "pinned-loader.py")]["sha256"]
    assert result["invocation"]["orig_argv"][1:] == release["argv"][1:]
    assert Path(result["invocation"]["orig_argv"][0]) == Path(result["invocation"]["executable"])
    assert Path(result["invocation"]["cwd"]) == ROOT
    assert set(result["thread_environment"].values()) == {"2"}
    assert git_bytes("experiments/m194g-larger-pupil/cost-release-2.json") == (HERE / "cost-release-2.json").read_bytes()
    commit_time = subprocess.check_output(["git", "show", "-s", "--format=%cI", COMMIT], cwd=ROOT, text=True).strip()
    assert datetime.fromisoformat(commit_time) < datetime.fromisoformat(result["started_utc"]) < datetime.fromisoformat(result["ended_utc"])
    controls = []
    for ref in [release["affected_control"], *release["historical_controls"]]:
        path = current(ref)
        record = read(path)
        assert len(record["checks"]) == ref["checks"] and all(row["passed"] is True for row in record["checks"])
        if record["schema"] == "m194g-author-controls-v1":
            assert record["status"] == "PASS_AUTHOR_CONTROLS" and record["passed"] == 41
        elif record["schema"] == "m194g-independent-geometry-controls-v1":
            assert record["status"] == "PASS_GEOMETRY_COMPONENTS_ONLY" and record["check_count"] == 373
        else:
            assert record["passed"] is True and record["failure"] is None and record["check_count"] == ref["checks"]
        assert git_bytes(path.relative_to(ROOT)) == path.read_bytes()
        controls.append(dict(path=ref["path"], sha256=ref["sha256"], checks=ref["checks"], historical=ref is not release["affected_control"]))
    affected = read(current(release["affected_control"]))
    assert affected["sources_before"] == affected["sources_after"]
    assert all(sha(path) == digest for path, digest in affected["sources_after"].items())

    # Reuse only the original independent row search, not a copy of numerical methods.
    oracle_source = (HERE / "independent-cost-1-read.py").read_bytes()
    names = {"first_true", "branch_prefix"}
    nodes = [node for node in ast.parse(oracle_source).body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    namespace = dict(Fraction=Fraction)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<pinned-independent-row-boundary-oracle-only>", "exec"), namespace)
    assert fixture["gauge"] == "reference-2 native pixels; identity placements" and fixture["reference_index"] == 2
    assert (result["width"], result["height"]) == (320, 240)
    assert result["frame_indices"] == list(range(5)) and all(type(x) is int for x in result["frame_indices"])
    arms = ["primary", "angle-refined", "cell-refined"]
    assert result["arms"] == fixture["arms"] == arms
    rows = result["frames"]
    assert len(rows) == 15 and [(r["arm"], r["frame_index"]) for r in rows] == [(a, i) for a in arms for i in range(5)]
    for key, expected in (("completed_frames", 15), ("completed_cells", 1152000), ("width", 320), ("height", 240)):
        assert type(result[key]) is int and result[key] == expected
    work = result["work"]
    limits = dict(whole_run_cpu_seconds=180.0, whole_run_wall_seconds=240.0,
                  tracked_owned_ndarray_bytes=33554432, per_frame_points_strictly_below=8000000,
                  per_frame_angular_nodes_strictly_below=1200000000)
    assert work["limits"] == fixture["preflight_limits"] == release["limits"] == limits
    frame_rows = []
    for row in rows:
        assert all(type(row[k]) is int and row[k] >= 0 for k in
                   ("frame_index", "visited_cells", "roots", "low_points", "high_points", "angular_nodes", "maximum_intervals"))
        assert row["status"] == "complete" and row["visited_cells"] == 76800 and row["last_coordinate"] == [319, 239]
        assert row["unsupported_selector_reason"] is None
        assert set(row["branches"]) == {"foreground", "background", "numerical"}
        assert all(type(v) is int and v >= 0 for v in row["branches"].values())
        expected = namespace["branch_prefix"](fixture, row["frame_index"], 76800)
        assert row["branches"] == expected and sum(expected.values()) == 76800
        points = row["low_points"] + row["high_points"]
        assert points < limits["per_frame_points_strictly_below"] and row["angular_nodes"] < limits["per_frame_angular_nodes_strictly_below"]
        expected_orders = (8, 16, 16, 32) if row["arm"] == "cell-refined" else ((4, 8, 32, 64) if row["arm"] == "angle-refined" else (4, 8, 16, 32))
        assert tuple(row["integrator"][k] for k in ("cell_low", "cell_high", "angle_low", "angle_high")) == expected_orders
        assert row["low_points"] == row["roots"] * expected_orders[0] ** 2
        assert row["high_points"] == row["roots"] * expected_orders[1] ** 2
        frame_rows.append(dict(arm=row["arm"], index=row["frame_index"], cells=76800, branches=expected,
                               roots=row["roots"], points=points, angular_nodes=row["angular_nodes"], maximum_intervals=row["maximum_intervals"]))
    assert rows[:10] == previous["frames"][:10]
    assert sum(r["visited_cells"] for r in rows) == result["completed_cells"]
    assert work["frame_count"] == 15 and work["total_points"] == sum(r["points"] for r in frame_rows) == 11750400
    assert work["total_angular_nodes"] == sum(r["angular_nodes"] for r in rows) == 3698302464
    assert work["frame_points"] == frame_rows[-1]["points"] and work["frame_angular_nodes"] == frame_rows[-1]["angular_nodes"]
    assert 0 <= work["cpu_seconds"] <= 180 and 0 <= work["wall_seconds"] <= 240
    assert 0 <= work["tracked_peak_ndarray_bytes"] <= 33554432
    assert isinstance(result["ordered_stream_sha256"], str) and len(result["ordered_stream_sha256"]) == 64
    assert all(c in "0123456789abcdef" for c in result["ordered_stream_sha256"])
    progress = read(HERE / "preflight-2/progress.json")
    assert progress["completed_cells"] <= result["completed_cells"] and progress["completed_frames"] <= 15
    assert progress["work"]["cpu_seconds"] <= work["cpu_seconds"] and progress["work"]["wall_seconds"] <= work["wall_seconds"]
    assert {p.name for p in (HERE / "preflight-2").iterdir()} == {"source", "progress.json", "result.json"}
    assert read(HERE / "preflight-2-launch.log")["status"] == "PASS_COST_ONLY"
    for name, digest in PINS.items():
        assert sha(HERE / name) == digest
    record = dict(schema="m194g-independent-complete-cost-read-v1", evidence_consistent=True, disposition="PASS_COST_ONLY",
                  scope="complete geometry cost admission only; no numerical/radiance/quality admission",
                  command=sys.orig_argv, reader_sha256=sha(Path(__file__)), external_pins=PINS,
                  source_commit=COMMIT, commit_time=commit_time, started_utc=result["started_utc"], ended_utc=result["ended_utc"],
                  source_files=21, all_source_current_snapshot_release_git_bindings_match=True, controls=controls,
                  complete_rows=15, complete_cells=1152000, frame_rows=frame_rows, work=work,
                  maximum_frame_points=max(r["points"] for r in frame_rows),
                  maximum_frame_nodes=max(r["angular_nodes"] for r in frame_rows),
                  old_ten_rows_exactly_equal=True, ordered_stream_sha256=result["ordered_stream_sha256"],
                  independent_full_stream_replay=False, nominal_counter_not_rerun=True,
                  root_attributed_exit=dict(session=9359, exit_code=0, independently_observed_by_this_reader=False))
    output = HERE / "independent-cost-2-read.json"
    assert not output.exists()
    output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(dict(evidence_consistent=True, disposition="PASS_COST_ONLY", output_sha256=sha(output))))


if __name__ == "__main__":
    main()
