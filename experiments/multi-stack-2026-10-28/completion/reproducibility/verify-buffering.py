"""Compare the complete frozen-build profiles, including every saved ring curve."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
base = root / "outputs/multi-stack/completion"
labels = ["09", "10a", "10b", "09b"]
reports = [json.loads((base / f"repro-profile-{label}/reproducibility.json").read_text()) for label in labels]
excluded = {"algorithm_sha256", "patch_compute_seconds", "stage_seconds"}
clean = lambda report: {key: value for key, value in report.items() if key not in excluded}
assert all(clean(report) == clean(reports[0]) for report in reports)
sha = lambda path: hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
files = [entry["file"] for entry in reports[0]["files"]]
for name in files:
    hashes = [sha(base / f"repro-profile-{label}" / name) for label in labels]
    assert len(set(hashes)) == 1, (name, hashes)
runs = [json.loads((base / f"repro-profile-run-{label}/receipt.json").read_text()) for label in labels]
assert all(run["state"] == "complete" and run["exit_code"] == 0 for run in runs)
result = {
    "status": "VERIFIED exact maps, all tile curves and all nontiming report fields",
    "order": labels,
    "excluded_metadata_fields": sorted(excluded),
    "elapsed_seconds": [run["elapsed_seconds"] for run in runs],
    "stages": [report["stage_seconds"] for report in reports],
    "report_publication_seconds": [json.loads((base / f"repro-profile-{label}/completed.json").read_text()).get("report_publication_seconds") for label in labels],
    "sampled_memory_caveat": "One-second process sampling can miss short-lived peaks in the two-second runs; no memory-reduction claim.",
    "runs": runs,
    "script_sha256": sha(Path(__file__)),
}
with (base / "repro-buffering-comparison.json").open("x", encoding="utf-8") as file:
    json.dump(result, file, indent=2)
    file.write("\n")
print(json.dumps({key: result[key] for key in ["status", "order", "elapsed_seconds", "report_publication_seconds"]}, indent=2))
