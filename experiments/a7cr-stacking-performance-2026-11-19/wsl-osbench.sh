#!/bin/bash
set -e
. "$HOME/.cargo/env"
W=/mnt/c/dev/blog/death-of-software/projects/strehl/outputs/perf-plan-3
mkdir -p "$HOME/osb"
cd "$HOME/osb"
rustc -O -C target-cpu=x86-64-v3 "$W/osbench.rs" -o osbench 2>/dev/null
echo "== WSL2, ext4 in the distro's VHDX =="
cat /sys/kernel/mm/transparent_hugepage/enabled
./osbench "$HOME/osb" 4
echo "== WSL2, the same with transparent huge pages off for this process is not settable without root; THP state above =="
echo "== WSL2, Windows drive through 9p (/mnt/c) =="
./osbench "$W/scratch" 2 | grep -E "read|open"
