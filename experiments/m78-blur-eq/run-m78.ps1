$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:PYTHONIOENCODING = "utf-8"

Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path "out" | Out-Null

$CB = "C:\dev\macro\test\coffee-bean"
$S112 = "D:\personal\macro\112MSDCF"
$CaptureRoots = @("C:\dev\macro", "D:\macro-dark-frames", "D:\personal\macro")
$Focus = "data\coffee-bean-focus.csv"
$ExpectedHashes = @{
    "data\m10-coffee-bean-edges.csv" = "E242A64A6367FBE2C1A52D679D85CAA40BD091529E2FCE0D477EDB94FAC801A6"
    "data\m12-stack-112-edges.csv" = "045995EFA2CFF6804D0391274EB51E2919432BBC869F1983C853E9F036D943FF"
    $Focus = "C5533D43654CC84E7CD4FA95ACFE87F72236B81D6C585484811017DC2D6FF8D4"
}

function Get-CaptureInventory {
    param([string[]]$Roots)
    foreach ($root in $Roots) {
        if (-not (Test-Path -LiteralPath $root)) {
            "$root : MISSING"
            continue
        }
        $files = Get-ChildItem -LiteralPath $root -Recurse -Force -File
        $bytes = ($files | Measure-Object Length -Sum).Sum
        "$root : $($files.Count) files, $bytes bytes"
    }
}

function Invoke-Harness {
    param(
        [string[]]$Arguments,
        [string]$Log
    )
    & $script:Bin @Arguments 2>&1 | Tee-Object -FilePath $Log
    if ($LASTEXITCODE -ne 0) {
        throw "harness failed with exit code $LASTEXITCODE"
    }
}

foreach ($entry in $ExpectedHashes.GetEnumerator()) {
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Key).Hash -ne $entry.Value) {
        throw "input hash mismatch: $($entry.Key)"
    }
}

Get-CaptureInventory $CaptureRoots | Tee-Object -FilePath "out\capture-before.txt"

cargo clean -p m78-blur-eq
cargo test --release
cargo build --release
$Bin = Join-Path $PSScriptRoot "target\release\m78-blur-eq.exe"

# Interpolator-free amplitude ladders.
Invoke-Harness @(
    "field-probe", "a-mismatch", "--treatment", "blur",
    "--native-ref", "0.5", "--native-mov", "1.5", "--reps", "12",
    "--scales", "0.0001,0.0002,0.0004,0.0008"
) "out\run-a-field.txt"
Invoke-Harness @(
    "field-probe", "a-equal", "--treatment", "blur",
    "--native-ref", "1.0", "--native-mov", "1.0", "--reps", "12",
    "--scales", "0.0001,0.0002,0.0004,0.0008"
) "out\run-a-equal-field.txt"
Invoke-Harness @(
    "field-probe", "b-phase", "--treatment", "phase",
    "--ax", "4.5", "--ay", "-3.5", "--reps", "12",
    "--scales", "0.0001,0.0002,0.0004,0.0008"
) "out\run-b-field.txt"

# Fatal real-content self-pairs.
Invoke-Harness @(
    "blur-eq", $CB, "a-self", "--case", "a-self", "--focus", $Focus,
    "--q", "0.1666667", "--spans", "1", "--stride", "2", "--self"
) "out\run-a-self.txt"
Invoke-Harness @(
    "phase", $CB, "b-self", "--case", "b-self", "--ax", "4.5", "--ay", "-3.5",
    "--spans", "1", "--stride", "2", "--self"
) "out\run-b-self.txt"

# Arm A primary and non-selectable sensitivity ladder.
Invoke-Harness @(
    "blur-eq", $CB, "a-primary", "--case", "a-primary", "--focus", $Focus,
    "--q", "0.1666667", "--spans", "1,2"
) "out\run-a-primary.txt"
foreach ($run in @(
    @("a-q0833333", "0.0833333"),
    @("a-q3333333", "0.3333333"),
    @("a-q6666667", "0.6666667")
)) {
    Invoke-Harness @(
        "blur-eq", $CB, $run[0], "--case", $run[0], "--focus", $Focus,
        "--q", $run[1], "--spans", "1,2"
    ) "out\run-$($run[0]).txt"
}

# Arm B primary, mirror, exact point-copy placebo, and no-defect stack.
Invoke-Harness @(
    "phase", $CB, "b-primary", "--case", "b-primary", "--ax", "4.5",
    "--ay", "-3.5", "--spans", "1,2"
) "out\run-b-primary.txt"
Invoke-Harness @(
    "phase", $CB, "b-mirror", "--case", "b-mirror", "--ax", "-4.5",
    "--ay", "3.5", "--spans", "1,2"
) "out\run-b-mirror.txt"
Invoke-Harness @(
    "phase", $CB, "b-integer", "--case", "b-integer", "--ax", "4",
    "--ay", "-3", "--spans", "1", "--integer"
) "out\run-b-integer.txt"
Invoke-Harness @(
    "phase", $S112, "b-112", "--case", "b-112", "--ax", "4.5",
    "--ay", "-3.5", "--spans", "1"
) "out\run-b-112.txt"

python m78_analyze.py | Tee-Object -FilePath "out\analysis.txt"
python m78_heldout.py | Tee-Object -FilePath "out\heldout.txt"

Get-CaptureInventory $CaptureRoots | Tee-Object -FilePath "out\capture-after.txt"
if ((Compare-Object (Get-Content "out\capture-before.txt") (Get-Content "out\capture-after.txt")).Count) {
    throw "capture inventory changed"
}
"capture inventories identical"
