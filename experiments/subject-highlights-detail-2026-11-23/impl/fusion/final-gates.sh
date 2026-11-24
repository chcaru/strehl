#!/bin/sh
# Every X4 gate with one engine build:
#   sh final-gates.sh <out dir> <new exe> <base exe> <fixture dir>
# 1. identity: the weevil and scarab (no highlight groups) with the base build and this one;
# 2. gates.sh on the real tiered rig captures;
# 3. the three-plane fixture (1.3 s base, 1/15 s highlight, ratio about 20);
# 4. the in-capture checker on the every-plane capture.
set -u
OUT=$1
NEW=$2
BASE=$3
FIXTURE=$4
HERE=$(dirname "$0")
sh "$HERE/identity-gate.sh" "$OUT/identity" "$BASE" "$NEW"
for r in weevil scarab; do
  sha256sum "$OUT/identity/id-base-$r/result.tiff" "$OUT/identity/id-new-$r/result.tiff"
done > "$OUT/identity/sha256.txt"
sh "$HERE/gates.sh" "$OUT/rig" "$NEW"
STREHL_CACHE_DIR="$OUT/fixture/cache" sh "$HERE/render.sh" "$NEW" "$FIXTURE" "$OUT/fixture/tier3"
python "$HERE/summarise.py" "$OUT/fixture/tier3/fusion.jsonl" > "$OUT/fixture/tier3/summary.txt"
mkdir -p "$OUT/follow"
STREHL_CACHE_DIR="$OUT/follow/cache" "$NEW" follow D:/StrehlCaptures/stack-1795512217588-11344 \
  --idle-timeout-s 60 > "$OUT/follow/every1.txt" 2>&1
echo "exit $?" >> "$OUT/follow/every1.txt"
echo done > "$OUT/final-done.txt"
