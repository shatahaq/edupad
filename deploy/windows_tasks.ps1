# Jadwal otomatis di Windows (untuk uji coba di laptop).
# Pakai : powershell -ExecutionPolicy Bypass -File deploy\windows_tasks.ps1
# Hapus : powershell -ExecutionPolicy Bypass -File deploy\windows_tasks.ps1 -Remove
param([switch]$Remove)

$root = Split-Path $PSScriptRoot
$pythonw = Join-Path (Split-Path (Get-Command python).Source) "pythonw.exe"

if ($Remove) {
    schtasks /Delete /TN "EduPad\keepalive" /F
    schtasks /Delete /TN "EduPad\pipeline" /F
    return
}

# pythonw: tanpa jendela konsol. Working directory diatur oleh config.BASE_DIR.
schtasks /Create /F /TN "EduPad\keepalive" /SC MINUTE /MO 20 /TR "`"$pythonw`" -m edupad keepalive"
schtasks /Create /F /TN "EduPad\pipeline" /SC HOURLY /MO 2 /TR "`"$pythonw`" -m edupad pipeline"
Write-Host "Terpasang. Log di $root\logs"
