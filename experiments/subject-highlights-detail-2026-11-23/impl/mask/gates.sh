#!/bin/sh
# Plan S5 gates for the product subject mask. Outputs under C:/w/shd-mask-out/gates.
S=/c/w/shd-mask/target/release/strehl.exe
W=D:/StrehlCaptures/stack-1795460665629-8651
C=D:/StrehlCaptures/stack-1795300522964-6430
O=/c/w/shd-mask-out/gates
CMP="python /c/w/shd-mask/experiments/subject-highlights-detail-2026-11-23/impl/mask/compare.py"
P=/c/w/shd-mask-out/proto
mkdir -p $O
cd $O
run() {
  name=$1; shift
  echo "### strehl subject $* --out $name.json --mask-png $name.png"
  $S subject "$@" --out $name.json --mask-png $name.png --dump-evidence $name.bin
  echo "exit $?"
}
run weevil-c13 $W
$CMP weevil-c13 $P/weevil-e1-g3.npz --offset 32,20
run weevil-e16 $W --every 16
$CMP weevil-e16 $P/weevil-e1-g3.npz --offset 32,20
$CMP weevil-e16 $P/weevil-e16-g3.npz
run scarab-c13 $C
$CMP scarab-c13 $P/scarab-e1-g3.npz --offset 32,20
run scarab-e17 $C --every 17
$CMP scarab-e17 $P/scarab-e1-g3.npz --offset 32,20
$CMP scarab-e17 $P/scarab-e17-g3.npz
run weevil-oof $W --planes 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21
for f in $W $C; do
  echo "### capture folder unchanged: newest file mtime"
  ls -t --full-time $f | sed -n 2p
done
