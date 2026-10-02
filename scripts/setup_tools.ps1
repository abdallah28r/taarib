[CmdletBinding()]
param(
    [ValidateSet('core','qa','fonts','media','ocr','cat','patching','binary','source','gamemaker','all')]
    [string]$Profile = 'core',
    [switch]$InstallApps,
    [string]$SevenZipTag,
    [string]$XdeltaTag,
    [string]$TessdataSha256,
    [hashtable]$AppVersions = @{}
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
        if ($TessdataSha256 -notmatch '^[0-9a-fA-F]{64}$') { throw 'OCR download requires a verified -TessdataSha256.' }
        $TemporaryModel = "$ArabicModel.download"
        Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/ara.traineddata' -OutFile $TemporaryModel
        if ((Get-FileHash -LiteralPath $TemporaryModel -Algorithm SHA256).Hash -ne $TessdataSha256.ToUpperInvariant()) {
            Remove-Item -LiteralPath $TemporaryModel
            throw 'Arabic OCR model checksum mismatch.'
        }
        Move-Item -LiteralPath $TemporaryModel -Destination $ArabicModel
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
            if (-not $SevenZipTag) { throw '7zr installation requires an exact -SevenZipTag.' }
            $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/ip7z/7zip/releases/tags/$([uri]::EscapeDataString($SevenZipTag))"
            $Asset = $Release.assets | Where-Object name -eq '7zr.exe' | Select-Object -First 1
            if (-not $Asset -or $Asset.digest -notmatch '^sha256:[0-9a-fA-F]{64}$') { throw '7zr release asset requires a published SHA-256 digest.' }
            $TemporarySevenZip = "$SevenZip.download"
            Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $TemporarySevenZip
            $Expected = $Asset.digest.Substring(7).ToUpperInvariant()
            $Actual = (Get-FileHash -LiteralPath $TemporarySevenZip -Algorithm SHA256).Hash
            if ($Actual -ne $Expected) { Remove-Item -LiteralPath $TemporarySevenZip; throw '7zr.exe checksum mismatch.' }
            Move-Item -LiteralPath $TemporarySevenZip -Destination $SevenZip
        }
    }
    if ($Profile -in @('patching','all')) {
        $BinDir = Join-Path $Root '.tools\bin'
        $Downloads = Join-Path $Root '.tools\downloads'
        $Extracted = Join-Path $Downloads 'xdelta3'
        New-Item -ItemType Directory -Path $BinDir,$Downloads,$Extracted -Force | Out-Null
        $Xdelta = Join-Path $BinDir 'xdelta3.exe'
        if (-not (Test-Path -LiteralPath $Xdelta)) {
            if (-not $XdeltaTag) { throw 'Xdelta installation requires an exact -XdeltaTag.' }
            $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/jmacd/xdelta/releases/tags/$([uri]::EscapeDataString($XdeltaTag))"
            $Asset = $Release.assets | Where-Object name -like '*windows-x86_64.zip' | Select-Object -First 1
            if (-not $Asset -or $Asset.digest -notmatch '^sha256:[0-9a-fA-F]{64}$') { throw 'Xdelta release asset requires a published SHA-256 digest.' }
            $Archive = Join-Path $Downloads $Asset.name
            Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $Archive
            $Expected = $Asset.digest.Substring(7).ToUpperInvariant()
            $Actual = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
            if ($Actual -ne $Expected) { Remove-Item -LiteralPath $Archive; throw 'Xdelta archive checksum mismatch.' }
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
        if (-not $AppVersions.ContainsKey($Id)) { throw "winget installation requires an exact version for $Id in -AppVersions" }
        winget install --id $Id --version $AppVersions[$Id] --exact --silent --accept-source-agreements --accept-package-agreements --disable-interactivity
        if ($LASTEXITCODE -notin 0, -1978335189) { throw "winget failed for $Id with exit code $LASTEXITCODE" }
    }
}

& $Python (Join-Path $PSScriptRoot 'tool_doctor.py') --profile $Profile --json (Join-Path $Root 'reports\TOOL_STATUS.json')
Write-Output "Isolated Python environment: $Venv"
