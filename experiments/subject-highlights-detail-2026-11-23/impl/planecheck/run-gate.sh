#!/bin/sh
# Plan Q5 gate runs: the new check's reports on the two close-tile captures and the weevil,
# then default four-shot renders of the stopped 1 s capture and the weevil with the base
# engine (e09d0593f, old check) and the new one. Capture folders are read only; caches,
# warp maps and outputs stay under $OUT.
#   sh run-gate.sh <out dir> <base exe> <new exe>
set -u
OUT=$1
BASE=$2
NEW=$3
ONE=D:/StrehlCaptures/stack-1795478933629-8651
QUARTER=D:/StrehlCaptures/stack-1795476520452-8651
WEEVIL=D:/StrehlCaptures/stack-1795460665629-8651
mkdir -p "$OUT/reports" "$OUT/renders"
export STREHL_GROUP_JOURNAL=off
export STREHL_CACHE_DIR="$OUT/cache-reports"
[ -n "${SKIP_REPORTS:-}" ] || "$NEW" pixel-shift "$ONE" --all-groups --json "$OUT/reports/one-s-all.json" > "$OUT/reports/one-s-all.txt" 2>&1; echo "exit $?" >> "$OUT/reports/one-s-all.txt"
[ -n "${SKIP_REPORTS:-}" ] || "$NEW" pixel-shift "$QUARTER" --all-groups --json "$OUT/reports/quarter-all.json" > "$OUT/reports/quarter-all.txt" 2>&1; echo "exit $?" >> "$OUT/reports/quarter-all.txt"
[ -n "${SKIP_REPORTS:-}" ] || "$NEW" pixel-shift "$ONE" --json "$OUT/reports/one-s.json" > "$OUT/reports/one-s.txt" 2>&1; echo "exit $?" >> "$OUT/reports/one-s.txt"
[ -n "${SKIP_REPORTS:-}" ] || "$NEW" pixel-shift "$WEEVIL" --json "$OUT/reports/weevil.json" > "$OUT/reports/weevil.txt" 2>&1; echo "exit $?" >> "$OUT/reports/weevil.txt"
export STREHL_PIXEL_SHIFT=remosaic
for arm in base new; do
  if [ "$arm" = base ]; then EXE=$BASE; else EXE=$NEW; fi
  for run in one-s weevil; do
    if [ "$run" = one-s ]; then DIR=$ONE; else DIR=$WEEVIL; fi
    R="$OUT/renders/$arm-$run"
    mkdir -p "$R" "$OUT/cache-$arm"
    export STREHL_CACHE_DIR="$OUT/cache-$arm"
    # Rule 45 asks for STREHL_WARPMAP, but `strehl align` solves every RAW of a
    # four-shot capture (380 here) while the stack aligns one frame per plane, so
    # its map is refused. Each arm solves its own map instead, cached only in its
    # private STREHL_CACHE_DIR (`align_cmd::sidecar_path` is under `cache_root`;
    # nothing is written to the capture folder).
    unset STREHL_WARPMAP
    start=$(date +%s)
    "$EXE" stack "$DIR" --merge pyramid --srgb --out "$R/result.tiff" > "$R/render.log" 2>&1
    echo "exit $? seconds $(( $(date +%s) - start ))" >> "$R/render.log"
  done
done
echo done > "$OUT/gate-done.txt"
