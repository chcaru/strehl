"""Prospective saved-outcome audit. Stdlib only; never imports subjects or decodes images.

Prepare and AST-check before the run. Execute only after externally supplied actual
release/result/root-observation pins exist. A verified refusal is not admission.
"""
import argparse
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
OUT = HERE / "native-sensor-white-artifact-derivative-1"
PREFIX = HERE / "work/native-sensor-white-artifact-1"
RELEASE = HERE / "native-sensor-white-artifact-derivative-release-1.json"
SUCCESS = "COMPLETE_NINE_SENSOR_WHITE_DERIVATIVES_AWAITING_COVERAGE"
READER_SUCCESS = "PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY"
INDICES = [0, 13, 26, 39, 52, 65, 78, 91, 104]
NATIVE_IDS = ["owned-sensor-copy", "active-shape", "local-rggb", "active-u16-bytes",
              "active-row-u16-bytes", "scalar-black-camera-white", "green-normalized-wb",
              "tiff-native-rgb16", "tiff-linear-camera-description", "tiff-full-pixel-read",
              "input-source-stability"]
DOMAIN_IDS = ["sensor-nonzero-origin", "visible-crop-null", "wrong-offset-hash-refusal",
              "truncated-buffer-refusal", "borrowed-sensor-refusal", "late-copy-lifetime-destroyer",
              "restored-sensor-copy", "source-origin-cfa"]
WHITE_IDS = ["camera-white-authority", "global-match-wrong-camera-refused",
             "mixed-used-camera-white-refused", "absent-camera-white-refused",
             "malformed-camera-white-refused", "malformed-global-white-refused",
             "malformed-cfa-index-refused", "native-black-regression-refused",
             "native-wb-regression-refused", "camera-white-restored"]
SNAPSHOT_NAMES = ["independent-sensor-white-derivative-read.py", "sensor-white-reader-preregister.md",
                  "sensor-domain-reader-preregister.md", "independent-derivative-tiff.py",
                  "independent-derivative-reader-preregister.md", "independent-rgb-tiff.py"]
ARTIFACT_IDS = ["artifact-extra-payload-refused", "artifact-altered-source-refused",
                "artifact-missing-source-refused", "artifact-restored"]
TEST = "merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native"
MIB = 1 << 20
seen = {}
control_anchor = None


