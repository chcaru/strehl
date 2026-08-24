# M109 cache-contamination control (ORCH fact 1446).
#
# fact 1446: StackIdentity keys the frame set but NOT `reference` and NOT
# `resampler`, so an identical command line can return bytes produced under
# different inputs depending on what ran earlier in the tree.
#
# ORCH's prescribed control runs `align --reference <other frame>` between the
# two arms. That is NOT run here: `strehl align` has a documented history of
# dropping warpmap.txt sidecars into the source directory (11 quarantined) and
# D:\personal\macro is strictly read-only. This substitutes a perturbation that
# exercises the same dependency without any write risk to the corpus --
# toggling whether the warpmap cache is VISIBLE at all:
#
#   arm A: STREHL_CACHE_DIR -> empty dir   => forced fresh solve
#   arm B: default cache                   => reuses the stored warpmap
#
# The perturbation is verified genuine by strehl's own stderr, which reports
# "(solved)" for A and "(sidecar)" for B, and by the runtime difference.
#
# Exit-code note (AGENTS.md rule 47): this script never reads $LASTEXITCODE
# after a filtering pipeline. It compares SHA-256 literals, not predicates.

$ErrorActionPreference = "Continue"

$Out   = "C:\dev\strehl-out\M109"
$Empty = Join-Path $Out "cache-empty"
$Stack = "D:\personal\macro\dry-erase-marker-head-cpl"

New-Item -ItemType Directory -Force -Path $Empty | Out-Null

function Invoke-Arm {
    param(
        [string]$Exe,
        [string[]]$StrehlArgs,
        [string]$OutTif,
        [switch]$HideCache
    )
    if ($HideCache) {
        # MUST be emptied every time. The forced-solve arm WRITES its freshly
        # solved warpmap into this directory, so on a second run the "hidden"
        # arm would read back its own output and report (sidecar) -- the
        # perturbation silently becomes inert. The inertness guard below caught
        # exactly this on the first run of this script.
        Remove-Item (Join-Path $Empty "*") -Force -Recurse -EA SilentlyContinue
        $env:STREHL_CACHE_DIR = $Empty
    }
    else { Remove-Item Env:\STREHL_CACHE_DIR -ErrorAction SilentlyContinue }

    $t0 = Get-Date
    $log = & $Exe @StrehlArgs --out $OutTif 2>&1 | Out-String -Width 200
    $secs = [int]((Get-Date) - $t0).TotalSeconds

    $mode = "none"
    if ($log -match "alignment\s*:\s*ON \((\w+)\)") { $mode = $Matches[1] }

    [pscustomobject]@{
        Sha     = (Get-FileHash $OutTif -Algorithm SHA256).Hash
        Align   = $mode
        Seconds = $secs
    }
}

$arms = @(
    @{ Name = "argmax AFTER"; Exe = "$Out\strehl-after.exe";
       Args = @("argmax-baseline", $Stack, "--srgb", "--exposure=-0.24");
       Ref  = "$Out\marker-argmax-e024-after.tif" }
    @{ Name = "argmax BEFORE"; Exe = "$Out\strehl-before.exe";
       Args = @("argmax-baseline", $Stack, "--srgb", "--exposure=-0.24");
       Ref  = "$Out\marker-argmax-e024-before.tif" }
    @{ Name = "stack AFTER"; Exe = "$Out\strehl-after.exe";
       Args = @("stack", $Stack, "--srgb", "--auto-exposure", "--gate", "4");
       Ref  = "$Out\marker-stack-after.tif" }
)

$contaminated = $false

foreach ($arm in $arms) {
    $a = Invoke-Arm -Exe $arm.Exe -StrehlArgs $arm.Args -OutTif "$Out\ctl-a.tif" -HideCache
    $b = Invoke-Arm -Exe $arm.Exe -StrehlArgs $arm.Args -OutTif "$Out\ctl-b.tif"
    $refSha = (Get-FileHash $arm.Ref -Algorithm SHA256).Hash

    Write-Output ""
    Write-Output "=== $($arm.Name) ==="
    Write-Output ("  hidden  : {0}  align={1} {2}s" -f $a.Sha, $a.Align, $a.Seconds)
    Write-Output ("  visible : {0}  align={1} {2}s" -f $b.Sha, $b.Align, $b.Seconds)
    Write-Output ("  reported: {0}" -f $refSha)

    if ($a.Sha -ne $b.Sha) {
        Write-Output "  *** CONTAMINATED: A != B ***"
        $contaminated = $true
    } elseif ($a.Sha -ne $refSha) {
        Write-Output "  *** NOT REPRODUCIBLE: matches itself but not the reported render ***"
        $contaminated = $true
    } else {
        Write-Output "  CLEAN: cache-independent and reproduces the reported render"
    }

    if ($a.Align -eq "none" -and $b.Align -eq "none") {
        Write-Output "  (no alignment stage on this subcommand -- structurally cache-free)"
    } elseif ($a.Align -eq $b.Align) {
        Write-Output "  *** CONTROL INERT: both arms reported align=$($a.Align); the A==B above proves nothing ***"
        $contaminated = $true
    } else {
        Write-Output "  perturbation confirmed genuine: hidden=$($a.Align) visible=$($b.Align)"
    }
}

# The decisive check for the one arm that touches StackIdentity: was the cached
# warpmap actually equal to a fresh solve, or merely harmless on this output?
$fresh  = Get-ChildItem $Empty -File -Filter "*marker*warpmap*" -EA SilentlyContinue | Select-Object -Last 1
$cached = Get-ChildItem "$env:LOCALAPPDATA\strehl\warpmaps" -File -Filter "*marker*warpmap*" -EA SilentlyContinue | Select-Object -Last 1
Write-Output ""
Write-Output "=== warpmap geometry ==="
if ($fresh -and $cached) {
    $hf = (Get-FileHash $fresh.FullName -Algorithm SHA256).Hash
    $hc = (Get-FileHash $cached.FullName -Algorithm SHA256).Hash
    Write-Output "  fresh solve : $hf"
    Write-Output "  cache entry : $hc"
    if ($hf -eq $hc) { Write-Output "  IDENTICAL: cache entry was solved under the same reference/resampler" }
    else { Write-Output "  *** DIFFER: cache entry was solved under different inputs ***"; $contaminated = $true }
} else {
    Write-Output "  one side missing -- cannot compare"
}

# D:\personal\macro is strictly read-only. Prove this control did not write there.
Write-Output ""
Write-Output "=== read-only corpus ==="
$bad = Get-ChildItem $Stack -Recurse -File | Where-Object { $_.Extension -ne ".ARW" }
if ($bad) {
    $bad | ForEach-Object { Write-Output "  *** WROTE INTO READ-ONLY CORPUS: $($_.FullName)" }
    $contaminated = $true
} else {
    Write-Output "  CLEAN: 0 non-ARW files"
}

Write-Output ""
if ($contaminated) { Write-Output "RESULT: CONTAMINATED -- see marked lines above" }
else { Write-Output "RESULT: all arms clean" }
