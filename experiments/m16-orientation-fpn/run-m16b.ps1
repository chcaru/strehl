# M16 supplementary arms, added AFTER the preregistration was committed.
#
# These are declared additions, not preregistered arms. They are flagged as such
# in the report. Both were added because the preregistered H1/H2 arms turned out
# to be weaker than they looked:
#
#   A11 -- real corpus texture, SYMMETRISED: T <- (T + T_transpose)/2 on a square
#          tile. The scene is then EXACTLY invariant under transposition while
#          keeping the corpus's own contrast, inter-layer step and spatial
#          spectrum. Preregistered arm A7 used synthetic texture for the same
#          purpose and landed in a different regime (its window argmin is w4/w8,
#          not w11-w15), so it cannot carry the H2 verdict alone. A11 has no
#          regime mismatch to argue about: any asymmetry it shows is machinery.
#
#   A12 -- the same symmetrised plant with destripe-mean on top. A11's null
#          control: the treatment must not reintroduce an asymmetry.
#
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$exe = "target-aux\release\m16-orientation-fpn.exe"
if (-not (Test-Path $exe)) { throw "build target-aux first" }

$W15 = @(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 23, 26, 33, 40)
$MEAS = ($W15 | ForEach-Object { "tenengrad-w$_" }) -join ","
$WIDTHS = "1,17"
$MARGIN = 106
$SEEDS = "20260823,771117,4242424,13371337,90210"
$STEPS = "0,2,4,8,16,32"
$SHAPES = @("--shape", "vertical", "--shape", "horizontal", "--shape", "bar")

$STACKS = @(
    @("109MSDCF", "C:\dev\macro\test\109MSDCF", "2080,1056,256,256", "2480,1040,256,256"),
    @("119MSDCF", "C:\dev\macro\test\119MSDCF", "2016,1152,256,256", "2528,1152,256,256")
)

function Run-Arm {
    param([string]$Arm, [string[]]$Extra)
    foreach ($stk in $STACKS) {
        $out = "data\$Arm-$($stk[0]).csv"
        if (Test-Path $out) { Write-Host "  skip $out (exists)"; continue }
        & $exe edge $stk[1] --label $stk[0] --roi-near $stk[2] --roi-far $stk[3] `
            --frames 41 --steps $STEPS --widths $WIDTHS --margin $MARGIN `
            --seeds $SEEDS --measures $MEAS @SHAPES `
            --arm $Arm @Extra --out $out
        if ($LASTEXITCODE -ne 0) { throw "arm $Arm on $($stk[0]) failed" }
    }
}

Write-Host "== A11 symmetrised real texture, square ROI (H2: machinery-only asymmetry) =="
Run-Arm "A11" @("--symmetrise")

Write-Host "== A12 symmetrised real texture + destripe-mean (A11's null) =="
Run-Arm "A12" @("--symmetrise", "--destripe", "mean")

Write-Host "== done =="
