# Sweep the shipping pyramid knobs against the halo, carrying sharpness on
# the same pixels in every arm.
#
# WHY SHARPNESS IS NOT OPTIONAL HERE. Every knob in this sweep moves the merge
# along the same axis: how hard it selects. Lower exponent, flatter ramp,
# higher gate and a mean base all move it toward an average. An average has no
# halo because it has no structure, so a sweep scored on the halo alone will
# rank the blurriest arm first and be completely confident about it. ORCH's
# standing warning, reproduced independently by the falsification lane, is
# exactly this: "on blotch alone the worst arm wins" -- a plain mean scored
# best on blotch and destroyed 78% of the sharpness.
#
# So every arm reports BOTH, and an arm only counts as a fix if it moves the
# halo without moving sharpness by more than the sharpness metric's own
# resolution.
#
# ARMS. The halo under investigation sits at 36-56 px, which is a COARSE band
# feature, so the knobs swept are the ones that reach coarse-band selection:
# the coarsest-band exponent, the per-octave ramp that sets how fast selection
# sharpens toward fine bands, the band-noise gate below which no frame wins,
# the band count, and the base-band rule. STREHL_HULL is included because the
# hull is the merge's only existing clamp on out-of-range excursion.

param(
    [string]$Subject = "tweezers-cpl",
    [string]$ArmSet = "knobs",
    [string]$Bin = "C:\dev\blog\death-of-software\projects\strehl\target-vspeed\release\strehl.exe",
    [string]$Out = "C:\dev\strehl-out\V-SPEED-HALO\sweep"
)

$ErrorActionPreference = "Continue"
$src = "D:\personal\macro\$Subject"
$dir = Join-Path $Out $Subject
New-Item -ItemType Directory -Force -Path $dir | Out-Null

if ($ArmSet -eq "knobs") {
    $arms = @(
        @{ tag = "baseline";     args = @();                            hull = $null },
        @{ tag = "exp1";         args = @("--pyramid-exponent", "1");   hull = $null },
        @{ tag = "exp4";         args = @("--pyramid-exponent", "4");   hull = $null },
        @{ tag = "sharpen1";     args = @("--pyramid-sharpen", "1.0");  hull = $null },
        @{ tag = "gate8";        args = @("--pyramid-gate", "8");       hull = $null },
        @{ tag = "bands5";       args = @("--pyramid-bands", "5");      hull = $null },
        @{ tag = "bands9";       args = @("--pyramid-bands", "9");      hull = $null },
        @{ tag = "baseweighted"; args = @("--pyramid-base", "weighted"); hull = $null },
        @{ tag = "hullperlevel"; args = @();                            hull = "per-level" }
    )
} elseif ($ArmSet -eq "depth") {
    # Is the band count response MONOTONE? The knob sweep showed 5 better than
    # 7 better than 9 on the halo, which is what coarse-band ringing predicts:
    # the coarsest band sets the scale of the ring. If that reading is right,
    # 3 and 4 should be better still -- and the CLI's own warning says they
    # must eventually cost black density, so this arm set is where the cost
    # appears if it is going to. Combos test whether the two free knobs stack.
    $arms = @(
        @{ tag = "baseline";     args = @();                            hull = $null },
        @{ tag = "bands3";       args = @("--pyramid-bands", "3");      hull = $null },
        @{ tag = "bands4";       args = @("--pyramid-bands", "4");      hull = $null },
        @{ tag = "bands6";       args = @("--pyramid-bands", "6");      hull = $null },
        @{ tag = "bands5wbase";  args = @("--pyramid-bands", "5", "--pyramid-base", "weighted"); hull = $null },
        @{ tag = "bands5exp1";   args = @("--pyramid-bands", "5", "--pyramid-exponent", "1"); hull = $null }
    )
} elseif ($ArmSet -eq "ab") {
    # Two arms only, for the corpus before/after. BOTH are rendered by THIS
    # binary. The delivered faithful masters were rendered at 5f367a94 and this
    # binary is cc985615-dirty, so scoring bands5 against a delivered master
    # would confound the flag with 13+ commits of drift plus another lane's
    # uncommitted merge_cmd.rs. The baseline arm costs a second render per
    # subject and removes that confound entirely.
    $arms = @(
        @{ tag = "baseline";     args = @();                            hull = $null },
        @{ tag = "bands5";       args = @("--pyramid-bands", "5");      hull = $null }
    )
} elseif ($ArmSet -eq "scene") {
    # THE SCENE FLOOR. --pyramid-exponent 0.001 with the per-octave ramp
    # disabled makes every band's selection weight excess^0.001, which is ~1
    # for any frame above the gate: a plain average, with the SAME frames, the
    # SAME alignment and the SAME tone pipeline as every other arm. Whatever
    # radial structure survives THAT is not selection ringing, because there
    # is no selection.
    #
    # This is the arm that says how much of a measured "halo" a merge change
    # could even in principle remove. On tweezers-cpl it reads 654.9 DN
    # against the shipping merge's 2621.7, so a quarter of that subject's halo
    # is the scene and is not addressable by any knob in this sweep.
    #
    # IT IS ALSO THE TRAP ARM. Measured on tweezers-cpl it removes 75.0% of
    # the halo and 81.4% of the sharpness -- independently reproducing ORCH's
    # warning that "on blotch alone the worst arm wins" (they measured 78% on
    # a different subject and statistic). It is a REFERENCE, never a candidate.
    $arms = @(
        @{ tag = "plainmean";    args = @("--pyramid-exponent", "0.001", "--pyramid-sharpen", "1.0"); hull = $null }
    )
} else {
    throw "unknown ArmSet '$ArmSet'"
}

Write-Output "subject: $Subject   frames: $((Get-ChildItem $src -Filter *.ARW).Count)"
Write-Output "binary : $((Get-FileHash $Bin -Algorithm SHA256).Hash)"
Write-Output "version: $(& $Bin --version)"
Write-Output "recipe : stack --srgb  (NO --auto-exposure; faithful-corpus recipe)"
Write-Output ""

foreach ($a in $arms) {
    $dst = Join-Path $dir ("{0}.tiff" -f $a.tag)
    if (Test-Path $dst) {
        Write-Output ("SKIP {0} (exists)" -f $a.tag)
        continue
    }
    Remove-Item Env:\STREHL_HULL -ErrorAction SilentlyContinue
    if ($a.hull) { $env:STREHL_HULL = $a.hull }
    $log = Join-Path $dir ("{0}.log" -f $a.tag)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $Bin stack $src --out $dst --srgb @($a.args) *> $log
    $rc = $LASTEXITCODE
    $sw.Stop()
    Remove-Item Env:\STREHL_HULL -ErrorAction SilentlyContinue
    Write-Output ("{0,-14} rc={1} {2,6:N0}s  {3}" -f $a.tag, $rc,
        $sw.Elapsed.TotalSeconds, $(if (Test-Path $dst) { "ok" } else { "NO OUTPUT" }))
}
Write-Output ""
Write-Output "renders complete in $dir"
