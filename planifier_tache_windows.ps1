<#
Utilitaire — planifie l'exécution quotidienne de l'agent sur une VM/serveur
Windows, via le Planificateur de tâches Windows.

À exécuter EN ADMINISTRATEUR, une seule fois, depuis le dossier du projet sur
le serveur (le chemin est déduit automatiquement, pas besoin de le modifier).

Usage :
    .\planifier_tache_windows.ps1                  # tous les jours à 8h30 (défaut)
    .\planifier_tache_windows.ps1 -Heure "06:00"    # à une autre heure

Ne fait PAS partie de l'exécution normale de l'agent (main.py) : c'est un
utilitaire de déploiement, à lancer une fois par serveur.
#>

param(
    [string]$Heure = "08:30"
)

$cheminProjet = $PSScriptRoot
$cheminPython = Join-Path $cheminProjet ".venv\Scripts\python.exe"
$nomTache = "Agent prospection G2S"

if (-not (Test-Path $cheminPython)) {
    Write-Error "Environnement virtuel introuvable ($cheminPython). Créer d'abord le .venv (python -m venv .venv ; pip install -r requirements.txt) avant de planifier la tâche."
    exit 1
}

$action = New-ScheduledTaskAction -Execute $cheminPython -Argument "main.py" -WorkingDirectory $cheminProjet
$trigger = New-ScheduledTaskTrigger -Daily -At $Heure
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $nomTache -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description "Exécute l'agent de prospection G2S tous les jours à $Heure" -Force | Out-Null

Write-Host "Tâche « $nomTache » créée (tous les jours à $Heure, dossier $cheminProjet)."
Write-Host "Test immédiat..."
Start-ScheduledTask -TaskName $nomTache
Start-Sleep -Seconds 5
Get-ScheduledTaskInfo -TaskName $nomTache | Format-List TaskName, LastRunTime, LastTaskResult, NextRunTime
