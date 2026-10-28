"""Root-only bounded commissioning and actual weevil placement observation."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import threading
import time

import psutil

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-27"
PRIOR = ROOT / "experiments/raw-quality-2026-10-27/reconstruction-photo-observation/run.py"
spec = importlib.util.spec_from_file_location("insect_observer_helpers", PRIOR)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
b, ref, save = prior.b, prior.ref, prior.save


def check_refs(rows):
    for row in rows:
        assert ref(row["path"]) == row, f"bound file changed: {row['path']}"


def folder(stage, iteration):
    return CAMPAIGN / f"insect-placement-{stage}-{iteration}"


def observed_run(command, env, out, bounds):
    rows, stop = [], threading.Event()

    def observe():
        psutil.cpu_percent(None)
        while not stop.is_set():
            rows.append(dict(monotonic_seconds=time.monotonic(),
                host_cpu_percent=psutil.cpu_percent(None),
                available_ram_bytes=psutil.virtual_memory().available))
            stop.wait(2)

    observer = threading.Thread(target=observe, daemon=True)
    observer.start()
    try:
        result = b.run(command, env, ROOT, out / "process.log",
                       api=b.load_job_api(b.binding(b.HARNESS)), **bounds)
    finally:
        stop.set()
        observer.join(timeout=3)
        save(out / "host-observation.json", dict(rows=rows,
             logical_cpus=psutil.cpu_count(), physical_cpus=psutil.cpu_count(logical=False),
             scope="Whole-host load; not an exclusive performance benchmark."))
    save(out / "process.json", result)
    print(json.dumps({k: result[k] for k in ("exit_code", "error", "wall_seconds", "job_memory")}))
    print((out / "process.log").read_text(encoding="utf-8", errors="replace")[-16000:])
    assert result["exit_code"] == 0 and result["error"] is None
    assert result["terminal_job_accounting"] and not result["cleanup_errors"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("build", "checks", "core-tests", "controls-core", "controls", "observe", "summary", "support"))
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--build-iteration", type=int, default=1)
    parser.add_argument("--controls-iteration", type=int, default=1)
    parser.add_argument("--observation-iteration", type=int, default=1)
    parser.add_argument("--summary-iteration", type=int, default=1)
    args = parser.parse_args()
    assert min(args.iteration, args.build_iteration, args.controls_iteration, args.observation_iteration) > 0
    out = folder(args.stage, args.iteration)
    out.mkdir(parents=True, exist_ok=False)
    if args.stage == "checks":
        sources = prior.source_bindings()
        save(out / "rust-sources.json", sources)
        env, removed = b.clean_environment()
        env.update(CARGO_BUILD_JOBS="4", STREHL_TEST_TMP=str(CAMPAIGN / "test-tmp"))
        checks = [
            ("clippy-core", ["cargo", "clippy", "--locked", "--offline", "-p", "strehl-core", "--all-targets", "--no-deps", "--", "-D", "warnings"]),
            ("clippy-cli", ["cargo", "clippy", "--locked", "--offline", "-p", "strehl-cli", "--all-targets", "--no-deps", "--", "-D", "warnings"]),
            ("fmt-core", ["cargo", "fmt", "-p", "strehl-core", "--", "--check"]),
            ("fmt-cli", ["cargo", "fmt", "-p", "strehl-cli", "--", "--check"]),
        ]
        rows = []
        for name, command in checks:
            start = time.monotonic()
            with (out / (name + ".log")).open("xb") as log:
                process = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
            rows.append(dict(name=name, command=command, exit_code=process.returncode,
                             wall_seconds=time.monotonic()-start, log=ref(out / (name + ".log"))))
            print(json.dumps({k: rows[-1][k] for k in ("name", "exit_code", "wall_seconds")}))
        check_refs(sources)
        save(out / "checks.json", dict(checks=rows, removed_environment=removed,
             scope="Actual check exits; preexisting failures require source-specific review. No green aggregate claim."))
        return
    if args.stage == "build":
        sources = prior.source_bindings()
        save(out / "rust-sources.json", sources)
        command = ["cargo", "test", "--locked", "--offline", "--release", "-p", "strehl-core",
                   "-p", "strehl-cli", "--lib", "--no-run", "--jobs", "4",
                   "--message-format=json-render-diagnostics"]
        env, removed = b.clean_environment()
        env.update(CARGO_INCREMENTAL="0", CARGO_BUILD_JOBS="4",
                   STREHL_TEST_TMP=str(CAMPAIGN / "test-tmp"))
        save(out / "invocation.json", dict(command=command, removed_environment=removed,
             runner=ref(__file__), scope="Root-supervised compilation only; four workers."))
        started = time.monotonic()
        with (out / "artifacts.jsonl").open("xb") as stdout, (out / "build.log").open("xb") as stderr:
            process = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
        save(out / "process.json", dict(exit_code=process.returncode, wall_seconds=time.monotonic()-started))
        log = (out / "build.log").read_text(encoding="utf-8", errors="replace")
        print(log[-18000:])
        assert process.returncode == 0
        assert "Compiling strehl-core" in log and "Compiling strehl-cli" in log
        check_refs(sources)
        rows = [json.loads(line) for line in (out / "artifacts.jsonl").read_text(encoding="utf-8").splitlines()
                if line.startswith("{")]
        assert any(r.get("reason") == "build-finished" and r.get("success") for r in rows)
        executables = {}
        for crate in ("strehl_core", "strehl_cli"):
            exes = [r["executable"] for r in rows if r.get("reason") == "compiler-artifact"
                    and r.get("executable") and r.get("target", {}).get("name") == crate
                    and r.get("profile", {}).get("test")]
            assert len(exes) == 1
            exe = out / (crate.replace("_", "-") + "-tests.exe")
            shutil.copyfile(exes[0], exe)
            assert b.binding(exe) == b.binding(exes[0])
            executables[crate] = ref(exe)
        save(out / "executables.json", executables)
        save(out / "completion.json", dict(reports=[ref(out / "executables.json"), ref(out / "rust-sources.json")],
             source_bindings_unchanged=True, photographic_improvement_claimed=False))
        print(json.dumps(executables))
        return

    build = folder("build", args.build_iteration)
    completion = json.loads((build / "completion.json").read_text())
    check_refs(completion["reports"])
    sources = json.loads((build / "rust-sources.json").read_text())
    if args.stage in ("summary", "support"):
        # These read saved evidence only. The historical source manifest is
        # bound by build completion; current Rust files are not their inputs.
        sources = []
    else:
        check_refs(sources)
    exes = json.loads((build / "executables.json").read_text())
    check_refs(exes.values())
    fields = dict(RAYON_NUM_THREADS="4", STREHL_TEST_TMP=str(CAMPAIGN / "test-tmp"))
    bounds = dict(wall_seconds=120, cpu_seconds=480, committed_bytes=4 << 30, log_bytes=32 << 20)
    reports = []
    if args.stage == "core-tests":
        command = [exes["strehl_core"]["path"], "--nocapture", "--test-threads=4"]
    elif args.stage == "controls-core":
        command = [exes["strehl_core"]["path"], "align::insect_placement_controls::generated_controls",
                   "--ignored", "--exact", "--nocapture", "--test-threads=1"]
        fields["STREHL_INSECT_PLACEMENT_CORE_OUT"] = str(out / "output")
    elif args.stage == "controls":
        command = [exes["strehl_cli"]["path"], "align_cmd::insect_placement_observer::independent_controls::generated_controls",
                   "--ignored", "--exact", "--nocapture", "--test-threads=1"]
        fields["STREHL_INSECT_PLACEMENT_CONTROL_OUT"] = str(out / "output")
    elif args.stage == "observe":
        for stage in ("controls-core", "controls"):
            control = folder(stage, args.controls_iteration)
            control_completion = json.loads((control / "completion.json").read_text())
            check_refs(control_completion["reports"])
            assert control_completion["build_completion"] == ref(build / "completion.json")
        config = out / "config.json"
        save(config, dict(schema=1, out_dir=str(out / "output"),
             expected_test_executable_sha256=exes["strehl_cli"]["sha256"]))
        fields.update(STREHL_INSECT_PLACEMENT_CONFIG=str(config),
                      STREHL_WARPMAP=str(out / "output/alignment.txt"))
        bounds.update(wall_seconds=300, cpu_seconds=1200, committed_bytes=16 << 30)
        command = [exes["strehl_cli"]["path"],
                   "align_cmd::insect_placement_observer::observe_complete_weevil_alignment",
                   "--ignored", "--exact", "--nocapture", "--test-threads=1"]
    else:
        observation = folder("observe", args.observation_iteration)
        observation_completion = json.loads((observation / "completion.json").read_text())
        check_refs(observation_completion["reports"])
        assert observation_completion["build_completion"] == ref(build / "completion.json")
        script = AREA / ("summarize.py" if args.stage == "summary" else "support.py")
        sources += [ref(script)]
        command = [sys.executable, "-B", "-X", "faulthandler", str(script),
                   "--observation", str(observation), "--out", str(out / "output")]
        if args.stage == "support":
            command += ["--summary", str(folder("summary", args.summary_iteration))]
    env, removed = b.clean_environment(fields.items())
    sources += [ref(__file__), ref(PRIOR), ref(prior.HELPER), ref(b.HARNESS)]
    save(out / "source-bindings.json", sources)
    save(out / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
         bounds=bounds, runner=ref(__file__), executable=ref(command[0]),
         source_manifest=ref(build / "rust-sources.json"), photographic_improvement_claimed=False))
    observed_run(command, env, out, bounds)
    log = (out / "process.log").read_text(encoding="utf-8", errors="replace")
    if args.stage in ("controls-core", "controls", "observe"):
        assert "1 passed; 0 failed" in log, "exact commissioned test did not run"
    check_refs(sources)
    if (out / "output").exists():
        reports += [ref(p) for p in sorted((out / "output").rglob("*.json"))]
    if args.stage != "core-tests":
        assert reports, "missing complete child receipt"
    save(out / "completion.json", dict(reports=reports, source_bindings_unchanged=True,
         build_completion=ref(build / "completion.json"), photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
