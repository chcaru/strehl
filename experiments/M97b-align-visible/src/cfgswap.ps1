$ErrorActionPreference = "Continue"
$exe  = "C:\dev\strehl-target-m97\release\strehl.exe"
$src  = "D:\personal\macro\flat-on-ruler-cpl"
$a    = "C:\dev\strehl-out\M97\warpmap-flatruler.txt"          # reference 0
$b    = "C:\dev\strehl-out\M97\warpmap-flatruler-ref40.txt"    # reference 40, SAME 79 frames
$out  = "C:\dev\strehl-out\M97\freeze"
$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\M97\cache"
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue

if (-not (Test-Path $b)) {
  "solving second sidecar: same 79 frames, --reference 40 ..."
  & $exe align $src --limit 79 --reference 40 --out $b 2>&1 | Out-Null
  "  rc=$LASTEXITCODE  exists=" + (Test-Path $b)
}
""
"sidecar A: " + ((Select-String -Path $a -Pattern '^(frames|reference)\s' | ForEach-Object { $_.Line }) -join "  ")
"sidecar B: " + ((Select-String -Path $b -Pattern '^(frames|reference)\s' | ForEach-Object { $_.Line }) -join "  ")
""

$h = @{}
foreach ($arm in @(@{n="A-ref0";p=$a}, @{n="B-ref40";p=$b})) {
  $f = Join-Path $out ("cfg-" + $arm.n + ".tif")
  if (Test-Path $f) { Remove-Item $f }
  $env:STREHL_WARPMAP = $arm.p
  $txt = & $exe stack $src --limit 79 --out $f 2>&1 | Out-String
  $rc = $LASTEXITCODE
  Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
  $al = ($txt -split "`n" | Where-Object { $_ -match 'alignment\s+:' }) -join ""
  $ok = Test-Path $f
  $h[$arm.n] = $(if ($ok) { (Get-FileHash $f -Algorithm SHA256).Hash } else { "NO-OUTPUT" })
  "{0,-8} rc={1} accepted={2}  {3}" -f $arm.n, $rc, $ok, $al.Trim()
  "         sha256 {0}" -f $h[$arm.n].Substring(0, [Math]::Min(16, $h[$arm.n].Length))
}

""
"---- bars ----"
$accepted = ($h["A-ref0"] -ne "NO-OUTPUT") -and ($h["B-ref40"] -ne "NO-OUTPUT")
"BAR 1  both sidecars accepted on the same bracket  : {0}" -f $(if ($accepted) { "YES -> digest does NOT cover solve config" } else { "NO  -> digest DOES cover solve config" })
$moved = $h["A-ref0"] -ne $h["B-ref40"]
"BAR 2  PLANT: the two renders must differ          : {0}" -f $(if ($moved) { "PASS - config change is not inert" } else { "FAIL - config change inert, BAR 1 vacuous" })
""
if ($accepted -and $moved) { "HAZARD CONFIRMED: same frame set + different solve config = silent swap, no warning." }
elseif (-not $accepted)    { "HAZARD ABSENT: solve config is covered by the identity check." }
else                       { "INCONCLUSIVE: plant did not fire." }
