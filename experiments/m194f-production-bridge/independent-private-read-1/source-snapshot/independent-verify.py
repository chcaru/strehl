"""Actual eleven-TIFF M194f verification, independent of authored pixel summaries."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("m194f_independent_reader", HERE / "independent-reader.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

AUTHORITY = dict(manifest_sha256="f47c2b8720560fe9dbd777eeed3281ce2531f1f2287f5c88ef7b51a083d03299",
                 cfa_commission_sha256="706462ad18a5a3846cadd99e1ef24d6b92b77e064df2e34cbe72e45907fc06a6",
                 float_commission_sha256="4bd57b896be0b68c42fb1384a468a4f29cc54139a18a046a678dd97bad408217")
RUNS = [("baseline-off", "off", False, 0), ("baseline-count", "count", False, 0),
        ("baseline-placebo", "placebo", False, 0), ("confidence-count", "count", True, 0),
        ("exposure-plus-one-count", "count", False, 1)]
BASE_ENV = dict(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER="1",
                STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
TEST = "merge_cmd::known_scene_benchmark::joint_pupil_bridge::m194f_production_bridge"
PRIVATE_TEST = "merge_cmd::known_scene_benchmark::joint_pupil_bridge::m194f_author_tests::m194f_private_coordinate_and_rank_controls"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for raw in iter(lambda: stream.read(65536), b""):
            h.update(raw)
    return h.hexdigest()


def keys(value, expected, label):
    R.require(type(value) is dict and set(value) == set(expected), label + " keys")


def same(a, b, label):
    # Keep JSON booleans distinct from numbers. int/float remain distinct too;
    # actual serialized plan copies use the same representation.
    R.require(json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False), label)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def numeric_list(value, expected, label):
    R.require(type(value) is list and len(value) == len(expected)
              and all(type(a) in (int,float) and np.isfinite(a) and a == b
                      for a,b in zip(value,expected,strict=True)), label)


def unique(items):
    result = {}
    for key, value in items:
        R.require(key not in result, "duplicate JSON key " + key)
        result[key] = value
    return result


def load(path, digest=None):
    with Path(path).open("rb") as stream:
        raw = stream.read(R.LIMIT + 1)
    R.require(len(raw) <= R.LIMIT, "bounded JSON")
    R.require(digest is None or R.digest(raw) == digest, "external JSON SHA")
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(R.Refusal("nonfinite JSON " + value)))


def repository_path(value):
    R.require(type(value) is str and value and "\\" not in value, "repository POSIX path")
    relative = PurePosixPath(value)
    R.require(not relative.is_absolute() and ":" not in value and
              all(part not in (".", "..", "") for part in value.split("/")), "relative path traversal")
    path = (ROOT / value).resolve()
    R.require(path.is_relative_to(ROOT), "resolved repository containment")
    return path


def artifact_path(value):
    # Rust receipts deliberately emit canonical absolute workspace paths.
    R.require(type(value) is str, "artifact path type")
    path = Path(value).resolve()
    R.require(path.is_relative_to(ROOT), "artifact containment")
    return path


def file_ref(ref):
    keys(ref, ("path", "sha256", "bytes"), "FileRef")
    R.require(integer(ref["bytes"], 1) and re.fullmatch("[0-9a-f]{64}", ref["sha256"]) is not None, "FileRef values")
    path = repository_path(ref["path"])
    R.require(path.is_file() and path.stat().st_size == ref["bytes"] and sha(path) == ref["sha256"], "actual FileRef binding")
    return path


def check_source_map(source_map):
    R.require(type(source_map) is dict and source_map, "nonempty source map")
    for relative, expected in source_map.items():
        R.require(sha(repository_path(relative)) == expected, "current source differs " + relative)


def check_build(ref, external_sha):
    R.require(ref["sha256"] == external_sha, "external build authority")
    path = file_ref(ref)
    build = load(path, external_sha)
    R.require(build["schema"] == "m194f-consumer-build-v1" and build["pass"] is True
              and build["exit_code"] == 0 and build["rebuilt_cli"] is True, "successful rebuilt compiler record")
    same(build["sources_before"], build["sources_after"], "compiled source stable")
    check_source_map(build["sources_after"])
    R.require(sha(HERE / "consumer-run.py") == build["driver_sha256"], "compiled driver pin")
    log = artifact_path(build["log"])
    R.require(sha(log) == build["log_sha256"] and b"Compiling strehl-cli" in log.read_bytes(), "actual compile log")
    expected_command = ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl", "--target-dir",
                        "target/m194f-production-bridge", "--no-run", "--message-format=json-render-diagnostics"]
    same(build["command"], expected_command, "build command")
    same(build["environment"], BASE_ENV, "build environment")
    artifact = build["compiler_artifact_message"]
    R.require(artifact["reason"] == "compiler-artifact" and artifact["target"]["name"] == "strehl"
              and artifact["profile"]["test"] is True, "compiler message kind")
    R.require(any(line.startswith(b"{") and json.loads(line) == artifact
                  for line in log.read_bytes().splitlines() if line.startswith(b"{")), "actual compiler artifact message")
    original, copied = build["compiler_artifact"], build["test_executable"]
    for record in (original, copied):
        executable = artifact_path(record["path"])
        R.require(executable.stat().st_size == record["bytes"] and sha(executable) == record["sha256"], "actual executable hash")
    R.require(artifact_path(artifact["executable"]) == artifact_path(original["path"])
              and original["sha256"] == copied["sha256"] and original["bytes"] == copied["bytes"]
              and build["copy_matches_compiler_artifact"] is True, "compiler-to-copied artifact lineage")
    return build


def check_plan(plan, run, build):
    R.require(plan["schema"] == "m194f-consumer-plan-v1", "plan schema")
    same(plan["authority"], AUTHORITY, "genuine input authority")
    same(plan["full_native"], [64,48], "input native extent")
    same(plan["full_quad"], [32,24], "input quad extent")
    same(plan["environment"], BASE_ENV, "plan environment")
    R.require(plan["reference_original_index"] == plan["reference_local_index"] == 2, "frame2 gauge")
    R.require(plan["output_channels"] == 3, "output channels")
    crop = plan["crop_quad"]
    keys(crop, ("x", "y", "width", "height"), "crop")
    R.require(all(integer(v) for v in crop.values()) and crop["width"] > 0 and crop["height"] > 0
              and crop["x"]+crop["width"] <= 32 and crop["y"]+crop["height"] <= 24, "bounded crop")
    same(plan["canonical_native_offset"], [crop["x"]*2,crop["y"]*2], "quad-to-native origin")
    same(plan["output_native"], [crop["width"]*2,crop["height"]*2], "quad-to-native size")
    R.require(plan["cover_fit"]["kind"] == "Crop", "actual cover disposition")
    R.require(len(plan["level_sizes"]) == 2 and plan["level_sizes"][0] == [crop["width"],crop["height"]], "one band plus base")
    for i, placement in enumerate(plan["placements"]):
        R.require(placement["original_index"] == placement["local_index"] == i, "original/local identity")
        same(placement["quad_similarity"], dict(a_re=1.0,a_im=0.0,b_re=0.0,b_im=0.0), "identity placement")
    R.require(len(plan["placements"]) == 5, "five placements")
    R.require(plan["wb_f32"] == [float(np.float32(4/3)),1.0,float(np.float32(5/3))], "represented WB")
    n = plan["normalization"]
    R.require(n["tiff_u16_to_dn"] == R.RANGE/65535 and n["second_black_subtraction"] is False
              and n["input_rounding"] == "ties-to-even" and n["output_rounding"] == "half-up after clipping", "normalization convention")
    noise = plan["noise"]
    for key, value in dict(gain_dn_per_e=.25, read_noise_e=4, black=512, white=15360, iso=160).items():
        R.require(type(noise[key]) in (int,float) and noise[key] == value, "injected noise " + key)
    R.require(noise["prnu"] is False and noise["provenance"] == "Fallback: injected synthetic algorithm coefficients; noise draws off", "noise scope")
    config = plan["config"]
    fixed = dict(merge="Pyramid",bands=3,gate=2.0,exponent=2.0,select="SoftPower",base="Mean",admission="HardFloor",
                 mean_coarse=0,hull="InputRange",resampler="CatmullRom",demosaic="MHC",space="CameraLinear",
                 fullres_gather=True,auto_exposure=False,photometric="Off",gate_floor_enabled=True,
                 measured_floor_bands=0,floor_fallback="empty measured beta; existing per-band fixed beta",
                 ca="off",defect="off",restoration="unset")
    for key, value in fixed.items():
        R.require(type(config[key]) is type(value) and config[key] == value, "effective config " + key)
    R.require(type(config["confidence"]) is bool and config["confidence"] == run["confidence"]
              and type(config["exposure_stops"]) is int and config["exposure_stops"] == run["exposure"], "run settings consumed")
    same(plan["observer"], dict(mode=run["observer"], excludes_planning_reads=True, excludes_raw_prologue=True), "observer scope")
    R.require(plan["build"]["test_executable_sha256"] == build["test_executable"]["sha256"]
              and plan["build"]["bytes"] == build["test_executable"]["bytes"], "actual plan executable")
    for record in plan["input_bindings"].values():
        path = artifact_path(record["path"])
        R.require(path.stat().st_size == record["bytes"] and sha(path) == record["sha256"], "actual admitted input/source")
    return crop


def check_command(command, run, build, build_sha, mode="render"):
    R.require(command["schema"] == "m194f-consumer-command-v1" and command["passed"] is True
              and command["exit_code"] == 0 and command["sources_unchanged"] is True, "terminal command")
    R.require(command["build_sha256"] == build_sha and command["driver_sha256"] == build["driver_sha256"], "command build/driver")
    target = run["receipt"] if mode == "render" else run["plan"]
    R.require(artifact_path(command["result"]) == file_ref(target)
              and command["result_sha256"] == target["sha256"], "command result association")
    expected = [str(artifact_path(build["test_executable"]["path"])),"--exact",TEST,"--ignored","--test-threads=1","--nocapture"]
    same(command["command"], expected, "actual child command")
    log = artifact_path(command["log"])
    check_test_log(log,command["log_sha256"],1)
    env = command["environment"]
    same({k:v for k,v in env.items() if not k.startswith("STREHL_M194F_")},BASE_ENV,"child render environment")
    fields = dict(MODE=mode,OBSERVER=run["observer"],CONFIDENCE=str(int(run["confidence"])),EXPOSURE=str(run["exposure"]),
                  MANIFEST_SHA256=AUTHORITY["manifest_sha256"],CFA_COMMISSION_SHA256=AUTHORITY["cfa_commission_sha256"])
    if mode == "render":
        fields["PLAN_SHA256"] = run["plan"]["sha256"]
    for key,value in fields.items():
        R.require(env["STREHL_M194F_"+key] == value, "child argument " + key)
    extras = {"MANIFEST","CFA_COMMISSION","PLAN"}
    if mode == "render":
        extras.update(("RECEIPT","OUTPUT"))
        if run["confidence"]:extras.add("CONFIDENCE_OUTPUT")
    same(set_as_list(env),sorted([*BASE_ENV]+["STREHL_M194F_"+k for k in set(fields)|extras]),"closed child environment")
    R.require(artifact_path(env["STREHL_M194F_PLAN"]) == file_ref(run["plan"]), "child plan path")
    if mode == "render":
        R.require(artifact_path(env["STREHL_M194F_RECEIPT"]) == file_ref(run["receipt"]), "child receipt path")
    for key,pin in (("MANIFEST",AUTHORITY["manifest_sha256"]),("CFA_COMMISSION",AUTHORITY["cfa_commission_sha256"])):
        R.require(sha(artifact_path(env["STREHL_M194F_"+key])) == pin,"child actual authority file")
    return env


def set_as_list(value):
    return sorted(value)


def check_test_log(path, expected_sha, count, ignored=0):
    R.require(sha(path) == expected_sha,"actual command log hash")
    lines = [line for line in path.read_text(encoding="utf-8",errors="replace").splitlines() if line.startswith("test result:")]
    R.require(len(lines) == 1 and re.fullmatch(
        rf"test result: ok\. {count} passed; 0 failed; {ignored} ignored; 0 measured; [0-9]+ filtered out; finished in [0-9.]+s",lines[0]) is not None,
        "actual terminal test count")


def check_run_bindings(value, build, drivers):
    same(value["sources_before"],build["sources_after"],"run source-before build binding")
    same(value["sources_after"],build["sources_after"],"run source-after build binding")
    same(value["driver_before"],drivers,"run driver-before binding")
    same(value["driver_after"],drivers,"run driver-after binding")


def check_private_command(command, private_ref, build, build_sha, drivers):
    keys(command,("schema","command","interpreter_argv","started_utc","ended_utc","exit_code","passed",
                  "log","log_sha256","build_sha256","test_executable","sources_before","sources_after",
                  "driver_before","driver_after","environment","result","result_sha256"),"private wrapper")
    R.require(command["schema"] == "m194f-private-command-v1" and command["passed"] is True
              and type(command["exit_code"]) is int and command["exit_code"] == 0
              and command["build_sha256"] == build_sha,"private wrapper terminal build")
    same(command["test_executable"],build["test_executable"],"private compiled executable")
    same(command["command"],[build["test_executable"]["path"],"--exact",PRIVATE_TEST,"--ignored","--test-threads=1","--nocapture"],"private actual child command")
    check_run_bindings(command,build,drivers)
    check_test_log(artifact_path(command["log"]),command["log_sha256"],1)
    result = file_ref(private_ref)
    R.require(artifact_path(command["result"]) == result and command["result_sha256"] == private_ref["sha256"],"private actual result")
    same(command["environment"],dict(BASE_ENV,STREHL_M194F_PRIVATE_OUTPUT=str(result.parent)),"private environment/output root")


def check_controls_command(controls, build, build_sha):
    R.require(controls["schema"] == "m194f-controls-command-v1" and controls["passed"] is True
              and type(controls["exit_code"]) is int and controls["exit_code"] == 0
              and controls["build_sha256"] == build_sha and controls["unchanged"] is True,"actual prerequisite control wrapper")
    same(controls["test_executable"],build["test_executable"],"controls compiled executable")
    for key in ("sources_before","sources_after","source_set_after"):
        same(controls[key],build["sources_after"],"controls source closure " + key)
    same(controls["owned_before"],controls["owned_after"],"controls owned source stable")
    for name,pin in controls["owned_after"].items():
        R.require(sha(artifact_path(str(ROOT/name))) == pin,"actual owned control source")
    same(controls["environment"],BASE_ENV,"controls environment")
    same(controls["command"],[build["test_executable"]["path"],
         "merge_cmd::known_scene_benchmark::joint_pupil_bridge::","--test-threads=1","--nocapture"],"focused seven-test command")
    check_test_log(artifact_path(controls["log"]),controls["log_sha256"],7,2)
    R.require(type(controls["independent_results"]) is list and len(controls["independent_results"]) == 6,"complete six independent input result records")
    count, paths = 0, set()
    for ref in controls["independent_results"]:
        keys(ref,("path","sha256","bytes"),"control result reference")
        path=artifact_path(ref["path"])
        R.require(path not in paths,"unique control result files");paths.add(path)
        R.require(path.stat().st_size == ref["bytes"] and sha(path) == ref["sha256"],"actual input control result")
        value=load(path,ref["sha256"])
        R.require(value["schema"] == "m194f-independent-input-controls-v1" and value["pass"] is True
                  and integer(value["check_count"],1) and value["check_count"] == len(value["checks"]),"terminal independent input checks")
        R.require(all(c["pass"] is True for c in value["checks"]),"all actual independent input checks passed")
        count += value["check_count"]
    R.require(count == controls["check_count"],"complete control check count")


def read_output(record, kind, shape):
    path = artifact_path(record["path"])
    pixels, own = R.read_tiff(path,kind,shape,record["sha256"])
    R.require(record["bytes"] == own["bytes"] and record["width"] == shape[1]
              and record["height"] == shape[0] and record["channels"] == (3 if kind == "rgb" else 1)
              and record["sample_type"] == "u16" and record["pixel_sha256_le"] == own["pixel_sha256"], "receipt actual TIFF agreement")
    R.require(record["software"] == (R.SOFTWARE if kind == "rgb" else None), "receipt software disposition")
    return pixels, own


def verify_private(private):
    R.require(private["schema"] == "m194f-private-controls-v1" and private["status"] == "complete"
              and private["fixture_only"] is True, "private component scope")
    same(private["crop_quad"],dict(x=3,y=5,width=24,height=16),"private unequal crop")
    same(private["canonical_native_offset"],[6,10],"private native offset")
    same(private["oracle_output_window"],[14,14,34,18],"fixed80 sites")
    keys(private["rgb"],("constant","affine","mutation"),"private RGB population")
    keys(private["gray"],("rank","sentinel"),"private Gray population")
    keys(private["rgb_successful_decode_counts"],("constant","affine","mutation"),"private RGB decode population")
    for counts in private["rgb_successful_decode_counts"].values():
        same(counts,[1]*5,"actual private RGB one decode")
    arrays, evidence = {}, {}
    for scene in ("constant","affine","mutation"):
        arrays[scene], evidence[scene] = read_output(private["rgb"][scene],"rgb",(32,48,3))
        if scene != "mutation":
            evidence[scene]["oracle"] = R.coordinate_check(arrays[scene],scene)
    evidence["mutation"]["oracle"] = R.mutation_check(arrays["affine"],arrays["mutation"])
    c = private["confidence_component"]
    same(c["native"],[32,16],"component native geometry")
    same(c["quad"],[16,8],"component quad geometry")
    numeric_list(c["input_green_dn"],[100,200,200,400,500],"green input luma")
    numeric_list(c["merged_luma_dn"],[99,100,200,201,300,400,500,501]*16,"direct merged-luma targets")
    same(c["successful_decode_counts"],[1]*5,"actual component one decode")
    R.require(type(c["sentinel_index"]) is int and c["sentinel_index"] == 0
              and type(c["reached_zero_index"]) is int and c["reached_zero_index"] == 1,"actual sentinel/zero locations")
    for key in ("below","seen","sentinel_below","sentinel_seen"):
        R.require(len(c[key]) == 128 and all(integer(v) for v in c[key]), "actual integer counts " + key)
    for name, b, s, sentinel in (("rank","below","seen",None),("sentinel","sentinel_below","sentinel_seen",0)):
        arrays[name], evidence[name] = read_output(private["gray"][name],"gray",(8,16))
        evidence[name]["oracle"] = R.rank_check(arrays[name],c[b],c[s],sentinel)
    R.require(int(arrays["sentinel"].flat[1]) == 0,"reached-zero value")
    return evidence


def verify(index_path, index_sha, build_sha):
    index = load(index_path,index_sha)
    keys(index,("schema","status","preregistration","build","private_controls","private_command_record",
                "controls_command_record","runs","sources_before","sources_after","driver_before","driver_after",
                "command","interpreter_argv","started_utc","ended_utc"),"final index")
    R.require(index["schema"] == "m194f-production-run-v1" and index["status"] == "OUTPUTS_COMPLETE_UNVERIFIED", "complete unverified eleven-file index")
    file_ref(index["preregistration"])
    build = check_build(index["build"],build_sha)
    drivers = {p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/"consumer-run.py",HERE/"run-commission.py")}
    check_run_bindings(index,build,drivers)
    check_private_command(load(file_ref(index["private_command_record"])),index["private_controls"],build,build_sha,drivers)
    controls = load(file_ref(index["controls_command_record"]))
    check_controls_command(controls,build,build_sha)
    R.require(len(index["runs"]) == 5,"complete five genuine runs")
    results, pixels, plans = {}, {}, []
    for run, expected in zip(index["runs"],RUNS,strict=True):
        keys(run,("name","observer","confidence","exposure","plan","receipt","command_record","plan_command_record"),"genuine run")
        same([run["name"],run["observer"],run["confidence"],run["exposure"]],list(expected),"fixed ordered run matrix")
        plan = load(file_ref(run["plan"]))
        receipt = load(file_ref(run["receipt"]))
        command = load(file_ref(run["command_record"]))
        check_command(load(file_ref(run["plan_command_record"])),run,build,build_sha,"plan")
        crop = check_plan(plan,run,build)
        env = check_command(command,run,build,build_sha)
        R.require(receipt["schema"] == "m194f-consumer-receipt-v1" and receipt["status"] == "complete"
                  and receipt["inputs_unchanged"] is True and receipt["plan_sha256"] == run["plan"]["sha256"],"complete bound receipt")
        same(receipt["plan"],plan,"receipt actual plan")
        calls = 2 if run["confidence"] else 1
        same(receipt["successful_decode_counts"],[calls if run["observer"] == "count" else 0]*5,"successful decode observer")
        R.require(type(receipt["hook_calls"]) is int and receipt["hook_calls"] == (0 if run["observer"] == "off" else calls*5),"hook count witness")
        shape = (crop["height"]*2,crop["width"]*2,3)
        pixels[run["name"]], actual = read_output(receipt["output"],"rgb",shape)
        R.require(artifact_path(env["STREHL_M194F_OUTPUT"]) == artifact_path(receipt["output"]["path"]),"child output path")
        results[run["name"]] = dict(rgb=actual,successful_decode_counts=receipt["successful_decode_counts"],hook_calls=receipt["hook_calls"])
        if run["confidence"]:
            gray, gray_evidence = read_output(receipt["confidence"],"gray",(crop["height"],crop["width"]))
            gray_evidence["oracle"] = R.genuine_confidence_check(gray,(crop["height"],crop["width"]))
            R.require(artifact_path(env["STREHL_M194F_CONFIDENCE_OUTPUT"]) == artifact_path(receipt["confidence"]["path"]),"child confidence path")
            results[run["name"]]["gray"] = gray_evidence
        else:
            R.require(receipt["confidence"] is None and "STREHL_M194F_CONFIDENCE_OUTPUT" not in env,"disabled confidence output")
        normalized = copy.deepcopy(plan)
        normalized["observer"]["mode"] = "off"
        normalized["config"]["confidence"] = False
        normalized["config"]["exposure_stops"] = 0
        plans.append(normalized)
    for plan in plans[1:]:
        same(plan,plans[0],"only preregistered settings differ across plans")
    for name in ("baseline-count","baseline-placebo","confidence-count"):
        R.require(results[name]["rgb"]["sha256"] == results["baseline-off"]["rgb"]["sha256"]
                  and np.array_equal(pixels[name],pixels["baseline-off"]),"actual observer/confidence RGB byte null " + name)
    changed = pixels["exposure-plus-one-count"] != pixels["baseline-count"]
    R.require(bool(changed.any()),"exposure control actual pixels must change")
    private = verify_private(load(file_ref(index["private_controls"])))
    outputs = [item["rgb"] for item in results.values()] + [results["confidence-count"]["gray"]] + list(private.values())
    R.require(len(outputs) == 11 and len({p["path"] for p in outputs}) == 11,"eleven distinct actual TIFFs")
    check_source_map(build["sources_after"])
    same(drivers,{p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/"consumer-run.py",HERE/"run-commission.py")},"drivers unchanged through independent read")
    R.require(sha(index_path) == index_sha,"index unchanged through independent read")
    return dict(status="PASS_DELIVERED_TIFF_VALUES",scope="bounded production integration, no quality or optical-confidence claim",
                genuine=results,private=private,tiff_count=11,
                exposure_changed_samples=int(changed.sum()),input_plan=plans[0],
                source_map=build["sources_after"],index_sha256=index_sha,build_sha256=build_sha)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index",type=Path,required=True)
    ap.add_argument("--index-sha256",required=True)
    ap.add_argument("--build-sha256",required=True)
    ap.add_argument("--reader-controls",type=Path,required=True)
    ap.add_argument("--reader-controls-sha256",required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    snapshot=out/"source-snapshot";snapshot.mkdir()
    sources=[Path(__file__),HERE/"independent-reader.py",HERE/"independent-reader-preregister.md"]
    before={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    for p in sources:shutil.copyfile(p,snapshot/p.name)
    result=dict(schema="m194f-independent-delivered-verification-v1",status="RUNNING",orig_argv=sys.orig_argv,
                executable=sys.executable,python=sys.version,platform=platform.platform(),numpy=np.__version__,
                xoptions=sys._xoptions,source_before=before,
                thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")},
                started_utc=datetime.now(timezone.utc).isoformat())
    start,cpu=time.perf_counter(),time.process_time()
    try:
        controls=load(args.reader_controls,args.reader_controls_sha256)
        R.require(controls["status"] == "PASS_READER_INSTRUMENT_ONLY" and controls["source_unchanged"] is True
                  and controls["passed"] == controls["count"] == 59,"actual commissioned reader controls")
        R.require(controls["source_after"][str(Path("experiments/m194f-production-bridge/independent-reader.py"))] == sha(HERE/"independent-reader.py"),"reader commissioning source pin")
        result.update(verify(args.index,args.index_sha256,args.build_sha256))
    except Exception as error:
        result.update(status="FAIL_DELIVERED_TIFF_VERIFICATION",error=repr(error),traceback=traceback.format_exc())
    result.update(source_after={p.relative_to(ROOT).as_posix():sha(p) for p in sources},
                  wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,
                  ended_utc=datetime.now(timezone.utc).isoformat())
    result["source_unchanged"]=result["source_before"]==result["source_after"]
    if not result["source_unchanged"]:result["status"]="FAIL_SOURCE_CHANGED"
    (out/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],result_sha256=sha(out/"result.json"))))
    return 0 if result["status"] == "PASS_DELIVERED_TIFF_VALUES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
