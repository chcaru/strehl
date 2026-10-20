"""Independent AVIF decode/metadata control for the deterministic hdr-fixture example.

Requires FFmpeg/ffprobe executables and NumPy. Does not import the encoder's
transfer function. Run:
  cargo run -p strehl-edit --example hdr-fixture -- outputs/hdr-edit-validation
  python scripts/verify-hdr-avif.py outputs/hdr-edit-validation
"""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np


def verify(path):
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)
    ], text=True))
    stream = probe["streams"][0]
    expected = {
        "codec_name": "av1", "width": 128, "height": 64,
        "pix_fmt": "yuv444p10le", "color_range": "pc",
        "color_space": "bt2020nc", "color_transfer": "smpte2084",
        "color_primaries": "bt2020",
    }
    for key, value in expected.items():
        assert stream[key] == value, (key, stream.get(key), value)
    raw = path.read_bytes()
    nclx = raw.index(b"nclx")
    assert raw[nclx + 4:nclx + 11] == bytes([0, 9, 0, 16, 0, 9, 128]), "container/bitstream color disagreement"
    decoded = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(path),
        "-pix_fmt", "gbrpf32le", "-f", "rawvideo", "pipe:1"
    ])
    rgb = np.frombuffer(decoded, dtype="<f4").reshape(3, 64, 128)[[2, 0, 1]].astype(np.float64)
    # ST 2084 EOTF, the inverse direction from the encoder. The plant names
    # absolute emitted light levels, not samples recomputed by its own encoder.
    power = rgb ** (32.0 / 2523.0)
    nits = (np.maximum(power - 3424.0 / 4096.0, 0) /
            (2413.0 / 128.0 - (2392.0 / 128.0) * power)) ** (16384.0 / 2610.0) * 10000
    samples = np.array([nits[:, 16, 8 + 16 * k].mean() for k in range(8)])
    targets = np.array([2.03, 36.54, 101.5, 203.0, 406.0, 812.0, 20.3, 162.4])
    # Quantized YUV -> RGB conversion costs small rounding; SDR-at-PQ and wrong
    # reference-white plants miss this by orders of magnitude.
    assert np.all(np.abs(samples - targets) < np.maximum(0.15, targets * 0.03)), (samples, targets)
    assert samples[5] > 3.8 * samples[3], "HDR highlights flattened to reference white"
    assert np.all(np.diff(samples[:6]) > 0), "luminance order collapsed"
    content = next(x for x in stream["side_data_list"] if x["side_data_type"] == "Content light level metadata")
    assert content["max_content"] == 812 and content["max_average"] > 0
    return {"metadata": expected, "decoded_gray_nits": samples.tolist(), "expected_gray_nits": targets.tolist(),
            "content_light": content}


def main():
    directory = Path(sys.argv[1])
    result = verify(directory / "fixture.avif")
    bad = bytearray((directory / "fixture.avif").read_bytes())
    nclx = bad.index(b"nclx")
    bad[nclx + 7] = 13  # Deliberately mislabeled sRGB transfer in container.
    broken = directory / "wrong-transfer-control.avif"
    broken.write_bytes(bad)
    try:
        verify(broken)
    except AssertionError:
        result["mislabeled_transfer_control"] = "rejected"
    else:
        raise AssertionError("verification accepted wrong transfer metadata")
    (directory / "independent-hdr-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
