# M69 arm A6 -- the gate ladder that prices the blast radius.
#
# Gate::tolerance() = T * SQRT_2 * FOCUS_NOISE_SD is exactly linear in the
# constant, so running the SHIPPED binary at gate T*rho is arithmetically
# identical to running gate T with the constant scaled by rho. That identity is
# why M69 priced every published number without touching crates/.
#
# The binary is built into a PRIVATE target dir, never the shared target/, and
# the build log is kept so the artefact is attributable (a `Finished` line with
# no `Compiling` proves freshness, not authorship).

$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR = Join-Path $root "target-m69"

Push-Location $root
cargo build --release -p strehl-cli
Pop-Location

$exe = Join-Path $env:CARGO_TARGET_DIR "release\strehl.exe"
$out = Join-Path $PSScriptRoot "..\out"

# 4*rho for every rho this milestone needed, plus the corpus anchors. One pass
# folds all 17 gates, and --out is omitted so nothing is written.
$gates = @(0.5, 1.0, 1.12, 1.80, 2.0, 3.0, 3.352, 3.444, 3.792, 4.0,
           4.072, 4.0984, 4.394, 4.5544, 4.7684, 4.84, 8.0)

foreach ($stack in @("coffee-bubbles", "109MSDCF", "119MSDCF", "113MSDCF",
                     "112MSDCF", "foam", "coffee-bean")) {
    & $exe stack --gate @gates "D:\personal\macro\$stack" |
        Tee-Object -FilePath (Join-Path $out "60-ladder-$stack.log")
}
