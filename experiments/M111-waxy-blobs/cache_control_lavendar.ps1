# M111 cache-contamination control, arm 2 -- the EXPOSED stack.
#
# The marker arms all logged `alignment: ON (sidecar-override)`: STREHL_WARPMAP
# was pinned, so `align_cmd::load_or_solve` -- the function fact 1446 poisons --
# was never called. cache_control.ps1 proves that structurally.
#
# The two `lavendar-cpl` generality arms did NOT. They logged `(sidecar)`, which
# is the cache path, and they ran at 13:31 and 13:32 on the pre-fix binary. They
# are exactly the case ORCH's warning describes and they must be tested, not
# argued about.
#
# The test is the sharpest one available: force a fresh solve into an empty
# cache directory and compare it, byte for byte, against the entry the arms
# actually consumed. A cache entry that equals a fresh solve cannot have carried
# a foreign `reference` or `resampler` into the render, whatever the key omitted.
#
#   L0  existing cache  -> must reproduce the hash the generality arm reported
#   L1  empty cache     -> forced fresh solve; writes a new sidecar
#   compare  L1's sidecar vs the entry L0 used, and L1's render vs L0's
#
# The liveness of this control is inherited: cache_control.ps1's A3 arm proved
# that a poisoned entry on this exact code path changes the output hash. So a
# match here is a measurement, not a silence.
#
# Exit-code note (AGENTS.md rule 47): compares SHA-256 literals, never
# $LASTEXITCODE after a filtering pipeline.

$ErrorActionPreference = "Continue"

$Root     = "C:\dev\strehl-out\M111"
$Exe      = "$Root\.cargo-target\release\strehl.exe"
$Stack    = "D:\personal\macro\lavendar-cpl"
$Ctl      = "$Root\cachectl"
$FreshDir = "$Ctl\cache-lav-fresh"
$RealCache = "$env:LOCALAPPDATA\strehl\warpmaps"
$RealLeaf  = "lavendar-cpl-47e596c1cc69bdfc.warpmap.txt"

# The hash the generality arm reported, recorded at render time.
$Reported = (Get-FileHash "$Root\render\lavendar-g4.tif" -Algorithm SHA256).Hash

New-Item -ItemType Directory -Force -Path $FreshDir | Out-Null
Remove-Item (Join-Path $FreshDir "*") -Force -Recurse -EA SilentlyContinue

function Invoke-Lav {
    param([string]$Label, [string]$CacheDir)

    foreach ($v in "STREHL_ALIGN", "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA",
                   "STREHL_DUMP_ELECTION", "STREHL_DUMP_MERGE_STATE",
                   "STREHL_M111_REG_RADIUS", "STREHL_SMOOTH", "STREHL_SMOOTH_HUBER",
                   "STREHL_WARPMAP") {
        Remove-Item "Env:\$v" -EA SilentlyContinue
    }
    $env:STREHL_CACHE_DIR = $CacheDir

    $tif = "$Ctl\lav-$Label.tif"
    Remove-Item $tif -Force -EA SilentlyContinue
    $t0  = Get-Date
    $log = & $Exe stack $Stack --srgb --auto-exposure --gate 4 --out $tif 2>&1 | Out-String -Width 220
    $secs = [int]((Get-Date) - $t0).TotalSeconds

    $mode = "NONE"
    $m = [regex]::Match($log, 'alignment\s*:\s*([^\r\n]*)')
    if ($m.Success) { $mode = $m.Groups[1].Value.Trim() }

    $sha = "MISSING"
    if (Test-Path $tif) { $sha = (Get-FileHash $tif -Algorithm SHA256).Hash }

    Set-Content -Path "$Ctl\lav-$Label.log" -Value $log -Encoding utf8
    [pscustomobject]@{ Label = $Label; Sha = $sha; Align = $mode; Seconds = $secs }
}

Write-Output "M111 cache control, arm 2: lavendar-cpl (the arm that used the cache)"
Write-Output "reported generality-arm hash: $Reported"
Write-Output ""

$l0 = Invoke-Lav -Label "L0-cached" -CacheDir $RealCache
$l1 = Invoke-Lav -Label "L1-fresh"  -CacheDir $FreshDir

foreach ($a in @($l0, $l1)) {
    Write-Output ("{0,-10} {1}  [{2}]  {3}s" -f $a.Label, $a.Sha, $a.Align, $a.Seconds)
}
Write-Output ""

$verdicts = @()
if ($l0.Sha -eq $Reported) { $verdicts += "PASS L0 reproduces the generality arm's render" }
else { $verdicts += "FAIL L0 does not reproduce the generality arm's render" }

if ($l1.Align -match "solved") { $verdicts += "PASS L1 genuinely re-solved (log says '$($l1.Align)')" }
else { $verdicts += "FAIL L1 did not re-solve -- the perturbation is inert, log says '$($l1.Align)'" }

if ($l1.Sha -eq $l0.Sha) { $verdicts += "PASS L1 == L0: a fresh solve renders the same bytes as the cached entry" }
else { $verdicts += "FAIL L1 != L0: CONTAMINATED -- the cached entry was not what a fresh solve produces" }

$fresh = Get-ChildItem $FreshDir -File -Filter "*.warpmap.txt" -EA SilentlyContinue | Select-Object -Last 1
$real  = Join-Path $RealCache $RealLeaf
if ($fresh -and (Test-Path $real)) {
    $hf = (Get-FileHash $fresh.FullName -Algorithm SHA256).Hash
    $hr = (Get-FileHash $real -Algorithm SHA256).Hash
    Write-Output "fresh sidecar : $($fresh.Name)"
    Write-Output "   $hf"
    Write-Output "cached sidecar: $RealLeaf"
    Write-Output "   $hr"
    if ($hf -eq $hr) { $verdicts += "PASS sidecar bytes identical: the cached entry IS a fresh solve at this config" }
    else { $verdicts += "NOTE sidecar bytes differ -- compare headers below before concluding" }
    Write-Output ""
    Write-Output "--- fresh header ---"
    Get-Content $fresh.FullName -TotalCount 12 | Select-Object -Skip 4 | ForEach-Object { "    $_" }
    Write-Output "--- cached header ---"
    Get-Content $real -TotalCount 12 | Select-Object -Skip 4 | ForEach-Object { "    $_" }
} else {
    $verdicts += "FAIL could not locate one of the two sidecars to compare"
}

Write-Output ""
$verdicts | ForEach-Object { Write-Output "  $_" }
Write-Output ""
$bad = @($verdicts | Where-Object { $_.StartsWith("FAIL") })
if ($bad.Count -eq 0) { Write-Output "RESULT: lavendar arms CLEAN for the sequence actually executed" }
else { Write-Output "RESULT: $($bad.Count) FAILING -- see above" }

$stray = Get-ChildItem $Stack -Recurse -File | Where-Object { $_.Extension -ne ".ARW" }
if ($stray) { $stray | ForEach-Object { Write-Output "*** WROTE INTO READ-ONLY CORPUS: $($_.FullName)" } }
else { Write-Output "read-only corpus: CLEAN, 0 non-ARW files" }
