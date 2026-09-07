"""Polar radial/angle and clipped-triangle cell integration, M194e only."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
import math
from pathlib import Path
import time
import weakref

import numpy as np

from model import file_ref, write_json


class NumericalFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class Integrator:
    arm: str = "primary"
    angle_low: int = 16
    angle_high: int = 32
    cell_low: int = 4
    cell_high: int = 8
    pupil_tolerance: float = .00025
    cell_tolerance: float = .00075
    angle_depth: int = 10
    cell_depth: int = 6
    point_limit: int = 4_000_000
    angular_limit: int = 600_000_000
    cpu_limit: float = 600
    wall_limit: float = 1200
    array_limit: int = 32 * 1024 * 1024
    node_pair_limit: int = 32768

    def __post_init__(self):
        for name in ("angle_low", "angle_high", "cell_low", "cell_high", "point_limit", "angular_limit", "array_limit", "node_pair_limit"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                raise ValueError(f"positive integer required: {name}")
        for name in ("angle_depth", "cell_depth"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise ValueError(f"nonnegative integer required: {name}")
        for name in ("pupil_tolerance", "cell_tolerance", "cpu_limit", "wall_limit"):
            v = getattr(self, name)
            if isinstance(v, bool) or not math.isfinite(v) or v <= 0:
                raise ValueError(f"finite positive value required: {name}")


def integrator_for(arm):
    if arm == "primary":
        return Integrator()
    if arm == "angle-refined":
        return Integrator(arm=arm, angle_low=32, angle_high=64, pupil_tolerance=.00025 / 4)
    if arm == "cell-refined":
        return Integrator(arm=arm, cell_low=8, cell_high=16, cell_tolerance=.00075 / 4)
    raise ValueError("unregistered integration arm")


class Meter:
    """Counts owned arrays, not hidden ufunc buffers or RSS; counters never set quadrature."""

    def __init__(self, integrator, observer="count"):
        if observer not in ("off", "count", "placebo"):
            raise ValueError("unknown observer")
        self.config = integrator
        self.observer = observer
        self.started_cpu, self.started_wall = time.process_time(), time.monotonic()
        self.points = self.nodes = self.peak_pairs = self.peak_bytes = self.peak_arrays = 0
        self.frame_refs = []
        self.peak_frames = 0
        self.observer_events = 0
        self.optional_hook_calls = 0
        self.arrays = {}

    def _optional_observe(self, arrays):
        self.optional_hook_calls += 1
        if self.observer == "count":
            # Collection occurs only in count mode. Placebo traverses the same
            # optional hook and returns without collecting the statistic.
            self.observer_events += sum(isinstance(a, np.ndarray) for a in arrays)

    def watch(self, *arrays):
        # The storage bound is checked in every observer mode. Optional event
        # counting is the observer under the byte-null/placebo control.
        if self.observer != "off":
            self._optional_observe(arrays)
        for value in arrays:
            if isinstance(value, np.ndarray):
                base = value
                while isinstance(base.base, np.ndarray):
                    base = base.base
                self.arrays[id(base)] = (weakref.ref(base), base.nbytes)
        self.arrays = {k: v for k, v in self.arrays.items() if v[0]() is not None}
        self.peak_bytes = max(self.peak_bytes, sum(v[1] for v in self.arrays.values()))
        self.peak_arrays = max(self.peak_arrays, len(self.arrays))
        if self.peak_bytes > self.config.array_limit:
            raise NumericalFailure("UNCOMMISSIONED_NUMERICS: tracked ndarray byte ceiling")

    def frame(self, array):
        self.frame_refs = [r for r in self.frame_refs if r() is not None]
        self.frame_refs.append(weakref.ref(array))
        self.peak_frames = max(self.peak_frames, len(self.frame_refs))
        self.watch(array)
        if len(self.frame_refs) > 1:
            raise NumericalFailure("UNCOMMISSIONED_NUMERICS: more than one scalar frame retained")

    def check(self, points=0, nodes=0, pairs=0):
        self.points += points
        self.nodes += nodes
        self.peak_pairs = max(self.peak_pairs, pairs)
        c = self.config
        if self.points > c.point_limit or self.nodes > c.angular_limit or self.peak_pairs > c.node_pair_limit:
            raise NumericalFailure("UNCOMMISSIONED_NUMERICS: evaluation ceiling")
        if time.process_time() - self.started_cpu > c.cpu_limit or time.monotonic() - self.started_wall > c.wall_limit:
            raise NumericalFailure("UNCOMMISSIONED_NUMERICS: own-process time ceiling")

    def new_frame(self):
        self.points = self.nodes = 0
        self.check()

    def receipt(self):
        return dict(point_calls=self.points, angular_nodes=self.nodes, peak_node_pairs=self.peak_pairs,
                    tracked_peak_ndarray_bytes=self.peak_bytes, tracked_peak_ndarrays=self.peak_arrays,
                    peak_live_scalar_frames=self.peak_frames, observer=self.observer, observer_events=self.observer_events,
                    optional_hook_calls=self.optional_hook_calls,
                    cpu_seconds=time.process_time() - self.started_cpu, wall_seconds=time.monotonic() - self.started_wall)


@lru_cache(maxsize=16)
def gauss(order):
    x, w = np.polynomial.legendre.leggauss(order)
    return (x + 1) / 2, w / 2


def cosine_radial(phi, beta, lo, hi, meter=None):
    """Integral of r*cos(phi+beta*r), stable at beta=0 and zero width."""
    m, h = (hi + lo) / 2, (hi - lo) / 2
    z = beta * h
    small = np.abs(z) < .01
    z2 = z * z
    sinc_series = 1 + z2 * (-1 / 6 + z2 * (1 / 120 + z2 * (-1 / 5040 + z2 / 362880)))
    d_series = z * (1 / 3 + z2 * (-1 / 30 + z2 * (1 / 840 + z2 * (-1 / 45360 + z2 / 3991680))))
    safe = np.where(small, 1, z)
    sinc = np.where(small, sinc_series, np.sin(z) / safe)
    d = np.where(small, d_series, (np.sin(z) - z * np.cos(z)) / (safe * safe))
    phase = phi + beta * m
    result = 2 * m * h * sinc * np.cos(phase) - 2 * h * h * d * np.sin(phase)
    if meter is not None:
        meter.watch(phi, beta, lo, hi, m, h, z, small, z2, sinc_series, d_series, safe, sinc, d, phase, result)
    return result


def field_radial(field, q0, direction, displacement, lo, hi, meter):
    c = field.constant + field.affine[0] * q0[..., 0] + field.affine[1] * q0[..., 1]
    if np.all(np.equal(lo, hi)) and np.all(c > 0):
        # Zero radial area is exactly +0 in the original positive-DC evaluation,
        # including signed wave/affine terms. The c>0 guard keeps signed-zero
        # behavior for other component inputs on the original arithmetic path.
        value = np.zeros(np.broadcast_shapes(c.shape, direction.shape[:-1], np.shape(lo), np.shape(hi)))
        meter.watch(q0, direction, lo, hi, c, value)
        return value
    slope = displacement * (field.affine[0] * direction[..., 0] + field.affine[1] * direction[..., 1])
    value = c * (hi * hi - lo * lo) / 2 + slope * (hi**3 - lo**3) / 3
    meter.watch(q0, direction, lo, hi, c, slope, value)
    for wave in field.waves:
        phi = 2 * np.pi * (wave.frequency[0] * q0[..., 0] + wave.frequency[1] * q0[..., 1]) + wave.phase
        beta = 2 * np.pi * displacement * (wave.frequency[0] * direction[..., 0] + wave.frequency[1] * direction[..., 1])
        meter.watch(phi, beta, value)
        value = value + wave.amplitude * cosine_radial(phi, beta, lo, hi, meter)
        meter.watch(value)
    return value


def native_mask(scene, frame):
    matrix = frame.forward_similarity.inverse_matrix()
    n = matrix.T @ np.array(scene.mask_normal)
    origin = frame.forward_similarity.inverse(np.array((0., 0.)))
    offset = scene.mask_offset - np.dot(scene.mask_normal, origin)
    return n, offset


def angular_integrand(scene, frame, xy, heights, angles, meter):
    # xy has (interval,2), angles (interval,node); this is the only pupil batch.
    count = angles.size
    meter.check(nodes=count, pairs=count)
    u = np.stack((np.cos(angles), np.sin(angles)), axis=-1)
    direction = u @ frame.forward_similarity.inverse_matrix().T
    q0 = frame.forward_similarity.inverse(xy)[:, None, :]
    df, db = frame.defocus(scene)
    # The exact same represented chief-ray height sets cuts and radial crossing.
    h = heights[:, None]
    slope = df * (direction[..., 0] * scene.mask_normal[0] + direction[..., 1] * scene.mask_normal[1])
    crossing = np.clip(-h / np.where(slope == 0, 1., slope), 0., 1.)
    lo = np.where(slope > 0, crossing, 0.)
    hi = np.where(slope < 0, crossing, 1.)
    lo = np.where((slope == 0) & (h < 0), 1., lo)
    if scene.mask_state == "full":
        lo, hi = np.zeros_like(lo), np.ones_like(hi)
    elif scene.mask_state == "absent":
        lo, hi = np.ones_like(lo), np.ones_like(hi)
    meter.watch(xy, heights, angles, u, direction, q0, h, slope, crossing, lo, hi)
    fg = field_radial(scene.foreground, q0, direction, df, lo, hi, meter)
    meter.watch(fg)
    bg_first = field_radial(scene.background, q0, direction, db, 0., lo, meter)
    meter.watch(bg_first)
    bg = bg_first + field_radial(scene.background, q0, direction, db, hi, 1., meter)
    value = (fg + bg) / np.pi
    meter.watch(xy, angles, u, direction, q0, h, slope, crossing, lo, hi, fg, bg, value)
    if not np.isfinite(value).all():
        raise NumericalFailure("UNCOMMISSIONED_NUMERICS: nonfinite angular evaluation")
    return value


def angular_cuts(height, radius, alpha, mask_state, include_ladder=True):
    """Fixed geometry-only subdivision; no radial mass is omitted."""
    start = alpha - np.pi / 2
    cuts = [start, start + 2 * np.pi]
    if mask_state == "half-plane" and radius and abs(height) < radius:
        cuts.append(start + np.pi)
        if height:
            eta = abs(height) / radius
            sign = 1 if height > 0 else -1
            levels = (1.,) + tuple(2. ** -j for j in range(1, 33)) if include_ladder else (1.,)
            for r in levels:
                if eta < r:
                    delta = math.asin(max(0., min(1., eta / r)))
                    for angle in (alpha + np.pi / 2 + sign * delta, alpha + 3 * np.pi / 2 - sign * delta):
                        cuts.append(start + ((angle - start) % (2 * np.pi)))
    # Only identical floating endpoints coalesce; no tolerance-based snapping.
    return sorted(set(cuts))


def render_points(scene, frame, xy, integrator, meter):
    xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
    if not np.isfinite(xy).all():
        raise ValueError("finite point coordinates required")
    meter.check(points=len(xy))
    n, offset = native_mask(scene, frame)
    df, _ = frame.defocus(scene)
    radius = abs(df) * math.hypot(*n)
    q0 = frame.forward_similarity.inverse(xy)
    h = q0[:, 0] * scene.mask_normal[0] + q0[:, 1] * scene.mask_normal[1] - scene.mask_offset
    # A mask-normal perpendicular is the periodic boundary; crossing directions
    # and the fixed radial ladder resolve narrow visibility boundary layers.
    alpha = math.atan2(n[1] * df, n[0] * df) if df else math.atan2(n[1], n[0])
    start = alpha - np.pi / 2
    ids, left, right = [], [], []
    for j, hj in enumerate(h):
        cuts = angular_cuts(hj, radius, alpha, scene.mask_state)
        for a, b in zip(cuts[:-1], cuts[1:]):
            if b > a:
                ids.append(j)
                left.append(a)
                right.append(b)
    ids, left, right = np.array(ids), np.array(left), np.array(right)
    values, errors = np.zeros(len(xy)), np.zeros(len(xy))
    meter.watch(xy, q0, h, ids, left, right, values, errors)
    budgets = integrator.pupil_tolerance * (right - left) / (2 * np.pi)
    pending = [(ids, left, right, budgets, 0)]
    low_nodes, low_weights = gauss(integrator.angle_low)
    high_nodes, high_weights = gauss(integrator.angle_high)
    chunk = max(1, integrator.node_pair_limit // max(integrator.angle_low, integrator.angle_high))
    while pending:
        ids, left, right, budgets, depth = pending.pop()
        for begin in range(0, len(ids), chunk):
            ix, a, b, budget = ids[begin:begin + chunk], left[begin:begin + chunk], right[begin:begin + chunk], budgets[begin:begin + chunk]
            width = b - a
            low = width * (angular_integrand(scene, frame, xy[ix], h[ix], a[:, None] + width[:, None] * low_nodes, meter) @ low_weights)
            high = width * (angular_integrand(scene, frame, xy[ix], h[ix], a[:, None] + width[:, None] * high_nodes, meter) @ high_weights)
            error = np.abs(high - low)
            good = error <= budget
            np.add.at(values, ix[good], high[good])
            np.add.at(errors, ix[good], error[good])
            meter.watch(xy, values, errors, ids, left, right, budgets, low, high, error, good)
            if not good.all():
                if depth >= integrator.angle_depth:
                    raise NumericalFailure("UNCOMMISSIONED_NUMERICS: angular depth/error ceiling")
                bad = ~good
                mid = (a[bad] + b[bad]) / 2
                if np.any((mid <= a[bad]) | (mid >= b[bad])):
                    raise NumericalFailure("UNCOMMISSIONED_NUMERICS: unresolved unrepresentable angular midpoint")
                pending.append((np.concatenate((ix[bad], ix[bad])), np.concatenate((a[bad], mid)),
                                np.concatenate((mid, b[bad])), np.tile(budget[bad] / 2, 2), depth + 1))
    if not np.isfinite(values).all() or np.any(values < 0) or np.any(errors > integrator.pupil_tolerance * (1 + 1e-12)):
        raise NumericalFailure("UNCOMMISSIONED_NUMERICS: point result/error")
    return values, errors


def render_point(scene, frame, native_xy, integrator=Integrator(), meter=None):
    meter = meter or Meter(integrator)
    values, errors = render_points(scene, frame, np.asarray(native_xy).reshape(1, 2), integrator, meter)
    return float(values[0]), dict(value_error_indicator_e=float(errors[0]), work=meter.receipt())


def clip_polygon(poly, n, offset, positive):
    output = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        ha, hb = np.dot(a, n) - offset, np.dot(b, n) - offset
        inside_a, inside_b = (ha >= 0, hb >= 0) if positive else (ha <= 0, hb <= 0)
        if inside_a:
            output.append(a)
        if inside_a != inside_b:
            output.append(a + (b - a) * (ha / (ha - hb)))
    return output


def cell_triangles(scene, frame, xy):
    x, y = xy
    square = [np.array(p) for p in ((x - .5, y - .5), (x + .5, y - .5), (x + .5, y + .5), (x - .5, y + .5))]
    pieces = [square]
    if scene.mask_state == "half-plane":
        n, offset = native_mask(scene, frame)
        radius = abs(frame.defocus(scene)[0]) * math.hypot(*n)
        for cut in sorted(set((offset, offset - radius, offset + radius))):
            new = []
            for poly in pieces:
                distances = [np.dot(p, n) - cut for p in poly]
                if min(distances) < 0 < max(distances):
                    new.extend((clip_polygon(poly, n, cut, True), clip_polygon(poly, n, cut, False)))
                else:
                    new.append(poly)
            pieces = new
    triangles = []
    for poly in pieces:
        for i in range(1, len(poly) - 1):
            triangle = np.array((poly[0], poly[i], poly[i + 1]))
            if triangle_area(triangle) > 0:
                triangles.append(triangle)
    return triangles


def triangle_area(t):
    a, b = t[1] - t[0], t[2] - t[0]
    return abs(a[0] * b[1] - a[1] * b[0]) / 2


def tangent_indices(t, scene, frame):
    """Select a coordinate map, never move vertices or claim exact incidence."""
    t = np.asarray(t, dtype=np.float64)
    if t.shape != (3, 2) or not np.isfinite(t).all():
        raise NumericalFailure("UNCOMMISSIONED_NUMERICS: finite triangle vertices required")
    if scene.mask_state != "half-plane":
        return ()
    n, offset = native_mask(scene, frame)
    radius = abs(frame.defocus(scene)[0]) * math.hypot(*n)
    if radius == 0:
        return ()
    h = t @ n - offset
    tau = 64 * np.finfo(float).eps * (np.abs(n[0] * t[:, 0]) + np.abs(n[1] * t[:, 1]) + abs(offset) + radius)
    if not np.isfinite(radius) or not np.isfinite(h).all() or not np.isfinite(tau).all():
        raise NumericalFailure("UNCOMMISSIONED_NUMERICS: nonfinite cell-map predicate")
    alternatives = []
    for sign in (-1, 1):
        distance = np.abs(h - sign * radius)
        if not np.isfinite(distance).all():
            raise NumericalFailure("UNCOMMISSIONED_NUMERICS: nonfinite tangent residual")
        candidates = [j for j in range(3) if distance[j] <= tau[j]]
        if candidates:
            ranked = sorted(candidates, key=lambda j: (distance[j], tuple(t[j])))
            alternatives.append((float(distance[ranked[0]]), sign, tuple(ranked[:2])))
    return min(alternatives, key=lambda item: (item[0], item[1]))[2] if alternatives else ()


def triangle_rule(t, order, indices=()):
    nodes, weights = gauss(order)
    s, u = np.meshgrid(nodes, nodes, indexing="ij")
    if indices:
        if len(indices) > 2 or len(set(indices)) != len(indices) or any(type(j) is not int or not 0 <= j < 3 for j in indices):
            raise ValueError("one or two distinct triangle vertex indices required")
        r = s * s
        area = triangle_area(t)
        if len(indices) == 2:
            a, b = sorted((t[j] for j in indices), key=lambda vertex: tuple(vertex))
            c = t[next(j for j in range(3) if j not in indices)]
            xy = ((1 - r)[..., None] * ((1 - u)[..., None] * a + u[..., None] * b) + r[..., None] * c).reshape(-1, 2)
            jacobian = 4 * area * s * (1 - r)
        else:
            c = t[indices[0]]
            a, b = sorted((t[j] for j in range(3) if j not in indices), key=lambda vertex: tuple(vertex))
            xy = ((1 - r)[..., None] * c + r[..., None] * ((1 - u)[..., None] * a + u[..., None] * b)).reshape(-1, 2)
            jacobian = 4 * area * s**3
        return xy, (weights[:, None] * weights[None, :] * jacobian).ravel()
    w = (weights[:, None] * weights[None, :] * (1 - s) * (2 * triangle_area(t))).ravel()
    xy = (t[0] + s[..., None] * (t[1] - t[0]) + ((1 - s) * u)[..., None] * (t[2] - t[0])).reshape(-1, 2)
    return xy, w


def integrate_triangle(scene, frame, triangle, integrator, meter, depth=0):
    area = triangle_area(triangle)
    indices = tangent_indices(triangle, scene, frame)
    low_xy, low_w = triangle_rule(triangle, integrator.cell_low, indices)
    high_xy, high_w = triangle_rule(triangle, integrator.cell_high, indices)
    low_v, low_e = render_points(scene, frame, low_xy, integrator, meter)
    high_v, high_e = render_points(scene, frame, high_xy, integrator, meter)
    low, high = float(low_w @ low_v), float(high_w @ high_v)
    pl, ph = float(low_w @ low_e), float(high_w @ high_e)
    indicator = abs(high - low) + pl + ph
    meter.watch(triangle, low_xy, low_w, high_xy, high_w, low_v, low_e, high_v, high_e)
    if indicator <= integrator.cell_tolerance * area:
        return high, indicator, ph, abs(high - low), 1
    if depth >= integrator.cell_depth:
        raise NumericalFailure("UNCOMMISSIONED_NUMERICS: cell depth/error ceiling")
    lengths = [np.sum((triangle[(j + 1) % 3] - triangle[j]) ** 2) for j in range(3)]
    j = int(np.argmax(lengths))
    a, b, c = triangle[j], triangle[(j + 1) % 3], triangle[(j + 2) % 3]
    midpoint = (a + b) / 2
    first = integrate_triangle(scene, frame, np.array((a, midpoint, c)), integrator, meter, depth + 1)
    second = integrate_triangle(scene, frame, np.array((midpoint, b, c)), integrator, meter, depth + 1)
    return tuple(x + y for x, y in zip(first, second))


def render_cell(scene, frame, native_xy, integrator=Integrator(), meter=None):
    xy = np.asarray(native_xy, dtype=np.float64)
    if xy.shape != (2,) or not np.isfinite(xy).all():
        raise ValueError("finite cell centre pair required")
    meter = meter or Meter(integrator)
    triangles = cell_triangles(scene, frame, xy)
    area = sum(triangle_area(t) for t in triangles)
    if abs(area - 1) > 1e-11:
        raise NumericalFailure("UNCOMMISSIONED_NUMERICS: cell partition area")
    results = [integrate_triangle(scene, frame, t, integrator, meter) for t in triangles]
    value, cell_error, pupil_error, delta, leaves = (sum(r[i] for r in results) for i in range(5))
    if cell_error > integrator.cell_tolerance * (1 + 1e-11) or pupil_error > integrator.pupil_tolerance * (1 + 1e-11):
        raise NumericalFailure("UNCOMMISSIONED_NUMERICS: final cell indicator")
    return value, dict(value_error_indicator_e=cell_error + pupil_error, cell_indicator_e=cell_error,
                       weighted_high_pupil_indicator_e=pupil_error, cell_quadrature_delta_e=delta,
                       area=area, leaf_triangles=leaves, work=meter.receipt())


def render_frame(scene, frame, sensor, integrator, output_directory, *, meter=None, tile=8):
    if tile not in (8, 16):
        raise ValueError("registered tile size is8 or16")
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    meter = meter or Meter(integrator)
    meter.new_frame()
    shape = (sensor["height"], sensor["width"])
    values = np.full(shape, np.nan, dtype="<f8")
    errors = np.full(shape, np.nan, dtype="<f8")
    meter.frame(values)
    meter.watch(errors)
    completed = 0
    try:
        for by in range(0, shape[0], tile):
            for bx in range(0, shape[1], tile):
                for y in range(by, min(shape[0], by + tile)):
                    for x in range(bx, min(shape[1], bx + tile)):
                        values[y, x], receipt = render_cell(scene, frame, (x, y), integrator, meter)
                        errors[y, x] = receipt["value_error_indicator_e"]
                        completed += 1
                meter.check()
                write_json(output_directory / f"frame-{frame.index:02d}-progress.json",
                           dict(status="running", completed_cells=completed, total_cells=int(values.size), work=meter.receipt()))
    except Exception as error:
        # Uncomputed cells remain explicitly NaN, never mistaken for a full array.
        np.save(output_directory / f"frame-{frame.index:02d}-partial.npy", values, allow_pickle=False)
        write_json(output_directory / f"frame-{frame.index:02d}-failure.json", dict(status="UNCOMMISSIONED_NUMERICS", completed_cells=completed,
                   error=repr(error), frame=asdict(frame), integrator=asdict(integrator), work=meter.receipt()))
        raise
    scalar = output_directory / f"frame-{frame.index:02d}-scalar.npy"
    error_path = output_directory / f"frame-{frame.index:02d}-indicator.npy"
    np.save(scalar, values, allow_pickle=False)
    np.save(error_path, errors, allow_pickle=False)
    scalar_ref = dict(**file_ref(scalar, output_directory), dtype="<f8", shape=list(shape))
    error_ref = dict(**file_ref(error_path, output_directory), dtype="<f8", shape=list(shape))
    receipt = dict(schema="m194e-float-frame-v1", status="uncommissioned", frame=asdict(frame), expected_scalar=scalar_ref,
                   error_indicator=error_ref, max_error_indicator_e=float(errors.max()), integrator=asdict(integrator),
                   tile=tile, work=meter.receipt())
    numerical_path = output_directory / f"frame-{frame.index:02d}-numerical.json"
    write_json(numerical_path, receipt)
    return dict(**asdict(frame), expected_scalar=scalar_ref, numerical_receipt=file_ref(numerical_path, output_directory))
