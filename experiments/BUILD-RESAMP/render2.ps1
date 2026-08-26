# BUILD-RESAMP -- pass 2.
#
# (a) COMMISSIONING THE FLAG at the byte level. With STREHL_ALIGN=0 there is no
#     warp map, so the gather never runs and --resampler cannot reach a pixel:
#     two kernels MUST produce byte-identical output (the null). With alignment
#     on they MUST differ (the potency). Without both, a kernel A/B could be
#     measuring a flag that does nothing.
#
# (b) THE COVERAGE UPSCALE, end to end, on real pixels. STREHL_ALIGN=zoom keeps
#     `fit_to_cover`'s uniform scale and throws away registration, so
#     zoom-vs-off is one coverage upscale and NOTHING else -- same frames, same
#     merge, same everything, no per-frame warp in either arm. That is the
#     isolated price of the 3% upscale that the finding attributes half the
#     deficit to. Running it at two kernels also prices what a better kernel
#     recovers of that specific loss.
$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\BUILD-RESAMP\bin\strehl.exe'
$root = 'C:\dev\strehl-out\BUILD-RESAMP\render'

function Run($tag, $subject, $kern, $alignEnv) {
  $out = Join-Path $root "$tag.tiff"
  $log = Join-Path $root "$tag.log"
  if (Test-Path $out) { Write-Host "SKIP $tag (exists)"; return }
  Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
  if ($null -eq $alignEnv) { Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue }
  else                     { $env:STREHL_ALIGN = $alignEnv }
  $t0 = Get-Date
  $txt = & $exe stack "D:\personal\macro\$subject" --out $out --merge pyramid --demosaic --resampler $kern 2>&1
  $code = $LASTEXITCODE
  $dt = ((Get-Date) - $t0).TotalSeconds
  $txt | Out-File -FilePath $log -Encoding utf8
  "ARGV: $exe stack `"D:\personal\macro\$subject`" --out $out --merge pyramid --demosaic --resampler $kern" |
    Out-File -FilePath $log -Encoding utf8 -Append
  "ENV : STREHL_ALIGN=$(if ($null -eq $alignEnv) { '<unset>' } else { $alignEnv })" |
    Out-File -FilePath $log -Encoding utf8 -Append
  "EXIT: $code   WALL_S: $([math]::Round($dt,1))" | Out-File -FilePath $log -Encoding utf8 -Append
  Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
  Write-Host ("DONE {0}  exit {1}  {2:N1} s" -f $tag, $code, $dt)
}

# (a) null + potency for the flag itself, on the cheapest subject.
Run 'commission-off-cr'   'coffee-bubbles' 'catmull-rom' '0'
Run 'commission-off-l3'   'coffee-bubbles' 'lanczos3'    '0'
Run 'commission-on-cr'    'coffee-bubbles' 'catmull-rom' $null
Run 'commission-on-l3'    'coffee-bubbles' 'lanczos3'    $null

# (b) the coverage upscale in isolation, on a planar fine-detail subject.
Run 'cover-off-cr'  'flat-on-ruler-cpl' 'catmull-rom' '0'
Run 'cover-zoom-cr' 'flat-on-ruler-cpl' 'catmull-rom' 'zoom'
Run 'cover-zoom-l3' 'flat-on-ruler-cpl' 'lanczos3'    'zoom'

Write-Host "PASS 2 COMPLETE"
