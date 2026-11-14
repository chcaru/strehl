#!/bin/bash
set -euo pipefail
cd /mnt/c/dev/blog/death-of-software/projects/strehl
export PATH="/root/.cargo/bin:$PATH"
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
export CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc
export AR_aarch64_unknown_linux_gnu=aarch64-linux-gnu-ar
export CARGO_TARGET_DIR=/tmp/strehl-pi-build/cargo
cargo clippy --locked -p strehl-capture --no-default-features \
  --target aarch64-unknown-linux-gnu --all-targets --no-deps -- -D warnings
