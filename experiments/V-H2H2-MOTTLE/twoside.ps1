# V-H2H2: score the confidence-scaled exponent (p_eff) on ORCH's two-sided
# criterion, against ORCH's global band-0 floor knob, on ORCH's subject.
#
# THE CONTROL THAT MAKES THIS COMMENSURABLE: arm K reproduces ORCH's own
# published run (STREHL_GATE_FLOOR_SCALE=4,1,1,1,1,1,1 -> FLAT 0.2717,
# EDGE 0.9108). If K does not land near those numbers, my harness is not
# measuring what ORCH's was and NO p_eff number below is comparable to theirs.
# That check runs first and its result is printed whether it passes or fails.
#
# PREDICTION, RECORDED BEFORE THE RUN (V-H2H2 measured, coffee-bean):
#   At band 0 in flat regions, concentration = 1.0000 EXACTLY -- every frame but
#   one carries weight exactly zero. select_weight returns 0.0 on `excess <= 0`
#   BEFORE it consults the exponent, so those zeros are the GATE's doing, not
#   the weight law's. Where exactly one frame is admitted, its normalised weight
#   is 1 for ANY exponent. So p_eff is predicted to be WEAK on FLAT grain at
#   band 0, which is precisely where ORCH's floor knob is strong.
#   If the measurement contradicts this, the prediction is wrong and I say so.
#
# ORCH's knob and p_eff act at different points on the same coefficient:
#   floor scale -> changes WHICH frames are admitted (gate)
#   p_eff       -> changes how admitted frames are WEIGHTED
# A coefficient with one admitted frame is immune to the second and not the first.
#
# Every arm lands in a counted bucket; a render that fails is FAILED, never absent.

$ErrorActionPreference = "Stop"
$root   = "C:\dev\blog\death-of-software\projects\strehl"
$cli    = Join-Path $root "target-vh2h2\release\strehl.exe"
$stack  = "D:\personal\macro\112MSDCF"
$outdir = Join-Path $env:TEMP "vh2h2-2side"
New-Item -ItemType Directory -Force -Path $outdir | Out-Null

function CliSha { (Get-FileHash -Algorithm SHA256 $cli).Hash }
$sha0 = CliSha
Write-Host "binary      : $cli"
Write-Host "binary sha  : $sha0"
Write-Host "version     : $(& $cli --version 2>&1)"
Write-Host "subject     : $stack   (--srgb, NO --auto-exposure)"
Write-Host ""

# name -> @{ sig = <STREHL_PYRAMID_SIGNIFICANCE or $null>; gfs = <SCALE or $null> }
$arms = [ordered]@{
    "A"     = @{ sig = $null;   gfs = $null }
    "K"     = @{ sig = $null;   gfs = "4,1,1,1,1,1,1" }
    "S1"    = @{ sig = "1";     gfs = $null }
    "S100"  = @{ sig = "100";   gfs = $null }
    "S1000" = @{ sig = "1000";  gfs = $null }
}

$made   = @{}
$failed = @()

foreach ($name in $arms.Keys) {
    $spec = $arms[$name]
    Remove-Item Env:\STREHL_PYRAMID_SIGNIFICANCE -ErrorAction SilentlyContinue
    Remove-Item Env:\STREHL_GATE_FLOOR_SCALE     -ErrorAction SilentlyContinue
    if ($null -ne $spec.sig) { $env:STREHL_PYRAMID_SIGNIFICANCE = $spec.sig }
    if ($null -ne $spec.gfs) { $env:STREHL_GATE_FLOOR_SCALE     = $spec.gfs }

    $out = Join-Path $outdir "$name.tif"
    Remove-Item $out -ErrorAction SilentlyContinue
    $desc = "sig=$(if($spec.sig){$spec.sig}else{'-'})  gfs=$(if($spec.gfs){$spec.gfs}else{'-'})"
    Write-Host ("-- arm {0,-6} {1}" -f $name, $desc)

    $t0 = Get-Date
    $ErrorActionPreference = "Continue"
    $log = & $cli stack $stack --merge pyramid --srgb -o $out 2>&1 | Out-String -Width 4096
    $rc = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    $secs = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)

    if ((CliSha) -ne $sha0) { Write-Host "VOID: binary changed during arm $name"; exit 2 }
    if ($rc -ne 0 -or -not (Test-Path $out)) {
        Write-Host "   FAILED rc=$rc"
        ($log -split "`n" | Select-Object -Last 8) | ForEach-Object { Write-Host "      $_" }
        $failed += $name
        continue
    }

    $avg = ($log -split "`n" | Where-Object { $_ -match 'averaged' } | Select-Object -First 1)
    if ($avg) { Write-Host ("   {0}" -f $avg.Trim()) }
    Write-Host ("   ok in {0}s" -f $secs)
    $made[$name] = $out
}

Write-Host ""
Write-Host "PARTITION  rendered $($made.Count) / $($arms.Count)   failed $($failed.Count)"
if ($failed.Count) { Write-Host "  FAILED: $($failed -join ', ')" }
if (-not $made.ContainsKey("A")) { Write-Host "baseline A missing -- nothing is comparable"; exit 1 }

Write-Host ""
Write-Host "clip% (fact 1817) -- a saturated region has no structure to measure:"
python (Join-Path $root "experiments\V-H2H2-MOTTLE\clipcheck2.py") @($made.Values)

foreach ($name in $made.Keys) {
    if ($name -eq "A") { continue }
    Write-Host ""
    Write-Host ("=== {0}  vs A {1}" -f $name, ("=" * 40))
    python (Join-Path $root "experiments\ORCH-drift-check\contrast_ab.py") $made["A"] $made[$name]
}
