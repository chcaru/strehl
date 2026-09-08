"""M193c sensor/camera-white parent with an exact independent source-artifact contract.

No decoder, image library, process helper or capture is loaded on import.
An independently released per-frame reader is mandatory before the first RAW read.
"""
import time

STARTED = time.monotonic()

import argparse
from datetime import datetime, timezone
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
CORPUS = Path("D:/personal/macro/coffee-bean")
PROCESS = HERE / "bounded-process.py"
HARNESS = ROOT / "experiments/m12-scorecard/m12-harness.py"
TEST = "merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native"
ENV_PREFIX = "STREHL_M193C_DERIVATIVE_"
POPULATION = (
    (0, "DSC00016.ARW", 39030784), (13, "DSC00029.ARW", 39878656),
    (26, "DSC00042.ARW", 40873984), (39, "DSC00055.ARW", 40669184),
    (52, "DSC00068.ARW", 39497728), (65, "DSC00081.ARW", 39235584),
    (78, "DSC00094.ARW", 39096320), (91, "DSC00107.ARW", 39018496),
    (104, "DSC00120.ARW", 38969344),
)
COMPILED = tuple("experiments/m193c-output-grid/" + name for name in (
    "registration-derivative.rs", "derivative-controls-preregister.md",
    "registration-derivative-design.md", "independent-derivative-design-review.md"))
CHECKS = (
    "owned-sensor-copy", "active-shape", "local-rggb", "active-u16-bytes",
    "active-row-u16-bytes", "scalar-black-camera-white", "green-normalized-wb",
    "tiff-native-rgb16", "tiff-linear-camera-description", "tiff-full-pixel-read",
    "input-source-stability",
)
DOMAIN_IDS = ("sensor-nonzero-origin", "visible-crop-null", "wrong-offset-hash-refusal",
              "truncated-buffer-refusal", "borrowed-sensor-refusal", "late-copy-lifetime-destroyer",
              "restored-sensor-copy", "source-origin-cfa")
WHITE_IDS = ("camera-white-authority", "global-match-wrong-camera-refused",
             "mixed-used-camera-white-refused", "absent-camera-white-refused",
             "malformed-camera-white-refused", "malformed-global-white-refused",
             "malformed-cfa-index-refused", "native-black-regression-refused",
             "native-wb-regression-refused", "camera-white-restored")
ARTIFACT_IDS = ("artifact-extra-payload-refused", "artifact-altered-source-refused",
                "artifact-missing-source-refused", "artifact-restored")
READER_SNAPSHOT_SOURCES = (
    "experiments/m193c-output-grid/independent-sensor-white-derivative-read.py",
    "experiments/m193c-output-grid/independent-derivative-tiff.py",
    "experiments/m194g-larger-pupil/independent-rgb-tiff.py",
    "experiments/m193c-output-grid/independent-derivative-reader-preregister.md",
    "experiments/m193c-output-grid/sensor-domain-reader-preregister.md",
    "experiments/m193c-output-grid/sensor-white-reader-preregister.md",
)
SETTINGS = dict(purpose="registration-development-only", colour="linear-camera-native",
                transfer="identity", matrix=None, orientation_applied=False,
                spatial_transform="identity")
SOURCE_KEYS = set("stride buffer_height allocated_samples allocated_bytes active active_samples "
                  "active_sha256_u16_le active_row_sha256_u16_le black white black_f32_bits "
                  "white_f32_bits inverse_range_f32_bits wb_rgb wb_rgb_f32_bits raw_wb_f32_bits "
                  "normalized_min normalized_max mosaic_bytes cfa_validation level_selection "
                  "operation compiled_sources decode_calls live_frame_leases_after_prepare".split())
MIB = 1 << 20
RAW_CAP = 64 * MIB
TIFF_CAP = 6 * 36_000_000 + MIB


def need(ok, message):
    if not ok:
        raise ValueError(message)


def closed(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), label + " keys")


def integer(value, low=0, high=(1 << 63) - 1):
    return type(value) is int and low <= value <= high


def number(value, low=0):
    return type(value) in (int, float) and math.isfinite(value) and value >= low


def hash_form(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def strict(raw):
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def finite(value):
        if type(value) is float:
            need(math.isfinite(value), "nonfinite JSON number")
        elif type(value) is list:
            for item in value:
                finite(item)
        elif type(value) is dict:
            for item in value.values():
                finite(item)

    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    finite(value)
    return value


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def repo_path(name):
    need(type(name) is str and "\\" not in name, "repository POSIX path")
    parts = PurePosixPath(name)
    need(not parts.is_absolute() and str(parts) == name and
         all(p not in ("", ".", "..") for p in parts.parts) and ":" not in name,
         "repository relative path")
    path = ROOT.joinpath(*parts.parts)
    need(path.resolve().is_relative_to(ROOT), "repository path escape")
    return path.resolve()


def plain_file(path):
    path = Path(path)
    value = path.stat(follow_symlinks=False)
    need(stat.S_ISREG(value.st_mode) and not value.st_file_attributes & 0x400,
         "ordinary non-reparse file required: " + str(path))
    return value


def metadata(path):
    value = plain_file(path)
    seconds, nanos = divmod(value.st_mtime_ns, 1_000_000_000)
    stamp = datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return dict(bytes=value.st_size, mtime_ns=value.st_mtime_ns,
                mtime_utc=stamp + f".{nanos:09d}Z", attributes=value.st_file_attributes,
                device=value.st_dev, file_id=value.st_ino)


def file_digest(path, cap, check=lambda: None):
    before = metadata(path)
    need(0 < before["bytes"] <= cap, "bounded file extent: " + str(path))
    digest, count = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        handle = os.fstat(stream.fileno())
        need((handle.st_dev, handle.st_ino) == (before["device"], before["file_id"]),
             "opened file identity")
        while raw := stream.read(MIB):
            count += len(raw)
            need(count <= cap, "file grew beyond cap")
            digest.update(raw)
            check()
    need(metadata(path) == before and count == before["bytes"], "file changed while hashing")
    return dict(sha256=digest.hexdigest(), bytes=count)


class Budget:
    """One parent clock plus terminal child CPU, and cumulative output extents."""
    def __init__(self, output, prior, started, cpu_started):
        closed(prior, ("cpu_seconds", "wall_seconds", "file_bytes", "metadata_bytes"), "prior work")
        need(number(prior["cpu_seconds"]) and number(prior["wall_seconds"]) and
             integer(prior["file_bytes"]) and integer(prior["metadata_bytes"]), "typed prior work")
        self.output, self.prior = output, prior.copy()
        self.started, self.cpu_started = started, cpu_started
        self.child_cpu, self.extents, self.binary = 0.0, {}, set()
        self.last_scan = -math.inf

    def work(self):
        return dict(cpu_seconds=self.prior["cpu_seconds"] + time.process_time() - self.cpu_started + self.child_cpu,
                    wall_seconds=self.prior["wall_seconds"] + time.monotonic() - self.started,
                    file_bytes=self.prior["file_bytes"] + sum(self.extents.values()),
                    metadata_bytes=self.prior["metadata_bytes"] +
                    sum(size for path, size in self.extents.items() if path not in self.binary))

    def scan(self):
        if self.output.exists():
            for base, directories, files in os.walk(self.output, followlinks=False):
                for name in directories:
                    st = (Path(base) / name).stat(follow_symlinks=False)
                    need(not st.st_file_attributes & 0x400, "output reparse directory")
                for name in files:
                    path = Path(base) / name
                    st = plain_file(path)
                    self.extents[str(path)] = max(st.st_size, self.extents.get(str(path), 0))
        self.last_scan = time.monotonic()

    def check(self, force=False):
        now = time.monotonic()
        if force or now - self.last_scan >= .2:
            self.scan()
        work = self.work()
        need(work["cpu_seconds"] <= 1200, "complete real CPU bound")
        need(work["wall_seconds"] <= 1800, "complete real wall bound")
        need(work["file_bytes"] <= 4 << 30, "complete real output extent bound")
        need(work["metadata_bytes"] <= 128 * MIB, "complete real metadata/log bound")

    def limits(self, metadata_cap=16 * MIB):
        self.check(True)
        work = self.work()
        limits = dict(cpu_seconds=1200 - work["cpu_seconds"],
                      wall_seconds=min(240, 1800 - work["wall_seconds"]),
                      log_bytes=min(metadata_cap, 128 * MIB - work["metadata_bytes"],
                                    (4 << 30) - work["file_bytes"]), committed_bytes=8 << 30)
        need(all(v > 0 for v in limits.values()), "no remaining child budget")
        return limits

    def child(self, observation):
        accounting = observation.get("job_accounting")
        need(type(accounting) is dict and integer(accounting.get("total_cpu_100ns")),
             "actual terminal child CPU required")
        self.child_cpu += accounting["total_cpu_100ns"] / 1e7
        self.check(True)

    def save(self, path, value, cap=4 * MIB):
        raw = json_bytes(value)
        need(len(raw) <= cap, "bounded metadata write")
        self.check(True)
        work = self.work()
        growth = max(0, len(raw) - self.extents.get(str(path), 0))
        need(work["file_bytes"] + growth <= 4 << 30 and
             work["metadata_bytes"] + growth <= 128 * MIB, "metadata reservation")
        with path.open("xb") as stream:
            need(stream.write(raw) == len(raw), "short metadata write")
            stream.flush()
            os.fsync(stream.fileno())
        self.extents[str(path)] = max(len(raw), self.extents.get(str(path), 0))
        need(file_digest(path, cap, self.check) ==
             dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)), "metadata write identity")
        self.check(True)


