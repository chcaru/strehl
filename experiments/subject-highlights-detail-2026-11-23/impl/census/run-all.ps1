$ErrorActionPreference = 'Continue'
$env:STREHL_CACHE_DIR = 'C:/w/shd-census-out/cache'
Remove-Item Env:STREHL_SURVEY_DEBUG -ErrorAction SilentlyContinue
$exe = 'C:/w/shd-census/target/release/strehl.exe'
$o = 'C:/w/shd-census-out/runs'
New-Item -ItemType Directory -Force $o | Out-Null
foreach ($n in $args) {
    $extra = @()
    if ($n -like '*=*') { $parts = $n.Split('='); $n = $parts[0]; $extra = @('--subject', $parts[1]); $tag = "$n-given" } else { $tag = $n }
    $start = Get-Date
    & $exe survey "C:/w/shd-census-out/fixtures/$n" --out "$o/$tag.json" @extra *> "$o/$tag.txt"
    $code = $LASTEXITCODE
    "$tag exit $code ($([int]((Get-Date) - $start).TotalSeconds) s)"
}
