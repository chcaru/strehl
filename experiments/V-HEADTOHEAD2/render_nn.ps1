# V-H2H2 / render_nn.ps1
#
# THE ARM THAT DECIDES WHETHER C IS USABLE.
#
# commission.py found C rates a nearest-neighbour rescale up to 3.2x BETTER
# than a bicubic one when the rescale is applied identically to both halves --
# the same direction as the +29%/+42% failure that killed the retracted
# statistic.  This runs the SAME degradation through the REAL pipeline, where
# the gather is per-frame at per-frame sub-pixel offsets across disjoint,
# separately-solved frame sets.
#
# PREDICTION, written before the run: if C is usable for this comparison, the
# real NN gather must score WORSE than the real catmull-rom gather at every
# band above 0.10.  If it scores better, C is unusable and this milestone's
# answer is "no instrument on this corpus can decide fine-scale resolution".
#
# ONE VARIABLE: the sidecar is byte-identical to the catmull-rom one except for
# the string "catmull-rom" -> "nearest" (make_nn_maps.py verifies this by
# splitting on that token and comparing every other byte).  Same geometry, same
# frames, same binary, same env except the map path.
#
# RULE 47 RECORD -- identical to render_linear.ps1 except STREHL_WARPMAP.

$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$out  = 'C:\dev\strehl-out\V-H2H2'
$ren  = "$out\lin"
$logs = "$out\logs"

$clear = @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN','STREHL_MERGE',
           'STREHL_DEBUG','STREHL_LOG','STREHL_THREADS','STREHL_MEM_BUDGET_MB',
           'STREHL_NO_HALO','STREHL_SEED','STREHL_RESAMPLER')

$sets = @(
  @{ tag='113-A'; src="$out\halves\113-A" },
  @{ tag='113-B'; src="$out\halves\113-B" },
  @{ tag='cb-A';  src="$out\halves\cb-A"  },
  @{ tag='cb-B';  src="$out\halves\cb-B"  }
)

foreach ($s in $sets) {
  $tag = "$($s.tag)-nn-g1"
  $dst = "$ren\$tag.tiff"
  $log = "$logs\lin-$tag.log"
  if (Test-Path $dst) { Write-Host "  $tag exists, skipped"; continue }
  foreach ($v in $clear) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
  $env:STREHL_FULLRES_GATHER = '1'
  $env:STREHL_WARPMAP = "$out\warpmaps\$($s.tag)-nn.warpmap.txt"
  $t0 = Get-Date
  & cmd /c exit 0
  & $exe stack $s.src --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-File -FilePath $log -Encoding utf8
  $code = $LASTEXITCODE
  $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
  Write-Host ("  {0} exit={1} {2}s" -f $tag, $code, $dt)
  # PRINT-THEN-TEST: the tool must SAY it used the sidecar's nearest kernel.
  $said = (Select-String -Path $log -Pattern 'nearest' |
           ForEach-Object { $_.Line.Trim() }) -join ' | '
  Write-Host ("      kernel evidence: {0}" -f $(if ($said) { $said } else { 'NONE FOUND -- ARM IS INVALID' }))
  if ($code -ne 0) { throw "$tag failed with exit $code" }
  if (-not $said) { throw "${tag}: log never mentions nearest; the sidecar kernel was not honoured" }
}
Write-Host "NN ARM RENDERS DONE"
