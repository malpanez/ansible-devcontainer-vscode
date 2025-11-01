param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Stack,

    [switch]$Prune
)

function Remove-DevcontainerArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspacePath
    )

    $containerCli = $null
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $containerCli = "docker"
    }
    elseif (Get-Command podman -ErrorAction SilentlyContinue) {
        $containerCli = "podman"
    }

    if (-not $containerCli) {
        Write-Warning "No container CLI (docker/podman) found; skipping optional clean-up."
        return
    }

    $resolvedPath = [System.IO.Path]::GetFullPath($WorkspacePath)
    Write-Host ">> Pruning Dev Container resources for '$resolvedPath' using $containerCli ..." -ForegroundColor Yellow

    $filter = "label=devcontainer.local_folder=$resolvedPath"

    $containers = & $containerCli ps -aq --filter "$filter"
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($containers)) {
        $containers -split "[\r\n]+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object {
            & $containerCli rm -f $_ | Out-Null
        }
    }

    $volumes = & $containerCli volume ls --filter "$filter" --format "{{.Name}}"
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($volumes)) {
        $volumes -split "[\r\n]+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object {
            & $containerCli volume rm $_ | Out-Null
        }
    }

    Write-Host ">> Clean-up complete." -ForegroundColor Green
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$templateRoot = Join-Path $repoRoot "devcontainers"
$targetDir = Join-Path $repoRoot ".devcontainer"
$templateDir = Join-Path $templateRoot $Stack

if (-not (Test-Path $templateDir)) {
    Write-Error "Unknown stack '$Stack'. Available stacks: $(Get-ChildItem $templateRoot | Where-Object { $_.PSIsContainer } | ForEach-Object { $_.Name } | Sort-Object -Unique -join ', ')"
    exit 1
}

Write-Host ">> Switching Dev Container to '$Stack' ..." -ForegroundColor Green
if (Test-Path $targetDir) {
    Remove-Item $targetDir -Recurse -Force
}
New-Item -ItemType Directory -Path $targetDir | Out-Null

Copy-Item (Join-Path $templateDir '*') -Destination $targetDir -Recurse

Write-Host ">> .devcontainer now matches '$Stack'. Use VS Code's 'Reopen in Container' to apply the change." -ForegroundColor Green

if ($Prune.IsPresent) {
    Remove-DevcontainerArtifacts -WorkspacePath $repoRoot
}
