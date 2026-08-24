# M97: independently re-measure M100's byte-freeze at current HEAD.
#
# The orchestrator asked me to confirm a default render still hashes
# 54A5E20F...7E7A2. Their OWN control script committed in 925d03d
# (experiments/ORCH-drift-check/freeze_control.ps1) already records a different
# value, CF266004..., and hypothesises the freeze was broken not by M100 but by
# M86c wiring alignment into `strehl stack` by default.
#
# Nobody has run the test that discriminates those two, so:
#
#   A  default render                      -> which hash?
#   B  default render, STREHL_ALIGN=0      -> if this recovers 54A5E20F, the
#                                             cause is alignment-on-by-default
#                                             and M100 is exonerated outright
#   C  --srgb  vs  --srgb --exposure 0     -> B2, binned path
#   D  --srgb --demosaic  vs + --exposure 0-> B2, demosaiced path
#
# C and D are M100's round-trip identity: an explicit zero must be bit-identical
# to not passing the flag at all.
#
# Everything is written to C:\dev\strehl-out\M97\. The capture corpus is
# READ-ONLY and is only ever read from.

$ErrorActionPreference = "Continue"
$exe  = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir  = "D:\personal\macro\bee-3-cpl"
$out  = "C:\dev\strehl-out\M97\freeze"
$FROZEN = "54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2"
$ORCH   = "CF266004EB1EE57A82E17038F3B6C9B497C4975CD8C5A7C5AB1748122A94B868"

New-Item -ItemType Directory -Force -Path $out | Out-Null
$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\M97\cache"

function Render($tag, $extra) {
    $f = "$out\$tag.tif"
    if (Test-Path $f) { Remove-Item $f -Force }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $cmd = @($dir, "--gate", "2", "--limit", "60", "--out", $f) + $extra
    & $exe stack @cmd 2>&1 | Out-Null
    $sw.Stop()
    if (-not (Test-Path $f)) { return @{ tag=$tag; hash="NO-OUTPUT"; s=0 } }
    return @{ tag=$tag; hash=(Get-FileHash $f -Algorithm SHA256).Hash;
              s=[math]::Round($sw.Elapsed.TotalSeconds,1) }
}

$res = @{}

Write-Output "=== A: default (measurement path), alignment as shipped ==="
$env:STREHL_ALIGN = $null
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
$res.A = Render "A-default" @()
Write-Output "  $($res.A.hash)  ($($res.A.s)s)"

Write-Output "=== B: default with STREHL_ALIGN=0 (alignment off) ==="
$env:STREHL_ALIGN = "0"
$res.B = Render "B-noalign" @()
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
Write-Output "  $($res.B.hash)  ($($res.B.s)s)"

Write-Output "=== C: --srgb  vs  --srgb --exposure 0  (binned) ==="
$res.C1 = Render "C1-srgb"    @("--srgb")
$res.C2 = Render "C2-srgb-e0" @("--srgb", "--exposure", "0")
Write-Output "  plain      : $($res.C1.hash)"
Write-Output "  --exposure 0: $($res.C2.hash)"

Write-Output "=== D: --srgb --demosaic  vs  + --exposure 0 ==="
$res.D1 = Render "D1-dem"    @("--srgb", "--demosaic")
$res.D2 = Render "D2-dem-e0" @("--srgb", "--demosaic", "--exposure", "0")
Write-Output "  plain      : $($res.D1.hash)"
Write-Output "  --exposure 0: $($res.D2.hash)"

Write-Output ""
Write-Output "=== VERDICT ==="
Write-Output "A default            = $($res.A.hash)"
Write-Output "  vs M100 frozen     : $(if($res.A.hash -eq $FROZEN){'MATCH'}else{'DIFFERS'})"
Write-Output "  vs orch control    : $(if($res.A.hash -eq $ORCH){'MATCH'}else{'DIFFERS'})"
Write-Output "B STREHL_ALIGN=0     = $($res.B.hash)"
Write-Output "  vs M100 frozen     : $(if($res.B.hash -eq $FROZEN){'MATCH -- cause is alignment-by-default'}else{'DIFFERS'})"
Write-Output "C binned round trip  : $(if($res.C1.hash -eq $res.C2.hash){'PASS (bit-identical)'}else{'FAIL'})"
Write-Output "D demosaic round trip: $(if($res.D1.hash -eq $res.D2.hash){'PASS (bit-identical)'}else{'FAIL'})"
Write-Output "A vs B differ        : $(if($res.A.hash -ne $res.B.hash){'yes -- alignment does change the default output'}else{'NO -- alignment is inert here, which would be its own defect'})"

$res | ConvertTo-Json -Depth 4 | Set-Content "$out\freeze.json"
Write-Output ""
Write-Output "wrote $out\freeze.json"
