# M111 cache-contamination control -- ORCH fact 1446.
#
# fact 1446: `StackIdentity` keys the frame set but NOT `reference` and NOT
# `resampler`, so an identical command line can be served bytes produced under a
# different solve configuration depending on what ran earlier in the tree. Every
# M111 measurement arm rendered BEFORE M97's fix landed (69f7b4c, 13:41); the
# arms are timestamped 13:12-13:32. So the question is live for this milestone
# and cannot be answered by pointing at the fix.
#
# ORCH's prescribed control is: run the arm, run an unrelated command that
# changes `reference` or `resampler`, re-run the arm, compare hashes. That
# prescription is NOT run literally here, for the reason M109 recorded: `strehl
# align` writes sidecars, and `D:\personal\macro` is strictly read-only. This
# substitutes a perturbation that reproduces fact 1446's exact EFFECT without
# writing anywhere near the corpus -- a sidecar that passes every identity check
# strehl makes (same stack name, digest, frame count, plane) and places the
# frames 2.0 plane px differently. That is precisely what a foreign-`reference`
# cache entry is: an accepted map with different warps.
#
# The four arms, and what each could have killed:
#
#   A0 BASELINE   pinned warpmap, empty cache
#                 -> must reproduce the reported render DB7BAAD2...
#   A1 RED        warpmap := POISON
#                 -> must DIFFER from A0. If it does not, the poison is inert
#                    and every green verdict below is vacuous (discipline 722).
#   A2 GREEN      pinned warpmap, cache dir holds the POISON under the key the
#                 pre-fix binary computes
#                 -> must EQUAL A0. This is the claim: STREHL_WARPMAP wins over
#                    the cache, so a poisoned cache could not have moved M111's
#                    bytes.
#   A3 EXPOSURE   warpmap UNSET, same poisoned cache
#                 -> must DIFFER from A0. This proves the poisoned entry is
#                    reachable on this code path at this filename -- without it,
#                    A2's green could mean "the cache file was never found".
#
# A2 and A3 together are the load-bearing pair: the same poisoned cache is
# invisible with the override and decisive without it.
#
# Exit-code note (AGENTS.md rule 47): this script never reads $LASTEXITCODE
# after a filtering pipeline. It compares SHA-256 literals, not predicates.

$ErrorActionPreference = "Continue"

$Root     = "C:\dev\strehl-out\M111"
$Exe      = "$Root\.cargo-target\release\strehl.exe"     # the pre-fix binary that produced the arms
$Stack    = "D:\personal\macro\dry-erase-marker-head-cpl"
$Pinned   = "$Root\marker-warpmap.txt"
$Ctl      = "$Root\cachectl"
$Poison   = "$Ctl\marker-POISON.warpmap.txt"
$EmptyDir = "$Ctl\cache-empty"
$PoisonD  = "$Ctl\cache-poisoned"

# The pre-fix cache key is hash(canonicalize(dir)) alone, so this filename is
# stable and is the one observed in the real cache at 11:53.
$CacheLeaf = "dry-erase-marker-head-cpl-57fff568a7ede183.warpmap.txt"

$Reported = "DB7BAAD2FDC5BF74309B132D0DDEB1A681609037312E76923C2B22703BA1DDDC"

New-Item -ItemType Directory -Force -Path $EmptyDir, $PoisonD | Out-Null
Remove-Item (Join-Path $EmptyDir "*") -Force -EA SilentlyContinue
Copy-Item $Poison (Join-Path $PoisonD $CacheLeaf) -Force

