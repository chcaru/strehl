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
DEST = HERE / "native-sensor-white-artifact-derivative-release-1.json"
DETAILS = HERE / "work/native-sensor-white-artifact-release-1-preparation.json"
OUTPUT = HERE / "native-sensor-white-artifact-derivative-1"
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
    "native-sensor-white-derivative-release-1.json": "70d44a9c43d9d8c194824b214b1287358a4f254e01ce6e1efc955d1f85af6611",
    "native-sensor-white-derivative-1/result.json": "af72a5964fe1434db61a1c40638cf0ab4ac1d14ba2133440c067e00cba7fa76f",
    "native-sensor-white-derivative-1/frame-00/frame-result.json": "f6367388ae472d54b2c2c3597b6ab0e04ab7cb169def68909bcd451539ad4fc1",
    "native-sensor-white-derivative-1/frame-00/independent/result.json": "6ec2727b5d8e2b6f3c12c50434d7591735bb57af92339a751fb76d4aae11f3aa",
    "work/native-sensor-white-1-outer.json": "c25135fca535b84dd7ebb517a09f79a0a51dc680a091fda793afd39b0dfdd3d7",
    "work/native-sensor-white-1-console.txt": "b2e5d1d489dd882cbbcc46a3f93d1c2dbba162bb2d6e431592601569a05aa62e",
    "work/native-sensor-white-1-exit.txt": "f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04",
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
    for key in ("parent", "reader", "spec", "previous-read"):
        parser.add_argument("--" + key + "-sha256", required=True)
    parser.add_argument("--audit-script", nargs=2, required=True, metavar=("PATH", "SHA256"))
    parser.add_argument("--review", nargs=2, action="append", required=True, metavar=("PATH", "SHA256"))
    parser.add_argument("--root-artifact", nargs=2, action="append", default=[], metavar=("PATH", "SHA256"))
    args = parser.parse_args()
    need(os.name == "nt" and Path.cwd().resolve() == ROOT and not any(p.exists() for p in (DEST, DETAILS, OUTPUT)), "Windows ROOT/fresh destinations")
    inputs, inventory, admin_inventory = {}, {}, {}
    def add(ref):
        ref = checked(ref)
        need(inputs.setdefault(ref["path"], ref) == ref, "input collision")
        return ref
    def reserve(ref):
        ref = add(ref)
        need(inventory.setdefault(ref["path"], ref) == ref, "reservation collision")
        return ref
    refs = {name: add(binding(HERE/name, sha)) for name, sha in PINS.items()}
    previous = read(refs["native-sensor-white-derivative-release-1.json"])
    result = read(refs["native-sensor-white-derivative-1/result.json"])
    row = read(refs["native-sensor-white-derivative-1/frame-00/frame-result.json"])
    reader = read(refs["native-sensor-white-derivative-1/frame-00/independent/result.json"])
    need(previous["schema"] == "m193c-sensor-white-native-derivative-release-v1" and previous["scope"] == "sensor-white-native-nine" and len(previous["source_bindings"]) == 150 and len(previous["inputs"]) == 118, "actual predecessor150/118")
    need(result["schema"] == "m193c-sensor-white-native-derivative-run-v1" and result["status"] == "REFUSED" and result["current_stage"] == "independent-result" and result["attempted_original_index"] == 0 and result["unvisited"] == [v[0] for v in POPULATION[1:]] and result["rows"] == [row] and result["finalization_errors"] == [], "actual one-frame parent refusal")
    need("ValueError: independent reader metadata-only output" in result["error"] and "ValueError: independent reader metadata-only output" in row["error"] and row["stage"] == "independent-result" and row["independent_read"] is None, "preserve actual parent artifact-refusal cause")
    need(checked(result["execution_release"]) == refs["native-sensor-white-derivative-release-1.json"] and result["sources_before"] == result["sources_after"] == previous["source_bindings"] and result["inputs_before"] == result["inputs_after"] == previous["inputs"] and result["prior_work"] == previous["prior_work"], "actual predecessor stable closure and carry")
    for ref in previous["inputs"]:
        add(ref)  # Preserved declared metadata/code/artifact inputs; image refs are separate.
    sources = dict(previous["source_bindings"])
    need(reader["schema"] == "m193c-sensor-white-native-derivative-independent-frame-v1" and reader["status"] == "PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY" and reader["error"] is None and reader["finalization_errors"] == [] and reader["original_index"] == 0, "actual successful reader is distinct from failed parent")
    for key, count in (("checks", 11), ("domain_controls", 8), ("white_controls", 10)):
        need(type(reader[key]) is list and len(reader[key]) == count and len({x["id"] for x in reader[key]}) == count and all(x["pass"] is True for x in reader[key]), "complete saved reader checks: " + key)
    need(reader["invocation"]["source_bindings"] == sources and checked(reader["request"]) == checked(row["read_request"]), "successful reader release/request association")
    add(row["read_request"])
    for key in ("primary_receipt", "snapshot", "tiff"):
        need(reader[key] == row[key], "reader/row association: " + key)  # Never open image refs.
    observation = row["independent_launch"]["observation"]
    need(observation["exit_code"] == 0 and observation["error"] is None and observation["cleanup_errors"] == [] and observation["terminal_job_accounting"] is True and observation["job_accounting"]["active_processes"] == 0 and observation["direct_exit_observed"] is True and observation["pipe_eof_observed"] is True, "actual successful fresh reader Job")
    need(observation["command"] == row["independent_launch"]["command"] == reader["invocation"]["orig_argv"], "actual reader command chain")
    add(observation["log"])
    expected_reader = [checked(row["read_request"])["sha256"] if x == "ACTUAL_FRAME_REQUEST_SHA256" else x for x in previous["reader"]["commands"][0]]
    need(expected_reader == observation["command"], "released first reader argv")
    outer = read(refs["work/native-sensor-white-1-outer.json"])
    console = read(refs["work/native-sensor-white-1-console.txt"], True)
    need(read(refs["work/native-sensor-white-1-exit.txt"], True) == 1, "recorded root exit1")
    actual_command = [refs["native-sensor-white-derivative-release-1.json"]["sha256"] if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in previous["commands"][0]]
    need(outer["command"] == result["invocation"] == actual_command and outer["exit_code"] == 1 and outer["admissible_parent_exit"] is False and outer["release_sha256"] == refs["native-sensor-white-derivative-release-1.json"]["sha256"] and outer["dependency_error"] is None and outer["dependency_before"] == outer["dependency_after"], "actual refused root invocation and dependency endpoints")
    need(console["status"] == "REFUSED" and console["error"] == result["error"] and console["finalization_errors"] == [] and Path(console["result"]) == HERE/"native-sensor-white-derivative-1/result.json", "actual console JSON, not Hashtable display fields")
    work = console["work_through_final_checks"]
    need(work["cpu_seconds"] == 50.46875 and work["file_bytes"] == 243457739 and work["metadata_bytes"] == 6628688 and Decimal(str(previous["prior_work"]["wall_seconds"])) + Decimal(str(outer["elapsed_wall_seconds"])) == Decimal("45.1272058"), "all failed work carried without refund or duplicate primary CPU")
    # The fresh release preserves original-native1 reuse, never the failed-parent launch as new.
    reuse = {key: add(ref) for key, ref in previous["reuse_first"].items()}
    need(set(reuse) == {"result", "frame_result", "primary_launch", "independent_refusal", "outer", "console", "exit"}, "closed historical first reuse")
    old_result = read(reuse["result"])
    old_row = read(reuse["frame_result"])
    need(reuse["result"]["sha256"] == "4299877897694e655ef04f88001e6406058c1b2d0efddded6d525510fbc9dfe0" and old_result["status"] == "REFUSED" and old_result["rows"] == [old_row] and read(reuse["independent_refusal"])["status"] == "REFUSED", "original native1 refusal immutable")
    need(row["primary_reused"] is True and row["snapshot_deleted"] is False and row["snapshot_retained_from_refused_run"] is True and row["primary_launch"] == old_row["primary_launch"] == read(reuse["primary_launch"]), "old successful primary remains historical only")
    for key in ("primary_receipt", "snapshot", "tiff"):
        need(row[key] == old_row[key], "same original primary artifacts: " + key)
    primary = read(add(old_row["primary_receipt"]))
    old_plan = add(old_result["input_plan"])
    new_plan = add(result["input_plan"])
    need(old_plan["sha256"] == new_plan["sha256"] == "ed77972c956e9267dfb88907778ac8ff2f83887085457b83d7dccdc299db546f" and old_plan["bytes"] == new_plan["bytes"] and read(old_plan) == read(new_plan) and primary["input_plan"] == old_result["input_plan"], "saved full-nine plan identity; future observation still required")
    runtime = add(previous["reader"]["runtime"])
    need(Path(read(runtime)["python_executable"]["path"]) == PYTHON, "same captured interpreter")
    unchanged_reader = add(binding(HERE/"independent-sensor-white-derivative-read.py", args.reader_sha256))
    need(unchanged_reader == checked(previous["reader"]["script"]) and unchanged_reader["sha256"] == "6a318b439d1b9c5cb460808fc1388c7723d66a5adaf63b3303a6c791568a4bb8", "unchanged independently reviewed scientific reader")
    new_sources = {"native-sensor-white-artifact-run.py": args.parent_sha256, "artifact-parent-preregister.md": args.spec_sha256, "work/prepare-native-sensor-white-artifact-release-1.py": None}
    for name, pin in new_sources.items():
        ref = reserve(binding(HERE/name, pin))
        need(ref["path"] not in sources, "new source only")
        sources[ref["path"]] = {k: ref[k] for k in ("sha256", "bytes")}
    audit = reserve(binding(HERE/"independent-native-sensor-white-1-read.md", args.previous_read_sha256))
    audit_path = metadata_path(args.audit_script[0])
    need(audit_path.parent == HERE/"work" and audit_path.suffix == ".py", "actual saved-record audit source")
    reserve(binding(audit_path, args.audit_script[1]))
    review_names = []
    for name, pin in args.review:
        p = metadata_path(name)
        need(p.parent == HERE and p.suffix == ".md" and p.name.startswith("independent-"), "actual local independent review")
        review_names.append(reserve(binding(p, pin))["path"])
    required_reviews = {"experiments/m193c-output-grid/independent-artifact-native-parent-source-review.md"}
    need(len(review_names) == len(set(review_names)) and required_reviews.issubset(review_names), "required actual parent repair review")
    prep_path = "experiments/m193c-output-grid/work/native-sensor-white-release-1-preparation.json"
    need(prep_path in inputs, "preserved predecessor preparation record")
    previous_prep = read(inputs[prep_path])
    admin_paths = {ROOT/name for name in ("docs/research/M193c-output-grid.md", "docs/proposals/2026-09-sota-program.md", "AGENTS.md")}
    baselines = {v["path"]: v for v in previous_prep["administrative_files"]}
    need(set(baselines) == {p.relative_to(ROOT).as_posix() for p in admin_paths}, "closed previously charged admin baselines")
    def reserve_admin(p, pin=None):
        current = binding(p, pin)
        entry = dict(current=current, baseline=baselines[current["path"]], charged_growth_bytes=max(0, current["bytes"]-baselines[current["path"]]["bytes"]))
        need(admin_inventory.setdefault(current["path"], entry) == entry, "administrative inventory collision")
        return current  # Accounting only; neither historical nor current docs become inputs.
    for name, pin in args.root_artifact:
        p = metadata_path(name)
        need(p.suffix in (".py", ".md", ".txt", ".json", ".nul"), "bounded explicit root/archive metadata")
        if p in admin_paths:
            reserve_admin(p, pin)
        else:
            reserve(binding(p, pin))
    for name in ("work/native-sensor-white-1-console.txt", "work/native-sensor-white-1-outer.json", "work/native-sensor-white-1-exit.txt", "work/native-sensor-white-1-checkpoint.json"):
        reserve(binding(HERE/name))
    for p in sorted(admin_paths):
        reserve_admin(p)
    need(not any(p.relative_to(ROOT).as_posix() in inputs for p in admin_paths), "live scheduling documents are not subject inputs")
    need(literal(HERE/"native-sensor-white-artifact-run.py", "POPULATION") == literal(HERE/"independent-sensor-white-derivative-read.py", "ORIGINALS") == POPULATION, "same exact nine source literals")
    build = read(add(previous["build"]))
    need(build["test_executable"]["sha256"] == "fa03b12fe177608851d6758517c9bda050998cdc4d777195fab8e3dc1e0813a3" and build["sources_before"] == build["sources_after"] and previous["private_admission"] == result["private_admission"], "same compiled producer/private gate")
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
    need(len(schedule) == 17, "eight fresh primaries and nine fresh readers")
    command = [str(PYTHON), "-B", "-X", "faulthandler", "-X", "pycache_prefix="+str(OUTPUT/"parent-cache"), str(HERE/"native-sensor-white-artifact-run.py"), "--release", str(DEST), "--release-sha256", "ACTUAL_EXECUTION_RELEASE_SHA256", "--output", str(OUTPUT)]
    details = dict(schema="m193c-sensor-white-artifact-release-preparation-v1", metadata_files=list(inventory.values()), administrative_files=list(admin_inventory.values()), administrative_scope="Previously reserved admin baseline extents remain carried; charge only positive growth now. Historical/current size/hash observations are accounting only, not subject inputs or future identity requirements.", observed_metadata_bytes=sum(v["bytes"] for v in inventory.values())+sum(v["charged_growth_bytes"] for v in admin_inventory.values()), reserved_bytes=MIB, release_upper_bytes=RELEASE_ALLOWANCE, carry_before_reserve=dict(cpu_seconds=50.46875, wall_seconds=45.1272058, file_bytes=243457739, metadata_bytes=6628688), previous_refusal=dict(release=refs["native-sensor-white-derivative-release-1.json"], result=refs["native-sensor-white-derivative-1/result.json"], reader=refs["native-sensor-white-derivative-1/frame-00/independent/result.json"], independent_read=audit, parent_status="REFUSED", reader_status="PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY", reader_exit=0, parent_exit=1), new_children=schedule, primary_reuse=dict(ordinal=0, authority=reuse, snapshot=old_row["snapshot"], tiff=old_row["tiff"], primary=old_row["primary_receipt"], original_plan=old_result["input_plan"], new_primary_invocation=False, snapshot_delete=False, cpu_already_carried=True, runtime_requirement="fresh all-nine observations and actual plan bytes/content must match original plan before reuse"), scope="Nonrefundable additional metadata reservation; all failed work retained; no image reads/new launches or prospective runtime equality claim")
    details["future_root_metadata"] = dict(reserved_bytes=FUTURE_METADATA_ALLOWANCE,
        intended_basenames=["independent-native-sensor-white-artifact-release-1-review.md", "independent-native-sensor-white-artifact-1-audit.py", "independent-native-sensor-white-artifact-1-read.md", "native-sensor-white-artifact-1-console.txt", "native-sensor-white-artifact-1-exit.txt", "native-sensor-white-artifact-1-outer.json", "prepare-native-sensor-white-artifact-archive-1.py", "archive-native-sensor-white-artifact-1.nul", "native-sensor-white-artifact-1-checkpoint.json", "archive-native-sensor-white-outcome-1.py", "archive-native-sensor-white-outcome-1.nul", "native-sensor-white-1-root-metadata.json", "M193c-output-grid.md", "2026-09-sota-program.md", "AGENTS.md"],
        scope="Aggregate later independent actual-audit source/report and root manifest-review/console/exit/outer/archive/checkpoint/accounting allowance; no nonexistent FileRefs. Charge full maximum extents for new paths; only positive growth beyond current maxima for metadata_files/administrative_files already charged or carried. Root inventories these extents/growth before admission. No refund or increase to the one MiB or global caps.")
    detail_raw = payload(details)
    need(details["observed_metadata_bytes"] + len(detail_raw) + RELEASE_ALLOWANCE + FUTURE_METADATA_ALLOWANCE < MIB, "entire defined metadata population fits one MiB")
    write_new(DETAILS, detail_raw)
    add(binding(DETAILS))
    release = dict(schema=previous["schema"], scope=previous["scope"], source_bindings=sources, inputs=list(inputs.values()), commands=[command], build=previous["build"], private_admission=previous["private_admission"], reader=dict(script=unchanged_reader, runtime=runtime, commands=reader_commands), prior_work=dict(cpu_seconds=50.46875, wall_seconds=45.1272058, file_bytes=243457739+MIB, metadata_bytes=6628688+MIB), reuse_first=reuse)
    need(len(sources) == 153 and all(sources[k] == v for k, v in previous["source_bindings"].items()) and all(inputs[v["path"]] == v for v in previous["inputs"]), "all150 prior sources and118 prior inputs preserved")
    for name, ref in sources.items(): checked(dict(path=name, **ref))
    for ref in inputs.values(): checked(ref)
    for entry in admin_inventory.values(): checked(entry["current"])  # Same preparation only.
    raw = payload(release)
    need(len(raw) <= RELEASE_ALLOWANCE and not OUTPUT.exists(), "bounded release and still-fresh output")
    write_new(DEST, raw)
    print(json.dumps(dict(status="PREPARED_METADATA_ONLY", release=binding(DEST), preparation=binding(DETAILS), sources=len(sources), inputs=len(inputs), new_children=17), indent=2), flush=True)


if __name__ == "__main__":
    main()
