"""Metadata-only coverage release preparation; SOURCE ONLY until root freezes argv.

Never imports a subject, starts a process, or opens a RAW/TIFF/array payload.
Requires actual completed nine-input native authority and its independent audit.
The root four-field carry must include the nonrefundable 30 CPU /60 wall /2 MiB
preparation allowance, inside the original global limits. The separate coverage
snapshot reservation remains exactly sum(nine TIFF extents)+5 MiB, with no refund.

Successor to immutable db33e171 after its actual same-buffer-identity refusal.
The historical predicate did not identify a changed stat field: access time is
not asserted to be the historical cause. Stable identity here means device,
inode, extent, modification time and Windows attributes, plus the actual opened
file identity and the SHA256 of the one parsed byte buffer. Access time is not
content identity. Six tiny controls call the production Metadata.bytes path:
baseline and access-time-only pass; changed content (same size/restored mtime),
mtime-only and replaced inode refuse; restored passes. The atime/mtime/inode
interventions run after the actual read closes, before its final identity check.
No scientific/native/coverage helpers or image payloads are exercised.

The old preparation reservation is fully spent, not measured or refunded. This
attempt's controls, retained metadata and all final checks share the new root-
reserved 30 CPU /60 wall /2 MiB, added inside the unchanged global caps.
"""
import time
STARTED, CPU_STARTED = time.monotonic(), 0.0
import argparse
import ast
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
SUBJECT = HERE / "native-sensor-white-artifact-derivative-1"
DEST = HERE / "sensor-white-coverage-release-2.json"
DETAILS = HERE / "work/sensor-white-coverage-release-2-preparation.json"
CONTROL_DIR = HERE / "work/sensor-white-coverage-preparation-2-controls"
OUTPUT = HERE / "sensor-white-coverage-1"
PREVIOUS_RELEASE_SHA = "ad8b391f54d3fd10843a75e4515a8344b5e2b903145d5f256c0248f7758e95ec"
PYTHON = Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
MIB = 1 << 20
ALLOWANCE = dict(cpu_seconds=30, wall_seconds=60, file_bytes=2*MIB, metadata_bytes=2*MIB)
WRITTEN_BYTES = 0  # Every requested write is charged, including failed/overwritten writes.
LIMITS = dict(cpu_seconds=1200, wall_seconds=1800, file_bytes=4 << 30, metadata_bytes=128*MIB)
PINS = {
    "experiments/m193c-output-grid/coverage-sensor-white-run.py": "16f9e944673aa58b81727fabddadc7192a082cef149e950cd7dda24f217e51cf",
    "experiments/m193c-output-grid/sensor-white-coverage-preregister.md": "12ec3389dacdb8ea79ba278fd14805e0399d2ec9230b53216b76df513d51e38c",
    "experiments/m193c-output-grid/independent-sensor-white-coverage-source-review.md": "72781cb1f8f4794e3d23cd7d52a08c03a7da05cf5018d93c90015e718401fe0d",
    "experiments/m193c-output-grid/coverage-run-preregister.md": "ac02242cacd41b0d0aacfd8961f41cbb7b7d090ac233a5e0cb1f73a94429734b",
    "experiments/m193c-output-grid/sensor-coverage-preregister.md": "4176be1c68d461d41fcd3629701f213420a29159254218043c92a83fda6cb521",
    "experiments/m193c-output-grid/native-derivative-run.py": "94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a",
    "experiments/m193b-geometry-consumer/consumer.py": "41e087797866505cc30384888ed83cd7a94dbcd7b757054433186003b37d2b26",
    "experiments/M193-cover-overlap/reference.py": "c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790",
    "experiments/M193-cover-overlap/fixtures.json": "8f5ebcba9688f0d08e71d74f1e8c881702c932ba7d3386e1f9131ffa882ac693",
    "experiments/M193-cover-overlap/contract-v1.json": "19421729ac39273a5f61cda5068026f3458ba08c98f0aa954de7c219cbfabf47",
    "experiments/m193c-output-grid/bounded-process.py": "47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b",
    "experiments/m12-scorecard/m12-harness.py": "6cfb408992f37b225f102da4d62ba836f9c5b67c92bdd418ff460987866a1bb9",
}
POPULATION = ((0, "DSC00016.ARW"), (13, "DSC00029.ARW"), (26, "DSC00042.ARW"),
              (39, "DSC00055.ARW"), (52, "DSC00068.ARW"), (65, "DSC00081.ARW"),
              (78, "DSC00094.ARW"), (91, "DSC00107.ARW"), (104, "DSC00120.ARW"))
IMAGE_SUFFIXES = {".arw", ".raw", ".dng", ".tif", ".tiff", ".npy", ".npz", ".png", ".jpg", ".jpeg"}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def closed(value, names, reason):
    need(type(value) is dict and set(value) == set(names), reason + " closed fields")


