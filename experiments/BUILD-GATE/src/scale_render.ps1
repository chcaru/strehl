# Per-band gate-floor scale sweep at HEAD.
#
# STREHL_GATE_FLOOR_SCALE is a comma-separated per-band multiplier on the
# measured noise floor, band 0 first. It exists because --pyramid-gate takes a
# single number and cannot ask for more averaging at coarse scales while
# leaving the finest band alone -- which is exactly what a blotch-vs-sharpness
# conflict requires.
#
# THE NULL ARM IS NOT RENDERED. `1,1,1,1,1,1,1` was verified pixel-identical
# to the existing G200 masters (0 of 98,898,048 pixels differing on
# coffee-bubbles and 119MSDCF), with the comparator potency-checked against
# G200-vs-G160 (96.3% / 95.7% differing). The only file-level difference was
# the TIFF Software tag, which records the build ID. G200 is therefore the
# baseline and re-rendering it would only re-measure the same pixels.
#
# Subject order is deliberate: bee-1-cpl and flower-bud-alone-cpl are scored
# first because bee-1-cpl is the only subject whose sharpness column decouples
# from grain (r=+0.617 against +0.933..+0.997 elsewhere), so it is the only one
# where "flat sharpness, falling blotch" can be told apart from "less grain".
# The binary writes its banner to stderr, and `$ErrorActionPreference = "Stop"`
# turns any native stderr output into a terminating NativeCommandError. Render
# failures are detected explicitly below by testing for the output file, which
# is the condition that actually matters.
$ErrorActionPreference = "Continue"
$BIN = "C:\dev\strehl-wt\BG-scale\target\release\strehl.exe"
$ROOT = "C:\dev\strehl-out\BUILD-GATE\scale\ab"
$SRC = "D:\personal\macro"

$arms = @(
  @{ name = "S04";   scale = "1,4,4,4,4,4,4" },
  @{ name = "S08";   scale = "1,8,8,8,8,8,8" },
  @{ name = "S16";   scale = "1,16,16,16,16,16,16" },
  @{ name = "SRAMP"; scale = "1,1,4,16,32,32,32" },
  @{ name = "S32";   scale = "1,32,32,32,32,32,32" },
  # The band-1 decomposition. SRAMP scales bands 2-6 HARDER than S04 (4/16/32
  # vs 4) yet gets less blotch reduction on 4 of 5 subjects; the only band it
  # does not scale is band 1. These two arms turn that inference into a
  # measurement: B1ONLY scales band 1 alone, NOB1 scales everything except
  # band 1. If the mottle is a band-1 artifact, B1ONLY carries most of S32's
  # benefit and NOB1 carries little.
  @{ name = "B1ONLY"; scale = "1,32,1,1,1,1,1" },
  @{ name = "NOB1";   scale = "1,1,32,32,32,32,32" }
)
$subjects = @("bee-1-cpl", "flower-bud-alone-cpl",
              "119MSDCF", "109MSDCF", "coffee-bubbles")

New-Item -ItemType Directory -Force -Path $ROOT | Out-Null
Remove-Item Env:\STREHL_GATE_FLOOR -ErrorAction SilentlyContinue

foreach ($s in $subjects) {
  foreach ($a in $arms) {
    $dir = Join-Path $ROOT $a.name
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $out = Join-Path $dir "$s.tiff"
    # A run interrupted mid-write leaves a short TIFF that `Test-Path` happily
    # accepts, and it would then be scored as a finished render. Require the
    # file to be at least 90% of the baseline master's size before trusting it.
    $ref = Join-Path "C:\dev\strehl-out\BUILD-GATE\head\ab\G200" "$s.tiff"
    if (Test-Path $out) {
      $min = if (Test-Path $ref) { (Get-Item $ref).Length * 0.9 } else { 1MB }
      if ((Get-Item $out).Length -ge $min) {
        Write-Output "$($a.name)/$s already rendered"; continue
      }
      Write-Output "$($a.name)/$s TRUNCATED ($((Get-Item $out).Length) bytes), re-rendering"
      Remove-Item $out -Force
    }
    $env:STREHL_GATE_FLOOR_SCALE = $a.scale
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $log = & $BIN stack (Join-Path $SRC $s) --out $out --srgb --auto-exposure `
             --merge pyramid --pyramid-gate 2.0 2>&1
    $sw.Stop()
    if (-not (Test-Path $out)) {
      Write-Output "$($a.name)/$s RENDER FAILED"; $log | Select-Object -Last 8; continue
    }
    $log | Out-File (Join-Path $dir "$s.log")
    # The banner is kept as evidence the knob turned. `averaged` is a duty
    # cycle, not a quality metric, and is not reported as a result.
    $av = ($log | Select-String -Pattern '^averaged' | Select-Object -First 1)
    $avs = if ($av) { "$av" -replace '\s+', ' ' } else { "(no averaged line)" }
    Write-Output ("{0,-6} {1,-22} {2,7:N1}s  {3}" -f $a.name, $s, $sw.Elapsed.TotalSeconds, $avs)
  }
  Write-Output "---- $s complete ----"
}
Remove-Item Env:\STREHL_GATE_FLOOR_SCALE -ErrorAction SilentlyContinue
Write-Output "SCALE SWEEP COMPLETE"
