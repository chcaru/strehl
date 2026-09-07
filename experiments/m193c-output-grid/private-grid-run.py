"""Actual fixed10 plans, precision component and renders; no quality admission."""
import time
START_CPU, START_WALL = time.process_time(), time.monotonic()
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASES = ("identity-nine", "curved-nine-off", "curved-nine-count", "curved-nine-placebo",
         "curved-nine-scale", "original-one-correct", "original-one-swapped",
         "original-one-restored", "original-one-inverse", "constant-nine-null")
TEST = "merge_cmd::production_truth::m193c_output_grid::m193c_private_output_case"
PRECISION = "merge_cmd::production_truth::m193c_output_grid::precision_witness::m193c_private_precision_witness"
BASE_ENV = dict(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER="1",
                STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")


def need(ok, message):
    if not ok:
        raise ValueError(message)


def binding(path):
    h, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while raw := stream.read(1 << 20):
            h.update(raw); size += len(raw)
    return dict(sha256=h.hexdigest(), bytes=size)


def ref(path):
    return dict(path=path.resolve().relative_to(ROOT).as_posix(), **binding(path))


def path(value):
    need(type(value) is dict and set(value) == {"path", "sha256", "bytes"}, "closed file reference")
    need(type(value["path"]) is str and type(value["bytes"]) is int and value["bytes"] > 0,
         "file reference scalar types")
    p = Path(value["path"])
    p = (p if p.is_absolute() else ROOT/p).resolve(strict=True)
    need(p.is_relative_to(ROOT) and p.is_file(), "file reference containment")
    return p


def strict(raw):
    def unique(items):
        out = {}
        for k, v in items:
            need(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    def nonfinite(value):
        raise ValueError("nonfinite JSON token " + value)
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    def finite(item):
        if isinstance(item, float):
            need(math.isfinite(item), "nonfinite JSON number")
        elif isinstance(item, dict):
            for child in item.values():
                finite(child)
        elif isinstance(item, list):
            for child in item:
                finite(child)
    finite(value)
    return value


class Attempt:
    def __init__(self, output, release, release_ref):
        self.output, self.release, self.release_ref = output, release, release_ref
        self.child_cpu, self.artifact_bytes = 0., 0
        self.inputs, self.outputs = {}, {}
        self.observed_sizes = {}
        self.cpu_accounting_complete = True

    def inventory(self):
        # Path.rglob includes hidden files. Count unfinished child writes too;
        # this is separate from the immutable, successfully collected outputs.
        for p in self.output.rglob("*"):
            need(not p.is_symlink() and p.resolve().is_relative_to(self.output), "owned artifact containment")
            if p.is_file():
                name, size = p.relative_to(ROOT).as_posix(), p.stat().st_size
                old = self.observed_sizes.get(name, 0)
                self.artifact_bytes += max(0, size-old)
                self.observed_sizes[name] = size

    def budget(self):
        self.inventory()
        need(time.monotonic()-START_WALL <= 1200, "private producer wall allowance")
        need(time.process_time()-START_CPU+self.child_cpu <= 600, "private producer CPU allowance")
        need(self.artifact_bytes <= 128 << 20, "private producer artifact allowance")

    def track(self, value):
        p = path(value)
        need(binding(p) == {k: value[k] for k in ("sha256", "bytes")}, "bound input changed")
        normalized = dict(path=p.relative_to(ROOT).as_posix(), sha256=value["sha256"], bytes=value["bytes"])
        old = self.inputs.setdefault(normalized["path"], normalized)
        need(old == normalized, "conflicting input binding")
        self.budget()
        return p

    def read(self, value, cap=4 << 20):
        p = path(value)
        need(value["bytes"] <= cap, "bounded JSON input")
        with p.open("rb") as stream:
            raw = stream.read(cap+1)
        need(len(raw) == value["bytes"] and hashlib.sha256(raw).hexdigest() == value["sha256"], "actual parse bytes")
        normalized = dict(path=p.relative_to(ROOT).as_posix(), sha256=value["sha256"], bytes=value["bytes"])
        need(self.inputs.setdefault(normalized["path"], normalized) == normalized, "repeated parse binding")
        self.budget()
        return strict(raw)

    def save(self, name, value):
        raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
        need(len(raw) <= 4 << 20, "bounded result JSON")
        p = self.output/name
        self.budget()
        # A rewritten result consumes new write work even at the same pathname.
        # Reserve the whole write even if persistence later stops partway.
        self.artifact_bytes += len(raw)
        need(self.artifact_bytes <= 128 << 20, "private producer reserved artifact allowance")
        try:
            with p.open("wb") as f:
                need(f.write(raw) == len(raw), "short result write")
                f.flush(); os.fsync(f.fileno())
        finally:
            self.observed_sizes[p.relative_to(ROOT).as_posix()] = p.stat().st_size if p.exists() else 0
        r = ref(p)
        need(r["bytes"] == len(raw) and r["sha256"] == hashlib.sha256(raw).hexdigest(), "result persistence")
        self.outputs[r["path"]] = r
        return r

    def collect(self, p):
        r = ref(p)
        need(r["path"] not in self.outputs, "duplicate produced artifact")
        self.outputs[r["path"]] = r
        self.budget()
        return r

    def closure(self):
        self.track(self.release_ref)
        for name, item in self.release["source_bindings"].items():
            self.track(dict(path=name, **item))
        for item in self.release["inputs"]:
            self.track(item)
        for item in list(self.inputs.values()) + list(self.outputs.values()):
            need(ref(path(item)) == item, "source/input/output changed through publication")
            self.budget()


def load_source(name, attempt):
    relative = (HERE/name).relative_to(ROOT).as_posix()
    wanted = attempt.release["source_bindings"][relative]
    p = ROOT/relative
    raw = p.read_bytes()
    need(dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)) == wanted, "actual imported source bytes")
    spec = importlib.util.spec_from_file_location("m193c_"+p.stem.replace("-", "_"), p)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(p), "exec"), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser()
    for name in ("release", "build", "controls"):
        parser.add_argument("--"+name, type=Path, required=True)
        parser.add_argument("--"+name+"-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    for p in (a.release, a.build, a.controls, a.output):
        need(p.is_absolute() and p.resolve().is_relative_to(ROOT), "absolute workspace execution path")
    with a.release.open("rb") as f:
        raw = f.read((4 << 20)+1)
    need(len(raw) <= 4 << 20 and hashlib.sha256(raw).hexdigest() == a.release_sha256, "release hash/extent")
    release = strict(raw)
    need(set(release) == {"schema", "scope", "source_bindings", "inputs", "commands"}
         and release["schema"] == "m193c-execution-release-v1" and release["scope"] == "private-grid-run", "private release schema")
    need(list(sys.orig_argv) in [[a.release_sha256 if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in c]
                               for c in release["commands"]], "actual private command")
    a.output.mkdir(parents=True, exist_ok=False)
    release_ref = dict(path=a.release.resolve().relative_to(ROOT).as_posix(), sha256=a.release_sha256, bytes=len(raw))
    attempt = Attempt(a.output, release, release_ref)
    result = dict(schema="m193c-private-grid-run-v1", status="UNCOMMISSIONED_PRIVATE_OUTPUTS",
                  release=release_ref, build=ref(a.build), controls=ref(a.controls), command=list(sys.orig_argv),
                  sources_before=release["source_bindings"], sources_after=None, inputs_before=None, inputs_after=None,
                  entries=[], precision=None, failed_launch=None, last_launch=None, active_launch=None, owned_artifacts=[],
                  work=None, error=None, finalization_errors=[])
    try:
        required = {"experiments/m193c-output-grid/"+name for name in
                    ("private-grid-run.py", "bounded-process.py", "bridge-build.py")}
        required.add("experiments/m12-scorecard/m12-harness.py")
        need(required <= set(release["source_bindings"]), "required actual producer/helper sources")
        attempt.closure()
        need(result["build"]["sha256"] == a.build_sha256 and result["controls"]["sha256"] == a.controls_sha256, "external prerequisite pins")
        need(result["build"] in release["inputs"] and result["controls"] in release["inputs"], "released actual prerequisites")
        control = attempt.read(result["controls"])
        need(control["schema"] == "m193c-controller-controls-v1" and control["status"] == "PASS_OWNED_PROCESS_CONTROLS_ONLY"
             and control["error"] is None and control["finalization_errors"] == []
             and [r["mode"] for r in control["cases"]] == ["valid", "nonzero", "exact-log", "overflow-log", "timeout",
                 "nested-timeout", "memory-allowed", "memory", "late-log-binding", "changed-input", "restored",
                 "drain-finish", "drain-persist", "drain-restored"]
             and all(r["passed"] is True and r["actual"]["terminal_job_accounting"] is True
                     and r["actual"]["job_accounting"]["active_processes"] == 0 for r in control["cases"]),
             "complete controller instruments")
        need(control["sources_before"] == control["sources_after"], "controller source closure")
        control_release = attempt.read(control["release"])
        need(control_release["schema"] == "m193c-execution-release-v1" and control_release["scope"] == "controller-controls"
             and control_release["source_bindings"] == control["sources_before"], "controller prerequisite scope")
        for item in control["artifacts"]:
            attempt.track(item)
        for name, item in control["sources_before"].items():
            attempt.track(dict(path=name, **item))
        build = attempt.read(result["build"])
        need(build["schema"] == "m193c-bridge-build-v1" and build["status"] == "COMPLETE_COMPILED_TESTS_ONLY"
             and build["exit_code"] == 0 and build["rebuilt_cli"] is True and build["error"] is None
             and build["finalization_errors"] == [] and build["sources_before"] == build["sources_after"], "actual complete compiled build")
        for name, item in build["sources_before"].items():
            need(release["source_bindings"].get(name) == item, "compiled source missing from execution release")
            attempt.track(dict(path=name, **item))
        for key in ("driver", "compiler_artifact", "test_executable", "test_listing", "compiler_log", "execution_release"):
            attempt.track(build[key])
        for key in ("compiler_process", "listing_process"):
            need(build[key]["error"] is None and build[key]["cleanup_errors"] == []
                 and build[key]["terminal_job_accounting"] is True
                 and build[key]["job_accounting"]["active_processes"] == 0 and build[key]["exit_code"] == 0,
                 "complete bounded build prerequisite")
        build_release = attempt.read(build["execution_release"])
        need(build_release["schema"] == "m193c-bridge-build-release-v1"
             and build_release["scope"] == "build-only", "build prerequisite scope")
        exe = path(build["test_executable"])
        need(binding(exe) == binding(path(build["compiler_artifact"])), "original/copied executable identity")
        message = build["compiler_artifact_message"]
        need(Path(message["executable"]).resolve() == path(build["compiler_artifact"])
             and message["profile"]["test"] is True and message["target"]["name"] == "strehl", "actual compiler association")
        listing = path(build["test_listing"]).read_text(encoding="utf8")
        for name in (TEST, PRECISION):
            need(listing.splitlines().count(name+": test") == 1, "actual listed private entry")
        driver = load_source("bridge-build.py", attempt)
        need(driver.sources() == build["sources_before"], "current compiled include set")
        helper = load_source("bounded-process.py", attempt)
        api = helper.load_job_api(release["source_bindings"]["experiments/m12-scorecard/m12-harness.py"])

        def launch(ordinal, phase, test, fields):
            attempt.closure()
            env, removed = helper.clean_environment({**BASE_ENV, **fields})
            argv = [str(exe), "--exact", test, "--ignored", "--test-threads=1", "--nocapture"]
            name = f"{ordinal:02}-{phase}"
            record = dict(schema="m193c-child-launch-v1", ordinal=ordinal, phase=phase, status="FAILED_CHILD",
                          command=argv, environment={**BASE_ENV, **fields}, removed_environment_names=removed,
                          executable=build["test_executable"], started_utc=datetime.now(timezone.utc).isoformat(),
                          ended_utc=None, started_monotonic_ns=time.monotonic_ns(), ended_monotonic_ns=None,
                          observation=None, log=None, error=None)
            result["active_launch"] = record
            try:
                remaining_cpu = 600-(time.process_time()-START_CPU+attempt.child_cpu)
                remaining_wall = 1200-(time.monotonic()-START_WALL)
                actual = helper.run(argv, env, ROOT, a.output/(name+".log"), api=api,
                                    wall_seconds=min(240, remaining_wall), cpu_seconds=remaining_cpu,
                                    log_bytes=16<<20, committed_bytes=8<<30, check=attempt.budget)
                record["observation"] = actual
                if actual["job_accounting"] is None or actual["terminal_job_accounting"] is not True:
                    attempt.cpu_accounting_complete = False
                if actual["job_accounting"] is not None:
                    attempt.child_cpu += actual["job_accounting"]["total_cpu_100ns"]/1e7
                attempt.inventory()
                record["log"] = attempt.collect(a.output/(name+".log"))
                need(actual["job_accounting"] is not None, "child Job accounting absent")
                need(actual["terminal_job_accounting"] is True and actual["error"] is None
                     and actual["cleanup_errors"] == [] and actual["exit_code"] == 0, "actual bounded child failure")
                text = path(record["log"]).read_text(encoding="utf8", errors="strict")
                summaries = re.findall(r"^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;.*$", text, re.M)
                need(summaries == [("1", "0", "0")], "actual exact one-test summary")
                attempt.closure()
                record["status"] = "COMPLETE_CHILD_EXIT_ZERO"
            except Exception:
                if record["observation"] is None:
                    attempt.cpu_accounting_complete = False
                record["error"] = traceback.format_exc()
            record["ended_utc"] = datetime.now(timezone.utc).isoformat()
            record["ended_monotonic_ns"] = time.monotonic_ns()
            r = attempt.save(name+"-launch.json", record)
            result["last_launch"] = r
            if record["status"] != "COMPLETE_CHILD_EXIT_ZERO":
                result["failed_launch"] = r
            result["active_launch"] = None
            need(record["status"] == "COMPLETE_CHILD_EXIT_ZERO", "private child refused: "+name)
            return r

        for ordinal, name in enumerate(CASES):
            plan_path = a.output/f"{ordinal:02}-plan.json"
            launch_ref = launch(ordinal, "plan", TEST, dict(STREHL_M193C_GRID_MODE="plan", STREHL_M193C_GRID_CASE=name,
                                                          STREHL_M193C_GRID_PLAN=str(plan_path)))
            plan_ref = attempt.collect(plan_path)
            plan = attempt.read(plan_ref)
            need(plan["schema"] == "m193c-private-grid-plan-v1" and plan["status"] == "PLAN_ONLY"
                 and plan["case"]["ordinal"] == ordinal and plan["case"]["id"] == name, "actual plan identity")
            result["entries"].append(dict(ordinal=ordinal, id=name, plan=plan_ref, plan_launch=launch_ref,
                                          receipt=None, tiff=None, render_launch=None))
        attempt.save("all-ten-plans.json", dict(schema="m193c-all-plans-v1", entries=result["entries"]))
        precision_dir = a.output/"precision"
        precision_launch = launch(10, "component", PRECISION, dict(STREHL_M193C_PRECISION_OUTPUT=str(precision_dir)))
        for p in sorted(precision_dir.iterdir()):
            need(p.is_file(), "unexpected precision subdirectory")
            attempt.collect(p)
        precision_ref = ref(precision_dir/"result.json")
        precision = attempt.read(precision_ref)
        need(precision["schema"] == "m193c-precision-witness-v1" and precision["status"] == "COMPONENT_OBSERVED_UNVERIFIED"
             and precision["error"] is None and precision["secondary_errors"] == [] and len(precision["cases"]) == 10,
             "complete actual precision component")
        for entry, r in zip(result["entries"], precision["cases"], strict=True):
            actual = attempt.read(r)
            need(actual["plan"] == attempt.read(entry["plan"]) and actual["plan_sha256"] == entry["plan"]["sha256"]
                 and actual["plan_bytes"] == entry["plan"]["bytes"], "component to actual saved plan")
        result["precision"] = dict(launch=precision_launch, result=precision_ref)
        for entry in result["entries"]:
            ordinal, name = entry["ordinal"], entry["id"]
            output, receipt_path = a.output/f"{ordinal:02}.tif", a.output/f"{ordinal:02}-receipt.json"
            fields = dict(STREHL_M193C_GRID_MODE="render", STREHL_M193C_GRID_CASE=name,
                          STREHL_M193C_GRID_PLAN=str(path(entry["plan"])), STREHL_M193C_GRID_PLAN_SHA256=entry["plan"]["sha256"],
                          STREHL_M193C_GRID_OUTPUT=str(output), STREHL_M193C_GRID_RECEIPT=str(receipt_path))
            entry["render_launch"] = launch(ordinal, "render", TEST, fields)
            entry["receipt"], entry["tiff"] = attempt.collect(receipt_path), attempt.collect(output)
            receipt = attempt.read(entry["receipt"])
            need(receipt["schema"] == "m193c-private-grid-receipt-v1" and receipt["status"] == "COMPLETE_RGB_UNVERIFIED"
                 and receipt["error"] is None and receipt["secondary_errors"] == []
                 and receipt["plan"] == attempt.read(entry["plan"]) and receipt["plan_sha256"] == entry["plan"]["sha256"]
                 and receipt["plan_bytes"] == entry["plan"]["bytes"],
                 "actual completed render receipt")
            need(attempt.track(receipt["output"]) == path(entry["tiff"]), "actual declared receipt TIFF identity")
            attempt.save("progress.json", dict(completed_renders=ordinal+1, entries=result["entries"]))
            print(f"M193c rendered {ordinal+1}/10: {name}", flush=True)
        result["failed_launch"] = None
        result["status"] = "COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED"
    except Exception:
        result["error"] = traceback.format_exc()
    try:
        attempt.inventory()
        result["owned_artifacts"] = [ref(p) for p in sorted(a.output.rglob("*")) if p.is_file()]
        result["inputs_before"] = dict(attempt.inputs)
        for _ in range(2):
            attempt.closure()
            result["sources_after"] = {name: binding(ROOT/name) for name in release["source_bindings"]}
            result["inputs_after"] = dict(attempt.inputs)
            result["work"] = dict(parent_cpu_seconds=time.process_time()-START_CPU, child_cpu_seconds=attempt.child_cpu,
                                  cpu_accounting_complete=attempt.cpu_accounting_complete,
                                  scope="PRODUCER_ONLY_FINAL_ADMISSION_REQUIRES_ENCOMPASSING_CAMPAIGN_JOB_AND_INVENTORY",
                                  byte_accounting="observed child-file growth plus complete parent-write reservations, including failed writes",
                                  wall_seconds=time.monotonic()-START_WALL, cumulative_written_bytes=attempt.artifact_bytes,
                                  limits=dict(cpu_seconds=600, wall_seconds=1200, artifact_bytes=128<<20))
            attempt.save("run-index.json", result)
        attempt.closure()
    except Exception:
        result["status"] = "UNCOMMISSIONED_PRIVATE_OUTPUTS"
        result["finalization_errors"].append(traceback.format_exc())
        try:
            canonical = a.output/"run-index.json"
            if canonical.exists():
                canonical.rename(a.output/"run-index.json.rejected")
            raw = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
            need(len(raw) <= 4 << 20, "bounded refused-result JSON")
            attempt.inventory()
            attempt.artifact_bytes += len(raw)
            need(attempt.artifact_bytes <= 128 << 20, "refused-result artifact reservation")
            canonical.write_bytes(raw)
            need(canonical.read_bytes() == raw, "refused result persistence")
        except Exception as exc:
            print("M193c refused-result persistence: "+repr(exc), file=sys.stderr, flush=True)
    print(json.dumps({k: result[k] for k in ("status", "error", "finalization_errors")}), flush=True)
    return 0 if result["status"] == "COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
