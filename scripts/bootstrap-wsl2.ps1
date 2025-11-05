<#
.SYNOPSIS
  Bootstraps a Windows workstation for the ansible-devcontainer-vscode project.
.DESCRIPTION
  Enables WSL2, installs Ubuntu, configures Docker Desktop integration, ensures
  Visual Studio Code + Dev Containers extension are present, and clones the repo
  inside the default distribution. Requires administrative PowerShell.
#>

[CmdletBinding()]
param(
    [switch]$UsePodman,
    [string]$RepositoryUrl = "https://github.com/malpanez/ansible-devcontainer-vscode.git",
    [string]$WslDistro = "Ubuntu",
    [string]$TargetDirectory = "$HOME\\Projects"
)

function Assert-Admin {
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell session."
    }
}

function Enable-WSLFeatures {
    Write-Host "Enabling WSL and Virtual Machine Platform..." -ForegroundColor Cyan
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Null
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Null
}

function Install-WSLDistribution {
    Write-Host "Installing/Updating WSL with distribution $WslDistro..." -ForegroundColor Cyan
    wsl.exe --install -d $WslDistro
}

function Install-DockerDesktop {
    if ($UsePodman) {
        Write-Host "Skipping Docker Desktop (UsePodman specified)." -ForegroundColor Yellow
        return
    }

    $dockerPath = "$Env:ProgramFiles\\Docker\\Docker\\Docker Desktop.exe"
    if (Test-Path $dockerPath) {
        Write-Host "Docker Desktop already installed." -ForegroundColor Green
        return
    }

    $installer = "$env:TEMP\\DockerDesktopInstaller.exe"
    Write-Host "Downloading Docker Desktop..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" -OutFile $installer
    Write-Host "Installing Docker Desktop..." -ForegroundColor Cyan
    & $installer install --accept-license --quiet
}

function Configure-DockerWSLIntegration {
    if ($UsePodman) { return }
    $settingsPath = "$Env:APPDATA\\Docker\\settings.json"
    if (-not (Test-Path $settingsPath)) { return }
    $settings = Get-Content $settingsPath | ConvertFrom-Json
    if (-not $settings.wslEngineEnabled) {
        $settings.wslEngineEnabled = $true
    }
    if (-not $settings.WSLDistros) {
        $settings | Add-Member -MemberType NoteProperty -Name WSLDistros -Value @{}
    }
    $settings.WSLDistros[$WslDistro] = $true
    $settings | ConvertTo-Json -Depth 5 | Set-Content $settingsPath
    Write-Host "Enabled Docker Desktop WSL2 integration for $WslDistro." -ForegroundColor Green
}

function Install-VSCode {
    if (Get-Command code -ErrorAction SilentlyContinue) {
        Write-Host "VS Code already installed." -ForegroundColor Green
    }
    else {
        $installer = "$env:TEMP\\VSCodeSetup.exe"
        Write-Host "Downloading Visual Studio Code..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri "https://code.visualstudio.com/sha/download?build=stable&os=win32-x64-user" -OutFile $installer
        & $installer /VERYSILENT /MERGETASKS=!runcode | Out-Null
    }
    Write-Host "Ensuring Dev Containers extension is installed..." -ForegroundColor Cyan
    code --install-extension ms-vscode-remote.remote-containers --force | Out-Null
}

function Clone-Repository {
    Write-Host "Preparing repository location..." -ForegroundColor Cyan
    if (-not (Test-Path $TargetDirectory)) {
        New-Item -ItemType Directory -Path $TargetDirectory | Out-Null
    }

    $cloneCommand = "wsl.exe";
    $repoDir = "$TargetDirectory/ansible-devcontainer-vscode"
    if (Test-Path $repoDir) {
        Write-Host "Repository already exists at $repoDir" -ForegroundColor Yellow
        return
    }

    $cloneline = "cd ~ && mkdir -p Projects && cd Projects && git clone $RepositoryUrl"
    wsl.exe -d $WslDistro -- bash -lc "$cloneline"
    Write-Host "Repository cloned inside $WslDistro" -ForegroundColor Green
}

function Launch-VSCodeRemote {
    $command = "cd ~/Projects/ansible-devcontainer-vscode && code ."
    wsl.exe -d $WslDistro -- bash -lc "$command"
}

try {
    Assert-Admin
    Enable-WSLFeatures
    Install-WSLDistribution
    Install-DockerDesktop
    Configure-DockerWSLIntegration
    Install-VSCode
    Clone-Repository
    Launch-VSCodeRemote
    Write-Host "Bootstrap complete." -ForegroundColor Green
    Write-Host "If prompted, reopen the project in a Dev Container." -ForegroundColor Green
}
catch {
    Write-Error $_
    exit 1
}
