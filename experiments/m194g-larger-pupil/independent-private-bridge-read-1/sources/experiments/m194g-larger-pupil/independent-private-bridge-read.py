"""Independent saved private-RGB read; no stacker or optical producer imports."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.perf_counter()
import argparse
import copy
import hashlib
import importlib.util
import math
from pathlib import Path
import re
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PREFIX = "merge_cmd::known_scene_benchmark::noise_pupil_bridge::private_controls"
FIELDS = ("constant-off", "constant-count", "constant-placebo", "affine-off", "green-change-off", "constant-pedestal")
ENV = dict(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER="1", STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
XS = (109, 110, 127, 128, 159, 160, 191, 192, 207, 208)
YS = (107, 108, 119, 120, 131, 132)
WB = (1.3333333730697632, 1., 1.6666666269302368)
IO = None


def need(ok, message):
    if not ok: raise ValueError(message)


def keys(value, names, label):
    need(type(value) is dict and set(value) == set(names), label + " keys")


def integer(value):
    return type(value) is int and value >= 0


def bind(ref, reads):
    path = reads.ref(ref)
    actual = IO.file_binding(path)
    need(actual == {k: ref[k] for k in ("sha256", "bytes")}, "bound stream bytes")
    key = str(path.resolve())
    need(key not in reads.observed or reads.observed[key] == actual, "changed bound stream")
    reads.observed[key] = actual
    reads.budget.check()
    return path


def mapped(mapping, reads):
    need(type(mapping) is dict and mapping, "nonempty file mapping")
    for path, value in mapping.items(): bind(dict(path=path, **value), reads)


def build_record(ref, reads):
    value, _ = reads.json(ref)
    need(value["schema"] == "m194g-bridge-build-v1" and value["status"] == "COMPLETE_COMPILED_TESTS_ONLY"
         and value["rebuilt_cli"] is True and type(value["exit_code"]) is int and value["exit_code"] == 0
         and value["error"] is None and value["finalization_errors"] == [], "actual compiled build")
    need(value["sources_before"] == value["sources_after"], "build source closure")
    mapped(value["sources_before"], reads)
    for name in ("compiler_artifact", "test_executable", "driver", "execution_release", "compiler_log", "test_listing"):
        bind(value[name], reads)
    need(all(value["compiler_artifact"][k] == value["test_executable"][k] for k in ("sha256", "bytes")), "compiler/copy identity")
    log = (ROOT / value["compiler_log"]["path"]).read_bytes()
    need(b"Compiling strehl-cli" in log, "actual CLI rebuild line")
    return value


def command_record(ref, kind, build, reads):
    value, _ = reads.json(ref)
    need(value["schema"] == "m194g-production-command-v1" and value["status"] == "COMPLETE_PRODUCTION_COMMAND_UNVERIFIED"
         and value["kind"] == kind and value["error"] is None and value["finalization_errors"] == [], "complete private command")
    need(value["sources_before"] == value["sources_after"] and value["inputs_before"] == value["inputs_after"], "private command closure")
    mapped(value["sources_before"], reads); mapped(value["inputs_before"], reads)
    released, _ = reads.json(value["execution_release"])
    choices = [[value["execution_release"]["sha256"] if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in row] for row in released["commands"]]
    need(value["invocation"] in choices and released["scope"] == "production-" + kind, "actual private invocation")
    need(value["build"] == build, "same private build")
    launch, _ = reads.json(value["child"]["launch"])
    need(launch == value["child"]["record"], "actual private launch association")
    need(launch["schema"] == "m194g-private-production-launch-v1" and launch["phase"] == kind
         and launch["status"] == "COMPLETE_CHILD_EXIT_ZERO" and type(launch["exit_code"]) is int
         and launch["exit_code"] == 0 and launch["error"] is None, "actual successful child")
    executable = value["child"]["record"]["executable"]
    parent_build, _ = reads.json(build)
    need(executable == parent_build["test_executable"], "same actual compiled private executable")
    bind(executable, reads)
    expected = ([str((ROOT / executable["path"]).resolve()), PREFIX, "--test-threads=1", "--nocapture"] if kind == "private-controls" else
                [str((ROOT / executable["path"]).resolve()), "--exact", PREFIX + "::m194g_private_production_outputs", "--ignored", "--test-threads=1", "--nocapture"])
    need(launch["command"] == expected, "exact private test selection")
    need(all(launch["environment"].get(k) == v for k, v in ENV.items()), "actual required private environment")
    for k, v in launch["environment"].items():
        if k.startswith("STREHL_") and k not in ENV and k != "STREHL_M194G_BRIDGE_PRIVATE_OUTPUT":
            need(v is None, "private foreign environment override")
    output = Path(value["child"]["private_output"]).resolve()
    need(output.is_relative_to(ROOT) and launch["environment"]["STREHL_M194G_BRIDGE_PRIVATE_OUTPUT"] == str(output), "private output association")
    log_path = bind(launch["log"], reads)
    need(launch["log"]["bytes"] <= 16 * 1024**2 and 0 <= launch["wall_seconds"] <= 240, "actual private operational bounds")
    log = log_path.read_text(encoding="utf8")
    summaries = [line for line in log.splitlines() if line.startswith("test result:")]
    passed, ignored = (6, 1) if kind == "private-controls" else (1, 0)
    need(len(summaries) == 1 and re.fullmatch(rf"test result: ok\. {passed} passed; 0 failed; {ignored} ignored; 0 measured; [0-9]+ filtered out; finished in [0-9.]+s", summaries[0]) is not None, "actual private test count")
    return value, output, log


def geometry(value):
    keys(value, ("full_native", "full_quad", "crop_quad", "canonical_native_offset", "output_native", "reference_coordinate_gauge", "reference_local_index", "level_sizes", "placements"), "private geometry")
    for name in ("full_native", "full_quad", "canonical_native_offset", "output_native"):
        need(type(value[name]) is list and len(value[name]) == 2 and all(integer(v) for v in value[name]), "typed native geometry")
    need(type(value["level_sizes"]) is list and len(value["level_sizes"]) == 4
         and all(type(row) is list and len(row) == 2 and all(integer(v) for v in row) for row in value["level_sizes"]), "typed level geometry")
    need(value["full_native"] == [320, 240] and value["full_quad"] == [160, 120], "private full geometry")
    rect = value["crop_quad"]
    keys(rect, ("x", "y", "width", "height"), "crop")
    need(all(integer(v) for v in rect.values()) and rect["width"] > 0 and rect["height"] > 0, "typed crop")
    x, y, w, h = (rect[k] for k in ("x", "y", "width", "height"))
    need(x + w <= 160 and y + h <= 120, "contained crop")
    need(value["canonical_native_offset"] == [2*x, 2*y] and value["output_native"] == [2*w, 2*h], "native quad mapping")
    need(type(value["reference_coordinate_gauge"]) is int and value["reference_coordinate_gauge"] == 2
         and type(value["reference_local_index"]) is int and value["reference_local_index"] == 2, "private reference gauge")
    levels = []
    lw, lh = w, h
    for _ in range(4):
        levels.append([lw, lh]); lw, lh = (lw + 1)//2, (lh + 1)//2
    need(value["level_sizes"] == levels and min(levels[-1]) >= 8, "three actual Laplacian levels")
    expected = [dict(original_index=i, local_index=i, probe_seed_index=i,
                     quad_similarity=dict(a_re=1., a_im=0., b_re=0., b_im=0.)) for i in range(5)]
    need(IO.canonical_bytes(value["placements"]) == IO.canonical_bytes(expected), "private identity placement/probe")
    need(104-2*x >= 74 and 2*(x+w)-216 >= 74 and 104-2*y >= 74 and 2*(y+h)-136 >= 74, "private supported oracle window")
    return (2*h, 2*w, 3), (2*x, 2*y)


def floors(log, expected_count):
    lines = [line for line in log.splitlines() if line.startswith("measured floor  :")]
    counts = re.findall(r"THE FLOOR THE GATE ACTUALLY USED, averaged over ([0-9]+) warped", log)
    need(len(lines) == len(counts) == expected_count, "private floor banner population")
    values = []
    for line, count in zip(lines, counts, strict=True):
        numbers = [float(v) for v in line.split(":", 1)[1].split()]
        need(1 <= len(numbers) <= 2 and all(math.isfinite(v) and v >= 0 for v in numbers) and int(count) == 5, "private finite measured floor/count")
        values.append(numbers)
    return values


def expected(field, x, y):
    raw = (1500 + 2*x + y, 1800 + x + 3*y + (64 if field == "green-change-off" else 0), 2300 + 3*x + 2*y) if field in ("affine-off", "green-change-off") else (1800, 2000, 2400)
    return tuple(a*b for a, b in zip(raw, WB, strict=True))


def canonical_output(value):
    need(type(value) is str, "absolute native output path")
    # Rust canonicalize() returns Windows verbatim paths; normalize only that
    # native spelling, then enforce the exact contained expected output below.
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    path = Path(value)
    need(path.is_absolute(), "absolute native output path")
    return path.resolve(strict=True)


def pixels_check(pixels, field, offset, *, shift=(0, 0)):
    errors = [0., 0., 0.]
    for y in YS:
        for x in XS:
            actual = pixels[y-offset[1], x-offset[0]]
            oracle = expected(field, x+shift[0], y+shift[1])
            for c in range(3): errors[c] = max(errors[c], abs(int(actual[c])*14848./65535. - oracle[c]))
    need(max(errors) <= .25, "private independent native RGB oracle")
    return dict(sites=len(XS)*len(YS), maximum_absolute_dn=max(errors), per_channel_maximum_absolute_dn=errors)


def main():
    global IO
    spec = importlib.util.spec_from_file_location("m194g_private_rgb_io", HERE / "independent-quality-io.py")
    IO = importlib.util.module_from_spec(spec); spec.loader.exec_module(IO)
    parser = argparse.ArgumentParser()
    for name in ("release", "private-tests", "private-outputs", "build"):
        parser.add_argument("--"+name, type=Path, required=True); parser.add_argument("--"+name+"-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    names = {str((HERE / n).relative_to(ROOT)).replace("\\", "/") for n in (Path(__file__).name, "independent-quality-io.py", "independent-quality-metrics.py", "independent-rgb-tiff.py")}
    release, reads = IO.verify_release(args.release, args.release_sha256, "private-bridge-read", names,
                                       [p.resolve() for p in (args.private_tests, args.private_outputs, args.build, HERE/"next-private-bridge-reader-design.md")])
    m = IO.load_bound(HERE/"independent-quality-metrics.py", "m194g_private_rgb_metrics", release["source_bindings"])
    IO.np = m.np
    budget = m.Budget("instruments", start_cpu=ENTRY_CPU, start_wall=ENTRY_WALL)
    reads.budget = budget
    store = IO.Store(args.output, budget)
    result = dict(schema="m194g-independent-private-bridge-read-v1", status="UNCOMMISSIONED_PRIVATE_BRIDGE_READ",
                  build=IO.file_ref(args.build), private_tests=IO.file_ref(args.private_tests), private_outputs=IO.file_ref(args.private_outputs),
                  execution_release=IO.file_ref(args.release), invocation=IO.invocation(), sources_before=release["source_bindings"], sources_after=None,
                  inputs_before=None, inputs_after=None, outputs=[], controls=[], floor_prefixes=None, work=None, error=None, finalization_errors=[])
    def check_inputs():
        current = reads.finish()
        result["inputs_after"] = {Path(k).relative_to(ROOT).as_posix(): v for k, v in current.items()}
        need(result["inputs_before"] is None or result["inputs_before"] == result["inputs_after"], "private read input closure")
        result["sources_after"] = {name: IO.file_binding(ROOT/name) for name in result["sources_before"]}
        need(result["sources_before"] == result["sources_after"], "private read source closure")
    def control(name, call, fragment):
        try: call()
        except ValueError as exc:
            need(fragment in str(exc), "wrong private reader refusal")
            result["controls"].append(dict(name=name, passed=True, error=str(exc)))
        else: raise ValueError("unpowered private reader control "+name)
    try:
        store.snapshots(release["source_bindings"])
        for key in ("build", "private_tests", "private_outputs"):
            need(result[key]["sha256"] == getattr(args, key+"_sha256"), "external private read pin")
        built = build_record(result["build"], reads)
        command_record(result["private_tests"], "private-controls", result["build"], reads)
        command, output_root, log = command_record(result["private_outputs"], "private-outputs", result["build"], reads)
        need(command["child"]["record"]["executable"] == built["test_executable"], "actual private executable")
        parent_path = output_root / "private-outputs/result.json"
        private, _ = reads.json(IO.file_ref(parent_path))
        keys(private, ("schema", "status", "fixture_only", "environment", "outputs", "decode_fault", "scope"), "private RGB parent")
        need(private["schema"] == "m194g-private-bridge-output-v1" and private["status"] == "COMPLETE_PRIVATE_RGB_UNVERIFIED"
             and private["fixture_only"] is True and private["environment"] == ENV, "private RGB parent completion")
        need(tuple(r["name"] for r in private["outputs"]) == FIELDS, "exact six RGB private rows")
        result["floor_prefixes"] = floors(log, 6)
        control("missing-floor", lambda: floors(log.replace("measured floor  :", "missing floor   :", 1), 6), "population")
        control("duplicate-floor", lambda: floors(log + "\nmeasured floor  : 1\n", 6), "population")
        control("nonfinite-floor", lambda: floors(log.replace("measured floor  :", "measured floor  : nan ", 1), 6), "finite")
        control("wrong-contributors", lambda: floors(log.replace("averaged over 5 warped", "averaged over 4 warped", 1), 6), "count")
        tiff = IO.load_bound(HERE/"independent-rgb-tiff.py", "m194g_private_rgb_tiff", release["source_bindings"])
        identities = set()
        first_shape = first_offset = None
        for row in private["outputs"]:
            keys(row, ("name", "configuration", "geometry", "output", "successful_decode_counts", "hook_calls"), "private RGB row")
            field = row["name"]
            obs = "count" if field == "constant-count" else "placebo" if field == "constant-placebo" else "off"
            need(row["configuration"] == dict(admission="FloorPedestalV1" if field == "constant-pedestal" else "HardFloor", observer=obs), "private setting")
            need(type(row["successful_decode_counts"]) is list and all(type(v) is int for v in row["successful_decode_counts"])
                 and row["successful_decode_counts"] == [int(obs == "count")]*5 and type(row["hook_calls"]) is int
                 and row["hook_calls"] == (0 if obs == "off" else 5), "actual private observer counts")
            shape, offset = geometry(row["geometry"])
            if field == "constant-off":
                bad = copy.deepcopy(row["geometry"]); bad["output_native"][0] = float(bad["output_native"][0])
                control("float-native-extent", lambda: geometry(bad), "typed native")
                bad = copy.deepcopy(row["geometry"]); bad["level_sizes"][1][0] = float(bad["level_sizes"][1][0])
                control("float-level-extent", lambda: geometry(bad), "typed level")
            if first_shape is None: first_shape, first_offset = shape, offset
            need(shape == first_shape and offset == first_offset, "common private output gauge")
            image = row["output"]
            keys(image, ("path", "sha256", "bytes", "width", "height", "channels", "sample_type", "pixel_sha256_le", "software"), "private output")
            path = canonical_output(image["path"])
            need(path == output_root/"private-outputs"/field/"output.tiff", "private actual TIFF path")
            image_ref = dict(path=path.relative_to(ROOT).as_posix(), sha256=image["sha256"], bytes=image["bytes"])
            bind(image_ref, reads)
            stat = path.stat(); identity = (stat.st_dev, stat.st_ino)
            need(identity not in identities, "private TIFF aliases"); identities.add(identity)
            need(image["width"] == shape[1] and image["height"] == shape[0] and image["channels"] == 3
                 and image["sample_type"] == "u16" and image["software"] == "strehl 0.0.0", "private TIFF metadata")
            budget.tiff_decodes += 1
            pixels, evidence = tiff.read_rgb_tiff(path, shape, image["sha256"], budget)
            need(evidence["pixel_sha256"] == image["pixel_sha256_le"], "actual private pixel bytes")
            checked = pixels_check(pixels, field, offset)
            if field == "affine-off":
                control("false-native-x", lambda: pixels_check(pixels, field, offset, shift=(1, 0)), "native RGB")
                control("false-native-y", lambda: pixels_check(pixels, field, offset, shift=(0, 1)), "native RGB")
            if field == "green-change-off":
                control("discard-green-change", lambda: pixels_check(pixels, "affine-off", offset), "native RGB")
            result["outputs"].append(dict(name=field, tiff=image_ref, geometry=row["geometry"], pixels=evidence, oracle=checked,
                                          successful_decode_counts=row["successful_decode_counts"], hook_calls=row["hook_calls"]))
            del pixels
        hashes = [r["tiff"]["sha256"] for r in result["outputs"][:3]]
        need(len(set(hashes)) == 1, "whole-file observer identity")
        need(private["decode_fault"] == dict(index=3, attempt=1, successful_decode_counts=[1,1,1,0,0], output_absent=True)
             and not (output_root/"private-outputs/decode-fault/output.tiff").exists(), "actual decode-failure output absence")
        need(len(result["controls"]) == 9 and budget.tiff_decodes == 6, "private independent read population")
        result["status"] = "PASS_PRIVATE_PRODUCTION_BRIDGE_READ"
    except Exception:
        result["error"] = traceback.format_exc()
    result["inputs_before"] = {Path(k).relative_to(ROOT).as_posix(): v for k, v in reads.observed.items()}
    ok = IO.finish_terminal(store, "result.json", result, "PASS_PRIVATE_PRODUCTION_BRIDGE_READ", check_inputs)
    print(IO.canonical_bytes(dict(status=result["status"], error=result["error"], finalization_errors=result["finalization_errors"])).decode(), flush=True)
    return 0 if ok else 1


if __name__ == "__main__": raise SystemExit(main())
