"""Bounded root observations of the already rejected finite flat; no refit."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import threading
import time

import psutil

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("band_root_runner", AREA / "run.py")
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=("saved-review", "residual-budget"))
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    script = AREA / ("review-cost.py" if args.name == "saved-review" else "residual-budget.py")
    assert args.iteration > 0 and script.is_file()
    out = r.folder(args.name, args.iteration)
    out.mkdir(parents=True, exist_ok=False)
    arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    assert "--out" not in arguments
    sources = [r.ref(p) for p in sorted({script, Path(__file__).resolve(),
        AREA / "run.py", AREA / "controls.py", AREA / "fixtures.py", AREA / "sensor-operator.py"})]
    sources += [r.ref(r.PRIOR), r.ref(r.prior.HELPER), r.ref(r.b.HARNESS)]
    r.save(out / "sources.json", sources)
    fields = dict(OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4", MKL_NUM_THREADS="4",
                  NUMEXPR_NUM_THREADS="4", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    env, removed = r.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=120, cpu_seconds=480, committed_bytes=4 << 30, log_bytes=16 << 20)
    command = [sys.executable, "-B", "-X", "faulthandler", str(script), *arguments,
               "--out", str(out / "output")]
    r.save(out / "invocation.json", dict(command=command, environment=fields,
         removed_environment=removed, bounds=bounds, source_bindings=sources,
         scope="No-refit saved-output observation; no photograph or quality admission."))
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
        process = r.b.run(command, env, r.ROOT, out / "process.log",
                          api=r.b.load_job_api(r.b.binding(r.b.HARNESS)), **bounds)
    finally:
        stop.set()
        observer.join(timeout=3)
        r.save(out / "host-observation.json", dict(rows=observations,
             scope="Whole-host load, not exclusive timing benchmark."))
    r.save(out / "process.json", process)
    print(json.dumps({k: process[k] for k in ("exit_code", "error", "wall_seconds", "job_memory")}))
    print((out / "process.log").read_text(encoding="utf-8", errors="replace")[-12000:])
    assert process["exit_code"] == 0 and process["error"] is None
    assert process["terminal_job_accounting"] and not process["cleanup_errors"]
    r.check_refs(sources)
    reports = sorted((out / "output").rglob("*.json"))
    assert reports
    r.save(out / "completion.json", dict(reports=[r.ref(p) for p in reports],
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
