"""M194e's declared geometric model; no numerical integrator or camera model."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def finite(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)) or not math.isfinite(value):
        raise ValueError(f"{name}: finite real number required")
    return float(value)


def pair(value, name):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{name}: pair required")
    return tuple(finite(x, name) for x in value)


@dataclass(frozen=True)
class Wave:
    amplitude: float
    frequency: tuple[float, float]
    phase: float

    def __post_init__(self):
        object.__setattr__(self, "amplitude", finite(self.amplitude, "amplitude"))
        object.__setattr__(self, "frequency", pair(self.frequency, "frequency"))
        object.__setattr__(self, "phase", finite(self.phase, "phase"))


@dataclass(frozen=True)
class Field:
    constant: float
    affine: tuple[float, float] = (0.0, 0.0)
    waves: tuple[Wave, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "constant", finite(self.constant, "constant"))
        object.__setattr__(self, "affine", pair(self.affine, "affine"))
        if not isinstance(self.waves, (tuple, list)) or len(self.waves) > 2 or any(not isinstance(w, Wave) for w in self.waves):
            raise ValueError("at most two Wave records required")
        object.__setattr__(self, "waves", tuple(self.waves))

    def evaluate(self, xy):
        xy = np.asarray(xy, dtype=np.float64)
        result = self.constant + self.affine[0] * xy[..., 0] + self.affine[1] * xy[..., 1]
        for w in self.waves:
            result = result + w.amplitude * np.cos(2 * np.pi * (w.frequency[0] * xy[..., 0] + w.frequency[1] * xy[..., 1]) + w.phase)
        return result


@dataclass(frozen=True)
class Scene:
    foreground: Field
    background: Field
    depths: tuple[float, float]
    mask_normal: tuple[float, float]
    mask_offset: float
    mask_state: str = "half-plane"

    def __post_init__(self):
        if not isinstance(self.foreground, Field) or not isinstance(self.background, Field):
            raise ValueError("Field records required")
        z = pair(self.depths, "depths")
        if not 0 < z[0] < z[1]:
            raise ValueError("positive foreground depth must precede background")
        n = pair(self.mask_normal, "mask_normal")
        if math.hypot(*n) == 0:
            raise ValueError("mask normal must be nonzero")
        if self.mask_state not in ("half-plane", "full", "absent"):
            raise ValueError("unknown mask state")
        object.__setattr__(self, "depths", z)
        object.__setattr__(self, "mask_normal", n)
        object.__setattr__(self, "mask_offset", finite(self.mask_offset, "mask_offset"))


@dataclass(frozen=True)
class Similarity:
    scale: float = 1.0
    rotation: float = 0.0
    centre: tuple[float, float] = (0.0, 0.0)
    translation: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self):
        a = finite(self.scale, "scale")
        if a <= 0:
            raise ValueError("positive scale required")
        object.__setattr__(self, "scale", a)
        object.__setattr__(self, "rotation", finite(self.rotation, "rotation"))
        object.__setattr__(self, "centre", pair(self.centre, "centre"))
        object.__setattr__(self, "translation", pair(self.translation, "translation"))

    def inverse_matrix(self):
        c, s = math.cos(self.rotation), math.sin(self.rotation)
        return np.array(((c, s), (-s, c)), dtype=np.float64) / self.scale

    def inverse(self, xy):
        xy = np.asarray(xy, dtype=np.float64)
        return (xy - self.centre - np.array(self.translation)) @ self.inverse_matrix().T + self.centre


@dataclass(frozen=True)
class Frame:
    index: int
    inverse_focus: float
    K: float
    forward_similarity: Similarity = Similarity()

    def __post_init__(self):
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 0:
            raise ValueError("nonnegative integer frame index required")
        f, k = finite(self.inverse_focus, "inverse_focus"), finite(self.K, "K")
        if f <= 0 or k < 0 or not isinstance(self.forward_similarity, Similarity):
            raise ValueError("positive inverse focus, nonnegative K and Similarity required")
        object.__setattr__(self, "inverse_focus", f)
        object.__setattr__(self, "K", k)

    def defocus(self, scene):
        return tuple(self.K * (self.inverse_focus - 1 / z) for z in scene.depths)


def evaluate_rays(scene, frame, native_xy, pupil_uv):
    z, u = np.asarray(native_xy, dtype=np.float64), np.asarray(pupil_uv, dtype=np.float64)
    if z.ndim < 1 or u.ndim < 1 or z.shape[-1] != 2 or u.shape[-1] != 2 or not np.isfinite(z).all() or not np.isfinite(u).all():
        raise ValueError("finite coordinate pairs required")
    if np.any(np.sum(u * u, axis=-1) > 1 + 8 * np.finfo(float).eps):
        raise ValueError("pupil coordinate outside unit disc")
    df, db = frame.defocus(scene)
    qf = frame.forward_similarity.inverse(z + df * u)
    qb = frame.forward_similarity.inverse(z + db * u)
    if scene.mask_state == "full":
        visibility = True
    elif scene.mask_state == "absent":
        visibility = False
    else:
        visibility = qf[..., 0] * scene.mask_normal[0] + qf[..., 1] * scene.mask_normal[1] >= scene.mask_offset
    result = np.where(visibility, scene.foreground.evaluate(qf), scene.background.evaluate(qb))
    if not np.isfinite(result).all() or np.any(result < 0):
        raise ValueError("radiance must be finite and nonnegative on evaluated footprint")
    return result


def primary_scene():
    return Scene(Field(15000, waves=(Wave(1400, (.045, .095), .7), Wave(700, (.17, .01), .3))),
                 Field(12000, waves=(Wave(3200, (.08, .015), .2), Wave(1800, (-.035, .12), 1.1))),
                 (1, 2), (1, -.15), 28.4)


def primary_frames():
    return tuple(Frame(i, f, 12) for i, f in enumerate((.5, .625, .75, .875, 1)))


def sensor_record():
    return dict(width=64, height=48, cfa="RGGB", active_origin=[0, 0], channel_factors=[.75, 1, .6], black=512,
                white=15360, gain_dn_per_e=.25, noise=False, rounding="ties-to-even", cell="integer-centre-unit-square")


def scene_record(scene):
    return dict(depths=list(scene.depths), mask=dict(normal=list(scene.mask_normal), offset=scene.mask_offset, side="ge"),
                foreground=asdict(scene.foreground), background=asdict(scene.background))


RAY_MODEL = dict(name="shared-pupil-two-opaque-planes-v1", pupil="uniform-unit-disc-area", visibility="foreground-first-same-ray",
                 coordinates="native-displacement-before-inverse-similarity", defocus="K*(inverse_focus-1/depth)",
                 exposure="radiance-normalized", diffraction=False, spectral_optics=False)


def strict_json_loads(text):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError(f"duplicate JSON key: {k}")
            result[k] = v
        return result
    def bad(value):
        raise ValueError(f"nonfinite JSON value: {value}")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=bad)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_ref(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    return dict(path=path.relative_to(root).as_posix(), sha256=sha256(path), bytes=path.stat().st_size)


def write_json(path, record):
    Path(path).write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

raise RuntimeError('must not execute')
