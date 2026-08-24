# Render the angled-ruler bracket both ways for the straightness ground truth.
#
# The sidecar is solved OUTSIDE the corpus with --out and consumed through
# STREHL_WARPMAP, because align's default sidecar path writes into the stack
# directory and D:\personal\macro is read-only. The stray-sidecar count under
# D:\personal\macro is asserted unchanged at the end.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$stack = "D:\personal\macro\highly-angled-ruler-mm-cpl"
$out = "C:\dev\strehl-out\M97"
$map = "$out\warpmap-angruler.txt"

$before = (Get-ChildItem 'D:\personal\macro' -Recurse -Filter warpmap.txt).Count
"corpus sidecars before: $before"

# Solve unconditionally. An earlier version of this script skipped the solve
# when the target existed, and picked up a stale sidecar fitted on the OTHER
# ruler stack -- check_stack refused it, which is the behaviour working, but
# the near-miss is why this is no longer conditional. Names are prefixed
# "angruler" so the earlier flat-on-ruler artefacts are not clobbered.
"=== SOLVE ==="
# --force-tilted is REQUIRED here and the reason matters. The solver refuses
# this stack by design: "its subject is not normal to the optical axis, so
# focus change moves different parts of the frame by different amounts and no
# single similarity describes it. The sidecar would be confidently wrong."
# The steep angle is exactly what makes the ruler decisive as a TARGET and
# exactly what makes a global similarity the wrong MODEL. Forcing it does not
# measure "does alignment improve the render"; it measures "does the
# similarity model, applied where the project says it does not hold, still
# straighten a line that is straight by construction". That is a real question
# and the refusal is on trial with it.
& $exe align $stack --out $map --force-tilted 2>&1 | Tee-Object "$out\angruler-SOLVE.log" | Select-Object -Last 14
"solve rc=$LASTEXITCODE"

$env:STREHL_WARPMAP = $map
foreach ($arm in @("ALIGNED", "ZOOMNULL")) {
    "=== $arm ==="
    if ($arm -eq "ZOOMNULL") { $env:STREHL_ALIGN = "zoom" } else { Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $exe stack $stack --gate 2 --srgb --demosaic -o "$out\angruler-$arm.tif" 2>&1 |
        Tee-Object "$out\angruler-$arm.log" | Select-Object -Last 6
    $sw.Stop()
    "$arm rc=$LASTEXITCODE  elapsed $([math]::Round($sw.Elapsed.TotalSeconds,1))s"
}

$after = (Get-ChildItem 'D:\personal\macro' -Recurse -Filter warpmap.txt).Count
"corpus sidecars after: $after"
if ($after -ne $before) { "CORPUS POLLUTED: $before -> $after" } else { "corpus clean" }
Get-ChildItem "$out\angruler-*.tif" | Select-Object Name, Length | Format-Table -AutoSize
