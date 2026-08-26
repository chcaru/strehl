<#
.SYNOPSIS
  Render the same subjects twice from ONE binary: the shipping default merge
  and the shipping selection baseline (`argmax-baseline`).

.DESCRIPTION
  This is the A/B that closes the README's `ARGUED` detail gap. The two arms
  must differ in ONE thing only -- estimation vs selection -- so:

    * ONE binary, hashed, for both arms. Two binaries from different points in
      the tree differ by a chromatic-aberration correction that moves red by up
      to 3902 DN, which would contaminate every number.
    * BOTH ARMS LINEAR. Neither arm ever sees --srgb. A numeric comparison
      across a tone curve is not a measurement.
    * BOTH ARMS BINNED. `argmax-baseline` only writes binned 3516x2344 camera
      RGB (one output pixel per 2x2 CFA quad, no interpolation). `stack`
      defaults to the same binned geometry -- render_all.ps1 passes --demosaic
      only when it explicitly wants the full-resolution print artifact. Leaving
      it off makes the two arms pixel-comparable without resampling either one,
      and resampling is itself a detail operation.

  Nothing is written under D:\personal\macro. It is read-only.
#>
[CmdletBinding()]
param(
    [string]$Exe = "C:\dev\strehl-scratch-THESIS\target\release\strehl.exe",
    [string]$Root = "D:\personal\macro",
    [string]$OutDir = "C:\dev\strehl-out\BUILD-THESIS\renders",
    [string[]]$Subjects = @(),
    [switch]$Resume
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Exe)) { throw "no strehl binary at $Exe" }

$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash
Write-Host ("binary   : {0}" -f $Exe)
Write-Host ("sha256   : {0}" -f $hash)
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$hash | Set-Content -Encoding utf8 (Join-Path $OutDir "binary-sha256.txt")

foreach ($s in $Subjects) {
    $src = Join-Path $Root $s
    if (-not (Test-Path $src)) { Write-Host "MISSING $src"; continue }
    $d = Join-Path $OutDir $s
    New-Item -ItemType Directory -Force -Path $d | Out-Null

    $arms = @(
        @{ name = "merge";  argv = @("stack", $src, "--out", (Join-Path $d "merge.tif")) },
        @{ name = "argmax"; argv = @("argmax-baseline", $src, "--out", (Join-Path $d "argmax.tif"),
                                     "--index-map", (Join-Path $d "argmax-index.tif")) }
    )

    foreach ($a in $arms) {
        $tif = Join-Path $d "$($a.name).tif"
        $log = Join-Path $d "$($a.name).log"
        $err = Join-Path $d "$($a.name).err"
        if ($Resume -and (Test-Path $tif)) { Write-Host ("skip     : {0} {1}" -f $s, $a.name); continue }
        Write-Host ("render   : {0,-20} {1,-7} ..." -f $s, $a.name) -NoNewline
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $p = Start-Process -FilePath $Exe -ArgumentList $a.argv -PassThru -NoNewWindow `
            -RedirectStandardOutput $log -RedirectStandardError $err
        $null = $p.Handle
        $p.WaitForExit()
        $sw.Stop()
        $code = $p.ExitCode
        $ok = (Test-Path $tif)
        Write-Host (" {0,8}s  exit={1}  out={2}" -f [math]::Round($sw.Elapsed.TotalSeconds, 1), $code, $ok)
        [pscustomobject]@{
            subject = $s; arm = $a.name; exit = $code; wall_s = [math]::Round($sw.Elapsed.TotalSeconds, 1)
            argv = ($a.argv -join " "); sha256 = $hash
        } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $d "$($a.name).provenance.json")
    }
}
