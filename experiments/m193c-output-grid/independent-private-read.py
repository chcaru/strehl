"""Bound the actual private launches before invoking the independent pixel reader."""
import time
START_CPU, START_WALL = time.process_time(), time.monotonic()
import argparse
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
BASE = dict(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER="1",
            STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
TEST = "merge_cmd::production_truth::m193c_output_grid::m193c_private_output_case"
PRECISION = "merge_cmd::production_truth::m193c_output_grid::precision_witness::m193c_private_precision_witness"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def binding(p):
    h, size = hashlib.sha256(), 0
    with p.open("rb") as stream:
        while raw := stream.read(1 << 20):
            h.update(raw); size += len(raw)
    return dict(sha256=h.hexdigest(), bytes=size)


def strict(raw):
    def unique(items):
        out = {}
        for k, v in items:
            need(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    def bad(token):
        raise ValueError("nonfinite JSON token "+token)
    def walk(value):
        if isinstance(value, float):
            need(math.isfinite(value), "nonfinite JSON number")
        elif isinstance(value, dict):
            for v in value.values(): walk(v)
        elif isinstance(value, list):
            for v in value: walk(v)
    out = json.loads(raw, object_pairs_hook=unique, parse_constant=bad)
    walk(out)
    return out


def resolve(ref):
    need(type(ref) is dict and set(ref) == {"path", "sha256", "bytes"}, "closed FileRef")
    need(type(ref["path"]) is str and type(ref["bytes"]) is int and ref["bytes"] >= 0
         and type(ref["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", ref["sha256"]), "FileRef types")
    p = Path(ref["path"])
    p = (p if p.is_absolute() else ROOT/p).resolve(strict=True)
    need(p.is_file() and p.is_relative_to(ROOT), "workspace FileRef")
    return p


class Store:
    def __init__(self, output, limits):
        self.output, self.limits = output, limits
        self.inputs, self.outputs, self.written = {}, {}, 0
        self.read_bytes = 0
        self.numeric_budget = None

    def check(self):
        need(time.process_time()-START_CPU <= self.limits["cpu_seconds"], "reader CPU allowance")
        need(time.monotonic()-START_WALL <= self.limits["wall_seconds"], "reader wall allowance")
        need(self.written <= self.limits["artifact_bytes"], "reader reserved output allowance")
        numeric_reads = 0 if self.numeric_budget is None else self.numeric_budget.read_bytes
        need(self.read_bytes + numeric_reads <= 512 << 20, "combined reader input allowance")
        if self.numeric_budget is not None:
            self.numeric_budget.read_limit = (512 << 20)-self.read_bytes

    def remember(self, p, ref):
        value = dict(path=p.relative_to(ROOT).as_posix(), sha256=ref["sha256"], bytes=ref["bytes"])
        need(self.inputs.setdefault(value["path"], value) == value, "consumed input binding conflict")

    def digest(self, p):
        self.check()
        value = binding(p)
        self.read_bytes += value["bytes"]
        self.check()
        return value

    def track(self, ref):
        p = resolve(ref)
        self.check()
        actual = self.digest(p)
        need(actual == {k: ref[k] for k in ("sha256", "bytes")}, "bound file changed")
        self.remember(p, ref)
        self.check()
        return p

    def read(self, ref, cap=4 << 20):
        p = resolve(ref)
        need(ref["bytes"] <= cap, "bounded authority input")
        self.check()
        with p.open("rb") as f:
            raw = f.read(cap+1)
        self.read_bytes += len(raw)
        need(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], "actual authority bytes")
        self.remember(p, ref)
        self.check()
        return raw

    def json(self, ref):
        return strict(self.read(ref))

    def write(self, name, raw):
        p = self.output/name
        need(p.resolve().is_relative_to(self.output) and not p.exists(), "fresh contained reader artifact")
        need(type(raw) is bytes and len(raw) <= 4 << 20, "bounded reader artifact")
        self.written += len(raw)
        self.check()
        with p.open("xb") as f:
            need(f.write(raw) == len(raw), "short reader write")
            f.flush(); os.fsync(f.fileno())
        ref = dict(path=p.resolve().relative_to(ROOT).as_posix(), **self.digest(p))
        need(ref["bytes"] == len(raw) and ref["sha256"] == hashlib.sha256(raw).hexdigest(), "reader persistence")
        self.outputs[ref["path"]] = ref
        self.check()
        return ref

    def save(self, name, value):
        return self.write(name, (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n").encode())

    def closure(self):
        for ref in list(self.inputs.values()) + list(self.outputs.values()):
            p = resolve(ref)
            actual = self.digest(p)
            need(actual == {k: ref[k] for k in ("sha256", "bytes")}, "reader input/output changed through persistence")
            self.check()


def import_bound(name, source, store):
    relative = (HERE/name).relative_to(ROOT).as_posix()
    raw = store.read(dict(path=relative, **source[relative]), 1 << 20)
    spec = importlib.util.spec_from_file_location("m193c_independent_"+Path(name).stem.replace("-", "_"), HERE/name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(HERE/name), "exec"), module.__dict__)
    return module


def bounded_success(actual):
    need(actual["exit_code"] == 0 and actual["error"] is None and actual["cleanup_errors"] == []
         and actual["terminal_job_accounting"] is True
         and actual["job_accounting"]["active_processes"] == 0, "actual terminal child success")


def bind_observation(row):
    actual = row["observation"]
    bounded_success(actual)
    need(actual["command"] == row["command"], "actual observation argv")
    need(resolve(actual["log"]) == resolve(row["log"])
         and actual["log"]["sha256"] == row["log"]["sha256"]
         and actual["log"]["bytes"] == row["log"]["bytes"] == actual["log_bytes"], "actual observation log identity")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    need(a.request.is_absolute() and a.output.is_absolute() and a.output.resolve().is_relative_to(ROOT), "absolute workspace reader paths")
    with a.request.open("rb") as f:
        raw = f.read((4 << 20)+1)
    need(len(raw) <= 4 << 20 and hashlib.sha256(raw).hexdigest() == a.request_sha256, "external request pin")
    request_ref = dict(path=a.request.resolve().relative_to(ROOT).as_posix(), sha256=a.request_sha256, bytes=len(raw))
    request = strict(raw)
    need(set(request) == {"schema", "execution_release", "build", "producer_result", "producer_launch", "reader_runtime", "remaining_limits"}
         and request["schema"] == "m193c-grid-reader-request-v1", "private reader request schema")
    limits = request["remaining_limits"]
    need(set(limits) == {"cpu_seconds", "wall_seconds", "artifact_bytes"}, "closed reader limits")
    for key, cap in dict(cpu_seconds=120, wall_seconds=240, artifact_bytes=32 << 20).items():
        need(type(limits[key]) in (int, float) and math.isfinite(limits[key]) and 0 < limits[key] <= cap, "bounded reader limit")
    need(type(limits["artifact_bytes"]) is int, "integer reader artifact limit")
    a.output.mkdir(parents=True, exist_ok=False)
    store = Store(a.output, limits)
    store.read_bytes = len(raw)
    result = dict(schema="m193c-private-grid-admission-v1", status="REFUSED_GRID_ADAPTER_PRIVATE",
                  request=request_ref, build=request["build"], producer_result=request["producer_result"],
                  producer_launch=request["producer_launch"], command=list(sys.orig_argv), context=None,
                  sources_before=None, sources_after=None, inputs_before=None, inputs_after=None,
                  controls=None, cases=[], precision=None, active_child=None, work=None, error=None, finalization_errors=[])
    core = reads = budget = None
    runtime = request["reader_runtime"]
    try:
        store.track(request_ref)
        release = store.json(request["execution_release"])
        need(set(release) == {"schema", "scope", "source_bindings", "inputs", "commands", "build", "reader_runtime"}
             and release["schema"] == "m193c-private-campaign-release-v1" and release["scope"] == "private-twelve", "campaign release scope")
        source = release["source_bindings"]
        required = {"experiments/m193c-output-grid/"+n for n in ("independent-private-read.py", "independent-grid-read.py")}
        required.add("experiments/m194g-larger-pupil/independent-rgb-tiff.py")
        need(required <= set(source), "required reader source population")
        result["sources_before"] = source
        for name, item in source.items():
            store.track(dict(path=name, **item))
        for item in release["inputs"]:
            store.track(item)
        need(release["build"] == request["build"] and release["reader_runtime"] == runtime, "released build/runtime")
        need(set(runtime) == {"path", "sha256", "bytes"} and Path(runtime["path"]).is_absolute()
             and Path(runtime["path"]).resolve() == Path(sys.executable).resolve(), "actual Python executable")
        need(store.digest(Path(runtime["path"])) == {k: runtime[k] for k in ("sha256", "bytes")}, "Python executable bytes")
        need(sys.dont_write_bytecode is True, "reader requires -B")
        expected = [a.request_sha256 if x == "ACTUAL_GRID_REQUEST_SHA256" else x for x in release["commands"]["grid_reader"]]
        need(list(sys.orig_argv) == expected, "actual released reader command")
        parent_launch = store.json(request["producer_launch"])
        need(parent_launch["schema"] == "m193c-campaign-child-launch-v1"
             and parent_launch["stage"] == "grid_producer"
             and parent_launch["status"] == "COMPLETE_CHILD_EXIT_ZERO" and parent_launch["error"] is None, "actual producer launch")
        bind_observation(parent_launch)
        store.track(parent_launch["log"])
        grid = store.json(request["producer_result"])
        need(grid["schema"] == "m193c-private-grid-run-v1" and grid["status"] == "COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED"
             and grid["error"] is None and grid["finalization_errors"] == []
             and grid["failed_launch"] is None and grid["active_launch"] is None, "complete actual grid producer")
        need(parent_launch["command"] == grid["command"], "actual producer command association")
        need(grid["sources_before"] == grid["sources_after"] and grid["inputs_before"] == grid["inputs_after"]
             and grid["work"]["cpu_accounting_complete"] is True, "producer source/input/accounting closure")
        producer_release = store.json(grid["release"])
        need(producer_release["schema"] == "m193c-execution-release-v1" and producer_release["scope"] == "private-grid-run", "producer release scope")
        need(grid["sources_before"] == producer_release["source_bindings"], "exact producer source population")
        for item in producer_release["inputs"]:
            normalized = dict(path=resolve(item).relative_to(ROOT).as_posix(), sha256=item["sha256"], bytes=item["bytes"])
            need(grid["inputs_after"].get(normalized["path"]) == normalized, "complete declared producer inputs")
        need(grid["command"] in [[grid["release"]["sha256"] if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in c]
                                 for c in producer_release["commands"]], "released actual producer command")
        for name, item in grid["sources_before"].items():
            need(source.get(name) == item, "producer source in common release")
        for item in grid["inputs_after"].values():
            store.track(item)
        for item in grid["owned_artifacts"]:
            store.track(item)
        build = store.json(request["build"])
        need(grid["build"] == request["build"] and build["schema"] == "m193c-bridge-build-v1"
             and build["status"] == "COMPLETE_COMPILED_TESTS_ONLY" and build["rebuilt_cli"] is True
             and build["error"] is None and build["finalization_errors"] == []
             and build["sources_before"] == build["sources_after"], "complete actual bound build")
        for key in ("compiler_process", "listing_process"):
            bounded_success(build[key])
        exe = store.track(build["test_executable"])
        store.track(build["compiler_artifact"])
        need(all(build["test_executable"][k] == build["compiler_artifact"][k] for k in ("sha256", "bytes")), "copied compiler executable")
        for name, item in build["sources_before"].items():
            need(source.get(name) == item, "compiled source in common release")
        compiler = store.read(build["compiler_log"], 64 << 20)
        messages = [strict(line) for line in compiler.splitlines() if line.startswith(b"{")]
        need(b"Compiling strehl-cli" in compiler and messages.count(build["compiler_artifact_message"]) == 1
             and messages.count(build["build_script_message"]) == 1, "actual compiler messages")
        stamps = [v for k, v in build["build_script_message"]["env"] if k == "STREHL_BUILD_ID"]
        need(len(stamps) == 1 and build["software"] == "strehl 0.0.0 ("+stamps[0]+")", "actual compiled software context")
        context = dict(build=dict(path=str(exe), sha256=build["test_executable"]["sha256"],
                                 bytes=build["test_executable"]["bytes"], software=build["software"]),
                       compiled_inputs=dict(private_protocol_sha256=source["experiments/m193c-output-grid/private-protocol.md"]["sha256"],
                                            private_adapter_sha256=source["experiments/m193c-output-grid/private-adapter.rs"]["sha256"]),
                       precision_witness_sha256=source["experiments/m193c-output-grid/precision-witness.rs"]["sha256"])
        result["context"] = context
        core = import_bound("independent-grid-read.py", source, store)
        budget = core.Budget(cpu=limits["cpu_seconds"], wall=limits["wall_seconds"], start_cpu=START_CPU, start_wall=START_WALL)
        store.numeric_budget = budget
        store.check()
        reads = core.Reads(budget)
        parser_core = core.load_parser(budget)
        core.validate_rows(grid["entries"])

        def launch(ref, ordinal, phase, test, env):
            row = store.json(ref)
            need(row["schema"] == "m193c-child-launch-v1" and row["ordinal"] == ordinal and row["phase"] == phase
                 and row["status"] == "COMPLETE_CHILD_EXIT_ZERO" and row["error"] is None, "grid launch identity")
            need(row["command"] == [str(exe), "--exact", test, "--ignored", "--test-threads=1", "--nocapture"]
                 and row["environment"] == env and row["executable"] == build["test_executable"], "exact grid invocation")
            bind_observation(row)
            log = store.read(row["log"], 16 << 20).decode("utf8", errors="strict")
            need(re.findall(r"^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;.*$", log, re.M) == [("1", "0", "0")],
                 "actual one-test grid summary")
            need(type(row["started_monotonic_ns"]) is int and type(row["ended_monotonic_ns"]) is int
                 and row["started_monotonic_ns"] < row["ended_monotonic_ns"], "actual grid chronology")
            return row

        ordered = []
        for i, row in enumerate(grid["entries"]):
            ordered.append(launch(row["plan_launch"], i, "plan", TEST, {**BASE, "STREHL_M193C_GRID_MODE":"plan",
                "STREHL_M193C_GRID_CASE":row["id"], "STREHL_M193C_GRID_PLAN":str(resolve(row["plan"]))}))
        ordered.append(launch(grid["precision"]["launch"], 10, "component", PRECISION,
                             {**BASE, "STREHL_M193C_PRECISION_OUTPUT":str(resolve(grid["precision"]["result"]).parent)}))
        for i, row in enumerate(grid["entries"]):
            ordered.append(launch(row["render_launch"], i, "render", TEST, {**BASE, "STREHL_M193C_GRID_MODE":"render",
                "STREHL_M193C_GRID_CASE":row["id"], "STREHL_M193C_GRID_PLAN":str(resolve(row["plan"])),
                "STREHL_M193C_GRID_PLAN_SHA256":row["plan"]["sha256"], "STREHL_M193C_GRID_OUTPUT":str(resolve(row["tiff"])),
                "STREHL_M193C_GRID_RECEIPT":str(resolve(row["receipt"]))}))
        need(all(a["ended_monotonic_ns"] <= b["started_monotonic_ns"] for a,b in zip(ordered,ordered[1:])),
             "all ten plans before component before all renders")
        control = {}; result["active_child"] = control
        core.run_controls(grid["entries"], reads=reads, budget=budget, parser=parser_core, context=context,
                          kernel_witness=grid["precision"]["result"], write_bytes=store.write, partial=control)
        need(control["status"] == "PASS_GRID_READER_CONTROLS" and control["counts"] == dict(total=45,rejected=35,valid=10), "all powered reader controls")
        control_precision = control.pop("precision")
        control["precision"] = store.save("controls-precision.json", control_precision)
        result["controls"] = store.save("controls.json", control)
        population = {}; result["active_child"] = population
        core.read_population(grid["entries"], reads=reads, budget=budget, parser=parser_core, context=context,
                             kernel_witness=grid["precision"]["result"], partial=population)
        need(population["status"] == "PASS_GRID_SEMANTICS_AND_PIXELS", "complete independent population")
        result["cases"] = [store.save(f"case-{i:02}.json", value) for i,value in enumerate(population["cases"])]
        result["precision"] = store.save("precision.json", population["precision"])
        result["active_child"] = None
        reads.recheck()
        result["status"] = "PASS_GRID_ADAPTER_PRIVATE_ONLY"
    except Exception:
        result["error"] = traceback.format_exc()
    try:
        result["inputs_before"] = dict(store.inputs)
        store.closure()
        if reads is not None: reads.recheck()
        need(store.digest(Path(runtime["path"])) == {k: runtime[k] for k in ("sha256", "bytes")}, "runtime unchanged through persistence")
        result["sources_after"] = {name: store.digest(ROOT/name) for name in (result["sources_before"] or {})}
        result["inputs_after"] = dict(store.inputs)
        result["work"] = dict(cpu_seconds=time.process_time()-START_CPU, wall_seconds=time.monotonic()-START_WALL,
                              reserved_artifact_bytes=store.written, authority_read_bytes=store.read_bytes,
                              numeric_reader=budget.receipt() if budget is not None else None, limits=limits,
                              scope="pre-publication local sample; enclosing campaign owns terminal whole-process accounting")
        store.save("result.json", result)
        store.closure()
        if reads is not None: reads.recheck()
        need(store.digest(Path(runtime["path"])) == {k: runtime[k] for k in ("sha256", "bytes")}, "runtime unchanged after publication")
        store.check()
    except Exception:
        result["status"] = "REFUSED_GRID_ADAPTER_PRIVATE"
        result["finalization_errors"].append(traceback.format_exc())
        canonical = a.output/"result.json"
        try:
            if canonical.exists(): canonical.rename(a.output/"result.json.rejected")
            store.save("result.json", result)
        except Exception as secondary:
            print("M193c refused reader publication: "+repr(secondary), file=sys.stderr, flush=True)
    print(json.dumps({k:result[k] for k in ("status", "error", "finalization_errors")}), flush=True)
    return 0 if result["status"] == "PASS_GRID_ADAPTER_PRIVATE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
