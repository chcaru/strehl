$ErrorActionPreference = "Continue"
$dir = "C:\dev\blog\death-of-software\projects\strehl\experiments\V-bestframe"
$out = "C:\dev\strehl-out\V-BESTFRAME-SHIP"
New-Item -ItemType Directory -Force -Path $out | Out-Null
New-Item -ItemType Directory -Force -Path "$out\images" | Out-Null
Set-Location $dir
$env:VBF_GAL = "C:\dev\strehl-out\SHIP-V1"
$env:VBF_OUT = $out
# Depths matched to the GALLERY-FIXED-SRGB run so the diff is like-for-like.
$deep = @("highly-angled-ruler-mm-cpl", "lead-1-cpl", "flowers-cpl", "bee-1-cpl")
# Control gaps matched to the GALLERY-FIXED-SRGB run, subject by subject.
$gap = @{ "109MSDCF" = 21; "119MSDCF" = 32; "coffee-bubbles" = 18;
          "flower-bud-alone-cpl" = 200 }
$subj = Get-ChildItem "C:\dev\strehl-out\SHIP-V1\*.tiff" | ForEach-Object { $_.BaseName }
foreach ($s in $subj) {
    $n = if ($deep -contains $s) { 10 } else { 6 }
    $g = if ($gap.ContainsKey($s)) { $gap[$s] } else { 60 }
    "=== $s  ($n pairs, fpn gap $g)  $(Get-Date -Format HH:mm:ss)" | Tee-Object -Append "$out\survey.log"
    & python paircov.py $s --pairs $n *>> "$out\survey.log"
    "   paircov exit $LASTEXITCODE" | Tee-Object -Append "$out\survey.log"
    & python fpn.py $s --k 0 --gap $g *>> "$out\survey.log"
    "   fpn exit $LASTEXITCODE" | Tee-Object -Append "$out\survey.log"
}
"SHIP SURVEY COMPLETE $(Get-Date -Format HH:mm:ss)" | Tee-Object -Append "$out\survey.log"
