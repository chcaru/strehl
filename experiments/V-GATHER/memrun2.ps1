# Peak-memory harness for the SHIPPING default command line.
#   stack <DIR> --out <FILE> --srgb --auto-exposure     (default merge backend)
# Measures the strehl process's own PeakPagedMemorySize64 (private commit),
# which -- unlike PeakWorkingSet64 -- is not trimmed by Windows under pressure.
param([string]$Subject, [string]$Fullres, [int]$Limit = 0, [string]$Tag = "ship")
$OUT = "C:\dev\strehl-out\V-GATHER\mem"
New-Item -ItemType Directory -Force -Path $OUT | Out-Null
$env:STREHL_FULLRES_GATHER = $Fullres
$env:STREHL_FIX_CA = "off"
$env:STREHL_CACHE_DIR = "$OUT\warpcache"
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_ALIGN  -ErrorAction SilentlyContinue
$name = "$Tag-$Subject-g$Fullres" + $(if ($Limit -gt 0) { "-n$Limit" } else { "-all" })
$tif = "$OUT\$name.tif"; $so = "$OUT\$name.out.log"; $se = "$OUT\$name.err.log"
$argl = @("stack", "D:\personal\macro\$Subject", "--out", $tif, "--srgb", "--auto-exposure")
if ($Limit -gt 0) { $argl += @("--limit", "$Limit") }
$freeBefore = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
$sw = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath "C:\dev\strehl-out\V-GATHER\strehl-pinned.exe" `
  -ArgumentList $argl -NoNewWindow -PassThru -RedirectStandardOutput $so -RedirectStandardError $se
$peakWS = 0; $peakPriv = 0; $minFree = 999999.0; $samples = 0
while (-not $proc.HasExited) {
  try { $proc.Refresh()
        if ($proc.PeakWorkingSet64      -gt $peakWS)   { $peakWS   = $proc.PeakWorkingSet64 }
        if ($proc.PeakPagedMemorySize64 -gt $peakPriv) { $peakPriv = $proc.PeakPagedMemorySize64 }
  } catch {}
  $f = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
  if ($f -lt $minFree) { $minFree = $f }
  $samples++
  Start-Sleep -Milliseconds 250
}
$proc.WaitForExit(); $sw.Stop()
[pscustomobject]@{
  name=$name; subject=$Subject; fullres=$Fullres; limit=$Limit
  rc=$proc.ExitCode; rc_hex=("0x{0:X8}" -f $proc.ExitCode)
  wall_s=[math]::Round($sw.Elapsed.TotalSeconds,1)
  peakWS_MiB=[math]::Round($peakWS/1MB,0)
  peakPriv_MiB=[math]::Round($peakPriv/1MB,0)
  freePhys_before_GiB=[math]::Round($freeBefore,2)
  freePhys_min_GiB=[math]::Round($minFree,2)
  samples=$samples
} | Format-List
