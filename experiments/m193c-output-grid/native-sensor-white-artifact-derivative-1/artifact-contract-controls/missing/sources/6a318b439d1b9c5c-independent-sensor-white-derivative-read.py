"""Sensor-domain native consumer with explicit camera-channel white authority.

No RAW dependency is imported by the private path. Native uses rawpy only for
one bounded snapshot and owns the primary's explicit sensor ROI before close.
The old private and runtime paths remain unchanged; no native visible crop is substituted.
Generic white is retained, but cannot replace missing or disagreeing camera metadata.
"""
from __future__ import annotations

import time
ENTRY_WALL = time.monotonic()
import argparse
from array import array
from copy import deepcopy
from fractions import Fraction
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import struct
import sys
import traceback
import weakref

THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
for _name in THREADS:
    os.environ[_name] = "2"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TIFF_SOURCE = HERE / "independent-derivative-tiff.py"
OLD_TIFF = ROOT / "experiments/m194g-larger-pupil/independent-rgb-tiff.py"
OLD_TIFF_SHA = "d01a74aefcfa15b2146256b54ea51876715ab203b7de123b3cff2b0af4a1b19c"
RAW_LIMIT = 64 << 20
TIFF_LIMIT = 217_048_576
OWNED = ("registration-derivative.rs", "derivative-controls-preregister.md",
         "registration-derivative-design.md", "independent-derivative-design-review.md")
SOURCE_IDS = (
    "valid-affine", "empty-active", "odd-origin-x", "odd-origin-y", "odd-width", "odd-height",
    "stride-storage", "active-outside", "stride-overflow", "axis-bound", "pixel-bound", "buffer-bound",
    "black-nan", "black-negative", "white-infinity", "white-container", "zero-range", "negative-range",
    "red-gain-zero", "green-gain-zero", "blue-gain-nan", "gain-ratio-overflow", "fourth-wb-null",
    "padding-null", "red-gain-live", "black-clamp-live", "wb-order-live", "nine-plan-before-decode",
    "decode-once-drop-before-write", "snapshot-changed", "late-publication-revokes", "restored-affine")
READER_IDS = (
    "producer-valid", "producer-false-check", "producer-omitted-check", "producer-unknown-key",
    "producer-output-association", "producer-changed-reference", "producer-restored",
    "tiff-little-endian", "tiff-big-endian", "tiff-wide322", "old-parser-width-refusal",
    "tiff-appended", "tiff-truncated", "tiff-duplicate-tag", "tiff-compression", "tiff-orientation",
    "tiff-description", "tiff-software", "tiff-wrong-shape", "tiff-bool-shape", "tiff-changed-code",
    "tiff-restored", "affine-rational", "signed-rational", "premature-black-clamp",
    "white-balance-after-mhc", "padding-null", "oracle-restored", "owned-lifetime",
    "borrowed-lifetime-refusal", "lifetime-restored", "wrong-cfa", "wrong-black", "wrong-white",
    "wrong-wb", "metadata-restored", "wrong-active-hash", "wrong-row-hash", "conflicting-reference",
    "json-overflow")
ALL_READER_IDS = ("refusal-helper-false-acceptance",) + READER_IDS
NATIVE_IDS = ("owned-sensor-copy", "active-shape", "local-rggb", "active-u16-bytes",
              "active-row-u16-bytes", "scalar-black-camera-white", "green-normalized-wb",
              "tiff-native-rgb16", "tiff-linear-camera-description", "tiff-full-pixel-read",
              "input-source-stability")
DOMAIN_IDS = ("sensor-nonzero-origin", "visible-crop-null", "wrong-offset-hash-refusal",
              "truncated-buffer-refusal", "borrowed-sensor-refusal", "late-copy-lifetime-destroyer",
              "restored-sensor-copy", "source-origin-cfa")
WHITE_IDS = ("camera-white-authority", "global-match-wrong-camera-refused",
             "mixed-used-camera-white-refused", "absent-camera-white-refused",
             "malformed-camera-white-refused", "malformed-global-white-refused",
             "malformed-cfa-index-refused", "native-black-regression-refused",
             "native-wb-regression-refused", "camera-white-restored")
ORIGINALS = ((0, "DSC00016.ARW", 39030784), (13, "DSC00029.ARW", 39878656),
             (26, "DSC00042.ARW", 40873984), (39, "DSC00055.ARW", 40669184),
             (52, "DSC00068.ARW", 39497728), (65, "DSC00081.ARW", 39235584),
             (78, "DSC00094.ARW", 39096320), (91, "DSC00107.ARW", 39018496),
             (104, "DSC00120.ARW", 38969344))


def need(ok, message):
    if not ok:
        raise ValueError(message)


def keys(value, names, label):
    need(type(value) is dict and set(value) == set(names), label + " closed fields")


def finite(value, label, minimum=None, maximum=None):
    need(type(value) in (int, float) and math.isfinite(value), label + " finite scalar")
    need(minimum is None or value >= minimum, label + " lower bound")
    need(maximum is None or value <= maximum, label + " upper bound")
    return value


def integer(value, label, minimum=0, maximum=2**63 - 1):
    need(type(value) is int and minimum <= value <= maximum, label + " integer bound")
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def valid_sha(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def reject(value):
        raise ValueError("nonfinite JSON constant: " + value)
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)
    def visit(value):
        if type(value) is float:
            need(math.isfinite(value), "nonfinite JSON overflow")
        elif type(value) is list:
            for item in value:
                visit(item)
        elif type(value) is dict:
            for item in value.values():
                visit(item)
    visit(result)
    return result


def path_of(value, *, repository=False):
    need(type(value) is str and value, "path string")
    p = Path(value)
    if not p.is_absolute():
        need(repository and ".." not in p.parts, "absolute reference required")
        p = ROOT / p
    p = p.resolve()
    if repository:
        need(p.is_relative_to(ROOT), "repository containment")
    return p


def ref_shape(ref, cap):
    keys(ref, ("path", "sha256", "bytes"), "FileRef")
    integer(ref["bytes"], "FileRef bytes", 1, cap)
    need(valid_sha(ref["sha256"]), "FileRef sha")
    return path_of(ref["path"], repository=not Path(ref["path"]).is_absolute())


def same_ref(a, b):
    pa, pb = ref_shape(a, 512 << 20), ref_shape(b, 512 << 20)
    need(pa == pb and a["sha256"] == b["sha256"] and a["bytes"] == b["bytes"], "FileRef association")


class Budget:
    def __init__(self, limits, private):
        keys(limits, ("cpu_seconds", "wall_seconds", "artifact_bytes") if private else
             ("cpu_seconds", "wall_seconds", "metadata_bytes", "committed_bytes"), "limits")
        self.cpu = min(120 if private else 1200, finite(limits["cpu_seconds"], "CPU", 0))
        self.wall = min(240, finite(limits["wall_seconds"], "wall", 0))
        cap = limits["artifact_bytes"] if private else limits["metadata_bytes"]
        self.output_limit = min(32 << 20 if private else 4 << 20, integer(cap, "output remaining"))
        if not private:
            need(limits["committed_bytes"] == 8589934592 and type(limits["committed_bytes"]) is int,
                 "outer committed-memory contract")
        self.array_limit = 128 << 20
        self.arrays, self.peak, self.extents, self.written = {}, 0, {}, {}
        self.read_bytes = 0
        self.check()

    def live(self):
        self.arrays = {k: v for k, v in self.arrays.items() if v[0]() is not None}
        return sum(v[1] for v in self.arrays.values())

    def check(self):
        need(time.process_time() <= self.cpu, "reader CPU ceiling")
        need(time.monotonic() - ENTRY_WALL <= self.wall, "reader wall ceiling")
        live = self.live()
        self.peak = max(self.peak, live)
        need(live <= self.array_limit, "reader owned ndarray ceiling")
        need(sum(self.extents.values()) <= self.output_limit, "reader artifact ceiling")

    def check_allocation(self, shape, dtype):
        # Only the public dtype sizes used by these readers are admitted.
        itemsize = {"<u2": 2, ">u2": 2, "uint16": 2, "float32": 4, "<f4": 4}[str(dtype)]
        need(all(type(n) is int and n >= 0 for n in shape), "typed allocation shape")
        need(math.prod(shape) * itemsize + self.live() <= self.array_limit, "allocation ceiling")
        self.check()

    def watch(self, value, label):
        root = value
        while hasattr(root, "base") and hasattr(root.base, "nbytes"):
            root = root.base
        self.live()  # Remove stale weak owners before id lookup.
        old = self.arrays.get(id(root))
        if old is None or old[0]() is not root:
            self.arrays[id(root)] = (weakref.ref(root), int(root.nbytes), label)
        self.check()

    def account(self, path):
        if path.exists():
            self.extents[str(path.resolve()).casefold()] = max(
                self.extents.get(str(path.resolve()).casefold(), 0), path.stat().st_size)

    def write(self, path, raw):
        need(type(raw) is bytes and len(raw) <= 4 << 20, "bounded metadata/fixture write")
        need(sum(self.extents.values()) + len(raw) <= self.output_limit, "prewrite artifact allowance")
        try:
            with path.open("xb") as stream:
                need(stream.write(raw) == len(raw), "short artifact write")
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            self.account(path)
        self.check()
        ref = dict(path=str(path.resolve()), sha256=sha(raw), bytes=len(raw))
        need(file_ref(path) == ref, "actual persisted artifact bytes")
        self.written[str(path.resolve()).casefold()] = ref
        return ref

    def receipt(self):
        return dict(cpu_seconds=time.process_time(), wall_seconds=time.monotonic() - ENTRY_WALL,
                    artifact_bytes=sum(self.extents.values()), artifact_limit=self.output_limit,
                    owned_array_peak_bytes=self.peak, owned_array_limit=self.array_limit,
                    bounded_bytes_read=self.read_bytes)


