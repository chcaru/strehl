# BUILD-RESAMP -- pass 4: the total resampling headroom.
#
# The two candidate causes -- the kernel and the coverage enlargement -- are
# folded into ONE fused matrix and paid in ONE gather, so they cannot simply be
# added. The only honest way to price them together is to render the arm that
# has both removed as far as they can be removed, and compare it to the shipping
# arm. That is what this pass does: same binary, same subject, same solve, same
# merge, differing in the kernel and the enlargement together.
#
#   cv-<s>-on        shipping:            catmull-rom, coverage on   (the floor)
#   cv-<s>-off       coverage removed:    catmull-rom, coverage off
#   cv-<s>-onl3      kernel changed:      lanczos3,    coverage on
#   cv-<s>-offl3     both removed:        lanczos3,    coverage off  (the ceiling)
#
# A 2x2 on one binary. Every cell is comparable to every other.
$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\BUILD-RESAMP\bin\strehl-cover.exe'
$root = 'C:\dev\strehl-out\BUILD-RESAMP\render'

function Run($tag, $subject, $kern, $coverEnv) {
  $out = Join-Path $root "$tag.tiff"
  $log = Join-Path $root "$tag.log"
  if (Test-Path $out) { Write-Host "SKIP $tag (exists)"; return }
  Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
  Remove-Item Env:\STREHL_ALIGN   -ErrorAction SilentlyContinue
  Remove-Item Env:\STREHL_COVER   -ErrorAction SilentlyContinue
  if ($null -ne $coverEnv) { $env:STREHL_COVER = $coverEnv }
  $t0 = Get-Date
  $txt = & $exe stack "D:\personal\macro\$subject" --out $out --merge pyramid --demosaic --resampler $kern 2>&1
  $code = $LASTEXITCODE
  $dt = ((Get-Date) - $t0).TotalSeconds
  $txt | Out-File -FilePath $log -Encoding utf8
  "ARGV: $exe stack `"D:\personal\macro\$subject`" --out $out --merge pyramid --demosaic --resampler $kern" |
    Out-File -FilePath $log -Encoding utf8 -Append
  "ENV : STREHL_COVER=$(if ($null -eq $coverEnv) {'<unset>'} else {$coverEnv})" |
    Out-File -FilePath $log -Encoding utf8 -Append
  "EXIT: $code   WALL_S: $([math]::Round($dt,1))" | Out-File -FilePath $log -Encoding utf8 -Append
  Remove-Item Env:\STREHL_COVER -ErrorAction SilentlyContinue
  Write-Host ("DONE {0}  exit {1}  {2:N1} s" -f $tag, $code, $dt)
}

Run 'cv-112-onl3'   '112MSDCF'          'lanczos3' $null
Run 'cv-112-offl3'  '112MSDCF'          'lanczos3' '0'
Run 'cv-flat-onl3'  'flat-on-ruler-cpl' 'lanczos3' $null
Run 'cv-flat-offl3' 'flat-on-ruler-cpl' 'lanczos3' '0'

Write-Host "PASS 4 COMPLETE"
