"""One encompassing observed Job for the M193c fixed12 private TIFF stage.

Source preparation only: no process/helper/image work on import.
"""
import time
START = time.monotonic()

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROCESS = HERE / "bounded-process.py"
HARNESS = ROOT / "experiments/m12-scorecard/m12-harness.py"
STAGES = ("grid_producer", "grid_reader", "derivative_producer", "derivative_reader")
TEST = "merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_private"
CASES = ("identity-nine", "curved-nine-off", "curved-nine-count", "curved-nine-placebo",
         "curved-nine-scale", "original-one-correct", "original-one-swapped",
         "original-one-restored", "original-one-inverse", "constant-nine-null")
MIB = 1 << 20
SUCCESS = "PASS_M193C_PRIVATE_STAGE_ONLY"
DERIVATIVE_SOURCE_IDS = (
    "valid-affine", "empty-active", "odd-origin-x", "odd-origin-y", "odd-width", "odd-height",
    "stride-storage", "active-outside", "stride-overflow", "axis-bound", "pixel-bound", "buffer-bound",
    "black-nan", "black-negative", "white-infinity", "white-container", "zero-range", "negative-range",
    "red-gain-zero", "green-gain-zero", "blue-gain-nan", "gain-ratio-overflow", "fourth-wb-null",
    "padding-null", "red-gain-live", "black-clamp-live", "wb-order-live", "nine-plan-before-decode",
    "decode-once-drop-before-write", "snapshot-changed", "late-publication-revokes", "restored-affine")
DERIVATIVE_READER_IDS = (
    "refusal-helper-false-acceptance", "producer-valid", "producer-false-check", "producer-omitted-check",
    "producer-unknown-key", "producer-output-association", "producer-changed-reference", "producer-restored",
    "tiff-little-endian", "tiff-big-endian", "tiff-wide322", "old-parser-width-refusal", "tiff-appended",
    "tiff-truncated", "tiff-duplicate-tag", "tiff-compression", "tiff-orientation", "tiff-description",
    "tiff-software", "tiff-wrong-shape", "tiff-bool-shape", "tiff-changed-code", "tiff-restored",
    "affine-rational", "signed-rational", "premature-black-clamp", "white-balance-after-mhc", "padding-null",
    "oracle-restored", "owned-lifetime", "borrowed-lifetime-refusal", "lifetime-restored", "wrong-cfa",
    "wrong-black", "wrong-white", "wrong-wb", "metadata-restored", "wrong-active-hash", "wrong-row-hash",
    "conflicting-reference", "json-overflow")


def need(ok, message):
    if not ok:
        raise ValueError(message)


def keys(value, expected, label):
    need(type(value) is dict and set(value) == set(expected), label + " keys")


def strict(raw):
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))

    def finite(item):
        if type(item) is float:
            need(math.isfinite(item), "nonfinite JSON number")
        elif type(item) is list:
            for child in item:
                finite(child)
        elif type(item) is dict:
            for child in item.values():
                finite(child)
    finite(value)
    return value


def integer(value, low=0):
    return type(value) is int and value >= low


def finite_positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def hash_form(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def source_path(name):
    need(type(name) is str and "\\" not in name and ":" not in name, "POSIX source path")
    parts = PurePosixPath(name)
    need(not parts.is_absolute() and str(parts) == name and ".." not in parts.parts, "relative source path")
    path = ROOT.joinpath(*parts.parts).resolve()
    need(path.is_relative_to(ROOT), "source containment")
    return path


def path_ref(ref, external=False):
    keys(ref, ("path", "sha256", "bytes"), "FileRef")
    need(type(ref["path"]) is str and hash_form(ref["sha256"]) and integer(ref["bytes"]), "typed FileRef")
    path = Path(ref["path"])
    path = path.resolve() if path.is_absolute() else source_path(ref["path"])
    need(external or path.is_relative_to(ROOT), "FileRef containment")
    return path


def plain(path):
    info = path.stat(follow_symlinks=False)
    need(stat.S_ISREG(info.st_mode) and not info.st_file_attributes & 0x400, "ordinary non-reparse file")
    return info


def binding(path, cap=128 * MIB, check=lambda: None):
    before = plain(path)
    need(0 <= before.st_size <= cap, "bounded file extent")
    digest, count = hashlib.sha256(), 0
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        need((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), "opened file identity")
        while raw := stream.read(MIB):
            digest.update(raw)
            count += len(raw)
            need(count <= cap, "file growth bound")
            check()
    after = plain(path)
    need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_file_attributes) ==
         (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_file_attributes)
         and count == before.st_size, "file changed while hashing")
    return dict(sha256=digest.hexdigest(), bytes=count)


