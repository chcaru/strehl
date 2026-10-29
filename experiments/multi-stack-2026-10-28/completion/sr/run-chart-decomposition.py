"""Frozen same-exposure chart arms; all original photons remain cache-only."""
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
p.add_argument("--stage", choices=["measure", "render"], required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[4]
out = root / "outputs/multi-stack/completion"
arms = [
    ("dot-short", 0, [4105, 3245], list(range(27, 34)), [26, 34], True),
    ("dot-long", 0, [4105, 3245], list(range(90, 97)), [89, 97], True),
    ("dot-union", 0, [4105, 3245], list(range(27, 34))+list(range(90, 97)), [26, 34, 89, 97], True),
    ("bars-short", 1, [5305, 1945], list(range(31, 38)), [30, 38], True),
]
if a.stage == "render":
    arms.append(("legacy-union", 0, [4105, 3245], list(range(27, 34))+list(range(90, 97)), [26, 34, 89, 97], False))


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


records = []
for name, roi, origin, targets, guides, rgb in arms:
    destination = out / f"sr-chart-decomposition-{a.tag}-{a.stage}-{name}"
    receipt = out / f"sr-chart-decomposition-run-{a.tag}-{a.stage}-{name}"
    command = [str(a.binary), "--render-dir", "outputs/multi-stack/completion/hdr-precision-03",
               "--cache", "outputs/multi-stack/completion/hdr-source-cache-current", "--out", str(destination),
               "--workers", "4", "--x", str(origin[0]), "--y", str(origin[1]), "--size", "192",
               "--assumed-registration-sigma-sensor", "0.10",
               "--focus-census", "outputs/multi-stack/completion/sr-chart-census-02",
               "--focus-seal", "experiments/multi-stack-2026-10-28/completion/sr/chart-focus-census-02-seal.json",
               "--focus-roi", str(roi), "--targets", ",".join(map(str, targets)),
               "--guides", ",".join(map(str, guides)), "--measure-registration",
               "--registration-geometry-sigma-quad", "1.2", "--registration-tile-quad", "46",
               "--registration-grid-axis", "3", "--refine-registration", "--registration-patch-diagnostics"]
    if rgb:
        command.append("--coherent-color-motion")
    if a.stage == "measure":
        command += ["--registration-only", "--original-patch-diagnostics"]
    else:
        command += ["--require-registration", "--heldout-prediction", "--matched-comparator"]
    subprocess.run([sys.executable, "experiments/multi-stack-2026-10-28/run-command.py",
                    "--receipt", str(receipt), "--cwd", str(root), "--env", "RAYON_NUM_THREADS=4",
                    "--", *command], cwd=root, check=True)
    report_name = "local-registration-report.json" if a.stage == "measure" else "report.json"
    report = json.loads((destination / report_name).read_text())
    assert report["raw_decodes"] == 0
    record = {"arm": name, "targets": targets, "guides": guides,
              "report": str(destination / report_name), "report_sha256": sha(destination / report_name),
              "receipt_sha256": sha(receipt / "receipt.json"), "raw_decodes": 0}
    if a.stage == "render":
        assert report["coherent_color_motion"] == rgb
        mask = np.fromfile(destination / "coherent-rgb-mask.u8", np.uint8).reshape(192, 192).astype(bool)
        native = tifffile.imread(destination / "native.tiff")
        for name2 in ["candidate.tiff", "matched-cfa-mhc.tiff"]:
            pixels = tifffile.imread(destination / name2)
            assert np.isfinite(pixels).all()
            assert pixels[~mask].tobytes() == native[~mask].tobytes()
        record.update(coherent_pixels=int(mask.sum()), finite=True, exact_fallback=True)
        if name == "legacy-union":
            previous = out / "sr-chart-constant-02"
            compared = []
            for path in previous.iterdir():
                if path.suffix in {".u8", ".f32"}:
                    assert path.read_bytes() == (destination / path.name).read_bytes(), path.name
                    compared.append(path.name)
                elif path.suffix == ".tiff":
                    assert tifffile.imread(path).tobytes() == tifffile.imread(destination / path.name).tobytes(), path.name
                    compared.append(path.name)
            record["legacy_exact_artifacts"] = compared
    records.append(record)
result = {"command": sys.argv, "script_sha256": sha(Path(__file__)),
          "plan_sha256": sha(Path(__file__).with_name("single-exposure-plan.md")),
          "binary_sha256": sha(a.binary), "arms": records,
          "bars_long": "No nomination: zero qualified focus sites in sealed census02; not reconstructed."}
with (out / f"sr-chart-decomposition-{a.tag}-{a.stage}-summary.json").open("x") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
print(json.dumps(result, indent=2))
