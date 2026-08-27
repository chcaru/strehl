# V-H2H2 -- build the odd/even half-stacks and render them.
#
# WHY.  Every instrument the prior pass tried was fooled by NOISE POWER: a
# nearest-neighbour gather scored +29%/+42%, a 0.5x downscale scored 4.35x
# better, and flat featureless ROIs gained MORE than detail ROIs.  All three are
# the same defect -- band POWER counts noise as if it were detail.
#
# Two renders built from DISJOINT halves of the same bracket see the same scene
# through independent photons.  Their CROSS-SPECTRUM is therefore an estimate of
# the real structure alone: independent noise contributes zero in expectation,
# and its residual shows up as variance, which is measurable.  That is the only
# route on this corpus to a fine-scale statistic that noise cannot inflate.
#
# The halves are COPIES, not links: D:\personal\macro is read-only and is a
# different volume, so a hardlink is not available.
#
# RULE 47 -- the full invocation:
#   binary   C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe
#            sha256 15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0
#   align    strehl align <halfdir> --out <halfdir>.warpmap.txt      (no other flags)
#   stack    strehl stack <halfdir> --out <OUT> --merge pyramid --pyramid-gate 4.5
#   NOT passed: --srgb --exposure --limit --resampler --gate --threads
#   env      STREHL_FULLRES_GATHER = 0 or 1 ; STREHL_WARPMAP = the half's own map;
#            all other STREHL_* cleared by name below.

$ErrorActionPreference = 'Continue'
$exe   = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$root  = 'C:\dev\strehl-out\V-H2H2'
$half  = "$root\halves"
$rend  = "$root\renders"
$logs  = "$root\logs"
$wm    = "$root\warpmaps"
foreach ($d in $half,$rend,$logs,$wm) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

foreach ($v in 'STREHL_FULLRES_GATHER','STREHL_ALIGN','STREHL_WARPMAP','STREHL_FIX_HALO',
                'STREHL_MERGE','STREHL_ACUITY','STREHL_ONLY_FRAME','STREHL_SOFT_GATE',
                'STREHL_COVER','STREHL_PYRAMID_WORKERS','STREHL_CACHE_DIR') {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}

$stacks = @(
  @{ name='113'; src='D:\personal\macro\113MSDCF' }
)
if ($args -contains '-cb') { $stacks += @{ name='cb'; src='D:\personal\macro\coffee-bean' } }

foreach ($s in $stacks) {
  $files = Get-ChildItem $s.src -Filter *.ARW | Sort-Object Name
  "$($s.name): $($files.Count) frames"
  for ($p = 0; $p -lt 2; $p++) {
    $tag = if ($p -eq 0) { 'A' } else { 'B' }          # A = even index, B = odd index
    $dir = "$half\$($s.name)-$tag"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $n = 0
    for ($i = $p; $i -lt $files.Count; $i += 2) {
      $dst = Join-Path $dir $files[$i].Name
      if (-not (Test-Path $dst) -or (Get-Item $dst).Length -ne $files[$i].Length) {
        Copy-Item $files[$i].FullName $dst
      }
      $n++
    }
    "  half $tag -> $dir  ($n frames)"
    $map = "$wm\$($s.name)-$tag.warpmap.txt"
    if (-not (Test-Path $map)) {
      $o = & $exe align $dir --out $map 2>&1
      $c = $LASTEXITCODE
      Set-Content -Path "$logs\align-$($s.name)-$tag.log" -Value ($o | Out-String -Width 220)
      "  align exit=$c"
      if ($c -ne 0) { throw "align $($s.name)-$tag exit $c" }
    }
    foreach ($g in '0','1') {
      $out = "$rend\$($s.name)-$tag-g$g.tiff"
      $env:STREHL_WARPMAP = $map
      $env:STREHL_FULLRES_GATHER = $g
      $sw = [Diagnostics.Stopwatch]::StartNew()
      $o = & $exe stack $dir --out $out --merge pyramid --pyramid-gate 4.5 2>&1
      $c = $LASTEXITCODE
      $sw.Stop()
      Set-Content -Path "$logs\$($s.name)-$tag-g$g.log" -Value ($o | Out-String -Width 220)
      $sz = if (Test-Path $out) { (Get-Item $out).Length } else { -1 }
      "  $($s.name)-$tag-g$g exit=$c $([math]::Round($sw.Elapsed.TotalSeconds,1))s bytes=$sz"
      if ($c -ne 0) { throw "$($s.name)-$tag-g$g exit $c" }
    }
  }
}
Remove-Item Env:\STREHL_FULLRES_GATHER -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
'HALVES DONE'
