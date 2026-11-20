#!/bin/bash
# Build the experimental bridge for the Pi in WSL from a scratch overlay of the workspace.
#   build-lab.sh <repo root as a WSL path>
# The repository is only read: the overlay is symlinks to it, except a patched copy of
# crates/strehl-capture/src/ptp.rs. Output: /tmp/strehl-lab/strehl-sony-ptp-lab (aarch64).
set -euo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
repo="$1"
work=/tmp/strehl-lab
rm -rf "$work/src"
mkdir -p "$work/src/crates/strehl-capture/src"
cp "$repo/Cargo.toml" "$repo/Cargo.lock" "$work/src/"
for entry in third-party experiments rust-toolchain.toml .cargo; do
  if [ -e "$repo/$entry" ]; then ln -s "$repo/$entry" "$work/src/$entry"; fi
done
for crate in "$repo"/crates/*; do
  name=$(basename "$crate")
  if [ "$name" != strehl-capture ]; then ln -s "$crate" "$work/src/crates/$name"; fi
done
for entry in "$repo"/crates/strehl-capture/*; do
  name=$(basename "$entry")
  if [ "$name" != src ] && [ "$name" != target ]; then ln -s "$entry" "$work/src/crates/strehl-capture/$name"; fi
done
for entry in "$repo"/crates/strehl-capture/src/*; do
  name=$(basename "$entry")
  if [ "$name" != ptp.rs ]; then ln -s "$entry" "$work/src/crates/strehl-capture/src/$name"; fi
done
python3 "$repo/experiments/capture-pipeline-2026-11-20/ptp-lab/make-lab.py" \
  "$repo/crates/strehl-capture/src/ptp.rs" "$work/src/crates/strehl-capture/src/ptp.rs"
cd "$work/src"
export CARGO_TARGET_DIR=/tmp/strehl-pi-build/cargo
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
cargo build --locked -p strehl-capture --no-default-features --release \
  --bin strehl-sony-ptp --target aarch64-unknown-linux-gnu 2>&1 | tail -12
cp "$CARGO_TARGET_DIR/aarch64-unknown-linux-gnu/release/strehl-sony-ptp" "$work/strehl-sony-ptp-lab"
ls -la "$work/strehl-sony-ptp-lab"
sha256sum "$work/strehl-sony-ptp-lab"