def need(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def strict(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, "duplicate JSON key")
            out[key] = value
        return out
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    def finite(v):
        if type(v) is float:
            need(math.isfinite(v), "nonfinite JSON number")
        elif type(v) in (dict, list):
            for item in v.values() if type(v) is dict else v:
                finite(item)
    finite(value)
    return value


def exact(a, b):
    need(json.dumps(a, sort_keys=True, allow_nan=False) ==
         json.dumps(b, sort_keys=True, allow_nan=False), "exact typed JSON association")


def path(value):
    p = Path(value)
    return (p if p.is_absolute() else ROOT / p).resolve()


def ordinary(p):
    s = p.stat(follow_symlinks=False)
    need(stat.S_ISREG(s.st_mode) and not getattr(s, "st_file_attributes", 0) & 0x400,
         "ordinary non-reparse file: " + str(p))
    return s


def bind(value, cap=256*MIB):
    p = path(value)
    before = ordinary(p)
    need(0 <= before.st_size <= cap, "bounded file: " + str(p))
    h, count = hashlib.sha256(), 0
    with p.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        need((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), "opened identity")
        while chunk := stream.read(MIB):
            count += len(chunk)
            need(count <= cap, "file grew beyond bound")
            h.update(chunk)
    after = ordinary(p)
    fields = ("st_size", "st_mtime_ns", "st_dev", "st_ino", "st_nlink")
    need(all(getattr(before, k) == getattr(after, k) for k in fields) and count == before.st_size,
         "file changed while hashing")
    ref = dict(path=str(p), bytes=count, sha256=h.hexdigest())
    need(str(p) not in seen or seen[str(p)] == ref, "conflicting consumed file binding")
    seen[str(p)] = ref
    return ref


def ref_shape(ref):
    need(type(ref) is dict and set(ref) == {"path", "bytes", "sha256"} and
         type(ref["path"]) is str and integer(ref["bytes"], 1) and
         type(ref["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", ref["sha256"]), "typed FileRef")


def verify(ref, cap=256*MIB):
    ref_shape(ref)
    actual = bind(ref["path"], cap)
    need(all(ref[k] == actual[k] for k in ("bytes", "sha256")), "FileRef mismatch: " + ref["path"])
    return actual


def read(value, cap=16*MIB):
    ref = verify(value, cap) if type(value) is dict else bind(value, cap)
    with path(ref["path"]).open("rb") as stream:
        raw = stream.read(cap+1)
    need(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], "same JSON bytes")
    return strict(raw)


def pinned(p, sha, cap=16*MIB):
    need(type(sha) is str and re.fullmatch("[0-9a-f]{64}", sha), "external SHA format")
    ref = bind(p, cap)
    need(ref["sha256"] == sha, "external authority mismatch: " + str(p))
    return ref


def last_json(ref):
    p = path(verify(ref, 16*MIB)["path"])
    lines = p.read_bytes().splitlines()
    need(lines and lines[-1].strip(), "actual final stdout JSON")
    return strict(lines[-1])


def descendants(directory, cap=2000):
    files = []
    count = 0
    for base, dirs, names in os.walk(directory, followlinks=False):
        for name in dirs:
            p = Path(base)/name
            s = p.stat(follow_symlinks=False)
            need(stat.S_ISDIR(s.st_mode) and not getattr(s, "st_file_attributes", 0) & 0x400,
                 "ordinary directory")
        for name in names:
            files.append(Path(base)/name)
        count += len(dirs)+len(names)
        need(count <= cap, "bounded artifact population")
    return sorted(files), count


def snapshot_sources(release):
    expected = {}
    for name in SNAPSHOT_NAMES:
        folder = "m194g-larger-pupil" if name == "independent-rgb-tiff.py" else "m193c-output-grid"
        source = "experiments/"+folder+"/"+name
        ref = dict(path=source, **release["source_bindings"][source])
        verify(ref, 32*MIB)
        basename = ref["sha256"][:16]+"-"+name
        need(basename not in expected, "snapshot basename collision")
        expected[basename] = ref
    need(len(expected) == 6, "six snapshot sources")
    return expected


def reader_artifacts(directory, expected, cap, result_ref):
    need({p.name for p in directory.iterdir()} == {"result.json", "sources"}, "reader root population")
    need({p.name for p in (directory/"sources").iterdir()} == set(expected), "six exact source artifacts")
    files, count = descendants(directory, 256)
    need(count == 8 and len(files) == 7, "seven files/eight reader entries")
    identities = set()
    total = 0
    for p in files:
        s = ordinary(p)
        need(s.st_nlink == 1 and (s.st_dev, s.st_ino) not in identities, "reader hardlink/alias")
        identities.add((s.st_dev, s.st_ino))
        actual = bind(p, cap)
        total += actual["bytes"]
        target = result_ref if p.name == "result.json" else expected[p.name]
        need(all(actual[k] == target[k] for k in ("bytes", "sha256")), "reader artifact source/result bytes")
    need(total <= cap <= 4*MIB, "reader metadata allowance")
    return total


def artifact_controls(release, expected):
    ref = bind(OUT/"artifact-contract-controls.json", 65536)
    value = read(ref)
    need(set(value) == {"schema", "status", "checks", "files", "artifact_bytes", "error", "finalization_errors"},
         "artifact controls closed schema")
    need(value["schema"] == "m193c-native-artifact-controls-v1", "artifact controls schema")
    complete = value["status"] == "PASS_EXACT_READER_ARTIFACT_CONTRACT_ONLY"
    actual_files, _ = descendants(OUT/"artifact-contract-controls", 256)
    actual = {str(p.resolve()): bind(p, MIB) for p in actual_files}
    if not complete:
        need(value["status"] == "REFUSED" and (value["error"] or value["finalization_errors"]),
             "retained artifact-control refusal")
        return dict(file=ref, complete=False, groups=value["checks"], retained_files=len(actual),
                    artifact_bytes=sum(v["bytes"] for v in actual.values()))
    need(value["error"] is None and value["finalization_errors"] == [], "artifact control terminal")
    need([g["id"] for g in value["checks"]] == ARTIFACT_IDS and
         all(set(g) == {"id", "passed", "attempts"} and g["passed"] is True for g in value["checks"]),
         "four artifact groups")
    cases = [a for g in value["checks"] for a in g["attempts"]]
    need([a["case"] for a in cases] == ["extra", "nested", "altered", "missing", "restored"], "five artifact cases")
    messages = ["independent root artifact population", "independent source artifact population",
                "independent source snapshot bytes", "independent source artifact population"]
    for a, message in zip(cases[:4], messages, strict=True):
        exact(a, dict(case=a["case"], expected=message, exception_type="ValueError", exception=message, refused=True))
    restored = cases[4]
    need(set(restored) == {"case", "expected", "observed", "refused"} and
         restored["expected"] is None and restored["refused"] is False, "actual restored contract")
    expected_paths = set()
    ordered_sources = sorted(expected)
    for case in ("extra", "nested", "altered", "missing", "restored"):
        base = OUT/"artifact-contract-controls"/case
        fixture = base/"result.json"
        exact(read(fixture), dict(fixture_only=True, case=case))
        expected_paths.add(str(fixture.resolve()))
        for i, name in enumerate(ordered_sources):
            p = base/"sources"/name
            if case == "missing" and i == 5:
                need(not p.exists(), "actual missing sixth source")
                continue
            expected_paths.add(str(p.resolve()))
            actual_ref = bind(p, MIB)
            source = expected[name]
            if case == "altered" and i == 0:
                raw = path(source["path"]).read_bytes()
                changed = bytes([raw[0] ^ 1])+raw[1:]
                need(actual_ref["bytes"] == len(raw) and actual_ref["sha256"] == hashlib.sha256(changed).hexdigest()
                     != source["sha256"], "actual same-extent first-byte destroyer")
            else:
                need(all(actual_ref[k] == source[k] for k in ("sha256", "bytes")), "actual unchanged fixture source")
        for extra, payload in (("unexpected.py", b"not a released snapshot\n"),) if case == "extra" else (
                (("sources/nested/payload.json", b"{}\n"),) if case == "nested" else ()):
            p = base/extra
            expected_paths.add(str(p.resolve()))
            need(p.read_bytes() == payload, "literal unexpected artifact bytes")
    need(set(actual) == expected_paths and len(actual) == 36, "complete 36-file control population")
    need(len(value["files"]) == 36 and len({str(path(v["path"])) for v in value["files"]}) == 36,
         "complete unique control inventory")
    for recorded in value["files"]:
        need(verify(recorded, MIB) == actual[str(path(recorded["path"]))], "control actual inventory association")
    total = sum(v["bytes"] for v in actual.values())
    need(integer(value["artifact_bytes"]) and value["artifact_bytes"] == total <= MIB, "control byte accounting")
    observed = restored["observed"]
    need(set(observed) == {"entries", "file_count", "artifact_bytes", "files"} and
         type(observed["entries"]) is int and observed["entries"] == 8 and
         type(observed["file_count"]) is int and observed["file_count"] == 7, "restored actual return")
    restored_dir = OUT/"artifact-contract-controls/restored"
    restored_total = reader_artifacts(restored_dir, expected, MIB, bind(restored_dir/"result.json"))
    need(observed["artifact_bytes"] == restored_total and len(observed["files"]) == 7, "restored artifact extent")
    need([r["name"] for r in observed["files"]] == ["result.json"]+["sources/"+n for n in ordered_sources],
         "restored returned file order")
    for item in observed["files"]:
        need(set(item) == {"name", "file", "source"}, "restored returned ref schema")
        need(path(item["file"]["path"]) == (restored_dir/item["name"]).resolve(), "restored returned file association")
        verify(item["file"], MIB)
        source = None if item["name"] == "result.json" else expected[Path(item["name"]).name]["path"]
        need(item["source"] == source, "restored source provenance")
    return dict(file=ref, complete=True, groups=4, cases=5, retained_files=36, artifact_bytes=total)


def job(launch, command, expected_exit=None):
    need(launch["command"] == command, "actual launch argv")
    o = launch["observation"]
    need(o["command"] == command and type(o["exit_code"]) is int, "observed command/exit")
    if expected_exit is not None:
        need(o["exit_code"] == expected_exit, "expected actual child exit")
    need(o["terminal_job_accounting"] is True, "complete terminal Job CPU observation")
    a = o["job_accounting"]
    need(all(integer(a[k]) for k in ("active_processes", "total_processes", "total_terminated_processes",
         "total_cpu_100ns", "total_user_100ns", "total_kernel_100ns")), "typed Job counters")
    need(a["active_processes"] == 0 and a["total_cpu_100ns"] == a["total_user_100ns"]+a["total_kernel_100ns"],
         "terminal Job closure/CPU components")
    need(number(o["wall_seconds"]) and integer(o["job_memory"]["peak_job_memory_used_bytes"]), "actual Job resources")
    healthy = o["exit_code"] == 0 and o["error"] is None and o["cleanup_errors"] == []
    if healthy:
        need(o["direct_exit_observed"] is True and o["pipe_eof_observed"] is True and
             a["total_processes"] >= 1 and a["total_terminated_processes"] == 0, "normal complete process tree")
        need(o["post_exit_drain"]["completed"] is True and
             o["post_exit_drain"]["last_accounting"] == a, "successful Job drain")
        need(o["termination"] == dict(attempted=False, before_accounting=None, succeeded=False), "healthy no termination")
        need(a["total_cpu_100ns"]/1e7 <= o["limits"]["cpu_seconds"] and
             o["wall_seconds"] <= o["limits"]["wall_seconds"], "healthy original elapsed limits")
        need(o["job_memory"]["peak_job_memory_used_bytes"] <= o["limits"]["committed_bytes"], "healthy Job memory cap")
    verify(o["log"], 16*MIB)
    need(integer(o["log_bytes"]) and o["log_bytes"] == o["log"]["bytes"] <= 16*MIB, "actual complete log extent")
    need(o["limits"]["wall_seconds"] <= 240 and o["limits"]["committed_bytes"] == 8 << 30,
         "unchanged per-child resource ceiling")
    return dict(cpu_seconds=a["total_cpu_100ns"]/1e7, wall_seconds=o["wall_seconds"], healthy=healthy,
                exit_code=o["exit_code"], log=o["log"], accounting=a, error=o["error"], cleanup_errors=o["cleanup_errors"])


def checked_prefix(rows, ids):
    need(type(rows) is list and len(rows) <= len(ids), "bounded actual check prefix")
    for row, name in zip(rows, ids):
        need(row["id"] == name, "actual ordered check prefix")


def read_frame(row, ordinal, release, result, build, plan, old, expected):
    base = OUT/f"frame-{ordinal:02d}"
    need(integer(row["ordinal"]) and row["ordinal"] == ordinal and
         integer(row["original_index"]) and row["original_index"] == INDICES[ordinal], "typed original/local frame index")
    exact(row, read(base/"frame-result.json"))
    original = plan["entries"][ordinal]
    need(row["name"] == original["name"] and row["primary_reused"] is (ordinal == 0), "frame/reuse identity")
    completed = row["stage"] == "COMPLETE_FRAME_INDEPENDENTLY_READ" and row["error"] is None
    summary = dict(ordinal=ordinal, original_index=INDICES[ordinal], completed=completed, stage=row["stage"],
                   frame_result=bind(base/"frame-result.json"), fresh_primary_job=None, fresh_reader_job=None,
                   primary_receipt=row["primary_receipt"], independent_read=None, native_checks=0,
                   domain_controls=0, white_groups=0, white_calls=0, rows_compared=0,
                   snapshot=row["snapshot"], snapshot_deleted=row["snapshot_deleted"], tiff=row["tiff"], error=row["error"])
    if ordinal == 0:
        historical = old["rows"][0]
        need(row["reuse_provenance"] == dict(authority=release["reuse_first"], controls=result["reuse_controls"],
             primary_cpu_scope="historical; already charged in prior_work"), "historical CPU provenance")
        need(row["snapshot_retained_from_refused_run"] is True and row["snapshot_deleted"] is False, "retained old snapshot")
        for k in ("snapshot", "primary_launch"):
            need(row[k] == historical[k], "unchanged historical " + k)
        if row["primary_receipt"] is not None:
            need(row["primary_receipt"] == historical["primary_receipt"] and row["tiff"] == historical["tiff"],
                 "unchanged historical primary products")
    else:
        need(row["reuse_provenance"] is None and row["snapshot_retained_from_refused_run"] is False, "fresh primary provenance")
    if row["snapshot"] is not None:
        ref_shape(row["snapshot"])
        need(all(row["snapshot"][k] == original[k] for k in ("bytes", "sha256")), "snapshot planned byte identity")
        if ordinal:
            need(path(row["snapshot"]["path"]) == (base/original["name"]).resolve(), "fresh snapshot path")
        if row["snapshot_deleted"]:
            need(ordinal > 0 and completed and not path(row["snapshot"]["path"]).exists(), "only completed fresh snapshot deleted")
        else:
            verify(row["snapshot"], 64*MIB)  # Opaque retained snapshot hash; never decode.
    primary = None
    if row["primary_launch"] is not None:
        launch = row["primary_launch"]
        command = [str(path(build["test_executable"]["path"])), "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]
        observed = job(launch, command, 0 if row["primary_receipt"] is not None else None)
        if ordinal:
            exact(launch, read(base/"native-launch.json"))
            summary["fresh_primary_job"] = observed
        if observed["healthy"]:
            raw_log = path(launch["observation"]["log"]["path"]).read_text(encoding="utf8")
            need(len(re.findall(r"(?m)^test "+re.escape(TEST)+r" \.\.\. ok\r?$", raw_log)) == 1, "one actual named native test")
            matches = re.findall(r"(?m)^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured;", raw_log)
            need(matches == [("1", "0", "0", "0")], "one actual passed native test summary")
    if row["primary_receipt"] is not None:
        primary = read(row["primary_receipt"])
        need(primary["schema"] == "m193c-registration-derivative-v1" and
             primary["status"] == "COMPLETE_REGISTRATION_DERIVATIVE_UNVERIFIED" and primary["error"] is None and
             primary["finalization_errors"] == [], "complete primary receipt")
        plan_ref = old["input_plan"] if ordinal == 0 else result["input_plan"]
        need(primary["input_plan"] == plan_ref and primary["snapshot"] == row["snapshot"] and
             primary["output"] == row["tiff"] and type(primary["selected"]) is int and
             primary["selected"] == INDICES[ordinal], "primary selected payload/plan association")
        need(primary["command"] == row["primary_launch"]["command"] and
             primary["environment"] == row["primary_launch"]["environment"], "primary actual invocation")
        source = primary["source"]
        need(type(source["decode_calls"]) is int and source["decode_calls"] == 1 and
             type(source["live_frame_leases_after_prepare"]) is int and source["live_frame_leases_after_prepare"] == 0,
             "one primary decode and released owned frame")
        need(source["compiled_sources"] and all(release["source_bindings"][k]["sha256"] == v
             for k, v in source["compiled_sources"].items()), "actual compiled primary sources")
        verify(row["tiff"], 256*MIB)  # Hash entire TIFF as bytes, no image interpretation here.
    if row["read_request"] is not None:
        request = read(row["read_request"])
        need(request["schema"] == "m193c-sensor-white-native-derivative-read-request-v1" and
             request["execution_release"] == result["execution_release"] and request["original"] == original,
             "fresh request authority/original")
        need(primary is not None and request["input_plan"] == primary["input_plan"], "actual primary plan selected by request")
        for k in ("snapshot", "tiff", "primary_receipt"):
            need(request[k] == row[k], "reader actual file association " + k)
        for k, selected in (("build", release["build"]), ("reader_runtime", release["reader"]["runtime"])):
            need(verify(request[k]) == verify(selected), "request prerequisite identity")
        need(0 < request["limits"]["metadata_bytes"] <= 4*MIB and request["limits"]["committed_bytes"] == 8 << 30,
             "request inherited reader limits")
    if row["independent_launch"] is not None:
        command = [row["read_request"]["sha256"] if x == "ACTUAL_FRAME_REQUEST_SHA256" else x
                   for x in release["reader"]["commands"][ordinal]]
        launch = row["independent_launch"]
        exact(launch, read(base/"independent-launch.json"))
        summary["fresh_reader_job"] = job(launch, command)
        reader_path = base/"independent/result.json"
        if reader_path.exists():
            rr = bind(reader_path, 4*MIB)
            reader = read(rr)
            summary["independent_read"] = rr
            need(reader["schema"] == "m193c-sensor-white-native-derivative-independent-frame-v1" and
                 reader["request"] == row["read_request"] and type(reader["original_index"]) is int and
                 reader["original_index"] == INDICES[ordinal], "actual reader result/request/index")
            for k in ("snapshot", "tiff", "primary_receipt"):
                need(reader[k] == row[k], "reader final file association")
            invocation = reader["invocation"]
            if invocation:
                need(invocation["orig_argv"] == command and
                     invocation["source_bindings"] == release["source_bindings"], "actual fresh reader command/sources")
                need(invocation["runtime"] == read(release["reader"]["runtime"]) and
                     path(invocation["executable"]) == path(command[0]) and invocation["cwd"] == str(ROOT), "reader runtime/cwd")
                need(invocation["thread_environment"] == {k:"2" for k in
                     ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}, "reader thread environment")
                cache = next(x.split("=", 1)[1] for x in command if x.startswith("pycache_prefix="))
                exact(invocation["xoptions"], dict(faulthandler=True, pycache_prefix=cache))
            final = last_json(launch["observation"]["log"])
            need(final["status"] == reader["status"] and final["error"] == reader["error"] and
                 final["finalization_errors"] == reader["finalization_errors"] and path(final["result"]) == reader_path.resolve(),
                 "reader actual final stdout association")
            for key, ids in (("checks", NATIVE_IDS), ("domain_controls", DOMAIN_IDS), ("white_controls", WHITE_IDS)):
                checked_prefix(reader[key], ids)
            summary.update(reader_status=reader["status"], reader_error=reader["error"],
                           reader_finalization_errors=reader["finalization_errors"], native_checks=len(reader["checks"]),
                           domain_controls=len(reader["domain_controls"]), white_groups=len(reader["white_controls"]))
            if reader["status"] == READER_SUCCESS:
                need(reader["error"] is None and reader["finalization_errors"] == [] and
                     summary["fresh_reader_job"]["healthy"], "successful actual independent reader terminal")
                check_reader_evidence(reader, primary)
                summary["white_calls"] = 23
                summary["rows_compared"] = primary["source"]["active"]["height"]
                size = reader_artifacts(reader_path.parent, expected, request["limits"]["metadata_bytes"], rr)
                need(final["work_through_final_checks"]["artifact_bytes"] == size, "reader final artifact accounting")
                work = final["work_through_final_checks"]
                need(work["artifact_limit"] == request["limits"]["metadata_bytes"] and
                     work["cpu_seconds"] <= request["limits"]["cpu_seconds"] and
                     work["wall_seconds"] <= request["limits"]["wall_seconds"] and
                     work["owned_array_peak_bytes"] <= work["owned_array_limit"], "reader actual resource admission")
            else:
                need(reader["status"] == "REFUSED" and (reader["error"] or reader["finalization_errors"]), "retained reader refusal")
            if row["independent_read"] is not None:
                need(verify(row["independent_read"], 4*MIB) == rr, "parent consumed actual saved reader")
        else:
            need(not completed and row["independent_read"] is None, "no absent successful reader")
    if completed:
        need(summary.get("reader_status") == READER_SUCCESS and row["independent_read"] is not None and
             row["snapshot_deleted"] is (ordinal > 0), "all actual completed frame prerequisites")
    return summary


def check_reader_evidence(reader, primary):
    for key, ids in (("checks", NATIVE_IDS), ("domain_controls", DOMAIN_IDS), ("white_controls", WHITE_IDS)):
        need([r["id"] for r in reader[key]] == ids and all(set(r) == {"id", "pass", "evidence"} and
             r["pass"] is True for r in reader[key]), "complete actual "+key)
    source = primary["source"]
    active = source["active"]
    width, height = active["width"], active["height"]
    need(integer(width, 1) and integer(height, 1) and width*height <= 36_000_000, "bounded actual sensor dimensions")
    checks = reader["checks"]
    first = checks[0]["evidence"]
    need(first["owned"] is True and first["contiguous"] is True and first["compared_after_context"] is True and
         type(first["postprocess_calls"]) is int and first["postprocess_calls"] == 0, "actual owned live-domain copy")
    meta = first["independent_decoder_metadata"]
    need(checks[1]["evidence"]["shape"] == [height, width] and
         checks[1]["evidence"]["primary_padding"] == active, "sensor-domain dimensions")
    need(checks[2]["evidence"]["letters"] == ["R", "G", "G", "B"] and
         checks[2]["evidence"]["indices"] == meta["indices"], "actual local CFA")
    whole = source["active_sha256_u16_le"]
    need(reader["active_sha256_u16_le"] == whole == checks[3]["evidence"]["sha256"] and
         checks[3]["evidence"]["samples"] == width*height, "whole active hash association")
    rows = checks[4]["evidence"]
    need(type(rows["rows"]) is int and rows["rows"] == height and
         len(rows["row_sha256_u16_le"]) == height and rows["row_sha256_u16_le"] == source["active_row_sha256_u16_le"] and
         all(type(s) is str and re.fullmatch("[0-9a-f]{64}", s) for s in rows["row_sha256_u16_le"]), "every actual active row hash")
    agreement = checks[5]["evidence"]
    used = sorted(set(meta["indices"]))
    camera = meta["channel_white"]
    need(integer(meta["white"], 1) and meta["white"] <= 65535 and type(camera) is list and len(camera) == 4 and
         all(integer(x, 1) and x <= 65535 for x in camera), "actual typed white metadata")
    need(all(camera[i] == source["white"] for i in used) and len(set(camera[i] for i in used)) == 1,
         "actual camera-only white authority independent of generic agreement")
    exact(agreement["white_authority"], dict(method="m193c-camera-channel-white-v1", generic_white=meta["white"],
         camera_white=camera, used_cfa_indices=used, selected_white=camera[used[0]], primary_white=source["white"],
         generic_matches_selected=meta["white"] == camera[used[0]], selection="equal-positive-used-camera-channels",
         fallback="forbidden", physical_calibration_claim=False, primary_metadata_presence_claim=False))
    need(all(abs(meta["black"][i]-source["black"]) <= 1e-6 for i in used), "unchanged actual black agreement")
    selected = [meta["wb"][meta["indices"][i]] for i in (0, 1, 3)]
    normalized = [selected[0]/selected[1], 1.0, selected[2]/selected[1]]
    need(all(abs(a-b) <= 2**-20*max(1.0, abs(b)) for a,b in zip(normalized, source["wb_rgb"], strict=True)),
         "unchanged actual local-G1 WB comparison")
    need(checks[6]["evidence"]["actual"] == agreement["normalized_wb"] and
         checks[6]["evidence"]["primary"] == source["wb_rgb"], "actual WB evidence association")
    need(checks[7]["evidence"]["shape"] == [height,width,3] and checks[7]["evidence"]["endian"] in ("<", ">") and
         integer(checks[7]["evidence"]["strip_count"], 1), "actual complete RGB16 interpretation")
    need(checks[8]["evidence"]["software"] == "strehl 0.0.0", "unchanged writer Software")
    pixel_hash = reader["tiff_pixel_sha256_u16_le"]
    need(type(pixel_hash) is str and re.fullmatch("[0-9a-f]{64}", pixel_hash) and
         checks[9]["evidence"] == dict(consumed_pixel_bytes=width*height*6, sha256=pixel_hash), "actual whole RGB payload consumption")
    need(checks[10]["evidence"]["snapshot_rechecked"] is True and
         checks[10]["evidence"]["original_corpus_opened"] is False, "recorded read-only original scope")
    check_private_evidence(reader)


def check_private_evidence(reader):
    """Same frozen controls, checked against the independently audited literal records.

    This is a saved-evidence regression, not a new independent numerical oracle.
    The preceding audit explicitly inspected the eight domain records and all
    twenty-three camera-white calls, including matching-generic/wrong-camera.
    """
    global control_anchor
    if control_anchor is None:
        prior = HERE/"native-sensor-white-derivative-1/frame-00/independent/result.json"
        pinned(prior,"6ec2727b5d8e2b6f3c12c50434d7591735bb57af92339a751fb76d4aae11f3aa")
        pinned(HERE/"work/independent-native-sensor-white-1-audit.py",
               "db09546a781c33e3768d78dbe3fb820311cf32a81fade31df5c2da0356ea0961")
        pinned(HERE/"independent-native-sensor-white-1-read.md",
               "b2cbcbfd9d3bfdd5c66d6a90bdf7c1af4c45a07692b4d1a9bf75c67446e27467")
        control_anchor = read(prior)
        need(control_anchor["status"] == READER_SUCCESS, "historical control evidence scope")
    exact(reader["domain_controls"],control_anchor["domain_controls"])
    exact(reader["white_controls"],control_anchor["white_controls"])
    exact(reader["checks"][8]["evidence"],control_anchor["checks"][8]["evidence"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("release-sha256", "result-sha256", "outer-sha256", "console-sha256", "exit-sha256", "commit"):
        parser.add_argument("--"+name, required=True)
    args = parser.parse_args()
    need(not sys.flags.optimize and sys.dont_write_bytecode, "run audit with -B, without -O")
    external = dict(release=pinned(RELEASE,args.release_sha256), result=pinned(OUT/"result.json",args.result_sha256),
                    outer=pinned(str(PREFIX)+"-outer.json",args.outer_sha256),
                    console=pinned(str(PREFIX)+"-console.txt",args.console_sha256),
                    exit=pinned(str(PREFIX)+"-exit.txt",args.exit_sha256,64))
    release, result, outer = (read(external[k]) for k in ("release", "result", "outer"))
    need(release["schema"] == "m193c-sensor-white-native-derivative-release-v1" and
         release["scope"] == "sensor-white-native-nine", "released native-nine scope")
    for name, ref in release["source_bindings"].items():
        verify(dict(path=name, **ref),32*MIB)
    for ref in release["inputs"]:
        need(Path(ref["path"]).suffix.lower() not in (".arw", ".tif", ".tiff"), "metadata-only released inputs")
        verify(ref,64*MIB)
    command = [args.release_sha256 if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in release["commands"][0]]
    need(result["schema"] == "m193c-sensor-white-native-derivative-run-v1" and
         result["status"] in (SUCCESS,"REFUSED"), "actual outcome scope")
    need(result["invocation"] == outer["command"] == command and outer["release_sha256"] == args.release_sha256,
         "actual released root argv")
    need(verify(result["execution_release"]) == external["release"], "actual release FileRef")
    exact(result["sources_before"],release["source_bindings"])
    exact(result["sources_after"],release["source_bindings"])
    exact(result["inputs_before"],release["inputs"])
    exact(result["inputs_after"],release["inputs"])
    exact(result["prior_work"],release["prior_work"])
    need(result["build"] == release["build"] and result["private_admission"] == release["private_admission"], "upstream parent authority")
    build = read(release["build"])
    need(build["status"] == "COMPLETE_COMPILED_TESTS_ONLY" and build["error"] is None and
         build["finalization_errors"] == [] and build["sources_before"] == build["sources_after"], "frozen successful build closure")
    verify(build["test_executable"],64*MIB)
    need(all(release["source_bindings"][k] == v for k,v in build["sources_before"].items()), "compiled sources carried unchanged")
    expected = snapshot_sources(release)
    controls_path = OUT/"artifact-contract-controls.json"
    controls = artifact_controls(release,expected) if controls_path.exists() else dict(complete=False,file=None)
    old = read(release["reuse_first"]["result"])
    need(old["status"] == "REFUSED" and old["first_refusal"]["original_index"] == 0 and
         len(old["rows"]) == 1 and old["unvisited"] == INDICES[1:], "preserved original refusal authority")
    need(result["originals_before"] == result["originals_after"], "actual before/after original observations")
    originals = result["originals_before"]
    need([x["original_index"] for x in originals] == INDICES[:len(originals)], "ordered original observation prefix")
    for i, original in enumerate(originals):
        need(original == old["originals_before"][i] == old["originals_after"][i], "historical all-nine original identity")
        st = ordinary(path(original["path"]))  # Stat only; never reopen corpus RAW bytes.
        need((st.st_size,st.st_mtime_ns,st.st_dev,st.st_ino,st.st_file_attributes) ==
             (original["bytes"],original["mtime_ns"],original["device"],original["file_id"],original["attributes"]), "current corpus metadata unchanged")
    summaries = []
    if result["rows"]:
        need(len(originals) == 9 and controls["complete"], "controls and all-nine hashes precede any consumer")
        exact(result["reuse_controls"], [dict(id="reuse-full-plan-valid",passed=True),
              dict(id="reuse-later-entry-refused",passed=True,exception="full nine-plan byte/content equality"),
              dict(id="reuse-full-plan-restored",passed=True)])
        plan = read(result["input_plan"])
        exact(plan,read(old["input_plan"]))
        need(all(result["input_plan"][k] == old["input_plan"][k] for k in ("bytes","sha256")), "all-nine canonical plan byte equality")
        need([e["original_index"] for e in plan["entries"]] == INDICES, "exact nine plan entries")
        need(len(result["rows"]) <= 9, "bounded row population")
        for ordinal,row in enumerate(result["rows"]):
            summaries.append(read_frame(row,ordinal,release,result,build,plan,old,expected))
        need(all(r["completed"] for r in summaries[:-1]), "stop at first row refusal")
    complete = result["status"] == SUCCESS
    if complete:
        need(len(summaries) == 9 and all(r["completed"] for r in summaries) and result["unvisited"] == [] and
             result["first_refusal"] is None and result["attempted_original_index"] is None and
             result["error"] is None and result["finalization_errors"] == [], "complete nine-frame terminal")
    else:
        need(type(result["first_refusal"]) is dict and (result["error"] or result["finalization_errors"]), "explicit retained first refusal")
        if summaries:
            need(result["unvisited"] == INDICES[len(summaries):], "exact unvisited post-refusal suffix")
            if not summaries[-1]["completed"]:
                need(result["first_refusal"]["original_index"] == summaries[-1]["original_index"] and
                     result["first_refusal"]["stage"] == summaries[-1]["stage"] == result["current_stage"], "actual first row refusal location")
                need(summaries[-1]["error"] in result["error"], "original row traceback retained by parent")
    for ordinal in range(len(summaries),9):
        need(not (OUT/f"frame-{ordinal:02d}").exists(), "no unvisited frame output directory")
    primary_jobs = [r["fresh_primary_job"] for r in summaries if r["fresh_primary_job"] is not None]
    reader_jobs = [r["fresh_reader_job"] for r in summaries if r["fresh_reader_job"] is not None]
    if complete:
        need(len(primary_jobs) == 8 and len(reader_jobs) == 9, "17 fresh Jobs; historical primary excluded")
    need(type(outer["exit_code"]) is int and outer["exit_code"] == (0 if complete else 1) and
         outer["admissible_parent_exit"] is complete and outer["dependency_error"] is None, "actual root OS disposition")
    need(path(external["exit"]["path"]).read_bytes().strip() == str(outer["exit_code"]).encode(), "actual synchronous root exit")
    supplements = [r for r in release["inputs"] if r["sha256"] == outer["dependency_supplement_sha256"]]
    need(len(supplements) == 1, "unique actual adjacent dependency authority")
    supplement = read(supplements[0])
    runtime = read(release["reader"]["runtime"])
    need(supplement["runtime_sha256"] == release["reader"]["runtime"]["sha256"] and
         supplement["files"] == outer["dependency_before"] == outer["dependency_after"], "actual adjacent DLL endpoints")
    for ref in [runtime["python_executable"],*runtime["module_files"],*supplement["files"]]:
        verify(ref,64*MIB)
    final = last_json(external["console"])
    need(final["status"] == result["status"] and final["error"] == result["error"] and
         final["finalization_errors"] == result["finalization_errors"] and path(final["result"]) == OUT/"result.json",
         "actual final stdout/result association")
    current_files,_ = descendants(OUT)
    outputs = [bind(p,256*MIB) for p in current_files]
    deleted = [r["snapshot"] for r in summaries if r["snapshot_deleted"]]
    retained_bytes = sum(r["bytes"] for r in outputs)
    binary_bytes = sum(r["bytes"] for r in outputs if Path(r["path"]).suffix.lower() in (".arw", ".tiff"))
    final_work = final["work_through_final_checks"]
    file_lower = release["prior_work"]["file_bytes"]+retained_bytes+sum(r["bytes"] for r in deleted)
    metadata_lower = release["prior_work"]["metadata_bytes"]+retained_bytes-binary_bytes
    # On ordinary complete publication these are exact extents, not cumulative write I/O.
    # Failed publication can retain renamed maximum extents in the parent's ledger.
    need(final_work["file_bytes"] >= file_lower and final_work["metadata_bytes"] >= metadata_lower, "no forgotten deleted snapshot/metadata bytes")
    if complete:
        need(final_work["file_bytes"] == file_lower and final_work["metadata_bytes"] == metadata_lower, "exact complete extent carry")
    child_cpu = sum(j["cpu_seconds"] for j in primary_jobs+reader_jobs)
    need(final_work["cpu_seconds"] >= release["prior_work"]["cpu_seconds"]+child_cpu, "all fresh Job CPU charged once")
    if complete:
        for key,limit in (("cpu_seconds",1200),("wall_seconds",1800),("file_bytes",4<<30),("metadata_bytes",128*MIB)):
            need(number(final_work[key]) and final_work[key] <= limit, "complete admitted global "+key)
    need(number(outer["elapsed_wall_seconds"]), "actual outer elapsed")
    next_wall = Decimal(str(release["prior_work"]["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"]))
    names = list(release["source_bindings"])
    listed = subprocess.run(["git","ls-tree","-r","--name-only",args.commit,"--",*names],cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()
    need(set(listed) == set(names), "all sources committed before execution")
    need(not subprocess.run(["git","diff","--name-only",args.commit,"--",*names],cwd=ROOT,capture_output=True,check=True).stdout,
         "released sources unchanged from committed revision")
    committed = subprocess.run(["git","show",args.commit+":"+RELEASE.relative_to(ROOT).as_posix()],cwd=ROOT,capture_output=True,check=True).stdout
    need(hashlib.sha256(committed).hexdigest() == args.release_sha256, "committed actual release bytes")
    for frame in summaries:
        for label,filename in (("fresh_primary_job","native-launch.json"),("fresh_reader_job","independent-launch.json")):
            if frame[label] is not None:
                observed = frame[label]
                frame[label] = {k:observed[k] for k in ("cpu_seconds","wall_seconds","healthy","exit_code")}
                frame[label]["launch"] = bind(OUT/f"frame-{frame['ordinal']:02d}"/filename)
    inventory_bytes = json.dumps(outputs,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    receipt = dict(schema="m193c-saved-sensor-white-artifact-audit-v1",status="PASS_SAVED_SENSOR_WHITE_ARTIFACT_OUTCOME_AUDIT",
                   subject_status=result["status"],subject_complete=complete,external=external,commit=args.commit,
                   audit_source=bind(__file__,MIB),invocation=sys.orig_argv,source_count=len(names),input_count=len(release["inputs"]),
                   artifact_controls=controls,frames=summaries,first_refusal=result["first_refusal"],unvisited=result["unvisited"],
                   fresh_primary_jobs=len(primary_jobs),fresh_reader_jobs=len(reader_jobs),fresh_child_cpu_seconds=child_cpu,
                   deleted_snapshots=deleted,output_inventory=dict(files=len(outputs),sha256=hashlib.sha256(inventory_bytes).hexdigest()),
                   actual_final_work=final_work,prior_work=release["prior_work"],
                   retained_output_bytes=retained_bytes,retained_binary_bytes=binary_bytes,
                   extent_lower_bounds=dict(file_bytes=file_lower,metadata_bytes=metadata_lower),
                   next_wall_seconds=str(next_wall),unique_hashed_files=len(seen),
                   scope="Saved bytes and actual process/consumer evidence only; no RAW/TIFF decode, coverage, physical-domain or common-TIFF qualification")
    raw = json.dumps(receipt,sort_keys=True,separators=(",",":"),allow_nan=False)
    need(len(raw.encode()) <= 40*1024,"bounded audit stdout receipt")
    print(raw,flush=True)


if __name__ == "__main__":
    main()
