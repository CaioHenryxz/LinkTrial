# Registers (or removes) the LinkTrial daily sync in Windows Task Scheduler.
# Usage (PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts\install_windows_task.ps1            # daily 06:00
#   powershell -ExecutionPolicy Bypass -File scripts\install_windows_task.ps1 -Time 05:30
#   powershell -ExecutionPolicy Bypass -File scripts\install_windows_task.ps1 -Uninstall
param([string]$Time = "06:00", [switch]$Uninstall, [string]$Python = "")
$TaskName = "LinkTrial-DailySync"
$Root = Split-Path -Parent $PSScriptRoot
if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Removida: $TaskName"; exit 0
}
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Root\scripts\sync.py`"" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "LinkTrial: sincroniza estudos oncologicos do ClinicalTrials.gov (CRUD + auditoria)" -Force | Out-Null
Write-Output "Agendada: $TaskName diariamente as $Time ($Python)"
Write-Output "Rodar agora:  Start-ScheduledTask -TaskName $TaskName"
