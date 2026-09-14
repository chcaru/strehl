"""Export already verified CFA patches for the native consumer; no RAW read."""
from pathlib import Path
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parent


def main():
    out = HERE / "local-placement-consumer-inputs-1"
    out.mkdir()
    source = HERE / "joint-raw-samples-2/receipt.json"
    fit_path = HERE / "local-green-translation-1/result.json"
    receipt = json.loads(source.read_text())
    local = json.loads(fit_path.read_text())
    corrections = {row["frame"]: row for row in local["frames"]}
    frames = []
    for row in receipt["frames"]:
        index = row["index"]
        if index == 145:
            continue
        raw = np.load(HERE / f"joint-raw-samples-2/frame-{index}-cfa.npy", allow_pickle=False)
        assert raw.dtype == np.uint16
        data = raw.astype("<u2", copy=False).tobytes()
        assert hashlib.sha256(data).hexdigest() == row["raw_u16_sha256"]
        name = f"frame-{index}.u16"
        (out / name).write_bytes(data)
        frames.append(dict(row, file=name, delta_source_native=corrections[index]["delta_source_native"]))
    assert [row["index"] for row in frames] == list(range(146, 154))
    receipt["frames"] = frames
    receipt.update(camera="ILCE-7CM2", iso=100,
        xyz_to_cam=[[.746, -.2365, -.0588], [-.5687, 1.3442, .2474], [-.0624, .1156, .6584]],
        tone_bits=json.loads((HERE / "matched-chip-on-1/receipt.json").read_text())["tone_bits"],
        scope="Eight saved original CFA patches for a four-Laplacian-level actual cropped-consumer diagnostic; not full seven-band baseline. No original RAW read during export.",
        camera_provenance="chip-baseline-1/render.log:5",
        source_receipt_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        local_alignment_sha256=hashlib.sha256(fit_path.read_bytes()).hexdigest())
    (out / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (out / "config.json").write_text(json.dumps(dict(input_dir=str(out),
        out=str(HERE / "local-placement-consumer-1")), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
