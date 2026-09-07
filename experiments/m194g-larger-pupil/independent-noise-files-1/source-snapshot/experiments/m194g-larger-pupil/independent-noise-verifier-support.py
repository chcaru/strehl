"""Small shared read-only verifier budget, source release and persistence support.

Standard library only. Numerical modules are loaded from released bytes later.
"""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
import weakref

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def need(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def parse(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, "duplicate JSON key")
            out[key] = value
        return out
    def finite(value):
        if isinstance(value, float):
            need(math.isfinite(value), "nonfinite JSON number")
        elif isinstance(value, dict):
            for child in value.values():
                finite(child)
        elif isinstance(value, list):
            for child in value:
                finite(child)
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: need(False, "nonfinite JSON token"))
    finite(value)
    return value


def relative(base, name):
    need(type(name) is str and name and "\\" not in name and ":" not in name
         and not name.startswith("/") and all(p not in ("", ".", "..") for p in name.split("/")),
         "noncanonical relative path")
    base = Path(base).resolve()
    path = (base / name).resolve(strict=True)
    need(path.is_relative_to(base) and path.is_file(), "reference outside base or not file")
    return path


def binding(path):
    h, count = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1 << 20):
            h.update(chunk)
            count += len(chunk)
    return {"sha256": h.hexdigest(), "bytes": count}


def file_ref(path):
    path = Path(path).resolve(strict=True)
    return {"path": path.relative_to(ROOT).as_posix(), **binding(path)}


class Budget:
    """Live named ndarray owners, not RSS; one cumulative verification scope."""
    def __init__(self, name, cpu, wall):
        self.name, self.cpu, self.wall = name, cpu, wall
        self.owners = {}
        self.peak = self.output_bytes = 0
        self.np = None
        self.generators = 0
        self.requested = {"photo": 0, "read": 0}
        self.forbidden_calls = 0

    def live(self):
        self.owners = {k: v for k, v in self.owners.items() if v[0]() is not None}
        return sum(v[1] for v in self.owners.values())

    def check(self):
        need(time.process_time() - self.cpu <= 120, "verification CPU budget exceeded")
        need(time.perf_counter() - self.wall <= 240, "verification wall budget exceeded")
        need(self.live() <= 32 << 20, "verification named array budget exceeded")
        need(self.output_bytes <= 16 << 20, "verification output budget exceeded")

    def check_allocation(self, shape, dtype):
        self.check()
        need(self.np is not None, "numerical runtime not attached")
        size = math.prod(shape) * self.np.dtype(dtype).itemsize
        need(self.live() + size <= 32 << 20, "verification allocation would exceed budget")

    def watch(self, array, name="array"):
        self.check()
        root = array
        while isinstance(getattr(root, "base", None), self.np.ndarray):
            root = root.base
        key = id(root)
        entry = self.owners.get(key)
        if entry is None or entry[0]() is not root:
            need(self.live() + root.nbytes <= 32 << 20, "verification live owner exceeds budget")
            self.owners[key] = (weakref.ref(root), int(root.nbytes), {name})
        else:
            entry[2].add(name)
        self.peak = max(self.peak, self.live())
        return array

    def empty(self, shape, dtype, name):
        self.check_allocation(shape, dtype)
        return self.watch(self.np.empty(shape, dtype=dtype), name)

    def receipt(self):
        return dict(name=self.name, limits=dict(cpu_seconds=120, wall_seconds=240,
                    named_array_bytes=32 << 20, output_bytes=16 << 20),
                    cpu_seconds=time.process_time()-self.cpu, wall_seconds=time.perf_counter()-self.wall,
                    live_array_bytes=self.live(), peak_live_array_bytes=self.peak,
                    output_bytes=self.output_bytes, generator_constructions=self.generators,
                    requested_by_component=dict(self.requested), forbidden_calls=self.forbidden_calls,
                    memory_scope="live named ndarray backing owners; not measured RSS")


class Reads:
    def __init__(self, budget):
        self.budget, self.observed = budget, {}

    def raw(self, ref, base=ROOT, *, maximum=4 << 20, array=False):
        need(type(ref) is dict and set(ref) == ({"path", "sha256", "bytes", "dtype", "shape"}
             if array else {"path", "sha256", "bytes"}), "reference keys")
        need(type(ref["bytes"]) is int and 0 < ref["bytes"] <= maximum, "reference byte limit/type")
        need(type(ref["sha256"]) is str and len(ref["sha256"]) == 64
             and all(c in "0123456789abcdef" for c in ref["sha256"]), "reference SHA type")
        path = relative(base, ref["path"])
        self.budget.check()
        with path.open("rb") as stream:
            raw = stream.read(maximum + 1)
        actual = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        need(actual == {k: ref[k] for k in actual}, "input bytes/hash changed")
        key = path.relative_to(ROOT).as_posix()
        need(key not in self.observed or self.observed[key] == actual, "input changed between reads")
        self.observed[key] = actual
        self.budget.check()
        return raw, path

    def json(self, ref, base=ROOT, **kwargs):
        raw, path = self.raw(ref, base, **kwargs)
        return parse(raw), path

    def finish(self):
        for name, wanted in self.observed.items():
            need(binding(relative(ROOT, name)) == wanted, "input changed before completion")
            self.budget.check()
        return dict(self.observed)


