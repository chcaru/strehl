# The white-vs-default A/B at HEAD, plus the re-tuned-k arms.
#
# ORCH's correction: on real (demosaiced) frames the measured floor is ABOVE
# the white constant, so the landed fix makes the gate STRICTER and a stricter
# gate averages more and softens more. That is the sign BUILD-GATE measured and
# it is now the expected one. The re-tuned-k arms therefore hunt DOWNWARD.
#
# Arms:
#   WHITE200  STREHL_GATE_FLOOR=white, k=2.0   the pre-fix shipping default
#   G200      default floor,           k=2.0   TODAY'S SHIPPING DEFAULT
#   G140      default floor,           k=1.4   re-tuned candidate
#   G100      default floor,           k=1.0   lower still
#
# One binary for every arm, built at HEAD in a disposable worktree so a build
# lane dirtying the shared tree cannot change it underneath the render.
$ErrorActionPreference = "Stop"
$BIN = "C:\dev\strehl-wt\BG-head\target\release\strehl.exe"
$ROOT = "C:\dev\strehl-out\BUILD-GATE\head\ab"
$SRC = "D:\personal\macro"

$arms = @(
  @{ name = "WHITE200"; gate = "2.0";  floor = "white" },
  @{ name = "G090";     gate = "0.9";  floor = "" },
  @{ name = "G100";     gate = "1.0";  floor = "" },
  @{ name = "G129";     gate = "1.29"; floor = "" },
  @{ name = "G140";     gate = "1.4";  floor = "" },
  @{ name = "G160";     gate = "1.6";  floor = "" },
  @{ name = "G200";     gate = "2.0";  floor = "" },
  @{ name = "G260";     gate = "2.6";  floor = "" }
)
$subjects = @("coffee-bubbles", "109MSDCF", "119MSDCF",
              "flower-bud-alone-cpl", "bee-1-cpl")

New-Item -ItemType Directory -Force -Path $ROOT | Out-Null
foreach ($s in $subjects) {
  foreach ($a in $arms) {
    $dir = Join-Path $ROOT $a.name
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $out = Join-Path $dir "$s.tiff"
    if (Test-Path $out) { Write-Output "$($a.name)/$s already rendered"; continue }
    if ($a.floor) { $env:STREHL_GATE_FLOOR = $a.floor }
    else { Remove-Item Env:\STREHL_GATE_FLOOR -ErrorAction SilentlyContinue }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $log = & $BIN stack (Join-Path $SRC $s) --out $out --srgb --auto-exposure --merge pyramid --pyramid-gate $a.gate 2>&1
    $sw.Stop()
    if (-not (Test-Path $out)) {
      Write-Output "$($a.name)/$s RENDER FAILED"; $log | Select-Object -Last 6; continue
    }
    # Keep the banner: the measured floor and the averaged-per-level line are
    # the potency evidence that the two floor arms genuinely differ. Runtime is
    # recorded because the measured floor probes every frame and costs ~1.9x.
    $log | Out-File (Join-Path $dir "$s.log")
    $xw = ($log | Select-String -Pattern 'x white' | Select-Object -First 1)
    $av = ($log | Select-String -Pattern '^averaged' | Select-Object -First 1)
    $xws = if ($xw) { "$xw" -replace '\s+', ' ' } else { "(white floor arm: no measured floor printed)" }
    $avs = if ($av) { "$av" -replace '\s+', ' ' } else { "(no averaged line)" }
    Write-Output ("{0,-9} {1,-22} {2,7:N1}s" -f $a.name, $s, $sw.Elapsed.TotalSeconds)
    Write-Output ("          " + $xws)
    Write-Output ("          " + $avs)
  }
}
Remove-Item Env:\STREHL_GATE_FLOOR -ErrorAction SilentlyContinue
Write-Output "AB RENDER COMPLETE"