function Invoke-Arm {
    param([string]$Label, [string]$WarpMap, [string]$CacheDir)

    foreach ($v in "STREHL_ALIGN", "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA",
                   "STREHL_DUMP_ELECTION", "STREHL_DUMP_MERGE_STATE",
                   "STREHL_M111_REG_RADIUS", "STREHL_SMOOTH", "STREHL_SMOOTH_HUBER") {
        Remove-Item "Env:\$v" -EA SilentlyContinue
    }
    if ($WarpMap) { $env:STREHL_WARPMAP = $WarpMap }
    else { Remove-Item Env:\STREHL_WARPMAP -EA SilentlyContinue }
    $env:STREHL_CACHE_DIR = $CacheDir

    $tif = "$Ctl\arm.tif"
    Remove-Item $tif -Force -EA SilentlyContinue
    $t0  = Get-Date
    $log = & $Exe stack $Stack --srgb --auto-exposure --gate 4 --out $tif 2>&1 | Out-String -Width 220
    $secs = [int]((Get-Date) - $t0).TotalSeconds

    $mode = "NONE"
    $m = [regex]::Match($log, 'alignment\s*:\s*ON \(([^)]+)\), reference frame (\d+)')
    if ($m.Success) { $mode = "$($m.Groups[1].Value) ref=$($m.Groups[2].Value)" }
    elseif ($log -match 'alignment\s*:\s*([^\r\n]*)') { $mode = $Matches[1].Trim() }

    $sha = "MISSING"
    if (Test-Path $tif) { $sha = (Get-FileHash $tif -Algorithm SHA256).Hash }

    Set-Content -Path "$Ctl\$Label.log" -Value $log -Encoding utf8
    [pscustomobject]@{ Label = $Label; Sha = $sha; Align = $mode; Seconds = $secs }
}

Write-Output "M111 cache-contamination control (fact 1446)"
Write-Output "binary   : $Exe  mtime=$((Get-Item $Exe).LastWriteTime)"
Write-Output "pinned   : $Pinned  sha=$((Get-FileHash $Pinned -Algorithm SHA256).Hash.Substring(0,16))"
Write-Output "poison   : $Poison  sha=$((Get-FileHash $Poison -Algorithm SHA256).Hash.Substring(0,16))"
Write-Output ""

$a0 = Invoke-Arm -Label "A0-baseline" -WarpMap $Pinned -CacheDir $EmptyDir
$a1 = Invoke-Arm -Label "A1-red"      -WarpMap $Poison -CacheDir $EmptyDir
$a2 = Invoke-Arm -Label "A2-green"    -WarpMap $Pinned -CacheDir $PoisonD
$a3 = Invoke-Arm -Label "A3-exposure" -WarpMap ""      -CacheDir $PoisonD

foreach ($a in @($a0, $a1, $a2, $a3)) {
    Write-Output ("{0,-12} {1}  [{2}]  {3}s" -f $a.Label, $a.Sha, $a.Align, $a.Seconds)
}
Write-Output ""

$verdicts = @()
if ($a0.Sha -eq $Reported) { $verdicts += "PASS A0 reproduces the reported render" }
else { $verdicts += "FAIL A0 does not reproduce the reported render ($Reported)" }

if ($a1.Sha -ne $a0.Sha) { $verdicts += "PASS A1 red: the poison moves the bytes, so the substitution is live" }
else { $verdicts += "FAIL A1 red: poison is INERT -- every green below is vacuous" }

if ($a3.Sha -ne $a0.Sha) { $verdicts += "PASS A3 exposure: the poisoned cache entry is reachable without the override" }
else { $verdicts += "FAIL A3 exposure: the cache entry was never read -- A2 proves nothing" }

if ($a2.Sha -eq $a0.Sha) { $verdicts += "PASS A2 green: STREHL_WARPMAP wins over a poisoned cache" }
else { $verdicts += "FAIL A2 green: CONTAMINATED -- the cache changed the bytes despite the override" }

$verdicts | ForEach-Object { Write-Output "  $_" }
Write-Output ""

$bad = @($verdicts | Where-Object { $_.StartsWith("FAIL") })
if ($bad.Count -eq 0) {
    Write-Output "RESULT: marker arms are CACHE-INDEPENDENT; the control could have fired and did not"
} else {
    Write-Output "RESULT: $($bad.Count) FAILING -- see above"
}

# D:\personal\macro is strictly read-only. Prove this control did not write there.
$stray = Get-ChildItem $Stack -Recurse -File | Where-Object { $_.Extension -ne ".ARW" }
if ($stray) { $stray | ForEach-Object { Write-Output "*** WROTE INTO READ-ONLY CORPUS: $($_.FullName)" } }
else { Write-Output "read-only corpus: CLEAN, 0 non-ARW files" }