class State:
    def __init__(self, output):
        self.output = output
        self.child_cpu = 0.0
        self.extents = {}
        self.bound = {}
        self.last_scan = -math.inf

    def scan(self):
        count = 0
        if self.output.exists():
            for directory, dirs, names in os.walk(self.output, followlinks=False):
                for name in dirs:
                    info = (Path(directory) / name).stat(follow_symlinks=False)
                    need(not info.st_file_attributes & 0x400, "output reparse directory")
                for name in names:
                    count += 1
                    need(count <= 8192, "bounded private artifact count")
                    path = Path(directory) / name
                    info = plain(path)
                    self.extents[str(path)] = max(self.extents.get(str(path), 0), info.st_size)
        self.last_scan = time.monotonic()

    def work(self):
        return dict(owner_or_worker_cpu_seconds=time.process_time(), observed_child_cpu_seconds=self.child_cpu,
                    cpu_seconds=time.process_time() + self.child_cpu,
                    wall_seconds=time.monotonic() - START, artifact_bytes=sum(self.extents.values()),
                    byte_scope="cumulative observed per-path high-water extents; deleted paths remain charged")

    def check(self, force=False):
        if force or time.monotonic() - self.last_scan >= .2:
            self.scan()
        work = self.work()
        need(work["cpu_seconds"] <= 600, "complete private CPU allowance")
        need(work["wall_seconds"] <= 1200, "complete private wall allowance")
        need(work["artifact_bytes"] <= 128 * MIB, "complete private artifact allowance")

    def limits(self, stage=None):
        self.check(True)
        work = self.work()
        wall_cap = 1200 if stage in (None, "grid_producer") else 240
        return dict(cpu_seconds=600 - work["cpu_seconds"],
                    wall_seconds=min(wall_cap, 1200 - work["wall_seconds"]),
                    log_bytes=min(16 * MIB, 128 * MIB - work["artifact_bytes"]), committed_bytes=8 << 30)

    def reader_limits(self):
        work = self.work()
        result = dict(cpu_seconds=min(120, 600 - work["cpu_seconds"]),
                      wall_seconds=min(240, 1200 - work["wall_seconds"]),
                      artifact_bytes=min(32 * MIB, 128 * MIB - work["artifact_bytes"]))
        need(all(finite_positive(value) for value in result.values()), "remaining independent reader bounds")
        return result

    def add_observed_cpu(self, observation):
        account = observation.get("job_accounting")
        need(type(account) is dict and integer(account.get("total_cpu_100ns")), "observed Job CPU absent")
        self.child_cpu += account["total_cpu_100ns"] / 1e7
        self.check(True)

    def ref(self, path, absolute=False, cap=128 * MIB, track=True):
        path = path.resolve()
        value = binding(path, cap, self.check)
        if track:
            need(self.bound.setdefault(str(path), value) == value, "previously bound file changed")
        return dict(path=str(path) if absolute else relative(path), **value)

    def verify(self, ref, external=False, cap=128 * MIB):
        path = path_ref(ref, external)
        value = self.ref(path, Path(ref["path"]).is_absolute(), cap)
        need(value == ref, "FileRef bytes changed: " + str(path))
        return path

    def read(self, ref, cap=4 * MIB):
        path = path_ref(ref)
        need(ref["bytes"] <= cap, "JSON extent")
        with path.open("rb") as stream:
            raw = stream.read(cap + 1)
        need(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], "same-byte JSON pin")
        need(self.bound.setdefault(str(path), {k: ref[k] for k in ("sha256", "bytes")}) ==
             {k: ref[k] for k in ("sha256", "bytes")}, "JSON changed across reads")
        self.check()
        return strict(raw)

    def closure(self):
        for name, expected in tuple(self.bound.items()):
            need(binding(Path(name), expected["bytes"], self.check) == expected, "source/input/product closure changed")
        self.check(True)

    def save(self, path, value, emergency=False):
        raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
        need(len(raw) <= 4 * MIB, "bounded publication JSON")
        if not emergency:
            self.check(True)
            need(self.work()["artifact_bytes"] + len(raw) <= 128 * MIB, "metadata output reservation")
        with path.open("xb") as stream:
            need(stream.write(raw) == len(raw), "short metadata write")
            stream.flush()
            os.fsync(stream.fileno())
        self.extents[str(path)] = max(self.extents.get(str(path), 0), len(raw))
        check = (lambda: None) if emergency else self.check
        need(binding(path, 4 * MIB, check) == dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)),
             "published byte identity")
        return dict(path=relative(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def successful(observation, command):
    need(observation.get("command") == command and type(observation.get("exit_code")) is int and
         observation["exit_code"] == 0, "actual exact zero exit")
    need(observation.get("error") is None and observation.get("cleanup_errors") == [] and
         observation.get("terminal_job_accounting") is True and
         observation["job_accounting"]["active_processes"] == 0, "terminal bounded Job outcome")


def load_process(release, state):
    raw = PROCESS.read_bytes()
    need(dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)) ==
         release["source_bindings"][relative(PROCESS)], "actual process helper source bytes")
    spec = importlib.util.spec_from_loader("m193c_private_campaign_process", loader=None, origin=str(PROCESS))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(PROCESS)
    sys.modules[spec.name] = module
    exec(compile(raw, str(PROCESS), "exec"), module.__dict__)
    api = module.load_job_api(release["source_bindings"][relative(HARNESS)])
    state.check()
    return module, api


