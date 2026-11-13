#!/bin/bash
set -euo pipefail
source_root=$(realpath "$1")
sdk_root=$(realpath "$2")
output=$(realpath -m "$3")
mkdir -p "$output" /tmp/strehl-pi-build
link_flags=""
if [ "$#" -ge 4 ]; then link_flags="-Wl,-rpath-link,$4/usr/lib/aarch64-linux-gnu"; fi
cmake -S "$source_root/tools/sony-control" -B /tmp/strehl-pi-build/bridge \
  -DSONY_SDK_ROOT="$sdk_root" -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 -DCMAKE_CXX_COMPILER=aarch64-linux-gnu-g++ -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXE_LINKER_FLAGS="$link_flags"
cmake --build /tmp/strehl-pi-build/bridge -j 4
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
export CARGO_TARGET_DIR=/tmp/strehl-pi-build/cargo
export PATH="/root/.cargo/bin:$PATH"
cargo build --manifest-path "$source_root/Cargo.toml" --locked -p strehl-capture --no-default-features \
  --bin strehl-capture-headless --target aarch64-unknown-linux-gnu --release
cp /tmp/strehl-pi-build/cargo/aarch64-unknown-linux-gnu/release/strehl-capture-headless "$output/"
cp -a /tmp/strehl-pi-build/bin/. "$output/"
aarch64-linux-gnu-readelf -h "$output/strehl-capture-headless" "$output/strehl-sony-control"
