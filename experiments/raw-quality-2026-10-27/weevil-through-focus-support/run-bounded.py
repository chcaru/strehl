"""Root-only fixed31-source cached-TIFF export:120s/2GiB, one library thread."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
HARNESS = ROOT / "experiments/m12-scorecard/m12-harness.py"
spec = importlib.util.spec_from_file_location("weevil_through_focus_bound", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def ref(path):
    return dict(path=str(path.resolve()), **b.binding(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, default=1)
    args = parser.parse_args()
    assert args.run_id > 0
    base = ROOT / "outputs/raw-quality-2026-10-27"
    out = base / f"weevil-through-focus-support-{args.run_id}"
    job = base / f"weevil-through-focus-support-job-{args.run_id}"
    assert not out.exists() and not job.exists()
    job.mkdir()
    files = [HERE / "export-source-views.py", Path(__file__), HERE / "brief.md", HELPER, HARNESS, Path(sys.executable)]
    before = [ref(path) for path in files]
    fields = tuple((name, "1") for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "RAYON_NUM_THREADS"))
    env, removed = b.clean_environment(fields)
    command = [sys.executable, "-B", "-X", "faulthandler", str(HERE / "export-source-views.py"), "--out", str(out)]
    bounds = dict(wall_seconds=120, cpu_seconds=120, log_bytes=2 << 20, committed_bytes=2 << 30)
    save(job / "invocation.json", dict(command=command, environment=dict(fields), removed_environment=removed, dependencies=before,
         bounds=bounds, scope="Cached31-source RGB16 views/crops only; no RAW, fit, focus score or quality claim."))
    result = b.run(command, env, ROOT, job / "process.log", api=b.load_job_api(b.binding(HARNESS)), **bounds)
    save(job / "process.json", result)
    print(json.dumps({k: result[k] for k in ("exit_code", "wall_seconds", "job_memory")}))
    assert result["exit_code"] == 0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"]
    assert [ref(path) for path in files] == before
    receipt = json.loads((out / "receipt.json").read_text())
    assert receipt["status"] == "COMPLETE_CACHED_SOURCE_SUPPORT_NO_VERDICT"
    assert receipt["indices"] == list(range(0, 291, 10)) + [298] and len(receipt["records"]) == 31
    assert receipt["witness_names"] == ["upper-leg-hairs", "turquoise-scales", "thorax-texture", "elytron-seam", "blue-joint"]
    assert all(len(row["witnesses"]) == 5 for row in receipt["records"])
    assert receipt["original_raw_reads"] == 0 and receipt["quality_claim"] is False
    assert receipt["selected_source_tiffs_unchanged"] and receipt["dependency_bindings_unchanged"] and receipt["all_complete_views_exported_before_crops"]
    save(job / "completion.json", dict(receipt=ref(out / "receipt.json"), whole_views=ref(out / "whole-views.json"), dependencies_unchanged=True,
         source_count=31, witness_observation_count=155, photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