def source_closure(release, state):
    need(type(release["source_bindings"]) is dict and release["source_bindings"], "source map")
    for name, value in release["source_bindings"].items():
        keys(value, ("sha256", "bytes"), "source binding")
        source_path(name)
        state.verify(dict(path=name, **value), cap=32 * MIB)
    required = {relative(__file__), relative(HERE / "private-campaign-preregister.md"), relative(PROCESS), relative(HARNESS)}
    required.update(relative(HERE / name) for name in ("private-grid-run.py", "independent-private-read.py",
                                                      "independent-derivative-read.py", "registration-derivative.rs"))
    need(required <= set(release["source_bindings"]), "complete owner/stage source closure")
    need(type(release["inputs"]) is list and len({str(path_ref(ref)) for ref in release["inputs"]}) ==
         len(release["inputs"]), "unique released input references")
    for ref in release["inputs"]:
        state.verify(ref)
    need(release["build"] in release["inputs"], "build absent from released inputs")
    runtime = release["reader_runtime"]
    need(Path(runtime["path"]).is_absolute(), "absolute Python runtime reference")
    state.verify(runtime, external=True, cap=64 * MIB)


def build_authority(release, state):
    build = state.read(release["build"])
    need(build.get("schema") == "m193c-bridge-build-v1" and build.get("status") == "COMPLETE_COMPILED_TESTS_ONLY"
         and type(build.get("exit_code")) is int and build["exit_code"] == 0 and build.get("rebuilt_cli") is True
         and build.get("error") is None and build.get("finalization_errors") == []
         and build["sources_before"] == build["sources_after"], "actual complete compiled build")
    for name, expected in build["sources_before"].items():
        need(release["source_bindings"].get(name) == expected, "compiled source absent from owner release")
    for name in ("registration-derivative.rs", "derivative-controls-preregister.md",
                 "registration-derivative-design.md", "independent-derivative-design-review.md"):
        need(relative(HERE / name) in build["sources_before"], "derivative compiled include set")
    for key in ("compiler_artifact", "test_executable", "compiler_log", "test_listing", "execution_release", "driver"):
        state.verify(build[key])
    exe, artifact = path_ref(build["test_executable"]), path_ref(build["compiler_artifact"])
    need(exe != artifact and all(build["test_executable"][key] == build["compiler_artifact"][key]
                                for key in ("sha256", "bytes")), "actual artifact/copied executable bytes")
    build_release = state.read(build["execution_release"])
    need(build_release.get("schema") == "m193c-bridge-build-release-v1" and build_release.get("scope") == "build-only",
         "build release scope")
    expected_sources = {**build["sources_before"], relative(path_ref(build["driver"])):
                        {key: build["driver"][key] for key in ("sha256", "bytes")}}
    need(build_release["source_bindings"] == expected_sources and build_release["build_command"] == build["command"],
         "build command/source-release association")
    for ref in build_release["inputs"]:
        state.verify(ref)
    successful(build["compiler_process"], build["command"])
    successful(build["listing_process"], [str(exe), "--list"])
    need(state.verify(build["compiler_process"]["log"]) == path_ref(build["compiler_log"]) and
         state.verify(build["listing_process"]["log"]) == path_ref(build["test_listing"]), "actual build logs")
    message = build["compiler_artifact_message"]
    need(message.get("reason") == "compiler-artifact" and Path(message["executable"]).resolve() == artifact and
         message.get("target", {}).get("name") == "strehl" and
         Path(message.get("target", {}).get("src_path", "")).resolve() == ROOT / "crates/strehl-cli/src/main.rs" and
         Path(message.get("manifest_path", "")).resolve() == ROOT / "crates/strehl-cli/Cargo.toml" and
         message.get("package_id") == "path+" + (ROOT / "crates/strehl-cli").as_uri() + "#0.0.0" and
         message.get("profile", {}).get("test") is True, "actual compiler artifact association")
    compiled, emitted = False, 0
    with path_ref(build["compiler_log"]).open("rb") as stream:
        while line := stream.readline(4 * MIB + 1):
            need(len(line) <= 4 * MIB, "bounded compiler log line")
            compiled |= b"Compiling strehl-cli" in line
            if line.startswith(b"{"):
                emitted += strict(line) == message
            state.check()
    need(compiled and emitted == 1, "actual compiler rebuild/artifact emission")
    listing = path_ref(build["test_listing"]).read_text(encoding="utf8").splitlines()
    need(listing.count(TEST + ": test") == 1, "actual listed derivative private test")
    return build, exe


def arg(command, flag):
    need(command.count(flag) == 1 and command.index(flag) + 1 < len(command), "single command argument " + flag)
    return command[command.index(flag) + 1]


def commands_authority(release, owner_output, exe):
    commands = release["commands"]
    keys(commands, ("owner", "worker", *STAGES), "literal campaign commands")
    for command in commands.values():
        need(type(command) is list and command and all(type(value) is str for value in command), "literal argv array")
    python = str(path_ref(release["reader_runtime"], True))
    scripts = dict(owner="private-campaign.py", worker="private-campaign.py", grid_producer="private-grid-run.py",
                   grid_reader="independent-private-read.py", derivative_reader="independent-derivative-read.py")
    outputs = dict(owner=owner_output, worker=owner_output / "worker", grid_producer=owner_output / "worker/grid",
                   grid_reader=owner_output / "worker/grid-reader", derivative_reader=owner_output / "worker/derivative-reader")
    for name, filename in scripts.items():
        command = commands[name]
        need(command[0] == python and "-B" in command and str(HERE / filename) in command and
             arg(command, "--output") == str(outputs[name]), "exact Python stage/output: " + name)
        need("faulthandler" in command, "faulthandler required")
        caches = [value.split("=", 1)[1] for value in command if value.startswith("pycache_prefix=")]
        need(len(caches) == 1 and Path(caches[0]).is_absolute() and Path(caches[0]).resolve().is_relative_to(owner_output),
             "owned fresh cache prefix")
    need("--worker" not in commands["owner"] and commands["worker"].count("--worker") == 1, "owner/worker command split")
    need(commands["derivative_producer"] == [str(exe), "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"],
         "fixed derivative test argv")
    for name, token, request_name in (("grid_reader", "ACTUAL_GRID_REQUEST_SHA256", "grid-reader-request.json"),
                                     ("derivative_reader", "ACTUAL_DERIVATIVE_REQUEST_SHA256", "derivative-reader-request.json")):
        need(arg(commands[name], "--request") == str(owner_output / "worker" / request_name) and
             arg(commands[name], "--request-sha256") == token, "fixed reader request command")
    need(commands["derivative_reader"].count("--private") == 1, "derivative private reader mode")


