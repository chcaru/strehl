"""Prepare bounded metadata only, after root freezes this source and exact argv.

No subject/helper imports, subprocesses, RAW/TIFF reads or image hashes. Reused
image references come from pinned old records; runtime checks their actual bytes.
"""
import argparse
import ast
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
DEST = HERE / "native-sensor-derivative-release-1.json"
DETAILS = HERE / "work/native-sensor-release-1-preparation.json"
OUTPUT = HERE / "native-sensor-derivative-1"
PYTHON = Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
TEST = "merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native"
MIB = 1 << 20
RELEASE_ALLOWANCE = 128 << 10
FUTURE_METADATA_ALLOWANCE = 256 << 10
POPULATION = ((0, "DSC00016.ARW", 39030784), (13, "DSC00029.ARW", 39878656),
              (26, "DSC00042.ARW", 40873984), (39, "DSC00055.ARW", 40669184),
              (52, "DSC00068.ARW", 39497728), (65, "DSC00081.ARW", 39235584),
              (78, "DSC00094.ARW", 39096320), (91, "DSC00107.ARW", 39018496),
              (104, "DSC00120.ARW", 38969344))
PINS = {
    "native-derivative-release-1.json": "37f4f8ceb590dbff386f9a7a773d2f99381e8be481145f2dc9e0ec6896928dc2",
    "native-derivative-1/result.json": "4299877897694e655ef04f88001e6406058c1b2d0efddded6d525510fbc9dfe0",
    "independent-native-derivative-1-read.md": "82f9eea0f293b29454b6555dad01e49654b58ee42daa1e6d9ef73f0bb4f4d91f",
    "active-domain-probe-release-1.json": "b540b3dd8d88587a87a98e5347c579221bc46dd40f014ddd7e0e70de17452538",
    "active-domain-probe-1/result.json": "78330bd2c6f83ff9791fdd3406679ea1e7cd766d1968375e0a418f2185ef688e",
    "active-domain-probe-1/worker.json": "1031e0bee6bec02473981911634857a700cc59f414d575cd18c7ff9a9b9cb03c",
    "independent-active-domain-probe-1-read.md": "16d3b83d8ec718c42f5a3594cf6e260f4d94f3bd71d18033aeb9506d76536e90",
    "work/active-domain-probe-1-console.txt": "e529731c77e828af28b004b365c0e147fbc0f665e2f981b8da8c10526a79d6a2",
    "work/active-domain-probe-1-outer.json": "97358d1936cf9229990c8ae4788f7b24a9ab6e398afd4150d8c01288cfc503bd",
    "work/active-domain-probe-1-exit.txt": "13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354",
}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def metadata_path(value):
    p = Path(value)
    p = p if p.is_absolute() else ROOT / p
    p = p.resolve()
    need(p.is_relative_to(ROOT) and p.suffix.lower() not in (".arw", ".raw", ".tif", ".tiff", ".npy"), "metadata/source only")
    return p


def binding(value, expected=None):
    p = metadata_path(value)
    before = p.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and not before.st_file_attributes & 0x400 and before.st_size <= 64*MIB, "ordinary bounded file")
    h, size = hashlib.sha256(), 0
    with p.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        need((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), "opened identity")
        while chunk := stream.read(MIB):
            size += len(chunk)
            need(size <= 64*MIB, "file growth limit")
            h.update(chunk)
    after = p.stat(follow_symlinks=False)
    need(all(getattr(before, k) == getattr(after, k) for k in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_file_attributes")) and size == before.st_size, "file changed")
    ref = dict(path=p.relative_to(ROOT).as_posix(), sha256=h.hexdigest(), bytes=size)
    if expected is not None:
        need(type(expected) is str and re.fullmatch("[0-9a-f]{64}", expected) and expected == ref["sha256"], "external pin")
    return ref


def checked(ref):
    need(type(ref) is dict and set(ref) == {"path", "sha256", "bytes"} and type(ref["bytes"]) is int, "closed typed FileRef")
    got = binding(ref["path"], ref["sha256"])
    need(got["bytes"] == ref["bytes"], "bound extent")
    return got


def read(ref, text_json=False):
    p = metadata_path(ref["path"])
    need((p.suffix == ".json" or text_json and p.suffix == ".txt") and ref["bytes"] <= 4*MIB, "bounded JSON metadata")
    with p.open("rb") as stream:
        raw = stream.read(4*MIB+1)
    need(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], "same-buffer metadata")
    def pairs(rows):
        value = {}
        for k, v in rows:
            need(k not in value, "duplicate JSON key")
            value[k] = v
        return value
    def number(s):
        value = float(s)
        need(math.isfinite(value), "finite JSON number")
        return value
    return json.loads(raw, object_pairs_hook=pairs, parse_float=number, parse_constant=lambda s: need(False, s))


def literal(p, key):
    tree = ast.parse(p.read_bytes(), filename=str(p))
    values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == key for t in n.targets)]
    need(len(values) == 1, "one source literal: " + key)
    return values[0]


