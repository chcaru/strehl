"""Bounded saved-output presentation; no fitting, RAW decoding or new rendering."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
spec = importlib.util.spec_from_file_location("restoration_view_runner", AREA / "run.py")
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generated", "weevil", "flat"))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    output = args.out.resolve()
    assert output.is_relative_to(ROOT / "outputs") and not output.exists()
    job = output.with_name(output.name + "-job")
    assert not job.exists()
    job.mkdir()
    script = AREA / ("prepare-generated-views.py" if args.mode == "generated" else "prepare-views.py")
    binding = r.ref(script)
    command = [sys.executable, "-B", "-X", "faulthandler", str(script)]
    if args.mode != "generated":
        command += ["--dataset", args.mode]
    command += ["--input", str(args.input.resolve()), "--out", str(output)]
    fields = dict(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    env, removed = r.b.clean_environment(fields.items())
    bounds = dict(wall_seconds=180, cpu_seconds=180, log_bytes=16 << 20, committed_bytes=4 << 30)
    r.save(job / "invocation.json", dict(command=command, script=binding, runner=r.ref(__file__),
           environment=fields, removed_environment=removed, bounds=bounds))
    api = r.b.load_job_api(r.b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    result = r.b.run(command, env, ROOT, job / "process.log", api=api, **bounds)
    r.save(job / "process.json", result)
    print(json.dumps({k: result[k] for k in ("exit_code", "error", "wall_seconds", "job_memory")}))
    print((job / "process.log").read_text(encoding="utf-8", errors="replace")[-4000:])
    assert result["exit_code"] == 0 and result["error"] is None
    assert result["terminal_job_accounting"] and not result["cleanup_errors"]
    assert r.ref(script) == binding
    reports = sorted(output.glob("*.json"))
    assert reports
    r.save(job / "completion.json", dict(script=binding, reports=[r.ref(p) for p in reports],
           photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
