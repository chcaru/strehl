"""Independent core/consumer controls, with compiler and actual TIFF bindings."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CORE_PREFIX = "pyramid::m194d_independent_tests::"
CLI_PREFIX = "merge_cmd::known_scene_benchmark::band_admission_benchmark::m194d_independent_consumer_tests::"
CORE_TESTS = ["independent_threshold_cutoff_and_strong_detail",
              "independent_missing_reset_failure_retained",
              "independent_units_order_and_numerical_edges",
              "independent_numeric_refusal_before_hull",
              "independent_config_refusal_and_storage_bound"]
CAMERA_DESCRIPTION = (
    "Linear camera-native RGB (sensor primaries), NO colour matrix, no transfer curve. "
    "THIS IS NOT sRGB -- do not treat it as such. This is the measurement output. "
    "White balance: as-shot per-channel gains, green = 1, applied AFTER black "
    "subtraction and normalisation by (white - black), and AFTER the noise model, "
    "which is calibrated in raw DN before any gain."
)


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def loads(text):
    return json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def load(path):
    return loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bind_build(path, expected_sha, kind):
    require(sha(path) == expected_sha, "external build record SHA mismatch")
    record = load(path)
    require(record["pass"] and record["exit_code"] == 0, "incomplete/failed build")
    crate = "strehl-core" if kind == "core" else "strehl-cli"
    target = "strehl_core" if kind == "core" else "strehl"
    command = record["command"]
    require(command[:2] == ["cargo", "test"] and command[command.index("-p") + 1] == crate,
            "wrong compiler command/package")
    require("--no-run" in command and "--message-format=json-render-diagnostics" in command
            and "-q" not in command and "--quiet" not in command, "missing compile lineage argv")
    log = Path(record["log"])
    require(sha(log) == record["log_sha256"], "compile log hash mismatch")
    raw = log.read_bytes()
    require(f"Compiling {crate}".encode() in raw, "required actual crate rebuild absent")
    artifacts = []
    for line in raw.decode("utf-8", "replace").splitlines():
        if line.startswith("{"):
            item = loads(line)
            if (item.get("reason") == "compiler-artifact" and item.get("executable")
                    and item.get("target", {}).get("name") == target
                    and item.get("profile", {}).get("test")):
                artifacts.append(Path(item["executable"]).resolve())
    require(artifacts == [Path(record["compiler_artifact"]["path"]).resolve()],
            "original compiler-artifact lineage mismatch")
    for key in ["compiler_artifact", "test_executable"]:
        binding = record[key]
        p = Path(binding["path"])
        require(p.is_file() and p.stat().st_size == binding["bytes"] and sha(p) == binding["sha256"],
                f"{key} no longer matches build")
    require(record["compiler_artifact"]["sha256"] == record["test_executable"]["sha256"],
            "copied executable does not match original compiler artifact")
    require(record["sources_before"] == record["sources_after"], "sources changed during compile")
    sources = dict(record["sources_after"])
    if "included_test_sources_after" in record:
        require(record["included_test_sources_before"] == record["included_test_sources_after"],
                "external includes changed during compile")
        sources.update(record["included_test_sources_after"])
    owned = f"experiments/m194d-band-admission/independent-{kind if kind == 'core' else 'consumer'}-tests.rs"
    require(owned in sources and "crates/strehl-core/src/pyramid.rs" in sources,
            "required compiled source binding missing")
    if kind == "cli":
        require("crates/strehl-cli/src/merge_cmd/band-admission-benchmark.rs" in sources,
                "candidate consumer source missing")
    require(all(sha(ROOT / p) == value for p, value in sources.items()),
            "compiled sources no longer match the working source")
    return Path(record["test_executable"]["path"]), sources, record


def environment(gather=None, directory=None):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("STREHL_")}
    for key in ["RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RAYON_NUM_THREADS", "CARGO_TARGET_DIR"]:
        env.pop(key, None)
    env.update(STREHL_DEFECT="off", STREHL_FIX_CA="off",
               STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
    if gather is not None:
        env["STREHL_FULLRES_GATHER"] = gather
    if directory is not None:
        env["STREHL_M194D_INDEPENDENT_OUTPUT"] = str(directory)
    return env


def run_child(exe, prefix, env, log):
    command = [str(exe), prefix, "--test-threads=1", "--nocapture"]
    started = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    log.write_bytes(proc.stdout + proc.stderr)
    text = proc.stdout.decode("utf-8", "replace")
    record = dict(command=command, exit_code=proc.returncode, started_utc=started,
                  ended_utc=datetime.now(timezone.utc).isoformat(), log=str(log),
                  log_sha256=sha(log), environment={k: v for k, v in env.items()
                  if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"},
                  evidence=[s for s in text.splitlines() if "M194D_INDEPENDENT" in s])
    return record, text


def check_tiffs(directory, text, gather):
    import numpy as np
    import tifffile
    emitted = []
    for line in text.splitlines():
        preamble = f"test {CLI_PREFIX}independent_candidate_layout_and_source_power ... "
        if line.startswith(preamble):
            line = line[len(preamble):]
        if line.startswith("M194D_INDEPENDENT_CONSUMER "):
            emitted.append(loads(line.split(" ", 1)[1]))
    require(len(emitted) == 20 and len({x["label"] for x in emitted}) == 20,
            "actual TIFF emission records incomplete/duplicated")
    summaries = [loads(s.split(" ", 1)[1]) for s in text.splitlines()
                 if s.startswith("M194D_INDEPENDENT_CONSUMER_SUMMARY ")]
    require(len(summaries) == 1 and summaries[0]["layout_equalities"] == 8
            and summaries[0]["observer_equalities"] == 4
            and summaries[0]["live_controls"] == 6 and not summaries[0]["stats_flags_used"],
            "wrong actual consumer control summary")
    records = {}
    for record in emitted:
        p = Path(record["path"]).resolve()
        require(p.parent == directory.resolve() and sha(p) == record["sha256"], "TIFF binding mismatch")
        observer = record["observer"]
        require(observer in ["Off", "Count", "Placebo"], "unknown counter observer arm")
        require(record["reads"] == ([1] if observer == "Count" else [0]) * 5
                and record["placebo_count"] == (5 if observer == "Placebo" else 0)
                and record["admission"] == "FloorPedestalV1"
                and record["fullres"] == (gather == "1"), "consumer did not exercise pinned observer/mode/one pass")
        expected_observer = ("Off" if record["label"].endswith("-counter-off") else
                             "Placebo" if record["label"].endswith("-counter-placebo") else "Count")
        require(observer == expected_observer, "emitted observer not requested arm")
        with tifffile.TiffFile(p) as tif:
            require(len(tif.pages) == 1, "TIFF page count changed")
            page = tif.pages[0]
            pixels = page.asarray()
            shape = [156, 224, 3] if record["cropped"] else [190, 274, 3]
            require(pixels.dtype == np.dtype("uint16") and list(pixels.shape) == shape,
                    "actual TIFF shape/type mismatch")
            require(int(page.photometric) == 2 and int(page.compression) == 1
                    and int(page.planarconfig) == 1, "unsupported TIFF coding")
            orientation = page.tags[274].value if 274 in page.tags else 1
            require(orientation == 1 and 34675 not in page.tags and 301 not in page.tags,
                    "unexpected orientation/profile/transfer interpretation")
            description = page.tags[270].value
            require(description == CAMERA_DESCRIPTION, "incorrect output space/WB disposition")
            info = dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size,
                        shape=shape, pixel_sha256=hashlib.sha256(pixels.astype("<u2").tobytes()).hexdigest(),
                        minimum=int(pixels.min()), maximum=int(pixels.max()),
                        software=page.tags[305].value, description=description,
                        reads=record["reads"], observer=observer, placebo_count=record["placebo_count"],
                        admission=record["admission"])
            require(info["minimum"] != info["maximum"], "unpowered constant delivered stimulus")
            records[record["label"]] = info
    require({p.resolve() for p in directory.glob("*.tif")} == {Path(v["path"]) for v in records.values()},
            "unindexed or missing TIFFs")
    for prefix in ["whole", "crop"]:
        baseline = records[prefix + "-baseline"]
        for name in ["layout1", "layout2", "poison1", "poison2", "counter-off", "counter-placebo"]:
            require(all(records[prefix + "-" + name][k] == baseline[k]
                        for k in ["sha256", "pixel_sha256", "shape"]), "layout/poison identity failed")
        for name in ["single-site", "noise", "warp"]:
            require(all(records[prefix + "-" + name][k] != baseline[k]
                        for k in ["sha256", "pixel_sha256"]), "actual source/model/warp control inert")
    return records


def main():
    import numpy as np
    import tifffile
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-build", type=Path, required=True)
    parser.add_argument("--core-sha256", required=True)
    parser.add_argument("--cli-build", type=Path, required=True)
    parser.add_argument("--cli-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194d-independent-components-v1", started_utc=datetime.now(timezone.utc).isoformat(),
                  runner_sha256=sha(__file__), design_sha256=sha(HERE / "independent-design.md"),
                  observer_clarification_sha256=sha(HERE / "independent-observer-clarification.md"),
                  python=sys.version, numpy=np.__version__, tifffile=tifffile.__version__,
                  core_build=str(args.core_build.resolve()), core_build_sha256=args.core_sha256,
                  cli_build=str(args.cli_build.resolve()), cli_build_sha256=args.cli_sha256,
                  checks=[], pass_=False)
    try:
        core, core_sources, core_record = bind_build(args.core_build, args.core_sha256, "core")
        cli, cli_sources, cli_record = bind_build(args.cli_build, args.cli_sha256, "cli")
        result["source_bindings"] = dict(core=core_sources, cli=cli_sources)
        child, text = run_child(core, CORE_PREFIX, environment(), out / "core.log")
        child["pass"] = (child["exit_code"] == 0 and "5 passed; 0 failed" in text
                         and all(CORE_PREFIX + t in text for t in CORE_TESTS) and "should panic" in text)
        result["checks"].append(child)
        write(out / "core.json", child)
        print(json.dumps({"group": "core", "pass": child["pass"]}), flush=True)
        for gather in ["0", "1"]:
            directory = out / f"gather-{gather}-tiffs"
            child, text = run_child(cli, CLI_PREFIX, environment(gather, directory), out / f"gather-{gather}.log")
            child["gather"] = gather
            child["pass"] = (child["exit_code"] == 0 and "1 passed; 0 failed" in text
                             and CLI_PREFIX + "independent_candidate_layout_and_source_power" in text)
            # Read outputs even if another assertion fails; do not promote partial artifacts.
            try:
                child["tiffs"] = check_tiffs(directory, text, gather)
                child["artifact_pass"] = True
            except Exception as error:
                child["artifact_pass"] = False
                child["artifact_error"] = repr(error)
                child["pass"] = False
            result["checks"].append(child)
            write(out / f"gather-{gather}.json", child)
            print(json.dumps({"group": f"gather-{gather}", "pass": child["pass"]}), flush=True)
        result["sources_unchanged"] = all(sha(ROOT / p) == h for sources in [core_sources, cli_sources]
                                            for p, h in sources.items())
        result["executables_unchanged"] = all(sha(r[k]["path"]) == r[k]["sha256"]
            for r in [core_record, cli_record] for k in ["compiler_artifact", "test_executable"])
        result["pass_"] = (result["sources_unchanged"] and result["executables_unchanged"]
                           and all(c["pass"] for c in result["checks"]))
    except Exception as error:
        result["exception"] = repr(error)
    result["ended_utc"] = datetime.now(timezone.utc).isoformat()
    write(out / "result.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ["checks", "source_bindings"]}), flush=True)
    return 0 if result["pass_"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
