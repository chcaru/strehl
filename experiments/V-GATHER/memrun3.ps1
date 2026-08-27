# As memrun2 but with a PER-ARM warp cache (so both arms solve alignment: a
# shared cache lets the second arm read the first arm's sidecar and skip it),
# and a time series of private bytes so the peak can be attributed to a stage.
param([string]$Subject, [string]$Fullres, [int]$Limit = 0, [string]$Tag = "iso")
$OUT = "C:\dev\strehl-out\V-GATHER\mem"
New-Item -ItemType Directory -Force -Path $OUT | Out-Null
$env:STREHL_FULLRES_GATHER = $Fullres
$env:STREHL_FIX_CA = "off"
$env:STREHL_CACHE_DIR = "$OUT\wc-$Tag-$Subject-g$Fullres"
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_ALIGN  -ErrorAction SilentlyContinue
$name = "$Tag-$Subject-g$Fullres" + $(if ($Limit -gt 0) { "-n$Limit" } else { "-all" })
$tif = "$OUT\$name.tif"; $so = "$OUT\$name.out.log"; $se = "$OUT\$name.err.log"
$argl = @("stack", "D:\personal\macro\$Subject", "--out", $tif, "--srgb", "--auto-exposure")
if ($Limit -gt 0) { $argl += @("--limit", "$Limit") }
$sw = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath "C:\dev\strehl-out\V-GATHER\strehl-pinned.exe" `
  -ArgumentList $argl -NoNewWindow -PassThru -RedirectStandardOutput $so -RedirectStandardError $se
$peakWS = 0; $peakPriv = 0; $minFree = 999999.0; $series = @()
while (-not $proc.HasExited) {
  try { $proc.Refresh()
        if ($proc.PeakWorkingSet64      -gt $peakWS)   { $peakWS   = $proc.PeakWorkingSet64 }
        if ($proc.PeakPagedMemorySize64 -gt $peakPriv) { $peakPriv = $proc.PeakPagedMemorySize64 }
        $series += [pscustomobject]@{ t=[math]::Round($sw.Elapsed.TotalSeconds,2)
                                      priv_MiB=[math]::Round($proc.PagedMemorySize64/1MB,0) }
  } catch {}
  $f = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
  if ($f -lt $minFree) { $minFree = $f }
  Start-Sleep -Milliseconds 250
}
$proc.WaitForExit(); $sw.Stop()
$series | ConvertTo-Json -Compress | Set-Content "$OUT\$name.series.json"
[pscustomobject]@{
  name=$name; fullres=$Fullres; exit=$proc.ExitCode
  wall_s=[math]::Round($sw.Elapsed.TotalSeconds,1)
  peakWS_MiB=[math]::Round($peakWS/1MB,0); peakPriv_MiB=[math]::Round($peakPriv/1MB,0)
  freePhys_min_GiB=[math]::Round($minFree,2)
} | Format-List
