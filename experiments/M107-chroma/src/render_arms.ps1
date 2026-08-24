# M107 arm ladder: render each stack through three output paths, holding the
# solve, the reference, the election and the binary FIXED.
#
# The three arms isolate the stages a chroma defect could live in:
#   linear : default no-flag byte-frozen path -- binned, camera-native linear,
#            NO demosaic, NO colour matrix, NO sRGB curve, NO cosite correction.
#   binned : --srgb --binned -- adds the matrix, the curve and M95's COSITE_SHIFT.
#   (the demosaic arm already exists as ORCH-gallery3/<stack>.tif)
#
# Rule 45: STREHL_WARPMAP points at OUR OWN COPY of the gallery sidecar, so no
# other agent's re-solve can move it and nothing writes into D:\personal\macro.
# Rule 46: exit code captured in its own statement, never through a pipeline.
# The binary is the one that produced ORCH-gallery3 and is NOT rebuilt.

$ErrorActionPreference = "Continue"
$exe  = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-orch\release\strehl.exe"
$src  = "C:\dev\strehl-out\ORCH-gallery3"
$out  = "C:\dev\strehl-out\M107-chroma\renders"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$log = Join-Path $out "renders.log"
"M107 arm ladder -- $(Get-Date -Format o)" | Set-Content $log
"binary sha256: $((Get-FileHash $exe -Algorithm SHA256).Hash)" | Add-Content $log

foreach ($s in @("tweezers-cpl", "leaf-2-cpl", "bee-3-cpl")) {
    $dir  = "D:\personal\macro\$s"
    $side = Join-Path $out "$s-warpmap.txt"
    Copy-Item (Join-Path $src "$s-warpmap.txt") $side -Force
    $env:STREHL_WARPMAP = $side

    foreach ($arm in @("linear", "binned")) {
        $tif = Join-Path $out "$s-$arm.tif"
        if (Test-Path $tif) { "SKIP $s $arm (exists)" | Add-Content $log; continue }
        if ($arm -eq "linear") { $args = @("stack", $dir, "-o", $tif) }
        else { $args = @("stack", $dir, "--srgb", "--binned", "--auto-exposure", "-o", $tif) }

        "" | Add-Content $log
        "=== $s / $arm ===" | Add-Content $log
        $o = & $exe @args 2>&1
        $code = $LASTEXITCODE
        $o | Add-Content $log
        "EXIT $code" | Add-Content $log
        Write-Host "$s $arm -> exit $code"
    }
    $env:STREHL_WARPMAP = $null
}
"finished $(Get-Date -Format o)" | Add-Content $log
