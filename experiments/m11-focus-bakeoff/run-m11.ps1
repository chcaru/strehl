# M11 -- the exact chain that produced everything in data\.
#
# Read-only with respect to C:\dev\macro and D:\macro-dark-frames.
# Usage:  $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"; .\run-m11.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$R109 = "C:\dev\macro\test\109MSDCF"
$R119 = "C:\dev\macro\test\119MSDCF"
$exe = ".\target\release\m11-focus-bakeoff.exe"

# ROIs, as chosen by the `rois` mode from measured structure.
$roi109 = @(
    "--roi", "2080,1056,256,256", "--roi-kind", "detail",
    "--roi", "2480,1040,256,256", "--roi-kind", "detail",
    "--roi", "2272,1344,256,256", "--roi-kind", "flat",
    "--roi", "1104,2064,256,256", "--roi-kind", "flat"
)
$roi119 = @(
    "--roi", "1744,1216,256,256", "--roi-kind", "detail",
    "--roi", "1728,1104,256,256", "--roi-kind", "detail",
    "--roi", "2848,1728,256,256", "--roi-kind", "flat",
    "--roi", "624,1728,256,256", "--roi-kind", "flat"
)

function Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

cargo build --release

Step "audit the read-only corpora BEFORE touching anything"
& $exe audit --out data\audit-before.txt

Step "gate 1 -- self-test (synthetic only, no RAW touched)"
& $exe selftest --out data\selftest.txt

Step "gate 2 -- reproduce M2's headline number through this code path"
& $exe xcheck $R109 --out data\xcheck-109MSDCF.txt

Step "choose ROIs by measured structure"
& $exe rois $R109 --out data\rois-109MSDCF.txt
& $exe rois $R119 --out data\rois-119MSDCF.txt

Step "noise axis N -- three matched arms per stack"
& $exe noise $R109 @roi109 --out data\noise-109MSDCF.csv
& $exe noise $R109 @roi109 --placebo    --out data\noise-109MSDCF-placebo.csv
& $exe noise $R109 @roi109 --coupled-g2 --out data\noise-109MSDCF-coupledg2.csv
& $exe noise $R119 @roi119 --out data\noise-119MSDCF.csv
& $exe noise $R119 @roi119 --placebo    --out data\noise-119MSDCF-placebo.csv
& $exe noise $R119 @roi119 --coupled-g2 --out data\noise-119MSDCF-coupledg2.csv

Step "centre-tap sensitivity fraction phi"
& $exe phi $R109 @roi109 --out data\phi-109MSDCF.csv
& $exe phi $R119 @roi119 --out data\phi-119MSDCF.csv

Step "controls for the selectivity axis"
& $exe planted $R109 @roi109 --synthetic --w-true 11 --noise-scales 0,1 `
    --widths 1,9,17 --out data\planted-109MSDCF-p0.csv
& $exe planted $R109 @roi109 --null --w-true 11 --out data\planted-109MSDCF-p2null.csv
& $exe planted $R109 --roi 2080,1056,256,256 --roi-kind detail `
    --roi 2272,1344,256,256 --roi-kind flat --flat-base --w-true 11 `
    --noise-scales 1 --out data\planted-109MSDCF-flatbase.csv

Step "selectivity axis S"
& $exe planted $R109 @roi109 --w-true 11 --widths 1,5,9,17,33 --out data\planted-109MSDCF-p1.csv
& $exe planted $R119 @roi119 --w-true 16 --widths 1,5,9,17,33 --out data\planted-119MSDCF-p1.csv

Step "sweeps"
& $exe planted $R109 @roi109 --w-true 11 --alpha 0.15,0.35,0.7,1.4 `
    --out data\planted-109MSDCF-alpha.csv
& $exe planted $R109 @roi109 --w-true 11 --noise-scales 0,0.5,1,2,4 `
    --out data\planted-109MSDCF-noisescale.csv
foreach ($t in 0, 4, 16, 32) {
    & $exe planted $R109 --roi 2080,1056,256,256 --roi-kind detail `
        --roi 2480,1040,256,256 --roi-kind detail --w-true 11 --tilt $t `
        --noise-scales 1 --widths 1,5,9,17,33 --out "data\planted-109MSDCF-tilt$t.csv"
}

Step "real-data winner stability kappa"
& $exe stability $R109 @roi109 --out data\stability-109MSDCF-inject.csv
& $exe stability $R109 @roi109 --planes --out data\stability-109MSDCF-planes.csv
& $exe stability $R119 @roi119 --out data\stability-119MSDCF-inject.csv
& $exe stability $R119 @roi119 --planes --out data\stability-119MSDCF-planes.csv

Step "cost"
& $exe cost $R109 @roi109 --out data\cost-109MSDCF.csv

Step "audit the read-only corpora AFTER"
& $exe audit --out data\audit-after.txt

Step "resolve everything against the registered rule"
python m11_analyse.py --out data\analysis.txt

Write-Host "done." -ForegroundColor Green
