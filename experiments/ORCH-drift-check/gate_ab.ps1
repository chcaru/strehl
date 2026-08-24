# ORCH gate ablation -- bee-3-cpl, 299 frames.
#
# QUESTION. The tool's own help says: "The sharpness cost of THIS gate on real
# frames is not measured in this corpus, and no number here should be read as
# claiming otherwise."  That is an unmeasured hole sitting exactly where the
# owner's complaint is ("those stacks don't look too good yet").
#
# MEASURED LADDER (this stack, sidecar-override, 299 placed / 0 refused):
#   gate   mean n_eff   n_eff=1 %   pred sigma gain
#   0.00      1.000      100.00%       1.0000x
#   0.50      1.968       70.70%       0.8675x
#   1.00      4.562       60.89%       0.7810x
#   2.00     19.182       51.15%       0.6974x
#   4.00     55.321       38.77%       0.6273x   <-- SHIPPED DEFAULT
#   8.00     68.096       23.86%       0.5497x
#   solved gate for target n_eff = 3 (fact 324's recommendation): 0.7078
#
# So the shipped default sits 5.65x in gate and 18.4x in n_eff above the target
# the corpus's own fact 324 says to set, and 4.5x beyond the top of M57's only
# measured sharpness-price range (n_eff 12.4 -> 1.45 recovered 0.556 px of PSF
# width).  ARGUED, NOT MEASURED: the gate is a larger softness term on this
# stack than the resampler kernel (-0.2360 dex).  This script exists to kill
# that hypothesis or promote it.
#
# INSTRUMENT.  Single-variable ablation via the sidecar (discipline 685): one
# solved warpmap is reused by every arm, so placements, reference (149),
# stack digest, frame count and resampler are byte-identical across arms and
# --gate is the only free variable.
#
# ============================ BARS, REGISTERED BEFORE THE RUN ================
#
# G0  CONFOUND. --auto-exposure chooses gain FROM THE IMAGE. If the chosen
#     exposure differs between arms, every visual comparison is confounded by
#     brightness and the experiment must be re-run with a fixed --exposure.
#     BAR: the printed exposure must be IDENTICAL across all four arms.
#     If it is not, this run is void as a visual comparison -- re-run pinned.
#
# G1  VALIDITY / CONTROL. The gate-4.00 arm passes the default explicitly.
#     It must reproduce the existing kernel-A/B catmull-rom render EXACTLY:
#       E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112
#     This proves (a) --gate 4 is genuinely the default, and (b) nothing else
#     moved between sessions, so any difference in the other arms is the gate.
#     BAR: exact 64-char match. Anything else voids the run.
#
# G2  RESPONSIVENESS. The four arms must yield FOUR DISTINCT hashes (beyond
#     the control's match). If gate 0.7078 renders identically to gate 4.00,
#     the knob is not wired to the output and every gate claim in the corpus
#     is about a number that does not reach the image.
#     BAR: 4 distinct SHA-256 values.
#
# G3  SHARPNESS (BY EYE, 1:1, no post). On the thorax-hair region, does a
#     lower gate resolve hairs the default merges into mush?  Reported as a
#     look, not a metric -- discipline: do not score sharpness with an
#     unreferenced high-frequency metric.
#
# G4  VEIL. Does the silhouette veil (facts 1371-1372, invariant across all
#     three resampler kernels, fact 1375) weaken as the gate falls?  If it
#     does, the veil is an ADMISSION artifact and M87 should be rerouted.
#     If it is invariant here too, that is a second clean non-cause.
#
# G5  THE PRICE / NEGATIVE CONTROL. Noise in a flat background ROI MUST RISE
#     monotonically as the gate falls -- the ladder predicts sigma gain
#     1.0000x at gate 0 against 0.6273x at gate 4. If measured noise does NOT
#     rise, I am not measuring what I think I am and G3/G4 mean nothing.
#     BAR: flat-ROI sigma strictly increasing as gate decreases.
#
# =============================================================================

$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"

$exe   = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-orch\release\strehl.exe"
$stack = "D:\personal\macro\bee-3-cpl"
$car   = "C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-catmull-rom-warpmap.txt"
$out   = "C:\dev\strehl-out\ORCH-gate"

$CONTROL_HASH = "E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112"

New-Item -ItemType Directory -Force -Path $out | Out-Null

# gate 4.00   = shipped default, the control
# gate 2.00   = what M85 froze
# gate 0.7078 = solved for fact 324's target n_eff = 3
# gate 0.00   = pure selection, "the thing every other stacker does"
$gates = @("4.00", "2.00", "0.7078", "0.00")

foreach ($g in $gates) {
    $tag = "gate-$g"
    $tif = "$out\bee-3-cpl-$tag.tif"
    if (Test-Path $tif) { Write-Output "SKIP $tag (exists)"; continue }

    $env:STREHL_WARPMAP = $car
    $t0  = Get-Date
    $log = & $exe stack $stack --gate $g --srgb --auto-exposure --out $tif 2>&1
    $code = $LASTEXITCODE                      # rule 46: before any filtering
    Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
    $secs = ((Get-Date) - $t0).TotalSeconds

    $log | Out-File -FilePath "$out\bee-3-cpl-$tag.log" -Encoding utf8

    # rule 45: the override must be reported by the tool, not assumed
    $ovr = ($log | Select-String -Pattern "sidecar-override").Count
    $exp = ($log | Select-String -Pattern "exposure" | Select-Object -First 3) -join " ; "
    $nef = ($log | Select-String -Pattern "^\s+$([regex]::Escape($g))\s") -join " "
    $h   = (Get-FileHash $tif -Algorithm SHA256).Hash

    Write-Output "$tag  exit=$code  override=$ovr  $([math]::Round($secs,1))s  $h"
    Write-Output "    neff : $nef"
    Write-Output "    expo : $exp"
}

Write-Output ""
Write-Output "=== G1 CONTROL ==="
$h4 = (Get-FileHash "$out\bee-3-cpl-gate-4.00.tif" -Algorithm SHA256).Hash
if ($h4 -eq $CONTROL_HASH) { Write-Output "G1 PASS  $h4" }
else { Write-Output "G1 FAIL  got $h4  want $CONTROL_HASH  -- RUN IS VOID" }

Write-Output ""
Write-Output "=== G2 RESPONSIVENESS ==="
$hashes = @{}
foreach ($g in $gates) {
    $p = "$out\bee-3-cpl-gate-$g.tif"
    if (Test-Path $p) { $hashes[$g] = (Get-FileHash $p -Algorithm SHA256).Hash }
}
$n = ($hashes.Values | Sort-Object -Unique).Count
Write-Output "distinct hashes: $n of $($hashes.Count)"
if ($n -eq $hashes.Count) { Write-Output "G2 PASS" } else { Write-Output "G2 FAIL -- gate does not reach the image" }
$hashes.GetEnumerator() | Sort-Object Name | ForEach-Object { Write-Output "  $($_.Key)  $($_.Value)" }
