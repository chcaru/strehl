# V-H2H2: is the knob's apparent acuity cost on 112MSDCF real, or a tone artefact?
#
# WHY THIS RUN EXISTS -- a self-correction.
#
# I reported "K costs 6.9% band-1 acuity on 112MSDCF (0.9306)". Applying ORCH's
# FINAL criterion 3 strictly to my own table, that claim is not admissible:
#
#     K coarsest EDGE = 1.0061  ->  |1.0061 - 1.000| = 0.0061 > 0.005
#
# so by ORCH's own rule the arms differ GLOBALLY and the comparison is VOID.
# I cannot assert an acuity cost from a void comparison, and I withdraw the
# assertion pending this run.
#
# WHY THE NULL PROBABLY FAILED. STREHL_GATE_FLOOR_SCALE=4,1,1,1,1,1,1 touches
# BAND 0 ONLY. By construction it should not move the coarsest band at all, so
# a 0.61% coarsest-band shift is far more likely to be residual tone placement
# than a real coarse-scale change. contrast_ms.py removes the tone confound
# POST HOC, by rescaling B to A's median. That is second best: under --srgb both
# arms place white on their OWN 99.9th percentile, which is a NON-LINEAR
# remapping, and a single median scale factor cannot undo a non-linear curve.
#
# THE FIX, APPLIED AT THE SOURCE INSTEAD. --linear-srgb applies the colour
# matrix and STOPS BEFORE THE TONE CURVE, so there is no percentile-based white
# placement for the two arms to disagree about and nothing to undo afterwards.
# If the 1.0061 null was tone, it should collapse toward 1.000 here.
#
# WHAT EACH OUTCOME MEANS -- both are informative, which is why this is worth
# rendering rather than arguing:
#   null passes AND band-1 EDGE ~ 1.00  -> the 6.9% was a tone artefact. The
#                                          knob is free on 112MSDCF too, and
#                                          ORCH's bee result generalises.
#   null passes AND band-1 EDGE ~ 0.93  -> the cost is REAL and subject-
#                                          dependent, and the bee is the
#                                          exception rather than the rule.
#   null still fails                    -> not tone. Something else differs
#                                          globally and BOTH subjects need it
#                                          found before any verdict is quoted.
#
# One binary, hashed either side of every arm. No --auto-exposure anywhere.

$ErrorActionPreference = "Stop"
$root   = "C:\dev\blog\death-of-software\projects\strehl"
$cli    = Join-Path $root "target-vh2h2\release\strehl.exe"
$stack  = "D:\personal\macro\112MSDCF"
$outdir = Join-Path $env:TEMP "vh2h2-lin"
New-Item -ItemType Directory -Force -Path $outdir | Out-Null

function CliSha { (Get-FileHash -Algorithm SHA256 $cli).Hash }
$sha0 = CliSha
Write-Host "binary  : $sha0"
Write-Host "version : $(& $cli --version 2>&1)"
Write-Host "subject : $stack  (--linear-srgb --demosaic, NO tone curve, NO --auto-exposure)"
Write-Host ""

$arms = [ordered]@{ "A" = $null; "K" = "4,1,1,1,1,1,1" }
$made = @{}
$failed = @()

foreach ($name in $arms.Keys) {
    Remove-Item Env:\STREHL_GATE_FLOOR_SCALE -ErrorAction SilentlyContinue
    Remove-Item Env:\STREHL_PYRAMID_SIGNIFICANCE -ErrorAction SilentlyContinue
    if ($null -ne $arms[$name]) { $env:STREHL_GATE_FLOOR_SCALE = $arms[$name] }

    $out = Join-Path $outdir "$name.tif"
    Remove-Item $out -ErrorAction SilentlyContinue
    Write-Host ("-- arm {0}  gfs={1}" -f $name, $(if($arms[$name]){$arms[$name]}else{'-'}))

    $ErrorActionPreference = "Continue"
    $log = & $cli stack $stack --merge pyramid --linear-srgb --demosaic -o $out 2>&1 | Out-String -Width 4096
    $rc = $LASTEXITCODE
    $ErrorActionPreference = "Stop"

    if ((CliSha) -ne $sha0) { Write-Host "VOID: binary moved during arm $name"; exit 2 }
    # A tone curve or an exposure gain here would defeat the entire point.
    if ($log -match 'auto-exposure applied|--exposure=') { Write-Host "VOID: arm $name carried a gain"; exit 2 }
    if ($rc -ne 0 -or -not (Test-Path $out)) {
        Write-Host "   FAILED rc=$rc"
        ($log -split "`n" | Select-Object -Last 8) | ForEach-Object { Write-Host "      $_" }
        $failed += $name
        continue
    }
    Write-Host "   ok"
    $made[$name] = $out
}

Write-Host ""
Write-Host "PARTITION  rendered $($made.Count) / $($arms.Count)  failed $($failed.Count)"
if ($failed.Count) { Write-Host "  FAILED: $($failed -join ', ')"; exit 1 }

Write-Host ""
python (Join-Path $root "experiments\V-H2H2-MOTTLE\clipcheck2.py") $made["A"] $made["K"]
Write-Host ""
Write-Host ("=== K vs A, LINEAR (no tone curve) {0}" -f ("=" * 30))
python (Join-Path $root "experiments\ORCH-drift-check\contrast_ms.py") $made["A"] $made["K"]
