"""M194f fixed population launcher. Completion is not independent admission."""
import argparse
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("m194f_consumer_driver", HERE / "consumer-run.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
PRIVATE_TEST = "merge_cmd::known_scene_benchmark::joint_pupil_bridge::m194f_author_tests::m194f_private_coordinate_and_rank_controls"
MANIFEST = ROOT / "experiments/m194e-joint-pupil/cfa-emission-1/manifest.json"
MANIFEST_SHA = "f47c2b8720560fe9dbd777eeed3281ce2531f1f2287f5c88ef7b51a083d03299"
GATE = ROOT / "experiments/m194e-joint-pupil/independent-cfa-verification-1/cfa-commission.json"
GATE_SHA = "706462ad18a5a3846cadd99e1ef24d6b92b77e064df2e34cbe72e45907fc06a6"
RUNS = [("baseline-off", "off", False, 0), ("baseline-count", "count", False, 0),
        ("baseline-placebo", "placebo", False, 0), ("confidence-count", "count", True, 0),
        ("exposure-plus-one-count", "count", False, 1)]


def now():
    return datetime.now(timezone.utc).isoformat()


def ref(path):
    path = Path(path).resolve()
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=D.sha(path), bytes=path.stat().st_size)


def drivers():
    return {p.relative_to(ROOT).as_posix(): D.sha(p)
            for p in (Path(__file__).resolve(), HERE / "consumer-run.py")}


def admitted_build(args):
    if D.sha(args.build_record) != args.build_sha256:
        raise ValueError("external build SHA differs")
    b = D.load(args.build_record)
    if (b["schema"] != "m194f-consumer-build-v1" or b["pass"] is not True
            or b["driver_sha256"] != D.sha(HERE / "consumer-run.py")
            or b["sources_before"] != b["sources_after"] or b["sources_after"] != D.sources()):
        raise ValueError("build/source/driver disagreement")
    D.checked_executable(b)
    return b


def check_private_result(path):
    value = D.load(path)
    if (value["schema"] != "m194f-private-controls-v1" or value["status"] != "complete"
            or value["fixture_only"] is not True or set(value["rgb"]) != {"constant", "affine", "mutation"}
            or set(value["gray"]) != {"rank", "sentinel"}):
        raise ValueError("private component population incomplete")
    visited = set()
    for binding in [*value["rgb"].values(), *value["gray"].values()]:
        actual = Path(binding["path"]).resolve()
        if (str(actual).casefold() in visited or type(binding["bytes"]) is not int or binding["bytes"] <= 0
                or actual.stat().st_size != binding["bytes"] or D.sha(actual) != binding["sha256"]):
            raise ValueError("private output binding changed")
        visited.add(str(actual).casefold())
    return value


def check_dependency(value, name, build):
    exe = build["test_executable"]
    if value["test_executable"] != exe:
        raise ValueError(name + " executable differs")
    log = Path(value["log"])
    if D.sha(log) != value["log_sha256"]:
        raise ValueError(name + " log changed")
    if name == "private_command_record":
        expected = [exe["path"], "--exact", PRIVATE_TEST, "--ignored", "--test-threads=1", "--nocapture"]
        if (value["command"] != expected or not D.single_test_pass(log.read_bytes())
                or value["driver_before"] != value["driver_after"] or value["driver_after"] != drivers()):
            raise ValueError("private command or source completion differs")
        check_private_result(Path(value["result"]))
    else:
        expected = [exe["path"], "merge_cmd::known_scene_benchmark::joint_pupil_bridge::", "--test-threads=1", "--nocapture"]
        summaries = [line for line in log.read_text(encoding="utf-8").splitlines() if line.startswith("test result:")]
        if (value["command"] != expected or value["unchanged"] is not True
                or len(summaries) != 1 or re.fullmatch(
                    r"test result: ok\. 7 passed; 0 failed; 2 ignored; 0 measured; [0-9]+ filtered out; finished in [0-9.]+s",
                    summaries[0]) is None):
            raise ValueError("seven compiled controls did not complete")
        children = value["independent_results"]
        if type(children) is not list or len(children) != 6:
            raise ValueError("six independent groups required")
        visited = set()
        for binding in children:
            path = Path(binding["path"]).resolve()
            if (str(path).casefold() in visited or type(binding["bytes"]) is not int
                    or path.stat().st_size != binding["bytes"] or D.sha(path) != binding["sha256"]):
                raise ValueError("independent group binding differs")
            visited.add(str(path).casefold())
            result = D.load(path)
            checks = result["checks"]
            if (result["schema"] != "m194f-independent-input-controls-v1" or result["pass"] is not True
                    or type(result["check_count"]) is not int or result["check_count"] <= 0
                    or type(checks) is not list or len(checks) != result["check_count"]
                    or any(row["pass"] is not True for row in checks)):
                raise ValueError("independent group failed or incomplete")