class Reads:
    def __init__(self, budget):
        self.budget, self.used = budget, {}
        self.runtime_paths = {Path(sys.executable).resolve()}

    def file(self, ref, cap=4 << 20):
        p = ref_shape(ref, cap)
        need(p.is_relative_to(ROOT) or p in self.runtime_paths, "outside-root access is only actual pinned runtime")
        key = str(p).casefold()
        previous = self.used.get(key)
        need(previous is None or (previous["sha256"], previous["bytes"]) ==
             (ref["sha256"], ref["bytes"]), "conflicting consumed reference")
        self.budget.check()
        with p.open("rb") as stream:
            raw = stream.read(cap + 1)
        self.budget.read_bytes += len(raw)
        need(len(raw) == ref["bytes"] and sha(raw) == ref["sha256"], "bound file changed")
        self.used[key] = dict(path=str(p), sha256=ref["sha256"], bytes=ref["bytes"])
        self.budget.check()
        return raw

    def json(self, ref):
        return strict(self.file(ref))

    def recheck(self):
        for ref in tuple(self.used.values()):
            self.file(ref, max(ref["bytes"], 4 << 20))


def file_ref(path, cap=512 << 20):
    p = Path(path).resolve()
    h, count = hashlib.sha256(), 0
    with p.open("rb") as stream:
        for raw in iter(lambda: stream.read(65536), b""):
            count += len(raw)
            need(count <= cap, "file binding cap")
            h.update(raw)
    return dict(path=str(p), sha256=h.hexdigest(), bytes=count)


def load_checked(path, ref, reads, name):
    need(Path(path).resolve() == ref_shape(ref, 4 << 20), "loaded module path")
    raw = reads.file(ref)
    module = type(sys)(name)
    module.__file__ = str(Path(path).resolve())
    sys.modules[name] = module
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module


def runtime_record(np, rawpy=None):
    modules = [np, np._core._multiarray_umath]
    if rawpy is not None:
        modules += [rawpy, rawpy._rawpy]
    paths = {Path(m.__file__).resolve() for m in modules}
    for module in (np,) if rawpy is None else (np, rawpy):
        package = Path(module.__file__).resolve().parent
        for library_dir in (package / ".libs", package.parent / (package.name + ".libs")):
            if library_dir.is_dir():
                paths.update(p.resolve() for p in library_dir.iterdir() if p.suffix.lower() == ".dll")
    return dict(schema="m193c-derivative-reader-runtime-v1",
                python_executable=file_ref(sys.executable), python_version=sys.version,
                numpy_version=np.__version__, rawpy_version=None if rawpy is None else rawpy.__version__,
                libraw_version=None if rawpy is None else list(rawpy.libraw_version),
                module_files=[file_ref(p) for p in sorted(paths)],
                thread_environment={k: os.environ.get(k) for k in THREADS})


def load_runtime(request, reads, private):
    import numpy as np
    rawpy = None
    if private:
        same_ref(request["reader_runtime"], file_ref(sys.executable))
        reads.file(request["reader_runtime"], 64 << 20)
    else:
        import rawpy
        recorded = reads.json(request["reader_runtime"])
        keys(recorded, ("schema", "python_executable", "python_version", "numpy_version", "rawpy_version",
                        "libraw_version", "module_files", "thread_environment"), "runtime")
        actual = runtime_record(np, rawpy)
        need(recorded == actual, "actual dependency runtime differs")
        reads.runtime_paths.update(ref_shape(ref, 128 << 20) for ref in actual["module_files"])
        for ref in recorded["module_files"] + [recorded["python_executable"]]:
            reads.file(ref, 128 << 20)
    return np, rawpy, runtime_record(np, rawpy)


def validate_build(build, reads):
    need(build.get("schema") == "m193c-bridge-build-v1" and
         build.get("status") == "COMPLETE_COMPILED_TESTS_ONLY" and build.get("exit_code") == 0 and
         build.get("rebuilt_cli") is True and build.get("error") is None and
         build.get("finalization_errors") == [], "complete compiled build")
    need(build.get("sources_before") == build.get("sources_after") and build["sources_before"], "stable build sources")
    same_ref({**build["compiler_artifact"], "path": build["test_executable"]["path"]}, build["test_executable"])
    reads.file(build["test_executable"], 256 << 20)
    listing = reads.file(build["test_listing"], 1 << 20).decode("utf8")
    for suffix in ("m193c_derivative_private", "m193c_derivative_native"):
        name = "merge_cmd::production_truth::m193c_registration_derivative::" + suffix
        need(listing.splitlines().count(name + ": test") == 1, "compiled derivative test listing")
    return build


def release_entry(request, request_ref, reads, private):
    release = reads.json(request["execution_release"])
    need(release.get("schema") == ("m193c-private-campaign-release-v1" if private else
                                  "m193c-sensor-white-native-derivative-release-v1"), "release schema")
    need(release.get("scope") == ("private-twelve" if private else "sensor-white-native-nine"), "release scope")
    bindings = release.get("source_bindings")
    need(type(bindings) is dict and bindings, "nonempty source bindings")
    refs = {}
    for name, value in bindings.items():
        p = path_of(name, repository=True)
        keys(value, ("sha256", "bytes"), "source binding")
        ref = dict(path=str(p), **value)
        reads.file(ref, 32 << 20)
        refs[str(p)] = ref
    for p in (Path(__file__).resolve(), TIFF_SOURCE, HERE / "independent-derivative-reader-preregister.md", OLD_TIFF):
        need(str(p) in refs, "required reader source absent: " + p.name)
    if not private:
        need(str(HERE / "sensor-domain-reader-preregister.md") in refs, "sensor-domain specification absent")
        need(str(HERE / "sensor-white-reader-preregister.md") in refs, "camera-white specification absent")
    need(refs[str(OLD_TIFF)]["sha256"] == OLD_TIFF_SHA, "held TIFF dependency")
    token = "ACTUAL_DERIVATIVE_REQUEST_SHA256" if private else "ACTUAL_FRAME_REQUEST_SHA256"
    commands = [release["commands"]["derivative_reader"]] if private else release["reader"]["commands"]
    need(type(commands) is list and (private or len(commands) == 9), "reader command population")
    wanted = []
    for command in commands:
        need(type(command) is list and all(type(v) is str for v in command) and command.count(token) == 1,
             "literal reader command with one token")
        wanted.append([request_ref["sha256"] if x == token else x for x in command])
    need(sys.orig_argv in wanted, "actual reader invocation not released")
    need("-B" in sys.orig_argv and "faulthandler" in sys.orig_argv and
         any(x.startswith("pycache_prefix=") for x in sys.orig_argv), "reader interpreter flags")
    need(Path(sys.orig_argv[0]).resolve() == Path(sys.executable).resolve(), "actual interpreter path")
    same_ref(release["build"], request["build"])
    inputs = release.get("inputs")
    need(type(inputs) is list and inputs, "release inputs required")
    for ref in inputs:
        reads.file(ref, 32 << 20)
    if private:
        same_ref(release["reader_runtime"], request["reader_runtime"])
    else:
        same_ref(release["reader"]["runtime"], request["reader_runtime"])
        same_ref(release["reader"]["script"], refs[str(Path(__file__).resolve())])
    return release, refs


def check_record(identifier, evidence):
    return dict(id=identifier, **{"pass": True}, evidence=evidence)


def validate_private(value, build):
    keys(value, ("schema", "status", "checks", "outputs", "command", "environment", "elapsed_seconds",
                 "error", "finalization_errors"), "private producer")
    need(value["schema"] == "m193c-derivative-private-v1" and
         value["status"] == "COMPLETE_PRIVATE_DERIVATIVE_PRODUCTS_UNVERIFIED" and
         value["error"] is None and value["finalization_errors"] == [], "private producer terminal")
    finite(value["elapsed_seconds"], "producer elapsed", 0)
    need(type(value["checks"]) is list and len(value["checks"]) == 32, "source32 population")
    for record, identifier in zip(value["checks"], SOURCE_IDS, strict=True):
        keys(record, ("id", "pass", "evidence"), "source check")
        need(record["id"] == identifier and record["pass"] is True and type(record["evidence"]) is dict,
             "actual source32 check")
    exe = str(ref_shape(build["test_executable"], 256 << 20))
    need(value["command"] == [exe, "--exact", "merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_private",
                               "--ignored", "--test-threads=1", "--nocapture"], "producer command association")
    keys(value["environment"], ("RAYON_NUM_THREADS", "STREHL_M193C_DERIVATIVE_OUTPUT_DIR"), "private environment")
    need(value["environment"]["RAYON_NUM_THREADS"] == "2", "private thread count")
    directory = path_of(value["environment"]["STREHL_M193C_DERIVATIVE_OUTPUT_DIR"], repository=True)
    keys(value["outputs"], ("affine", "signed_border"), "two private outputs")
    for key, name in (("affine", "affine.tiff"), ("signed_border", "signed-border.tiff")):
        need(ref_shape(value["outputs"][key], TIFF_LIMIT) == directory / name, "private output association")
    return value


