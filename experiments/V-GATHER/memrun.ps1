param([string]$Arm, [string]$Fullres, [string]$Resampler = "catmull-rom", [string]$Subject = "109MSDCF")
$OUT = "C:\dev\strehl-out\V-GATHER\esf"
$env:STREHL_ALIGN = "1"
$env:STREHL_FULLRES_GATHER = $Fullres
$env:STREHL_FIX_CA = "off"
$env:STREHL_CACHE_DIR = "$OUT\warpcache-$Resampler"
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
$tif = "$OUT\mem-$Subject--$Arm.tif"
$so  = "$OUT\mem-$Subject--$Arm.out.log"
$se  = "$OUT\mem-$Subject--$Arm.err.log"
$os = Get-CimInstance Win32_OperatingSystem
$freeBefore = [math]::Round($os.FreePhysicalMemory/1MB,2)
$sw = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath "C:\dev\strehl-out\V-GATHER\strehl-pinned.exe" `
  -ArgumentList @("stack", "D:\personal\macro\$Subject", "--out", $tif, "--gate", "0", "--resampler", $Resampler) `
  -NoNewWindow -PassThru -RedirectStandardOutput $so -RedirectStandardError $se
$peakWS = 0; $peakPriv = 0; $minFree = 999999
while (-not $proc.HasExited) {
  try { $proc.Refresh()
        if ($proc.PeakWorkingSet64 -gt $peakWS) { $peakWS = $proc.PeakWorkingSet64 }
        if ($proc.PeakPagedMemorySize64 -gt $peakPriv) { $peakPriv = $proc.PeakPagedMemorySize64 }
  } catch {}
  $f = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
  if ($f -lt $minFree) { $minFree = $f }
  Start-Sleep -Milliseconds 250
}
$proc.WaitForExit()
$sw.Stop()
[pscustomobject]@{
  arm=$Arm; fullres=$Fullres; rc=$proc.ExitCode; wall_s=[math]::Round($sw.Elapsed.TotalSeconds,1)
  peakWS_MiB=[math]::Round($peakWS/1MB,0); peakPriv_MiB=[math]::Round($peakPriv/1MB,0)
  freePhys_before_GiB=[math]::Round($freeBefore,2); freePhys_min_GiB=[math]::Round($minFree,2)
} | Format-List
