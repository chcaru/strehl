#!/bin/sh
# F1 gates (capture calibration spec 9, F1): highlight groups reach the picture.
#   sh gates.sh <out dir> <base exe> <new exe>
# Each arm renders with its own private cache; capture folders are only read.
# TIFFs are hashed and deleted (disk); logs and fusion reports are kept.
set -u
OUT=$1
BASE=$2
NEW=$3
HERE=$(dirname "$0")
RENDER="$HERE/../../subject-highlights-detail-2026-11-23/impl/fusion/render.sh"
CAP=D:/StrehlCaptures
mkdir -p "$OUT"
export STREHL_UI_PROGRESS=1
one() { # arm exe capture name [VAR=value ...]
  arm=$1; exe=$2; dir=$3; name=$4; shift 4
  STREHL_CACHE_DIR="$OUT/cache-$arm" sh "$RENDER" "$exe" "$dir" "$OUT/$arm-$name" "$@" > /dev/null
  if [ -f "$OUT/$arm-$name/result.tiff" ]; then
    sha256sum "$OUT/$arm-$name/result.tiff" | cut -d' ' -f1 > "$OUT/$arm-$name/result.sha256"
    rm -f "$OUT/$arm-$name/result.tiff"
  fi
  printf '%s %s: ' "$arm" "$name"
  grep -E "^highlights      : [0-9]+ planes fused" "$OUT/$arm-$name/render.log" | tail -1 | cut -c19-140
  grep -E "event=highlights" "$OUT/$arm-$name/render.log" | tail -1
  tail -1 "$OUT/$arm-$name/render.log"
}
# 1. Captures without highlight groups: identical bytes.
for pair in "weevil stack-1795460665629-8651" "short stack-1795082306428-20449"; do
  set -- $pair
  for arm in base new; do
    if [ $arm = base ]; then exe=$BASE; else exe=$NEW; fi
    one $arm "$exe" "$CAP/$2" "$1"
  done
  if cmp -s "$OUT/base-$1/result.sha256" "$OUT/new-$1/result.sha256"; then
    echo "IDENTICAL $1"
  else
    echo "DIFFERENT $1"
  fi
done
# 2. Every capture with highlight groups on this machine besides the dragonfly.
for run in stack-1795583186775-12502 stack-1795638138175-14989 stack-1795640925619-14989 \
  stack-1795649995211-14989; do
  for arm in base new; do
    if [ $arm = base ]; then exe=$BASE; else exe=$NEW; fi
    one $arm "$exe" "$CAP/$run" "$run"
  done
done
# 3. Planted ratio errors on the dragonfly: 5 % corrected, 25 % refused, and a
#    planted factor of 2 makes every pair unusable (the checks row's failing input).
D=$CAP/stack-1795713444768-14989
one new "$NEW" "$D" plant-1.05 STREHL_HIGHLIGHT_RATIO_PLANT=1.05
one new "$NEW" "$D" plant-1.25 STREHL_HIGHLIGHT_RATIO_PLANT=1.25
one new "$NEW" "$D" plant-2 STREHL_HIGHLIGHT_RATIO_PLANT=2
echo done > "$OUT/gates-done.txt"
