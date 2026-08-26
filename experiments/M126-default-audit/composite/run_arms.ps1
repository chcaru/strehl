param(
  [Parameter(Mandatory=$true)][string]$Subject,
  [Parameter(Mandatory=$true)][string]$Tag,
  [string]$Extra = ""
)
$ErrorActionPreference = "Continue"
$BIN = "C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe"
$O   = "C:\dev\strehl-out\M126-COMPOSITE\$Tag"
New-Item -ItemType Directory -Force -Path "$O\lin","$O\logs","$O\cache" | Out-Null

function Clear-Strehl {
  Get-ChildItem env: | Where-Object { $_.Name -like "STREHL_*" } |
    ForEach-Object { Remove-Item "env:$($_.Name)" -ErrorAction SilentlyContinue }
}

# arm -> @{ args = <string[]>; env = <hashtable>; base = <arm name or $null> }
$arms = [ordered]@{
  "A"  = @{ args = @("--merge","pyramid");                                     env = @{}; base = $null }
  "B"  = @{ args = @("--merge","pyramid","--pyramid-gate","4.5");              env = @{}; base = "A"  }
  "C"  = @{ args = @("--merge","pyramid","--pyramid-gate","4.5");              env = @{ STREHL_RESTORE = "1.7" }; base = "B" }
  "E"  = @{ args = @("--merge","pyramid","--pyramid-gate","4.5","--resampler","lanczos3"); env = @{}; base = "B" }
  "P"  = @{ args = @("--merge","pyramid","--pyramid-gate","4.5");              env = @{ STREHL_RESTORE = "1.0" }; base = "B" }
  "D0" = @{ args = @("--merge","estimator","--photometric");                   env = @{}; base = $null }
  "D"  = @{ args = @("--merge","estimator","--photometric");                   env = @{ STREHL_VEIL = "1"; STREHL_FIX_HALO = "1" }; base = "D0" }
}

$rows = @()
foreach ($name in $arms.Keys) {
  $a   = $arms[$name]
  $out = "$O\lin\$name.tif"
  $log = "$O\logs\$name.log"
  Clear-Strehl
  $env:STREHL_CACHE_DIR = "$O\cache\$name"
  New-Item -ItemType Directory -Force -Path $env:STREHL_CACHE_DIR | Out-Null
  foreach ($k in $a.env.Keys) { Set-Item "env:$k" $a.env[$k] }

  $argv = @("stack", $Subject) + $a.args
  if ($Extra -ne "") { $argv += $Extra.Split(" ") }
  $argv += @("-o", $out)

  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $BIN @argv > $log 2>&1
  $rc = $LASTEXITCODE
  $sw.Stop()

  $hash = ""
  if (Test-Path $out) { $hash = (Get-FileHash -Algorithm SHA256 $out).Hash }
  $banner = (Select-String -Path $log -Pattern "^merge backend" | Select-Object -First 1).Line
  $napp   = (Select-String -Path $log -Pattern "^not applied"   | Select-Object -First 1).Line

  $rows += [pscustomobject]@{
    arm = $name; rc = $rc; secs = [math]::Round($sw.Elapsed.TotalSeconds,1)
    sha = $hash; base = $a.base
    banner = $(if ($banner) { $banner.Trim() } else { "<none>" })
    notapplied = $(if ($napp) { $napp.Trim() } else { "<none>" })
    envstr = ($a.env.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join " "
    argstr = ($a.args -join " ")
  }
  Write-Output ("[{0}] rc={1} {2}s sha={3}" -f $name, $rc, [math]::Round($sw.Elapsed.TotalSeconds,1), $(if($hash){$hash.Substring(0,16)}else{"FAILED"}))
}
Clear-Strehl

$rows | Export-Csv -NoTypeInformation -Path "$O\arms.csv"
Write-Output ""
Write-Output "=== differ-from-base ==="
foreach ($r in $rows) {
  if ($r.base) {
    $b = $rows | Where-Object { $_.arm -eq $r.base }
    $same = ($b -and $b.sha -eq $r.sha -and $r.sha -ne "")
    Write-Output ("{0} vs {1}: {2}" -f $r.arm, $r.base, $(if ($same) { "IDENTICAL" } else { "DIFFERS" }))
  }
}
