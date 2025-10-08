# Rebuild the Mimic Motion Conda environment (PowerShell version)

$condaRoot = ${env:CONDA_ROOT}
if (-not $condaRoot -or -not (Test-Path $condaRoot)) {
    $condaRoot = Join-Path $env:USERPROFILE 'miniconda3'
}

$condaExe = Join-Path $condaRoot 'Scripts\conda.exe'
if (-not (Test-Path $condaExe)) {
    Write-Error "Could not find conda at '$condaExe'. Set CONDA_ROOT or adjust this script."
    exit 1
}

$envName = 'mimic'
$yml = 'environment.yml'

# Remove existing environment (safe even if it doesn't exist).
& $condaExe env remove -n $envName -y 2>$null

Write-Host "Creating environment from $yml"
& $condaExe env create -f $yml

Write-Host "Upgrading pip, setuptools, and wheel"
& $condaExe run -n $envName python -m pip install --upgrade pip setuptools wheel

Write-Host "Exporting requirements.txt"
$freeze = & $condaExe run -n $envName python -m pip freeze
$freeze | Out-File -FilePath "requirements.txt" -Encoding ascii

Write-Host "Done. Activate with: conda activate $envName"