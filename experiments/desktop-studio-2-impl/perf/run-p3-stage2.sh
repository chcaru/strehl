#!/usr/bin/env bash
# P3 stage 2 measurements: the composed Stack station against the P0 baseline.
# Baseline and P3 test binaries run interleaved; host load is logged per run.
# Read-only on capture folders and on the real render's log.
# Usage (Git Bash, from the worktree root):
#   experiments/desktop-studio-2-impl/perf/run-p3-stage2.sh <baseline exe> <P3 exe> [real render.log]
set -u
base="$1"
mine="$2"
real_log="${3:-}"
out="$(dirname "$0")/p3-stage2"
scratch="${SCRATCH:-C:/strehl-scratch/p3s2}"
mkdir -p "$out"
log="$out/run.txt"
note() { echo "$*" | tee -a "$log"; }
load() { powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average" | tr -d '\r'; }
compilers() { tasklist.exe 2>/dev/null | grep -Eic "^(cargo|rustc)\.exe"; }
run() {
  local exe="$1" filter="$2" file="$3"
  local before; before="$(load)"
  "$exe" --ignored "$filter" --nocapture --test-threads 1 > "$file" 2>&1
  note "$(basename "$exe") $filter exit $? cpu load before ${before} % compilers $(compilers)"
}
echo "started $(date -Iseconds)" > "$log"
note "base $base"
note "mine $mine (build $(git rev-parse --short HEAD))"
for i in 1 2 3; do
  run "$base" benchmark_finished_workspace_pointer_sweeps "$out/process-base-$i.txt"
  run "$mine" benchmark_finished_workspace_pointer_sweeps "$out/process-mine-$i.txt"
done
for i in 1 2; do
  run "$mine" benchmark_stack_station_pointer_sweeps "$out/station-$i.txt"
  run "$mine" benchmark_long_stack_pointer_sweeps "$out/theater-long-$i.txt"
done
if [ -n "$real_log" ]; then
  export STREHL_UI_BENCH_RUN_LOG="$real_log"
  run "$mine" benchmark_stack_station_pointer_sweeps "$out/station-real.txt"
  unset STREHL_UI_BENCH_RUN_LOG
fi
export STREHL_UI_BENCH_SOURCE="D:/personal/macro/insects/bug-3/107MSDCF"
for i in 1 2; do
  export STREHL_UI_BENCH_REPORT="$scratch/resident-299-base-$i.json"
  run "$base" benchmark_real_stack_scrub_publication "$out/resident-299-base-$i.txt"
  export STREHL_UI_BENCH_REPORT="$scratch/resident-299-mine-$i.json"
  run "$mine" benchmark_real_stack_scrub_publication "$out/resident-299-mine-$i.txt"
done
export STREHL_UI_BENCH_SOURCE="D:/personal/macro/insects/bug-7/100MSDCF"
export STREHL_UI_BENCH_CACHE="$scratch/derivatives"
export STREHL_UI_BENCH_REPORT="$scratch/resident-1444-mine.json"
run "$mine" benchmark_real_stack_scrub_publication "$out/resident-1444-mine.txt"
unset STREHL_UI_BENCH_CACHE STREHL_UI_BENCH_SOURCE STREHL_UI_BENCH_REPORT
note "finished $(date -Iseconds)"
