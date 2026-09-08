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
DEST = HERE / "native-sensor-white-derivative-release-1.json"
DETAILS = HERE / "work/native-sensor-white-release-1-preparation.json"
OUTPUT = HERE / "native-sensor-white-derivative-1"
PYTHON = Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
TEST = "merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native"
MIB = 1 << 20
RELEASE_ALLOWANCE = 128 << 10
FUTURE_METADATA_ALLOWANCE = 192 << 10
POPULATION = ((0, "DSC00016.ARW", 39030784), (13, "DSC00029.ARW", 39878656),
              (26, "DSC00042.ARW", 40873984), (39, "DSC00055.ARW", 40669184),
              (52, "DSC00068.ARW", 39497728), (65, "DSC00081.ARW", 39235584),
              (78, "DSC00094.ARW", 39096320), (91, "DSC00107.ARW", 39018496),
              (104, "DSC00120.ARW", 38969344))
PINS = {
    "work/independent-native-sensor-1-audit.py": "9c96b022c05b247e13d591bfc835099336e4b1f40fa7edcc637858ca5aa55eae",
    "native-sensor-derivative-release-1.json": "fb651f3b4aa5eeb891d6cef77e8719e13bb556ba086bd2dbd2add742d93505b8",
    "native-sensor-derivative-1/result.json": "00ae754f28277c69196a55da5fff88c8c807de17f6c48123d73c8b3ee1a6eadb",
    "native-sensor-derivative-1/frame-00/independent/result.json": "58f4a7208a12a5a17913f1c048a54d106faa9a40e0ee3c849c83cbc71c962db7",
    "work/native-sensor-1-console.txt": "d256eb2a353639ca02e62bde2959d994764c8710c1c316469dea06b5f8c5f007",
    "work/native-sensor-1-outer.json": "d5b1950c49691cdfcea2e2fd5fbc70440c81a8474db06ebc0463ab6470d83c2e",
    "work/native-sensor-1-exit.txt": "f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04",
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
    parser.add_argument("--previous-read-sha256", required=True)
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
    # Preserve the immediately preceding sensor run as a refusal, not an admission.
    previous = read(refs["native-sensor-derivative-release-1.json"])
    previous_result = read(refs["native-sensor-derivative-1/result.json"])
    previous_reader = read(refs["native-sensor-derivative-1/frame-00/independent/result.json"])
    need(previous["schema"] == "m193c-sensor-native-derivative-release-v1" and previous["scope"] == "sensor-native-nine" and len(previous["source_bindings"]) == 146 and len(previous["inputs"]) == 93, "actual predecessor source/input population")
    need(previous_result["schema"] == "m193c-sensor-native-derivative-run-v1" and previous_result["status"] == "REFUSED" and previous_result["current_stage"] == "independent-child" and previous_result["attempted_original_index"] == 0 and previous_result["unvisited"] == [v[0] for v in POPULATION[1:]] and len(previous_result["rows"]) == 1 and previous_result["finalization_errors"] == [], "first camera-white refusal remains first class")
    need(checked(previous_result["execution_release"]) == refs["native-sensor-derivative-release-1.json"] and previous_result["sources_before"] == previous_result["sources_after"] == previous["source_bindings"] and previous_result["inputs_before"] == previous_result["inputs_after"] == previous["inputs"], "predecessor actual stable closure")
    for ref in previous["inputs"]:
        add(ref)
    for name, ref in previous["source_bindings"].items():
        need(sources.setdefault(name, ref) == ref, "all prior source bytes preserved")
    need(len(sources) == 146 and previous["reuse_first"] == reuse and previous["build"] == native["build"] and previous["private_admission"] == native["private_admission"] and checked(previous["reader"]["runtime"]) == runtime, "same original native1 primary reuse/build/runtime")
    previous_row = previous_result["rows"][0]
    need(previous_row["primary_reused"] is True and previous_row["snapshot_deleted"] is False and previous_row["snapshot_retained_from_refused_run"] is True and previous_row["independent_read"] is None and previous_row["primary_launch"] == row["primary_launch"] and previous_row["snapshot"] == row["snapshot"] and previous_row["tiff"] == row["tiff"], "no new historical primary replay or snapshot deletion")
    need(previous_reader["status"] == "REFUSED" and "ValueError: scalar white disagrees" in previous_reader["error"] and previous_reader["finalization_errors"] == [] and checked(previous_reader["request"]) == checked(previous_row["read_request"]), "actual saved scalar-white cause")
    need(previous_reader["primary_receipt"] == row["primary_receipt"] and previous_reader["snapshot"] == row["snapshot"] and previous_reader["tiff"] == row["tiff"] and previous_reader["invocation"]["source_bindings"] == previous["source_bindings"], "failed fresh reader historical associations")
    add(previous_row["read_request"])
    previous_observation = previous_row["independent_launch"]["observation"]
    add(previous_observation["log"])
    need(previous_observation["exit_code"] == 1 and previous_observation["error"] is None and previous_observation["cleanup_errors"] == [] and previous_observation["terminal_job_accounting"] is True and previous_observation["job_accounting"]["active_processes"] == 0 and previous_observation["command"] == previous_reader["invocation"]["orig_argv"], "actual one failed fresh reader Job")
    previous_outer = read(refs["work/native-sensor-1-outer.json"])
    previous_final = read(refs["work/native-sensor-1-console.txt"], True)
    previous_command = [refs["native-sensor-derivative-release-1.json"]["sha256"] if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in previous["commands"][0]]
    need(previous_outer["exit_code"] == 1 and previous_outer["admissible_parent_exit"] is False and previous_outer["command"] == previous_result["invocation"] == previous_command and previous_outer["release_sha256"] == refs["native-sensor-derivative-release-1.json"]["sha256"] and previous_outer["dependency_error"] is None and previous_outer["dependency_before"] == previous_outer["dependency_after"] == read(probe_release["adjacent"])["files"], "actual refused predecessor outer chain")
    need(previous_final["status"] == "REFUSED" and previous_final["error"] == previous_result["error"] and previous_final["finalization_errors"] == [] and Path(previous_final["result"]) == HERE/"native-sensor-derivative-1/result.json", "actual predecessor final stdout")
    previous_work = previous_final["work_through_final_checks"]
    need(previous_work["cpu_seconds"] == 43.46875 and previous_work["file_bytes"] == 241651810 and previous_work["metadata_bytes"] == 4822759 and Decimal(str(previous["prior_work"]["wall_seconds"])) + Decimal(str(previous_outer["elapsed_wall_seconds"])) == Decimal("37.9876842"), "complete failed work carried without refund or duplicate primary CPU")
    new_sources = {"native-sensor-white-derivative-run.py": args.parent_sha256, "independent-sensor-white-derivative-read.py": args.reader_sha256, "sensor-white-reader-preregister.md": args.spec_sha256, "work/prepare-native-sensor-white-release-1.py": None}
    inventory, admin_inventory = {}, {}
    admin_paths = {ROOT/name for name in ("docs/research/M193c-output-grid.md", "docs/proposals/2026-09-sota-program.md", "AGENTS.md")}
    def reserve(ref):
        ref = add(ref)
        need(inventory.setdefault(ref["path"], ref) == ref, "reservation collision")
        return ref
    def reserve_admin(p, pin=None):
        ref = binding(p, pin)
        need(admin_inventory.setdefault(ref["path"], ref) == ref, "administrative inventory collision")
        return ref  # Historical size observation only, never a released subject input.
    for name, pin in new_sources.items():
        ref = reserve(binding(HERE/name, pin))
        need(ref["path"] not in sources, "new source only")
        sources[ref["path"]] = {k: ref[k] for k in ("sha256", "bytes")}
    previous_read = reserve(binding(HERE/"independent-native-sensor-1-read.md", args.previous_read_sha256))
    review_names = []
    for name, pin in args.review:
        p = metadata_path(name)
        need(p.parent == HERE and p.suffix == ".md" and p.name.startswith("independent-"), "actual local independent review")
        review_names.append(reserve(binding(p, pin))["path"])
    required_reviews = {"experiments/m193c-output-grid/independent-sensor-white-source-review.md", "experiments/m193c-output-grid/independent-sensor-white-native-parent-source-review.md"}
    need(len(review_names) == len(set(review_names)) and required_reviews.issubset(review_names), "required actual domain and parent reviews")
    for name, pin in args.root_artifact:
        p = metadata_path(name)
        need(p.suffix in (".py", ".md", ".txt", ".json"), "bounded explicit repository root/archive metadata")
        if p in admin_paths:
            reserve_admin(p, pin)
        else:
            reserve(binding(p, pin))
    for name in ("work/native-sensor-1-console.txt", "work/native-sensor-1-outer.json", "work/native-sensor-1-exit.txt", "work/native-sensor-1-checkpoint.json", "work/independent-native-sensor-1-audit.py"):
        reserve(binding(HERE/name))
    for p in sorted(admin_paths):
        reserve_admin(p)
    need(not any(p.relative_to(ROOT).as_posix() in inputs for p in admin_paths), "live scheduling documents are not scientific inputs")
    need(literal(HERE/"native-sensor-white-derivative-run.py", "POPULATION") == literal(HERE/"independent-sensor-white-derivative-read.py", "ORIGINALS") == POPULATION, "exact nine source literals")
    reader_ref = inputs[(HERE/"independent-sensor-white-derivative-read.py").relative_to(ROOT).as_posix()]
    build = read(add(native["build"]))
    need(build["test_executable"]["sha256"] == "fa03b12fe177608851d6758517c9bda050998cdc4d777195fab8e3dc1e0813a3" and build["sources_before"] == build["sources_after"], "same actual compiled producer")
    exe = str(metadata_path(checked(build["test_executable"])["path"]))
    producer_command = [exe, "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]
    reader_commands, schedule = [], []
    for ordinal, (original_index, _, _) in enumerate(POPULATION):
        base = OUTPUT/f"frame-{ordinal:02d}"
        command = [str(PYTHON), "-B", "-X", "faulthandler", "-X", "pycache_prefix="+str(base/"reader-cache"), str(HERE/"independent-sensor-white-derivative-read.py"), "--request", str(base/"read-request.json"), "--request-sha256", "ACTUAL_FRAME_REQUEST_SHA256", "--output", str(base/"independent")]
        reader_commands.append(command)
        if ordinal:
            schedule.append(dict(ordinal=ordinal, original_index=original_index, role="new-primary", command=producer_command))
        schedule.append(dict(ordinal=ordinal, original_index=original_index, role="new-independent-reader", command=command))
    need(len(schedule) == 17, "eight new producers and nine new readers")
    command = [str(PYTHON), "-B", "-X", "faulthandler", "-X", "pycache_prefix="+str(OUTPUT/"parent-cache"), str(HERE/"native-sensor-white-derivative-run.py"), "--release", str(DEST), "--release-sha256", "ACTUAL_EXECUTION_RELEASE_SHA256", "--output", str(OUTPUT)]
    details = dict(schema="m193c-sensor-white-release-preparation-v1", metadata_files=list(inventory.values()), administrative_files=list(admin_inventory.values()), administrative_scope="Historical size/hash observations solely for accounting; not subject inputs or future byte-identity requirements", observed_metadata_bytes=sum(v["bytes"] for v in [*inventory.values(), *admin_inventory.values()]), reserved_bytes=MIB, release_upper_bytes=RELEASE_ALLOWANCE, carry_before_reserve=dict(cpu_seconds=43.46875, wall_seconds=37.9876842, file_bytes=241651810, metadata_bytes=4822759), previous_refusal=dict(release=refs["native-sensor-derivative-release-1.json"], result=refs["native-sensor-derivative-1/result.json"], reader=refs["native-sensor-derivative-1/frame-00/independent/result.json"], independent_read=previous_read, status="REFUSED", previous_primary_was_reused=True), new_children=schedule, primary_reuse=dict(ordinal=0, authority=reuse, snapshot=row["snapshot"], tiff=row["tiff"], primary=row["primary_receipt"], original_plan=old["input_plan"], new_primary_invocation=False, snapshot_delete=False, cpu_already_carried=True, runtime_requirement="fresh full-nine observations and plan bytes/content must equal old plan before reuse"), scope="nonrefundable metadata reservation; no image reads, new launch, or runtime equality claim")
    details["future_root_metadata"] = dict(reserved_bytes=FUTURE_METADATA_ALLOWANCE,
        intended_basenames=["independent-native-sensor-white-release-1-review.md",
            "native-sensor-white-1-console.txt", "native-sensor-white-1-exit.txt", "native-sensor-white-1-outer.json",
            "prepare-native-sensor-white-archive-1.py", "archive-native-sensor-white-1.nul", "native-sensor-white-1-checkpoint.json",
            "M193c-output-grid.md", "2026-09-sota-program.md", "AGENTS.md"],
        scope="Aggregate allowance for later exact manifest review and external root launch/archive/checkpoint metadata; no nonexistent FileRefs. Charge full maximum extents for new paths. For administrative_files already charged above, charge only positive growth beyond their recorded baseline maximum, never their full extent again. Root must inventory these follow-on extents/growth against this allowance before admission. No refund or extra allowance outside the existing one MiB.")
    detail_raw = payload(details)
    need(details["observed_metadata_bytes"] + len(detail_raw) + RELEASE_ALLOWANCE + FUTURE_METADATA_ALLOWANCE < MIB, "whole defined metadata population including future root writes fits reserve")
    write_new(DETAILS, detail_raw)
    add(binding(DETAILS))
    release = dict(schema="m193c-sensor-white-native-derivative-release-v1", scope="sensor-white-native-nine", source_bindings=sources, inputs=list(inputs.values()), commands=[command], build=native["build"], private_admission=native["private_admission"], reader=dict(script=reader_ref, runtime=runtime, commands=reader_commands), prior_work=dict(cpu_seconds=43.46875, wall_seconds=37.9876842, file_bytes=241651810+MIB, metadata_bytes=4822759+MIB), reuse_first=reuse)
    need(len(sources) == 150, "complete preserved and new source closure")
    for name, ref in sources.items(): checked(dict(path=name, **ref))
    for ref in inputs.values(): checked(ref)
    for ref in admin_inventory.values(): checked(ref)  # Same preparation observation only.
    raw = payload(release)
    need(len(raw) <= RELEASE_ALLOWANCE and not OUTPUT.exists(), "bounded release and still-fresh output")
    write_new(DEST, raw)
    print(json.dumps(dict(status="PREPARED_METADATA_ONLY", release=binding(DEST), preparation=binding(DETAILS), sources=len(sources), inputs=len(inputs), new_children=17), indent=2), flush=True)


if __name__ == "__main__":
    main()
