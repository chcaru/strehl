# M111 -- NC8: is the soft-gate module byte-inert on the default merge path?
#
# The claim is that adding `softgate.rs` and its `mod` line changes no output
# byte, because nothing on the default path can reach it. `git grep` already
# shows no call site, but a static argument is not a measurement. This renders
# the same stack twice from the SAME scratch tree:
#
#   arm S : the tree exactly as committed at HEAD (softgate present)
#   arm N : the identical tree with softgate.rs deleted and the mod line
#           removed -- i.e. HEAD minus this milestone's commit, and nothing else
#
# Everything else is held: same binary source, same target dir, same stack, same
# flags, same pinned warpmap, same environment. So an unequal SHA-256 can only
# be the module, and an equal one is the non-perturbation proof.
#
# This compares HEAD against HEAD-minus-my-change rather than against M111's
# earlier DB7BAAD2 reference, because HEAD has since taken other milestones'
# merged work (M97's cache-key fix among them) which may legitimately move
# bytes. Comparing to the old hash would conflate their changes with mine.
#
# Rule 47: `$LASTEXITCODE` is captured on the line immediately after the call
# and asserted EXACTLY. Never `-ne 0` -- the corrupted value is 0 on PS7 and -1
# on PS5.1, so a nonzero check is satisfied by the corruption itself.
#
# Exit codes are distinct so a harness failure can never be read as a
# measurement: 0 = byte-inert (pass), 1 = bytes moved (measured fail),
# 3 = the harness could not run the comparison at all.
$ErrorActionPreference = "Stop"

function Fail-Harness($m) { Write-Host "NC8 HARNESS ERROR: $m"; exit 3 }

$V     = "C:\dev\strehl-out\M111\verify-536fb17"
$OUT   = "C:\dev\strehl-out\M111\nc8"
$STACK = "D:\personal\macro\dry-erase-marker-head-cpl"   # READ-ONLY, never written
$WARP  = "C:\dev\strehl-out\M111\marker-warpmap.txt"
$cargo = "$env:USERPROFILE\.cargo\bin\cargo.exe"

$env:CARGO_TARGET_DIR = "C:\dev\strehl-out\M111\.cargo-nc8"
New-Item -ItemType Directory -Force -Path $OUT | Out-Null

# Hold every byte-affecting variable at a known state (byte-freezes.tsv).
Remove-Item Env:STREHL_ALIGN            -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO         -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO_DELTA   -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_DUMP_ELECTION    -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_DUMP_MERGE_STATE -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_M111_REG_RADIUS  -ErrorAction SilentlyContinue
$env:STREHL_WARPMAP = $WARP

function Build-And-Render($tag) {
    # Cargo writes progress to stderr; with $ErrorActionPreference = 'Stop' that
    # is promoted to a terminating error, which is a harness defect and not a
    # result. Native calls run under 'Continue' and are judged by exit code.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        Push-Location $V
        $null = & $cargo build --release -p strehl-cli 2>&1
        $code = $LASTEXITCODE
        Pop-Location
        if ($code -ne 0) { Fail-Harness "build failed for arm ${tag}: exit $code (expected exactly 0)" }

        $exe = "$env:CARGO_TARGET_DIR\release\strehl.exe"
        if (-not (Test-Path $exe)) { Fail-Harness "no binary for arm $tag" }
        $tif = "$OUT\marker-$tag.tif"
        Remove-Item $tif -ErrorAction SilentlyContinue

        $log = & $exe stack $STACK --srgb --auto-exposure --gate 4 --out $tif 2>&1
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            $log | Select-Object -Last 20 | ForEach-Object { Write-Host "    $_" }
            Fail-Harness "render failed for arm ${tag}: exit $code (expected exactly 0)"
        }
        $path = ($log | Select-String -Pattern 'sidecar-override|sidecar|solved' |
                 Select-Object -First 1)
        Write-Host ("  arm {0}: alignment path -> {1}" -f $tag, ($path -replace '\s+', ' '))
        return (Get-FileHash -Algorithm SHA256 $tif).Hash
    } finally {
        $ErrorActionPreference = $prev
    }
}

Write-Host "NC8 -- soft gate byte-inertness on the default merge path"
Write-Host "=========================================================="

# ---- arm S: exactly as committed ----
if (-not (Test-Path "$V\crates\strehl-core\src\softgate.rs")) {
    Fail-Harness "arm S precondition: softgate.rs is not in the extracted tree"
}
$hashS = Build-And-Render "S-softgate-present"
Write-Host "  arm S (softgate present) : $hashS"

# ---- arm N: the same tree with the module removed ----
# A scratch extraction, not the repository, so no git rule applies here.
$lib = "$V\crates\strehl-core\src\lib.rs"
$before = Get-Content $lib -Raw
$after = $before -replace '(?m)^pub mod softgate;\r?\n', ''
if ($after -eq $before) { Fail-Harness "MUTATION TARGET NOT FOUND: 'pub mod softgate;' not in lib.rs" }
Set-Content -Path $lib -Value $after -NoNewline
Remove-Item "$V\crates\strehl-core\src\softgate.rs" -Force
(Get-Item $lib).LastWriteTime = Get-Date   # cargo must not skip the rebuild

$hashN = Build-And-Render "N-softgate-absent"
Write-Host "  arm N (softgate absent)  : $hashN"

Write-Host ""
if ($hashS -eq $hashN) {
    Write-Host "NC8 PASS -- the soft-gate module is byte-inert on the default path."
    Write-Host "            Identical SHA-256 with the module present and absent."
    exit 0
} else {
    Write-Host "NC8 FAIL -- adding an unreachable module moved the output bytes."
    exit 1
}
