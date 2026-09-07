"""Independent analytic-x / split-y K=0 target check; no optical helper imports."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import sys
import traceback
import warnings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREFIX = "experiments/m194g-larger-pupil/"
FIXTURE_SHA = "e84f0bbbda9bef039da86616c9f051d416929f4dbe78477cc5b3fc21206856bb"
FLOAT_SHA = "3f18d8954347382b2dffe0ca501f93ef8da54c3b966a1a606851323d86277a2b"
CELLS = ((142, 0), (142, 1), (143, 7), (150, 53), (151, 64), (152, 64),
         (159, 117), (160, 117), (169, 179), (178, 239))
REQUEST = 1e-7
METHOD = "analytic-x-split-y-quad-k0-v1"
F = C = np = quad = None
SCIPY_VERSION = None


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sinc(value):
    return 1.0 if value == 0.0 else math.sin(value) / value


def x_integral(field, left, right, y):
    """Cosine antiderivative in midpoint form; no polygon/Fourier helper."""
    width = right - left
    need(math.isfinite(width) and width >= 0, "invalid x interval")
    if width == 0:
        return 0.0
    midpoint = left + width * 0.5
    gx, gy = field["affine"]
    terms = [width * (field["constant"] + gx * midpoint + gy * y)]
    for wave in field["waves"]:
        fx, fy = wave["frequency"]
        terms.append(wave["amplitude"] * width * sinc(math.pi * fx * width)
                     * math.cos(2 * math.pi * (fx * midpoint + fy * y) + wave["phase"]))
    return math.fsum(terms)


def integrate_cell(scene, xy, budget, *, fault=None, record=None):
    """Each call owns one fixed absolute request, shared over its y pieces."""
    need(fault in (None, "shift-x", "centre-mask", "unweighted-alpha", "separate-alpha"), "unknown K0 fault")
    x, y = map(float, xy)
    if fault == "shift-x":
        x += 1.0
    nx, ny = scene["mask_normal"]
    offset = scene["mask_offset"]
    need(nx == 1.0 and math.isfinite(ny) and math.isfinite(offset), "independent K0 requires n_x1")
    need(scene["mask_state"] == "half-plane", "independent K0 requires half-plane")
    xl, xr, yl, yr = x - .5, x + .5, y - .5, y + .5
    crossings = []
    if ny != 0.0:
        crossings = [(offset - edge) / ny for edge in (xl, xr)]
    breaks = sorted({yl, yr, *(cut for cut in crossings if yl < cut < yr)})
    pieces = []
    branch_calls = dict(foreground=0, background=0, mixed=0)
    callback_calls = 0
    if record is None:
        record = {}
    record.update(native_xy=list(xy), evaluated_xy=[x, y], fault=fault, value_e=None,
                  indicator_e=None, absolute_request_e=REQUEST, y_breaks=breaks,
                  pieces=pieces, callback_calls=0, branch_calls=branch_calls)

    def integrand(at_y):
        nonlocal callback_calls
        budget.check()
        callback_calls += 1
        record["callback_calls"] = callback_calls
        cut = min(xr, max(xl, offset - ny * at_y))
        branch = "foreground" if cut == xl else "background" if cut == xr else "mixed"
        branch_calls[branch] += 1
        fg, bg = scene["foreground"], scene["background"]
        if fault == "centre-mask":
            value = x_integral(fg if x + ny * y >= offset else bg, xl, xr, at_y)
        elif fault == "unweighted-alpha":
            value = x_integral(fg, xl, xr, at_y) + x_integral(bg, xl, xr, at_y)
        elif fault == "separate-alpha":
            # Unit-width cell: these lengths are its slice visibility weights.
            value = ((xr - cut) * x_integral(fg, xl, xr, at_y)
                     + (cut - xl) * x_integral(bg, xl, xr, at_y))
        else:
            value = x_integral(bg, xl, cut, at_y) + x_integral(fg, cut, xr, at_y)
        need(math.isfinite(value), "nonfinite K0 callback")
        return value

    allocation = REQUEST / (len(breaks) - 1)
    for low, high in zip(breaks[:-1], breaks[1:]):
        budget.check()
        before = callback_calls
        piece = dict(low=low, high=high, value_e=None, indicator_e=None,
                     epsabs=allocation, epsrel=0.0, limit=128, callbacks=0, error=None)
        pieces.append(piece)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                returned = quad(integrand, low, high, epsabs=allocation, epsrel=0.0,
                                limit=128, full_output=1)
            if type(returned) is tuple and len(returned) >= 3 and type(returned[2]) is dict:
                budget.watch(*(v for v in returned[2].values() if type(v) is np.ndarray))
            need(type(returned) is tuple and len(returned) == 3,
                 "K0 quadrature nonterminal status: " + repr(returned[3:] if isinstance(returned, tuple) else returned))
            value, indicator, info = returned
            need(math.isfinite(value) and math.isfinite(indicator), "K0 nonfinite quadrature value/indicator")
            piece.update(value_e=float(value), indicator_e=float(indicator))
            need(0 <= indicator <= allocation, "K0 quadrature indicator exceeds piece request")
            actual = callback_calls - before
            need(actual > 0 and type(info.get("neval")) is int and info["neval"] == actual,
                 "K0 callback/neval mismatch")
        except Exception as exc:
            piece["error"] = dict(type=type(exc).__name__, message=str(exc))
            raise
        finally:
            piece["callbacks"] = callback_calls - before
    value = math.fsum(p["value_e"] for p in pieces)
    error = math.fsum(p["indicator_e"] for p in pieces)
    need(math.isfinite(value) and error <= REQUEST, "K0 complete-cell indicator failed")
    budget.check()
    record.update(value_e=value, indicator_e=error)
    return record


def field(constant, gx=0.0, gy=0.0, waves=()):
    return dict(constant=constant, affine=[gx, gy], waves=list(waves))


def scene(fg, bg, *, ny=0.0, offset=.1):
    return dict(mask_normal=[1.0, ny], mask_offset=offset, mask_state="half-plane",
                foreground=fg, background=bg)


def private_controls(budget, record):
    rows, faults = [], []
    record.update(schema="m194g-independent-k0-private-controls-v1", status="UNCOMMISSIONED_PRIVATE_K0_CONTROLS",
                  literal_oracles=rows, faults=faults, calls=[], check_count=0)

    def call(name, s, fault=None):
        row = dict(name=name, scene=s, native_xy=[0, 0], fault=fault, result={}, error=None)
        record["calls"].append(row)
        try:
            integrate_cell(s, (0, 0), budget, fault=fault, record=row["result"])
            return row["result"]
        except Exception as exc:
            row["error"] = dict(type=type(exc).__name__, message=str(exc))
            raise

    def oracle(name, s, expected, limit=1e-8):
        result = call(name, s)
        discrepancy = abs(Fraction.from_float(result["value_e"]) - expected)
        row = dict(name=name, kind="literal-oracle", expected_fraction=str(expected),
                   actual=result, absolute_error_e=float(discrepancy), limit_e=limit,
                   passed=discrepancy <= Fraction.from_float(limit))
        rows.append(row)
        need(row["passed"], "independent K0 literal oracle failed: " + name)
        return result

    oracle("constant-foreground", scene(field(30), field(10), offset=-2), Fraction(30))
    oracle("affine-background", scene(field(30), field(10, 4), offset=2), Fraction(10))
    vertical = scene(field(30), field(10, 4))
    baseline = oracle("vertical-coupled", vertical, Fraction(438, 25))
    need(baseline["branch_calls"]["mixed"] > 0, "vertical oracle did not exercise mixed visibility")
    oracle("vertical-reversed-gradient", scene(field(30), field(10, -4)), Fraction(462, 25))
    diagonal = oracle("diagonal-coupled", scene(field(30), field(10, 4), ny=1, offset=0), Fraction(59, 3))
    need(diagonal["branch_calls"]["mixed"] > 0, "diagonal oracle did not exercise mixed visibility")
    wave_scene = None
    for name, fx, fy in (("wave", .125, .0625), ("negative-sinc", 1.5, .0625), ("zero-fx", 0.0, .0625)):
        w = dict(amplitude=7.0, frequency=[fx, fy], phase=.3)
        s = scene(field(100, waves=[w]), field(10), offset=-2)
        # This full-rectangle separable scalar formula is distinct from the
        # callback's clipped x integral followed by adaptive y quadrature.
        expected = 100 + 7 * sinc(math.pi * fx) * sinc(math.pi * fy) * math.cos(.3)
        oracle(name, s, Fraction.from_float(expected), 1e-7)
        if name == "wave":
            wave_scene = s
        if name == "negative-sinc":
            need(sinc(math.pi * fx) < 0, "negative sinc control unpowered")
    for fault, s in (("shift-x", wave_scene), ("centre-mask", vertical),
                     ("unweighted-alpha", vertical), ("separate-alpha", vertical)):
        before = call(fault + "-baseline", s)
        active = call(fault + "-active", s, fault)
        restored = call(fault + "-restored", s)
        difference = abs(active["value_e"] - before["value_e"])
        same = struct.pack("<d", before["value_e"]) == struct.pack("<d", restored["value_e"])
        row = dict(name=fault, kind="active-restored", baseline=before, active=active,
                   restored=restored, absolute_change_e=difference, restored_bytes_equal=same,
                   passed=math.isfinite(difference) and difference > .004 and same)
        faults.append(row)
        need(row["passed"], "independent K0 fault unpowered: " + fault)
    record.update(status="PASS_PRIVATE_K0_CONTROLS", check_count=len(rows) + len(faults))
    return record


def bootstrap(args):
    global F, C, np, quad, SCIPY_VERSION
    need(time.process_time() - ENTRY_CPU <= 120 and time.monotonic() - ENTRY_WALL <= 240, "K0 entry time budget")
    with Path(args.execution_release).open("rb") as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    need(len(raw) <= 16 * 1024 * 1024 and hashlib.sha256(raw).hexdigest() == args.execution_release_sha256,
         "K0 external execution release pin")
    release = json.loads(raw)
    reuse = PREFIX + "independent-full-array-reader.py"
    wanted = release["source_bindings"][reuse]
    with (ROOT / reuse).open("rb") as stream:
        source = stream.read(1024 * 1024 + 1)
    need(len(source) <= 1024 * 1024 and dict(sha256=hashlib.sha256(source).hexdigest(), bytes=len(source)) == wanted,
         "K0 reused reader source pin")
    spec = importlib.util.spec_from_loader("m194g_k0_file_utilities", loader=None, origin=str(ROOT / reuse))
    F = importlib.util.module_from_spec(spec)
    F.__file__ = str(ROOT / reuse)
    sys.modules[spec.name] = F
    exec(compile(source, F.__file__, "exec"), F.__dict__)
    release = F.bootstrap(args.execution_release, args.execution_release_sha256, "independent-k0-target", sys.orig_argv)
    C, np = F.C, F.np
    for name in ("independent-k0-target.py", "independent-k0-target-design.md", "independent-full-array-reader.py",
                 "independent-component-reader.py", "next-quality-target-interface.md"):
        need(PREFIX + name in release["source_bindings"], "K0 source closure lacks " + name)
    budget = F.Budget(started_cpu=ENTRY_CPU, started_wall=ENTRY_WALL)
    reads = F.make_reads(budget)
    # Retain every release source/input in the actual finalization ledger.
    C.read_execution(reads, args.execution_release, args.execution_release_sha256,
                     scope="independent-k0-target", argv=sys.orig_argv)
    for path, sha in ((args.target, args.target_sha256), (args.float_commission, args.float_commission_sha256)):
        actual = str(Path(path).resolve())
        need(reads.observed.get(actual, {}).get("sha256") == sha, "K0 actual prerequisite absent from release")
    from scipy.integrate import quad as scipy_quad
    from scipy import __version__ as scipy_version
    quad = scipy_quad
    SCIPY_VERSION = scipy_version
    budget.check()
    return release, budget, reads


def target_metadata(reads, path, sha, float_path, float_sha, release, budget):
    target = reads.external(path, sha)
    C.keys(target, ("schema", "status", "ref_root", "upstream_ref_root", "fixture", "float_commission", "scalar",
                    "geometry", "method", "controls", "sources_before", "sources_after", "runtime", "work",
                    "error", "finalization_errors", "execution_release", "invocation"), "K0 target")
    need(target["schema"] == "m194g-quality-target-v1" and target["status"] == "COMPLETE_K0_TARGET_UNCOMMISSIONED"
         and target["error"] is None and target["finalization_errors"] == [], "K0 target failed/incomplete")
    need(target["ref_root"] == "target-parent" and target["upstream_ref_root"] == "repository"
         and target["method"] == "m194g-k0-clipped-cell-v1", "K0 target model/root")
    fixture = C.strict_json(reads.bound(ROOT, target["fixture"]))
    need(target["fixture"]["sha256"] == FIXTURE_SHA, "K0 fixed fixture pin")
    floats = reads.external(float_path, float_sha)
    need(float_sha == FLOAT_SHA and floats["schema"] == "m194g-float-commission-v1"
         and floats["status"] == "PASS_COMPLETE_FLOAT_MODEL" and floats["fixture"] == target["fixture"],
         "K0 genuine full-float prerequisite")
    fp = C.relative_path(ROOT, target["float_commission"]["path"])
    need(fp == Path(float_path).resolve() and target["float_commission"]["sha256"] == float_sha,
         "K0 target float association")
    reads.bound(ROOT, target["float_commission"])
    expected = dict(width=320, height=240, native_origin=[0, 0], cell="integer-centre-unit-square",
                    units="expected-electrons", K=0.0, forward_similarity=fixture["forward_similarity"])
    C.equal_record(target["geometry"], expected, "K0 target geometry")
    for key in ("width", "height"):
        need(type(target["geometry"][key]) is int, "K0 geometry integer type")
    need(all(type(v) is int for v in target["geometry"]["native_origin"]), "K0 native origin integer type")
    need(fixture["scene"]["mask_normal"] == [1.0, -.15] and fixture["scene"]["mask_offset"] == 142,
         "K0 fixed half-plane changed")
    C.equal_record(target["sources_before"], target["sources_after"], "K0 producer source before/after")
    need(type(target["sources_before"]) is dict and target["sources_before"], "K0 producer sources absent")
    for name, binding in target["sources_before"].items():
        reads.bound(ROOT, dict(path=name, **binding))
    controls_raw = reads.bound(Path(path).parent, target["controls"])
    controls = C.strict_json(controls_raw)
    # Read the concrete controller child, never just a pass-string envelope.
    validate_target_controller(target, controls, reads, Path(path), release)
    scalar, raw = reads.array(Path(path).parent, target["scalar"], "<f8", (240, 320))
    finite = np.isfinite(scalar)
    budget.watch(scalar, finite)
    need(bool(finite.all()) and float(scalar.min()) >= 0, "K0 target scalar finite/nonnegative")
    return target, fixture, scalar


def validate_target_controller(target, controls, reads, target_path, _release):
    ids = ("constant-full-foreground", "constant-full-background", "constant-mixed", "vertical-affine",
           "oblique-affine", "centre-mask-live", "separate-alpha-live", "coupled-restored", "fourier-zero",
           "fourier-full-x", "fourier-negative-sinc", "fourier-two-dimensional", "translated-phase-live",
           "translated-phase-restored", "nonfinite-refuses", "empty-normal-refuses")
    C.keys(controls, ("schema", "status", "checks", "error"), "K0 local controls")
    need(controls["schema"] == "m194g-quality-target-controls-v1"
         and controls["status"] == "PASS_LOCAL_K0_CONTROLS_ONLY" and controls["error"] is None,
         "K0 local target controls failed")
    need(type(controls["checks"]) is list and len(controls["checks"]) == len(ids), "K0 local checks incomplete")
    for expected, check in zip(ids, controls["checks"]):
        C.keys(check, ("id", "passed", "details"), "K0 local check")
        need(check["id"] == expected and check["passed"] is True and type(check["details"]) is dict,
             "K0 local check failed or reordered")
    runtime = target["runtime"]
    C.keys(runtime, ("python", "numpy", "scipy", "thread_environment", "executable", "cwd"), "K0 target runtime")
    need(all(type(runtime[k]) is str and runtime[k] for k in ("python", "numpy", "scipy", "executable", "cwd")),
         "K0 target runtime string types")
    C.equal_record(runtime["thread_environment"], {k: "2" for k in F.THREADS}, "K0 target threads")
    invocation = target["invocation"]
    C.keys(invocation, ("orig_argv", "argv", "xoptions"), "K0 target invocation")
    need(all(type(invocation[k]) is list and invocation[k] and all(type(s) is str for s in invocation[k])
             for k in ("orig_argv", "argv")) and type(invocation["xoptions"]) is dict, "K0 invocation types")
    release = C.strict_json(reads.bound(ROOT, target["execution_release"]))
    C.keys(release, ("schema", "scope", "source_bindings", "inputs", "commands"), "K0 target release")
    need(release["schema"] == "m194g-quality-execution-release-v1" and release["scope"] == "target", "K0 target release scope")
    C.equal_record(release["source_bindings"], target["sources_before"], "K0 target released source closure")
    for name, ref in release["source_bindings"].items():
        reads.bound(ROOT, dict(path=name, **ref))
        reads.bound(target_path.parent / "sources", dict(path=name, **ref))
    dependencies = {PREFIX + name for name in ("independent-quality-target.py", "independent-quality-io.py",
                                               "independent-quality-metrics.py", "software-noise-authority.py")}
    dependencies.add("experiments/m194e-joint-pupil/independent-model.py")
    need(set(release["source_bindings"]) == dependencies
         and release["source_bindings"].get("experiments/m194e-joint-pupil/independent-model.py", {}).get("sha256")
         == "0cd8ea2331b269e65befdee110560cbc345e89c12348cbe1dc3144f7c04443f0", "K0 declared target dependencies missing")
    need(type(release["inputs"]) is list and release["inputs"], "K0 target release inputs missing")
    seen = set()
    for ref in release["inputs"]:
        name = str(C.relative_path(ROOT, ref["path"])).casefold()
        need(name not in seen, "K0 duplicate target release input")
        seen.add(name)
        reads.bound(ROOT, ref, limit=C.MAX_ARRAY + 4096)
    for key in ("fixture", "float_commission"):
        need(target[key] in release["inputs"], "K0 target prerequisite absent from its release: " + key)
    for name in ("next-quality-reader-preregister.md", "next-quality-target-interface.md",
                 "independent-full-float-authority-schema.md"):
        need(str((ROOT / PREFIX / name).resolve()).casefold() in seen,
             "K0 target protocol absent from released inputs: " + name)
    need(type(release["commands"]) is list and release["commands"], "K0 target commands missing")
    commands = []
    for command in release["commands"]:
        need(type(command) is list and command and all(type(x) is str for x in command)
             and command.count("ACTUAL_EXECUTION_RELEASE_SHA256") == 1, "K0 target exact command syntax")
        commands.append([target["execution_release"]["sha256"] if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in command])
    need(invocation["orig_argv"] in commands, "K0 actual target invocation not released")
    argv = invocation["argv"]
    need(invocation["orig_argv"][-len(argv):] == argv
         and Path(argv[0]).resolve() == ROOT / PREFIX / "independent-quality-target.py",
         "K0 target argv does not identify actual released script")
    need(len(argv) == 11 and len(set(argv[1::2])) == 5, "K0 target exact argument extent")
    arguments = dict(zip(argv[1::2], argv[2::2]))
    need(set(arguments) == {"--release", "--release-sha256", "--float-commission",
                            "--float-commission-sha256", "--output"}, "K0 target exact argument names")
    need(Path(arguments["--release"]).resolve() == C.relative_path(ROOT, target["execution_release"]["path"])
         and arguments["--release-sha256"] == target["execution_release"]["sha256"]
         and Path(arguments["--float-commission"]).resolve() == C.relative_path(ROOT, target["float_commission"]["path"])
         and arguments["--float-commission-sha256"] == target["float_commission"]["sha256"]
         and Path(arguments["--output"]).resolve() == target_path.parent.resolve(),
         "K0 actual target command associations")
    work = target["work"]
    C.keys(work, ("stage", "limits", "cpu_seconds", "wall_seconds", "live_array_bytes", "output_bytes", "tiff_decodes",
                  "target_cells", "peak_live_array_bytes", "tracked_scope"), "K0 target work")
    limits = dict(cpu_seconds=120.0, wall_seconds=240.0, live_array_bytes=33554432, output_bytes=67108864,
                  tiff_decodes=128, target_cells=76928)
    C.equal_record(work["limits"], limits, "K0 target work limits")
    need(work["stage"] == "target" and work["tracked_scope"] == "unique live backing ndarrays; not process RSS", "K0 work scope")
    for key in ("live_array_bytes", "output_bytes", "tiff_decodes", "target_cells", "peak_live_array_bytes"):
        C.integer(work[key], "K0 " + key)
    for key in ("cpu_seconds", "wall_seconds"):
        need(C.finite(work[key], "K0 " + key, 0) <= limits[key], "K0 target elapsed cap")
    need(work["live_array_bytes"] <= work["peak_live_array_bytes"] <= limits["live_array_bytes"]
         and work["output_bytes"] <= limits["output_bytes"] and work["tiff_decodes"] == 0
         and 76800 <= work["target_cells"] <= 76928, "K0 target work extent/counters")


def output_limit(output, budget):
    total = 0
    for path in output.rglob("*"):
        need(not path.is_symlink() and path.resolve().is_relative_to(output), "K0 output alias/escape")
        if path.is_file():
            total += path.stat().st_size
    need(total <= 16 * 1024 * 1024, "K0 total output budget")
    budget.check()
    return total


def write(path, value):
    path.write_bytes((json.dumps(value, allow_nan=False, sort_keys=True, indent=2) + "\n").encode())


def run(args):
    output = Path(args.output).resolve()
    need(not output.exists(), "K0 new output directory required")
    result = dict(schema="m194g-independent-k0-target-verification-v1", status="UNCOMMISSIONED_K0_TARGET",
                  method=METHOD, scope="ten fixed scalar cells and private integration controls; no whole-target or quality admission",
                  invocation=list(sys.orig_argv), target=None, float_commission=None, scalar=None,
                  execution_release=None, source_before=None, source_after=None, input_bindings=None,
                  controls=None, cells=[], maximum_error_e=None, rms_error_e=None,
                  runtime=None, work=None, error=None, finalization_errors=[])
    budget = reads = release = None
    try:
        release, budget, reads = bootstrap(args)
        output.mkdir()
        result["source_before"] = release["source_bindings"]
        for name, binding in release["source_bindings"].items():
            destination = output / "source-snapshot" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(reads.bound(ROOT, dict(path=name, **binding)))
            output_limit(output, budget)
        result["execution_release"] = F.file_ref(reads, args.execution_release)
        result["runtime"] = dict(python=sys.version, numpy=np.__version__, scipy=SCIPY_VERSION,
                                  executable=sys.executable, cwd=str(Path.cwd()), xoptions=dict(sys._xoptions),
                                  thread_environment={k: os.environ.get(k) for k in F.THREADS})
        result["controls"] = {}
        private_controls(budget, result["controls"])
        target, fixture, scalar = target_metadata(reads, args.target, args.target_sha256,
                                                  args.float_commission, args.float_commission_sha256, release, budget)
        result["target"] = F.file_ref(reads, args.target)
        result["float_commission"] = F.file_ref(reads, args.float_commission)
        sp = C.relative_path(Path(args.target).parent, target["scalar"]["path"])
        result["scalar"] = dict(path=sp.relative_to(ROOT).as_posix(), **{k: v for k, v in target["scalar"].items() if k != "path"})
        for x, y in CELLS:
            value = float(scalar[y, x])
            row = dict(native_xy=[x, y], target_e=value, independent={}, signed_error_e=None)
            result["cells"].append(row)
            independent = integrate_cell(fixture["scene"], (x, y), budget, record=row["independent"])
            row.update(independent=independent, signed_error_e=value - independent["value_e"])
        need(len(result["cells"]) == 10 and any(len(r["independent"]["y_breaks"]) > 2 for r in result["cells"]),
             "K0 fixed population or interior split unpowered")
        errors = [row["signed_error_e"] for row in result["cells"]]
        result["maximum_error_e"] = max(map(abs, errors))
        result["rms_error_e"] = math.sqrt(math.fsum(e * e for e in errors) / 10)
        need(result["maximum_error_e"] <= .004 and result["rms_error_e"] <= .0008, "K0 ten-cell comparison failed")
        result["status"] = "PASS_TEN_CELL_K0_TARGET"
    except Exception as exc:
        result["error"] = dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
    finally:
        try:
            if reads is not None:
                result["input_bindings"] = {Path(k).relative_to(ROOT).as_posix(): v for k, v in reads.observed.items()}
                reads.finish()
                result["source_after"] = release["source_bindings"]
            if budget is not None:
                result["work"] = budget.receipt()
                output_limit(output, budget)
        except Exception as exc:
            result["finalization_errors"].append(dict(type=type(exc).__name__, message=str(exc)))
        if result["error"] or result["finalization_errors"]:
            result["status"] = "UNCOMMISSIONED_K0_TARGET"
        path = output / "result.json"
        try:
            output.mkdir(exist_ok=True)
            write(path, result)
            if reads is not None:
                reads.finish()
            if budget is not None:
                output_limit(output, budget)
        except Exception as exc:
            result["status"] = "UNCOMMISSIONED_K0_TARGET"
            result["finalization_errors"].append(dict(type=type(exc).__name__, message=str(exc)))
            try:
                if path.exists():
                    path.rename(output / "result-rejected.json")
            except Exception as secondary:
                result["finalization_errors"].append(dict(type=type(secondary).__name__, message="retain rejected result: " + str(secondary)))
            try:
                write(path, result)
            except Exception as secondary:
                result["finalization_errors"].append(dict(type=type(secondary).__name__, message="persist refusal: " + str(secondary)))
                print(json.dumps(result, allow_nan=False), file=sys.stderr, flush=True)
    print(result["status"], flush=True)
    return 0 if result["status"] == "PASS_TEN_CELL_K0_TARGET" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    for arg in ("target", "float-commission", "execution-release"):
        parser.add_argument("--" + arg, required=True)
        parser.add_argument("--" + arg + "-sha256", required=True)
    raise SystemExit(run(parser.parse_args()))
