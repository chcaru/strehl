# 44-default-arms.ps1 -- what does STREHL_DEFECT do when nobody sets it?
#
# WHY THIS EXISTS. `scripts/check-defaults.py` grades a declaration's
# `verified` field as one of "measured" (ran the binary), "code" (read the
# resolving expression) or "assumed" (UNEXAMINED, and a FAIL for anything
# claiming to be a quality switch). I am declaring four `STREHL_DEFECT*`
# switches and I want the master switch to carry "measured", because the whole
# argument for holding this correction OFF rests on the claim that unset means
# off -- and that claim, unmeasured, is exactly the kind of thing this project
# has shipped wrong three times.
#
# THE THREE ARMS, AND WHY THE THIRD IS NOT OPTIONAL. A two-arm test (unset vs
# `on`) has an uninterpretable null: if the two renders are byte-identical,
# that is equally consistent with
#
#   (a) the default is `on` and setting `on` changed nothing, and
#   (b) the variable is never read on this code path at all,
#
# which are different facts with different consequences. `STREHL_FULLRES_GATHER`
# is declared in that registry with a third arm carrying a deliberately bogus
# value, and its entry says the bogus arm "is the only reason the null case
# would have been interpretable". Same structure here:
#
#   A  unset          -> hash
#   B  STREHL_DEFECT=on   -> hash
#   C  STREHL_DEFECT=bogus -> must exit non-zero, naming the variable
#
# Arm C proves the read happens. Given the read happens, A != B proves unset
# resolves to something other than `on`; combined with the resolving
# expression at stack.rs:895 (`Err(_) => false`) that pins unset == off.
#
# SUBJECT. `coffee-bean`, because it is the stack where the correction is
# measured to fire hardest: -14.859% depth at the nominated site, p 0.0025,
# FIRES True (BUILD-DEFECT.md sec 11). If any subject can separate the arms it
# is this one, so a null here would be a strong null rather than a shrug.
#
# BACKEND. Pyramid, i.e. no `--gate` and no `--merge estimator`. The correction
# is applied by `stack.rs`'s `load_frame`, which is the pyramid loader; the
# estimator never sees it and now refuses to run with a map configured. Passing
# `--gate` here would measure the refusal, not the default.
#
# PINNING. Run against a binary built in a detached worktree at a pinned
# commit. Six agents are writing to the main tree; a hash from it is
# attributable to nobody.

$ErrorActionPreference = "Continue"

$bin     = "C:\dev\strehl-wt-defect4\.cargo-target\release\strehl.exe"
$stack   = "D:\personal\macro\coffee-bean"
$scratch = "C:\dev\strehl-out\BUILD-DEFECT\44-arms"
$limit   = 10

New-Item -ItemType Directory -Force -Path $scratch | Out-Null

function Invoke-Arm {
    param([string]$Name, [hashtable]$Env)

    $out = Join-Path $scratch "$Name.tif"
    Remove-Item $out -ErrorAction SilentlyContinue

    # Clear every defect variable first so an arm inherits nothing from the
    # shell or from the arm before it. "unset" has to actually be unset.
    foreach ($k in @("STREHL_DEFECT", "STREHL_DEFECT_MAP", "STREHL_DEFECT_ARM", "STREHL_DEFECT_HOT_FLOOR")) {
        Remove-Item "env:$k" -ErrorAction SilentlyContinue
    }
    foreach ($k in $Env.Keys) { Set-Item "env:$k" $Env[$k] }

    $log = Join-Path $scratch "$Name.log"
    & $bin stack $stack --limit $limit --srgb --auto-exposure --out $out *>&1 |
        Tee-Object -FilePath $log | Out-Null
    $code = $LASTEXITCODE

    $hash = "(no output file)"
    $size = 0
    if (Test-Path $out) {
        $hash = (Get-FileHash $out -Algorithm SHA256).Hash
        $size = (Get-Item $out).Length
    }

    foreach ($k in $Env.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }

    [PSCustomObject]@{
        arm = $Name; exit = $code; bytes = $size; sha256 = $hash
    }
}

Write-Host "=== STREHL_DEFECT three-arm default probe ==="
Write-Host "binary  : $bin"
Write-Host "commit  : $(git -C C:\dev\strehl-wt-defect4 rev-parse HEAD)"
Write-Host "stack   : $stack (--limit $limit, pyramid backend)"
Write-Host ""

$rows = @()
$rows += Invoke-Arm -Name "A-unset" -Env @{}
$rows += Invoke-Arm -Name "B-on"    -Env @{ "STREHL_DEFECT" = "on" }
$rows += Invoke-Arm -Name "C-bogus" -Env @{ "STREHL_DEFECT" = "bogus" }

$rows | Format-Table -AutoSize | Out-String -Width 120 | Write-Host

# ---- the tests. Printed values that nothing conditions on are a defect this
# project has shipped three times, so each of these prints a VERDICT.

$a = $rows[0]; $b = $rows[1]; $c = $rows[2]

Write-Host "--- verdicts ---"

if ($c.exit -eq 0) {
    Write-Host "READ       : NOT PROVEN -- bogus value was accepted (exit 0). The"
    Write-Host "             variable may not be read on this path at all."
} else {
    $named = (Select-String -Path (Join-Path $scratch "C-bogus.log") -Pattern "STREHL_DEFECT" -Quiet)
    Write-Host "READ       : PROVEN -- bogus exits $($c.exit); message names STREHL_DEFECT: $named"
}

if ($a.sha256 -eq $b.sha256) {
    Write-Host "DEFAULT    : unset == on (identical bytes). Given READ is proven,"
    Write-Host "             the default resolves to ON, or the switch does not"
    Write-Host "             reach the render on this backend."
} else {
    Write-Host "DEFAULT    : unset != on. The switch changes the render, so unset"
    Write-Host "             does NOT resolve to `on`. With stack.rs:894 (Err(_) =>"
    Write-Host "             false) that pins unset == OFF."
}

foreach ($r in @($a, $b)) {
    if ($r.exit -ne 0) { Write-Host "WARNING    : arm $($r.arm) exited $($r.exit) -- hash is not a render" }
}

Write-Host ""
Write-Host "--- what each arm reported about the map ---"
foreach ($n in @("A-unset", "B-on")) {
    $line = Select-String -Path (Join-Path $scratch "$n.log") -Pattern "defect map|defect corr" |
            ForEach-Object { $_.Line.Trim() }
    Write-Host ("{0,-8} : {1}" -f $n, ($line -join " | "))
}
