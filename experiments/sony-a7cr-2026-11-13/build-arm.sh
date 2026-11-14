#!/bin/bash
set -euo pipefail
cd /mnt/c/dev/blog/death-of-software/projects/strehl
export PATH="/root/.cargo/bin:$PATH"
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
export CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc
export AR_aarch64_unknown_linux_gnu=aarch64-linux-gnu-ar
export CARGO_TARGET_DIR=/tmp/strehl-pi-build/cargo
cargo build --locked -p strehl-capture --no-default-features --release \
  --target aarch64-unknown-linux-gnu --bin strehl-capture-headless --bin strehl-sony-ptp -j 2
out=outputs/sony-a7cr-2026-11-13/arm64
mkdir -p "$out"
cp "$CARGO_TARGET_DIR/aarch64-unknown-linux-gnu/release/strehl-capture-headless" "$out/"
cp "$CARGO_TARGET_DIR/aarch64-unknown-linux-gnu/release/strehl-sony-ptp" "$out/"
sha256sum "$out/strehl-capture-headless" "$out/strehl-sony-ptp"
