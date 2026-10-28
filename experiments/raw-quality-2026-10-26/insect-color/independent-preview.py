"""Bounded display conversion of complete generated camera-RGB arrays; no RAW IO."""
from pathlib import Path
import hashlib
import json
import time

import numpy as np
from PIL import Image, ImageCms

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / "outputs/raw-quality-2026-10-26/insect-color-observed-screen-1"
OUT = HERE / "independent-previews"
OUT.mkdir(exist_ok=False)
START = time.monotonic()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


screen_path = RUN / "output/screen.json"
screen = json.loads(screen_path.read_text())
completion = json.loads((RUN / "completion.json").read_text())
invocation = json.loads((RUN / "invocation.json").read_text())
assert sha(screen_path) == completion["report"]["sha256"]
assert sha(Path(invocation["executable"]["path"])) == invocation["executable"]["sha256"]
icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
rows = []


def convert(row, prefix):
    assert time.monotonic() - START < 9.0, "bounded display job exceeded budget"
    path = Path(row["camera_rgb_f32"])
    assert sha(path) == row["sha256"]
    a = np.fromfile(path, dtype="<f4").reshape(250, 290, 3)
    assert np.isfinite(a).all()
    # Fixed unit gain and sRGB OETF. Camera RGB is not a measured display
    # colour space; this is a common structural preview, not colourimetry.
    linear = np.clip(a, 0, 1)
    display = np.where(linear <= 0.0031308, 12.92 * linear,
                       1.055 * np.power(linear, 1 / 2.4) - 0.055)
    target = OUT / f"{prefix}-{row.get('arm', 'focused-source-2')}.png"
    Image.fromarray(np.round(display * 255).astype(np.uint8)).save(target, icc_profile=icc)
    rows.append({"source": str(path), "source_sha256": row["sha256"],
                 "preview": str(target), "preview_sha256": sha(target),
                 "width": 290, "height": 250, "resized": False,
                 "clipped_components": int(((a < 0) | (a > 1)).sum())})


for case in screen["cases"]:
    for row in case["outputs"]:
        convert(row, f"{case['scene']}-iso{case['iso']:g}")
companion = screen["independent_noiseless_companion"]
for row in companion["outputs"]:
    convert(row, "noiseless-cofocused")
convert(companion["focused_source"], "noiseless-cofocused")
receipt = {"screen_sha256": sha(screen_path), "command": "python -B experiments/raw-quality-2026-10-26/insect-color/independent-preview.py",
           "script_sha256": sha(Path(__file__)), "rows": rows,
           "display": "unit gain; clip [0,1]; sRGB OETF; rounded RGB8; same ICC; no resize",
           "scope": "complete generated camera-RGB structural previews; not calibrated photograph colours",
           "elapsed_seconds": time.monotonic() - START}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"outputs": len(rows), "seconds": receipt["elapsed_seconds"],
                  "receipt": str(OUT / 'receipt.json')}))
