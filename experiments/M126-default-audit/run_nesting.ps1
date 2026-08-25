# M126 addendum -- the gate-nesting sweep and the load-bearing negative control.
#
# WHY THIS EXISTS
# ---------------
# ORCH's addendum, received after the main report was committed, made a point
# the campaign did not design for: a gate can read null for two completely
# different reasons.
#
#   (a) it ran, and the data gave it nothing to do        -- MEASURABLY USELESS
#   (b) it could not run at all, by construction          -- STRUCTURALLY INERT
#
# Both print the same number. Only (a) is evidence about promotion; (b) is
# evidence about the code. ORCH's instruction was explicit: determine which by
# READING THE CODE, not by inferring it from a null. This script is the
# empirical half of that -- the code reading is in the report.
#
# THE PRIMARY NEGATIVE CONTROL (ORCH addendum, point 2)
# -----------------------------------------------------
# STREHL_FIX_CA under STREHL_ALIGN=0 is a known-inert intervention that is not
# a no-op by construction of the metric: a real flag, really set, parsed into a
# real profile, that provably cannot change a byte because optics::active_profile
# is consumed ONLY in align_cmd.rs (324, 1317) and load_or_solve returns at the
# !align_enabled() guard before either is reached. If the metric reads anything
# but exactly zero there, the harness is broken and every other number is void.
#
# It is stronger than the campaign's P1/P2 placebos because a COMMITTED FREEZE
# ROW pins the expected bytes independently of me:
#   crates/strehl-cli/tests/byte-freezes.tsv:86
#   coffee-bean-20-gate2-unaligned
#   D99F5D82337AA2F093202D12677FBD1DE6D78A94761C0DE250020085271C76CA  49449626 B
# so NC0 is checkable against the corpus, not just against itself.
#
# THE POSITIVE CONTROLS ARE THE POINT
# -----------------------------------
# A sweep in which everything reads null is indistinguishable from a sweep in
# which the renders are all broken. NC4 and NC5 are gates I read as NOT nested
# under alignment, so they must MOVE under STREHL_ALIGN=0. If they do not, the
# nulls in NC1-NC3 mean nothing and this script has failed rather than measured.
#
# ARGV AND ENVIRONMENT are copied from the freeze harness itself
# (crates/strehl-cli/tests/byte-freeze.rs:426-440 argv, :411-415 the cleared
# set) so the record and the execution are the same object -- rule 47's point.

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$EXE  = "C:\dev\strehl-out\M126\target\release\strehl.exe"
$LIB  = "D:\personal\macro"          # READ-ONLY. Never write to D:\.
$OUT  = "C:\dev\strehl-out\M126\nesting"
$CACHE= "C:\dev\strehl-out\M126\nesting-cache"

# The freeze row's own invocation, verbatim.
$SUBJ  = "coffee-bean"
$LIMIT = "20"
$GATE  = "2.0"
$FREEZE_SHA = "D99F5D82337AA2F093202D12677FBD1DE6D78A94761C0DE250020085271C76CA"
$FREEZE_BYTES = 49449626

$CAKEY = "a7c2-fe100gm-2xtc-x4cpl"   # same profile the campaign used

New-Item -ItemType Directory -Force -Path $OUT, $CACHE | Out-Null

# Everything the freeze harness clears, plus the gates this milestone touches.
$WIPE = @(
    "STREHL_ALIGN", "STREHL_WARPMAP", "STREHL_CACHE_DIR",
    "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA",
    "STREHL_SOFT_GATE", "STREHL_FIX_CA", "STREHL_SMOOTH", "STREHL_SMOOTH_HUBER",
    "STREHL_ROBUST_ELECTION", "STREHL_PHOTOMETRIC",
    "STREHL_DUMP_NEFF", "STREHL_DUMP_ELECTION"
)

function Invoke-Arm {
    param([string]$Tag, [hashtable]$Env, [string[]]$Extra = @())

    foreach ($k in $WIPE) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    $env:STREHL_CACHE_DIR = $CACHE
    foreach ($k in $Env.Keys) { Set-Item "env:$k" $Env[$k] }

    $tif = Join-Path $OUT "$Tag.tif"
    $log = Join-Path $OUT "$Tag.log"
    $argv = @("stack", (Join-Path $LIB $SUBJ), "--limit", $LIMIT, "--gate", $GATE) +
            $Extra + @("--out", $tif)

    # NOTE: redirect with '>' -- Tee-Object piped into Select-Object truncates
    # the file it writes (rule 46's hazard, and it bit this milestone once).
    #
    # strehl writes its banner to stderr, and under $ErrorActionPreference=Stop
    # PowerShell promotes native stderr to a terminating error. Drop to Continue
    # across the call and judge the run by $LASTEXITCODE, which is what actually
    # reports failure here.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $EXE @argv > $log 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev

    foreach ($k in $Env.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }

    if ($code -ne 0) { Write-Host "  $Tag EXIT $code -- see $log" -ForegroundColor Red; return $null }

    $h = (Get-FileHash $tif -Algorithm SHA256).Hash
    $b = (Get-Item $tif).Length
    $plan = (Select-String -Path $log -Pattern "chunks of <=" | Select-Object -First 1).Line
    if ($plan) { $plan = $plan.Trim() } else { $plan = "(plan not printed)" }
    [pscustomobject]@{ tag = $Tag; sha = $h; bytes = $b; plan = $plan }
}

