# M9 end-to-end reproduction. Run from experiments\m9-support\.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File run-m9.ps1
#
# Stages are numbered to match README.md. Pass -Skip <n> to start partway
# through, e.g. -Skip 4 to reuse the committed ROI files.
param([int]$Skip = 0)

$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path data | Out-Null

$S109 = 'C:\dev\macro\test\109MSDCF'
$S119 = 'C:\dev\macro\test\119MSDCF'

# ROIs from stage 3. Four flat + one detail per stack. On 109MSDCF the
# top-ranked flat block (2361,1417) is replaced by M2's 2272,1344 -- 51st of
# 22538, same flat region -- so M2's exact measurement is a row of the sweep.
$R109 = @('2272,1344,256,256','2505,441,256,256','2665,1513,256,256','329,1353,256,256','2089,1065,256,256')
$R119 = @('3065,425,256,256','2713,1673,256,256','3065,1577,256,256','649,1433,256,256','2025,1161,256,256')
$KINDS = @('flat','flat','flat','flat','detail')

function RoiArgs($rois) {
    $a = @()
    foreach ($r in $rois)  { $a += '--roi';      $a += $r }
    foreach ($k in $KINDS) { $a += '--roi-kind'; $a += $k }
    return $a
}

function Step([int]$n, [string]$what, [scriptblock]$body) {
    if ($n -lt $Skip) { Write-Host "[$n] skipped: $what"; return }
    Write-Host "`n=== [$n] $what ===" -ForegroundColor Cyan
    $t = [Diagnostics.Stopwatch]::StartNew()
    & $body
    if ($LASTEXITCODE -ne 0) { throw "[$n] $what failed with exit code $LASTEXITCODE" }
    Write-Host ("=== [$n] done in {0:N1} s ===" -f $t.Elapsed.TotalSeconds) -ForegroundColor Cyan
}

Step 0 'build' { cargo build --release }

Step 1 'self-test (the statistic before the data)' {
    cargo run --release -- selftest
}

Step 2 'reproduce M2 + cross-check the tile path against the shipped CLI' {
    cargo run --release -- xcheck $S109 --roi 2272,1344,256,256 |
        Tee-Object data\xcheck-109MSDCF.txt
}

Step 3 'choose ROIs by structure' {
    # 109MSDCF at the default margin (105); its choices were verified to fit the
    # sweep. 119MSDCF needs 169 -- its flattest blocks sit near the frame edge.
    cargo run --release -- rois $S109 --top 6 --rank 2272,1344,256,256 | Tee-Object data\rois-109MSDCF.txt
    cargo run --release -- rois $S119 --margin 169 --top 6 | Tee-Object data\rois-119MSDCF.txt
}

Step 4 'sweep: 109MSDCF coupled (the real configuration)' {
    cargo run --release -- sweep $S109 @(RoiArgs $R109) --out data\sweep-109MSDCF-coupled.csv
}

Step 5 'sweep: 109MSDCF placebo (elect on G1, evaluate on G2 -- the whole-sweep null)' {
    cargo run --release -- sweep $S109 @(RoiArgs $R109) --placebo --out data\sweep-109MSDCF-placebo.csv
}

Step 6 'sweep: 119MSDCF coupled (replication, 33 frames, ISO 50)' {
    cargo run --release -- sweep $S119 @(RoiArgs $R119) --out data\sweep-119MSDCF-coupled.csv
}

Step 7 'centre-tap sensitivity phi, measured on real frames' {
    cargo run --release -- sensitivity $S109 --out data\sensitivity-109MSDCF.csv
    cargo run --release -- sensitivity $S119 --out data\sensitivity-119MSDCF.csv
}

Step 8 'focus-field autocorrelation (supplementary)' {
    cargo run --release -- acf $S109 --roi 2272,1344,256,256 --out data\acf-109MSDCF.csv
}

Step 9 'analysis (controls print before treatments by construction)' {
    python m9_analyse.py data\sweep-109MSDCF-coupled.csv | Tee-Object data\analysis-109MSDCF-coupled.txt | Out-Null
    python m9_analyse.py data\sweep-109MSDCF-placebo.csv | Tee-Object data\analysis-109MSDCF-placebo.txt | Out-Null
    python m9_analyse.py data\sweep-119MSDCF-coupled.csv | Tee-Object data\analysis-119MSDCF-coupled.txt | Out-Null
    python m9_acf.py     data\acf-109MSDCF.csv           | Tee-Object data\analysis-acf-109MSDCF.txt   | Out-Null
    Get-Content data\analysis-109MSDCF-coupled.txt | Select-String 'VALUE OF|Spearman rho\(centre-tap|Spearman rho\(support radius,'
}

Step 10 'regression test + its negative control' {
    Push-Location ..\..
    try {
        cargo test -p strehl-core focus::tests::centre
        if ($LASTEXITCODE -ne 0) { return }
        powershell -NoProfile -ExecutionPolicy Bypass -File experiments\m9-support\negative-control.ps1 |
            Tee-Object experiments\m9-support\data\negative-control.txt
    } finally { Pop-Location }
}

Write-Host "`nM9 reproduction complete." -ForegroundColor Green
