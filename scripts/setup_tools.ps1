[CmdletBinding()]
param(
    [ValidateSet('core','qa','fonts','media','ocr','cat','patching','all')]
    [string]$Profile = 'core',
    [switch]$InstallApps
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root '.tools\venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
$Constraints = Join-Path $Root 'requirements\constraints-20260926.txt'

if (-not (Test-Path -LiteralPath $Python)) {
    python -m venv $Venv
}
& $Python -m pip install -c $Constraints -r (Join-Path $Root 'requirements.txt')

$RequirementProfiles = switch ($Profile) {
    'qa'       { @('qa') }
    'fonts'    { @('fonts') }
    'ocr'      { @('fonts','ocr') }
    # Local model profiles are intentionally excluded. OCR is explicit-only.
    'all'      { @('qa','fonts') }
    default    { @() }
}
foreach ($Name in $RequirementProfiles | Select-Object -Unique) {
    & $Python -m pip install -c $Constraints -r (Join-Path $Root "requirements\$Name.txt")
}

if ($Profile -eq 'ocr') {
    $Tessdata = Join-Path $Root '.tools\tessdata'
    New-Item -ItemType Directory -Path $Tessdata -Force | Out-Null
    $ArabicModel = Join-Path $Tessdata 'ara.traineddata'
    if (-not (Test-Path -LiteralPath $ArabicModel)) {
        Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/ara.traineddata' -OutFile $ArabicModel
    }
}

if ($InstallApps) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'winget is required for -InstallApps on Windows.'
    }
    if ($Profile -in @('core','qa','all')) {
        $BinDir = Join-Path $Root '.tools\bin'
        New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
        $SevenZip = Join-Path $BinDir '7zr.exe'
        if (-not (Test-Path -LiteralPath $SevenZip)) {
            $Release = Invoke-RestMethod -Uri 'https://api.github.com/repos/ip7z/7zip/releases/latest'
            $Asset = $Release.assets | Where-Object name -eq '7zr.exe' | Select-Object -First 1
            if (-not $Asset) { throw 'The latest 7-Zip release has no 7zr.exe asset.' }
            Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $SevenZip
            if ($Asset.digest -like 'sha256:*') {
                $Expected = $Asset.digest.Substring(7).ToUpperInvariant()
                $Actual = (Get-FileHash -LiteralPath $SevenZip -Algorithm SHA256).Hash
                if ($Actual -ne $Expected) { throw '7zr.exe checksum mismatch.' }
            }
        }
    }
    if ($Profile -in @('patching','all')) {
        $BinDir = Join-Path $Root '.tools\bin'
        $Downloads = Join-Path $Root '.tools\downloads'
        $Extracted = Join-Path $Downloads 'xdelta3'
        New-Item -ItemType Directory -Path $BinDir,$Downloads,$Extracted -Force | Out-Null
        $Xdelta = Join-Path $BinDir 'xdelta3.exe'
        if (-not (Test-Path -LiteralPath $Xdelta)) {
            $Release = Invoke-RestMethod -Uri 'https://api.github.com/repos/jmacd/xdelta/releases/latest'
            $Asset = $Release.assets | Where-Object name -like '*windows-x86_64.zip' | Select-Object -First 1
            if (-not $Asset) { throw 'The latest Xdelta release has no Windows x64 asset.' }
            $Archive = Join-Path $Downloads $Asset.name
            Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $Archive
            if ($Asset.digest -like 'sha256:*') {
                $Expected = $Asset.digest.Substring(7).ToUpperInvariant()
                $Actual = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
                if ($Actual -ne $Expected) { throw 'Xdelta archive checksum mismatch.' }
            }
            Expand-Archive -LiteralPath $Archive -DestinationPath $Extracted -Force
            $Found = Get-ChildItem -LiteralPath $Extracted -Filter 'xdelta3.exe' -File -Recurse | Select-Object -First 1
            if (-not $Found) { throw 'xdelta3.exe was not found in the downloaded archive.' }
            Copy-Item -LiteralPath $Found.FullName -Destination $Xdelta
        }
    }
    $AppIds = switch ($Profile) {
        'core'  { @() }
        'qa'    { @() }
        'cat'   { @('OmegaT.OmegaT') }
        'media' { @('ImageMagick.ImageMagick.Q16') }
        'ocr'   { @('ImageMagick.ImageMagick.Q16','tesseract-ocr.tesseract') }
        # Do not install Tesseract through all; local OCR requires explicit authorization.
        'all'   { @('OmegaT.OmegaT','ImageMagick.ImageMagick.Q16') }
        default { @() }
    }
    foreach ($Id in $AppIds | Select-Object -Unique) {
        winget install --id $Id --exact --silent --accept-source-agreements --accept-package-agreements --disable-interactivity
        if ($LASTEXITCODE -notin 0, -1978335189) { throw "winget failed for $Id with exit code $LASTEXITCODE" }
    }
}

& $Python (Join-Path $PSScriptRoot 'tool_doctor.py') --profile $Profile --json (Join-Path $Root 'reports\TOOL_STATUS.json')
Write-Output "Isolated Python environment: $Venv"
