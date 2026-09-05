from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "experiments" / "m12-scorecard" / "m12-harness.py"
STACKS = {
    "bee-1-cpl": Path(r"D:\personal\macro\bee-1-cpl"),
    "coffee-bean": Path(r"D:\personal\macro\coffee-bean"),
}


def load_harness():
    spec = importlib.util.spec_from_file_location("m139_m12_harness", HARNESS)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {HARNESS}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_id() -> str:
    head = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    diff = subprocess.check_output(
        ["git", "-C", str(ROOT), "diff", "--binary", "--", "Cargo.lock", "crates"]
    )
    return f"{head}+worktree-{hashlib.sha256(diff).hexdigest()[:12]}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--stack", choices=sorted(STACKS), required=True)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--kind", choices=("warmup", "measured"), default="measured")
    args = parser.parse_args()

    harness = load_harness()
    output_root = args.output_root.resolve()
    name = f"{args.kind}-n{args.limit}-w{args.workers}"
    destination = output_root / "runs" / f"{name}.tiff"
    record_path = output_root / "records" / f"{name}.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    measured_source = source_id()
    record = harness.run_once(
        exe=args.exe.resolve(),
        stack=STACKS[args.stack],
        limit=args.limit,
        workers=args.workers,
        destination=destination,
        cache=output_root / "cache" / f"n{args.limit}",
        temp=output_root / "temp" / name,
        flags=["--linear-srgb", "--demosaic"],
        sidecar=None,
        align_off=False,
        fixed_env={},
        required_log_substrings=[
            "strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)",
            "noise gate      : 2.00 x",
            "not applied     : photometric gain, clip census, outlier rejection, halo correction, through-focus",
            "alignment       : ON (",
            "16-bit RGB, linear sRGB",
            "Full sensor resolution",
        ],
        kind=args.kind,
        repetition=None,
        sweep=None,
        measured_commit=measured_source,
    )
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    memory = record["memory"]
    summary = {
        "valid": record["valid"],
        "limit": args.limit,
        "workers": args.workers,
        "peak_process_tree_private_committed_bytes": memory[
            "peak_process_tree_private_committed_bytes"
        ],
        "peak_job_memory_used_bytes": memory["kernel_job_peak_memory"][
            "peak_job_memory_used_bytes"
        ],
        "output_sha256": record.get("output_sha256"),
        "pixel_sha256": record.get("pixel_sha256"),
        "record": str(record_path),
    }
    print(json.dumps(summary, indent=2))
    return 0 if record["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
