# Behavioural commission of the STREHL_HULL environment variable added to
# crates/strehl-core/src/pyramid.rs.
#
# WHAT THIS HAS TO PROVE, and why each arm exists:
#
#   A. The renderer is DETERMINISTIC run to run. Without this control the
#      other two arms are uninterpretable: "unset == input-range" could be a
#      preserved default or could be two runs of a renderer that always
#      produces the same bytes for unrelated reasons, and "per-level differs"
#      could be a real behaviour change or could be run-to-run jitter. This
#      arm is the one that makes the other two mean anything.
#   B. UNSET is byte-identical to explicit `input-range`. This is the
#      default-preservation claim. If it fails, the env var changed shipping
#      behaviour merely by existing, which is a regression.
#   C. `per-level` DIFFERS from unset. This is the potency claim. An env var
#      that is accepted and silently does nothing is worse than none, because
#      every downstream measurement then reads as "the fix does not help".
#   D. An unrecognised value ABORTS. House style in strehl-core is to panic on
#      a bad env value, never to fall back silently (demosaic.rs:326,
#      merge.rs:682, pyramid.rs:708). A typo that silently renders the default
#      would make an entire measurement campaign read as a null result.
#
# Arms B, C and D are all necessary. Arm B alone is satisfied by an env var
# that is never read; arm C alone is satisfied by one that corrupts the
# default; arm D alone is satisfied by one that rejects everything.

param(
    [string]$Src = "D:\personal\macro\109MSDCF",
    [string]$Bin = "C:\dev\blog\death-of-software\projects\strehl\target-vspeed\release\strehl.exe",
    [string]$Out = "C:\dev\strehl-out\V-SPEED-HALO\hullcommission"
)

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

Write-Output "binary : $Bin"
Write-Output "sha256 : $((Get-FileHash $Bin -Algorithm SHA256).Hash)"
Write-Output "version: $(& $Bin --version)"
Write-Output "source : $Src"
Write-Output "recipe : stack --srgb   (NO --auto-exposure; matches the faithful"
Write-Output "         corpus recipe of fact 1823, which is the exposure the"
Write-Output "         masters under test were rendered at)"
Write-Output ""

function Render($tag, $hullValue) {
    $dst = Join-Path $Out "$tag.tiff"
    if (Test-Path $dst) { Remove-Item $dst -Force }
    if ($null -eq $hullValue) {
        Remove-Item Env:\STREHL_HULL -ErrorAction SilentlyContinue
    } else {
        $env:STREHL_HULL = $hullValue
    }
    $log = Join-Path $Out "$tag.log"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $Bin stack $Src --out $dst --srgb *> $log
    $rc = $LASTEXITCODE
    $sw.Stop()
    Remove-Item Env:\STREHL_HULL -ErrorAction SilentlyContinue
    $h = $null
    if (Test-Path $dst) { $h = (Get-FileHash $dst -Algorithm SHA256).Hash }
    [pscustomobject]@{
        tag = $tag; value = $hullValue; rc = $rc; sha = $h
        secs = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        bytes = $(if (Test-Path $dst) { (Get-Item $dst).Length } else { 0 })
    }
}

$rows = @()
$rows += Render "unset1"      $null
$rows += Render "unset2"      $null
$rows += Render "inputrange"  "input-range"
$rows += Render "perlevel"    "per-level"
$rows += Render "unclamped"   "unclamped"
$rows += Render "bogus"       "not-a-hull-mode"

$rows | Format-Table -AutoSize | Out-String | Write-Output

$u1 = ($rows | Where-Object tag -eq "unset1")
$u2 = ($rows | Where-Object tag -eq "unset2")
$ir = ($rows | Where-Object tag -eq "inputrange")
$pl = ($rows | Where-Object tag -eq "perlevel")
$uc = ($rows | Where-Object tag -eq "unclamped")
$bg = ($rows | Where-Object tag -eq "bogus")

$fails = @()

# A. determinism control
$detOk = ($u1.rc -eq 0) -and ($u2.rc -eq 0) -and ($u1.sha -eq $u2.sha)
if (-not $detOk) { $fails += "A determinism" }
Write-Output ("[{0}] A. renderer is deterministic (unset run 1 == unset run 2)" -f $(if ($detOk) { "PASS" } else { "FAIL" }))
Write-Output ("       run1 {0}" -f $u1.sha)
Write-Output ("       run2 {0}" -f $u2.sha)

# B. default preserved
$defOk = ($ir.rc -eq 0) -and ($ir.sha -eq $u1.sha)
if (-not $defOk) { $fails += "B default preserved" }
Write-Output ("[{0}] B. UNSET is byte-identical to explicit input-range" -f $(if ($defOk) { "PASS" } else { "FAIL" }))

# C. potency
$potOk = ($pl.rc -eq 0) -and ($pl.sha -ne $u1.sha)
if (-not $potOk) { $fails += "C per-level is potent" }
Write-Output ("[{0}] C. per-level DIFFERS from the default" -f $(if ($potOk) { "PASS" } else { "FAIL" }))
Write-Output ("       per-level {0}" -f $pl.sha)

# C2. unclamped reachable and distinct -- the positive control that the
# defect the hull exists to suppress can still be reproduced on demand.
$ucOk = ($uc.rc -eq 0) -and ($uc.sha -ne $u1.sha) -and ($uc.sha -ne $pl.sha)
if (-not $ucOk) { $fails += "C2 unclamped distinct" }
Write-Output ("[{0}] C2. unclamped is reachable and distinct from both" -f $(if ($ucOk) { "PASS" } else { "FAIL" }))
Write-Output ("       unclamped {0}" -f $uc.sha)

# D. bad value refused
$badOk = ($bg.rc -ne 0)
if (-not $badOk) { $fails += "D bad value refused" }
Write-Output ("[{0}] D. unrecognised value aborts (rc={1}, want nonzero)" -f $(if ($badOk) { "PASS" } else { "FAIL" }), $bg.rc)

Write-Output ""
if ($fails.Count -eq 0) {
    Write-Output "hull commission: 5/5 PASS"
    exit 0
} else {
    Write-Output ("hull commission: {0} FAIL -- {1}" -f $fails.Count, ($fails -join ", "))
    Write-Output "REFUSING to interpret any STREHL_HULL measurement."
    exit 1
}
