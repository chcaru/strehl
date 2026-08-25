param([string]$Exe)
$stack = "D:\personal\macro\109MSDCF"
$root = "C:\dev\strehl-out\M117\guards"
Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $root | Out-Null
function Hash16([string]$p) { (Get-FileHash -Algorithm SHA256 -Path $p).Hash.Substring(0,16) }
$env:STREHL_WARPMAP=$null; $env:STREHL_ALIGN=$null

# ===== G1: STREHL_ALIGN=0 immunity =====
# clean cache, align=0
$c="$root\g1a"; New-Item -ItemType Directory -Force -Path $c|Out-Null; $env:STREHL_CACHE_DIR=$c
$env:STREHL_ALIGN="0"
$l1 = & $Exe stack $stack --limit 22 --gate 4.0 --out "$root\g1a.tiff" 2>&1 | Out-String
$g1a = Hash16 "$root\g1a.tiff"
$g1a_entries = (Get-ChildItem $c -Filter *.warpmap.txt -EA SilentlyContinue).Count
# poisoned cache, align=0
$c="$root\g1b"; New-Item -ItemType Directory -Force -Path $c|Out-Null; $env:STREHL_CACHE_DIR=$c
$env:STREHL_ALIGN=$null
& $Exe align $stack --limit 22 --reference 3 *>$null
$env:STREHL_ALIGN="0"
$l2 = & $Exe stack $stack --limit 22 --gate 4.0 --out "$root\g1b.tiff" 2>&1 | Out-String
$g1b = Hash16 "$root\g1b.tiff"
$env:STREHL_ALIGN=$null
Write-Output "G1 STREHL_ALIGN=0 : clean=$g1a poisoned=$g1b  IMMUNE=$($g1a -eq $g1b)  cacheWritesUnderAlign0=$g1a_entries"
Write-Output ($l1 -split "`n" | Select-String -Pattern "alignment" | Out-String).Trim()

# ===== G2: frame-count guard =====
# align all 22, then stack --limit 10 (different frame set)
$c="$root\g2"; New-Item -ItemType Directory -Force -Path $c|Out-Null; $env:STREHL_CACHE_DIR=$c
& $Exe align $stack --limit 22 --reference 3 *>$null
$l3 = & $Exe stack $stack --limit 10 --gate 4.0 --out "$root\g2.tiff" 2>&1 | Out-String
Write-Output "G2 frame-count mismatch (cache=22 frames, stack --limit 10):"
Write-Output ($l3 -split "`n" | Select-String -Pattern "alignment|sidecar|re-solv" | Out-String).Trim()

# ===== G3: same frame COUNT, different frame SET =====
# cache from 112MSDCF-like? use --limit 10 align on 109 then stack --limit 10 -> should HIT (same set)
$c="$root\g3"; New-Item -ItemType Directory -Force -Path $c|Out-Null; $env:STREHL_CACHE_DIR=$c
& $Exe align $stack --limit 10 --reference 2 *>$null
$l4 = & $Exe stack $stack --limit 10 --gate 4.0 --out "$root\g3.tiff" 2>&1 | Out-String
Write-Output "G3 matched --limit 10 align(ref 2) then stack --limit 10:"
Write-Output ($l4 -split "`n" | Select-String -Pattern "alignment" | Out-String).Trim()

# ===== G4: STREHL_WARPMAP bypass =====
$c="$root\g4"; New-Item -ItemType Directory -Force -Path $c|Out-Null; $env:STREHL_CACHE_DIR=$c
& $Exe align $stack --limit 22 --reference 3 --out "$root\side.txt" *>$null
$env:STREHL_WARPMAP="$root\side.txt"
$l5 = & $Exe stack $stack --limit 22 --gate 4.0 --out "$root\g4.tiff" 2>&1 | Out-String
$env:STREHL_WARPMAP=$null
Write-Output "G4 STREHL_WARPMAP override, cache entries written=$((Get-ChildItem $c -Filter *.warpmap.txt -EA SilentlyContinue).Count):"
Write-Output ($l5 -split "`n" | Select-String -Pattern "alignment" | Out-String).Trim()
$env:STREHL_CACHE_DIR=$null
