#!/bin/bash
# Cross-build the Pi controller and bridge from the working tree (read-only use of it).
set -euo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
cd "$1"
export CARGO_TARGET_DIR=/tmp/strehl-pi-build/cargo
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
cargo build --locked -p strehl-capture --no-default-features --release \
  --bin strehl-capture-headless --bin strehl-sony-ptp --target aarch64-unknown-linux-gnu 2>&1 | grep -E "Compiling strehl|Finished|error|warning" || true
mkdir -p "$2"
for b in strehl-capture-headless strehl-sony-ptp; do
  cp "$CARGO_TARGET_DIR/aarch64-unknown-linux-gnu/release/$b" "$2/$b"
  sha256sum "$2/$b"
done
