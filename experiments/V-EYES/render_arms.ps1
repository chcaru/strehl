# Render the two arms for a second subject, so the softness verdict is not a
# claim about one flower bud. Same pinned binary as SHIP-V4, same flags for both
# arms: --linear-srgb --demosaic, and no --auto-exposure (the binary refuses it
# outside --srgb), so master and frames sit on a common linear scale by
# construction rather than by correction.
#
# The reference frames are developed by strehl itself, one ARW per otherwise
# empty directory, so the demosaic, black level, as-shot white balance, colour
# matrix and coverage rescale are all common-mode with the master and cancel in
# the comparison. Developing them through rawpy instead would leave the
# demosaicer as an uncontrolled difference, which is the confound that made the
# first attempt at this measurement unreportable.

param(
  [string]$Subject = "lead-1-cpl",
  [int]$Stride = 10
)

$exe = "C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
$src = "D:\personal\macro\$Subject"
$out = "C:\dev\strehl-out\V-EYES\lin2"
$scratch = "C:\dev\strehl-out\V-EYES\scratch2"

New-Item -ItemType Directory -Force -Path $out | Out-Null

Write-Host "=== master arm: full stack ==="
& $exe stack $src --out "$out\MASTER-linear.tiff" --linear-srgb --demosaic 2>&1 |
  Tee-Object -FilePath "$out\MASTER-linear.log" | Select-String -Pattern 'averaged|wrote|coverage|demosaic'

$frames = Get-ChildItem $src -Filter *.ARW | Sort-Object Name
Write-Host "=== reference arm: $([math]::Floor($frames.Count / $Stride)) frames at stride $Stride ==="
for ($i = 0; $i -lt $frames.Count; $i += $Stride) {
  $f = $frames[$i]
  $d = "$scratch\$($f.BaseName)"
  New-Item -ItemType Directory -Force -Path $d | Out-Null
  Copy-Item $f.FullName -Destination $d -Force
  & $exe stack $d --out "$out\frame-$($f.BaseName).tiff" --linear-srgb --demosaic 2>&1 |
    Out-File "$out\frame-$($f.BaseName).log"
  if ($LASTEXITCODE -ne 0) { Write-Host "  FAILED $($f.BaseName)" }
  Remove-Item $d -Recurse -Force
}
Write-Host "=== done: $((Get-ChildItem $out -Filter 'frame-*.tiff').Count) reference frames ==="
