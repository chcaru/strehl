"""M194g independent spatial reference. Implementation release is not execution.

Full layers use independent real spatial integrals. Partly visible cells reuse
the immutable M194e Cartesian/chord plus analytic clipped-cell reference.
No author model, selector, polar integrator, Bessel or cached factor is imported.
"""
from __future__ import annotations

import os
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "2"

import argparse
from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import shutil
import sys
import traceback
import warnings
import weakref

import numpy as np
import scipy
from scipy.integrate import quad, IntegrationWarning

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = HERE.parent / "m194e-joint-pupil" / "independent-model.py"
OLD_SHA = "0cd8ea2331b269e65befdee110560cbc345e89c12348cbe1dc3144f7c04443f0"
CATALOG_SHA = "3814eeaf459e14a0a32e90ceeab6fc9d2994c92ee55bf17c824478accc3cbd41"
FIXTURE_SHA = "e84f0bbbda9bef039da86616c9f051d416929f4dbe78477cc5b3fc21206856bb"
TARGETS = {"primary": .000125, "refined": .0000078125}
METHOD = "m194g-independent-spatial-cache-v1"
BRANCHES = {"foreground": 0, "background": 1, "numerical": 2, "point": 3}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_source(path, name, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("pinned independent source mismatch: " + str(path))
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(path)
    sys.modules[name] = mod
    exec(compile(raw, str(path), "exec"), mod.__dict__)
    return mod


m = load_source(OLD, "m194g_frozen_independent_model", OLD_SHA)
Refusal = m.Refusal


def pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise Refusal("duplicate JSON key: " + key)
        out[key] = value
    return out


def read_json(path, expected=None):
    path = Path(path)
    with path.open("rb") as stream:
        raw = stream.read(64 * 1024 * 1024 + 1)
    if len(raw) > 64 * 1024 * 1024:
        raise Refusal("JSON byte ceiling")
    if expected is not None and hashlib.sha256(raw).hexdigest() != expected:
        raise Refusal("external file digest mismatch: " + str(path))
    data = json.loads(raw.decode("utf8"), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(Refusal("nonfinite JSON " + x)))
    def finite(v):
        if isinstance(v, float) and not math.isfinite(v):
            raise Refusal("overflowed JSON float")
        if isinstance(v, dict):
            for child in v.values():
                finite(child)
        elif isinstance(v, list):
            for child in v:
                finite(child)
    finite(data)
    return data


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf8")


def normalized(value):
    return json.loads(json.dumps(value, allow_nan=False))


def require_input(actual, expected):
    # Literal normalized boundary, including numeric/bool distinctions.
    left = json.dumps(normalized(actual), sort_keys=True, separators=(",", ":"), allow_nan=False)
    right = json.dumps(normalized(expected), sort_keys=True, separators=(",", ":"), allow_nan=False)
    if left != right:
        raise Refusal("normalized input changed")


def keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise Refusal("wrong keys: " + label)


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise Refusal("nonfinite/non-numeric " + label)
    return float(value)


def vector(value, label):
    if not isinstance(value, list) or len(value) != 2:
        raise Refusal("not a two-coordinate list: " + label)
    return tuple(number(x, label) for x in value)


def radiance(record):
    keys(record, ("constant", "affine", "waves"), "field")
    if not isinstance(record["waves"], list) or len(record["waves"]) > 2:
        raise Refusal("invalid wave list")
    waves = []
    for wave in record["waves"]:
        keys(wave, ("amplitude", "frequency", "phase"), "wave")
        waves.append((number(wave["amplitude"], "amplitude"),
                      *vector(wave["frequency"], "frequency"), number(wave["phase"], "phase")))
    return m.Radiance(number(record["constant"], "constant"), vector(record["affine"], "affine"), tuple(waves))


@dataclass(frozen=True)
class Prepared:
    scene: object
    frame: object
    mask_state: str
    centre: tuple
    translation: tuple
    # Exact finite-coefficient affine form for our wider independent selector.
    exact_M: tuple
    exact_b: tuple
    exact_pulled: tuple
    exact_h0: object
    exact_guard: object
    scene_record: dict
    frame_record: dict


def prepare(scene, frame):
    keys(scene, ("depths", "mask_normal", "mask_offset", "mask_state", "foreground", "background"), "scene")
    keys(frame, ("index", "inverse_focus", "K", "forward_similarity"), "frame")
    if type(frame["index"]) is not int or frame["index"] not in range(5):
        raise Refusal("invalid original frame index")
    sim = frame["forward_similarity"]
    keys(sim, ("scale", "rotation", "centre", "translation"), "similarity")
    scale, angle = number(sim["scale"], "scale"), number(sim["rotation"], "rotation")
    if scale <= 0:
        raise Refusal("nonpositive scale")
    c, t = vector(sim["centre"], "centre"), vector(sim["translation"], "translation")
    # Independent elementary matrix construction, not the author's inverse API.
    cosine, sine = math.cos(angle), math.sin(angle)
    matrix = ((cosine / scale, sine / scale), (-sine / scale, cosine / scale))
    exact_matrix = tuple(tuple(F(v) for v in row) for row in matrix)
    exact_b = tuple(F(c[i]) - sum(exact_matrix[i][j] * (F(c[j]) + F(t[j])) for j in range(2))
                    for i in range(2))
    # The old independent primitive consumes its own direct M*z+b API.
    # One correctly rounded b is an explicit finite-arithmetic adapter choice.
    b = tuple(float(v) for v in exact_b)
    depths = vector(scene["depths"], "depths")
    s = m.Scene(*depths, vector(scene["mask_normal"], "normal"), number(scene["mask_offset"], "offset"),
                radiance(scene["foreground"]), radiance(scene["background"]))
    f = m.Frame(number(frame["inverse_focus"], "focus"), number(frame["K"], "K"), matrix, b)
    if scene["mask_state"] not in ("half-plane", "full", "absent"):
        raise Refusal("unsupported mask state")
    m.validate(s, f)
    exact_n = tuple(F(v) for v in s.normal)
    pulled = tuple(sum(exact_n[i] * exact_matrix[i][j] for i in range(2)) for j in range(2))
    h0 = sum(exact_n[i] * exact_b[i] for i in range(2)) - F(s.offset)
    df = F(f.K * (f.inverse_focus - 1 / s.foreground_depth))
    guard = (abs(df) + F(3, 2)) * (abs(pulled[0]) + abs(pulled[1]))
    return Prepared(s, f, scene["mask_state"], c, t, exact_matrix, exact_b,
                    pulled, h0, guard, normalized(scene), normalized(frame))


def case_input(catalog, case):
    s = case["scene"]
    scene = {k: s[k] for k in ("depths", "mask_normal", "mask_offset", "mask_state")}
    scene["foreground"] = catalog["fields"][s["foreground_field"]]
    scene["background"] = catalog["fields"][s["background_field"]]
    return prepare(scene, catalog["frames"][case["frame"]])


def validate_population(catalog):
    if catalog.get("schema") != "m194g-component-population-v1" or catalog.get("status") != "REGISTERED_COMPONENTS":
        raise Refusal("unregistered component population")
    cases = catalog.get("cases")
    if not isinstance(cases, list) or len(cases) != 150 or len({c["id"] for c in cases}) != 150:
        raise Refusal("incomplete/duplicate component population")
    if sum(c["call"] == "cell" for c in cases) != 149 or sum(c["call"] == "point" for c in cases) != 1:
        raise Refusal("changed cell/point population")
    for case in cases:
        vector(case["native_xy"], "native_xy")
        if case["reference_arms"] != ["primary", "refined"]:
            raise Refusal("changed reference arms")
        case_input(catalog, case)
    return catalog


class Budget(m.Budget):
    """Shared actual integrand counter; full arms and component batch are separate."""
    def __init__(self, *, start_cpu=None, start_wall=None):
        super().__init__(start_cpu=time.process_time() if start_cpu is None else start_cpu,
                         start_wall=time.monotonic() if start_wall is None else start_wall)
        self.factor_evaluations = 0
        self.chord_evaluations = 0
        self.peak_explicit_array_bytes = 0
        self.max_array_bytes = 32 * 1024 * 1024
        self._owners = {}
        self._scalar_frames = {}

    def tick(self, factor=False):
        if self.evaluations >= self.max_evaluations:
            raise Refusal("independent evaluation budget")
        self.evaluations += 1
        self.factor_evaluations += int(factor)
        self.chord_evaluations += int(not factor)
        if self.evaluations % 64 == 0:
            self.check()

    def arrays(self, *arrays, scalar_frame=None):
        # Weak owners persist across registrations but never keep arrays alive.
        self._owners = {key: value for key, value in self._owners.items() if value[0]() is not None}
        self._scalar_frames = {key: value for key, value in self._scalar_frames.items() if value() is not None}
        for a in arrays:
            if not isinstance(a, np.ndarray):
                raise Refusal("untracked non-ndarray storage")
            root = a
            while isinstance(root.base, np.ndarray):
                root = root.base
            self._owners[id(root)] = (weakref.ref(root), root.nbytes)
        if scalar_frame is not None:
            if not isinstance(scalar_frame, np.ndarray):
                raise Refusal("invalid scalar frame owner")
            owner = scalar_frame
            while isinstance(owner.base, np.ndarray):
                owner = owner.base
            self._scalar_frames[id(owner)] = weakref.ref(owner)
            if len(self._scalar_frames) > 1:
                raise Refusal("second live scalar reference frame")
        live = sum(value[1] for value in self._owners.values())
        self.peak_explicit_array_bytes = max(live, self.peak_explicit_array_bytes)
        if live > self.max_array_bytes:
            raise Refusal("independent explicit array budget")

    def receipt(self):
        return dict(**super().receipt(), factor_evaluations=self.factor_evaluations,
                    chord_evaluations=self.chord_evaluations,
                    peak_explicit_array_bytes=self.peak_explicit_array_bytes,
                    live_scalar_frame_owners=sum(ref() is not None for ref in self._scalar_frames.values()),
                    array_accounting_scope="live named ndarray backing allocations; excludes hidden temporaries, Python objects and RSS")


def exact_support(p, xy):
    z = tuple(F(number(v, "xy")) for v in xy)
    h = sum(p.exact_pulled[j] * z[j] for j in range(2)) + p.exact_h0
    d = F(p.frame.K * (p.frame.inverse_focus - 1 / p.scene.foreground_depth))
    return h, p.exact_pulled, d


def select(p, xy):
    if p.mask_state != "half-plane":
        return "foreground" if p.mask_state == "full" else "background"
    h = sum(p.exact_pulled[j] * F(xy[j]) for j in range(2)) + p.exact_h0
    # Wider independent pupil box + one extra native-cell guard. No author predicate.
    guard = p.exact_guard
    return "foreground" if h > guard else "background" if h < -guard else "numerical"


def integrate_factor(kind, argument, eps, budget):
    argument = number(argument, "factor argument")
    if not math.isfinite(eps) or eps <= 0:
        raise Refusal("invalid dimensionless factor target")
    if kind == "disc":
        norm, lo, hi = 4 / math.pi, 0., math.pi / 2
        def fn(t):
            budget.tick(factor=True)
            return math.cos(t) ** 2 * math.cos(argument * math.sin(t))
    elif kind == "square":
        norm, lo, hi = 1., -.5, .5
        def fn(t):
            budget.tick(factor=True)
            return math.cos(argument * t)
    else:
        raise Refusal("unknown spatial factor")
    budget.check()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", IntegrationWarning)
        value, error = quad(fn, lo, hi, epsabs=eps / norm, epsrel=0., limit=128)
    if caught:
        raise Refusal("spatial-factor quadrature warning: " + str(caught[0].message))
    value, error = norm * value, norm * error
    budget.check()
    if not math.isfinite(value) or not math.isfinite(error) or error < 0 or error > eps:
        raise Refusal("spatial factor/error refusal")
    return value, dict(kind=kind, argument=argument, value=value,
                      absolute_indicator=error, absolute_request=eps)


def wave_vector(frame, fx, fy):
    return frame.pull((2 * math.pi * fx, 2 * math.pi * fy))


def chief_ray(frame, xy):
    return frame.transform(xy)


class Engine:
    def __init__(self, budget, target):
        if target not in TARGETS.values():
            raise Refusal("unregistered reference target")
        self.budget, self.target = budget, target
        self.cache = OrderedDict()
        self.cache_hits = self.cache_misses = self.cache_evictions = 0
        self.transfer_consumptions = 0
        self.branch_counts = {k: 0 for k in BRANCHES}
        self.last_entry = None

    def factors(self, p, layer, cell=True):
        rad = p.scene.foreground if layer == "foreground" else p.scene.background
        depth = p.scene.foreground_depth if layer == "foreground" else p.scene.background_depth
        d = p.frame.K * (p.frame.inverse_focus - 1 / depth)
        key = (METHOD, self.target, p.frame.M, rad, d, cell)
        if key in self.cache:
            self.cache_hits += 1
            self.cache.move_to_end(key)
            self.last_entry = self.cache[key]
            return self.last_entry
        self.cache_misses += 1
        amplitude_sum = sum(abs(w[0]) for w in rad.waves)
        eps = self.target / (16 * max(1., amplitude_sum))
        waves = []
        for amplitude, fx, fy, phase in rad.waves:
            k = wave_vector(p.frame, fx, fy)
            disc, dr = integrate_factor("disc", abs(d) * math.hypot(*k), eps, self.budget)
            if cell:
                sx, xr = integrate_factor("square", k[0], eps, self.budget)
                sy, yr = integrate_factor("square", k[1], eps, self.budget)
            else:
                sx = sy = 1.
                xr = yr = dict(kind="no-point-cell-factor", absolute_indicator=0., absolute_request=0.)
            waves.append(dict(amplitude=amplitude, frequency=[fx, fy], phase=phase,
                              native_k=list(k), signed_defocus=d, disc=disc, sx=sx, sy=sy,
                              quadrature=[dr, xr, yr]))
        entry = dict(layer=layer, signed_defocus=d, target_e=self.target,
                     factor_target=eps, waves=waves, field=rad)
        if len(self.cache) == 20:
            self.cache.popitem(last=False)
            self.cache_evictions += 1
        self.cache[key] = entry
        self.last_entry = entry
        return entry

    def full_layer(self, p, xy, layer, cell=True):
        entry = self.factors(p, layer, cell)
        if entry["target_e"] != self.target:
            raise Refusal("cached integration target mismatch")
        rad = p.scene.foreground if layer == "foreground" else p.scene.background
        q = chief_ray(p.frame, xy)
        radius = abs(entry["signed_defocus"])
        extent = tuple((.5 * sum(abs(v) for v in row) if cell else 0.) + radius * math.hypot(*row)
                       for row in p.frame.M)
        domain = [[q[i] - extent[i], q[i] + extent[i]] for i in range(2)]
        lower = rad.constant + sum(rad.affine[i] * q[i] - abs(rad.affine[i]) * extent[i] for i in range(2)) - sum(abs(w[0]) for w in rad.waves)
        if not all(math.isfinite(v) for row in domain for v in row) or not math.isfinite(lower) or lower < 0:
            raise Refusal("unbounded/negative selected radiance domain")
        terms = [rad.constant, rad.affine[0] * q[0], rad.affine[1] * q[1]]
        quad_error = 0.
        for wave in entry["waves"]:
            amplitude = wave["amplitude"]
            fx, fy = wave["frequency"]
            phase = 2 * math.pi * (fx * q[0] + fy * q[1]) + wave["phase"]
            factors = (wave["disc"], wave["sx"], wave["sy"])
            terms.append(amplitude * math.cos(phase) * math.prod(factors))
            errors = [r["absolute_indicator"] for r in wave["quadrature"]]
            # Conditional propagation of quadrature estimates, not a rigorous bound.
            a, b, c = map(abs, factors)
            ex, ey, ez = errors
            expansion = math.fsum((ex * b * c, ey * a * c, ez * a * b,
                                    ex * ey * c, ex * ez * b, ey * ez * a, ex * ey * ez))
            quad_error += abs(amplitude) * expansion
            self.transfer_consumptions += 1
        value = math.fsum(terms)
        if not math.isfinite(value) or value < 0 or not math.isfinite(quad_error) or quad_error > self.target / 2:
            raise Refusal("nonfinite/negative independent analytic value")
        return value, dict(method=METHOD, branch=layer, request_e=self.target,
                           absolute_error_indicator_e=quad_error,
                           indicator_scope="conditional propagated spatial quadrature estimates; phase/product roundoff is not measured",
                           phase_arithmetic_engineering_reservation_e=self.target / 2,
                           canonical_centre=list(q), conservative_evaluated_coordinate_box=domain,
                           conservative_radiance_lower_e=lower,
                           factors=[{k: v for k, v in w.items()} for w in entry["waves"]])

    def render(self, p, xy, *, cell=True):
        self.budget.check()
        branch = select(p, xy) if cell else "point"
        self.branch_counts[branch] += 1
        if branch in ("foreground", "background"):
            value, receipt = self.full_layer(p, xy, branch, cell)
        else:
            if p.mask_state != "half-plane":
                raise Refusal("point full/absent case outside registered population")
            value, receipt = m.render(p.scene, p.frame, xy, cell=cell,
                                      eps=self.target, budget=self.budget)
            receipt = dict(receipt, branch=branch,
                           indicator_scope="frozen independent Cartesian quadrature estimate")
        self.budget.check()
        return value, receipt

    def receipt(self):
        return dict(method=METHOD, target_e=self.target, cache_entries=len(self.cache),
                    cache_hits=self.cache_hits, cache_misses=self.cache_misses,
                    cache_evictions=self.cache_evictions, transfer_consumptions=self.transfer_consumptions,
                    branch_counts=dict(self.branch_counts))


def file_ref(path, *, array=None):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise Refusal("artifact outside repository")
    rec = dict(path=path.relative_to(ROOT).as_posix(), sha256=digest(path), bytes=path.stat().st_size)
    if array is not None:
        rec.update(dtype=array.dtype.str, shape=list(array.shape))
    return rec


def source_map():
    paths = [Path(__file__).resolve(), HERE / "independent-reference-components.py", OLD,
             HERE / "component-population.json", HERE / "fixture.json",
             HERE / "next-reference-plan.md", HERE / "next-numerical-release.md",
             HERE / "numerical-implementation-release-1.json"]
    return {p.relative_to(ROOT).as_posix(): dict(sha256=digest(p), bytes=p.stat().st_size) for p in paths}


def snapshot(sources, out):
    for rel, binding in sources.items():
        path = ROOT / rel
        expected = binding["sha256"]
        if digest(path) != expected:
            raise Refusal("source changed before snapshot")
        dest = Path(out) / "source-snapshot" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        if digest(dest) != expected:
            raise Refusal("source snapshot changed")


def execution_gate(path, expected, scope, sources):
    """Closed execution gate; exact root schema is confirmed before source freeze."""
    release = read_json(path, expected)
    if release.get("schema") != "m194g-numerical-execution-release-v1":
        raise Refusal("wrong numerical execution release")
    keys(release, ("schema", "scope", "source_bindings", "inputs", "commands"), "execution release")
    if release.get("scope") != scope:
        raise Refusal("execution scope mismatch")
    bindings = release["source_bindings"]
    for rel, binding in sources.items():
        if bindings.get(rel) != binding:
            raise Refusal("execution source mismatch: " + rel)
    for rel, binding in bindings.items():
        checked_ref(dict(path=rel, **binding))
    for item in release["inputs"]:
        checked_ref(item)
    command = list(sys.orig_argv)
    commands = [[expected if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in row]
                for row in release["commands"]]
    if command not in commands:
        raise Refusal("original interpreter command not released")
    return file_ref(path)


def checked_ref(ref):
    path = ROOT / ref["path"]
    if Path(ref["path"]).is_absolute() or ".." in Path(ref["path"]).parts or not path.resolve().is_relative_to(ROOT.resolve()):
        raise Refusal("invalid repository-relative reference")
    if digest(path) != ref["sha256"] or ("bytes" in ref and path.stat().st_size != ref["bytes"]):
        raise Refusal("bound reference mismatch: " + ref["path"])
    return path


def read_array(ref, shape, dtype, budget):
    path = ROOT / ref["path"]
    if Path(ref["path"]).is_absolute() or ".." in Path(ref["path"]).parts or not path.resolve().is_relative_to(ROOT.resolve()):
        raise Refusal("invalid array reference path")
    ceiling = math.prod(shape) * np.dtype(dtype).itemsize + 16384
    with path.open("rb") as stream:
        raw = stream.read(ceiling + 1)
    if len(raw) > ceiling or hashlib.sha256(raw).hexdigest() != ref["sha256"] or ("bytes" in ref and len(raw) != ref["bytes"]):
        raise Refusal("array byte binding/size mismatch")
    stream = io.BytesIO(raw)
    version = np.lib.format.read_magic(stream)
    if version == (1, 0):
        actual_shape, fortran, actual_dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=4096)
    elif version == (2, 0):
        actual_shape, fortran, actual_dtype = np.lib.format.read_array_header_2_0(stream, max_header_size=4096)
    else:
        raise Refusal("unsupported NPY version")
    if (any(type(v) is not int or v < 0 for v in actual_shape) or actual_shape != tuple(shape)
            or actual_dtype.str != dtype or actual_dtype.hasobject or fortran is not False
            or math.prod(actual_shape) * actual_dtype.itemsize != len(raw) - stream.tell()):
        raise Refusal("bounded NPY header/extent mismatch")
    stream.seek(0)
    array = np.load(stream, allow_pickle=False)
    if not isinstance(array, np.ndarray) or array.shape != tuple(shape) or array.dtype.str != dtype or stream.tell() != len(raw):
        raise Refusal("array dtype/shape/trailing data mismatch")
    budget.arrays(array)
    if not np.all(np.isfinite(array)):
        raise Refusal("nonfinite bound array")
    return array


