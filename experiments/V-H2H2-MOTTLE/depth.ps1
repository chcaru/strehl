# V-H2H2: score the confidence exponent AT DEPTH, on a QUALIFIED subject.
#
# ORCH's instruction (correction #5, item 2): score the exponent at depth on
# bee-1-cpl (N=299) or dry-erase-marker-head-cpl (N=300), NOT on 112MSDCF or
# flower-bud-alone-cpl, because at 0.30-0.35 those two are unqualified.
#
# BUT THE QUALIFICATION CUTS BOTH WAYS, AND IT CHANGES THE CRITERION.
# I read the committed far=20 sweeps for both subjects ORCH named. On BOTH,
# every one of contrast_ms.py's bands is qualified SIGNAL -- bee's twelve fine
# sub-bands all PASS, from R=3.63 at 0.40-0.48 up to R=106.03. There is no
# qualified NOISE band anywhere in the instrument's range on these subjects.
#
# So criterion 1 -- "band-0 FLAT ratio well below 1 is a GRAIN WIN" -- cannot be
# applied here as written. Its direction is not a property of the criterion; it
# is a property of the subject. Where band 0 is noise, a large FLAT reduction is
# grain removed. Where band 0 is SIGNAL, the identical number is signal removed.
# On this subject a low FLAT ratio is DAMAGE, and I score it as damage.
#
# ============================ PRE-REGISTERED ==============================
# Recorded before the first frame is read. The mechanism I am testing is that
# `select_weight` returns 0.0 on `excess <= 0` BEFORE it consults the exponent,
# so wherever the gate has already reduced the candidate set to one frame, the
# exponent is inert by construction, for any value.
#
# P1. p_eff is near-inert at FLAT sites even at N=299: FLAT ratio >= 0.95 at
#     every strength, while EDGE contrast falls monotonically with strength.
#     No knee, same shape as N=79 on 112MSDCF.
#     FALSIFIER: FLAT ratio < 0.95 at any p_eff strength. That is a live
#     possibility and the reason this run is worth its cost -- at N=299 many
#     more frames may clear the gate in a flat region than at N=79, so the
#     candidate set may NOT collapse to one and the exponent may have real
#     authority at depth that it lacked shallow. If that happens my N=79
#     falsification does not transfer and I will say so.
#
# P2. K (ORCH's band-0 gate floor at 4x) reproduces roughly their published bee
#     numbers -- large band-0 FLAT reduction, EDGE ratios near 1.000.
#     STATED IN ADVANCE SO I CANNOT OVERCLAIM IT AFTERWARDS: that outcome does
#     NOT by itself prove ORCH destroyed signal. Band qualification is measured
#     over focus-responsive tiles across the frame; ORCH's flat sites are a
#     specific low-gradient subset, and a subject can carry strong fine signal
#     overall while its flattest tiles are genuinely featureless. What such an
#     outcome DOES establish is narrower and still worth having: the phrase "in
#     the noise band" is not available on this subject, and the deciding
#     measurement is a band qualification restricted to the low-gradient tiles,
#     which nobody has run.
# ==========================================================================
#
# One binary, hashed either side of every arm. No --auto-exposure. Output to D:
# per ORCH's redirect. clipcheck on every master before any quality verdict.

$ErrorActionPreference = "Stop"
$root   = "C:\dev\blog\death-of-software\projects\strehl"
$cli    = Join-Path $root "target-vh2h2\release\strehl.exe"
$stack  = "D:\personal\macro\bee-1-cpl"
$outdir = "D:\strehl-out\V-H2H2\depth"
New-Item -ItemType Directory -Force -Path $outdir | Out-Null

function CliSha { (Get-FileHash -Algorithm SHA256 $cli).Hash }
$sha0 = CliSha
Write-Host "binary  : $sha0"
Write-Host "version : $(& $cli --version 2>&1)"
Write-Host "subject : $stack  (N=299, boundary 0.48, EVERY contrast_ms band qualified SIGNAL)"
Write-Host "recipe  : stack --merge pyramid --srgb   (NO --auto-exposure)"
Write-Host ""

# name -> @{ sig = STREHL_PYRAMID_SIGNIFICANCE ; gfs = STREHL_GATE_FLOOR_SCALE }
$arms = [ordered]@{
    "A"     = @{ sig = $null;   gfs = $null }
    "K"     = @{ sig = $null;   gfs = "4,1,1,1,1,1,1" }
    "S100"  = @{ sig = "100";   gfs = $null }
    "S1000" = @{ sig = "1000";  gfs = $null }
}

$made = @{}; $failed = @()
foreach ($name in $arms.Keys) {
    $spec = $arms[$name]
    Remove-Item Env:\STREHL_PYRAMID_SIGNIFICANCE -ErrorAction SilentlyContinue
    Remove-Item Env:\STREHL_GATE_FLOOR_SCALE     -ErrorAction SilentlyContinue
    if ($null -ne $spec.sig) { $env:STREHL_PYRAMID_SIGNIFICANCE = $spec.sig }
    if ($null -ne $spec.gfs) { $env:STREHL_GATE_FLOOR_SCALE     = $spec.gfs }

    $out = Join-Path $outdir "$name.tif"
    Remove-Item $out -ErrorAction SilentlyContinue
    $t0 = Get-Date
    Write-Host ("-- arm {0,-6} sig={1,-5} gfs={2}" -f $name, $(if($spec.sig){$spec.sig}else{'-'}), $(if($spec.gfs){$spec.gfs}else{'-'}))

    $ErrorActionPreference = "Continue"
    $log = & $cli stack $stack --merge pyramid --srgb -o $out 2>&1 | Out-String -Width 4096
    $rc = $LASTEXITCODE
    $ErrorActionPreference = "Stop"

    if ((CliSha) -ne $sha0) { Write-Host "VOID: binary moved during arm $name"; exit 2 }
    if ($log -match 'auto-exposure applied') { Write-Host "VOID: arm $name carried an auto gain"; exit 2 }
    if ($rc -ne 0 -or -not (Test-Path $out)) {
        Write-Host "   FAILED rc=$rc"
        ($log -split "`n" | Select-Object -Last 10) | ForEach-Object { Write-Host "      $_" }
        $failed += $name
        continue
    }
    Write-Host ("   ok  {0:N0}s" -f ((Get-Date) - $t0).TotalSeconds)
    $made[$name] = $out
}

Write-Host ""
Write-Host "PARTITION  rendered $($made.Count) / $($arms.Count)   failed $($failed.Count)"
if ($failed.Count) { Write-Host "  FAILED: $($failed -join ', ')"; exit 1 }

Write-Host ""
python (Join-Path $root "experiments\V-H2H2-MOTTLE\clipcheck2.py") @($made.Values)

foreach ($name in @("K","S100","S1000")) {
    Write-Host ""
    Write-Host ("=== {0} vs A  on bee-1-cpl N=299 {1}" -f $name, ("=" * 34))
    python (Join-Path $root "experiments\ORCH-drift-check\contrast_ms.py") $made["A"] $made[$name]
}