def validate_launch(launch, producer, build):
    keys(launch, ("schema", "stage", "status", "command", "environment", "removed_environment_names",
                  "observation", "log", "started_monotonic_ns", "ended_monotonic_ns", "error"), "campaign launch")
    need(launch.get("schema") == "m193c-campaign-child-launch-v1" and
         launch.get("stage") == "derivative_producer" and launch.get("status") == "COMPLETE_CHILD_EXIT_ZERO" and
         launch.get("error") is None, "actual derivative launch")
    need(launch.get("command") == producer["command"] and launch.get("environment") == producer["environment"],
         "producer/observed launch association")
    need(Path(launch["command"][0]).resolve() == ref_shape(build["test_executable"], 256 << 20), "actual copied executable")
    observation = launch["observation"]
    need(observation.get("exit_code") == 0 and observation.get("error") is None and
         observation.get("cleanup_errors") == [] and observation.get("terminal_job_accounting") is True and
         observation.get("job_accounting", {}).get("active_processes") == 0, "terminal successful child Job")
    need(observation.get("command") == launch["command"], "observed command association")
    same_ref(observation["log"], launch["log"])
    need(type(observation.get("log_bytes")) is int and observation["log_bytes"] == launch["log"]["bytes"],
         "observed log extent association")


def reflect(x, size):
    period = 2 * (size - 1)
    x %= period
    return x if x < size else period - x


def channel(x, y):
    return 0 if not (x % 2 or y % 2) else 2 if x % 2 and y % 2 else 1


def private_raw(signed, padding=65000):
    buffer = [[padding] * 40 for _ in range(32)]
    corners = {(0, 0): 2368, (29, 0): 576, (0, 21): 1088, (29, 21): 1472, (10, 8): 48}
    for y in range(22):
        for x in range(30):
            if signed:
                value = corners.get((x, y), 192)
            else:
                value = (320 + 4*x + 8*y, 1088 + 16*x - 8*y, 448 - 2*x + 2*y)[channel(x, y)]
            buffer[y + 4][x + 2] = value
    return [row[2:32] for row in buffer[4:26]]


def mosaic(raw, *, clamp=False, wb=True):
    gains = (2, 1, 4) if wb else (1, 1, 1)
    return [[Fraction(max(0, raw[y][x] - 64) if clamp else raw[y][x] - 64, 4096) * gains[channel(x, y)]
             for x in range(30)] for y in range(22)]


def mhc(values, x, y, c):
    def p(dx, dy):
        return values[reflect(y + dy, 22)][reflect(x + dx, 30)]
    own = channel(x, y)
    if c == own:
        return p(0, 0)
    axis2 = p(-2, 0) + p(2, 0) + p(0, -2) + p(0, 2)
    if c == 1:
        return (4*p(0, 0) + 2*(p(-1, 0)+p(1, 0)+p(0, -1)+p(0, 1)) - axis2) / 8
    if own != 1:
        return (6*p(0, 0) + 2*(p(-1, -1)+p(-1, 1)+p(1, -1)+p(1, 1)) - Fraction(3, 2)*axis2) / 8
    horizontal = (y % 2 == 0 and c == 0) or (y % 2 == 1 and c == 2)
    if not horizontal:
        old = p
        p = lambda dx, dy: old(dy, dx)
    return (5*p(0, 0) + 4*(p(-1, 0)+p(1, 0)) - p(-2, 0)-p(2, 0)
            - p(-1, -1)-p(-1, 1)-p(1, -1)-p(1, 1) + (p(0, -2)+p(0, 2))/2) / 8


def encode(value):
    value = min(Fraction(1), max(Fraction(0), value)) * 65535 + Fraction(1, 2)
    return value.numerator // value.denominator


def expected_image(np, signed, *, clamp=False, late_wb=False, padding=65000):
    values = mosaic(private_raw(signed, padding), clamp=clamp, wb=not late_wb)
    output = np.empty((22, 30, 3), dtype="<u2")
    for y in range(22):
        for x in range(30):
            for c in range(3):
                value = mhc(values, x, y, c) * ((2, 1, 4)[c] if late_wb else 1)
                output[y, x, c] = encode(value)
    return output


def compare_pixels(pixels, expected, signed):
    need(pixels.shape == expected.shape == (22, 30, 3), "comparison shape")
    sites = [(x, y) for y in range(22) for x in range(30)] if signed else [
        (x, y) for y in range(2, 18, 3) for x in range(2, 27, 3)]
    maximum = max(abs(int(pixels[y, x, c]) - int(expected[y, x, c])) for x, y in sites for c in range(3))
    need(maximum <= 1, "independent private pixel discrepancy")
    return dict(compared_sites=len(sites), max_code_error=maximum)


def owned_visible(raw, np, budget, *, copy=True):
    view = raw.raw_image_visible
    need(isinstance(view, np.ndarray) and view.dtype == np.dtype("uint16") and view.ndim == 2,
         "visible native u16 plane")
    h, w = view.shape
    need(0 < w <= 8192 and 0 < h <= 8192 and w*h <= 36_000_000 and w % 2 == h % 2 == 0,
         "active visible bounds")
    budget.check_allocation((h, w), "<u2")
    active = view.copy(order="C") if copy else view
    need(active.flags.owndata and active.flags.c_contiguous and not np.shares_memory(active, view),
         "owned visible copy inside lifetime")
    budget.watch(active, "owned visible RAW")
    return active


def owned_sensor(raw, domain, np, budget, *, copy=True):
    """Copy exactly the declared primary ROI, while the independent decoder lives."""
    keys(domain, ("x", "y", "width", "height"), "sensor ROI")
    for name in domain:
        integer(domain[name], "sensor ROI " + name, 1 if name in ("width", "height") else 0, 8192)
        need(domain[name] % 2 == 0, "sensor ROI even native origin/extent")
    x, y, w, h = (domain[k] for k in ("x", "y", "width", "height"))
    need(w*h <= 36_000_000, "sensor ROI pixel bound")
    full = raw.raw_image
    need(isinstance(full, np.ndarray) and full.ndim == 2 and full.dtype == np.dtype("uint16"),
         "full decoded native u16 plane")
    need(full.shape[0]*full.shape[1] <= 40_000_000 and full.shape == (raw.sizes.raw_height, raw.sizes.raw_width),
         "full decoded shape/metadata association")
    need(x+w <= full.shape[1] and y+h <= full.shape[0], "sensor ROI outside decoded buffer")
    view = full[y:y+h, x:x+w]
    budget.check_allocation((h, w), "<u2")
    active = view.copy(order="C") if copy else view
    need(active.shape == (h, w) and active.flags.owndata and active.flags.c_contiguous and
         not np.shares_memory(active, full), "owned sensor copy inside lifetime")
    budget.watch(active, "owned explicit sensor ROI")
    sizes = {name: int(getattr(raw.sizes, name)) for name in
             ("raw_height", "raw_width", "height", "width", "top_margin", "left_margin", "flip")}
    visible = dict(x=sizes["left_margin"], y=sizes["top_margin"], width=sizes["width"], height=sizes["height"])
    for name, value in visible.items():
        integer(value, "visible metadata " + name, 1 if name in ("width", "height") else 0, 8192)
    need(visible["x"]+visible["width"] <= full.shape[1] and visible["y"]+visible["height"] <= full.shape[0] and
         raw.raw_image_visible.shape == (visible["height"], visible["width"]), "visible metadata bounds/shape")
    indices = [int(raw.raw_color(y+dy, x+dx)) for dy in range(2) for dx in range(2)]
    desc = bytes(raw.color_desc).rstrip(b"\0").decode("ascii")
    need(all(0 <= index < len(desc) for index in indices), "sensor CFA indices")
    return active, dict(sensor_domain=dict(domain), full_shape=list(full.shape), visible_domain=visible,
                        visible_shape=list(raw.raw_image_visible.shape), visible_domain_agrees=visible == domain,
                        sensor_cfa_origin=[x, y], indices=indices, letters=[desc[i] for i in indices],
                        color_desc=desc, sizes=sizes, physical_sensor_validity_claim=False)


