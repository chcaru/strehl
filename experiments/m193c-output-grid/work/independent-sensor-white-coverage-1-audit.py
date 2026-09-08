"""Prospective coverage saved-outcome audit: stdlib, hashes, metadata and exact reporting algebra.
No registrar/decoder import, image decode, registration or fixture generation.
Only run after root supplies the actual terminal release/result/outer pins.
"""
import argparse
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
OUT = HERE / "sensor-white-coverage-1"
RELEASE = HERE / "sensor-white-coverage-release-2.json"
PREFIX = HERE / "work/sensor-white-coverage-1"
CONSUMER = ROOT / "experiments/m193b-geometry-consumer/consumer.py"
REFERENCE = ROOT / "experiments/M193-cover-overlap/reference.py"
FIXTURES = REFERENCE.with_name("fixtures.json")
CONTRACT = REFERENCE.with_name("contract-v1.json")
SUCCESS = "COMPLETE_NINE_INPUT_REGISTRATION_ONLY"
INDICES = [0,13,26,39,52,65,78,91,104]
CONTROL_IDS = ["frozen-three-input-manifest","identity-retention","crop-retention-destroyer",
               "rehashed-denominator-destroyer","restored-identity-retention",
               "complementary-self-registration","complementary-first-refusal","exact-gauge-direction-and-order"]
MIB = 1 << 20
seen = {}


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


def replace(command, release_sha, request_sha=None):
    return [release_sha if s == "ACTUAL_EXECUTION_RELEASE_SHA256" else
            request_sha if s == "ACTUAL_COVERAGE_REQUEST_SHA256" else s for s in command]


def manifest_hash(manifest):
    body = {k:v for k,v in manifest.items() if k != "manifest_sha256"}
    raw = (json.dumps(body,ensure_ascii=True,sort_keys=True,separators=(",",":"))+"\n").encode()
    return hashlib.sha256(raw).hexdigest()


def ordered_groups(rows):
    """Actual fixed population has no digest ties; do not silently guess a tie order."""
    keyed = sorted(rows,key=lambda r:(bytes.fromhex(r["tiff"]["sha256"]),r["tiff"]["bytes"]))
    need(len({r["tiff"]["sha256"] for r in keyed}) == len(keyed), "fixed input digest uniqueness; exact-byte tie would need separate observation")
    return [dict(path=str(path(r["tiff"]["path"])),sha256=r["tiff"]["sha256"],bytes=r["tiff"]["bytes"],
                 multiplicity=1,original_indices=[r["original_index"]]) for r in keyed]


def check_sources(sources, groups, allow_alias_field=False):
    need(type(sources) is list and len(sources) <= len(groups), "bounded committed source prefix")
    for i,(s,g) in enumerate(zip(sources,groups)):
        need(s["source_sha256"] == g["sha256"] and type(s["byte_length"]) is int and
             s["byte_length"] == g["bytes"] and type(s["multiplicity"]) is int and
             s["multiplicity"] == g["multiplicity"] and s["reference"] is (i == 0), "ordered source/reference association")
        if allow_alias_field:
            exact(s["original_indices"],g["original_indices"])
        t = s["source_to_reference_q32"]
        need(set(t) == {"a","b","tx","ty"} and all(type(x) is int for x in t.values()) and
             t["a"]**2+t["b"]**2 > 0, "typed nonsingular Q32 source map")
        if i == 0:
            exact(t,dict(a=1<<32,b=0,tx=0,ty=0))
        need(type(s["valid_center_guard_q8"]) is int and s["valid_center_guard_q8"] >= 0,
             "actual source guard units")


def refusal(value, groups, real=True):
    need(type(value) is dict and set(value) == {"type","code","message","traceback","frames","failure_phase",
         "constructor_index","committed_sources","ordered_groups","ordered_groups_complete","failing_input","unvisited_inputs"},
         "closed actual refusal observation")
    need(type(value["traceback"]) is str and value["traceback"] and value["message"] in value["traceback"] and
         type(value["frames"]) is list and value["frames"], "actual first traceback/message")
    need(any(f["function"] == "construct_overlap_paths" and
             path(f["file"]) == (OUT/"worker/registrar/m193b-geometry-consumer/consumer.py").resolve()
             for f in value["frames"]), "actual copied constructor exception frame")
    for f in value["frames"]:
        need(type(f["line"]) is int and f["line"] > 0, "actual traceback line")
    seen_groups = value["ordered_groups"]
    need(type(value["ordered_groups_complete"]) is bool, "group completeness explicitly observed")
    if seen_groups is not None:
        expected = groups[:len(seen_groups)]
        exact(seen_groups,expected if real else [{k:v for k,v in g.items() if k != "original_indices"} for g in expected])
    if value["ordered_groups_complete"]:
        need(seen_groups is not None and len(seen_groups) == len(groups), "complete ordered byte population")
        check_sources(value["committed_sources"],groups,allow_alias_field=real)
        n = len(value["committed_sources"])
        if n < len(groups):
            need(type(value["constructor_index"]) is int and value["constructor_index"] == n,
                 "first failing constructor index after actual committed prefix")
            need(value["failing_input"] == seen_groups[n] and value["unvisited_inputs"] == seen_groups[n+1:],
                 "exact failing input and unvisited suffix")
        else:
            need(value["constructor_index"] is None and value["failing_input"] is None and
                 value["unvisited_inputs"] == [], "all sources registered before a later overlap refusal")
    else:
        need(value["constructor_index"] is None and value["failing_input"] is None and
             value["unvisited_inputs"] is None, "no invented failed frame before group setup")


