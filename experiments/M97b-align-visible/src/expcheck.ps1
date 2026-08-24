$ErrorActionPreference = "Continue"
$exe  = "C:\dev\strehl-target-m97\release\strehl.exe"
$src  = "D:\personal\macro\bee-3-cpl"
$out  = "C:\dev\strehl-out\M97\freeze"
$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\M97\cache"
Remove-Item Env:\STREHL_ALIGN, Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue

# M100 fixture EXACTLY as recorded in its 3.3: --limit 60, no --gate, aligned default.
$arms = @(
  @{ n = "A-default";     a = @() },
  @{ n = "B-srgb";        a = @("--srgb") },
  @{ n = "C-srgb-exp0";   a = @("--srgb", "--exposure", "0") },
  @{ n = "D-srgb-exp0.5"; a = @("--srgb", "--exposure", "0.5") }
)

$res = @{}
foreach ($arm in $arms) {
  $f = Join-Path $out ("exp-" + $arm.n + ".tif")
  if (Test-Path $f) { Remove-Item $f }
  $argv = @("stack", $src, "--limit", "60", "--out", $f) + $arm.a
  & $exe @argv 2>$null | Out-Null
  if (-not (Test-Path $f)) { throw ("no output for " + $arm.n) }
  $h = (Get-FileHash $f -Algorithm SHA256).Hash
  $res[$arm.n] = $h
  "{0,-16} {1}" -f $arm.n, $h.Substring(0, 16)
}

""
"---- pre-registered bars ----"
$FREEZE = "54A5E20F"
$b1 = $res["A-default"].StartsWith($FREEZE)
"BAR 1  byte-freeze, default render starts 54A5E20F : {0}" -f $(if ($b1) { "PASS" } else { "FAIL -> " + $res["A-default"].Substring(0,16) })

$b2 = ($res["C-srgb-exp0"] -eq $res["B-srgb"])
"BAR 2  --exposure 0 identical to plain --srgb       : {0}" -f $(if ($b2) { "PASS" } else { "FAIL" })

$b3 = ($res["D-srgb-exp0.5"] -ne $res["B-srgb"])
"BAR 3  PLANT: --exposure 0.5 MUST move the file     : {0}" -f $(if ($b3) { "PASS" } else { "FAIL - flag is being ignored; BAR 2 is then vacuous" })

""
if ($b1 -and $b2 -and $b3) { "ALL BARS PASS - exposure is wired and reaches pixels; freeze intact." }
else { "AT LEAST ONE BAR FAILED" }
