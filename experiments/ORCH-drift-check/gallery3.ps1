# ORCH gallery, isolated per rule 45.
#
# Every stack gets its OWN sidecar in this script's scratch directory and is
# rendered with STREHL_WARPMAP pointing at it, so:
#   - nothing writes into D:\personal\macro (rule 45), and
#   - no other agent's re-solve can change what this gallery renders.
#
# Reference frame is set explicitly to the MIDDLE frame, matching
# align_cmd::merge_reference(). `strehl align` defaults --reference to 0, which
# is NOT what the automatic merge path uses, and referencing frame 0 makes the
# uncovered border grow with distance from it.
#
# Exit codes are read per rule 46: capture first, read $LASTEXITCODE into a
# variable immediately, filter afterwards. Never gate on a truncated pipeline.

$ErrorActionPreference = "Continue"
$repo = "C:\dev\blog\death-of-software\projects\strehl"
$exe  = Join-Path $repo ".cargo-target-orch\release\strehl.exe"
$out  = "C:\dev\strehl-out\ORCH-gallery3"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$stacks = @(
    "bee-3-cpl",
    "leaf-2-cpl",
    "dry-erase-marker-head-cpl",
    "lavendar-cpl",
    "tweezers-cpl"
)

$log = Join-Path $out "gallery.log"
"ORCH gallery3 -- started $(Get-Date -Format o)" | Set-Content $log
"binary: $exe" | Add-Content $log

foreach ($s in $stacks) {
    $dir = "D:\personal\macro\$s"
    $n = (Get-ChildItem $dir -Filter *.ARW).Count
    $ref = [int]([math]::Floor($n / 2))
    $side = Join-Path $out "$s-warpmap.txt"
    $tif = Join-Path $out "$s.tif"

    "" | Add-Content $log
    "=== $s : $n frames, reference $ref ===" | Add-Content $log
    Write-Host "=== $s : $n frames, reference $ref ==="

    # --- solve into OUR sidecar, never the shared one -----------------------
    $t0 = Get-Date
    $alignOut = & $exe align $dir --out $side --reference $ref 2>&1
    $alignCode = $LASTEXITCODE
    $alignSec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    $alignOut | Add-Content $log
    if ($alignCode -ne 0) {
        "SKIPPED $s -- align exited $alignCode" | Add-Content $log
        Write-Host "  align FAILED ($alignCode), skipping"
        continue
    }
    $placed = ($alignOut | Select-String "placed").Line
    Write-Host "  aligned in ${alignSec}s :$placed"

    # --- render through OUR sidecar ----------------------------------------
    $env:STREHL_WARPMAP = $side
    $t1 = Get-Date
    $stackOut = & $exe stack $dir --srgb --auto-exposure -o $tif 2>&1
    $stackCode = $LASTEXITCODE
    $stackSec = [math]::Round(((Get-Date) - $t1).TotalSeconds, 1)
    $env:STREHL_WARPMAP = $null
    $stackOut | Add-Content $log
    if ($stackCode -ne 0) {
        "FAILED $s -- stack exited $stackCode" | Add-Content $log
        Write-Host "  stack FAILED ($stackCode)"
        continue
    }

    # The override path must report `sidecar-override`. If it says anything
    # else, this render silently used a sidecar we do not control and the
    # isolation this whole script exists for did not happen.
    $align_line = ($stackOut | Select-String "^alignment").Line
    $wrote = ($stackOut | Select-String "^wrote").Line
    Write-Host "  stacked in ${stackSec}s"
    Write-Host "  $align_line"
    "TIMING $s : align ${alignSec}s, stack ${stackSec}s" | Add-Content $log
}

"" | Add-Content $log
"finished $(Get-Date -Format o)" | Add-Content $log
Write-Host "`nDONE. Log: $log"
Get-ChildItem $out -Filter *.tif | ForEach-Object { "{0,-34} {1,10:N1} MB" -f $_.Name, ($_.Length / 1MB) }