def run_sensor_controls(np, budget, records):
    """Eight fixed in-memory calls; no RAW/TIFF/decoder/producer execution."""
    from types import SimpleNamespace
    domain = dict(x=4, y=2, width=8, height=6)
    payloads = [b"".join(struct.pack("<H", 500+31*y+3*x) for x in range(4, 12)) for y in range(2, 8)]
    expected = dict(active=domain, active_sha256_u16_le=sha(b"".join(payloads)),
                    active_row_sha256_u16_le=[sha(row) for row in payloads])

    class Raw:
        def __init__(self, visible=(7, 5, 6, 4), truncate=False):
            self.closed = False
            self.raw_image = np.asarray([[500+31*y+3*x for x in range(16)] for y in range(12)], dtype="<u2")
            budget.watch(self.raw_image, "domain-control full buffer")
            if truncate:
                self.raw_image = self.raw_image[:7]
            vx, vy, vw, vh = visible
            self.raw_image_visible = self.raw_image[vy:vy+vh, vx:vx+vw]
            self.sizes = SimpleNamespace(raw_height=self.raw_image.shape[0], raw_width=16,
                height=vh, width=vw, top_margin=vy, left_margin=vx, flip=0)
            self.color_desc = b"RGBG"
        def __enter__(self):
            return self
        def __exit__(self, *_):
            self.raw_image.fill(65535)
            self.closed = True
        def raw_color(self, y, x):
            need(not self.closed, "CFA queried after decoder close")
            return ((0, 1), (3, 2))[y % 2][x % 2]

    def correct(visible=(7, 5, 6, 4)):
        with Raw(visible) as raw:
            active, witness = owned_sensor(raw, domain, np, budget)
        full, rows = compare_active(active, expected, budget)
        need(raw.closed and witness["visible_domain_agrees"] is False, "observed poisoned close/different visible domain")
        return dict(full_sha256=full, row_sha256=rows, domain=witness, compared_after_poison=True)
    control_call(records, DOMAIN_IDS[0], correct)
    control_call(records, DOMAIN_IDS[1], lambda: correct((2, 4, 10, 6)))

    def offset():
        with Raw() as raw:
            active, _ = owned_sensor(raw, dict(domain, x=6), np, budget)
        compare_active(active, expected, budget)
    control_call(records, DOMAIN_IDS[2], offset, refusal="whole active u16 disagreement")
    def truncated():
        with Raw(truncate=True) as raw:
            owned_sensor(raw, domain, np, budget)
    control_call(records, DOMAIN_IDS[3], truncated, refusal="sensor ROI outside decoded buffer")
    def borrowed():
        with Raw() as raw:
            owned_sensor(raw, domain, np, budget, copy=False)
    control_call(records, DOMAIN_IDS[4], borrowed, refusal="owned sensor copy inside lifetime")
    def late_copy():
        with Raw() as raw:
            borrowed_view = raw.raw_image[2:8, 4:12]
        active = borrowed_view.copy()
        budget.watch(active, "deliberate late sensor copy")
        full, rows = active_hashes(active, budget)
        need(raw.closed and full != expected["active_sha256_u16_le"] and
             all(a != b for a, b in zip(rows, expected["active_row_sha256_u16_le"], strict=True)),
             "actual poisoned late-copy hash destroyer")
        return dict(observed_sha256=full, expected_sha256=expected["active_sha256_u16_le"],
                    all_six_rows_changed=True, compared_after_poison=True)
    control_call(records, DOMAIN_IDS[5], late_copy)
    control_call(records, DOMAIN_IDS[6], correct)
    def cfa_origin():
        with Raw() as raw:
            active, witness = owned_sensor(raw, domain, np, budget)
            wrong = [raw.color_desc[raw.raw_color(5+y, 7+x):raw.raw_color(5+y, 7+x)+1].decode()
                     for y in range(2) for x in range(2)]
        compare_active(active, expected, budget)
        need(witness["sensor_cfa_origin"] == [4, 2] and witness["letters"] == ["R", "G", "G", "B"] and
             wrong == ["B", "G", "G", "R"], "actual sensor-origin CFA versus wrong visible origin")
        return dict(sensor_origin=[4, 2], sensor_letters=witness["letters"],
                    wrong_visible_origin=[7, 5], wrong_visible_letters=wrong)
    control_call(records, DOMAIN_IDS[7], cfa_origin)
    need(tuple(row["id"] for row in records) == DOMAIN_IDS and all(row["pass"] is True for row in records),
         "complete eight sensor controls")


def active_hashes(active, budget):
    digest, rows = hashlib.sha256(), []
    for row in active:
        budget.check()
        raw = row.astype("<u2", copy=False).tobytes(order="C")
        digest.update(raw)
        rows.append(sha(raw))
    return digest.hexdigest(), rows


def validate_independent_metadata(metadata, source):
    need(metadata["letters"] == ["R", "G", "G", "B"], "independent local RGGB")
    black = finite(source["black"], "primary black", 0, 65535)
    white = finite(source["white"], "primary white", 0, 65535)
    need(white > black, "primary range")
    used = sorted(set(metadata["indices"]))
    for i in used:
        need(finite(metadata["black"][i], "independent black", 0, 65535) == black,
             "used-channel black disagrees")
    need(finite(metadata["white"], "independent white", 0, 65535) == white,
         "scalar white disagrees")
    channel_white = metadata["channel_white"]
    if channel_white is not None:
        need(type(channel_white) is list and len(channel_white) >= max(used)+1, "channel white extent")
        for i in used:
            value = channel_white[i]
            if value is not None:
                finite(value, "channel white", 0, 65535)
                need(value == 0 or value == white, "used-channel white disagrees")
    gains = metadata["wb"]
    indices = (metadata["indices"][0], metadata["indices"][1], metadata["indices"][3])
    for i in indices:
        finite(gains[i], "independent WB", 0)
        need(gains[i] > 0, "positive independent WB")
    normalized = [gains[i]/gains[indices[1]] for i in indices]
    need(type(source["wb_rgb"]) is list and len(source["wb_rgb"]) == 3, "primary WB shape")
    for actual, target in zip(normalized, source["wb_rgb"], strict=True):
        need(finite(target, "primary WB", 0) > 0 and
             abs(actual-target) <= 2**-20 * max(1, abs(target)), "green-normalized WB disagrees")
    return dict(used_cfa_indices=used, normalized_wb=normalized,
                camera_white_availability=channel_white, metadata_presence_claim=False)


def native_white_authority(metadata, source):
    """Native-only scalar comparison policy; no generic-value fallback or calibration claim."""
    indices = metadata["indices"]
    need(type(indices) is list and len(indices) == 4 and
         all(type(i) is int and 0 <= i < 4 for i in indices), "camera white CFA indices")
    used = sorted(set(indices))
    generic = metadata["white"]
    need(type(generic) is int and 0 < generic <= 65535, "generic white integer range")
    camera = metadata["channel_white"]
    need(camera is not None, "camera white metadata required; no generic fallback")
    need(type(camera) is list and len(camera) == 4, "camera white four-entry list")
    need(all(type(value) is int and 0 < value <= 65535 for value in camera),
         "camera white positive integer entries")
    selected = camera[used[0]]
    need(all(camera[i] == selected for i in used), "mixed used-channel camera white")
    primary = finite(source["white"], "primary white", 0, 65535)
    need(selected == primary, "selected camera white disagrees with primary")
    return dict(method="m193c-camera-channel-white-v1", generic_white=generic,
                camera_white=list(camera), used_cfa_indices=used, selected_white=selected,
                primary_white=primary, generic_matches_selected=generic == selected,
                selection="equal-positive-used-camera-channels", fallback="forbidden",
                physical_calibration_claim=False, primary_metadata_presence_claim=False)


def validate_native_metadata(metadata, source):
    """Keep the old black/WB arithmetic; select white through the explicit native policy."""
    need(metadata["letters"] == ["R", "G", "G", "B"], "independent local RGGB")
    black = finite(source["black"], "primary black", 0, 65535)
    white = finite(source["white"], "primary white", 0, 65535)
    need(white > black, "primary range")
    authority = native_white_authority(metadata, source)
    used = authority["used_cfa_indices"]
    for i in used:
        need(finite(metadata["black"][i], "independent black", 0, 65535) == black,
             "used-channel black disagrees")
    gains = metadata["wb"]
    indices = (metadata["indices"][0], metadata["indices"][1], metadata["indices"][3])
    for i in indices:
        finite(gains[i], "independent WB", 0)
        need(gains[i] > 0, "positive independent WB")
    normalized = [gains[i]/gains[indices[1]] for i in indices]
    need(type(source["wb_rgb"]) is list and len(source["wb_rgb"]) == 3, "primary WB shape")
    for actual, target in zip(normalized, source["wb_rgb"], strict=True):
        need(finite(target, "primary WB", 0) > 0 and
             abs(actual-target) <= 2**-20 * max(1, abs(target)), "green-normalized WB disagrees")
    return dict(used_cfa_indices=used, normalized_wb=normalized,
                camera_white_availability=metadata["channel_white"], metadata_presence_claim=False,
                white_authority=authority)