class Session:
    def __init__(self, args, scope, cpu, wall, required):
        self.budget = Budget(scope, cpu, wall)
        self.reads = Reads(self.budget)
        path = Path(args.release).resolve(strict=True)
        ref = file_ref(path)
        need(ref["sha256"] == args.release_sha256, "external execution release SHA mismatch")
        release, _ = self.reads.json(ref)
        need(set(release) == {"schema", "scope", "source_bindings", "inputs", "commands"}
             and release["schema"] == "m194g-numerical-execution-release-v1" and release["scope"] == scope,
             "execution release schema/scope")
        commands = [[args.release_sha256 if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x
                     for x in cmd] for cmd in release["commands"]]
        need(list(sys.orig_argv) in commands, "actual original argv not released")
        self.release, self.release_ref = release, ref
        need(type(release["source_bindings"]) is dict and set(required) <= set(release["source_bindings"]),
             "actual executable/dependency omitted from release")
        self.sources = {}
        for name, wanted in release["source_bindings"].items():
            raw, _ = self.reads.raw({"path": name, **wanted})
            self.sources[name] = raw
        for ref in release["inputs"]:
            self.reads.raw(ref)
        self.output = Path(args.output).resolve()
        need(self.output.is_relative_to(ROOT), "output outside repository")
        self.output.mkdir(parents=True, exist_ok=False)
        self.written = {}
        self.final_checks = []
        for name, raw in self.sources.items():
            self.write("source-snapshot/" + name, raw)

    def load(self, filename, module_name):
        path = HERE / filename
        name = path.relative_to(ROOT).as_posix()
        need(name in self.sources, "unreleased executable dependency")
        spec = importlib.util.spec_from_loader(module_name, loader=None, origin=str(path))
        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(path)
        sys.modules[module_name] = module
        exec(compile(self.sources[name], str(path), "exec"), module.__dict__)
        return module

    def write(self, name, raw):
        self.budget.check()
        need(type(raw) is bytes and self.budget.output_bytes + len(raw) <= 16 << 20, "output reservation exceeded")
        path = (self.output / name).resolve()
        need(path.is_relative_to(self.output) and not path.exists(), "output collision/escape")
        path.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        try:
            with path.open("xb") as stream:
                written = stream.write(raw)
            need(written == len(raw), "short output write")
        finally:
            self.budget.output_bytes += path.stat().st_size if path.exists() else written
        ref = file_ref(path)
        self.written[ref["path"]] = {k: ref[k] for k in ("sha256", "bytes")}
        self.budget.check()
        return ref

    def json(self, name, value):
        return self.write(name, canonical(value) + b"\n")

    def finish(self):
        inputs = self.reads.finish()
        for name, wanted in self.written.items():
            need(binding(ROOT / name) == wanted, "saved verification output changed")
            self.budget.check()
        for check in self.final_checks:
            check()
            self.budget.check()
        return inputs

    def terminal(self, result, *, gate=False):
        """Post-write failure removes any admission; retained first result is refused."""
        primary = None
        try:
            result["sources_after"] = {name: binding(ROOT/name) for name in self.sources}
            result["inputs_after"] = self.finish()
            need(result["sources_before"] == result["sources_after"], "terminal source mismatch")
            need(result["inputs_before"] == result["inputs_after"], "terminal input mismatch")
            result["work"] = self.budget.receipt()
            ref = self.json("result.json", result)
            self.finish()
            if gate:
                need(result["status"] == "PASS_SOFTWARE_NOISE_FILES_ONLY", "failed result cannot issue gate")
                admission = dict(schema="m194g-software-noise-admission-v1",
                                 status="PASS_SOFTWARE_NOISE_FILES_ONLY", ref_root="repository",
                                 **{k: result[k] for k in ("manifest", "generation_result", "float_commission", "noise_commission")},
                                 independent_read=ref)
                self.json("noise-admission.json", admission)
                self.finish()
            self.budget.check()
            return ref
        except Exception as exc:
            primary = exc
            result["finalization_errors"].append(traceback.format_exc())
            result["status"] = ("UNCOMMISSIONED_NOISE_FILES" if result["schema"] == "m194g-independent-noise-files-read-v1"
                                else "UNCOMMISSIONED_AUTHORITY_CONTROLS")
            if result["error"] is None:
                result["error"] = repr(exc)
            # All rename targets are fixed children of this fresh owned output.
            for name in ("noise-admission.json", "result.json"):
                path = self.output/name
                if path.exists():
                    try:
                        path.rename(self.output/(name+".rejected"))
                    except Exception as secondary:
                        primary.add_note("Could not revoke terminal file " + name + ": " + repr(secondary))
            try:
                raw = canonical(result)+b"\n"
                need(self.budget.output_bytes+len(raw) <= 16 << 20, "failure receipt output cap")
                path = self.output/"result.json"
                with path.open("xb") as stream:
                    count = stream.write(raw)
                self.budget.output_bytes += path.stat().st_size
                need(count == len(raw), "short failure receipt")
            except Exception as secondary:
                primary.add_note("Failed to persist downgraded receipt: " + repr(secondary))
            raise primary
