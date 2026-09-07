"""Released-only observation of the unchanged independent Cartesian quadrature."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import sys
import traceback
import warnings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REFERENCE = "experiments/m194g-larger-pupil/independent-reference.py"
REFERENCE_SHA = "40199977f0f7f2d2e487ccacae59f04b60c67a6e7b636eea092c2365483c2de3"
OLD = "experiments/m194e-joint-pupil/independent-model.py"
OLD_SHA = "0cd8ea2331b269e65befdee110560cbc345e89c12348cbe1dc3144f7c04443f0"
FIRST = "experiments/m194g-larger-pupil/independent-reference-components-1/result.json"
FIRST_SHA = "514520ee73ea4504be17f0520791c174d11f202c371cd1ce9f6b11a4a8da7b0b"
DESIGN = "experiments/m194g-larger-pupil/next-reference-interval-diagnosis.md"
DESIGN_SHA = "b9d54a18f42ed8a83ef301265a6ecb9e286757e9041c6d740a2c635ed92e5179"
CATALOG = "experiments/m194g-larger-pupil/component-population.json"
CATALOG_SHA = "3814eeaf459e14a0a32e90ceeab6fc9d2994c92ee55bf17c824478accc3cbd41"
FAILED = (4, 6, 11, 13, 15, 22, 60, 62, 67, 69, 71, 78, 116, 117)
POSITIVE = (3, 14)
IDS = tuple(f"geometry-{i:03d}" for i in sorted(FAILED + POSITIVE))
ARMS = ("primary", "refined")
MODES = ("off", "count", "placebo")
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
MAX_TRACE_RECORDS = 100_000
MAX_TRACE_BYTES = 32 * 1024 * 1024


class DiagnosticRefusal(RuntimeError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def write_json(path, value):
    with Path(path).open("wb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def read_bytes(path, expected=None):
    with Path(path).open("rb") as stream:
        raw = stream.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024 or expected is not None and hashlib.sha256(raw).hexdigest() != expected:
        raise DiagnosticRefusal("bounded input/source digest mismatch")
    return raw


def file_ref(path, base=None):
    path = Path(path).resolve(strict=True)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return dict(path=str(path) if base is None else path.relative_to(base).as_posix(), sha256=h.hexdigest(), bytes=path.stat().st_size)


def strict_json(raw):
    def pairs(items):
        output = {}
        for key, value in items:
            if key in output:
                raise DiagnosticRefusal("duplicate JSON key")
            output[key] = value
        return output
    def bad(value):
        raise DiagnosticRefusal("nonfinite JSON: " + value)
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise DiagnosticRefusal("overflowed JSON number")
        if isinstance(value, dict):
            for child in value.values():
                finite(child)
        elif isinstance(value, list):
            for child in value:
                finite(child)
    finite(result)
    return result


def relative_path(name):
    if not isinstance(name, str) or not name or "\\" in name or Path(name).is_absolute() or any(p in ("", ".", "..") for p in name.split("/")):
        raise DiagnosticRefusal("canonical repository-relative path required")
    path = (ROOT / name).resolve(strict=True)
    path.relative_to(ROOT)
    return path


def entry_gate(path, expected):
    if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise DiagnosticRefusal("external release SHA256 required")
    release = strict_json(read_bytes(path, expected))
    if set(release) != {"schema", "scope", "source_bindings", "inputs", "commands"} or release["schema"] != "m194g-numerical-execution-release-v1" or release["scope"] != "reference-interval-diagnostic":
        raise DiagnosticRefusal("exact diagnostic execution release required")
    commands = release["commands"]
    if not isinstance(commands, list) or not commands or any(not isinstance(c, list) or c.count("ACTUAL_EXECUTION_RELEASE_SHA256") != 1 or any(not isinstance(a, str) for a in c) for c in commands):
        raise DiagnosticRefusal("literal command with one digest placeholder required")
    permitted = [[expected if a == "ACTUAL_EXECUTION_RELEASE_SHA256" else a for a in c] for c in commands]
    if list(sys.orig_argv) not in permitted:
        raise DiagnosticRefusal("actual interpreter command not released")
    required = {REFERENCE, OLD, Path(__file__).resolve().relative_to(ROOT).as_posix()}
    if not required <= set(release["source_bindings"]):
        raise DiagnosticRefusal("actual diagnostic source closure missing")
    inputs = release["inputs"]
    if not isinstance(inputs, list) or len({x["path"] for x in inputs}) != len(inputs) or not {FIRST, DESIGN, CATALOG} <= {x["path"] for x in inputs}:
        raise DiagnosticRefusal("fixed diagnostic inputs missing or duplicated")
    for name, wanted in release["source_bindings"].items():
        if set(wanted) != {"sha256", "bytes"} or type(wanted["bytes"]) is not int:
            raise DiagnosticRefusal("typed exact source binding required")
        raw = read_bytes(relative_path(name), wanted["sha256"])
        if len(raw) != wanted["bytes"]:
            raise DiagnosticRefusal("source byte extent mismatch")
    for ref in inputs:
        if set(ref) != {"path", "sha256", "bytes"} or type(ref["bytes"]) is not int:
            raise DiagnosticRefusal("typed exact input binding required")
        raw = read_bytes(relative_path(ref["path"]), ref["sha256"])
        if len(raw) != ref["bytes"]:
            raise DiagnosticRefusal("input byte extent mismatch")
    for rel, sha in ((REFERENCE, REFERENCE_SHA), (OLD, OLD_SHA), (FIRST, FIRST_SHA), (DESIGN, DESIGN_SHA), (CATALOG, CATALOG_SHA)):
        read_bytes(ROOT / rel, sha)
    return release


def load_reference(release):
    path = ROOT / REFERENCE
    raw = read_bytes(path, REFERENCE_SHA)
    if release["source_bindings"][REFERENCE]["sha256"] != REFERENCE_SHA:
        raise DiagnosticRefusal("frozen reference release mismatch")
    spec = importlib.util.spec_from_loader("m194g_interval_reference", loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def snapshot(release, output, name):
    bindings = dict(release["source_bindings"])
    for ref in release["inputs"]:
        wanted = {k: ref[k] for k in ("sha256", "bytes")}
        if ref["path"] in bindings and bindings[ref["path"]] != wanted:
            raise DiagnosticRefusal("inconsistent source/input reference")
        bindings[ref["path"]] = wanted
    for rel, wanted in bindings.items():
        raw = read_bytes(relative_path(rel), wanted["sha256"])
        if len(raw) != wanted["bytes"]:
            raise DiagnosticRefusal("snapshot extent mismatch")
        target = output / name / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        if file_ref(target)["sha256"] != wanted["sha256"]:
            raise DiagnosticRefusal("snapshot write mismatch")
    return bindings


def float_order(value):
    bits = struct.unpack(">Q", struct.pack(">d", value))[0]
    return (~bits & ((1 << 64)-1)) if bits >> 63 else bits | (1 << 63)


def interval_geometry(left, right):
    if not math.isfinite(left) or not math.isfinite(right) or not -1 <= left < right <= 1:
        raise DiagnosticRefusal("actual quadrature interval out of pupil domain")
    steps = float_order(right) - float_order(left)
    endpoint = left == -1.0 or right == 1.0
    return dict(left=left, right=right, left_hex=left.hex(), right_hex=right.hex(), width=right-left,
                representable_steps=steps, endpoint=endpoint, suspected_endpoint_interval=endpoint and steps <= 256)


class Observer:
    def __init__(self, reference, budget, mode, output):
        self.reference, self.budget, self.mode, self.output = reference, budget, mode, output
        self.original_quad = reference.m.quad
        self.intervals = []
        self.call_id = None
        self.hook_calls = self.collected_records = self.trace_bytes = 0
        self.closed = False
        self.stream = (output / "queried-points.jsonl").open("wb") if mode == "count" else None

    def close(self):
        if self.closed:
            return []
        self.closed = True
        errors = []
        try:
            if self.stream is not None:
                try:
                    self.stream.flush()
                    os.fsync(self.stream.fileno())
                except Exception:
                    errors.append(traceback.format_exc())
                finally:
                    try:
                        self.stream.close()
                    except Exception:
                        errors.append(traceback.format_exc())
            try:
                write_json(self.output / "observer-partial.json", dict(mode=self.mode, intervals=self.intervals,
                           optional_hook_calls=self.hook_calls, collected_records=self.collected_records, trace_bytes=self.trace_bytes))
            except Exception:
                errors.append(traceback.format_exc())
        finally:
            self.reference.m.quad = self.original_quad
        return errors

    def observe(self, interval, t, value):
        self.hook_calls += 1
        if self.mode == "placebo":
            return
        item = dict(call_id=self.call_id, interval=interval["ordinal"], ordinal=interval["collected_calls"],
                    t=t, t_hex=t.hex(), value=value, value_hex=float(value).hex())
        raw = canonical(item)
        if self.collected_records >= MAX_TRACE_RECORDS or self.trace_bytes + len(raw) > MAX_TRACE_BYTES:
            raise DiagnosticRefusal("diagnostic trace ceiling")
        self.stream.write(raw)
        self.trace_bytes += len(raw)
        self.collected_records += 1
        interval["collected_calls"] += 1
        interval["queried_t_hex"].add(item["t_hex"])
        interval["left_endpoint_queries"] += int(t == interval["left"])
        interval["right_endpoint_queries"] += int(t == interval["right"])
        interval["value_min"] = value if interval["value_min"] is None else min(interval["value_min"], value)
        interval["value_max"] = value if interval["value_max"] is None else max(interval["value_max"], value)

    def quad(self, function, left, right, **kwargs):
        # Same numeric callback and kwargs. Only optional recording wraps the
        # callback; no normalized interval or proposed correction exists here.
        if set(kwargs) != {"epsabs", "epsrel", "limit"} or kwargs["epsrel"] != 0. or kwargs["limit"] != 128:
            raise DiagnosticRefusal("unchanged frozen quad call required")
        row = dict(call_id=self.call_id, ordinal=len(self.intervals), **interval_geometry(left, right),
                   epsabs=kwargs["epsabs"], epsrel=kwargs["epsrel"], limit=kwargs["limit"],
                   evaluations_before=self.budget.evaluations, actual_calls=None, collected_calls=0,
                   queried_t_hex=set(), value_min=None, value_max=None, integral=None, error_indicator=None,
                   distinct_queried_coordinates=0, repeated_queries=0, left_endpoint_queries=0, right_endpoint_queries=0,
                   warnings=[], exception=None)
        def recorded(t):
            value = function(t)
            self.observe(row, t, value)
            return value
        actual = function if self.mode == "off" else recorded
        caught = []
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", self.reference.IntegrationWarning)
                value, error = self.original_quad(actual, left, right, **kwargs)
            row["integral"], row["error_indicator"] = value, error
            return value, error
        except Exception:
            row["exception"] = traceback.format_exc()
            raise
        finally:
            row["actual_calls"] = self.budget.evaluations - row["evaluations_before"]
            row["queried_t_hex"] = sorted(row["queried_t_hex"], key=float.fromhex)
            row["distinct_queried_coordinates"] = len(row["queried_t_hex"])
            row["repeated_queries"] = row["collected_calls"] - row["distinct_queried_coordinates"]
            row["warnings"] = [dict(category=w.category.__name__, message=str(w.message)) for w in caught]
            self.intervals.append(row)
            # The original render's outer catch must still receive each warning.
            for warning in caught:
                warnings.warn(warning.message, warning.category)


def numerical_signature(row):
    return {k: row[k] for k in ("case_id", "arm", "status", "value_e", "branch", "receipt", "error", "actual_integrand_calls")}


def trace_correspondence(mode, points):
    """Consumes persisted records; not an assertion about live Python objects."""
    intervals = mode["intervals"]
    grouped = [[] for _ in intervals]
    for point in points:
        ordinal = point["interval"]
        if type(ordinal) is not int or not 0 <= ordinal < len(intervals):
            raise DiagnosticRefusal("trace interval association")
        row = intervals[ordinal]
        if point["call_id"] != row["call_id"] or point["ordinal"] != len(grouped[ordinal]):
            raise DiagnosticRefusal("ordered trace association")
        if point["t"].hex() != point["t_hex"] or float(point["value"]).hex() != point["value_hex"] or not row["left"] <= point["t"] <= row["right"]:
            raise DiagnosticRefusal("trace numeric association")
        grouped[ordinal].append(point)
    for row, samples in zip(intervals, grouped):
        wanted = interval_geometry(row["left"], row["right"])
        if any(canonical(row[key]) != canonical(value) for key, value in wanted.items()):
            raise DiagnosticRefusal("interval bound correspondence")
        if len(samples) != row["collected_calls"] or len(samples) != row["actual_calls"]:
            raise DiagnosticRefusal("complete actual callback coverage")
        unique = sorted({s["t_hex"] for s in samples}, key=float.fromhex)
        if unique != row["queried_t_hex"]:
            raise DiagnosticRefusal("distinct queried coordinates correspondence")
        if (row["distinct_queried_coordinates"] != len(unique) or row["repeated_queries"] != len(samples)-len(unique)
                or row["left_endpoint_queries"] != sum(s["t"] == row["left"] for s in samples)
                or row["right_endpoint_queries"] != sum(s["t"] == row["right"] for s in samples)):
            raise DiagnosticRefusal("query multiplicity/endpoint correspondence")
    return True


def read_trace(output, ref):
    if set(ref) != {"path", "sha256", "bytes"} or type(ref["bytes"]) is not int or not 0 <= ref["bytes"] <= MAX_TRACE_BYTES:
        raise DiagnosticRefusal("bounded trace reference required")
    relative = Path(ref["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise DiagnosticRefusal("relative trace path required")
    path = (output / relative).resolve(strict=True)
    path.relative_to(output)
    total = 0
    h = hashlib.sha256()
    records = []
    with path.open("rb") as stream:
        while True:
            line = stream.readline(MAX_TRACE_BYTES - total + 1)
            if not line:
                break
            total += len(line)
            if total > MAX_TRACE_BYTES or len(records) >= MAX_TRACE_RECORDS or not line.endswith(b"\n"):
                raise DiagnosticRefusal("trace byte/record/framing ceiling")
            h.update(line)
            records.append(strict_json(line))
    if total != ref["bytes"] or h.hexdigest() != ref["sha256"]:
        raise DiagnosticRefusal("actual trace hash/extent mismatch")
    return records


def runtime(reference=None):
    return dict(cpu_seconds=time.process_time()-ENTRY_CPU, wall_seconds=time.monotonic()-ENTRY_WALL,
                python=sys.version, numpy=None if reference is None else reference.np.__version__,
                scipy=None if reference is None else reference.scipy.__version__,
                threads={name: os.environ.get(name) for name in THREADS})


def run(args):
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    release = reference = budget = observer = None
    result = dict(schema="m194g-reference-interval-diagnostic-v1", status="UNCOMMISSIONED_DIAGNOSTIC",
                  invocation=dict(orig_argv=list(sys.orig_argv), argv=list(sys.argv), cwd=os.getcwd(), executable=sys.executable, xoptions=dict(sys._xoptions)),
                  execution_release=None, first_result=None, catalog=None, design=None,
                  sources_before=None, sources_after=None, source_capture_error=None,
                  modes=[], checks=[], hypothesis=None, budget=None, runtime=None, error=None, cleanup_errors=[])
    try:
        release = entry_gate(args.execution_release, args.execution_release_sha256)
        result["execution_release"] = file_ref(args.execution_release)
        result["sources_before"] = snapshot(release, output, "sources-before")
        reference = load_reference(release)
        budget = reference.Budget(start_cpu=ENTRY_CPU, start_wall=ENTRY_WALL)
        budget.max_evaluations, budget.max_cpu, budget.max_wall = 100_000, 10., 20.
        budget.check()
        first = strict_json(read_bytes(ROOT / FIRST, FIRST_SHA))
        catalog = strict_json(read_bytes(ROOT / CATALOG, CATALOG_SHA))
        result.update(first_result=file_ref(ROOT / FIRST), catalog=file_ref(ROOT / CATALOG), design=file_ref(ROOT / DESIGN))
        reference.validate_population(catalog)
        cases = {c["id"]: c for c in catalog["cases"]}
        original = {(r["case_id"], r["arm"]): r for r in first["baseline"]}
        original_signatures = []
        for case_id in IDS:
            for arm in ARMS:
                row = dict(original[(case_id, arm)])
                row["actual_integrand_calls"] = row["work_after"]["evaluations"] - row["work_before"]["evaluations"]
                original_signatures.append(numerical_signature(row))
        initial_quad = reference.m.quad
        for mode in MODES:
            directory = output / mode
            directory.mkdir()
            observer = Observer(reference, budget, mode, directory)
            before = budget.receipt()
            rows = []
            reference.m.quad = observer.quad
            try:
                for case_id in IDS:
                    for arm in ARMS:
                        budget.check()
                        observer.call_id = case_id + ":" + arm
                        start = budget.evaluations
                        row = dict(case_id=case_id, arm=arm, status="REFUSED", value_e=None, branch=None, receipt=None,
                                   error=None, actual_integrand_calls=None)
                        unexpected = None
                        try:
                            prepared = reference.case_input(catalog, cases[case_id])
                            value, receipt = reference.Engine(budget, reference.TARGETS[arm]).render(prepared, tuple(cases[case_id]["native_xy"]), cell=True)
                            row.update(status="VALUE", value_e=value, branch=receipt["branch"], receipt=receipt)
                        except Exception as exc:
                            row["error"] = repr(exc)
                            if not isinstance(exc, reference.Refusal):
                                unexpected = exc
                        row["actual_integrand_calls"] = budget.evaluations - start
                        rows.append(row)
                        write_json(directory / "partial.json", dict(rows=rows, intervals=observer.intervals, budget=budget.receipt()))
                        if unexpected is not None:
                            raise DiagnosticRefusal("unexpected observed call failure") from unexpected
                        budget.check()
            finally:
                result["cleanup_errors"].extend(observer.close())
            if reference.m.quad is not initial_quad:
                raise DiagnosticRefusal("original quadrature dependency was not restored")
            record = dict(mode=mode, rows=rows, intervals=observer.intervals, work_before=before, work_after=budget.receipt(),
                          optional_hook_calls=observer.hook_calls, collected_records=observer.collected_records,
                          trace_bytes=observer.trace_bytes, trace=None)
            if mode == "count":
                record["trace"] = file_ref(directory / "queried-points.jsonl", output)
            write_json(directory / "result.json", record)
            result["modes"].append(file_ref(directory / "result.json", output))
            signature = [numerical_signature(row) for row in rows]
            write_json(directory / "numerical-signature.json", signature)
            equal = canonical(signature) == canonical(original_signatures)
            result["checks"].append(dict(name=mode+"-original-numerical-byte-null", passed=equal,
                                        actual_sha256=hashlib.sha256(canonical(signature)).hexdigest(),
                                        original_sha256=hashlib.sha256(canonical(original_signatures)).hexdigest()))
            hooks_ok = observer.hook_calls == observer.collected_records == 0 if mode == "off" else (
                observer.hook_calls > 0 and observer.collected_records == 0 if mode == "placebo" else
                observer.hook_calls == observer.collected_records > 0)
            result["checks"].append(dict(name=mode+"-actual-observer-power", passed=hooks_ok))
            observer = None
            budget.check()
        count = strict_json(read_bytes(output / "count" / "result.json"))
        points = read_trace(output, count["trace"])
        trace_correspondence(count, points)
        result["checks"].append(dict(name="reopened-trace-correspondence", passed=True))
        changed = copy.deepcopy(count)
        changed["intervals"][0]["left"] = math.nextafter(changed["intervals"][0]["left"], math.inf)
        write_json(output / "changed-bound.json", changed)
        refused = None
        try:
            trace_correspondence(strict_json(read_bytes(output / "changed-bound.json")), points)
        except DiagnosticRefusal as exc:
            refused = repr(exc)
        result["checks"].append(dict(name="changed-actual-bound-refused", passed=refused is not None, refusal=refused))
        coherent = copy.deepcopy(count)
        ordinary_row = next(row for row in coherent["intervals"]
                            if row["call_id"] == "geometry-003:primary" and not row["suspected_endpoint_interval"])
        smallest = min(float.fromhex(t) for t in ordinary_row["queried_t_hex"])
        ordinary_row.update(interval_geometry(math.nextafter(smallest, math.inf), ordinary_row["right"]))
        write_json(output / "coherent-changed-bound.json", coherent)
        refused = None
        try:
            trace_correspondence(strict_json(read_bytes(output / "coherent-changed-bound.json")), points)
        except DiagnosticRefusal as exc:
            refused = repr(exc)
        result["checks"].append(dict(name="coherent-sample-range-fault-refused",
                                    passed=refused is not None and "trace numeric association" in refused, refusal=refused))
        trace_correspondence(strict_json(read_bytes(output / "count" / "result.json")), points)
        result["checks"].append(dict(name="restored-reopened-bound-companion", passed=True))
        warning_rows = [row for row in count["intervals"] if row["warnings"]]
        ordinary = [row for row in count["intervals"] if row["call_id"].split(":")[0] in {f"geometry-{x:03d}" for x in POSITIVE}
                    and not row["suspected_endpoint_interval"]]
        result["hypothesis"] = dict(threshold_steps=256, warning_intervals=len(warning_rows),
                                    suspected_warning_intervals=sum(row["suspected_endpoint_interval"] for row in warning_rows),
                                    contrary_warning_intervals=sum(not row["suspected_endpoint_interval"] for row in warning_rows),
                                    warning_intervals_with_repeated_coordinates=sum(len(row["queried_t_hex"]) < row["actual_calls"] for row in warning_rows),
                                    ordinary_positive_companion_intervals=len(ordinary),
                                    supported=bool(warning_rows) and all(row["suspected_endpoint_interval"] for row in warning_rows)
                                              and all(len(row["queried_t_hex"]) < row["actual_calls"] for row in warning_rows),
                                    scope="diagnostic support only; no normalized-interval implementation or optical commission")
        result["checks"].append(dict(name="ordinary-width-positive-companions-reached", passed=bool(ordinary) and all(not row["warnings"] for row in ordinary)))
        if len(result["modes"]) != 3 or not all(check["passed"] for check in result["checks"]):
            raise DiagnosticRefusal("incomplete or failed diagnostic controls")
        result["status"] = "PASS_DIAGNOSTIC"
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        if observer is not None:
            result["cleanup_errors"].extend(observer.close())
        if result["cleanup_errors"]:
            result["status"] = "UNCOMMISSIONED_DIAGNOSTIC"
        if release is not None:
            try:
                result["sources_after"] = snapshot(release, output, "sources-after")
                if result["sources_after"] != result["sources_before"]:
                    raise DiagnosticRefusal("source/input bytes changed")
            except Exception:
                result["source_capture_error"] = traceback.format_exc()
                result["status"] = "UNCOMMISSIONED_DIAGNOSTIC"
        if budget is not None:
            try:
                budget.check()
            except Exception:
                result["status"] = "UNCOMMISSIONED_DIAGNOSTIC"
                if result["error"] is None:
                    result["error"] = traceback.format_exc()
            result["budget"] = budget.receipt()
        result["runtime"] = runtime(reference)
        write_json(output / "result.json", result)
        if budget is not None:
            try:
                budget.check()
            except Exception:
                result["status"] = "UNCOMMISSIONED_DIAGNOSTIC"
                if result["error"] is None:
                    result["error"] = traceback.format_exc()
                result["budget"] = budget.receipt()
                result["runtime"] = runtime(reference)
                write_json(output / "result.json", result)
    print(result["status"], flush=True)
    return 0 if result["status"] == "PASS_DIAGNOSTIC" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--execution-release", required=True)
    parser.add_argument("--execution-release-sha256", required=True)
    raise SystemExit(run(parser.parse_args()))
