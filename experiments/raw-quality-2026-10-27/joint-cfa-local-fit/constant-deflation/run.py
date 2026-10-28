"""Root-owned bounded constant-deflation screen; no RAW/full photograph."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import threading
import time

import psutil

AREA = Path(__file__).resolve().parent
PARENT = AREA.parent / "band-residual"
spec = importlib.util.spec_from_file_location("constant_root_helpers", PARENT / "run.py")
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("cost", "full"))
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--cost-iteration", type=int, default=1)
    args = parser.parse_args()
    assert min(args.iteration, args.cost_iteration) > 0
    out = r.CAMPAIGN / f"joint-cfa-deflation-{args.stage}-{args.iteration}"
    out.mkdir(parents=True, exist_ok=False)
    sources = [r.ref(p) for p in sorted(AREA.iterdir()) if p.suffix in (".py", ".md")]
    sources += [r.ref(PARENT / n) for n in ("sensor-operator.py", "controls.py", "fixtures.py", "run.py")]
    sources += [r.ref(r.PRIOR), r.ref(r.prior.HELPER), r.ref(r.b.HARNESS)]
    r.save(out / "sources.json", sources)
    fixtures = r.completed("prepare", 1)
    baseline = r.completed("baseline", 1)
    dependencies = [r.ref(fixtures / "output/fixture-manifest.json"), r.ref(baseline / "output/receipt.json")]
    bounds = dict(wall_seconds=120, cpu_seconds=480, committed_bytes=4 << 30, log_bytes=16 << 20)
    if args.stage == "full":
        cost = r.CAMPAIGN / f"joint-cfa-deflation-cost-{args.cost_iteration}"
        completion = json.loads((cost / "completion.json").read_text(encoding="utf-8"))
        r.check_refs(completion["reports"])
        r.check_refs(json.loads((cost / "sources.json").read_text(encoding="utf-8")))
        decision = json.loads((cost / "cost-decision.json").read_text(encoding="utf-8"))
        assert decision["full_screen_released"], "cost or actual flat quality refused"
        dependencies.append(r.ref(cost / "cost-decision.json"))
        bounds.update(wall_seconds=300, cpu_seconds=1200)
    command = [sys.executable, "-B", "-X", "faulthandler", str(AREA / "controls.py"),
               "--stage", args.stage, "--fixtures", str(fixtures / "output/fixture-manifest.json"),
               "--baseline", str(baseline / "output/receipt.json"), "--expected-operator-sha",
               r.ref(AREA / "sensor-operator.py")["sha256"], "--out", str(out / "output")]
    fields = dict(OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4", MKL_NUM_THREADS="4",
                  NUMEXPR_NUM_THREADS="4", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    env, removed = r.b.clean_environment(fields.items())
    r.save(out / "invocation.json", dict(command=command, environment=fields,
         removed_environment=removed, bounds=bounds, dependencies=dependencies,
         scope="Generated screen only; no photographic improvement or full-image release."))
    rows, stop = [], threading.Event()

    def observe():
        psutil.cpu_percent(None)
        while not stop.is_set():
            rows.append(dict(monotonic_seconds=time.monotonic(), host_cpu_percent=psutil.cpu_percent(None),
                             available_ram_bytes=psutil.virtual_memory().available))
            stop.wait(2)

    observer = threading.Thread(target=observe, daemon=True)
    observer.start()
    try:
        process = r.b.run(command, env, r.ROOT, out / "process.log",
                          api=r.b.load_job_api(r.b.binding(r.b.HARNESS)), **bounds)
    finally:
        stop.set()
        observer.join(timeout=3)
        r.save(out / "host-observation.json", dict(rows=rows, scope="Whole-host load, not exclusive benchmark."))
    r.save(out / "process.json", process)
    print(json.dumps({k: process[k] for k in ("exit_code", "error", "wall_seconds", "job_memory")}))
    print((out / "process.log").read_text(encoding="utf-8", errors="replace")[-12000:])
    assert process["exit_code"] == 0 and process["error"] is None
    assert process["terminal_job_accounting"] and not process["cleanup_errors"]
    r.check_refs(sources + dependencies)
    screen = json.loads((out / "output/screen.json").read_text(encoding="utf-8"))
    assert screen["admission"] is False and screen["photographic_admission"] is False
    if args.stage == "full":
        assert screen["status"] == "COMPLETE_CONSTANT_DEFLATION_GENERATED_DIAGNOSTIC"
        assert screen["all_cases_completed"] and len(screen["cases"]) == 14
        assert sum(row["mode"] == "candidate" for row in screen["cases"]) == 10
        assert screen["bound_sources_unchanged"]
    reports = sorted((out / "output").rglob("*.json"))
    if args.stage == "cost":
        assert screen["status"] in ("COMPLETE_CONSTANT_DEFLATION_COST_DIAGNOSTIC", "MECHANICAL_REFUSAL")
        projected = None
        if len(screen["cases"]) == 1:
            row = screen["cases"][0]
            assert row["case_id"] == "flat-neutral" and row["mode"] == "candidate"
            overhead = max(0, process["wall_seconds"] - row["total_observed_seconds"])
            projected = overhead + 1.25*14*(row["prepare_seconds"]
                + row["fit_and_delivery_seconds"]*64/max(1, row["iterations"]))
        r.save(out / "cost-decision.json", dict(projected_seconds=projected, limit_seconds=300,
             formula="observed non-fit overhead + 1.25*14*(prepare + fit_and_delivery*64/max(iterations,1))",
             full_screen_released=bool(screen["all_cases_completed"] and screen["mechanical_pass"]
                 and screen["model_adequacy_pass"] and screen["quality_pass"]
                 and projected is not None and projected <= 300),
             numerical_status_separate=screen["numerical_pass"], photographic_admission=False))
        reports.append(out / "cost-decision.json")
    r.save(out / "completion.json", dict(reports=[r.ref(p) for p in reports],
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
