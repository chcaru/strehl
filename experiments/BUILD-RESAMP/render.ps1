# BUILD-RESAMP — render the same subject through one pinned binary with only
# --resampler changing between arms.
#
# The ONLY difference between arms is the --resampler value. Everything else --
# binary, subject, backend, gate, output mode -- is held identical, and each
# arm's own banner is written to its log so the backend can be read from the
# run rather than from this script.
$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\BUILD-RESAMP\bin\strehl.exe'
$root = 'C:\dev\strehl-out\BUILD-RESAMP\render'
New-Item -ItemType Directory -Force -Path $root | Out-Null

# STREHL_WARPMAP is deliberately NOT set: a named sidecar's own resampler wins
# over --resampler (merge_cmd.rs alignment_for), which would silently defeat
# this entire A/B. The shared solve cache is keyed by resampler already.
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_ALIGN   -ErrorAction SilentlyContinue

$jobs = @(
  @{ s = 'flat-on-ruler-cpl'; k = @('catmull-rom','lanczos3','lanczos2','nearest') },
  @{ s = '112MSDCF';          k = @('catmull-rom','lanczos3','lanczos2','nearest') },
  @{ s = 'bee-3-cpl';         k = @('catmull-rom','lanczos3','nearest') },
  @{ s = 'couch-fibers-cpl';  k = @('catmull-rom','lanczos3','nearest') }
)

foreach ($j in $jobs) {
  foreach ($kern in $j.k) {
    $tag = "$($j.s)--$kern"
    $out = Join-Path $root "$tag.tiff"
    $log = Join-Path $root "$tag.log"
    if (Test-Path $out) { Write-Host "SKIP $tag (exists)"; continue }
    $t0 = Get-Date
    $txt = & $exe stack "D:\personal\macro\$($j.s)" --out $out --merge pyramid --demosaic --resampler $kern 2>&1
    $code = $LASTEXITCODE
    $dt = ((Get-Date) - $t0).TotalSeconds
    $txt | Out-File -FilePath $log -Encoding utf8
    "ARGV: $exe stack `"D:\personal\macro\$($j.s)`" --out $out --merge pyramid --demosaic --resampler $kern" |
      Out-File -FilePath $log -Encoding utf8 -Append
    "EXIT: $code   WALL_S: $([math]::Round($dt,1))" | Out-File -FilePath $log -Encoding utf8 -Append
    Write-Host ("DONE {0}  exit {1}  {2:N1} s" -f $tag, $code, $dt)
  }
}
Write-Host "ALL RENDERS COMPLETE"
