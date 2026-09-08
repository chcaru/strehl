"""Saved refusal audit only: stdlib, byte hashes and metadata; no decode/import of subjects."""
import ast
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
OUT = HERE / "native-sensor-derivative-1"
PIN = "fb651f3b4aa5eeb891d6cef77e8719e13bb556ba086bd2dbd2add742d93505b8"
seen = {}


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=pairs,
                        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    def finite(value):
        if type(value) is float:
            assert math.isfinite(value)
        elif type(value) in (list, dict):
            for item in value.values() if type(value) is dict else value:
                finite(item)
    finite(result)
    return result


def path(value):
    value = Path(value)
    return (value if value.is_absolute() else ROOT / value).resolve()


def bind(value):
    p = path(value)
    before = p.stat()
    digest = hashlib.sha256()
    length = 0
    with p.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
            length += len(chunk)
    after = p.stat()
    assert (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
    result = dict(path=str(p), bytes=length, sha256=digest.hexdigest())
    assert str(p) not in seen or seen[str(p)] == result
    seen[str(p)] = result
    return result


def verify(ref):
    assert set(ref) == {"path", "bytes", "sha256"}
    assert type(ref["bytes"]) is int and ref["bytes"] > 0
    actual = bind(ref["path"])
    assert all(ref[k] == actual[k] for k in ("bytes", "sha256")), ref["path"]
    return actual


def read(value):
    if type(value) is dict:
        verify(value)
        value = value["path"]
    p = path(value)
    ref = bind(p)
    assert ref["bytes"] < 16 << 20
    raw = p.read_bytes()
    assert len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"]
    return strict(raw)


release = read(HERE / "native-sensor-derivative-release-1.json")
assert bind(HERE / "native-sensor-derivative-release-1.json")["sha256"] == PIN
assert len(release["source_bindings"]) == 146 and len(release["inputs"]) == 93
for name, ref in release["source_bindings"].items():
    verify(dict(path=name, **ref))
for ref in release["inputs"]:
    assert Path(ref["path"]).suffix.lower() not in (".arw", ".tiff", ".tif")
    verify(ref)
result = read(OUT / "result.json")
assert bind(OUT / "result.json")["sha256"] == "00ae754f28277c69196a55da5fff88c8c807de17f6c48123d73c8b3ee1a6eadb"
assert result["schema"] == "m193c-sensor-native-derivative-run-v1"
assert result["status"] == "REFUSED" and result["finalization_errors"] == []
assert "observed exact zero child exit" in result["error"]
assert result["execution_release"]["sha256"] == PIN
verify(result["execution_release"])
assert result["sources_before"] == result["sources_after"] == release["source_bindings"]
assert result["inputs_before"] == result["inputs_after"] == release["inputs"]
assert result["prior_work"] == release["prior_work"]
assert result["invocation"] == [PIN if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in release["commands"][0]]
assert len(result["rows"]) == 1 and result["attempted_original_index"] == 0
assert result["first_refusal"]["original_index"] == 0
assert result["first_refusal"]["stage"] == result["current_stage"] == "independent-child"
assert result["unvisited"] == [13, 26, 39, 52, 65, 78, 91, 104]
row = result["rows"][0]
assert row == read(OUT / "frame-00/frame-result.json")
assert row["ordinal"] == row["original_index"] == 0 and row["stage"] == "independent-child"
assert row["primary_reused"] is True and row["snapshot_retained_from_refused_run"] is True
assert row["snapshot_deleted"] is False and row["independent_read"] is None
old = read(release["reuse_first"]["result"])
historical = read(release["reuse_first"]["frame_result"])
assert old["status"] == "REFUSED" and historical == old["rows"][0]
assert old["unvisited"] == result["unvisited"]
assert result["originals_before"] == result["originals_after"] == old["originals_before"] == old["originals_after"]
assert [x["original_index"] for x in result["originals_before"]] == [0,13,26,39,52,65,78,91,104]
for original in result["originals_before"]:
    st = path(original["path"]).stat()  # Metadata only: do not reopen corpus RAW bytes.
    assert (st.st_size, st.st_mtime_ns, st.st_dev, st.st_ino, st.st_file_attributes) == (
        original["bytes"], original["mtime_ns"], original["device"], original["file_id"], original["attributes"])
assert row["reuse_provenance"] == dict(authority=release["reuse_first"], controls=result["reuse_controls"],
    primary_cpu_scope="historical; already charged in prior_work")
assert result["reuse_controls"] == [dict(id="reuse-full-plan-valid",passed=True),
    dict(id="reuse-later-entry-refused",passed=True,exception="full nine-plan byte/content equality"),
    dict(id="reuse-full-plan-restored",passed=True)]
for key in ("primary_receipt", "snapshot", "tiff", "primary_launch"):
    assert row[key] == historical[key]
for key in ("primary_receipt", "snapshot", "tiff"):
    verify(row[key])
assert row["primary_launch"] == read(release["reuse_first"]["primary_launch"])
verify(row["primary_launch"]["observation"]["log"])
primary = read(row["primary_receipt"])
fresh_plan, old_plan = read(result["input_plan"]), read(old["input_plan"])
assert fresh_plan == old_plan
assert all(result["input_plan"][k] == old["input_plan"][k] for k in ("bytes","sha256"))
request = read(row["read_request"])
assert request["schema"] == "m193c-sensor-native-derivative-read-request-v1"
assert request["execution_release"] == result["execution_release"]
assert request["input_plan"] == primary["input_plan"] == old["input_plan"]
assert request["original"] == old_plan["entries"][0]
for key in ("snapshot", "tiff", "primary_receipt"):
    assert request[key] == row[key]
for key in ("build", "reader_runtime"):
    verify(request[key])
reader_path = OUT / "frame-00/independent/result.json"
reader = read(reader_path)
assert bind(reader_path)["sha256"] == "58f4a7208a12a5a17913f1c048a54d106faa9a40e0ee3c849c83cbc71c962db7"
assert reader["schema"] == "m193c-sensor-native-derivative-independent-frame-v1"
assert reader["status"] == "REFUSED" and reader["finalization_errors"] == []
assert reader["error"].endswith("ValueError: scalar white disagrees\n")
assert reader["request"] == row["read_request"] and reader["original_index"] == 0
assert reader["tiff_pixel_sha256_u16_le"] is None
assert [x["id"] for x in reader["checks"]] == ["owned-sensor-copy","active-shape","local-rggb","active-u16-bytes","active-row-u16-bytes"]
assert all(x["pass"] is True for x in reader["checks"])
actual_rows = reader["checks"][4]["evidence"]["row_sha256_u16_le"]
assert len(actual_rows) == reader["checks"][4]["evidence"]["rows"] == 4688
assert actual_rows == primary["source"]["active_row_sha256_u16_le"]
assert all(type(x) is str and re.fullmatch("[0-9a-f]{64}",x) for x in actual_rows)
assert reader["active_sha256_u16_le"] == primary["source"]["active_sha256_u16_le"] == reader["checks"][3]["evidence"]["sha256"]
assert reader["checks"][3]["evidence"]["samples"] == 7032*4688
assert reader["checks"][1]["evidence"]["shape"] == [4688,7032]
metadata = reader["checks"][0]["evidence"]["independent_decoder_metadata"]
assert metadata["white"] == 16383 and metadata["channel_white"] == [15360]*4 and primary["source"]["white"] == 15360
older_reader = read(release["reuse_first"]["independent_refusal"])
older_metadata = older_reader["checks"][0]["evidence"]["independent_decoder_metadata"]
assert all(metadata[k] == older_metadata[k] for k in ("white","channel_white","black","wb"))
def validator(name):
    tree=ast.parse((HERE/name).read_bytes())
    return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="validate_independent_metadata"),include_attributes=False)
