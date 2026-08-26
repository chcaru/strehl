param(
  [Parameter(Mandatory=$true)][string]$Subject,
  [Parameter(Mandatory=$true)][string]$Tag
)
$ErrorActionPreference = "Continue"
$BIN = "C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe"
$O   = "C:\dev\strehl-out\M126-POTENCY\$Tag"
New-Item -ItemType Directory -Force -Path "$O\lin","$O\logs","$O\cache" | Out-Null

function Clear-Strehl {
  Get-ChildItem env: | Where-Object { $_.Name -like "STREHL_*" } |
    ForEach-Object { Remove-Item "env:$($_.Name)" -ErrorAction SilentlyContinue }
}

# Escalation set, pre-committed in PREREG-POTENCY.md: any DEAD reading on the
# 22-frame subject must be re-run on 299 frames before it is called dead,
# because STREHL_FIX_HALO is byte-inert below ~41 frames.
$arms = [ordered]@{
  "S_unset" = @{ env = @{};                              base = $null     }
  "S_0"     = @{ env = @{ STREHL_SMOOTH = "0" };         base = "S_unset" }
  "S_h"     = @{ env = @{ STREHL_SMOOTH_HUBER = "off" }; base = "S_unset" }
}

$rows = @()
foreach ($name in $arms.Keys) {
  $a = $arms[$name]
  $out = "$O\lin\$name.tif"; $log = "$O\logs\$name.log"
  Clear-Strehl
  $env:STREHL_CACHE_DIR = "$O\cache\$name"
  New-Item -ItemType Directory -Force -Path $env:STREHL_CACHE_DIR | Out-Null
  foreach ($k in $a.env.Keys) { Set-Item "env:$k" $a.env[$k] }

  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $BIN @("stack", $Subject, "--merge", "pyramid", "-o", $out) > $log 2>&1
  $rc = $LASTEXITCODE
  $sw.Stop()

  $hash = ""
  if (Test-Path $out) { $hash = (Get-FileHash -Algorithm SHA256 $out).Hash }
  $prior = (Select-String -Path $log -Pattern "track prior" | Select-Object -First 1).Line
  $rows += [pscustomobject]@{
    arm=$name; rc=$rc; secs=[math]::Round($sw.Elapsed.TotalSeconds,1); sha=$hash; base=$a.base
    prior=$(if($prior){$prior.Trim()}else{"<PRIOR SILENT>"})
    envstr=($a.env.GetEnumerator()|ForEach-Object{"$($_.Key)=$($_.Value)"}) -join " "
  }
  Write-Output ("[{0,-8}] rc={1} {2,7}s sha={3}  {4}" -f $name,$rc,
    [math]::Round($sw.Elapsed.TotalSeconds,1),
    $(if($hash){$hash.Substring(0,16)}else{"FAILED----------"}),
    $(if($prior){$prior.Trim()}else{"<prior silent>"}))
}
Clear-Strehl
$rows | Export-Csv -NoTypeInformation -Path "$O\arms.csv"
Write-Output ""
foreach ($r in $rows) {
  if ($r.base) {
    $b = $rows | Where-Object { $_.arm -eq $r.base }
    Write-Output ("{0,-8} vs {1,-8}: {2}" -f $r.arm,$r.base,
      $(if ($b -and $b.sha -eq $r.sha -and $r.sha -ne "") { "IDENTICAL" } else { "DIFFERS" }))
  }
}
