param([string]$Subject = "D:\personal\macro\109MSDCF", [string]$Tag = "109MSDCF")
$ErrorActionPreference = "Continue"
$BIN = "C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe"
$O   = "C:\dev\strehl-out\M126-COMPOSITE\$Tag"
New-Item -ItemType Directory -Force -Path "$O\lin","$O\logs","$O\cache" | Out-Null

function Clear-Strehl {
  Get-ChildItem env: | Where-Object { $_.Name -like "STREHL_*" } |
    ForEach-Object { Remove-Item "env:$($_.Name)" -ErrorAction SilentlyContinue }
}

$arms = [ordered]@{
  # restore reachability: positive control under --demosaic
  "Bd" = @{ args = @("--merge","pyramid","--pyramid-gate","4.5","--demosaic"); env = @{}; base = $null }
  "Cd" = @{ args = @("--merge","pyramid","--pyramid-gate","4.5","--demosaic"); env = @{ STREHL_RESTORE = "1.7" }; base = "Bd" }
  # decompose arm D
  "Dv" = @{ args = @("--merge","estimator","--photometric"); env = @{ STREHL_VEIL = "1" };     base = "D0" }
  "Dh" = @{ args = @("--merge","estimator","--photometric"); env = @{ STREHL_FIX_HALO = "1" }; base = "D0" }
}

$rows = @()
foreach ($name in $arms.Keys) {
  $a = $arms[$name]; $out = "$O\lin\$name.tif"; $log = "$O\logs\$name.log"
  Clear-Strehl
  $env:STREHL_CACHE_DIR = "$O\cache\$name"
  New-Item -ItemType Directory -Force -Path $env:STREHL_CACHE_DIR | Out-Null
  foreach ($k in $a.env.Keys) { Set-Item "env:$k" $a.env[$k] }
  $argv = @("stack", $Subject) + $a.args + @("-o", $out)
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $BIN @argv > $log 2>&1
  $rc = $LASTEXITCODE; $sw.Stop()
  $hash = ""; if (Test-Path $out) { $hash = (Get-FileHash -Algorithm SHA256 $out).Hash }
  Write-Output ("[{0}] rc={1} {2}s sha={3}" -f $name, $rc, [math]::Round($sw.Elapsed.TotalSeconds,1), $(if($hash){$hash.Substring(0,16)}else{"FAILED"}))
  $rows += [pscustomobject]@{ arm=$name; rc=$rc; sha=$hash; base=$a.base
    banner=$((Select-String -Path $log -Pattern "^merge backend" | Select-Object -First 1).Line)
    envstr=(($a.env.GetEnumerator()|ForEach-Object{"$($_.Key)=$($_.Value)"}) -join " ")
    argstr=($a.args -join " ") }
}
Clear-Strehl
$prev = Import-Csv "$O\arms.csv"
$all  = @($prev) + @($rows)
$rows | Export-Csv -NoTypeInformation -Path "$O\arms2.csv"
Write-Output ""
Write-Output "=== differ-from-base ==="
foreach ($r in $rows) {
  if ($r.base) {
    $b = $all | Where-Object { $_.arm -eq $r.base } | Select-Object -First 1
    $same = ($b -and $b.sha -eq $r.sha -and $r.sha -ne "")
    Write-Output ("{0} vs {1}: {2}" -f $r.arm, $r.base, $(if ($same) { "IDENTICAL" } else { "DIFFERS" }))
  }
}
