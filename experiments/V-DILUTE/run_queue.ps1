# V-DILUTE render queue. Pin binary only. Always names --merge pyramid explicitly,
# because the CLI infers the ESTIMATOR backend from any estimator-only flag.
$exe  = "C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
$runs = "C:\dev\strehl-out\V-DILUTE\runs"
$stk  = "C:\dev\strehl-out\V-DILUTE\stacks"
$bee  = "D:\personal\macro\bee-3-cpl"
New-Item -ItemType Directory -Force -Path $runs | Out-Null
$summary = "$runs\_queue_summary.txt"

function Run-Arm {
  param([string]$Tag, [string]$Dir, [string[]]$Extra = @(), [int]$Limit = 0, [bool]$Conf = $true)
  $o = "$runs\$Tag.tif"
  if (Test-Path $o) { Add-Content $summary "[$Tag] SKIP (exists)"; return }
  $a = @('stack', $Dir, '--merge', 'pyramid', '--out', $o)
  if ($Limit -gt 0) { $a += @('--limit', "$Limit") }
  if ($Conf) { $a += @('--confidence-map', "$runs\${Tag}_conf.tif") }
  $a += $Extra
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $out = & $exe @a 2>&1
  $sw.Stop()
  $out | Set-Content "$runs\$Tag.log"
  $mean = ($out | Select-String -Pattern 'mean .* over the').Line
  $avg  = ($out | Select-String -Pattern '^averaged').Line
  $dim  = ($out | Select-String -Pattern '^wrote').Line
  Add-Content $summary "[$Tag] $([math]::Round($sw.Elapsed.TotalSeconds,1))s | $mean"
  Add-Content $summary "        $avg"
  Add-Content $summary "        $dim"
}

Add-Content $summary "=== queue start $(Get-Date -Format o) ==="

# --- Experiment B: equal-N decimation (ORCH's priority) ---
Run-Arm -Tag 'B_step2_n150'   -Dir "$stk\beeB_step2"
Run-Arm -Tag 'B_first150_n150' -Dir $bee -Limit 150
Run-Arm -Tag 'B_dup300_n300'  -Dir "$stk\beeB_dup300"

# --- Experiment A: confidence vs N, with committed/averaged brackets at the ends ---
Run-Arm -Tag 'A_n299_default' -Dir $bee
Run-Arm -Tag 'A_n299_hardmax' -Dir $bee -Extra @('--pyramid-select','hard-max')
Run-Arm -Tag 'A_n299_meanarm' -Dir $bee -Extra @('--pyramid-exponent','0.05','--pyramid-sharpen','1.0')
Run-Arm -Tag 'A_n63_default'  -Dir "$stk\beeN63"
Run-Arm -Tag 'A_n63_hardmax'  -Dir "$stk\beeN63" -Extra @('--pyramid-select','hard-max')
Run-Arm -Tag 'A_n63_meanarm'  -Dir "$stk\beeN63" -Extra @('--pyramid-exponent','0.05','--pyramid-sharpen','1.0')
Run-Arm -Tag 'A_n33_default'  -Dir "$stk\beeN33"
Run-Arm -Tag 'A_n105_default' -Dir "$stk\beeN105"

# --- Experiment C: exponent sweep on bee at N=299 (no confidence map needed) ---
Run-Arm -Tag 'C_e0p5_s1p4' -Dir $bee -Conf $false -Extra @('--pyramid-exponent','0.5','--pyramid-sharpen','1.4')
Run-Arm -Tag 'C_e1_s1p4'   -Dir $bee -Conf $false -Extra @('--pyramid-exponent','1.0','--pyramid-sharpen','1.4')
Run-Arm -Tag 'C_e4_s1p4'   -Dir $bee -Conf $false -Extra @('--pyramid-exponent','4.0','--pyramid-sharpen','1.4')
Run-Arm -Tag 'C_e8_s1p0'   -Dir $bee -Conf $false -Extra @('--pyramid-exponent','8.0','--pyramid-sharpen','1.0')

Add-Content $summary "=== queue done $(Get-Date -Format o) ==="
