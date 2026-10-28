"""Root-only bounded generated original-CFA experiment; no corpus reads."""
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
ROOT = AREA.parents[3]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-27"
PRIOR = ROOT / "experiments/raw-quality-2026-10-27/reconstruction-photo-observation/run.py"
spec = importlib.util.spec_from_file_location("band_residual_runner_helpers", PRIOR)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
b, ref, save = prior.b, prior.ref, prior.save


def check_refs(rows):
    assert all(ref(row["path"]) == row for row in rows), "bound file changed"


def folder(stage, iteration):
    return CAMPAIGN / f"joint-cfa-band-{stage}-{iteration}"


def completed(stage, iteration):
    path = folder(stage, iteration)
    receipt = json.loads((path / "completion.json").read_text(encoding="utf-8"))
    check_refs(receipt["reports"])
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "cost", "build", "baseline", "full"))
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--fixture-iteration", type=int, default=1)
    parser.add_argument("--cost-iteration", type=int, default=1)
    parser.add_argument("--build-iteration", type=int, default=1)
    parser.add_argument("--baseline-iteration", type=int, default=1)
    args = parser.parse_args()
    assert min(args.iteration, args.fixture_iteration, args.cost_iteration,
               args.build_iteration, args.baseline_iteration) > 0
    out = folder(args.stage, args.iteration)
    out.mkdir(parents=True, exist_ok=False)
    sources = [ref(p) for p in sorted(AREA.iterdir()) if p.suffix in (".py", ".rs", ".md")]
    sources += [ref(PRIOR), ref(prior.HELPER), ref(b.HARNESS)]
    save(out / "sources.json", sources)
    if args.stage == "build":
        rust_sources = prior.source_bindings()
        save(out / "rust-sources.json", rust_sources)
        command = ["cargo", "test", "--locked", "--offline", "--release", "-p", "strehl-cli",
                   "--lib", "--no-run", "--features",
                   "native-direct-planes,native-correction-variance,native-gpu-gather",
                   "--jobs", "4", "--message-format=json-render-diagnostics"]
        env, removed = b.clean_environment()
        env.update(CARGO_INCREMENTAL="0", CARGO_BUILD_JOBS="4",
                   STREHL_TEST_TMP=str(CAMPAIGN / "test-tmp"))
        save(out / "invocation.json", dict(command=command, removed_environment=removed,
             build_jobs=4, runner=ref(__file__), scope="Root-supervised compilation only."))
        start = time.monotonic()
        with (out / "artifacts.jsonl").open("xb") as stdout, (out / "build.log").open("xb") as stderr:
            process = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
        save(out / "process.json", dict(exit_code=process.returncode, wall_seconds=time.monotonic()-start))
        log = (out / "build.log").read_text(encoding="utf-8", errors="replace")
        print(log[-12000:])
        assert process.returncode == 0 and "Compiling strehl-cli" in log
        check_refs(sources + rust_sources)
        rows = [json.loads(line) for line in (out / "artifacts.jsonl").read_text(encoding="utf-8").splitlines()
                if line.startswith("{")]
        assert any(r.get("reason") == "build-finished" and r.get("success") for r in rows)
        exes = [r["executable"] for r in rows if r.get("reason") == "compiler-artifact"
                and r.get("executable") and r.get("target", {}).get("name") == "strehl_cli"
                and r.get("profile", {}).get("test")]
        assert len(exes) == 1
        exe = out / "cli-tests.exe"
        shutil.copyfile(exes[0], exe)
        assert b.binding(exe) == b.binding(exes[0])
        save(out / "executable.json", ref(exe))
        save(out / "completion.json", dict(reports=[ref(out / "executable.json"), ref(out / "rust-sources.json")],
             source_bindings_unchanged=True, photographic_improvement_claimed=False))
        print(json.dumps(ref(exe)))
        return

    fields = dict(OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4", MKL_NUM_THREADS="4",
                  NUMEXPR_NUM_THREADS="4", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    bounds = dict(wall_seconds=120, cpu_seconds=480, log_bytes=16 << 20, committed_bytes=4 << 30)
    command = [sys.executable, "-B", "-X", "faulthandler", str(AREA / "controls.py"),
               "--stage", args.stage, "--out", str(out / "output")]
    dependencies = []
    if args.stage != "prepare":
        fixtures = completed("prepare", args.fixture_iteration)
        dependencies += [ref(fixtures / "output/fixture-manifest.json"),
                         ref(fixtures / "output/baseline-manifest.json")]
        command += ["--fixtures", str(fixtures / "output/fixture-manifest.json"),
                    "--expected-operator-sha", ref(AREA / "sensor-operator.py")["sha256"]]
    if args.stage == "baseline":
        build = completed("build", args.build_iteration)
        rust_sources = json.loads((build / "rust-sources.json").read_text(encoding="utf-8"))
        check_refs(rust_sources)
        sources += rust_sources
        exe = build / "cli-tests.exe"
        assert ref(exe) == json.loads((build / "executable.json").read_text(encoding="utf-8"))
        dependencies += [ref(exe)]
        config = out / "config.json"
        manifest = ref(fixtures / "output/baseline-manifest.json")
        save(config, dict(schema=1, fixture_manifest=manifest["path"],
             fixture_manifest_sha256=manifest["sha256"], out_dir=str(out / "output"),
             expected_test_executable_sha256=ref(exe)["sha256"]))
        fields.update(STREHL_JOINT_CFA_BASELINE_CONFIG=str(config), RAYON_NUM_THREADS="4",
                      STREHL_ALIGN="1", STREHL_FULLRES_GATHER="1", STREHL_DIRECT_PLANES="off",
                      STREHL_GPU_GATHER="off", STREHL_FIX_CA="off", STREHL_DEFECT="off",
                      STREHL_TEMPORAL_ENERGY="off", STREHL_SPATIAL_NOISE_FLOOR="off",
                      STREHL_DEMOSAIC="malvar", STREHL_PROBE_GATHER="green",
                      STREHL_WARP_WRITEBACK="parallel")
        command = [str(exe), "merge_cmd::joint_cfa_band_residual_baseline::actual_product_fixture_baseline",
                   "--ignored", "--exact", "--nocapture", "--test-threads=1"]
    if args.stage == "full":
        cost = completed("cost", args.cost_iteration)
        decision = json.loads((cost / "cost-decision.json").read_text(encoding="utf-8"))
        assert decision["full_screen_within_projection"], "fixed full-screen cost bound not met"
        previous_sources = json.loads((cost / "sources.json").read_text(encoding="utf-8"))
        check_refs(previous_sources)
        baseline = completed("baseline", args.baseline_iteration)
        command += ["--baseline", str(baseline / "output/receipt.json")]
        dependencies += [ref(baseline / "output/receipt.json"), ref(cost / "cost-decision.json")]
        bounds.update(wall_seconds=300, cpu_seconds=1200)
    env, removed = b.clean_environment(fields.items())
    save(out / "invocation.json", dict(command=command, environment=fields,
         removed_environment=removed, runner=ref(__file__), dependencies=dependencies, bounds=bounds,
         scope="Generated controls only; execution/finite fields do not demonstrate photographic gain."))
    observations, stop = [], threading.Event()

    def observe():
        psutil.cpu_percent(None)
        while not stop.is_set():
            observations.append(dict(monotonic_seconds=time.monotonic(),
                host_cpu_percent=psutil.cpu_percent(None), available_ram_bytes=psutil.virtual_memory().available))
            stop.wait(2)

    observer = threading.Thread(target=observe, daemon=True)
    observer.start()
    try:
        result = b.run(command, env, ROOT, out / "process.log",
                       api=b.load_job_api(b.binding(b.HARNESS)), **bounds)
    finally:
        stop.set()
        observer.join(timeout=3)
        save(out / "host-observation.json", dict(logical_cpus=psutil.cpu_count(),
             physical_cpus=psutil.cpu_count(logical=False), ram_bytes=psutil.virtual_memory().total,
             scope="Whole-host samples, not exclusive benchmark load.", rows=observations))
    save(out / "process.json", result)
    print(json.dumps({k: result[k] for k in ("exit_code", "error", "wall_seconds", "job_memory")}))
    log = (out / "process.log").read_text(encoding="utf-8", errors="replace")
    print(log[-12000:])
    assert result["exit_code"] == 0 and result["error"] is None
    assert result["terminal_job_accounting"] and not result["cleanup_errors"]
    check_refs(sources + dependencies)
    reports = sorted((out / "output").rglob("*.json"))
    assert reports, "missing child receipts"
    if args.stage == "cost":
        screen = json.loads((out / "output/screen.json").read_text(encoding="utf-8"))
        row = screen["cases"][0] if screen["cases"] else None
        projected = None
        if row is not None:
            # Price all 14 fits at 64 steps, including true residual checks.
            # Fit/delivery includes fixed costs, so scaling all of it is conservative.
            per_fit = row["prepare_seconds"] + row["fit_and_delivery_seconds"] * 64 / max(1, row["iterations"])
            overhead = max(0, result["wall_seconds"] - row["total_observed_seconds"])
            projected = overhead + 1.25 * 14 * per_fit
        save(out / "cost-decision.json", dict(projected_seconds=projected, limit_seconds=300,
             formula="observed non-fit overhead + 1.25*14*(prepare + fit_and_delivery*64/max(iterations,1))",
             qualification="Engineering projection, not measured full-screen time or photographic evidence.",
             full_screen_within_projection=bool(screen["mechanical_pass"] and projected is not None and projected <= 300)))
        reports.append(out / "cost-decision.json")
    if args.stage == "baseline":
        receipt = json.loads((out / "output/receipt.json").read_text(encoding="utf-8"))
        assert receipt["status"] == "COMPLETE_ACTUAL_PRODUCT_BASELINES"
        assert receipt["mechanical_pass"] and receipt["original_inputs_unchanged"]
        assert "1 passed; 0 failed" in log
    save(out / "completion.json", dict(reports=[ref(p) for p in reports],
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