class Files:
    def __init__(self, budget):
        self.budget, self.retained = budget, {}

    def path(self, ref, absolute=False):
        closed(ref, ("path", "sha256", "bytes"), "FileRef")
        need(hash_form(ref["sha256"]) and integer(ref["bytes"], 1), "typed FileRef")
        if absolute:
            path = Path(ref["path"])
            need(path.is_absolute(), "absolute FileRef")
            return path.resolve()
        return repo_path(ref["path"])

    def bind(self, path, cap, absolute=False, retain=True):
        path = Path(path).resolve()
        value = file_digest(path, cap, self.budget.check)
        if retain:
            prior = self.retained.get(str(path))
            need(prior is None or prior == value, "previously bound file changed")
            self.retained[str(path)] = value
        return dict(path=str(path) if absolute else relative(path), **value)

    def verify(self, ref, cap, absolute=False, retain=True):
        path = self.path(ref, absolute)
        need(self.bind(path, cap, absolute, retain) == ref, "FileRef bytes changed: " + str(path))
        return path

    def read(self, ref, cap=4 * MIB, absolute=False):
        path = self.path(ref, absolute)
        need(ref["bytes"] <= cap, "bounded JSON reference")
        before = metadata(path)
        with path.open("rb") as stream:
            raw = stream.read(cap + 1)
        need(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"] and
             metadata(path) == before, "same-byte bounded JSON pin")
        value = strict(raw)
        expected = {k: ref[k] for k in ("sha256", "bytes")}
        prior = self.retained.get(str(path))
        need(prior is None or prior == expected, "bound JSON changed")
        self.retained[str(path)] = expected
        self.budget.check()
        return value

    def recheck(self):
        for name, expected in tuple(self.retained.items()):
            need(file_digest(name, expected["bytes"], self.budget.check) == expected,
                 "retained authority/product changed: " + name)


def binding_map(value, files):
    need(type(value) is dict and value, "nonempty source map")
    for name, bound in value.items():
        closed(bound, ("sha256", "bytes"), "source binding")
        files.verify(dict(path=name, **bound), 32 * MIB)


def successful_process(value, command):
    need(value.get("command") == command and type(value.get("exit_code")) is int and value["exit_code"] == 0,
         "observed exact zero child exit")
    need(value.get("error") is None and value.get("cleanup_errors") == [] and
         value.get("terminal_job_accounting") is True, "complete bounded child observation")
    need(value["job_accounting"]["active_processes"] == 0, "no surviving child descendant")


def build_authority(ref, release, files):
    build = files.read(ref)
    need(build.get("schema") == "m193c-bridge-build-v1" and
         build.get("status") == "COMPLETE_COMPILED_TESTS_ONLY" and
         build.get("error") is None and build.get("finalization_errors") == [] and
         type(build.get("exit_code")) is int and build["exit_code"] == 0 and
         build.get("rebuilt_cli") is True, "completed compiled build required")
    need(build["sources_before"] == build["sources_after"], "build source stability")
    binding_map(build["sources_before"], files)
    need(all(release["source_bindings"].get(k) == v for k, v in build["sources_before"].items()),
         "compiled sources absent from current release")
    need(all(name in build["sources_before"] for name in COMPILED), "compiled derivative include closure")
    build_release = files.read(build["execution_release"])
    need(build_release.get("schema") == "m193c-bridge-build-release-v1" and
         build_release.get("scope") == "build-only", "build-only source release")
    driver = files.verify(build["driver"], 4 * MIB)
    need(driver == HERE / "bridge-build.py", "actual build driver")
    complete = {**build["sources_before"], relative(driver):
                {k: build["driver"][k] for k in ("sha256", "bytes")}}
    need(build_release["source_bindings"] == complete, "exact build/release source association")
    need(build["command"] == build_release["build_command"], "released actual build command")
    allowed = [[build["execution_release"]["sha256"] if word == "ACTUAL_EXECUTION_RELEASE_SHA256" else word
                for word in command] for command in build_release["commands"]]
    need(build["invocation"] in allowed, "build invocation association")
    for item in build_release["inputs"]:
        files.verify(item, 64 * MIB)
    exe = files.verify(build["test_executable"], 64 * MIB)
    artifact = files.verify(build["compiler_artifact"], 64 * MIB)
    need(exe != artifact and all(build["test_executable"][k] == build["compiler_artifact"][k]
                                for k in ("sha256", "bytes")), "copied compiler artifact identity")
    message = build["compiler_artifact_message"]
    need(message.get("reason") == "compiler-artifact" and
         Path(message.get("executable", "")).resolve() == artifact and
         message.get("target", {}).get("name") == "strehl" and
         Path(message.get("target", {}).get("src_path", "")).resolve() == ROOT / "crates/strehl-cli/src/main.rs" and
         Path(message.get("manifest_path", "")).resolve() == ROOT / "crates/strehl-cli/Cargo.toml" and
         message.get("package_id") == "path+" + (ROOT / "crates/strehl-cli").as_uri() + "#0.0.0" and
         message.get("profile", {}).get("test") is True, "actual compiler artifact message")
    successful_process(build["compiler_process"], build["command"])
    successful_process(build["listing_process"], [str(exe), "--list"])
    log = files.verify(build["compiler_log"], 64 * MIB)
    need(files.verify(build["compiler_process"]["log"], 64 * MIB, True) == log,
         "compiler observation/log association")
    matches, compiled = 0, False
    with log.open("rb") as stream:
        while line := stream.readline(4 * MIB + 1):
            need(len(line) <= 4 * MIB, "bounded compiler log line")
            compiled |= b"Compiling strehl-cli" in line
            if line.startswith(b"{"):
                item = strict(line)
                matches += item == message
            files.budget.check()
    need(compiled and matches == 1, "actual compile line and artifact emission")
    listing = files.verify(build["test_listing"], MIB)
    need(files.verify(build["listing_process"]["log"], MIB, True) == listing,
         "listing observation/log association")
    names = [line[:-6] for line in listing.read_text(encoding="utf8").splitlines()
             if line.endswith(": test") and "::m193c_" in line]
    need(len(names) == len(set(names)) and names.count(TEST) == 1 and
         set(names) == set(build_release["expected_tests"]), "actual M193c test-list population")
    return build, exe


