# M109 -- measure the `strehl stack` delta once M97 lands the section 6 patch.
#
# I AUTHORED THE PATCH, SO THIS IS A MEASUREMENT, NOT A VERIFICATION.
# ORCH is assigning the independent read to M110's 1:1 sheet.
#
# Run with no arguments after M97 confirms. It refuses to run if the patch is
# not present, so it cannot silently measure the unpatched path and report a
# null result as a finding.
#
# --------------------------------------------------------------------------
# WHY BOTH ARMS ARE BUILT FROM ONE TREE
#
# The obvious "before" is the binary I already have at C:\dev\strehl-out\M109.
# That would be WRONG here: optics.rs and robust.rs are currently dirty with
# another agent's in-flight work, so a rebuild after M97 lands would differ
# from the old binary by THEIR changes as well as the patch. The delta would
# be confounded and I would not be able to tell which change moved a pixel.
#
# Instead both arms are built from the SAME tree at the SAME moment, differing
# only in whether `color::saturation_ceiling` returns a real ceiling or +inf.
# That is the B3 negative control mechanism, already shown able to go red, and
# it is the toggle the montage's "ceiling disabled" panel already describes.
#
# color.rs is MY file. merge_cmd.rs is M97's and is never touched here.
# --------------------------------------------------------------------------
#
# Exit-code discipline (AGENTS.md rule 47): every native command is captured to
# a variable first and $LASTEXITCODE read immediately, never after a filtering
# pipeline, and every gate asserts the EXACT expected code rather than -ne 0.

$ErrorActionPreference = "Continue"

$Root  = "C:\dev\blog\death-of-software\projects\strehl"
$Out   = "C:\dev\strehl-out\M109"
$Marker = "D:\personal\macro\dry-erase-marker-head-cpl"
$Null1  = "D:\personal\macro\109MSDCF"

$ColorRs = Join-Path $Root "crates\strehl-core\src\color.rs"
$MergeRs = Join-Path $Root "crates\strehl-cli\src\merge_cmd.rs"
$Anchor  = "    let k0 = (f32::from(clip::CONTAINER_MAX_DN) - levels.black) / range;"
$Planted = "    let k0 = f32::INFINITY; // M109 negative control: ceiling disabled"

$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR = Join-Path $Root ".cargo-target-orch"

function Die([string]$m) { Write-Output "FATAL: $m"; exit 2 }

# --- guard 1: refuse to run against an unpatched merge_cmd.rs ---------------
$merge = [IO.File]::ReadAllText($MergeRs)
if ($merge -notmatch "saturation_ceiling" -or $merge -notmatch "with_ceiling") {
    Die "merge_cmd.rs does not contain the section 6 patch yet. Nothing to measure."
}
Write-Output "guard 1 ok: patch present in merge_cmd.rs"

# --- guard 2: the toggle anchor must be unique ------------------------------
$orig = [IO.File]::ReadAllText($ColorRs)
$n = [regex]::Matches($orig, [regex]::Escape($Anchor)).Count
if ($n -ne 1) { Die "ceiling anchor found $n times in color.rs, expected exactly 1" }
Write-Output "guard 2 ok: ceiling anchor unique"

function Build([string]$ExeName) {
    $log = & cargo build --release 2>&1 | Out-String -Width 200
    $code = $LASTEXITCODE
    if ($code -ne 0) { Write-Output $log; Die "cargo build exited $code, expected 0" }
    Copy-Item (Join-Path $env:CARGO_TARGET_DIR "release\strehl.exe") "$Out\$ExeName" -Force
    Write-Output "  built $ExeName"
}

function Stack([string]$Exe, [string]$Dir, [string]$OutTif, [string[]]$Extra) {
    $a = @("stack", $Dir, "--srgb") + $Extra + @("--out", $OutTif)
    $log = & "$Out\$Exe" @a 2>&1 | Out-String -Width 200
    $code = $LASTEXITCODE
    if ($code -ne 0) { Write-Output $log; Die "strehl stack exited $code, expected 0" }
    return (Get-FileHash $OutTif -Algorithm SHA256).Hash
}

# --- arm A: ceiling live ----------------------------------------------------
Write-Output "`n=== building AFTER (ceiling live) ==="
Build "strehl-stack-after.exe"

