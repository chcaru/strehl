param(
    [string]$SdkArchive = "$env:USERPROFILE\Downloads\CrSDK_v2.02.00_20260610a_Win64.zip"
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$outputRoot = Join-Path $repoRoot 'outputs\sony-control'
$sdkRoot = Join-Path $outputRoot 'sdk-2.02.00'
$buildRoot = Join-Path $outputRoot 'build'
$vswherePath = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path -LiteralPath $vswherePath)) { throw 'Install Visual Studio 2022 Build Tools with Desktop development with C++.' }
$visualStudio = & $vswherePath -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$discoveryExit = $LASTEXITCODE
if ($discoveryExit -ne 0 -or -not $visualStudio) { throw 'Visual Studio C++ build tools were not found.' }
$cmakePath = Join-Path $visualStudio 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
if (-not (Test-Path -LiteralPath $cmakePath)) { throw 'Install the C++ CMake tools component in Visual Studio Installer.' }
& python (Join-Path $PSScriptRoot 'prepare-sdk.py') $SdkArchive $sdkRoot
$prepareExit = $LASTEXITCODE
if ($prepareExit -ne 0) { throw "SDK preparation failed: $prepareExit" }
& $cmakePath -S $PSScriptRoot -B $buildRoot -G 'Visual Studio 17 2022' -A x64 "-DSONY_SDK_ROOT=$sdkRoot"
$configureExit = $LASTEXITCODE
if ($configureExit -ne 0) { throw "CMake configure failed: $configureExit" }
& $cmakePath --build $buildRoot --config Release --parallel 2
$buildExit = $LASTEXITCODE
if ($buildExit -ne 0) { throw "Native build failed: $buildExit" }
$executable = Join-Path $outputRoot 'bin\strehl-sony-control.exe'
$receipt = [ordered]@{
    builtUtc = [DateTime]::UtcNow.ToString('o')
    sdk = Get-Content -LiteralPath (Join-Path $sdkRoot 'archive-receipt.json') -Raw | ConvertFrom-Json
    generator = 'Visual Studio 17 2022; x64; Release; /W4 /WX; 2 build workers'
    executableSha256 = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
    sourceSha256 = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'strehl-sony-control.cpp') -Algorithm SHA256).Hash
    sourceFilesSha256 = [ordered]@{
        'strehl-sony-control.cpp' = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'strehl-sony-control.cpp') -Algorithm SHA256).Hash
        'card-capture.h' = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'card-capture.h') -Algorithm SHA256).Hash
        'CMakeLists.txt' = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'CMakeLists.txt') -Algorithm SHA256).Hash
    }
}
$receiptText = ($receipt | ConvertTo-Json -Depth 6) + "`n"
[IO.File]::WriteAllText((Join-Path $outputRoot 'build-receipt.json'), $receiptText, [Text.UTF8Encoding]::new($false))
Write-Output "Built: $executable"
