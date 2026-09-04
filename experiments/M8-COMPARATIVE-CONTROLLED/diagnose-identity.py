from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np

from common import (
    COMPARATOR,
    COMPARATOR_OPTIONS,
    EXPECTED,
    ROOT,
    atomic_json,
    bounded_environment,
    byte_sha256,
    linear_rec2020_icc,
    pixel_sha256,
    sha256,
    write_rgb16,
)


ARMS = {
    "I02-S": {"count": 2, "width": 256, "height": 192, "variant": False},
    "I08-S": {"count": 8, "width": 256, "height": 192, "variant": False},
    "I92-S": {"count": 92, "width": 256, "height": 192, "variant": False},
    "V92-S": {"count": 92, "width": 256, "height": 192, "variant": True},
    "I02-F": {"count": 2, "width": 3392, "height": 2262, "variant": False},
}


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def require_gate(path: Path, size_class: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    age = dt.datetime.now(dt.timezone.utc) - parse_time(payload["measured_at"])
    if payload.get("class") != size_class:
        raise RuntimeError(
            f"host gate class {payload.get('class')!r}, expected {size_class!r}"
        )
    if payload.get("pass") is not True:
        raise RuntimeError("host-load gate did not pass")
    if age.total_seconds() < 0 or age.total_seconds() > 600:
        raise RuntimeError(f"host-load gate is stale: {age.total_seconds():.1f}s")
    return payload


def synthetic(width: int, height: int, offset: int = 0) -> np.ndarray:
    y = np.arange(height, dtype=np.uint32)[:, None]
    x = np.arange(width, dtype=np.uint32)[None, :]
    image = np.empty((height, width, 3), dtype=np.uint16)
    for channel, seed in enumerate([0x13579BDF, 0x2468ACE1, 0x10293847]):
        values = (
            (x * np.uint32(73856093))
            ^ (y * np.uint32(19349663))
            ^ np.uint32(seed)
        )
        image[..., channel] = (
            4096 + ((values + np.uint32(offset)) % np.uint32(53248))
        ).astype(np.uint16)
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("arm", choices=sorted(ARMS))
    parser.add_argument("--host-gate", type=Path, required=True)
    parser.add_argument("--extra-option", action="append", default=[])
    args = parser.parse_args()
    arm = ARMS[args.arm]
    size_class = "full" if args.arm.endswith("-F") else "small"
    gate = require_gate(args.host_gate, size_class)
    if sha256(COMPARATOR) != EXPECTED["comparator_sha256"]:
        raise RuntimeError("comparator binary changed")
    root = ROOT / "diagnostics" / args.arm
    if args.extra_option:
        suffix = byte_sha256("\0".join(args.extra_option).encode("utf-8"))[:12]
        root = ROOT / "diagnostics" / f"{args.arm}-extra-{suffix}"
    if root.exists():
        raise RuntimeError(f"diagnostic already exists: {root}")
    input_dir = root / "input"
    work = root / "work"
    input_dir.mkdir(parents=True)
    work.mkdir()
    icc = linear_rec2020_icc()
    inputs = []
    base_hashes = []
    if arm["variant"]:
        for index in range(arm["count"]):
            image = synthetic(arm["width"], arm["height"], index % 7)
            path = input_dir / f"{index:03d}.tif"
            write_rgb16(path, image, icc, f"diagnostic {args.arm} input {index}")
            inputs.append(path)
            base_hashes.append(pixel_sha256(image))
    else:
        image = synthetic(arm["width"], arm["height"])
        base = root / "identity-source.tif"
        write_rgb16(base, image, icc, f"diagnostic {args.arm} identity input")
        for index in range(arm["count"]):
            path = input_dir / f"{index:03d}.tif"
            os.link(base, path)
            inputs.append(path)
        base_hashes.append(pixel_sha256(image))
    output = root / "direct-output.tif"
    command = [
        str(COMPARATOR),
        *COMPARATOR_OPTIONS,
        *args.extra_option,
        f"--output={output}",
        *[str(path) for path in inputs],
    ]
    run = subprocess.run(
        command,
        cwd=work,
        env=bounded_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout_path = root / "stdout.txt"
    stderr_path = root / "stderr.txt"
    stdout_path.write_text(run.stdout, encoding="utf-8")
    stderr_path.write_text(run.stderr, encoding="utf-8")
    payload = {
        "diagnostic_only": True,
        "arm": args.arm,
        "count": arm["count"],
        "dimensions": [arm["height"], arm["width"], 3],
        "variant_offsets": arm["variant"],
        "pixel_sha256": base_hashes,
        "host_gate": gate,
        "comparator_sha256": sha256(COMPARATOR),
        "extra_options": args.extra_option,
        "command": command,
        "returncode": run.returncode,
        "output_exists": output.is_file(),
        "output_sha256": sha256(output) if output.is_file() else None,
        "stdout_sha256": sha256(stdout_path),
        "stderr_sha256": sha256(stderr_path),
        "last_stdout_lines": run.stdout.splitlines()[-10:],
        "stderr": run.stderr,
    }
    atomic_json(root / "result.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