# --- byte-freeze BEFORE anything else. merge_cmd.rs IS the frozen path. -----
Write-Output "`n=== B4 byte-freeze (merge_cmd.rs is the frozen measurement path) ==="
$env:STREHL_FREEZE_REQUIRE = "1"
$log = & cargo test --release --test byte-freeze 2>&1 | Out-String -Width 200
$code = $LASTEXITCODE
Remove-Item Env:\STREHL_FREEZE_REQUIRE -EA SilentlyContinue
Write-Output (($log -split "`n" | Select-String "test result|running \d+ test") | Out-String -Width 140)
if ($code -ne 0) { Write-Output "*** BYTE-FREEZE FAILED (exit $code) -- the patch altered the measurement path ***"; exit 3 }
Write-Output "B4 PASS (exit 0)"

# --- arm B: ceiling disabled, same tree -------------------------------------
Write-Output "`n=== building BEFORE (ceiling disabled) ==="
$backup = Join-Path $env:TEMP "m109-color.rs.bak"
Copy-Item $ColorRs $backup -Force          # never `git checkout --`
[IO.File]::WriteAllText($ColorRs, $orig.Replace($Anchor, $Planted))
$check = [IO.File]::ReadAllText($ColorRs)
if ($check -notmatch [regex]::Escape($Planted)) { Die "plant did not land" }
Build "strehl-stack-before.exe"

# restore, then TOUCH: Copy-Item preserves mtime and cargo would reuse the
# stale build without noticing the file changed back.
Copy-Item $backup $ColorRs -Force
(Get-Item $ColorRs).LastWriteTime = Get-Date
$after = [IO.File]::ReadAllText($ColorRs)
if ($after -ne $orig) { Die "color.rs did not restore byte-identically" }
Write-Output "  color.rs restored byte-identically and touched"

# --- renders ----------------------------------------------------------------
$mk = @("--auto-exposure", "--gate", "4")
Write-Output "`n=== rendering marker, both arms ==="
$hB = Stack "strehl-stack-before.exe" $Marker "$Out\stack-marker-before.tif" $mk
$hA = Stack "strehl-stack-after.exe"  $Marker "$Out\stack-marker-after.tif"  $mk
Write-Output "  before = $hB"
Write-Output "  after  = $hA"
if ($hA -eq $hB) { Write-Output "  *** ARMS IDENTICAL -- the patch changed nothing on marker ***" }

Write-Output "`n=== B2 null (109MSDCF, no saturated pixels) must be byte-identical ==="
$nB = Stack "strehl-stack-before.exe" $Null1 "$Out\stack-null-before.tif" @("--gate", "4")
$nA = Stack "strehl-stack-after.exe"  $Null1 "$Out\stack-null-after.tif"  @("--gate", "4")
Write-Output "  before = $nB"
Write-Output "  after  = $nA"
if ($nA -eq $nB) { Write-Output "  B2 PASS: byte-identical" } else { Write-Output "  *** B2 FAIL: the fix moved an unsaturated stack ***" }

# --- metrics ----------------------------------------------------------------
Write-Output "`n=== B1 magenta predicate ==="
$m = & python (Join-Path $Root "experiments\M109-highlights\src\magenta.py") "$Out\stack-marker-before.tif" "$Out\stack-marker-after.tif" 2>&1 | Out-String -Width 160
if ($LASTEXITCODE -ne 0) { Write-Output "magenta.py exited $LASTEXITCODE" }
Write-Output $m

Write-Output "`n=== B8 ORCH's D1/D8 ==="
$d = & python (Join-Path $Root "experiments\M109-highlights\src\d1d8.py") "stack-before=$Out\stack-marker-before.tif" "stack-after=$Out\stack-marker-after.tif" 2>&1 | Out-String -Width 160
if ($LASTEXITCODE -ne 0) { Write-Output "d1d8.py exited $LASTEXITCODE" }
Write-Output $d

Write-Output "`n=== B6 montage ==="
$g = & python (Join-Path $Root "experiments\M109-highlights\src\montage.py") `
        --before "$Out\stack-marker-before.tif" --after "$Out\stack-marker-after.tif" `
        "--tag=-stack" --cmd "stack --srgb --auto-exposure --gate 4" 2>&1 | Out-String -Width 160
if ($LASTEXITCODE -ne 0) { Write-Output "montage.py exited $LASTEXITCODE" }
Write-Output $g

Write-Output "`nNEXT: run cache_control.ps1 -- merge_cmd.rs is one of only two files"
Write-Output "that touch StackIdentity, so these stack arms actually exercise fact 1446."
