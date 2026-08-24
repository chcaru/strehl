# M111 arm F -- the GATE sweep, the causal test of the admission axis.
#
# Arm C (mechanism.py) found admission collapsing from n_eff 275 to n_eff 1 as
# the focus response rises from 0.6 to 5, because the gate tolerance is a fixed
# 0.086063 focus units while the response is contrast-scaled and spans 0.43..84.
# If that collapse is what makes the waxy patches, then forcing the gate open
# must dissolve them and forcing it shut must maximise them -- and `--gate` is
# already a CLI flag, so this needs no code change and no uncalibrated constant.
#
# Rule 47, the whole invocation: identical to sweep_radius.ps1 except that
# --gate is the swept variable and STREHL_M111_REG_RADIUS is NOT set, so every
# arm here runs the shipping 17x17 regulariser.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$root = "C:\dev\strehl-out\M111"
$exe = "$root\.cargo-target\release\strehl.exe"
$stack = "D:\personal\macro\dry-erase-marker-head-cpl"
$out = "$root\render"

Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO_DELTA -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_DUMP_ELECTION -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_M111_REG_RADIUS -ErrorAction SilentlyContinue
$env:STREHL_WARPMAP = "$root\marker-warpmap.txt"

foreach ($g in @("0.25", "1", "4", "16", "64", "100000")) {
    $tag = "g$($g -replace '\.', 'p')"
    $dumpdir = "$out\state-$tag"
    $tif = "$out\marker-$tag.tif"
    if (Test-Path $tif) { "skip $tag"; continue }
    New-Item -ItemType Directory -Force -Path $dumpdir | Out-Null
    $env:STREHL_DUMP_MERGE_STATE = $dumpdir
    $o = & $exe stack $stack --srgb --exposure=-0.24 --gate $g --out $tif 2>&1
    $c = $LASTEXITCODE
    $o | Out-String | Set-Content -Encoding utf8 "$out\marker-$tag.log"
    if ($c -ne 0) { throw "gate $g exited $c (expected 0)" }
    $ne = ($o | Select-String "^\s+$([regex]::Escape($g))").Line
    "{0,-9} sha256={1}  {2}" -f $tag, (Get-FileHash $tif -Algorithm SHA256).Hash.Substring(0, 16), $ne.Trim()
}
Remove-Item Env:STREHL_DUMP_MERGE_STATE
"gate sweep done"
