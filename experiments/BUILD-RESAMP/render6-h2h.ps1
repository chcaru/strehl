# BUILD-RESAMP -- comparator renders on a file list BOTH tools see identically.
#
# The fork holds every input frame in memory at once (float32, 3 channels, full
# raster ~396 MB each) and dies at 79 frames on this machine:
#   OpenCV(4.13.0) alloc.cpp:73: (-4:Insufficient memory) Failed to allocate
#   392896512 bytes in function 'cv::OutOfMemoryError'
# So the stack is decimated to a frame count both tools can carry, and BOTH are
# pointed at the SAME staged directory. The A/B is then over one variable, the
# tool. It is not a comparison of "the fork on 33 frames vs strehl on 130".

$ErrorActionPreference = 'Continue'
$SRC   = 'D:\personal\macro\wrapped-text-1'
$STAGE = 'C:\dev\strehl-out\BUILD-RESAMP\subset\wrapped-text-1'
$OUT   = 'C:\dev\strehl-out\BUILD-RESAMP\h2h'
$FORK  = 'C:\dev\macro\focus-stack\dist\focus-stack.exe'
$STREHL= 'C:\dev\strehl-out\BUILD-RESAMP\bin\strehl.exe'
$STRIDE = 4

New-Item -ItemType Directory -Force -Path $STAGE, $OUT | Out-Null
$all = Get-ChildItem $SRC -Filter *.ARW | Sort-Object Name
$pick = @()
for ($i = 0; $i -lt $all.Count; $i += $STRIDE) { $pick += $all[$i] }
"staging $($pick.Count) of $($all.Count) frames (stride $STRIDE)"
foreach ($f in $pick) {
  $d = Join-Path $STAGE $f.Name
  if (-not (Test-Path $d)) { Copy-Item $f.FullName $d }
}
$staged = Get-ChildItem $STAGE -Filter *.ARW | Sort-Object Name
"staged: $($staged.Count)"
$staged.Name -join "`n" | Out-File "$OUT\framelist.txt" -Encoding utf8

# ---- fork -------------------------------------------------------------------
$fo = "$OUT\wrapped-text-1--fork.tif"
$fargs = @("--output=$fo", "--output-colorspace=linear-rec2020",
           "--output-bitdepth=32") + ($staged.FullName)
$t0 = Get-Date
$log = & $FORK @fargs 2>&1
$code = $LASTEXITCODE
$dt = ((Get-Date) - $t0).TotalSeconds
$log | Out-File "$OUT\wrapped-text-1--fork.log" -Encoding utf8
"ARGV: $FORK --output=$fo --output-colorspace=linear-rec2020 --output-bitdepth=32 <$($staged.Count) ARW from $STAGE>" |
  Out-File "$OUT\wrapped-text-1--fork.log" -Encoding utf8 -Append
"EXIT: $code   WALL_S: $([math]::Round($dt,1))   FRAMES: $($staged.Count)" |
  Out-File "$OUT\wrapped-text-1--fork.log" -Encoding utf8 -Append
"FORK exit $code  $([math]::Round($dt,1)) s"

# ---- strehl -----------------------------------------------------------------
Remove-Item Env:\STREHL_WARPMAP, Env:\STREHL_ALIGN, Env:\STREHL_COVER -ErrorAction SilentlyContinue
$env:STREHL_PYRAMID_WORKERS = '2'
$so = "$OUT\wrapped-text-1--strehl.tiff"
$t0 = Get-Date
$log = & $STREHL stack $STAGE --out $so --merge pyramid --demosaic --resampler catmull-rom 2>&1
$code = $LASTEXITCODE
$dt = ((Get-Date) - $t0).TotalSeconds
$log | Out-File "$OUT\wrapped-text-1--strehl.log" -Encoding utf8
"ARGV: $STREHL stack $STAGE --out $so --merge pyramid --demosaic --resampler catmull-rom  [STREHL_PYRAMID_WORKERS=2]" |
  Out-File "$OUT\wrapped-text-1--strehl.log" -Encoding utf8 -Append
"EXIT: $code   WALL_S: $([math]::Round($dt,1))   FRAMES: $($staged.Count)" |
  Out-File "$OUT\wrapped-text-1--strehl.log" -Encoding utf8 -Append
"STREHL exit $code  $([math]::Round($dt,1)) s"
"H2H RENDERS COMPLETE"