def run_white_controls(budget, records):
    """Ten deterministic groups on the actual native metadata consumer, before RAW access."""
    baseline = dict(indices=[0, 1, 3, 2], letters=["R", "G", "G", "B"],
                    black=[64, 64, 64, 64], white=16383, channel_white=[12000]*4,
                    wb=[3.0, 2.0, 5.0, 2.0])
    source = dict(black=64.0, white=12000.0, wb_rgb=[1.5, 1.0, 2.5])

    def invoke(metadata):
        budget.check()
        before, source_before = deepcopy(metadata), deepcopy(source)
        try:
            return validate_native_metadata(metadata, source)
        finally:
            need(metadata == before and source == source_before, "native metadata validation mutated inputs")
            budget.check()

    def valid():
        metadata = deepcopy(baseline)
        agreement = invoke(metadata)
        expected = dict(method="m193c-camera-channel-white-v1", generic_white=16383,
                        camera_white=[12000]*4, used_cfa_indices=[0, 1, 2, 3], selected_white=12000,
                        primary_white=12000.0, generic_matches_selected=False,
                        selection="equal-positive-used-camera-channels", fallback="forbidden",
                        physical_calibration_claim=False, primary_metadata_presence_claim=False)
        need(agreement["white_authority"] == expected and agreement["normalized_wb"] == [1.5, 1.0, 2.5],
             "independent literal camera-white/WB oracle")
        return dict(input=metadata, source=deepcopy(source), agreement=agreement, inputs_unchanged=True)

    def rejected(metadata, expected):
        try:
            invoke(metadata)
        except ValueError as error:
            need(str(error) == expected, "wrong native metadata refusal: " + str(error))
            return dict(input=deepcopy(metadata), source=deepcopy(source), exception_type="ValueError",
                        exception=str(error), expected=expected, inputs_unchanged=True)
        raise ValueError("native metadata defect was accepted: " + expected)

    def changed(key, value, expected):
        metadata = deepcopy(baseline)
        metadata[key] = value
        return rejected(metadata, expected)

    def global_match():
        metadata = deepcopy(baseline)
        metadata["white"] = 12000
        metadata["channel_white"] = [11000]*4
        need(metadata["white"] == source["white"], "matching generic-white fault potency")
        return rejected(metadata, "selected camera white disagrees with primary")

    def malformed_camera():
        rows = []
        for value, expected in (
            ([12000]*3, "camera white four-entry list"),
            ("12000", "camera white four-entry list"),
            ([12000, 12000, 12000, None], "camera white positive integer entries"),
            ([12000, 12000, 12000, 0], "camera white positive integer entries"),
            ([12000, 12000, 12000, -1], "camera white positive integer entries"),
            ([12000, 12000, 12000, True], "camera white positive integer entries"),
            ([12000, 12000, 12000, 12000.0], "camera white positive integer entries"),
            ([12000, 12000, 12000, 65536], "camera white positive integer entries"),
        ):
            rows.append(changed("channel_white", value, expected))
        return dict(attempts=rows)

    def malformed_generic():
        return dict(attempts=[changed("white", value, "generic white integer range")
                              for value in (None, True, 16383.0, 0, 65536)])

    def malformed_indices():
        return dict(attempts=[changed("indices", value, "camera white CFA indices")
                              for value in ([0, 1, 3], [0, 1, 3, 4], [0, 1, 3, True])])

    actions = (valid, global_match,
               lambda: changed("channel_white", [12000, 12000, 12000, 12001], "mixed used-channel camera white"),
               lambda: changed("channel_white", None, "camera white metadata required; no generic fallback"),
               malformed_camera, malformed_generic, malformed_indices,
               lambda: changed("black", [64, 64, 65, 64], "used-channel black disagrees"),
               lambda: changed("wb", [3.0, 2.0, 6.0, 2.0], "green-normalized WB disagrees"), valid)
    for identifier, action in zip(WHITE_IDS, actions, strict=True):
        control_call(records, identifier, action)
    need(tuple(row["id"] for row in records) == WHITE_IDS and all(row["pass"] is True for row in records),
         "complete ten native camera-white controls")


def compare_active(active, source, budget):
    need(list(active.shape) == [source["active"]["height"], source["active"]["width"]], "active shape agreement")
    full, rows = active_hashes(active, budget)
    need(full == source["active_sha256_u16_le"], "whole active u16 disagreement")
    need(rows == source["active_row_sha256_u16_le"], "active row u16 disagreement")
    return full, rows


def fixture_tiff(pixels, parser, *, endian="<", override=None, duplicate=False):
    """Private classic-TIFF bytes; not a production writer invocation."""
    h, w, channels = pixels.shape
    need(channels == 3, "fixture RGB")
    values = [(256, 4, (w,)), (257, 4, (h,)), (258, 3, (16, 16, 16)),
              (259, 3, (1,)), (262, 3, (2,)), (270, 2, parser.DESCRIPTION),
              (273, 4, (0,)), (274, 3, (1,)), (277, 3, (3,)), (278, 4, (h,)),
              (279, 4, (h*w*6,)), (305, 2, parser.SOFTWARE)]
    if override:
        values = [(tag, typ, override.get(tag, value)) for tag, typ, value in values]
    if duplicate:
        values.append(values[0])
    end_ifd = 8 + 2 + 12*len(values) + 4
    tail, fields = bytearray(), []
    strip_entry = None
    for tag, typ, value in values:
        raw = (value.encode("ascii") + b"\0") if typ == 2 else struct.pack(endian +
              ("H" if typ == 3 else "I")*len(value), *value)
        count = len(raw) if typ == 2 else len(value)
        if len(raw) <= 4:
            field = raw + bytes(4-len(raw))
        else:
            field = struct.pack(endian + "I", end_ifd + len(tail))
            tail.extend(raw)
        if tag == 273:
            strip_entry = len(fields)
        fields.append(struct.pack(endian + "HHI", tag, typ, count) + field)
    need(strip_entry is not None, "fixture strip")
    offset = end_ifd + len(tail)
    fields[strip_entry] = fields[strip_entry][:8] + struct.pack(endian + "I", offset)
    header = (b"II" if endian == "<" else b"MM") + struct.pack(endian + "HIH", 42, 8, len(fields))
    return header + b"".join(fields) + bytes(4) + bytes(tail) + pixels.astype(endian + "u2").tobytes()


def control_call(records, identifier, function, *, refusal=None):
    row = dict(id=identifier, **{"pass": False}, evidence={})
    records.append(row)
    try:
        evidence = function()
    except ValueError as error:
        row["evidence"] = dict(exception_type=type(error).__name__, exception=str(error), expected=refusal)
        if refusal is None or refusal not in str(error):
            raise
        row["pass"] = True
    else:
        # Never catch this helper's own failed expectation as subject evidence.
        need(refusal is None, "expected refusal did not occur: " + identifier)
        row["evidence"] = {} if evidence is None else evidence
        row["pass"] = True


