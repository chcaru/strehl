"""Independent private software-noise reader; never imports or calls a sampler.

The producer supplies its already-running stage Budget. This reader neither
creates a budget nor grants float/input authority. No execution is authorized
by this file's existence. All array work is bounded and charged to that caller.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path
import struct

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CONTRACT_SHA = "4e92e176d0cfae6dcdc9fedab3ff8f5d40f858c47eb0fcddbd14877d894d29f2"
METHOD = "m194g-independent-software-noise-reader-v1"
SHAPE = (96, 128)
FACTORS = (.75, 1.0, 1.0, .6)
PARITIES = ((0, 0), (0, 1), (1, 0), (1, 1))
LEVELS = (0, 64, 4096, 12000)
FAULT_LEVELS = (("c-after-poisson", 12000), ("gain-double", 4096),
                ("omit-read", 0), ("reuse-repeat-zero", 0),
                ("clone-green", 4096), ("read-lag2-mix", 0), ("clamp-black", 0))
THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
FILE_KEYS = {"path", "sha256", "bytes"}
ARRAY_KEYS = FILE_KEYS | {"shape", "dtype"}
INPUT_KEYS = {"scene", "seed", "frame_index", "width", "height", "scalar_level", "expected_scalar_sha256"}
TRACE_KEYS = {"call_id", "group", "phase", "fault_id", "observer_mode", "input", "streams",
              "arrays", "derived_hashes", "rail_counts", "witness"}
ARRAY_NAMES = {"photo_draw", "read_used", "x_used", "q", "photo_used_override", "read_draw_override"}
STREAM_KEYS = {"key", "key_sha256", "entropy_words", "initial_state", "final_state", "call", "draw_sha256"}
RAIL_KEYS = {"x_below_zero", "x_above_white", "rounded_below_zero", "rounded_above_white"}
WITNESS_KEYS = {"sample_calls", "encode_calls", "hook_calls", "collected_events"}


class Rejection(ValueError):
    pass


def need(ok, label):
    if not ok:
        raise Rejection(label)


def keys(value, expected, label):
    need(type(value) is dict and set(value) == set(expected), label + " keys")


def integer(value, label, lo=0, hi=None):
    need(type(value) is int and value >= lo and (hi is None or value <= hi), label + " integer")
    return value


def number(value, label):
    need(type(value) in (int, float) and math.isfinite(value), label + " finite number")
    return float(value)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hash_value(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def canonical(value):
    return (json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def same(a, b):
    return canonical(a) == canonical(b)


def parse_json(raw):
    def object_pairs(pairs):
        out = {}
        for key, val in pairs:
            need(key not in out, "duplicate JSON key")
            out[key] = val
        return out

    def walk(val):
        if type(val) is float:
            need(math.isfinite(val), "nonfinite JSON")
        elif type(val) is dict:
            for item in val.values():
                walk(item)
        elif type(val) is list:
            for item in val:
                walk(item)
    value = json.loads(raw, object_pairs_hook=object_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(Rejection("nonfinite JSON")))
    walk(value)
    return value


def contained(base, relative):
    need(type(relative) is str and relative and "\\" not in relative and ":" not in relative,
         "relative POSIX file path")
    need(all(p not in ("", ".", "..") for p in relative.split("/")), "path components")
    need(not Path(relative).is_absolute(), "absolute reference")
    base = Path(base).resolve(strict=True)
    path = (base / relative).resolve(strict=True)
    need(path.is_relative_to(base) and path != base and path.is_file(), "contained regular file")
    return path


def read_ref(ref, base, budget, *, limit=1_048_576, array=False):
    keys(ref, ARRAY_KEYS if array else FILE_KEYS, "array reference" if array else "file reference")
    integer(ref["bytes"], "file bytes", 1, limit)
    need(hash_value(ref["sha256"]), "file SHA-256")
    path = contained(base, ref["path"])
    budget.check()
    need(path.stat().st_size == ref["bytes"], "file extent before read")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    need(len(raw) == ref["bytes"] and sha(raw) == ref["sha256"], "file bytes/hash")
    budget.check()
    return path, raw


def allocated(budget, shape=SHAPE, dtype="<f8", name="reader array", fill=None):
    budget.check_allocation(tuple(shape), dtype)
    out = budget.watch(np.empty(shape, dtype=dtype), name)
    if fill is not None:
        out.fill(fill)
    return out


def copied(budget, source, name):
    out = allocated(budget, source.shape, source.dtype, name)
    np.copyto(out, source)
    return out


def finite_array(array, budget, label):
    scratch = allocated(budget, array.shape, "|b1", label + " finite mask")
    np.isfinite(array, out=scratch)
    need(bool(scratch.all()), label + " finite array")


def raw_hash(array):
    need(array.flags.c_contiguous, "hash C-contiguous array")
    return hashlib.sha256(memoryview(array).cast("B")).hexdigest()


def read_array(ref, base, budget, dtype, shape=SHAPE, *, allow_nonfinite=False):
    need(type(ref) is dict and ref.get("dtype") == dtype, "declared array dtype")
    need(type(ref.get("shape")) is list and all(type(n) is int for n in ref["shape"])
         and tuple(ref["shape"]) == tuple(shape), "declared array shape")
    size = math.prod(shape) * np.dtype(dtype).itemsize
    _, raw = read_ref(ref, base, budget, limit=size + 4096, array=True)
    need(raw[:8] == b"\x93NUMPY\x01\x00" and len(raw) >= 10, "fixed NPY v1 container")
    header_len = struct.unpack("<H", raw[8:10])[0]
    need(0 < header_len <= 4096 and 10 + header_len <= len(raw), "bounded NPY header")
    try:
        node = ast.parse(raw[10:10 + header_len].decode("latin1").strip(), mode="eval").body
        need(isinstance(node, ast.Dict) and all(isinstance(k, ast.Constant) and type(k.value) is str for k in node.keys),
             "NPY literal dictionary keys")
        header_keys = [k.value for k in node.keys]
        need(len(header_keys) == len(set(header_keys)), "duplicate NPY header key")
        header = ast.literal_eval(node)
    except Rejection:
        raise
    except (ValueError, SyntaxError, UnicodeError) as exc:
        raise Rejection("NPY literal header") from exc
    keys(header, {"descr", "fortran_order", "shape"}, "NPY header")
    need(header["descr"] == dtype and header["fortran_order"] is False,
         "NPY dtype/order")
    need(type(header["shape"]) is tuple and all(type(n) is int for n in header["shape"])
         and header["shape"] == tuple(shape), "NPY exact shape")
    need(len(raw) == 10 + header_len + size, "NPY exact payload extent")
    budget.check_allocation(tuple(shape), dtype)
    array = budget.watch(np.load(io.BytesIO(raw), allow_pickle=False), "verified NPY payload")
    need(array.dtype.str == dtype and array.shape == tuple(shape) and array.flags.c_contiguous,
         "loaded NPY layout")
    need(type(allow_nonfinite) is bool, "explicit nonfinite fixture mode")
    if not allow_nonfinite:
        finite_array(array, budget, "NPY payload")
    budget.check()
    return array


def independent_key(spec, component):
    """Deterministic pre-draw check API; no RNG construction or sampling."""
    need(type(spec) is dict, "key input")
    need(component in ("photo", "read"), "key component")
    need(spec["scene"] in ("textured", "flat", "control-s0", "control-s64", "control-s4096",
                           "control-s12000", "control-live-a", "control-live-b"), "key scene")
    for key, hi in (("seed", 2**32 - 1), ("frame_index", 4), ("width", 320), ("height", 240)):
        integer(spec[key], "key " + key, 0 if key in ("seed", "frame_index") else 2, hi)
    raw = ("strehl-software-noise-v1\nscene=" + spec["scene"] + "\nseed=" + str(spec["seed"])
           + "\nframe=" + str(spec["frame_index"]) + "\ncomponent=" + component
           + "\nwidth=" + str(spec["width"]) + "\nheight=" + str(spec["height"]) + "\n").encode("ascii")
    digest = hashlib.sha256(raw).digest()
    return raw, [struct.unpack("<I", digest[i:i + 4])[0] for i in range(0, 32, 4)]


def state_record(value):
    keys(value, {"bit_generator", "state", "has_uint32", "uinteger"}, "PCG state")
    need(value["bit_generator"] == "PCG64DXSM", "PCG method")
    keys(value["state"], {"state", "inc"}, "PCG inner state")
    integer(value["state"]["state"], "PCG state", 0, 2**128 - 1)
    integer(value["state"]["inc"], "PCG increment", 1, 2**128 - 1)
    need(value["state"]["inc"] % 2 == 1, "PCG odd increment")
    integer(value["has_uint32"], "PCG uint cache flag", 0, 1)
    integer(value["uinteger"], "PCG uint cache", 0, 2**32 - 1)


def witness(value, mode, noisy):
    keys(value, WITNESS_KEYS, "witness")
    for key in WITNESS_KEYS:
        integer(value[key], "witness " + key)
    operations = 3 if noisy else 1
    expected = {"sample_calls": 2 if noisy else 0, "encode_calls": 1,
                "hook_calls": operations if mode != "off" else 0,
                "collected_events": operations if mode == "count" else 0}
    need(same(value, expected), "actual operation/observer witness")


def rounded_codes(x, budget):
    """Independent floor/fraction/parity form of ties-to-even, then rail."""
    finite_array(x, budget, "rounding input")
    floor = allocated(budget, x.shape, "<f8", "rounding floor")
    fraction = allocated(budget, x.shape, "<f8", "rounding fraction")
    odd = allocated(budget, x.shape, "<f8", "rounding parity")
    up = allocated(budget, x.shape, "|b1", "rounding increment mask")
    tie = allocated(budget, x.shape, "|b1", "rounding tie mask")
    np.floor(x, out=floor)
    np.subtract(x, floor, out=fraction)
    np.remainder(floor, 2.0, out=odd)
    np.equal(fraction, .5, out=tie)
    np.greater(odd, 0.0, out=up)
    np.logical_and(tie, up, out=tie)
    np.greater(fraction, .5, out=up)
    np.logical_or(up, tie, out=up)
    np.add(floor, up, out=floor)
    rails = {}
    for name, arr, bound, op in (("x_below_zero", x, 0, np.less),
                                 ("x_above_white", x, 15360, np.greater),
                                 ("rounded_below_zero", floor, 0, np.less),
                                 ("rounded_above_white", floor, 15360, np.greater)):
        op(arr, bound, out=up)
        rails[name] = int(np.count_nonzero(up))
    np.clip(floor, 0, 15360, out=floor)
    q = allocated(budget, x.shape, "<u2", "independently encoded CFA")
    np.copyto(q, floor, casting="unsafe")
    return q, rails


def schedule():
    out = []

    def add(call_id, group, level, seed, frame=0, scene=None, phase="baseline", fault=None, mode="off"):
        out.append({"call_id": call_id, "group": group, "phase": phase,
                    "fault_id": fault, "observer_mode": mode,
                    "input": {"scene": scene or "control-s" + str(level), "seed": seed,
                              "frame_index": frame, "width": 128, "height": 96, "scalar_level": level}})
    for level in LEVELS:
        for r in range(64):
            add(f"baseline-s{level}-r{r:02d}", f"baseline-s{level}", level, 100000 + r)
    for fault, level in FAULT_LEVELS:
        for phase in ("fault", "restored"):
            for r in range(64):
                add(f"{phase}-{fault}-r{r:02d}", f"{phase}-{fault}", level, 100000 + r,
                    phase=phase, fault=fault)
    for seed in (701, 709):
        for frame in range(5):
            add(f"live-a-s{seed}-f{frame}", "live", 12000, seed, frame, "control-live-a")
    add("live-b-s701-f0", "live", 12000, 701, 0, "control-live-b")
    for mode in ("count", "placebo"):
        add("observer-" + mode, "observer", 12000, 701, 0, "control-live-a", phase="replay", mode=mode)
    for frame in reversed(range(5)):
        add(f"replay-f{frame}", "replay", 12000, 701, frame, "control-live-a", phase="replay")
    for frame in range(5):
        add(f"dark-f{frame}", "dark", 0, 701, frame)
    for phase in ("fault", "restored"):
        group = "shared-read-frame" if phase == "fault" else "shared-read-frame-restored"
        for frame in range(5):
            add(f"{group}-f{frame}", group, 0, 701, frame, phase=phase, fault="shared-read-frame")
    add("component-key-restored", "component-key-restored", 12000, 701, 0,
        "control-live-a", phase="restored", fault="omit-component-key")
    need(len(out) == 1186 and len({v["call_id"] for v in out}) == 1186, "literal schedule extent")
    return out


@dataclass
class Trace:
    record: dict
    photo: np.ndarray
    read: np.ndarray
    electrons: np.ndarray
    x: np.ndarray
    q: np.ndarray
    read_draw: np.ndarray
    signature: dict
    nominal: dict


def read_trace(ref, base, expected, budget, *, payload_identities=None):
    path, raw = read_ref(ref, base, budget)
    record = parse_json(raw)
    keys(record, TRACE_KEYS, "private trace")
    for key in ("call_id", "group", "phase", "fault_id", "observer_mode"):
        need(same(record[key], expected[key]), "scheduled " + key)
    inp = record["input"]
    keys(inp, INPUT_KEYS, "trace input")
    need(same({k: inp[k] for k in expected["input"] if k != "scalar_level"},
              {k: v for k, v in expected["input"].items() if k != "scalar_level"})
         and number(inp["scalar_level"], "scalar level") == expected["input"]["scalar_level"], "scheduled input identity")
    need(hash_value(inp["expected_scalar_sha256"]), "scalar hash field")
    scalar = allocated(budget, fill=float(inp["scalar_level"]), name="independent constant input")
    need(raw_hash(scalar) == inp["expected_scalar_sha256"], "actual input binding")
    mu = allocated(budget, name="independent photosite means")
    for (y, x), c in zip(PARITIES, FACTORS):
        np.multiply(scalar[y::2, x::2], c, out=mu[y::2, x::2])
    active = record["fault_id"] if record["phase"] == "fault" else None
    arrays = record["arrays"]
    keys(arrays, ARRAY_NAMES, "trace arrays")
    local_identities = set()
    for array_ref in arrays.values():
        if array_ref is None:
            continue
        keys(array_ref, ARRAY_KEYS, "array FileRef")
        array_path = contained(path.parent, array_ref["path"])
        stat = array_path.stat()
        need(stat.st_ino != 0, "actual payload file identity unavailable")
        identity = (stat.st_dev, stat.st_ino)
        need(identity not in local_identities, "duplicate payload identity within trace")
        local_identities.add(identity)
        if payload_identities is not None:
            need(identity not in payload_identities, "reused payload file identity across calls")
            payload_identities.add(identity)
    photo_raw = read_array(arrays["photo_draw"], path.parent, budget, "<i8")
    need(int(photo_raw.min()) >= 0, "negative photon count")
    read = read_array(arrays["read_used"], path.parent, budget, "<f8")
    x_used = read_array(arrays["x_used"], path.parent, budget, "<f8")
    q = read_array(arrays["q"], path.parent, budget, "<u2")
    photo_exception = active in ("c-after-poisson", "clone-green")
    read_exception = active in ("omit-read", "read-lag2-mix")
    need((arrays["photo_used_override"] is not None) == photo_exception, "required photo override disposition")
    need((arrays["read_draw_override"] is not None) == read_exception, "required read override disposition")
    photo = (read_array(arrays["photo_used_override"], path.parent, budget, "<f8") if photo_exception
             else allocated(budget, name="reconstructed consumed photo"))
    if not photo_exception:
        np.copyto(photo, photo_raw, casting="unsafe")
    z = (read_array(arrays["read_draw_override"], path.parent, budget, "<f8") if read_exception
         else allocated(budget, name="reconstructed raw normal"))
    if not read_exception:
        np.divide(read, 4.0, out=z)
    derived = record["derived_hashes"]
    keys(derived, {"photo_used", "read_draw", "electron_sum", "pre_encoder_x"}, "derived hashes")
    need(raw_hash(photo) == derived["photo_used"] and raw_hash(z) == derived["read_draw"],
         "actual consumed/raw reconstruction hashes")
    scratch = allocated(budget, name="active photo law")
    np.copyto(scratch, photo_raw, casting="unsafe")
    if active == "c-after-poisson":
        for (y, x), c in zip(PARITIES, FACTORS):
            np.multiply(scratch[y::2, x::2], c, out=scratch[y::2, x::2])
    elif active == "clone-green":
        np.copyto(scratch[1::2, 0::2], scratch[0::2, 1::2])
    need(raw_hash(scratch) == raw_hash(photo), "actual declared photo intervention")
    if active == "read-lag2-mix":
        np.add(z[:, :-2], z[:, 2:], out=scratch[:, :-2])
        np.add(z[:, -2:], z[:, :2], out=scratch[:, -2:])
        np.multiply(scratch, 4.0, out=scratch)
        np.divide(scratch, math.sqrt(2.0), out=scratch)
    elif active == "omit-read":
        scratch.fill(0.0)
    else:
        np.multiply(z, 4.0, out=scratch)
    need(raw_hash(scratch) == raw_hash(read), "actual declared read intervention")
    electrons = allocated(budget, name="reconstructed consumed electron sum")
    np.add(photo, read, out=electrons)
    need(raw_hash(electrons) == derived["electron_sum"], "actual electron sum hash")
    pre = allocated(budget, name="reconstructed pre-encoder DN")
    np.multiply(electrons, .5 if active == "gain-double" else .25, out=pre)
    np.add(pre, 512.0, out=pre)
    need(raw_hash(pre) == derived["pre_encoder_x"], "actual pre-encoder hash")
    np.copyto(scratch, pre)
    if active == "clamp-black":
        np.maximum(scratch, 512.0, out=scratch)
    need(raw_hash(scratch) == raw_hash(x_used), "actual declared encoder-input intervention")
    predicted, x_rails = rounded_codes(x_used, budget)
    need(raw_hash(predicted) == raw_hash(q), "exact independently encoded Q")
    del predicted
    _, pre_rails = rounded_codes(pre, budget)
    keys(record["rail_counts"], {"pre_encoder_x", "x_used"}, "rail stages")
    for key, actual in (("pre_encoder_x", pre_rails), ("x_used", x_rails)):
        keys(record["rail_counts"][key], RAIL_KEYS, "rail counts")
        need(same(record["rail_counts"][key], actual), "actual pre-clipping rail counts")
    need(all(v == 0 for v in pre_rails.values()) and all(v == 0 for v in x_rails.values()),
         "unrailed registered private noisy population")
    np.subtract(q, x_used, out=scratch)
    np.abs(scratch, out=scratch)
    rounding_max = float(scratch.max())
    need(rounding_max <= .5, "per-sample rounding bound")
    witness(record["witness"], record["observer_mode"], True)
    streams = record["streams"]
    keys(streams, {"photo", "read"}, "stream pair")
    nominal_keys = {}
    for component, draw in (("photo", photo_raw), ("read", z)):
        st = streams[component]
        keys(st, STREAM_KEYS, "stream")
        actual_spec = dict(inp)
        if active == "reuse-repeat-zero":
            actual_spec["seed"] = 100000
        if active == "shared-read-frame" and component == "read":
            actual_spec["frame_index"] = 0
        key, words = independent_key(actual_spec, component)
        need(type(st["key"]) is str and st["key"].encode("ascii") == key
             and st["key_sha256"] == sha(key) and same(st["entropy_words"], words), "actual RNG key/entropy")
        state_record(st["initial_state"])
        state_record(st["final_state"])
        need(st["initial_state"]["state"]["inc"] == st["final_state"]["state"]["inc"], "PCG increment stability")
        keys(st["call"], {"method", "size", "dtype", "lambda_sha256"}, "actual RNG call")
        call = ({"method": "poisson", "size": None, "dtype": "<i8",
                 "lambda_sha256": raw_hash(scalar if active == "c-after-poisson" else mu)}
                if component == "photo" else {"method": "standard_normal", "size": 12288,
                                               "dtype": "<f8", "lambda_sha256": None})
        need(same(st["call"], call) and st["draw_sha256"] == raw_hash(draw), "actual call/draw hash")
        nominal_key, _ = independent_key(inp, component)
        nominal_keys[component] = (key == nominal_key)
    np.multiply(electrons, .25, out=scratch)
    np.add(scratch, 512.0, out=scratch)
    nominal = {"tuple_keys": nominal_keys, "nominal_gain_encoder": raw_hash(scratch) == raw_hash(x_used),
               "rounding_max_dn": rounding_max}
    signature = {"photo_draw": raw_hash(photo_raw), "read_draw": raw_hash(z),
                 "photo_used": raw_hash(photo), "read_used": raw_hash(read),
                 "electron_sum": raw_hash(electrons), "pre_encoder_x": raw_hash(pre),
                 "x_used": raw_hash(x_used), "q": raw_hash(q), "streams": streams}
    budget.check()
    return Trace(record, photo, read, electrons, x_used, q, z, signature, nominal)


class PairMoments:
    def __init__(self):
        self.n = 0
        self.sums = [0.0] * 5

    def add(self, a, b, buffers, mean_a=0.0, mean_b=0.0):
        need(a.shape == b.shape and a.ndim == 2, "pair input layout")
        h, w = a.shape
        x, y, product = (v[:h, :w] for v in buffers)
        np.subtract(a, mean_a, out=x)
        np.subtract(b, mean_b, out=y)
        terms = [float(np.sum(x, dtype=np.float64)), float(np.sum(y, dtype=np.float64))]
        for left, right in ((x, x), (y, y), (x, y)):
            np.multiply(left, right, out=product)
            terms.append(float(np.sum(product, dtype=np.float64)))
        self.n += a.size
        self.sums = [math.fsum((old, term)) for old, term in zip(self.sums, terms)]

    def result(self, expected_n, undefined=False):
        need(self.n == expected_n, "pair population extent")
        sx, sy, sxx, syy, sxy = self.sums
        n = self.n
        xx = sxx - sx * sx / n
        yy = syy - sy * sy / n
        xy = sxy - sx * sy / n
        correlation = None if xx <= 0 or yy <= 0 else xy / math.sqrt(xx * yy)
        need(correlation is None or math.isfinite(correlation), "finite pair correlation")
        return {"pair_count": n, "covariance": xy / (n - 1), "correlation": correlation,
                "centered_sum_square_a": xx, "centered_sum_square_b": yy,
                "undefined": "zero-photon-law" if undefined else ("zero-denominator" if correlation is None else None),
                "pass": None if undefined else correlation is not None and abs(correlation) <= .02}


class Temporal:
    def __init__(self, budget, level):
        self.budget, self.level, self.n = budget, level, 0
        self.means = {key: allocated(budget, name="online mean " + key, fill=0) for key in ("P", "R", "E", "X", "Q")}
        self.m2 = {key: allocated(budget, name="online M2 " + key, fill=0) for key in self.means}
        self.work = [allocated(budget, name="online scratch") for _ in range(3)]
        self.previous = None
        self.pairs = {f"{kind}-{p}": PairMoments() for kind in ("photo-read", "repeat-photo", "repeat-read", "read-x", "read-y") for p in range(4)}
        self.pairs["green-photo"] = PairMoments()
        self.below = [0] * 4
        self.negative = [0] * 4
        self.photo_nonzero = [0] * 4
        self.max_rounding = 0.0

    def add(self, trace):
        self.n += 1
        for key, array in (("P", trace.photo), ("R", trace.read), ("E", trace.electrons), ("X", trace.x), ("Q", trace.q)):
            delta, delta2, product = self.work
            np.subtract(array, self.means[key], out=delta)
            np.divide(delta, self.n, out=product)
            np.add(self.means[key], product, out=self.means[key])
            np.subtract(array, self.means[key], out=delta2)
            np.multiply(delta, delta2, out=product)
            np.add(self.m2[key], product, out=self.m2[key])
        for p, ((y, x), c) in enumerate(zip(PARITIES, FACTORS)):
            a, b = trace.photo[y::2, x::2], trace.read[y::2, x::2]
            self.pairs[f"photo-read-{p}"].add(a, b, self.work, c * self.level)
            if self.previous is not None:
                self.pairs[f"repeat-photo-{p}"].add(self.previous[0][y::2, x::2], a, self.work, c * self.level, c * self.level)
                self.pairs[f"repeat-read-{p}"].add(self.previous[1][y::2, x::2], b, self.work)
            self.pairs[f"read-x-{p}"].add(trace.read[y::2, x:126:2], trace.read[y::2, x + 2::2], self.work)
            self.pairs[f"read-y-{p}"].add(trace.read[y:94:2, x::2], trace.read[y + 2::2, x::2], self.work)
            # Count masks are explicit tracked arrays, not hidden full-volume populations.
            mask = allocated(self.budget, a.shape, "|b1", "per-parity count mask")
            np.less(trace.q[y::2, x::2], 512, out=mask)
            self.below[p] += int(np.count_nonzero(mask))
            np.less(b, 0.0, out=mask)
            self.negative[p] += int(np.count_nonzero(mask))
            np.not_equal(a, 0.0, out=mask)
            self.photo_nonzero[p] += int(np.count_nonzero(mask))
            del mask
        self.pairs["green-photo"].add(trace.photo[0::2, 1::2], trace.photo[1::2, 0::2], self.work,
                                      self.level, self.level)
        self.previous = None
        self.previous = (copied(self.budget, trace.photo, "previous-repeat consumed photo"),
                         copied(self.budget, trace.read, "previous-repeat consumed read"))
        self.max_rounding = max(self.max_rounding, trace.nominal["rounding_max_dn"])
        self.budget.check()

    def finish(self):
        need(self.n == 64, "complete 64-repeat temporal group")
        moments, quantization = {}, {}
        dark = rounded_normal_oracle()
        for p, ((y, x), c) in enumerate(zip(PARITIES, FACTORS)):
            mu = c * self.level
            actual = {}
            for key in self.means:
                actual[key] = {"mean": float(np.mean(self.means[key][y::2, x::2], dtype=np.float64)),
                               "variance": float(np.sum(self.m2[key][y::2, x::2], dtype=np.float64)) / (63 * 3072)}
            for key, target_mean, target_var in (("P", mu, mu), ("R", 0.0, 16.0),
                                                 ("E", mu, mu + 16.0), ("X", 512 + .25 * mu, .0625 * (mu + 16))):
                row = actual[key]
                row.update(expected_mean=target_mean, expected_variance=target_var)
                row["mean_residual"] = row["mean"] - target_mean
                row["variance_ratio"] = None if target_var == 0 else row["variance"] / target_var
                row["mean_pass"] = row["mean"] == 0 if target_var == 0 else abs(row["mean_residual"]) <= .02 * math.sqrt(target_var)
                row["variance_pass"] = row["variance"] == 0 if target_var == 0 else abs(row["variance_ratio"] - 1) <= .02
                row["nonzero_samples"] = self.photo_nonzero[p] if key == "P" else None
                row["undefined"] = "zero-photon-variance-ratio" if target_var == 0 else None
            moments[str(p)] = actual
            q, xrow = actual["Q"], actual["X"]
            if self.level == 0:
                quantization[str(p)] = {"kind": "dark-rounded-normal", "variance_oracle": dark["variance"],
                    "mean_pass": abs(q["mean"] - 512) <= .02 * math.sqrt(dark["variance"]),
                    "variance_pass": abs(q["variance"] / dark["variance"] - 1) <= .02,
                    "below_black_fraction": self.below[p] / 196608,
                    "negative_read_fraction": self.negative[p] / 196608,
                    "below_black_pass": .29 <= self.below[p] / 196608 <= .33,
                    "negative_read_pass": .48 <= self.negative[p] / 196608 <= .52}
            else:
                a = 64 / 63
                variance_limit = math.sqrt(a * max(xrow["variance"], 0.0)) + a / 4 + .02 * .0625 * (mu + 16)
                mean_limit = .5 + .02 * math.sqrt(.0625 * (mu + 16))
                quantization[str(p)] = {"kind": "bright-finite-sample-bound", "variance_limit": variance_limit,
                    "mean_limit": mean_limit, "variance_movement": q["variance"] - xrow["variance"],
                    "mean_movement": q["mean"] - xrow["mean"],
                    "variance_pass": abs(q["variance"] - xrow["variance"]) <= variance_limit,
                    "mean_pass": abs(q["mean"] - xrow["mean"]) <= mean_limit}
        pairs = {}
        for name, accumulator in self.pairs.items():
            count = (196608 if name.startswith("photo-read") or name == "green-photo" else
                     192512 if name.startswith("read-y") else 193536)
            undefined = self.level == 0 and (name.startswith("photo-read") or name.startswith("repeat-photo") or name == "green-photo")
            pairs[name] = accumulator.result(count, undefined)
        healthy = all(v["mean_pass"] and v["variance_pass"] for rows in moments.values()
                      for key, v in rows.items() if key != "Q")
        healthy &= all(v["pass"] is not False for v in pairs.values())
        healthy &= all(v for row in quantization.values() for key, v in row.items() if key.endswith("_pass"))
        healthy &= all(self.photo_nonzero[p] == 0 for p in range(4)) if self.level == 0 else True
        return {"level": self.level, "repeat_count": 64, "sites_per_parity": 3072,
                "moments": moments, "pairs": pairs, "quantization": quantization,
                "max_rounding_error_dn": self.max_rounding, "nominal_pass": bool(healthy)}


def rounded_normal_oracle():
    p0 = math.erf(.5 / math.sqrt(2))
    probabilities = [p0] + [.5 * (math.erfc((k - .5) / math.sqrt(2)) - math.erfc((k + .5) / math.sqrt(2))) for k in range(1, 13)]
    variance = 2 * math.fsum(k * k * probabilities[k] for k in range(1, 13))
    limit = 12.5
    remainder = 2 * ((limit + 1) + 1.25 / limit) * math.exp(-limit * limit / 2) / math.sqrt(2 * math.pi)
    return {"variance": variance, "p0": p0, "positive_probabilities": probabilities[1:],
            "omitted_second_moment_bound": remainder,
            "scope": "continuous normal rounded to integer; float encoding separately exact; no added-1/12 premise"}


def fault_power(fault, group, signatures):
    """Name the actual rejecting instruments; never use a generic failed group."""
    moments, pairs, quant = group["moments"], group["pairs"], group["quantization"]
    conditions = {}
    if fault == "c-after-poisson":
        conditions["red-shot-variance-rejects"] = not moments["0"]["P"]["variance_pass"]
        conditions["blue-shot-variance-rejects"] = not moments["3"]["P"]["variance_pass"]
        conditions["green-marginal-companions"] = all(moments[str(p)]["P"]["mean_pass"] and moments[str(p)]["P"]["variance_pass"] for p in (1, 2))
    elif fault == "gain-double":
        conditions["all-X-means-reject"] = all(not moments[str(p)]["X"]["mean_pass"] for p in range(4))
        conditions["all-X-variances-reject"] = all(not moments[str(p)]["X"]["variance_pass"] for p in range(4))
    elif fault == "omit-read":
        conditions["all-read-variances-reject"] = all(not moments[str(p)]["R"]["variance_pass"] for p in range(4))
        conditions["all-encoded-dark-variances-reject"] = all(not quant[str(p)]["variance_pass"] for p in range(4))
    elif fault == "reuse-repeat-zero":
        conditions["read-temporal-variance-exact-zero"] = all(moments[str(p)]["R"]["variance"] == 0 for p in range(4))
        conditions["same-read-array-every-repeat"] = len({s["read_used"] for s in signatures}) == 1
        conditions["all-adjacent-read-null-reject"] = all(pairs[f"repeat-read-{p}"]["pass"] is False and pairs[f"repeat-read-{p}"]["correlation"] is not None for p in range(4))
    elif fault == "clone-green":
        conditions["green-photon-null-reject"] = pairs["green-photo"]["pass"] is False and pairs["green-photo"]["correlation"] is not None
        conditions["green-marginal-laws-remain"] = all(moments[str(p)]["P"]["mean_pass"] and moments[str(p)]["P"]["variance_pass"] for p in (1, 2))
    elif fault == "read-lag2-mix":
        conditions["all-read-marginal-variances-pass"] = all(moments[str(p)]["R"]["variance_pass"] for p in range(4))
        conditions["all-lag2-read-correlations-powered"] = all(pairs[f"read-x-{p}"]["correlation"] is not None and pairs[f"read-x-{p}"]["correlation"] > .2 and pairs[f"read-x-{p}"]["pass"] is False for p in range(4))
    elif fault == "clamp-black":
        conditions["no-encoded-value-below-black"] = all(quant[str(p)]["below_black_fraction"] == 0 and not quant[str(p)]["below_black_pass"] for p in range(4))
        conditions["all-encoded-dark-means-and-variances-reject"] = all(not quant[str(p)]["mean_pass"] and not quant[str(p)]["variance_pass"] for p in range(4))
    else:
        raise Rejection("unknown temporal power control")
    return {"fault_id": fault, "conditions": conditions, "pass": all(conditions.values())}


def validate_source_bindings(value, budget):
    need(type(value) is dict and value, "source bindings")
    required = {"experiments/m194g-larger-pupil/" + name for name in
                ("software-noise.py", "software-noise-run.py", "software-noise-authority.py",
                 "independent-noise-reader.py", "software-noise-interface.md", "next-noise-contract.md",
                 "independent-full-float-authority-schema.md")}
    need(required <= set(value), "actual noise source closure")
    for relative, ref in value.items():
        keys(ref, {"sha256", "bytes"}, "source binding")
        read_ref({"path": relative, **ref}, ROOT, budget, limit=2_097_152)
    return sha(canonical(value))


def validate_runtime(ref, base, budget):
    _, raw = read_ref(ref, base, budget)
    value = parse_json(raw)
    keys(value, {"schema", "python", "implementation", "numpy", "system", "machine", "processor",
                 "byteorder", "thread_environment", "interpreter", "modules"}, "runtime record")
    need(value["schema"] == "strehl-software-noise-runtime-v1" and value["python"] == "3.12.10"
         and value["implementation"] == "CPython" and value["numpy"] == "2.4.4"
         and value["system"] == "Windows" and value["machine"] == "AMD64" and value["byteorder"] == "little",
         "registered runtime identity")
    need(type(value["processor"]) is str, "runtime processor description")
    need(same(value["thread_environment"], {key: "2" for key in THREAD_KEYS}), "recorded thread caps")
    need(all(os.environ.get(key) == "2" for key in THREAD_KEYS), "actual reader thread caps")
    need(np.__version__ == "2.4.4", "actual reader NumPy version")
    modules = value["modules"]
    need(type(modules) is dict and {"numpy", "numpy.random", "numpy.random._generator", "numpy.random._pcg64",
         "numpy.random.bit_generator", "numpy._core._multiarray_umath", "numpy.lib.format"} <= set(modules), "runtime module closure")
    for binding in [value["interpreter"], *modules.values()]:
        keys(binding, FILE_KEYS, "actual runtime file binding")
        integer(binding["bytes"], "runtime file size", 1)
        need(hash_value(binding["sha256"]) and type(binding["path"]) is str, "runtime file hash/path")
        path = Path(binding["path"])
        need(path.is_absolute() and path.is_file() and path.stat().st_size == binding["bytes"], "actual runtime file extent")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while block := stream.read(1_048_576):
                digest.update(block)
                budget.check()
        need(digest.hexdigest() == binding["sha256"], "actual runtime file bytes")
    return ref["sha256"]


def validate_index(index_path, external_sha256, budget, *, runtime=True):
    need(hash_value(external_sha256), "external private-index SHA")
    index_path = Path(index_path).resolve(strict=True)
    need(index_path.is_file() and 0 < index_path.stat().st_size <= 1_048_576, "bounded private index")
    with index_path.open("rb") as stream:
        raw = stream.read(1_048_577)
    need(len(raw) <= 1_048_576 and sha(raw) == external_sha256, "external private-index bytes")
    index = parse_json(raw)
    keys(index, {"schema", "status", "contract", "runtime", "source_bindings", "records", "deterministic", "work"}, "private index")
    need(index["schema"] == "m194g-software-noise-private-index-v1"
         and index["status"] == "COMPLETE_PRIVATE_TRACES_UNCOMMISSIONED", "private index status/schema")
    _, contract_raw = read_ref(index["contract"], index_path.parent, budget)
    need(sha(contract_raw) == CONTRACT_SHA, "frozen Markdown noise contract")
    source_digest = validate_source_bindings(index["source_bindings"], budget)
    if runtime:
        validate_runtime(index["runtime"], index_path.parent, budget)
    else:
        read_ref(index["runtime"], index_path.parent, budget)
    need(type(index["records"]) is list and len(index["records"]) == 1186, "complete private record count")
    expected = schedule()
    paths = set()
    for item, spec in zip(index["records"], expected):
        keys(item, {"call_id", "record"}, "scheduled record reference")
        need(item["call_id"] == spec["call_id"], "literal ordered call population")
        keys(item["record"], FILE_KEYS, "record FileRef")
        path = contained(index_path.parent, item["record"]["path"])
        need(path not in paths, "unique private record file identity")
        paths.add(path)
    work = index["work"]
    keys(work, {"stage", "limits", "cpu_seconds", "wall_seconds", "requested_variates", "live_array_bytes",
                "output_bytes", "requested_by_component", "generator_constructions", "started_frames", "completed_frames",
                "peak_live_array_bytes", "tracked_scope"}, "shared work receipt")
    need(work["stage"] == "commission", "shared commission work stage")
    limits = {"cpu_seconds": 120.0, "wall_seconds": 240.0, "requested_variates": 32_000_000,
              "live_array_bytes": 33_554_432, "output_bytes": 536_870_912}
    need(same(work["limits"], limits), "fixed commission limits")
    for key, limit in limits.items():
        value = number(work[key], "work " + key) if key.endswith("seconds") else integer(work[key], "work " + key)
        need(0 <= value <= limit, "recorded work within " + key)
    integer(work["peak_live_array_bytes"], "peak named allocation", 0, limits["live_array_bytes"])
    need(type(work["tracked_scope"]) is str and "not RSS" in work["tracked_scope"], "explicit allocation scope")
    need(type(work.get("requested_variates")) is int and work["requested_variates"] == 29_147_136,
         "actual complete requested variates")
    need(same(work.get("requested_by_component"), {"photo": 14_573_568, "read": 14_573_568}), "actual component request counts")
    need(work.get("generator_constructions") == 2372 and type(work.get("generator_constructions")) is int,
         "actual generator construction count")
    need(type(work["started_frames"]) is int and work["started_frames"] == 1195
         and type(work["completed_frames"]) is int and work["completed_frames"] == 1194,
         "actual completed and pre-draw-refused frame accounting")
    budget.check()
    return index_path, index, expected, source_digest


def cross_frame(records, expected, base, budget, *, fault=False):
    by_id = {v["call_id"]: (v["record"], s) for v, s in zip(records, expected)}
    rows = []
    for first in range(5):
        for second in range(first + 1, 5):
            pooled = PairMoments()
            descriptive = []
            work = [allocated(budget, name="cross-frame pair scratch") for _ in range(3)]
            for group in ("live-a-s701", "live-a-s709", "shared-read-frame" if fault else "dark"):
                a_ref, a_expected = by_id[f"{group}-f{first}"]
                b_ref, b_expected = by_id[f"{group}-f{second}"]
                a = read_trace(a_ref, base, a_expected, budget)
                b = read_trace(b_ref, base, b_expected, budget)
                pooled.add(a.read, b.read, work)
                for parity, (y, x) in enumerate(PARITIES):
                    subset = PairMoments()
                    subset.add(a.read[y::2, x::2], b.read[y::2, x::2], work)
                    data = subset.result(3072)
                    data["pass"] = None
                    data["scope"] = "descriptive subset; no .02 acceptance bar"
                    descriptive.append({"group": group, "parity": parity, **data})
                del a, b
            rows.append({"frame_pair": [first, second], "pooled": pooled.result(36864), "subsets": descriptive})
            del work
            budget.check()
    return rows


def replay_checks(signatures, metadata):
    checks = []

    def record(name, condition):
        checks.append({"name": name, "pass": bool(condition)})
    for fault, level in FAULT_LEVELS:
        for r in range(64):
            record(f"restored-{fault}-r{r:02d}", same(signatures[f"restored-{fault}-r{r:02d}"],
                   signatures[f"baseline-s{level}-r{r:02d}"]))
    for mode in ("count", "placebo"):
        record("observer-" + mode, same(signatures["observer-" + mode], signatures["live-a-s701-f0"]))
    for frame in range(5):
        record(f"reverse-replay-{frame}", same(signatures[f"replay-f{frame}"], signatures[f"live-a-s701-f{frame}"]))
        record(f"shared-read-restored-{frame}", same(signatures[f"shared-read-frame-restored-f{frame}"], signatures[f"dark-f{frame}"]))
    record("component-key-restored", same(signatures["component-key-restored"], signatures["live-a-s701-f0"]))
    live_ids = [f"live-a-s{seed}-f{frame}" for seed in (701, 709) for frame in range(5)] + ["live-b-s701-f0"]
    for component in ("photo", "read"):
        for field in ("key", "initial_state", "final_state"):
            values = {canonical(signatures[name]["streams"][component][field]) for name in live_ids}
            record("live-" + component + "-" + field, len(values) == 11)
    for field in ("photo_draw", "read_draw", "photo_used", "read_used", "electron_sum", "x_used", "q"):
        record("live-payload-" + field, len({signatures[name][field] for name in live_ids}) == 11)
    record("shared-read-five-identical", len({signatures[f"shared-read-frame-f{k}"]["read_used"] for k in range(5)}) == 1)
    for name, nominal in metadata.items():
        if name.startswith("fault-reuse-repeat-zero-") or name.startswith("shared-read-frame-f"):
            continue
        record("nominal-keys-" + name, all(nominal["tuple_keys"].values()))
    # A changed variance can never substitute for a preserved raw read-stream control.
    for fault, level in FAULT_LEVELS:
        if fault == "reuse-repeat-zero":
            continue
        for r in range(64):
            record(f"unchanged-raw-read-{fault}-{r}", signatures[f"fault-{fault}-r{r:02d}"]["read_draw"] == signatures[f"baseline-s{level}-r{r:02d}"]["read_draw"])
    return checks


DETERMINISTIC_IDS = ("round-baseline", "round-half-up", "round-restored", "reject-nan", "reject-posinf",
                     "reject-neginf", "tag-baseline", "tag-swap-rb", "tag-rb-restored", "tag-swap-green",
                     "tag-green-restored", "noise-off-off", "noise-off-count", "noise-off-placebo",
                     "component-key-omitted", "resource-stale-owner", "independent-key-preflight")


def deterministic_checks(records, base, budget):
    need(type(records) is list and len(records) == len(DETERMINISTIC_IDS), "complete deterministic population")
    results, signatures = [], {}
    round_x = [-1.5, -.5, .5, 1.5, 511.5, 512.5, 513.5, 15359.5, 15360.5, 15361.5]
    round_q = [0, 0, 0, 2, 512, 512, 514, 15360, 15360, 15360]
    for record, call_id in zip(records, DETERMINISTIC_IDS):
        keys(record, {"call_id", "kind", "input", "q", "witness", "status", "exception", "details"}, "deterministic record")
        need(record["call_id"] == call_id, "ordered deterministic identity")
        kind = ("rounding" if call_id.startswith("round-") else "nonfinite" if call_id.startswith("reject-")
                else "tag" if call_id.startswith("tag-") else "noise-off" if call_id.startswith("noise-off-")
                else "omitted-key" if call_id == "component-key-omitted" else "resource" if call_id == "resource-stale-owner"
                else "key-preflight")
        need(record["kind"] == kind, "deterministic kind")
        refusing = kind in ("nonfinite", "omitted-key")
        need(record["status"] == ("REFUSED" if refusing else "VALUE"), "deterministic disposition")
        if refusing:
            keys(record["exception"], {"type", "message"}, "expected refusal")
            expected_message = "encoder input contains nonfinite values" if kind == "nonfinite" else "RNG key bytes mismatch"
            need(record["exception"]["type"] == "ValueError" and record["exception"]["message"] == expected_message,
                 "named input refusal; not unrelated I/O or budget")
            need(record["q"] is None and record["witness"] is None, "refusal has no successful output/witness")
        else:
            need(record["exception"] is None, "successful deterministic exception")
        evidence = {"call_id": call_id, "pass": True}
        if kind in ("rounding", "tag", "noise-off"):
            shape = (10,) if kind == "rounding" else (4, 6) if kind == "tag" else SHAPE
            x = read_array(record["input"], base, budget, "<f8", shape)
            q = read_array(record["q"], base, budget, "<u2", shape)
            expected_x = allocated(budget, shape, name="deterministic input oracle")
            expected_q = allocated(budget, shape, "<u2", "deterministic code oracle")
            if kind == "rounding":
                expected_x[:] = round_x
                expected_q[:] = round_q
                need(raw_hash(x) == raw_hash(expected_x), "literal rounding stimulus")
                oracle_q, _ = rounded_codes(x, budget)
                need(raw_hash(oracle_q) == raw_hash(expected_q), "independent rounding instrument literal oracle")
                del oracle_q
                if call_id == "round-half-up":
                    expected_q[:] = [0, 0, 1, 2, 512, 513, 514, 15360, 15360, 15360]
                    need(raw_hash(q) != signatures["round-baseline"], "half-up Q destroyer active")
                mode = "off"
                keys(record["details"], set(), "round details")
            elif kind == "tag":
                for y in range(4):
                    for xindex in range(6):
                        scalar = 1600 + 80 * xindex + 160 * y
                        expected_x[y, xindex] = scalar
                        c = FACTORS[(y % 2) * 2 + xindex % 2]
                        expected_q[y, xindex] = round(512 + .25 * (c * scalar))
                need(raw_hash(x) == raw_hash(expected_x), "literal tagged scalar stimulus")
                if call_id in ("tag-swap-rb", "tag-swap-green"):
                    for y in range(0, 4, 2):
                        for xindex in range(0, 6, 2):
                            a, b = ((y, xindex), (y + 1, xindex + 1)) if call_id == "tag-swap-rb" else ((y, xindex + 1), (y + 1, xindex))
                            old = int(expected_q[a])
                            expected_q[a] = expected_q[b]
                            expected_q[b] = old
                    need(raw_hash(q) != signatures["tag-baseline"], "tagged parity destroyer active")
                mode = "off"
                keys(record["details"], set(), "tag details")
            else:
                expected_x.fill(12000.0)
                for (y, xindex), code in zip(PARITIES, (2762, 3512, 3512, 2312)):
                    expected_q[y::2, xindex::2] = code
                need(raw_hash(x) == raw_hash(expected_x), "literal noise-off scalar")
                mode = call_id.removeprefix("noise-off-")
                details = record["details"]
                keys(details, {"generator_delta", "requested_delta", "forbidden_sampler_calls", "audit"}, "noise-off details")
                for key in ("generator_delta", "requested_delta", "forbidden_sampler_calls"):
                    need(type(details[key]) is int and details[key] == 0, "noise-off actual zero " + key)
                audit = details["audit"]
                keys(audit, {"input", "phase", "fault_id", "observer_mode", "streams", "derived_hashes", "rail_counts", "witness", "q_sha256"}, "noise-off actual audit")
                keys(audit["input"], INPUT_KEYS, "noise-off input identity")
                expected_input = {"scene": "control-s12000", "seed": None, "frame_index": 0,
                                  "width": 128, "height": 96, "scalar_level": 12000,
                                  "expected_scalar_sha256": raw_hash(x)}
                need(same(audit["input"], expected_input) and audit["streams"] is None
                     and audit["input"]["expected_scalar_sha256"] == raw_hash(x)
                     and audit["q_sha256"] == raw_hash(q) and audit["observer_mode"] == mode
                     and audit["phase"] == "baseline" and audit["fault_id"] is None
                     and same(audit["witness"], record["witness"]), "actual noise-off metadata/hash/witness")
                expected_e = allocated(budget, name="noise-off actual consumed oracle")
                expected_pre = allocated(budget, name="noise-off actual pre-encoder oracle")
                for (y, xindex), c in zip(PARITIES, FACTORS):
                    np.multiply(x[y::2, xindex::2], c, out=expected_e[y::2, xindex::2])
                np.multiply(expected_e, .25, out=expected_pre)
                np.add(expected_pre, 512.0, out=expected_pre)
                need(same(audit["derived_hashes"], {"photo_used": raw_hash(expected_e), "read_draw": None,
                     "electron_sum": raw_hash(expected_e), "pre_encoder_x": raw_hash(expected_pre)}),
                     "noise-off actual consumed hashes")
                need(same(audit["rail_counts"], {stage: {key: 0 for key in RAIL_KEYS} for stage in ("pre_encoder_x", "x_used")}),
                     "noise-off rail counts")
                del expected_e, expected_pre
            need(raw_hash(q) == raw_hash(expected_q), "deterministic exact Q")
            witness(record["witness"], mode, False)
            signatures[call_id] = raw_hash(q)
            evidence["q_sha256"] = raw_hash(q)
            del x, q, expected_x, expected_q
        elif kind == "nonfinite":
            x = read_array(record["input"], base, budget, "<f8", (1,), allow_nonfinite=True)
            actual = float(x[0])
            need(math.isnan(actual) if call_id == "reject-nan" else actual == (math.inf if call_id == "reject-posinf" else -math.inf), "actual named nonfinite input")
            need(record["details"] == {}, "nonfinite details")
            # The reader's ordinary path must independently refuse that same payload.
            try:
                read_array(record["input"], base, budget, "<f8", (1,))
            except Rejection as exc:
                need("finite array" in str(exc), "actual nonfinite-reader rejection cause")
            else:
                raise Rejection("ordinary array reader accepted named nonfinite payload")
            evidence["input_class"] = call_id.removeprefix("reject-")
            del x
        elif kind == "omitted-key":
            need(record["input"] is None, "omitted key has no emitted numeric input fixture")
            details = record["details"]
            keys(details, {"spec", "generator_delta", "requested_delta"}, "omitted-key details")
            need(same(details["spec"], {"scene": "control-live-a", "seed": 701, "frame_index": 0,
                 "width": 128, "height": 96, "scalar_level": 12000}), "omitted-key fixed tuple")
            for key in ("generator_delta", "requested_delta"):
                need(type(details[key]) is int and details[key] == 0, "omitted-key zero " + key)
        elif kind == "resource":
            need(record["input"] is None and record["q"] is None and record["witness"] is None, "resource has no sample payload")
            expected = {"expired_owner_dead": True, "live_shape": [5, 8], "live_nbytes": 320,
                        "registered_owner_is_live": True, "registered_bytes": 320,
                        "live_delta_bytes": 320, "alias_delta_bytes": 0,
                        "oversize_refused": True, "restored_alias_same_bytes": True}
            need(same(record["details"], expected), "actual stale-owner/alias/resource refusal witness")
        else:
            need(record["input"] is None and record["q"] is None and record["witness"] is None, "key preflight has no draw")
            need(same(record["details"], {"component_keys_checked": 2372, "key_bytes_checked": True,
                 "entropy_words_checked": True}), "actual complete independent key comparison witness")
        results.append(evidence)
        budget.check()
    for restored, original in (("round-restored", "round-baseline"), ("tag-rb-restored", "tag-baseline"),
                                ("tag-green-restored", "tag-baseline"), ("noise-off-count", "noise-off-off"),
                                ("noise-off-placebo", "noise-off-off")):
        need(signatures[restored] == signatures[original], "deterministic restored/null bytes")
    return results


def read_commission(index_path, external_index_sha256, *, budget, private_preflight=False):
    """The actual entrypoint; preflight mode is explicitly incapable of admission."""
    need(type(private_preflight) is bool, "private preflight mode")
    budget.check()
    before = budget.receipt()
    own_before = sha(Path(__file__).read_bytes())
    path, index, expected, source_digest = validate_index(index_path, external_index_sha256, budget,
                                                       runtime=not private_preflight)
    if private_preflight:
        return {"schema": "m194g-independent-noise-preflight-v1", "status": "PASS_PRIVATE_READER_PREFLIGHT_ONLY",
                "index_sha256": external_index_sha256, "count": len(expected), "source_bindings_sha256": source_digest}
    deterministic = deterministic_checks(index["deterministic"], path.parent, budget)
    groups, signatures, nominal = {}, {}, {}
    payload_identities = set()
    engine = None
    current_group = None
    for index_number, (item, spec) in enumerate(zip(index["records"], expected)):
        trace = read_trace(item["record"], path.parent, spec, budget, payload_identities=payload_identities)
        signatures[spec["call_id"]] = trace.signature
        nominal[spec["call_id"]] = trace.nominal
        if index_number < 1152:
            if current_group != spec["group"]:
                need(engine is None, "previous temporal group not finalized")
                engine = Temporal(budget, spec["input"]["scalar_level"])
                current_group = spec["group"]
            engine.add(trace)
            if engine.n == 64:
                groups[current_group] = engine.finish()
                del engine
                engine = None
        del trace
        budget.check()
    need(engine is None and len(groups) == 18 and len(signatures) == 1186 and len(payload_identities) == 5000,
         "all actual temporal groups and distinct payloads read")
    replay = replay_checks(signatures, nominal)
    powers = [fault_power(fault, groups["fault-" + fault], [signatures[f"fault-{fault}-r{r:02d}"] for r in range(64)]) for fault, _ in FAULT_LEVELS]
    cross_null = cross_frame(index["records"], expected, path.parent, budget)
    cross_fault = cross_frame(index["records"], expected, path.parent, budget, fault=True)
    cross_power = all(row["pooled"]["pass"] is False and row["pooled"]["correlation"] is not None for row in cross_fault)
    healthy = all(group["nominal_pass"] for name, group in groups.items() if not name.startswith("fault-"))
    passed = (healthy and all(row["pass"] for row in replay) and all(row["pass"] for row in powers)
              and all(row["pooled"]["pass"] for row in cross_null) and cross_power)
    need(sha(Path(__file__).read_bytes()) == own_before, "independent reader source changed")
    need(validate_source_bindings(index["source_bindings"], budget) == source_digest, "noise source set changed through read")
    rechecked = recheck_commission_files(path, external_index_sha256, budget=budget)
    # Actual consumer work must never request another photo/normal variate.
    after = budget.receipt()
    need(same(before["requested_by_component"], after["requested_by_component"])
         and before["generator_constructions"] == after["generator_constructions"], "reader drew samples or constructed generators")
    result = {"schema": "m194g-independent-software-noise-reader-v1", "method": METHOD,
              "status": "PASS_SOFTWARE_NOISE_PRIVATE_TRACES" if passed else "UNCOMMISSIONED_SOFTWARE_NOISE_PRIVATE_TRACES",
              "index": {"path": str(path), "sha256": external_index_sha256, "bytes": path.stat().st_size},
              "contract_sha256": CONTRACT_SHA, "reader_source_sha256": own_before,
              "source_bindings_sha256": source_digest, "record_count": 1186, "groups": groups,
              "deterministic": deterministic, "fault_power": powers, "replay": replay,
              "cross_frame_null": cross_null, "cross_frame_fault": cross_fault, "cross_frame_fault_power": cross_power,
              "rounded_normal_oracle": rounded_normal_oracle(), "signatures_sha256": sha(canonical(signatures)),
              "nominal_metadata_sha256": sha(canonical(nominal)), "work_before": before, "work_after": after,
              "nominal_metadata_failures": [{"call_id": name, **item} for name, item in nominal.items()
                                            if not all(item["tuple_keys"].values()) or not item["nominal_gain_encoder"]],
              "terminal_input_recheck": rechecked,
              "scope": "actual private traces only; no RNG resampling, physical calibration, float authority or intended-CFA admission"}
    need(len(canonical(result)) <= 1_048_576, "bounded independent reader result")
    budget.check()
    return result


def recheck_commission_files(index_path, external_index_sha256, *, budget):
    """Recheck actual bound bytes at the caller's final authority boundary."""
    path, index, expected, source_digest = validate_index(index_path, external_index_sha256, budget)
    count = 0
    array_count = 0
    digest = hashlib.sha256()
    for item, spec in zip(index["records"], expected):
        record_path, raw = read_ref(item["record"], path.parent, budget)
        record = parse_json(raw)
        keys(record, TRACE_KEYS, "terminal trace")
        need(record["call_id"] == spec["call_id"], "terminal trace identity")
        keys(record["arrays"], ARRAY_NAMES, "terminal trace array set")
        digest.update(canonical(item))
        for ref in record["arrays"].values():
            if ref is not None:
                read_ref(ref, record_path.parent, budget, limit=102400, array=True)
                digest.update(canonical(ref))
                array_count += 1
        count += 1
    need(count == 1186 and array_count == 5000, "terminal full trace/payload recheck")
    need(type(index["deterministic"]) is list and len(index["deterministic"]) == len(DETERMINISTIC_IDS),
         "terminal deterministic population")
    deterministic_arrays = 0
    for record, name in zip(index["deterministic"], DETERMINISTIC_IDS):
        need(record["call_id"] == name, "terminal deterministic identity")
        for field in ("input", "q"):
            if record[field] is not None:
                read_ref(record[field], path.parent, budget, limit=102400, array=True)
                digest.update(canonical(record[field]))
                deterministic_arrays += 1
    budget.check()
    return {"status": "RECHECKED_BOUND_PRIVATE_BYTES_ONLY", "record_count": count,
            "noisy_array_count": array_count, "deterministic_array_count": deterministic_arrays,
            "reference_sequence_sha256": digest.hexdigest(), "source_bindings_sha256": source_digest,
            "runtime_sha256": index["runtime"]["sha256"]}


