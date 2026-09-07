"""Bounded quality-stage metadata; no numerical imports or optical operations."""
import ast
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
np = None  # Explicitly attached from the source-bound metrics module after entry checks.


def need(ok, message):
    if not ok:
        raise ValueError(message)


def valid_hash(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    def finite(node):
        if type(node) is float:
            need(math.isfinite(node), "nonfinite JSON number")
        elif type(node) is dict:
            for child in node.values(): finite(child)
        elif type(node) is list:
            for child in node: finite(child)
    finite(value)
    return value


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def binding_bytes(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def file_binding(path):
    h, length = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block); length += len(block)
    return {"sha256": h.hexdigest(), "bytes": length}


def relative(base, name):
    need(type(name) is str and name and ":" not in name and "\\" not in name
         and all(p not in ("", ".", "..") for p in name.split("/")), "canonical contained path")
    base = Path(base).resolve()
    path = (base / name).resolve()
    need(path.is_relative_to(base), "reference outside root")
    return path


def file_ref(path, base=ROOT):
    path = Path(path).resolve()
    return {"path": path.relative_to(Path(base).resolve()).as_posix(), **file_binding(path)}


class Reads:
    def __init__(self, budget=None):
        self.budget, self.observed = budget, {}

    def raw(self, path, sha, length=None, cap=4 * 1024**2):
        if self.budget: self.budget.check()
        need(valid_hash(sha) and (length is None or type(length) is int and 0 < length <= cap),
             "typed input hash/extent")
        path = Path(path).resolve(strict=True)
        with path.open("rb") as stream: raw = stream.read(cap + 1)
        actual = binding_bytes(raw)
        need(len(raw) <= cap and actual["sha256"] == sha
             and (length is None or len(raw) == length), "input hash/extent mismatch")
        key = str(path)
        need(key not in self.observed or self.observed[key] == actual, "input changed between reads")
        self.observed[key] = actual
        if self.budget: self.budget.check()
        return raw

    def ref(self, ref, base=ROOT, *, array=False):
        need(type(ref) is dict and set(ref) == {"path", "sha256", "bytes"} | ({"dtype", "shape"} if array else set()),
             "closed input FileRef/ArrayRef")
        need(type(ref["bytes"]) is int and ref["bytes"] > 0 and valid_hash(ref["sha256"]), "typed input reference")
        return relative(base, ref["path"])

    def json(self, ref, base=ROOT):
        path = self.ref(ref, base)
        return strict_json(self.raw(path, ref["sha256"], ref["bytes"])), path

    def array(self, ref, base, shape, dtype, *, nonnegative=False):
        path = self.ref(ref, base, array=True)
        need(type(ref["shape"]) is list and all(type(n) is int for n in ref["shape"])
             and ref["shape"] == list(shape) and ref["dtype"] == dtype, "array reference layout")
        count = math.prod(shape)
        raw = self.raw(path, ref["sha256"], ref["bytes"], count * np.dtype(dtype).itemsize + 65548)
        need(raw[:6] == b"\x93NUMPY", "NPY magic")
        if raw[6:8] == b"\x01\x00":
            need(len(raw) >= 10, "short NPY header")
            length, prefix = struct.unpack("<H", raw[8:10])[0], 10
        elif raw[6:8] == b"\x02\x00":
            need(len(raw) >= 12, "short NPY header")
            length, prefix = struct.unpack("<I", raw[8:12])[0], 12
        else:
            raise ValueError("unsupported NPY version")
        need(length <= 65536 and prefix + length <= len(raw), "bounded NPY header")
        tree = ast.parse(raw[prefix:prefix + length].decode("latin1").strip(), mode="eval")
        need(isinstance(tree.body, ast.Dict), "NPY dictionary header")
        keys = [ast.literal_eval(key) for key in tree.body.keys]
        need(all(type(key) is str for key in keys) and len(set(keys)) == len(keys), "duplicate NPY header key")
        header = ast.literal_eval(tree)
        need(set(header) == {"descr", "fortran_order", "shape"}
             and header["descr"] == dtype and header["fortran_order"] is False
             and type(header["shape"]) is tuple and all(type(n) is int for n in header["shape"])
             and header["shape"] == tuple(shape), "NPY header layout")
        need(len(raw) == prefix + length + count * np.dtype(dtype).itemsize, "exact NPY payload extent")
        self.budget.check_allocation(tuple(shape), dtype)
        array = np.frombuffer(raw, dtype=dtype, count=count, offset=prefix + length).reshape(shape)
        return checked_array(array, self.budget, shape=tuple(shape), name="reopened quality array", nonnegative=nonnegative)

    def finish(self):
        for path, expected in self.observed.items():
            need(file_binding(path) == expected, "input changed before finalization")
            if self.budget: self.budget.check()
        return dict(self.observed)


def checked_array(array, budget, *, shape, name, nonnegative=False):
    need(isinstance(array, np.ndarray) and array.shape == tuple(shape) and array.dtype.str == "<f8", "finite float layout")
    budget.watch(array, name)
    scratch = budget.empty(tuple(shape), "|b1", "array admission mask")
    np.isfinite(array, out=scratch)
    need(bool(scratch.all()), "nonfinite float payload")
    if nonnegative:
        np.greater_equal(array, 0., out=scratch)
        need(bool(scratch.all()), "negative expected scalar")
    return array


def verify_release(path, external_sha, scope, required_sources, required_inputs):
    reads = Reads()
    raw = reads.raw(path, external_sha)
    release = strict_json(raw)
    need(type(release) is dict and set(release) == {"schema", "scope", "source_bindings", "inputs", "commands"}
         and release["schema"] == "m194g-quality-execution-release-v1" and release["scope"] == scope,
         "quality execution release schema/scope")
    need(type(release["source_bindings"]) is dict and set(release["source_bindings"]) == set(required_sources),
         "exact quality source closure")
    for name, ref in release["source_bindings"].items():
        need(type(ref) is dict and set(ref) == {"sha256", "bytes"}, "source binding keys")
        reads.raw(relative(ROOT, name), ref["sha256"], ref["bytes"])
    need(type(release["inputs"]) is list and release["inputs"], "nonempty release inputs")
    paths = []
    for ref in release["inputs"]:
        path = reads.ref(ref)
        reads.raw(path, ref["sha256"], ref["bytes"])
        paths.append(str(path))
    need(len(paths) == len(set(paths)) and set(map(str, required_inputs)) <= set(paths), "required nonaliased release inputs")
    commands = release["commands"]
    need(type(commands) is list and commands and all(type(row) is list and row and all(type(v) is str for v in row) for row in commands),
         "actual command list")
    expanded = [[external_sha if value == "ACTUAL_EXECUTION_RELEASE_SHA256" else value for value in row] for row in commands]
    need(list(sys.orig_argv) in expanded, "actual interpreter command not released")
    return release, reads


def load_bound(path, name, sources):
    path = Path(path).resolve()
    key = path.relative_to(ROOT).as_posix()
    need(key in sources and file_binding(path) == sources[key], "import source binding")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    need(Path(module.__file__).resolve() == path and file_binding(path) == sources[key], "actual imported source changed")
    return module


class Store:
    def __init__(self, path, budget):
        self.root = Path(path).resolve()
        need(self.root.is_relative_to(ROOT), "output outside repository")
        self.root.mkdir(parents=True, exist_ok=False)
        self.budget, self.files = budget, {}

    def raw(self, name, raw, *, replace=False):
        path = relative(self.root, name)
        self.budget.output_bytes += len(raw)
        self.budget.check()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb" if replace else "xb") as stream:
            written = stream.write(raw)
            need(written == len(raw), "incomplete artifact write")
            stream.flush(); os.fsync(stream.fileno())
        ref = {"path": name, **binding_bytes(raw)}
        self.files[name] = ref
        self.budget.check()
        return ref

    def json(self, name, value, *, replace=False):
        raw = canonical_bytes(value)
        need(len(raw) <= 4 * 1024**2, "bounded quality JSON")
        return self.raw(name, raw, replace=replace)

    def array(self, name, array):
        self.budget.watch(array, name)
        buffer = io.BytesIO()
        np.save(buffer, array, allow_pickle=False)
        return {**self.raw(name, buffer.getvalue()), "dtype": array.dtype.str, "shape": list(array.shape)}

    def snapshots(self, sources):
        for name, expected in sources.items():
            raw = (ROOT / name).read_bytes()
            need(binding_bytes(raw) == expected, "source changed before snapshot")
            self.raw("sources/" + name, raw)

    def check(self):
        for name, expected in self.files.items():
            need(file_binding(relative(self.root, name)) == {k: expected[k] for k in ("sha256", "bytes")}, "persisted artifact changed")
            self.budget.check()


def runtime():
    import scipy
    return {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__,
            "thread_environment": {key: os.environ.get(key) for key in THREAD_KEYS},
            "executable": sys.executable, "cwd": str(Path.cwd().resolve())}


def invocation():
    return {"orig_argv": list(sys.orig_argv), "argv": list(sys.argv), "xoptions": dict(sys._xoptions)}


def finish_terminal(store, name, result, success_status, check_inputs):
    """Final checks revoke success; failed persistence cannot replace the primary error."""
    def fail(exc):
        result["status"] = "UNCOMMISSIONED_QUALITY_TARGET" if result["schema"] == "m194g-quality-target-v1" else "UNCOMMISSIONED_QUALITY_STAGE"
        result["finalization_errors"].append(repr(exc))
    try:
        check_inputs(); store.check(); store.budget.check()
        result["work"] = store.budget.receipt()
        store.json(name, result, replace=name in store.files)
        check_inputs(); store.check(); store.budget.check()
        result["work"] = store.budget.receipt()
        store.json(name, result, replace=True)
        check_inputs(); store.check(); store.budget.check()
    except Exception as exc:
        fail(exc)
        try:
            # If a cap itself refused, preserve rejection without asserting that
            # the failed package meets its budget. This tiny terminal write is
            # still counted; it cannot turn the status back into success.
            raw = canonical_bytes(result)
            store.budget.output_bytes += len(raw)
            with (store.root / name).open("wb") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        except Exception as second:
            result["finalization_errors"].append("terminal failure persistence: " + repr(second))
            print(result["finalization_errors"][-1], file=sys.stderr, flush=True)
    return result["status"] == success_status
