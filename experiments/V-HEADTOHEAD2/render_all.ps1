# V-H2H2 -- every render this milestone measures, from ONE binary.
#
# WHY --srgb.  Without it the tool writes 3516x2344, "binned from one 2x2 quad
# per pixel" -- half resolution, which discards the entire frequency range under
# investigation.  The shipped master is the 7032x4688 --srgb render, and that is
# what the comparators are compared against, so that is what must be measured.
# Its tone chain is removed numerically afterwards (tone.py), using the black,
# white and contrast values THIS RENDER PRINTS, not hard-coded ones.
#
# WHY --exposure and not --auto-exposure.  --auto-exposure picks a gain PER
# IMAGE, so two arms can land at different exposures and any absolute comparison
# is then meaningless.  Both arms of every pair are pinned to the gain SHIP-V2's
# --auto-exposure chose, so these renders are also comparable to the prior pass.
#
# RULE 47 -- the full invocation, including what was left at its default:
#   binary  C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe
#           sha256 15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0
#           git    740e70565d101b0edfaeffc7d0466feb01db8a0f  (the flip commit)
#   align   strehl align <DIR> --out <MAP>
#           (--reference --spans --threads --resampler --limit all default)
#   stack   strehl stack <DIR> --out <OUT> --merge pyramid --pyramid-gate 4.5
#                       --srgb --exposure <E>
#           (--limit, --resampler, --gate, --threads all default; --auto-exposure
#            NOT passed; --merge pyramid is also the default and is passed
#            explicitly so the record does not depend on a default moving)
#   env     STREHL_FULLRES_GATHER = 0 (pre-flip) or 1 (post-flip)   <-- THE VARIABLE
#           STREHL_WARPMAP        = a scratch sidecar, solved once per frame set
#           everything else cleared by name below.
#   host    Windows, PowerShell 5.1 launcher, machine under concurrent load.

$ErrorActionPreference = 'Continue'
$exe   = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$root  = 'C:\dev\strehl-out\V-H2H2'
$half  = "$root\halves"; $rend = "$root\renders"; $logs = "$root\logs"; $wm = "$root\warpmaps"
foreach ($d in $half,$rend,$logs,$wm) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
foreach ($v in 'STREHL_FULLRES_GATHER','STREHL_ALIGN','STREHL_WARPMAP','STREHL_FIX_HALO',
                'STREHL_MERGE','STREHL_ACUITY','STREHL_ONLY_FRAME','STREHL_SOFT_GATE',
                'STREHL_COVER','STREHL_PYRAMID_WORKERS','STREHL_CACHE_DIR') {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}

$subjects = @(
  @{ name='113'; src='D:\personal\macro\113MSDCF';    exp='2.34'  },
  @{ name='cb';  src='D:\personal\macro\coffee-bean'; exp='-0.22' }
)

function Render($tag, $dir, $map, $g, $exp) {
  $out = "$rend\$tag.tiff"
  if (Test-Path $out) { "  $tag SKIP (exists)"; return }
  $env:STREHL_WARPMAP = $map
  $env:STREHL_FULLRES_GATHER = $g
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $o = & $script:exe stack $dir --out $out --merge pyramid --pyramid-gate 4.5 --srgb --exposure $exp 2>&1
  $c = $LASTEXITCODE
  $sw.Stop()
  Set-Content -Path "$script:logs\$tag.log" -Value ($o | Out-String -Width 220)
  $sz = if (Test-Path $out) { (Get-Item $out).Length } else { -1 }
  $tone = ($o | Out-String -Width 220).Split("`n") | Where-Object { $_ -match '^tone\s+:' }
  "  $tag exit=$c $([math]::Round($sw.Elapsed.TotalSeconds,1))s bytes=$sz  $($tone -replace '\s+',' ')"
  if ($c -ne 0) { throw "$tag exit $c" }
}

foreach ($s in $subjects) {
  $files = Get-ChildItem $s.src -Filter *.ARW | Sort-Object Name
  "$($s.name): $($files.Count) frames, --exposure $($s.exp)"
  # ---- full stack, both arms ------------------------------------------------
  $map = "$wm\$(if($s.name -eq '113'){'113MSDCF'}else{'coffee-bean'}).warpmap.txt"
  Render "$($s.name)-full-g0" $s.src $map '0' $s.exp
  Render "$($s.name)-full-g1" $s.src $map '1' $s.exp
  # ---- disjoint halves, both arms ------------------------------------------
  for ($p = 0; $p -lt 2; $p++) {
    $tag = if ($p -eq 0) { 'A' } else { 'B' }
    $dir = "$half\$($s.name)-$tag"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $n = 0
    for ($i = $p; $i -lt $files.Count; $i += 2) {
      $dst = Join-Path $dir $files[$i].Name
      if (-not (Test-Path $dst) -or (Get-Item $dst).Length -ne $files[$i].Length) { Copy-Item $files[$i].FullName $dst }
      $n++
    }
    "  half ${tag}: $n frames -> $dir"
    $hmap = "$wm\$($s.name)-$tag.warpmap.txt"
    if (-not (Test-Path $hmap)) {
      $o = & $exe align $dir --out $hmap 2>&1
      $c = $LASTEXITCODE
      Set-Content -Path "$logs\align-$($s.name)-$tag.log" -Value ($o | Out-String -Width 220)
      "  align $($s.name)-$tag exit=$c"
      if ($c -ne 0) { throw "align $($s.name)-$tag exit $c" }
    }
    Render "$($s.name)-$tag-g0" $dir $hmap '0' $s.exp
    Render "$($s.name)-$tag-g1" $dir $hmap '1' $s.exp
  }
}
Remove-Item Env:\STREHL_FULLRES_GATHER -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
'ALL SRGB RENDERS DONE'