def runtime():
    return dict(command=list(sys.argv), interpreter_argv=list(sys.orig_argv), executable=sys.executable,
                xoptions=dict(sys._xoptions), python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
                environment={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})


def render_frame(engine, prepared, width, height, out, stem, progress):
    shape = (height, width)
    values = np.full(shape, np.nan, dtype="<f8")
    errors = np.full(shape, np.nan, dtype="<f8")
    branches = np.full(shape, 255, dtype="u1")
    coverage = np.zeros(shape, dtype="u1")
    engine.budget.arrays(values, errors, branches, coverage, scalar_frame=values)
    count = 0
    try:
        for y in range(height):
            for x in range(width):
                if coverage[y, x]:
                    raise Refusal("duplicate native cell")
                value, receipt = engine.render(prepared, (x, y))
                values[y, x], errors[y, x] = value, receipt["absolute_error_indicator_e"]
                branches[y, x] = BRANCHES[receipt["branch"]]
                coverage[y, x] = 1
                count += 1
            engine.budget.check()
            write_json(progress, dict(status="RUNNING", stem=stem, completed=count,
                                      total=width * height, budget=engine.budget.receipt()))
        if count != width * height or not np.all(coverage == 1):
            raise Refusal("incomplete reference frame")
        if not np.all(np.isfinite(values)) or not np.all(np.isfinite(errors)) or np.any(errors < 0):
            raise Refusal("nonfinite reference frame")
        engine.budget.check()
        refs = {}
        for label, array in (("array", values), ("indicators", errors), ("branches", branches)):
            dest = Path(out) / f"{stem}-{label}.npy"
            np.save(dest, array, allow_pickle=False)
            refs[label] = file_ref(dest, array=array)
        return dict(**refs, completed_cells=count, shape=list(shape), dtype="<f8",
                    minimum_e=float(values.min()), maximum_e=float(values.max()),
                    maximum_indicator_e=float(errors.max()), engine=engine.receipt(),
                    indicator_scope_by_branch={"foreground": "conditional propagated spatial quadrature estimates",
                                               "background": "conditional propagated spatial quadrature estimates",
                                               "numerical": "frozen independent Cartesian quadrature estimate"},
                    analytic_phase_arithmetic_engineering_reservation_e=engine.target / 2)
    except Exception:
        for label, array in (("array", values), ("indicators", errors), ("branches", branches), ("coverage", coverage)):
            np.save(Path(out) / f"partial-{stem}-{label}.npy", array, allow_pickle=False)
        raise