def load_process(release, files):
    expected = release["source_bindings"][relative(PROCESS)]
    raw = PROCESS.read_bytes()
    need(dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)) == expected,
         "executed process helper source pin")
    spec = importlib.util.spec_from_loader("m193c_native_process", loader=None, origin=str(PROCESS))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(PROCESS)
    sys.modules[spec.name] = module
    exec(compile(raw, str(PROCESS), "exec"), module.__dict__)
    api = module.load_job_api(release["source_bindings"][relative(HARNESS)])
    files.budget.check()
    return module, api


def reader_authority(release, output, files):
    reader = release["reader"]
    closed(reader, ("script", "runtime", "commands"), "independent reader")
    script = files.verify(reader["script"], 4 * MIB)
    need(script == HERE / "independent-sensor-white-derivative-read.py", "explicit sensor-domain camera-white reader")
    need(release["source_bindings"].get(relative(script)) ==
         {k: reader["script"][k] for k in ("sha256", "bytes")}, "independent reader source closure")
    runtime = files.read(reader["runtime"])
    need(type(runtime) is dict and "python_executable" in runtime, "independent runtime interpreter authority")
    python = files.verify(runtime["python_executable"], 64 * MIB, True)
    need(type(reader["commands"]) is list and len(reader["commands"]) == 9,
         "exact nine independent commands")
    for ordinal, row in enumerate(reader["commands"]):
        base = output / f"frame-{ordinal:02d}"
        expected = [str(python), "-B", "-X", "faulthandler", "-X",
                    "pycache_prefix=" + str(base / "reader-cache"), str(script),
                    "--request", str(base / "read-request.json"), "--request-sha256",
                    "ACTUAL_FRAME_REQUEST_SHA256", "--output", str(base / "independent")]
        need(row == expected, "exact independently released reader argv/locations")
    gate = files.read(release["private_admission"])
    closed(gate, ("schema", "status", "build", "private_result", "independent_read", "error",
                  "finalization_errors"), "derivative private admission")
    need(gate["schema"] == "m193c-derivative-private-admission-v1" and
         gate["status"] == "PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY" and
         gate["build"] == release["build"] and gate["error"] is None and
         gate["finalization_errors"] == [], "prior independent derivative private admission")
    for name in ("private_result", "independent_read"):
        files.verify(gate[name], 4 * MIB)


def original_observation(index, name, size, budget):
    path = CORPUS / name
    before = metadata(path)
    need(before["bytes"] == size, "literal source size")
    bound = file_digest(path, RAW_CAP, budget.check)
    need(metadata(path) == before, "source metadata changed during original observation")
    return dict(original_index=index, path=str(path), name=name, **before, sha256=bound["sha256"])


def copy_snapshot(original, path, budget):
    source = Path(original["path"])
    expected_meta = {key: original[key] for key in metadata(source)}
    need(metadata(source) == expected_meta, "original metadata changed before snapshot")
    budget.check(True)
    need(budget.work()["file_bytes"] + original["bytes"] <= 4 << 30, "snapshot space reservation")
    budget.binary.add(str(path))
    digest, count = hashlib.sha256(), 0
    with source.open("rb") as incoming, path.open("xb") as outgoing:
        opened = os.fstat(incoming.fileno())
        need((opened.st_dev, opened.st_ino) == (original["device"], original["file_id"]),
             "snapshot opened original identity")
        while raw := incoming.read(MIB):
            count += len(raw)
            need(count <= original["bytes"], "snapshot source extent grew")
            digest.update(raw)
            need(outgoing.write(raw) == len(raw), "short snapshot write")
            budget.check()
        outgoing.flush()
        os.fsync(outgoing.fileno())
    need(count == original["bytes"] and digest.hexdigest() == original["sha256"] and
         metadata(source) == expected_meta, "snapshot source identity/bytes")
    need(file_digest(path, RAW_CAP, budget.check) == {k: original[k] for k in ("sha256", "bytes")},
         "actual workspace snapshot bytes")
    budget.check(True)


def primary_result(row, plan, snapshot, output, command, env_fields, files):
    ref = files.bind(output / "result.json", MIB, True)
    row["primary_receipt"] = ref
    value = files.read(ref, MIB, True)
    closed(value, ("schema", "status", "input_plan", "selected", "snapshot", "source", "output",
                   "command", "environment", "elapsed_seconds", "error", "finalization_errors"), "native receipt")
    need(value["schema"] == "m193c-registration-derivative-v1" and
         value["status"] == "COMPLETE_REGISTRATION_DERIVATIVE_UNVERIFIED" and
         value["error"] is None and value["finalization_errors"] == [], "complete native derivative receipt")
    need(value["input_plan"] == plan and value["snapshot"] == snapshot and
         type(value["selected"]) is int and value["selected"] == row["original_index"] and
         value["command"] == command and value["environment"] == env_fields and
         number(value["elapsed_seconds"]), "actual native plan/command/environment association")
    source = value["source"]
    closed(source, SOURCE_KEYS, "native source metadata")
    need(type(source["decode_calls"]) is int and source["decode_calls"] == 1 and
         type(source["live_frame_leases_after_prepare"]) is int and
         source["live_frame_leases_after_prepare"] == 0, "actual one-decode/dropped-owned-frame witness")
    need(hash_form(source["active_sha256_u16_le"]) and
         source["compiled_sources"] == {name: files.retained[str(repo_path(name))]["sha256"] for name in COMPILED},
         "compiled derivative pins and active hash")
    expected = output / (Path(row["name"]).stem + "-registration.tiff")
    need(files.path(value["output"], True) == expected, "exact native TIFF location")
    files.verify(value["output"], TIFF_CAP, True)
    row["tiff"] = value["output"]
    need({p.name for p in output.iterdir()} == {"result.json", expected.name}, "native successful output population")
    return value


