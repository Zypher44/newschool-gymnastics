# Run from Windows PowerShell 5.1 or later, under your normal Windows account.
[CmdletBinding()]
param(
    [string]$DailyTime = '20:00',
    [ValidateRange(2, 365)][int]$KeepBackups = 30,
    [string]$PostgresBin = 'C:\Program Files\PostgreSQL\18\bin'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'This installer is for Windows only.' }
$ParsedTime = [datetime]::ParseExact($DailyTime, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
if (-not (Test-Path -LiteralPath (Join-Path $PostgresBin 'pg_dump.exe'))) {
    $PostgresBin = Read-Host 'Folder containing PostgreSQL 18 pg_dump.exe (example C:\Program Files\PostgreSQL\18\bin)'
}
foreach ($Tool in @('pg_dump.exe', 'pg_restore.exe', 'psql.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $PostgresBin $Tool))) { throw "Missing $Tool. Install PostgreSQL 18 client tools first." }
}
$Version = & (Join-Path $PostgresBin 'pg_dump.exe') --version
if ($LASTEXITCODE -ne 0 -or $Version -notmatch 'PostgreSQL\) 18\.') { throw 'Use PostgreSQL 18 client tools for this test database.' }
$PythonExe = (Get-Command python.exe -ErrorAction Stop).Source
& $PythonExe -c 'import sys; assert sys.version_info >= (3, 10)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 or later must be available as python.exe.' }
foreach ($File in @('Run-NewSchoolBackup.ps1', 'database_recovery.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $File))) { throw "Extract the full ZIP before running setup. Missing $File." }
}
$InstallRoot = Join-Path $env:LOCALAPPDATA 'NewSchoolBackup'
$BackupRoot = Join-Path $env:USERPROFILE 'NewSchoolBackups'
$Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
foreach ($Directory in @($InstallRoot, $BackupRoot)) {
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    $Acl = [Security.AccessControl.DirectorySecurity]::new()
    $Acl.SetAccessRuleProtection($true, $false)
    $Acl.SetOwner($Identity.User)
    foreach ($Sid in @($Identity.User, [Security.Principal.SecurityIdentifier]::new('S-1-5-18'))) {
        $Rule = [Security.AccessControl.FileSystemAccessRule]::new($Sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $Acl.AddAccessRule($Rule)
    }
    Set-Acl -LiteralPath $Directory -AclObject $Acl
}
$TaskName = 'NewSchool - Daily Test Database Backup'
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Disable-ScheduledTask -TaskName $TaskName | Out-Null
    Stop-ScheduledTask -TaskName $TaskName
}
$SecureUrl = Read-Host 'Paste the TEST database External Database URL (input is hidden)' -AsSecureString
$SecureUrl | ConvertFrom-SecureString | Set-Content -LiteralPath (Join-Path $InstallRoot 'connection.dpapi') -Encoding ASCII
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Run-NewSchoolBackup.ps1') -Destination $InstallRoot -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'database_recovery.py') -Destination $InstallRoot -Force
@{ PythonExe = $PythonExe; PostgresBin = $PostgresBin; BackupRoot = $BackupRoot; KeepBackups = $KeepBackups } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $InstallRoot 'config.json') -Encoding UTF8
Write-Host 'Testing the first backup. The daily task will be registered only if this succeeds.'
$PowerShellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$Runner = Join-Path $InstallRoot 'Run-NewSchoolBackup.ps1'
& $PowerShellExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $Runner -Force
if ($LASTEXITCODE -ne 0) {
    throw 'First backup failed. No daily task is enabled. Check Render external access, the test URL, and PostgreSQL tools, then run setup again.'
}
$TaskArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $Runner + '" -Force'
$Action = New-ScheduledTaskAction -Execute $PowerShellExe -Argument $TaskArgs -WorkingDirectory $InstallRoot
$Daily = New-ScheduledTaskTrigger -Daily -At $ParsedTime
$Logon = New-ScheduledTaskTrigger -AtLogOn -User $Identity.Name
$Principal = New-ScheduledTaskPrincipal -UserId $Identity.Name -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 15) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger @($Daily, $Logon) -Principal $Principal `
    -Settings $Settings -Description 'Back up the NewSchool test database to this PC. Requires this Windows user to be signed in and network access.' -Force | Out-Null
Write-Host "Ready: daily at $DailyTime local time, plus catch-up at sign-in. Keep newest $KeepBackups successful backups."
Write-Host "Backup folder: $BackupRoot"
Write-Host 'Your PC must be on, awake, connected, and signed in (a locked screen is fine). No restore has been performed.'
