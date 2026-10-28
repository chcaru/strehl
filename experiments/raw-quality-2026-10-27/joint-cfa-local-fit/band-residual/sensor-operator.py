"""Bounded original-photosite band-residual experiment. No import-time jobs."""
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import torch


PHASE_CHANNEL = np.asarray([0, 1, 1, 2], dtype=np.int64)
SQRT_HALF = np.float32(1 / math.sqrt(2))


def _hash(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _finite(value, name):
    if not bool(torch.isfinite(value).all()):
        raise ValueError("nonfinite " + name)
    return value


def _f32(value):
    if torch.is_tensor(value):
        if value.dtype != torch.float32 or value.device.type != "cpu":
            raise ValueError("CPU f32 required")
        return value
    array = np.asarray(value)
    if array.dtype != np.float32:
        raise ValueError("f32 array required")
    return torch.from_numpy(array.copy())


@dataclass
class Config:
    observed_hw: tuple
    shot4: tuple
    read4: tuple
    black4: tuple
    saturation: int
    device: str = "cpu"
    _delivery: object = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self.observed_hw = tuple(int(v) for v in self.observed_hw)
        if len(self.observed_hw) != 2 or not all(4 <= v <= 128 for v in self.observed_hw):
            raise ValueError("observed dimensions must be4..128")
        if self.device != "cpu":
            raise ValueError("first bounded operator is CPU only")
        for name in ("shot4", "read4", "black4"):
            values = tuple(float(v) for v in getattr(self, name))
            if len(values) != 4 or not all(math.isfinite(v) for v in values):
                raise ValueError("four finite noise/level values required")
            if not np.isfinite(np.asarray(values, dtype=np.float32)).all():
                raise ValueError("noise/levels must be representable f32")
            setattr(self, name, values)
        if min(self.shot4) < 0 or min(self.read4) < 0:
            raise ValueError("negative injected noise")
        if (type(self.saturation) is not int or not 0 < self.saturation <= 65535
                or min(self.black4) < 0 or max(self.black4) >= self.saturation):
            raise ValueError("invalid sensor levels")

    @property
    def field_hw(self):
        return tuple(v + 16 for v in self.observed_hw)

    @property
    def output_xywh(self):
        h, w = self.observed_hw
        return (8, 8, w, h)

    def public(self):
        return {"observed_hw": self.observed_hw, "field_hw": self.field_hw,
                "output_xywh": self.output_xywh, "shot4": self.shot4,
                "read_variance_dn2_4": self.read4, "black4": self.black4,
                "saturation": self.saturation, "device": self.device}


@dataclass
class Query:
    original_xy: np.ndarray
    nodes_xy: np.ndarray
    footprint_weights: np.ndarray

    def __post_init__(self):
        xy, nodes, weights = [np.asarray(v) for v in
                             (self.original_xy, self.nodes_xy, self.footprint_weights)]
        if xy.dtype != np.int32 or xy.ndim != 3 or xy.shape[2] != 2:
            raise ValueError("original_xy must be int32 H,W,2")
        h, w = xy.shape[:2]
        if not (4 <= h <= 128 and 4 <= w <= 128) or np.any(xy < 0):
            raise ValueError("original extent/coordinates unsupported")
        yy, xx = np.mgrid[:h, :w]
        expected = np.stack((xx, yy), axis=-1) + xy[0, 0]
        if not np.array_equal(xy, expected):
            raise ValueError("complete contiguous original sensel grid required")
        if (nodes.dtype != np.float64 or nodes.shape != (h, w, 9, 2)
                or not np.isfinite(nodes).all()):
            raise ValueError("finite f64 physical footprint nodes required")
        if (weights.dtype != np.float32 or weights.shape != (9,)
                or not np.isfinite(weights).all() or np.any(weights <= 0)
                or abs(float(weights.sum(dtype=np.float64)) - 1) > 1e-6):
            raise ValueError("positive normalized f32 footprint weights required")
        self.original_xy, self.nodes_xy, self.footprint_weights = [
            np.array(v, copy=True) for v in (xy, nodes, weights)]
        for v in (self.original_xy, self.nodes_xy, self.footprint_weights):
            v.flags.writeable = False

    @property
    def phase(self):
        return ((self.original_xy[..., 1] & 1) * 2
                + (self.original_xy[..., 0] & 1)).astype(np.uint8)


@dataclass
class Source:
    source_id: int
    query: Query
    codes: np.ndarray

    def __post_init__(self):
        codes = np.asarray(self.codes)
        if (type(self.source_id) is not int or codes.dtype != np.uint16
                or codes.shape != self.query.original_xy.shape[:2]):
            raise ValueError("integer source ID and original uint16 H,W required")
        self.codes = codes.copy()
        self.codes.flags.writeable = False


def _axis_weights(coordinates, integer):
    # Independently authored normalized Lanczos3, retained from the prior
    # raw-blur operator. Geometry f64; all interpolation weight arithmetic f32.
    offsets = np.arange(-2, 4, dtype=np.int32)
    distance = (coordinates[:, None] - (integer[:, None] + offsets)).astype(np.float32)
    angle = np.float32(np.pi) * distance
    angle3 = angle / np.float32(3)
    sinc, window = np.ones_like(distance), np.ones_like(distance)
    nonzero = distance != np.float32(0)
    np.divide(np.sin(angle), angle, out=sinc, where=nonzero)
    np.divide(np.sin(angle3), angle3, out=window, where=nonzero)
    weights = sinc * window
    weights[np.abs(distance) >= np.float32(3)] = np.float32(0)
    exact = coordinates == integer
    weights[exact, :] = np.float32(0)
    weights[exact, 2] = np.float32(1)
    weights /= np.sum(weights, axis=1, keepdims=True, dtype=np.float32)
    return weights


def _matrix(nodes, footprint_weights, channels, field_hw):
    h, w = field_hw
    nodes = np.asarray(nodes).reshape(-1, 9, 2)
    n = len(nodes)
    points = nodes.reshape(-1, 2)
    integer = np.floor(points).astype(np.int64)
    if (np.any(integer[:, 0] - 2 < 0) or np.any(integer[:, 1] - 2 < 0)
            or np.any(integer[:, 0] + 3 >= w) or np.any(integer[:, 1] + 3 >= h)):
        raise ValueError("unsupported source footprint/Lanczos support; no extension")
    wx = _axis_weights(points[:, 0], integer[:, 0])
    wy = _axis_weights(points[:, 1], integer[:, 1])
    weights = (wy[:, :, None] * wx[:, None, :]).reshape(n, 9, 36)
    weights *= footprint_weights[None, :, None]
    offsets = np.arange(-2, 4, dtype=np.int64)
    sites = ((integer[:, 1, None, None] + offsets[None, :, None]) * w
             + (integer[:, 0, None, None] + offsets[None, None, :])).reshape(n, 9, 36)
    columns = sites * 3 + np.asarray(channels, dtype=np.int64).reshape(n, 1, 1)
    rows = np.broadcast_to(np.arange(n, dtype=np.int64)[:, None, None], weights.shape)
    indices = np.stack((rows.reshape(-1), columns.reshape(-1)))
    matrix = torch.sparse_coo_tensor(torch.from_numpy(indices),
        torch.from_numpy(weights.reshape(-1).copy()), (n, h * w * 3),
        dtype=torch.float32).coalesce()
    mass = torch.zeros(n, dtype=torch.float32)
    mass.scatter_add_(0, matrix.indices()[0], matrix.values())
    if not bool(torch.isfinite(mass).all()) or bool((mass <= 0).any()):
        raise ValueError("invalid interpolation row mass")
    matrix = torch.sparse_coo_tensor(matrix.indices(),
        matrix.values() / mass[matrix.indices()[0]], matrix.shape,
        dtype=torch.float32).coalesce()
    _finite(matrix.values(), "measurement weights")
    return matrix.to_sparse_csr(), matrix.transpose(0, 1).coalesce().to_sparse_csr()


class Measurement:
    def __init__(self, query, config):
        if query.original_xy.shape[:2] != config.observed_hw:
            raise ValueError("query/config extent mismatch")
        self.query, self.config = query, config
        self.matrix, self.transpose_matrix = _matrix(query.nodes_xy,
            query.footprint_weights, PHASE_CHANNEL[query.phase], config.field_hw)

    def forward(self, x):
        x = _f32(x)
        if tuple(x.shape) != (*self.config.field_hw, 3):
            raise ValueError("latent HWC shape differs")
        return torch.sparse.mm(self.matrix, x.reshape(-1, 1))[:, 0].reshape(
            self.config.observed_hw)

    def adjoint(self, y):
        y = _f32(y)
        if tuple(y.shape) != self.config.observed_hw:
            raise ValueError("original observation shape differs")
        return torch.sparse.mm(self.transpose_matrix, y.reshape(-1, 1))[:, 0].reshape(
            *self.config.field_hw, 3)


def _pair(value, axis, variance=False):
    n = value.shape[axis]
    paired = n // 2
    even = value.index_select(axis, torch.arange(0, 2 * paired, 2))
    odd = value.index_select(axis, torch.arange(1, 2 * paired, 2))
    if variance:
        lo = (even + odd) * np.float32(.5)
        hi = lo.clone()
    else:
        lo = (even + odd) * SQRT_HALF
        hi = (even - odd) * SQRT_HALF
    if n & 1:
        lo = torch.cat((lo, value.narrow(axis, n - 1, 1)), dim=axis)
    return lo, hi


def _unpair(lo, hi, axis, n):
    shape = list(lo.shape)
    shape[axis] = n
    out = torch.empty(shape, dtype=torch.float32)
    pairs = n // 2
    paired_lo = lo.narrow(axis, 0, pairs)
    out.index_copy_(axis, torch.arange(0, pairs * 2, 2), (paired_lo + hi) * SQRT_HALF)
    out.index_copy_(axis, torch.arange(1, pairs * 2, 2), (paired_lo - hi) * SQRT_HALF)
    if n & 1:
        out.narrow(axis, n - 1, 1).copy_(lo.narrow(axis, pairs, 1))
    return out


class HaarPlan:
    def __init__(self, observed_hw, origin_xy=(0, 0)):
        self.observed_hw = tuple(int(v) for v in observed_hw)
        if len(self.observed_hw) != 2 or min(self.observed_hw) < 2:
            raise ValueError("Haar requires a2D original extent")
        self.origin_xy = tuple(int(v) for v in origin_xy)
        self.bands, self.sizes, self._phase = [], [], []
        offset = 0
        for phase in range(4):
            dx = (phase % 2 - self.origin_xy[0]) % 2
            dy = (phase // 2 - self.origin_xy[1]) % 2
            h = len(range(dy, self.observed_hw[0], 2))
            w = len(range(dx, self.observed_hw[1], 2))
            sizes = [(h, w)]
            entries = []
            for level in range(7):
                if min(h, w) < 2:
                    break
                shapes = [(h // 2, (w + 1) // 2), ((h + 1) // 2, w // 2),
                          (h // 2, w // 2)]
                current = []
                for kind, shape in zip(("LH", "HL", "HH"), shapes):
                    count = shape[0] * shape[1]
                    band = dict(phase=phase, level=level, kind=kind, shape=shape,
                                start=offset, end=offset + count)
                    self.bands.append(band)
                    current.append(band)
                    offset += count
                entries.append(current)
                h, w = (h + 1) // 2, (w + 1) // 2
                sizes.append((h, w))
            low = dict(phase=phase, level=len(entries), kind="LL", shape=(h, w),
                       start=offset, end=offset + h * w)
            self.bands.append(low)
            offset += h * w
            self.sizes.append(sizes)
            self._phase.append((dy, dx, entries, low, sizes))
        self.count = offset
        if self.count != self.observed_hw[0] * self.observed_hw[1]:
            raise ValueError("Haar packing not complete")

    def _forward(self, y, variance):
        y = _f32(y)
        if tuple(y.shape) != self.observed_hw:
            raise ValueError("Haar original shape differs")
        values = []
        for dy, dx, entries, _, _ in self._phase:
            current = y[dy::2, dx::2]
            for _ in entries:
                lx, hx = _pair(current, 1, variance)
                ll, lh = _pair(lx, 0, variance)
                hl, hh = _pair(hx, 0, variance)
                values.extend((lh.reshape(-1), hl.reshape(-1), hh.reshape(-1)))
                current = ll
            values.append(current.reshape(-1))
        return torch.cat(values)

    def forward(self, y):
        return self._forward(y, False)

    def variance(self, v):
        v = _f32(v)
        if bool((v < 0).any()):
            raise ValueError("negative original variance")
        return self._forward(v, True)

    def inverse(self, coefficients):
        coefficients = _f32(coefficients)
        if coefficients.ndim != 1 or coefficients.numel() != self.count:
            raise ValueError("Haar coefficient count differs")
        out = torch.empty(self.observed_hw, dtype=torch.float32)
        for dy, dx, entries, low, sizes in self._phase:
            current = coefficients[low["start"]:low["end"]].reshape(low["shape"])
            for k in range(len(entries) - 1, -1, -1):
                detail = [coefficients[b["start"]:b["end"]].reshape(b["shape"])
                          for b in entries[k]]
                lh, hl, hh = detail
                h, w = sizes[k]
                lx = _unpair(current, lh, 0, h)
                hx = _unpair(hl, hh, 0, h)
                current = _unpair(lx, hx, 1, w)
            out[dy::2, dx::2] = current
        return out


def integrate_reference(x, config):
    x = _f32(x)
    if tuple(x.shape) != (*config.field_hw, 3):
        raise ValueError("delivery latent shape differs")
    if config._delivery is None:
        h, w = config.observed_hw
        yy, xx = np.mgrid[:h, :w]
        centers = np.stack((xx.ravel() + 8, yy.ravel() + 8), axis=1).astype(np.float64)
        axis = np.asarray([-math.sqrt(3 / 5) / 2, 0, math.sqrt(3 / 5) / 2])
        oy, ox = np.meshgrid(axis, axis, indexing="ij")
        offsets = np.stack((ox.ravel(), oy.ravel()), axis=1)
        a = np.asarray([5 / 18, 4 / 9, 5 / 18], dtype=np.float32)
        weight = (a[:, None] * a[None, :]).reshape(9)
        nodes = np.repeat(centers[:, None, :] + offsets[None, :, :], 3, axis=0)
        channels = np.tile(np.arange(3, dtype=np.int64), len(centers))
        config._delivery = _matrix(nodes, weight, channels, config.field_hw)[0]
    return torch.sparse.mm(config._delivery, x.reshape(-1, 1))[:, 0].reshape(
        *config.observed_hw, 3)


@dataclass
class SquaredNorm:
    mantissa: torch.Tensor
    exponent: int

    @property
    def is_zero(self):
        return float(self.mantissa) == 0

    def ratio(self, other):
        if other.is_zero:
            raise ValueError("zero squared-norm denominator")
        return torch.ldexp(self.mantissa / other.mantissa,
                           torch.tensor(self.exponent - other.exponent, dtype=torch.int32))

    def root_ratio(self, other):
        if other.is_zero:
            raise ValueError("zero norm denominator")
        delta = self.exponent - other.exponent
        value = torch.sqrt(self.mantissa / other.mantissa)
        if delta % 2:
            value = value * np.float32(math.sqrt(2))
        return torch.ldexp(value, torch.tensor(delta // 2, dtype=torch.int32))

    def scaled(self, factor):
        factor = torch.as_tensor(factor, dtype=torch.float32)
        if factor.ndim != 0 or not bool(torch.isfinite(factor)) or float(factor) <= 0:
            raise ValueError("positive finite f32 norm scale required")
        if self.is_zero:
            return SquaredNorm(self.mantissa.clone(), 0)
        sf, se = torch.frexp(factor)
        mf, me = torch.frexp(self.mantissa * sf)
        return SquaredNorm(mf, self.exponent + int(se) + int(me))

    def le(self, other):
        if self.is_zero:
            return True
        if other.is_zero:
            return False
        return (self.exponent < other.exponent or
                (self.exponent == other.exponent and float(self.mantissa) <= float(other.mantissa)))

    def receipt(self):
        value = torch.ldexp(self.mantissa, torch.tensor(self.exponent, dtype=torch.int32))
        return {"mantissa_f32": float(self.mantissa), "binary_exponent": self.exponent,
                "value_f32": float(value) if bool(torch.isfinite(value)) else None,
                "nonzero": not self.is_zero}


def norm_pair(value):
    """Stable f32 squared norm; never square an unscaled image/gradient."""
    values = value if isinstance(value, (list, tuple)) else [value]
    if not values:
        raise ValueError("empty norm input")
    values = [_finite(_f32(v), "norm input") for v in values]
    maximum = torch.stack([v.abs().max() for v in values]).max()
    if float(maximum) == 0:
        return SquaredNorm(torch.tensor(0, dtype=torch.float32), 0)
    total = torch.tensor(0, dtype=torch.float32)
    for v in values:
        total = total + (v / maximum).square().sum(dtype=torch.float32)
    mf, me = torch.frexp(maximum)
    sf, se = torch.frexp(mf.square() * total)
    _finite(sf, "scaled squared norm")
    return SquaredNorm(sf, 2 * int(me) + int(se))


def _smooth3(value):
    h, w = value.shape
    yi = torch.arange(-1, h + 1).clamp(0, h - 1)
    xi = torch.arange(-1, w + 1).clamp(0, w - 1)
    padded = value[yi[:, None], xi[None, :]]
    out = torch.zeros_like(value)
    for y in range(3):
        for x in range(3):
            out = out + padded[y:y + h, x:x + w]
    return out / np.float32(9)


def _admission(d, variance, plan, mode):
    admission = torch.ones_like(d)
    if mode == "no-focus":
        return admission
    if mode == "full-value":
        energy = torch.tensor(0, dtype=torch.float32)
        noise = torch.tensor(0, dtype=torch.float32)
        count = 0
        for band in plan.bands:
            if band["kind"] == "LL":
                continue
            a, b = band["start"], band["end"]
            energy = energy + d[a:b].square().sum(dtype=torch.float32)
            noise = noise + variance[a:b].sum(dtype=torch.float32)
            count += b - a
        scalar = ((energy - 2 * noise).clamp_min(0)
                  / (64 * noise.clamp_min(count))).square().clamp_min(np.float32(1e-4))
        _finite(scalar, "full-value admission")
        return admission * scalar
    if mode != "candidate":
        raise ValueError("unknown admission mode")
    for band in plan.bands:
        if band["kind"] == "LL":
            continue
        a, b = band["start"], band["end"]
        energy = _smooth3(d[a:b].reshape(band["shape"]).square())
        floor = _smooth3(variance[a:b].reshape(band["shape"]))
        value = ((energy - 2 * floor).clamp_min(0)
                 / (64 * floor.clamp_min(1))).square().clamp_min(np.float32(1e-4))
        admission[a:b] = value.reshape(-1)
    return _finite(admission, "band admission")


class Problem:
    def __init__(self, sources, config, mode="candidate", metric_override=None):
        sources = tuple(sources)
        if not 1 <= len(sources) <= 7 or len({v.source_id for v in sources}) != len(sources):
            raise ValueError("one..seven distinct source IDs required")
        if mode not in ("candidate", "no-focus", "full-value"):
            raise ValueError("unknown admission mode")
        if metric_override is not None:
            override = np.float32(metric_override)
            if not np.isfinite(override) or override <= 0:
                raise ValueError("total metric override must be positive finite f32")
        else:
            override = None
        self.sources, self.config, self.mode = sources, config, mode
        self.count = sum(source.codes.size for source in sources)
        self.source_operators, self.observations, self.variances = [], [], []
        self.metrics, self.admissions, self._band_observations = [], [], []
        source_evidence = []
        # Preserve original-u16 source storage. Convert only the current source
        # to signed DN for the fixed original-phase observations and statistics.
        for source in sources:
            if source.codes.shape != config.observed_hw:
                raise ValueError("source/config dimensions differ")
            if np.any(source.codes >= config.saturation):
                raise ValueError("clipped source unsupported by this discriminator")
            measurement = Measurement(source.query, config)
            plan = HaarPlan(config.observed_hw, tuple(source.query.original_xy[0, 0]))
            phase = torch.from_numpy(source.query.phase.astype(np.int64))
            black = torch.tensor(config.black4, dtype=torch.float32)[phase]
            shot = torch.tensor(config.shot4, dtype=torch.float32)[phase]
            read = torch.tensor(config.read4, dtype=torch.float32)[phase]
            observed = torch.from_numpy(source.codes.astype(np.float32)) - black
            # Exact supplied NoiseModel variance. u16 rounding is a disclosed
            # acquisition approximation, not a private +1/12 model amendment.
            original_variance = _finite(shot * observed.clamp_min(0) + read, "original variance")
            d = _finite(plan.forward(observed), "original Haar coefficients")
            variance = _finite(plan.variance(original_variance), "Haar marginal variance")
            admission = _admission(d, variance, plan, mode)
            metric = admission / variance.clamp_min(1)
            if override is not None:
                metric = torch.full_like(metric, float(override))
            _finite(metric, "total metric")
            if bool((metric <= 0).any()):
                raise ValueError("nonpositive/underflowed total metric")
            self.source_operators.append((measurement, plan))
            self.observations.append(observed)
            self.variances.append(variance)
            self.admissions.append(admission)
            self.metrics.append(metric)
            self._band_observations.append(d)
            source_evidence.append({"source_id": source.source_id,
                "original_u16_sha256": _hash(source.codes),
                "original_xy_sha256": _hash(source.query.original_xy),
                "footprint_nodes_sha256": _hash(source.query.nodes_xy),
                "footprint_weights_sha256": _hash(source.query.footprint_weights),
                "phase_origin_xy": [int(v) for v in source.query.original_xy[0, 0]],
                "physical_phase_order": ["R", "G1", "G2", "B"],
                "actual_phase_level_sizes": plan.sizes,
                "sparse_A_nonzeros_including_zero_taps": measurement.matrix.values().numel(),
                "metric_min": float(metric.min()), "metric_max": float(metric.max()),
                "metric_sha256": _hash(metric.numpy()),
                "admission_min": float(admission.min()), "admission_max": float(admission.max())})
        self.metric_scale = torch.stack([q.max() for q in self.metrics]).max()
        _finite(self.metric_scale, "common metric scale")
        sqrt_scale = torch.sqrt(self.metric_scale)
        sqrt_count = torch.sqrt(torch.tensor(self.count, dtype=torch.float32))
        self.factors = [(torch.sqrt(q) / sqrt_scale) / sqrt_count for q in self.metrics]
        for factor in self.factors:
            _finite(factor, "weighted operator factor")
            if bool((factor <= 0).any()):
                raise ValueError("positive total metric lost to f32 factor underflow")
        self.rhs = [_finite(r * d, "weighted RHS")
                    for r, d in zip(self.factors, self._band_observations)]
        self.evidence = {"config": config.public(), "mode": mode,
            "metric_override": None if override is None else float(override),
            "source_count": len(sources), "sources": source_evidence,
            "original_sensel_count": self.count, "metric_scale_f32": float(self.metric_scale),
            "objective": "sum(q*(H(Ax-y))^2)/N; solver divides all q by one max(q)",
            "factor": "(sqrt(q)/sqrt(global_max_q))/sqrt(N)",
            "latent_coefficients": int(np.prod(config.field_hw) * 3),
            "apron_pixels": int(np.prod(config.field_hw) - np.prod(config.observed_hw)),
            "full_latent_is_free": True, "rank_or_identifiability_established": False,
            "prior": None, "blur_fit": False, "per_source_rgb": False,
            "source_storage": "original uint16 CFA; one signed f32 original-domain observation per source",
            "sparse_cache_policy": "all small source A and transpose matrices retained; not full-image streaming",
            "noise": "exact supplied phase variance; no added quantization variance",
            "covariance": "Haar marginal diagonal only; omitted siblings are not asserted independent",
            "admission": False, "quality_claim": False}

    def forward(self, x):
        return [factor * plan.forward(measurement.forward(x))
                for factor, (measurement, plan) in zip(self.factors, self.source_operators)]

    def adjoint(self, coefficients):
        if len(coefficients) != len(self.source_operators):
            raise ValueError("weighted transpose source count differs")
        out = torch.zeros((*self.config.field_hw, 3), dtype=torch.float32)
        for value, factor, (measurement, plan) in zip(coefficients, self.factors, self.source_operators):
            out = out + measurement.adjoint(plan.inverse(_f32(value) * factor))
        return out

    def residual(self, x):
        return [b - value for b, value in zip(self.rhs, self.forward(x))]

    def objective(self, x):
        scaled = norm_pair(self.residual(x))
        return {"scaled": scaled.receipt(), "original": scaled.scaled(self.metric_scale).receipt()}


def prepare(sources, config, mode="candidate", metric_override=None):
    return Problem(sources, config, mode, metric_override)


@dataclass
class FitResult:
    x: torch.Tensor
    output: torch.Tensor
    status: str
    converged: bool
    iterations: int
    history: list
    evidence: dict

    def save(self, out_dir):
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=False)
        _finite(self.x, "saved latent")
        _finite(self.output, "saved delivered output")
        np.save(out / "latent.npy", self.x.detach().numpy(), allow_pickle=False)
        np.save(out / "output.npy", self.output.detach().numpy(), allow_pickle=False)
        receipt = {"status": self.status, "converged": self.converged,
            "iterations": self.iterations, "history": self.history, "evidence": self.evidence,
            "latent": {"path": str((out / "latent.npy").resolve()),
                       "sha256": hashlib.sha256((out / "latent.npy").read_bytes()).hexdigest()},
            "output": {"path": str((out / "output.npy").resolve()),
                       "sha256": hashlib.sha256((out / "output.npy").read_bytes()).hexdigest()},
            "admission": False, "quality_claim": False}
        (out / "result.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return receipt


def fit(problem):
    """Fixed64-step f32 CGLS, no prior/restart/private variance/implicit clamp."""
    x = torch.zeros((*problem.config.field_hw, 3), dtype=torch.float32)
    residual = [v.clone() for v in problem.rhs]
    gradient = _finite(problem.adjoint(residual), "initial normal residual")
    direction = gradient.clone()
    initial_normal = norm_pair(gradient)
    gamma = initial_normal
    initial_objective = norm_pair(residual)
    previous_objective = initial_objective
    monotonic = True
    history = [{"iteration": 0, "scaled_objective": initial_objective.receipt(),
                "original_objective": initial_objective.scaled(problem.metric_scale).receipt(),
                "true_relative_normal_residual": 0.0 if initial_normal.is_zero else 1.0}]
    iterations = 0
    status = "zero-initial-normal-residual" if initial_normal.is_zero else "iteration-cap"
    reached = initial_normal.is_zero
    forward_calls, adjoint_calls = 0, 1
    for iteration in range(1, 65):
        if reached:
            break
        try:
            projected = problem.forward(direction)
            forward_calls += 1
            delta = norm_pair(projected)
            if delta.is_zero:
                status = "zero-projected-direction"
                break
            alpha = gamma.ratio(delta)
            if not bool(torch.isfinite(alpha)) or float(alpha) <= 0:
                status = "nonfinite-or-underflowed-step"
                break
            candidate = _finite(x + alpha * direction, "candidate iterate")
            recursive = [_finite(r - alpha * p, "recursive residual")
                         for r, p in zip(residual, projected)]
            # Independent true residual/normal for the recorded gates. Do not
            # replace recursive CGLS residual or direction with these checks.
            true_residual = problem.residual(candidate)
            forward_calls += 1
            true_normal = problem.adjoint(true_residual)
            adjoint_calls += 1
            objective = norm_pair(true_residual)
            relative = norm_pair(true_normal).root_ratio(initial_normal)
            _finite(relative, "true relative normal residual")
            monotonic = monotonic and objective.le(previous_objective)
            x = candidate
            iterations = iteration
            history.append({"iteration": iteration, "alpha_f32": float(alpha),
                "scaled_objective": objective.receipt(),
                "original_objective": objective.scaled(problem.metric_scale).receipt(),
                "true_relative_normal_residual": float(relative),
                "objective_nonincreasing_so_far": monotonic})
            previous_objective = objective
            if float(relative) <= 1e-5:
                reached = True
                status = "normal-residual-converged" if monotonic else "objective-increased"
                break
            new_gradient = problem.adjoint(recursive)
            adjoint_calls += 1
            new_gamma = norm_pair(new_gradient)
            if new_gamma.is_zero:
                status = "recursive-zero-with-nonzero-true-normal"
                break
            beta = new_gamma.ratio(gamma)
            if not bool(torch.isfinite(beta)) or float(beta) <= 0:
                status = "nonfinite-or-underflowed-conjugate-step"
                break
            direction = _finite(new_gradient + beta * direction, "CGLS direction")
            residual, gamma = recursive, new_gamma
        except ValueError as error:
            status = "numeric-refusal: " + str(error)
            break
    if status == "iteration-cap" and not monotonic:
        status = "iteration-cap-and-objective-increased"
    output = _finite(integrate_reference(x, problem.config), "delivered output")
    evidence = dict(problem.evidence)
    evidence.update({"maximum_iterations": 64, "normal_tolerance": 1e-5,
        "initialization": "zero", "restarts": 0, "recursive_residual_replaced": False,
        "normal_norm": "max-rescaled f32 sum with integer binary exponent",
        "objective_nonincreasing": monotonic, "finite_last_iterate_retained": True,
        "weighted_forward_calls": forward_calls, "weighted_adjoint_calls": adjoint_calls,
        "reference_cell_delivery_count": 1,
        "source_bytes_unchanged": all(_hash(source.codes) == item["original_u16_sha256"]
            for source, item in zip(problem.sources, problem.evidence["sources"]))})
    return FitResult(x, output, status, bool(reached and monotonic), iterations, history, evidence)
