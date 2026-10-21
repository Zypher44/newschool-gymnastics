[CmdletBinding()]
param([switch]$Force)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Bstr = [IntPtr]::Zero
$OldPath = $env:PATH
$OldDatabaseUrl = [Environment]::GetEnvironmentVariable('NS_BACKUP_DATABASE_URL', 'Process')
$LockStream = $null
$Failed = $false
$BackupRoot = $null
try {
    $LockStream = [IO.File]::Open((Join-Path $PSScriptRoot 'backup.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    $Config = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'config.json') -Raw | ConvertFrom-Json
    $BackupRoot = [string]$Config.BackupRoot
    if (-not (Test-Path -LiteralPath $BackupRoot -PathType Container)) { throw 'Backup folder is unavailable.' }
    $SuccessFile = Join-Path $PSScriptRoot 'last-success.json'
    if (-not $Force -and (Test-Path -LiteralPath $SuccessFile)) {
        $Previous = Get-Content -LiteralPath $SuccessFile -Raw | ConvertFrom-Json
        if ([datetime]::Parse($Previous.Time).ToUniversalTime() -gt [datetime]::UtcNow.AddHours(-12)) {
            Write-Host 'A successful backup is less than 12 hours old; skipping catch-up.'
            return
        }
    }
    $EncryptedUrl = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'connection.dpapi') -Raw).Trim()
    $SecureUrl = ConvertTo-SecureString -String $EncryptedUrl
    $Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureUrl)
    $env:NS_BACKUP_DATABASE_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)
    # Restrict this package to staging. Do not accidentally copy production data.
    & ([string]$Config.PythonExe) -c "import os,urllib.parse; u=urllib.parse.urlsplit(os.environ['NS_BACKUP_DATABASE_URL']); assert u.scheme in ('postgres', 'postgresql') and urllib.parse.unquote(u.path[1:]) == 'newschool_v2_test'"
    if ($LASTEXITCODE -ne 0) { throw 'Use the newschool_v2_test database External URL.' }
    $env:PATH = [string]$Config.PostgresBin + [IO.Path]::PathSeparator + $OldPath
    $Name = 'newschool-v2-test-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.dump'
    $Archive = Join-Path $BackupRoot $Name
    & ([string]$Config.PythonExe) (Join-Path $PSScriptRoot 'database_recovery.py') backup $Archive
    if ($LASTEXITCODE -ne 0) { throw 'Database export failed.' }
    # Retention applies only after success and only to validated package archives.
    $Verified = @()
    foreach ($File in (Get-ChildItem -LiteralPath $BackupRoot -Filter 'newschool-v2-test-*.dump' -File | Sort-Object LastWriteTimeUtc -Descending)) {
        $Manifest = $File.FullName + '.json'
        if (-not (Test-Path -LiteralPath $Manifest)) { continue }
        try {
            $Record = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
            if ((Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash -ieq [string]$Record.sha256) { $Verified += $File }
        } catch { continue }
    }
    $Keep = [int]$Config.KeepBackups
    if ($Keep -lt 2) { throw 'Retention must keep at least two successful backups.' }
    foreach ($File in @($Verified | Select-Object -Skip $Keep)) {
        Remove-Item -LiteralPath ($File.FullName + '.json') -ErrorAction Stop
        Remove-Item -LiteralPath $File.FullName -ErrorAction Stop
    }
    $Status = @{ Time = [datetime]::UtcNow.ToString('o'); Success = $true; Archive = $Name; RestoreTested = $false }
    $Status | ConvertTo-Json | Set-Content -LiteralPath $SuccessFile -Encoding UTF8
    $Status | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'last-run.json') -Encoding UTF8
    Write-Host 'Backup succeeded. Check the backup folder and keep a second encrypted copy off this PC.'
} catch {
    $Failed = $true
    # Intentionally do not write exception text, connection strings, or passwords.
    @{ Time = [datetime]::UtcNow.ToString('o'); Success = $false; Message = 'Backup failed; check network, Render external access, disk space, saved credentials, and PostgreSQL tools.' } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'last-run.json') -Encoding UTF8
    Write-Host 'Backup failed. See last-run.json in the installation folder. Credentials have not been printed.'
} finally {
    if ($Bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr) }
    $env:PATH = $OldPath
    [Environment]::SetEnvironmentVariable('NS_BACKUP_DATABASE_URL', $OldDatabaseUrl, 'Process')
    if ($null -ne $LockStream) { $LockStream.Dispose() }
}
if ($Failed) { exit 1 }
