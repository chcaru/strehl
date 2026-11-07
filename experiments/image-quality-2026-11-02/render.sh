#!/usr/bin/env bash
# Align a capture folder once (into OUT_DIR, never into the capture) and render
# it with the current release binary plus optional environment assignments.
# usage: render.sh CAPTURE_DIR OUT_DIR NAME ["ENV=VAL ..."] [extra stack flags...]
set -euo pipefail
src="$1"; out="$2"; name="$3"; envs="${4:-}"; shift 4 || shift $#
S=/c/dev/blog/death-of-software/projects/strehl/target/release/strehl.exe
mkdir -p "$out"; cd "$out"
w="$(cygpath -m "$out")"
[ -f warp.txt ] || "$S" align "$src" --out "$w/warp.txt" > align.log 2>&1
env STREHL_WARPMAP="$w/warp.txt" $envs "$S" stack "$src" -o "$w/$name.tif" --srgb "$@" > "$name.log" 2>&1
echo "$name exit $? -> $w/$name.tif"
