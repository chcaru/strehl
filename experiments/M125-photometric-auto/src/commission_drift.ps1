# M125 -- commission the Rust drift estimator against M24's published numbers.
#
# The bar, inherited from M122 and not relaxed: reproduce M24's published
# peak-to-peak figures to within +-0.004 percentage points.
#
# M24 sampled `sorted(glob)[::sub][:40]`. The Rust merge consumes a prefix
# (`--limit N`), so the three stacks M24 read at sub=1 are directly
# reproducible; the two it read at sub=2 and sub=3 are not reachable through
# the shipped CLI and are reported as such rather than fudged.
#
# Nothing is written to D:\.

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M125\bin\strehl-m125.exe"
$ROOT = "C:\dev\strehl-out\M125"
$LIB  = "D:\personal\macro"

# stack, frames M24 used at sub=1, M24's published p2p, whether reachable
$plan = @(
    @{ s = "109MSDCF";       lim = 40;  pub = 0.91; note = "M24 sub=1 nmax=40 -> all 22 frames" },
    @{ s = "119MSDCF";       lim = 40;  pub = 2.88; note = "M24 sub=1 nmax=40 -> all 33 frames" },
    @{ s = "coffee-bubbles"; lim = 40;  pub = 8.93; note = "M24 sub=1 nmax=40 -> all 19 frames" }
)

function Clear-StrehlEnv {
    foreach ($v in @("STREHL_WARPMAP","STREHL_ALIGN","STREHL_PHOTOMETRIC","STREHL_SOFT_GATE",
                     "STREHL_FIX_CA","STREHL_FIX_HALO","STREHL_SMOOTH","STREHL_DUMP_NEFF",
                     "STREHL_CACHE_DIR","STREHL_RESAMPLER","STREHL_DUMP_ELECTION")) {
        Remove-Item "env:$v" -ErrorAction SilentlyContinue
    }
}

$rows = @()
foreach ($p in $plan) {
    $dir = Join-Path $LIB $p.s
    Write-Output "==================== $($p.s) ===================="

    Clear-StrehlEnv
    $env:STREHL_CACHE_DIR = Join-Path $ROOT "cache"
    $wp = Join-Path $ROOT "warp\$($p.s)-l$($p.lim).txt"
    if (-not (Test-Path $wp)) {
        $ErrorActionPreference = "Continue"
        $null = & $EXE align $dir --limit $p.lim --out $wp 2>&1
        $ac = $LASTEXITCODE
        $ErrorActionPreference = "Stop"
        if ($ac -ne 0) { throw "$($p.s) align exit $ac" }
    }

    Clear-StrehlEnv
    $env:STREHL_WARPMAP = $wp
    $ErrorActionPreference = "Continue"
    $out  = & $EXE stack $dir --limit $p.lim --gate 4 --photometric auto 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = "Stop"

    $text = ($out | ForEach-Object { "$_" }) -join "`n"
    Set-Content -Path (Join-Path $ROOT "logs\commission-$($p.s).log") -Value $text

    $m = [regex]::Match($text, 'measured drift\s*:\s*([0-9.]+)% peak-to-peak over (\d+) frame')
    if (-not $m.Success) {
        Write-Output "  NO DRIFT LINE (exit $code)"
        $rows += [pscustomobject]@{ stack = $p.s; frames = 0; published = $p.pub
                                    measured = [double]::NaN; delta = [double]::NaN
                                    within = $false; note = $p.note; exit = $code }
        continue
    }
    $val = [double]$m.Groups[1].Value
    $nf  = [int]$m.Groups[2].Value
    $d   = $val - $p.pub
    $ok  = [Math]::Abs($d) -le 0.004
    Write-Output ("  frames {0}  M24 {1:N2}%  rust {2:N4}%  delta {3:+0.0000;-0.0000}  {4}" -f `
                  $nf, $p.pub, $val, $d, $(if ($ok) { "WITHIN +-0.004" } else { "OUTSIDE +-0.004" }))
    $dec = [regex]::Match($text, 'AUTO: (APPLIED|DECLINED|ABSTAINED)\s*(.*)')
    if ($dec.Success) { Write-Output ("  decision: " + $dec.Groups[1].Value + " " + $dec.Groups[2].Value.Substring(0, [Math]::Min(90, $dec.Groups[2].Value.Length))) }

    $rows += [pscustomobject]@{ stack = $p.s; frames = $nf; published = $p.pub
                                measured = $val; delta = $d; within = $ok
                                note = $p.note; exit = $code
                                decision = $(if ($dec.Success) { $dec.Groups[1].Value } else { "" }) }
}

Clear-StrehlEnv
$rows | Export-Csv -NoTypeInformation -Path (Join-Path $ROOT "commission-drift.csv")
Write-Output ""
Write-Output "COMMISSIONING: $(($rows | Where-Object within).Count) of $($rows.Count) within +-0.004 pp"
Write-Output "COMMISSION-DONE"
