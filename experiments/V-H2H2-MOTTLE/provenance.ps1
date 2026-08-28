# Does MY binary still reproduce the SHIPPING merge, byte for byte?
#
# My build is HEAD plus my own additive instrumentation, but pyramid.rs has also
# drifted 300 lines from the sealed pin under other lanes -- including a new
# `beta_for` path whose author states that `None` "is bit-identical *by
# construction*". That is their claim and it may well be right, but the N-ladder
# is only a statement about the shipping merge if it holds for the binary that
# actually rendered the ladder. So it gets measured here rather than accepted.
#
# coffee-bubbles, 19 frames: the cheapest subject in the corpus and one of the
# six convicted ones. Same flags, same input, two binaries, compare hashes.

$ErrorActionPreference = 'Stop'

$MINE = 'C:\dev\strehl-out\V-H2H2\target\release\strehl.exe'
$PIN  = 'C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe'
$SRC  = 'D:\personal\macro\coffee-bubbles'
$OUT  = 'C:\dev\strehl-out\V-H2H2\ladder\prov'

New-Item -ItemType Directory -Force -Path $OUT | Out-Null
foreach ($p in @($MINE, $PIN, $SRC)) {
    if (-not (Test-Path $p)) { throw "missing: $p" }
}
"mine: $((Get-FileHash $MINE -Algorithm SHA256).Hash.Substring(0,16))"
"pin : $((Get-FileHash $PIN  -Algorithm SHA256).Hash.Substring(0,16))"

$res = @{}
foreach ($k in @('mine', 'pin')) {
    $exe = if ($k -eq 'mine') { $MINE } else { $PIN }
    $tif = Join-Path $OUT "$k.tiff"
    if (-not (Test-Path $tif)) {
        $ErrorActionPreference = 'Continue'
        & $exe stack $SRC --out $tif --linear-srgb --demosaic *> (Join-Path $OUT "$k.log")
        $rc = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        if ($rc -ne 0) { throw "$k FAILED rc=$rc" }
    }
    $res[$k] = (Get-FileHash $tif -Algorithm SHA256).Hash
    "$k render: $($res[$k].Substring(0,16))"
}

if ($res['mine'] -eq $res['pin']) {
    "IDENTICAL - the ladder was rendered by the shipping merge"
} else {
    "DIFFER by hash - now measure the SIZE of the drift, because a hash is one"
    "bit and cannot say whether the numbers are void or hold to 5 decimals."
    & python -u (Join-Path $PSScriptRoot 'provdiff.py')
    if ($LASTEXITCODE -ne 0) { throw "provdiff failed rc=$LASTEXITCODE" }
}
