#!/usr/bin/env python3
"""Extract only the headers/runtime needed from the owner's Sony SDK archive."""
# SPDX-License-Identifier: MIT OR Apache-2.0
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", type=Path)
parser.add_argument("out", type=Path)
args = parser.parse_args()
with args.archive.open("rb") as stream:
    archive_hash = hashlib.file_digest(stream, "sha256").hexdigest()
args.out.mkdir(parents=True, exist_ok=True)
with ZipFile(args.archive) as outer:
    with ZipFile(io.BytesIO(outer.read("SimpleCli.zip"))) as inner:
        for member in inner.infolist():
            name = member.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or ":" in name:
                raise ValueError("Unsafe path in SDK archive")
            selected = name == "README.md" or name.startswith(("app/CRSDK/", "external/crsdk/"))
            if selected and not member.is_dir():
                target = args.out.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(inner.read(member))
(args.out / "archive-receipt.json").write_text(json.dumps({
    "archive": str(args.archive.resolve()), "sha256": archive_hash,
    "sdk_version": "2.02.00", "source": "SimpleCli.zip headers and runtime; SDK remains external",
}, indent=2) + "\n", encoding="utf-8")
print(f"Prepared external SDK at {args.out.resolve()}")
