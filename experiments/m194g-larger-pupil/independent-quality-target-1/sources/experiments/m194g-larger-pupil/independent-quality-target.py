"""K=0 coupled-cell target producer. Local controls do not admit the target."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.perf_counter()
import argparse
import copy
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FROZEN = ROOT / "experiments/m194e-joint-pupil/independent-model.py"
FROZEN_SHA = "0cd8ea2331b269e65befdee110560cbc345e89c12348cbe1dc3144f7c04443f0"
LOCAL_IDS = ("constant-full-foreground", "constant-full-background", "constant-mixed",
             "vertical-affine", "oblique-affine", "centre-mask-live", "separate-alpha-live",
             "coupled-restored", "fourier-zero", "fourier-full-x", "fourier-negative-sinc",
             "fourier-two-dimensional", "translated-phase-live", "translated-phase-restored",
             "nonfinite-refuses", "empty-normal-refuses")
SQUARE = ((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5))
METHOD = "m194g-k0-clipped-cell-v1"


class Target:
    """Only frozen clip/moments/polygon_fourier/sinc are consumed."""
    def __init__(self, frozen, budget):
        self.m, self.budget = frozen, budget

    @staticmethod
    def validate(scene, xy):
        if type(scene) is not dict or set(scene) != {"depths", "mask_normal", "mask_offset", "mask_state", "foreground", "background"}:
            raise ValueError("target scene keys")
        if scene["mask_state"] != "half-plane" or len(scene["mask_normal"]) != 2 or len(xy) != 2:
            raise ValueError("target half-plane layout")
        values = [*xy, *scene["depths"], *scene["mask_normal"], scene["mask_offset"]]
        for name in ("foreground", "background"):
            field = scene[name]
            if set(field) != {"constant", "affine", "waves"} or len(field["affine"]) != 2 or len(field["waves"]) > 2:
                raise ValueError("target field layout")
            values.extend((field["constant"], *field["affine"]))
            for wave in field["waves"]:
                if set(wave) != {"amplitude", "frequency", "phase"} or len(wave["frequency"]) != 2:
                    raise ValueError("target wave layout")
                values.extend((wave["amplitude"], *wave["frequency"], wave["phase"]))
        if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
            raise ValueError("nonfinite/incorrect target geometry or radiance")
        if len(scene["depths"]) != 2 or not 0 < scene["depths"][0] < scene["depths"][1] or scene["mask_normal"] == [0., 0.]:
            raise ValueError("target depths/normal")

    def cell(self, scene, xy, *, fault=None):
        if fault not in (None, "centre-mask", "separate-alpha", "lost-phase"):
            raise ValueError("unknown target private fault")
        self.validate(scene, xy)
        self.budget.target_cells += 1
        self.budget.check()
        n, offset = scene["mask_normal"], scene["mask_offset"]
        threshold = offset - (n[0] * xy[0] + n[1] * xy[1])
        polygon = self.m.clip(SQUARE, tuple(n), threshold)
        area, moment = self.m.moments(polygon)
        if not math.isfinite(area) or not 0 <= area <= 1 or not all(math.isfinite(v) for v in moment):
            raise ValueError("target clipped area/moment")
        if fault == "centre-mask":
            area, moment = float(threshold <= 0), (0., 0.)
        terms = []
        for layer, name in enumerate(("foreground", "background")):
            field = scene[name]
            a = area if layer == 0 else 1 - area
            m = moment if layer == 0 else (-moment[0], -moment[1])
            if fault == "separate-alpha": m = (0., 0.)
            gradient = field["affine"]
            terms.append((field["constant"] + gradient[0] * xy[0] + gradient[1] * xy[1]) * a
                         + gradient[0] * m[0] + gradient[1] * m[1])
            for wave in field["waves"]:
                fx, fy = wave["frequency"]
                k = (2 * math.pi * fx, 2 * math.pi * fy)
                whole = complex(self.m.sinc(k[0] / 2) * self.m.sinc(k[1] / 2))
                clipped = self.m.polygon_fourier(polygon, k)
                value = clipped if layer == 0 else whole - clipped
                if fault in ("centre-mask", "separate-alpha"): value = whole * a
                phase = wave["phase"] + (0. if fault == "lost-phase" else k[0] * xy[0] + k[1] * xy[1])
                terms.append(wave["amplitude"] * (math.cos(phase) * value.real - math.sin(phase) * value.imag))
        result = math.fsum(terms)
        if not math.isfinite(result) or result < 0:
            raise ValueError("nonfinite/negative target scalar")
        self.budget.check()
        return result


def scene_record(normal=(1., 0.), offset=0., foreground=30., background=10.):
    def field(value):
        return {"constant": value, "affine": [0., 0.], "waves": []}
    return {"depths": [1., 2.], "mask_normal": list(normal), "mask_offset": offset,
            "mask_state": "half-plane", "foreground": field(foreground), "background": field(background)}


def local_controls(target):
    result = {"schema": "m194g-quality-target-controls-v1", "status": "UNCOMMISSIONED_LOCAL_K0_CONTROLS",
              "checks": [], "error": None}
    def check(name, passed, **details):
        result["checks"].append({"id": name, "passed": bool(passed), "details": details})
        if not passed: raise ValueError("K0 local control " + name)
    def near(name, actual, expected, tolerance=1e-8):
        check(name, abs(actual - expected) <= tolerance, actual=actual, expected=expected, tolerance=tolerance)
    def sha(value):
        import struct
        return hashlib.sha256(struct.pack("<d", value)).hexdigest()
    try:
        base = scene_record()
        near(LOCAL_IDS[0], target.cell(base, (3, 2)), 30.)
        near(LOCAL_IDS[1], target.cell(base, (-3, 2)), 10.)
        near(LOCAL_IDS[2], target.cell(base, (0, 0)), 20.)
        vertical = scene_record(offset=113.125)
        vertical["background"].update(constant=10. - 4. * 113., affine=[4., 0.])
        value = target.cell(vertical, (113, 117))
        near(LOCAL_IDS[3], value, 17.03125)
        oblique = copy.deepcopy(vertical)
        oblique.update(mask_normal=[1., 1.], mask_offset=113. + 117. + .25)
        near(LOCAL_IDS[4], target.cell(oblique, (113, 117)), 15.34375)
        wrong = target.cell(vertical, (113, 117), fault="centre-mask")
        check(LOCAL_IDS[5], abs(wrong - value) > .1, correct=value, mutated=wrong)
        wrong = target.cell(vertical, (113, 117), fault="separate-alpha")
        check(LOCAL_IDS[6], abs(wrong - value) > .1, correct=value, mutated=wrong)
        restored = target.cell(vertical, (113, 117))
        check(LOCAL_IDS[7], sha(restored) == sha(value), original_sha256=sha(value), restored_sha256=sha(restored))
        for name, frequency, phase in ((LOCAL_IDS[8], (0., 0.), .31),
                                       (LOCAL_IDS[9], (.25, 0.), -.27),
                                       (LOCAL_IDS[10], (1.5, 0.), 0.),
                                       (LOCAL_IDS[11], (.25, -.375), .19)):
            wave_scene = scene_record(offset=-100., foreground=3000.)
            wave_scene["foreground"]["waves"] = [{"amplitude": 40., "frequency": list(frequency), "phase": phase}]
            sx = 1. if frequency[0] == 0 else math.sin(math.pi * frequency[0]) / (math.pi * frequency[0])
            sy = 1. if frequency[1] == 0 else math.sin(math.pi * frequency[1]) / (math.pi * frequency[1])
            expected = 3000. + 40. * sx * sy * math.cos(phase)
            near(name, target.cell(wave_scene, (0, 0)), expected, 1e-7)
        translated = scene_record(offset=-100., foreground=3000.)
        translated["foreground"]["waves"] = [{"amplitude": 40., "frequency": [.125, .0625], "phase": .31}]
        good = target.cell(translated, (3, 5))
        bad = target.cell(translated, (3, 5), fault="lost-phase")
        check(LOCAL_IDS[12], abs(good - bad) > 1., correct=good, mutated=bad)
        restored = target.cell(translated, (3, 5))
        check(LOCAL_IDS[13], sha(restored) == sha(good), original_sha256=sha(good), restored_sha256=sha(restored))
        for name, bad_scene in ((LOCAL_IDS[14], scene_record(foreground=float("nan"))),
                                (LOCAL_IDS[15], scene_record(normal=(0., 0.)))):
            try:
                target.cell(bad_scene, (0, 0))
            except ValueError as error:
                check(name, ("nonfinite" in str(error)) if name == LOCAL_IDS[14] else ("normal" in str(error)),
                      exception_type=type(error).__name__, message=str(error))
            else:
                check(name, False)
        if tuple(row["id"] for row in result["checks"]) != LOCAL_IDS:
            raise ValueError("local target control population")
        result["status"] = "PASS_LOCAL_K0_CONTROLS_ONLY"
    except Exception:
        result["error"] = traceback.format_exc()
    return result


def main():
    spec = importlib.util.spec_from_file_location("m194g_quality_io", HERE / "independent-quality-io.py")
    io = importlib.util.module_from_spec(spec); spec.loader.exec_module(io)
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--float-commission", type=Path, required=True)
    parser.add_argument("--float-commission-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    required_paths = (Path(__file__), HERE / "independent-quality-io.py", HERE / "independent-quality-metrics.py",
                      HERE / "software-noise-authority.py", FROZEN)
    source_names = {p.resolve().relative_to(ROOT).as_posix() for p in required_paths}
    required_inputs = [(HERE / name).resolve() for name in ("fixture.json", "next-quality-reader-preregister.md",
                       "next-quality-target-interface.md", "independent-full-float-authority-schema.md")]
    required_inputs.append(args.float_commission.resolve())
    release, reads = io.verify_release(args.release, args.release_sha256, "target", source_names, required_inputs)
    sources = release["source_bindings"]
    io.need(sources[FROZEN.relative_to(ROOT).as_posix()]["sha256"] == FROZEN_SHA, "immutable independent polygon source")
    metrics = io.load_bound(HERE / "independent-quality-metrics.py", "m194g_quality_metrics", sources)
    io.np = metrics.np
    budget = metrics.Budget("target", start_cpu=ENTRY_CPU, start_wall=ENTRY_WALL)
    reads.budget = budget
    store = io.Store(args.output, budget)
    result = {"schema": "m194g-quality-target-v1", "status": "UNCOMMISSIONED_QUALITY_TARGET",
              "ref_root": "target-parent", "upstream_ref_root": "repository", "fixture": None,
              "float_commission": None, "scalar": None, "geometry": None, "method": METHOD, "controls": None,
              "sources_before": sources, "sources_after": None, "runtime": None, "work": None,
              "error": None, "finalization_errors": [], "execution_release": io.file_ref(args.release),
              "invocation": io.invocation()}
    authority = None
    def check_inputs():
        reads.finish()
        if authority is not None: authority.reads.finish()
        after = {name: io.file_binding(ROOT / name) for name in sources}
        io.need(after == sources, "target source changed")
        result["sources_after"] = after
    try:
        store.snapshots(sources)
        frozen = io.load_bound(FROZEN, "m194g_quality_frozen_polygon", sources)
        authority_module = io.load_bound(HERE / "software-noise-authority.py", "m194g_quality_float_authority", sources)
        authority = authority_module.FloatAuthority(args.float_commission, args.float_commission_sha256, io, budget)
        result["fixture"] = io.file_ref(HERE / "fixture.json")
        result["float_commission"] = authority.reference
        fixture = authority.fixture
        identity = {"scale": 1., "rotation": 0., "centre": [0., 0.], "translation": [0., 0.]}
        io.need(fixture["width"] == 320 and fixture["height"] == 240 and fixture["forward_similarity"] == identity,
                "fixed native target identity")
        result["geometry"] = {"width": 320, "height": 240, "native_origin": [0, 0],
                              "cell": "integer-centre-unit-square", "units": "expected-electrons", "K": 0.,
                              "forward_similarity": fixture["forward_similarity"]}
        result["runtime"] = io.runtime()
        target = Target(frozen, budget)
        controls = local_controls(target)
        result["controls"] = store.json("controls.json", controls)
        io.need(controls["status"] == "PASS_LOCAL_K0_CONTROLS_ONLY", "local target controls failed")
        scalar = budget.empty((240, 320), "<f8", "full K0 scalar target")
        full_start = budget.target_cells
        for y in range(240):
            for x in range(320): scalar[y, x] = target.cell(fixture["scene"], (x, y))
        io.need(budget.target_cells - full_start == 76800, "full target population")
        io.checked_array(scalar, budget, shape=(240, 320), name="completed K0 scalar", nonnegative=True)
        result["scalar"] = store.array("scalar.npy", scalar)
        result["status"] = "COMPLETE_K0_TARGET_UNCOMMISSIONED"
    except Exception:
        result["error"] = traceback.format_exc()
    success = io.finish_terminal(store, "target.json", result, "COMPLETE_K0_TARGET_UNCOMMISSIONED", check_inputs)
    print(io.canonical_bytes({"status": result["status"], "target": str(store.root / "target.json"),
                             "error": result["error"], "finalization_errors": result["finalization_errors"]}).decode(), flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
