# The byte-level arms for the gate-floor change, run at a PINNED commit in a
# DETACHED worktree because six agents write to the main tree.
#
# Reproduces each byte-freeze row's OWN recorded invocation, except that
# `--merge` is set explicitly. Both frozen rows hardcode `--merge estimator`
# while DEFAULT_MERGE_BACKEND is Pyramid, so the registry does not cover the
# shipping backend and cannot see this change. These are the numbers ORCH needs
# to decide whether to add a pyramid row.
#
# The `unaligned` row is the PLACEBO and it is structural: no warp runs, so the
# probe is never called and the two floor arms must be BYTE-IDENTICAL.
param([string]$Wt = "C:\dev\strehl-out\BUILD-GATE\wt\fix")

$exe = Join-Path $Wt "target\release\strehl.exe"
$data = Join-Path $Wt "crates\strehl-cli\tests\data"
$out = "C:\dev\strehl-out\BUILD-GATE\freeze"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$rows = @(
    @{ id = "coffee-bean-20-gate2-unaligned"; align = "0"; warpmap = $null },
    @{ id = "coffee-bean-20-gate2-sidecar"; align = $null; warpmap = "coffee-bean-20.warpmap.txt" }
)

$results = @()
foreach ($row in $rows) {
    foreach ($backend in @("estimator", "pyramid")) {
        foreach ($floor in @("white", "measured")) {
            # An estimator render cannot see the floor at all; skip the dup.
            if ($backend -eq "estimator" -and $floor -eq "measured") { continue }

            foreach ($v in @("STREHL_ALIGN", "STREHL_WARPMAP", "STREHL_CACHE_DIR",
                    "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA", "STREHL_GATE_FLOOR",
                    "STREHL_FULLRES_GATHER", "STREHL_DEFECT")) {
                Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
            }
            $scratch = Join-Path $out "scratch"
            New-Item -ItemType Directory -Force -Path $scratch | Out-Null
            $env:STREHL_CACHE_DIR = $scratch
            if ($row.align) { $env:STREHL_ALIGN = $row.align }
            if ($row.warpmap) { $env:STREHL_WARPMAP = (Join-Path $data $row.warpmap) }
            if ($floor -eq "white") { $env:STREHL_GATE_FLOOR = "white" }

            $tif = Join-Path $out "$($row.id)-$backend-$floor.tif"
            $log = "$tif.log"
            # `--gate` is estimator-only; the tool REFUSES it under pyramid
            # rather than ignoring it. `--pyramid-gate` is a different quantity
            # (a multiple of modelled band-noise power) that happens to share
            # the frozen row's numeric value, and it is named explicitly here
            # rather than defaulted for the reason byte-freeze.rs gives.
            $gate = if ($backend -eq "pyramid") { @("--pyramid-gate", "2.0") } else { @("--gate", "2.0") }
            # `--photometric` is likewise estimator-only and the pyramid REFUSES
            # it -- it is "not yet implemented on this backend", not
            # inapplicable. The frozen rows are photometric-off, and the pyramid
            # has no photometric stage at all, so omitting it renders the same
            # pipeline the rows describe.
            $photo = if ($backend -eq "pyramid") { @() } else { @("--photometric", "off") }
            & $exe stack "D:\personal\macro\coffee-bean" --merge $backend `
                @photo --limit 20 @gate --out $tif *>&1 |
            Out-File -FilePath $log -Encoding utf8
            if (-not (Test-Path $tif)) { Write-Host "FAILED $($row.id) $backend $floor"; continue }
            $h = (Get-FileHash $tif -Algorithm SHA256).Hash
            $results += [pscustomobject]@{
                row = $row.id; backend = $backend; floor = $floor
                sha256 = $h; bytes = (Get-Item $tif).Length
            }
            Write-Host ("{0,-32} {1,-10} {2,-9} {3}" -f $row.id, $backend, $floor, $h)
        }
    }
}

Write-Host ""
Write-Host "=== VERDICT ==="
foreach ($row in $rows) {
    $w = ($results | Where-Object { $_.row -eq $row.id -and $_.backend -eq "pyramid" -and $_.floor -eq "white" }).sha256
    $m = ($results | Where-Object { $_.row -eq $row.id -and $_.backend -eq "pyramid" -and $_.floor -eq "measured" }).sha256
    $e = ($results | Where-Object { $_.row -eq $row.id -and $_.backend -eq "estimator" }).sha256
    Write-Host ("{0}" -f $row.id)
    Write-Host ("   estimator (THE FROZEN ROW) : {0}" -f $e)
    Write-Host ("   pyramid white floor        : {0}" -f $w)
    Write-Host ("   pyramid measured floor     : {0}" -f $m)
    # An empty hash is a FAILED render, not a match. The first version of this
    # script compared two empty strings and printed IDENTICAL for a run that
    # never produced a file -- a null that passes by not happening.
    if (-not $w -or -not $m) {
        Write-Host "   pyramid arms UNMEASURED    <- a render failed; this is not a result"
    }
    elseif ($w -eq $m) {
        Write-Host "   pyramid arms IDENTICAL     <- no warp, probe never called"
    }
    else {
        Write-Host "   pyramid arms DIFFER        <- the fix is reaching the gate"
    }
}
