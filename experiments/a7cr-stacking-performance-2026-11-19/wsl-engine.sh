#!/bin/bash
# The engine inside WSL on a 24-plane copy of the scarab capture held in the
# distro's own ext4 disk: CPU route with an empty cache, then cached; then
# what the GPU route finds.
W=/mnt/c/dev/blog/death-of-software/projects/strehl/outputs/perf-plan-3
S=$HOME/scarab24
BIN=$HOME/strehl-wsl-target/release
if ! [ -f "$S/frame-000096.ARW.straw" ]; then
  mkdir -p "$S"
  time cp "$W/scratch/scarab24/"* "$S/"
  echo "copied through 9p: $(du -sh "$S" | cut -f1)"
fi
rm -rf "$HOME/strehl-wsl-cache"; mkdir -p "$HOME/strehl-wsl-cache" "$HOME/strehl-wsl-out"
run() {
  tag=$1; shift
  echo "== $tag: $*"
  TIMEFORMAT="$tag wall_s=%R user_s=%U kernel_s=%S"
  time env STREHL_PIXEL_SHIFT=remosaic STREHL_CACHE_DIR=$HOME/strehl-wsl-cache "$@" "$BIN/strehl" stack "$S" --demosaic --limit 24 --out "$HOME/strehl-wsl-out/$tag.tif" 2> "$HOME/strehl-wsl-out/$tag.log" > /dev/null
  echo "exit=$?"
  tail -1 "$HOME/strehl-wsl-out/$tag.log" | cut -c1-200
  grep -E "gpu fold|total  |folded  |alignment  " "$HOME/strehl-wsl-out/$tag.log" | cut -c1-170
  [ -f "$HOME/strehl-wsl-out/$tag.tif" ] && sha256sum "$HOME/strehl-wsl-out/$tag.tif" | cut -c1-64 && rm -f "$HOME/strehl-wsl-out/$tag.tif"
}
run wsl-cpu-first STREHL_GPU_FOLD=off
run wsl-cpu-later STREHL_GPU_FOLD=off
run wsl-cpu-later2 STREHL_GPU_FOLD=off
run wsl-gpu-on STREHL_GPU_FOLD=on
run wsl-auto STREHL_GPU_FOLD=auto
