param(
  [string]$Dest = 'D:\strehl-out\BUILD-DEFECT\probe',
  [switch]$PinOnly
)
# BUILD-DEFECT / 90-render-probes.ps1
#
# Re-render the six exposure probes that section 21 is measured on.
#
# WHY THIS SCRIPT EXISTS, AND WHY IT DID NOT BEFORE
# -------------------------------------------------
# The six probe renders were produced by an ad-hoc invocation typed at a prompt.
# When the disk reclamation of 2026-08-28 deleted them as "consumed
# intermediates", the RECIPE went with them: there was no script, so nothing on
# disk recorded which binary, which subject, or which flags had produced the
# numbers section 21 rests on.  Three scripts (72, 73, 76) stopped being able to
# certify anything, and the loss was found only because an exit-code audit ran
# 73 as a subprocess and read a 1 where the suite had been reading a 0.
#
# That is the same failure class as an artifact without provenance being
# re-adopted by whoever finds it next, except in the other direction: an
# artifact without provenance gets DELETED by whoever finds it next, because
# nothing on it says what it is for.  The remedy is a script, so the recipe
# survives the files.
#
# WHAT IS AND IS NOT REPRODUCIBLE
# -------------------------------
#   pin-*.tiff   EXACTLY reproducible.  The pin binary 9b05d0b7 still exists at
#                the path below, and stacking is deterministic, so these four
#                renders must come back byte-identical.  That is not merely a
#                restoration -- it is a determinism control, and if it fails,
#                something about this tree is not what section 21 assumed.
#
#   head-*.tiff  NOT reproducible.  HEAD has moved since section 21 was
#                measured; 393d7ca3 re-fit the lateral-CA coefficient eps_r,
#                which changes the warp and therefore the pixels.  Re-rendering
#                these produces a DIFFERENT binary's output, and any comparison
#                against section 21's HEAD rows is binary drift, not a defect in
#                section 21.  The script records the binary hash for exactly
#                this reason and refuses to pretend the two are the same thing.
#
# The provenance sidecar this writes is the artifact that should have existed
# the first time.
$ErrorActionPreference = 'Stop'

$repo    = 'C:\dev\blog\death-of-software\projects\strehl'
$pinExe  = 'C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe'
$headExe = "$repo\.cargo-target-defect\release\strehl.exe"
$subject = 'D:\personal\macro\109MSDCF'

foreach ($p in @($pinExe, $headExe, $subject)) {
  if (-not (Test-Path $p)) { throw "MISSING, refusing to guess a substitute: $p" }
}

# Every STREHL_* must be absent.  The pin binary has no defect correction at all,
# so a stray variable cannot affect it -- but it CAN affect the HEAD renders, and
# a probe that silently inherited another lane's switch would be measuring
# something other than the default behaviour section 21 named "HEAD".
$leak = Get-ChildItem env: | Where-Object { $_.Name -like 'STREHL_*' }
if ($leak) { throw ("UNEXPECTED STREHL_* SET: " + ($leak.Name -join ',')) }

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

$plan = @(
  @{ f = 'pin-epos3.tiff'; exe = $pinExe;  stops = '+3'    ; who = 'pin' }
  @{ f = 'pin-eneg.tiff' ; exe = $pinExe;  stops = '-3'    ; who = 'pin' }
  @{ f = 'pin-e260.tiff' ; exe = $pinExe;  stops = '+2.60' ; who = 'pin' }
  @{ f = 'pin-e000.tiff' ; exe = $pinExe;  stops = '0'     ; who = 'pin' }
  @{ f = 'head-e260.tiff'; exe = $headExe; stops = '+2.60' ; who = 'head' }
  @{ f = 'head-e000.tiff'; exe = $headExe; stops = '0'     ; who = 'head' }
)
if ($PinOnly) { $plan = $plan | Where-Object { $_.who -eq 'pin' } }

$binHash = @{}
foreach ($e in @($pinExe, $headExe)) { $binHash[$e] = (Get-FileHash $e -Algorithm SHA256).Hash }
Write-Host ("pin  binary  " + $binHash[$pinExe].Substring(0,16))
Write-Host ("head binary  " + $binHash[$headExe].Substring(0,16) + "   HEAD " + (& git -C $repo rev-parse --short HEAD).Trim())

$rendered = 0; $skipped = 0; $failed = 0
$rows = @()
foreach ($job in $plan) {
  $dst = Join-Path $Dest $job.f
  if (Test-Path $dst) {
    Write-Host ("  {0,-16} present already, skipped" -f $job.f); $skipped++
    $rows += [pscustomobject]@{ file=$job.f; who=$job.who; stops=$job.stops; exe=$job.exe
                                binary_sha256=$binHash[$job.exe]; seconds=$null
                                sha256=(Get-FileHash $dst -Algorithm SHA256).Hash; state='skipped' }
    continue
  }
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $job.exe stack $subject --out $dst --srgb "--exposure=$($job.stops)" 2>&1 | Out-Null
  $code = $LASTEXITCODE
  $dt = [math]::Round($sw.Elapsed.TotalSeconds, 1)
  if ($code -ne 0 -or -not (Test-Path $dst)) {
    Write-Host ("  {0,-16} EXIT={1} after {2}s" -f $job.f, $code, $dt) -ForegroundColor Red
    $failed++
    $rows += [pscustomobject]@{ file=$job.f; who=$job.who; stops=$job.stops; exe=$job.exe
                                binary_sha256=$binHash[$job.exe]; seconds=$dt; sha256=$null; state='failed' }
    continue
  }
  $h = (Get-FileHash $dst -Algorithm SHA256).Hash
  Write-Host ("  {0,-16} {1,6}s  {2}" -f $job.f, $dt, $h.Substring(0,16))
  $rendered++
  $rows += [pscustomobject]@{ file=$job.f; who=$job.who; stops=$job.stops; exe=$job.exe
                              binary_sha256=$binHash[$job.exe]; seconds=$dt; sha256=$h; state='rendered' }
}

$total = $plan.Count
Write-Host ""
Write-Host ("declared {0} = rendered {1} + skipped {2} + failed {3}" -f $total, $rendered, $skipped, $failed)
if (($rendered + $skipped + $failed) -ne $total) { throw "PARTITION DOES NOT SUM -- the accounting is wrong, not the renders" }

$prov = [pscustomobject]@{
  written_utc   = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  subject       = $subject
  flags         = '--srgb --exposure=<stops>'
  pin_commit    = '9b05d0b7'
  pin_exe       = $pinExe
  pin_sha256    = $binHash[$pinExe]
  head_exe      = $headExe
  head_sha256   = $binHash[$headExe]
  head_commit   = (& git -C $repo rev-parse --short HEAD).Trim()
  head_caveat   = 'HEAD has moved since section 21 was measured (393d7ca3 re-fit eps_r); head-*.tiff are NOT the originals and any difference from section 21 HEAD rows is binary drift.'
  declared      = $total
  rendered      = $rendered
  skipped       = $skipped
  failed        = $failed
  files         = $rows
}
$provPath = Join-Path $Dest 'PROVENANCE.json'
$prov | ConvertTo-Json -Depth 6 | Set-Content $provPath -Encoding utf8
Write-Host "wrote $provPath"
if ($failed -gt 0) { exit 2 }
exit 0
