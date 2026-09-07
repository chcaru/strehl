"""Read actual stopped profile evidence; execute only source-extracted input/reader helpers."""
import ast
from dataclasses import asdict
from datetime import datetime
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PINS = {
    "counter-profile-off-1/result.json": "c4d3298dd64df03f092e5904b3dbf08c6ebbb8284f5e7ddb5e142d0193f75762",
    "counter-profile-count-1/result.json": "d80f9f77b9bcb415eee5c423c30b4f114b6ecaaec6fcadc478bc7f7994c78bea",
    "counter-profile.py": "fc1dd81cf3c6dbccdb46830dcffb98a91b21f05f2a89089d9f40c85f253d0020",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def check_ref(ref):
    path = Path(ref["path"])
    if not path.is_absolute():
        path = ROOT / path
    assert sha(path) == ref["sha256"] and path.stat().st_size == ref["bytes"]
    return path


def main():
    for name, digest in PINS.items():
        assert sha(HERE / name) == digest
    off, failed = [read(HERE / name) for name in list(PINS)[:2]]
    release = read(HERE / "counter-profile-release-1.json")
    assert off["status"] == "PASS_PROFILE_MODE" and off["mode"] == "off"
    assert failed["status"] == "UNCOMMISSIONED_PROFILE" and failed["mode"] == "count"
    assert off["sources_before"] == off["sources_after"] == failed["sources_before"] == failed["sources_after"]
    for directory, record in (("counter-profile-off-1", off), ("counter-profile-count-1", failed)):
        assert len(record["sources_before"]) == 7
        for ref in record["sources_before"].values():
            path = check_ref(ref)
            assert path.read_bytes() == (HERE / directory / "source" / path.name).read_bytes()
        assert record["actual_imports"]["counter"] == record["sources_before"][str(HERE / "preflight.py")]
        assert record["actual_imports"]["geometry"] == record["sources_before"][str(HERE / "geometry.py")]
        assert record["actual_imports"]["loader_sha256"] == record["sources_before"][str(HERE / "pinned-loader.py")]["sha256"]
        for ref in record["actual_imports"]["frozen"].values():
            check_ref(ref)
        command = next(row["argv"] for row in release["commands"] if row["mode"] == record["mode"])
        suffix = [PINS["counter-profile-off-1/result.json"] if v == "ACTUAL_COMPLETED_OFF_RESULT_SHA256" else v for v in command[1:]]
        assert record["invocation"]["orig_argv"][1:] == suffix
    commit = "25a223f639b642b56b2d0c716ebe0abc54dca0aa"
    for ref in release["files"]:
        check_ref(ref)
        raw = subprocess.check_output(["git", "show", commit + ":" + ref["path"]], cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest() == ref["sha256"] and len(raw) == ref["bytes"]
    commit_time = subprocess.check_output(["git", "show", "-s", "--format=%cI", commit], cwd=ROOT, text=True).strip()
    assert datetime.fromisoformat(commit_time) < datetime.fromisoformat(off["started_utc"])
    assert datetime.fromisoformat(off["ended_utc"]) < datetime.fromisoformat(failed["started_utc"])
    payload_path = check_ref(off["payload"])
    payload = read(payload_path)
    assert payload_path.read_bytes() == (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    actual = off["count"]
    expected_pairs = [(arm, i) for arm in ("primary", "angle-refined", "cell-refined") for i in range(5)]
    assert [(r["arm"], r["frame_index"]) for r in actual["frames"]] == expected_pairs
    assert actual["completed_frames"] == 15 and actual["completed_cells"] == 810
    assert all(r["status"] == "complete" and r["visited_cells"] == 54 and r["last_coordinate"] == [8, 5] for r in actual["frames"])
    oracle = read(HERE / "independent-preflight-3/private-reference.json")
    independent_actual = read(HERE / "independent-preflight-3/private-actual.json")
    assert actual["ordered_stream_sha256"] == independent_actual["ordered_stream_sha256"]
    for row, reference in zip(actual["frames"], oracle, strict=True):
        normalized = dict(arm=row["arm"], index=row["frame_index"], visited=row["visited_cells"],
                          branches=row["branches"], roots=row["roots"], low_points=row["low_points"],
                          high_points=row["high_points"], nodes=row["angular_nodes"], max_intervals=row["maximum_intervals"])
        assert normalized == reference
        f = Fraction.from_float((.5, .75, 1., 1.25, 1.5)[row["frame_index"]])
        radius2 = (2 * (f - 1)) ** 2 * Fraction(17, 64)
        branches = dict(foreground=0, background=0, numerical=0)
        for y in range(6):
            for x in range(9):
                h = Fraction(x, 2) + Fraction(y, 8) - Fraction(75, 32)
                gap = abs(h) - Fraction(5, 16)
                branch = ("foreground" if h > 0 else "background") if gap > 0 and gap * gap > radius2 else "numerical"
                branches[branch] += 1
        assert row["branches"] == branches
    assert payload["frames"] == actual["frames"] and payload["inputs"] == off["inputs"]
    assert payload["total_points"] == off["work"]["total_points"] == 167040
    assert payload["total_angular_nodes"] == off["work"]["total_angular_nodes"] == 39819840
    assert len(off["checks"]) == 11 and all(row["passed"] is True for row in off["checks"])
    assert off["profiler"] == dict(constructed=False, collection_enabled=False)
    assert len(off["radiance_traps"]) == 7 and all(v == dict(intentional_calls=1, genuine_calls=0) for v in off["radiance_traps"].values())
    assert failed["checks"] == [] and "count" not in failed and "profiler" not in failed
    assert all(failed["work"][key] == 0 for key in ("frame_count", "total_points", "total_angular_nodes"))
    assert not (HERE / "counter-profile-placebo-1").exists() and not (HERE / "counter-profile-mutated-cut-1").exists()

    # Extract only constructors and reader helpers. Never execute run/load_counter/count_geometry.
    source = (HERE / "counter-profile.py").read_bytes()
    tree = ast.parse(source)
    wanted = {"make_inputs", "baseline_payload", "read_bound", "canonical"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    assert {node.name for node in functions} == wanted
    helper_globals = dict(Path=Path, hashlib=hashlib, json=json, asdict=asdict,
                          ARMS=("primary", "angle-refined", "cell-refined"), PROTOCOL_SHA=off["protocol"]["sha256"])
    exec(compile(ast.Module(body=functions, type_ignores=[]), "<source-extracted-profile-input-reader-only>", "exec"), helper_globals)
    model_ref = off["actual_imports"]["frozen"]["model.py"]
    model_path = check_ref(model_ref)
    model = types.ModuleType("m194g_independent_representation_model")
    model.__file__ = str(model_path)
    sys.modules[model.__name__] = model
    exec(compile(model_path.read_bytes(), str(model_path), "exec"), model.__dict__)
    _, _, live = helper_globals["make_inputs"](model)
    canonical_live = helper_globals["canonical"](live)
    assert off["inputs"] == failed["inputs"] == json.loads(canonical_live)
    assert live != off["inputs"] and isinstance(live["scene"]["depths"], tuple)
    assert isinstance(off["inputs"]["scene"]["depths"], list)
    predicate_values = dict(schema=off["schema"] == "m194g-counter-profile-v1", status=off["status"] == "PASS_PROFILE_MODE",
                            mode=off["mode"] == "off", sources_before=off["sources_before"] == failed["sources_before"],
                            sources_after=off["sources_after"] == failed["sources_before"],
                            inputs=off["inputs"] == live, protocol=off["protocol"]["sha256"] == helper_globals["PROTOCOL_SHA"])
    assert [k for k, v in predicate_values.items() if not v] == ["inputs"]
    baseline_args = (HERE / "counter-profile-off-1/result.json", PINS["counter-profile-off-1/result.json"], failed["sources_before"])
    try:
        helper_globals["baseline_payload"](*baseline_args, live)
    except ValueError as error:
        refusal = repr(error)
    else:
        raise AssertionError("actual reader must reproduce the recorded refusal")
    assert refusal == failed["error"]
    returned_bytes, _, _ = helper_globals["baseline_payload"](*baseline_args, json.loads(canonical_live))
    assert returned_bytes == payload_path.read_bytes()
    changed = json.loads(canonical_live)
    changed["frames"][-1]["inverse_focus"] = 1.625
    try:
        helper_globals["baseline_payload"](*baseline_args, changed)
    except ValueError:
        changed_input_refused = True
    else:
        raise AssertionError("numeric input destroyer must still refuse")
    tuple_paths = []
    def tuples(value, prefix="inputs"):
        if isinstance(value, tuple):
            tuple_paths.append(prefix)
        if isinstance(value, dict):
            for k, v in value.items(): tuples(v, prefix + "." + k)
        elif isinstance(value, (tuple, list)):
            for i, v in enumerate(value): tuples(v, prefix + "[" + str(i) + "]")
    tuples(live)
    for name, digest in PINS.items():
        assert sha(HERE / name) == digest
    output = HERE / "independent-profile-1-read.json"
    assert not output.exists()
    record = dict(schema="m194g-independent-stopped-profile-read-v1", evidence_consistent=True,
                  disposition="off population valid; count receipt comparison defective; profiling uncommissioned",
                  command=sys.orig_argv, reader_sha256=sha(Path(__file__)), bound_results=PINS,
                  source_commit=commit, commit_time=commit_time, off_payload_sha256=sha(payload_path),
                  complete_off_rows=15, complete_off_cells=810, off_points=167040, off_nominal_nodes=39819840,
                  off_geometry_digest=actual["ordered_stream_sha256"], branch_oracle="independent exact dyadic predicate plus retained private reference",
                  refusal=refusal, baseline_predicates=predicate_values, tuple_paths=tuple_paths,
                  json_only_normalized_companion_passes=True, numeric_changed_input_refuses=changed_input_refused,
                  live_constructor_json_matches_both_actual_input_records=True,
                  no_counter_or_mode_rerun=True, no_profiler_constructed_or_executed=True,
                  author_frozen_sources_unchanged=True, off_work=off["work"], failed_work=failed["work"])
    output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(dict(evidence_consistent=True, output_sha256=sha(output), reason="tuple/list baseline defect; no profile obtained")))


if __name__ == "__main__":
    main()
