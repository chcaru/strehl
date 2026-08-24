# M111 NC6 -- the planted mutation. A green test suite is a claim about the
# instrument, and an unfalsified claim is not evidence. This sabotages the one
# guarantee `dump.rs` makes that is not visible in the output -- that a
# length-mismatched plane is refused BEFORE a file is created -- and requires
# `cargo test` to go red with cargo's exact failure code, 101.
#
# Rule 47 on the trap: `$LASTEXITCODE` is read on the line immediately after the
# call, into a variable, before anything filters or formats the output, and the
# assertion is on the EXACT code. Gating on "nonzero" would be satisfied by the
# corruption itself (0 under PS7, -1 under PS5.1).
#
# Rule 42: the file is restored from a copy under my own scratch directory, not
# with `git checkout --`, which reverts to HEAD and has destroyed uncommitted
# work on this machine. `Copy-Item` preserves mtime, so the restored file is
# touched afterwards or cargo skips the rebuild and leaves the sabotage live.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR = "C:\dev\strehl-out\M111\.cargo-target-live"
$repo = "C:\dev\blog\death-of-software\projects\strehl"
$file = "$repo\crates\strehl-cli\src\merge_cmd\dump.rs"
$backup = "C:\dev\strehl-out\M111\dump.rs.pristine"

# The anchor is a unique full line. If it is not there, the mutation did not
# land and every result below would be a green control on nothing.
$anchor = '        len == width * height,'
$src = Get-Content -Raw $file
$hits = ([regex]::Matches($src, [regex]::Escape($anchor))).Count
if ($hits -ne 1) { throw "anchor found $hits times, expected 1 -- refusing to plant" }
Copy-Item $file $backup -Force

try {
    Set-Content -NoNewline -Path $file -Value ($src -replace [regex]::Escape($anchor), '        true,')
    (Get-Item $file).LastWriteTime = Get-Date
    $o = & cargo test -p strehl-cli --bin strehl merge_cmd::dump 2>&1
    $code = $LASTEXITCODE
    $red = ($o | Out-String)
    "SABOTAGED exit code : $code   (cargo test failure is exactly 101)"
    if ($code -ne 101) { throw "RED CONTROL FAILED: expected exactly 101, got $code. The test cannot detect the sabotage, so its green result proves nothing." }
    if ($red -notmatch "a_length_mismatch_is_refused_and_the_message_names_both_shapes") { throw "the wrong test failed" }
    "SABOTAGED: the refusal test failed, as required"
} finally {
    Copy-Item $backup $file -Force
    (Get-Item $file).LastWriteTime = Get-Date
}

$o = & cargo test -p strehl-cli --bin strehl merge_cmd::dump 2>&1
$code = $LASTEXITCODE
"RESTORED  exit code : $code   (expected exactly 0)"
if ($code -ne 0) { throw "restore failed: expected exactly 0, got $code" }
($o | Out-String) -split "`n" | Where-Object { $_ -match "^test |test result" } | ForEach-Object { $_.Trim() }
"NC6 passed: the suite goes red under sabotage and green when restored"