def run_private_controls(producer, build, parser, old_parser, np, reads, budget, directory, records):
    def helper_power():
        attempt = []
        try:
            control_call(attempt, "tiff-compression", lambda: {"accepted": True}, refusal="compression")
        except ValueError as error:
            need(str(error) == "expected refusal did not occur: tiff-compression" and
                 len(attempt) == 1 and attempt[0]["pass"] is False, "refusal helper power witness")
            return dict(accepted_subject_rejected=True, attempted=attempt, exception=str(error))
        raise ValueError("refusal helper accepted a normal-returning subject")
    control_call(records, ALL_READER_IDS[0], helper_power)
    affine = expected_image(np, False)
    signed = expected_image(np, True)
    budget.watch(affine, "private affine oracle")
    budget.watch(signed, "private signed oracle")
    fdir = directory / "fixtures"
    fdir.mkdir()
    refs = {"affine": budget.write(fdir / "affine.tiff", fixture_tiff(affine, parser)),
            "signed_border": budget.write(fdir / "signed-border.tiff", fixture_tiff(signed, parser))}
    fixture = deepcopy(producer)
    fixture["outputs"] = refs
    fixture["environment"]["STREHL_M193C_DERIVATIVE_OUTPUT_DIR"] = str(fdir.resolve())

    def fixture_entry(value):
        validate_private(value, build)
        for name in ("affine", "signed_border"):
            raw = reads.file(value["outputs"][name], 1 << 20)
            pixels, evidence = parser.read_rgb_tiff(raw, (22, 30, 3), budget, numpy=np)
            compare_pixels(pixels, affine if name == "affine" else signed, name != "affine")
        return dict(status="PRIVATE_FIXTURE_ENTRY_ONLY", output_count=2)

    control_call(records, READER_IDS[0], lambda: fixture_entry(fixture))
    bad = deepcopy(fixture); bad["checks"][0]["pass"] = False
    control_call(records, READER_IDS[1], lambda: fixture_entry(bad), refusal="actual source32")
    bad = deepcopy(fixture); bad["checks"].pop()
    control_call(records, READER_IDS[2], lambda: fixture_entry(bad), refusal="source32 population")
    bad = deepcopy(fixture); bad["unknown"] = True
    control_call(records, READER_IDS[3], lambda: fixture_entry(bad), refusal="closed fields")
    bad = deepcopy(fixture); bad["outputs"]["affine"] = refs["signed_border"]
    control_call(records, READER_IDS[4], lambda: fixture_entry(bad), refusal="output association")
    bad = deepcopy(fixture); bad["outputs"]["affine"]["sha256"] = "0"*64
    control_call(records, READER_IDS[5], lambda: fixture_entry(bad), refusal="conflicting consumed reference")
    control_call(records, READER_IDS[6], lambda: fixture_entry(fixture))

    def tiff_case(identifier, raw, *, shape=(22, 30, 3), expected=affine, signed_case=False):
        ref = budget.write(fdir / (identifier + ".tiff"), raw)
        consumed = reads.file(ref, 1 << 20)
        pixels, evidence = parser.read_rgb_tiff(consumed, shape, budget, numpy=np)
        if expected is not None:
            compare_pixels(pixels, expected, signed_case)
        return dict(tiff=ref, pixel_sha256=evidence["pixel_sha256"])

    little = fixture_tiff(affine, parser)
    control_call(records, READER_IDS[7], lambda: tiff_case(READER_IDS[7], little))
    control_call(records, READER_IDS[8], lambda: tiff_case(READER_IDS[8], fixture_tiff(affine, parser, endian=">")))
    wide = np.zeros((2, 322, 3), dtype="<u2")
    budget.watch(wide, "wide TIFF fixture")
    wide_ref = budget.write(fdir / "wide.tiff", fixture_tiff(wide, parser))
    control_call(records, READER_IDS[9], lambda: parser.read_rgb_tiff(reads.file(wide_ref), (2, 322, 3), budget)[1])
    control_call(records, READER_IDS[10], lambda: old_parser.read_rgb_tiff(wide_ref["path"], (2, 322, 3), wide_ref["sha256"], budget),
                 refusal="typed native-bounded")
    control_call(records, READER_IDS[11], lambda: tiff_case(READER_IDS[11], little+b"x"), refusal="trailing bytes")
    control_call(records, READER_IDS[12], lambda: tiff_case(READER_IDS[12], little[:-1]), refusal="strip outside")
    control_call(records, READER_IDS[13], lambda: tiff_case(READER_IDS[13], fixture_tiff(affine, parser, duplicate=True)), refusal="duplicate tag")
    control_call(records, READER_IDS[14], lambda: tiff_case(READER_IDS[14], fixture_tiff(affine, parser, override={259: (5,)})), refusal="compression")
    control_call(records, READER_IDS[15], lambda: tiff_case(READER_IDS[15], fixture_tiff(affine, parser, override={274: (2,)})), refusal="orientation")
    control_call(records, READER_IDS[16], lambda: tiff_case(READER_IDS[16], fixture_tiff(affine, parser, override={270: "sRGB"})), refusal="CameraLinear description")
    control_call(records, READER_IDS[17], lambda: tiff_case(READER_IDS[17], fixture_tiff(affine, parser, override={305: "strehl wrong"})), refusal="measurement software")
    control_call(records, READER_IDS[18], lambda: tiff_case(READER_IDS[18], little, shape=(20, 30, 3)), refusal="dimensions/channels")
    control_call(records, READER_IDS[19], lambda: tiff_case(READER_IDS[19], little, shape=(True, 30, 3)), refusal="typed native-bounded")
    changed = affine.copy(); budget.watch(changed, "changed private code"); changed[8, 11, 0] += 64
    control_call(records, READER_IDS[20], lambda: tiff_case(READER_IDS[20], fixture_tiff(changed, parser)), refusal="pixel discrepancy")
    control_call(records, READER_IDS[21], lambda: tiff_case(READER_IDS[21], little))

    def affine_formula():
        for y in range(2, 18, 3):
            for x in range(2, 27, 3):
                literal = (Fraction(1, 8)+Fraction(x, 512)+Fraction(y, 256),
                           Fraction(1, 4)+Fraction(x, 256)-Fraction(y, 512),
                           Fraction(3, 8)-Fraction(x, 512)+Fraction(y, 512))
                for c in range(3):
                    need(int(affine[y, x, c]) == encode(literal[c]), "affine rational component")
        return dict(sites=54, channels=3, arithmetic="Fraction affine versus Fraction MHC")
    control_call(records, READER_IDS[22], affine_formula)
    values = mosaic(private_raw(True))
    def signed_component():
        need(values[8][10] == -Fraction(1, 128), "below-black signed source")
        need(max(max(row) for row in values) > 1, "above-white source")
        need(mhc(values, 0, 0, 0) == Fraction(9, 8), "literal corner R")
        return dict(signed_r= str(values[8][10]), corner_r=str(mhc(values, 0, 0, 0)), full_sites=660)
    control_call(records, READER_IDS[23], signed_component)
    clamped = expected_image(np, True, clamp=True); budget.watch(clamped, "early clamp fault")
    delta = mhc(mosaic(private_raw(True), clamp=True), 11, 8, 0) - mhc(values, 11, 8, 0)
    need(delta == Fraction(1, 256), "fixed early-clamp control power")
    control_call(records, READER_IDS[24], lambda: tiff_case(READER_IDS[24], fixture_tiff(clamped, parser), expected=signed, signed_case=True),
                 refusal="pixel discrepancy")
    late = expected_image(np, True, late_wb=True); budget.watch(late, "late WB fault")
    need(abs(int(late[8, 10, 1])-int(signed[8, 10, 1])) > 128, "fixed WB-order control power")
    control_call(records, READER_IDS[25], lambda: tiff_case(READER_IDS[25], fixture_tiff(late, parser), expected=signed, signed_case=True),
                 refusal="pixel discrepancy")
    def padding_null():
        companion = expected_image(np, True, padding=17)
        budget.watch(companion, "padding null oracle")
        need(companion.tobytes() == signed.tobytes() and private_raw(True, 17) == private_raw(True), "padding byte null")
        return dict(pixel_sha256=sha(companion.tobytes()), unchanged=True,
                    scope="array-layout identity after extracting the same active rectangle; arithmetic null",
                    pipeline_control="separate actual producer source32 padding-null")
    control_call(records, READER_IDS[26], padding_null)
    control_call(records, READER_IDS[27], lambda: tiff_case(READER_IDS[27], fixture_tiff(signed, parser), expected=signed, signed_case=True))

    class PoisonContext:
        def __init__(self):
            self.backing = np.full((26, 36), 17, dtype="<u2")
            budget.watch(self.backing, "private borrowed owner")
            self.raw_image_visible = self.backing[2:24, 3:33]
            self.raw_image_visible[:] = np.asarray(private_raw(False), dtype="<u2")
        def __enter__(self): return self
        def __exit__(self, *_): self.backing[:] = 65535
        def postprocess(self, *_args, **_kwargs): raise AssertionError("postprocess must never execute")
    def lifetime(copy=True):
        with PoisonContext() as raw:
            result = owned_visible(raw, np, budget, copy=copy)
        need(result.tolist() == private_raw(False), "post-close copy changed")
        return dict(owned=True, compared_after_context=True, postprocess_calls=0)
    control_call(records, READER_IDS[28], lifetime)
    control_call(records, READER_IDS[29], lambda: lifetime(False), refusal="owned visible copy")
    control_call(records, READER_IDS[30], lifetime)

    metadata = dict(letters=["R", "G", "G", "B"], indices=[0, 1, 3, 2], black=[64]*4,
                    white=4160, channel_white=[4160]*4, wb=[2, 1, 4, 1])
    source = dict(black=64, white=4160, wb_rgb=[2, 1, 4], active=dict(width=30, height=22))
    for i, (field, replacement, wanted) in enumerate((
            ("letters", ["G", "R", "B", "G"], "local RGGB"),
            ("black", [64, 64, 64, 63], "black disagrees"),
            ("channel_white", [4160, 4160, 4160, 4095], "white disagrees"),
            ("wb", [3, 1, 4, 1], "WB disagrees"))):
        bad_meta = deepcopy(metadata); bad_meta[field] = replacement
        control_call(records, READER_IDS[31+i], lambda bad_meta=bad_meta: validate_independent_metadata(bad_meta, source), refusal=wanted)
    control_call(records, READER_IDS[35], lambda: validate_independent_metadata(metadata, source))
    active = np.asarray(private_raw(False), dtype="<u2"); budget.watch(active, "private active hash oracle")
    full, rows = active_hashes(active, budget)
    source.update(active_sha256_u16_le=full, active_row_sha256_u16_le=rows)
    bad_source = deepcopy(source); bad_source["active_sha256_u16_le"] = "0"*64
    control_call(records, READER_IDS[36], lambda: compare_active(active, bad_source, budget), refusal="whole active")
    bad_source = deepcopy(source); bad_source["active_row_sha256_u16_le"][7] = "0"*64
    control_call(records, READER_IDS[37], lambda: compare_active(active, bad_source, budget), refusal="active row")
    conflict = dict(refs["affine"], sha256="f"*64)
    control_call(records, READER_IDS[38], lambda: reads.file(conflict), refusal="conflicting consumed")
    control_call(records, READER_IDS[39], lambda: strict(b'{"value":1e999}'), refusal="nonfinite JSON overflow")
    need(tuple(row["id"] for row in records) == ALL_READER_IDS and all(row["pass"] is True for row in records),
         "complete41 independent controls")
    return affine, signed


def private_run(request, result, reads, budget, np, parser, old_parser, directory):
    keys(request, ("schema", "execution_release", "build", "producer_result", "producer_launch", "reader_runtime", "limits"), "private request")
    need(request["schema"] == "m193c-derivative-private-read-request-v1", "private request schema")
    build = validate_build(reads.json(request["build"]), reads)
    producer = validate_private(reads.json(request["producer_result"]), build)
    launch = reads.json(request["producer_launch"])
    validate_launch(launch, producer, build)
    reads.file(launch["log"], 16 << 20)
    result["checks"]["source"] = producer["checks"]
    affine, signed = run_private_controls(producer, build, parser, old_parser, np, reads, budget,
                                         directory, result["checks"]["reader"])
    for name, expected in (("affine", affine), ("signed_border", signed)):
        raw = reads.file(producer["outputs"][name], TIFF_LIMIT)
        pixels, evidence = parser.read_rgb_tiff(raw, (22, 30, 3), budget, numpy=np)
        comparison = compare_pixels(pixels, expected, name == "signed_border")
        result["outputs"][name] = dict(tiff=producer["outputs"][name],
                                      pixel_sha256_u16_le=evidence["pixel_sha256"], shape=[22, 30, 3], **comparison)
    need(len(result["outputs"]) == 2, "actual two complete private outputs")


