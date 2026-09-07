"""Bounded software-noise core; this module confers no input/output authority.

Load this module before NumPy, with caller entry clocks already captured. No
sampling is possible without a RuntimeGuard matching a separately frozen runtime
record. The future runner owns execution-release and genuine float-authority
checks, the complete call matrix, failure retention and post-terminal-write check.
Independent moment/encoding readers deliberately do not live in this module.
"""
from __future__ import annotations

import time

ENTRY_CPU = time.process_time()
ENTRY_WALL = time.perf_counter()

import os
import sys

THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS")
if "numpy" in sys.modules:
    raise RuntimeError("software-noise must be loaded before the first NumPy import")
for _key in THREAD_KEYS:
    os.environ[_key] = "2"

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import stat
import threading
import weakref

import numpy as np
from numpy.random import Generator, PCG64DXSM, SeedSequence
from numpy.lib import format as npy_format  # Bind the actual writer before snapshot.

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CONTRACT = HERE / "next-noise-contract.md"
CONTRACT_SHA256 = "4e92e176d0cfae6dcdc9fedab3ff8f5d40f858c47eb0fcddbd14877d894d29f2"
SCENES = frozenset(("textured", "flat", "control-s0", "control-s64",
                    "control-s4096", "control-s12000", "control-live-a",
                    "control-live-b"))
SEEDS = (701, 709, 719, 727, 733, 739, 743, 751)
FACTORS = (0.75, 1.0, 1.0, 0.6)
PARITIES = ((0, 0), (0, 1), (1, 0), (1, 1))
FAULTS = frozenset(("c-after-poisson", "gain-double", "omit-read",
                   "reuse-repeat-zero", "clone-green", "read-lag2-mix",
                   "clamp-black", "shared-read-frame", "omit-component-key",
                   "swap-rb", "swap-green", "half-up-rounding"))
PHOTO_OVERRIDES = frozenset(("c-after-poisson", "clone-green"))
READ_OVERRIDES = frozenset(("omit-read", "read-lag2-mix"))
ARRAY_NAMES = ("photo_draw", "read_used", "x_used", "q",
               "photo_used_override", "read_draw_override")
MIB = 1_048_576


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, label, minimum=0, maximum=None):
    require(type(value) is int and value >= minimum
            and (maximum is None or value <= maximum), label + " must be a real bounded integer")
    return value


