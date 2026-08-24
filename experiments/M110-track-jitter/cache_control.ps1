# Control for fact 1446: StackIdentity omits `reference` and `resampler`, so a
# cached sidecar can hand an arm bytes produced under inputs it did not ask for.
#
# M110's B6 arms name their sidecar explicitly via STREHL_WARPMAP. `alignment_for`
# (merge_cmd.rs:1046) takes the explicit path and never calls `load_or_solve`, so
# the ambient cache should not be reachable. That is an ARGUED claim about the
# code; this script MEASURES it.
#
# The intervening align uses the FULL frame set with a DIFFERENT --reference, so
# its StackIdentity is identical to the arm's. That is precisely the collision.
#
# Exit codes are asserted on the EXACT expected value (fact 1443), never on
# non-zero-ness, and every hash is recorded as a literal.

$ErrorActionPreference = "Continue"
$B       = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m110\release\strehl.exe"
$STACK   = "D:\personal\macro\bee-3-cpl"
$SCRATCH = "C:\dev\strehl-out\M110\ctl"
$ARM     = "C:\dev\strehl-out\M110\wm-B.json"
New-Item -ItemType Directory -Force -Path $SCRATCH | Out-Null

function Get-Sha($p) { (Get-FileHash $p -Algorithm SHA256).Hash }
function Align-Line($o) { (($o | Out-String) -split "`n" | Where-Object { $_ -match 'alignment\s+:' }) -join ' ' }

# Prove the capture library starts clean, so any sidecar the run drops is visible.
$before = (Get-ChildItem $STACK -File | Where-Object { $_.Extension -ne '.ARW' }).Count
"LIBRARY non-ARW files before : $before"

# ---- STEP 1: arm B, byte-identical to the B6 command line -------------------
$env:STREHL_WARPMAP = $ARM
Remove-Item "$SCRATCH\r1.tif" -ErrorAction SilentlyContinue
cmd /c exit 0
$o1 = & $B merge $STACK --out "$SCRATCH\r1.tif" 2>&1
$c1 = $LASTEXITCODE
if ($c1 -ne 0) { throw "STEP1 merge: expected exit 0, got $c1" }
$H1 = Get-Sha "$SCRATCH\r1.tif"
"STEP1 exit=$c1  hash=$H1"
"STEP1 provenance : $(Align-Line $o1)"

# ---- STEP 2: unrelated align, SAME frames, DIFFERENT reference --------------
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
cmd /c exit 0
$o2 = & $B align $STACK --reference 40 --out "$SCRATCH\wm-ref40.json" 2>&1
$c2 = $LASTEXITCODE
if ($c2 -ne 0) { throw "STEP2 align: expected exit 0, got $c2" }
"STEP2 exit=$c2  (align --reference 40, full frame set)"

# ---- STEP 3: arm B again, byte-identical to STEP 1 ---------------------------
$env:STREHL_WARPMAP = $ARM
Remove-Item "$SCRATCH\r2.tif" -ErrorAction SilentlyContinue
cmd /c exit 0
$o3 = & $B merge $STACK --out "$SCRATCH\r2.tif" 2>&1
$c3 = $LASTEXITCODE
if ($c3 -ne 0) { throw "STEP3 merge: expected exit 0, got $c3" }
$H2 = Get-Sha "$SCRATCH\r2.tif"
"STEP3 exit=$c3  hash=$H2"
"STEP3 provenance : $(Align-Line $o3)"

# ---- VERDICT ----------------------------------------------------------------
$ORIG = Get-Sha "C:\dev\strehl-out\M110\img\B-prior.tif"
"ORIGINAL B-prior.tif hash    : $ORIG"
"STEP1 == STEP3               : $($H1 -eq $H2)"
"STEP1 == ORIGINAL (B6 run)   : $($H1 -eq $ORIG)"
if ($H1 -eq $H2) { "VERDICT: CLEAN  -- the intervening reference change did not move the arm" }
else             { "VERDICT: CONTAMINATED -- B6 numbers must be re-run or reported contaminated" }

$after = (Get-ChildItem $STACK -File | Where-Object { $_.Extension -ne '.ARW' }).Count
"LIBRARY non-ARW files after  : $after"
if ($after -ne $before) { "*** WARNING: the run wrote into the read-only capture library ***" }
