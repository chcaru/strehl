#!/bin/sh
# Plan X7 gate 1 (X4): captures without highlight groups render byte-identically.
#   sh identity-gate.sh <out dir> <base exe> <new exe>
# Weevil and scarab four-shot captures, each arm with its own private cache.
set -u
OUT=$1
BASE=$2
NEW=$3
HERE=$(dirname "$0")
WEEVIL=D:/StrehlCaptures/stack-1795460665629-8651
SCARAB=D:/StrehlCaptures/stack-1795300522964-6430
for run in weevil scarab; do
  if [ "$run" = weevil ]; then DIR=$WEEVIL; else DIR=$SCARAB; fi
  for arm in base new; do
    if [ "$arm" = base ]; then EXE=$BASE; else EXE=$NEW; fi
    STREHL_CACHE_DIR="$OUT/cache-$arm" sh "$HERE/render.sh" "$EXE" "$DIR" "$OUT/id-$arm-$run"
  done
done
echo done > "$OUT/identity-done.txt"
