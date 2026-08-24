# M100 behavioural bars, re-run at current HEAD + the orchestrator's application
# of the patch. Predictions are pre-registered in the session transcript and in
# the table below; this script only measures.
# NOT "Stop": strehl writes its report to stderr, and under Stop PowerShell
# turns any native stderr line into a terminating error. Failures here are
# checked explicitly instead.
$ErrorActionPreference = "Continue"
$s = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-orch\release\strehl.exe"
$dir = "D:\personal\macro\bee-3-cpl"
$o = "$env:TEMP\M100-bars"
New-Item -ItemType Directory -Force -Path $o | Out-Null

$expect = @{
  "P1-default"      = "54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2"
  "P2-srgb-binned"  = "EB1E0FE7DEE6D63FE1522C6C44B1AB1F13FDB349E4915C4C5261A4F4B1AE4D25"
  "P3-srgb"         = "18F5702463C56853C04A4DAE87E4F3315E16C13579A8988875AAE63FFD4D6840"
  "P4-srgb-exp0"    = "18F5702463C56853C04A4DAE87E4F3315E16C13579A8988875AAE63FFD4D6840"
}

$runs = @(
  @{ n = "P1-default";     a = @() },
  @{ n = "P2-srgb-binned"; a = @("--srgb", "--binned") },
  @{ n = "P3-srgb";        a = @("--srgb") },
  @{ n = "P4-srgb-exp0";   a = @("--srgb", "--exposure", "0") }
)

$results = @{}
foreach ($r in $runs) {
  $out = Join-Path $o "$($r.n).tif"
  $argv = @("stack", $dir, "--gate", "2", "--limit", "60", "--out", $out) + $r.a
  & $s @argv 2>&1 | Out-Null
  if (-not (Test-Path $out)) { throw "$($r.n): no output written" }
  $h = (Get-FileHash $out -Algorithm SHA256).Hash
  $results[$r.n] = $h
  $e = $expect[$r.n]
  $verdict = if ($h -eq $e) { "PASS" } else { "**FAIL**" }
  "{0,-16} {1} {2}" -f $r.n, $verdict, $h
  if ($h -ne $e) { "                 expected {0}" -f $e }
}

# P5: the auto-exposure round trip. Capture the printed flag and replay it.
""
"=== P5 auto-exposure round trip ==="
$out5 = Join-Path $o "P5-auto.tif"
$log = & $s stack $dir --srgb --auto-exposure --gate 2 --limit 60 --out $out5 2>&1 | Out-String
$line = ($log -split "`n" | Where-Object { $_ -match "reproduce this exact file with" })
$line.Trim()
if ($line -match "(--exposure=[-0-9.]+)") {
  $flag = $Matches[1]
  $out6 = Join-Path $o "P5-replay.tif"
  & $s stack $dir --srgb $flag --gate 2 --limit 60 --out $out6 2>&1 | Out-Null
  $h5 = (Get-FileHash $out5 -Algorithm SHA256).Hash
  $h6 = (Get-FileHash $out6 -Algorithm SHA256).Hash
  $v = if ($h5 -eq $h6) { "PASS" } else { "**FAIL**" }
  "round trip       $v  auto=$h5"
  "                     replay=$h6"
  "M100 recorded    BEF36AB8DD8E1C00D850BB640F5FAD1E8A5398758B9E952A87038A1B248E5577 (at --srgb=binned, pre-M95)"
} else {
  "**FAIL** no reproduce line printed"
}

""
"=== the advisory on a plain --srgb run ==="
($log2 = & $s stack $dir --srgb --gate 2 --limit 60 --out "$o\advisory.tif" 2>&1 | Out-String) | Out-Null
($log2 -split "`n" | Where-Object { $_ -match "exposure" }) | ForEach-Object { $_.TrimEnd() }
