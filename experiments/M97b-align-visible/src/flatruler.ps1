# The DISCRIMINATING arm. Same instrument, same two treatments, on the ruler
# stack the aligner ACCEPTS.
#
# Why this run exists. The angled ruler is refused by the solver as a tilted
# subject and had to be forced with --force-tilted. So any result on it is
# ambiguous between two very different claims:
#   (a) the sidecar's per-frame warps are too imprecise to help anywhere, or
#   (b) forcing the similarity model onto a stack where the project says it
#       does not hold injects error -- i.e. the refusal is CORRECT.
# `flat-on-ruler-cpl` is normal to the optical axis, so the solver accepts it
# with no override. If alignment helps here and hurts on the angled stack, the
# answer is (b) and the refusal check is vindicated by measurement. If it hurts
# here too, the answer is (a) and that is a much larger negative result.
#
# Names are prefixed "flatruler-" so the earlier "ruler-*" artefacts from the
# first M97 session are not clobbered.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$stack = "D:\personal\macro\flat-on-ruler-cpl"
$out = "C:\dev\strehl-out\M97"
$map = "$out\warpmap-flatruler.txt"

$before = (Get-ChildItem 'D:\personal\macro' -Recurse -Filter warpmap.txt).Count
"corpus sidecars before: $before"

"=== SOLVE (no --force-tilted: this stack must be accepted on its own) ==="
& $exe align $stack --out $map 2>&1 | Tee-Object "$out\flatruler-SOLVE.log" | Select-Object -Last 14
"solve rc=$LASTEXITCODE"

$env:STREHL_WARPMAP = $map
foreach ($arm in @("ALIGNED", "ZOOMNULL")) {
    "=== $arm ==="
    if ($arm -eq "ZOOMNULL") { $env:STREHL_ALIGN = "zoom" } else { Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $exe stack $stack --gate 2 --srgb --demosaic -o "$out\flatruler-$arm.tif" 2>&1 |
        Tee-Object "$out\flatruler-$arm.log" | Select-Object -Last 6
    $sw.Stop()
    "$arm rc=$LASTEXITCODE  elapsed $([math]::Round($sw.Elapsed.TotalSeconds,1))s"
}

$after = (Get-ChildItem 'D:\personal\macro' -Recurse -Filter warpmap.txt).Count
"corpus sidecars after: $after"
if ($after -ne $before) { "CORPUS POLLUTED: $before -> $after" } else { "corpus clean" }
Get-ChildItem "$out\flatruler-*.tif" | Select-Object Name, Length | Format-Table -AutoSize
