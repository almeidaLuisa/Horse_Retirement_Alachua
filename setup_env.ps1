<#
Usage (PowerShell):
  .\setup_env.ps1

This script will create a virtual environment in `.venv`, activate it for the session,
upgrade pip, and install packages from `requirements.txt`.
#>

$venvDir = "$PSScriptRoot\.venv"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not found in PATH. Please install Python 3.8+ and re-run this script."
    exit 1
}

if (-not (Test-Path $venvDir)) {
    python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create venv"; exit 1 }
}

Write-Host "Activating virtual environment located at $venvDir"
. "$venvDir\Scripts\Activate.ps1"

Write-Host "Upgrading pip and installing requirements..."
python -m pip install --upgrade pip
pip install -r "$PSScriptRoot\requirements.txt"

Write-Host "Environment ready. To activate later run:` .\.venv\Scripts\Activate.ps1`"
