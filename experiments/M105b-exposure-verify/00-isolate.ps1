# 00-isolate.ps1 -- recreate the isolated stack copies the other scripts consume.
#
# WHY THIS EXISTS. `strehl stack` writes a `warpmap.txt` sidecar into its own
# INPUT directory (`align_cmd.rs`, `load_or_solve` -> `map.save(&side)`; already
# recorded as SYNTHESIS fact 1296 / discipline 623). `D:\personal\macro` is
# read-only by POLICY, not by permission, so the write succeeds and silently
# mutates the corpus. Every render in this experiment therefore runs against a
# copy under `C:\`, and this script makes the copies.
#
# `merge_cmd.rs` defines `STREHL_WARPMAP` which redirects that sidecar and would
# have made the copying unnecessary. I went to the file that performs the write
# and missed the override, which lives in a different file. Copying 25 GB is the
# expensive way to get the same isolation; it is left as-written because that is
# what the committed numbers were produced from, and re-running under
# STREHL_WARPMAP would not reproduce the same conditions without a fresh check.
#
# 03-sidecar.py needs   iso60               (60 frames of bee-3-cpl)
# 04-percentile.py, discarded arm, needs
#                       iso-coffee-bean     (60)   iso-foam (60)
# 04-percentile.py, full-depth arm, needs
#                       isofull-bee-3-cpl   (299)  isofull-coffee-bean (105)
#                       isofull-foam        (100)
#
# ~25.6 GB. Sources are READ-ONLY and are only ever read here.

$ErrorActionPreference = "Stop"
$OUT = "C:\dev\strehl-out\M105"
$SRC = "D:\personal\macro"

# name, source stack, frame count (n = -1 means the whole stack)
$jobs = @(
    @("iso60",               "bee-3-cpl",   60),
    @("iso-coffee-bean",     "coffee-bean", 60),
    @("iso-foam",            "foam",        60),
    @("isofull-bee-3-cpl",   "bee-3-cpl",   -1),
    @("isofull-coffee-bean", "coffee-bean", -1),
    @("isofull-foam",        "foam",        -1)
)

foreach ($j in $jobs) {
    $dst = Join-Path $OUT $j[0]
    # NOT $src: PowerShell variable names are case-insensitive, so $src and $SRC
    # are one variable and the first iteration would clobber the root path.
    $stackDir = Join-Path $SRC $j[1]
    if (-not (Test-Path $stackDir)) { throw "source stack missing: $stackDir" }
    New-Item -ItemType Directory -Force -Path $dst | Out-Null

    # Sorted by name, because main.rs `raw_paths` sorts by filename so that
    # frame index is capture order -- taking the first n here must select the
    # same frames `--limit n` would.
    $frames = Get-ChildItem -Force $stackDir -Filter *.ARW | Sort-Object Name
    if ($j[2] -ge 0) { $frames = $frames | Select-Object -First $j[2] }

    $have = (Get-ChildItem -Force $dst -Filter *.ARW -ErrorAction SilentlyContinue).Count
    if ($have -eq $frames.Count) {
        Write-Output ("{0,-22} {1,4} frames  already present" -f $j[0], $frames.Count)
        continue
    }

    foreach ($f in $frames) { Copy-Item -Force $f.FullName (Join-Path $dst $f.Name) }
    Write-Output ("{0,-22} {1,4} frames  copied from {2}" -f $j[0], $frames.Count, $stackDir)
}

Write-Output ""
Write-Output "NOTE: the copies carry no warpmap.txt, so the first render against"
Write-Output "each is a COLD solve. 03-sidecar.py depends on that and will report"
Write-Output "INSTRUMENT BROKEN if a stale sidecar is present."
