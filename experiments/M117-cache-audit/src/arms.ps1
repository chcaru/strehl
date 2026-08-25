param(
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$Exe,
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9._-]+$')][string]$Tag,
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$AlignRef)
if (-not (Test-Path $Exe)) { throw "EXE NOT FOUND: $Exe" }
$root = "C:\dev\strehl-out\M117\pc\$Tag"
$stack = "D:\personal\macro\109MSDCF"
function Hash16([string]$p) {
  (Get-FileHash -Algorithm SHA256 -Path $p).Hash.Substring(0,16)
}
function FreshCache([string]$c) {
  if (Test-Path $c) { Remove-Item -Recurse -Force $c }
  New-Item -ItemType Directory -Force -Path $c | Out-Null
}
Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $root | Out-Null
$env:STREHL_ALIGN = $null
$env:STREHL_WARPMAP = $null
$env:STREHL_SMOOTH = $null
$env:STREHL_SMOOTH_HUBER = $null

$results = @()

# ---- Arm A: clean cache, plain stack ----
$c = "$root\cacheA"; FreshCache $c; $env:STREHL_CACHE_DIR = $c
$outA = "$root\A.tiff"
$logA = & $Exe stack $stack --limit 22 --gate 4.0 --out $outA 2>&1 | Out-String
$codeA = $LASTEXITCODE
$results += [pscustomobject]@{arm="A_clean"; code=$codeA; hash=(Hash16 $outA); entries=(Get-ChildItem $c -Filter *.warpmap.txt).Count}
Set-Content "$root\A.log" $logA

# ---- Arm A2: repeat, determinism ----
$c = "$root\cacheA2"; FreshCache $c; $env:STREHL_CACHE_DIR = $c
$outA2 = "$root\A2.tiff"
$logA2 = & $Exe stack $stack --limit 22 --gate 4.0 --out $outA2 2>&1 | Out-String
$results += [pscustomobject]@{arm="A2_repeat"; code=$LASTEXITCODE; hash=(Hash16 $outA2); entries=(Get-ChildItem $c -Filter *.warpmap.txt).Count}
Set-Content "$root\A2.log" $logA2

# ---- Arm B: poison the cache with a differently-configured align, then the SAME stack line ----
$c = "$root\cacheB"; FreshCache $c; $env:STREHL_CACHE_DIR = $c
if ($AlignRef -eq "none") {
  $logP = & $Exe align $stack --limit 22 2>&1 | Out-String
} else {
  $logP = & $Exe align $stack --limit 22 --reference $AlignRef 2>&1 | Out-String
}
$codeP = $LASTEXITCODE
Set-Content "$root\B.align.log" $logP
$entriesAfterAlign = (Get-ChildItem $c -Filter *.warpmap.txt -ErrorAction SilentlyContinue).Count
$outB = "$root\B.tiff"
$logB = & $Exe stack $stack --limit 22 --gate 4.0 --out $outB 2>&1 | Out-String
$results += [pscustomobject]@{arm="B_poisoned"; code=$LASTEXITCODE; hash=(Hash16 $outB); entries=(Get-ChildItem $c -Filter *.warpmap.txt).Count}
Set-Content "$root\B.log" $logB

Write-Output "### TAG=$Tag EXE=$Exe ALIGNREF=$AlignRef"
Write-Output "align exit=$codeP ; cache entries after align=$entriesAfterAlign"
$results | Format-Table -AutoSize | Out-String -Width 200
$hA = ($results | Where-Object {$_.arm -eq "A_clean"}).hash
$hA2= ($results | Where-Object {$_.arm -eq "A2_repeat"}).hash
$hB = ($results | Where-Object {$_.arm -eq "B_poisoned"}).hash
Write-Output "determinism A==A2 : $($hA -eq $hA2)"
Write-Output "POISONED  A!=B    : $($hA -ne $hB)"
Write-Output "alignment lines:"
($logA -split "`n" | Select-String -Pattern "alignment") | Out-String
($logB -split "`n" | Select-String -Pattern "alignment") | Out-String
$env:STREHL_CACHE_DIR = $null

