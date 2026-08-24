# M98 -- renders for the "where IS the softness" measurement (D3).
#
# The aligner's fit_to_cover scales the field of view by k <= 1 while keeping
# the output dimensions, so a registered render is UPSAMPLED by 1/k through a
# resampler.  On bee-3-cpl k = 0.9227, i.e. 8.4% of magnification applied by
# interpolation.  That is a global softness source and it is NEW tonight.
#
# It cannot be read off a pixel-space metric, because magnification reads as
# sharpness (discipline 606).  It CAN be read off a millimetre ruler, whose
# tick pitch is known a priori: convert the equivalent blur to OBJECT space
# (per mm) and the magnification divides out.
#
# Two renders, same gate, same frames.  Only registration differs.
#   ALN : registration on   (loads the existing warpmap.txt sidecar)
#   A0  : STREHL_ALIGN=0    (no warp, no zoom, native scale)
#
# D:\personal\macro is READ-ONLY.  flat-on-ruler-cpl already carries a solved
# warpmap.txt, so load_or_solve LOADS and never writes; STREHL_ALIGN=0 does not
# reach the sidecar at all.  The listing is asserted before and after.

$ErrorActionPreference = 'Continue'   # strehl writes its banner to stderr;
                                      # 'Stop' turns that into a terminating
                                      # error before the render even starts.
$exe = 'C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m98\release\strehl.exe'
$src = 'D:\personal\macro\flat-on-ruler-cpl'
$out = 'C:\dev\strehl-out\M98\renders'
$log = 'C:\dev\strehl-out\M98\logs'
New-Item -ItemType Directory -Force -Path $out, $log | Out-Null

$before = Get-ChildItem -Force -Recurse $src |
    ForEach-Object { "$($_.FullName)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)" } |
    Sort-Object

foreach ($g in @('0', '4')) {
    foreach ($arm in @('ALN', 'A0')) {
        if ($arm -eq 'A0') { $env:STREHL_ALIGN = '0' }
        else { Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue }
        $tif = Join-Path $out "flat-on-ruler-cpl-RS-$arm-g$g.tif"
        $lg = Join-Path $log "flat-on-ruler-cpl-RS-$arm-g$g.log"
        if (Test-Path $tif) { Write-Host "skip $tif"; continue }
        Write-Host "render $arm gate $g"
        & $exe stack $src --gate $g -o $tif 2>&1 | Out-File -FilePath $lg -Encoding utf8
        if ($LASTEXITCODE -ne 0) { throw "render failed: $arm g$g" }
    }
}
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue

$after = Get-ChildItem -Force -Recurse $src |
    ForEach-Object { "$($_.FullName)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)" } |
    Sort-Object
if (Compare-Object $before $after) {
    throw 'READ-ONLY VIOLATION: D:\personal\macro\flat-on-ruler-cpl changed'
}
Write-Host "READ-ONLY assertion PASSED: $($before.Count) entries identical (name, size, mtime)"
