"""Render already completed tiny generated outputs only; no fit or RAW access."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "outputs/raw-quality-2026-10-26/green-phase-screen-3/output/screen.json"
OUT = HERE / "independent-previews-2"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def image(record):
    path = Path(record["path"])
    assert sha(path) == record["sha256"]
    a = np.fromfile(path, dtype="<f4").reshape(record["height"], record["width"], 3)
    assert np.isfinite(a).all()
    a = np.clip(a, 0, 1)
    encoded = np.where(a <= .0031308, 12.92*a, 1.055*a**(1/2.4)-.055)
    return Image.fromarray(np.rint(255*encoded).astype(np.uint8))


def main():
    assert not OUT.exists()
    OUT.mkdir()
    result = json.loads(SOURCE.read_text())
    receipt = {"screen_sha256": sha(SOURCE), "script_sha256": sha(__file__),
               "display": "identical unit gain, clip display only to0..1, sRGB transfer on camera-RGB diagnostic channels; no calibrated color claim",
               "resize": False, "source_pixels_unchanged": True, "panels": []}
    for case in result["cases"]:
        arms = {a["arm"]: a["master"] for a in case["outputs"]}
        records = [("truth", case["truth"])] + [(n, arms[n]) for n in ("canonical", "matched-mean", "phase-energy")]
        panel = Image.new("RGB", (4*290, 274), "#181818")
        draw = ImageDraw.Draw(panel)
        for index, (name, record) in enumerate(records):
            im = image(record)
            assert im.size == (290, 250)
            panel.paste(im, (index*290, 24))
            draw.text((index*290+4, 5), name, fill="white")
        path = OUT / (case["scene"]+".png")
        panel.save(path)
        receipt["panels"].append({"scene": case["scene"], "path": str(path), "sha256": sha(path), "inputs": records})
        if (case.get("extras") or {}).get("foils"):
            records = [("phase-energy", arms["phase-energy"])] + [(f["name"], f["master"]) for f in case["extras"]["foils"]]
            panel = Image.new("RGB", (3*290, 274), "#181818")
            draw = ImageDraw.Draw(panel)
            for index, (name, record) in enumerate(records):
                panel.paste(image(record), (index*290, 24))
                draw.text((index*290+4, 5), name, fill="white")
            path = OUT / "thin-foils.png"
            panel.save(path)
            receipt["panels"].append({"scene": "thin-foils", "path": str(path), "sha256": sha(path), "inputs": records})
    assert sha(SOURCE) == receipt["screen_sha256"]
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(json.dumps({"complete_panels": len(receipt["panels"]), "screen_sha256": receipt["screen_sha256"]}))


if __name__ == "__main__":
    main()
