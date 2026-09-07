"""Fixed quality instruments; source preparation is not execution authority."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.perf_counter()
import math
import os
import weakref

for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "2"
import numpy as np


class Refusal(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Refusal(message)


class Budget:
    def __init__(self, stage, *, start_cpu, start_wall, cpu_clock=time.process_time,
                 wall_clock=time.perf_counter):
        require(stage in ("target", "instruments", "score"), "quality stage")
        self.stage, self.start_cpu, self.start_wall = stage, start_cpu, start_wall
        self.cpu_clock, self.wall_clock = cpu_clock, wall_clock
        self.limits = {"cpu_seconds": 120.0, "wall_seconds": 240.0,
                       "live_array_bytes": 32 * 1024**2,
                       "output_bytes": (32 if stage == "score" else 64) * 1024**2,
                       "tiff_decodes": 256 if stage == "score" else 128,
                       "target_cells": 76800 + 128}
        self.arrays = {}
        self.peak_bytes = self.output_bytes = self.tiff_decodes = self.target_cells = 0
        self.check()

    def live(self):
        self.arrays = {key: value for key, value in self.arrays.items() if value[0]() is not None}
        return sum(value[1] for value in self.arrays.values())

    def check(self):
        values = {"cpu_seconds": self.cpu_clock() - self.start_cpu,
                  "wall_seconds": self.wall_clock() - self.start_wall,
                  "live_array_bytes": self.live(), "output_bytes": self.output_bytes,
                  "tiff_decodes": self.tiff_decodes, "target_cells": self.target_cells}
        self.peak_bytes = max(self.peak_bytes, values["live_array_bytes"])
        for name, value in values.items():
            require(type(value) in (int, float) and math.isfinite(value)
                    and 0 <= value <= self.limits[name], "quality budget " + name)
        return values

    def check_allocation(self, shape, dtype):
        require(type(shape) in (tuple, list) and shape and all(type(n) is int and n >= 0 for n in shape),
                "typed allocation dimensions")
        require(self.live() + math.prod(shape) * np.dtype(dtype).itemsize <= self.limits["live_array_bytes"],
                "quality allocation ceiling")
        self.check()

    def watch(self, array, label):
        require(isinstance(array, np.ndarray), "tracked array type")
        owner = array
        while isinstance(owner.base, np.ndarray):
            owner = owner.base
        self.live()
        old = self.arrays.get(id(owner))
        if old is None or old[0]() is not owner:
            self.arrays[id(owner)] = (weakref.ref(owner), int(owner.nbytes), {label})
        else:
            old[2].add(label)
        self.check()
        return array

    def empty(self, shape, dtype, label):
        self.check_allocation(shape, dtype)
        return self.watch(np.empty(shape, dtype=dtype), label)

    def receipt(self):
        return {"stage": self.stage, "limits": dict(self.limits), **self.check(),
                "peak_live_array_bytes": self.peak_bytes,
                "tracked_scope": "unique live backing ndarrays; not process RSS"}


def finite(array, budget):
    mask = budget.empty(array.shape, "|b1", "finite-value mask")
    np.isfinite(array, out=mask)
    require(bool(mask.all()), "nonfinite quality array")


def selected(array, mask, budget, label):
    require(array.ndim == 2 and mask.shape == array.shape and mask.dtype == np.bool_, "masked plane layout")
    n = int(np.count_nonzero(mask))
    require(n > 0, "empty fixed quality region")
    budget.check_allocation((n,), array.dtype)
    return budget.watch(array[mask], label)


def regions(shape, offset, budget):
    require(type(shape) in (tuple, list) and len(shape) == 2
            and all(type(v) is int for v in shape), "quality native shape")
    h, w = shape
    require(type(offset) in (tuple, list) and len(offset) == 2
            and all(type(v) is int for v in offset), "quality native offset")
    ox, oy = offset
    require(0 < w <= 320 and 0 < h <= 240 and 0 <= ox <= 320 - w and 0 <= oy <= 240 - h,
            "quality crop outside native frame")
    require(104 - ox >= 74 and ox + w - 216 >= 74
            and 104 - oy >= 74 and oy + h - 136 >= 74, "fixed74-native supported-window guard")
    xs = budget.empty((w,), "<f8", "native x coordinates")
    ys = budget.empty((h,), "<f8", "native y coordinates")
    for x in range(w):
        xs[x] = ox + x
    for y in range(h):
        ys[y] = oy + y
    heights = budget.empty((h, w), "<f8", "input-defined heights")
    term = budget.empty((h,), "<f8", "height row term")
    np.multiply(ys, .15, out=term)
    np.subtract(xs[None, :], term[:, None], out=heights)
    np.subtract(heights, 142., out=heights)
    masks = {}
    for name in ("whole", "window", "boundary", "surface-background", "surface-foreground",
                 "endpoint-background", "endpoint-foreground"):
        masks[name] = budget.empty((h, w), "|b1", name + " region")
    masks["whole"].fill(True)
    window = masks["window"]
    window.fill(False)
    window[104 - oy:136 - oy, 104 - ox:216 - ox] = True
    absolute = budget.empty((h, w), "<f8", "absolute height")
    np.abs(heights, out=absolute)
    np.less_equal(absolute, 8., out=masks["boundary"])
    np.less(heights, -8., out=masks["surface-background"])
    np.greater(heights, 8., out=masks["surface-foreground"])
    np.less(heights, -(.575 + 6 * math.sqrt(1.0225) + 2), out=masks["endpoint-background"])
    np.greater(heights, .575 + 2, out=masks["endpoint-foreground"])
    for name, mask in masks.items():
        if name not in ("whole", "window"):
            np.logical_and(mask, window, out=mask)
        require(bool(mask.any()), "empty fixed region: " + name)
    budget.check()
    return masks


def errors(image, target, mask, budget):
    require(image.shape == target.shape and image.ndim == 2, "error plane layout")
    a = selected(image, mask, budget, "selected observation")
    b = selected(target, mask, budget, "selected target")
    np.subtract(a, b, out=a)
    finite(a, budget)
    bias = float(np.mean(a, dtype=np.float64))
    np.multiply(a, a, out=b)
    mse = float(np.mean(b, dtype=np.float64))
    return {"sites": int(a.size), "bias_dn": bias, "mse_dn2": mse, "rmse_dn": math.sqrt(mse)}


class Temporal:
    """Eight actual repeat planes; scratch is supplied and reused between modes."""
    def __init__(self, shape, budget):
        require(type(shape) in (tuple, list) and len(shape) == 2
                and all(type(v) is int and v > 0 for v in shape), "temporal plane dimensions")
        self.budget, self.n = budget, 0
        self.mean = budget.empty(shape, "<f8", "repeat mean")
        self.m2 = budget.empty(shape, "<f8", "repeat M2")
        self.mean.fill(0.)
        self.m2.fill(0.)

    def add(self, image, scratch):
        require(self.n < 8 and image.shape == self.mean.shape and image.dtype.str == "<f8",
                "exact eight-repeat population/layout")
        require(len(scratch) == 2 and all(a.shape == image.shape and a.dtype.str == "<f8" for a in scratch),
                "temporal scratch layout")
        self.check_scratch(image, scratch)
        finite(image, self.budget)
        delta, product = scratch
        self.n += 1
        np.subtract(image, self.mean, out=delta)
        np.divide(delta, self.n, out=product)
        np.add(self.mean, product, out=self.mean)
        np.subtract(image, self.mean, out=product)
        np.multiply(delta, product, out=product)
        np.add(self.m2, product, out=self.m2)
        self.budget.check()

    def check_scratch(self, image, scratch):
        require(len(scratch) == 2 and all(a.shape == self.mean.shape and a.dtype.str == "<f8" for a in scratch),
                "temporal scratch layout")
        arrays = (image, self.mean, self.m2, *scratch)
        require(all(not np.shares_memory(arrays[i], arrays[j]) for i in range(len(arrays))
                    for j in range(i + 1, len(arrays))), "temporal observation/state/scratch alias")

    def variance_region(self, mask):
        require(self.n == 8, "incomplete repeat variance")
        values = selected(self.m2, mask, self.budget, "region M2")
        return float(np.sum(values, dtype=np.float64)) / (7 * values.size)

    def leave_one(self, image, scratch, mask):
        require(self.n == 8 and image.shape == self.mean.shape and image.dtype.str == "<f8", "leave-one population/layout")
        self.check_scratch(image, scratch)
        finite(image, self.budget)
        delta, work = scratch
        np.subtract(image, self.mean, out=delta)
        np.multiply(delta, delta, out=work)
        np.multiply(work, 8 / 7, out=work)
        np.subtract(self.m2, work, out=work)
        values = selected(work, mask, self.budget, "delete-one M2")
        return float(np.sum(values, dtype=np.float64)) / (6 * values.size)


def repeat_summary(values):
    require(len(values) == 8 and all(type(v) in (int, float) and math.isfinite(v) for v in values),
            "eight finite repeat scalars")
    mean = math.fsum(values) / 8
    sd = math.sqrt(math.fsum((v - mean)**2 for v in values) / 7)
    return {"values": list(values), "mean": mean, "sample_sd": sd, "standard_error": sd / math.sqrt(8)}


def jackknife(values):
    result = repeat_summary(values)
    result["jackknife_standard_error"] = math.sqrt(7 / 8 * math.fsum((v - result["mean"])**2 for v in values))
    return result


class WaveFit:
    def __init__(self, mask, offset, waves, budget):
        require(len(waves) == 2 and mask.ndim == 2 and mask.dtype == np.bool_, "fixed two-wave mask")
        self.mask, self.budget = mask, budget
        n = int(np.count_nonzero(mask))
        require(n >= 5, "insufficient wave-fit sites")
        self.x = budget.empty((n, 5), "<f8", "joint wave design")
        self.x[:, 0] = 1.
        index = 0
        for y in range(mask.shape[0]):
            for x in range(mask.shape[1]):
                if mask[y, x]:
                    for j, frequency in enumerate(waves):
                        angle = 2 * math.pi * (frequency[0] * (x + offset[0]) + frequency[1] * (y + offset[1]))
                        self.x[index, 1 + 2*j] = math.cos(angle)
                        self.x[index, 2 + 2*j] = math.sin(angle)
                    index += 1
        require(index == n, "wave design coverage")
        budget.check_allocation((n * 5 + 5 + 25,), "<f8")
        # All returned arrays are tracked before any further owned allocation.
        u, singular, vt = np.linalg.svd(self.x, full_matrices=False)
        budget.watch(u, "wave SVD left vectors")
        budget.watch(singular, "wave SVD singular values")
        budget.watch(vt, "wave SVD right vectors")
        self.condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else math.inf
        threshold = max(n, 5) * np.finfo(np.float64).eps * singular[0]
        require(int(np.count_nonzero(singular > threshold)) == 5 and self.condition <= 1e6,
                "wave-fit rank/condition guard")
        self.inverse = budget.empty((5, n), "<f8", "wave pseudoinverse")
        scaled = budget.empty((5, 5), "<f8", "scaled right singular vectors")
        np.divide(vt.T, singular[None, :], out=scaled)
        np.matmul(scaled, u.T, out=self.inverse)
        budget.check()

    def read(self, plane):
        values = selected(plane, self.mask, self.budget, "wave readout values")
        finite(values, self.budget)
        coefficients = self.budget.empty((5,), "<f8", "wave coefficients")
        residual = self.budget.empty(values.shape, "<f8", "wave residual")
        np.matmul(self.inverse, values, out=coefficients)
        np.matmul(self.x, coefficients, out=residual)
        np.subtract(values, residual, out=residual)
        np.multiply(residual, residual, out=residual)
        waves = []
        for j in range(2):
            real, imaginary = float(coefficients[1 + 2*j]), -float(coefficients[2 + 2*j])
            amplitude = math.hypot(real, imaginary)
            waves.append({"real_dn": real, "imaginary_dn": imaginary, "amplitude_dn": amplitude,
                          "phase_radians": None if amplitude <= 1e-8 else math.atan2(imaginary, real)})
        return {"sites": int(values.size), "condition": self.condition, "intercept_dn": float(coefficients[0]),
                "waves": waves, "residual_rms_dn": math.sqrt(float(np.mean(residual, dtype=np.float64)))}


def wave_difference(observed, target):
    rows = []
    for a, b in zip(observed["waves"], target["waves"], strict=True):
        real, imaginary = a["real_dn"] - b["real_dn"], a["imaginary_dn"] - b["imaginary_dn"]
        phase = None
        if a["phase_radians"] is not None and b["phase_radians"] is not None:
            delta = a["phase_radians"] - b["phase_radians"]
            phase = math.atan2(math.sin(delta), math.cos(delta))
        rows.append({"real_error_dn": real, "imaginary_error_dn": imaginary,
                     "complex_error_dn": math.hypot(real, imaginary),
                     "amplitude_difference_dn": a["amplitude_dn"] - b["amplitude_dn"],
                     "phase_error_radians": phase})
    return rows


def decomposition(temporal, target, mask, mean_repeat_mse):
    require(temporal.n == 8, "complete decomposition population")
    mean_error = errors(temporal.mean, target, mask, temporal.budget)
    variance = temporal.variance_region(mask)
    squared_bias = mean_error["mse_dn2"] - variance / 8
    residual = squared_bias + variance - mean_repeat_mse
    require(math.isfinite(residual) and abs(residual) <= 1e-8 + 1e-10 * abs(mean_repeat_mse),
            "finite-repeat arithmetic decomposition")
    return {"mean_image_bias_dn": mean_error["bias_dn"], "mean_image_mse_dn2": mean_error["mse_dn2"],
            "temporal_variance_dn2": variance, "unbiased_squared_bias_dn2": squared_bias,
            "mean_repeat_mse_dn2": mean_repeat_mse, "arithmetic_residual_dn2": residual,
            "scope": "eight-repeat decomposition; identity is arithmetic, negative squared-bias estimates retained"}


def sparse_pair(before, after, target, mask, offset, budget):
    require(before.shape == after.shape == target.shape == mask.shape, "paired sparse plane layout")
    a = selected(before, mask, budget, "before sparse errors")
    b = selected(after, mask, budget, "after sparse errors")
    work = selected(target, mask, budget, "sparse target scratch")
    np.subtract(a, work, out=a)
    np.subtract(b, work, out=b)
    finite(a, budget)
    finite(b, budget)
    abs_a = budget.empty(a.shape, "<f8", "before absolute errors")
    abs_b = budget.empty(b.shape, "<f8", "after absolute errors")
    np.abs(a, out=abs_a)
    np.abs(b, out=abs_b)
    budget.check_allocation((int(a.size),), np.intp)
    sites = budget.watch(np.flatnonzero(mask), "canonical selected site indices")
    def site(index):
        y, x = divmod(int(sites[index]), mask.shape[1])
        old, new, truth = float(before[y, x]), float(after[y, x]), float(target[y, x])
        return {"native_xy": [x + offset[0], y + offset[1]], "before_dn": old, "after_dn": new,
                "target_dn": truth, "before_signed_error_dn": old - truth,
                "after_signed_error_dn": new - truth,
                "absolute_error_movement_dn": abs(new - truth) - abs(old - truth)}
    worst_before, worst_after = int(np.argmax(abs_a)), int(np.argmax(abs_b))
    before_site, after_site = site(worst_before), site(worst_after)
    maximum_a, maximum_b = float(abs_a[worst_before]), float(abs_b[worst_after])
    np.subtract(abs_b, abs_a, out=work)
    worsening_site = site(int(np.argmax(work)))
    flags = budget.empty(a.shape, "|b1", "sparse threshold flags")
    np.greater(work, 10., out=flags)
    worse = int(np.count_nonzero(flags))
    np.less(work, -10., out=flags)
    improved = int(np.count_nonzero(flags))
    rank = math.ceil(.999 * a.size) - 1
    abs_a.partition(rank)
    abs_b.partition(rank)
    budget.check()
    return {"sites": int(a.size), "nearest_rank_index": rank,
            "before_p999_absolute_error_dn": float(abs_a[rank]),
            "after_p999_absolute_error_dn": float(abs_b[rank]),
            "before_maximum_absolute_error_dn": maximum_a, "after_maximum_absolute_error_dn": maximum_b,
            "before_worst_site": before_site, "after_worst_site": after_site,
            "maximum_worsening_site": worsening_site, "worsening_gt10_dn_count": worse,
            "improvement_gt10_dn_count": improved}
