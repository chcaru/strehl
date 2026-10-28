"""Lossless PNG wrapping of saved complete fixed-display generated PPMs only."""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]


def binding(path):
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    source, out = a.input.resolve(), a.out.resolve()
    assert source.is_relative_to(ROOT / "outputs") and source.is_dir()
    assert out.is_relative_to(ROOT / "outputs") and not out.exists() and not out.is_relative_to(source)
    screen_path = source / "screen.json"
    screen = json.loads(screen_path.read_text())
    assert screen["all_cases_completed"] and screen["admission"] is False
    paths = [source / "guard-destroyers" / (name + ".ppm") for name in ("truth", "false-green", "erased-coarse")]
    for case in screen["cases"]:
        paths.extend(source / case["case"] / (name + ".ppm") for name in ("truth", "baseline", "off", "bounded", "unbounded"))
    before = [binding(path) for path in [screen_path, Path(__file__).resolve(), *paths]]
    out.mkdir()
    records = []
    for path in paths:
        target = out / path.relative_to(source).with_suffix(".png")
        target.parent.mkdir(exist_ok=True)
        with Image.open(path) as image:
            assert image.mode == "RGB" and image.size == (128,128)
            original = image.tobytes()
            image.save(target)
        with Image.open(target) as check:
            assert check.size == (128,128) and check.tobytes() == original
        records.append(dict(input=binding(path), output=binding(target), exact=True))
    assert before == [binding(path) for path in [screen_path, Path(__file__).resolve(), *paths]]
    result = dict(status="COMPLETE_GENERATED_PREVIEWS_NO_VERDICT", inputs=before, outputs=records,
                  input_unchanged=True, admission=False, display="Exact saved PPM pixels; no resize, retone, filtering or claimed camera color calibration.")
    with (out / "receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(status=result["status"], outputs=len(records))))


if __name__ == "__main__":
    main()
