#!/bin/sh
# One four-shot render for the X4 gates: sh render.sh <exe> <capture> <out dir> [VAR=value ...]
# The cache (warp maps) is private to the out dir's parent; the group journal is off so
# each arm measures its own groups; the capture folder is only read.
set -u
EXE=$1
DIR=$2
OUT=$3
shift 3
mkdir -p "$OUT"
export STREHL_CACHE_DIR="${STREHL_CACHE_DIR:-$(dirname "$OUT")/cache}"
export STREHL_GROUP_JOURNAL=off
export STREHL_PIXEL_SHIFT=remosaic
export STREHL_HIGHLIGHT_REPORT="$OUT/fusion.jsonl"
rm -f "$OUT/fusion.jsonl"
for kv in "$@"; do export "$kv"; done
start=$(date +%s)
# STACK_ARGS: extra `stack` arguments (word-split), e.g. a sensor master.
# shellcheck disable=SC2086
"$EXE" stack "$DIR" --merge pyramid --srgb --out "$OUT/result.tiff" ${STACK_ARGS:-} > "$OUT/render.log" 2>&1
code=$?
echo "exit $code seconds $(( $(date +%s) - start ))" >> "$OUT/render.log"
tail -1 "$OUT/render.log"
grep -E "^highlights" "$OUT/render.log" | tail -4