def actual_command(release, name, release_sha, request_sha=None):
    substitutions = dict(ACTUAL_EXECUTION_RELEASE_SHA256=release_sha)
    if request_sha is not None:
        substitutions["ACTUAL_GRID_REQUEST_SHA256" if name == "grid_reader" else "ACTUAL_DERIVATIVE_REQUEST_SHA256"] = request_sha
    return [substitutions.get(word, word) for word in release["commands"][name]]


def clean_environment(helper, fields=()):
    env, removed = helper.clean_environment(fields)
    for key in tuple(env):
        if key.upper().startswith("PYTHON"):
            removed.append(key)
            del env[key]
    return env, sorted(set(removed))


def launch(stage, command, fields, log_path, helper, api, state, reader_limits=None):
    env, removed = clean_environment(helper, fields)
    result = dict(schema="m193c-campaign-child-launch-v1", stage=stage, status="FAILED_CHILD", command=command,
                  environment=dict(fields), removed_environment_names=removed, observation=None, log=None,
                  started_monotonic_ns=time.monotonic_ns(), ended_monotonic_ns=None, error=None)
    try:
        state.closure()
        limits = state.limits(stage)
        if reader_limits is not None:
            limits["cpu_seconds"] = min(limits["cpu_seconds"], reader_limits["cpu_seconds"])
            limits["wall_seconds"] = min(limits["wall_seconds"], reader_limits["wall_seconds"])
        need(all(finite_positive(value) for value in limits.values()), "remaining child limits")
        observation = helper.run(command, env, ROOT, log_path, api=api, **limits, check=state.check)
        result["observation"] = observation
        # Nested stage observations are local only. Owner adds only its one outer Job.
        state.add_observed_cpu(observation)
        result["log"] = state.ref(log_path)
        successful(observation, command)
        need(state.verify(observation["log"]) == log_path, "actual stage log association")
        if stage == "derivative_producer":
            text = log_path.read_text(encoding="utf8")
            need(len(re.findall(r"(?m)^test " + re.escape(TEST) + r" \.\.\. ok\r?$", text)) == 1,
                 "actual named derivative test")
            summary = re.findall(r"(?m)^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured;.*$", text)
            need(summary == [("1", "0", "0", "0")], "actual one-test derivative summary")
        state.closure()
        result["status"] = "COMPLETE_CHILD_EXIT_ZERO"
    except Exception:
        result["error"] = traceback.format_exc()
    result["ended_monotonic_ns"] = time.monotonic_ns()
    return result


def verify_launch(ref, stage, expected, state):
    value = state.read(ref)
    keys(value, ("schema", "stage", "status", "command", "environment", "removed_environment_names", "observation",
                 "log", "started_monotonic_ns", "ended_monotonic_ns", "error"), "stage launch")
    need(value["schema"] == "m193c-campaign-child-launch-v1" and value["stage"] == stage and
         value["status"] == "COMPLETE_CHILD_EXIT_ZERO" and value["error"] is None and value["command"] == expected,
         "actual successful stage launch")
    need(integer(value["started_monotonic_ns"]) and integer(value["ended_monotonic_ns"]) and
         value["ended_monotonic_ns"] >= value["started_monotonic_ns"], "actual launch interval")
    successful(value["observation"], expected)
    need(state.verify(value["log"]) == state.verify(value["observation"]["log"]), "actual launch log refs")
    return value


def complete_record(ref, schema, status, state):
    value = state.read(ref)
    need(value.get("schema") == schema and value.get("status") == status and
         value.get("error") is None and value.get("finalization_errors") == [], "complete stage result: " + schema)
    return value


def products(grid, derivative, worker_output, state):
    need(type(grid["entries"]) is list and len(grid["entries"]) == 10, "complete10 grid products")
    refs = []
    for ordinal, (name, row) in enumerate(zip(CASES, grid["entries"])):
        need(type(row["ordinal"]) is int and row["ordinal"] == ordinal and row["id"] == name, "literal grid product order")
        need(path_ref(row["tiff"]) == worker_output / "grid" / f"{ordinal:02}.tif", "grid product location")
        state.verify(row["tiff"])
        refs.append(row["tiff"])
    keys(derivative["outputs"], ("affine", "signed_border"), "two derivative products")
    for key, name in (("affine", "affine.tiff"), ("signed_border", "signed-border.tiff")):
        ref = derivative["outputs"][key]
        need(path_ref(ref) == worker_output / "derivative" / name, "derivative product location")
        state.verify(ref)
        refs.append(ref)
    identities = set()
    for ref in refs:
        info = plain(path_ref(ref))
        need((info.st_dev, info.st_ino) not in identities, "distinct actual12 product file identities")
        identities.add((info.st_dev, info.st_ino))
    for directory in (worker_output / "grid", worker_output / "derivative"):
        actual = {p.resolve() for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in (".tif", ".tiff")}
        expected = {path_ref(ref) for ref in refs if path_ref(ref).is_relative_to(directory)}
        need(actual == expected, "no extra producer TIFF population")
    return refs


