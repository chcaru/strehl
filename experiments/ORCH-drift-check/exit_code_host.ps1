# ORCH independent probe of M108's claim that the $LASTEXITCODE corruption VALUE
# is PowerShell-EDITION dependent, and that a "nonzero" gate can therefore be
# manufactured by the trap.
#
# The disputed clause is mine: rule 47's addendum says a PASS taken from an
# observed nonzero exit code is safe because truncation cannot invent a nonzero.
# M108 measured -1 under 5.1. If that is right, my clause is false in exactly the
# gate shape a RED CONTROL uses, and I broadcast it to seven agents.
#
# Registered predictions, written before the run (scored by bar H1/H2):
#   H1  under PS 7.x  the corrupted value is 0   -> gate "-ne 0" FAILS (correct-by-luck)
#   H2  under PS 5.1  the corrupted value is -1  -> gate "-ne 0" PASSES (false PASS)
#   H3  -First 51 on 50 lines preserves 1 on BOTH editions
#   H4  -Last 3 and unfiltered preserve 1 on BOTH editions
# A run in which H2 does not reproduce leaves my original clause standing.

param([string]$Tag = "unknown")
$ErrorActionPreference = "Continue"

$prod = Join-Path $PSScriptRoot "producer_n.cmd"
if (-not (Test-Path $prod)) { throw "producer missing: $prod" }

function Preclear {
    cmd /c exit 0
    if ($LASTEXITCODE -ne 0) { throw "PRECLEAR FAILED - probe is invalid" }
}

# Warm once: a cold first invocation preserves the code (fact 1437, 1/320).
$junk = & $prod 5
$junk = $null

$arms = @(
    @{ Name = "50 lines | -First 3";  N = 50; Mode = "first"; K = 3  },
    @{ Name = "50 lines | -First 50"; N = 50; Mode = "first"; K = 50 },
    @{ Name = "50 lines | -First 51"; N = 50; Mode = "first"; K = 51 },
    @{ Name = " 5 lines | -First 3";  N = 5;  Mode = "first"; K = 3  },
    @{ Name = "50 lines | -Last 3";   N = 50; Mode = "last";  K = 3  },
    @{ Name = "50 lines | unfiltered";N = 50; Mode = "none";  K = 0  }
)

$rows = @()
foreach ($a in $arms) {
    Preclear
    switch ($a.Mode) {
        "first" { $junk = & $prod $a.N | Select-Object -First $a.K }
        "last"  { $junk = & $prod $a.N | Select-Object -Last  $a.K }
        "none"  { $junk = & $prod $a.N }
    }
    $code = $LASTEXITCODE
    $rows += [pscustomobject]@{
        Arm      = $a.Name
        Code     = $code
        Gate_ne0 = $(if ($code -ne 0) { "PASS-nonzero" } else { "fail-zero" })
        Gate_eq1 = $(if ($code -eq 1) { "PASS-eq1" }     else { "fail-ne-1" })
    }
}

"=== HOST: $Tag ==="
"PSVersion  : $($PSVersionTable.PSVersion)"
"PSEdition  : $($PSVersionTable.PSEdition)"
$rows | Format-Table -AutoSize | Out-String -Width 200

# Score the registered predictions.
$corrupt = $rows | Where-Object { $_.Arm -like "*-First 3" -or $_.Arm -eq "50 lines | -First 50" }
$clean   = $rows | Where-Object { $_.Arm -eq "50 lines | -First 51" -or $_.Arm -eq "50 lines | -Last 3" -or $_.Arm -eq "50 lines | unfiltered" }
$vals    = ($corrupt.Code | Sort-Object -Unique) -join ","
$falsePass = @($corrupt | Where-Object { $_.Gate_ne0 -eq "PASS-nonzero" }).Count

"corrupted arms n=$($corrupt.Count)  distinct value(s)=$vals"
"clean arms     n=$($clean.Count)    all preserve 1 : $(@($clean | Where-Object { $_.Code -eq 1 }).Count -eq $clean.Count)"
"FALSE-PASS count under 'if (`$code -ne 0)' : $falsePass of $($corrupt.Count)"
if ($falsePass -gt 0) {
    "VERDICT: H2 CONFIRMED on this host - a truncation artifact CAN manufacture a nonzero PASS."
} else {
    "VERDICT: corrupted value is 0 here - the naive -ne 0 gate fails closed on this host."
}