def private(args):
    b = admitted_build(args)
    out = args.output.resolve()
    record = out.with_name(out.name + "-command.json")
    log = out.with_name(out.name + "-command.log")
    if any(p.exists() for p in (out, record, log)):
        raise ValueError("private population and command paths must be new")
    out.parent.mkdir(parents=True, exist_ok=True)
    before, driver_before = D.sources(), drivers()
    env = D.controlled_env()
    env["STREHL_M194F_PRIVATE_OUTPUT"] = str(out)
    command = [b["test_executable"]["path"], "--exact", PRIVATE_TEST,
               "--ignored", "--test-threads=1", "--nocapture"]
    start = now()
    p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, check=False)
    with log.open("xb") as stream:
        stream.write(p.stdout + p.stderr)
    after, driver_after = D.sources(), drivers()
    result = out / "private-controls.json"
    unchanged = (before == after and driver_before == driver_after
                 and D.sha(Path(b["test_executable"]["path"])) == b["test_executable"]["sha256"])
    result_error = None
    try:
        check_private_result(result)
    except (ValueError, OSError, KeyError, TypeError) as error:
        result_error = type(error).__name__ + ": " + str(error)
    passed = (p.returncode == 0 and D.single_test_pass(p.stdout + p.stderr)
              and result.is_file() and unchanged and result_error is None)
    evidence = dict(schema="m194f-private-command-v1", command=command,
                    interpreter_argv=sys.orig_argv, started_utc=start, ended_utc=now(),
                    exit_code=p.returncode, passed=passed, log=str(log), log_sha256=D.sha(log),
                    build_sha256=args.build_sha256, test_executable=b["test_executable"],
                    sources_before=before, sources_after=after, driver_before=driver_before,
                    driver_after=driver_after, environment=D.relevant_env(env))
    if result.is_file():
        evidence.update(result=str(result), result_sha256=D.sha(result))
    if result_error is not None:
        evidence["result_error"] = result_error
    D.write_new(record, evidence)
    print(dict(command_record=ref(record), passed=passed), flush=True)
    if not passed:
        print((p.stdout + p.stderr).decode("utf-8", "replace"), flush=True)
    return 0 if passed else 1


def renders(args):
    b = admitted_build(args)
    out = args.output.resolve()
    if out.exists():
        raise ValueError("new intended output directory required")
    dependencies = {}
    for name, path, pin, schema in (
            ("private_command_record", args.private_command_record, args.private_command_sha256, "m194f-private-command-v1"),
            ("controls_command_record", args.controls_command_record, args.controls_command_sha256, "m194f-controls-command-v1")):
        if D.sha(path) != pin:
            raise ValueError(name + " external digest differs")
        value = D.load(path)
        if (value["schema"] != schema or value["passed"] is not True
                or type(value["exit_code"]) is not int or value["exit_code"] != 0
                or value["build_sha256"] != args.build_sha256
                or value["sources_before"] != b["sources_after"]
                or value["sources_after"] != b["sources_after"]):
            raise ValueError(name + " did not complete on this build")
        check_dependency(value, name, b)
        dependencies[name] = ref(path)
        if name == "private_command_record":
            private_result = Path(value["result"])
            if D.sha(private_result) != value["result_sha256"]:
                raise ValueError("private result changed")
            dependencies["private_controls"] = ref(private_result)
    if D.sha(MANIFEST) != MANIFEST_SHA or D.sha(GATE) != GATE_SHA:
        raise ValueError("genuine authority changed")
    before, driver_before, start = D.sources(), drivers(), now()
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for name, observer, confidence, exposure in RUNS:
        run = out / name
        run.mkdir()
        plan, receipt = run / "plan.json", run / "receipt.json"
        common = dict(build_record=args.build_record, build_sha256=args.build_sha256,
                      manifest=MANIFEST, manifest_sha256=MANIFEST_SHA, cfa_commission=GATE,
                      cfa_commission_sha256=GATE_SHA, observer=observer, confidence=confidence,
                      exposure=exposure, plan=plan, log=None)
        if D.invoke(argparse.Namespace(mode="plan", **common)) != 0:
            return 1
        if D.invoke(argparse.Namespace(mode="render", **common, plan_sha256=D.sha(plan),
                    receipt=receipt, output=run / "output.tif",
                    confidence_output=run / "confidence.tif" if confidence else None)) != 0:
            return 1
        rows.append(dict(name=name, observer=observer, confidence=confidence, exposure=exposure,
                         plan=ref(plan), receipt=ref(receipt),
                         command_record=ref(receipt.with_suffix(".command.json")),
                         plan_command_record=ref(plan.with_suffix(".command.json"))))
    after, driver_after = D.sources(), drivers()
    if before != after or driver_before != driver_after:
        raise ValueError("sources changed during intended population")
    D.checked_executable(b)
    index = dict(schema="m194f-production-run-v1", status="OUTPUTS_COMPLETE_UNVERIFIED",
                 preregistration=ref(HERE / "preregister.md"), build=ref(args.build_record),
                 **dependencies, runs=rows, sources_before=before, sources_after=after,
                 driver_before=driver_before, driver_after=driver_after,
                 command=sys.argv, interpreter_argv=sys.orig_argv, started_utc=start, ended_utc=now())
    D.write_new(out / "run-index.json", index)
    print(ref(out / "run-index.json"), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("private", "renders"))
    p.add_argument("--build-record", type=Path, required=True)
    p.add_argument("--build-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    for prefix in ("private", "controls"):
        p.add_argument("--" + prefix + "-command-record", type=Path)
        p.add_argument("--" + prefix + "-command-sha256")
    args = p.parse_args()
    if args.mode == "renders" and any(getattr(args, field) is None for field in
            ("private_command_record", "private_command_sha256", "controls_command_record", "controls_command_sha256")):
        p.error("renders requires both previous command records and external digests")
    return private(args) if args.mode == "private" else renders(args)


if __name__ == "__main__":
    raise SystemExit(main())
