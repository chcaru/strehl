# M111 NC4 (live tree) -- rule 26 non-perturbation of the shipped addition.
#
# The scratch build already proved that a dump-on render reproduces ORCH's
# `marker-HEAD-8f46f04.tif` byte for byte
# (DB7BAAD2FDC5BF74309B132D0DDEB1A681609037312E76923C2B22703BA1DDDC). That
# anchored the state planes to the exact pixels ORCH measured, but it was a
# build of `git archive a7bd05a`, not of the tree I am committing into, and the
# tree I am committing into carries other agents' uncommitted work.
#
# So this repeats the on/off comparison with the LIVE tree's release binary. It
# cannot be compared against ORCH's hash -- other agents have moved align.rs and
# robust.rs, which move output bytes -- but that is not what it is for. It is
# for the only claim my change needs to support: that setting
# STREHL_DUMP_MERGE_STATE does not alter a single output byte.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR = "C:\dev\strehl-out\M111\.cargo-target-live"
$repo = "C:\dev\blog\death-of-software\projects\strehl"
$root = "C:\dev\strehl-out\M111"
$stack = "D:\personal\macro\dry-erase-marker-head-cpl"

Push-Location $repo
$o = & cargo build -p strehl-cli --bin strehl --release 2>&1
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { ($o | Out-String); throw "release build exited $code (expected 0)" }
if (($o | Out-String) -notmatch "Compiling strehl-cli") {
    "note: strehl-cli was already fresh in this target dir"
}
$exe = "$env:CARGO_TARGET_DIR\release\strehl.exe"

Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO_DELTA -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_DUMP_ELECTION -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_M111_REG_RADIUS -ErrorAction SilentlyContinue
$env:STREHL_WARPMAP = "$root\marker-warpmap.txt"

Remove-Item Env:STREHL_DUMP_MERGE_STATE -ErrorAction SilentlyContinue
$o = & $exe stack $stack --srgb --exposure=-0.24 --gate 4 --out "$root\render\nc4-live-off.tif" 2>&1
$code = $LASTEXITCODE
$o | Out-String | Set-Content -Encoding utf8 "$root\render\nc4-live-off.log"
if ($code -ne 0) { throw "dump-off render exited $code (expected 0)" }

$env:STREHL_DUMP_MERGE_STATE = "$root\render\state-nc4-live"
$o = & $exe stack $stack --srgb --exposure=-0.24 --gate 4 --out "$root\render\nc4-live-on.tif" 2>&1
$code = $LASTEXITCODE
$o | Out-String | Set-Content -Encoding utf8 "$root\render\nc4-live-on.log"
if ($code -ne 0) { throw "dump-on render exited $code (expected 0)" }

$a = (Get-FileHash "$root\render\nc4-live-off.tif" -Algorithm SHA256).Hash
$b = (Get-FileHash "$root\render\nc4-live-on.tif" -Algorithm SHA256).Hash
"dump OFF sha256 : $a"
"dump ON  sha256 : $b"
if ($a -ne $b) { throw "NC4 FAILED: the dump moved output bytes" }
"NC4 (live tree) passed: STREHL_DUMP_MERGE_STATE is byte-inert"
Get-ChildItem "$root\render\state-nc4-live" | ForEach-Object { "  {0,-22} {1,12} bytes" -f $_.Name, $_.Length }