assert validator("independent-derivative-read.py") == validator("independent-sensor-derivative-read.py")
controls = reader["domain_controls"]
assert [x["id"] for x in controls] == ["sensor-nonzero-origin","visible-crop-null","wrong-offset-hash-refusal",
    "truncated-buffer-refusal","borrowed-sensor-refusal","late-copy-lifetime-destroyer","restored-sensor-copy","source-origin-cfa"]
assert all(set(x)=={"id","pass","evidence"} and x["pass"] is True for x in controls)
positive = controls[0]["evidence"]
for idx in (0,1,6):
    evidence=controls[idx]["evidence"]
    assert evidence["compared_after_poison"] is True
    assert evidence["full_sha256"] == positive["full_sha256"] and evidence["row_sha256"] == positive["row_sha256"]
    assert evidence["domain"]["sensor_domain"] == dict(x=4,y=2,width=8,height=6)
assert controls[1]["evidence"]["domain"]["visible_domain"] != positive["domain"]["visible_domain"]
for idx, wanted in ((2,"whole active u16 disagreement"),(3,"sensor ROI outside decoded buffer"),(4,"owned sensor copy inside lifetime")):
    assert controls[idx]["evidence"] == dict(exception=wanted,exception_type="ValueError",expected=wanted)
late=controls[5]["evidence"]
assert late["all_six_rows_changed"] is True and late["compared_after_poison"] is True
assert late["expected_sha256"] == positive["full_sha256"] != late["observed_sha256"]
assert controls[7]["evidence"] == dict(sensor_letters=["R","G","G","B"],sensor_origin=[4,2],
    wrong_visible_letters=["B","G","G","R"],wrong_visible_origin=[7,5])
