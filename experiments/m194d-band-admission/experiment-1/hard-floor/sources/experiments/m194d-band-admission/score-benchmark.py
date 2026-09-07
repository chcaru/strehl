"""Read an explicit M194d mode with unchanged M194b numerical scoring."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXED = ROOT / "experiments/m194b-known-scene"
spec = importlib.util.spec_from_file_location("m194b_score", FIXED / "score.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
spec_sparse = importlib.util.spec_from_file_location("m194d_sparse", HERE / "sparse-error.py")
SP = importlib.util.module_from_spec(spec_sparse)
spec_sparse.loader.exec_module(SP)
SEEDS = (None, 701, 709, 719, 727, 733, 739, 743, 751)
MATRIX = {(scene, seed) for scene in ("flat", "plane") for seed in SEEDS}
MATRIX |= {("color", None), ("color-null", None)}
CONFIG = {"merge": "Pyramid", "bands": 3, "gate": 2.0, "exponent": 2.0,
          "sharpen_per_octave": float(np.float32(1.4)), "select": "SoftPower",
          "base": "Mean", "mean_coarse": 0, "hull": "InputRange", "hull_lambda": 2.0,
          "hull_low_only": False, "hull_from_level": 1, "fallback": "Mean",
          "fallback_k": 3, "fallback_power": 4.0, "significance_scale": 0.0,
          "resampler": "CatmullRom", "demosaic": True, "space": "CameraLinear",
          "exposure_stops": 0, "auto_exposure": False, "photometric": "Off",
          "gate_floor_enabled": True, "ca": "off", "defect": "off", "restoration": "unset"}
ENVIRONMENT = {"RAYON_NUM_THREADS": "2", "STREHL_DEFECT": "off", "STREHL_FIX_CA": "off",
               "STREHL_FULLRES_GATHER": "1", "STREHL_PYRAMID_WORKERS": "2"}


MODES = {"hard-floor": ("HardFloor", "hard-floor-v1"),
         "floor-pedestal-v1": ("FloorPedestalV1", "floor-pedestal-v1: q=max(E-F,0); w=(hypot(q/max(F,1),1)/64)^p")}


def configuration(admission):
    require(admission in MODES, "unknown admission mode")
    name, formula = MODES[admission]
    return dict(CONFIG, admission=name, admission_formula=formula)


def environment(admission):
    require(admission in MODES, "unknown admission mode")
    return dict(ENVIRONMENT, STREHL_M194D_ADMISSION=admission)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    d = {}
    for k, v in pairs:
        require(k not in d, f"duplicate JSON field {k}")
        d[k] = v
    return d


def bad_constant(value):
    raise ValueError(f"nonfinite JSON constant {value}")


def read_bound(path, expected):
    p = Path(path)
    require(isinstance(expected, str) and len(expected) == 64
            and all(c in "0123456789abcdef" for c in expected), "invalid SHA-256")
    require(S.sha256(p) == expected, f"content binding changed: {p}")
    return json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                      parse_constant=bad_constant)


def resolve(path, base):
    p = Path(path)
    return p if p.is_absolute() else base / p


def validate_plan(plan, manifest, manifest_sha, admission):
    fields = {"canonical_native_offset", "config", "cover_fit", "crop_quad", "diagnostic",
              "environment", "full_native", "full_quad", "inputs", "level_sizes", "manifest_sha256",
              "noise", "noise_enabled", "normalization", "output_channels", "output_native",
              "placements", "producer", "reference_original_index", "repeat", "roi_native",
              "scale_centre_native", "scene", "schema", "sensor", "software", "wb_f32"}
    require(set(plan) == fields, "unknown/missing fields in frozen plan schema")
    require(plan["schema"] == "m194d-consumer-plan-v1", "wrong plan schema")
    require(plan["manifest_sha256"] == manifest_sha, "plan input binding")
    for key in ("scene", "noise_enabled", "repeat", "sensor", "producer", "inputs"):
        mk = "frames" if key == "inputs" else key
        require(plan[key] == manifest[mk], f"plan differs from input: {key}")
    require(plan["reference_original_index"] == 4, "wrong consumer gauge")
    require(plan["diagnostic"] is None, "diagnostic control is not a baseline output")
    require(plan["full_native"] == [320, 240] and plan["full_quad"] == [160, 120], "wrong full geometry")
    require(plan["roi_native"] == [64, 64, 256, 176], "moved score window")
    require(plan["output_channels"] == 3, "wrong channel count")
    crop = plan["crop_quad"]
    # Trusted pre-render domain from actual fixed-geometry preflight, independently
    # reviewed before the forty-output baseline. Never infer it from TIFF content.
    require(crop == {"x": 9, "y": 7, "width": 142, "height": 106}, "crop differs from frozen registered domain")
    require(set(crop) == {"x", "y", "width", "height"}, "crop fields")
    require(all(type(v) is int for v in crop.values()), "crop is not integer")
    require(min(crop["x"], crop["y"]) >= 0 and min(crop["width"], crop["height"]) > 0, "invalid crop")
    require(crop["x"] + crop["width"] <= 160 and crop["y"] + crop["height"] <= 120, "crop outside full grid")
    require(plan["canonical_native_offset"] == [2 * crop["x"], 2 * crop["y"]], "false canonical mapping")
    require(plan["output_native"] == [2 * crop["width"], 2 * crop["height"]], "wrong crop output dimensions")
    norm = plan["normalization"]
    require(norm["second_black_subtraction"] is False and norm["tiff_u16_to_dn"] == (15360 - 512) / 65535, "wrong delivered-DN conversion")
    require(np.array_equal(np.asarray(plan["wb_f32"], dtype=np.float32).astype(np.float64), S.WB), "wrong white balance")
    noise = plan["noise"]
    for key, wanted in {"gain_dn_per_e": .25, "read_noise_e": 4, "black": 512,
                        "white": 15360, "iso": 160, "variance_at_3000_dn": 751}.items():
        require(noise[key] == wanted, f"wrong injected noise field: {key}")
    require(noise["prnu"] is False, "unexpected fixed pattern")
    require(plan["config"] == configuration(admission), "wrong complete baseline configuration")
    require(plan["environment"] == environment(admission), "wrong complete consumer environment")
    placements = plan["placements"]
    require(len(placements) == 9, "incomplete placement family")
    c = manifest["geometry"]["scale_centre_native"]
    require(c == [183.0, 101.0] and plan["scale_centre_native"] == c, "wrong scale centre")
    for i, (placement, original) in enumerate(zip(placements, manifest["geometry"]["frames"])):
        scale = original["scale"]
        require(placement["original_index"] == i == original["index"], "placement reorder")
        require(placement["scale"] == scale, "placement scale mismatch")
        # Independent direct affine coefficient construction in the full quad gauge.
        got = placement["quad_similarity"]
        expected = {"a_re": scale, "a_im": 0.0,
                    "b_re": (1 - scale) * (c[0] / 2 - 80),
                    "b_im": (1 - scale) * (c[1] / 2 - 60)}
        require(all(math.isfinite(got[k]) and abs(got[k] - v) <= 1e-12 for k, v in expected.items()), "wrong pull direction/centre/scale")
    require(manifest["geometry"]["frames"][4]["scale"] == 1.0, "reference is not identity")
    x, y = S.canonical_grid(*plan["output_native"], crop["x"], crop["y"])
    mask = S.main_mask(x, y)
    return x, y, mask


def validate_commands(index, root, build):
    expected = [(case, None) for case in index["cases"]]
    expected += [(case, arm) for case in index["cases"] for arm in case["arms"]]
    require(len(expected) == 60 and len(index["commands"]) == 60, "wrong command count")
    executable = str(Path(build["test_executable"]["path"]))
    exact_command = [executable, "--exact", "merge_cmd::known_scene_benchmark::band_admission_benchmark::m194d_known_scene_consumer",
                     "--ignored", "--test-threads=1", "--nocapture"]
    build_hash = index["build_record"]["sha256"]
    for command, (case, arm) in zip(index["commands"], expected):
        require(command["exit_code"] == 0, "failed controller command")
        log = resolve(command["log"], root)
        require(S.sha256(log) == command["log_sha256"], "controller log changed")
        ref = command["consumer_evidence"]
        evidence = read_bound(resolve(ref["path"], root), ref["sha256"])
        require(evidence["schema"] == "m194d-consumer-command-v1" and evidence["exit_code"] == 0
                and evidence["pass_"] is True and evidence["build_sha256"] == build_hash
                and evidence["command"] == exact_command, "consumer did not run the pinned test successfully")
        child_log = Path(evidence["log"])
        require(S.sha256(child_log) == evidence["log_sha256"], "consumer command log changed")
        raw_log = child_log.read_bytes()
        require(b"1 passed; 0 failed" in raw_log and b"test result: ok." in raw_log, "missing successful exact-test completion")
        mode = "plan" if arm is None else "render"
        plan_path = resolve(case["plan_path"], root).resolve()
        manifest_path = resolve(case["manifest_path"], root).resolve()
        expected_env = dict(environment(index["admission"]), STREHL_M194B_MODE=mode,
                           STREHL_M194B_MANIFEST=str(manifest_path),
                           STREHL_M194B_MANIFEST_SHA256=case["manifest_sha256"],
                           STREHL_M194B_PLAN=str(plan_path))
        wanted_result, wanted_hash = plan_path, case["plan_sha256"]
        if arm is not None:
            wanted_result = resolve(arm["receipt_path"], root).resolve()
            wanted_hash = arm["receipt_sha256"]
            receipt = read_bound(wanted_result, wanted_hash)
            # Rust canonicalize emits a Windows extended-length path. Compare
            # resolved Paths for outputs, while all other environment values are exact.
            actual_output = Path(evidence["environment"]["STREHL_M194B_OUTPUT"]).resolve()
            require(actual_output.samefile(Path(receipt["output"]["path"])), "command wrote a different TIFF")
            expected_env.update(STREHL_M194B_PLAN_SHA256=case["plan_sha256"],
                               STREHL_M194B_SUBSET="all" if arm["name"] == "full9" else "best",
                               STREHL_M194B_OUTPUT=str(actual_output),
                               STREHL_M194B_RECEIPT=str(wanted_result))
        got_env = dict(evidence["environment"])
        if arm is not None:
            got_env["STREHL_M194B_OUTPUT"] = str(Path(got_env["STREHL_M194B_OUTPUT"]).resolve())
        require(got_env == expected_env, "wrong complete invoked environment")
        require(Path(evidence["result"]).resolve() == wanted_result and evidence["result_sha256"] == wanted_hash,
                "command result differs from indexed case")
        argv = command["command"]
        require(argv[1:4] == ["-X", "utf8", str(HERE / "consumer-run.py")] and argv[4] == mode,
                "unexpected parent driver command")
        # Binding the structured child result does not excuse different parent arguments.
        options = argv[5:]
        require(len(options) % 2 == 0 and len(set(options[::2])) == len(options[::2]), "malformed parent arguments")
        flags = dict(zip(options[::2], options[1::2]))
        wanted_flags = {"--admission": index["admission"], "--build-record": str(resolve(index["build_record"]["path"], root).resolve()),
                        "--build-sha256": build_hash, "--manifest": str(manifest_path),
                        "--manifest-sha256": case["manifest_sha256"], "--plan": str(plan_path),
                        "--log": str(child_log)}
        if arm is not None:
            wanted_flags.update({"--plan-sha256": case["plan_sha256"], "--subset": expected_env["STREHL_M194B_SUBSET"],
                                 "--output": evidence["environment"]["STREHL_M194B_OUTPUT"],
                                 "--receipt": str(wanted_result)})
        require(flags == wanted_flags, "parent argv differs from indexed consumer operation")


def score_run(index_path: Path, expected_sha: str, reader_binding=None):
    index = read_bound(index_path, expected_sha)
    root = index_path.parent
    require(index["schema"] == "m194d-benchmark-run-v1" and index["status"] == "complete", "incomplete/wrong benchmark index")
    require(index["admission"] in MODES, "unknown indexed admission mode")
    require(index["sources_before"] == index["sources_after"], "source changed during baseline")
    snapshot_map = {s["original_path"]: s["sha256"] for s in index["source_snapshots"]}
    require(len(snapshot_map) == len(index["source_snapshots"]) and snapshot_map == index["sources_before"], "source snapshots do not cover exact indexed source map")
    for source in index["source_snapshots"]:
        path = resolve(source["path"], root)
        require(S.sha256(path) == source["sha256"], "frozen source snapshot changed")
    scorer_paths = {"experiments/m194b-known-scene/score.py",
                    "experiments/m194d-band-admission/score-benchmark.py",
                    "experiments/m194d-band-admission/sparse-error.py"}
    actual_readers = {p: S.sha256(ROOT / p) for p in scorer_paths}
    original_readers = {p: snapshot_map.get(p) for p in scorer_paths}
    if reader_binding is None:
        require(actual_readers == original_readers, "active scorer differs; an explicit bound reader revision is required")
    else:
        revision = read_bound(reader_binding[0], reader_binding[1])
        require(revision["schema"] == "m194d-reader-revision-v1" and revision["render_index_sha256"] == expected_sha,
                "reader revision belongs to a different rendered package")
        require(revision["previous"] == original_readers and revision["current"] == actual_readers,
                "reader revision does not bind exact previous/current analysis sources")
        require(isinstance(revision["reason"], str) and len(revision["reason"]) > 10, "reader revision needs an explicit reason")
    build_ref = index["build_record"]
    build = read_bound(resolve(build_ref["path"], root), build_ref["sha256"])
    require(build["schema"] == "m194d-consumer-build-v1" and build["pass"] is True
            and build["exit_code"] == 0 and build["rebuilt_cli"] is True
            and build["sources_before"] == build["sources_after"], "invalid compiled source lineage")
    required_sources = {"Cargo.toml", "Cargo.lock", "crates/strehl-cli/Cargo.toml",
                        "crates/strehl-cli/src/main.rs", "crates/strehl-cli/src/merge_cmd.rs",
                        "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs",
                        "crates/strehl-cli/src/merge_cmd/band-admission-benchmark.rs",
                        "crates/strehl-core/src/pyramid.rs"}
    require(required_sources <= set(build["sources_after"]), "missing compiler inputs")
    require(build["command"] == ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl",
            "--target-dir", "target/m194d-band-admission", "merge_cmd::known_scene_benchmark::band_admission_benchmark::m194d_known_scene_consumer",
            "--no-run", "--message-format=json-render-diagnostics"], "unexpected build argv")
    require(build["environment"] == ENVIRONMENT, "unexpected build environment")
    build_log = Path(build["log"])
    require(S.sha256(build_log) == build["log_sha256"], "build log changed")
    raw_build = build_log.read_bytes()
    require(b"Compiling strehl-cli" in raw_build, "no CLI rebuild evidence")
    compiler_artifacts = []
    for line in raw_build.decode("utf-8", "replace").splitlines():
        if line.startswith("{"):
            message = json.loads(line)
            if (message.get("reason") == "compiler-artifact" and message.get("executable")
                    and message.get("target", {}).get("name") == "strehl"
                    and message.get("profile", {}).get("test")):
                compiler_artifacts.append(message)
    require(len(compiler_artifacts) == 1, "ambiguous/missing test compiler artifact")
    require(all(snapshot_map.get(p) == h for p, h in build["sources_after"].items()), "frozen snapshots differ from compiled sources")
    executable = build["test_executable"]
    require(S.sha256(Path(executable["path"])) == executable["sha256"], "pinned test binary changed")
    artifact = build["compiler_artifact"]
    require(Path(artifact["path"]) == Path(compiler_artifacts[0]["executable"]) and artifact["sha256"] == executable["sha256"]
            and artifact["bytes"] == executable["bytes"], "copied executable differs from compiler artifact")
    require(Path(executable["path"]).stat().st_size == executable["bytes"], "actual copied executable has wrong byte count")
    producer_ref = index["producer_result"]
    producer_path = resolve(producer_ref["path"], root)
    producer = read_bound(producer_path, producer_ref["sha256"])
    require(producer["status"] == "complete", "producer did not complete whole baseline")
    require(producer["sources_before"] == producer["sources_after"], "producer source changed during generation")
    require(all(snapshot_map.get(p) == h for p, h in producer["sources_after"].items()), "frozen snapshots differ from producer sources")
    commission_ref = index["producer_commission"]
    commission_path = resolve(commission_ref["path"], root)
    commission = read_bound(commission_path, commission_ref["sha256"])
    require(producer["commission_sha256"] == commission_ref["sha256"], "producer commissioning binding")
    require(producer["preregistration_sha256"] == commission["preregistration_sha256"], "producer changed preregistration")
    require(commission["source_before"] == commission["source_after"] and commission["source_unchanged"] is True,
            "producer commissioning source changed")
    require(snapshot_map.get("experiments/m194b-known-scene/commission-forward.py") == commission["commission_source_sha256"],
            "commissioning source not frozen in baseline")
    groups = commission["groups"]
    needed = ("flat-dc", "aperture-cfa-quantization", "defocus-diffraction", "noise-law",
              "observer-on-off-placebo", "plane-numerical-convergence", "analytic-color-geometry")
    require(all(groups[name]["status"] == "pass" for name in needed), "not all first-scope producer controls pass")
    by_manifest = {str(resolve(m["path"], producer_path.parent).resolve()): m["sha256"] for m in producer["manifests"]}
    require(len(by_manifest) == 20 and len(index["cases"]) == 20, "incomplete input case count")
    outputs, rows, seen, used_paths = {}, [], set(), set()
    common_domain = None
    for case in index["cases"]:
        key = (case["scene"], case["repeat"])
        require(key in MATRIX and key not in seen, "unexpected/duplicate case")
        require(type(case["noise_enabled"]) is bool and case["noise_enabled"] == (case["repeat"] is not None), "wrong noise repeat label")
        seen.add(key)
        manifest_path = resolve(case["manifest_path"], root)
        require(by_manifest[str(manifest_path.resolve())] == case["manifest_sha256"], "producer case binding")
        manifest = read_bound(manifest_path, case["manifest_sha256"])
        require(manifest["schema"] == "m194b-known-scene-v1" and (manifest["scene"], manifest["repeat"]) == key
                and manifest["noise_enabled"] == case["noise_enabled"], "manifest case label")
        require(len(manifest["frames"]) == 9, "wrong input frame count")
        for i, frame in enumerate(manifest["frames"]):
            path = (manifest_path.parent / frame["path"]).resolve()
            require(path.is_relative_to(manifest_path.parent.resolve()), "source escaped manifest directory")
            require(frame["index"] == i and frame["bytes"] == 153600 and path.stat().st_size == frame["bytes"], "wrong CFA input")
            require(S.sha256(path) == frame["sha256"], "actual CFA input changed")
        plan_path = resolve(case["plan_path"], root)
        plan = read_bound(plan_path, case["plan_sha256"])
        x, y, mask = validate_plan(plan, manifest, case["manifest_sha256"], index["admission"])
        domain = (plan["crop_quad"], plan["output_native"], plan["canonical_native_offset"])
        if common_domain is None:
            common_domain = domain
        require(domain == common_domain, "case-dependent score domain")
        require(len(case["arms"]) == 2 and {a["name"] for a in case["arms"]} == {"full9", "single4"}, "incomplete comparison")
        for arm in case["arms"]:
            receipt_path = resolve(arm["receipt_path"], root)
            receipt = read_bound(receipt_path, arm["receipt_sha256"])
            require(receipt["schema"] == "m194d-consumer-receipt-v1" and receipt["plan"] == plan
                    and receipt["manifest_sha256"] == case["manifest_sha256"]
                    and receipt["plan_sha256"] == case["plan_sha256"], "consumer differs from trusted plan")
            wanted_indices = list(range(9)) if arm["name"] == "full9" else [4]
            require(receipt["frame_subset_original"] == wanted_indices and receipt["reference_original_index"] == 4
                    and receipt["reference_local_index"] == (4 if arm["name"] == "full9" else 0), "wrong single-frame gauge or subset")
            require(receipt["decode_counts"] == [1] * len(wanted_indices) and receipt["confidence"] is None, "unexpected baseline observer/source reads")
            out = receipt["output"]
            require(out["sample_type"] == "u16", "wrong sample type")
            # CameraLinear/no-ICC writer uses package version, as independently
            # verified by M194. Full build lineage lives in the pinned executable.
            require(out["software"] == "strehl 0.0.0", "unexpected camera-linear TIFF Software stamp")
            path = resolve(out["path"], receipt_path.parent)
            require(str(path.resolve()) not in used_paths, "reused output path across cases")
            used_paths.add(str(path.resolve()))
            rgb, tiff = S.read_tiff(path)
            for tk, rk in (("file_sha256", "sha256"), ("pixel_sha256", "pixel_sha256_le"),
                           ("bytes", "bytes"), ("width", "width"), ("height", "height"),
                           ("channels", "channels"), ("software", "software")):
                require(tiff[tk] == out[rk], f"actual TIFF differs from receipt: {tk}")
            require([tiff["width"], tiff["height"]] == plan["output_native"], "actual TIFF has wrong grid")
            require(not any(tiff["rail_zero_by_channel"] + tiff["rail_max_by_channel"]), "unexpected normal-output rails")
            outputs[(case["scene"], case["repeat"], arm["name"])] = rgb
            row = {"scene": case["scene"], "repeat": case["repeat"], "arm": arm["name"],
                   "tiff": tiff, "mask_pixels": int(mask.sum()), "mask_sha256": S.array_hash(mask)}
            for kind in (("ideal", "observation") if case["scene"] in ("flat", "plane") else ("ideal",)):
                ref = S.target(case["scene"], x, y, kind=kind)
                row[kind] = {"reference_sha256": S.array_hash(ref), "error": S.error(rgb, ref, mask)}
                row[kind]["sparse_truth_error"] = SP.summarize(rgb, ref, mask, x, y)
                if case["scene"] == "plane":
                    row[kind]["reference_wave_response"] = S.wave_response(ref, x, y, mask)
            if case["scene"] == "plane":
                row["output_wave_response"] = S.wave_response(rgb, x, y, mask)
            rows.append(row)
    require(seen == MATRIX and len(rows) == 40, "incomplete baseline")
    validate_commands(index, root, build)
    summary = {}
    for scene in ("flat", "plane"):
        summary[scene] = {}
        stacks = {arm: np.stack([outputs[(scene, seed, arm)] for seed in SEEDS[1:]]) for arm in ("full9", "single4")}
        for kind in ("ideal", "observation"):
            ref = S.target(scene, x, y, kind)
            summary[scene][kind] = {arm: S.repeat_error(stack, ref, mask) for arm, stack in stacks.items()}
            summary[scene][kind]["paired"] = S.paired_error(stacks["full9"], stacks["single4"], ref, mask)
        if scene == "plane":
            summary[scene]["wave_response_of_repeat_mean"] = {arm: S.wave_response(stack.mean(axis=0), x, y, mask) for arm, stack in stacks.items()}
    return {"schema": "m194d-mode-score-v1", "admission": index["admission"], "status": "measured-under-declared-model",
            "index_sha256": expected_sha, "scorer_sha256": S.sha256(FIXED / "score.py"),
            "integration_sha256": S.sha256(Path(__file__)), "producer_commission_sha256": commission_ref["sha256"],
            "reader_revision_sha256": reader_binding[1] if reader_binding else None,
            "output_count": len(rows), "domain": common_domain, "rows": rows, "summary": summary,
            "scope": "software discrepancy under explicit synthetic model; no physical/SOTA or two-layer admission",
            "failure_direction": "noise-reducing blur may improve noisy MSE; fixed-wave response and noise-off rows expose lost texture",
            "color_wb_convention": "producer divides exact f64 rational gains; actual f32 WB leaves a small finite-arithmetic discrepancy against desired color target"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--expected-index-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reader-binding", type=Path)
    parser.add_argument("--reader-binding-sha")
    args = parser.parse_args()
    require(not args.out.exists(), "retain earlier result; output already exists")
    require(bool(args.reader_binding) == bool(args.reader_binding_sha), "both reader binding path and digest required")
    revision = (args.reader_binding, args.reader_binding_sha) if args.reader_binding else None
    result = score_run(args.index, args.expected_index_sha, revision)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "outputs": result["output_count"], "domain": result["domain"]}))


if __name__ == "__main__":
    main()
