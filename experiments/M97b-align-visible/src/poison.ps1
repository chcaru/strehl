$ErrorActionPreference = "Continue"
$exe  = "C:\dev\strehl-target-m97\release\strehl.exe"
$src  = "D:\personal\macro\flat-on-ruler-cpl"
$out  = "C:\dev\strehl-out\M97\freeze"
$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\M97\cache"
Remove-Item Env:\STREHL_ALIGN, Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue

# End-to-end: can `strehl align` with a non-default --reference and NO --out
# silently change what a later plain `strehl stack` renders, for everyone?
# No override is used anywhere below. This is the shared-cache path only.

Get-ChildItem "$env:STREHL_CACHE_DIR\flat-on-ruler-cpl-*.warpmap.txt" -EA SilentlyContinue | Remove-Item

"---- ARM 1: cache populated by default solve (align, no --reference, no --out) ----"
& $exe align $src --limit 79 2>&1 | Out-Null
$rc1 = $LASTEXITCODE
$f = (Get-ChildItem "$env:STREHL_CACHE_DIR\flat-on-ruler-cpl-*.warpmap.txt" | Select-Object -First 1)
"  align rc=$rc1  cache file: $($f.Name)"
"  cache says: " + ((Select-String -Path $f.FullName -Pattern '^(frames|reference)\s' | ForEach-Object { $_.Line }) -join "  ")
$t1 = Join-Path $out "poison-A.tif"
if (Test-Path $t1) { Remove-Item $t1 }
$o1 = & $exe stack $src --limit 79 --out $t1 2>&1 | Out-String
"  stack sees: " + (($o1 -split "`n" | Where-Object { $_ -match 'alignment\s+:' }) -join "").Trim()
$h1 = (Get-FileHash $t1 -Algorithm SHA256).Hash

""
"---- ARM 2: same command line, but cache poisoned by `align --reference 40` (still no --out) ----"
& $exe align $src --limit 79 --reference 40 2>&1 | Out-Null
$rc2 = $LASTEXITCODE
$f2 = (Get-ChildItem "$env:STREHL_CACHE_DIR\flat-on-ruler-cpl-*.warpmap.txt" | Select-Object -First 1)
"  align rc=$rc2  cache file: $($f2.Name)"
"  cache says: " + ((Select-String -Path $f2.FullName -Pattern '^(frames|reference)\s' | ForEach-Object { $_.Line }) -join "  ")
$t2 = Join-Path $out "poison-B.tif"
if (Test-Path $t2) { Remove-Item $t2 }
$o2 = & $exe stack $src --limit 79 --out $t2 2>&1 | Out-String
"  stack sees: " + (($o2 -split "`n" | Where-Object { $_ -match 'alignment\s+:' }) -join "").Trim()
$h2 = (Get-FileHash $t2 -Algorithm SHA256).Hash

""
"---- bars ----"
"  A sha256 " + $h1.Substring(0,16)
"  B sha256 " + $h2.Substring(0,16)
"BAR 1  same cache filename in both arms          : {0}" -f $(if ($f.Name -eq $f2.Name) { "YES - one entry, overwritten" } else { "NO - separate entries" })
"BAR 2  identical `strehl stack` command line     : YES (--limit 79, no override, no flags)"
"BAR 3  PLANT: rendered pixels must differ        : {0}" -f $(if ($h1 -ne $h2) { "PASS - poisoning reaches the image" } else { "FAIL - inert, finding is vacuous" })
"BAR 4  did stack warn about the swap?            : {0}" -f $(if ($o2 -match 'reject|re-solv|mismatch|WARN.*sidecar') { "yes - announced" } else { "NO - accepted silently" })