def independent_association(value, request_ref, request, command, state):
    actual_request = value["request"]
    need(state.verify(actual_request) == state.verify(request_ref) and
         all(actual_request[k] == request_ref[k] for k in ("sha256", "bytes")), "actual independent request identity")
    need(value.get("build") == request["build"] and
         value.get("producer_result") == request["producer_result"] and
         value.get("producer_launch") == request["producer_launch"], "actual independent request/producer association")
    if "command" in value:
        need(value["command"] == command, "actual grid interpreter argv")
    else:
        invocation = value["invocation"]
        keys(invocation, ("argv", "orig_argv", "executable", "cwd", "xoptions", "thread_environment", "runtime",
                          "source_bindings", "work"), "typed derivative invocation")
        need(type(invocation["argv"]) is list and all(type(v) is str for v in invocation["argv"]) and
             type(invocation["orig_argv"]) is list and invocation["orig_argv"] == command and
             type(invocation["executable"]) is str and Path(invocation["executable"]).resolve() == Path(command[0]).resolve()
             and invocation["cwd"] == str(ROOT), "actual derivative argv/executable/cwd")
        for key in ("xoptions", "thread_environment", "runtime", "source_bindings", "work"):
            need(type(invocation[key]) is dict and invocation[key], "typed derivative invocation " + key)
        for key in ("cpu_seconds", "wall_seconds"):
            need(type(invocation["work"].get(key)) in (int, float) and math.isfinite(invocation["work"][key]) and
                 invocation["work"][key] >= 0, "typed derivative work time")
        for key in ("artifact_bytes", "artifact_limit", "owned_array_peak_bytes", "owned_array_limit", "bounded_bytes_read"):
            need(integer(invocation["work"].get(key)), "typed derivative work counter")
    state.verify(request_ref)
    for key in ("build", "producer_result", "producer_launch"):
        state.verify(value[key])


def independent_population(stage, value, producer, release, state):
    """Consume the independent result records; do not rerun their pixel arithmetic."""
    if stage == "grid_reader":
        need(value.get("sources_before") == release["source_bindings"] and
             value.get("sources_after") == release["source_bindings"] and
             type(value.get("inputs_before")) is dict and value["inputs_before"] == value.get("inputs_after") and
             value.get("active_child") is None, "complete independent grid closure")
        controls = state.read(value["controls"])
        need(controls.get("schema") == "m193c-independent-grid-controls-v1" and
             controls.get("status") == "PASS_GRID_READER_CONTROLS" and controls.get("error") is None and
             controls.get("counts") == dict(total=45, rejected=35, valid=10), "actual45 grid instruments")
        checks = controls["checks"]
        need(type(checks) is list and len(checks) == 45 and len({row["id"] for row in checks}) == 45 and
             sum(row["status"] == "PASS_EXPECTED_REFUSAL" for row in checks) == 35 and
             sum(row["status"] == "PASS_VALID_COMPANION" for row in checks) == 10, "all45 retained grid control outcomes")
        need(type(value["cases"]) is list and len(value["cases"]) == 10, "all10 actual independent cases")
        for ordinal, ref in enumerate(value["cases"]):
            case = state.read(ref)
            need(case.get("schema") == "m193c-independent-grid-case-v1" and case.get("status") == "PASS_PRIVATE_CASE" and
                 type(case.get("ordinal")) is int and case["ordinal"] == ordinal and case.get("id") == CASES[ordinal],
                 "literal independent case association")
            for key in ("plan", "receipt", "tiff"):
                actual, expected = case[key], producer["entries"][ordinal][key]
                need(state.verify(actual) == state.verify(expected) and
                     all(actual[k] == expected[k] for k in ("sha256", "bytes")), "independent actual case file")
        precision = state.read(value["precision"])
        need(precision.get("schema") == "m193c-independent-grid-precision-v1" and
             precision.get("status") == "PASS_LITERAL_KERNEL_PRECISION" and len(precision["samples"]) == 3712,
             "actual3712 independent precision observations")
        actual, expected = precision["witness"], producer["precision"]["result"]
        need(state.verify(actual) == state.verify(expected) and
             all(actual[k] == expected[k] for k in ("sha256", "bytes")), "actual producer precision witness")
    else:
        need(value["invocation"]["source_bindings"] == release["source_bindings"], "independent derivative source closure")
        keys(value["checks"], ("source", "reader"), "source32/reader41 groups")
        need(value["checks"]["source"] == producer["checks"], "actual source32 association")
        for key, expected_ids in (("source", DERIVATIVE_SOURCE_IDS), ("reader", DERIVATIVE_READER_IDS)):
            rows = value["checks"][key]
            need(type(rows) is list and tuple(row["id"] for row in rows) == expected_ids and
                 all(type(row["id"]) is str and row["pass"] is True and type(row["evidence"]) is dict for row in rows),
                 "all actual derivative control outcomes: " + key)
        keys(value["outputs"], ("affine", "signed_border"), "two independent derivative reads")
        for key in ("affine", "signed_border"):
            row = value["outputs"][key]
            keys(row, ("tiff", "pixel_sha256_u16_le", "shape", "compared_sites", "max_code_error"), "derivative output read")
            need(row["tiff"] == producer["outputs"][key] and state.verify(row["tiff"]) == path_ref(producer["outputs"][key])
                 and hash_form(row["pixel_sha256_u16_le"]) and row["shape"] == [22, 30, 3] and
                 type(row["compared_sites"]) is int and row["compared_sites"] == (54 if key == "affine" else 660) and
                 integer(row["max_code_error"]) and row["max_code_error"] <= 1, "actual two derivative pixel reads")


