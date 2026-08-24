# DIAGNOSIS: my quota probe read "preserved" for 4000-line | -First 3, but my earlier
# probe read LOST for that exact case on this machine. One of the two harnesses is broken.
# The only structural difference is HOW the filter is invoked:
#   earlier: literal   python $py 2>&1 | Select-Object -First 3 | Out-Null
#   later:   indirect  python $py 2>&1 | & $filter | Out-Null     (filter = { Select-Object -First 3 })
# Hypothesis: & {scriptblock} is a pipeline boundary, so StopUpstreamCommandsException is
# absorbed there and never reaches the native command. If so the indirection DESTROYS the
# phenomenon and my quota probe was vacuous.

function Preclear {
    cmd /c exit 0
    if ($LASTEXITCODE -ne 0) { throw "preclear failed" }
}

$lines = @("import sys", "for i in range(50): print('x'*60)", "sys.exit(1)")
$py = 'C:\dev\strehl-out\M107-chroma\verify\n50b.py'
Set-Content -Path $py -Value $lines

"true exit code is 1 in every arm; pre-cleared to 0 before each rep"
""

# --- FORM A: literal pipeline, no indirection ---
$a = @()
for ($i = 0; $i -lt 5; $i++) {
    Preclear
    python $py 2>&1 | Select-Object -First 3 | Out-Null
    $a += $LASTEXITCODE
}
"FORM A  literal   | -First 3   -> {0}" -f ($a -join ',')

# --- FORM B: scriptblock indirection, exactly as my quota probe did it ---
$sb = { Select-Object -First 3 }
$b = @()
for ($i = 0; $i -lt 5; $i++) {
    Preclear
    python $py 2>&1 | & $sb | Out-Null
    $b += $LASTEXITCODE
}
"FORM B  & scriptblock | -First 3 -> {0}" -f ($b -join ',')

# --- FORM C: literal, but inside a function (isolates 'function' from 'scriptblock arg') ---
function ArmLiteral([string]$p) {
    $c = @()
    for ($i = 0; $i -lt 5; $i++) {
        Preclear
        python $p 2>&1 | Select-Object -First 3 | Out-Null
        $c += $LASTEXITCODE
    }
    return $c
}
"FORM C  literal-in-function  -> {0}" -f ((ArmLiteral $py) -join ',')

""
"If A and C are 0 and B is 1, the scriptblock indirection was the defect and the"
"quota probe proved nothing."
