"""Prospective bounded M194d runtime controls; no build and no full matrix.

Choices fixed before the first invocation: flat/seed-709/full9, both modes,
same-mode repeated TIFF byte null and archived M194c off identity. Candidate
pixel change is plumbing power, never quality. Rehashed private plan mutations
change mode/formula/schema/crop/gate; direct child calls test actual missing or
wrong settings. Driver-only controls change copied build bindings, including
the real historical binary. Receipt/index admission waits for the full package.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = ROOT / "experiments/m194c-probe-layout/candidate-2/run/run-index.json"
BASELINE_SHA = "71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab"
TEST = "merge_cmd::known_scene_benchmark::band_admission_benchmark::m194d_known_scene_consumer"
SETTINGS = {"STREHL_DEFECT": "off", "STREHL_FIX_CA": "off", "STREHL_FULLRES_GATHER": "1",
            "STREHL_PYRAMID_WORKERS": "2", "RAYON_NUM_THREADS": "2"}
MODES = ("hard-floor", "floor-pedestal-v1")


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def write(path, value):
    with Path(path).open("x", encoding="utf8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-record", type=Path, required=True)
    parser.add_argument("--build-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("independent_m194d_driver", HERE / "consumer-run.py")
    C = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(C)
    result = dict(schema="m194d-independent-mode-controls-v1", command=sys.argv,
                  script_sha256=sha(__file__), checks=[], invocations=[],
                  scope="bounded runtime plumbing; no full matrix, calibration, default promotion or quality admission")
    build_path = args.build_record.resolve()
    try:
        require(sha(build_path) == args.build_sha256, "external build hash mismatch")
        build = read(build_path)
        require(build["schema"] == "m194d-consumer-build-v1" and build["pass"] is True,
                "not a passed M194d build")
        require(build["rebuilt_cli"] is True and build["exit_code"] == 0,
                "missing actual CLI compilation")
        require(sha(build["log"]) == build["log_sha256"] and
                b"Compiling strehl-cli" in Path(build["log"]).read_bytes(), "compile log mismatch")
        before = C.sources()
        require(before == build["sources_before"] == build["sources_after"], "source map mismatch")
        executable = Path(build["test_executable"]["path"])
        for name in ("test_executable", "compiler_artifact"):
            ref = build[name]
            require(sha(ref["path"]) == ref["sha256"] and Path(ref["path"]).stat().st_size == ref["bytes"],
                    "compiler/pinned artifact mismatch")
        require(build["test_executable"]["sha256"] == build["compiler_artifact"]["sha256"],
                "pinned executable is not compiler output")
        require(sha(BASELINE) == BASELINE_SHA, "historical index changed")
        historical = read(BASELINE)
        case = next(c for c in historical["cases"] if c["scene"] == "flat" and c["repeat"] == 709)
        manifest_path = Path(case["manifest_path"])
        require(sha(manifest_path) == case["manifest_sha256"], "historical manifest changed")
        manifest = read(manifest_path)
        input_hashes = {str(manifest_path): case["manifest_sha256"]}
        for frame in manifest["frames"]:
            path = manifest_path.parent / frame["path"]
            require(path.stat().st_size == frame["bytes"] and sha(path) == frame["sha256"], "input changed")
            input_hashes[str(path)] = frame["sha256"]
        result.update(build_record=dict(path=str(build_path), sha256=args.build_sha256),
                      pinned_executable=build["test_executable"], sources_before=before,
                      inputs_before=input_hashes, baseline_index_sha256=BASELINE_SHA,
                      case=["flat", 709, "full9"], driver_sha256=sha(HERE / "consumer-run.py"))

        def check(name, condition, **details):
            result["checks"].append(dict(name=name, pass_=bool(condition), **details))
            print(("PASS " if condition else "FAIL ") + name, flush=True)

        def guard():
            require(C.sources() == before, "source changed during independent controls")
            require(sha(executable) == build["test_executable"]["sha256"], "pinned executable changed")
            require(sha(HERE / "consumer-run.py") == result["driver_sha256"], "driver changed")

        def env_for(mode, action, plan, destination):
            env = {k: v for k, v in os.environ.items() if not k.upper().startswith("STREHL_")}
            for key in ("RAYON_NUM_THREADS", "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_TARGET_DIR"):
                env.pop(key, None)
            env.update(SETTINGS)
            env.update(STREHL_M194D_ADMISSION=mode, STREHL_M194B_MODE=action,
                       STREHL_M194B_MANIFEST=str(manifest_path), STREHL_M194B_MANIFEST_SHA256=case["manifest_sha256"],
                       STREHL_M194B_PLAN=str(plan))
            if action == "render":
                env.update(STREHL_M194B_PLAN_SHA256=sha(plan), STREHL_M194B_SUBSET="all",
                           STREHL_M194B_OUTPUT=str(destination / "output.tif"),
                           STREHL_M194B_RECEIPT=str(destination / "receipt.json"))
            return env

        def execute(label, argv, env, expected_success, target, output=None, direct=False):
            guard()
            p = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True)
            raw = p.stdout + p.stderr
            log = out / (label + ".log")
            log.write_bytes(raw)
            guard()
            observed = p.returncode == 0 and target.exists()
            if expected_success:
                accepted = observed
            else:
                accepted = p.returncode != 0 and not target.exists() and (output is None or not output.exists())
                if direct:
                    accepted = accepted and b"1 failed" in raw
            evidence = dict(label=label, command=argv, exit_code=p.returncode,
                            log=str(log), log_sha256=sha(log), expected_success=expected_success,
                            environment={k: v for k, v in env.items() if k.upper().startswith("STREHL_") or k == "RAYON_NUM_THREADS"},
                            target_exists=target.exists(), output_exists=output.exists() if output else None,
                            direct_child=direct)
            result["invocations"].append(evidence)
            check(label, accepted)
            return accepted

        def driver(label, mode, action, plan, *, expected=True, supplied_build=None, ambient_changes=None):
            destination = out / label
            destination.mkdir()
            b = supplied_build or build_path
            argv = [sys.executable, "-B", str(HERE / "consumer-run.py"), action,
                    "--admission", mode, "--build-record", str(b), "--build-sha256", sha(b),
                    "--manifest", str(manifest_path), "--manifest-sha256", case["manifest_sha256"],
                    "--plan", str(plan), "--log", str(destination / "child.log")]
            target = plan
            output = None
            if action == "render":
                target, output = destination / "receipt.json", destination / "output.tif"
                argv += ["--plan-sha256", sha(plan), "--subset", "all", "--output", str(output), "--receipt", str(target)]
            ambient = os.environ.copy()
            ambient.update(ambient_changes or {})
            accepted = execute(label, argv, ambient, expected, target, output)
            if expected and accepted:
                witness = read(destination / "child.json")
                expected_env = env_for(mode, action, plan, destination)
                expected_subset = {k: v for k, v in expected_env.items() if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"}
                check(label + "-actual-child-binding", witness["pass_"] is True and witness["exit_code"] == 0
                      and witness["build_sha256"] == args.build_sha256
                      and witness["command"] == [str(executable), "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]
                      and witness["environment"] == expected_subset
                      and sha(witness["log"]) == witness["log_sha256"] and sha(target) == witness["result_sha256"])
            return target, output

        plans = {}
        for mode in MODES:
            path = out / (mode + "-plan.json")
            driver("valid-plan-" + mode, mode, "plan", path)
            require(path.exists(), "valid planning failed; later mutations would lack a valid companion")
            plan = read(path)
            expected_name = "HardFloor" if mode == MODES[0] else "FloorPedestalV1"
            check("compiled-plan-mode-" + mode, plan["schema"] == "m194d-consumer-plan-v1"
                  and plan["config"]["admission"] == expected_name
                  and plan["environment"] == dict(SETTINGS, STREHL_M194D_ADMISSION=mode)
                  and plan["manifest_sha256"] == case["manifest_sha256"])
            plans[mode] = path

        ambient_plan = out / "cleaned-ambient-plan.json"
        driver("valid-driver-clears-ambient-overrides", MODES[1], "plan", ambient_plan,
               ambient_changes={"STREHL_M194D_ADMISSION": MODES[0], "STREHL_PYRAMID_GATE": "8"})
        check("ambient-overrides-are-inert-in-actual-plan", read(ambient_plan) == read(plans[MODES[1]]))

        delivered = {}
        for label, mode in (("valid-off", MODES[0]), ("valid-on", MODES[1]), ("same-off-null", MODES[0])):
            receipt, output = driver(label, mode, "render", plans[mode])
            require(output.exists() and receipt.exists(), "valid render failed")
            value = read(receipt)
            with tifffile.TiffFile(output) as t:
                pixels = t.pages[0].asarray()
                dtype_ok = pixels.dtype == np.dtype("uint16")
            pixel_sha = hashlib.sha256(pixels.astype("<u2", copy=False).tobytes()).hexdigest()
            check(label + "-actual-tiff-and-receipt", dtype_ok and pixels.shape == (212, 284, 3)
                  and value["schema"] == "m194d-consumer-receipt-v1" and value["plan"] == read(plans[mode])
                  and value["plan_sha256"] == sha(plans[mode]) and value["manifest_sha256"] == case["manifest_sha256"]
                  and value["frame_subset_original"] == list(range(9)) and value["decode_counts"] == [1] * 9
                  and value["output"]["sha256"] == sha(output) and value["output"]["pixel_sha256_le"] == pixel_sha)
            delivered[label] = (output, pixels)
        check("same-off-byte-null", sha(delivered["valid-off"][0]) == sha(delivered["same-off-null"][0]))
        arm = next(a for a in case["arms"] if a["name"] == "full9")
        old_receipt = BASELINE.parent / arm["receipt_path"]
        require(sha(old_receipt) == arm["receipt_sha256"], "historical receipt changed")
        old = read(old_receipt)["output"]
        require(sha(old["path"]) == old["sha256"], "historical TIFF changed")
        check("one-off-historical-whole-tiff-identity", sha(delivered["valid-off"][0]) == old["sha256"])
        delta = delivered["valid-on"][1].astype(np.int32) - delivered["valid-off"][1].astype(np.int32)
        check("candidate-setting-has-actual-pixel-power", bool(np.any(delta)),
              changed_components=int(np.count_nonzero(delta)), maximum_movement_tiff_lsb=int(np.max(np.abs(delta))),
              interpretation="plumbing power only; no quality inference")

        direct_argv = [str(executable), "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]

        def direct(label, *, plan=None, changes=None, omit=(), action="render", expected=False):
            destination = out / label
            destination.mkdir()
            plan = plan or plans[MODES[1]]
            if action == "plan":
                plan = destination / "plan.json"
            env = env_for(MODES[1], action, plan, destination)
            for key in omit:
                env.pop(key, None)
            env.update(changes or {})
            target = plan if action == "plan" else destination / "receipt.json"
            execute(label, direct_argv, env, expected, target,
                    destination / "output.tif" if action == "render" else None, direct=True)
            return target

        direct_plan = direct("valid-direct-child-plan", action="plan", expected=True)
        check("direct-child-valid-companion-matches-driver", read(direct_plan) == read(plans[MODES[1]]))
        direct("missing-admission", omit=("STREHL_M194D_ADMISSION",), action="plan")
        for i, bad in enumerate(("", "HardFloor", "floor-pedestal-v2")):
            direct(f"malformed-admission-{i}", changes={"STREHL_M194D_ADMISSION": bad}, action="plan")
        direct("missing-gather-setting", omit=("STREHL_FULLRES_GATHER",), action="plan")
        direct("wrong-worker-setting", changes={"STREHL_PYRAMID_WORKERS": "1"}, action="plan")
        direct("unexpected-gate-setting", changes={"STREHL_PYRAMID_GATE": "8"}, action="plan")
        direct("forbidden-white-diagnostic", changes={"STREHL_M194B_DIAGNOSTIC": "white-floor-isolation",
                                                        "STREHL_GATE_FLOOR": "white"}, action="plan")
        direct("on-mode-with-valid-off-plan", plan=plans[MODES[0]])
        mutations = {
            "plan-legacy-schema": lambda p: p.update(schema="m194b-consumer-plan-v1"),
            "plan-unknown-schema": lambda p: p.update(schema="m194d-consumer-plan-v2"),
            "plan-missing-admission": lambda p: p["config"].pop("admission"),
            "plan-false-admission": lambda p: p["config"].update(admission="HardFloor"),
            "plan-false-formula": lambda p: p["config"].update(admission_formula="hard-floor-v1"),
            "plan-bool-admission": lambda p: p["config"].update(admission=True),
            "plan-extra-field": lambda p: p.update(unregistered=True),
            "plan-unrelated-gate": lambda p: p["config"].update(gate=4.0),
            "plan-coherent-crop-shift": lambda p: (p["crop_quad"].update(x=p["crop_quad"]["x"] + 1),
                                                   p["canonical_native_offset"].__setitem__(0, p["canonical_native_offset"][0] + 2)),
        }
        for label, mutate in mutations.items():
            changed = copy.deepcopy(read(plans[MODES[1]]))
            mutate(changed)
            path = out / (label + ".json")
            write(path, changed)
            direct(label, plan=path)
        duplicate = out / "plan-duplicate-schema.json"
        text = plans[MODES[1]].read_text(encoding="utf8")
        duplicate.write_text('{"schema":"m194d-consumer-plan-v1",' + text.lstrip()[1:], encoding="utf8")
        direct("plan-duplicate-schema", plan=duplicate)

        for label, drop in (("rehashed-build-missing-core", "crates/strehl-core/src/pyramid.rs"),
                            ("rehashed-build-missing-test-source", "experiments/m194d-band-admission/independent-consumer-tests.rs")):
            changed = copy.deepcopy(build)
            require(drop in changed["sources_after"], "chosen source omission did not occur")
            changed["sources_before"].pop(drop)
            changed["sources_after"].pop(drop)
            path = out / (label + ".json")
            write(path, changed)
            driver(label, MODES[1], "plan", out / (label + "-plan.json"), expected=False, supplied_build=path)
        old_build_ref = historical["build_record"]
        require(sha(old_build_ref["path"]) == old_build_ref["sha256"], "historical build changed")
        old_exe = read(old_build_ref["path"])["test_executable"]
        require(sha(old_exe["path"]) == old_exe["sha256"], "historical executable changed")
        changed = copy.deepcopy(build)
        changed["test_executable"] = old_exe
        path = out / "rehashed-build-old-executable.json"
        write(path, changed)
        driver("rehashed-build-old-executable", MODES[1], "plan", out / "old-executable-plan.json", expected=False, supplied_build=path)
        guard()
        result["sources_after"] = C.sources()
        result["inputs_after"] = {path: sha(path) for path in input_hashes}
        check("all-source-and-input-bytes-unchanged", result["sources_after"] == before and result["inputs_after"] == input_hashes)
        result["pass_"] = all(c["pass_"] for c in result["checks"])
    except Exception as exc:
        result.update(pass_=False, failure=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        write(out / "result.json", result)
        print(json.dumps(dict(pass_=result.get("pass_", False), checks=len(result["checks"]), result=str(out / "result.json"))), flush=True)
    return 0 if result["pass_"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
