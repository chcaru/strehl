# Stage an N-ladder on ONE subject, with an independent PAIR at every rung.
#
# THE POINT OF THE PAIR. A single render cannot be decomposed into scene and
# noise, because both are just variance in one image. Two renders of the SAME
# scene from DISJOINT frames can be:
#
#     var(scene) = var((A+B)/2) - var((A-B)/2)
#
# exactly, with no comparator, no external reference and no model of the noise.
#
# ADJACENT PAIRING, AND THE FIRST DESIGN THAT FAILED. The first version dealt 2N
# evenly-spaced frames alternately into A and B. It was measured and it was wrong
# in two ways at once, both of which grew as the rung got sparser:
#
#   1 A and B were then half a focus STEP apart -- 8 frames of 299 at rung 18,
#     but only 1 at rung 149. So the two arms did not share a scene at the sparse
#     rungs. Real focus differences landed in the half-difference and were
#     counted as noise, deflating the scene term hardest exactly where the ladder
#     needed it clean. Measured: at rung 18 the best achievable arm-to-arm match
#     was 9.98 codes and integer registration improved it only 1.04x, against
#     2.88x at rung 74.
#   2 The merged output's PIXEL GRID depends on which frames are in the stack --
#     there is no flag to pin the alignment reference -- so the two arms landed
#     up to (-5, +12) px apart, and by a DIFFERENT amount at every rung.
#
# Both defects varied systematically with N, which is the one thing a ladder
# cannot tolerate: they would have manufactured an N-trend out of the staging.
#
# The fix is to pair ADJACENT frames. For each of N depth positions, A takes the
# frame at p and B takes the frame at p+1. Then at EVERY rung:
#   * A and B are one frame apart in focus, not half a rung apart -- constant in N
#   * A and B contain near-identical frames, so their alignment references are
#     adjacent and the grid offset is small and constant in N
#   * A and B still share no frame, so their sensor noise is independent
#   * both still span the whole bracket, so the range is matched across rungs
#
# What remains is a one-frame focus difference between the arms, which is a real
# scene difference that will be counted as noise. It is not zero. But it is the
# SAME at every rung, so it shifts the ladder rather than tilting it, and a trend
# in N cannot be manufactured from it.
#
# D:\ IS READ-ONLY. This only reads from it.

$ErrorActionPreference = 'Stop'

$SUBJECT = 'bee-3-cpl'
$SRC     = "D:\personal\macro\$SUBJECT"
$DEST    = 'C:\dev\strehl-out\V-H2H2\ladder2'
$RUNGS   = @(18, 37, 74, 149)

$raw = Get-ChildItem $SRC -File -Filter *.ARW | Sort-Object Name
"source: $SUBJECT, $($raw.Count) frames, $($raw[0].Name) .. $($raw[-1].Name)"
$last = $raw.Count - 1

foreach ($n in $RUNGS) {
    # N depth positions across the bracket, leaving room for the +1 partner.
    $pos = @()
    for ($i = 0; $i -lt $n; $i++) {
        $pos += [int][math]::Round($i * ($last - 1) / ($n - 1))
    }
    $pos = $pos | Select-Object -Unique
    if ($pos.Count -ne $n) { throw "rung $n drew $($pos.Count) unique positions of $n" }
    # A frame may not appear in both arms: p_i + 1 must never equal p_j.
    foreach ($p in $pos) { if ($pos -contains ($p + 1)) { throw "rung $n : positions $p and $($p+1) collide" } }

    foreach ($arm in @('a', 'b')) {
        $off = if ($arm -eq 'a') { 0 } else { 1 }
        $pick = $pos | ForEach-Object { $raw[$_ + $off] }
        if ($pick.Count -ne $n) { throw "rung $n arm $arm picked $($pick.Count)" }

        $dir = Join-Path $DEST ("n{0}{1}" -f $n, $arm)
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        if ((Get-ChildItem $dir -File -Filter *.ARW -ErrorAction SilentlyContinue).Count -eq $n) {
            "n$n$arm already staged"; continue
        }
        foreach ($f in $pick) { Copy-Item $f.FullName -Destination $dir -Force }
        $got = (Get-ChildItem $dir -File -Filter *.ARW).Count
        if ($got -ne $n) { throw "n$n$arm staged $got of $n" }
        "staged n$n$arm : $n frames, $($pick[0].Name) .. $($pick[-1].Name)"
    }

    # Disjointness is this experiment's only defence against reporting shared
    # noise as scene -- commdecomp.py arm 6 measures exactly that failure.
    $da = (Get-ChildItem (Join-Path $DEST "n${n}a") -File -Filter *.ARW).Name
    $db = (Get-ChildItem (Join-Path $DEST "n${n}b") -File -Filter *.ARW).Name
    $shared = Compare-Object $da $db -IncludeEqual -ExcludeDifferent
    if ($shared) { throw "rung $n arms share $($shared.Count) frame(s)" }
    $spanA = ($da[-1] -replace '\D','') - ($da[0] -replace '\D','')
    "rung $n : arms disjoint, arm a spans frame index range $spanA of $last"
}
"DONE"
