from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_ICC = b"M153-SYNTHETIC-LINEAR-RGB-V1"
STAGES = ("load", "register", "stack", "color")


def emit_stages() -> None:
    for name in STAGES:
        print(
            f"M153_STAGE {name} wall_seconds=0.000000 "
            "cpu_seconds=0.000000 source=synthetic",
            flush=True,
        )


def write_tiff(
    path: Path,
    *,
    width: int,
    height: int,
    icc: bytes,
    corrupt: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if corrupt == "bytes":
        path.write_bytes(b"not-a-tiff")
        return
    icc_payload = b""
    if corrupt != "missing-icc":
        icc_payload = b"WRONG-ICC" if corrupt == "wrong-icc" else icc
    entries: list[tuple[int, int, int, bytes | None]] = [
        (256, 4, 1, struct.pack("<I", width)),
        (257, 4, 1, struct.pack("<I", height)),
        (258, 3, 3, struct.pack("<HHH", 16, 16, 16)),
        (259, 3, 1, struct.pack("<H", 1)),
        (262, 3, 1, struct.pack("<H", 2)),
        (273, 4, 1, None),
        (277, 3, 1, struct.pack("<H", 3)),
        (278, 4, 1, struct.pack("<I", height)),
        (279, 4, 1, struct.pack("<I", width * height * 6)),
        (282, 5, 1, struct.pack("<II", 72, 1)),
        (283, 5, 1, struct.pack("<II", 72, 1)),
        (284, 3, 1, struct.pack("<H", 1)),
        (296, 3, 1, struct.pack("<H", 2)),
        (339, 3, 3, struct.pack("<HHH", 1, 1, 1)),
    ]
    if icc_payload:
        entries.append((34675, 7, len(icc_payload), icc_payload))
    entries.sort(key=lambda entry: entry[0])
    ifd_size = 2 + len(entries) * 12 + 4
    extra_offset = 8 + ifd_size
    extras = bytearray()
    encoded_entries: list[tuple[int, int, int, bytes]] = []
    strip_index = next(index for index, entry in enumerate(entries) if entry[0] == 273)
    for index, (tag, kind, count, value) in enumerate(entries):
        if index == strip_index:
            encoded_entries.append((tag, kind, count, b""))
            continue
        if value is None:
            raise AssertionError(f"unexpected deferred TIFF tag {tag}")
        if len(value) <= 4:
            encoded_entries.append((tag, kind, count, value.ljust(4, b"\0")))
            continue
        if (extra_offset + len(extras)) % 2:
            extras.extend(b"\0")
        offset = extra_offset + len(extras)
        encoded_entries.append((tag, kind, count, struct.pack("<I", offset)))
        extras.extend(value)
    if (extra_offset + len(extras)) % 2:
        extras.extend(b"\0")
    pixel_offset = extra_offset + len(extras)
    strip_tag, strip_kind, strip_count, _ = encoded_entries[strip_index]
    encoded_entries[strip_index] = (
        strip_tag,
        strip_kind,
        strip_count,
        struct.pack("<I", pixel_offset),
    )
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            pixels.extend(
                struct.pack(
                    "<HHH",
                    x * 257,
                    y * 257,
                    (x + y) * 127,
                )
            )
    payload = bytearray(b"II")
    payload.extend(struct.pack("<HI", 42, 8))
    payload.extend(struct.pack("<H", len(encoded_entries)))
    for tag, kind, count, value in encoded_entries:
        payload.extend(struct.pack("<HHI", tag, kind, count))
        payload.extend(value)
    payload.extend(struct.pack("<I", 0))
    payload.extend(extras)
    payload.extend(pixels)
    path.write_bytes(payload)
    with path.open("r+b") as output:
        output.flush()
        os.fsync(output.fileno())


def child(args: argparse.Namespace) -> int:
    time.sleep(args.sleep_ms / 1000.0)
    write_tiff(
        args.output,
        width=args.width,
        height=args.height,
        icc=args.icc_text.encode("ascii"),
        corrupt=args.corrupt,
    )
    print(
        "M153_STAGE write wall_seconds=0.000000 cpu_seconds=0.000000 source=synthetic",
        flush=True,
    )
    return 0


def render(args: argparse.Namespace) -> int:
    emit_stages()
    if args.spawn_child_ms is not None:
        command = [
            str(Path(sys.executable).resolve(strict=True)),
            str(Path(__file__).resolve()),
            "_child",
            "--output",
            str(args.output),
            "--sleep-ms",
            str(args.spawn_child_ms),
            "--width",
            str(args.width),
            "--height",
            str(args.height),
            "--icc-text",
            args.icc_text,
            "--corrupt",
            args.corrupt,
        ]
        subprocess.Popen(command)
        return 0
    time.sleep(args.sleep_ms / 1000.0)
    write_tiff(
        args.output,
        width=args.width,
        height=args.height,
        icc=args.icc_text.encode("ascii"),
        corrupt=args.corrupt,
    )
    print(
        "M153_STAGE write wall_seconds=0.000000 cpu_seconds=0.000000 source=synthetic",
        flush=True,
    )
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="command", required=True)
    for name in ("render", "_child"):
        command = subparsers.add_parser(name)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--sleep-ms", type=float, default=0.0)
        command.add_argument("--spawn-child-ms", type=float)
        command.add_argument("--width", type=int, default=4)
        command.add_argument("--height", type=int, default=4)
        command.add_argument(
            "--icc-text",
            default=DEFAULT_ICC.decode("ascii"),
        )
        command.add_argument(
            "--corrupt",
            choices=("none", "bytes", "missing-icc", "wrong-icc"),
            default="none",
        )
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "_child":
        return child(args)
    return render(args)


if __name__ == "__main__":
    raise SystemExit(main())