launch=row["independent_launch"]
assert launch == read(OUT / "frame-00/independent-launch.json")
command=[row["read_request"]["sha256"] if x=="ACTUAL_FRAME_REQUEST_SHA256" else x for x in release["reader"]["commands"][0]]
assert launch["command"] == command == reader["invocation"]["orig_argv"]
assert reader["invocation"]["source_bindings"] == release["source_bindings"]
runtime=read(release["reader"]["runtime"])
assert reader["invocation"]["runtime"] == runtime
assert reader["invocation"]["thread_environment"] == {k:"2" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS")}
outer=read(HERE/"work/native-sensor-1-outer.json")
assert outer["command"] == result["invocation"] and outer["release_sha256"] == PIN
assert type(outer["exit_code"]) is int and outer["exit_code"] == 1 and outer["admissible_parent_exit"] is False
assert outer["dependency_error"] is None
supplements=[ref for ref in release["inputs"] if ref["sha256"]==outer["dependency_supplement_sha256"]]
assert len(supplements)==1
supplement=read(supplements[0])
assert supplement["runtime_sha256"] == release["reader"]["runtime"]["sha256"]
assert supplement["files"] == outer["dependency_before"] == outer["dependency_after"]
for ref in [runtime["python_executable"],*runtime["module_files"],*supplement["files"]]:
    verify(ref)
observation=launch["observation"]
assert observation["command"] == command and observation["exit_code"] == 1
assert observation["error"] is None and observation["cleanup_errors"] == []
assert all(observation[k] is True for k in ("direct_exit_observed","pipe_eof_observed","terminal_job_accounting"))
account=observation["job_accounting"]
assert account["active_processes"] == 0 and account["total_processes"] == 2 and account["total_terminated_processes"] == 0
assert account["total_cpu_100ns"] == account["total_user_100ns"]+account["total_kernel_100ns"] == 24843750
assert observation["post_exit_drain"]["completed"] is True and observation["post_exit_drain"]["last_accounting"] == account
assert observation["termination"] == dict(attempted=False,before_accounting=None,succeeded=False)
assert account["total_cpu_100ns"]/1e7 <= observation["limits"]["cpu_seconds"]
assert observation["wall_seconds"] <= observation["limits"]["wall_seconds"] == 240
assert observation["job_memory"]["peak_job_memory_used_bytes"] <= observation["limits"]["committed_bytes"] == 8<<30
verify(observation["log"])
assert observation["log_bytes"] == observation["log"]["bytes"] == 1492
child_final = strict(path(observation["log"]["path"]).read_bytes().splitlines()[-1])
assert child_final["error"] == reader["error"] and child_final["status"] == "REFUSED" and child_final["finalization_errors"] == []
assert path(child_final["result"]) == reader_path.resolve()
console=HERE/"work/native-sensor-1-console.txt"
bind(console)
final=strict(console.read_bytes().splitlines()[-1])
assert final["status"] == "REFUSED" and final["error"] == result["error"] and final["finalization_errors"] == []
assert path(final["result"]) == (OUT/"result.json").resolve()
exit_path=HERE/"work/native-sensor-1-exit.txt"
bind(exit_path)
assert exit_path.read_bytes()==b"1\r\n"
outputs=[bind(p) for p in sorted(OUT.rglob("*")) if p.is_file()]
assert len(outputs)==13 and all(Path(x["path"]).suffix.lower() not in (".arw",".tif",".tiff") for x in outputs)
assert not any((OUT/f"frame-{i:02d}").exists() for i in range(1,9))
for key in ("file_bytes","metadata_bytes"):
    assert final["work_through_final_checks"][key] == release["prior_work"][key]+sum(x["bytes"] for x in outputs)
assert final["work_through_final_checks"]["cpu_seconds"] == 43.46875
assert final["work_through_final_checks"]["cpu_seconds"] >= release["prior_work"]["cpu_seconds"]+account["total_cpu_100ns"]/1e7
for key,limit in (("cpu_seconds",1200),("wall_seconds",1800),("file_bytes",4<<30),("metadata_bytes",128<<20)):
    assert final["work_through_final_checks"][key] <= limit
for p in (OUT/"frame-00/independent/sources").iterdir():
    matching=[dict(path=k,**v) for k,v in release["source_bindings"].items() if p.name==v["sha256"][:16]+"-"+Path(k).name]
    assert len(matching)==1
    assert all(bind(p)[k]==matching[0][k] for k in ("bytes","sha256"))
names=list(release["source_bindings"])
listed=subprocess.run(["git","ls-tree","-r","--name-only","b7e0be39","--",*names],cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()
assert set(listed)==set(names)
assert not subprocess.run(["git","diff","--name-only","b7e0be39","--",*names],cwd=ROOT,capture_output=True,check=True).stdout
committed=subprocess.run(["git","show","b7e0be39:experiments/m193c-output-grid/native-sensor-derivative-release-1.json"],cwd=ROOT,capture_output=True,check=True).stdout
assert hashlib.sha256(committed).hexdigest()==PIN
print(json.dumps(dict(status="PASS_SAVED_SENSOR_REFUSAL_AUDIT",subject_status="REFUSED",sources=146,inputs=93,
    unique_hashed_files=len(seen),output_files=outputs,rows_compared=len(actual_rows),domain_controls=len(controls),
    native_checks=len(reader["checks"]),fresh_reader_jobs=1,fresh_primaries=0,
    global_white=metadata["white"],channel_white=metadata["channel_white"],primary_white=primary["source"]["white"],
    child_cpu_seconds=account["total_cpu_100ns"]/1e7,child_wall_seconds=observation["wall_seconds"],
    actual_final_work=final["work_through_final_checks"],prior_work=release["prior_work"],
    next_wall_seconds=release["prior_work"]["wall_seconds"]+outer["elapsed_wall_seconds"],
    outer_refs=[bind(p) for p in (console,exit_path,HERE/"work/native-sensor-1-outer.json")]),sort_keys=True))
