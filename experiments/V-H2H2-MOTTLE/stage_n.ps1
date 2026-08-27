# Stage two frame sets that differ ONLY in frame count, at a MATCHED focus range.
#
# The question is whether the merge softens as N rises. `--limit N` cannot ask
# it: --limit takes the FIRST N frames in filename order, which shortens the
# focus bracket, so a --limit arm differs in depth-of-field as well as in N and
# any softness difference is confounded with photographing less of the subject.
# The matched-range arm is a DECIMATION -- every other frame across the whole
# bracket -- which holds the first frame, the last frame and the total focus
# travel fixed and changes only how densely that travel is sampled.
#
# BOTH arms are staged as copies onto the same volume, including the one that
# could have read D:\ directly. That costs 2.9 GB and buys the only thing that
# makes the comparison an A/B: the arms then differ in which files are present
# and in nothing else -- not the drive, not the sidecar policy, not the path
# length. The softness lane reached a number tonight with its arms rendered at
# +2.33 and +0.85 stops; the cheapest defence against that class of error is to
# make the two inputs identical by construction rather than by inspection.
#
# D:\ IS READ-ONLY. This only ever reads from it.

$ErrorActionPreference = 'Stop'

$SRC  = 'D:\personal\macro\113MSDCF'
$DEST = 'C:\dev\strehl-out\V-H2H2\nscale'

$raw = Get-ChildItem $SRC -File -Filter *.ARW | Sort-Object Name
if ($raw.Count -ne 63) { throw "expected 63 ARW, found $($raw.Count)" }

# Decimate by 2 from index 0: keeps frame 1 and frame 63, so the bracket
# endpoints are identical between the arms.
$keep = @()
for ($i = 0; $i -lt $raw.Count; $i += 2) { $keep += $raw[$i] }

$arms = @{ 'n63' = $raw; 'n32' = $keep }

foreach ($name in @('n63', 'n32')) {
    $dir = Join-Path $DEST $name
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $want = $arms[$name]
    $have = (Get-ChildItem $dir -File -Filter *.ARW -ErrorAction SilentlyContinue).Count
    if ($have -eq $want.Count) { "$name already staged ($have frames)"; continue }
    "staging $name : $($want.Count) frames"
    foreach ($f in $want) { Copy-Item $f.FullName -Destination $dir -Force }
    $got = (Get-ChildItem $dir -File -Filter *.ARW).Count
    if ($got -ne $want.Count) { throw "$name staged $got of $($want.Count)" }
}

# Report the bracket endpoints so a mismatched range cannot pass silently.
foreach ($name in @('n63', 'n32')) {
    $d = Get-ChildItem (Join-Path $DEST $name) -File -Filter *.ARW | Sort-Object Name
    "{0}: {1} frames, {2} .. {3}" -f $name, $d.Count, $d[0].Name, $d[-1].Name
}
"DONE"
