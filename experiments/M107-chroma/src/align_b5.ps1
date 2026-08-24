# M107 bar B5 -- the no-CPL, achromatic, opposite-sweep control.
#
# Every stack in ORCH-gallery3 was shot through the Breakthrough X4 CPL and,
# per e5_sweep.py, all three were racked the SAME direction (decreasing
# magnification, Pearson r <= -0.99).  A shared sign across those three is
# therefore expected under BOTH the optical hypothesis and an instrumental
# artefact, and discriminates neither.
#
# wrapped-text-1 was shot WITHOUT the CPL on an achromatic black-on-white
# subject.  It gives (i) a CPL control and (ii), if it happens to be racked the
# other way, the sign-flip test that no CPL stack can provide.
#
# Rule 45: STREHL_WARPMAP is our own sidecar, outside the capture library.
# Rule 46: exit code captured in its own statement, never through a pipeline.
# The binary is the one that produced ORCH-gallery3 and is NOT rebuilt.

$ErrorActionPreference = "Continue"
$exe = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-orch\release\strehl.exe"
$out = "C:\dev\strehl-out\M107-chroma\renders"
$log = Join-Path $out "align-b5.log"
New-Item -ItemType Directory -Force -Path $out | Out-Null
"M107 B5 align -- $(Get-Date -Format o)" | Set-Content $log
"binary sha256: $((Get-FileHash $exe -Algorithm SHA256).Hash)" | Add-Content $log

foreach ($s in @("wrapped-text-1", "coffee-bean")) {
    $dir  = "D:\personal\macro\$s"
    if (-not (Test-Path $dir)) { "MISSING $dir" | Add-Content $log; continue }
    $side = Join-Path $out "$s-warpmap.txt"
    $env:STREHL_WARPMAP = $side

    "" | Add-Content $log
    "=== align $s ===" | Add-Content $log
    $o = & $exe align $dir --out $side 2>&1
    $code = $LASTEXITCODE
    $o | Add-Content $log
    "EXIT $code" | Add-Content $log
    Write-Host "$s align -> exit $code"

    $env:STREHL_WARPMAP = $null
}
"finished $(Get-Date -Format o)" | Add-Content $log
