param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("small", "full")]
    [string]$Class,

    [Parameter(Mandatory = $true)]
    [string]$Output
)

$samples = Get-Counter '\Processor(_Total)\% Processor Time' `
    -SampleInterval 1 -MaxSamples 5
$cpu = @($samples.CounterSamples | ForEach-Object { $_.CookedValue })
$os = Get-CimInstance Win32_OperatingSystem
$freeGiB = [double]$os.FreePhysicalMemory * 1KB / 1GB
$totalGiB = [double]$os.TotalVisibleMemorySize * 1KB / 1GB
$meanCpu = ($cpu | Measure-Object -Average).Average
$cpuLimit = if ($Class -eq "small") { 50.0 } else { 35.0 }
$memoryMinimum = if ($Class -eq "small") { 8.0 } else { 24.0 }
$passed = ($meanCpu -le $cpuLimit) -and ($freeGiB -ge $memoryMinimum)

$payload = [ordered]@{
    measured_at = (Get-Date).ToUniversalTime().ToString("o")
    class = $Class
    samples_seconds = 5
    cpu_samples_percent = $cpu
    mean_cpu_percent = $meanCpu
    cpu_limit_percent = $cpuLimit
    free_memory_gib = $freeGiB
    total_memory_gib = $totalGiB
    minimum_free_memory_gib = $memoryMinimum
    pass = $passed
}

$parent = Split-Path -Parent $Output
if ($parent) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
}
$payload | ConvertTo-Json -Depth 4 | Set-Content -Path $Output -Encoding UTF8
$payload | ConvertTo-Json -Depth 4
if (-not $passed) {
    exit 2
}

