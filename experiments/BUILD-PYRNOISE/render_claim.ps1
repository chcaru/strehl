# render_claim.ps1 -- reproduce the README's leaf-2-cpl claim on the PINNED binary.
#
# The claim was measured at commit 925d03d with `.cargo-target-orch\release\strehl.exe`.
# Cross-build comparison is void in this project, so rather than measure the old
# renders against anything new, the claim is RE-RUN here on the pinned shipping
# binary with thesis_demo.py's exact argv. Everything downstream is then one build.
#
# Three arms:
#   gate0      -- the claim's selection arm, argv copied exactly
#   gate2      -- the claim's estimation arm, argv copied exactly
#   gate2_neff -- gate2 again PLUS --n-eff-map. The help says that flag "does not
#                 change the merged image by a byte"; this arm exists so that
#                 sentence is CHECKED rather than believed, by requiring the two
#                 gate2 TIFFs to be bit-identical. If they differ, the n_eff map
#                 is not describing the arm that was measured and is discarded.
#
# Note the INFERENCE TRAP, deliberately preserved: the claim passes --gate without
# --merge, so the backend is INFERRED. The banner is captured for every arm and it
# is the banner, not this argv, that records which backend ran.

$ErrorActionPreference = 'Stop'
$EXE = 'C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe'
$WANT = 'CF33AE080F438C6473034EC5078D0AB4C0AA9B53421747A3F765008DDDF0D6E6'
$SRC = 'D:\personal\macro\leaf-2-cpl'
$DST = 'C:\dev\strehl-out\BUILD-PYRNOISE\claim'

$got = (Get-FileHash $EXE -Algorithm SHA256).Hash
if ($got -ne $WANT) { throw "BINARY MISMATCH: $got" }
Write-Host "binary sha256 OK: $got"
New-Item -ItemType Directory -Force -Path $DST | Out-Null

function Invoke-Arm {
    param([string]$Tag, [string[]]$ArgList)
    $out = Join-Path $DST "$Tag.tif"
    $err = Join-Path $DST "$Tag.err"
    if (Test-Path $out) { Write-Host "  [skip] $Tag (exists)"; return }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $EXE -ArgumentList $ArgList -NoNewWindow -Wait -PassThru `
        -RedirectStandardError $err -RedirectStandardOutput (Join-Path $DST "$Tag.out")
    $banner = (Select-String -Path $err -Pattern '^merge backend' | Select-Object -First 1).Line
    Write-Host ("  [{0,3}] {1,-12} {2,7:N1}s   {3}" -f $p.ExitCode, $Tag, $sw.Elapsed.TotalSeconds, $banner)
    if ($p.ExitCode -ne 0) { Get-Content $err -Tail 20 | Write-Host }
}

Write-Host "`n== leaf-2-cpl : the README claim's own arms, on the pinned binary =="
Invoke-Arm 'gate0' @('stack', $SRC, '--out', "$DST\gate0.tif", '--srgb', '--exposure=3.19', '--gate', '0')
Invoke-Arm 'gate2' @('stack', $SRC, '--out', "$DST\gate2.tif", '--srgb', '--exposure=3.19', '--gate', '2')
Invoke-Arm 'gate2_neff' @('stack', $SRC, '--out', "$DST\gate2_neff.tif", '--srgb', '--exposure=3.19',
    '--gate', '2', '--n-eff-map', "$DST\neff.tif")

Write-Host "`n-- n-eff-map purity null: the two gate2 TIFFs must be bit-identical --"
$a = (Get-FileHash "$DST\gate2.tif" -Algorithm SHA256).Hash
$b = (Get-FileHash "$DST\gate2_neff.tif" -Algorithm SHA256).Hash
Write-Host "  gate2      $a"
Write-Host "  gate2_neff $b"
Write-Host $(if ($a -eq $b) { "  PASS -- --n-eff-map did not perturb the merge" }
             else { "  FAIL -- the n_eff map does NOT describe the measured arm" })
Write-Host "`ndone: $DST"
