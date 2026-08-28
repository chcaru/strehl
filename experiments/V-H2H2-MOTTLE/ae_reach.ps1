# Does `--auto-exposure` -- ORCH's exposure regression -- reach V-H2H2's
# concentration statistic at all?
#
# The concentration number is taken from STREHL_PYRAMID_WEIGHT_DUMP, which the
# merge writes while it merges. Exposure is resolved and applied at OUTPUT time.
# So the structural prediction is that the weight dump is byte-identical with
# and without --auto-exposure, and only the master moves. Structural predictions
# are what this campaign keeps getting wrong, so this measures it.
#
# BOTH arms pass --srgb. That is load-bearing: main.rs:1144 sets
# `demosaic: demosaic || (srgb && !binned)`, so --srgb changes the pipeline
# UPSTREAM of the merge. Comparing a bare render against `--srgb --auto-exposure`
# would confound the exposure stage with a demosaic change and could not
# attribute a moved dump. The arms differ in exactly one flag.
#
# CONTROL: the run is only informative if --auto-exposure actually did something
# on this subject. If the two masters are identical the experiment is inert and
# says nothing about the dump, so that case is reported as VOID, not as a pass.

$ErrorActionPreference = "Stop"
$root = "C:\dev\blog\death-of-software\projects\strehl"
$cli  = Join-Path $root "target\release\strehl.exe"
$dump = "C:\dev\strehl-out\V-H2H2\wdump-ae"
$stack = "D:\personal\macro\coffee-bean"
$outdir = Join-Path $env:TEMP "vh2h2-ae"
Remove-Item -Recurse -Force $dump -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $dump, $outdir | Out-Null

function CliSha { (Get-FileHash -Algorithm SHA256 $cli).Hash }
$sha0 = CliSha
Write-Host "strehl.exe sha256: $sha0"
Write-Host "stack            : $stack (limit 20, --merge pyramid, both arms --srgb)"
Write-Host ""

# Significance off in both arms: this is a question about exposure, not the fix.
$env:STREHL_PYRAMID_SIGNIFICANCE = "0"

$arms = [ordered]@{ "plain" = @(); "auto" = @("--auto-exposure") }
$results = @{}

foreach ($tag in $arms.Keys) {
    $env:STREHL_PYRAMID_WEIGHT_DUMP = Join-Path $dump $tag
    $out = Join-Path $outdir "ae-$tag.tif"
    Remove-Item $out -ErrorAction SilentlyContinue

    $ErrorActionPreference = "Continue"
    $log = & $cli stack $stack --merge pyramid -l 20 --srgb @($arms[$tag]) -o $out 2>&1 | Out-String -Width 4096
    $rc = $LASTEXITCODE
    $ErrorActionPreference = "Stop"

    if ((CliSha) -ne $sha0) { Write-Host "VOID: strehl.exe changed during arm $tag"; exit 2 }
    if ($rc -ne 0) {
        Write-Host "arm $tag FAILED rc=$rc"
        ($log -split "`n" | Select-Object -Last 12) | ForEach-Object { Write-Host "    $_" }
        exit 1
    }

    # The gain the tool chose, in its own words.
    $gain = ($log -split "`n" | Where-Object { $_ -match 'exposure|stops|gain' } |
             Select-Object -First 3) -join " | "

    $dumpFiles = Get-ChildItem (Join-Path $dump "$tag*") -File | Sort-Object Name
    if ($dumpFiles.Count -eq 0) { Write-Host "arm $tag wrote NO DUMP"; exit 1 }
    $dumpHash = ($dumpFiles | ForEach-Object { (Get-FileHash -Algorithm SHA256 $_.FullName).Hash }) -join ""
    $dumpHash = (Get-FileHash -Algorithm SHA256 -InputStream (
        [System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($dumpHash)))).Hash

    $results[$tag] = [pscustomobject]@{
        Master   = (Get-FileHash -Algorithm SHA256 $out).Hash
        Dump     = $dumpHash
        Files    = $dumpFiles.Count
        Gain     = $gain.Trim()
        Path     = $out
    }
    Write-Host ("{0,-6} master {1}  dump {2}  ({3} dump files)" -f $tag,
        $results[$tag].Master.Substring(0,16), $dumpHash.Substring(0,16), $dumpFiles.Count)
    if ($gain) { Write-Host ("       tool said: {0}" -f $gain.Trim()) }
}

Write-Host ""
$masterSame = $results["plain"].Master -eq $results["auto"].Master
$dumpSame   = $results["plain"].Dump   -eq $results["auto"].Dump

if ($masterSame) {
    Write-Host "VOID -- --auto-exposure changed NOTHING on this subject, so this run"
    Write-Host "        cannot say whether it could have reached the weight dump."
    exit 3
}

Write-Host "master moved : YES  (--auto-exposure is potent here, so the probe is live)"
Write-Host ("weight dump  : {0}" -f $(if ($dumpSame) { "IDENTICAL -- exposure cannot reach the concentration statistic" }
                                     else { "MOVED -- exposure DOES reach the statistic; V-H2H2 numbers are suspect" }))
Write-Host ""
Write-Host "clip fractions:"
python (Join-Path $root "experiments\V-H2H2-MOTTLE\clipcheck2.py") $results["plain"].Path $results["auto"].Path
