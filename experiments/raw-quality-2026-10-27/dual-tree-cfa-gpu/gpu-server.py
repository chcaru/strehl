"""Literal f32 CUDA execution of the frozen native CFA dual-tree consumer.

Independently written from this repo's frozen CPU algorithm/published filter
facts. No third-party DTCWT implementation or coefficient asset is imported.
Binary stdin/stdout only. Rust retains all original u16 data and noise/gather.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import sys
import time
import traceback
import types

LIMIT = 24 * 1024**3
CPU_TRANSFORM = "d49b6fe8ae336e2e25c3df506e38756201ad86ac7365543037b1390bc9598c65"
CPU_CONSUMER = "eb6a51dbee5e65af9aec06c8e9e8a12dc4d29784572caa835c522df4029391e6"
ORDERED_FIR_HELPER_SHA256 = "16688f2bf6b555c2fe5c90e4d141415ddc0b59d0d7574f847f55a13bbd715dce"
EXPONENT_BITS = [1090519040, 1090519040, 1089854661, 1085250994,
                 1081794887, 1077097267, 1073741824]
FIRST_LOW = [
    [0., -.08838834, .08838834, .69587998, .69587998,
     .08838834, -.08838834, .01122679, .01122679, 0.],
    [.01122679, .01122679, -.08838834, .08838834, .69587998,
     .69587998, .08838834, -.08838834, 0., 0.],
]
FIRST_HIGH = [
    [0., -.01122679, .01122679, .08838834, .08838834,
     -.69587998, .69587998, -.08838834, -.08838834, 0.],
    [0., 0., -.08838834, -.08838834, .69587998,
     -.69587998, .08838834, .08838834, .01122679, -.01122679],
]
Q14 = [.00325314, -.00388321, .03466035, -.03887280, -.11720389,
       .27529538, .75614564, .56881042, .01186609, -.10671180,
       .02382538, .01702522, -.00543948, -.00455690]
SQRT_HALF_BITS = 0x3f3504f3


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def exact(stream, count):
    need(isinstance(count, int) and 0 <= count <= 16 * 4096 * 4096 * 4,
         "invalid bounded payload length")
    data = bytearray(count)
    view = memoryview(data)
    offset = 0
    while offset < count:
        got = stream.readinto(view[offset:])
        need(got is not None and got > 0, "truncated input")
        offset += got
    return data


def read_header(stream):
    length = struct.unpack("<I", exact(stream, 4))[0]
    need(0 < length <= 262144, "invalid JSON header length")
    def invalid(value):
        raise RuntimeError("nonfinite JSON constant: " + value)
    result = json.loads(exact(stream, length), parse_constant=invalid)
    need(isinstance(result, dict), "object header required")
    return result


def write_header(stream, value):
    data = json.dumps(value, allow_nan=False, separators=(",", ":")).encode()
    need(len(data) <= 262144, "response header exceeds bound")
    stream.write(struct.pack("<I", len(data)))
    stream.write(data)
    stream.flush()


def keyset(value, required, optional=()):
    need(set(required) <= set(value) and set(value) <= set(required) | set(optional),
         "header keys differ: " + repr(sorted(value)))


class Worker:
    def __init__(self, start, limit):
        import numpy as np
        import torch
        import torch.nn.functional as F
        self.np, self.torch, self.F = np, torch, F
        keyset(start, ("op", "schema", "width", "height", "wb", "exponents",
                       "device_limit_bytes", "debug"),
               ("floor_foil", "cpu_transform_sha256", "cpu_consumer_sha256"))
        need(start["op"] == "start" and start["schema"] == 1, "schema1 start required")
        self.w, self.h = start["width"], start["height"]
        need(type(self.w) is int and type(self.h) is int
             and 1 <= self.w <= 4096 and 1 <= self.h <= 4096, "phase shape bound")
        need(limit == LIMIT == start["device_limit_bytes"], "fixed device cap differs")
        self.limit = limit
        self.debug = start["debug"]
        self.floor_foil = start.get("floor_foil", False)
        need(type(self.debug) is bool and type(self.floor_foil) is bool,
             "boolean debug/foil required")
        need(not self.debug or (self.w <= 128 and self.h <= 128), "debug extent bound")
        need(not self.floor_foil or self.debug, "floor foil only in debug")
        for key, expected in [("cpu_transform_sha256", CPU_TRANSFORM),
                              ("cpu_consumer_sha256", CPU_CONSUMER)]:
            need(start.get(key, expected) == expected, "frozen CPU binding differs")
        wb = start["wb"]
        need(len(wb) == 3 and all(math.isfinite(x) and x > 0 for x in wb), "WB requires3finitepositive")
        self.exponents = [f32(v) for v in start["exponents"]]
        need([bits(v) for v in self.exponents] == EXPONENT_BITS, "CPU exponent bits differ")
        need(torch.cuda.is_available(), "CUDA required; no CPU fallback")
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        torch.set_default_dtype(torch.float32)
        torch.set_grad_enabled(False)
        need(not torch.is_autocast_enabled(), "CUDA autocast must be disabled")
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.set_float32_matmul_precision("highest")
        torch.cuda.set_device(0)
        properties = torch.cuda.get_device_properties(0)
        need(properties.total_memory >= limit, "device smaller than fixed memory cap")
        torch.cuda.set_per_process_memory_fraction(limit / properties.total_memory, 0)
        torch.cuda.reset_peak_memory_stats(0)
        self.mw = 2 * ((self.w + 127) // 128) * 128
        self.mh = 2 * ((self.h + 127) // 128) * 128
        self.shapes = [(self.mw >> (k + 1), self.mh >> (k + 1)) for k in range(7)]
        self.coefficient_floats = sum(12 * w * h for w, h in self.shapes)
        self.low_floats = 4 * self.shapes[-1][0] * self.shapes[-1][1]
        self.s = struct.unpack("<f", struct.pack("<I", SQRT_HALF_BITS))[0]
        wb_gpu = torch.tensor(wb, dtype=torch.float32, device="cuda")
        gains = torch.stack((wb_gpu[0] / wb_gpu[1], wb_gpu.new_tensor(1.),
                             wb_gpu.new_tensor(1.), wb_gpu[2] / wb_gpu[1]))
        self.gains2 = gains * gains
        self.index_cache = {}
        self.filter_cache = {}
        self.num = [torch.zeros((4, 6, 2, h, w), device="cuda", dtype=torch.float32)
                    for w, h in self.shapes]
        self.den = self.scalars()
        self.scale = self.scalars()
        self.mean = torch.zeros((4, self.h, self.w), dtype=torch.float32, device="cuda")
        self.low = torch.full_like(self.mean, float("inf"))
        self.high = torch.full_like(self.mean, float("-inf"))
        self.ids = []
        self.active = None
        self.current = None
        self.next_draw = 0
        self.pair_a = None
        self.energy = None
        self.variance = None
        self.probe_seconds = 0.
        self.current_started = 0.
        self.source_records = []
        self.device_name = properties.name
        self.device_total = properties.total_memory
        helper_path = Path(__file__).with_name("ordered-fir.py")
        helper_bytes = helper_path.read_bytes()
        need(hashlib.sha256(helper_bytes).hexdigest() == ORDERED_FIR_HELPER_SHA256,
             "ordered FIR helper binding differs")
        helper = types.ModuleType("strehl_ordered_fir")
        helper.__file__ = str(helper_path)
        # Execute the exact bytes just hashed; do not import an unbound pyc.
        exec(compile(helper_bytes, str(helper_path), "exec"), helper.__dict__)
        self.ordered_fir = helper.OrderedFir(torch)
        need(self.ordered_fir.helper_sha256 == ORDERED_FIR_HELPER_SHA256,
             "ordered FIR helper changed during initialization")
        self.check_memory()

    def scalars(self):
        return [self.torch.zeros((6, h, w), device="cuda", dtype=self.torch.float32)
                for w, h in self.shapes]

    def check_memory(self):
        t = self.torch
        need(t.cuda.max_memory_allocated(0) <= self.limit
             and t.cuda.max_memory_reserved(0) <= self.limit, "CUDA allocator high-water cap")

    def memory(self, strict=True):
        if strict:
            self.check_memory()
        t = self.torch
        return {"device_limit_bytes": self.limit,
                "peak_allocated_bytes": t.cuda.max_memory_allocated(0),
                "peak_reserved_bytes": t.cuda.max_memory_reserved(0)}

    def finite(self, tensors, label):
        t = self.torch
        need(bool(t.stack([t.isfinite(x).all() for x in tensors]).all().item()),
             "nonfinite " + label)

    def input(self, stream, count, shape):
        data = exact(stream, count * 4)
        a = self.np.frombuffer(data, dtype="<f4")
        need(bool(self.np.isfinite(a).all()), "nonfinite wire payload")
        value = self.torch.from_numpy(a).to(device="cuda", dtype=self.torch.float32).reshape(shape)
        self.check_memory()
        return value

    def indices(self, length, minimum, maximum):
        key = ("periodic", length, minimum, maximum)
        if key not in self.index_cache:
            self.index_cache[key] = self.torch.arange(-maximum, length - minimum,
                device="cuda", dtype=self.torch.int64).remainder(length)
        return self.index_cache[key]

    def filters(self, level, bank_foil=False):
        key = (level == 0, bank_foil)
        if key in self.filter_cache:
            return self.filter_cache[key]
        if level == 0:
            lows = [[f32(v) for v in a] for a in FIRST_LOW]
            highs = [[f32(v) for v in a] for a in FIRST_HIGH]
            if bank_foil:
                lows[0][3] = f32(lows[0][3] * f32(1.01))
            minimum = 0
        else:
            h = [f32(v) for v in Q14]
            lows = [h, list(reversed(h))]
            highs = [[f32((1. if (j-6) % 2 == 0 else -1.) * h[13-j]) for j in range(14)],
                     [f32((-1. if (j-6) % 2 == 0 else 1.) * h[j]) for j in range(14)]]
            minimum = -6
        horizontal, vertical = [], []
        for tree in range(4):
            # conv2d is correlation, so reverse the mathematical FIR taps.
            for a in (lows[tree // 2], highs[tree // 2]):
                horizontal.append(list(reversed(a)))
            for unused_x_branch in range(2):
                for a in (lows[tree % 2], highs[tree % 2]):
                    vertical.append(list(reversed(a)))
        t = self.torch
        length = len(lows[0])
        hx = t.tensor(horizontal, dtype=t.float32, device="cuda").reshape(8, 1, 1, length)
        hy = t.tensor(vertical, dtype=t.float32, device="cuda").reshape(16, 1, length, 1)
        result = hx, hy, minimum, minimum + length - 1
        self.filter_cache[key] = result
        return result

    def extend(self, plane):
        t = self.torch
        def reflected(length, original, padded):
            key = ("reflect", length, original, padded)
            if key not in self.index_cache:
                q = t.arange(length, device="cuda", dtype=t.int64)
                q = t.where(q < padded, q, 2 * padded - 1 - q)
                q = q.remainder(2 * original)
                self.index_cache[key] = t.where(q < original, q, 2 * original - 1 - q)
            return self.index_cache[key]
        y = reflected(self.mh, self.h, self.mh // 2)
        x = reflected(self.mw, self.w, self.mw // 2)
        return plane.index_select(0, y).index_select(1, x)

    def forward(self, plane, bank_foil=False):
        t = self.torch
        need(tuple(plane.shape) == (self.h, self.w), "phase input dimensions")
        current = self.extend(plane)[None, None].expand(1, 4, self.mh, self.mw)
        bands = []
        for k in range(7):
            hx, hy, minimum, maximum = self.filters(k, bank_foil)
            h, w = current.shape[-2:]
            x = self.ordered_fir.horizontal(current, hx, minimum)
            del current
            y = self.ordered_fir.vertical(x, hy, minimum)
            del x
            y = y.reshape(4, 4, h // 2, w // 2)
            current = y[:, 0].unsqueeze(0).contiguous()
            aa, ab, ba, bb = (y[j, 1:] for j in range(4))
            plus_re = (aa - bb) * self.s
            plus_im = (ab + ba) * self.s
            minus_re = (aa + bb) * self.s
            minus_im = (ab - ba) * self.s
            z = t.stack((t.stack((plus_re, plus_im), 1),
                         t.stack((minus_re, minus_im), 1)), 1)
            bands.append(z.reshape(6, 2, h // 2, w // 2))
            del y, aa, ab, ba, bb, plus_re, plus_im, minus_re, minus_im, z
            self.check_memory()
        low = current.squeeze(0)
        self.finite(bands + [low], "forward coefficients")
        return bands, low

    def fold_periodic(self, raw, axis, length, shift):
        # Transpose of periodic extension. No atomic scatter/index_add: fixed
        # wrap order also works when a14tap filter is longer than a coarse axis.
        t = self.torch
        size = raw.shape[axis]
        shape = list(raw.shape)
        shape[axis] = length
        output = t.zeros(shape, dtype=t.float32, device="cuda")
        base = t.arange(length, dtype=t.int64, device="cuda") + shift
        first = -((shift + length - 1) // length)
        last = (size - 1 - shift) // length
        view_shape = [1] * raw.ndim
        view_shape[axis] = length
        for wrap in range(first, last + 1):
            index = base + wrap * length
            mask = ((index >= 0) & (index < size)).to(t.float32).reshape(view_shape)
            part = raw.index_select(axis, index.clamp(0, size - 1))
            output.add_(part * mask)
        return output

    def inverse(self, coefficients, bank_foil=False):
        bands, low = coefficients
        t = self.torch
        self.validate_coefficients(coefficients)
        current = low.unsqueeze(0)
        for k in reversed(range(7)):
            w, h = self.shapes[k]
            z = bands[k].reshape(3, 2, 2, h, w)
            plus, minus = z[:, 0], z[:, 1]
            details = t.stack(((plus[:, 0] + minus[:, 0]) * self.s,
                               (plus[:, 1] + minus[:, 1]) * self.s,
                               (plus[:, 1] - minus[:, 1]) * self.s,
                               (minus[:, 0] - plus[:, 0]) * self.s), 0)
            packed = t.cat((current.squeeze(0).unsqueeze(1), details), 1).reshape(1, 16, h, w)
            hx, hy, minimum, maximum = self.filters(k, bank_foil)
            vertical = self.F.conv_transpose2d(packed, hy, stride=(2, 1), groups=8)
            vertical = self.fold_periodic(vertical, 2, 2 * h, maximum)
            horizontal = self.F.conv_transpose2d(vertical, hx, stride=(1, 2), groups=4)
            current = self.fold_periodic(horizontal, 3, 2 * w, maximum)
            del packed, details, vertical, horizontal, z, plus, minus
            self.check_memory()
        a = current[0]
        output = ((a[0] + a[1]) + (a[2] + a[3])) * 0.25
        output = output[:self.h, :self.w].contiguous()
        self.finite([output], "inverse")
        return output

    def validate_coefficients(self, coefficients):
        bands, low = coefficients
        need(len(bands) == 7 and all(tuple(b.shape) == (6, 2, h, w)
             for b, (w, h) in zip(bands, self.shapes)), "coefficient dimensions")
        w, h = self.shapes[-1]
        need(tuple(low.shape) == (4, h, w), "lowpass dimensions")
        self.finite(bands + [low], "supplied coefficients")

    def coefficient_arrays(self, coefficients):
        bands, low = coefficients
        # Wire is direction,row,column,re/im; tensor math is direction,re/im,row,column.
        return [b.permute(0, 2, 3, 1).contiguous().reshape(-1) for b in bands] + [low.reshape(-1)]

    def parse_coefficients(self, flat):
        bands = []
        at = 0
        for w, h in self.shapes:
            n = 12 * w * h
            bands.append(flat[at:at+n].reshape(6, h, w, 2).permute(0, 3, 1, 2).contiguous())
            at += n
        w, h = self.shapes[-1]
        low = flat[at:].reshape(4, h, w).contiguous()
        return bands, low

    def smooth(self, field):
        # Literal horizontal then vertical clamped5tap, with explicit f32
        # multiply and add per tap; no image/frame axis is convolved.
        t = self.torch
        weights = [1/16, 4/16, 6/16, 4/16, 1/16]
        h, w = field.shape[-2:]
        padded = self.F.pad(field.unsqueeze(0), (2, 2, 0, 0), mode="replicate").squeeze(0)
        horizontal = t.zeros_like(field)
        for j, value in enumerate(weights):
            horizontal.add_(padded[:, :, j:j+w] * value)
        padded = self.F.pad(horizontal.unsqueeze(0), (0, 0, 2, 2), mode="replicate").squeeze(0)
        output = t.zeros_like(field)
        for j, value in enumerate(weights):
            output.add_(padded[:, j:j+h, :] * value)
        return output

    def source(self, index, signal):
        need(self.active is None and type(index) is int and 0 <= index < 299
             and index not in self.ids and len(self.ids) < 299, "source ordinal/state")
        self.active = index
        self.current = signal
        self.current_started = time.monotonic()
        self.energy = self.scalars()
        self.variance = self.scalars()
        self.probe_seconds = 0.
        self.next_draw = 0
        for p in range(4):
            bands, low = self.forward(signal[p])
            for e, z in zip(self.energy, bands):
                e.add_(self.gains2[p] * (z[:, 0] * z[:, 0] + z[:, 1] * z[:, 1]))
            del bands, low
        self.torch.cuda.synchronize()
        self.signal_energy_seconds = time.monotonic() - self.current_started
        self.check_memory()

    def probe(self, index, draw, field):
        need(index == self.active and draw == self.next_draw and 0 <= draw < 16,
             "probe ordinal/draw/state")
        clock = time.monotonic()
        if draw % 2 == 0:
            need(self.pair_a is None, "previous pair not consumed")
            self.pair_a = [self.forward(field[p]) for p in range(4)]
        else:
            need(self.pair_a is not None, "pair A absent")
            for p in range(4):
                b, low = self.forward(field[p])
                a, unused_low = self.pair_a[p]
                for v, aa, bb in zip(self.variance, a, b):
                    dr = aa[:, 0] - bb[:, 0]
                    di = aa[:, 1] - bb[:, 1]
                    q = self.gains2[p] * (dr * dr + di * di)
                    v.add_(q / 16.0)
                self.pair_a[p] = None
                del a, b, low, unused_low, dr, di, q
            self.pair_a = None
        self.next_draw += 1
        self.torch.cuda.synchronize()
        self.probe_seconds += time.monotonic() - clock
        self.check_memory()

    def end_source(self, index):
        need(index == self.active and self.next_draw == 16 and self.pair_a is None,
             "source lacks all16 probe draws")
        t = self.torch
        clock = time.monotonic()
        relative_fields = []
        debug_e, debug_f, debug_w = [], [], []
        counts = []
        for k, (e, v) in enumerate(zip(self.energy, self.variance)):
            e = self.smooth(e)
            floor = 2.0 * self.smooth(v)
            if self.floor_foil:
                floor = floor * 2.0
            self.finite([e, floor], "energy/floor")
            need(bool(((e >= 0).all() & (floor >= 0).all()).item()), "negative energy/floor")
            excess = (e - floor).clamp_min(0.)
            r = excess / floor.clamp_min(1.0) / 64.0
            p = self.exponents[k]
            if p == 1.0:
                weight = r
            elif p == 2.0:
                weight = r * r
            else:
                weight = (p * r.log()).clamp(-80., 80.).exp()
            weight = t.where(excess > 0., weight, t.zeros_like(weight))
            self.finite([weight], "shared weights")
            counts.append((weight > 0.).sum(dim=(1, 2)))
            larger = weight > self.scale[k]
            safe_weight = t.where(larger, weight, t.ones_like(weight))
            factor = t.where(larger, self.scale[k] / safe_weight, t.ones_like(weight))
            self.num[k].mul_(factor[None, :, None])
            self.den[k].mul_(factor)
            self.scale[k] = t.maximum(self.scale[k], weight)
            safe_scale = t.where(self.scale[k] > 0., self.scale[k], t.ones_like(weight))
            relative = t.where(weight > 0., weight / safe_scale, t.zeros_like(weight))
            self.den[k].add_(relative)
            relative_fields.append(relative)
            if self.debug:
                debug_e.append(e.reshape(-1))
                debug_f.append(floor.reshape(-1))
                debug_w.append(weight.reshape(-1))
        self.energy = self.variance = None
        t.cuda.synchronize()
        field_seconds = time.monotonic() - clock
        clock = time.monotonic()
        phase0 = None
        for p in range(4):
            wave = self.forward(self.current[p])
            for num, z, relative in zip(self.num, wave[0], relative_fields):
                num[p].add_(relative[:, None] * z)
            if self.debug and p == 0:
                phase0 = self.coefficient_arrays(wave)
            self.mean[p].add_(self.current[p])
            self.low[p] = t.minimum(self.low[p], self.current[p])
            self.high[p] = t.maximum(self.high[p], self.current[p])
            del wave
            self.check_memory()
        self.finite(self.num + self.den + [self.mean], "accumulators")
        t.cuda.synchronize()
        fold_seconds = time.monotonic() - clock
        self.ids.append(index)
        self.active = None
        self.current = None
        evidence = {"source_index": index, "probe_pairs": 8, "probe_draws": 16,
                    "signal_analyses_per_phase": 2, "probe_analyses_per_phase": 16,
                    "positive_weight_coefficients": t.cat(counts).cpu().tolist(),
                    "signal_energy_seconds": self.signal_energy_seconds,
                    "probe_seconds": self.probe_seconds, "field_seconds": field_seconds,
                    "signal_reanalysis_and_fold_seconds": fold_seconds,
                    "source_seconds": time.monotonic() - self.current_started,
                    "reconstruction_planes_per_shared_field": 4,
                    "real_imaginary_share_weight": True, "floor_foil": self.floor_foil,
                    **self.memory()}
        self.source_records.append(evidence)
        arrays = []
        if self.debug:
            arrays = [("energy", t.cat(debug_e)), ("floor", t.cat(debug_f)),
                      ("raw_weights", t.cat(debug_w)),
                      ("signal_coefficients_phase0", t.cat(phase0))]
        return evidence, arrays

    def finish(self, source_ids):
        need(self.active is None and self.ids and source_ids == self.ids,
             "finish source census/state differs")
        t = self.torch
        clock = time.monotonic()
        mean = self.mean / float(len(self.ids))
        pre, uniform = [], []
        for p in range(4):
            bands, low = self.forward(mean[p])
            uniform.append(self.inverse((bands, low)))
            for k in range(7):
                safe_den = t.where(self.den[k] > 0., self.den[k], t.ones_like(self.den[k]))
                bands[k] = t.where((self.den[k] > 0.)[:, None],
                                   self.num[k][p] / safe_den[:, None], bands[k])
            pre.append(self.inverse((bands, low)))
        pre = t.stack(pre)
        uniform = t.stack(uniform)
        planes = t.maximum(t.minimum(pre, self.high), self.low)
        self.finite([planes, pre, uniform, mean], "final arms")
        t.cuda.synchronize()
        evidence = {"source_count": len(self.ids), "source_ids": self.ids,
                    "input_phase_dimensions": [self.w, self.h],
                    "extended_phase_dimensions": [self.mw, self.mh],
                    "levels": 7, "directions": 6, "real_trees": 4, "CFA_phases": 4,
                    "exponents": self.exponents, "exponent_bits": EXPONENT_BITS,
                    "wb_squared_energy_gains": self.gains2.cpu().tolist(),
                    "fallback_coefficients": t.cat([(d == 0.).sum(dim=(1, 2)) for d in self.den]).cpu().tolist(),
                    "hull_changed_sites": (planes != pre).sum(dim=(1, 2)).cpu().tolist(),
                    "finish_seconds": time.monotonic() - clock,
                    "admission": False, "quality_claim": False, **self.memory()}
        return evidence, [planes, pre, uniform, mean]

    def runtime(self, strict=True):
        t = self.torch
        return {"backend": "torch-cuda-f32", "torch_version": t.__version__,
                "cuda_version": t.version.cuda, "cudnn_version": t.backends.cudnn.version(),
                "device": self.device_name, "device_total_bytes": self.device_total,
                "tf32": False, "autocast": False, "autograd": False, "f16": False,
                "deterministic_algorithms": True, "cudnn_benchmark": False,
                "arithmetic_difference": "forward explicit CPU tap-order f32 multiply/add; unchanged grouped adjoint reductions and device log-exp order still differ from CPU",
                "ordered_fir_helper_sha256": ORDERED_FIR_HELPER_SHA256,
                "ordered_fir": self.ordered_fir.metadata(strict),
                "cpu_transform_sha256": CPU_TRANSFORM, "cpu_consumer_sha256": CPU_CONSUMER,
                "bank": "published first-stage Farras10 and local-signed Q14; literal frozen constants",
                **self.memory(strict)}


def transmit(stream, worker, header, arrays=()):
    # At most final16WH output or bounded debug tensors are transferred. There
    # is no full-size coefficient CPU copy or per-source coefficient hashing.
    total = sum(x.numel() for x in arrays)
    write_header(stream, {"ok": True, **header, "floats": total})
    for value in arrays:
        flat = value.detach().contiguous().reshape(-1)
        # Bounded host copy avoids a temporary16WH byte string at finish.
        for at in range(0, flat.numel(), 1 << 20):
            part = flat[at:at+(1 << 20)].cpu().numpy().astype("<f4", copy=False)
            stream.write(part.tobytes())
    stream.flush()


def main(args):
    need(not args.receipt.exists(), "fresh terminal receipt required")
    need(args.device_limit_bytes == LIMIT, "fixed24GiB cap required")
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    worker = None
    started = time.monotonic()
    receipt = None
    try:
        start = read_header(sys.stdin.buffer)
        worker = Worker(start, args.device_limit_bytes)
        transmit(sys.stdout.buffer, worker, {"op": "start", "schema": 1,
                 "server_sha256": source_sha, "runtime": worker.runtime(),
                 "band_shapes": worker.shapes, "coefficient_floats": worker.coefficient_floats,
                 "low_floats": worker.low_floats})
        while True:
            request = read_header(sys.stdin.buffer)
            op = request.get("op")
            worker.torch.cuda.synchronize()
            clock = time.monotonic()
            if op in ("source", "probe"):
                required = ("op", "index", "floats") + (("draw",) if op == "probe" else ())
                keyset(request, required)
                need(request["floats"] == 4 * worker.w * worker.h, "four-phase payload count")
                field = worker.input(sys.stdin.buffer, request["floats"], (4, worker.h, worker.w))
                if op == "source":
                    worker.source(request["index"], field)
                else:
                    worker.probe(request["index"], request["draw"], field)
                del field
                worker.torch.cuda.synchronize()
                reply = {"op": op, "index": request["index"], "seconds": time.monotonic()-clock,
                         **worker.memory()}
                if op == "probe":
                    reply["draw"] = request["draw"]
                transmit(sys.stdout.buffer, worker, reply)
            elif op == "end-source":
                keyset(request, ("op", "index"))
                evidence, arrays = worker.end_source(request["index"])
                worker.torch.cuda.synchronize()
                transmit(sys.stdout.buffer, worker, {"op": op, "index": request["index"],
                    "source_evidence": evidence, "seconds": time.monotonic()-clock,
                    "arrays": [{"name": name, "floats": value.numel()} for name, value in arrays]},
                    [value for name, value in arrays])
                del arrays
            elif op == "transform":
                keyset(request, ("op", "floats"), ("bank_foil",))
                need(worker.debug and worker.active is None, "transform only bounded idle debug")
                need(request["floats"] == worker.w * worker.h, "one-phase transform payload")
                bank_foil = request.get("bank_foil", False)
                need(type(bank_foil) is bool, "boolean bank foil required")
                field = worker.input(sys.stdin.buffer, request["floats"], (worker.h, worker.w))
                coefficients = worker.forward(field, bank_foil)
                inverse = worker.inverse(coefficients, bank_foil)
                payload = worker.coefficient_arrays(coefficients) + [inverse]
                transmit(sys.stdout.buffer, worker, {"op": op,
                    "coefficient_floats": worker.coefficient_floats, "low_floats": worker.low_floats,
                    "inverse_floats": worker.w * worker.h, "band_shapes": worker.shapes,
                    "bank_foil": bank_foil}, payload)
                del coefficients, inverse, payload, field
            elif op == "inverse":
                keyset(request, ("op", "floats"))
                need(worker.debug and worker.active is None, "inverse only bounded idle debug")
                need(request["floats"] == worker.coefficient_floats + worker.low_floats,
                     "coefficient payload count")
                field = worker.input(sys.stdin.buffer, request["floats"], (request["floats"],))
                result = worker.inverse(worker.parse_coefficients(field))
                transmit(sys.stdout.buffer, worker, {"op": op}, [result])
                del field, result
            elif op in ("finish", "close"):
                if op == "finish":
                    keyset(request, ("op", "source_ids"))
                    evidence, arrays = worker.finish(request["source_ids"])
                else:
                    keyset(request, ("op",))
                    need(worker.debug and worker.active is None, "close only idle debug")
                    evidence, arrays = {}, []
                worker.torch.cuda.synchronize()
                receipt = {"status": "COMPLETE_DUAL_TREE_CUDA_WORKER", "complete": True,
                           "server_sha256": source_sha, "source_count": len(worker.ids),
                           "source_ids": worker.ids, "source_records": worker.source_records,
                           "seconds_before_terminal_transfer": time.monotonic()-started,
                           "finish_evidence": evidence, **worker.runtime()}
                transmit(sys.stdout.buffer, worker, {"op": op, "evidence": evidence,
                         "source_count": len(worker.ids), "source_ids": worker.ids}, arrays)
                receipt["seconds_including_terminal_transfer"] = time.monotonic()-started
                break
            else:
                raise RuntimeError("unknown operation: " + str(op))
            worker.check_memory()
    except BaseException as exc:
        receipt = {"status": "FAILED_DUAL_TREE_CUDA_WORKER", "complete": False,
                   "server_sha256": source_sha, "reason": str(exc),
                   "seconds": time.monotonic()-started}
        if worker is not None:
            receipt.update({"source_count": len(worker.ids), "source_ids": worker.ids,
                            "active_source": worker.active, "next_draw": worker.next_draw,
                            **worker.runtime(strict=False)})
        traceback.print_exc(file=sys.stderr)
        raise
    finally:
        if receipt is not None:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            with args.receipt.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(receipt, stream, allow_nan=False, indent=2)
                stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--device-limit-bytes", required=True, type=int)
    main(parser.parse_args())
