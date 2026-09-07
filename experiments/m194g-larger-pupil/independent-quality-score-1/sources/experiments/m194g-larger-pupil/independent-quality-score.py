"""Read the fixed38 actual outputs; completion never means quality acceptance."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.perf_counter()
import argparse
from datetime import datetime
import importlib.util
import math
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE_FILES = ("independent-quality-score.py", "independent-quality-io.py", "independent-quality-metrics.py",
                "independent-quality-adapter.py", "independent-quality-readout.py", "independent-rgb-tiff.py",
                "independent-production-bridge-read.py", "independent-private-bridge-read.py")
DESIGNS = ("fixture.json", "next-quality-reader-preregister.md", "next-quality-target-interface.md",
           "next-quality-instrument-interface.md", "next-quality-adapter-control-interface.md",
           "next-quality-score-adapter.md", "next-quality-matrix-design.md", "next-quality-score-interface.md")
CELLS = ((142, 0), (142, 1), (143, 7), (150, 53), (151, 64), (152, 64),
         (159, 117), (160, 117), (169, 179), (178, 239))
TARGET_IDS = ("constant-full-foreground", "constant-full-background", "constant-mixed", "vertical-affine",
              "oblique-affine", "centre-mask-live", "separate-alpha-live", "coupled-restored", "fourier-zero",
              "fourier-full-x", "fourier-negative-sinc", "fourier-two-dimensional", "translated-phase-live",
              "translated-phase-restored", "nonfinite-refuses", "empty-normal-refuses")


class Ancestors:
    """Small consumer of actual already-issued records; it issues no new gate."""
    def __init__(self, io, reads, adapter, private):
        self.io, self.reads, self.a, self.p = io, reads, adapter, private
        private.IO = io

    def json(self, ref, base=ROOT):
        return self.reads.json(ref, base)

    def terminal(self, record, schema, status):
        self.a.exact(record["schema"], schema, "upstream schema")
        self.a.exact(record["status"], status, "upstream status")
        self.a.exact(record["error"], None, "upstream error")
        self.a.exact(record["finalization_errors"], [], "upstream finalization")

    def maps(self, record, source_stem="sources", input_stem="inputs"):
        for stem in (source_stem, input_stem):
            if stem is None: continue
            self.a.exact(record[stem + "_after"], record[stem + "_before"], "upstream " + stem + " invariance")
            self.p.mapped(record[stem + "_before"], self.reads)

    def checks(self, rows, count, ids=None):
        self.io.need(type(rows) is list and len(rows) == count, "complete upstream control population")
        names = []
        for row in rows:
            self.a.keys(row, "id passed details", "upstream control")
            self.io.need(type(row["id"]) is str and row["id"] and row["passed"] is True
                         and type(row["details"]) is dict, "upstream control failed/type")
            names.append(row["id"])
        self.io.need(len(set(names)) == count, "upstream duplicate controls")
        if ids is not None: self.a.exact(names, list(ids), "upstream literal control ids")

    def release(self, ref, schema, scope, sources, invocation, required=(), snapshots=None):
        release, _ = self.json(ref)
        self.a.keys(release, "schema scope source_bindings inputs commands", "upstream release")
        self.a.exact(release["schema"], schema, "upstream release schema")
        self.a.exact(release["scope"], scope, "upstream release scope")
        self.a.exact(release["source_bindings"], sources, "released upstream sources")
        self.p.mapped(sources, self.reads)
        if snapshots is not None:
            for name, binding in sources.items():
                path = self.io.relative(snapshots, name)
                self.reads.raw(path, binding["sha256"], binding["bytes"])
        self.io.need(type(release["inputs"]) is list and release["inputs"], "nonempty upstream release inputs")
        paths = []
        for item in release["inputs"]: paths.append(self.p.bind(item, self.reads))
        self.io.need(len(set(paths)) == len(paths), "upstream input aliases")
        for item in required: self.io.need(item in release["inputs"], "upstream required input absent")
        self.io.need(type(release["commands"]) is list and release["commands"], "upstream released commands")
        choices = []
        for command in release["commands"]:
            self.io.need(type(command) is list and command and all(type(v) is str for v in command)
                         and command.count("ACTUAL_EXECUTION_RELEASE_SHA256") == 1, "upstream exact command syntax")
            choices.append([ref["sha256"] if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in command])
        self.io.need(invocation in choices, "upstream actual invocation not released")
        return release

    def work(self, work, stage, *, tiff, target):
        self.a.keys(work, "stage limits cpu_seconds wall_seconds live_array_bytes output_bytes tiff_decodes target_cells peak_live_array_bytes tracked_scope", "quality work")
        limits = dict(cpu_seconds=120., wall_seconds=240., live_array_bytes=33554432,
                      output_bytes=67108864, tiff_decodes=128, target_cells=76928)
        self.a.exact(work["limits"], limits, "upstream quality limits")
        self.a.exact(work["stage"], stage, "upstream quality stage")
        for name in ("live_array_bytes", "output_bytes", "tiff_decodes", "target_cells", "peak_live_array_bytes"):
            self.io.need(type(work[name]) is int and work[name] >= 0, "upstream genuine integer counter")
        for name in ("cpu_seconds", "wall_seconds"):
            self.io.need(type(work[name]) in (int, float) and math.isfinite(work[name])
                         and 0 <= work[name] <= limits[name], "upstream elapsed bound")
        self.io.need(work["live_array_bytes"] <= work["peak_live_array_bytes"] <= limits["live_array_bytes"]
                     and work["output_bytes"] <= limits["output_bytes"], "upstream storage bound")
        self.a.exact(work["tiff_decodes"], tiff, "upstream TIFF population")
        self.io.need(target[0] <= work["target_cells"] <= target[1], "upstream optical cell population")
        self.a.exact(work["tracked_scope"], "unique live backing ndarrays; not process RSS", "upstream storage scope")


def bridge_context(matrix, gate_ref, *, ancestors, loader):
    c, a, io = ancestors, ancestors.a, ancestors.io
    gate, _ = c.json(gate_ref)
    a.keys(gate, "schema status ref_root build private_tests private_outputs intended_outputs independent_read execution_release sources_before sources_after inputs_before inputs_after error finalization_errors", "bridge gate")
    c.terminal(gate, "m194g-production-bridge-commission-v1", "PASS_PRODUCTION_BRIDGE_ONLY")
    a.exact(gate["ref_root"], "repository", "bridge root")
    c.maps(gate)
    actual, _ = c.json(gate["independent_read"])
    c.terminal(actual, "m194g-independent-production-bridge-read-v1", "PASS_PRODUCTION_BRIDGE_ONLY")
    c.maps(actual)
    for key in ("build", "intended_outputs", "execution_release", "sources_before", "sources_after", "inputs_before", "inputs_after"):
        a.exact(actual[key], gate[key], "bridge actual child " + key)
    io.need(type(actual["outputs"]) is list and len(actual["outputs"]) == 12, "bridge twelve independent outputs")
    a.exact(actual["observer_identity"]["ordinals"], [6, 8, 9], "bridge actual observer population")
    c.work(actual["work"], "instruments", tiff=12, target=(0, 0))
    c.release(actual["execution_release"], "m194g-quality-execution-release-v1", "intended-bridge-read",
              actual["sources_before"], actual["invocation"]["orig_argv"],
              (gate["build"], gate["intended_outputs"], actual["private_read"]))
    context, subjects, private, intended = loader.context_and_rows(gate["intended_outputs"], gate["build"], actual["private_read"],
        io=io, reads=c.reads, private_reader=c.p, adapter=a)
    for key in ("private_tests", "private_outputs"): a.exact(gate[key], private[key], "bridge private child " + key)
    a.exact(matrix["noise_admission"], context["noise_admission"], "matrix same admitted noise inputs")
    for checked, subject in zip(actual["outputs"], subjects, strict=True):
        a.exact(checked["row"], subject["row"], "actual twelve read association")
    return context, actual


def instrument_gate(ref, bridge_read, *, ancestors):
    c, a, io = ancestors, ancestors.a, ancestors.io
    # The actual matrix consumes this original69 result. The actual bridge
    # read separately binds its59 adapter child; no synthetic composite gate.
    math_record, math_path = c.json(ref)
    a.keys(math_record, "schema status checks sources_before sources_after runtime work error finalization_errors execution_release invocation fixture artifacts", "math/TIFF result")
    c.terminal(math_record, "m194g-quality-instruments-v1", "PASS_QUALITY_INSTRUMENTS_ONLY")
    c.maps(math_record, input_stem=None)
    c.checks(math_record["checks"], 69)
    c.work(math_record["work"], "instruments", tiff=23, target=(0, 0))
    c.release(math_record["execution_release"], "m194g-quality-execution-release-v1", "instruments",
              math_record["sources_before"], math_record["invocation"]["orig_argv"],
              (math_record["fixture"],), snapshots=math_path.parent / "sources")
    for ref in math_record["artifacts"]:
        path = c.reads.ref(ref, math_path.parent)
        c.reads.raw(path, ref["sha256"], ref["bytes"], cap=1024**2)
    controls, _ = c.json(bridge_read["adapter_controls"])
    a.keys(controls, "schema status checks genuine_subjects private_load_counts work_before work_after error scope", "adapter result")
    a.exact(controls["schema"], "m194g-quality-adapter-controls-v1", "adapter schema")
    a.exact(controls["status"], "PASS_QUALITY_MATRIX_ADAPTER_INSTRUMENTS", "adapter status")
    a.exact(controls["error"], None, "adapter error")
    c.checks(controls["checks"], 59)
    io.need(type(controls["genuine_subjects"]) is list and len(controls["genuine_subjects"]) == 12, "actual adapter twelve companions")
    a.exact(controls["private_load_counts"], [dict(case=name, calls=34) for name in ("half-noise", "bias", "spike")], "actual complete private reducers")
    for name in ("work_before", "work_after"): c.work(controls[name], "instruments", tiff=0, target=(0, 0))
    return math_record, controls


def target_inputs(target_ref, verifier_ref, context, *, ancestors):
    c, a, io = ancestors, ancestors.a, ancestors.io
    target, path = c.json(target_ref)
    a.keys(target, "schema status ref_root upstream_ref_root fixture float_commission scalar geometry method controls sources_before sources_after runtime work error finalization_errors execution_release invocation", "target receipt")
    c.terminal(target, "m194g-quality-target-v1", "COMPLETE_K0_TARGET_UNCOMMISSIONED")
    a.exact(target["ref_root"], "target-parent", "target root")
    a.exact(target["upstream_ref_root"], "repository", "target upstream root")
    a.exact(target["method"], "m194g-k0-clipped-cell-v1", "target method")
    a.exact(target["float_commission"], context["authority"]["float_commission"], "target matches actual noise full-float authority")
    fixture, fixture_path = c.json(target["fixture"])
    io.need(fixture_path == HERE / "fixture.json", "original registered target fixture")
    floats, _ = c.json(target["float_commission"])
    a.exact(floats["schema"], "m194g-float-commission-v1", "actual full-float schema")
    a.exact(floats["status"], "PASS_COMPLETE_FLOAT_MODEL", "actual full-float admission")
    a.exact(floats["fixture"], target["fixture"], "actual full-float fixture")
    a.exact(target["geometry"], dict(width=320, height=240, native_origin=[0, 0], cell="integer-centre-unit-square",
            units="expected-electrons", K=0., forward_similarity=fixture["forward_similarity"]), "target geometry")
    a.exact(fixture["forward_similarity"], dict(scale=1., rotation=0., centre=[0., 0.], translation=[0., 0.]), "target identity gauge")
    a.exact(fixture["scene"]["mask_normal"], [1., -.15], "fixed target normal")
    a.exact(fixture["scene"]["mask_offset"], 142., "fixed target offset")
    c.maps(target, input_stem=None)
    declared = {(HERE / n).relative_to(ROOT).as_posix() for n in
                ("independent-quality-target.py", "independent-quality-io.py", "independent-quality-metrics.py", "software-noise-authority.py")}
    frozen = "experiments/m194e-joint-pupil/independent-model.py"
    io.need(set(target["sources_before"]) == declared | {frozen}
             and target["sources_before"][frozen]["sha256"] == "0cd8ea2331b269e65befdee110560cbc345e89c12348cbe1dc3144f7c04443f0", "exact target source model")
    c.release(target["execution_release"], "m194g-quality-execution-release-v1", "target", target["sources_before"],
              target["invocation"]["orig_argv"], (target["fixture"], target["float_commission"]), snapshots=path.parent / "sources")
    c.work(target["work"], "target", tiff=0, target=(76800, 76928))
    local, _ = c.json(target["controls"], path.parent)
    a.keys(local, "schema status checks error", "target local controls")
    a.exact(local["schema"], "m194g-quality-target-controls-v1", "target control schema")
    a.exact(local["status"], "PASS_LOCAL_K0_CONTROLS_ONLY", "target local status")
    a.exact(local["error"], None, "target local error")
    c.checks(local["checks"], 16, TARGET_IDS)
    scalar = c.reads.array(target["scalar"], path.parent, (240, 320), "<f8", nonnegative=True)
    scalar_path = c.reads.ref(target["scalar"], path.parent, array=True)
    scalar_ref = {**target["scalar"], "path": scalar_path.relative_to(ROOT).as_posix()}
    verifier, verify_path = c.json(verifier_ref)
    a.keys(verifier, "schema status method scope invocation target float_commission scalar execution_release source_before source_after input_bindings controls cells maximum_error_e rms_error_e runtime work error finalization_errors", "separate target verifier")
    c.terminal(verifier, "m194g-independent-k0-target-verification-v1", "PASS_TEN_CELL_K0_TARGET")
    a.exact(verifier["method"], "analytic-x-split-y-quad-k0-v1", "separate target method")
    for key, wanted in (("target", target_ref), ("float_commission", target["float_commission"]), ("scalar", scalar_ref)):
        a.exact(verifier[key], wanted, "separate verifier actual " + key)
    c.maps(verifier, source_stem="source", input_stem=None)
    c.p.mapped(verifier["input_bindings"], c.reads)
    c.release(verifier["execution_release"], "m194g-numerical-execution-release-v1", "independent-k0-target",
              verifier["source_before"], verifier["invocation"], (target_ref, target["float_commission"]), snapshots=verify_path.parent / "source-snapshot")
    controls = verifier["controls"]
    a.keys(controls, "schema status literal_oracles faults calls check_count", "independent target controls")
    a.exact(controls["schema"], "m194g-independent-k0-private-controls-v1", "independent target control schema")
    a.exact(controls["status"], "PASS_PRIVATE_K0_CONTROLS", "independent target control status")
    a.exact(controls["check_count"], 12, "independent target control count")
    io.need(len(controls["literal_oracles"]) == 8 and len(controls["faults"]) == 4 and len(controls["calls"]) == 20
             and all(r["passed"] is True for r in controls["literal_oracles"] + controls["faults"])
             and all(r["error"] is None for r in controls["calls"]), "complete separate target actual controls")
    io.need(type(verifier["cells"]) is list and len(verifier["cells"]) == 10, "ten fixed target cells")
    errors = []
    for xy, row in zip(CELLS, verifier["cells"], strict=True):
        a.keys(row, "native_xy target_e independent signed_error_e", "target verification cell")
        a.exact(row["native_xy"], list(xy), "target verification cell coordinate")
        a.exact(row["target_e"], float(scalar[xy[1], xy[0]]), "actual target scalar cell")
        expected = row["target_e"] - row["independent"]["value_e"]
        a.exact(row["signed_error_e"], expected, "saved independent signed discrepancy")
        errors.append(expected)
    maximum = max(map(abs, errors)); rms = math.sqrt(math.fsum(e*e for e in errors) / 10)
    a.exact(verifier["maximum_error_e"], maximum, "saved maximum discrepancy")
    a.exact(verifier["rms_error_e"], rms, "saved RMS discrepancy")
    io.need(maximum <= .004 and rms <= .0008, "unchanged separate target accuracy bars")
    return target, fixture, scalar, scalar_ref


def review_triggers(scene):
    """Preserve every inspected value; flags have no admission role."""
    rows, paired = [], {}
    for row in scene["individual_errors"]:
        key = (row["seed"], row["channel"], row["reference"], row["region"])
        paired.setdefault(key, {})[row["mode"]] = row
    for (seed, channel, reference, region), modes in paired.items():
        before, after = (modes[name]["rmse_dn"] for name in ("hard-floor", "floor-pedestal-v1"))
        rows.append(dict(kind="rmse-increase", scene=scene["scene"], seed=seed, channel=channel,
                         reference=reference, region=region, baseline_dn=before, candidate_dn=after,
                         change_dn=after-before, threshold_dn=1., triggered=after-before > 1.))
    for row in scene["paired_variance"]:
        ratio = row["candidate_over_baseline"]
        rows.append(dict(kind="temporal-variance-increase", scene=scene["scene"], channel=row["channel"], region=row["region"],
                         baseline_dn2=row["baseline_variance_dn2"], candidate_dn2=row["candidate_variance_dn2"],
                         change_dn2=row["candidate_minus_baseline_dn2"], ratio=ratio, threshold_ratio=1.02,
                         triggered=None if ratio is None else ratio > 1.02))
    paired = {}
    for row in scene["noise_off_waves"]: paired.setdefault((row["channel"], row["region"]), {})[row["mode"]] = row
    for (channel, region), modes in paired.items():
        before, after = (modes[name]["observed"]["waves"] for name in ("hard-floor", "floor-pedestal-v1"))
        for index, (first, second) in enumerate(zip(before, after, strict=True)):
            change = second["amplitude_dn"] - first["amplitude_dn"]
            rows.append(dict(kind="noise-off-wave-amplitude-loss", scene=scene["scene"], channel=channel, region=region,
                             wave_index=index, baseline_dn=first["amplitude_dn"], candidate_dn=second["amplitude_dn"],
                             change_dn=change, threshold_dn=-1., triggered=change < -1.))
    return rows


def main():
    spec = importlib.util.spec_from_file_location("m194g_score_io", HERE / "independent-quality-io.py")
    io = importlib.util.module_from_spec(spec); spec.loader.exec_module(io)
    parser = argparse.ArgumentParser()
    for name in ("matrix", "target", "target-verification", "instrument-commission", "release"):
        parser.add_argument("--" + name, type=Path, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    names = {(HERE / name).relative_to(ROOT).as_posix() for name in SOURCE_FILES}
    required = [(HERE / name).resolve() for name in DESIGNS]
    required += [getattr(args, name).resolve() for name in ("matrix", "target", "target_verification", "instrument_commission")]
    release, reads = io.verify_release(args.release, args.release_sha256, "score", names, required)
    bound = release["source_bindings"]
    modules = {name: io.load_bound(HERE / filename, "m194g_score_" + name, bound) for name, filename in (
        ("metrics", "independent-quality-metrics.py"), ("adapter", "independent-quality-adapter.py"),
        ("readout", "independent-quality-readout.py"), ("tiff", "independent-rgb-tiff.py"),
        ("loader", "independent-production-bridge-read.py"), ("private", "independent-private-bridge-read.py"))}
    io.np = modules["metrics"].np
    budget = modules["metrics"].Budget("score", start_cpu=ENTRY_CPU, start_wall=ENTRY_WALL)
    reads.budget = budget
    store = io.Store(args.output, budget)
    a, m, np = modules["adapter"], modules["metrics"], io.np
    result = dict(schema="m194g-quality-score-v1", status="UNCOMMISSIONED_QUALITY_STAGE", ref_root="repository",
        artifact_ref_root="result-parent", matrix=None, target=None, target_verification=None, instrument_commission=None,
        bridge_commission=None, noise_admission=None, fixture=None, scalar=None, execution_release=io.file_ref(args.release),
        invocation=io.invocation(), sources_before=bound, sources_after=None, inputs_before=None, inputs_after=None,
        runtime=None, work=None, geometry=None, region_masks={}, entries=[], scene_results=[], review_triggers=[],
        decode_reads=[], error=None, finalization_errors=[],
        scope="fixed38 diagnostics; no quality pass, performance comparison or physical calibration claim")
    def check_inputs():
        current = {Path(name).relative_to(ROOT).as_posix(): binding for name, binding in reads.finish().items()}
        result["inputs_after"] = current
        io.need(result["inputs_before"] is None or result["inputs_before"] == current, "score actual input closure")
        result["sources_after"] = {name: io.file_binding(ROOT / name) for name in bound}
        a.exact(result["sources_after"], bound, "score source closure")
    try:
        store.snapshots(bound); result["runtime"] = io.runtime()
        for name in ("matrix", "target", "target_verification", "instrument_commission"):
            path = getattr(args, name)
            result[name] = io.file_ref(path)
            a.exact(result[name]["sha256"], getattr(args, name + "_sha256"), "external score input pin")
        c = Ancestors(io, reads, a, modules["private"])
        matrix, _ = c.json(result["matrix"])
        rows = a.validate_population(matrix)
        result["bridge_commission"], result["noise_admission"] = matrix["bridge_commission"], matrix["noise_admission"]
        a.exact(matrix["instrument_commission"], result["instrument_commission"], "actual matrix instrument gate")
        c.maps(matrix)
        c.release(matrix["execution_release"], "m194g-numerical-execution-release-v1", "quality-production-matrix",
                  matrix["sources_before"], matrix["invocation"],
                  (matrix["noise_admission"], matrix["bridge_commission"], matrix["instrument_commission"]))
        context, bridge = bridge_context(matrix, result["bridge_commission"], ancestors=c, loader=modules["loader"])
        instrument_gate(result["instrument_commission"], bridge, ancestors=c)
        del bridge  # The historical12 metadata has been admitted; no retained duplicate volume.
        target, fixture, scalar, scalar_ref = target_inputs(result["target"], result["target_verification"], context, ancestors=c)
        result["fixture"], result["scalar"] = target["fixture"], scalar_ref
        a.keys(matrix["work"], "completed_plans failed_launch metadata_and_log_bytes metadata_and_log_limit per_child_wall_seconds per_child_log_bytes", "actual matrix work")
        for name, expected in (("metadata_and_log_limit", 64 << 20), ("per_child_wall_seconds", 240), ("per_child_log_bytes", 16 << 20)):
            a.exact(matrix["work"][name], expected, "actual matrix operational " + name)
        io.need(type(matrix["work"]["metadata_and_log_bytes"]) is int
                and 0 <= matrix["work"]["metadata_and_log_bytes"] <= matrix["work"]["metadata_and_log_limit"],
                "actual matrix bookkeeping bound")
        a.exact(matrix["work"]["failed_launch"], None, "no failed matrix child")
        a.exact(matrix["work"]["completed_plans"], [dict(plan=row["plan"], launch=row["plan_launch"]) for row in rows], "all38 actual plan completions")
        plan_ends, render_starts, identities, pixel_hashes = [], [], set(), {}
        for row in rows:
            for name in ("plan", "plan_launch", "receipt", "tiff", "log", "launch"):
                stat = reads.ref(row[name]).stat(); identity = (stat.st_dev, stat.st_ino)
                io.need(stat.st_ino != 0 and identity not in identities, "physical38 artifact alias")
                identities.add(identity)
            checked = a.read_entry(row, io=io, reads=reads, context=context, decode=True, tiff_reader=modules["tiff"])
            # A full checked entry repeats its actual plan inside the receipt.
            # Persist it separately under the unchanged4MiB-per-JSON ceiling.
            result["entries"].append(store.json("entries/entry-" + str(row["ordinal"]).zfill(2) + ".json", checked))
            if context.get("common_geometry") is None: context["common_geometry"] = checked["geometry"]
            pixel_hashes[row["ordinal"]] = checked["receipt"]["output"]["pixel_sha256_le"]
            result["decode_reads"].append(dict(phase="association", ordinal=row["ordinal"], tiff=row["tiff"],
                                                pixel_sha256=checked["decoded"]["pixel_sha256"]))
            del checked
            plan_ends.append(datetime.fromisoformat(c.json(row["plan_launch"])[0]["ended_utc"]))
            render_starts.append(datetime.fromisoformat(c.json(row["launch"])[0]["started_utc"]))
        io.need(max(plan_ends) <= min(render_starts), "all actual plans precede all renders")
        io.need(len(result["entries"]) == budget.tiff_decodes == 38, "all38 initial actual TIFF decodes")
        geom = context["common_geometry"]
        result["geometry"] = geom
        width, height = geom["output_native"]
        masks = m.regions((height, width), tuple(geom["canonical_native_offset"]), budget)
        for name, array in masks.items(): result["region_masks"][name] = store.array("masks/" + name + ".npy", array)
        del masks, array
        active_scene = None
        def load_rgb(row):
            budget.tiff_decodes += 1; budget.check()
            path = reads.ref(row["tiff"])
            pixels, evidence = modules["tiff"].read_rgb_tiff(path, (height, width, 3), row["tiff"]["sha256"], budget)
            a.exact(evidence["pixel_sha256"], pixel_hashes[row["ordinal"]], "actual repeated pixel association")
            result["decode_reads"].append(dict(phase="reduce-" + active_scene, ordinal=row["ordinal"], tiff=row["tiff"], pixel_sha256=evidence["pixel_sha256"]))
            values = budget.empty((height, width, 3), "<f8", "actual TIFF code to post-WB DN")
            np.multiply(pixels, 14848. / 65535., out=values)
            return values
        for active_scene in ("flat", "textured"):
            selected = {(r["seed"], r["admission"]): r for r in rows if r["scene"] == active_scene and r["subset"] == "all-five"}
            endpoints = {r["original_indices"][0]: r for r in rows if r["scene"] == active_scene and r["subset"] != "all-five"}
            start = budget.tiff_decodes
            scene = modules["readout"].scene_readout(active_scene, selected, scalar, endpoints, geom, fixture,
                                                    metrics=m, budget=budget, load_rgb=load_rgb)
            io.need(budget.tiff_decodes - start == (34 if active_scene == "flat" else 36), "complete scene actual decode population")
            result["review_triggers"].extend(review_triggers(scene))
            result["scene_results"].append(store.json(active_scene + "-readout.json", scene))
            del scene
        io.need(budget.tiff_decodes == 108 and len(result["decode_reads"]) == 108 and budget.target_cells == 0,
                "complete actual score population with no optical calls")
        result["status"] = "COMPLETE_FIXED_QUALITY_DIAGNOSTICS"
    except Exception:
        result["error"] = traceback.format_exc()
    result["inputs_before"] = {Path(name).relative_to(ROOT).as_posix(): value for name, value in reads.observed.items()}
    ok = io.finish_terminal(store, "result.json", result, "COMPLETE_FIXED_QUALITY_DIAGNOSTICS", check_inputs)
    print(io.canonical_bytes(dict(status=result["status"], complete_entries=len(result["entries"]),
                                  scene_results=len(result["scene_results"]), error=result["error"],
                                  finalization_errors=result["finalization_errors"])).decode(), flush=True)
    return 0 if ok else 1


if __name__ == "__main__": raise SystemExit(main())
