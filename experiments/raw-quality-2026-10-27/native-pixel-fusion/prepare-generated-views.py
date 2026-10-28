"""Display only: immutable complete generated RGB arrays, no model or RAW imports."""
from pathlib import Path
import hashlib
import json
import time

import numpy as np
from PIL import Image, ImageCms

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "outputs/raw-quality-2026-10-27/native-pixel-screen-1/output/screen.json"
OUT = ROOT / "outputs/raw-quality-2026-10-27/native-pixel-screen-1-views"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started = time.perf_counter()
    source_hash = digest(SOURCE)
    script_hash = digest(Path(__file__))
    screen = json.loads(SOURCE.read_text())
    assert screen["status"] == "SCREEN_COMPLETE"
    OUT.mkdir(exist_ok=False)
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    rows = []
    for case in screen["cases"]:
        images = [(row.get("arm", row.get("name")), row["master"])
                  for row in case.get("outputs", case.get("arms", []))]
        if "truth" in case:
            images.append(("truth", case["truth"]))
        for arm, item in images:
            source = Path(item["path"])
            before = digest(source)
            assert before == item["sha256"]
            rgb = np.fromfile(source, dtype="<f4").reshape(item["height"], item["width"], 3)
            assert np.isfinite(rgb).all()
            clipped = {"below_zero": int((rgb < 0).sum()), "above_one": int((rgb > 1).sum())}
            linear = np.clip(rgb, 0, 1)
            display = np.where(linear <= 0.0031308, 12.92 * linear,
                               1.055 * np.power(linear, 1 / 2.4) - 0.055)
            pixels = np.floor(display * 255 + 0.5).clip(0, 255).astype(np.uint8)
            dest = OUT / f"{case['name']}-{arm}.png"
            Image.fromarray(pixels).save(dest, icc_profile=icc)
            assert digest(source) == before
            rows.append({"case": case["name"], "arm": arm, "input": str(source),
                         "input_sha256": before, "output": str(dest),
                         "output_sha256": digest(dest), "width": item["width"],
                         "height": item["height"], "display_clipping_samples": clipped})
            del rgb, linear, display, pixels
    assert digest(SOURCE) == source_hash and digest(Path(__file__)) == script_hash
    receipt = {"status": "COMPLETE_GENERATED_VIEWS_READY_NO_VERDICT", "screen_sha256": source_hash,
               "script_sha256": script_hash, "display": "component-wise fixed sRGB transfer, gain1, clip0..1, nearest8-bit; no fitted color matrix or camera-color calibration",
               "resized": False, "source_files_unchanged": True, "raw_reads": 0,
               "seconds": time.perf_counter() - started, "images": rows}
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "images": len(rows), "seconds": receipt["seconds"]}))


if __name__ == "__main__":
    main()
