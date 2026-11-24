#!/bin/sh
# Plan X7 gates for X4 on the real tiered rig captures (2026-11-24, weevil pronotum at the
# lens's closest focus, 2 s base, 1/4 s highlight groups) and the three-plane fixture.
#   sh gates.sh <out dir> <exe>
# Capture folders are only read; caches, maps and outputs stay under <out dir>.
set -u
OUT=$1
EXE=$2
HERE=$(dirname "$0")
R="sh $HERE/render.sh"
EVERY1=D:/StrehlCaptures/stack-1795512217588-11344
EVERY2=D:/StrehlCaptures/stack-1795512705325-11344
mkdir -p "$OUT"
export STREHL_CACHE_DIR="$OUT/cache"

# 1. The default render, fused, of both captures (SKIP_DEFAULT=1 skips it).
[ -n "${SKIP_DEFAULT:-}" ] || for c in every1 every2; do
  if [ "$c" = every1 ]; then DIR=$EVERY1; else DIR=$EVERY2; fi
  $R "$EXE" "$DIR" "$OUT/$c-fused"
  python "$HERE/summarise.py" "$OUT/$c-fused/fusion.jsonl" > "$OUT/$c-fused/summary.txt"
done

# 2. Unpinned areas against the base exposure alone: sensor masters (the merged CFA
#    planes before any display step), with the per-capture lateral-CA refinement and the
#    optical restoration off in both arms (each is measured from the whole picture, so a
#    fused highlight could move them everywhere), and the colour carry off (the sensor
#    master holds the four CFA planes only).
export STREHL_CARRY_RGB=off
for c in every1 every2; do
  if [ "$c" = every1 ]; then DIR=$EVERY1; else DIR=$EVERY2; fi
  for arm in fused base; do
    rm -f "$OUT/$c-master-$arm/master.tif" "$OUT/$c-master-$arm/master.tif.json"
    mkdir -p "$OUT/$c-master-$arm"
    if [ "$arm" = fused ]; then F=on; else F=off; fi
    STACK_ARGS="--refine-ca=off --sensor-master $OUT/$c-master-$arm/master.tif" \
      $R "$EXE" "$DIR" "$OUT/$c-master-$arm" STREHL_OPTICAL_RESTORE=off STREHL_HIGHLIGHT_FUSION=$F
  done
  python "$HERE/compare-masters.py" "$OUT/$c-master-fused/master.tif" "$OUT/$c-master-base/master.tif" \
    > "$OUT/$c-compare.txt" 2>&1
done

# 3. The GPU's patch kernels against the CPU's: the fused sensor master with the GPU
#    fold off must be the same bytes.
mkdir -p "$OUT/every1-master-cpu"
rm -f "$OUT/every1-master-cpu/master.tif" "$OUT/every1-master-cpu/master.tif.json"
STACK_ARGS="--refine-ca=off --sensor-master $OUT/every1-master-cpu/master.tif" \
  $R "$EXE" "$EVERY1" "$OUT/every1-master-cpu" STREHL_OPTICAL_RESTORE=off STREHL_GPU_FOLD=off
sha256sum "$OUT/every1-master-fused/master.tif" "$OUT/every1-master-cpu/master.tif" > "$OUT/gpu-cpu.txt"

# 4. Planted ratio errors: 5 % must be corrected, 25 % refused.
unset STREHL_CARRY_RGB
[ -n "${SKIP_PLANTS:-}" ] || for p in 1.05 1.25; do
  $R "$EXE" "$EVERY1" "$OUT/every1-plant-$p" STREHL_HIGHLIGHT_RATIO_PLANT=$p
  python "$HERE/summarise.py" "$OUT/every1-plant-$p/fusion.jsonl" > "$OUT/every1-plant-$p/summary.txt"
done
echo done > "$OUT/gates-done.txt"
