param([string[]]$Subjects = @(), [switch]$All)
# BUILD-DEFECT / render_arms.ps1
#
# Render each subject TWICE from ONE binary, changing only STREHL_DEFECT.
#
# WHY NOT COMPARE AGAINST THE EXISTING SHIP-V4 SEALS. defect_map.rs is ABSENT
# from pin 9b05d0b7, so those seals were produced by a binary that has no defect
# correction at all. An ON-vs-seal comparison would confound this feature with
# every other change between that pin and HEAD. Both arms are rendered here, from
# the same binary, so the only difference between them is the switch under test.
#
# THE ENV LEAK GUARD IS NOT CEREMONY. A stray STREHL_* inherited from another
# lane's shell would apply to BOTH arms and could silently change what is being
# measured. The guard throws rather than warns.
$ErrorActionPreference = 'Stop'

$repo = 'C:\dev\blog\death-of-software\projects\strehl'
$exe  = "$repo\.cargo-target-defect\release\strehl.exe"
if (-not (Test-Path $exe)) { throw "BINARY MISSING: $exe -- build it first" }
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash
$head = (& git -C $repo rev-parse --short HEAD).Trim()
$dirty = & git -C $repo status --porcelain -- crates/
Write-Host "binary  $($hash.Substring(0,16))  HEAD $head"
if ($dirty) { Write-Host "WARNING: crates/ is dirty; the binary is not exactly $head" -ForegroundColor Yellow }

# STREHL_DEFECT and STREHL_DEFECT_ARM are the variables under test and are set
# per arm below; everything else must be absent.
$allowed = @('STREHL_DEFECT','STREHL_DEFECT_ARM','STREHL_DEFECT_HOT_FLOOR','STREHL_DEFECT_MAP')
$leak = Get-ChildItem env: | Where-Object { $_.Name -like 'STREHL_*' -and $allowed -notcontains $_.Name }
if ($leak) { throw ("UNEXPECTED STREHL_* SET: " + ($leak.Name -join ',')) }
foreach ($v in $allowed) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }

$man = Import-Csv 'C:\dev\strehl-out\acceptance\SHIP-V4\manifest.tsv' -Delimiter "`t"
if ($All) { $Subjects = $man.subject }
if (-not $Subjects) { throw "no subjects: pass -Subjects a,b or -All" }

$root = 'C:\dev\strehl-out\BUILD-DEFECT\arms'
New-Item -ItemType Directory -Force -Path $root | Out-Null

foreach ($s in $Subjects) {
  $row = $man | Where-Object { $_.subject -eq $s }
  if (-not $row) { throw "SUBJECT NOT IN MANIFEST: $s -- refusing to guess its exposure" }
  $stops = $row.exposure_stops
  $src = "D:\personal\macro\$s"
  if (-not (Test-Path $src)) { throw "SOURCE MISSING (D: is read-only, never written): $src" }

  foreach ($arm in @('off','on')) {
    $dst = "$root\$s--$arm.tiff"
    $log = "$root\$s--$arm.log"
    if (Test-Path "$dst.ok") { Write-Host "  $s/$arm sealed already, skipped"; continue }

    foreach ($v in $allowed) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
    if ($arm -eq 'on') { $env:STREHL_DEFECT = 'on' } else { $env:STREHL_DEFECT = 'off' }

    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $exe stack $src --out $dst --srgb "--exposure=$stops" 2>$log | Out-Null
    $code = $LASTEXITCODE
    $dt = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    if ($code -ne 0) {
      Write-Host "  $s/$arm EXIT=$code" -ForegroundColor Red
      Get-Content $log -Tail 15
      throw "$s/$arm failed"
    }
    $len = (Get-Item $dst).Length
    $dh = (Get-FileHash $dst -Algorithm SHA256).Hash
    # SEAL AT RENDER TIME, never backfilled.
    Set-Content -Path "$dst.ok" -Value $hash -NoNewline -Encoding ascii
    $prov = @(
      "subject         : $s",
      "arm             : STREHL_DEFECT=$arm",
      "source frames   : $src  ($($row.frames) frames per SHIP-V4 manifest)",
      "binary          : $exe",
      "binary sha256   : $hash",
      "repo HEAD       : $head",
      "crates dirty    : $(if ($dirty) { 'YES -- binary is not exactly HEAD' } else { 'no' })",
      "command         : stack <src> --out <dst> --srgb --exposure=$stops",
      "recipe source   : experiments/V-GATHER/sharprender.ps1 (the SHIP-V4 recipe)",
      "env set         : STREHL_DEFECT=$arm",
      "env absent      : every other STREHL_* (guarded, throws on leak)",
      "output sha256   : $dh",
      "rendered        : $(Get-Date -Format o)",
      "seconds         : $dt",
      "bytes           : $len"
    ) -join "`n"
    Set-Content -Path "$dst.provenance.txt" -Value $prov -Encoding utf8
    Write-Host ("  {0,-38} {1,-3} {2,6:N1}s  {3}" -f $s, $arm, $dt, $dh.Substring(0,16))
  }

  $a = (Get-FileHash "$root\$s--off.tiff" -Algorithm SHA256).Hash
  $b = (Get-FileHash "$root\$s--on.tiff"  -Algorithm SHA256).Hash
  Write-Host ("  {0,-38} bytes differ: {1}" -f $s, ($a -ne $b))
}
foreach ($v in $allowed) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
Write-Host "ARMS DONE"