def worker(release, release_ref, output, state, helper, api):
    result = dict(schema="m193c-private-worker-v1", status="REFUSED_PRIVATE_WORKER", execution_release=release_ref,
                  command=list(sys.orig_argv), stages=[], unvisited=list(STAGES), products=[], work=None,
                  error=None, finalization_errors=[])
    values, requests = {}, {}
    try:
        for stage in STAGES:
            fields, request_sha, limits = {}, None, None
            if stage.endswith("reader"):
                producer = "grid_producer" if stage == "grid_reader" else "derivative_producer"
                producer_row = next(row for row in result["stages"] if row["stage"] == producer)
                limits = state.reader_limits()
                request = dict(schema="m193c-grid-reader-request-v1" if stage == "grid_reader" else
                               "m193c-derivative-private-read-request-v1", execution_release=release_ref,
                               build=release["build"],
                               producer_result=state.ref(path_ref(producer_row["result"]), True),
                               producer_launch=state.ref(path_ref(producer_row["launch"]), True),
                               reader_runtime=release["reader_runtime"])
                request["remaining_limits" if stage == "grid_reader" else "limits"] = limits
                request_path = output / ("grid-reader-request.json" if stage == "grid_reader" else "derivative-reader-request.json")
                state.save(request_path, request)
                request_ref = state.ref(request_path, True)
                request_sha = request_ref["sha256"]
                requests[stage] = (request_ref, request)
            elif stage == "derivative_producer":
                fields = {"RAYON_NUM_THREADS": "2", "STREHL_M193C_DERIVATIVE_OUTPUT_DIR": str(output / "derivative")}
            command = actual_command(release, stage, release_ref["sha256"], request_sha)
            row = dict(stage=stage, launch=None, result=None, request=requests.get(stage, (None,))[0])
            result["stages"].append(row)
            result["unvisited"] = list(STAGES[STAGES.index(stage) + 1:])
            actual = launch(stage, command, fields, output / (stage + ".log"), helper, api, state, limits)
            launch_path = output / (stage + "-launch.json")
            row["launch"] = state.save(launch_path, actual, emergency=actual["status"] != "COMPLETE_CHILD_EXIT_ZERO")
            need(actual["status"] == "COMPLETE_CHILD_EXIT_ZERO", "first stage refusal:\n" + str(actual["error"]))
            names = dict(grid_producer=("grid/run-index.json", "m193c-private-grid-run-v1", "COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED"),
                         grid_reader=("grid-reader/result.json", "m193c-private-grid-admission-v1", "PASS_GRID_ADAPTER_PRIVATE_ONLY"),
                         derivative_producer=("derivative/result.json", "m193c-derivative-private-v1", "COMPLETE_PRIVATE_DERIVATIVE_PRODUCTS_UNVERIFIED"),
                         derivative_reader=("derivative-reader/result.json", "m193c-derivative-private-independent-v1", "PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY"))
            name, schema, status = names[stage]
            row["result"] = state.ref(output / name)
            values[stage] = complete_record(row["result"], schema, status, state)
            if stage.endswith("reader"):
                independent_association(values[stage], requests[stage][0], requests[stage][1], command, state)
                independent_population(stage, values[stage], values[producer], release, state)
                reader_output = output / ("grid-reader" if stage == "grid_reader" else "derivative-reader")
                need(sum(p.stat().st_size for p in reader_output.rglob("*") if p.is_file()) <= limits["artifact_bytes"],
                     "reader local retained artifacts")
            state.closure()
        result["products"] = products(values["grid_producer"], values["derivative_producer"], output, state)
        result["status"] = "COMPLETE_PRIVATE_CHILD_OUTPUTS_UNVERIFIED"
    except Exception:
        result["error"] = traceback.format_exc()
    result["work"] = {**state.work(), "scope": "worker-local only; encompassing parent Job is admission authority"}
    try:
        ref = state.save(output / "result.json", result, emergency=result["error"] is not None)
        if result["error"] is None:
            state.closure()
            state.verify(ref)
    except Exception:
        result["status"] = "REFUSED_PRIVATE_WORKER"
        remember_failure(result, "worker publication", traceback.format_exc())
        preserve_refused(output / "result.json", result, state)
    try:
        print(json.dumps(dict(status=result["status"], error=result["error"],
                              finalization_errors=result["finalization_errors"]), allow_nan=False), flush=True)
    except Exception:
        result["status"] = "REFUSED_PRIVATE_WORKER"
        remember_failure(result, "worker terminal stdout", traceback.format_exc())
        best_effort_stderr(result)
        preserve_refused(output / "result.json", result, state)
    return 0 if result["status"] == "COMPLETE_PRIVATE_CHILD_OUTPUTS_UNVERIFIED" else 1


