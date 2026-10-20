#!/usr/bin/env python3
"""Render a known image through the packaged native app; no desktop input injection."""
import argparse
import binascii
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile
import zlib

COLORS = ((220, 40, 90), (40, 190, 170), (55, 95, 225), (210, 190, 45))
PNG = b"\x89PNG\r\n\x1a\n"


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data))


def fixture(width=320, height=240, colors=COLORS, alpha=None):
    rows = b"".join(b"\0" + b"".join(bytes(colors[(y >= height // 2) * 2 + (x >= width // 2)]
                                             + (() if alpha is None else (alpha,)))
                                       for x in range(width)) for y in range(height))
    return (PNG + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2 if alpha is None else 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def decode_png(data):
    if not data.startswith(PNG):
        raise ValueError("Missing PNG signature")
    offset, compressed, header = 8, bytearray(), None
    while offset < len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind, payload = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + size]
        crc = struct.unpack_from(">I", data, offset + 8 + size)[0]
        if binascii.crc32(kind + payload) != crc:
            raise ValueError("PNG checksum mismatch")
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            compressed.extend(payload)
        offset += size + 12
        if kind == b"IEND":
            break
    if header is None:
        raise ValueError("Missing PNG dimensions")
    width, height, depth, color, compression, filtering, interlace = header
    if (depth != 8 or color not in (2, 6) or compression or filtering or interlace
            or not 0 < width * height <= 16_000_000):
        raise ValueError("Expected a bounded, non-interlaced RGB/RGBA screenshot")
    channels = 3 if color == 2 else 4
    stride = width * channels
    raw = zlib.decompress(compressed)
    if len(raw) != height * (stride + 1):
        raise ValueError("Unexpected PNG pixel size")
    pixels, previous = bytearray(), bytearray(stride)
    for y in range(height):
        at = y * (stride + 1)
        mode, row = raw[at], bytearray(raw[at + 1:at + 1 + stride])
        if mode > 4:
            raise ValueError("Unknown PNG filter")
        for x in range(stride) if mode else ():
            left = row[x - channels] if x >= channels else 0
            up, upper_left = previous[x], previous[x - channels] if x >= channels else 0
            if mode == 4:
                predictors = (left, up, upper_left)
                p = left + up - upper_left
                predictor = min(enumerate(predictors), key=lambda item: (abs(p - item[1]), item[0]))[1]
            else:
                predictor = (0, left, up, (left + up) // 2)[mode]
            row[x] = (row[x] + predictor) & 255
        pixels.extend(row)
        previous = row
    return width, height, channels, pixels


# Hosted Windows can clamp the requested 1200x800 window to its 1024x768 display.
def inspect_image(data, minimum=(1024, 720)):
    width, height, channels, pixels = decode_png(data)
    if width < minimum[0] or height < minimum[1]:
        raise ValueError(f"Window is too small: {width}x{height}")
    points = [[] for _ in COLORS]
    # A sparse grid keeps validation inexpensive even for Retina screenshots.
    for y in range(0, height, max(1, height // 100)):
        for x in range(0, width, max(1, width // 100)):
            at = (y * width + x) * channels
            if channels == 4 and pixels[at + 3] < 250:
                continue
            for index, color in enumerate(COLORS):
                if all(abs(pixels[at + c] - color[c]) <= 8 for c in range(3)):
                    points[index].append((x, y))
    if any(len(group) < 30 for group in points):
        raise ValueError("The rendered window does not contain all four fixture colors")
    centers = [tuple(sum(p[i] for p in group) / len(group) for i in (0, 1)) for group in points]
    if not (centers[0][0] < centers[1][0] and centers[2][0] < centers[3][0]
            and centers[0][1] < centers[2][1] and centers[1][1] < centers[3][1]):
        raise ValueError("The rendered fixture quadrants are misplaced")
    return {"width": width, "height": height, "color_samples": [len(group) for group in points]}


def self_test():
    # Hand-calculated 2x2 RGB rows independently cover every PNG predictor.
    rows = (
        ((10, 20, 30, 40, 50, 60), (30, 40, 50, 60, 70, 80)),
        ((10, 20, 30, 30, 30, 30), (30, 40, 50, 30, 30, 30)),
        ((10, 20, 30, 40, 50, 60), (20, 20, 20, 20, 20, 20)),
        ((10, 20, 30, 35, 40, 45), (25, 30, 35, 25, 25, 25)),
        ((10, 20, 30, 30, 30, 30), (20, 20, 20, 20, 20, 20)),
    )
    for mode, pair in enumerate(rows):
        data = (PNG + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(b"".join(bytes((mode, *row)) for row in pair)))
                + chunk(b"IEND", b""))
        assert decode_png(data)[:3] == (2, 2, 3)
        assert decode_png(data)[3] == bytes((10, 20, 30, 40, 50, 60, 30, 40, 50, 60, 70, 80))
    rgba = (PNG + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes((4, 10, 20, 30, 255, 30, 30, 30, 129,
                                                 4, 20, 20, 20, 91, 20, 20, 20, 216))))
            + chunk(b"IEND", b""))
    assert decode_png(rgba)[3] == bytes((10, 20, 30, 255, 40, 50, 60, 128,
                                       30, 40, 50, 90, 60, 70, 80, 50))
    inspect_image(fixture(), minimum=(320, 240))
    inspect_image(fixture(alpha=255), minimum=(320, 240))
    inspect_image(fixture(width=1024, height=768))
    for width, height in ((1023, 768), (1024, 719)):
        try:
            inspect_image(fixture(width=width, height=height))
        except ValueError as error:
            assert "Window is too small" in str(error)
        else:
            raise AssertionError("An undersized screenshot passed")
    for bad in (fixture(colors=(COLORS[0],) * 4), fixture(colors=COLORS[::-1]),
                fixture(alpha=0), b"not a PNG"):
        try:
            inspect_image(bad, minimum=(320, 240))
        except (ValueError, struct.error):
            continue
        raise AssertionError("A broken screenshot passed")
    print("Native screenshot controls passed (valid RGB/RGBA; blank, reversed, transparent and invalid rejected)")


def smoke(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    preview, screenshot = output / "fixture.png", output / "window.png"
    preview.write_bytes(fixture())
    suffix = ".AppImage" if args.platform == "linux" else ".zip"
    package = (args.dist / f"Strehl-{args.version}-{args.target}{suffix}").resolve()
    with tempfile.TemporaryDirectory(prefix="strehl-native-smoke-") as temporary:
        unpacked = Path(temporary)
        profile = unpacked / "profile"
        profile.mkdir()
        environment = os.environ.copy()
        # workspace_history::default_path checks LOCALAPPDATA first on every OS.
        environment["LOCALAPPDATA"] = str(profile)
        if args.platform == "windows":
            # Windows has a single executable; extract its exact expected entry.
            executable = unpacked / "Strehl.exe"
            with zipfile.ZipFile(package) as archive:
                executable.write_bytes(archive.read("Strehl.exe"))
            command = [str(executable)]
        elif args.platform == "macos":
            subprocess.run(["ditto", "-x", "-k", str(package), str(unpacked)], check=True)
            command = [str(unpacked / "Strehl.app/Contents/MacOS/Strehl")]
        else:
            package.chmod(package.stat().st_mode | 0o111)
            command = [str(package), "--appimage-extract-and-run"]
        command += ["--preview", str(preview), "--screenshot", str(screenshot), "--size", "1200x800"]
        with (output / "app.log").open("w", encoding="utf-8") as log:
            log.write(json.dumps({"command": command}) + "\n")
            log.flush()
            result = subprocess.run(command, cwd=unpacked, env=environment,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=120)
            result.check_returncode()
        receipt = inspect_image(screenshot.read_bytes())
        receipt.update({"platform": args.platform, "target": args.target, "version": args.version,
                        "package": package.name, "scope": "native window and preview rendering"})
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(receipt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--platform", choices=("windows", "linux", "macos"))
    parser.add_argument("--version")
    parser.add_argument("--target")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, default=Path("native-smoke"))
    options = parser.parse_args()
    if options.self_test:
        self_test()
    elif not all((options.platform, options.version, options.target)):
        parser.error("--platform, --version and --target are required")
    else:
        smoke(options)