def payload(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf8")


def write_new(p, raw):
    with p.open("xb") as stream:
        need(stream.write(raw) == len(raw), "complete metadata write")
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser()
    for key in ("parent", "reader", "spec"):
        parser.add_argument("--" + key + "-sha256", required=True)
    parser.add_argument("--review", nargs=2, action="append", required=True, metavar=("PATH", "SHA256"))
    parser.add_argument("--root-artifact", nargs=2, action="append", default=[], metavar=("PATH", "SHA256"))
    args = parser.parse_args()
    need(os.name == "nt" and Path.cwd().resolve() == ROOT and not any(p.exists() for p in (DEST, DETAILS, OUTPUT)), "Windows ROOT/fresh destinations")
    inputs = {}
    def add(ref):
        ref = checked(ref)
        need(inputs.setdefault(ref["path"], ref) == ref, "input collision")
        return ref
    refs = {name: add(binding(HERE/name, sha)) for name, sha in PINS.items()}
    native = read(refs["native-derivative-release-1.json"])
    old = read(refs["native-derivative-1/result.json"])
    probe_release = read(refs["active-domain-probe-release-1.json"])
    probe = read(refs["active-domain-probe-1/result.json"])
    worker = read(refs["active-domain-probe-1/worker.json"])
    need(native["schema"] == "m193c-native-derivative-release-v1" and len(native["source_bindings"]) == 139 and len(native["inputs"]) == 58, "original native release")
    need(old["status"] == "REFUSED" and old["current_stage"] == "independent-child" and old["attempted_original_index"] == 0 and len(old["rows"]) == 1 and old["unvisited"] == [v[0] for v in POPULATION[1:]] and old["finalization_errors"] == [], "preserved native1 refusal")
    need(old["sources_before"] == old["sources_after"] == native["source_bindings"] and old["inputs_before"] == old["inputs_after"] == native["inputs"], "historical closure")
    for ref in [*native["inputs"], *probe_release["inputs"]]:
        add(ref)  # These declared lists contain metadata/source/artifacts, never image refs.
    sources = dict(native["source_bindings"])
    for name, ref in probe_release["sources"].items():
        need(sources.setdefault(name, ref) == ref, "native/probe source conflict")
    need(len(sources) == 142 and probe_release["schema"] == "m193c-active-domain-probe-release-v1", "complete actual probe closure")
    for result in (probe, worker):
        need(result["schema"] == "m193c-active-domain-probe-run-v1" and result["status"] == "COMPLETE_DIAGNOSTIC_ONLY" and result["error"] is None and result["finalization_errors"] == [] and result["cpu_accounting_complete"] is True, "terminal diagnostic")
        need(checked(result["execution_release"]) == refs["active-domain-probe-release-1.json"], "diagnostic release association")
    need(checked(probe["evidence"]) == refs["active-domain-probe-1/worker.json"], "actual worker result")
    primary = add(probe_release["primary"])
    primary_value = read(primary)
    evidence = worker["evidence"]
    need(checked(evidence["primary"]) == primary and evidence["snapshot"] == probe_release["snapshot"] and evidence["original_index"] == 0, "actual one-case diagnostic association")
    need(evidence["whole_domain_matches"] is True and evidence["mismatch_rows"] == [] and evidence["row_sha256_u16_le"] == primary_value["source"]["active_row_sha256_u16_le"] and len(evidence["row_sha256_u16_le"]) == 4688, "actual admitted domain-byte diagnostic")
    need(evidence["candidate_sha256_u16_le"] == evidence["primary_sha256_u16_le"] == primary_value["source"]["active_sha256_u16_le"] and evidence["common_visible_sha256"] == evidence["candidate_common_sha256"] and evidence["changed_code_detected"] is True and evidence["restored_code_matches"] is True, "complete diagnostic comparisons and controls")
    runtime = add(native["reader"]["runtime"])
    need(runtime == checked(probe_release["runtime"]) and Path(read(runtime)["python_executable"]["path"]) == PYTHON, "unchanged captured runtime/interpreter")
    add(probe_release["adjacent"])
    outer = read(refs["work/active-domain-probe-1-outer.json"])
    final = read(refs["work/active-domain-probe-1-console.txt"], True)
    commands = {key: [refs["active-domain-probe-release-1.json"]["sha256"] if v == "ACTUAL_RELEASE_SHA256" else v for v in argv] for key, argv in probe_release["commands"].items()}
    need(outer["exit_code"] == 0 and outer["release_sha256"] == refs["active-domain-probe-release-1.json"]["sha256"] and outer["command"] == probe["command"] == commands["parent"] and worker["command"] == commands["worker"], "observed exact diagnostic invocations")
    observation = probe["observation"]
    need(observation["command"] == commands["worker"] and observation["exit_code"] == 0 and observation["error"] is None and observation["cleanup_errors"] == [] and observation["terminal_job_accounting"] is True and observation["job_accounting"]["active_processes"] == 0 and observation["direct_exit_observed"] is True and observation["pipe_eof_observed"] is True, "actual terminal worker")
    add(observation["log"])
    need(final["status"] == "COMPLETE_DIAGNOSTIC_ONLY" and final["error"] is None and final["finalization_errors"] == [] and final["cpu_accounting_complete"] is True and Path(final["result"]) == HERE/"active-domain-probe-1/result.json", "actual final diagnostic stdout")
    work = final["work_through_final_checks"]
    need(work["cpu_seconds"] == 37.71875 and work["file_bytes"] == 239908463 and work["metadata_bytes"] == 3079412 and Decimal(str(probe_release["prior_work"]["wall_seconds"])) + Decimal(str(outer["elapsed_wall_seconds"])) == Decimal("32.1440803"), "actual cumulative carry without binary-float equality error")
    reuse_names = dict(result="native-derivative-1/result.json", frame_result="native-derivative-1/frame-00/frame-result.json", primary_launch="native-derivative-1/frame-00/native-launch.json", independent_refusal="native-derivative-1/frame-00/independent/result.json", outer="work/native-derivative-1-outer.json", console="work/native-derivative-1-console.txt", exit="work/native-derivative-1-exit.txt")
    reuse = {key: add(binding(HERE/name)) for key, name in reuse_names.items()}
    row = read(reuse["frame_result"])
    need(row == old["rows"][0] and read(reuse["primary_launch"]) == row["primary_launch"] and checked(row["primary_receipt"]) == primary and row["snapshot_deleted"] is False and row["independent_read"] is None, "old successful primary remains explicit history")
    add(row["read_request"])
    old_plan = add(old["input_plan"])
    need(old_plan["sha256"] == "ed77972c956e9267dfb88907778ac8ff2f83887085457b83d7dccdc299db546f" and primary_value["input_plan"] == old["input_plan"] and read(reuse["independent_refusal"])["status"] == "REFUSED", "old plan paths and refusal preserved")
    need(primary_value["snapshot"] == row["snapshot"] and primary_value["output"] == row["tiff"] and row["snapshot"]["sha256"] == probe_release["snapshot"]["sha256"] and row["snapshot"]["bytes"] == probe_release["snapshot"]["bytes"], "reused image references only; unopened")
    new_sources = {"native-sensor-derivative-run.py": args.parent_sha256, "independent-sensor-derivative-read.py": args.reader_sha256, "sensor-domain-reader-preregister.md": args.spec_sha256, "work/prepare-native-sensor-release-1.py": None}
    inventory = {}
    def reserve(ref):
        ref = add(ref)
        need(inventory.setdefault(ref["path"], ref) == ref, "reservation collision")
        return ref
    for name, pin in new_sources.items():
        ref = reserve(binding(HERE/name, pin))
        need(ref["path"] not in sources, "new source only")
        sources[ref["path"]] = {k: ref[k] for k in ("sha256", "bytes")}
    review_names = []
    for name, pin in args.review:
        p = metadata_path(name)
        need(p.parent == HERE and p.suffix == ".md" and p.name.startswith("independent-"), "actual local independent review")
        review_names.append(reserve(binding(p, pin))["path"])
    required_reviews = {"experiments/m193c-output-grid/independent-sensor-domain-source-review.md", "experiments/m193c-output-grid/independent-sensor-native-parent-source-review.md"}
    need(len(review_names) == len(set(review_names)) and required_reviews.issubset(review_names), "required actual domain and parent reviews")
    for name, pin in args.root_artifact:
        p = metadata_path(name)
        need(p.suffix in (".py", ".md", ".txt", ".json"), "bounded explicit repository root/archive metadata")
        reserve(binding(p, pin))
    for name in ("independent-active-domain-probe-1-read.md", "work/independent-active-domain-probe-1-audit.py", "work/active-domain-probe-1-console.txt", "work/active-domain-probe-1-outer.json", "work/active-domain-probe-1-exit.txt"):
        reserve(binding(HERE/name))
    need(literal(HERE/"native-sensor-derivative-run.py", "POPULATION") == literal(HERE/"independent-sensor-derivative-read.py", "ORIGINALS") == POPULATION, "exact nine source literals")
    reader_ref = inputs[(HERE/"independent-sensor-derivative-read.py").relative_to(ROOT).as_posix()]
    build = read(add(native["build"]))
    need(build["test_executable"]["sha256"] == "fa03b12fe177608851d6758517c9bda050998cdc4d777195fab8e3dc1e0813a3" and build["sources_before"] == build["sources_after"], "same actual compiled producer")
    exe = str(metadata_path(checked(build["test_executable"])["path"]))
    producer_command = [exe, "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]
    reader_commands, schedule = [], []
    for ordinal, (original_index, _, _) in enumerate(POPULATION):
        base = OUTPUT/f"frame-{ordinal:02d}"
        command = [str(PYTHON), "-B", "-X", "faulthandler", "-X", "pycache_prefix="+str(base/"reader-cache"), str(HERE/"independent-sensor-derivative-read.py"), "--request", str(base/"read-request.json"), "--request-sha256", "ACTUAL_FRAME_REQUEST_SHA256", "--output", str(base/"independent")]
        reader_commands.append(command)
        if ordinal:
            schedule.append(dict(ordinal=ordinal, original_index=original_index, role="new-primary", command=producer_command))
        schedule.append(dict(ordinal=ordinal, original_index=original_index, role="new-independent-reader", command=command))
    need(len(schedule) == 17, "eight new producers and nine new readers")
    command = [str(PYTHON), "-B", "-X", "faulthandler", "-X", "pycache_prefix="+str(OUTPUT/"parent-cache"), str(HERE/"native-sensor-derivative-run.py"), "--release", str(DEST), "--release-sha256", "ACTUAL_EXECUTION_RELEASE_SHA256", "--output", str(OUTPUT)]
    details = dict(schema="m193c-sensor-release-preparation-v1", metadata_files=list(inventory.values()), observed_metadata_bytes=sum(v["bytes"] for v in inventory.values()), reserved_bytes=MIB, release_upper_bytes=RELEASE_ALLOWANCE, carry_before_reserve=dict(cpu_seconds=37.71875, wall_seconds=32.1440803, file_bytes=239908463, metadata_bytes=3079412), new_children=schedule, primary_reuse=dict(ordinal=0, authority=reuse, snapshot=row["snapshot"], tiff=row["tiff"], primary=row["primary_receipt"], original_plan=old["input_plan"], new_primary_invocation=False, snapshot_delete=False, cpu_already_carried=True, runtime_requirement="fresh full-nine observations and plan bytes/content must equal old plan before reuse"), scope="nonrefundable metadata reservation; no image reads, new launch, or runtime equality claim")
    details["future_root_metadata"] = dict(reserved_bytes=FUTURE_METADATA_ALLOWANCE,
        intended_basenames=["independent-native-sensor-release-1-review.md",
            "native-sensor-1-console.txt", "native-sensor-1-exit.txt", "native-sensor-1-outer.json",
            "prepare-native-sensor-archive-1.py", "archive-native-sensor-1.nul", "native-sensor-1-checkpoint.json"],
        scope="Aggregate allowance for later exact manifest review and external root launch/archive/checkpoint metadata; no nonexistent FileRefs. Root must inventory actual follow-on extents against this allowance before admission. No refund or extra allowance outside the existing one MiB.")
    detail_raw = payload(details)
    need(details["observed_metadata_bytes"] + len(detail_raw) + RELEASE_ALLOWANCE + FUTURE_METADATA_ALLOWANCE < MIB, "whole defined metadata population including future root writes fits reserve")
    write_new(DETAILS, detail_raw)
    add(binding(DETAILS))
    release = dict(schema="m193c-sensor-native-derivative-release-v1", scope="sensor-native-nine", source_bindings=sources, inputs=list(inputs.values()), commands=[command], build=native["build"], private_admission=native["private_admission"], reader=dict(script=reader_ref, runtime=runtime, commands=reader_commands), prior_work=dict(cpu_seconds=37.71875, wall_seconds=32.1440803, file_bytes=239908463+MIB, metadata_bytes=3079412+MIB), reuse_first=reuse)
    need(len(sources) == 146, "complete preserved and new source closure")
    for name, ref in sources.items(): checked(dict(path=name, **ref))
    for ref in inputs.values(): checked(ref)
    raw = payload(release)
    need(len(raw) <= RELEASE_ALLOWANCE and not OUTPUT.exists(), "bounded release and still-fresh output")
    write_new(DEST, raw)
    print(json.dumps(dict(status="PREPARED_METADATA_ONLY", release=binding(DEST), preparation=binding(DETAILS), sources=len(sources), inputs=len(inputs), new_children=17), indent=2), flush=True)


if __name__ == "__main__":
    main()
