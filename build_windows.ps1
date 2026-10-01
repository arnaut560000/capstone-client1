param([switch]$CreateShortcut)
$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot
$buildEnvironment = Join-Path $env:LOCALAPPDATA 'OSYConnect\build-environment'
$buildPython = Join-Path $buildEnvironment 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $buildPython)) {
    python -m venv $buildEnvironment
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the packaging environment.' }
}
& $buildPython -m pip install --disable-pip-version-check -r (Join-Path $projectDir 'build-requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Could not install packaging dependencies.' }
$buildDir = Join-Path $projectDir 'build'
$outputDir = Join-Path $projectDir 'dist'
& $buildPython -m PyInstaller --noconfirm --onefile --windowed --name 'OSY Connect' --collect-all PIL --collect-all reportlab --distpath $outputDir --workpath (Join-Path $buildDir 'pyinstaller') --specpath $buildDir (Join-Path $projectDir 'main.py')
if ($LASTEXITCODE -ne 0) { throw 'Executable packaging failed.' }
$builtExe = Join-Path $outputDir 'OSY Connect.exe'
$report = Join-Path $buildDir ('packaged-check-' + [guid]::NewGuid().ToString('N') + '.json')
$check = Start-Process -FilePath $builtExe -ArgumentList @('--self-test', ('"' + $report + '"')) -WindowStyle Hidden -PassThru
if (-not $check.WaitForExit(90000)) { throw 'Packaged smoke test did not finish; inspect the test app before retrying.' }
if ($check.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $report)) { throw "Packaged smoke test failed. See $report" }
$result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
if (-not $result.ok -or -not $result.frozen) { throw "Packaged smoke test failed. See $report" }
$installedExe = Join-Path $projectDir 'OSY Connect.exe'
Copy-Item -LiteralPath $builtExe -Destination $installedExe -Force
if ($CreateShortcut) {
    $desktopFolder = [Environment]::GetFolderPath('Desktop')
    $shortcutPath = Join-Path $desktopFolder 'OSY Connect.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $installedExe
    $shortcut.WorkingDirectory = $projectDir
    $shortcut.Description = 'OSY Connect - Youth Monitoring'
    $shortcut.IconLocation = $installedExe + ',0'
    $shortcut.Save()
    Write-Output "Desktop shortcut: $shortcutPath"
}
Write-Output "Executable ready: $installedExe"
Write-Output "Packaged checks passed: $($result.checks -join ', ')"
