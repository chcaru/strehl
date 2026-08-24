# M111 arm G -- generality. The same two arms on a SECOND stack.
#
# Everything measured so far is one subject. A mechanism that only exists on
# `dry-erase-marker-head-cpl` is a property of that stack, not of the merge, so
# the claim needs a stack it was not derived from. `lavendar-cpl` is the other
# pair ORCH built a single-frame control for.
#
# Rule 47, the whole invocation: as sweep_gate.ps1 but on lavendar-cpl, with
# --auto-exposure replaced by the value the gate-4 arm picks, so the two arms
# are photometrically comparable and the difference image D is meaningful.
# STREHL_WARPMAP is NOT pinned here (no private copy exists for this stack); the
# two arms share the solve through the process cache, and the log's reported
# reference frame and placed count are checked to be identical afterwards.
$ErrorActionPreference = "Stop"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$root = "C:\dev\strehl-out\M111"
$exe = "$root\.cargo-target\release\strehl.exe"
$stack = "D:\personal\macro\lavendar-cpl"
$out = "$root\render"

Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO_DELTA -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_DUMP_ELECTION -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_M111_REG_RADIUS -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue

# Arm 1: gate 4, auto exposure, to learn the exposure the image wants.
$d1 = "$out\state-lav-g4"
New-Item -ItemType Directory -Force -Path $d1 | Out-Null
$env:STREHL_DUMP_MERGE_STATE = $d1
$o = & $exe stack $stack --srgb --auto-exposure --gate 4 --out "$out\lavendar-g4.tif" 2>&1
$c = $LASTEXITCODE
$o | Out-String | Set-Content -Encoding utf8 "$out\lavendar-g4.log"
if ($c -ne 0) { throw "lavendar gate 4 exited $c (expected 0)" }
$expLine = ($o | Select-String "reproduce this exact file with --exposure").Line
if (-not $expLine) { throw "could not read the chosen exposure from the log" }
$exp = [regex]::Match($expLine, "--exposure=(-?[0-9.]+)").Groups[1].Value
"lavendar gate 4  exposure=$exp  sha256=$((Get-FileHash "$out\lavendar-g4.tif" -Algorithm SHA256).Hash.Substring(0,16))"

# Arm 2: the same exposure, gate wide open -- the plain mean of every frame.
$d2 = "$out\state-lav-g1e5"
New-Item -ItemType Directory -Force -Path $d2 | Out-Null
$env:STREHL_DUMP_MERGE_STATE = $d2
$o = & $exe stack $stack --srgb "--exposure=$exp" --gate 100000 --out "$out\lavendar-g100000.tif" 2>&1
$c = $LASTEXITCODE
$o | Out-String | Set-Content -Encoding utf8 "$out\lavendar-g100000.log"
if ($c -ne 0) { throw "lavendar gate 1e5 exited $c (expected 0)" }
"lavendar gate 1e5  sha256=$((Get-FileHash "$out\lavendar-g100000.tif" -Algorithm SHA256).Hash.Substring(0,16))"

# The two arms must have been built on the SAME registration, or D is a
# registration difference rather than a selection difference.
$r1 = (Select-String "$out\lavendar-g4.log" -Pattern "reference frame|placed").Line -join " ; "
$r2 = (Select-String "$out\lavendar-g100000.log" -Pattern "reference frame|placed").Line -join " ; "
if ($r1 -ne $r2) { throw "registration differs between arms:`n  $r1`n  $r2" }
"registration identical across arms: $($r1.Trim())"
Remove-Item Env:STREHL_DUMP_MERGE_STATE
"lavendar arms done"