def validate_plan(plan, build):
    keys(plan, ("schema", "status", "entries", "build", "source_bindings", "settings"), "input plan")
    need(plan["schema"] == "m193c-registration-input-plan-v1" and plan["status"] == "PLAN_ONLY", "input plan status")
    same_ref(plan["build"], build["test_executable"])
    need(type(plan["entries"]) is list and len(plan["entries"]) == 9, "nine exact inputs")
    for entry, (index, name, size) in zip(plan["entries"], ORIGINALS, strict=True):
        keys(entry, ("original_index", "name", "path", "bytes", "sha256", "mtime_utc", "attributes"), "input entry")
        need(type(entry["original_index"]) is int and entry["original_index"] == index and entry["name"] == name and
             type(entry["bytes"]) is int and entry["bytes"] == size and valid_sha(entry["sha256"]), "literal selected input")
        need(path_of(entry["path"]) == Path("D:/personal/macro/coffee-bean") / name, "literal corpus identity")
        need(type(entry["mtime_utc"]) is str and 1 <= len(entry["mtime_utc"]) <= 128, "input mtime observation")
        integer(entry["attributes"], "Windows attributes", 0, 2**32-1)
    need(plan["settings"] == dict(purpose="registration-development-only", colour="linear-camera-native", transfer="identity",
                                  matrix=None, orientation_applied=False, spatial_transform="identity"), "fixed derivative convention")
    # bool orientation is an explicit typed field, not integer zero.
    need(plan["settings"]["orientation_applied"] is False, "orientation type")
    expected = {name: binding["sha256"] for name, binding in build["sources_before"].items()}
    need(plan["source_bindings"] == expected, "plan/compiled source set")
    return plan


def f32_bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def validate_source(source, plan):
    keys(source, ("stride", "buffer_height", "allocated_samples", "allocated_bytes", "active", "active_samples",
                  "active_sha256_u16_le", "active_row_sha256_u16_le", "black", "white", "black_f32_bits",
                  "white_f32_bits", "inverse_range_f32_bits", "wb_rgb", "wb_rgb_f32_bits", "raw_wb_f32_bits",
                  "normalized_min", "normalized_max", "mosaic_bytes", "cfa_validation", "level_selection",
                  "operation", "compiled_sources", "decode_calls", "live_frame_leases_after_prepare"), "primary source")
    keys(source["active"], ("x", "y", "width", "height"), "active rectangle")
    active = source["active"]
    for name in ("x", "y", "width", "height"):
        integer(active[name], "active " + name, 1 if name in ("width", "height") else 0, 8192)
        need(active[name] % 2 == 0, "primary active parity")
    stride = integer(source["stride"], "stride", 1)
    height = integer(source["buffer_height"], "buffer height", 1)
    need(stride*height <= 40_000_000 and active["width"]*active["height"] <= 36_000_000 and
         active["x"]+active["width"] <= stride and active["y"]+active["height"] <= height, "primary active/storage bounds")
    expected = dict(allocated_samples=stride*height, allocated_bytes=2*stride*height,
                    active_samples=active["width"]*active["height"], mosaic_bytes=4*active["width"]*active["height"],
                    decode_calls=1, live_frame_leases_after_prepare=0)
    for name, value in expected.items():
        need(type(source[name]) is int and source[name] == value, "source exact count " + name)
    need(valid_sha(source["active_sha256_u16_le"]) and type(source["active_row_sha256_u16_le"]) is list and
         len(source["active_row_sha256_u16_le"]) == active["height"] and
         all(valid_sha(x) for x in source["active_row_sha256_u16_le"]), "source active hash population")
    black, white = finite(source["black"], "black", 0, 65535), finite(source["white"], "white", 0, 65535)
    need(white > black, "positive range")
    for name, value in (("black_f32_bits", black), ("white_f32_bits", white),
                        ("inverse_range_f32_bits", 1/(white-black))):
        need(type(source[name]) is int and source[name] == f32_bits(value), "source f32 level bits")
    need(type(source["wb_rgb"]) is list and len(source["wb_rgb"]) == 3 and
         type(source["wb_rgb_f32_bits"]) is list and len(source["wb_rgb_f32_bits"]) == 3, "source WB arrays")
    for value, bits in zip(source["wb_rgb"], source["wb_rgb_f32_bits"], strict=True):
        need(finite(value, "source WB", 0) > 0 and type(bits) is int and bits == f32_bits(value), "source WB bits")
    need(type(source["raw_wb_f32_bits"]) is list and len(source["raw_wb_f32_bits"]) == 4, "raw WB bit extent")
    for value in source["raw_wb_f32_bits"]:
        integer(value, "raw WB bits", 0, 2**32-1)
    need(finite(source["normalized_min"], "normalized min") <= finite(source["normalized_max"], "normalized max"),
         "normalized source extrema")
    need(source["cfa_validation"] == "owned decoder requires camera RGGB; even active origin preserves local RGGB", "CFA convention")
    need(source["level_selection"] == "existing wrapper resolved scalar; absent black/white can become0/65535; metadata presence unproved", "level convention")
    need(source["operation"] == "((sample-black)*(1.0f32/(white-black)))*green-normalized-as-shot-gain", "normalization convention")
    expected_pins = {"experiments/m193c-output-grid/" + name: plan["source_bindings"]["experiments/m193c-output-grid/" + name]
                     for name in OWNED}
    need(source["compiled_sources"] == expected_pins, "actual owned compiled sources")


def native_run(request, result, reads, budget, np, rawpy, parser):
    keys(request, ("schema", "execution_release", "input_plan", "original", "snapshot", "primary_receipt",
                  "tiff", "build", "reader_runtime", "limits"), "native request")
    need(request["schema"] == "m193c-sensor-white-native-derivative-read-request-v1", "native request schema")
    build = validate_build(reads.json(request["build"]), reads)
    plan = validate_plan(reads.json(request["input_plan"]), build)
    need(request["original"] in plan["entries"], "selected plan entry")
    selected = request["original"]
    integer(selected["original_index"], "selected original")
    primary = reads.json(request["primary_receipt"])
    keys(primary, ("schema", "status", "input_plan", "selected", "snapshot", "source", "output", "command", "environment",
                   "elapsed_seconds", "error", "finalization_errors"), "primary receipt")
    need(primary["schema"] == "m193c-registration-derivative-v1" and primary["status"] == "COMPLETE_REGISTRATION_DERIVATIVE_UNVERIFIED"
         and primary["error"] is None and primary["finalization_errors"] == [], "complete primary derivative")
    need(type(primary["selected"]) is int and primary["selected"] == selected["original_index"], "primary original identity")
    finite(primary["elapsed_seconds"], "primary elapsed", 0)
    same_ref(primary["input_plan"], request["input_plan"])
    same_ref(primary["snapshot"], request["snapshot"])
    same_ref(primary["output"], request["tiff"])
    snapshot = ref_shape(request["snapshot"], RAW_LIMIT)
    need(snapshot.is_relative_to(ROOT) and snapshot.name == selected["name"] and
         request["snapshot"]["sha256"] == selected["sha256"] and request["snapshot"]["bytes"] == selected["bytes"],
         "live snapshot/original byte identity")
    tiff_path = ref_shape(request["tiff"], TIFF_LIMIT)
    need(tiff_path.is_relative_to(ROOT) and tiff_path.name == Path(selected["name"]).stem + "-registration.tiff", "native output identity")
    exe = str(ref_shape(build["test_executable"], 256 << 20))
    need(primary["command"] == [exe, "--exact", "merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native",
                                 "--ignored", "--test-threads=1", "--nocapture"], "native exact producer command")
    expected_env = dict(RAYON_NUM_THREADS="2", STREHL_M193C_DERIVATIVE_OUTPUT_DIR=str(tiff_path.parent),
                        STREHL_M193C_DERIVATIVE_INPUT_PLAN=str(ref_shape(request["input_plan"], 4 << 20)),
                        STREHL_M193C_DERIVATIVE_INPUT_PLAN_SHA256=request["input_plan"]["sha256"],
                        STREHL_M193C_DERIVATIVE_ORIGINAL_INDEX=str(selected["original_index"]),
                        STREHL_M193C_DERIVATIVE_SNAPSHOT=str(snapshot))
    need(primary["environment"] == expected_env, "native primary environment")
    source = primary["source"]
    validate_source(source, plan)
    run_sensor_controls(np, budget, result["domain_controls"])
    run_white_controls(budget, result["white_controls"])
    raw_bytes = reads.file(request["snapshot"], RAW_LIMIT)
    with rawpy.imread(io.BytesIO(raw_bytes)) as raw:
        active, domain_witness = owned_sensor(raw, source["active"], np, budget)
        indices, letters, desc = (domain_witness[k] for k in ("indices", "letters", "color_desc"))
        # Camera metadata can carry a deliberately unused fourth NaN. Record it
        # as null; every actually consumed R/G1/B coefficient remains finite.
        wb = [float(v) if math.isfinite(float(v)) else None for v in raw.camera_whitebalance]
        metadata = dict(indices=indices, letters=letters, black=list(raw.black_level_per_channel),
                        white=raw.white_level, channel_white=raw.camera_white_level_per_channel,
                        wb=wb, color_desc=desc, sizes=domain_witness["sizes"], sensor_domain=domain_witness)
    del raw_bytes
    result["checks"].append(check_record(NATIVE_IDS[0], dict(owned=bool(active.flags.owndata),
                               contiguous=bool(active.flags.c_contiguous), compared_after_context=True,
                               independent_decoder_metadata=metadata, postprocess_calls=0)))
    need(active.shape == (source["active"]["height"], source["active"]["width"]), "independent active dimensions")
    result["checks"].append(check_record(NATIVE_IDS[1], dict(shape=list(active.shape),
                              primary_padding=source["active"], independent_padding=metadata["sizes"])))
    need(letters == ["R", "G", "G", "B"], "independent local RGGB")
    result["checks"].append(check_record(NATIVE_IDS[2], dict(indices=indices, letters=letters)))
    full, rows = active_hashes(active, budget)
    need(full == source["active_sha256_u16_le"], "whole active u16 disagreement")
    result["active_sha256_u16_le"] = full
    result["checks"].append(check_record(NATIVE_IDS[3], dict(sha256=full, samples=int(active.size))))
    need(rows == source["active_row_sha256_u16_le"], "active row u16 disagreement")
    result["checks"].append(check_record(NATIVE_IDS[4], dict(rows=len(rows), row_sha256_u16_le=rows)))
    agreement = validate_native_metadata(metadata, source)
    result["checks"].append(check_record(NATIVE_IDS[5], dict(black=source["black"], white=source["white"], **agreement)))
    result["checks"].append(check_record(NATIVE_IDS[6], dict(actual=agreement["normalized_wb"], primary=source["wb_rgb"],
                              relative_absolute_factor=2**-20, green_denominator="local G1")))
    del active
    raw_tiff = reads.file(request["tiff"], TIFF_LIMIT)
    _, evidence = parser.read_rgb_tiff(raw_tiff, (source["active"]["height"], source["active"]["width"], 3), budget)
    result["tiff_pixel_sha256_u16_le"] = evidence["pixel_sha256"]
    result["checks"].append(check_record(NATIVE_IDS[7], dict(shape=evidence["shape"], endian=evidence["endian"], strip_count=evidence["strip_count"])))
    result["checks"].append(check_record(NATIVE_IDS[8], dict(description=evidence["tags"][270]["value"], software=evidence["tags"][305]["value"])))
    result["checks"].append(check_record(NATIVE_IDS[9], dict(sha256=evidence["pixel_sha256"], consumed_pixel_bytes=evidence["consumed_pixel_bytes"])))
    del raw_tiff
    reads.recheck()
    result["checks"].append(check_record(NATIVE_IDS[10], dict(consumed_file_count=len(reads.used),
                               snapshot_rechecked=True, original_corpus_opened=False,
                               original_authority="parent all-nine plan and live snapshot byte identity")))
    need(tuple(row["id"] for row in result["checks"]) == NATIVE_IDS, "complete11 native checks")


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf8")


