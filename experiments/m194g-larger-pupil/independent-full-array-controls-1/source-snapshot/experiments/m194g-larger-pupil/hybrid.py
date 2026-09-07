"""M194g author hybrid; immutable geometric model and numerical fallback."""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import asdict, replace
from fractions import Fraction
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import sys
import time

THREAD_VARIABLES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
for _thread_variable in THREAD_VARIABLES:
    os.environ[_thread_variable] = "2"
import numpy as np
import scipy
from scipy.special import j1

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PINS = {
    "pinned-loader.py": "222fab4a932fe236c120d8a48e4521747474e2ef57ba58781bf5c59f644f4f76",
    "geometry.py": "24b812071b8b6189423b9792a22c55abd9a4f4a78921a9d558ab24489f1923b3",
}
RELEASE_SHA = "77efbefaa876fe7d222a6a968d3233f0859df87924d49245431ba32eff239ba2"
CATALOG_SHA = "3814eeaf459e14a0a32e90ceeab6fc9d2994c92ee55bf17c824478accc3cbd41"
FIXTURE_SHA = "e84f0bbbda9bef039da86616c9f051d416929f4dbe78477cc5b3fc21206856bb"
BRANCHES = {"foreground": 0, "background": 1, "numerical": 2}
DIAGNOSTICS = ("value_error_indicator_e", "cell_indicator_e",
               "weighted_high_pupil_indicator_e", "cell_quadrature_delta_e")


def normalized(value):
    """One JSON representation, used before both persistence and comparison."""
    return json.loads(json.dumps(value, allow_nan=False))