def full_main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--arm", choices=tuple(TARGETS), required=True)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--controls-sha256", required=True)
    ap.add_argument("--execution-release", type=Path, required=True)
    ap.add_argument("--execution-release-sha256", required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    budget = Budget(start_cpu=ENTRY_CPU, start_wall=ENTRY_WALL)
    result = dict(schema="m194g-independent-reference-arm-v1", status="RUNNING", arm=args.arm,
                  ref_root="repository", repository_provenance=str(ROOT),
                  runtime=runtime(), frames=[], sources_before=source_map(), budget={},
                  exception=None, traceback=None, finalization_errors=[])
    try:
        snapshot(result["sources_before"], args.output)
        result["execution_release"] = execution_gate(args.execution_release, args.execution_release_sha256,
                                                     "full-reference-arm", result["sources_before"])
        controls = read_json(args.controls, args.controls_sha256)
        if controls.get("status") != "PASS_REFERENCE_COMPONENTS_ONLY" or controls.get("sources_before") != result["sources_before"] or controls.get("sources_after") != result["sources_before"]:
            raise Refusal("reference components not complete on current sources")
        if len(controls.get("baseline", [])) != 300:
            raise Refusal("missing component reference calls")
        result["controls"] = file_ref(args.controls)
        fixture = read_json(HERE / "fixture.json", FIXTURE_SHA)
        result["fixture"] = file_ref(HERE / "fixture.json")
        result["input"] = normalized(fixture)
        engine = Engine(budget, TARGETS[args.arm])
        for index, focus in zip(fixture["frame_indices"], fixture["inverse_foci"]):
            frame = dict(index=index, inverse_focus=focus, K=fixture["K"], forward_similarity=fixture["forward_similarity"])
            input_record = dict(scene=fixture["scene"], frame=frame, width=fixture["width"], height=fixture["height"])
            input_path = args.output / f"{args.arm}-{index}-input.json"
            write_json(input_path, normalized(input_record))
            require_input(read_json(input_path), input_record)
            prepared = prepare(fixture["scene"], frame)
            rec = render_frame(engine, prepared, fixture["width"], fixture["height"], args.output,
                               f"{args.arm}-{index}", args.output / "progress.json")
            result["frames"].append(dict(arm=args.arm, index=index, inverse_focus=focus, frame=frame,
                                         input=file_ref(input_path), **rec))
            result["budget"] = budget.receipt()
            write_json(args.output / "partial.json", result)
            print(json.dumps(dict(arm=args.arm, index=index, budget=budget.receipt())), flush=True)
        budget.check()
        if len(result["frames"]) != 5 or sum(v["completed_cells"] for v in result["frames"]) != 384000:
            raise Refusal("incomplete five-frame reference arm")
        result["status"] = "PASS_COMPLETE_REFERENCE_ARM_ONLY"
        result["authority"] = "one full reference arm only; cross-arm refinement and complete external comparison remain required"
    except Exception as exc:
        result["status"] = "UNCOMMISSIONED_REFERENCE"
        result["exception"], result["traceback"] = repr(exc), traceback.format_exc()
    finally:
        finalize(result, args.output, budget, "UNCOMMISSIONED_REFERENCE")
        print(json.dumps(dict(status=result["status"], sources_unchanged=result["sources_unchanged"])))
    return 0 if result["status"] == "PASS_COMPLETE_REFERENCE_ARM_ONLY" else 1


def finalize(result, out, budget, failure_status):
    """Preserve primary failure; secondary provenance/persistence faults are explicit."""
    result.setdefault("finalization_errors", [])
    try:
        result["sources_after"] = source_map()
        result["sources_unchanged"] = result["sources_before"] == result["sources_after"]
    except Exception as exc:
        result["sources_after"], result["sources_unchanged"] = None, False
        result["finalization_errors"].append(dict(stage="source-after", error=repr(exc)))
    if not result["sources_unchanged"]:
        result["status"] = failure_status
    result["budget"] = budget.receipt()
    path = Path(out) / "result.json"
    try:
        write_json(path, result)
        budget.check()
        result["budget"] = budget.receipt()
        write_json(path, result)
        # Include required final-result persistence in the elapsed admission check.
        budget.check()
    except Exception as exc:
        result["status"] = failure_status
        result["finalization_errors"].append(dict(stage="persistence-or-final-budget", error=repr(exc)))
        result["budget"] = budget.receipt()
        write_json(path, result)


if __name__ == "__main__":
    raise SystemExit(full_main())
