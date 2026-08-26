# BUILD-RESAMP -- pass 3: the coverage enlargement, priced against the identical
# render.
#
# ONE binary (strehl-cover.exe, SHA256 3B3B386D...), one subject, one solve
# (STREHL_COVER is deliberately NOT in SOLVE_ENV, so both arms load the same
# cached warp map), one kernel. The arms differ in exactly one environment
# variable: whether `fit_to_cover`'s 1/k enlargement is folded into the fused
# matrix. Nothing else moves.
#
# COMMISSIONING: with STREHL_ALIGN=0 there is no map to fit, so STREHL_COVER
# must make no difference at all -- byte-identical output is the null. If the
# null fails, the switch is doing something other than what it says.
$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\BUILD-RESAMP\bin\strehl-cover.exe'
$root = 'C:\dev\strehl-out\BUILD-RESAMP\render'

function Run($tag, $subject, $kern, $alignEnv, $coverEnv) {
  $out = Join-Path $root "$tag.tiff"
  $log = Join-Path $root "$tag.log"
  if (Test-Path $out) { Write-Host "SKIP $tag (exists)"; return }
  Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
  Remove-Item Env:\STREHL_ALIGN   -ErrorAction SilentlyContinue
  Remove-Item Env:\STREHL_COVER   -ErrorAction SilentlyContinue
  if ($null -ne $alignEnv) { $env:STREHL_ALIGN = $alignEnv }
  if ($null -ne $coverEnv) { $env:STREHL_COVER = $coverEnv }
  $t0 = Get-Date
  $txt = & $exe stack "D:\personal\macro\$subject" --out $out --merge pyramid --demosaic --resampler $kern 2>&1
  $code = $LASTEXITCODE
  $dt = ((Get-Date) - $t0).TotalSeconds
  $txt | Out-File -FilePath $log -Encoding utf8
  "ARGV: $exe stack `"D:\personal\macro\$subject`" --out $out --merge pyramid --demosaic --resampler $kern" |
    Out-File -FilePath $log -Encoding utf8 -Append
  "ENV : STREHL_ALIGN=$(if ($null -eq $alignEnv) {'<unset>'} else {$alignEnv})  STREHL_COVER=$(if ($null -eq $coverEnv) {'<unset>'} else {$coverEnv})" |
    Out-File -FilePath $log -Encoding utf8 -Append
  "EXIT: $code   WALL_S: $([math]::Round($dt,1))" | Out-File -FilePath $log -Encoding utf8 -Append
  Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
  Remove-Item Env:\STREHL_COVER -ErrorAction SilentlyContinue
  Write-Host ("DONE {0}  exit {1}  {2:N1} s" -f $tag, $code, $dt)
}

# null: no map -> the switch must be inert
Run 'cv-null-on'  'coffee-bubbles' 'catmull-rom' '0' $null
Run 'cv-null-off' 'coffee-bubbles' 'catmull-rom' '0' '0'

# the measurement, on two subjects with different k
Run 'cv-112-on'   '112MSDCF'          'catmull-rom' $null $null
Run 'cv-112-off'  '112MSDCF'          'catmull-rom' $null '0'
Run 'cv-flat-on'  'flat-on-ruler-cpl' 'catmull-rom' $null $null
Run 'cv-flat-off' 'flat-on-ruler-cpl' 'catmull-rom' $null '0'

Write-Host "PASS 3 COMPLETE"
