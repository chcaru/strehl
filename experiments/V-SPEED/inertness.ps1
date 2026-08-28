# Does the STREHL_HULL change alter output when the variable is UNSET?
#
# ORCH asked this directly and the stakes are "every master we re-render".
# Commission arm B already proved unset == explicit `input-range` byte for
# byte, but that is not the question. The question is whether the CURRENT code
# with the variable unset matches the code BEFORE the env var existed. Those
# differ: arm B proves the routing is self-consistent, not that the default was
# preserved across the commit.
#
# The only honest way to answer it is to build both commits and compare a real
# render. Two DETACHED worktrees are used so the shared working tree -- which
# nine other agents are writing to -- is never checked out or modified.
#
# `git diff --stat 6341a7a4~1 6341a7a4 -- '*.rs'` shows pyramid.rs is the only
# compiled file that differs, so any byte difference between the two renders is
# attributable to this change and nothing else.

param(
    [string]$Src = "D:\personal\macro\109MSDCF",
    [string]$Out = "D:\strehl-out\V-SPEED-HALO\inertness",
    [string]$WtParent = "D:\strehl-out\V-SPEED-HALO\wt-parent",
    [string]$WtMine = "D:\strehl-out\V-SPEED-HALO\wt-mine"
)

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

function Build($wt, $tag) {
    $tgt = "D:\strehl-out\V-SPEED-HALO\tgt-$tag"
    Write-Host "building $tag from $wt ..."
    Push-Location $wt
    & cargo build --release --bin strehl --target-dir $tgt *> "$Out\build-$tag.log"
    $rc = $LASTEXITCODE
    Pop-Location
    $bin = "$tgt\release\strehl.exe"
    if ($rc -ne 0 -or -not (Test-Path $bin)) {
        Write-Host "  BUILD FAILED rc=$rc -- see $Out\build-$tag.log"
        return $null
    }
    Write-Host ("  ok  sha256 {0}" -f (Get-FileHash $bin -Algorithm SHA256).Hash)
    return $bin
}

function Render($bin, $tag) {
    $dst = "$Out\$tag.tiff"
    if (Test-Path $dst) { Remove-Item $dst -Force }
    # STREHL_HULL deliberately NOT set. This is the shipping configuration.
    Remove-Item Env:STREHL_HULL -ErrorAction SilentlyContinue
    & $bin stack $Src --out $dst --srgb *> "$Out\render-$tag.log"
    $rc = $LASTEXITCODE
    if ($rc -ne 0 -or -not (Test-Path $dst)) {
        Write-Host "  RENDER FAILED rc=$rc"
        return $null
    }
    $h = (Get-FileHash $dst -Algorithm SHA256).Hash
    Write-Host ("  {0,-8} {1}  ({2:N1} MB)" -f $tag, $h, ((Get-Item $dst).Length / 1MB))
    return $h
}

# A FILE HASH IS THE WRONG INSTRUMENT FOR A CROSS-COMMIT COMPARISON, and this
# script read FAIL on one before it was fixed. The TIFF writer stamps the git
# hash into the header, so `parent` and `mine` differ at byte offset 3375 while
# 0 of 98,898,048 samples differ. Comparing pixels is the only comparison that
# answers the question asked. The determinism control below still uses a file
# hash, and legitimately: it compares two renders from the SAME binary, so the
# metadata is identical and any byte difference would be real.
function PixelsDiffer($p, $q) {
    & python -u "$PSScriptRoot\pixdiff.py" $p $q *> "$Out\pixdiff.log"
    return ($LASTEXITCODE -ne 0)
}

Write-Output "STREHL_HULL inertness check -- is the default preserved across the commit?"
Write-Output "source : $Src"
Write-Output "recipe : stack --srgb  (no --auto-exposure; faithful corpus recipe)"
Write-Output "env    : STREHL_HULL UNSET in both arms`n"

$binP = Build $WtParent "parent"
$binM = Build $WtMine "mine"
if (-not $binP -or -not $binM) { Write-Output "`nABORT: a build failed."; exit 2 }

Write-Output "`nrendering (STREHL_HULL unset in both) ..."
$hP = Render $binP "parent"
$hM = Render $binM "mine"
if (-not $hP -or -not $hM) { Write-Output "`nABORT: a render failed."; exit 2 }

# Same-binary repeat. Without this, "parent == mine" could mean the change is
# inert OR that the renderer is nondeterministic and both hashes are noise
# that happened to collide -- which they could not, but the control costs one
# render and removes the objection entirely.
Write-Output "`nstability control (same binary, second run) ..."
$hM2 = Render $binM "mine2"

Write-Output ""
$det = ($hM -eq $hM2)
Write-Output ("[{0}] CONTROL: renderer is deterministic (mine run1 == mine run2)" -f $(if ($det) { "PASS" } else { "FAIL" }))
$inert = -not (PixelsDiffer "$Out\parent.tiff" "$Out\mine.tiff")
Write-Output ("[{0}] RESULT : unset output is PIXEL-identical across the commit" -f $(if ($inert) { "PASS" } else { "FAIL" }))
Get-Content "$Out\pixdiff.log" | Where-Object { $_ -match 'samples|VERDICT|first byte' } | ForEach-Object { "         $_" }
Write-Output "         (file hashes differ only in the embedded git version:)"
Write-Output "         parent $hP"
Write-Output "         mine   $hM"

if (-not $det) {
    Write-Output "`nINCONCLUSIVE: renderer not deterministic, so equality proves nothing."
    exit 2
}
if ($inert) {
    Write-Output "`nSTREHL_HULL is PIXEL-INERT when unset. The commit does not change any"
    Write-Output "master rendered without the variable. Measured, not reasoned."
    exit 0
}
Write-Output "`nALERT: the change ALTERS OUTPUT when unset. ORCH must be told tonight."
exit 1


