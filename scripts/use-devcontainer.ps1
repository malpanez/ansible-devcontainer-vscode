param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Stack,

    [switch]$Prune
)

function Get-TemplateSignature {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TemplateDir
    )

    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    $sha256 = [System.Security.Cryptography.SHA256]::Create()

    try {
        $checksums = Get-ChildItem -Path $TemplateDir -Recurse -File | Sort-Object FullName | ForEach-Object {
            $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
            $hashBytes = $sha1.ComputeHash($bytes)
            [System.BitConverter]::ToString($hashBytes).Replace("-", "").ToLowerInvariant()
        }

        $joined = [System.Text.Encoding]::UTF8.GetBytes(($checksums -join ""))
        $signatureBytes = $sha256.ComputeHash($joined)
        return [System.BitConverter]::ToString($signatureBytes).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha1.Dispose()
        $sha256.Dispose()
    }
}

function Write-TemplateMetadata {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Stack,
        [Parameter(Mandatory = $true)]
        [string]$TemplateDir,
        [Parameter(Mandatory = $true)]
        [string]$TargetDir
    )

    $metadata = @{
        stack = $Stack
        source = [System.IO.Path]::GetFullPath($TemplateDir)
        signature = Get-TemplateSignature -TemplateDir $TemplateDir
    }

    $metadataPath = Join-Path $TargetDir ".template-metadata.json"
    $metadata | ConvertTo-Json | Set-Content -Path $metadataPath -Encoding utf8
}

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
Write-TemplateMetadata -Stack $Stack -TemplateDir $templateDir -TargetDir $targetDir

Write-Host ">> .devcontainer now matches '$Stack'. Use VS Code's 'Reopen in Container' to apply the change." -ForegroundColor Green

if ($Prune.IsPresent) {
    Remove-DevcontainerArtifacts -WorkspacePath $repoRoot
}