def run_reader_controls(index_path, external_index_sha256, *, budget, store, write_bytes, genuine_result):
    """Corrupt retained bytes/metadata without any random calls or copied trace volume.

    The real full entrypoint's preceding result is the valid companion. Cheap
    index controls use the SAME entrypoint's explicit preflight boundary. One
    actual full entry with a changed first input binding must reject there.
    Remaining payload controls exercise the exact downstream trace/NPY calls.
    """
    need(genuine_result.get("method") == METHOD and genuine_result.get("status") == "PASS_SOFTWARE_NOISE_PRIVATE_TRACES"
         and genuine_result.get("index", {}).get("sha256") == external_index_sha256
         and genuine_result.get("reader_source_sha256") == sha(Path(__file__).read_bytes()),
         "actual completed full-reader companion required")
    need(store.budget is budget, "reader controls share actual writer/budget")
    path, index, expected, _ = validate_index(index_path, external_index_sha256, budget, runtime=False)
    need(store.root.resolve() == path.parent, "control outputs in same counted package")
    start = budget.receipt()
    own_before = sha(Path(__file__).read_bytes())
    checks = []
    written_metadata = 0

    def write_json(relative, value):
        nonlocal written_metadata
        payload = canonical(value)
        need(len(payload) <= 1_048_576 and budget.output_bytes - start["output_bytes"] + len(payload) <= 67_108_864,
             "metadata control package limits")
        written_metadata += len(payload)
        return store.json(relative, value)

    def counted_bytes(relative, raw):
        need(type(raw) is bytes and len(raw) <= 1_048_576
             and budget.output_bytes - start["output_bytes"] + len(raw) <= 67_108_864,
             "byte-mutant package limits")
        ref = write_bytes(relative, raw)
        need(same(ref, {"path": relative, "bytes": len(raw), "sha256": sha(raw)}), "actual counted mutant bytes")
        return ref

    def reject(name, callback, message):
        try:
            callback()
        except Rejection as exc:
            checks.append({"name": name, "pass": message in str(exc), "exception": type(exc).__name__, "message": str(exc)})
        else:
            checks.append({"name": name, "pass": False, "exception": None, "message": "accepted deliberately invalid input"})
        budget.check()

    def clone(value):
        return parse_json(canonical(value))

    # These mutations are written beside the original index because FileRefs
    # resolve from the index parent. No path rebasing or whole-package copying.
    def index_fault(name, mutate, message):
        changed = clone(index)
        mutate(changed)
        ref = write_json("reader-control-" + name + "-index.json", changed)
        reject(name, lambda: read_commission(store.root / ref["path"], ref["sha256"], budget=budget, private_preflight=True), message)

    valid = read_commission(path, external_index_sha256, budget=budget, private_preflight=True)
    checks.append({"name": "actual-entry-preflight-valid", "pass": valid["status"] == "PASS_PRIVATE_READER_PREFLIGHT_ONLY"})
    index_fault("missing-call", lambda v: v["records"].pop(), "complete private record count")
    index_fault("duplicate-call", lambda v: v["records"].__setitem__(1, clone(v["records"][0])), "literal ordered call population")
    index_fault("reused-record-file", lambda v: v["records"][1].__setitem__("record", clone(v["records"][0]["record"])), "unique private record file identity")
    index_fault("omitted-reader-source", lambda v: v["source_bindings"].pop("experiments/m194g-larger-pupil/independent-noise-reader.py"), "actual noise source closure")
    index_fault("bool-variate-count", lambda v: v["work"].__setitem__("requested_variates", True), "work requested_variates integer")
    index_fault("incomplete-status", lambda v: v.__setitem__("status", "INCOMPLETE"), "private index status/schema")
    changed_contract = counted_bytes("reader-control-changed-contract.md", b"Changed deterministic control; no noise contract.\n")
    index_fault("rehashed-wrong-Markdown-contract", lambda v: v.__setitem__("contract", changed_contract), "frozen Markdown noise contract")

    first_ref = index["records"][0]["record"]
    first_path, first_raw = read_ref(first_ref, path.parent, budget)
    first = parse_json(first_raw)
    first_directory = Path(first_ref["path"]).parent.as_posix()
    original_trace = read_trace(first_ref, path.parent, expected[0], budget)
    original_signature = original_trace.signature
    del original_trace

    def trace_fault(name, mutate, message, *, entry=False):
        changed = clone(first)
        mutate(changed)
        relative = first_directory + "/reader-control-" + name + "-record.json"
        ref = write_json(relative, changed)
        if entry:
            changed_index = clone(index)
            changed_index["records"][0]["record"] = ref
            entry_ref = write_json("reader-control-" + name + "-index.json", changed_index)
            reject(name, lambda: read_commission(store.root / entry_ref["path"], entry_ref["sha256"], budget=budget), message)
        else:
            reject(name, lambda: read_trace(ref, path.parent, expected[0], budget), message)

    trace_fault("actual-full-entry-changed-input-binding", lambda v: v["input"].__setitem__("expected_scalar_sha256", "0" * 64), "actual input binding", entry=True)
    trace_fault("bool-original-frame", lambda v: v["input"].__setitem__("frame_index", False), "scheduled input identity")
    trace_fault("mislabeled-reused-frame", lambda v: v["input"].__setitem__("seed", 100001), "scheduled input identity")
    trace_fault("stale-raw-normal-hash", lambda v: v["derived_hashes"].__setitem__("read_draw", "0" * 64), "actual consumed/raw reconstruction hashes")
    trace_fault("unexpected-photo-override", lambda v: v["arrays"].__setitem__("photo_used_override", clone(v["arrays"]["read_used"])), "duplicate payload identity within trace")
    trace_fault("unreached-observer", lambda v: v["witness"].__setitem__("sample_calls", 0), "actual operation/observer witness")
    trace_fault("wrong-native-call-size", lambda v: v["streams"]["read"]["call"].__setitem__("size", 6144), "actual call/draw hash")
    trace_fault("omitted-key-component", lambda v: v["streams"]["read"].__setitem__("key", v["streams"]["read"]["key"].replace("component=read\n", "")), "actual RNG key/entropy")
    trace_fault("big-endian-entropy-words", lambda v: v["streams"]["read"].__setitem__("entropy_words", [struct.unpack(">I", hashlib.sha256(v["streams"]["read"]["key"].encode()).digest()[k:k + 4])[0] for k in range(0, 32, 4)]), "actual RNG key/entropy")
    trace_fault("bool-PCG-state", lambda v: v["streams"]["read"]["initial_state"]["state"].__setitem__("state", True), "PCG state integer")

    # A rehashed changed actual Q must reach the independent value check.
    original_q = read_array(first["arrays"]["q"], first_path.parent, budget, "<u2")
    changed_q = copied(budget, original_q, "reader Q destroyer")
    changed_q[5, 7] = int(changed_q[5, 7]) + 1
    q_path = first_directory + "/reader-control-changed-q.npy"
    q_ref = store.array(q_path, changed_q)
    q_ref = {**q_ref, "path": Path(q_path).name}
    trace_fault("rehashed-Q-value", lambda v: v["arrays"].__setitem__("q", q_ref), "exact independently encoded Q")
    del original_q, changed_q

    # Header/extent controls never construct the advertised wrong allocation.
    array_ref = first["arrays"]["read_used"]
    _, original_bytes = read_ref(array_ref, first_path.parent, budget, limit=102400, array=True)
    old_header_size = struct.unpack("<H", original_bytes[8:10])[0]
    body = original_bytes[10 + old_header_size:]

    def npy_fixture(name, header=None, payload=None, message="NPY exact payload extent"):
        if header is None:
            mutated = payload
        else:
            header_bytes = (repr(header) + "\n").encode("latin1")
            mutated = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header_bytes)) + header_bytes + body
        relative = first_directory + "/reader-control-" + name + ".npy"
        ref = counted_bytes(relative, mutated)
        ref = {**ref, "path": Path(relative).name, "dtype": "<f8", "shape": [96, 128]}
        reject(name, lambda: read_array(ref, first_path.parent, budget, "<f8"), message)

    npy_fixture("declared-huge-allocation", {"descr": "<f8", "fortran_order": False, "shape": (2**35, 128)}, message="NPY exact shape")
    npy_fixture("object-NPY", {"descr": "|O", "fortran_order": False, "shape": SHAPE}, message="NPY dtype/order")
    npy_fixture("transposed-storage-NPY", {"descr": "<f8", "fortran_order": True, "shape": SHAPE}, message="NPY dtype/order")
    npy_fixture("short-NPY", payload=original_bytes[:-1])
    npy_fixture("appended-NPY", payload=original_bytes + b"x")
    duplicate_header = b"{'descr': '|O', 'descr': '<f8', 'fortran_order': False, 'shape': (96, 128)}\n"
    npy_fixture("duplicate-descr-NPY", payload=b"\x93NUMPY\x01\x00" + struct.pack("<H", len(duplicate_header))
                + duplicate_header + body, message="duplicate NPY header key")
    duplicate = first_raw.rstrip()[:-1] + b',"call_id":"baseline-s0-r00"}\n'
    duplicate_ref = counted_bytes(first_directory + "/reader-control-duplicate-json-record.json", duplicate)
    reject("duplicate-JSON-key", lambda: read_trace(duplicate_ref, path.parent, expected[0], budget), "duplicate JSON key")

    # Required exceptional fields cannot silently revert to nominal raw draws.
    by_id = {row["call_id"]: (row["record"], spec) for row, spec in zip(index["records"], expected)}
    for call_id, field in (("fault-c-after-poisson-r00", "photo_used_override"),
                           ("fault-clone-green-r00", "photo_used_override"),
                           ("fault-omit-read-r00", "read_draw_override"),
                           ("fault-read-lag2-mix-r00", "read_draw_override")):
        ref, spec = by_id[call_id]
        actual_path, raw = read_ref(ref, path.parent, budget)
        record = parse_json(raw)
        valid_trace = read_trace(ref, path.parent, spec, budget)
        valid_signature = valid_trace.signature
        del valid_trace
        record["arrays"][field] = None
        relative = Path(ref["path"]).parent.as_posix() + "/reader-control-missing-override-record.json"
        bad_ref = write_json(relative, record)
        reject("missing-" + call_id + "-override", lambda: read_trace(bad_ref, path.parent, spec, budget),
               "required photo override disposition" if field.startswith("photo") else "required read override disposition")
        restored = read_trace(ref, path.parent, spec, budget)
        checks.append({"name": "restored-parser-" + call_id, "pass": same(restored.signature, valid_signature)})
        del restored
    restored_trace = read_trace(first_ref, path.parent, expected[0], budget)
    checks.append({"name": "restored-first-actual-trace", "pass": same(restored_trace.signature, original_signature)})
    del restored_trace
    restored_entry = read_commission(path, external_index_sha256, budget=budget, private_preflight=True)
    checks.append({"name": "restored-actual-entry", "pass": restored_entry["status"] == "PASS_PRIVATE_READER_PREFLIGHT_ONLY"})
    stop = budget.receipt()
    need(sha(Path(__file__).read_bytes()) == own_before, "reader-control source changed")
    need(stop["output_bytes"] - start["output_bytes"] <= 67_108_864, "total counted reader mutant package cap")
    need(same(start["requested_by_component"], stop["requested_by_component"])
         and start["generator_constructions"] == stop["generator_constructions"], "reader controls drew samples")
    return {"schema": "m194g-independent-noise-reader-controls-v1", "method": METHOD,
            "status": "PASS_INDEPENDENT_NOISE_READER_CONTROLS" if all(c["pass"] for c in checks) else "UNCOMMISSIONED_NOISE_READER_CONTROLS",
            "actual_full_entry_companion_sha256": sha(canonical(genuine_result)),
            "check_count": len(checks), "checks": checks, "metadata_mutant_bytes": written_metadata,
            "actual_control_output_bytes": stop["output_bytes"] - start["output_bytes"],
            "work_before": start, "work_after": stop,
            "scope": "retained actual trace/file/value/entry controls; no additional random calls"}