def native_summary(observation, log, command, files):
    successful_process(observation, command)
    files.verify(observation["log"], 16 * MIB, True)
    text = log.read_text(encoding="utf8", errors="strict")
    need(len(re.findall(r"(?m)^test " + re.escape(TEST) + r" \.\.\. ok\r?$", text)) == 1,
         "one actually executed named native test")
    summaries = re.findall(r"(?m)^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; "
                           r"(\d+) measured; (\d+) filtered out; finished in [^\r\n]+$", text)
    need(len(summaries) == 1 and summaries[0][:4] == ("1", "0", "0", "0"),
         "exact one-passed native test summary")


def expected_reader_sources(release):
    expected = {}
    for name in READER_SNAPSHOT_SOURCES:
        value = release["source_bindings"].get(name)
        closed(value, ("sha256", "bytes"), "reader source-snapshot binding")
        need(hash_form(value["sha256"]) and integer(value["bytes"], 1, 32 * MIB),
             "bounded reader source-snapshot binding")
        basename = value["sha256"][:16] + "-" + PurePosixPath(name).name
        need(basename not in expected, "reader source-snapshot name collision")
        expected[basename] = dict(source=name, **value)
    need(len(expected) == 6, "exact six reader source snapshots")
    return expected


def reader_artifacts(directory, release, files, metadata_cap):
    """Actual success-artifact path; exact population and source bytes, never suffix permission."""
    need(integer(metadata_cap, 1, 4 * MIB), "independent reader metadata cap")
    expected = expected_reader_sources(release)
    count = 0

    def children(path):
        nonlocal count
        st = Path(path).stat(follow_symlinks=False)
        need(stat.S_ISDIR(st.st_mode) and not st.st_file_attributes & 0x400,
             "ordinary non-reparse artifact directory")
        entries = {}
        with os.scandir(path) as stream:
            for entry in stream:
                count += 1
                need(count <= 256, "bounded independent metadata entry population")
                entries[entry.name] = Path(entry.path)
                files.budget.check()
        return entries

    roots = children(directory)
    need(set(roots) == {"result.json", "sources"}, "independent root artifact population")
    sources = children(roots["sources"])
    need(set(sources) == set(expected), "independent source artifact population")
    identities, total, observed = set(), 0, []
    for name, path, wanted in [("result.json", roots["result.json"], None)] + [
            ("sources/" + name, sources[name], expected[name]) for name in sorted(expected)]:
        before = plain_file(path)
        identity = (before.st_dev, before.st_ino)
        need(before.st_nlink == 1 and identity not in identities, "unlinked distinct reader artifact file")
        identities.add(identity)
        total += before.st_size
        need(total <= metadata_cap, "independent reader product bound")
        cap = 4 * MIB if wanted is None else min(32 * MIB, metadata_cap)
        actual = files.bind(path, cap, True)
        after = plain_file(path)
        need(after.st_nlink == 1 and (after.st_dev, after.st_ino, after.st_size) ==
             (before.st_dev, before.st_ino, before.st_size), "stable reader artifact identity")
        if wanted is not None:
            need(all(actual[key] == wanted[key] for key in ("sha256", "bytes")),
                 "independent source snapshot bytes")
        observed.append(dict(name=name, file=actual, source=None if wanted is None else wanted["source"]))
    return dict(entries=count, file_count=len(observed), artifact_bytes=total, files=observed)


def artifact_controls(release, output, files):
    """Five bounded metadata fixtures in four groups; no decoder, child or image call."""
    budget = files.budget
    directory = output / "artifact-contract-controls"
    directory.mkdir()
    expected = expected_reader_sources(release)
    need(5 * sum(value["bytes"] for value in expected.values()) + 65536 <= MIB,
         "private artifact controls one-MiB reservation")
    result = dict(schema="m193c-native-artifact-controls-v1", status="REFUSED", checks=[],
                  files=[], artifact_bytes=0, error=None, finalization_errors=[])
    written = 0
    primary_error = None

    def write(path, raw):
        nonlocal written
        need(written + len(raw) <= MIB, "private artifact controls one-MiB bound")
        budget.check(True)
        work = budget.work()
        need(work["file_bytes"] + len(raw) <= 4 << 30 and
             work["metadata_bytes"] + len(raw) <= 128 * MIB, "artifact-control metadata reservation")
        with path.open("xb") as stream:
            need(stream.write(raw) == len(raw), "short artifact-control write")
            stream.flush()
            os.fsync(stream.fileno())
        written += len(raw)
        budget.extents[str(path)] = len(raw)
        budget.check(True)

    def fixture(name, fault=None):
        case = directory / name
        case.mkdir()
        (case / "sources").mkdir()
        write(case / "result.json", json_bytes(dict(fixture_only=True, case=name)))
        for ordinal, (basename, value) in enumerate(sorted(expected.items())):
            if fault == "missing" and ordinal == 5:
                continue
            ref = {key: value[key] for key in ("sha256", "bytes")}
            source = files.verify(dict(path=value["source"], **ref), 32 * MIB)
            with source.open("rb") as stream:
                raw = stream.read(ref["bytes"] + 1)
            need(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"],
                 "same bounded source bytes for artifact fixture")
            if fault == "altered" and ordinal == 0:
                raw = bytes([raw[0] ^ 1]) + raw[1:]
                need(hashlib.sha256(raw).hexdigest() != ref["sha256"], "same-extent source fault potency")
            write(case / "sources" / basename, raw)
        if fault == "extra":
            write(case / "unexpected.py", b"not a released snapshot\n")
        elif fault == "nested":
            (case / "sources" / "nested").mkdir()
            write(case / "sources" / "nested" / "payload.json", b"{}\n")
        return case

    def attempt(name, fault, expected_failure):
        case = fixture(name, fault)
        try:
            observed = reader_artifacts(case, release, files, 4 * MIB)
        except ValueError as error:
            need(expected_failure is not None and str(error) == expected_failure,
                 "wrong artifact-control refusal: " + str(error))
            return dict(case=name, expected=expected_failure, exception_type="ValueError",
                        exception=str(error), refused=True)
        need(expected_failure is None, "artifact defect accepted: " + name)
        need(observed["entries"] == 8 and observed["file_count"] == 7,
             "restored exact reader artifact population")
        return dict(case=name, expected=None, observed=observed, refused=False)

    try:
        actions = (
            lambda: [attempt("extra", "extra", "independent root artifact population"),
                     attempt("nested", "nested", "independent source artifact population")],
            lambda: [attempt("altered", "altered", "independent source snapshot bytes")],
            lambda: [attempt("missing", "missing", "independent source artifact population")],
            lambda: [attempt("restored", None, None)],
        )
        for name, action in zip(ARTIFACT_IDS, actions, strict=True):
            check = dict(id=name, passed=False, attempts=[])
            result["checks"].append(check)
            check["attempts"] = action()
            check["passed"] = True
        need(tuple(row["id"] for row in result["checks"]) == ARTIFACT_IDS and
             all(row["passed"] is True for row in result["checks"]), "complete four artifact-control groups")
        result["status"] = "PASS_EXACT_READER_ARTIFACT_CONTRACT_ONLY"
    except Exception as error:
        primary_error = error
        result["error"] = traceback.format_exc()
    finally:
        try:
            for base, _, names in os.walk(directory):
                for name in sorted(names):
                    result["files"].append(files.bind(Path(base) / name, MIB, True))
            result["artifact_bytes"] = sum(ref["bytes"] for ref in result["files"])
            need(result["artifact_bytes"] == written and len(result["files"]) <= 40,
                 "complete bounded artifact-control inventory")
        except Exception:
            result["status"] = "REFUSED"
            result["finalization_errors"].append(traceback.format_exc())
        path = output / "artifact-contract-controls.json"
        try:
            budget.save(path, result, 65536)
            files.bind(path, 65536, True)
        except Exception:
            if primary_error is not None:
                primary_error.add_note("artifact-control persistence failure: " + traceback.format_exc())
                raise primary_error
            raise
    if primary_error is not None:
        raise primary_error
    need(result["status"] == "PASS_EXACT_READER_ARTIFACT_CONTRACT_ONLY" and result["error"] is None and
         result["finalization_errors"] == [], "artifact contract controls refused:\n" + str(result["error"]))


