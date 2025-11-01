[CmdletBinding()]
param(
    [string]$Distribution = "Ubuntu",
    [switch]$InstallDockerDesktop,
    [switch]$InstallPodmanDesktop,
    [switch]$InstallVSCode,
    [switch]$SkipGit,
    [switch]$SkipWSL,
    [string]$HttpProxy,
    [string]$HttpsProxy,
    [string]$NoProxy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($currentUser)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell session (Run as Administrator)."
    }
}

function Write-Section([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Step([string]$Message, [scriptblock]$Action) {
    Write-Host "-- $Message..." -ForegroundColor Yellow
    & $Action
    Write-Host "   Done."
}

function Ensure-Winget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is required but not installed. Install App Installer from the Microsoft Store and re-run this script."
    }
}

function Configure-Proxies {
    param(
        [string]$HttpProxyValue,
        [string]$HttpsProxyValue,
        [string]$NoProxyValue
    )

    if ([string]::IsNullOrWhiteSpace($HttpProxyValue) -and [string]::IsNullOrWhiteSpace($HttpsProxyValue) -and [string]::IsNullOrWhiteSpace($NoProxyValue)) {
        Write-Host "No proxy values supplied; skipping proxy configuration."
        return
    }

    Write-Section "Configuring proxy environment variables"

    $envTargets = @(
        [System.EnvironmentVariableTarget]::User,
        [System.EnvironmentVariableTarget]::Machine
    )

    foreach ($target in $envTargets) {
        if ($HttpProxyValue) {
            [System.Environment]::SetEnvironmentVariable('HTTP_PROXY', $HttpProxyValue, $target)
            [System.Environment]::SetEnvironmentVariable('http_proxy', $HttpProxyValue, $target)
        }
        if ($HttpsProxyValue) {
            [System.Environment]::SetEnvironmentVariable('HTTPS_PROXY', $HttpsProxyValue, $target)
            [System.Environment]::SetEnvironmentVariable('https_proxy', $HttpsProxyValue, $target)
        }
        if ($NoProxyValue) {
            [System.Environment]::SetEnvironmentVariable('NO_PROXY', $NoProxyValue, $target)
            [System.Environment]::SetEnvironmentVariable('no_proxy', $NoProxyValue, $target)
        }
    }

    Write-Host "Proxy variables configured. Restart running shells for changes to take effect." -ForegroundColor Green
}

function Install-WindowsFeatureIfMissing {
    param(
        [string]$FeatureName
    )

    $feature = Get-WindowsOptionalFeature -Online -FeatureName $FeatureName
    if ($feature.State -ne 'Enabled') {
        Enable-WindowsOptionalFeature -Online -FeatureName $FeatureName -NoRestart
    }
}

function Ensure-WSL {
    param(
        [string]$Distro
    )

    Write-Section "Configuring Windows Subsystem for Linux"
    Invoke-Step "Enabling VirtualMachinePlatform" { Install-WindowsFeatureIfMissing -FeatureName 'VirtualMachinePlatform' }
    Invoke-Step "Enabling Microsoft-Windows-Subsystem-Linux" { Install-WindowsFeatureIfMissing -FeatureName 'Microsoft-Windows-Subsystem-Linux' }

    if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
        $installed = wsl.exe --list --quiet | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
        if ($installed -contains $Distro) {
            Write-Host "WSL distribution '$Distro' is already installed."
        } else {
            Write-Section "Installing WSL distribution '$Distro'"
            wsl.exe --install -d $Distro
            Write-Host "Reboot the machine after the installation completes if prompted." -ForegroundColor Green
        }
    } else {
        Write-Section "Installing WSL (requires reboot when complete)"
        wsl.exe --install -d $Distro
    }
}

function Install-WingetPackage {
    param(
        [string]$PackageId
    )

    Ensure-Winget
    winget install --exact --id $PackageId --silent --accept-source-agreements --accept-package-agreements
}

function Install-DockerDesktop {
    Write-Section "Installing Docker Desktop"
    Install-WingetPackage -PackageId "Docker.DockerDesktop"
}

function Install-PodmanDesktop {
    Write-Section "Installing Podman Desktop"
    Install-WingetPackage -PackageId "RedHat.Podman-Desktop"
}

function Install-VSCode {
    Write-Section "Installing Visual Studio Code"
    Install-WingetPackage -PackageId "Microsoft.VisualStudioCode"
}

function Install-Git {
    Write-Section "Installing Git for Windows"
    Install-WingetPackage -PackageId "Git.Git"
}

function Configure-VSCodeExtensions {
    if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
        Write-Host "VS Code CLI not found; skipping extension configuration."
        return
    }

    Write-Section "Installing recommended VS Code extensions"
    $extensions = @(
        'ms-vscode-remote.remote-wsl',
        'ms-vscode-remote.remote-containers',
        'ms-python.python',
        'ms-azuretools.vscode-docker'
    )

    foreach ($ext in $extensions) {
        code --install-extension $ext --force | Out-Null
    }
}

try {
    if ($SkipWSL) {
        try {
            Assert-Administrator
        }
        catch {
            Write-Warning "Administrative privileges recommended for full bootstrap; continuing due to -SkipWSL."
        }
    }
    else {
        Assert-Administrator
    }

    if ($HttpProxy -or $HttpsProxy -or $NoProxy) {
        Configure-Proxies -HttpProxyValue $HttpProxy -HttpsProxyValue $HttpsProxy -NoProxyValue $NoProxy
    }

    if (-not $SkipWSL) {
        Ensure-WSL -Distro $Distribution
    }
    else {
        Write-Section "Skipping WSL enablement per request (-SkipWSL)."
    }

    if (-not $SkipGit) {
        Install-Git
    } else {
        Write-Host "Skipping Git installation per request."
    }

    if ($InstallDockerDesktop) {
        Install-DockerDesktop
    }

    if ($InstallPodmanDesktop) {
        Install-PodmanDesktop
    }

    if ($InstallVSCode) {
        Install-VSCode
        Configure-VSCodeExtensions
    }

    Write-Section "Bootstrap complete"
    Write-Host "Next steps:" -ForegroundColor Green
    if (-not $SkipWSL) {
        Write-Host "  1. Reboot if Windows prompts you after WSL installation."
        Write-Host "  2. Launch the '$Distribution' distribution and create your Linux user."
    }
    else {
        Write-Host "  1. Install or launch WSL manually when ready."
    }
    Write-Host "  3. Clone this repository inside WSL (e.g. `git clone https://github.com/<org>/<repo>.git`)."
    Write-Host "  4. Run ./scripts/use-devcontainer.sh <stack> and reopen in VS Code."
}
catch {
    Write-Error $_
    exit 1
}
