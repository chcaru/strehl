# M126 addendum -- the reachability probe.
#
# Reading code told me STREHL_ROBUST_ELECTION is unreachable from `strehl stack`:
# merge.rs:508 defines it, merge.rs:525 reads it inside active_arm(), and
# active_arm() has exactly one caller, FocusStats::new_robust at merge.rs:710 --
# which has NO production call site. The CLI's only FocusStats construction is
# merge_cmd.rs:1871, `FocusStats::new(geom)`, which never consults the arm.
#
# But "I read the code and concluded X" is exactly the kind of claim this
# project's corpus keeps catching out, and ORCH's addendum warned me off
# inferring reachability. So this probe tests it from OUTSIDE the binary, with
# no privileged knowledge, using the parsers' own documented refusal behaviour:
#
#   * merge.rs:1066 -- Estimator::new PANICS if SOFT_GATE_ENV names no kernel.
#     "Failing loudly is the point: a typo that silently disables the fix is
#      indistinguishable from the fix not working."
#   * merge.rs:530  -- an unknown ROBUST_ENV value "is refused rather than
#     silently" accepted; arm_from_setting returns Err(UnknownArm).
#   * optics.rs     -- profile_from_setting refuses an unknown CA profile key.
#
# So a garbage value is a REACHABILITY ORACLE. If the parser runs, the run dies.
# If the run succeeds, the parser never ran, and the variable is inert no matter
# what it is set to -- which is a far stronger statement than any null render.
#
# Predictions, written before running:
#   R1 soft gate  garbage, align on  -> FAILS   (parser is on the merge path)
#   R2 robust     garbage, align on  -> SUCCEEDS (parser is unreachable)
#   R3 CA         garbage, align on  -> FAILS   (parser is on the solve path)
#   R4 CA         garbage, align OFF -> SUCCEEDS (solve path never entered)
#
# R2 is the load-bearing one. R1 and R3 are the controls that prove a garbage
# value CAN kill a run, so R2's survival means something.

$ErrorActionPreference = "Continue"
Set-StrictMode -Version Latest

$EXE   = "C:\dev\strehl-out\M126\target\release\strehl.exe"
$LIB   = "D:\personal\macro"          # READ-ONLY. Never write to D:\.
$OUT   = "C:\dev\strehl-out\M126\reach"
$CACHE = "C:\dev\strehl-out\M126\reach-cache"
New-Item -ItemType Directory -Force -Path $OUT, $CACHE | Out-Null

$WIPE = @(
    "STREHL_ALIGN", "STREHL_WARPMAP", "STREHL_CACHE_DIR",
    "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA",
    "STREHL_SOFT_GATE", "STREHL_FIX_CA", "STREHL_SMOOTH", "STREHL_SMOOTH_HUBER",
    "STREHL_ROBUST_ELECTION", "STREHL_PHOTOMETRIC",
    "STREHL_DUMP_NEFF", "STREHL_DUMP_ELECTION"
)

function Probe {
    param([string]$Tag, [hashtable]$Env, [string]$Expect)

    foreach ($k in $WIPE) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    $env:STREHL_CACHE_DIR = $CACHE
    foreach ($k in $Env.Keys) { Set-Item "env:$k" $Env[$k] }

    $log = Join-Path $OUT "$Tag.log"
    & $EXE stack (Join-Path $LIB "coffee-bean") --limit 20 --gate 2.0 `
        --out (Join-Path $OUT "$Tag.tif") > $log 2>&1
    $code = $LASTEXITCODE

    foreach ($k in $Env.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }

    $got = if ($code -eq 0) { "SUCCEEDS" } else { "FAILS" }
    $ok  = if ($got -eq $Expect) { "as predicted" } else { "*** PREDICTION REFUTED ***" }
    $why = (Select-String -Path $log -Pattern "panic|refus|unknown|is not|error" |
            Select-Object -First 1).Line
    if ($why) { $why = $why.Trim() } else { $why = "" }
    if ($why.Length -gt 96) { $why = $why.Substring(0, 96) + "..." }

    Write-Host ("{0,-26} exit {1,-4} {2,-9} (predicted {3,-9}) {4}" -f $Tag, $code, $got, $Expect, $ok)
    if ($why) { Write-Host ("{0,-26}   -> {1}" -f "", $why) -ForegroundColor DarkGray }

    [pscustomobject]@{ tag = $Tag; exit = $code; got = $got; expect = $Expect; matched = ($got -eq $Expect); note = $why }
}

Write-Host "`n=== reachability probe: is a garbage value refused? ===`n"

$rows = @()
$rows += Probe -Tag "R1-softgate-garbage"   -Env @{ STREHL_SOFT_GATE = "banana" }                   -Expect "FAILS"
$rows += Probe -Tag "R2-robust-garbage"     -Env @{ STREHL_ROBUST_ELECTION = "banana" }             -Expect "SUCCEEDS"
$rows += Probe -Tag "R3-ca-garbage-alignon" -Env @{ STREHL_FIX_CA = "banana" }                      -Expect "FAILS"
$rows += Probe -Tag "R4-ca-garbage-alignoff" -Env @{ STREHL_FIX_CA = "banana"; STREHL_ALIGN = "0" } -Expect "SUCCEEDS"

$csv = Join-Path $OUT "reach.csv"
$rows | Export-Csv -Path $csv -NoTypeInformation
Write-Host "`nwrote $csv"

Write-Host "`n=== interpretation ==="
$r1 = ($rows | Where-Object { $_.tag -eq "R1-softgate-garbage" })
$r2 = ($rows | Where-Object { $_.tag -eq "R2-robust-garbage" })
if ($r1.got -eq "FAILS" -and $r2.got -eq "SUCCEEDS") {
    Write-Host "A garbage value CAN kill a run (R1), and STREHL_ROBUST_ELECTION's does not (R2)." -ForegroundColor Green
    Write-Host "The arm parser is never invoked by ``strehl stack``. The variable is inert by" -ForegroundColor Green
    Write-Host "construction -- not window-starved, not data-null. UNWIRED." -ForegroundColor Green
} elseif ($r2.got -eq "FAILS") {
    Write-Host "R2 failed: the parser IS reachable, so the gate is wired and my code" -ForegroundColor Yellow
    Write-Host "reading is wrong. The byte-identity would then be a genuine data null." -ForegroundColor Yellow
} else {
    Write-Host "R1 did not fail, so this probe has no power and proves nothing." -ForegroundColor Red
}
