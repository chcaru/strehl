# build_full.ps1 -- build the FULL merges for one subject, for route 1.
#
# WHY.  Every detail number this lane has produced was read off HALF-STACKS,
# because the half-split is how noise is estimated.  Detail does not need it.
# `C` counts only structure COHERENT across the two halves, so a merge whose
# halves select different source frames is charged for detail it actually
# delivered.  The full merge has no halves and therefore no such charge.
#
# Same pinned binary and identical flags as run_subject.ps1 sections 2 and 4 --
# the whole point is that the full arm differs from the half arms ONLY in how
# many frames it was given.
#
#   .\build_full.ps1 -Key 119 -Src D:\personal\macro\119MSDCF
param(
  [Parameter(Mandatory = $true)][string]$Key,
  [Parameter(Mandatory = $true)][string]$Src
)
# Native tools write progress to stderr; with 'Stop' PowerShell turns that into
# a terminating error even on exit 0.  Exit codes are checked explicitly below,
# which is the real contract.
$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$hb   = 'C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin'
$root = "C:\dev\strehl-out\V-NOISE2\$Key"
$arm  = "$root\arms"
$ali  = "$root\aligned"
$logs = "$root\logs"
$full = "$root\work\full"

function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }

# Rule 47: the binary is identified by hash, not by path, before it is used.
$want = '15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0'
$got = (Get-FileHash $exe -Algorithm SHA256).Hash
if ($got -ne $want) { throw "PIN MISMATCH: $got != $want" }
Say "pin verified $got"

# ---------------------------------------------------------------- strehl full
$dst = "$arm\strehl-full.tiff"
if (Test-Path $dst) {
  Say "strehl-full exists, skipped"
} else {
  New-Item -ItemType Directory -Force -Path $full | Out-Null
  Get-ChildItem "$full\*" -File | Remove-Item -Force
  $frames = Get-ChildItem "$Src\*.ARW" | Sort-Object Name
  Say "copying $($frames.Count) frames to a local full dir (D: stays read-only)"
  foreach ($f in $frames) { Copy-Item $f.FullName "$full\$($f.Name)" }

  $map = "$root\$Key-full.warpmap.txt"
  if (-not (Test-Path $map)) {
    Say "strehl align full ($($frames.Count) frames)"
    Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
    Remove-Item Env:STREHL_FULLRES_GATHER -ErrorAction SilentlyContinue
    & $exe align $full --out $map 2>&1 | Out-File "$logs\align-full.log" -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw "strehl align full exit $LASTEXITCODE" }
  }
  Say "strehl stack full"
  $env:STREHL_FULLRES_GATHER = '1'
  $env:STREHL_WARPMAP = $map
  $t0 = Get-Date
  & $exe stack $full --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-File "$logs\stack-full.log" -Encoding utf8
  $c = $LASTEXITCODE
  Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
  Remove-Item Env:STREHL_FULLRES_GATHER -ErrorAction SilentlyContinue
  if ($c -ne 0) { throw "strehl stack full exit $c" }
  Say ("  strehl-full {0}s bytes={1}" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1), (Get-Item $dst).Length)
  Get-ChildItem "$full\*" -File | Remove-Item -Force
}

# ---------------------------------------------------------------- enfuse full
$dste = "$arm\coh-enfuse-full.tif"
if (Test-Path $dste) {
  Say "coh-enfuse-full exists, skipped"
} else {
  $alist = Get-ChildItem "$ali\al_*.tif" | Sort-Object Name | ForEach-Object FullName
  Say "coh-enfuse-full ($($alist.Count) frames)"
  $t0 = Get-Date
  & "$hb\enfuse.exe" --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 `
      --hard-mask --output=$dste @($alist) 2>&1 |
      Out-File "$logs\coh-enfuse-full.log" -Encoding utf8
  Say ("  exit=$LASTEXITCODE {0}s bytes={1}" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1),
       $(if (Test-Path $dste) { (Get-Item $dste).Length } else { 0 }))
}
Say "done"
