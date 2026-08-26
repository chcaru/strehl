$ErrorActionPreference = "Continue"
$dir = "C:\dev\blog\death-of-software\projects\strehl\experiments\V-bestframe"
$out = "C:\dev\strehl-out\V-BESTFRAME"
Set-Location $dir
# ORCH called these two out by name: they get the same depth as the headline pair.
$deep = @("highly-angled-ruler-mm-cpl", "lead-1-cpl")
$done = @("flowers-cpl", "bee-1-cpl")
$subj = Get-ChildItem "C:\dev\strehl-out\GALLERY-FIXED-SRGB\*.tiff" | ForEach-Object { $_.BaseName }
foreach ($s in $subj) {
    if ($done -contains $s) { "SKIP $s (already measured at 10 pairs)" | Tee-Object -Append "$out\survey.log"; continue }
    $n = if ($deep -contains $s) { 10 } else { 6 }
    "=== $s  ($n pairs)  $(Get-Date -Format HH:mm:ss)" | Tee-Object -Append "$out\survey.log"
    & python paircov.py $s --pairs $n *>> "$out\survey.log"
    "   paircov exit $LASTEXITCODE" | Tee-Object -Append "$out\survey.log"
    & python fpn.py $s --k 0 --gap 60 *>> "$out\survey.log"
    "   fpn exit $LASTEXITCODE" | Tee-Object -Append "$out\survey.log"
}
"SURVEY COMPLETE $(Get-Date -Format HH:mm:ss)" | Tee-Object -Append "$out\survey.log"
