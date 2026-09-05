param(
    [Parameter(Mandatory = $true)]
    [int] $RuntimePid,

    [Parameter(Mandatory = $true)]
    [int] $HarnessPid,

    [Parameter(Mandatory = $true)]
    [string] $Output,

    [int] $DelaySeconds = 8,

    [int] $MaxSeconds = 1200
)

$ErrorActionPreference = 'Stop'

Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class M139NativeProcess {
    [DllImport("ntdll.dll")]
    public static extern int NtSuspendProcess(IntPtr processHandle);

    [DllImport("ntdll.dll")]
    public static extern int NtResumeProcess(IntPtr processHandle);
}
'@

$utf8 = [System.Text.UTF8Encoding]::new($false)
$result = [ordered]@{
    schema = 1
    evidence_tag = 'VERIFIED'
    measured_commit = '8009447e059febb8f9c59fda509f141835d6abdb'
    generated_utc = [DateTime]::UtcNow.ToString('o')
    runtime_pid = $RuntimePid
    harness_pid = $HarnessPid
    delay_seconds = $DelaySeconds
    max_seconds = $MaxSeconds
    suspended_utc = $null
    harness_completed_utc = $null
    resumed_utc = $null
    disposition = $null
    suspend_status = $null
    resume_status = $null
}

$runtime = $null
$suspended = $false
try {
    Get-Process -Id $HarnessPid -ErrorAction Stop | Out-Null
    $runtime = Get-Process -Id $RuntimePid -ErrorAction Stop
    Start-Sleep -Seconds $DelaySeconds

    Get-Process -Id $HarnessPid -ErrorAction Stop | Out-Null
    $result.suspend_status = [M139NativeProcess]::NtSuspendProcess($runtime.Handle)
    if ($result.suspend_status -ne 0) {
        throw "NtSuspendProcess failed with status $($result.suspend_status)"
    }
    $suspended = $true
    $result.suspended_utc = [DateTime]::UtcNow.ToString('o')

    $deadline = [DateTime]::UtcNow.AddSeconds($MaxSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (-not (Get-Process -Id $HarnessPid -ErrorAction SilentlyContinue)) {
            $result.harness_completed_utc = [DateTime]::UtcNow.ToString('o')
            $result.disposition = 'HARNESS_EXITED'
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $result.disposition) {
        $result.disposition = 'TIMEOUT'
    }
}
catch {
    $result.disposition = 'ERROR'
    $result.error = $_.Exception.Message
}
finally {
    if ($suspended) {
        $result.resume_status = [M139NativeProcess]::NtResumeProcess($runtime.Handle)
    }
    $result.resumed_utc = [DateTime]::UtcNow.ToString('o')
    $parent = Split-Path -Parent $Output
    if ($parent) {
        [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    }
    [System.IO.File]::WriteAllText(
        $Output,
        (($result | ConvertTo-Json -Depth 6) + "`n"),
        $utf8
    )
}

$result | ConvertTo-Json -Depth 6
if ($result.disposition -ne 'HARNESS_EXITED' -or $result.resume_status -ne 0) {
    exit 1
}
