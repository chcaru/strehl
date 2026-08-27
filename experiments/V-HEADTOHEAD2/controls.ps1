# V-H2H2 / controls.ps1
# Two things that must happen BEFORE any measurement is believed.
#
# (1) RED CONTROL.  STREHL_FULLRES_GATHER=<garbage> must PANIC.  An earlier
#     attempt used `strehl probe`, which exited 0 -- because probe never calls
#     warp_frame_in_place, the flag's only read site.  A control that cannot
#     fire is not a control.  This runs a real stack, with a pre-solved
#     warpmap, so the read site is definitely reached.
#     PREDICTION, written before running: exit code 101 (Rust panic), and
#     stderr names STREHL_FULLRES_GATHER.  Both are asserted; neither is
#     `-ne 0`.
#
# (2) TONE GROUND TRUTH.  h2.py inverts the develop chain transcribed from
#     image_out.rs.  Transcription is exactly the kind of thing that is wrong
#     and still looks plausible.  So: render the SAME merge twice at two
#     exposures 1.00 EV apart.  --exposure is one multiply in linear light
#     BEFORE the curve, so the two renders differ only by a factor of exactly
#     2 in the light entering two DIFFERENT auto-picked tone curves.  If the
#     inversion is right, inverting each with its own printed tone and taking
#     the ratio must give 2.000 FLAT ACROSS THE TONAL RANGE.  If s_curve, the
#     toe, or the luma coupling is wrong, the ratio bends.  That is the test.
#
#   binary   C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe
#   frames   C:\dev\strehl-out\V-H2H2\halves\113-A  (32 frames)
#   warpmap  C:\dev\strehl-out\V-H2H2\warpmaps\113-A.warpmap.txt  (pre-solved,
#            shared with the main pass, so the merge input is byte-identical)
#   flags    --merge pyramid --pyramid-gate 4.5 --srgb --exposure {2.34,1.34}
#   env      STREHL_FULLRES_GATHER=1, STREHL_WARPMAP=<above>; all other
#            STREHL_* cleared by name below.

$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$out  = 'C:\dev\strehl-out\V-H2H2'
$src  = "$out\halves\113-A"
$map  = "$out\warpmaps\113-A.warpmap.txt"

foreach ($v in @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN',
                 'STREHL_MERGE','STREHL_DEBUG','STREHL_LOG','STREHL_THREADS',
                 'STREHL_MEM_BUDGET_MB','STREHL_NO_HALO','STREHL_SEED',
                 'STREHL_RESAMPLER')) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

Write-Host "=== (1) RED CONTROL: STREHL_FULLRES_GATHER=bogus on a real stack ==="
$env:STREHL_WARPMAP = $map
$env:STREHL_FULLRES_GATHER = 'bogus-not-a-valid-value'
& cmd /c exit 0                      # clear $LASTEXITCODE to a known state
$rclog = "$out\logs\redcontrol.log"
& $exe stack $src --out "$out\renders\redcontrol.tiff" `
      --merge pyramid --pyramid-gate 4.5 --srgb --exposure 2.34 `
      2>&1 | Out-File -FilePath $rclog -Encoding utf8
$rc = $LASTEXITCODE
$txt = Get-Content $rclog -Raw
$named = $txt -match 'STREHL_FULLRES_GATHER'
Write-Host ("  exit code            : {0}   (predicted 101)" -f $rc)
Write-Host ("  stderr names the var : {0}   (predicted True)" -f $named)
$rcPass = ($rc -eq 101) -and $named
Write-Host ("  RED CONTROL          : {0}" -f $(if ($rcPass) { 'FIRED' } else { 'DID NOT MATCH PREDICTION' }))
if ($txt -match '(?m)^.*panic.*$') { Write-Host ("  panic line           : " + $Matches[0].Trim()) }
Remove-Item "$out\renders\redcontrol.tiff" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== (2) TONE GROUND TRUTH: same merge, two exposures 1.00 EV apart ==="
Remove-Item env:STREHL_FULLRES_GATHER -ErrorAction SilentlyContinue
$env:STREHL_FULLRES_GATHER = '1'
$env:STREHL_WARPMAP = $map
foreach ($e in @('2.34','1.34')) {
  $tag = "tone-e$($e -replace '\.','p')"
  $dst = "$out\renders\$tag.tiff"
  $log = "$out\logs\$tag.log"
  if (Test-Path $dst) { Write-Host "  $tag exists, skipped"; continue }
  $t0 = Get-Date
  & cmd /c exit 0
  & $exe stack $src --out $dst --merge pyramid --pyramid-gate 4.5 --srgb `
        --exposure $e 2>&1 | Out-File -FilePath $log -Encoding utf8
  $code = $LASTEXITCODE
  $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
  $tone = (Select-String -Path $log -Pattern '^tone\s' | ForEach-Object { $_.Line.Trim() }) -join ''
  Write-Host ("  {0} exit={1} {2}s  {3}" -f $tag, $code, $dt, $tone)
  if ($code -ne 0) { throw "$tag failed with exit $code" }
}
Write-Host "CONTROLS DONE"
