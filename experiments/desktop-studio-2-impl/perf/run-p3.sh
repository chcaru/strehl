#!/usr/bin/env bash
# P3 (Stack station, stage 1) measurements: baseline and P3 test binaries,
# interleaved so both see the same host load. Read-only on capture folders.
# Usage (from the worktree root, Git Bash):
#   experiments/desktop-studio-2-impl/perf/run-p3.sh <baseline strehl_ui test exe> <P3 strehl_ui test exe>
set -u
base="$1"
mine="$2"
label="${LABEL:-p3}"
short="${SHORT:-D:/personal/macro/insects/bug-3/107MSDCF}"
long="${LONG:-D:/personal/macro/insects/bug-7/100MSDCF}"
scratch="${SCRATCH:-C:/strehl-scratch/p3}"
repeats="${REPEATS:-3}"
out="$(dirname "$0")/$label"
mkdir -p "$out"
log="$out/run.txt"
note() { echo "$*" | tee -a "$log"; }
load() { powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average" | tr -d '\r'; }
compilers() { tasklist.exe 2>/dev/null | grep -Eic "^(cargo|rustc)\.exe"; }
run() {
  local exe="$1" filter="$2" file="$3"
  local before; before="$(load)"
  "$exe" --ignored "$filter" --nocapture --test-threads 1 > "$file" 2>&1
  local code=$?
  note "$(basename "$exe") $filter exit $code cpu load before ${before} % compilers $(compilers)"
}
echo "started $(date -Iseconds)" > "$log"
note "base $base"
note "mine $mine (build $(git rev-parse --short HEAD))"

# 1. Full-workspace paint, 130 captures, interleaved A/B.
for i in $(seq 1 "$repeats"); do
  run "$base" benchmark_finished_workspace_pointer_sweeps "$out/pointer-base-$i.txt"
  run "$mine" benchmark_finished_workspace_pointer_sweeps "$out/pointer-mine-$i.txt"
done
# 2. Long synthetic stacks (P3 only): the theater and the new parts.
for i in 1 2; do
  run "$mine" benchmark_long_stack_pointer_sweeps "$out/long-stack-$i.txt"
  run "$mine" benchmark_stack_parts_pointer_sweeps "$out/stack-parts-$i.txt"
done
# 3. Real RAWs, 299 planes, interleaved A/B (no disk derivative: unit-test default).
export STREHL_UI_BENCH_SOURCE="$short"
for i in 1 2; do
  export STREHL_UI_BENCH_REPORT="$scratch/resident-299-base-$i.json"
  run "$base" benchmark_real_stack_scrub_publication "$out/resident-299-base-$i.txt"
  export STREHL_UI_BENCH_REPORT="$scratch/resident-299-mine-$i.json"
  run "$mine" benchmark_real_stack_scrub_publication "$out/resident-299-mine-$i.txt"
done
# 4. Real RAWs, 1,444 planes (P3 only; the baseline refuses > 512), with an
#    emptied disk-derivative folder so the reopen is measured honestly.
export STREHL_UI_BENCH_SOURCE="$long"
export STREHL_UI_BENCH_CACHE="$scratch/derivatives"
for i in 1 2; do
  export STREHL_UI_BENCH_REPORT="$scratch/resident-1444-mine-$i.json"
  run "$mine" benchmark_real_stack_scrub_publication "$out/resident-1444-mine-$i.txt"
done
unset STREHL_UI_BENCH_CACHE STREHL_UI_BENCH_SOURCE STREHL_UI_BENCH_REPORT
note "finished $(date -Iseconds)"
