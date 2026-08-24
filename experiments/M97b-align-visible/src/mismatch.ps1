$ErrorActionPreference = "Continue"
$exe  = "C:\dev\strehl-target-m97\release\strehl.exe"
$src  = "D:\personal\macro\flat-on-ruler-cpl"
$side = "C:\dev\strehl-out\M97\warpmap-flatruler.txt"   # solved on 79 frames
$out  = "C:\dev\strehl-out\M97\freeze"
$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\M97\cache"
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue

"sidecar frame count: " + ((Select-String -Path $side -Pattern '^frames\s' | Select-Object -First 1).Line)
""

# CONTROL: sidecar frame count == run frame count. Must place 79.
# TREATMENT: sidecar solved on 79, run limited to 20. Mismatch.
# The question is whether the mismatch is announced or silently absorbed.
$arms = @(
  @{ n = "CONTROL  79-frame sidecar + 79-frame run"; lim = 79 },
  @{ n = "TREAT-A  79-frame sidecar + 20-frame run"; lim = 20 },
  @{ n = "TREAT-B  79-frame sidecar + 40-frame run"; lim = 40 }
)

foreach ($a in $arms) {
  "==== $($a.n) ===="
  $f = Join-Path $out ("mm-" + $a.lim + ".tif")
  if (Test-Path $f) { Remove-Item $f }
  $env:STREHL_WARPMAP = $side
  $err = & $exe stack $src --limit $a.lim --out $f 2>&1 | Out-String
  $rc = $LASTEXITCODE
  Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue

  $al = ($err -split "`n" | Where-Object { $_ -match 'alignment\s+:' }) -join " "
  $ex = ($err -split "`n" | Where-Object { $_ -match 'error|refus|mismatch|digest|does not|Error' }) -join " | "
  "  rc          : $rc"
  "  alignment   : " + $(if ($al) { $al.Trim() } else { "(no alignment line printed)" })
  if ($ex) { "  diagnostics : " + $ex.Trim() }
  "  wrote file  : " + (Test-Path $f)
  ""
}
