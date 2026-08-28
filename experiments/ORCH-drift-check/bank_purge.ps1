# Generic bank-then-purge for an orchestrator-owned scratch tree.
#
# Usage: bank_purge.ps1 -Root <dir> -Name <short-name> [-WhatIf]
#
# Writes a text index of every image artifact (SHA256, byte size, path) plus the
# full body of every small text/JSON/CSV/MD file found under Root, into the git
# tree under experiments/ORCH-drift-check/purged/<Name>-index.txt. Refuses to
# delete anything if the index would be empty. Deletion is only performed after
# the index has been written and re-read from disk.
#
# It DOES NOT commit -- the caller commits, then re-runs with -Purge.
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [Parameter(Mandatory = $true)][string]$Name,
  [switch]$Purge
)
$ErrorActionPreference = 'Stop'

# A refusal must be visible to the CALLER, not only on stderr. Without this,
# `powershell -File thisscript.ps1` exits 0 after a throw and a caller checking
# $LASTEXITCODE reads a refusal as a success.
trap { Write-Host $_.Exception.Message; exit 1 }

$protected = @(
  'D:\personal\macro',
  'D:\macro-dark-frames',
  'C:\dev\strehl-out\DELIVER-V6',
  'D:\strehl-out\DELIVER-V6',
  'D:\strehl-out\ORCH-GALLERY',
  'C:\dev\strehl-out\acceptance-pins',
  'C:\dev\blog\death-of-software\projects\strehl'
)
$full = (Resolve-Path $Root).Path
foreach ($p in $protected) {
  if ($full -eq $p -or $full.StartsWith($p + '\', 'OrdinalIgnoreCase') -or $p.StartsWith($full + '\', 'OrdinalIgnoreCase')) {
    throw "REFUSING: '$full' overlaps protected path '$p'"
  }
}

$outDir = 'C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\purged'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$out = Join-Path $outDir "$Name-index.txt"

$heavy = '*.tiff', '*.tif', '*.png', '*.jpg', '*.jpeg', '*.exr', '*.npy', '*.bin', '*.raw', '*.dat', '*.ARW'
$textish = '*.txt', '*.json', '*.csv', '*.md', '*.log', '*.yaml', '*.toml'

if (-not $Purge) {
  $before = (Get-ChildItem $full -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
  $L = New-Object System.Collections.Generic.List[string]
  $L.Add("=== PURGED SCRATCH INDEX: $Name")
  $L.Add("generated : $(Get-Date -Format o)")
  $L.Add("root      : $full")
  $L.Add(("bytes     : {0} ({1:N2} GB)" -f $before, ($before / 1GB)))
  $L.Add('note      : the heavy artifacts below were deleted to reclaim disk. Their')
  $L.Add('            SHA256 and size are preserved so any published claim about')
  $L.Add('            them stays checkable, and the text bodies are inlined whole.')
  $L.Add('')

  $L.Add('--- TEXT BODIES (inlined verbatim)')
  $nText = 0
  foreach ($t in (Get-ChildItem $full -Recurse -File -Include $textish -EA SilentlyContinue | Sort-Object FullName)) {
    if ($t.Length -gt 2MB) { $L.Add("  [SKIPPED >2MB] $($t.FullName)  $($t.Length) bytes"); continue }
    $L.Add("  [file] $($t.FullName)  ($($t.Length) bytes)")
    $body = Get-Content $t.FullName -Raw -EA SilentlyContinue
    if ($body) { foreach ($ln in ($body -split "`r?`n")) { $L.Add("    $ln") } }
    $L.Add('')
    $nText++
  }

  $L.Add('--- HEAVY ARTIFACT HASHES')
  $nHeavy = 0
  foreach ($h in (Get-ChildItem $full -Recurse -File -Include $heavy -EA SilentlyContinue | Sort-Object FullName)) {
    $sha = (Get-FileHash $h.FullName -Algorithm SHA256).Hash
    $L.Add(("  {0}  {1,12}  {2}" -f $sha, $h.Length, $h.FullName.Substring($full.Length + 1)))
    $nHeavy++
  }
  $L.Add('')
  $L.Add("text files inlined : $nText")
  $L.Add("heavy artifacts    : $nHeavy")

  if ($nText -eq 0 -and $nHeavy -eq 0) { throw "REFUSING: found nothing under $full -- an empty index must not authorise a delete" }
  Set-Content -Path $out -Value ($L -join "`n") -Encoding utf8

  $check = Get-Content $out -Raw
  if ($check.Length -lt 200) { throw "REFUSING: index re-read from disk is only $($check.Length) bytes" }
  Write-Host "BANKED  $out"
  Write-Host ("  text inlined : {0}   heavy hashed : {1}   reclaimable : {2:N2} GB" -f $nText, $nHeavy, ($before / 1GB))
  Write-Host "  now: git add + git commit the index, then re-run with -Purge"
}
else {
  if (-not (Test-Path $out)) { throw "REFUSING: no index at $out -- bank before you purge" }
  Push-Location 'C:\dev\blog\death-of-software\projects\strehl'
  $rel = "experiments/ORCH-drift-check/purged/$Name-index.txt"
  $inHead = & git cat-file -e "HEAD:$rel" 2>&1; $rc = $LASTEXITCODE
  Pop-Location
  if ($rc -ne 0) { throw "REFUSING: $rel is not committed at HEAD -- bank and COMMIT before you purge" }

  $before = (Get-ChildItem $full -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
  Get-ChildItem $full -Recurse -File -Include $heavy -EA SilentlyContinue | Remove-Item -Force -EA SilentlyContinue
  $after = (Get-ChildItem $full -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
  Write-Host ("PURGED  {0}: {1:N2} GB -> {2:N2} GB   reclaimed {3:N2} GB" -f $Name, ($before / 1GB), ($after / 1GB), (($before - $after) / 1GB))
}
