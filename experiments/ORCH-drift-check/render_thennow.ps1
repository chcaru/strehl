# Render lavendar and dry-erase-marker at HEAD, to complete the then-vs-now
# comparison for all three stacks the owner judged on 2026-08-23 23:37-23:47.
#
# Exposure is chosen by --auto-exposure rather than by me. It is deterministic,
# it prints the --exposure=N that reproduces the file byte for byte, and it CAN
# DARKEN -- which matters here because marker.tif already clips (luma p99.9 =
# 1.0000), so the +1.54 stops used for bee-3-cpl would have made it worse. Using
# the tool's own registered rule keeps my taste out of the comparison.
#
# Rule 47: the whole invocation and environment is recorded here, in this file,
# beside the outputs. Nothing is left at "the default".
$ErrorActionPreference = "Continue"
$env:CARGO_TARGET_DIR = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-orch"
$exe = "$env:CARGO_TARGET_DIR\release\strehl.exe"
$outdir = "C:\dev\strehl-out\ORCH-thennow"
New-Item -ItemType Directory -Force -Path $outdir | Out-Null

# Environment, stated rather than assumed:
Remove-Item Env:STREHL_ALIGN     -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_WARPMAP   -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO  -ErrorAction SilentlyContinue

$head = (& git -C C:\dev\blog\death-of-software\projects\strehl rev-parse --short HEAD)
"HEAD          : $head"
"binary        : $exe"
"binary mtime  : $((Get-Item $exe).LastWriteTime)"
"STREHL_ALIGN  : (unset -> alignment ON, solved)"
"STREHL_WARPMAP: (unset -> no sidecar pin)"
"STREHL_FIX_HALO: (unset)"
""

$jobs = @(
    @{ Name = "lavendar"; Dir = "D:\personal\macro\lavendar-cpl" },
    @{ Name = "marker";   Dir = "D:\personal\macro\dry-erase-marker-head-cpl" }
)

foreach ($j in $jobs) {
    $name = $j.Name
    $dir  = $j.Dir
    $tif  = Join-Path $outdir "$name-HEAD-$head.tif"
    $log  = Join-Path $outdir "$name-HEAD-$head.log"
    $n    = (Get-ChildItem $dir -Filter *.ARW).Count

    "=== $name : $n frames from $dir ==="
    "    invocation: strehl stack `"$dir`" --srgb --auto-exposure --gate 4 --out `"$tif`""
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $out = & $exe stack $dir --srgb --auto-exposure --gate 4 --out $tif 2>&1
    $code = $LASTEXITCODE          # captured BEFORE any filtering (fact 1427)
    $sw.Stop()

    $out | Out-String | Set-Content -Encoding utf8 $log
    $out | Select-String "exposure|n_eff|wrote|alignment|Error|WARNING" | Select-Object -Last 14
    "    exit={0}  elapsed={1:N1}s" -f $code, $sw.Elapsed.TotalSeconds
    if ($code -ne 0) { "    *** FAILED, exit $code -- see $log" }
    elseif (Test-Path $tif) {
        $f = Get-Item $tif
        "    wrote {0}  {1:N0} bytes  sha256={2}" -f $f.Name, $f.Length, (Get-FileHash $tif -Algorithm SHA256).Hash
    }
    ""
}
"done"
