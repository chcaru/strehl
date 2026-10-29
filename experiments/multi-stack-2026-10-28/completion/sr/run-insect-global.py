"""Execute the bounded, preselected insect replay and exact policy controls."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import tifffile

p = argparse.ArgumentParser()
p.add_argument("--binary", type=Path, required=True)
p.add_argument("--tag", required=True)
p.add_argument("--patch-diagnostics", action="store_true")
a = p.parse_args()
root = Path(__file__).resolve().parents[4]
out = root / "outputs/multi-stack/completion"
previous = out / "sr-insect-global-16"
plan = Path(__file__).with_name("insect-global-plan.md")
records = []
arms = [
    ("legacy", 0, [1970, 2090], list(range(107, 114)) + list(range(397, 404)), [106, 114, 396, 404], False),
    ("rgb-roi0", 0, [1970, 2090], list(range(107, 114)) + list(range(397, 404)), [106, 114, 396, 404], True),
    ("rgb-roi1", 1, [2350, 1330], list(range(100, 107)) + list(range(390, 397)), [99, 107, 389, 397], True),
]


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


for name, roi, origin, targets, guides, rgb in arms:
    destination = out / f"sr-insect-global-{a.tag}-{name}"
    receipt = out / f"sr-insect-global-run-{a.tag}-{name}"
    command = [str(a.binary), "--render-dir", "outputs/multi-stack/insect-repeat-7",
               "--cache", "outputs/multi-stack/full-source-cache", "--out", str(destination),
               "--workers", "4", "--x", str(origin[0]), "--y", str(origin[1]), "--size", "192",
               "--assumed-registration-sigma-sensor", "0.10", "--historical-cache",
               "--focus-census", "outputs/multi-stack/completion/sr-census-01",
               "--focus-seal", "experiments/multi-stack-2026-10-28/completion/sr/focus-census-01-seal.json",
               "--focus-roi", str(roi), "--targets", ",".join(map(str, targets)),
               "--guides", ",".join(map(str, guides)), "--measure-registration", "--require-registration",
               "--registration-geometry-sigma-quad", "1.2", "--registration-tile-quad", "46",
               "--registration-grid-axis", "3", "--refine-registration", "--heldout-prediction",
               "--matched-comparator"]
    if rgb:
        command.append("--coherent-color-motion")
    if a.patch_diagnostics:
        command.append("--registration-patch-diagnostics")
    subprocess.run([sys.executable, "experiments/multi-stack-2026-10-28/run-command.py",
                    "--receipt", str(receipt), "--cwd", str(root), "--env", "RAYON_NUM_THREADS=4",
                    "--", *command], cwd=root, check=True)
    report = json.loads((destination / "report.json").read_text())
    assert report["raw_decodes"] == 0
    assert report["coherent_color_motion"] == rgb
    for suffix in ["native.tiff", "candidate.tiff", "matched-cfa-mhc.tiff"]:
        pixels = tifffile.imread(destination / suffix)
        assert np.isfinite(pixels).all(), suffix
    mask = np.fromfile(destination / "coherent-rgb-mask.u8", np.uint8).reshape(192, 192).astype(bool)
    native = tifffile.imread(destination / "native.tiff").view(np.uint32)
    candidate = tifffile.imread(destination / "candidate.tiff").view(np.uint32)
    assert np.array_equal(native[~mask], candidate[~mask]), "fallback changed"
    record = {"arm": name, "report_sha256": sha(destination / "report.json"),
              "receipt_sha256": sha(receipt / "receipt.json"),
              "reconstructed": report["coherent_rgb_reconstructed_pixels"],
              "raw_decodes": 0, "finite": True, "unsupported_native_exact": True}
    if name == "legacy":
        compared = []
        for path in sorted(previous.iterdir()):
            if path.suffix in {".u8", ".f32"}:
                assert path.read_bytes() == (destination / path.name).read_bytes(), path.name
                compared.append(path.name)
            elif path.suffix == ".tiff":
                before = tifffile.imread(path)
                after = tifffile.imread(destination / path.name)
                assert before.dtype == after.dtype and before.shape == after.shape
                assert before.tobytes() == after.tobytes(), path.name
                compared.append(path.name)
        assert len(compared) >= 20, compared
        record["legacy_exact_artifacts"] = compared
    if a.patch_diagnostics:
        reference = out / f"sr-insect-global-16b-{name}"
        old = json.loads((reference / "report.json").read_text())["local_registration"]["measurement"]
        new = report["local_registration"]["measurement"]
        excluded = {"seconds", "source_sha256", "measurement_sha256", "patch_diagnostics"}
        assert {k: v for k, v in old.items() if k not in excluded} == {
            k: v for k, v in new.items() if k not in excluded
        }, "diagnostics perturbed registration"
        for path in reference.iterdir():
            if path.suffix in {".u8", ".f32"}:
                assert path.read_bytes() == (destination / path.name).read_bytes(), path.name
            elif path.suffix == ".tiff":
                assert tifffile.imread(path).tobytes() == tifffile.imread(destination / path.name).tobytes(), path.name
        pairs = new["patch_diagnostics"]["pairs"]
        assert len(pairs) == 75 and all(len(p["tiles"]) == 9 for p in pairs)
        record["diagnostic_nonperturbation"] = True
        record["diagnostic_predefined_tiles"] = sum(len(p["tiles"]) for p in pairs)
    records.append(record)

result = {"command": sys.argv, "plan_sha256": sha(plan), "binary_sha256": sha(a.binary), "arms": records}
with (out / f"sr-insect-global-summary-{a.tag}.json").open("x") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
print(json.dumps(result, indent=2))
