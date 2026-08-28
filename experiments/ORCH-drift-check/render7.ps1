# ORCH-RENDER7: render the seven subjects DELIVER-V6 was structurally blind to.
#
# DELIVER-V6's MANIFEST records `subjects : 26 (from C:\dev\strehl-out\ORCH-FAITHFUL\faithful)`
# -- it enumerated its work list from a STALE OUTPUT DIRECTORY rather than from the source
# tree, so the seven subjects the owner added after that tree was written could never appear.
# Same shape as the SEAL_DIR defect: an instrument's input path is part of its calibration.
#
# This script enumerates from D:\personal\macro itself and uses byte-identical invocation to
# DELIVER-V6's, so the outputs are directly comparable with the 26 already rendered.

$ErrorActionPreference = 'Continue'

$EXE  = 'C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe'
$SRC  = 'D:\personal\macro'
$DEST = 'C:\dev\strehl-out\DELIVER-V6\masters'
$MAN  = Join-Path $DEST 'MANIFEST-ORCH7.txt'
$CACHE = 'C:\dev\strehl-out\DELIVER-V6\scratch\warpmaps'

# Match DELIVER-V6 exactly: STREHL_CACHE_DIR set, every other STREHL_* unset.
Get-ChildItem Env: | Where-Object { $_.Name -like 'STREHL_*' -and $_.Name -ne 'STREHL_CACHE_DIR' } |
    ForEach-Object { Remove-Item "Env:$($_.Name)" -ErrorAction SilentlyContinue }
$env:STREHL_CACHE_DIR = $CACHE

$sha = (Get-FileHash $EXE -Algorithm SHA256).Hash

# Enumerate from the SOURCE, not from any output tree. That is the whole point.
$all = Get-ChildItem $SRC -Directory | Where-Object { $_.Name -ne 'flat-fields' } |
       Select-Object -ExpandProperty Name
$done = (Get-ChildItem $DEST -Filter *.tiff -ErrorAction SilentlyContinue).BaseName
$todo = $all | Where-Object { $_ -notin $done } | Sort-Object

"=== ORCH-RENDER7"                        | Tee-Object -FilePath $MAN
"exe            : $EXE"                   | Tee-Object -FilePath $MAN -Append
"exe SHA256     : $sha"                   | Tee-Object -FilePath $MAN -Append
"source root    : $SRC  (READ-ONLY)"      | Tee-Object -FilePath $MAN -Append
"enumerated from: $SRC   <-- NOT from an output tree"  | Tee-Object -FilePath $MAN -Append
"subjects       : $($todo.Count) of $($all.Count) total; $($done.Count) already present" |
    Tee-Object -FilePath $MAN -Append
"started        : $(Get-Date -Format o)"  | Tee-Object -FilePath $MAN -Append
""                                        | Tee-Object -FilePath $MAN -Append

foreach ($s in $todo) {
    $dir = Join-Path $SRC $s
    $out = Join-Path $DEST "$s.tiff"
    $n = (Get-ChildItem $dir -Filter *.ARW -ErrorAction SilentlyContinue).Count
    "subject   : $s"                      | Tee-Object -FilePath $MAN -Append
    "frames    : $n"                      | Tee-Object -FilePath $MAN -Append
    "command   : `"$EXE`" stack `"$dir`" -o `"$out`" --srgb" | Tee-Object -FilePath $MAN -Append

    $t0 = Get-Date
    & $EXE stack $dir -o $out --srgb 2>&1 | Out-File -FilePath (Join-Path $DEST "$s.render.log") -Encoding utf8
    $rc = $LASTEXITCODE
    $secs = ((Get-Date) - $t0).TotalSeconds

    if ($rc -eq 0 -and (Test-Path $out)) {
        $h = (Get-FileHash $out -Algorithm SHA256).Hash
        $b = (Get-Item $out).Length
        "out SHA256: $h"                  | Tee-Object -FilePath $MAN -Append
        "bytes     : $b"                  | Tee-Object -FilePath $MAN -Append
        "secs      : $([math]::Round($secs,1))"  | Tee-Object -FilePath $MAN -Append
    } else {
        "FAILED    : rc=$rc after $([math]::Round($secs,1))s -- see $s.render.log" |
            Tee-Object -FilePath $MAN -Append
    }
    ""                                    | Tee-Object -FilePath $MAN -Append
}

"finished       : $(Get-Date -Format o)"  | Tee-Object -FilePath $MAN -Append
"total masters  : $((Get-ChildItem $DEST -Filter *.tiff).Count)" | Tee-Object -FilePath $MAN -Append