def finite(value, label):
    require(type(value) in (int, float) and math.isfinite(value), label + " must be finite")
    return float(value)


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def valid_hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate JSON key: " + key)
            out[key] = value
        return out

    def walk(value):
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, float):
            require(math.isfinite(value), "nonfinite JSON number")
    result = json.loads(raw, object_pairs_hook=pairs,
                        parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON " + x)))
    walk(result)
    return result


def canonical_bytes(value):
    # Normalize one declared JSON representation, without coercing integer types.
    raw = (json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    strict_json(raw)
    return raw


def file_binding(path):
    path = Path(path).resolve(strict=True)
    require(path.is_file(), "binding is not a regular file")
    hasher = hashlib.sha256()
    length = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(MIB), b""):
            length += len(chunk)
            hasher.update(chunk)
    return {"path": str(path), "sha256": hasher.hexdigest(), "bytes": length}


def source_bindings():
    result = {}
    for path in (Path(__file__), CONTRACT):
        binding = file_binding(path)
        if path == CONTRACT:
            require(binding["sha256"] == CONTRACT_SHA256, "frozen noise contract changed")
        result[path.resolve().relative_to(ROOT).as_posix()] = {
            "sha256": binding["sha256"], "bytes": binding["bytes"]}
    return result


def runtime_manifest():
    """Describe current actual modules; caller must externally pin this before draws."""
    require(platform.python_version() == "3.12.10", "unregistered Python version")
    require(np.__version__ == "2.4.4", "unregistered NumPy version")
    require(platform.system() == "Windows" and platform.machine() == "AMD64"
            and sys.byteorder == "little", "unregistered machine/byte order")
    require(all(os.environ.get(key) == "2" for key in THREAD_KEYS), "numerical thread environment changed")
    modules = {}
    for name, module in sorted(sys.modules.items()):
        selected = (name == "numpy" or name == "numpy.random"
                    or name.startswith("numpy.random.") or name == "numpy._core"
                    or name.startswith("numpy._core.") or name == "numpy.lib.format")
        if selected and getattr(module, "__file__", None):
            modules[name] = file_binding(module.__file__)
    for name in ("numpy", "numpy.random", "numpy.random._generator",
                 "numpy.random._pcg64", "numpy.random.bit_generator",
                 "numpy._core._multiarray_umath", "numpy.lib.format"):
        require(name in modules, "missing loaded runtime module " + name)
    return {"schema": "strehl-software-noise-runtime-v1",
            "python": platform.python_version(), "implementation": platform.python_implementation(),
            "numpy": np.__version__, "system": platform.system(), "machine": platform.machine(),
            "processor": platform.processor(), "byteorder": sys.byteorder,
            "thread_environment": {key: os.environ[key] for key in THREAD_KEYS},
            "interpreter": file_binding(sys.executable), "modules": modules}


class BudgetError(ValueError):
    pass


class Budget:
    """One stage-wide budget; no frame/reset method exists."""
    def __init__(self, stage, *, start_cpu, start_wall,
                 cpu_clock=time.process_time, wall_clock=time.perf_counter):
        require(stage in ("commission", "intended"), "unknown budget stage")
        self.stage = stage
        self.start_cpu = finite(start_cpu, "entry CPU")
        self.start_wall = finite(start_wall, "entry wall")
        self.cpu_clock, self.wall_clock = cpu_clock, wall_clock
        self.limits = {"cpu_seconds": 120.0, "wall_seconds": 240.0,
                       "requested_variates": 32_000_000 if stage == "commission" else 12_288_000,
                       "live_array_bytes": 32 * MIB,
                       "output_bytes": (512 if stage == "commission" else 32) * MIB}
        self.requested = {"photo": 0, "read": 0}
        self.generators = self.started_frames = self.completed_frames = 0
        self.output_bytes = self.peak_array_bytes = 0
        self._arrays = {}
        self._thread = threading.get_ident()
        self._output_root = None
        self.check()

    def _live_bytes(self):
        self._arrays = {key: entry for key, entry in self._arrays.items() if entry[0]() is not None}
        return sum(entry[1] for entry in self._arrays.values())

    def check(self):
        require(threading.get_ident() == self._thread, "noise stage must use one Python worker")
        cpu = finite(self.cpu_clock(), "CPU clock") - self.start_cpu
        wall = finite(self.wall_clock(), "wall clock") - self.start_wall
        require(cpu >= 0 and wall >= 0, "clock precedes stage entry")
        live = self._live_bytes()
        self.peak_array_bytes = max(self.peak_array_bytes, live)
        values = {"cpu_seconds": cpu, "wall_seconds": wall,
                  "requested_variates": sum(self.requested.values()),
                  "live_array_bytes": live, "output_bytes": self.output_bytes}
        for key, actual in values.items():
            if actual > self.limits[key]:
                raise BudgetError(f"noise {key} ceiling: {actual} > {self.limits[key]}")
        return values

    def watch(self, array, name):
        require(isinstance(array, np.ndarray), "tracked allocation must be ndarray")
        root = array
        while isinstance(root.base, np.ndarray):
            root = root.base
        self._live_bytes()  # Drop expired owners before lookup of a possibly reused id.
        key = id(root)
        entry = self._arrays.get(key)
        if entry is None or entry[0]() is not root:
            self._arrays[key] = (weakref.ref(root), int(root.nbytes), {name})
        else:
            self._arrays[key][2].add(name)
        self.check()
        return array

    def check_allocation(self, shape, dtype):
        require(type(shape) in (tuple, list) and len(shape) > 0, "allocation shape must be explicit")
        for dimension in shape:
            integer(dimension, "allocation extent", 0)
        count = math.prod(shape)
        prospective = self._live_bytes() + count * np.dtype(dtype).itemsize
        if prospective > self.limits["live_array_bytes"]:
            raise BudgetError("noise live_array_bytes allocation would exceed ceiling")
        self.check()

    def empty(self, shape, dtype, name):
        self.check_allocation(shape, dtype)
        return self.watch(np.empty(shape, dtype=dtype), name)

    def reserve_draw(self, component, count):
        require(component in self.requested, "unknown sampling component")
        integer(count, "requested samples", 0)
        if sum(self.requested.values()) + count > self.limits["requested_variates"]:
            raise BudgetError("noise requested_variates would exceed ceiling")
        self.requested[component] += count
        self.check()

    def before_write(self, count):
        integer(count, "write size")
        if self.output_bytes + count > self.limits["output_bytes"]:
            raise BudgetError("noise output_bytes write would exceed ceiling")
        self.check()

    def receipt(self):
        values = self.check()
        return {"stage": self.stage, "limits": dict(self.limits), **values,
                "requested_by_component": dict(self.requested),
                "generator_constructions": self.generators,
                "started_frames": self.started_frames, "completed_frames": self.completed_frames,
                "peak_live_array_bytes": self.peak_array_bytes,
                "tracked_scope": "unique backing ndarrays; includes caller scalar, named scratch and casts; not RSS"}


class RuntimeGuard:
    def __init__(self, expected_runtime, budget):
        self.budget = budget
        budget.check()
        current = runtime_manifest()
        require(canonical_bytes(current) == canonical_bytes(expected_runtime), "externally frozen runtime mismatch")
        self.before = current
        self.sources_before = source_bindings()
        self._identities = (Generator, PCG64DXSM, SeedSequence, npy_format.write_array)
        self._module_paths = {name: binding["path"] for name, binding in current["modules"].items()}
        budget.check()

    def check_live(self):
        self.budget.check()
        require((Generator, PCG64DXSM, SeedSequence) == self._identities[:3],
                "actual generator constructor binding changed")
        require((np.random.Generator, np.random.PCG64DXSM, np.random.SeedSequence,
                 npy_format.write_array) == self._identities, "runtime callable identity changed")
        require(all(os.environ.get(key) == "2" for key in THREAD_KEYS), "thread environment changed")
        for name, path in self._module_paths.items():
            require(name in sys.modules and str(Path(sys.modules[name].__file__).resolve()) == path,
                    "actual loaded runtime module changed")

    def finish(self):
        self.check_live()
        after = runtime_manifest()
        sources_after = source_bindings()
        require(canonical_bytes(after) == canonical_bytes(self.before), "runtime bytes changed")
        require(sources_after == self.sources_before, "noise source bytes changed")
        self.budget.check()
        return {"sources_before": self.sources_before, "sources_after": sources_after,
                "runtime": after,
                "invocation": {"orig_argv": list(sys.orig_argv), "xoptions": dict(sys._xoptions),
                               "executable": sys.executable, "cwd": str(Path.cwd())},
                "work": self.budget.receipt()}


@dataclass(frozen=True)
class FrameSpec:
    scene: str
    seed: int | None
    frame_index: int
    width: int
    height: int
    scalar_level: float | int | None = None

    def validate(self):
        require(type(self.scene) is str and self.scene in SCENES, "unknown scene identity")
        integer(self.frame_index, "original frame index", 0, 4)
        integer(self.width, "width", 2, 320)
        integer(self.height, "height", 2, 240)
        require(self.width % 2 == 0 and self.height % 2 == 0, "complete native RGGB quads required")
        if self.seed is not None:
            integer(self.seed, "seed", 0, 2**32 - 1)
        if self.scalar_level is not None:
            require(finite(self.scalar_level, "scalar level") >= 0, "negative scalar level")
        return self


def key_bytes(spec, component):
    spec.validate()
    require(spec.seed is not None, "noise-off has no RNG key")
    require(component in ("photo", "read"), "unknown RNG component")
    return ("strehl-software-noise-v1\n" + f"scene={spec.scene}\nseed={spec.seed}\n"
            + f"frame={spec.frame_index}\ncomponent={component}\n"
            + f"width={spec.width}\nheight={spec.height}\n").encode("ascii")


def validate_key(actual, spec, component):
    require(type(actual) is bytes and actual == key_bytes(spec, component), "RNG key bytes mismatch")
    return [int.from_bytes(hashlib.sha256(actual).digest()[i:i + 4], "little") for i in range(0, 32, 4)]


def array_hash(array):
    require(isinstance(array, np.ndarray) and array.flags.c_contiguous,
            "hash requires contiguous actual array")
    require(array.dtype.str in ("<f8", "<i8", "<u2", "|b1"), "unsupported hash dtype")
    return hashlib.sha256(memoryview(array).cast("B")).hexdigest()


def checked_array(array, budget, *, dtype="<f8", shape=None, name="array", nonnegative=False):
    require(isinstance(array, np.ndarray) and array.dtype.str == dtype and array.flags.c_contiguous,
            name + " has wrong dtype/storage")
    if shape is not None:
        require(array.shape == tuple(shape), name + " has wrong shape")
    budget.watch(array, name)
    mask = budget.empty(array.shape, np.bool_, name + " finite scratch")
    np.isfinite(array, out=mask)
    require(bool(mask.all()), name + " contains nonfinite values")
    if nonnegative:
        np.greater_equal(array, 0, out=mask)
        require(bool(mask.all()), name + " contains negative values")
    return array


@dataclass
class Observer:
    mode: str
    sample_calls: int = 0
    encode_calls: int = 0
    hook_calls: int = 0
    collected_events: int = 0

    def __post_init__(self):
        require(self.mode in ("off", "count", "placebo"), "unknown observer mode")

    def _optional_hook(self, event):
        require(event in ("photo", "read", "encode"), "unknown observer event")
        self.hook_calls += 1
        if self.mode == "count":
            self.collected_events += 1

    def operation(self, event):
        if event in ("photo", "read"):
            self.sample_calls += 1
        elif event == "encode":
            self.encode_calls += 1
        else:
            raise ValueError("unknown actual operation")
        if self.mode != "off":
            self._optional_hook(event)

    def receipt(self):
        return {"sample_calls": self.sample_calls, "encode_calls": self.encode_calls,
                "hook_calls": self.hook_calls, "collected_events": self.collected_events}


def rail_counts(x, rounded, budget):
    mask = budget.empty(x.shape, np.bool_, "rail mask")
    out = {}
    for name, array, value, op in (("x_below_zero", x, 0, np.less),
                                  ("x_above_white", x, 15360, np.greater),
                                  ("rounded_below_zero", rounded, 0, np.less),
                                  ("rounded_above_white", rounded, 15360, np.greater)):
        op(array, value, out=mask)
        out[name] = int(np.count_nonzero(mask))
    return out


def encode_dn(x, budget, observer, *, half_up=False):
    """Actual common encoding seam; private rail controls are not admission."""
    require(type(half_up) is bool, "half_up must be bool")
    checked_array(x, budget, name="encoder input")
    require(x.size > 0, "empty encoding population")
    rounded = budget.empty(x.shape, "<f8", "rounded DN")
    if half_up:
        np.add(x, 0.5, out=rounded)
        np.floor(rounded, out=rounded)
    else:
        np.rint(x, out=rounded)
    counts = rail_counts(x, rounded, budget)
    np.clip(rounded, 0.0, 15360.0, out=rounded)
    q = budget.empty(x.shape, "<u2", "encoded CFA")
    np.copyto(q, rounded, casting="unsafe")
    observer.operation("encode")
    budget.check()
    return q, counts


def _new_generator(spec, component, budget, *, omitted_component=False):
    raw = key_bytes(spec, component)
    if omitted_component:
        raw = raw.replace(f"component={component}\n".encode("ascii"), b"")
    words = validate_key(raw, spec, component)  # Refuse malformed key before construction.
    generator = Generator(PCG64DXSM(SeedSequence(words, pool_size=4)))
    budget.generators += 1
    budget.check()
    return generator, {"key": raw.decode("ascii"), "key_sha256": digest_bytes(raw),
                       "entropy_words": words, "initial_state": generator.bit_generator.state}


def _active_fault(spec, fault_id, phase, stage):
    require(phase in ("baseline", "fault", "restored", "replay"), "unknown call phase")
    require(fault_id is None or fault_id in FAULTS, "unknown fixed fault")
    require(phase not in ("fault", "restored") or fault_id is not None, "fault/restored phase lacks fault identity")
    require(phase not in ("baseline", "replay") or fault_id is None, "clean phase has fault identity")
    if fault_id is not None:
        require(stage == "commission", "faults are private commission only")
    active = fault_id if phase == "fault" else None
    levels = {"c-after-poisson": 12000, "gain-double": 4096, "omit-read": 0,
              "reuse-repeat-zero": 0, "clone-green": 4096, "read-lag2-mix": 0,
              "clamp-black": 0, "shared-read-frame": 0, "omit-component-key": 12000}
    if active in levels:
        require(spec.seed is not None and spec.scalar_level == levels[active], "fault stimulus level mismatch")
    if active == "reuse-repeat-zero":
        require(spec.scene == "control-s0" and spec.frame_index == 0
                and 100000 <= spec.seed <= 100063, "repeat-key fault outside fixed population")
    if active == "shared-read-frame":
        require(spec.scene == "control-s0" and spec.seed == 701, "shared-frame fault outside fixed population")
    if active in ("swap-rb", "swap-green"):
        require(spec.seed is None and (spec.width, spec.height) == (6, 4), "tag fault outside deterministic fixture")
    require(active != "half-up-rounding", "half-up control uses encode_dn directly")
    return active


@dataclass
class SampledFrame:
    budget: Budget
    spec: FrameSpec
    phase: str
    fault_id: str | None
    active_fault: str | None
    observer: Observer
    scalar_hash: str
    streams: dict | None
    photo_draw: np.ndarray | None
    read_draw: np.ndarray | None
    photo_used: np.ndarray
    read_used: np.ndarray | None
    electron_sum: np.ndarray
    pre_encoder_x: np.ndarray
    x_used: np.ndarray
    q: np.ndarray
    rails: dict
    derived_hashes: dict
    payload_hashes: dict

    def validate_live(self):
        self.budget.check()
        for name, expected in self.payload_hashes.items():
            array = getattr(self, name)
            require((None if array is None else array_hash(array)) == expected,
                    "actual sample payload changed before persistence: " + name)
        for name, array in (("photo_used", self.photo_used), ("read_draw", self.read_draw),
                            ("electron_sum", self.electron_sum), ("pre_encoder_x", self.pre_encoder_x)):
            require((None if array is None else array_hash(array)) == self.derived_hashes[name],
                    "actual consumed value changed before persistence: " + name)
        self.budget.check()

    def input_record(self):
        return {"scene": self.spec.scene, "seed": self.spec.seed,
                "frame_index": self.spec.frame_index, "width": self.spec.width,
                "height": self.spec.height, "scalar_level": self.spec.scalar_level,
                "expected_scalar_sha256": self.scalar_hash}

    def audit_record(self):
        self.validate_live()
        return {"input": self.input_record(), "phase": self.phase, "fault_id": self.fault_id,
                "observer_mode": self.observer.mode, "streams": self.streams,
                "derived_hashes": self.derived_hashes, "rail_counts": self.rails,
                "witness": self.observer.receipt(), "q_sha256": self.payload_hashes["q"]}


def sample_frame(scalar, spec, context, *, fault_id=None, phase="baseline", observer_mode="off"):
    require(isinstance(context, RuntimeGuard), "a bound runtime context is required")
    require(type(spec) is FrameSpec, "typed FrameSpec required")
    context.check_live()
    budget = context.budget
    spec.validate()
    shape = (spec.height, spec.width)
    active = _active_fault(spec, fault_id, phase, budget.stage)
    scalar = checked_array(scalar, budget, shape=shape, name="expected scalar", nonnegative=True)
    if spec.scalar_level is not None:
        mask = budget.empty(shape, np.bool_, "scalar-level check")
        np.equal(scalar, spec.scalar_level, out=mask)
        require(bool(mask.all()), "scalar does not match declared constant level")
        del mask
    budget.started_frames += 1
    observer = Observer(observer_mode)
    mu = budget.empty(shape, "<f8", "photosite mean")
    for (y, x), factor in zip(PARITIES, FACTORS):
        np.multiply(scalar[y::2, x::2], factor, out=mu[y::2, x::2])
    checked_array(mu, budget, shape=shape, name="photosite mean", nonnegative=True)
    if active in ("swap-rb", "swap-green"):
        first, second = ((0, 0), (1, 1)) if active == "swap-rb" else ((0, 1), (1, 0))
        a, b = mu[first[0]::2, first[1]::2], mu[second[0]::2, second[1]::2]
        temporary = budget.empty(a.shape, "<f8", "tag swap")
        np.copyto(temporary, a)
        np.copyto(a, b)
        np.copyto(b, temporary)
        del temporary
    photo = z = read_used = None
    streams = None
    if spec.seed is not None:
        stream_spec = spec
        if active == "reuse-repeat-zero":
            stream_spec = FrameSpec(spec.scene, 100000, spec.frame_index, spec.width,
                                    spec.height, spec.scalar_level)
        photo_rng, photo_record = _new_generator(stream_spec, "photo", budget,
                                                 omitted_component=active == "omit-component-key")
        read_spec = stream_spec
        if active == "shared-read-frame":
            read_spec = FrameSpec(spec.scene, spec.seed, 0, spec.width, spec.height, spec.scalar_level)
        read_rng, read_record = _new_generator(read_spec, "read", budget)
        lam = scalar if active == "c-after-poisson" else mu
        count = spec.width * spec.height
        budget.check_allocation(shape, "<i8")
        budget.reserve_draw("photo", count)
        photo = budget.watch(photo_rng.poisson(lam=lam.reshape(-1), size=None), "Poisson draw").reshape(shape)
        observer.operation("photo")
        checked_array(photo, budget, dtype="<i8", name="Poisson draw", nonnegative=True)
        photo_record.update(final_state=photo_rng.bit_generator.state,
                            call={"method": "poisson", "size": None, "dtype": "<i8",
                                  "lambda_sha256": array_hash(lam)}, draw_sha256=array_hash(photo))
        budget.check_allocation(shape, "<f8")
        budget.reserve_draw("read", count)
        z = budget.watch(read_rng.standard_normal(size=count, dtype=np.float64), "normal draw").reshape(shape)
        observer.operation("read")
        read_record.update(final_state=read_rng.bit_generator.state,
                           call={"method": "standard_normal", "size": count, "dtype": "<f8",
                                 "lambda_sha256": None}, draw_sha256=array_hash(z))
        checked_array(z, budget, name="normal draw")
        streams = {"photo": photo_record, "read": read_record}
        photo_used = budget.empty(shape, "<f8", "consumed photo")
        np.copyto(photo_used, photo, casting="unsafe")
        if active == "c-after-poisson":
            for (y, x), factor in zip(PARITIES, FACTORS):
                np.multiply(photo_used[y::2, x::2], factor, out=photo_used[y::2, x::2])
        elif active == "clone-green":
            np.copyto(photo_used[1::2, 0::2], photo_used[0::2, 1::2])
        read_used = budget.empty(shape, "<f8", "consumed read")
        if active == "read-lag2-mix":
            np.add(z[:, :-2], z[:, 2:], out=read_used[:, :-2])
            np.add(z[:, -2:], z[:, :2], out=read_used[:, -2:])
            np.multiply(read_used, 4.0, out=read_used)
            np.divide(read_used, math.sqrt(2.0), out=read_used)
        else:
            np.multiply(z, 4.0, out=read_used)
            if active == "omit-read":
                read_used.fill(0.0)
        electrons = budget.empty(shape, "<f8", "consumed electron sum")
        np.add(photo_used, read_used, out=electrons)
    else:
        require(active is None or active in ("swap-rb", "swap-green"), "sampled fault requires noise")
        photo_used = electrons = mu
    checked_array(electrons, budget, name="consumed electron sum")
    pre_x = budget.empty(shape, "<f8", "pre-encoder DN")
    np.multiply(electrons, 0.5 if active == "gain-double" else 0.25, out=pre_x)
    np.add(pre_x, 512.0, out=pre_x)
    checked_array(pre_x, budget, name="pre-encoder DN")
    x = pre_x
    if active == "clamp-black":
        x = budget.empty(shape, "<f8", "faulted encoder input")
        np.maximum(pre_x, 512.0, out=x)
    q, used_rails = encode_dn(x, budget, observer)
    if x is pre_x:
        pre_rails = dict(used_rails)
    else:
        rounded = budget.empty(shape, "<f8", "pre-fault rail scratch")
        np.rint(pre_x, out=rounded)
        pre_rails = rail_counts(pre_x, rounded, budget)
        del rounded
    derived = {"photo_used": array_hash(photo_used),
               "read_draw": None if z is None else array_hash(z),
               "electron_sum": array_hash(electrons), "pre_encoder_x": array_hash(pre_x)}
    payload_hashes = {"photo_draw": None if photo is None else array_hash(photo),
                      "read_used": None if read_used is None else array_hash(read_used),
                      "x_used": array_hash(x), "q": array_hash(q)}
    result = SampledFrame(budget, spec, phase, fault_id, active, observer, array_hash(scalar), streams,
                          photo, z, photo_used, read_used, electrons, pre_x, x, q,
                          {"pre_encoder_x": pre_rails, "x_used": used_rails}, derived, payload_hashes)
    budget.completed_frames += 1
    context.check_live()
    return result


class _CountedWriter:
    def __init__(self, stream, budget):
        self.stream, self.budget = stream, budget
        self.bytes = 0
        self.hash = hashlib.sha256()

    def write(self, data):
        view = memoryview(data).cast("B")
        self.budget.before_write(len(view))
        written = self.stream.write(view)
        if written:
            self.bytes += written
            self.budget.output_bytes += written
            self.hash.update(view[:written])
        require(written == len(view), "short output write")
        self.budget.check()
        return written

    def flush(self):
        self.stream.flush()


class OutputStore:
    """Fresh bounded output directory; no overwrite, success certificate or input reader."""
    def __init__(self, root, budget):
        self.root = Path(root).resolve()
        self.budget = budget
        require(budget._output_root is None, "one output package per shared stage budget")
        self.root.mkdir(parents=True, exist_ok=False)
        budget._output_root = self.root
        self._written = set()
        budget.check()

    def _path(self, relative):
        require(type(relative) is str and relative and "\\" not in relative,
                "output reference must be a relative slash path")
        require(all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", part)
                    for part in relative.split("/")), "invalid output path component")
        rel = Path(relative)
        require(not rel.is_absolute() and all(part not in ("..", ".") for part in relative.split("/")),
                "output path escapes package")
        target = (self.root / rel).resolve()
        require(target.is_relative_to(self.root) and target != self.root, "output outside package")
        require(target not in self._written and not target.exists(), "output path already used")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def _write(self, relative, callback):
        target = self._path(relative)
        self._written.add(target)
        raw = target.open("xb")
        writer = _CountedWriter(raw, self.budget)
        primary = None
        cleanup_errors = []
        try:
            callback(writer)
        except BaseException as exc:
            primary = exc
            raise
        finally:
            try:
                raw.flush()
                os.fsync(raw.fileno())
            except BaseException as exc:
                cleanup_errors.append(f"flush/fsync: {type(exc).__name__}: {exc}")
            try:
                raw.close()
            except BaseException as exc:
                cleanup_errors.append(f"close: {type(exc).__name__}: {exc}")
            if cleanup_errors:
                if primary is not None:
                    for error in cleanup_errors:
                        primary.add_note("secondary output cleanup failure: " + error)
                    primary.noise_cleanup_errors = cleanup_errors
                else:
                    raise OSError("output cleanup failed: " + "; ".join(cleanup_errors))
        checked = file_binding(target)
        require(checked["sha256"] == writer.hash.hexdigest() and checked["bytes"] == writer.bytes,
                "persisted bytes differ from actual write")
        self.budget.check()
        return {"path": relative, "sha256": checked["sha256"], "bytes": checked["bytes"]}

    def array(self, relative, array):
        self.budget.watch(array, "persisted actual array")
        require(array.flags.c_contiguous and array.dtype.str in ("<i8", "<f8", "<u2"), "invalid trace array")
        ref = self._write(relative, lambda stream: npy_format.write_array(stream, array, version=(1, 0), allow_pickle=False))
        return {**ref, "dtype": array.dtype.str, "shape": list(array.shape)}

    def json(self, relative, value):
        raw = canonical_bytes(value)
        require(len(raw) <= MIB, "individual core JSON exceeds1MiB")
        return self._write(relative, lambda stream: stream.write(raw))

    def raw_cfa(self, relative, array):
        require(array.dtype.str == "<u2" and array.flags.c_contiguous, "invalid CFA dtype/storage")
        self.budget.watch(array, "written actual CFA")
        ref = self._write(relative, lambda stream: stream.write(memoryview(array).cast("B")))
        return {**ref, "dtype": "<u2", "shape": list(array.shape)}

    def check(self):
        total = 0
        for path in self.root.rglob("*"):
            mode = path.lstat().st_mode
            require(not path.is_symlink() and path.resolve().is_relative_to(self.root), "output link/escape")
            if stat.S_ISREG(mode):
                total += path.stat().st_size
            else:
                require(stat.S_ISDIR(mode), "nonregular output entry")
        require(total == self.budget.output_bytes, "output directory extent differs from accounted writes")
        self.budget.check()
        return total