def canonical(value):
    return (json.dumps(normalized(value), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_ref(path, root=None):
    path = Path(path).resolve(strict=True)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return dict(path=str(path) if root is None else path.relative_to(Path(root).resolve()).as_posix(),
                sha256=h.hexdigest(), bytes=path.stat().st_size)


def checked_bytes(path, expected=None, limit=4 * 1024 * 1024):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit or expected is not None and hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("bounded file/source binding mismatch: " + str(path))
    return raw


def load_module(path, name, expected):
    raw = checked_bytes(path, expected)
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    module.__checked_source__ = file_ref(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


LOADER = load_module(HERE / "pinned-loader.py", "m194g_hybrid_loader", PINS["pinned-loader.py"])
BOUND = LOADER.load_frozen()
MODEL, FALLBACK = BOUND.model, BOUND.render
GEOMETRY = load_module(HERE / "geometry.py", "m194g_hybrid_geometry", PINS["geometry.py"])


def strict_load(path, expected=None):
    return MODEL.strict_json_loads(checked_bytes(path, expected).decode("utf-8"))


def write_json(path, record):
    with Path(path).open("wb") as stream:
        stream.write(canonical(record))
        stream.flush()
        os.fsync(stream.fileno())


def source_bindings(extra=()):
    release_path = HERE / "numerical-implementation-release-1.json"
    release = strict_load(release_path, RELEASE_SHA)
    paths = {HERE / "hybrid.py", HERE / "pinned-loader.py", HERE / "geometry.py", release_path, *map(Path, extra)}
    for section in ("specifications", "cost_admission"):
        for ref in release[section]:
            path = ROOT / ref["path"]
            checked_bytes(path, ref["sha256"])
            if path.stat().st_size != ref["bytes"]:
                raise ValueError("release byte extent mismatch")
            paths.add(path)
    paths.update(Path(ref["path"]) for ref in BOUND.bindings.values())
    catalog = strict_load(HERE / "component-population.json", CATALOG_SHA)
    for case in catalog["cases"]:
        for ref in case.get("retained_reference", {}).values():
            if isinstance(ref, dict) and "path" in ref:
                path = ROOT / ref["path"]
                checked_bytes(path, ref["sha256"])
                paths.add(path)
    BOUND.assert_unchanged()
    for name, pin in PINS.items():
        checked_bytes(HERE / name, pin)
    return {str(path.resolve()): file_ref(path) for path in sorted(paths)}


class Budget:
    """One persistent component batch, or per-frame work in one full-image arm.

    The unchanged fallback Meter receives every actual point/node charge.
    Components never call its resetting new_frame. Both scopes share one clock.
    """
    def __init__(self, scope="components", observer="count", *, started_cpu=None, started_wall=None):
        if scope not in ("components", "full-arm"):
            raise ValueError("registered budget scope required")
        self.scope = scope
        self.limits = dict(points=16_000_000, nodes=2_400_000_000,
                           cpu=600 if scope == "components" else 1800,
                           wall=1200 if scope == "components" else 3600,
                           arrays=32 * 1024 * 1024, pairs=32768)
        self.base = FALLBACK.Meter(self.config_for(FALLBACK.integrator_for("primary")), observer)
        if started_cpu is not None:
            self.base.started_cpu = started_cpu
        if started_wall is not None:
            self.base.started_wall = started_wall
        self.total_points = self.total_nodes = self.frame_count = self.check_calls = 0
        self.hook_calls = 0
        self.collected = {}
        self.cache = OrderedDict()
        self.cache_limit = 20
        self.check()

    def config_for(self, integrator):
        return replace(integrator, point_limit=self.limits["points"], angular_limit=self.limits["nodes"],
                       cpu_limit=self.limits["cpu"], wall_limit=self.limits["wall"],
                       array_limit=self.limits["arrays"], node_pair_limit=self.limits["pairs"])

    def bind(self, integrator):
        self.base.config = self.config_for(integrator)
        # The unchanged fallback caches these owned rule arrays. Charge their
        # actual allocation once by underlying ndarray identity, including hits.
        for order in (integrator.angle_low, integrator.angle_high, integrator.cell_low, integrator.cell_high):
            self.watch(*FALLBACK.gauss(order))
        self.check()

    def observer(self, mode):
        if mode not in ("off", "count", "placebo"):
            raise ValueError("unknown observer")
        self.base.observer = mode

    def observe(self, event):
        if self.base.observer == "off":
            return
        self.hook_calls += 1
        if self.base.observer == "count":
            self.collected[event] = self.collected.get(event, 0) + 1

    def observe_cell(self, leaves):
        self.base.observe_cell(leaves)

    def check(self, points=0, nodes=0, pairs=0):
        if any(type(v) is not int or v < 0 for v in (points, nodes, pairs)):
            raise ValueError("nonnegative integer resource charges required")
        self.total_points += points
        self.total_nodes += nodes
        self.check_calls += 1
        self.base.check(points, nodes, pairs)

    def watch(self, *arrays):
        self.base.watch(*arrays)
        self.check()

    def frame(self, array):
        self.base.frame(array)
        self.check()

    def new_frame(self):
        self.check()
        self.frame_count += 1
        if self.scope == "full-arm":
            self.base.new_frame()
        # No reset at all in the component batch, including observer traversals.

    def receipt(self):
        return normalized(dict(scope=self.scope, limits=self.limits, **self.base.receipt(),
                               cumulative_point_calls=self.total_points, cumulative_angular_nodes=self.total_nodes,
                               frames_started=self.frame_count, check_calls=self.check_calls,
                               hybrid_hook_calls=self.hook_calls, hybrid_collection=dict(self.collected),
                               transfer_cache_entries=len(self.cache), transfer_cache_limit=self.cache_limit))


def field_from(record):
    if set(record) != {"constant", "affine", "waves"}:
        raise ValueError("exact field keys required")
    if any(set(w) != {"amplitude", "frequency", "phase"} for w in record["waves"]):
        raise ValueError("exact wave keys required")
    return MODEL.Field(record["constant"], tuple(record["affine"]),
                       tuple(MODEL.Wave(w["amplitude"], tuple(w["frequency"]), w["phase"]) for w in record["waves"]))


def scene_from(record):
    if set(record) != {"foreground", "background", "depths", "mask_normal", "mask_offset", "mask_state"}:
        raise ValueError("exact scene keys required")
    return MODEL.Scene(field_from(record["foreground"]), field_from(record["background"]),
                       tuple(record["depths"]), tuple(record["mask_normal"]), record["mask_offset"], record["mask_state"])


def frame_from(record):
    if set(record) != {"index", "inverse_focus", "K", "forward_similarity"}:
        raise ValueError("exact frame keys required")
    t = record["forward_similarity"]
    if set(t) != {"scale", "rotation", "centre", "translation"}:
        raise ValueError("exact similarity keys required")
    return MODEL.Frame(record["index"], record["inverse_focus"], record["K"],
                       MODEL.Similarity(t["scale"], t["rotation"], tuple(t["centre"]), tuple(t["translation"])))


def resolve_case(catalog, case):
    s = case["scene"]
    record = dict(foreground=catalog["fields"][s["foreground_field"]],
                  background=catalog["fields"][s["background_field"]],
                  **{k: s[k] for k in ("depths", "mask_normal", "mask_offset", "mask_state")})
    f = catalog["frames"][case["frame"]]
    return scene_from(record), frame_from(f), normalized(dict(scene=record, frame=f, native_xy=case["native_xy"]))


def load_catalog(path=HERE / "component-population.json"):
    catalog = strict_load(path, CATALOG_SHA)
    validate_catalog(catalog)
    return catalog


def validate_catalog(catalog):
    top = {"schema", "status", "derivation_label", "provenance", "counts", "fields", "frames", "cases", "numerical_targets",
           "independent_budgets", "active_fault_targets", "refusal_targets", "fault_policy", "author_component_budget",
           "observer_population", "resolved_design", "source_draft"}
    if set(catalog) != top:
        raise ValueError("exact registered catalog keys required")
    if catalog["schema"] != "m194g-component-population-v1" or catalog["status"] != "REGISTERED_COMPONENTS":
        raise ValueError("registered component schema required")
    ids = [c["id"] for c in catalog["cases"]]
    if len(ids) != 150 or len(set(ids)) != 150:
        raise ValueError("complete unique150-case population required")
    for case in catalog["cases"]:
        required = {"id", "call", "scene", "frame", "native_xy", "author_arms", "author_methods", "reference_arms", "group"}
        optional = {"coordinate_representation", "derived_centre", "derived_inverse_matrix", "evaluated_canonical_box", "evaluated_domain",
                    "expected", "expected_branch", "nominal_disc_argument", "parameter_derivation", "phase_derivation", "retained_reference",
                    "source_exact_height", "source_geometry_record", "radiance_bounds_e"}
        if not required <= set(case) or set(case) - required - optional or not isinstance(case["id"], str):
            raise ValueError("exact required/allowed case keys")
        if set(case["scene"]) != {"foreground_field", "background_field", "depths", "mask_normal", "mask_offset", "mask_state"}:
            raise ValueError("exact case scene keys")
        resolve_case(catalog, case)
        MODEL.pair(case["native_xy"], "native_xy")
        if case["call"] not in ("cell", "point"):
            raise ValueError("unknown component call")
        if not case["author_arms"] or len(set(case["author_arms"])) != len(case["author_arms"]):
            raise ValueError("unique nonempty component arms required")
        for arm in case["author_arms"]:
            FALLBACK.integrator_for(arm)
        wanted = ["frozen-point"] if case["call"] == "point" else ["analytic-enabled", "analytic-disabled"]
        if case["author_methods"] != wanted:
            raise ValueError("exact component methods required")
        if case["reference_arms"] != ["primary", "refined"]:
            raise ValueError("both independent reference arms required")
        if "radiance_bounds_e" in case:
            MODEL.pair(case["radiance_bounds_e"], "radiance_bounds_e")
    if sum(c["call"] == "cell" for c in catalog["cases"]) != 149 or sum(c["call"] == "point" for c in catalog["cases"]) != 1:
        raise ValueError("case call population mismatch")


class DefocusOverride:
    def __init__(self, frame, kind):
        self.original, self.kind = frame, kind
        self.forward_similarity = frame.forward_similarity

    def defocus(self, scene):
        df, db = self.original.defocus(scene)
        return (db, db) if self.kind == "background" else (abs(df), db)


def select_branch(scene, frame, xy, meter, fault=None):
    fid = None if fault is None else fault["id"]
    placed = DefocusOverride(frame, "background") if fid == "wrong-background-visibility-radius" else frame
    selector = GEOMETRY.ExactSelector(scene, placed, budget=meter)
    if fid == "missing-cell-visibility-support" and not selector.unsupported_reason:
        selector._ints = (*selector._ints[:3], 0)
        selector._coefficients["half"] = Fraction(0)
    return selector.classify(xy), selector.unsupported_reason


def sinc(value):
    return 1.0 if value == 0 else math.sin(value) / value


def analytic_value(scene, frame, xy, branch, meter, fault=None):
    fid = None if fault is None else fault["id"]
    field = scene.foreground if branch == "foreground" else scene.background
    if fid == "swapped-field":
        field = MODEL.Field(15000)
    displacement = frame.defocus(scene)[0 if branch == "foreground" else 1]
    matrix = frame.forward_similarity.inverse_matrix()
    coordinate = np.asarray(xy, dtype=np.float64).reshape(1, 2)
    q0 = frame.forward_similarity.inverse(coordinate)[0]
    if fid == "chief-ray-native-as-canonical":
        q0 = coordinate[0]
    meter.watch(matrix, coordinate, q0)
    terms = [field.constant, field.affine[0] * float(q0[0]), field.affine[1] * float(q0[1])]
    waves = []
    for wave in field.waves:
        omega = np.array(wave.frequency, dtype=float) * (2 * math.pi)
        k = (matrix if fid == "transpose-native-frequency" else matrix.T) @ omega
        argument = abs(displacement) * math.hypot(float(k[0]), float(k[1]))
        key = digest(dict(matrix=matrix.tolist(), omega=omega.tolist(), native_wave_vector=k.tolist(), displacement=displacement,
                          frequency=wave.frequency, field=asdict(field), formula="disc-sinc-v1"))
        consumed_key = fault["primed_key"] if fid == "stale-frequency-cache" else key
        if consumed_key in meter.cache:
            factors = meter.cache[consumed_key]
            hit = True
            meter.cache.move_to_end(consumed_key)
        elif fid == "stale-frequency-cache":
            raise ValueError("registered stale-cache prime missing")
        else:
            disc = 1.0 if argument == 0 else float(2 * j1(argument) / argument)
            factors = (disc, sinc(float(k[0]) / 2), sinc(float(k[1]) / 2))
            meter.cache[key] = factors
            if len(meter.cache) > meter.cache_limit:
                meter.cache.popitem(last=False)
            hit = False
        disc, sx, sy = factors
        if fid == "zero-over-zero" and argument == 0:
            with np.errstate(divide="ignore", invalid="ignore"):
                disc = float(np.divide(2 * j1(argument), argument))
        if fid == "abs-disc-transfer":
            disc = abs(disc)
        if fid == "clamp-disc-transfer":
            disc = max(disc, 0.)
        if fid == "always-unit-disc":
            disc = 1.
        if fid == "omit-square-factor":
            sx = sy = 1.
        field_phase = fault["primed_phase"] if fid == "cached-phase-zero" else wave.phase
        phase = float(omega @ q0) + field_phase
        contribution = wave.amplitude * math.cos(phase) * disc * sx * sy
        if not all(math.isfinite(v) for v in (argument, disc, sx, sy, phase, contribution)):
            raise FALLBACK.NumericalFailure("UNCOMMISSIONED_NUMERICS: nonfinite analytic transfer")
        terms.append(contribution)
        meter.observe("wave:" + branch + (":zero-defocus" if displacement == 0 else ":nonzero-defocus"))
        meter.observe("signed-wave:" + branch + (":zero" if displacement == 0 else ":negative" if displacement < 0 else ":positive"))
        meter.observe("cache-hit" if hit else "cache-miss")
        meter.watch(omega, k)
        waves.append(dict(argument=argument, displacement=displacement, native_wave_vector=k.tolist(),
                          factors=[disc, sx, sy], phase=phase, field_phase=field_phase,
                          cache_key=key, consumed_cache_key=consumed_key, contribution_e=contribution))
    value = math.fsum(terms)
    if fid == "omit-pupil-normalization":
        value *= math.pi
    if not math.isfinite(value) or value < 0:
        raise FALLBACK.NumericalFailure("UNCOMMISSIONED_NUMERICS: invalid analytic scalar")
    meter.check()
    return value, dict(method="uniform-disc-j1-native-cell-sinc-v1", error_scope="no adaptive indicator for analytic evaluation; external error bars apply",
                       selected_layer=branch, selected_defocus=displacement, canonical_centre=q0.tolist(), waves=waves)


def render_cell(scene, frame, native_xy, integrator, meter, *, analytic=True, fault=None):
    meter.bind(integrator)
    branch, unsupported = select_branch(scene, frame, native_xy, meter, fault)
    selected = branch if analytic else "numerical"
    if fault is not None and fault["id"] == "separate-cell-means":
        alpha_scene = replace(scene, foreground=MODEL.Field(1), background=MODEL.Field(0))
        alpha, ar = FALLBACK.render_cell(alpha_scene, frame, native_xy, integrator, meter)
        fg, fr = FALLBACK.render_cell(replace(scene, mask_state="full"), frame, native_xy, integrator, meter)
        bg, br = FALLBACK.render_cell(replace(scene, mask_state="absent"), frame, native_xy, integrator, meter)
        return alpha * fg + (1 - alpha) * bg, dict(branch="numerical", selector_branch=branch,
                                                  active_fault=fault["id"], independent_mean_receipts=[ar, fr, br])
    if selected != "numerical":
        value, transfer = analytic_value(scene, frame, native_xy, selected, meter, fault)
        receipt = dict(branch=selected, selector_branch=branch, transfer=transfer)
    else:
        value, numerical = FALLBACK.render_cell(scene, frame, native_xy, integrator, meter)
        receipt = dict(branch="numerical", selector_branch=branch, fallback=numerical)
    meter.observe("cell:" + selected)
    receipt.update(unsupported_selector_reason=unsupported, active_fault=None if fault is None else fault["id"])
    return value, normalized(receipt)


def render_point(scene, frame, native_xy, integrator, meter, *, fault=None):
    meter.bind(integrator)
    actual = DefocusOverride(frame, "absolute") if fault is not None and fault["id"] == "relative-sign" else frame
    value, receipt = FALLBACK.render_point(scene, actual, native_xy, integrator, meter)
    return value, normalized(dict(branch="point", fallback=receipt, active_fault=None if fault is None else fault["id"]))


def validate_arrays(values, branches, indices, diagnostics, meter=None):
    if values.dtype.str != "<f8" or values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("finite little-endian scalar frame required")
    if branches.dtype.str != "|u1" or branches.shape != values.shape or not np.isin(branches, (0, 1, 2)).all():
        raise ValueError("complete valid branch frame required")
    if indices.dtype.str != "<u4" or indices.ndim != 1 or np.any(indices[1:] <= indices[:-1]):
        raise ValueError("sorted unique u32 fallback indices required")
    expected = np.flatnonzero(branches.reshape(-1) == 2)
    if meter is not None:
        meter.watch(expected, values, branches, indices, diagnostics)
    if not np.array_equal(indices, expected):
        raise ValueError("fallback index set must equal actual numerical branches")
    if diagnostics.dtype.str != "<f8" or diagnostics.shape != (len(indices), 4) or not np.isfinite(diagnostics).all() or np.any(diagnostics < 0):
        raise ValueError("finite nonnegative four-column diagnostics required")
    if not np.array_equal(diagnostics[:, 0], diagnostics[:, 1] + diagnostics[:, 2]):
        raise ValueError("fallback indicator column correspondence mismatch")


def array_ref(path, array, root):
    return dict(**file_ref(path, root), dtype=array.dtype.str, shape=list(array.shape))


def render_frame(scene, frame, width, height, integrator, meter, output, *, traversal="row-major", source_set=None, coordinates=None):
    if type(width) is not int or type(height) is not int or not 0 < width <= 320 or not 0 < height <= 240:
        raise ValueError("registered bounded frame dimensions required")
    if traversal not in ("row-major", "reverse-row-major"):
        raise ValueError("registered traversal required")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    meter.bind(integrator)
    meter.new_frame()
    before = meter.receipt()
    values = np.full((height, width), np.nan, dtype="<f8")
    branches = np.full((height, width), 255, dtype="u1")
    # Bounded native-index slots avoid sort copies; only numerical rows emitted.
    slots = np.full((width * height, 4), np.nan, dtype="<f8")
    meter.frame(values)
    meter.watch(branches, slots)
    order = range(width * height) if traversal == "row-major" else range(width * height - 1, -1, -1)
    if coordinates is not None:
        order = coordinates(width, height)
    completed = 0
    trace = hashlib.sha256()
    inputs = normalized(dict(scene=asdict(scene), frame=asdict(frame), width=width, height=height,
                             arm=integrator.arm, method="analytic-enabled"))
    try:
        for index in order:
            meter.check()
            if type(index) is not int or not 0 <= index < width * height or branches.flat[index] != 255:
                raise ValueError("duplicate/out-of-range native coordinate")
            y, x = divmod(index, width)
            value, receipt = render_cell(scene, frame, (x, y), integrator, meter)
            branch = BRANCHES[receipt["branch"]]
            values[y, x], branches[y, x] = value, branch
            if branch == 2:
                slots[index] = [receipt["fallback"][key] for key in DIAGNOSTICS]
            completed += 1
            trace.update(index.to_bytes(4, "little"))
        if completed != width * height:
            raise ValueError("incomplete native coordinate coverage")
        indices = np.flatnonzero(branches.reshape(-1) == 2).astype("<u4")
        diagnostics = slots[indices].astype("<f8", copy=False)
        meter.watch(indices, diagnostics, slots, branches, values)
        validate_arrays(values, branches, indices, diagnostics, meter)
        refs = {}
        for name, array in (("scalar", values), ("branch", branches), ("fallback_indices", indices), ("fallback_diagnostics", diagnostics)):
            path = output / (name.replace("_", "-") + ".npy")
            np.save(path, array, allow_pickle=False)
            refs[name] = array_ref(path, array, output)
        receipt = dict(schema="m194g-author-frame-v1", status="complete-uncommissioned", inputs=inputs,
                       source_set_sha256=source_set, arrays=refs, diagnostic_columns=list(DIAGNOSTICS), branch_codes=BRANCHES,
                       analytic_error_scope="no adaptive indicator; independent scalar comparison required",
                       completed_cells=completed, traversal=traversal, traversal_sha256=trace.hexdigest(),
                       work_before=before, work_after=meter.receipt())
        meter.check()
        write_json(output / "receipt.json", receipt)
        return file_ref(output / "receipt.json")
    except Exception as exc:
        np.save(output / "scalar-partial.npy", values, allow_pickle=False)
        np.save(output / "branch-partial.npy", branches, allow_pickle=False)
        write_json(output / "failure.json", dict(status="UNCOMMISSIONED_NUMERICS", error=repr(exc), inputs=inputs,
                   completed_cells=completed, work=meter.receipt()))
        raise


def read_frame(receipt_path, expected_inputs, meter, *, expected_hash=None, verify_hash=True):
    receipt_path = Path(receipt_path).resolve()
    receipt = strict_load(receipt_path, expected_hash)
    if set(receipt) != {"schema", "status", "inputs", "source_set_sha256", "arrays", "diagnostic_columns", "branch_codes",
                        "analytic_error_scope", "completed_cells", "traversal", "traversal_sha256", "work_before", "work_after"}:
        raise ValueError("exact frame receipt keys required")
    if receipt.get("schema") != "m194g-author-frame-v1" or receipt.get("status") != "complete-uncommissioned" or canonical(receipt["inputs"]) != canonical(expected_inputs):
        raise ValueError("frame input/schema binding mismatch")
    inputs = receipt["inputs"]
    if set(inputs) != {"scene", "frame", "width", "height", "arm", "method"}:
        raise ValueError("exact frame input keys required")
    scene_from(inputs["scene"])
    frame_from(inputs["frame"])
    FALLBACK.integrator_for(inputs["arm"])
    if inputs["method"] != "analytic-enabled" or receipt["traversal"] not in ("row-major", "reverse-row-major"):
        raise ValueError("registered method/traversal required")
    for name, maximum in (("width", 320), ("height", 240)):
        if type(inputs[name]) is not int or not 0 < inputs[name] <= maximum:
            raise ValueError("strict native extent required")
    if type(receipt["completed_cells"]) is not int or receipt["completed_cells"] != inputs["width"] * inputs["height"]:
        raise ValueError("strict completed coverage required")
    if receipt["diagnostic_columns"] != list(DIAGNOSTICS) or canonical(receipt["branch_codes"]) != canonical(BRANCHES):
        raise ValueError("diagnostic/branch contract mismatch")
    arrays = []
    if set(receipt["arrays"]) != {"scalar", "branch", "fallback_indices", "fallback_diagnostics"}:
        raise ValueError("exact four array references required")
    for name in ("scalar", "branch", "fallback_indices", "fallback_diagnostics"):
        ref = receipt["arrays"][name]
        if set(ref) != {"path", "sha256", "bytes", "dtype", "shape"} or type(ref["bytes"]) is not int or ref["bytes"] < 0:
            raise ValueError("exact typed array reference required")
        if not isinstance(ref["shape"], list) or any(type(x) is not int or x < 0 for x in ref["shape"]):
            raise ValueError("strict array shape required")
        path = receipt_path.parent / ref["path"]
        if Path(ref["path"]).is_absolute() or path.resolve().parent != receipt_path.parent:
            raise ValueError("direct relative array path required")
        raw = checked_bytes(path, ref["sha256"] if verify_hash else None)
        if len(raw) != ref["bytes"]:
            raise ValueError("array extent mismatch")
        # Inspect and consume the same bounded, hashed bytes. Header dimensions
        # cannot cause an allocation before the exact payload extent is checked.
        stream = io.BytesIO(raw)
        if np.lib.format.read_magic(stream) != (1, 0):
            raise ValueError("NPY v1 required")
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=4096)
        permitted = {"scalar": "<f8", "branch": "|u1", "fallback_indices": "<u4", "fallback_diagnostics": "<f8"}
        if fortran or dtype.str != permitted[name] or list(shape) != ref["shape"] or dtype.str != ref["dtype"]:
            raise ValueError("bounded NPY header mismatch")
        if any(type(x) is not int or x < 0 for x in shape) or math.prod(shape) * dtype.itemsize != len(raw) - stream.tell():
            raise ValueError("exact NPY payload extent required")
        array = np.frombuffer(raw, dtype=dtype, count=math.prod(shape), offset=stream.tell()).reshape(shape).copy()
        if array.dtype.str != ref["dtype"] or list(array.shape) != ref["shape"]:
            raise ValueError("array dtype/shape mismatch")
        arrays.append(array)
        meter.watch(*arrays)
    if arrays[0].shape != (expected_inputs["height"], expected_inputs["width"]):
        raise ValueError("native array extent mismatch")
    validate_arrays(*arrays, meter=meter)
    meter.check()
    return receipt, arrays
