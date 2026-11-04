#!/usr/bin/env bash
# Align a capture folder once, then render baseline and candidate arms as
# pixel-aligned even/odd half-stack replicates plus one full render each, and
# score texture kept / noise removed / tone change.
#
# usage: run-replicates.sh CAPTURE_DIR OUT_DIR "CANDIDATE_ENV ASSIGNMENTS"
# Capture folders are only read; every output lands in OUT_DIR.
set -euo pipefail
src="$1"; out="$2"; cand="$3"
S=/c/dev/blog/death-of-software/projects/strehl/target/release/strehl.exe
E=/c/dev/blog/death-of-software/projects/strehl/experiments/image-quality-2026-11-02
mkdir -p "$out"; cd "$out"
win() { cygpath -m "$1"; }
[ -f warp.txt ] || "$S" align "$src" --out "$(win "$out")/warp.txt" > align.log 2>&1
export STREHL_WARPMAP="$(win "$out")/warp.txt"
for par in even odd; do
  [ -f rb-$par.tif ] || STREHL_PYRAMID_ENSEMBLE=0 STREHL_FRAME_PARITY=$par "$S" stack "$src" -o rb-$par.tif --srgb > rb-$par.log 2>&1
  [ -f rc-$par.tif ] || env $cand STREHL_FRAME_PARITY=$par "$S" stack "$src" -o rc-$par.tif --srgb > rc-$par.log 2>&1
done
[ -f base.tif ] || STREHL_PYRAMID_ENSEMBLE=0 "$S" stack "$src" -o base.tif --srgb > base.log 2>&1
[ -f cand.tif ] || env $cand "$S" stack "$src" -o cand.tif --srgb > cand.log 2>&1
echo "== $src  candidate: $cand"
python -I "$E/replicates.py" rb-even.tif rb-odd.tif rc-even.tif rc-odd.tif
python -I "$E/tone.py" base.tif cand.tif tone.png
python -I "$E/compare.py" base.tif cand.tif