def write_private_trace(sampled, store, relative_dir, *, call_id, group):
    require(sampled.budget is store.budget, "sample and writer must share one stage budget")
    require(store.budget.stage == "commission", "private trace requires commission budget")
    sampled.validate_live()
    require(sampled.spec.seed is not None and sampled.q.shape == (96, 128), "private noisy trace shape mismatch")
    require(type(call_id) is str and call_id and type(group) is str and group, "invalid trace identity")
    arrays = {"photo_draw": sampled.photo_draw, "read_used": sampled.read_used,
              "x_used": sampled.x_used, "q": sampled.q,
              "photo_used_override": sampled.photo_used if sampled.active_fault in PHOTO_OVERRIDES else None,
              "read_draw_override": sampled.read_draw if sampled.active_fault in READ_OVERRIDES else None}
    refs = {}
    for name in ARRAY_NAMES:
        if arrays[name] is None:
            refs[name] = None
        else:
            ref = store.array(relative_dir + "/" + name + ".npy", arrays[name])
            refs[name] = {**ref, "path": name + ".npy"}
    record = {"call_id": call_id, "group": group, "phase": sampled.phase,
              "fault_id": sampled.fault_id, "observer_mode": sampled.observer.mode,
              "input": sampled.input_record(), "streams": sampled.streams,
              "arrays": refs, "derived_hashes": sampled.derived_hashes,
              "rail_counts": sampled.rails, "witness": sampled.observer.receipt()}
    # Array refs resolve against this record's parent; the outer ref is store-relative.
    ref = store.json(relative_dir + "/record.json", record)
    store.budget.check()
    return record, ref


def write_cfa(sampled, store, relative):
    require(sampled.budget is store.budget, "sample and writer must share one stage budget")
    require(store.budget.stage == "intended", "intended CFA requires intended stage budget")
    sampled.validate_live()
    require(sampled.spec.scene in ("flat", "textured") and sampled.q.shape == (240, 320),
            "intended CFA population dimensions/scene mismatch")
    require(sampled.phase == "baseline" and sampled.fault_id is None, "private fault/replay cannot emit intended CFA")
    require(sampled.spec.seed is None or sampled.spec.seed in SEEDS, "unregistered intended seed")
    require(all(value == 0 for counts in sampled.rails.values() for value in counts.values()),
            "intended pre-clipping rail refusal")
    # Source/float authority and the complete90-file matrix belong to the future caller.
    ref = store.raw_cfa(relative, sampled.q)
    require(ref["bytes"] == 153600 and ref["sha256"] == sampled.payload_hashes["q"],
            "intended CFA exact extent/sample hash mismatch")
    return {"file": ref, "audit": sampled.audit_record()}
