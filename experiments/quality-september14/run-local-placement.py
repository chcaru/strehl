"""Two explicit phases for the frozen actual cropped-consumer diagnostic."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("placement_run_bounds", ROOT / "experiments/m193c-output-grid/bounded-process.py")
bounds = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bounds
spec.loader.exec_module(bounds)


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["preflight", "actual"])
    args = parser.parse_args()
    build = HERE / "local-placement-build-2"
    invocation = json.loads((build / "invocation.json").read_text())
    for row in invocation["source_files"]:
        assert dict(path=row["path"], **bounds.binding(Path(row["path"]))) == row
    executable = json.loads((build / "executable.json").read_text())
    exe = Path(executable["path"])
    assert dict(path=str(exe), **bounds.binding(exe)) == executable
    config = HERE / "local-placement-consumer-inputs-1/config.json"
    if args.phase == "actual":
        preflight = json.loads((HERE / "local-placement-preflight-1-process.json").read_text())
        assert preflight["exit_code"] == 0 and preflight["error"] is None
        assert "LOCAL_PLACEMENT_PREFLIGHT" in (HERE / "local-placement-preflight-1.log").read_text()
        assert not (HERE / "local-placement-consumer-1").exists()
    name = "local_placement_configuration_preflight" if args.phase == "preflight" else "local_placement_actual_consumer"
    command = [str(exe), "merge_cmd::local_placement_consumer_tests::" + name,
               "--exact", "--ignored", "--nocapture", "--test-threads=1"]
    fields = dict(RAYON_NUM_THREADS="8", STREHL_PYRAMID_WORKERS="8", STREHL_FULLRES_GATHER="1",
        STREHL_DIRECT_PLANES="rounded", STREHL_PROBE_GATHER="green", STREHL_WARP_WRITEBACK="parallel",
        STREHL_GPU_GATHER="on", STREHL_GPU_SCHEDULE="device", STREHL_GPU_GATHER_LOG="off", STREHL_DEFECT="off",
        STREHL_LOCAL_PLACEMENT_CONFIG=str(config))
    env, removed = bounds.clean_environment(fields.items())
    stem = "local-placement-" + args.phase + "-1"
    save(HERE / (stem + "-invocation.json"), dict(command=command, environment=fields,
        removed_environment=removed, executable=executable, runner=bounds.binding(Path(__file__)),
        config=bounds.binding(config), manifest=bounds.binding(config.with_name("manifest.json")),
        scope="Eight saved CFA patches. Original file metadata may be queried for current CA identity; no original pixel decode."))
    api = bounds.load_job_api(bounds.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    result = bounds.run(command, env, ROOT, HERE / (stem + ".log"), api=api,
        wall_seconds=180 if args.phase == "actual" else 30,
        cpu_seconds=800 if args.phase == "actual" else 60,
        log_bytes=4 << 20, committed_bytes=8 << 30)
    save(HERE / (stem + "-process.json"), result)
    print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_accounting")}), flush=True)
    assert result["exit_code"] == 0 and result["error"] is None and result["terminal_job_accounting"]
    assert not result["cleanup_errors"]
    if args.phase == "actual":
        import numpy as np
        import tifffile
        from PIL import Image
        out = HERE / "local-placement-consumer-1"
        receipt = json.loads((out / "receipt.json").read_text())
        assert receipt["filler_collapsed_and_output_exact"]
        assert receipt["actual_laplacian_bands"] == 4 and receipt["viewing_trim"] == 32
        for arm in ("original-black", "corrected-black"):
            image = tifffile.imread(out / (arm + "-product.tiff"))
            assert image.shape == (392, 392, 3) and image.dtype == np.uint16
            Image.fromarray((image[32:-32, 32:-32].astype(np.uint32) * 255 // 65535).astype(np.uint8)).save(
                out / (arm + "-native.png"))


if __name__ == "__main__":
    main()
