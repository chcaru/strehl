"""Frozen three-arm native repeat experiment; no capture writes or fitted display."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "outputs/multi-stack/completion/noise-bee-repeat-01"
DEST = ROOT / "outputs/multi-stack/overflow/repeat-proposals-17"
PRODUCT = ROOT / "outputs/multi-stack/completion/product-17"
ARMS = {"legacy": [], "proposals": ["--uncertainty-repeat-proposals"],
        "singletons": ["--no-repeat-grouping"]}
spec = importlib.util.spec_from_file_location("fixed_display", Path(__file__).with_name("noise-bee-repeat-inspect.py"))
display_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(display_module)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def freeze():
    DEST.mkdir(parents=True, exist_ok=False)
    inputs = [BASE / "inputs/manifest.json", BASE / "inputs/protocol.json",
              BASE / "alignment.json", BASE / "equal/source-identities.json",
              BASE / "equal/calibration.json", PRODUCT / "build.json",
              PRODUCT / "strehl.exe", Path(__file__), Path(display_module.__file__)]
    recipe = json.loads((BASE.parent / "noise-bee-repeat-equal-run-01/receipt.json").read_text())
    commands = {}
    for arm, flags in ARMS.items():
        command = recipe["command"].copy()
        command[0] = str(PRODUCT / "strehl.exe")
        command[command.index("--out-dir") + 1] = str(DEST / arm)
        commands[arm] = command + flags
    plan = {"schema": "strehl.repeat-proposal-full.v1", "arms": commands,
            "physical_output_root": str(DEST.resolve()),
            "bindings": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
            "environment": recipe["environment"],
            "comparison": "Complete native photographs and linear masters; nine predeclared 384px witnesses; fixed original display. No new original or ROI selection.",
            "limitations": "Geometric proposals are not focus/PSF equivalence or SR admission. The simple native session currently exports linear RGB and contribution maps, not a separate CFA sensor master. This three-arm comparison does not claim measured original-sensor noise or physical PSF equality."}
    (DEST / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def render():
    plan = freeze()
    for arm, command in plan["arms"].items():
        runner = [sys.executable, "-X", "faulthandler",
                  "experiments/multi-stack-2026-10-28/run-command.py",
                  "--receipt", str(DEST / (arm + "-run")), "--cwd", str(ROOT)]
        for key, value in plan["environment"].items():
            runner += ["--env", key + "=" + value]
        subprocess.run(runner + ["--"] + command, cwd=ROOT, check=True)


def inspect():
    plan = json.loads((DEST / "plan.json").read_text())
    for path, expected in plan["bindings"].items():
        assert sha(ROOT / path) == expected, path
    protocol = json.loads((BASE / "inputs/protocol.json").read_text())
    full = json.loads((BASE / "alignment.json").read_text())["report"]["geometry_plane_pixels"]
    old_report = json.loads((BASE / "equal/render-report.json").read_text())
    old = tifffile.memmap(BASE / "equal/master.tiff", mode="r")
    receipts = {}
    for arm in ARMS:
        source = DEST / arm
        out = DEST / "inspection" / arm
        out.mkdir(parents=True, exist_ok=False)
        report = json.loads((source / "render-report.json").read_text())
        assert report["canvas"] == old_report["canvas"]
        assert report["invalid_output_pixels"] == 0
        assert report["sources"] == old_report["sources"] == 32
        master = tifffile.memmap(source / "master.tiff", mode="r")
        assert master.shape == old.shape and master.dtype == old.dtype == np.float32
        pixel_hash = hashlib.sha256()
        equal = True
        delta_square = delta_abs = maximum = 0.0
        for y in range(0, master.shape[0], 128):
            block = np.asarray(master[y:y+128])
            assert np.isfinite(block).all()
            pixel_hash.update(block.tobytes())
            equal &= np.array_equal(block.view(np.uint8), old[y:y+128].view(np.uint8))
            delta = block.astype(np.float64) - old[y:y+128]
            delta_square += float(np.sum(delta * delta))
            delta_abs += float(np.sum(np.abs(delta)))
            maximum = max(maximum, float(np.max(np.abs(delta))))
        if arm == "legacy":
            assert equal, "Default session pixels changed from product16"
        full_display = display_module.display(master)
        Image.fromarray(full_display).save(out / "full.png")
        overview = Image.fromarray(full_display[::4, ::4])
        overview.thumbnail((1600, 1200), Image.Resampling.LANCZOS)
        overview.save(out / "overview.png")
        canvas = report["canvas"]
        witnesses = []
        for witness in protocol["witnesses"]:
            x, y = [int(np.floor(f * 2 * n - 192))
                    for f, n in zip(witness["active_fraction_center"], full)]
            x, y = max(0, min(2*full[0]-384, x)), max(0, min(2*full[1]-384, y))
            xx, yy = x - 2*canvas[0], y - 2*canvas[1]
            crop = master[yy:yy+384, xx:xx+384]
            assert crop.shape == (384, 384, 3)
            path = out / (witness["id"] + ".png")
            Image.fromarray(full_display[yy:yy+384, xx:xx+384]).save(path)
            witnesses.append({"id": witness["id"], "origin_full_sensor": [x, y],
                              "origin_output_sensor": [xx, yy], "dimensions": [384, 384],
                              "display_sha256": sha(path),
                              "linear_float32_sha256": hashlib.sha256(crop.tobytes()).hexdigest()})
        receipt = {"arm": arm, "dimensions": [master.shape[1], master.shape[0]],
                   "master_file_sha256": sha(source / "master.tiff"),
                   "master_pixel_sha256": pixel_hash.hexdigest(), "finite": True,
                   "bit_equal_product16_default": bool(equal),
                   "difference_from_default_not_quality": {
                       "mean_absolute": delta_abs / master.size,
                       "rms": (delta_square / master.size)**0.5, "maximum": maximum},
                   "proposed_groups": report["proposed_groups"],
                   "diagnostics": report["diagnostics"], "witnesses": witnesses,
                   "display": {"black": display_module.BLACK, "white": display_module.WHITE,
                               "transfer": "sRGB", "full": "native size; no resampling",
                               "overview": "orientation only; 1:4 and fit"},
                   "display_files": {p.name: sha(p) for p in sorted(out.glob("*.png"))},
                   "render_report_sha256": sha(source / "render-report.json"),
                   "run_receipt_sha256": sha(DEST / (arm + "-run") / "receipt.json")}
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        receipts[arm] = {"groups": len(report["proposed_groups"]),
                         "pairs": sum(len(g) == 2 for g in report["proposed_groups"]),
                         "bit_equal_product16_default": bool(equal),
                         "master_pixel_sha256": pixel_hash.hexdigest()}
    (DEST / "inspection-summary.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["render", "inspect"])
    args = parser.parse_args()
    {"render": render, "inspect": inspect}[args.action]()
