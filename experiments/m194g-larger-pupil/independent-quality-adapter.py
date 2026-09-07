"""Independent per-output plan/launch/receipt association; no producer imports."""
from datetime import datetime
import math
from pathlib import Path
import re

SEEDS = (701, 709, 719, 727, 733, 739, 743, 751)
MODES = ("hard-floor", "floor-pedestal-v1")
TEST = "merge_cmd::known_scene_benchmark::noise_pupil_bridge::m194g_noise_production_bridge"
ENV_PREFIX = "STREHL_M194G_BRIDGE_"
REQUIRED_ENV = {"STREHL_DEFECT": "off", "STREHL_FIX_CA": "off", "STREHL_FULLRES_GATHER": "1",
                "STREHL_PYRAMID_WORKERS": "2", "RAYON_NUM_THREADS": "2"}
REMOVED = ("STREHL_GATE_FLOOR", "STREHL_GATE_FLOOR_SCALE", "STREHL_WHITE_FLOOR",
           "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_TARGET_DIR")
WB = [1.3333333730697632, 1., 1.6666666269302368]


class Refusal(ValueError): pass


def need(ok, message):
    if not ok: raise Refusal(message)


def exact(actual, expected, label):
    """Strict identity types; finite physical numbers can be integer or float."""
    if type(expected) is float:
        need(type(actual) in (int, float) and math.isfinite(actual) and actual == expected, label)
    elif type(expected) is dict:
        need(type(actual) is dict and set(actual) == set(expected), label + " keys")
        for key, value in expected.items(): exact(actual[key], value, label + "/" + key)
    elif type(expected) is list:
        need(type(actual) is list and len(actual) == len(expected), label + " list")
        for i, value in enumerate(expected): exact(actual[i], value, label + "/" + str(i))
    else:
        need(type(actual) is type(expected) and actual == expected, label)


def keys(value, names, label):
    need(type(value) is dict and set(value) == set(names.split()), label + " keys")


def absolute(value):
    need(type(value) is str, "absolute observed path type")
    # Rust canonicalize on Windows uses the verbatim prefix. Remove only this
    # syntactic prefix; filesystem resolution/containment still occurs below.
    if value.startswith("\\\\?\\"): value = value[4:]
    path = Path(value)
    need(path.is_absolute(), "observed path must be absolute")
    return path.resolve()


def expected_rows():
    rows = []
    state_ordinal = 0
    for scene in ("flat", "textured"):
        for seed in (None, *SEEDS):
            order = MODES if state_ordinal % 2 == 0 else MODES[::-1]
            for mode in order:
                rows.append({"ordinal": len(rows), "scene": scene, "noise_enabled": seed is not None, "seed": seed,
                             "admission": mode, "subset": "all-five", "original_indices": [0, 1, 2, 3, 4]})
            state_ordinal += 1
    for index in (0, 4):
        rows.append({"ordinal": len(rows), "scene": "textured", "noise_enabled": False, "seed": None,
                     "admission": MODES[0], "subset": "endpoint-" + str(index), "original_indices": [index]})
    return rows


def selected_identity(row):
    need(type(row["scene"]) is str and row["scene"] in ("flat", "textured"), "selected scene")
    need(row["seed"] is None or type(row["seed"]) is int and row["seed"] in SEEDS, "selected seed type/value")
    exact(row["noise_enabled"], row["seed"] is not None, "selected noise flag")
    need(type(row["admission"]) is str and row["admission"] in MODES, "selected admission")
    subsets = {"all-five": ("all", [0, 1, 2, 3, 4]), "endpoint-0": ("first", [0]), "endpoint-4": ("last", [4])}
    need(type(row["subset"]) is str and row["subset"] in subsets, "selected subset")
    subset, indices = subsets[row["subset"]]
    exact(row["original_indices"], indices, "selected original indices")
    if subset != "all":
        need(row["scene"] == "textured" and row["seed"] is None and row["admission"] == MODES[0], "endpoint identity")
    return subset, indices


