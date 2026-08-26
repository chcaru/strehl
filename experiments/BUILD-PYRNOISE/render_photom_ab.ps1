# render_photom_ab.ps1 -- the decisive A/B for BOTH open questions at once.
#
# QUESTION 1 (the claim). The README's leaf-2-cpl paragraph was rendered at
# commit 925d03d. `git merge-base --is-ancestor` proves the commit that wired
# photometric normalisation into the merge (27646057, "M97q: wire photometric.rs
# into the merge behind --photometric (opt-in)") is NOT an ancestor of 925d03d.
# So the claim's two arms carried the full uncorrected per-frame gain drift that
# this subject's own banner measures at `gain span 1.1010`. A selection arm is a
# mosaic of differently-scaled frames and KEEPS that spread; an estimation arm
# averages it away. That inflates an arm-vs-arm ratio, and this renders the size
# of the effect on real arms of ONE build instead of simulating it.
#
# QUESTION 2 (a discrepancy found while checking question 1). `stack --help` on
# this same pinned binary says of --photometric: "Three-valued: `off` (the
# default), `on`, or `auto`." Every estimator run made in this campaign reports
#     mode            : on (unconditional, as asked)
# with no --photometric flag on the command line and STREHL_PHOTOMETRIC unset in
# every scope. Help and banner disagree about what the shipping default is. The
# project's rule is that the banner records what the program did, so this renders
# an explicit `--photometric off` arm and compares BYTES. If the flagless render
# and the explicit-off render are bit-identical the banner is wrong; if they
# differ, the help is wrong. Either way one of them is, and it is measured here.

$ErrorActionPreference = 'Stop'
$EXE = 'C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe'
$WANT = 'CF33AE080F438C6473034EC5078D0AB4C0AA9B53421747A3F765008DDDF0D6E6'
$SRC = 'D:\personal\macro\leaf-2-cpl'
$DST = 'C:\dev\strehl-out\BUILD-PYRNOISE\claim'

$got = (Get-FileHash $EXE -Algorithm SHA256).Hash
if ($got -ne $WANT) { throw "BINARY MISMATCH: $got" }
Write-Host "binary sha256 OK: $got"
Write-Host "STREHL_PHOTOMETRIC in this process = [$env:STREHL_PHOTOMETRIC]"

function Invoke-Arm {
    param([string]$Tag, [string[]]$ArgList)
    $out = Join-Path $DST "$Tag.tif"
    $err = Join-Path $DST "$Tag.err"
    if (Test-Path $out) { Write-Host "  [skip] $Tag (exists)"; return }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $EXE -ArgumentList $ArgList -NoNewWindow -Wait -PassThru `
        -RedirectStandardError $err -RedirectStandardOutput (Join-Path $DST "$Tag.out")
    $b = (Select-String -Path $err -Pattern '^merge backend' | Select-Object -First 1).Line
    $m = (Select-String -Path $err -Pattern '^mode            :' | Select-Object -First 1)
    Write-Host ("  [{0,3}] {1,-14} {2,7:N1}s  photometric {3}" -f $p.ExitCode, $Tag,
        $sw.Elapsed.TotalSeconds, $(if ($m) { $m.Line.Split(':')[1].Trim() } else { 'SECTION ABSENT' }))
    Write-Host ("        {0}" -f $b)
    if ($p.ExitCode -ne 0) { Get-Content $err -Tail 20 | Write-Host }
}

Write-Host "`n== leaf-2-cpl, pinned binary, photometric EXPLICITLY OFF =="
Invoke-Arm 'gate0_poff' @('stack', $SRC, '--out', "$DST\gate0_poff.tif", '--srgb',
    '--exposure=3.19', '--gate', '0', '--photometric', 'off')
Invoke-Arm 'gate2_poff' @('stack', $SRC, '--out', "$DST\gate2_poff.tif", '--srgb',
    '--exposure=3.19', '--gate', '2', '--photometric', 'off', '--n-eff-map', "$DST\neff_poff.tif")

Write-Host "`n-- does the flagless default differ from an explicit --photometric off? --"
foreach ($t in @(@('gate0', 'gate0_poff'), @('gate2', 'gate2_poff'))) {
    $a = (Get-FileHash "$DST\$($t[0]).tif" -Algorithm SHA256).Hash
    $b = (Get-FileHash "$DST\$($t[1]).tif" -Algorithm SHA256).Hash
    Write-Host ("  {0,-11} {1}" -f $t[0], $a)
    Write-Host ("  {0,-11} {1}" -f $t[1], $b)
    Write-Host $(if ($a -eq $b) {
            "  IDENTICAL -- the flagless default IS off, and the banner's 'mode : on' is wrong"
        } else {
            "  DIFFERENT -- the flagless default IS on, and --help's '`off` (the default)' is wrong"
        })
}
Write-Host "`ndone: $DST"