def remember_failure(value, label, error):
    message = label + ": " + error
    if value.get("error") is None:
        value["error"] = message
    else:
        value.setdefault("finalization_errors", []).append(message)


def best_effort_stderr(value):
    try:
        print(json.dumps(dict(original_error=value.get("error"), finalization_errors=value["finalization_errors"]),
                         allow_nan=False), file=sys.stderr, flush=True)
    except Exception:
        value.setdefault("finalization_errors", []).append("terminal stderr: " + traceback.format_exc())


def preserve_refused(path, value, state):
    try:
        if path.exists():
            # Preserve the first bytes and any earlier refused publication; never retry a child.
            names = [".first", ".refused-1", ".refused-2", ".refused-3"]
            retained = next((path.with_name(path.stem + name + path.suffix) for name in names
                             if not path.with_name(path.stem + name + path.suffix).exists()), None)
            need(retained is not None, "bounded retained publication slots exhausted")
            path.rename(retained)
        state.save(path, value, emergency=True)
    except Exception:
        value.setdefault("finalization_errors", []).append("refused persistence: " + traceback.format_exc())
        best_effort_stderr(value)


def revoke_owner(result, gate, gate_path, result_path, state):
    result["status"] = "REFUSED_PRIVATE_CAMPAIGN"
    if gate is not None:
        gate.update(status="REFUSED", error=result["error"], finalization_errors=list(result["finalization_errors"]))
        earlier = len(gate["finalization_errors"])
        preserve_refused(gate_path, gate, state)
        result["finalization_errors"].extend(gate["finalization_errors"][earlier:])
        result["derivative_admission"] = None
    preserve_refused(result_path, result, state)


def inventory(state, emergency=False):
    state.scan()
    excluded = {state.output / "artifact-index.json", state.output / "result.json"}
    rows = []
    for directory, _, names in os.walk(state.output):
        for name in sorted(names):
            path = Path(directory) / name
            if path not in excluded:
                if emergency:
                    rows.append(dict(path=relative(path), **binding(path)))
                else:
                    rows.append(state.ref(path))
    rows.sort(key=lambda ref: ref["path"])
    return dict(schema="m193c-private-artifact-index-v1", files=rows, file_count=len(rows),
                retained_bytes=sum(ref["bytes"] for ref in rows), observed_high_water_bytes=sum(state.extents.values()),
                excluded=[relative(path) for path in sorted(excluded)],
                scope="all retained owned files except this index and terminal result, externally bound in final stdout")