def geometry(value, indices):
    keys(value, "full_native full_quad crop_quad canonical_native_offset output_native reference_coordinate_gauge reference_local_index level_sizes placements", "geometry")
    exact(value["full_native"], [320, 240], "full native")
    exact(value["full_quad"], [160, 120], "full quad")
    rect = value["crop_quad"]
    keys(rect, "x y width height", "quad crop")
    need(all(type(v) is int for v in rect.values()), "quad crop integer types")
    x, y, w, h = (rect[k] for k in ("x", "y", "width", "height"))
    need(0 <= x < 160 and 0 <= y < 120 and 0 < w <= 160 - x and 0 < h <= 120 - y, "quad crop extent")
    exact(value["canonical_native_offset"], [2 * x, 2 * y], "native crop origin")
    exact(value["output_native"], [2 * w, 2 * h], "native crop size")
    sizes = [[w, h]]
    for _ in range(3):
        next_size = [(n + 1) // 2 for n in sizes[-1]]
        need(min(next_size) >= 8, "three actual bands required")
        sizes.append(next_size)
    exact(value["level_sizes"], sizes, "actual level sizes")
    exact(value["reference_coordinate_gauge"], 2, "reference gauge")
    exact(value["reference_local_index"], 0 if len(indices) == 1 else 2, "local reference")
    expected = [{"original_index": original, "local_index": local, "probe_seed_index": local,
                 "quad_similarity": {"a_re": 1., "a_im": 0., "b_re": 0., "b_im": 0.}}
                for local, original in enumerate(indices)]
    exact(value["placements"], expected, "actual placements/probe indices")
    need(104 - 2*x >= 74 and 2*(x+w) - 216 >= 74 and 104 - 2*y >= 74 and 2*(y+h) - 136 >= 74,
         "fixed supported native window")
    return value


def validate_population(value):
    keys(value, "schema status ref_root noise_admission bridge_commission instrument_commission execution_release invocation sources_before sources_after inputs_before inputs_after entries work error finalization_errors", "matrix")
    exact(value["schema"], "m194g-production-matrix-v1", "matrix schema")
    exact(value["status"], "COMPLETE_38_RGB_OUTPUTS_UNSCORED", "matrix status")
    exact(value["ref_root"], "repository", "matrix root")
    exact(value["error"], None, "matrix error")
    exact(value["finalization_errors"], [], "matrix finalization")
    for kind in ("sources", "inputs"):
        need(type(value[kind + "_before"]) is dict and value[kind + "_before"], "nonempty matrix " + kind)
        exact(value[kind + "_after"], value[kind + "_before"], "matrix invariant " + kind)
    rows = value["entries"]
    need(type(rows) is list and len(rows) == 38, "complete38 matrix population")
    file_paths = set()
    for actual, expected in zip(rows, expected_rows(), strict=True):
        keys(actual, "ordinal scene noise_enabled seed admission subset original_indices plan plan_launch receipt tiff log launch", "matrix row")
        for key, wanted in expected.items(): exact(actual[key], wanted, "matrix row " + key)
        for name in ("plan", "plan_launch", "receipt", "tiff", "log", "launch"):
            ref = actual[name]
            keys(ref, "path sha256 bytes", "matrix FileRef")
            need(type(ref["path"]) is str and ref["path"] not in file_paths, "matrix file aliases")
            file_paths.add(ref["path"])
    return rows


def config(mode):
    return {"merge": "Pyramid", "bands": 3, "gate": 2., "exponent": 2., "sharpen_per_octave": 1.399999976158142,
            "admission": "HardFloor" if mode == MODES[0] else "FloorPedestalV1", "select": "SoftPower", "base": "Mean",
            "mean_coarse": 0, "hull": "InputRange", "hull_lambda": 2., "hull_low_only": False, "hull_from_level": 1,
            "fallback": "Mean", "fallback_k": 3, "fallback_power": 4., "significance_scale": 0.,
            "resampler": "CatmullRom", "demosaic": "MHC", "space": "CameraLinear", "fullres_gather": True,
            "exposure_stops": 0, "auto_exposure": False, "confidence": False, "photometric": "Off",
            "gate_floor_enabled": True, "floor_scale": "unset", "ca": "off", "defect": "off", "restoration": "unset"}


def validate_plan(plan, row, *, authority, authority_sha, selected_frames, executable, observer="off"):
    """Pure semantic boundary; actual-file authority is supplied by read_entry."""
    keys(plan, "schema noise_admission_sha256 authority input_bindings selected geometry sensor config injected_noise wb_f32 frame_wb_f32 normalization observer floor_witness environment build", "plan")
    need(plan["schema"] == "m194g-noise-consumer-plan-v1", "plan schema")
    need(observer in ("off", "count", "placebo"), "observer mode")
    subset, indices = selected_identity(row)
    need(type(selected_frames) is list and len(selected_frames) == len(indices), "complete selected frame population")
    exact(plan["noise_admission_sha256"], authority_sha, "noise admission external hash")
    exact(plan["authority"], authority, "actual noise authority")
    exact(plan["selected"], {"scene": row["scene"], "noise_enabled": row["noise_enabled"], "seed": row["seed"],
                             "subset": subset, "frames": selected_frames}, "actual selected source tuple")
    for local, frame in enumerate(selected_frames):
        exact(frame["index"], indices[local], "selected original frame")
        exact(frame["inverse_focus"], .5 + indices[local] / 8, "selected focus")
    geometry(plan["geometry"], indices)
    exact(plan["config"], config(row["admission"]), "fixed production config")
    exact(plan["sensor"], {"cfa": "RGGB", "factors_f64": [.75, 1., 1., .6], "gain_dn_per_e": [.25] * 4,
                           "read_noise_e": [4.] * 4, "black": [512] * 4, "white": [15360] * 4,
                           "quantization": "ties-even-then-clip-[0,15360]", "wb_rgb_f32": WB}, "injected sensor")
    exact(plan["injected_noise"], {"iso": 160., "gain_dn_per_e": [.25] * 4, "read_noise_e": [4.] * 4,
                                  "provenance": "Fallback: injected synthetic algorithm coefficients; not physical calibration", "prnu": False}, "injected algorithm noise")
    exact(plan["wb_f32"], WB, "represented WB")
    exact(plan["frame_wb_f32"], WB, "frame WB")
    exact(plan["normalization"], {"tiff_u16_to_dn": 14848. / 65535., "second_black_subtraction": False,
                                 "input_rounding": "ties-even-then-clip-[0,15360]", "output_rounding": "half-up after clipping"}, "DN normalization")
    exact(plan["observer"], {"mode": observer, "excludes_planning_reads": True, "excludes_raw_prologue": True}, "source observer")
    exact(plan["floor_witness"], {"source": "actual terminal stderr", "eligible_prefix_maximum": 2,
                                 "required": "finite nonempty prefix and count equal selected frames", "unmeasured": "existing white-floor fallback"}, "floor witness scope")
    exact(plan["environment"], REQUIRED_ENV, "actual child required environment")
    exact(plan["build"], {"sha256": executable["sha256"], "bytes": executable["bytes"], "software": "strehl 0.0.0"}, "actual executable identity")
    need(type(plan["input_bindings"]) is dict and plan["input_bindings"], "nonempty actual input ledger")
    return plan["geometry"]


def floor_log(raw, count):
    text = raw.decode("utf8", "strict")
    lines = text.splitlines()
    headers = [line for line in lines if line.startswith("measured floor  :")]
    need(len(headers) == 1, "one measured-floor banner")
    need(re.fullmatch(r"measured floor  : (?:[+-]?[0-9]+\.[0-9]{4})(?: [+-]?[0-9]+\.[0-9]{4})?", headers[0]) is not None,
         "finite nonempty measured-floor prefix")
    values = [float(v) for v in headers[0].split(":", 1)[1].split()]
    need(1 <= len(values) <= 2 and all(math.isfinite(v) and v >= 0 for v in values), "finite nonnegative measured-floor prefix")
    contributions = [line for line in lines if "THE FLOOR THE GATE ACTUALLY USED, averaged over" in line]
    need(len(contributions) == 1 and re.fullmatch(r"                  THE FLOOR THE GATE ACTUALLY USED, averaged over [0-9]+ warped", contributions[0]) is not None,
         "one anchored measured-floor contribution witness")
    actual = int(re.search(r"averaged over ([0-9]+)", contributions[0]).group(1))
    need(actual == count, "measured-floor contributing frame count")
    return {"rounded_mean_prefix": values, "contributing_frames": actual,
            "scope": "actual four-decimal banner, no exact per-frame beta authority"}


def validate_launch(value, row, phase, *, paths, refs, executable, root, observer="off"):
    keys(value, "schema status ordinal phase command environment executable started_utc ended_utc wall_seconds exit_code log error", "parent launch")
    exact(value["schema"], "m194g-production-launch-v1", "launch schema")
    exact(value["status"], "COMPLETE_CHILD_EXIT_ZERO", "launch status")
    exact(value["ordinal"], row["ordinal"], "launch ordinal")
    exact(value["phase"], phase, "launch phase")
    exact(value["exit_code"], 0, "actual exit status")
    exact(value["error"], None, "actual launch error")
    need(type(value["wall_seconds"]) in (int, float) and math.isfinite(value["wall_seconds"])
         and 0 <= value["wall_seconds"] <= 240., "actual launch wall bound")
    dates = [datetime.fromisoformat(value[name]) for name in ("started_utc", "ended_utc")]
    need(all(date.tzinfo is not None for date in dates) and dates[1] >= dates[0], "actual UTC launch timestamps")
    exact(value["executable"], executable, "launch executable ref")
    exe_path = (root / executable["path"]).resolve()
    exact(value["command"], [str(exe_path), "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"], "actual bridge argv")
    env = value["environment"]
    need(type(env) is dict and all(type(k) is str and (v is None or type(v) is str) for k, v in env.items()), "actual launch environment")
    for name, wanted in REQUIRED_ENV.items(): exact(env.get(name), wanted, "required launch " + name)
    for name in REMOVED: need(name in env and env[name] is None, "explicit removed override " + name)
    subset, _ = selected_identity(row)
    values = {"MODE": phase, "NOISE_ADMISSION": str(paths["noise_admission"]),
              "NOISE_ADMISSION_SHA256": refs["noise_admission"]["sha256"], "SCENE": row["scene"],
              "SEED": "noise-off" if row["seed"] is None else str(row["seed"]), "SUBSET": subset,
              "ADMISSION": row["admission"], "OBSERVER": observer, "PLAN": str(paths["plan"])}
    if phase == "render": values.update(PLAN_SHA256=refs["plan"]["sha256"], OUTPUT=str(paths["tiff"]), RECEIPT=str(paths["receipt"]))
    for name, wanted in values.items(): exact(env.get(ENV_PREFIX + name), wanted, "actual launch " + name)
    allowed = {*REQUIRED_ENV, *(ENV_PREFIX + name for name in values)}
    need(all(v is None or k in allowed for k, v in env.items()), "unregistered active child override")
    return value


def read_entry(row, *, io, reads, context, observer="off", decode=False, tiff_reader=None):
    """Actual individual output API, usable for the12 bridge outputs and38 matrix.

    context is supplied after independently admitting its authority/build chain:
    executable FileRef, noise_admission FileRef+object, bundles from that actual
    manifest, manifest_root path, and optional common_geometry. Pure private controls name their
    deliberate bypass of this prerequisite; this function never forges it.
    """
    need(type(row["ordinal"]) is int and row["ordinal"] >= 0, "row ordinal type")
    subset, indices = selected_identity(row)
    executable = context["executable"]
    refs = {name: row[name] for name in ("plan", "plan_launch", "receipt", "tiff", "log", "launch")}
    refs["noise_admission"] = context["noise_admission"]
    paths = {name: reads.ref(ref) for name, ref in refs.items()}
    need(len(set(paths[name] for name in ("plan", "plan_launch", "receipt", "tiff", "log", "launch"))) == 6, "entry file aliases")
    entry_paths = [paths[name] for name in ("plan", "plan_launch", "receipt", "tiff", "log", "launch")]
    need(all(not a.samefile(b) for i, a in enumerate(entry_paths) for b in entry_paths[i + 1:]), "entry physical file aliases")
    def bind_file(path, wanted, cap):
        keys(wanted, "sha256 bytes", "actual file binding")
        need(type(wanted["bytes"]) is int and 0 < wanted["bytes"] <= cap and io.valid_hash(wanted["sha256"]), "actual file binding extent/hash")
        path = path.resolve(strict=True)
        need(path.is_relative_to(io.ROOT) and path.is_file(), "actual bound file outside repository")
        key = str(path)
        if key in reads.observed: exact(reads.observed[key], wanted, "repeated actual file binding")
        else:
            exact(io.file_binding(path), wanted, "actual file bytes")
            reads.observed[key] = wanted
        if reads.budget: reads.budget.check()
    exe_path = reads.ref(executable)
    bind_file(exe_path, {k: executable[k] for k in ("sha256", "bytes")}, 1024**3)
    plan, _ = reads.json(row["plan"])
    receipt, _ = reads.json(row["receipt"])
    bundles = [b for b in context["bundles"] if b["scene"] == row["scene"] and type(b["seed"]) is type(row["seed"]) and b["seed"] == row["seed"]]
    need(len(bundles) == 1, "one actual admitted selected bundle")
    selected = [bundles[0]["frames"][index] for index in indices]
    geom = validate_plan(plan, row, authority=context["authority"], authority_sha=context["noise_admission"]["sha256"],
                         selected_frames=selected, executable=executable, observer=observer)
    ledger = {}
    for name, wanted in plan["input_bindings"].items():
        path = absolute(name)
        need(path not in ledger, "duplicate normalized input ledger path")
        bind_file(path, wanted, 4 * 1024**2)
        ledger[path] = wanted
    for path, expected in [(paths["noise_admission"], refs["noise_admission"])] + [
            (io.relative(context["manifest_root"], frame[key]["path"]), frame[key]) for frame in selected for key in ("cfa", "audit")]:
        need(path in ledger, "selected actual input absent from consumed ledger")
        exact(ledger[path], {k: expected[k] for k in ("sha256", "bytes")}, "selected actual input ledger binding")
    if context.get("common_geometry") is not None:
        # Endpoint local indices differ; output domain and gauge stay common.
        for key in ("full_native", "full_quad", "crop_quad", "canonical_native_offset", "output_native", "level_sizes", "reference_coordinate_gauge"):
            exact(geom[key], context["common_geometry"][key], "common output " + key)
    for phase, name in (("plan", "plan_launch"), ("render", "launch")):
        launch, _ = reads.json(row[name])
        validate_launch(launch, row, phase, paths=paths, refs=refs, executable=executable, root=io.ROOT, observer=observer)
        log_path = reads.ref(launch["log"])
        raw = reads.raw(log_path, launch["log"]["sha256"], launch["log"]["bytes"], cap=16 * 1024**2)
        summaries = [line for line in raw.decode("utf8", "strict").splitlines() if line.startswith("test result:")]
        need(len(summaries) == 1 and re.fullmatch(r"test result: ok\. 1 passed; 0 failed; 0 ignored; 0 measured; [0-9]+ filtered out; finished in [0-9.]+s", summaries[0]) is not None,
             "actual one-test process summary")
        if phase == "render":
            exact(launch["log"], row["log"], "render log association")
            floor = floor_log(raw, len(indices))
    keys(receipt, "schema status plan_sha256 plan successful_decode_counts hook_calls output inputs_unchanged floor_witness", "actual render receipt")
    exact(receipt["schema"], "m194g-noise-consumer-receipt-v1", "receipt schema")
    exact(receipt["status"], "COMPLETE_RGB_UNVERIFIED", "receipt status")
    exact(receipt["plan_sha256"], row["plan"]["sha256"], "actual consumed plan hash")
    exact(receipt["plan"], plan, "actual recomputed versus saved plan")
    exact(receipt["inputs_unchanged"], True, "receipt input invariance")
    exact(receipt["successful_decode_counts"], [int(observer == "count")] * len(indices), "actual source decode counts")
    exact(receipt["hook_calls"], 0 if observer == "off" else len(indices), "actual optional hook calls")
    exact(receipt["floor_witness"], "bound terminal stderr requires independent read; no exact beta authority", "receipt floor scope")
    output = receipt["output"]
    keys(output, "path sha256 bytes width height channels sample_type pixel_sha256_le software", "actual TIFF receipt")
    need(absolute(output["path"]) == paths["tiff"], "actual output path association")
    for key in ("sha256", "bytes"): exact(output[key], row["tiff"][key], "actual TIFF " + key)
    for key, wanted in (("width", geom["output_native"][0]), ("height", geom["output_native"][1]), ("channels", 3), ("sample_type", "u16"), ("software", "strehl 0.0.0")):
        exact(output[key], wanted, "actual TIFF " + key)
    need(io.valid_hash(output["pixel_sha256_le"]), "actual pixel hash type")
    # Reopen/hash the actual file even in a metadata-only association call.
    reads.raw(paths["tiff"], row["tiff"]["sha256"], row["tiff"]["bytes"], cap=1024**2)
    evidence = None
    if decode:
        need(tiff_reader is not None and reads.budget is not None, "actual bounded TIFF decoder/budget required")
        reads.budget.tiff_decodes += 1; reads.budget.check()
        pixels, evidence = tiff_reader.read_rgb_tiff(paths["tiff"], (output["height"], output["width"], 3), row["tiff"]["sha256"], reads.budget)
        exact(evidence["pixel_sha256"], output["pixel_sha256_le"], "independent actual pixel hash")
        del pixels
    return {"row": row, "plan": plan, "receipt": receipt, "geometry": geom, "floor": floor, "decoded": evidence}
