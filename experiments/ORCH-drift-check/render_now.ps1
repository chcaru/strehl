<#
Re-render all 26 corpus subjects with the CURRENT binary at the best
measured configuration, so the gallery shows where the product actually
stands today rather than where it stood when SHIP-V1 was built.

Three disciplines this script exists to enforce:

  1. It renders from a PINNED COPY of the binary, not from
     target/release/strehl.exe, because eleven agents are rebuilding that
     tree and a binary that changes mid-run makes every card
     incomparable.

  2. It writes a per-subject .err sidecar and keeps it. SHIP-V1 kept a
     log with no argv, so its configuration had to be recovered later by
     byte-matching against a re-render. That is not happening twice.

  3. It names the backend explicitly with --merge pyramid rather than
     relying on the default, because the backend is inferred from the
     flags when --merge is absent and an inferred backend is not a
     recorded one.

D:\personal\macro is READ-ONLY. Nothing is written there.
#>
[CmdletBinding()]
param(
    [string]$Exe  = 'C:\dev\strehl-out\ORCH-GATE\pin-cur\strehl.exe',
    [string]$Root = 'D:\personal\macro',
    [string]$Out  = 'C:\dev\strehl-out\GALLERY-NOW',
    [double]$Gate = 4.5
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Exe)) { throw "pinned binary not found: $Exe" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash
$subjects = Get-ChildItem 'C:\dev\strehl-out\SHIP-V1\*.tiff' | ForEach-Object { $_.BaseName }

$log = Join-Path $Out '_render.log'
# UTF-8 without a BOM, and without PowerShell's UTF-16 redirection, so the
# log is readable by every tool that later wants to parse it. SHIP-V1's log
# is UTF-16LE for exactly the reason this line avoids.
$w = New-Object System.IO.StreamWriter($log, $false, (New-Object System.Text.UTF8Encoding($false)))
function Say([string]$s) {
    Write-Host $s
    $w.WriteLine($s); $w.Flush()
}

Say "binary   : $Exe"
Say "sha256   : $hash"
Say "config   : --merge pyramid --pyramid-gate $Gate --srgb"
Say "subjects : $($subjects.Count)"
Say "started  : $(Get-Date -Format o)"
Say ''

$ok = 0; $fail = 0
$swAll = [Diagnostics.Stopwatch]::StartNew()

foreach ($s in $subjects) {
    $src = Join-Path $Root $s
    if (-not (Test-Path $src)) { Say "SKIP  $s  (no source)"; $fail++; continue }
    $tif = Join-Path $Out "$s.tif"
    $err = Join-Path $Out "$s.err"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $Exe stack $src -o $tif --merge pyramid --pyramid-gate $Gate --srgb 2> $err
    $rc = $LASTEXITCODE
    $sw.Stop()
    if ($rc -eq 0 -and (Test-Path $tif)) {
        $mb = [math]::Round((Get-Item $tif).Length / 1MB, 1)
        Say ("OK    {0,-42} {1,7:N1}s  {2,8:N1} MB" -f $s, $sw.Elapsed.TotalSeconds, $mb)
        $ok++
    } else {
        Say ("FAIL  {0,-42} rc={1}  see {2}" -f $s, $rc, (Split-Path $err -Leaf))
        $fail++
    }
}

$swAll.Stop()
Say ''
Say ("DONE ok=$ok fail=$fail total=$($subjects.Count) in {0:N1} min" -f $swAll.Elapsed.TotalMinutes)
Say "finished : $(Get-Date -Format o)"
$w.Close()
