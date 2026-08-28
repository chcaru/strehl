# Stage an N-ladder on ONE subject, with an independent PAIR at every rung.
#
# THE POINT OF THE PAIR. A single render cannot be decomposed into scene and
# noise, because both are just variance in one image. Two renders of the SAME
# scene from DISJOINT frames can be: the scene is common to both and the noise is
# not, so
#
#     var(scene) = var((A+B)/2) - var((A-B)/2)
#
# exactly, with no comparator, no external reference and no assumption about what
# noise looks like. That is what makes this a one-subject experiment.
#
# CONSTRUCTION. For a rung of size N, 2N frames are drawn evenly across the WHOLE
# bracket and then dealt alternately into A and B. So at every rung:
#   * A and B have the same frame count,
#   * A and B span the same focus range, index 0 to 298, as does every other rung,
#   * A and B are interleaved at half a focus step, so they see the same scene,
#   * A and B share no frame, so their sensor noise is independent.
#
# MATCHED RANGE ACROSS RUNGS is the property that makes the ladder mean anything.
# A shallower rung here is a SPARSER sampling of the same focus travel, not a
# shorter bracket. `--limit` would have given the second thing and confounded
# frame count with depth of field.
#
# ONE CONFOUND, STATED, AND IT RUNS AGAINST THE FINDING. A sparse rung may leave
# focus gaps -- depths where no frame is sharp -- which costs the SHALLOW arms
# detail. If scene content still falls as N rises, it falls despite a confound
# pushing the other way, and the measurement is conservative.
#
# D:\ IS READ-ONLY. This only reads from it.

$ErrorActionPreference = 'Stop'

$SUBJECT = 'bee-3-cpl'
$SRC     = "D:\personal\macro\$SUBJECT"
$DEST    = 'C:\dev\strehl-out\V-H2H2\ladder'
$RUNGS   = @(18, 37, 74, 149)

$raw = Get-ChildItem $SRC -File -Filter *.ARW | Sort-Object Name
"source: $SUBJECT, $($raw.Count) frames, $($raw[0].Name) .. $($raw[-1].Name)"
$last = $raw.Count - 1

foreach ($n in $RUNGS) {
    $draw = 2 * $n
    # Evenly spaced integer indices across the full bracket, endpoints included.
    $idx = @()
    for ($i = 0; $i -lt $draw; $i++) {
        $idx += [int][math]::Round($i * $last / ($draw - 1))
    }
    $idx = $idx | Select-Object -Unique
    if ($idx.Count -ne $draw) { throw "rung $n drew $($idx.Count) unique of $draw" }

    foreach ($arm in @('a', 'b')) {
        $off = if ($arm -eq 'a') { 0 } else { 1 }
        $pick = @()
        for ($i = $off; $i -lt $draw; $i += 2) { $pick += $raw[$idx[$i]] }
        if ($pick.Count -ne $n) { throw "rung $n arm $arm picked $($pick.Count)" }

        $dir = Join-Path $DEST ("n{0}{1}" -f $n, $arm)
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        $have = (Get-ChildItem $dir -File -Filter *.ARW -ErrorAction SilentlyContinue).Count
        if ($have -eq $n) { "n$n$arm already staged"; continue }
        foreach ($f in $pick) { Copy-Item $f.FullName -Destination $dir -Force }
        $got = (Get-ChildItem $dir -File -Filter *.ARW).Count
        if ($got -ne $n) { throw "n$n$arm staged $got of $n" }
        "staged n$n$arm : $n frames, $($pick[0].Name) .. $($pick[-1].Name)"
    }

    # The two arms must be disjoint. A shared frame would put correlated noise in
    # both and the half-difference would understate it -- the decomposition would
    # then report that noise as scene, which is the direction that manufactures a
    # result.
    $da = (Get-ChildItem (Join-Path $DEST "n${n}a") -File -Filter *.ARW).Name
    $db = (Get-ChildItem (Join-Path $DEST "n${n}b") -File -Filter *.ARW).Name
    $shared = Compare-Object $da $db -IncludeEqual -ExcludeDifferent
    if ($shared) { throw "rung $n arms share $($shared.Count) frame(s)" }
    "rung $n : arms disjoint, both span the full bracket"
}
"DONE"