def owner(release, release_ref, output, state, helper, api):
    result = dict(schema="m193c-private-campaign-v1", status="REFUSED_PRIVATE_CAMPAIGN", execution_release=release_ref,
                  command=list(sys.orig_argv), build=release["build"], sources_before=release["source_bindings"],
                  sources_after=None, inputs_before=release["inputs"], inputs_after=None, enclosing_job=None,
                  worker_result=None, grid_read=None, derivative_read=None, derivative_admission=None,
                  products=[], artifact_index=None, work=None, error=None, finalization_errors=[])
    gate = None
    gate_path, result_path, index_path = output / "derivative-private-admission.json", output / "result.json", output / "artifact-index.json"
    try:
        command = actual_command(release, "worker", release_ref["sha256"])
        env, removed = clean_environment(helper)
        result["worker_environment_removed"] = removed
        observation = helper.run(command, env, ROOT, output / "worker.log", api=api, **state.limits(), check=state.check)
        result["enclosing_job"] = observation
        # Exactly once: this Job includes worker, stages and every descendant.
        state.add_observed_cpu(observation)
        successful(observation, command)
        state.verify(observation["log"])
        worker_path = output / "worker/result.json"
        result["worker_result"] = state.ref(worker_path)
        child = complete_record(result["worker_result"], "m193c-private-worker-v1", "COMPLETE_PRIVATE_CHILD_OUTPUTS_UNVERIFIED", state)
        need(child["execution_release"] == release_ref and child["command"] == command and child["unvisited"] == [] and
             [row["stage"] for row in child["stages"]] == list(STAGES), "complete fixed four-stage worker")
        values = {}
        for row in child["stages"]:
            stage = row["stage"]
            request_ref = row["request"]
            request = state.read(request_ref) if request_ref is not None else None
            expected = actual_command(release, stage, release_ref["sha256"],
                                      request_ref["sha256"] if request_ref is not None else None)
            verify_launch(row["launch"], stage, expected, state)
            value = state.read(row["result"])
            need(value.get("error") is None and value.get("finalization_errors") == [], "stage has no final error")
            values[stage] = value
            if stage.endswith("reader"):
                need(value["status"] == ("PASS_GRID_ADAPTER_PRIVATE_ONLY" if stage == "grid_reader" else
                                         "PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY"), "actual independent stage pass")
                producer = "grid_producer" if stage == "grid_reader" else "derivative_producer"
                parent_row = next(item for item in child["stages"] if item["stage"] == producer)
                need(path_ref(request["producer_result"]) == path_ref(parent_row["result"]) and
                     request["producer_result"]["sha256"] == parent_row["result"]["sha256"] and
                     path_ref(request["producer_launch"]) == path_ref(parent_row["launch"]), "actual reader predecessor")
                independent_association(value, request_ref, request, expected, state)
                independent_population(stage, value, values[producer], release, state)
                result["grid_read" if stage == "grid_reader" else "derivative_read"] = row["result"]
        result["products"] = products(values["grid_producer"], values["derivative_producer"], output / "worker", state)
        need(result["products"] == child["products"], "actual worker product binding")
        source_closure(release, state)
        state.closure()
        result["sources_after"], result["inputs_after"] = release["source_bindings"], release["inputs"]
        private_row = next(row for row in child["stages"] if row["stage"] == "derivative_producer")
        gate = dict(schema="m193c-derivative-private-admission-v1", status="PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY",
                    build=release["build"], private_result=private_row["result"], independent_read=result["derivative_read"],
                    error=None, finalization_errors=[])
        result["derivative_admission"] = state.save(gate_path, gate)
        index = inventory(state)
        result["artifact_index"] = state.save(index_path, index)
        result["status"] = SUCCESS
        result["work"] = {**state.work(), "scope": "outer actual encompassing terminal Job CPU plus owner CPU; before final publication"}
        final_ref = state.save(result_path, result)
        source_closure(release, state)
        state.closure()
        for ref in index["files"]:
            state.verify(ref)
        state.verify(result["derivative_admission"])
        state.verify(result["artifact_index"])
        state.verify(final_ref)
        state.check(True)
    except Exception:
        result["status"] = "REFUSED_PRIVATE_CAMPAIGN"
        result["error"] = traceback.format_exc()
        if gate is not None:
            gate["status"] = "REFUSED"
            gate["error"] = result["error"]
            preserve_refused(gate_path, gate, state)
            result["finalization_errors"].extend(gate["finalization_errors"])
            result["derivative_admission"] = None
        # Keep all failed attempts and create an actual byte inventory even on failure.
        try:
            if index_path.exists():
                index_path.rename(output / "artifact-index.first.json")
            # Existing retained bindings may name a replaced provisional gate/result;
            # failed inventory is evidence only and must not resurrect success authority.
            state.bound = {}
            index = inventory(state, emergency=True)
            result["artifact_index"] = state.save(index_path, index, emergency=True)
        except Exception:
            result["finalization_errors"].append("failed artifact inventory: " + traceback.format_exc())
        result["work"] = state.work()
        preserve_refused(result_path, result, state)
    try:
        state.scan()
        final_files = {name: dict(path=relative(path), **binding(path, 4 * MIB))
                       for name, path in (("result", result_path), ("artifact_index", index_path), ("derivative_admission", gate_path))
                       if path.exists()}
        if result["status"] == SUCCESS:
            state.check(True)
    except Exception:
        remember_failure(result, "final external receipt", traceback.format_exc())
        revoke_owner(result, gate, gate_path, result_path, state)
        final_files = {}
    try:
        print(json.dumps(dict(status=result["status"], files=final_files, work_through_final_checks=state.work(),
                              error=result["error"], finalization_errors=result["finalization_errors"]), allow_nan=False), flush=True)
    except Exception:
        remember_failure(result, "owner terminal stdout", traceback.format_exc())
        best_effort_stderr(result)
        revoke_owner(result, gate, gate_path, result_path, state)
    return 0 if result["status"] == SUCCESS else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    need(os.name == "nt" and sys.dont_write_bytecode and "-B" in sys.orig_argv, "Windows and explicit -B required")
    need(args.release.is_absolute() and args.output.is_absolute() and hash_form(args.release_sha256), "absolute paths/external hash")
    output = args.output.resolve()
    need(output.is_relative_to(HERE) and output != HERE and not output.exists() and output.parent.is_dir(),
         "fresh owned campaign directory")
    with args.release.open("rb") as stream:
        raw = stream.read(4 * MIB + 1)
    need(len(raw) <= 4 * MIB and hashlib.sha256(raw).hexdigest() == args.release_sha256, "external campaign release pin")
    release = strict(raw)
    keys(release, ("schema", "scope", "source_bindings", "inputs", "commands", "build", "reader_runtime"), "campaign release")
    need(release["schema"] == "m193c-private-campaign-release-v1" and release["scope"] == "private-twelve", "fixed private stage scope")
    name = "worker" if args.worker else "owner"
    need(list(sys.orig_argv) == actual_command(release, name, args.release_sha256), "actual released original argv")
    state = State(output)
    output.mkdir()
    release_ref = state.ref(args.release, True, 4 * MIB)
    need(release_ref["sha256"] == args.release_sha256, "release changed after parse")
    source_closure(release, state)
    build, exe = build_authority(release, state)
    owner_output = output.parent if args.worker else output
    commands_authority(release, owner_output, exe)
    need(Path(sys.executable).resolve() == path_ref(release["reader_runtime"], True), "actual Python runtime path")
    helper, api = load_process(release, state)
    state.closure()
    if args.worker:
        need(output.name == "worker", "fixed encompassing worker output")
        return worker(release, release_ref, output, state, helper, api)
    return owner(release, release_ref, output, state, helper, api)


if __name__ == "__main__":
    raise SystemExit(main())
