# M104 Phase 1 -- baseline renders at HEAD, BEFORE M95's fix.
#
# Gate 0 only.  Gate 0 takes exactly one frame per pixel, so the ONLY thing
# separating the two arms is the warp and the coverage rescale -- which is the
# operation under verification.  Adding gate would add an averaging term that
# has nothing to do with the fix.
#
#   ALN : registration on   (loads the existing warpmap.txt sidecar)
#   A0  : STREHL_ALIGN=0    (no warp, no rescale, native sampling)
#
# READ-ONLY.  Both stacks already carry a solved warpmap.txt, so load_or_solve
# LOADS and never writes; STREHL_ALIGN=0 does not reach the sidecar at all.
# Asserted by full recursive listing (name, size, mtime) before and after.
#
# PROVENANCE.  The sidecar hash is recorded.  Phase 2 must render against the
# SAME solve, or the before/after comparison is confounded by a re-solve rather
# than isolating M95's change.  A hash mismatch in Phase 2 is a stop condition.

$ErrorActionPreference = 'Continue'   # strehl banners to stderr
$exe = 'C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m98\release\strehl.exe'
$root = 'C:\dev\strehl-out\M104'
$out = Join-Path $root 'renders'
$log = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $out, $log | Out-Null

$stacks = @('flat-on-ruler-cpl', 'bee-3-cpl')
$phase = if ($args.Count -gt 0) { $args[0] } else { 'PRE' }

foreach ($s in $stacks) {
    $src = "D:\personal\macro\$s"

    $before = Get-ChildItem -Force -Recurse $src |
        ForEach-Object { "$($_.Name)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)" } |
        Sort-Object

    $side = Join-Path $src 'warpmap.txt'
    if (Test-Path $side) {
        $h = (Get-FileHash -Algorithm SHA256 $side).Hash
        "$s $h $((Get-Item $side).Length)" |
            Out-File -Append -FilePath (Join-Path $log "sidecar-$phase.txt") -Encoding utf8
        Write-Host "$s sidecar SHA256 $($h.Substring(0,16))..."
    }
    else {
        Write-Host "$s HAS NO SIDECAR -- a solve would WRITE into a read-only tree. SKIPPING."
        continue
    }

    foreach ($arm in @('ALN', 'A0')) {
        if ($arm -eq 'A0') { $env:STREHL_ALIGN = '0' }
        else { Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue }
        $tif = Join-Path $out "$s-$phase-$arm-g0.tif"
        $lg = Join-Path $log "$s-$phase-$arm-g0.log"
        if (Test-Path $tif) { Write-Host "skip $([IO.Path]::GetFileName($tif))"; continue }
        Write-Host "render $s $arm"
        & $exe stack $src --gate 0 -o $tif 2>&1 | Out-File -FilePath $lg -Encoding utf8
    }
    Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue

    $after = Get-ChildItem -Force -Recurse $src |
        ForEach-Object { "$($_.Name)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)" } |
        Sort-Object
    if (Compare-Object $before $after) {
        throw "READ-ONLY VIOLATION: $src changed"
    }
    Write-Host "READ-ONLY assertion PASSED for ${s}: $($before.Count) entries identical"
}
Write-Host "done ($phase)"
