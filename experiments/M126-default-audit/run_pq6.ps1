# M126/PQ6 Arm R -- the real-data analogue of the FOCUS_NOISE_SD calibration.
#
# `--limit 1` is the whole trick: with N = 1 the winner is the only frame, so
# `best_focus` is that frame's regularised response with the winner's curse
# removed by construction. That is the same quantity `merge.rs:2049-2060`
# measures on synthetic normals, evaluated on real sensor data instead.
#
# `STREHL_ALIGN=0` because a single frame has nothing to register, and because a
# resample would correlate neighbouring pixels and depress the very dispersion
# being measured. Recorded as a limitation in the report: the shipped default
# has alignment ON, so the gate in production operates on resampled data.
#
# D:\ is read-only (rule 45). Everything is written under C:\dev\strehl-out.

$ErrorActionPreference = "Continue"

$BIN  = "C:\dev\strehl-out\M126\target\release\strehl.exe"
$LIB  = "D:\personal\macro"
$OUT  = "C:\dev\strehl-out\M126\pq6"
$SUBJECTS = @("bee-3-cpl", "lead-1-cpl", "leaf-2-cpl", "coffee-bean", "tweezers-cpl")

# Wipe every strehl variable so an inherited one cannot silently enter an arm.
$STREHL_VARS = @("STREHL_WARPMAP", "STREHL_ALIGN", "STREHL_PHOTOMETRIC",
                 "STREHL_FIX_CA", "STREHL_ROBUST_ELECTION", "STREHL_SMOOTH",
                 "STREHL_SOFT_GATE", "STREHL_FIX_HALO", "STREHL_CACHE_DIR",
                 "STREHL_DUMP_MERGE_STATE", "STREHL_DUMP_ELECTION")

New-Item -ItemType Directory -Force -Path $OUT | Out-Null

foreach ($S in $SUBJECTS) {
    foreach ($v in $STREHL_VARS) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }

    $dump = Join-Path $OUT "dump-$S"
    New-Item -ItemType Directory -Force -Path $dump | Out-Null

    $env:STREHL_ALIGN = "0"
    $env:STREHL_DUMP_MERGE_STATE = $dump
    # Private cache per arm (ORCH's warning 3), even though N=1 with ALIGN=0
    # never reaches a cache path.
    $env:STREHL_CACHE_DIR = Join-Path $OUT "cache-$S"

    $log = Join-Path $OUT "$S.log"
    Write-Host "[$S] rendering 1 frame ..."
    & $BIN stack (Join-Path $LIB $S) --limit 1 -o (Join-Path $OUT "$S.tif") > $log 2>&1
    Write-Host "[$S] exit=$LASTEXITCODE"
}

# Q5 placebo: repeat one subject into a separate directory. Byte-identical
# inputs must read exactly zero difference, or the harness is broken.
foreach ($v in $STREHL_VARS) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
$dump2 = Join-Path $OUT "dump-bee-3-cpl-REPEAT"
New-Item -ItemType Directory -Force -Path $dump2 | Out-Null
$env:STREHL_ALIGN = "0"
$env:STREHL_DUMP_MERGE_STATE = $dump2
$env:STREHL_CACHE_DIR = Join-Path $OUT "cache-repeat"
Write-Host "[bee-3-cpl REPEAT] rendering ..."
& $BIN stack (Join-Path $LIB "bee-3-cpl") --limit 1 -o (Join-Path $OUT "bee-3-cpl-REPEAT.tif") > (Join-Path $OUT "bee-3-cpl-REPEAT.log") 2>&1
Write-Host "[bee-3-cpl REPEAT] exit=$LASTEXITCODE"

Write-Host "done"
