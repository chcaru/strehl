"""Read-only M194g cost-1 evidence review; no counter/model imports or render."""
from datetime import datetime
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def actual(ref):
    path = Path(ref["path"])
    if not path.is_absolute():
        path = ROOT / path
    raw = path.read_bytes()
    assert len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"]
    return path


def first_true(length, predicate):
    low, high = 0, length
    while low < high:
        middle = (low + high) // 2
        if predicate(middle):
            high = middle
        else:
            low = middle + 1
    return low


def branch_prefix(fixture, index, count):
    """Independent row boundary search, exact input dyadics; no selector calls."""
    assert fixture["forward_similarity"] == dict(scale=1.0, rotation=0.0, centre=[0.0, 0.0], translation=[0.0, 0.0])
    a, b = map(Fraction.from_float, fixture["scene"]["mask_normal"])
    assert a > 0
    offset = Fraction.from_float(fixture["scene"]["mask_offset"])
    half = (abs(a) + abs(b)) / 2
    # All intended focus/depth/K terms here are exact dyadics.
    df = Fraction.from_float(fixture["K"]) * (Fraction.from_float(fixture["inverse_foci"][index])
         - 1 / Fraction.from_float(fixture["scene"]["depths"][0]))
    radius2 = df * df * (a * a + b * b)
    totals = dict(foreground=0, background=0, numerical=0)
    width = fixture["width"]
    for y in range((count + width - 1) // width):
        extent = min(width, count - y * width)
        def foreground(x):
            clearance = a * x + b * y - offset - half
            return clearance > 0 and clearance * clearance > radius2
        def background(x):
            clearance = -(a * x + b * y - offset) - half
            return clearance > 0 and clearance * clearance > radius2
        fg = extent - first_true(extent, foreground)
        bg = first_true(extent, lambda x: not background(x))
        totals["foreground"] += fg
        totals["background"] += bg
        totals["numerical"] += extent - fg - bg
    return totals


def main():
    result_path = HERE / "preflight-1/result.json"
    progress_path = HERE / "preflight-1/progress.json"
    release_path = HERE / "cost-release-1.json"
    result, progress, release = map(load, (result_path, progress_path, release_path))
    result_sha = sha(result_path)
    fixture = load(HERE / "fixture.json")
    assert result["fixture_record"] == fixture
    assert result["sources_before"] == result["sources_after"]
    bound_files = {**result["sources_before"], **{v["path"]: v for v in result["frozen_imports"].values()}}
    released_files = {str(actual(ref)): ref for ref in release["files"]}
    assert set(bound_files) == set(released_files)
    for path, ref in bound_files.items():
        actual(ref)
        assert (ref["sha256"], ref["bytes"]) == (released_files[path]["sha256"], released_files[path]["bytes"])
        assert (HERE / "preflight-1/source" / Path(path).name).read_bytes() == Path(path).read_bytes()
    assert len({Path(path).name for path in bound_files}) == len(bound_files) == 14
    controls = []
    for ref in release["controls"]:
        record = load(actual(ref))
        assert record["passed"] is True and len(record["checks"]) == ref["checks"]
        assert all(row["passed"] for row in record["checks"])
        controls.append(dict(path=ref["path"], checks=ref["checks"], sha256=ref["sha256"]))
    loader = str((HERE / "pinned-loader.py").resolve())
    geometry = str((HERE / "geometry.py").resolve())
    assert result["local_imports"]["loader_sha256"] == bound_files[loader]["sha256"]
    assert result["local_imports"]["geometry"] == bound_files[geometry]
    assert result["invocation"]["orig_argv"][1:] == release["command"][1:]
    assert Path(result["invocation"]["orig_argv"][0]) == Path(result["invocation"]["executable"])
    assert Path(result["invocation"]["cwd"]) == ROOT
    assert set(result["thread_environment"].values()) == {"2"}
    commit = "0e125df2eb0319982a0cbf97c9f85608d68ab01e"
    committed = subprocess.check_output(["git", "show", commit + ":experiments/m194g-larger-pupil/cost-release-1.json"], cwd=ROOT)
    assert committed == release_path.read_bytes()
    committed_utc = subprocess.check_output(["git", "show", "-s", "--format=%cI", commit], cwd=ROOT, text=True).strip()
    assert datetime.fromisoformat(committed_utc) < datetime.fromisoformat(result["started_utc"])
    assert datetime.fromisoformat(result["started_utc"]) < datetime.fromisoformat(result["ended_utc"])
    for ref in release["files"] + release["controls"]:
        historical = subprocess.check_output(["git", "show", commit + ":" + ref["path"]], cwd=ROOT)
        assert len(historical) == ref["bytes"] and hashlib.sha256(historical).hexdigest() == ref["sha256"]
    expected_pairs = [(arm, i) for arm in fixture["arms"] for i in fixture["frame_indices"]]
    rows = result["frames"]
    assert [(row["arm"], row["frame_index"]) for row in rows] == expected_pairs[:11]
    assert len(rows) == 11 and result["completed_frames"] == 10
    assert all(row["status"] == "complete" and row["visited_cells"] == 76800 for row in rows[:10])
    partial = rows[-1]
    assert partial["status"] == "running" and partial["last_coordinate"] == [167, 166]
    assert partial["visited_cells"] == 166 * 320 + 167 == 53287
    branch_rows = []
    for row in rows:
        # The failing cell's branch is counted before its numerical work finishes.
        branch_count = row["visited_cells"] + (row is partial)
        expected = branch_prefix(fixture, row["frame_index"], branch_count)
        assert row["branches"] == expected and sum(expected.values()) == branch_count
        assert all(type(row[key]) is int and row[key] >= 0 for key in
                   ("frame_index", "visited_cells", "roots", "low_points", "high_points", "angular_nodes"))
        branch_rows.append(dict(arm=row["arm"], index=row["frame_index"], completed_cells=row["visited_cells"],
                                branch_records=branch_count, independent_branches=expected))
    assert result["completed_cells"] == sum(row["visited_cells"] for row in rows) == 821287 < 1152000
    work = result["work"]
    assert work["limits"] == fixture["preflight_limits"]
    assert work["total_points"] == sum(row["low_points"] + row["high_points"] for row in rows) == 5696960
    assert work["total_angular_nodes"] == sum(row["angular_nodes"] for row in rows) == 2091280512
    assert work["frame_count"] == len(rows)
    assert work["frame_points"] == partial["low_points"] + partial["high_points"] == 1780160
    assert work["frame_angular_nodes"] == partial["angular_nodes"] == 514394112
    assert work["cpu_seconds"] > work["limits"]["whole_run_cpu_seconds"]
    assert work["wall_seconds"] < work["limits"]["whole_run_wall_seconds"]
    assert all(row["low_points"] + row["high_points"] < work["limits"]["per_frame_points_strictly_below"]
               and row["angular_nodes"] < work["limits"]["per_frame_angular_nodes_strictly_below"] for row in rows)
    assert work["tracked_peak_ndarray_bytes"] < work["limits"]["tracked_owned_ndarray_bytes"]
    assert result["status"] == "UNCOMMISSIONED_COST" and "whole-run time ceiling" in result["error"]
    assert "ordered_stream_sha256" not in result and len(result["ordered_partial_stream_sha256"]) == 64
    assert progress["completed_cells"] < result["completed_cells"]
    assert progress["work"]["cpu_seconds"] <= 60 and progress["work"]["wall_seconds"] < 120
    assert set(p.name for p in (HERE / "preflight-1").iterdir()) == {"source", "result.json", "progress.json"}
    assert sha(result_path) == result_sha
    record = dict(schema="m194g-independent-cost-1-read-v1", evidence_consistent=True,
                  disposition="UNCOMMISSIONED_COST; incomplete population; no subset or numerical admission",
                  command=sys.orig_argv, reader_sha256=sha(Path(__file__)),
                  result_sha256=result_sha, progress_sha256=sha(progress_path), release_sha256=sha(release_path),
                  release_commit=commit, release_commit_time=committed_utc,
                  start=result["started_utc"], end=result["ended_utc"], sources_and_snapshots=14,
                  controls=controls, branch_rows=branch_rows, work=work,
                  scope="artifact read plus independent exact row-boundary searches; no counter/model import or rerun")
    output = HERE / "independent-cost-1-read.json"
    assert not output.exists()
    output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(dict(evidence_consistent=True, disposition=record["disposition"], output_sha256=sha(output))))


if __name__ == "__main__":
    main()
