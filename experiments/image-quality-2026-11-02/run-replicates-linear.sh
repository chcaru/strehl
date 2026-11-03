#!/usr/bin/env bash
# Like run-replicates.sh, but both arms are given explicitly and the replicates
# are scene-linear masters, so neither arm's SDR tone anchors enter the scores.
# usage: run-replicates-linear.sh CAPTURE_DIR OUT_DIR "ARM_A_ENV" "ARM_A_FLAGS" "ARM_B_ENV" "ARM_B_FLAGS"
set -euo pipefail
src="$1"; out="$2"; aenv="$3"; aflags="$4"; benv="$5"; bflags="$6"
S=/c/dev/blog/death-of-software/projects/strehl/target/release/strehl.exe
E=/c/dev/blog/death-of-software/projects/strehl/experiments/image-quality-2026-11-02
mkdir -p "$out"; cd "$out"
w="$(cygpath -m "$out")"
[ -f warp.txt ] || "$S" align "$src" --out "$w/warp.txt" > align.log 2>&1
export STREHL_WARPMAP="$w/warp.txt"
for par in even odd; do
  for arm in a b; do
    [ "$arm" = a ] && { e="$aenv"; f="$aflags"; } || { e="$benv"; f="$bflags"; }
    [ -f "L$arm-$par.tif" ] || env $e STREHL_FRAME_PARITY=$par "$S" stack "$src" -o "$w/s$arm-$par.tif" --srgb --linear-master "$w/L$arm-$par.tif" $f > "L$arm-$par.log" 2>&1
    rm -f "s$arm-$par.tif"
  done
done
echo "== $src  A: $aenv $aflags  B: $benv $bflags"
python -I "$E/replicates.py" La-even.tif La-odd.tif Lb-even.tif Lb-odd.tif
