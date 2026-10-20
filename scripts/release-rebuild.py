#!/usr/bin/env python3
"""Rebuild the source/relink kit, optionally substituting a modified crate."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=(
        "x86_64-pc-windows-msvc", "x86_64-unknown-linux-gnu",
        "x86_64-apple-darwin", "aarch64-apple-darwin"))
    parser.add_argument("--patch", action="append", default=[], metavar="CRATE=PATH")
    args = parser.parse_args()
    receipt = json.loads((root / "release-source.json").read_text(encoding="utf-8"))
    environment = {**os.environ, "STREHL_BUILD_ID": receipt["source_commit"][:12]}
    if args.target.endswith("-windows-msvc"):
        environment["RUSTFLAGS"] = "-C target-feature=+crt-static"
    if args.target.endswith("-apple-darwin"):
        environment["MACOSX_DEPLOYMENT_TARGET"] = "11.0"
    command = ["cargo", "build", "--offline", "--release", "--target", args.target,
               "-p", "strehl-ui", "--bin", "strehl-ui"]
    if not args.patch:
        command.append("--locked")
    for patch in args.patch:
        name, separator, path = patch.partition("=")
        if not separator or not name or not all(c.isalnum() or c in "-_" for c in name):
            parser.error("--patch must have the form crate-name=path")
        replacement = (root / path).resolve()
        if not (replacement / "Cargo.toml").is_file():
            parser.error(f"Modified crate has no Cargo.toml: {replacement}")
        command.extend(["--config", f"patch.crates-io.{name}.path={json.dumps(str(replacement))}"])
    subprocess.run(command, cwd=root, env=environment, check=True)


if __name__ == "__main__":
    main()