def matrix(t):
    q = 1 << 32
    a,b,x,y = [Fraction(t[k],q) for k in ("a","b","tx","ty")]
    return [[a,-b,x],[b,a,y],[Fraction(0),Fraction(0),Fraction(1)]]


def invert(m):
    """Independent exact 3x3 Gauss-Jordan route, not the subject's closed formula."""
    a = [list(row)+[Fraction(i==j) for j in range(3)] for i,row in enumerate(m)]
    for col in range(3):
        pivot = next(i for i in range(col,3) if a[i][col])
        a[col],a[pivot] = a[pivot],a[col]
        v = a[col][col]
        a[col] = [x/v for x in a[col]]
        for row in range(3):
            if row != col:
                v = a[row][col]
                a[row] = [x-v*y for x,y in zip(a[row],a[col],strict=True)]
    return [r[3:] for r in a]


def multiply(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def rational_map(m):
    return {key:dict(numerator=v.numerator,denominator=v.denominator)
            for key,v in zip(("a","b","tx","ty"),(m[0][0],m[1][0],m[0][2],m[1][2]),strict=True)}


def controls(worker):
    records = worker["controls"]
    need(type(records) is list and [r["id"] for r in records] == CONTROL_IDS[:len(records)], "ordered bounded control prefix")
    fixtures = worker["fixtures"]
    need(type(fixtures) is list and len(fixtures) <= 5, "fixed five-fixture upper bound")
    for i,ref in enumerate(fixtures):
        need(path(ref["path"]) == (OUT/f"worker/fixture-{i}.tiff").resolve(), "actual fixed fixture path")
        verify(ref,MIB)
    for r in records:
        need(set(r) == {"id","passed","evidence"} and type(r["passed"]) is bool, "actual control schema")
        exact(r,read(OUT/("worker/control-"+r["id"]+".json")))
    if len(records) != 8 or not all(r["passed"] for r in records):
        return dict(complete=False,records=records,fixtures=fixtures)
    need(len(fixtures) == 5, "complete fixed five fixtures")
    fixed = read(FIXTURES)
    exact(records[0]["evidence"],fixed["synthetic_overlap"])
    fixture_rows = [dict(original_index=i,tiff=f) for i,f in enumerate(fixtures[:3])]
    groups = ordered_groups(fixture_rows)
    check_sources(records[0]["evidence"]["sources"],groups)
    exact(records[1]["evidence"],fixed["output_retention"]["identity"])
    exact(records[2]["evidence"],fixed["output_retention"]["cropped"])
    need(records[1]["evidence"] != records[2]["evidence"], "actual crop control consumes a changed grid")
    destroyer = records[3]["evidence"]
    need(destroyer["old"]["field_of_view_verdict"] == "PASS" and
         destroyer["old"]["retained_pixels"] == destroyer["old"]["denominator_pixels"] == 400,
         "actual old self-denominator false pass witness")
    need(destroyer["actual_refusal"]["code"] == "UNMEASURED_DENOMINATOR_UNDEFINED" and
         type(destroyer["actual_refusal"]["message"]) is str and destroyer["actual_refusal"]["message"],
         "actual consumed rehashed denominator refusal")
    exact(records[4]["evidence"],records[1]["evidence"])
    self_match = records[5]["evidence"]
    need(type(self_match["mutual_match_count"]) is int and self_match["mutual_match_count"] == 256 and
         self_match["heldout_rms_reference_px"] == "0.000000000", "actual positive complementary self registration")
    complementary = records[6]["evidence"]
    fgroups = ordered_groups([dict(original_index=i,tiff=f) for i,f in enumerate(fixtures[3:])])
    refusal(complementary,fgroups,real=False)
    need(complementary["code"] == "UNMEASURED_INPUT_REGISTRATION_INADEQUATE" and
         complementary["constructor_index"] == 1 and len(complementary["committed_sources"]) == 1 and
         complementary["unvisited_inputs"] == [], "actual complementary first registration refusal")
    g = records[7]["evidence"]
    q = 1 << 32
    exact(g["anchor_q32"],dict(a=3*q//2,b=q//2,tx=7*q,ty=-3*q))
    exact(g["source_q32"],dict(a=q,b=-q//2,tx=-2*q,ty=5*q))
    a,s = matrix(g["anchor_q32"]),matrix(g["source_q32"])
    exact(g["forward"],rational_map(multiply(invert(a),s)))
    exact(g["pull"],rational_map(multiply(invert(s),a)))
    exact(g["reversed_order"],rational_map(multiply(s,invert(a))))
    changed = dict(g["source_q32"],b=-g["source_q32"]["b"])
    exact(g["reversed_rotation_sign"],rational_map(multiply(invert(a),matrix(changed))))
    need(g["reversed_order"] != g["forward"] and g["reversed_rotation_sign"] != g["forward"], "noncommuting and signed gauge powers")
    need(g["reversed_order"]["tx"] == dict(numerator=-4,denominator=1) and
         g["reversed_order"]["ty"] == dict(numerator=10,denominator=1), "literal wrong-order displacement")
    return dict(complete=True,records=records,fixtures=fixtures)


def completed_manifest(worker,rows):
    manifest,gauges = worker["native_manifest"],worker["original_gauges"]
    groups = ordered_groups(rows)
    need(manifest["input_count"] == manifest["unique_input_count"] == 9 and
         type(manifest["input_count"]) is int and type(manifest["unique_input_count"]) is int,
         "actual complete manifest counts")
    need(manifest["reference_rule"] == "minimum (sha256_digest_bytes, byte_length, exact_bytes)" and
         manifest["reference_source_sha256"] == groups[0]["sha256"], "actual byte-minimum reference")
    need(manifest["manifest_sha256"] == manifest_hash(manifest), "canonical completed manifest digest")
    need(len(manifest["sources"]) == 9, "all actual registered sources")
    check_sources(manifest["sources"],groups)
    bundle = hashlib.sha256(b"M193-INPUT-BUNDLE-V1\x00")
    for g in groups:
        bundle.update(struct.pack(">Q",g["bytes"]))
        with path(g["path"]).open("rb") as stream:
            while raw := stream.read(MIB):
                bundle.update(raw)
        verify(dict(path=g["path"],bytes=g["bytes"],sha256=g["sha256"]))
    need(bundle.hexdigest() == manifest["input_bundle_sha256"], "actual complete ordered byte bundle")
    need(type(gauges) is list and [r["original_index"] for r in gauges] == INDICES and
         all(type(r["original_index"]) is int for r in gauges), "actual all-nine original gauge order")
    by_hash = {s["source_sha256"]:s for s in manifest["sources"]}
    anchor = by_hash[rows[4]["tiff"]["sha256"]]["source_to_reference_q32"]
    for r,gauge in zip(rows,gauges,strict=True):
        source = by_hash[r["tiff"]["sha256"]]
        need(gauge["tiff"] == r["tiff"] and gauge["reference"] == source["reference"], "gauge original/TIFF/reference association")
        for key in ("source_to_reference_q32","registration","valid_center_guard_q8"):
            exact(gauge[key],source[key])
        s = matrix(source["source_to_reference_q32"])
        exact(gauge["source_to_original_52_exact_derived"],rational_map(multiply(invert(matrix(anchor)),s)))
        exact(gauge["original_52_to_source_pull_exact_derived"],rational_map(multiply(invert(s),matrix(anchor))))
    box = manifest["common_overlap"]
    need(all(type(box[k]) is int for k in ("x","y","width","height","area_pixels")) and
         box["width"] > 0 and box["height"] > 0 and box["area_pixels"] == box["width"]*box["height"],
         "actual positive reported rectangle")
    need(0 <= box["x"] and 0 <= box["y"] and box["x"]+box["width"] <= manifest["native_width"] and
         box["y"]+box["height"] <= manifest["native_height"], "reported rectangle in reference native grid")
    return dict(reference_original_indices=groups[0]["original_indices"],reference_tiff_sha256=groups[0]["sha256"],
                input_bundle_sha256=manifest["input_bundle_sha256"],manifest_sha256=manifest["manifest_sha256"],
                common_overlap=box,original_gauges=gauges)


def actual_job(o,command):
    need(o["command"] == command and type(o["exit_code"]) is int, "actual worker command/exit")
    verify(o["log"],16*MIB)
    need(path(o["log"]["path"]) == OUT/"worker.log" and o["log_bytes"] == o["log"]["bytes"], "actual worker complete log association")
    a = o["job_accounting"]
    need(o["terminal_job_accounting"] is True and all(integer(a[k]) for k in
         ("active_processes","total_processes","total_terminated_processes","total_cpu_100ns","total_user_100ns","total_kernel_100ns")),
         "actual terminal Job accounting")
    need(a["active_processes"] == 0 and a["total_cpu_100ns"] == a["total_user_100ns"]+a["total_kernel_100ns"],
         "no live worker descendant; CPU sum")
    clean = o["error"] is None and o["cleanup_errors"] == []
    if clean:
        need(o["direct_exit_observed"] is True and o["pipe_eof_observed"] is True and
             o["post_exit_drain"]["completed"] is True and o["post_exit_drain"]["last_accounting"] == a,
             "normal bounded worker direct-exit/EOF/drain")
        need(o["termination"] == dict(attempted=False,before_accounting=None,succeeded=False) and
             a["total_terminated_processes"] == 0, "no intervention in normally finished worker")
        need(a["total_cpu_100ns"]/1e7 <= o["limits"]["cpu_seconds"] and
             o["wall_seconds"] <= o["limits"]["wall_seconds"] and
             o["job_memory"]["peak_job_memory_used_bytes"] <= o["limits"]["committed_bytes"], "actual original Job limits")
    need(o["limits"]["wall_seconds"] <= 240 and o["limits"]["log_bytes"] <= 16*MIB and
         o["limits"]["committed_bytes"] == 8 << 30, "unchanged child resource ceilings")
    return dict(exit_code=o["exit_code"],cpu_seconds=a["total_cpu_100ns"]/1e7,wall_seconds=o["wall_seconds"],
                peak_committed_bytes=o["job_memory"]["peak_job_memory_used_bytes"],clean=clean,
                error=o["error"],cleanup_errors=o["cleanup_errors"],log=o["log"])


def carry_association(release,prior,native_audit):
    """Both nonrefundable preparation allowances remain separate from image snapshots."""
    def input_ref(name):
        matches = [r for r in release["inputs"] if path(r["path"]) == (HERE/"work"/name).resolve()]
        need(len(matches) == 1,"one actual released carry input: "+name)
        verify(matches[0],MIB)
        return matches[0]
    old_ref = input_ref("sensor-white-coverage-prior-work-1.json")
    current_ref = input_ref("sensor-white-coverage-prior-work-2.json")
    basis1_ref = input_ref("sensor-white-coverage-carry-1-basis.json")
    basis2_ref = input_ref("sensor-white-coverage-carry-2-basis.json")
    need(verify(current_ref) == verify(release["prior_work"]),"actual release selects second carry")
    need(old_ref["sha256"] == "caed0c531189417de52253ba927338c264105d29589c26335494b9dd54a01146",
         "preserved first preparation carry bytes")
    old,b1,b2 = (read(r) for r in (old_ref,basis1_ref,basis2_ref))
    base = dict(native_audit["actual_final_work"],wall_seconds=float(native_audit["next_wall_seconds"]))
    allowance = dict(cpu_seconds=30,wall_seconds=60,file_bytes=2*MIB,metadata_bytes=2*MIB)
    common = {"schema","scope","native_console","native_outer","native_actual_and_conservative_outer",
              "nonrefundable_preparation_allowance","prior_work","snapshot_reservation_separate_bytes",
              "combined_file_charge_before_worker","file_cap"}
    need(set(b1) == common and set(b2) == common|{"prior_preparation_work","prior_preparation_allowance","failed_preparation"},
         "closed first/second carry bases")
    need(b1["schema"] == "m193c-coverage-carry-basis-v1" and b2["schema"] == "m193c-coverage-carry-basis-v2",
         "preserved successive carry schemas")
    for basis,carry,ref in ((b1,old,old_ref),(b2,prior,current_ref)):
        exact(basis["native_actual_and_conservative_outer"],base)
        exact(basis["nonrefundable_preparation_allowance"],allowance)
        need(verify(basis["prior_work"]) == verify(ref),"basis selects its own actual carry")
        for key in ("console","outer"):
            need(verify(basis["native_"+key]) == verify(release["native"][key]),"basis exact native endpoint")
        snapshot = sum(r["tiff"]["bytes"] for r in native_audit["frames"])+5*MIB
        need(type(basis["snapshot_reservation_separate_bytes"]) is int and
             basis["snapshot_reservation_separate_bytes"] == snapshot and
             basis["combined_file_charge_before_worker"] == carry["file_bytes"]+snapshot and
             basis["file_cap"] == 4 << 30,"separate unchanged complete snapshot reservation")
    exact(b2["prior_preparation_allowance"],allowance)
    need(verify(b2["prior_preparation_work"]) == verify(old_ref),"second basis retains first full allowance")
    need(set(old) == set(prior) == set(allowance),"closed four-field carry records")
    for key in allowance:
        need(Decimal(str(old[key])) == Decimal(str(base[key]))+allowance[key] and
             Decimal(str(prior[key])) == Decimal(str(old[key]))+allowance[key],"exact two-attempt carry: "+key)
    failed = b2["failed_preparation"]
    need(set(failed) == {"source","console","exit","outer"},"closed failed preparation records")
    for key,ref in failed.items():
        need(any(verify(ref,MIB) == verify(r,MIB) for r in release["inputs"] if path(r["path"]) == path(ref["path"])),
             "failed preparation record retained in release: "+key)
    need(failed["source"]["sha256"] == "db33e171b786cbdef81fc8863aa2e77d9cb132075d6910a473e419066991cbfe" and
         path(failed["source"]["path"]) == HERE/"work/prepare-sensor-white-coverage-release-1.py","exact failed metadata-only source")
    outcome = read(failed["outer"])
    need(set(outcome) == {"scope","command","source_sha256","exit_code","elapsed_wall_seconds"} and
         outcome["source_sha256"] == failed["source"]["sha256"] and type(outcome["exit_code"]) is int and
         outcome["exit_code"] == 1 and number(outcome["elapsed_wall_seconds"]),"actual first preparation refusal")
    need(path(failed["exit"]["path"]).read_bytes().strip() == b"1" and
         b"ValueError: same-buffer metadata identity" in path(failed["console"]["path"]).read_bytes(),
         "preserved combined metadata-predicate refusal, no invented changed-field attribution")
    argv = outcome["command"]
    need(argv[:5] == [str(path(release["python_executable"]["path"])),"-B","-X","faulthandler",str(path(failed["source"]["path"]))],
         "actual failed preparation interpreter/source invocation")
    for flag,ref in (("--prior-work",old_ref),("--carry-basis",basis1_ref),("--self-sha256",failed["source"])):
        need(argv.count(flag) == 1,"one actual failed preparation option")
        at = argv.index(flag)+1
        if flag == "--self-sha256":
            need(argv[at] == ref["sha256"],"failed source external pin")
        else:
            need(path(argv[at]) == path(ref["path"]) and argv[at+1] == ref["sha256"],"failed invocation selected first carry/basis")
    return dict(first_carry=old_ref,second_carry=current_ref,first_basis=basis1_ref,second_basis=basis2_ref,
                failed_preparation=failed,total_allowance={k:2*v for k,v in allowance.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("release-sha256","result-sha256","outer-sha256","console-sha256","exit-sha256","commit"):
        p.add_argument("--"+arg,required=True)
    args = p.parse_args()
    need(sys.dont_write_bytecode and not sys.flags.optimize,"audit -B without -O")
    refs = dict(release=pinned(RELEASE,args.release_sha256),result=pinned(OUT/"result.json",args.result_sha256),
                outer=pinned(str(PREFIX)+"-outer.json",args.outer_sha256),console=pinned(str(PREFIX)+"-console.txt",args.console_sha256),
                exit=pinned(str(PREFIX)+"-exit.txt",args.exit_sha256,64))
    release,parent,outer = (read(refs[k]) for k in ("release","result","outer"))
    need(set(outer) == {"scope","command","release_sha256","exit_code","elapsed_wall_seconds","admissible_parent_exit"},
         "closed actual coverage outer receipt; no invented dependency endpoints")
    need(release["schema"] == "m193c-sensor-white-coverage-release-v1" and
         release["scope"] == "sensor-white-native-nine-coverage", "actual released coverage scope")
    for name,ref in release["source_bindings"].items():
        verify(dict(path=name,**ref),32*MIB)
    for ref in release["inputs"]:
        need(Path(ref["path"]).suffix.lower() != ".arw", "no corpus RAW payload admission by this audit")
        verify(ref,256*MIB)
    verify(release["python_executable"],32*MIB)
    command = replace(release["commands"]["parent"],args.release_sha256)
    need(parent["schema"] == "m193c-sensor-white-coverage-run-v1" and parent["command"] == command == outer["command"] and
         outer["release_sha256"] == args.release_sha256, "actual released parent invocation")
    need(verify(parent["execution_release"]) == refs["release"], "actual parent release FileRef")
    exact(parent["sources_before"],release["source_bindings"])
    exact(parent["sources_after"],release["source_bindings"])
    exact(parent["inputs_before"],release["inputs"])
    exact(parent["inputs_after"],release["inputs"])
    prior = read(release["prior_work"])
    exact(parent["prior_work"],prior)
    exact(parent["native"],release["native"])
    native = read(release["native"]["result"])
    need(native["status"] == "COMPLETE_NINE_SENSOR_WHITE_DERIVATIVES_AWAITING_COVERAGE" and
         native["error"] is None and native["finalization_errors"] == [] and len(native["rows"]) == 9,
         "actual complete native prerequisite")
    old_audit_ref = pinned(HERE/"work/independent-native-sensor-white-artifact-1-audit.json",
                          "bb53b2437a0c6f0cbe45c9f4ee2a40e9fee540df9a4cc708d6acf60326094c28")
    old_audit = read(old_audit_ref)
    need(old_audit["subject_complete"] is True and verify(release["native"]["result"]) == old_audit["external"]["result"],
         "same actual independently audited native run")
    for key in ("console","outer","exit"):
        need(verify(release["native"][key]) == old_audit["external"][key], "same actual native root observation")
    native_final = last_json(release["native"]["console"])
    if parent["native_final_stdout"] is not None:
        exact(parent["native_final_stdout"],native_final)
    need(prior["cpu_seconds"] >= native_final["work_through_final_checks"]["cpu_seconds"] and
         Decimal(str(prior["wall_seconds"])) >= Decimal(old_audit["next_wall_seconds"]) and
         all(prior[k] >= native_final["work_through_final_checks"][k] for k in ("file_bytes","metadata_bytes")),
         "no refund of prior native/failed/deleted costs")
    preparation_carry = carry_association(release,prior,old_audit)
    rows = parent["admitted_inputs"]
    reservation = 0
    if rows is not None:
        need(len(rows) == 9 and [r["original_index"] for r in rows] == INDICES, "nine admitted originals before constructor")
        for i,(row,nrow,arow) in enumerate(zip(rows,native["rows"],old_audit["frames"],strict=True)):
            need(type(row["ordinal"]) is int and row["ordinal"] == i and type(row["original_index"]) is int and
                 row["primary_reused"] is (i == 0) and row["snapshot_retained_from_refused_run"] is (i == 0),
                 "typed ordinal and historical primary scope")
            for key in ("tiff","primary_receipt","independent_read"):
                need(row[key] == nrow[key] and verify(row[key]) == verify(arow[key]), "actual admitted product association")
            reader = read(row["independent_read"])
            need(reader["status"] == "PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY" and reader["error"] is None and
                 reader["finalization_errors"] == [] and row["active_sha256_u16_le"] == reader["active_sha256_u16_le"] and
                 row["tiff_pixel_sha256_u16_le"] == reader["tiff_pixel_sha256_u16_le"], "same admitted reader payloads")
        reservation = sum(r["tiff"]["bytes"] for r in rows)+5*MIB
    worker = None
    job = None
    detail = None
    check_receipt = None
    if parent["request"] is not None:
        request = read(parent["request"])
        need(path(parent["request"]["path"]) == OUT/"request.json" and
             request["schema"] == "m193c-sensor-white-coverage-request-v1" and
             request["execution_release"] == parent["execution_release"] and request["native_rows"] == rows and
             type(request["snapshot_reservation_bytes"]) is int and request["snapshot_reservation_bytes"] == reservation,
             "actual request carries exact admitted bytes and conservative snapshot reservation")
    if parent["child"] is not None:
        wcommand = replace(release["commands"]["worker"],args.release_sha256,parent["request"]["sha256"])
        job = actual_job(parent["child"],wcommand)
        need(all(parent["child"]["limits"][k] <= request["remaining_limits"][k] for k in request["remaining_limits"]),
             "preparation time not restored in actual child limits")
        need(all(parent["environment"][k] == "2" for k in
             ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS")) and
             not any(k.upper().startswith("PYTHON") for k in parent["environment"]), "actual clean/pre-import environment")
    if parent["worker_result"] is not None:
        worker = read(parent["worker_result"])
        need(path(parent["worker_result"]["path"]) == OUT/"worker/result.json" and
             worker["schema"] == "m193c-sensor-white-coverage-worker-v1" and worker["command"] == wcommand and
             worker["request"] == parent["request"] and worker["execution_release"] == parent["execution_release"],
             "actual worker request/source/command association")
        expected_runtime = read(CONTRACT)["reference_environment"]
        if worker["runtime_before"] is not None:
            exact(worker["runtime_before"],expected_runtime)
            exact(worker["runtime_after"],expected_runtime)
            for original in (CONSUMER,REFERENCE):
                copy = OUT/"worker/registrar"/original.parent.name/original.name
                actual = bind(copy,MIB)
                need(all(actual[k] == release["source_bindings"][original.relative_to(ROOT).as_posix()][k]
                         for k in ("sha256","bytes")), "byte-identical actual executed registrar copy")
        check_receipt = controls(worker)
        need(parent["first_refusal"] == worker["first_refusal"], "parent retains exact actual first registrar refusal")
        final_worker = last_json(parent["child"]["log"])
        need(final_worker["status"] == worker["status"] and final_worker["error"] == worker["error"] and
             final_worker["finalization_errors"] == worker["finalization_errors"] and
             path(final_worker["result"]) == OUT/"worker/result.json", "actual worker final stdout")
        if worker["status"] == SUCCESS:
            need(job["exit_code"] == 0 and job["clean"] and worker["native_stage"] == "complete" and
                 worker["error"] is None and worker["finalization_errors"] == [] and worker["first_refusal"] is None and
                 check_receipt["complete"], "actual worker0 and completed controlled registration")
            detail = completed_manifest(worker,rows)
        elif worker["status"] == "REGISTRAR_REFUSED":
            need(job["exit_code"] == 1 and job["clean"] and worker["native_stage"] == "refused" and
                 worker["native_manifest"] is None and worker["original_gauges"] is None and check_receipt["complete"] and
                 worker["error"] == worker["first_refusal"]["traceback"], "preserved registrar refusal, no invented output")
            refusal(worker["first_refusal"],ordered_groups(rows))
            detail = dict(first_refusal=worker["first_refusal"])
        else:
            need(worker["status"] == "REFUSED" and (worker["error"] or worker["finalization_errors"]),
                 "explicit wrapper/runtime/control failure distinct from registered native refusal")
            detail = dict(native_stage=worker["native_stage"],error=worker["error"],first_refusal=worker["first_refusal"])
    complete = parent["status"] == SUCCESS
    if complete:
        need(worker is not None and worker["status"] == SUCCESS and parent["error"] is None and
             parent["finalization_errors"] == [], "actual complete parent admission")
    else:
        need(parent["status"] == "REFUSED" and (parent["error"] or parent["finalization_errors"]), "actual retained parent refusal")
    need(type(outer["exit_code"]) is int and outer["exit_code"] == (0 if complete else 1) and
         outer["admissible_parent_exit"] is complete, "actual root exit; PASS string is insufficient")
    need(path(refs["exit"]["path"]).read_bytes().strip() == str(outer["exit_code"]).encode(), "saved direct root exit")
    final = last_json(refs["console"])
    need(final["status"] == parent["status"] and final["error"] == parent["error"] and
         final["finalization_errors"] == parent["finalization_errors"] and path(final["result"]) == OUT/"result.json",
         "actual root final stdout association")
    accounting = final["work_through_final_checks"]
    need(set(accounting) == {"cpu_accounting_complete","observed_child_cpu_seconds","cpu_scope",
         "snapshot_bytes_reserved_upper_bound","retained_output_bytes_measured","work_observed_or_lower_bound"}, "closed complete accounting")
    work = accounting["work_observed_or_lower_bound"]
    outputs,_ = descendants(OUT)
    reserved_dir = OUT/"worker/registrar/m193b-geometry-consumer"
    temp_paths = [p for p in outputs if p.parent == reserved_dir and p.name != "consumer.py"]
    need(not temp_paths,"no surviving owned TemporaryFile after actual Job closure")
    output_refs = [bind(p,256*MIB) for p in outputs]
    total = sum(r["bytes"] for r in output_refs)
    binaries = sum(r["bytes"] for r in output_refs if Path(r["path"]).suffix.lower() in (".tiff",".tif"))
    need(accounting["snapshot_bytes_reserved_upper_bound"] == reservation and
         accounting["retained_output_bytes_measured"] >= total, "actual snapshot charge/no hidden retained bytes")
    need(work["file_bytes"] >= prior["file_bytes"]+reservation+total and
         work["metadata_bytes"] >= prior["metadata_bytes"]+total-binaries, "no refund of reserved snapshots or measured writes")
    if parent["finalization_errors"] == []:
        need(accounting["retained_output_bytes_measured"] == total and
             work["file_bytes"] == prior["file_bytes"]+reservation+total and
             work["metadata_bytes"] == prior["metadata_bytes"]+total-binaries,"exact ordinary final extent accounting")
    if job is not None:
        need(accounting["cpu_accounting_complete"] is True and
             accounting["observed_child_cpu_seconds"] == job["cpu_seconds"] and
             accounting["cpu_scope"] == "terminal Job plus parent" and
             work["cpu_seconds"] >= prior["cpu_seconds"]+job["cpu_seconds"], "actual full Job CPU retained in global carry")
    if complete or (job is not None and job["clean"]):
        for key,limit in (("cpu_seconds",1200),("wall_seconds",1800),("file_bytes",4<<30),("metadata_bytes",128*MIB)):
            need(number(work[key]) and work[key] <= limit,"actual bounded complete resource "+key)
    need(number(outer["elapsed_wall_seconds"]),"actual root outer elapsed")
    next_wall = Decimal(str(prior["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"]))
    source_names = list(release["source_bindings"])
    tree = subprocess.run(["git","ls-tree","-r","--name-only",args.commit,"--",*source_names],cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()
    need(set(tree) == set(source_names),"all subject sources committed before actual invocation")
    # The committed pre-execution review explicitly recorded this one metadata difference.
    contract_name = CONTRACT.relative_to(ROOT).as_posix()
    changed = subprocess.run(["git","diff","--name-only",args.commit,"--",*source_names],cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()
    need(changed == [contract_name],"exact expected contract metadata difference; no other checkout changes")
    query = "".join(args.commit+":"+name+"\n" for name in source_names).encode()
    blobs = subprocess.run(["git","cat-file","--batch"],input=query,cwd=ROOT,capture_output=True,check=True).stdout
    cursor,corresponding,old_contract = 0,0,None
    for name in source_names:
        end = blobs.index(b"\n",cursor)
        header = blobs[cursor:end].split()
        need(len(header) == 3 and header[1] == b"blob","actual committed source blob")
        size = int(header[2]); start = end+1
        raw = blobs[start:start+size]
        need(len(raw) == size and blobs[start+size:start+size+1] == b"\n","complete Git blob framing")
        cursor = start+size+1
        current = path(name).read_bytes()
        if name == contract_name:
            old_contract = raw
            need(hashlib.sha256(raw).hexdigest() == "012a1ff307f78c79789d37a7cad0ab036f05a2331669f45c48543c492e8ccbd9" and
                 hashlib.sha256(current).hexdigest() == "19421729ac39273a5f61cda5068026f3458ba08c98f0aa954de7c219cbfabf47",
                 "exact recorded committed/released contract versions")
            old_fields,new_fields = strict(raw),strict(current)
            need(old_fields["status"] == "ALGORITHM_PRECOMMIT_NO_SCORING_OUTPUT_EXISTS" and
                 old_fields["algorithm_precommit_commit"] is None and
                 new_fields["status"] == "FROZEN_PRE_COMPARATOR_OUTPUT" and
                 new_fields["algorithm_precommit_commit"] == "dfaa2f639b85af0b568e7f8af1e8722548831c91",
                 "exact expected status/provenance values")
            new_fields.update(status=old_fields["status"],algorithm_precommit_commit=old_fields["algorithm_precommit_commit"])
            exact(new_fields,old_fields)
            restored = current.replace(b'"status": "FROZEN_PRE_COMPARATOR_OUTPUT"',b'"status": "ALGORITHM_PRECOMMIT_NO_SCORING_OUTPUT_EXISTS"').replace(
                b'"algorithm_precommit_commit": "dfaa2f639b85af0b568e7f8af1e8722548831c91"',b'"algorithm_precommit_commit": null')
            need(restored.replace(b"\r\n",b"\n") == raw.replace(b"\r\n",b"\n"),"only those two contract fields differ after newline normalization")
        else:
            need(current.replace(b"\r\n",b"\n") == raw.replace(b"\r\n",b"\n"),"committed source content correspondence: "+name)
            corresponding += 1
    need(cursor == len(blobs) and old_contract is not None and corresponding == 164 and len(source_names) == 165,
         "164 commit-corresponding sources plus one asserted expected metadata difference")
    review = HERE/"independent-sensor-white-coverage-release-2-review.md"
    review_ref = pinned(review,"e63563ec14b6da062a1f5cb53f94777c798f537785acf5f6de4aad28d49d1f8d",MIB)
    review_blob = subprocess.run(["git","show",args.commit+":"+review.relative_to(ROOT).as_posix()],cwd=ROOT,capture_output=True,check=True).stdout
    need(hashlib.sha256(review_blob).hexdigest() == review_ref["sha256"] and
         b"two pre-existing status/provenance field changes" in review_blob and
         b"claim every local byte is identical to a Git blob" in review_blob,"actual committed pre-execution scope disclosure")
    commit_scope = dict(corresponding_after_newline_normalization=corresponding,
                        expected_metadata_difference=dict(path=contract_name,committed_bytes=len(old_contract),
                            committed_sha256=hashlib.sha256(old_contract).hexdigest(),released=bind(CONTRACT),
                            fields=["status","algorithm_precommit_commit"]),preexecution_review=review_ref)
    raw_release = subprocess.run(["git","show",args.commit+":"+RELEASE.relative_to(ROOT).as_posix()],cwd=ROOT,capture_output=True,check=True).stdout
    need(hashlib.sha256(raw_release).hexdigest() == args.release_sha256,"actual committed release bytes")
    # Keep complete evidence in the actual controlled files instead of duplicating it in the audit stdout.
    if check_receipt is not None:
        check_receipt = dict(complete=check_receipt["complete"],count=len(check_receipt["records"]),
                            fixtures=check_receipt["fixtures"],records=[bind(OUT/("worker/control-"+r["id"]+".json"))
                            for r in check_receipt["records"]])
    # Digest checks above authenticate saved state; no published assertion relies on a recomputed registrar call.
    receipt = dict(schema="m193c-saved-sensor-white-coverage-audit-v1",status="PASS_SAVED_COVERAGE_OUTCOME_AUDIT",
                   subject_status=parent["status"],subject_complete=complete,worker_status=worker["status"] if worker else None,
                   external=refs,audit_source=bind(__file__,MIB),invocation=sys.orig_argv,commit=args.commit,
                   source_count=len(source_names),source_commit_scope=commit_scope,input_count=len(release["inputs"]),native_audit=old_audit_ref,
                   worker_result=parent["worker_result"],worker_job=job,controls=check_receipt,registration=detail,
                   runtime=worker["runtime_before"] if worker else None,actual_final_accounting=accounting,
                   prior_work=prior,preparation_carry=preparation_carry,next_wall_seconds=str(next_wall),output_count=len(output_refs),
                   retained_output_bytes=total,retained_fixture_bytes=binaries,unique_hashed_files=len(seen),
                   scope="Actual saved registration/control/Job evidence and exact reporting-gauge algebra; no registrar or decoder execution, new TIFF, placement-truth or common-TIFF qualification")
    raw = json.dumps(receipt,sort_keys=True,separators=(",",":"),allow_nan=False)
    need(len(raw.encode()) <= 32*1024,"bounded independent audit stdout")
    print(raw,flush=True)


if __name__ == "__main__":
    main()
