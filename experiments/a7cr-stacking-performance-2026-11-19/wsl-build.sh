#!/bin/bash
# Build the engine and the codec bench inside WSL for the OS comparison.
# User-level only: nothing outside $HOME is touched; no shell profile is edited.
set -e
export CARGO_HOME=$HOME/.cargo RUSTUP_HOME=$HOME/.rustup
if ! [ -x "$HOME/.cargo/bin/cargo" ]; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain 1.98.0 --no-modify-path
fi
. "$HOME/.cargo/env"
cd /mnt/c/dev/blog/death-of-software/projects/strehl
export CARGO_TARGET_DIR=$HOME/strehl-wsl-target
date +%T
cargo build --release --locked -p strehl-raw-codec --example v2-bench 2>&1 | tail -5
date +%T
cargo build --release --locked -p strehl-cli 2>&1 | tail -15
date +%T
ls -la "$CARGO_TARGET_DIR/release/strehl" "$CARGO_TARGET_DIR/release/examples/v2-bench"
