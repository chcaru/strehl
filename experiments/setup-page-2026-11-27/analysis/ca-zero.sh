#!/usr/bin/env bash
# Lateral colour from nothing against from the shipped profile, on four-shot stacks.
# usage: ca-zero.sh <tag> <run folder>
cd "C:/strehl-scratch/calib-page" || exit 1
tag=$1
dir=$2
one() {
  name=$1
  val=$2
  (
    if [ -n "$val" ]; then export STREHL_CA_ZERO_PROFILE="$val"; fi
    export STREHL_PIXEL_SHIFT=remosaic
    export STREHL_CACHE_DIR="C:/strehl-scratch/calib-page/cache-zero"
    ./target/release/strehl.exe stack "$dir" --srgb -o "ca-$tag-$name.tif" > "ca-$tag-$name.log" 2>&1
    echo "exit $?" >> "ca-$tag-$name.log"
  )
  rm -f "ca-$tag-$name.tif"
  echo "== $tag $name ($val)"
  grep -A1 "CA refinement   : measured" "ca-$tag-$name.log" | cut -c1-150
  grep -E "^exit|^total" "ca-$tag-$name.log" | tr '\n' ' '
  echo
}
one zero "1"
r=$(grep "exact red" "ca-$tag-zero.log" | head -1 | awk '{print $3 * 1e6}')
b=$(grep "exact red" "ca-$tag-zero.log" | head -1 | awk '{print $7 * 1e6}')
if [ -n "$r" ]; then one pass2 "$r,$b"; fi
one shipped ""