$rows = @()

Write-Host "`n=== block 1: nesting under STREHL_ALIGN=0 (freeze-row invocation) ===`n"

# NC0 -- the frozen baseline. Nothing but alignment off.
$rows += Invoke-Arm -Tag "NC0-alignoff"        -Env @{ STREHL_ALIGN = "0" }

# NC1 -- THE PRIMARY NEGATIVE CONTROL. Predict: identical to NC0.
$rows += Invoke-Arm -Tag "NC1-ca-alignoff"     -Env @{ STREHL_ALIGN = "0"; STREHL_FIX_CA = $CAKEY }

# NC2 -- smoothing acts at solve time; with no solve there is nothing to smooth.
#        Predict: identical to NC0. This nesting is not in M124's report.
$rows += Invoke-Arm -Tag "NC2-smooth-alignoff" -Env @{ STREHL_ALIGN = "0"; STREHL_SMOOTH = "1" }

# NC3 -- robust election. NOT nested under alignment, but at 20 frames the plan
#        is 10 chunks of <= 2, and 2 < Z_WINDOW = 5, so every frame is elected
#        with z = 0 and the gate cannot act. Predict identical, for a THIRD
#        distinct reason: window starvation, not nesting and not a data null.
$rows += Invoke-Arm -Tag "NC3-robust-alignoff" -Env @{ STREHL_ALIGN = "0"; STREHL_ROBUST_ELECTION = "soft" }

# NC4 -- POSITIVE CONTROL. The soft gate is consumed in Estimator::new during
#        pass two of the merge, nowhere near the alignment path. Predict: MOVES.
$rows += Invoke-Arm -Tag "NC4-softgate-alignoff" -Env @{ STREHL_ALIGN = "0"; STREHL_SOFT_GATE = "gaussian" }

# NC5 -- POSITIVE CONTROL. Halo runs post-merge, gated on --out which is set.
#        Predict: MOVES.
$rows += Invoke-Arm -Tag "NC5-halo-alignoff"   -Env @{ STREHL_ALIGN = "0"; STREHL_FIX_HALO = "1" }

Write-Host "`n=== block 2: does the robust gate wake up when the chunk grows? ===`n"
# chunk_len = frames.div_ceil(workers) (merge_cmd.rs:804). The gate needs
# chunk_len >= Z_WINDOW = 5. Alignment stays OFF so the ONLY thing changing
# between these two pairs is the frame count -- and therefore the chunk length.
foreach ($n in @("20", "100")) {
    $LIMIT = $n
    $rows += Invoke-Arm -Tag "NL$n-base"   -Env @{ STREHL_ALIGN = "0" }
    $rows += Invoke-Arm -Tag "NL$n-robust" -Env @{ STREHL_ALIGN = "0"; STREHL_ROBUST_ELECTION = "soft" }
}

$rows = $rows | Where-Object { $_ -ne $null }
$csv = Join-Path $OUT "nesting.csv"
$rows | Export-Csv -Path $csv -NoTypeInformation
Write-Host "`nwrote $csv"

Write-Host "`n=== results ===`n"
$rows | Format-Table -AutoSize tag, bytes, plan, @{ n = "sha16"; e = { $_.sha.Substring(0, 16) } }

$nc0 = ($rows | Where-Object { $_.tag -eq "NC0-alignoff" }).sha
Write-Host "`n--- against the committed freeze row (byte-freezes.tsv:86) ---"
Write-Host "expected : $FREEZE_SHA  ($FREEZE_BYTES bytes)"
Write-Host "NC0      : $nc0"
if ($nc0 -eq $FREEZE_SHA) {
    Write-Host "FREEZE REPRODUCES -- the corpus pins this baseline independently of me." -ForegroundColor Green
} else {
    Write-Host "NC0 DIFFERS from the frozen digest. That is a finding about the freeze," -ForegroundColor Yellow
    Write-Host "not necessarily about the gates: this binary is d5ba764, the row was" -ForegroundColor Yellow
    Write-Host "baselined at fea1a72. The within-block comparisons below are unaffected," -ForegroundColor Yellow
    Write-Host "because every arm in a block shares this same binary." -ForegroundColor Yellow
}

Write-Host "`n--- nesting verdicts (each vs its own block baseline) ---"
foreach ($r in $rows | Where-Object { $_.tag -like "NC[1-5]*" }) {
    $same = $r.sha -eq $nc0
    $what = if ($same) { "IDENTICAL to NC0 -> inert under STREHL_ALIGN=0" }
            else       { "DIFFERS from NC0 -> live under STREHL_ALIGN=0" }
    Write-Host ("{0,-24} {1}" -f $r.tag, $what)
}
foreach ($n in @("20", "100")) {
    $b = ($rows | Where-Object { $_.tag -eq "NL$n-base" }).sha
    $g = ($rows | Where-Object { $_.tag -eq "NL$n-robust" }).sha
    if ($b -and $g) {
        $what = if ($b -eq $g) { "IDENTICAL -> robust changed nothing" } else { "DIFFERS -> robust changed the image" }
        Write-Host ("limit {0,-4} robust vs base : {1}" -f $n, $what)
    }
}
