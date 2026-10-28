"""Root-only known-training-blur diagnostic; no photographic release."""
from pathlib import Path
import argparse
import importlib.util
import json
import platform
import subprocess
import sys
import threading
import time

import psutil

ROOT = Path(__file__).resolve().parents[4]
AREA = Path(__file__).resolve().parent
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
HARNESS = ROOT / "experiments/m12-scorecard/m12-harness.py"
spec = importlib.util.spec_from_file_location("raw_blur_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)


def ref(path):
    path = Path(path).resolve()
    return dict(path=str(path), **b.binding(path))


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iteration", type=int, default=1)
    args = parser.parse_args()
    assert args.iteration > 0
    script = AREA / "controls.py"
    assert script.is_file() and (AREA / "model-oracle.py").is_file()
    sources = {HELPER, HARNESS, Path(sys.executable), *AREA.glob("*.py"), *AREA.glob("*.md"),
               *AREA.parent.glob("*.py"), *AREA.parent.glob("*.md")}
    sources.update(AREA.glob("*.json"))
    sources.update(AREA.glob("*.diff"))
    sources.update((AREA.parent / "finite-diagnostic").glob("*.py"))
    sources.update((AREA.parent / "counted-likelihood").glob("*.py"))
    sources.add(ROOT / "outputs/raw-quality-2026-10-27/raw-blur-compatible-1/output/observations.json")
    sources.add(ROOT / "outputs/raw-quality-2026-10-27/raw-blur-counted-1/output/observations.json")
    identity_path = AREA / "input-identities.json"
    sources.add(identity_path)
    for row in json.loads(identity_path.read_text(encoding="utf-8"))["originals"]:
        original = ROOT / row["path"]
        assert ref(original)["sha256"] == row["sha256"]
        sources.add(original)
    preceding = ROOT / "outputs/raw-quality-2026-10-27/raw-blur-controls-2"
    prior_completion = json.loads((preceding / "completion.json").read_text(encoding="utf-8"))
    assert prior_completion["sources_unchanged"] is True
    assert prior_completion["photographic_improvement_claimed"] is False
    assert prior_completion["scientific"] == dict(status="NUMERICAL_REFUSAL", all_cases_completed=False, all_pass=False)
    assert all(ref(row["path"]) == row for row in prior_completion["reports"])
    prior_preservation = json.loads((preceding / "preservation.json").read_text(encoding="utf-8"))
    assert prior_preservation["sources_unchanged"] is True
    sources.update((preceding / name for name in ("completion.json", "sources.json", "preservation.json",
        "output/observations.json", "output/commission.json", "output/flat-neutral/decision.json",
        "output/flat-neutral/fit/receipt.json")))
    # Retained operator sources may be imported by the model. Bind their code,
    # never read photographic arrays or original RAWs in this generated job.
    for relative in ("experiments/layered-raw-inverse", "experiments/quality-september14"):
        sources.update((ROOT / relative).glob("*.py"))
    before = [ref(path) for path in sorted(sources)]
    out = ROOT / f"outputs/raw-quality-2026-10-27/raw-blur-known-variance-{args.iteration}"
    assert not out.exists(), "fresh immutable run directory required"
    out.mkdir(parents=True)
    save(out / "sources.json", before)
    fields = dict(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="4",
                  MKL_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4", NVIDIA_TF32_OVERRIDE="0")
    env, removed = b.clean_environment(fields.items())
    command = [sys.executable, "-B", "-X", "faulthandler", str(script), "--out", str(out / "output")]
    limits = dict(wall_seconds=120, cpu_seconds=480, committed_bytes=4 << 30, log_bytes=32 << 20)
    save(out / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
         interpreter=ref(sys.executable), python=platform.python_version(), runner=ref(__file__),
         helper=ref(HELPER), limits=limits, sources=ref(out / "sources.json"),
         scope="Generated operator/refusal test only; successful execution does not establish native photographic quality."))
    observations = []
    stop = threading.Event()

    def observe():
        psutil.cpu_percent(None)
        while not stop.is_set():
            row = dict(monotonic_seconds=time.monotonic(), host_cpu_percent=psutil.cpu_percent(None),
                       available_ram_bytes=psutil.virtual_memory().available)
            try:
                gpu = subprocess.run(["nvidia-smi", "--query-gpu=timestamp,index,name,utilization.gpu,memory.used,memory.total",
                                      "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=False)
                row.update(gpu_exit=gpu.returncode, gpu=gpu.stdout.strip())
            except Exception as error:
                row["gpu_error"] = str(error)
            observations.append(row)
            stop.wait(3)

    thread = threading.Thread(target=observe, daemon=True)
    thread.start()
    try:
        result = b.run(command, env, ROOT, out / "process.log", api=b.load_job_api(b.binding(HARNESS)), **limits)
    finally:
        stop.set()
        thread.join(timeout=6)
        save(out / "host-observation.json", dict(rows=observations, logical_cpus=psutil.cpu_count(),
             physical_cpus=psutil.cpu_count(logical=False), scope="Whole-host/device observations, not process-exclusive GPU or a clean performance benchmark."))
    save(out / "process.json", result)
    print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_memory")}))
    print((out / "process.log").read_text(encoding="utf-8", errors="replace")[-10000:])
    unchanged = all(ref(row["path"]) == row for row in before)
    save(out / "preservation.json", dict(sources_unchanged=unchanged))
    assert unchanged and result["terminal_job_accounting"] and not result["cleanup_errors"]
    assert result["exit_code"] == 0 and result["error"] is None
    reports = sorted((out / "output").rglob("*.json"))
    assert reports, "no generated test report"
    observation = json.loads((out / "output" / "observations.json").read_text(encoding="utf-8"))
    assert observation["photographic_admission"] is False and observation["full_design_qualified"] is False
    scientific = {key: observation[key] for key in ("status", "all_cases_completed", "all_pass")}
    save(out / "completion.json", dict(reports=[ref(path) for path in reports], sources_unchanged=True,
         scientific=scientific,
         photographic_improvement_claimed=False, interpretation="Root and independent reviewer must inspect scientific status and complete generated fields."))


if __name__ == "__main__":
    main()
