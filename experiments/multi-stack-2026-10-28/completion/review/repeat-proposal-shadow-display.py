"""Common baseline-only shadow contrast; appearance diagnostic, not noise metric."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "outputs/multi-stack/completion/noise-bee-repeat-01"
NEW = ROOT / "outputs/multi-stack/overflow/repeat-proposals-17"
OUT = NEW / "shadow-inspection"
OUT.mkdir(exist_ok=False)
def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

old = tifffile.memmap(BASE / "equal/master.tiff", mode="r")
witnesses = [w for w in json.loads((BASE / "inspection/equal/receipt.json").read_text())["witnesses"]
             if w["id"] in ["dark-background", "upper-background"]]
values = []
for witness in witnesses:
    x, y = witness["origin_output_sensor"]
    values.append(old[y:y+384, x:x+384].reshape(-1))
black, white = np.quantile(np.concatenate(values), [.001, .999]).tolist()
assert np.isfinite([black, white]).all() and white > black
arms = {name: NEW / name for name in ["legacy", "proposals", "singletons"]}
arms.update({name: BASE / name for name in ["pass-a", "pass-b"]})
plan = {"schema": "strehl.repeat-shadow-display.v1", "frozen_unix": time.time(),
        "script_sha256": sha(Path(__file__)), "baseline_sha256": sha(BASE / "equal/master.tiff"),
        "original_witnesses_receipt_sha256": sha(BASE / "inspection/equal/receipt.json"),
        "policy": "Pooled0.1%/99.9% linear RGB quantiles from ONLY the two already-frozen baseline background witnesses; one scalar black/white pair for all channels, crops and five arms. No candidate-driven adjustment.",
        "black": black, "white": white, "transfer": "sRGB", "witnesses": witnesses,
        "arms": {name: str(path.relative_to(ROOT)) for name, path in arms.items()},
        "scope": "Additional contrast-sensitive inspection of visible grain/chromatic blotches. Spatial variation carries scene structure and is not temporal noise. Clipped tails are reported, not removed from any numerical risk assay. Original full-scene and all27 detail displays remain unchanged."}
(OUT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
results = {}
for name, path in arms.items():
    master = tifffile.memmap(path / "master.tiff", mode="r")
    assert master.shape == old.shape and master.dtype == np.float32
    rows = []
    for witness in witnesses:
        x, y = witness["origin_output_sensor"]
        crop = master[y:y+384, x:x+384]
        assert crop.shape == (384, 384, 3) and np.isfinite(crop).all()
        z = np.clip((crop.astype(np.float32)-black)/(white-black), 0, 1)
        z = np.where(z <= .0031308, 12.92*z, 1.055*np.power(z, 1/2.4)-.055)
        image_path = OUT / (name + "-" + witness["id"] + ".png")
        Image.fromarray(np.rint(255*np.clip(z, 0, 1)).astype(np.uint8)).save(image_path)
        rows.append({"id": witness["id"], "display_sha256": sha(image_path),
                     "below_black_fraction": float(np.mean(crop < black)),
                     "above_white_fraction": float(np.mean(crop > white)),
                     "linear_crop_sha256": hashlib.sha256(crop.tobytes()).hexdigest()})
    results[name] = {"master_sha256": sha(path / "master.tiff"), "witnesses": rows}
(OUT / "receipt.json").write_text(json.dumps({"plan_sha256": sha(OUT / "plan.json"),
                                             "results": results}, indent=2) + "\n")
print(json.dumps({"black": black, "white": white, "images": 10}))
