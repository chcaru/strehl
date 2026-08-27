# P40 -- does the DEFAULT-ON defect correction render every corpus stack?
#
# WHY THIS EXISTS.  The geometry guard was exact-equality and hard-failed 11 of
# 26 stacks (P39).  That was found by running the binary on ONE stack that
# happened to be in the failing bucket.  "I fixed it" is not a measurement; the
# only statement worth making about a default-ON feature is that every stack in
# the corpus renders, and that requires rendering every stack in the corpus.
#
# PARTITION: every stack lands in exactly one bucket -- rendered-and-corrected,
# rendered-and-skipped, or failed -- and the buckets are asserted to sum to the
# number examined.  "0 failures" must be distinguishable from "0 attempted".
#
# --limit 8 because the preflight samples 8 frames and the geometry guard, the
# validator and the correction all run identically at 8 as at 105; what is NOT
# exercised at 8 is the long-bracket fold, which is not what this measures.

$ErrorActionPreference = "Continue"   # a native tool writing to stderr is not a
                                      # PowerShell error; with "Stop" the first
                                      # banner line aborts the sweep.
$repo = "C:\dev\blog\death-of-software\projects\strehl"
$lib = "D:\personal\macro"
$out = "C:\dev\strehl-out\BUILD-DEFECT\corpus"
$exe = Join-Path $repo ".cargo-target-defect\release\strehl.exe"

New-Item -ItemType Directory -Force -Path $out | Out-Null
$env:CARGO_TARGET_DIR = ".cargo-target-defect"
$env:STREHL_ALIGN = "0"
$env:STREHL_CACHE_DIR = Join-Path $out "cache"

$stacks = Get-ChildItem -Directory $lib | Where-Object { (Get-ChildItem $_.FullName -Filter *.ARW | Measure-Object).Count -gt 0 } | Sort-Object Name

$examined = 0; $corrected = 0; $skipped = 0; $failed = 0
$rows = @()

foreach ($s in $stacks) {
    $examined++
    $log = Join-Path $out "$($s.Name).log"
    & $exe stack $s.FullName --merge pyramid --limit 8 --out (Join-Path $out "$($s.Name).tif") *> $log
    $code = $LASTEXITCODE
    $sites = (Select-String -Path $log -Pattern "^sites           : " | Select-Object -First 1).Line
    if ($null -ne $sites) { $sites = $sites -replace "^sites           : ", "" } else { $sites = "(no banner)" }
    $chg = (Select-String -Path $log -Pattern "^samples changed : " | Select-Object -First 1).Line
    if ($null -ne $chg) { $chg = ($chg -replace "^samples changed : ", "") -replace " over.*", "" } else { $chg = "0" }

    if ($code -ne 0) {
        $failed++
        $err = (Select-String -Path $log -Pattern "^Error|^Caused by" -Context 0, 1 | Select-Object -First 1)
        $rows += [pscustomobject]@{ stack = $s.Name; verdict = "FAILED"; sites = $sites; samples = "-"; note = "$err" }
    }
    elseif ($chg -eq "0") {
        $skipped++
        $rows += [pscustomobject]@{ stack = $s.Name; verdict = "skipped"; sites = $sites; samples = "0"; note = "" }
    }
    else {
        $corrected++
        $rows += [pscustomobject]@{ stack = $s.Name; verdict = "CORRECTED"; sites = $sites; samples = $chg; note = "" }
    }
    Remove-Item (Join-Path $out "$($s.Name).tif") -ErrorAction SilentlyContinue
}

""
"{0,-38} {1,-10} {2,-9} {3}" -f "stack", "verdict", "samples", "sites"
"-" * 130
foreach ($r in $rows) { "{0,-38} {1,-10} {2,-9} {3}" -f $r.stack, $r.verdict, $r.samples, $r.sites }
foreach ($r in $rows) { if ($r.verdict -eq "FAILED") { "  ! $($r.stack): $($r.note)" } }
""
"examined $examined = corrected $corrected + skipped $skipped + failed $failed"
$sum = $corrected + $skipped + $failed
if ($sum -ne $examined) { "PARTITION VIOLATED: $sum != $examined"; exit 2 }
if ($failed -gt 0) { "VERDICT: RED -- $failed of $examined stacks cannot be rendered with the default-ON correction"; exit 1 }
"VERDICT: GREEN -- every corpus stack renders with the correction on by default"
exit 0