def hash_form(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def check():
    need(time.process_time()-CPU_STARTED <= ALLOWANCE["cpu_seconds"], "preparation30 CPU bound")
    need(time.monotonic()-STARTED <= ALLOWANCE["wall_seconds"], "preparation60 wall bound")


def path(value, executable=False):
    need(type(value) is str, "string path")
    p = Path(value)
    if not p.is_absolute():
        q = PurePosixPath(value)
        need("\\" not in value and str(q) == value and ":" not in value and
             all(s not in ("", ".", "..") for s in q.parts), "contained POSIX reference")
        p = ROOT / p
    resolved = p.resolve()
    need((executable and resolved == PYTHON) or resolved.is_relative_to(ROOT), "contained metadata path")
    need(resolved.suffix.lower() not in IMAGE_SUFFIXES, "no image/array payload read")
    return resolved


def ordinary(p):
    st = p.stat(follow_symlinks=False)
    need(stat.S_ISREG(st.st_mode) and not st.st_file_attributes & 0x400, "ordinary bounded metadata file")
    return st


def stable_metadata(st):
    return {key: getattr(st, key) for key in
            ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_file_attributes")}


def strict(raw):
    def pairs(rows):
        out = {}
        for k, v in rows:
            need(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    def numeric(word):
        value = float(word)
        need(math.isfinite(value), "finite JSON number")
        return value
    return json.loads(raw, object_pairs_hook=pairs, parse_float=numeric,
                      parse_constant=lambda s: need(False, "invalid JSON constant: " + s))


def payload(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf8")


def save_bytes(destination, raw, mode="xb"):
    global WRITTEN_BYTES
    check()
    WRITTEN_BYTES += len(raw)
    need(WRITTEN_BYTES <= ALLOWANCE["file_bytes"], "preparation2MiB cumulative metadata write bound")
    with destination.open(mode) as stream:
        need(stream.write(raw) == len(raw), "complete proposed metadata write")
        stream.flush(); os.fsync(stream.fileno())
    check()


class Metadata:
    def __init__(self):
        self.seen = {}

    def bind(self, value, expected=None, executable=False):
        p = path(str(value), executable)
        before = ordinary(p)
        need(0 < before.st_size <= 64*MIB, "metadata/source extent cap")
        digest, size = hashlib.sha256(), 0
        with p.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            need((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), "opened metadata identity")
            while raw := stream.read(MIB):
                size += len(raw)
                need(size <= 64*MIB, "metadata grew beyond cap")
                digest.update(raw)
                check()
        after = ordinary(p)
        need(stable_metadata(before) == stable_metadata(after) and size == before.st_size,
             "metadata/source changed during hash")
        got = dict(path=str(p) if executable else p.relative_to(ROOT).as_posix(), sha256=digest.hexdigest(), bytes=size)
        if expected is not None:
            need(hash_form(expected) and got["sha256"] == expected, "external metadata pin")
        need(self.seen.setdefault(str(p), got) == got, "previously bound metadata changed")
        return got

    def ref(self, ref, executable=False):
        closed(ref, ("path", "sha256", "bytes"), "FileRef")
        need(type(ref["bytes"]) is int and ref["bytes"] > 0, "positive FileRef extent")
        got = self.bind(ref["path"], ref["sha256"], executable)
        need(got["bytes"] == ref["bytes"], "FileRef extent")
        return got

    def bytes(self, ref, cap=4*MIB, *, _after_read=None):
        p = path(ref["path"])
        need(ref["bytes"] <= cap, "bounded same-buffer metadata")
        before = ordinary(p)
        with p.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            need((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), "opened same-buffer metadata identity")
            raw = stream.read(cap+1)
        if _after_read is not None:
            _after_read(p, before)
        need(len(raw) == ref["bytes"], "same-buffer metadata extent")
        need(hashlib.sha256(raw).hexdigest() == ref["sha256"], "same-buffer metadata SHA256")
        need(stable_metadata(ordinary(p)) == stable_metadata(before), "stable same-buffer metadata identity")
        check()
        return raw

    def read(self, ref):
        need(path(ref["path"]).suffix == ".json", "JSON metadata path")
        return strict(self.bytes(ref))

    def recheck(self):
        for value in tuple(self.seen.values()):
            self.ref(value, Path(value["path"]) == PYTHON)


def literal(raw, name):
    tree = ast.parse(raw)
    found = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    need(len(found) == 1, "single source literal: " + name)
    return found[0]


def image_reference(ref):
    """Metadata stat only. Its SHA is inherited from admitted records, never recomputed here."""
    closed(ref, ("path", "sha256", "bytes"), "admitted TIFF ref")
    need(type(ref["path"]) is str and hash_form(ref["sha256"]) and type(ref["bytes"]) is int and
         0 < ref["bytes"] <= 217_048_576, "bounded admitted TIFF identity")
    p = Path(ref["path"])
    need(p.is_absolute() and p.suffix.lower() == ".tiff" and p.resolve().is_relative_to(HERE), "owned actual TIFF path")
    st = ordinary(p)
    need(st.st_size == ref["bytes"] and st.st_nlink == 1, "actual TIFF extent/ordinary identity; no payload access")
    return dict(path=p.resolve().relative_to(ROOT).as_posix(), sha256=ref["sha256"], bytes=ref["bytes"]), (st.st_dev, st.st_ino)


def metadata_controls():
    """Six actual byte-reader calls; private callbacks modify only this fresh directory."""
    need(CONTROL_DIR.resolve().is_relative_to(HERE) and not CONTROL_DIR.exists(), "fresh owned metadata controls")
    CONTROL_DIR.mkdir()
    rows, original = [], b'{"fixed": 17}\n'
    result = dict(schema="m193c-coverage-preparation-metadata-controls-v1", status="REFUSED", checks=rows,
                  files=[], requested_write_bytes=None, error=None, finalization_errors=[])
    try:
        for mode in ("baseline", "access-time-only", "changed-content", "mtime-only", "replaced-inode", "restored"):
            check()
            p = CONTROL_DIR / (mode+".json")
            save_bytes(p, original)
            os.utime(p, ns=(1_600_000_000_000_000_000, 1_600_000_002_000_000_000))
            reader = Metadata()
            ref = reader.bind(p)
            before = ordinary(p)
            if mode == "changed-content":
                save_bytes(p, b'{"fixed": 19}\n', "wb")
                os.utime(p, ns=(before.st_atime_ns, before.st_mtime_ns))
            def intervene(actual_path, at_read):
                need(actual_path == p and stable_metadata(at_read) == stable_metadata(before), "actual control read boundary")
                if mode == "access-time-only":
                    os.utime(p, ns=(before.st_atime_ns+2_000_000_000, before.st_mtime_ns))
                elif mode == "mtime-only":
                    os.utime(p, ns=(before.st_atime_ns, before.st_mtime_ns+2_000_000_000))
                elif mode == "replaced-inode":
                    replacement = CONTROL_DIR / "replacement.json"
                    save_bytes(replacement, original)
                    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
                    archived = CONTROL_DIR / "replaced-inode-original.json"
                    need(p.parent == replacement.parent == archived.parent == CONTROL_DIR, "owned nonrecursive metadata rename")
                    p.rename(archived)
                    replacement.rename(p)
            expected = "same-buffer metadata SHA256" if mode == "changed-content" else (
                "stable same-buffer metadata identity" if mode in ("mtime-only", "replaced-inode") else None)
            error, returned = None, None
            try:
                returned = reader.bytes(ref, 1024, _after_read=intervene if mode in
                                        ("access-time-only", "mtime-only", "replaced-inode") else None)
            except ValueError as exc:
                error = str(exc)
            after = ordinary(p)
            actual = p.read_bytes()  # Tiny owned fixture, never a subject/image payload.
            actual_sha = hashlib.sha256(actual).hexdigest()
            unchanged_hash = actual_sha == ref["sha256"]
            stable_before, stable_after = stable_metadata(before), stable_metadata(after)
            power = (stable_before == stable_after and unchanged_hash)
            if mode == "access-time-only":
                power = power and before.st_atime_ns != after.st_atime_ns
            elif mode == "changed-content":
                power = stable_before == stable_after and len(actual) == ref["bytes"] and not unchanged_hash
            elif mode == "mtime-only":
                power = unchanged_hash and before.st_mtime_ns != after.st_mtime_ns and all(
                    stable_before[k] == stable_after[k] for k in stable_before if k != "st_mtime_ns")
            elif mode == "replaced-inode":
                power = unchanged_hash and before.st_ino != after.st_ino and all(
                    stable_before[k] == stable_after[k] for k in stable_before if k != "st_ino")
            passed = power and error == expected and (returned == original if expected is None else returned is None)
            rows.append(dict(id=mode, passed=passed, expected_exception=expected, actual_exception=error,
                             before=stable_before, after=stable_after,
                             access_time_before_ns=before.st_atime_ns, access_time_after_ns=after.st_atime_ns,
                             original_sha256=ref["sha256"], actual_sha256=actual_sha,
                             returned_sha256=None if returned is None else hashlib.sha256(returned).hexdigest()))
            need(passed, "metadata control did not exercise expected boundary: "+mode)
        result["status"] = "PASS_STABLE_METADATA_IDENTITY_ONLY"
    except BaseException:
        result["error"] = traceback.format_exc()
    try:
        collector = Metadata()
        result["files"] = [collector.bind(p) for p in sorted(CONTROL_DIR.iterdir())]
        need(sum(v["bytes"] for v in result["files"]) <= 4096, "tiny metadata fixture extent bound")
        result["requested_write_bytes"] = WRITTEN_BYTES
        raw = payload(result)
        need(len(raw) <= 64*1024, "bounded metadata-control receipt")
        save_bytes(CONTROL_DIR/"result.json", raw)
    except BaseException:
        result["finalization_errors"].append(traceback.format_exc())
        if result["error"] is None:
            result["error"] = result["finalization_errors"][0]
    need(result["status"] == "PASS_STABLE_METADATA_IDENTITY_ONLY" and result["error"] is None and
         not result["finalization_errors"], "metadata reader controls refused: "+str(result["error"]))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-sha256", required=True)
    for key in ("native-result", "native-outer", "native-console", "native-exit", "audit-result",
                "audit-script", "audit-report", "prior-work", "carry-basis"):
        parser.add_argument("--"+key, nargs=2, required=True, metavar=("PATH", "SHA256"))
    parser.add_argument("--review", nargs=2, action="append", required=True, metavar=("PATH", "SHA256"))
    args = parser.parse_args()
    need(os.name == "nt" and Path.cwd().resolve() == ROOT and Path(sys.executable).resolve() == PYTHON,
         "actual Windows ROOT interpreter")
    need(sys.dont_write_bytecode and all(not p.exists() for p in (DEST, DETAILS, OUTPUT, CONTROL_DIR, DEST.with_suffix(".refused.json"))),
         "fresh proposed release/output with -B")
    m, inputs = Metadata(), {}
    def add(ref):
        value = m.ref(ref)
        need(inputs.setdefault(value["path"], value) == value, "input reference collision")
        return value
    prepared_self = m.bind(__file__, args.self_sha256)
    controlled = metadata_controls()
    control_ref = add(m.bind(CONTROL_DIR/"result.json"))
    for ref in controlled["files"]:
        add(ref)
    refs = {}
    for name in ("native_result", "native_outer", "native_console", "native_exit", "audit_result", "audit_script", "audit_report", "prior_work", "carry_basis"):
        refs[name] = add(m.bind(*getattr(args, name)))
    need(path(refs["native_result"]["path"]) == SUBJECT/"result.json", "literal completed native result")
    native = m.read(refs["native_result"])
    need(native.get("schema") == "m193c-sensor-white-native-derivative-run-v1" and
         native.get("status") == "COMPLETE_NINE_SENSOR_WHITE_DERIVATIVES_AWAITING_COVERAGE" and
         native.get("error") is None and native.get("finalization_errors") == [] and
         native.get("first_refusal") is None and native.get("unvisited") == [], "all-nine native admission required")
    release_ref = add(native["execution_release"])
    previous = m.read(release_ref)
    need(release_ref["sha256"] == PREVIOUS_RELEASE_SHA and len(previous["source_bindings"]) == 153 and len(previous["inputs"]) == 145 and
         previous["schema"] == "m193c-sensor-white-native-derivative-release-v1" and previous["scope"] == "sensor-white-native-nine" and
         native["sources_before"] == native["sources_after"] == previous["source_bindings"] and
         native["inputs_before"] == native["inputs_after"] == previous["inputs"], "completed stable native source/input closure")
    for ref in previous["inputs"]:
        add(ref)
    sources = dict(previous["source_bindings"])
    outer = m.read(refs["native_outer"])
    closed(outer, ("scope", "command", "release_sha256", "exit_code", "elapsed_wall_seconds", "dependency_before",
                   "dependency_after", "dependency_error", "dependency_supplement_sha256", "admissible_parent_exit"), "root native outer")
    need(type(outer["exit_code"]) is int and outer["exit_code"] == 0 and outer["admissible_parent_exit"] is True and
         outer["dependency_error"] is None and outer["command"] == native["invocation"] and
         outer["release_sha256"] == release_ref["sha256"] and outer["dependency_before"] == outer["dependency_after"],
         "actual root exit/command/dependency observation")
    actual_command = [release_ref["sha256"] if word == "ACTUAL_EXECUTION_RELEASE_SHA256" else word for word in previous["commands"][0]]
    need(native["invocation"] == actual_command and str(HERE/"native-sensor-white-artifact-run.py") in actual_command,
         "actual released artifact-parent command")
    supplements = [ref for ref in previous["inputs"] if ref["sha256"] == outer["dependency_supplement_sha256"]]
    need(len(supplements) == 1, "one actual adjacent dependency supplement")
    supplement = m.read(add(supplements[0]))
    closed(supplement, ("schema","scope","required_observation","files","runtime_sha256"), "adjacent dependency supplement")
    need(supplement["schema"] == "m193c-adjacent-dependency-observation-v1" and
         supplement["runtime_sha256"] == previous["reader"]["runtime"]["sha256"] and
         outer["dependency_before"] == outer["dependency_after"] == supplement["files"], "actual declared dependency endpoints")
    need(m.bytes(refs["native_exit"], 64).strip() == b"0", "actual root exit file")
    lines = [line for line in m.bytes(refs["native_console"],16*MIB).splitlines() if line.strip()]
    need(lines, "actual final native stdout")
    final = strict(lines[-1])
    closed(final, ("status", "result", "work_through_final_checks", "error", "finalization_errors"), "native final stdout")
    need(final["status"] == native["status"] and final["error"] is None and final["finalization_errors"] == [] and
         path(final["result"]) == SUBJECT/"result.json", "actual terminal native result association")
    carry = m.read(refs["prior_work"])
    closed(carry, LIMITS, "root four-field carry")
    closed(final["work_through_final_checks"], LIMITS, "actual native final four-field work")
    for key in LIMITS:
        actual, prior = final["work_through_final_checks"][key], carry[key]
        valid = (type(actual) is int and type(prior) is int) if key.endswith("bytes") else (
            type(actual) in (int,float) and type(prior) in (int,float) and math.isfinite(actual) and math.isfinite(prior))
        need(valid and actual >= 0 and prior >= actual + ALLOWANCE[key] and prior <= LIMITS[key],
             "root carry covers actual work and nonrefundable preparation allowance: " + key)
    need(type(outer["elapsed_wall_seconds"]) in (int,float) and math.isfinite(outer["elapsed_wall_seconds"]) and outer["elapsed_wall_seconds"] >= 0 and
         Decimal(str(carry["wall_seconds"])) >= Decimal(str(native["prior_work"]["wall_seconds"])) +
         Decimal(str(outer["elapsed_wall_seconds"])) + ALLOWANCE["wall_seconds"], "carry includes actual outer elapsed plus preparation")

    audit = m.read(refs["audit_result"])
    closed(audit, ("schema","status","subject_status","subject_complete","external","commit","audit_source","invocation",
                   "source_count","input_count","artifact_controls","frames","first_refusal","unvisited","fresh_primary_jobs",
                   "fresh_reader_jobs","fresh_child_cpu_seconds","deleted_snapshots","output_inventory","actual_final_work","prior_work",
                   "retained_output_bytes","retained_binary_bytes","extent_lower_bounds","next_wall_seconds","unique_hashed_files","scope"),
           "independent saved-outcome audit")
    need(audit["schema"] == "m193c-saved-sensor-white-artifact-audit-v1" and
         audit["status"] == "PASS_SAVED_SENSOR_WHITE_ARTIFACT_OUTCOME_AUDIT" and
         audit["subject_complete"] is True and audit["subject_status"] == native["status"] and
         audit["first_refusal"] is None and audit["unvisited"] == [], "actual independent complete-outcome audit")
    closed(audit["external"], ("release","result","outer","console","exit"), "audit actual external refs")
    for key, expected in (("release",release_ref),("result",refs["native_result"]),("outer",refs["native_outer"]),
                          ("console",refs["native_console"]),("exit",refs["native_exit"])):
        need(m.ref(audit["external"][key]) == expected, "audit externally pinned actual " + key)
    need(m.ref(audit["audit_source"]) == refs["audit_script"] and
         path(refs["audit_script"]["path"]) == HERE/"work/independent-native-sensor-white-artifact-1-audit.py" and
         path(refs["audit_report"]["path"]) == HERE/"independent-native-sensor-white-artifact-1-read.md" and
         type(audit["commit"]) is str and re.fullmatch(r"79d75c40(?:[0-9a-f]{32})?",audit["commit"]) is not None,
         "actual reviewed audit source and committed native revision")
    expected_audit_command = [str(PYTHON), "-B", refs["audit_script"]["path"]]
    for key, expected in (("release",release_ref),("result",refs["native_result"]),("outer",refs["native_outer"]),
                          ("console",refs["native_console"]),("exit",refs["native_exit"])):
        expected_audit_command += ["--"+key+"-sha256", expected["sha256"]]
    expected_audit_command += ["--commit", audit["commit"]]
    need(audit["invocation"] == expected_audit_command, "actual audit invocation and external argument pins")
    for key, expected in (("source_count",153),("input_count",145),("fresh_primary_jobs",8),("fresh_reader_jobs",9)):
        need(type(audit[key]) is int and audit[key] == expected, "exact actual audit count: " + key)
    need(audit["actual_final_work"] == final["work_through_final_checks"] and audit["prior_work"] == native["prior_work"] and
         Decimal(audit["next_wall_seconds"]) == Decimal(str(native["prior_work"]["wall_seconds"])) + Decimal(str(outer["elapsed_wall_seconds"])),
         "independent audit actual carry association")
    need(type(audit["frames"]) is list and len(audit["frames"]) == 9, "nine audited reader outcomes")

    def source(ref):
        value = add(ref)
        binding = {key:value[key] for key in ("sha256","bytes")}
        need(sources.setdefault(value["path"], binding) == binding, "preserved/new source collision")
        return value
    for name,pin in PINS.items():
        source(m.bind(ROOT/name,pin))
    self_ref = source(prepared_self)
    source(refs["audit_script"])
    review_refs = [add(m.bind(name,pin)) for name,pin in args.review]
    need(len({ref["path"] for ref in review_refs}) == len(review_refs) and
         all(path(ref["path"]).parent == HERE and path(ref["path"]).name.startswith("independent-") and
             path(ref["path"]).suffix == ".md" for ref in review_refs), "distinct actual local source reviews")
    build_ref = add(previous["build"])
    build = m.read(build_ref)
    need(build["schema"] == "m193c-bridge-build-v1" and build["status"] == "COMPLETE_COMPILED_TESTS_ONLY" and
         build["error"] is None and build["finalization_errors"] == [] and build["sources_before"] == build["sources_after"] and
         build["test_executable"]["sha256"] == "fa03b12fe177608851d6758517c9bda050998cdc4d777195fab8e3dc1e0813a3" and
         build["test_executable"]["bytes"] == 29488640 and native["build"] == previous["build"], "unchanged actual build3 metadata")
    need(all(previous["source_bindings"].get(name) == value for name,value in build["sources_before"].items()),
         "native release preserves actual compiled sources")
    add(build["test_executable"])
    worker_source = m.bytes(add(m.bind(HERE/"coverage-sensor-white-run.py",PINS["experiments/m193c-output-grid/coverage-sensor-white-run.py"])))
    native_ids, domain_ids, white_ids = (literal(worker_source,key) for key in ("NATIVE_CHECK_IDS","DOMAIN_IDS","WHITE_IDS"))
    need(len(native["rows"]) == 9, "exact nine completed native rows")
    tiffs, row_refs, identities, identities_in_order = [], [], set(), []
    for ordinal,(row,(index,name)) in enumerate(zip(native["rows"],POPULATION,strict=True)):
        need(type(row["original_index"]) is int and row["original_index"] == index and row["ordinal"] == ordinal and row["name"] == name and
             row["stage"] == "COMPLETE_FRAME_INDEPENDENTLY_READ" and row["error"] is None, "literal complete native row")
        need(row["primary_reused"] is (ordinal==0) and row["snapshot_deleted"] is (ordinal!=0) and
             row["snapshot_retained_from_refused_run"] is (ordinal==0), "one historical plus eight fresh snapshot dispositions")
        receipt_ref, primary_ref, request_ref = (add(row[key]) for key in ("independent_read","primary_receipt","read_request"))
        reader, primary, request = m.read(receipt_ref), m.read(primary_ref), m.read(request_ref)
        audited = audit["frames"][ordinal]
        need(type(audited["ordinal"]) is int and audited["ordinal"] == ordinal and type(audited["original_index"]) is int and
             audited["original_index"] == index and audited["completed"] is True and audited["stage"] == row["stage"] and
             audited["error"] is None and m.ref(audited["independent_read"]) == receipt_ref and
             m.ref(audited["primary_receipt"]) == primary_ref and audited["tiff"] == row["tiff"] and
             audited["snapshot"] == row["snapshot"] and audited["snapshot_deleted"] is (ordinal != 0),
             "independently audited actual row and file associations")
        for key,expected in (("native_checks",11),("domain_controls",8),("white_groups",10),("white_calls",23)):
            need(type(audited[key]) is int and audited[key] == expected, "audited complete native component population")
        frame_ref = add(audited["frame_result"])
        need(m.read(frame_ref) == row, "actual independently audited frame result")
        need(reader["schema"] == "m193c-sensor-white-native-derivative-independent-frame-v1" and
             reader["status"] == "PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY" and reader["error"] is None and
             reader["finalization_errors"] == [] and reader["original_index"] == index, "each actual independent native admission")
        need(reader["request"] == row["read_request"] and all(reader[key] == row[key] for key in ("snapshot","primary_receipt","tiff")) and
             request["execution_release"] == native["execution_release"] and
             reader["invocation"]["source_bindings"] == previous["source_bindings"],
             "reader actual request/file/source associations")
        for key,ids in (("checks",native_ids),("domain_controls",domain_ids),("white_controls",white_ids)):
            need(type(reader[key]) is list and tuple(c["id"] for c in reader[key]) == ids and all(c["pass"] is True for c in reader[key]),
                 "complete actual independent check population: "+key)
        need(reader["active_sha256_u16_le"] == primary["source"]["active_sha256_u16_le"] and hash_form(reader["tiff_pixel_sha256_u16_le"]),
             "actual full raw/TIFF hash association from admitted records")
        for key in ("primary_launch","independent_launch"):
            launch = row[key]; observation=launch["observation"]
            need(type(observation["exit_code"]) is int and observation["exit_code"]==0 and observation["error"] is None and
                 observation["cleanup_errors"]==[] and observation["terminal_job_accounting"] is True and
                 type(observation["job_accounting"]["active_processes"]) is int and observation["job_accounting"]["active_processes"]==0 and
                 observation["command"]==launch["command"], "actual successful terminal child")
            add(observation["log"])
            label = "fresh_primary_job" if key == "primary_launch" else "fresh_reader_job"
            job = audited[label]
            if key == "primary_launch" and ordinal == 0:
                need(job is None, "historical primary excluded from fresh Job count")
            else:
                need(job["healthy"] is True and type(job["exit_code"]) is int and job["exit_code"] == 0,
                     "independently audited actual healthy fresh Job")
                need(m.read(add(job["launch"])) == launch, "actual audited fresh launch metadata")
        expected_command=[row["read_request"]["sha256"] if x=="ACTUAL_FRAME_REQUEST_SHA256" else x for x in previous["reader"]["commands"][ordinal]]
        need(reader["invocation"]["orig_argv"] == row["independent_launch"]["command"] == expected_command, "actual released fresh reader command")
        tiff, identity=image_reference(row["tiff"])
        need(identity not in identities,"distinct nine actual TIFF identities")
        identities.add(identity); identities_in_order.append(identity); tiffs.append(tiff)
        need(inputs.setdefault(tiff["path"],tiff)==tiff,"admitted TIFF ref collision")
        row_refs.append(dict(original_index=index,reader=receipt_ref,primary=primary_ref,request=request_ref,tiff=tiff,
                             primary_reused=row["primary_reused"]))
    controls_ref=add(m.bind(SUBJECT/"artifact-contract-controls.json"))
    controls=m.read(controls_ref)
    need(controls["schema"]=="m193c-native-artifact-controls-v1" and controls["status"]=="PASS_EXACT_READER_ARTIFACT_CONTRACT_ONLY" and
         controls["error"] is None and controls["finalization_errors"]==[] and len(controls["checks"])==4 and
         all(c["passed"] is True for c in controls["checks"]),"actual artifact contract controls")
    closed(audit["artifact_controls"], ("file","complete","groups","cases","retained_files","artifact_bytes"), "audited artifact contract controls")
    audited_controls = audit["artifact_controls"]
    need(m.ref(audited_controls["file"]) == controls_ref and audited_controls["complete"] is True and
         all(type(audited_controls[k]) is int and audited_controls[k] == v for k,v in (("groups",4),("cases",5),("retained_files",36))) and
         audited_controls["artifact_bytes"] == controls["artifact_bytes"], "actual audited artifact-control population")
    need(audit["deleted_snapshots"] == [row["snapshot"] for row in native["rows"][1:]],
         "eight previously charged deleted snapshots; no request to reopen them")
    for ref in controls["files"]: add(ref)
    runtime_ref=add(previous["reader"]["runtime"]); runtime=m.read(runtime_ref)
    python=m.ref(runtime["python_executable"],True)
    need(path(python["path"],True)==PYTHON,"same actual captured interpreter")
    contract=m.read(add(m.bind(ROOT/"experiments/M193-cover-overlap/contract-v1.json",PINS["experiments/M193-cover-overlap/contract-v1.json"])))
    expected_runtime=contract["reference_environment"]
    need(expected_runtime==dict(python="3.12.10",numpy="2.4.4",opencv="4.13.0",opencv_build_information_sha256="8a55f551e40cf84d0fa7e2509bb9544da66782a8cbc017d7ce27a9de0ef9c1ac",tifffile="2026.5.2"),"unchanged frozen registrar runtime gate")
    need(runtime["numpy_version"]==expected_runtime["numpy"] and runtime["python_version"].startswith(expected_runtime["python"]+" "),
         "captured Python/NumPy agreement only; actual worker checks OpenCV/tifffile")
    snapshot=sum(t["bytes"] for t in tiffs)+5*MIB
    need(carry["file_bytes"]+snapshot<=LIMITS["file_bytes"],"nine-TIFF plus5MiB snapshot reservation within unchanged4GiB")
    basis = m.read(refs["carry_basis"])
    closed(basis, ("schema","scope","native_console","native_outer","native_actual_and_conservative_outer",
                   "nonrefundable_preparation_allowance","prior_work","snapshot_reservation_separate_bytes",
                   "combined_file_charge_before_worker","file_cap","prior_preparation_work","prior_preparation_allowance",
                   "failed_preparation"), "root carry origin")
    need(basis["schema"] == "m193c-coverage-carry-basis-v2" and m.ref(basis["native_console"]) == refs["native_console"] and
         m.ref(basis["native_outer"]) == refs["native_outer"] and m.ref(basis["prior_work"]) == refs["prior_work"] and
         basis["nonrefundable_preparation_allowance"] == basis["prior_preparation_allowance"] == ALLOWANCE,
         "actual root carry and two approved nonrefundable reserve associations")
    prior_preparation_ref = add(basis["prior_preparation_work"])
    need(prior_preparation_ref["sha256"] == "caed0c531189417de52253ba927338c264105d29589c26335494b9dd54a01146",
         "immutable first preparation carry")
    prior_preparation = m.read(prior_preparation_ref)
    closed(prior_preparation, LIMITS, "old reserved preparation work")
    closed(basis["failed_preparation"], ("source","console","exit","outer"), "retained failed preparation")
    failed = {key:add(ref) for key,ref in basis["failed_preparation"].items()}
    need(failed["source"]["sha256"] == "db33e171b786cbdef81fc8863aa2e77d9cb132075d6910a473e419066991cbfe" and
         path(failed["source"]["path"]) == HERE/"work/prepare-sensor-white-coverage-release-1.py", "immutable failed source")
    source(failed["source"])
    failed_outer = m.read(failed["outer"])
    closed(failed_outer, ("scope","command","source_sha256","exit_code","elapsed_wall_seconds"), "failed actual preparation outer")
    need(failed_outer["source_sha256"] == failed["source"]["sha256"] and type(failed_outer["exit_code"]) is int and
         failed_outer["exit_code"] == 1 and m.bytes(failed["exit"],64).strip() == b"1" and
         b"ValueError: same-buffer metadata identity" in m.bytes(failed["console"],64*1024),
         "actual first combined-predicate refusal; changed field was not recorded")
    old_command = failed_outer["command"]
    need(type(old_command) is list and all(type(x) is str for x in old_command) and
         old_command[:5] == [str(PYTHON),"-B","-X","faulthandler",str(path(failed["source"]["path"]))] and
         old_command.count("--self-sha256") == 1 and old_command[old_command.index("--self-sha256")+1] == failed["source"]["sha256"],
         "actual failed preparation invocation")
    # Keep the original attempt's metadata inputs/review, including its old root carry basis.
    for flag in ("native-result","native-outer","native-console","native-exit","audit-result","audit-script","audit-report",
                 "prior-work","carry-basis","review"):
        need(old_command.count("--"+flag) == 1, "one historical preparation argument: "+flag)
        start = old_command.index("--"+flag)+1
        add(m.bind(*old_command[start:start+2]))
    base = basis["native_actual_and_conservative_outer"]
    closed(base, LIMITS, "actual conservative carry base")
    need(all(base[k] == final["work_through_final_checks"][k] for k in ("cpu_seconds","file_bytes","metadata_bytes")) and
         Decimal(str(base["wall_seconds"])) == Decimal(audit["next_wall_seconds"]) and
         all(Decimal(str(prior_preparation[k])) == Decimal(str(base[k]))+ALLOWANCE[k] and
             Decimal(str(carry[k])) == Decimal(str(prior_preparation[k]))+ALLOWANCE[k] for k in LIMITS),
         "exact two-attempt nonrefundable root carry construction")
    need(type(basis["snapshot_reservation_separate_bytes"]) is int and basis["snapshot_reservation_separate_bytes"] == snapshot and
         basis["combined_file_charge_before_worker"] == carry["file_bytes"]+snapshot and basis["file_cap"] == LIMITS["file_bytes"],
         "root reservation basis matches exact nine extents plus5MiB")
    script=str(HERE/"coverage-sensor-white-run.py")
    parent_command=[str(PYTHON),"-B","-X","faulthandler","-X","pycache_prefix="+str(OUTPUT/"parent-cache"),script,
                    "--release",str(DEST),"--sha256","ACTUAL_EXECUTION_RELEASE_SHA256","--output",str(OUTPUT)]
    worker_command=[str(PYTHON),"-B","-X","faulthandler","-X","pycache_prefix="+str(OUTPUT/"worker-cache"),script,
                    "--release",str(DEST),"--sha256","ACTUAL_EXECUTION_RELEASE_SHA256","--output",str(OUTPUT/"worker"),
                    "--worker","--request",str(OUTPUT/"request.json"),"--request-sha256","ACTUAL_COVERAGE_REQUEST_SHA256"]
    details=dict(schema="m193c-sensor-white-coverage-preparation-v2",status="PROPOSED_COMMANDS_ONLY",
                 native=refs["native_result"],audit=refs["audit_result"],audit_source=refs["audit_script"],audit_report=refs["audit_report"],
                 artifact_controls=controls_ref,admitted_rows=row_refs,
                 root_prior_work=refs["prior_work"],root_carry_basis=refs["carry_basis"],carry=carry,preparation_reserved_not_measured=ALLOWANCE,
                 prior_preparation_work=prior_preparation_ref,failed_preparation=failed,metadata_controls=control_ref,
                 historical_failure_scope="Combined identity predicate refused; access-time cause not established",
                 snapshot_reservation_bytes=snapshot,snapshot_scope="nonrefundable upper-bound charge by coverage; not charged twice by this preparer",
                 expected_runtime=expected_runtime,runtime_scope="OpenCV build/tifffile remain actual worker gates; no subject imports here",
                 commands=dict(parent=parent_command,worker=worker_command),source_count=len(sources),reviews=review_refs,
                 image_scope="TIFF refs from independently admitted records; actual extent/stat checked; payloads not opened; coverage authenticates bytes")
    raw_details=payload(details)
    need(len(raw_details)<=256*1024,"bounded preparation details")
    prospective_detail=dict(path=DETAILS.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw_details).hexdigest(),bytes=len(raw_details))
    inputs[prospective_detail["path"]]=prospective_detail
    proposed=dict(schema="m193c-sensor-white-coverage-release-v1",scope="sensor-white-native-nine-coverage",source_bindings=sources,
                  inputs=list(inputs.values()),commands=dict(parent=parent_command,worker=worker_command),python_executable=python,
                  native=dict(result=refs["native_result"],console=refs["native_console"],exit=refs["native_exit"],outer=refs["native_outer"]),prior_work=refs["prior_work"])
    raw_release=payload(proposed)
    need(len(raw_release)<=256*1024 and WRITTEN_BYTES+len(raw_details)+len(raw_release)<=ALLOWANCE["metadata_bytes"],"bounded proposed metadata")
    need(all(sources[k]==v for k,v in previous["source_bindings"].items()) and
         all(inputs[m.ref(v)["path"]]==m.ref(v) for v in previous["inputs"]),"all predecessor sources/inputs preserved")
    for name,value in sources.items(): m.ref(dict(path=name,**value))
    def final_metadata_check():
        m.recheck()
        for row, expected, identity in zip(native["rows"], tiffs, identities_in_order, strict=True):
            need(image_reference(row["tiff"]) == (expected, identity), "admitted TIFF metadata remains unchanged")
        check()
    final_metadata_check()
    try:
        for destination,raw in ((DETAILS,raw_details),(DEST,raw_release)):
            save_bytes(destination,raw)
            m.bind(destination,hashlib.sha256(raw).hexdigest());check()
        final_metadata_check()
        need(not OUTPUT.exists(),"coverage output still uncreated")
        check()
        print(json.dumps(dict(status="PREPARED_METADATA_ONLY",release=m.bind(DEST),preparation=m.bind(DETAILS),
                              source_count=len(sources),input_count=len(inputs),snapshot_reservation_bytes=snapshot,
                              metadata_controls=control_ref,requested_metadata_write_bytes=WRITTEN_BYTES,
                              scope="No coverage or subject execution"),allow_nan=False),flush=True)
        check()
    except BaseException as primary_error:
        refused = DEST.with_suffix(".refused.json")
        try:
            if DEST.exists():
                DEST.rename(refused)
        except BaseException:
            primary_error.add_note("release revocation rename failed: " + traceback.format_exc())
            # Keep the original proposal where possible, then invalidate its canonical schema.
            try:
                if not refused.exists():
                    save_bytes(refused, raw_release)
                raw_failure = payload(dict(status="REFUSED_PREPARATION",error=str(primary_error),
                                           notes=getattr(primary_error,"__notes__",[])))
                save_bytes(DEST, raw_failure, "wb")
            except BaseException:
                primary_error.add_note("canonical refusal persistence failed: " + traceback.format_exc())
        raise


if __name__=="__main__":
    main()