def initial_result(request, request_ref, private):
    if private:
        return dict(schema="m193c-derivative-private-independent-v1", status="REFUSED",
                    request=request_ref, build=request.get("build"), producer_result=request.get("producer_result"),
                    producer_launch=request.get("producer_launch"), outputs={}, checks=dict(source=[], reader=[]),
                    invocation={}, error=None, finalization_errors=[])
    return dict(schema="m193c-sensor-white-native-derivative-independent-frame-v1", status="REFUSED",
                request=request_ref, original_index=request.get("original", {}).get("original_index"),
                snapshot=request.get("snapshot"), primary_receipt=request.get("primary_receipt"), tiff=request.get("tiff"),
                active_sha256_u16_le=None, tiff_pixel_sha256_u16_le=None,
                checks=[], domain_controls=[], white_controls=[], invocation={}, error=None, finalization_errors=[])


def terminal(result, output, reads, budget, successful_status):
    path = output / "result.json"
    try:
        reads.recheck()
        budget.check()
        result["invocation"]["work"] = budget.receipt()
        budget.write(path, json_bytes(result))
        # A successful return needs a real post-publication check. The retained
        # work sample precedes this check and is not described as process exit.
        reads.recheck()
        for name, extent in tuple(budget.extents.items()):
            p = Path(name)
            need(p.exists() and p.stat().st_size == extent, "published artifact extent changed")
        for ref in budget.written.values():
            need(file_ref(ref["path"]) == ref, "published artifact bytes changed")
        budget.check()
    except Exception:
        failure = traceback.format_exc()
        result["status"] = "REFUSED"
        if result["error"] is None:
            result["error"] = failure
        else:
            result["finalization_errors"].append(failure)
        try:
            if path.exists():
                retained = output / "result.first.json"
                path.rename(retained)
                # Same physical bytes retain one extent charge under new name.
                key = str(path.resolve()).casefold()
                extent = budget.extents.pop(key, path.stat().st_size if path.exists() else 0)
                budget.extents[str(retained.resolve()).casefold()] = max(extent, retained.stat().st_size)
            raw = json_bytes(result)
            need(len(raw) <= 4 << 20, "negative terminal size")
            with path.open("xb") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            budget.account(path)
        except Exception:
            secondary = traceback.format_exc()
            result["finalization_errors"].append(secondary)
            print("secondary failure preserving derivative reader refusal:\n" + secondary, file=sys.stderr, flush=True)
    return 0 if result["status"] == successful_status and result["error"] is None and result["finalization_errors"] == [] else 1


def main(argv=None):
    cli = argparse.ArgumentParser()
    cli.add_argument("--private", action="store_true")
    cli.add_argument("--request")
    cli.add_argument("--request-sha256")
    cli.add_argument("--output")
    cli.add_argument("--capture-runtime")
    args = cli.parse_args(argv)
    if args.capture_runtime:
        need(not args.private and args.request is None and args.request_sha256 is None and args.output is None,
             "runtime capture is a separate command")
        destination = path_of(args.capture_runtime, repository=True)
        need(not destination.exists() and destination.parent.is_dir(), "fresh runtime destination")
        import numpy as np
        import rawpy
        raw = json_bytes(runtime_record(np, rawpy))
        need(len(raw) <= 1 << 20, "runtime record bound")
        with destination.open("xb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        print(json.dumps(dict(status="CAPTURED_DEPENDENCY_RUNTIME_ONLY", runtime=file_ref(destination))), flush=True)
        return 0
    need(args.request and args.output and valid_sha(args.request_sha256), "hashed reader request and output required")
    request_path, output = path_of(args.request, repository=True), path_of(args.output, repository=True)
    need(not output.exists() and output.parent.is_dir(), "fresh output directory")
    output.mkdir()
    request_ref = dict(path=str(request_path), sha256=args.request_sha256, bytes=request_path.stat().st_size)
    need(0 < request_ref["bytes"] <= 1 << 20, "request byte cap")
    # Bounded request authentication precedes all numerical imports. Parent log
    # retains malformed startup failure even if no valid limits can be read.
    with request_path.open("rb") as stream:
        raw = stream.read((1 << 20) + 1)
    need(sha(raw) == args.request_sha256 and len(raw) == request_ref["bytes"], "external request SHA")
    request = strict(raw)
    budget = Budget(request["limits"], args.private)
    reads = Reads(budget)
    reads.file(request_ref, 1 << 20)
    result = initial_result(request, request_ref, args.private)
    successful_status = "PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY" if args.private else "PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY"
    result["invocation"] = dict(argv=list(sys.argv), orig_argv=list(sys.orig_argv), executable=sys.executable,
                                cwd=str(Path.cwd()), xoptions=dict(sys._xoptions), thread_environment={k: os.environ.get(k) for k in THREADS},
                                runtime=None, source_bindings=None, work=None)
    try:
        release, source_refs = release_entry(request, request_ref, reads, args.private)
        result["invocation"]["source_bindings"] = release["source_bindings"]
        snapshot = output / "sources"
        snapshot.mkdir()
        snapshot_names = {str(Path(__file__).resolve()), str(TIFF_SOURCE), str(OLD_TIFF),
                          str(HERE / "independent-derivative-reader-preregister.md")}
        if not args.private:
            snapshot_names.add(str(HERE / "sensor-domain-reader-preregister.md"))
            snapshot_names.add(str(HERE / "sensor-white-reader-preregister.md"))
        for name, ref in source_refs.items():
            if name not in snapshot_names:
                continue
            # A flat digest-prefixed basename avoids path collisions without
            # copying an unbounded directory or any runtime binary.
            budget.write(snapshot / (ref["sha256"][:16] + "-" + Path(name).name), reads.file(ref, 32 << 20))
        np, rawpy, runtime = load_runtime(request, reads, args.private)
        result["invocation"]["runtime"] = runtime
        reads.runtime_paths.update(ref_shape(ref, 128 << 20) for ref in runtime["module_files"])
        for ref in runtime["module_files"] + [runtime["python_executable"]]:
            reads.file(ref, 128 << 20)
        parser = load_checked(TIFF_SOURCE, source_refs[str(TIFF_SOURCE)], reads, "m193c_independent_native_tiff")
        if args.private:
            old_parser = load_checked(OLD_TIFF, source_refs[str(OLD_TIFF)], reads, "m193c_held_small_tiff")
            private_run(request, result, reads, budget, np, parser, old_parser, output)
        else:
            native_run(request, result, reads, budget, np, rawpy, parser)
        reads.recheck()
        budget.check()
        result["status"] = successful_status
    except Exception:
        result["error"] = traceback.format_exc()
        result["status"] = "REFUSED"
    exit_code = terminal(result, output, reads, budget, successful_status)
    print(json.dumps(dict(status=result["status"], result=str(output / "result.json"),
                          error=result["error"], finalization_errors=result["finalization_errors"],
                          work_through_final_checks=budget.receipt()), allow_nan=False), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
