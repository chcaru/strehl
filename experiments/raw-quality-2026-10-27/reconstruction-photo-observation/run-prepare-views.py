"""Root-only bounded export of already completed diagnostic TIFFs; no RAW/model work."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("reconstruction_photo_view_bounds", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)


def ref(path):
    return dict(path=str(Path(path).resolve()), **b.binding(path))


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.input.resolve(), args.out.resolve()
    job = out.with_name(out.name + "-job")
    assert source.is_dir() and source.is_relative_to(ROOT / "outputs")
    assert out.is_relative_to(ROOT / "outputs") and not out.exists() and not job.exists()
    assert not out.is_relative_to(source) and not job.is_relative_to(source)
    job.mkdir()
    exporter = HERE / "prepare-views.py"
    sources = [ref(path) for path in [Path(__file__), exporter, HERE / "independent-plan.md", HERE / "brief.md", HELPER,
                                    ROOT / "experiments/m12-scorecard/m12-harness.py", source / "receipt.json",
                                    ROOT / "experiments/raw-quality-2026-10-26/flat-baseline/frozen-witnesses.json"]]
    command = [sys.executable, "-B", "-X", "faulthandler", str(exporter), "--input", str(source), "--out", str(out)]
    env, removed = b.clean_environment((("OMP_NUM_THREADS", "1"), ("OPENBLAS_NUM_THREADS", "1"), ("MKL_NUM_THREADS", "1")))
    bounds = dict(wall_seconds=180, cpu_seconds=180, log_bytes=4 << 20, committed_bytes=4 << 30)
    save(job / "invocation.json", dict(command=command, bounds=bounds, sources=sources, removed_environment=removed,
         scope="Root released cached TIFF export only; input master/sidecar hashes additionally checked by exporter."))
    api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    result = b.run(command, env, ROOT, job / "process.log", api=api, **bounds)
    save(job / "process.json", result)
    assert result["exit_code"] == 0 and result["error"] is None
    assert result["terminal_job_accounting"] and not result["cleanup_errors"]
    assert all(ref(row["path"]) == row for row in sources), "export source changed"
    receipt = json.loads((out / "display-receipt.json").read_text())
    assert receipt["status"] == "COMPLETE_DIAGNOSTIC_IMAGES_READY_NO_VERDICT"
    assert receipt["inputs_unchanged"] and receipt["admission"] is False
    save(job / "completion.json", dict(display_receipt=ref(out / "display-receipt.json"), sources_unchanged=True,
         admission=False, photographic_improvement_claimed=False))
    print(json.dumps({k: result[k] for k in ("exit_code", "wall_seconds", "job_memory")}))


if __name__ == "__main__":
    main()
