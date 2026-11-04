#!/usr/bin/env bash
# usage: ca2pass.sh NAME SRC WARP  -- pass 1 shipped CA, measure output residual, pass 2 corrected.
set -u
name=$1; src=$2; warp=$3; S=D:/codex-work/tgt-exp/release/strehl.exe
out=/d/codex-work/ca/$name; mkdir -p $out; cd $out; w=$(cygpath -m $out)
if [ ! -f p1-lin.tif ]; then STREHL_WARPMAP=$warp $S stack $src -o $w/p1.tif --srgb --linear-master $w/p1-lin.tif > p1.log 2>&1 || { echo "$name p1 FAILED"; exit 1; }; fi
python /d/codex-work/loca/chanshift.py $w/p1-lin.tif > p1.shift
read rtx rty rs < <(grep "^R: t =" p1.shift | sed -E 's/R: t = \(([-+0-9.]+),([-+0-9.]+)\) px, scale ([-+0-9.]+) ppm.*/\1 \2 \3/')
read btx bty bs < <(grep "^B: t =" p1.shift | sed -E 's/B: t = \(([-+0-9.]+),([-+0-9.]+)\) px, scale ([-+0-9.]+) ppm.*/\1 \2 \3/')
ov=$(python -c "print(f'{-508.4e-6+$rs*1e-6:.4e},{$rtx},{$rty},{174.4e-6+$bs*1e-6:.4e},{$btx},{$bty}')")
echo "$name override $ov" > p2.params
rm -f p2.tif p2-lin.tif
STREHL_CA_OVERRIDE=$ov STREHL_WARPMAP=$warp $S stack $src -o $w/p2.tif --srgb --linear-master $w/p2-lin.tif > p2.log 2>&1 || { echo "$name p2 FAILED"; exit 1; }
python /d/codex-work/loca/chanshift.py $w/p2-lin.tif > p2.shift
echo "== $name: $ov"; grep -E "^(R|B): t" p1.shift | sed 's/^/  p1 /'; grep -E "^(R|B): t" p2.shift | sed 's/^/  p2 /'
python /d/codex-work/loca/fringe.py $w/p1-lin.tif $w/p2-lin.tif | sed 's/^/  /'
