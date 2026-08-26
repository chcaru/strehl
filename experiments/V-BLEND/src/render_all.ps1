$env:STREHL_FIX_CA = "a7c2-fe100gm-2xtc-x4cpl"
$SB = "C:\dev\strehl-out\BUILD-BLEND\tree-lin-0d9fd28\target\release\strehl.exe"
$BR = "C:\dev\strehl-out\BUILD-BLEND\tree-lin-0d9fd28\target\release\examples\blend-render.exe"
$PIN = "C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe"
$out = "C:\dev\strehl-out\V-BLEND\lin"
$log = "C:\dev\strehl-out\V-BLEND\RENDER.log"
New-Item -ItemType Directory -Force -Path $out | Out-Null
"render start $(Get-Date -Format o)" | Out-File $log -Encoding utf8
"CA=$env:STREHL_FIX_CA" | Out-File $log -Append -Encoding utf8

# build-vintage control: same BEFORE merge from two different builds
$t = "$out\flower-bud-alone-cpl-before-PIN.tiff"
if (-not (Test-Path $t)) {
  $t0 = Get-Date
  & $PIN stack "D:\personal\macro\flower-bud-alone-cpl" --out $t --demosaic *> "$out\_pinctl.log"
  "CTRL pin-1cacb61 before rc=$LASTEXITCODE $([math]::Round(((Get-Date)-$t0).TotalSeconds))s" | Out-File $log -Append -Encoding utf8
}

$subjects = @("flower-bud-alone-cpl","dry-erase-marker-head-cpl","foam",
              "bee-1-cpl","couch-fibers-cpl","flower-inner-edge-cpl")
foreach ($s in $subjects) {
  $d = "D:\personal\macro\$s"
  $tb = "$out\$s-before.tiff"
  if (-not (Test-Path $tb)) {
    $t0 = Get-Date
    & $SB stack $d --out $tb --demosaic *> "$out\_$s-before.log"
    "BEFORE $s rc=$LASTEXITCODE $([math]::Round(((Get-Date)-$t0).TotalSeconds))s" | Out-File $log -Append -Encoding utf8
  }
  $ta = "$out\$s-after.tiff"
  if (-not (Test-Path $ta)) {
    $t0 = Get-Date
    & $BR $d $ta --camera-linear *> "$out\_$s-after.log"
    "AFTER  $s rc=$LASTEXITCODE $([math]::Round(((Get-Date)-$t0).TotalSeconds))s" | Out-File $log -Append -Encoding utf8
  }
  "DONE $s" | Out-File $log -Append -Encoding utf8
}
"render end $(Get-Date -Format o)" | Out-File $log -Append -Encoding utf8