def independent_result(row, request_ref, command, directory, primary, files, release):
    ref = files.bind(directory / "result.json", 4 * MIB, True)
    row["independent_read"] = ref
    value = files.read(ref, 4 * MIB, True)
    closed(value, ("schema", "status", "request", "original_index", "snapshot", "primary_receipt", "tiff",
                   "active_sha256_u16_le", "tiff_pixel_sha256_u16_le", "checks", "domain_controls", "white_controls", "invocation", "error",
                   "finalization_errors"), "independent native result")
    need(value["schema"] == "m193c-sensor-white-native-derivative-independent-frame-v1" and
         value["status"] == "PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY" and
         value["error"] is None and value["finalization_errors"] == [], "actual independent native success")
    need(value["request"] == request_ref and type(value["original_index"]) is int and
         value["original_index"] == row["original_index"], "independent actual request/index")
    invocation = value["invocation"]
    closed(invocation, ("argv", "orig_argv", "executable", "cwd", "xoptions", "thread_environment", "runtime",
                        "source_bindings", "work"), "independent invocation metadata")
    script = str(files.path(release["reader"]["script"]))
    need(type(invocation["argv"]) is list and invocation["argv"] == command[command.index(script):] and
         type(invocation["orig_argv"]) is list and invocation["orig_argv"] == command and
         type(invocation["executable"]) is str and Path(invocation["executable"]).resolve() == Path(command[0]).resolve()
         and invocation["cwd"] == str(ROOT), "independent actual interpreter argv/executable/cwd")
    cache = next(word.split("=", 1)[1] for word in command if word.startswith("pycache_prefix="))
    closed(invocation["xoptions"], ("faulthandler", "pycache_prefix"), "independent interpreter options")
    need(invocation["xoptions"]["faulthandler"] is True and invocation["xoptions"]["pycache_prefix"] == cache,
         "independent actual interpreter options")
    need(invocation["thread_environment"] == {name: "2" for name in
         ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
         "independent actual thread caps")
    need(type(invocation["runtime"]) is dict and invocation["runtime"] == files.read(release["reader"]["runtime"])
         and invocation["source_bindings"] == release["source_bindings"], "independent runtime/source closure")
    closed(invocation["work"], ("cpu_seconds", "wall_seconds", "artifact_bytes", "artifact_limit",
                                "owned_array_peak_bytes", "owned_array_limit", "bounded_bytes_read"), "independent work metadata")
    for key in ("cpu_seconds", "wall_seconds"):
        need(number(invocation["work"][key]), "independent finite work time")
    for key in ("artifact_bytes", "artifact_limit", "owned_array_peak_bytes", "owned_array_limit", "bounded_bytes_read"):
        need(integer(invocation["work"][key]), "independent integral work counter")
    for key in ("snapshot", "primary_receipt", "tiff"):
        need(value[key] == row[key], "independent file association: " + key)
    need(value["active_sha256_u16_le"] == primary["source"]["active_sha256_u16_le"] and
         hash_form(value["tiff_pixel_sha256_u16_le"]), "independent actual active/TIFF hash")
    need(type(value["checks"]) is list and len(value["checks"]) == len(CHECKS), "independent check population")
    for check, name in zip(value["checks"], CHECKS):
        closed(check, ("id", "pass", "evidence"), "independent check")
        need(check["id"] == name and check["pass"] is True and type(check["evidence"]) is dict,
             "actual independent check: " + name)
    need(type(value["domain_controls"]) is list and len(value["domain_controls"]) == len(DOMAIN_IDS),
         "eight actual sensor-domain controls")
    for check, name in zip(value["domain_controls"], DOMAIN_IDS):
        closed(check, ("id", "pass", "evidence"), "sensor control")
        need(check["id"] == name and check["pass"] is True and type(check["evidence"]) is dict,
             "actual sensor-domain control: " + name)
    need(type(value["white_controls"]) is list and len(value["white_controls"]) == len(WHITE_IDS),
         "ten actual camera-white controls")
    for check, name in zip(value["white_controls"], WHITE_IDS):
        closed(check, ("id", "pass", "evidence"), "camera-white control")
        need(check["id"] == name and check["pass"] is True and type(check["evidence"]) is dict,
             "actual camera-white control: " + name)
    return value


def reuse_plan_equal(new_bytes, old_bytes):
    need(strict(new_bytes) == strict(old_bytes) and new_bytes == old_bytes, "full nine-plan byte/content equality")


def first_reuse(release, fresh_plan, current_originals, files):
    """One literal historical primary, never a general resume or new producer call."""
    refs = release["reuse_first"]
    closed(refs, ("result", "frame_result", "primary_launch", "independent_refusal", "outer", "console", "exit"),
           "original0 reuse authority")
    for ref in refs.values():
        need(ref in release["inputs"], "reuse metadata absent from released inputs")
    old = files.read(refs["result"])
    need(files.path(refs["result"]) == HERE / "native-derivative-1/result.json" and
         old.get("schema") == "m193c-native-derivative-run-v1" and old.get("status") == "REFUSED" and
         type(old.get("error")) is str and old["error"] and old.get("finalization_errors") == [] and
         old["first_refusal"]["original_index"] == 0 and old["current_stage"] == "independent-child" and
         old["unvisited"] == [item[0] for item in POPULATION[1:]] and len(old["rows"]) == 1,
         "exact retained first native refusal; no old parent admission")
    need(old["build"] == release["build"] and old["originals_before"] == old["originals_after"] == current_originals and
         old["sources_before"] == old["sources_after"] and old["inputs_before"] == old["inputs_after"],
         "same build/all-nine original observations and historical closure")
    binding_map(old["sources_before"], files)
    need(all(release["source_bindings"].get(k) == v for k, v in old["sources_before"].items()),
         "historical source bytes still bound")
    row = files.read(refs["frame_result"])
    need(row == old["rows"][0] and row["ordinal"] == row["original_index"] == 0 and
         row["stage"] == "independent-child" and row["snapshot_deleted"] is False,
         "exact historical first row")
    launch = files.read(refs["primary_launch"])
    need(launch == row["primary_launch"], "actual historical primary launch association")
    outer = files.read(refs["outer"])
    need(outer["command"] == old["invocation"] and outer["release_sha256"] == old["execution_release"]["sha256"] and
         type(outer["exit_code"]) is int and outer["exit_code"] == 1 and outer["admissible_parent_exit"] is False and
         outer["dependency_error"] is None and outer["dependency_before"] == outer["dependency_after"],
         "preserved old parent refusal and stable dependency endpoints")
    old_release = files.read(old["execution_release"], absolute=True)
    adjacent = [ref for ref in old_release["inputs"] if ref["sha256"] == outer["dependency_supplement_sha256"]]
    need(len(adjacent) == 1 and adjacent[0] in release["inputs"], "old adjacent-DLL supplement association")
    supplement = files.read(adjacent[0])
    need(supplement["schema"] == "m193c-adjacent-dependency-observation-v1" and
         supplement["runtime_sha256"] == release["reader"]["runtime"]["sha256"] and
         supplement["files"] == outer["dependency_before"] and len(supplement["files"]) == 2,
         "unchanged captured runtime and adjacent-DLL byte endpoints")
    for ref in supplement["files"]:
        files.verify(ref, 32*MIB, True)
    exit_path = files.verify(refs["exit"], 64)
    need(exit_path.read_bytes().strip() == b"1", "actual refused old parent exit")
    console_path = files.verify(refs["console"], 16*MIB)
    final = strict([line for line in console_path.read_bytes().splitlines() if line.strip()][-1])
    need(final["status"] == "REFUSED" and Path(final["result"]).resolve() == files.path(refs["result"]) and
         final["error"] == old["error"] and final["finalization_errors"] == [], "actual old final stdout")
    for key in ("cpu_seconds", "wall_seconds", "file_bytes", "metadata_bytes"):
        need(release["prior_work"][key] >= final["work_through_final_checks"][key], "old work remains paid: " + key)
    need(release["prior_work"]["wall_seconds"] >= old["prior_work"]["wall_seconds"] + outer["elapsed_wall_seconds"],
         "old actual outer elapsed remains paid")
    refused = files.read(refs["independent_refusal"])
    need(refused["schema"] == "m193c-native-derivative-independent-frame-v1" and refused["status"] == "REFUSED" and
         "ValueError: independent active dimensions" in refused["error"] and
         refused["finalization_errors"] == [] and refused["original_index"] == 0 and
         refused["request"] == row["read_request"] and
         refused["invocation"]["orig_argv"] == row["independent_launch"]["command"], "preserved visible-domain refusal")
    for key in ("snapshot", "primary_receipt", "tiff"):
        need(refused[key] == row[key], "old refused reader association: " + key)
    fresh = files.read(fresh_plan, MIB, True)
    old_plan = files.read(old["input_plan"], MIB, True)
    new_raw, old_raw = json_bytes(fresh), json_bytes(old_plan)
    need(file_digest(files.path(fresh_plan, True), MIB) == dict(sha256=hashlib.sha256(new_raw).hexdigest(), bytes=len(new_raw)) and
         file_digest(files.path(old["input_plan"], True), MIB) == dict(sha256=hashlib.sha256(old_raw).hexdigest(), bytes=len(old_raw)),
         "both actual plans use the original canonical bytes")
    checks = []
    reuse_plan_equal(new_raw, old_raw)
    checks.append(dict(id="reuse-full-plan-valid", passed=True))
    altered = strict(new_raw)
    target = altered["entries"][1]
    target["sha256"] = ("0" if target["sha256"][0] != "0" else "1") + target["sha256"][1:]
    need(altered["entries"][0] == fresh["entries"][0], "later-entry fault preserves original0")
    refused_plan = None
    try:
        reuse_plan_equal(json_bytes(altered), old_raw)
    except ValueError as exc:
        refused_plan = str(exc)
    need(refused_plan == "full nine-plan byte/content equality", "actual later-entry plan fault refused")
    checks.append(dict(id="reuse-later-entry-refused", passed=True, exception=refused_plan))
    reuse_plan_equal(new_raw, old_raw)
    checks.append(dict(id="reuse-full-plan-restored", passed=True))
    for key, cap in (("snapshot", RAW_CAP), ("primary_receipt", MIB), ("tiff", TIFF_CAP)):
        files.verify(row[key], cap, True)
    native_summary(launch["observation"], files.path(launch["observation"]["log"], True), launch["command"], files)
    return dict(authority=refs, input_plan=old["input_plan"], row=row, launch=launch, checks=checks)


def run_one(ordinal, original, plan_ref, build, exe, release, release_ref, output, process, api, files, reuse=None):
    budget = files.budget
    row = dict(ordinal=ordinal, original_index=original["original_index"], name=original["name"],
               stage="snapshot", snapshot=None, snapshot_deleted=False, primary_launch=None,
               primary_receipt=None, tiff=None, read_request=None, independent_launch=None,
               independent_read=None, primary_reused=reuse is not None, reuse_provenance=None,
               snapshot_retained_from_refused_run=False, error=None)
    base = output / f"frame-{ordinal:02d}"
    base.mkdir()
    snapshot = base / original["name"]
    native_output = base / "native"
    try:
        if reuse is not None:
            need(ordinal == original["original_index"] == 0, "only original0 may reuse a primary")
            row["stage"] = "historical-primary-recheck"
            row["reuse_provenance"] = dict(authority=reuse["authority"], controls=reuse["checks"],
                                            primary_cpu_scope="historical; already charged in prior_work")
            row["snapshot"] = reuse["row"]["snapshot"]
            row["snapshot_retained_from_refused_run"] = True
            snapshot = files.path(row["snapshot"], True)
            plan_ref = reuse["input_plan"]
            native_output = files.path(reuse["row"]["primary_receipt"], True).parent
            launch = reuse["launch"]
            command, fields = launch["command"], launch["environment"]
            row["primary_launch"] = launch
            need(command[0] == str(exe), "historical actual copied executable")
            native_summary(launch["observation"], files.path(launch["observation"]["log"], True), command, files)
        else:
            copy_snapshot(original, snapshot, budget)
            row["snapshot"] = files.bind(snapshot, RAW_CAP, True, retain=False)
            native_tiff = native_output / (Path(original["name"]).stem + "-registration.tiff")
            budget.binary.add(str(native_tiff))
            fields = {"RAYON_NUM_THREADS": "2", ENV_PREFIX + "OUTPUT_DIR": str(native_output),
                      ENV_PREFIX + "INPUT_PLAN": plan_ref["path"], ENV_PREFIX + "INPUT_PLAN_SHA256": plan_ref["sha256"],
                      ENV_PREFIX + "ORIGINAL_INDEX": str(original["original_index"]),
                      ENV_PREFIX + "SNAPSHOT": str(snapshot)}
            env, removed = process.clean_environment(fields)
            command = [str(exe), "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]
            log = base / "native.log"
            row["stage"] = "native-child"
            files.recheck()
            observation = process.run(command, env, ROOT, log, api=api, **budget.limits(), check=budget.check)
            launch = dict(command=command, environment=fields, removed_environment=removed, observation=observation)
            row["primary_launch"] = launch
            budget.child(observation)
            budget.save(base / "native-launch.json", launch)
            native_summary(observation, log, command, files)
        row["stage"] = "native-receipt"
        primary = primary_result(row, plan_ref, row["snapshot"], native_output, command, fields, files)
        files.verify(row["snapshot"], RAW_CAP, True, retain=False)
        files.recheck()
        row["stage"] = "independent-request"
        limits = budget.limits()
        request = dict(schema="m193c-sensor-white-native-derivative-read-request-v1", execution_release=release_ref,
                       input_plan=plan_ref, original=next(e for e in files.read(plan_ref, MIB, True)["entries"]
                                                       if e["original_index"] == original["original_index"]),
                       snapshot=row["snapshot"], primary_receipt=row["primary_receipt"], tiff=row["tiff"],
                       build=files.bind(files.path(release["build"]), 4 * MIB, True),
                       reader_runtime=files.bind(files.path(release["reader"]["runtime"]), 4 * MIB, True),
                       limits=dict(cpu_seconds=limits["cpu_seconds"], wall_seconds=limits["wall_seconds"],
                                   committed_bytes=8 << 30,
                                   metadata_bytes=min(4 * MIB, 128 * MIB - budget.work()["metadata_bytes"])))
        request_path = base / "read-request.json"
        budget.save(request_path, request)
        row["read_request"] = files.bind(request_path, 4 * MIB, True)
        reader_command = [row["read_request"]["sha256"] if word == "ACTUAL_FRAME_REQUEST_SHA256" else word
                          for word in release["reader"]["commands"][ordinal]]
        reader_env, removed = process.clean_environment()
        python_removed = sorted(key for key in reader_env if key.upper().startswith("PYTHON"))
        for key in python_removed:
            del reader_env[key]
        removed = sorted(set(removed + python_removed))
        row["stage"] = "independent-child"
        observation = process.run(reader_command, reader_env, ROOT, base / "independent.log", api=api,
                                  **budget.limits(), check=budget.check)
        launch = dict(command=reader_command, removed_environment=removed, observation=observation)
        row["independent_launch"] = launch
        budget.child(observation)
        budget.save(base / "independent-launch.json", launch)
        successful_process(observation, reader_command)
        files.verify(observation["log"], 16 * MIB, True)
        row["stage"] = "independent-result"
        directory = base / "independent"
        reader_artifacts(directory, release, files, request["limits"]["metadata_bytes"])
        independent_result(row, row["read_request"], reader_command, directory, primary, files, release)
        row["stage"] = "frame-final-check"
        files.verify(row["snapshot"], RAW_CAP, True, retain=False)
        need(original_observation(original["original_index"], original["name"], original["bytes"], budget) == original,
             "original changed across both consumers")
        files.recheck()
        budget.check(True)
        # Exact verified single file inside this fresh frame directory; never a corpus delete.
        if reuse is None:
            need(snapshot.resolve().is_relative_to(output) and snapshot.name == original["name"],
                 "snapshot removal containment")
            snapshot.unlink()
            row["snapshot_deleted"] = True
        else:
            files.verify(row["snapshot"], RAW_CAP, True)
        row["stage"] = "COMPLETE_FRAME_INDEPENDENTLY_READ"
    except Exception:
        row["error"] = traceback.format_exc()
    return row


def main():
    # Process CPU includes interpreter/import startup; monotonic observation begins
    # at this source's first clock read. Root also retains the outer process outcome.
    started, cpu_started = STARTED, 0.0
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    need(os.name == "nt", "Windows-only native controller")
    need(sys.dont_write_bytecode and "-B" in sys.orig_argv, "parent -B prevents unaccounted bytecode writes")
    need(args.release.is_absolute() and args.output.is_absolute() and hash_form(args.release_sha256),
         "absolute invocation paths/external hash")
    output = args.output.resolve()
    need(output.is_relative_to(HERE) and output != HERE and not output.exists() and output.parent.is_dir(),
         "fresh native workspace output with existing parent")
    with args.release.open("rb") as stream:
        raw = stream.read(4 * MIB + 1)
    need(len(raw) <= 4 * MIB and hashlib.sha256(raw).hexdigest() == args.release_sha256,
         "external execution release pin/extent")
    release = strict(raw)
    closed(release, ("schema", "scope", "source_bindings", "inputs", "commands", "build", "private_admission",
                     "reader", "prior_work", "reuse_first"), "native release")
    need(release["schema"] == "m193c-sensor-white-native-derivative-release-v1" and release["scope"] == "sensor-white-native-nine",
         "native nine release scope")
    need(type(release["commands"]) is list and all(type(row) is list and all(type(v) is str for v in row)
                                                for row in release["commands"]), "literal release commands")
    commands = [[args.release_sha256 if word == "ACTUAL_EXECUTION_RELEASE_SHA256" else word for word in row]
                for row in release["commands"]]
    need(list(sys.orig_argv) in commands, "actual original interpreter invocation not released")
    budget = Budget(output, release["prior_work"], started, cpu_started)
    files = Files(budget)
    output.mkdir()
    result = dict(schema="m193c-sensor-white-native-derivative-run-v1", status="REFUSED", invocation=list(sys.orig_argv),
                  execution_release=None, build=release["build"], private_admission=release["private_admission"],
                  started_utc=datetime.now(timezone.utc).isoformat(), ended_utc=None, sources_before=None,
                  sources_after=None, inputs_before=None, inputs_after=None, input_plan=None,
                  originals_before=[], originals_after=[], rows=[], unvisited=[r[0] for r in POPULATION],
                  prior_work=release["prior_work"], work=None,
                  work_observation_scope="before terminal publication; final complete work is in actual parent stdout",
                  current_stage="release-and-prerequisites", attempted_original_index=None,
                  first_refusal=None, reuse_controls=[], error=None, finalization_errors=[],
                  scope="native registration-development derivatives; independent per-frame read; no coverage/merge admission")
    try:
        result["execution_release"] = files.bind(args.release, 4 * MIB, True)
        need(result["execution_release"]["sha256"] == args.release_sha256, "release reread changed")
        binding_map(release["source_bindings"], files)
        required = {relative(__file__), relative(HERE / "native-derivative-run-preregister.md"),
                    relative(HERE / "sensor-domain-reader-preregister.md"),
                    relative(HERE / "sensor-white-reader-preregister.md"),
                    relative(HERE / "artifact-parent-preregister.md"),
                    relative(HERE / "charter.md"), relative(HERE / "bridge-build.py"), relative(PROCESS), relative(HARNESS)}
        need(required.issubset(release["source_bindings"]), "actual parent source closure")
        result["sources_before"] = release["source_bindings"]
        need(type(release["inputs"]) is list and
             len({item["path"] for item in release["inputs"]}) == len(release["inputs"]), "unique released inputs")
        for ref in release["inputs"]:
            files.verify(ref, 64 * MIB)
        for ref in (release["build"], release["private_admission"], release["reader"]["runtime"]):
            need(ref in release["inputs"], "prerequisite absent from released inputs")
        result["inputs_before"] = release["inputs"]
        build, exe = build_authority(release["build"], release, files)
        need(build["execution_release"] in release["inputs"], "build release absent from inputs")
        reader_authority(release, output, files)
        process, api = load_process(release, files)
        files.recheck()
        budget.save(output / "sources-before.json", release["source_bindings"])
        result["current_stage"] = "artifact-contract-controls"
        artifact_controls(release, output, files)
        # First capture byte access: all nine, before any decoder or snapshot launch.
        identities = set()
        for index, name, size in POPULATION:
            result["current_stage"] = "original-before-hash"
            result["attempted_original_index"] = index
            entry = original_observation(index, name, size, budget)
            identity = entry["device"], entry["file_id"]
            need(identity not in identities, "selected source file identity alias")
            identities.add(identity)
            result["originals_before"].append(entry)
        entries = [{key: row[key] for key in ("original_index", "name", "path", "bytes", "sha256", "mtime_utc", "attributes")}
                   for row in result["originals_before"]]
        plan = dict(schema="m193c-registration-input-plan-v1", status="PLAN_ONLY", entries=entries,
                    build=files.bind(exe, 64 * MIB, True), settings=SETTINGS,
                    source_bindings={name: value["sha256"] for name, value in build["sources_before"].items()})
        budget.save(output / "input-plan.json", plan, MIB)
        result["input_plan"] = files.bind(output / "input-plan.json", MIB, True)
        result["current_stage"] = "historical-original0-reuse"
        result["attempted_original_index"] = 0
        reused = first_reuse(release, result["input_plan"], result["originals_before"], files)
        result["reuse_controls"] = reused["checks"]
        for ordinal, original in enumerate(result["originals_before"]):
            result["current_stage"] = "frame"
            result["attempted_original_index"] = original["original_index"]
            row = run_one(ordinal, original, result["input_plan"], build, exe, release,
                          result["execution_release"], output, process, api, files, reused if ordinal == 0 else None)
            result["rows"].append(row)
            result["current_stage"] = row["stage"]
            result["unvisited"] = [entry[0] for entry in POPULATION[ordinal + 1:]]
            budget.save(output / f"frame-{ordinal:02d}" / "frame-result.json", row)
            need(row["error"] is None and row["stage"] == "COMPLETE_FRAME_INDEPENDENTLY_READ",
                 "first native frame refusal:\n" + str(row["error"]))
        result["status"] = "COMPLETE_NINE_SENSOR_WHITE_DERIVATIVES_AWAITING_COVERAGE"
        result["current_stage"] = "terminal-checks"
        result["attempted_original_index"] = None
    except Exception:
        result["error"] = traceback.format_exc()
        result["first_refusal"] = dict(stage=result["current_stage"],
                                       original_index=result["attempted_original_index"], error=result["error"])
    finally:
        terminal_ref = None

        def final_checks():
            files.recheck()
            for row in result["rows"]:
                if row["independent_read"] is not None:
                    request = files.read(row["read_request"], 4 * MIB, True)
                    reader_artifacts(files.path(row["independent_read"], True).parent, release,
                                     files, request["limits"]["metadata_bytes"])
            for original in result["originals_before"]:
                after = original_observation(original["original_index"], original["name"], original["bytes"], budget)
                need(after == original, "original source changed at final read-only check")
            if terminal_ref is not None:
                files.verify(terminal_ref, 4 * MIB, True)
            budget.check(True)

        # Capture independent secondary errors without erasing the first failed frame.
        for label, action in (
            ("source/input/product closure", files.recheck),
            ("complete budget", lambda: budget.check(True)),
        ):
            try:
                action()
            except Exception:
                result["finalization_errors"].append(label + ": " + traceback.format_exc())
        for original in result["originals_before"]:
            try:
                after = original_observation(original["original_index"], original["name"], original["bytes"], budget)
                result["originals_after"].append(after)
                need(after == original, "original before/after identity mismatch")
            except Exception:
                result["finalization_errors"].append("original after " + original["name"] + ": " + traceback.format_exc())
        try:
            binding_map(release["source_bindings"], files)
            result["sources_after"] = release["source_bindings"]
            for ref in release["inputs"]:
                files.verify(ref, 64 * MIB)
            result["inputs_after"] = release["inputs"]
        except Exception:
            result["finalization_errors"].append("source/input after capture: " + traceback.format_exc())
        if result["error"] is not None or result["finalization_errors"]:
            result["status"] = "REFUSED"
            if result["first_refusal"] is None:
                result["first_refusal"] = dict(stage="final-rechecks", original_index=None,
                                               error=result["finalization_errors"][0])
        result["work"] = budget.work()
        result["ended_utc"] = datetime.now(timezone.utc).isoformat()
        terminal = output / "result.json"
        try:
            budget.save(terminal, result)
            terminal_ref = files.bind(terminal, 4 * MIB, True)
            final_checks()
        except Exception:
            result["status"] = "REFUSED"
            result["finalization_errors"].append("terminal publication/check: " + traceback.format_exc())
            if result["first_refusal"] is None:
                result["first_refusal"] = dict(stage="terminal-publication", original_index=None,
                                               error=result["finalization_errors"][-1])
            try:
                if terminal.exists():
                    need(not (output / "result.first.json").exists(), "fresh retained first terminal")
                    terminal.rename(output / "result.first.json")
                result["work"] = budget.work()
                result["ended_utc"] = datetime.now(timezone.utc).isoformat()
                # A refusal receipt is bounded metadata; exhausted work must not suppress its cause.
                raw = json_bytes(result)
                need(len(raw) <= 4 * MIB, "refusal receipt bound")
                with terminal.open("xb") as stream:
                    need(stream.write(raw) == len(raw), "short refused terminal write")
                    stream.flush()
                    os.fsync(stream.fileno())
            except Exception:
                result["finalization_errors"].append("refusal persistence: " + traceback.format_exc())
        # This last observation is separately retained in the actual parent stdout log.
        if result["status"] == "REFUSED":
            try:
                budget.scan()
            except Exception:
                result["finalization_errors"].append("final extent observation: " + traceback.format_exc())
        actual_work = budget.work()
        summary = dict(status=result["status"], result=str(terminal), work_through_final_checks=actual_work,
                       error=result["error"], finalization_errors=result["finalization_errors"])
        print(json.dumps(summary, allow_nan=False), flush=True)
    return 0 if result["status"] == "COMPLETE_NINE_SENSOR_WHITE_DERIVATIVES_AWAITING_COVERAGE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
