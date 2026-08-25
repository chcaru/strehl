$exe   = "C:\dev\strehl-out\M117-tree\target\release\strehl.exe"
$stack = "D:\personal\macro\lavendar-cpl"
$out   = "C:\dev\strehl-out\M117\rerun"
$cache = "$out\cache-private"
Remove-Item -Recurse -Force $out -EA SilentlyContinue
New-Item -ItemType Directory -Force -Path $cache | Out-Null
Remove-Item Env:STREHL_ALIGN, Env:STREHL_FIX_HALO, Env:STREHL_WARPMAP, Env:STREHL_SMOOTH, Env:STREHL_SMOOTH_HUBER -EA SilentlyContinue
$env:STREHL_CACHE_DIR = $cache
$sw = [Diagnostics.Stopwatch]::StartNew()
$o = & $exe stack $stack --srgb --auto-exposure --gate 4 --out "$out\lavendar-g4.tif" 2>&1
$c = $LASTEXITCODE
$sw.Stop()
$o | Out-String | Set-Content -Encoding utf8 "$out\lavendar-g4.log"
Write-Output "exit=$c  elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,1))s"
Write-Output "SHA-256/16 = $((Get-FileHash "$out\lavendar-g4.tif" -Algorithm SHA256).Hash.Substring(0,16))"
Write-Output ($o | Select-String -Pattern "alignment|exposure=|placed" | Out-String).Trim()
Write-Output "cache entries written: $((Get-ChildItem $cache -Filter *.warpmap.txt -EA SilentlyContinue).Count)"
Get-ChildItem $cache -Filter *.warpmap.txt -EA SilentlyContinue | ForEach-Object {
  Write-Output "  $($_.Name)  sha=$((Get-FileHash $_.FullName -Algorithm SHA256).Hash.Substring(0,16))"
}
$env:STREHL_CACHE_DIR = $null
