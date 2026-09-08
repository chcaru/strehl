"""Single saved-record audit; standard library only, no image decoding."""
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
OUT = HERE / "active-domain-probe-1"
PIN = "b540b3dd8d88587a87a98e5347c579221bc46dd40f014ddd7e0e70de17452538"
seen = {}


def strict(raw):
    def pairs(items):
        value = {}
        for key, child in items:
            assert key not in value, key
            value[key] = child
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    def finite(x):
        if type(x) is float:
            assert math.isfinite(x)
        elif type(x) in (dict, list):
            for child in x.values() if type(x) is dict else x:
                finite(child)
    finite(value)
    return value


def path(value):
    result = Path(value)
    return (result if result.is_absolute() else ROOT / result).resolve()


def bind(value):
    p = path(value)
    before = p.stat()
    digest = hashlib.sha256()
    length = 0
    with p.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            length += len(chunk)
            digest.update(chunk)
    after = p.stat()
    assert (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
    result = dict(path=str(p), sha256=digest.hexdigest(), bytes=length)
    assert str(p) not in seen or seen[str(p)] == result
    seen[str(p)] = result
    return result


def verify(ref):
    assert set(ref) == {"path", "sha256", "bytes"}
    assert type(ref["bytes"]) is int and ref["bytes"] > 0
    actual = bind(ref["path"])
    assert all(actual[k] == ref[k] for k in ("sha256", "bytes")), ref["path"]
    return actual


def read(p):
    p = path(p)
    ref = bind(p)
    raw = p.read_bytes()
    assert len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"]
    return strict(raw)


release = read(HERE / "active-domain-probe-release-1.json")
assert bind(HERE / "active-domain-probe-release-1.json")["sha256"] == PIN
assert len(release["sources"]) == 142 and len(release["inputs"]) == 73
for name, ref in release["sources"].items():
    verify(dict(path=name, **ref))
for ref in release["inputs"]:
    verify(ref)
for key in ("runtime", "adjacent", "primary", "snapshot"):
    verify(release[key])
result = read(OUT / "result.json")
assert bind(OUT / "result.json")["sha256"] == "78330bd2c6f83ff9791fdd3406679ea1e7cd766d1968375e0a418f2185ef688e"
verify(result["evidence"])
worker = read(result["evidence"]["path"])
assert result["evidence"]["sha256"] == "1031e0bee6bec02473981911634857a700cc59f414d575cd18c7ff9a9b9cb03c"
for item, role in ((result, "parent"), (worker, "worker")):
    assert item["status"] == "COMPLETE_DIAGNOSTIC_ONLY" and item["error"] is None and item["finalization_errors"] == []
    assert item["cpu_accounting_complete"] is True
    verify(item["execution_release"])
    assert item["execution_release"]["sha256"] == PIN
    assert item["command"] == [PIN if x == "ACTUAL_RELEASE_SHA256" else x for x in release["commands"][role]]

evidence = worker["evidence"]
primary = read(release["primary"]["path"])
assert evidence["primary"] == release["primary"] and evidence["snapshot"] == release["snapshot"]
assert path(primary["snapshot"]["path"]) == path(release["snapshot"]["path"])
assert all(primary["snapshot"][k] == release["snapshot"][k] for k in ("sha256", "bytes"))
assert primary["selected"] == evidence["original_index"] == 0
assert evidence["candidate_domain"] == primary["source"]["active"] == dict(x=0, y=0, width=7032, height=4688)
assert evidence["independent_sizes"] == dict(flip=0, height=4688, width=7028, raw_height=5120, raw_width=7168, top_margin=0, left_margin=0)
assert evidence["copied_inside_context"] is True and evidence["owned_array_bytes"] == 65932032
assert evidence["postprocess_calls"] == 0
actual_rows, expected_rows = evidence["row_sha256_u16_le"], primary["source"]["active_row_sha256_u16_le"]
assert len(actual_rows) == len(expected_rows) == 4688
assert all(type(x) is str and re.fullmatch("[0-9a-f]{64}", x) for x in actual_rows + expected_rows)
assert actual_rows == expected_rows and evidence["mismatch_rows"] == []
assert evidence["candidate_sha256_u16_le"] == evidence["primary_sha256_u16_le"] == primary["source"]["active_sha256_u16_le"]
assert evidence["whole_domain_matches"] is True
assert evidence["common_visible_sha256"] == evidence["candidate_common_sha256"]
assert evidence["changed_code_detected"] is True and evidence["restored_code_matches"] is True
assert [x["x"] for x in evidence["disputed_columns"]] == list(range(7028, 7032))
assert all(x["samples"] == 4688 and x["zero_count"] == 0 and 0 < x["minimum"] <= x["maximum"] <= 65535 for x in evidence["disputed_columns"])

observation = result["observation"]
assert observation["command"] == worker["command"] and observation["exit_code"] == 0
assert observation["error"] is None and observation["cleanup_errors"] == []
assert all(observation[x] is True for x in ("terminal_job_accounting", "direct_exit_observed", "pipe_eof_observed"))
account = observation["job_accounting"]
assert account["active_processes"] == 0
assert account["total_cpu_100ns"] == account["total_user_100ns"] + account["total_kernel_100ns"]
assert observation["limits"] == dict(cpu_seconds=30, wall_seconds=60, committed_bytes=2 << 30, log_bytes=1 << 20)
assert account["total_cpu_100ns"] / 1e7 <= 30 and observation["wall_seconds"] <= 60
assert observation["job_memory"]["peak_job_memory_used_bytes"] <= 2 << 30
assert observation["post_exit_drain"]["completed"] is True
assert observation["post_exit_drain"]["last_accounting"] == account
assert observation["termination"] == dict(attempted=False, before_accounting=None, succeeded=False)
verify(observation["log"])
assert observation["log_bytes"] == observation["log"]["bytes"]

outer = read(HERE / "work/active-domain-probe-1-outer.json")
assert outer["command"] == result["command"] and outer["release_sha256"] == PIN and outer["exit_code"] == 0
assert (HERE / "work/active-domain-probe-1-exit.txt").read_bytes().strip() == b"0"
console = HERE / "work/active-domain-probe-1-console.txt"
bind(console)
final = strict(console.read_bytes().splitlines()[-1])
child_final = strict(path(observation["log"]["path"]).read_bytes().splitlines()[-1])
for last, p in ((final, OUT / "result.json"), (child_final, OUT / "worker.json")):
    assert last["status"] == "COMPLETE_DIAGNOSTIC_ONLY" and last["error"] is None and last["finalization_errors"] == []
    assert last["cpu_accounting_complete"] is True and path(last["result"]) == p.resolve()
    assert all(last["work_through_final_checks"][k] >= release["prior_work"][k] for k in release["prior_work"])
files = [bind(p) for p in sorted(OUT.rglob("*")) if p.is_file()]
assert {Path(x["path"]).name for x in files} == {"result.json", "worker.json", "worker.log"}
for key in ("file_bytes", "metadata_bytes"):
    assert final["work_through_final_checks"][key] == release["prior_work"][key] + sum(x["bytes"] for x in files)
for key, limit in (("cpu_seconds", 1200), ("wall_seconds", 1800), ("file_bytes", 4 << 30), ("metadata_bytes", 128 << 20)):
    assert final["work_through_final_checks"][key] <= limit

runtime = read(release["runtime"]["path"])
extra = read(release["adjacent"]["path"])
assert extra["runtime_sha256"] == release["runtime"]["sha256"]
for ref in [runtime["python_executable"], *runtime["module_files"], *extra["files"]]:
    verify(ref)
assert path(runtime["python_executable"]["path"]) == path(result["command"][0])
native = read(HERE / "native-derivative-1/result.json")
assert native["status"] == "REFUSED" and native["first_refusal"] is not None
reservation = read(HERE / "work/active-domain-probe-1-reservation.json")
assert sum(x["bytes"] for x in reservation["files"]) == reservation["observed_bytes"]
assert reservation["observed_bytes"] + reservation["release_upper_bytes"] < reservation["reserved_bytes"] == 1 << 20

names = list(release["sources"])
listed = subprocess.run(["git", "ls-tree", "-r", "--name-only", "3b10e8ff", "--", *names], cwd=ROOT, capture_output=True, check=True).stdout.decode().splitlines()
assert set(listed) == set(names)
changed = subprocess.run(["git", "diff", "--name-only", "3b10e8ff", "--", *names], cwd=ROOT, capture_output=True, check=True).stdout
assert not changed, changed
committed = subprocess.run(["git", "show", "3b10e8ff:experiments/m193c-output-grid/active-domain-probe-release-1.json"], cwd=ROOT, capture_output=True, check=True).stdout
assert hashlib.sha256(committed).hexdigest() == PIN
for p in (HERE / "work/active-domain-probe-1-exit.txt",):
    bind(p)
print(json.dumps(dict(status="PASS_SAVED_PROBE_RECORD_AUDIT", source_count=len(names), input_count=len(release["inputs"]),
    unique_hashed_files=len(seen), rows_compared=len(actual_rows), output_files=files,
    actual_final_work=final["work_through_final_checks"], prior_work=release["prior_work"],
    child_cpu_seconds=account["total_cpu_100ns"]/1e7,
    next_wall_seconds=release["prior_work"]["wall_seconds"]+outer["elapsed_wall_seconds"],
    columns=evidence["disputed_columns"], runtime_versions={k:runtime[k] for k in ("python_version","numpy_version","rawpy_version","libraw_version")},
    outer_refs=[seen[str(p.resolve())] for p in (console,HERE/"work/active-domain-probe-1-exit.txt",HERE/"work/active-domain-probe-1-outer.json")]), sort_keys=True))
