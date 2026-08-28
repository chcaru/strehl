# Bank the acceptance freeze outputs as text, then report what is safe to delete.
#
# The acceptance tree holds ~14.6 GB of freeze-test output TIFFs (SHIP-V3,
# SHIP-V4, HEAD-d2193a55-sealshape, PINTEST). A byte-freeze test compares
# SHA256, not pixels, so the hash IS the measurement and the TIFF is only its
# carrier. This script writes every hash and every per-file provenance record
# into one text index under the git tree so the freeze results survive the
# purge. It DELETES NOTHING -- deletion is a separate, explicit step.
$ErrorActionPreference = 'Stop'

$root = 'C:\dev\strehl-out\acceptance'
$outDir = 'C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check'
$out = Join-Path $outDir 'acceptance-hash-index.txt'

if (-not (Test-Path $root)) { throw "acceptance root not found: $root" }

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add('=== ACCEPTANCE FREEZE HASH INDEX')
$lines.Add("generated : $(Get-Date -Format o)")
$lines.Add("root      : $root")
$lines.Add('purpose   : a byte-freeze result is a SHA256. This file preserves every')
$lines.Add('            hash and provenance record so the TIFF carriers can be')
$lines.Add('            deleted without making any published freeze unreproducible.')
$lines.Add('')

$before = (Get-ChildItem $root -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
$lines.Add(("bytes before : {0} ({1:N2} GB)" -f $before, ($before / 1GB)))
$lines.Add('')

$total = 0
foreach ($set in (Get-ChildItem $root -Directory | Sort-Object Name)) {
  $lines.Add("--- SET $($set.Name)")

  foreach ($meta in (Get-ChildItem $set.FullName -Recurse -File -Include '*.txt' -EA SilentlyContinue | Sort-Object Name)) {
    $body = (Get-Content $meta.FullName -Raw -EA SilentlyContinue)
    if ($body -and $body.Trim().Length -gt 0) {
      $lines.Add("  [meta] $($meta.Name)")
      foreach ($l in ($body -split "`r?`n")) {
        if ($l.Trim().Length -gt 0) { $lines.Add("         $l") }
      }
    }
  }

  foreach ($t in (Get-ChildItem $set.FullName -Recurse -File -Include '*.tiff' -EA SilentlyContinue | Sort-Object Name)) {
    $h = (Get-FileHash $t.FullName -Algorithm SHA256).Hash
    $lines.Add(("  {0}  {1,12}  {2}" -f $h, $t.Length, $t.Name))
    $total++
  }
  $lines.Add('')
}

$lines.Add("total tiffs hashed : $total")
if ($total -eq 0) { throw "FATAL: hashed 0 TIFFs -- the index would be empty and deleting would destroy the freeze results" }

Set-Content -Path $out -Value ($lines -join "`n") -Encoding utf8
Write-Host "wrote $out"
Write-Host ("  tiffs hashed : {0}" -f $total)
Write-Host ("  reclaimable  : {0:N2} GB" -f ($before / 1GB))
