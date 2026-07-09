# Saberr — Windows Nuitka build orchestrator.
# Author: Claude

$ErrorActionPreference = "Stop"

$DEFAULT_UI_PROJECT_PATH = ""
$DEFAULT_PYTHON_PATH     = ""
$DEFAULT_MARIADB_PATH    = ""

$JOBS                    = 12
$OUTPUT_DIR              = "build"

$PYTHON_VERSION          = "3.13.8"  # keep major.minor.patch format
$NPM_VERSION             = "11.12.1"  # keep major.minor.patch format
$NUITKA_VERSION          = "4.1.3"  # keep major.minor.patch format
$PIPLICENSES_VERSION     = "4.5.1"  # build-only tool; generates THIRD-PARTY-NOTICES.txt

$MARIADB_REQUIRED_FILES  = @("mariadbd.exe", "mysqld.exe", "mariadb-install-db.exe", "server.dll")

# ---- helpers ------------------------------------------------------------------------------
function Get-SemVer {
    param([string]$Text)
    $m = [regex]::Match($Text, '(\d+)\.(\d+)\.(\d+)')
    if (-not $m.Success) { return $null }
    return [version]("{0}.{1}.{2}" -f $m.Groups[1].Value, $m.Groups[2].Value, $m.Groups[3].Value)
}

function Assert-ToolVersion {
    param([string]$Name, [version]$Actual, [string]$RequiredText)
    $required = [version]$RequiredText
    if ($null -eq $Actual) { throw "$Name version could not be determined." }
    if ($Actual -lt $required) { throw "$Name $Actual is older than the required $required." }
    if ($Actual -gt $required) {
        Write-Host "WARNING: $Name $Actual is newer than the expected $required." -ForegroundColor Yellow
        if ((Read-Host "Continue anyway? [y/N]").Trim() -notmatch '^(?i)y(es)?$') {
            throw "Aborted: $Name version mismatch."
        }
    }
}

function Assert-NpmVersion {
    $text = npm --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "npm not found in PATH (required $NPM_VERSION)." }
    Assert-ToolVersion -Name "npm" -Actual (Get-SemVer "$text") -RequiredText $NPM_VERSION
}

# ---- 0. work from the project base ------------
$ScriptsBase = Split-Path -Parent $PSScriptRoot
$ProjectBase = Split-Path -Parent $ScriptsBase
Set-Location $ProjectBase
Write-Host "Project base: $ProjectBase`n" -ForegroundColor Cyan

# ---- 1a. UI choice ----------------------------
$uiDefaultLabel = if ($DEFAULT_UI_PROJECT_PATH) { " (default, $DEFAULT_UI_PROJECT_PATH)" } else { "" }
Write-Host "UI build (options 1 and 2 require npm in PATH with version $NPM_VERSION):"
Write-Host "  1. Provide build path"
Write-Host "  2. Provide project path for a fresh build$uiDefaultLabel"
Write-Host "  3. No action"
$uiChoice = (Read-Host "Select").Trim()

$copyUi        = $true
$uiBuildPath   = $null
$uiProjectPath = $null
switch ($uiChoice) {
    "" {
        if (-not $DEFAULT_UI_PROJECT_PATH) { throw "A selection is required (no default UI project path configured)." }
        Assert-NpmVersion
        $uiProjectPath = $DEFAULT_UI_PROJECT_PATH
    }
    "1" {
        $uiBuildPath = (Read-Host "Build path").Trim('"').Trim()
        if (-not (Test-Path $uiBuildPath)) { throw "Build path not found: $uiBuildPath" }
    }
    "2" {
        Assert-NpmVersion
        $uiProjectPath = (Read-Host "UI project path").Trim('"').Trim()
    }
    "3" {
        $copyUi = $false
        Write-Host "  -> skipping UI build/copy action" -ForegroundColor DarkGray
    }
    default { throw "Invalid selection: '$uiChoice'" }
}
if ($uiProjectPath -and -not (Test-Path $uiProjectPath)) { throw "UI project path not found: $uiProjectPath" }

# ---- 1b. Python --------------------------------------------
$pyDefaultLabel = if ($DEFAULT_PYTHON_PATH) { " (default, $DEFAULT_PYTHON_PATH)" } else { "" }
Write-Host "`nPython path (required version: $PYTHON_VERSION):"
Write-Host "  1. From PATH (python)"
Write-Host "  2. Custom$pyDefaultLabel"
$pyChoice = (Read-Host "Select").Trim()

switch ($pyChoice) {
    "" {
        if (-not $DEFAULT_PYTHON_PATH) { throw "A selection is required (no default Python path configured)." }
        $basePython = $DEFAULT_PYTHON_PATH
    }
    "1" {
        $basePython = "python"
    }
    "2" {
        $p = (Read-Host "Python directory or executable path").Trim('"').Trim()
        if ($p -notmatch '(?i)python\.exe$') { $p = Join-Path $p "python.exe" }
        $basePython = $p
    }
    default { throw "Invalid selection: '$pyChoice'" }
}
if ($basePython -ne "python" -and -not (Test-Path $basePython)) {
    throw "Python executable not found: $basePython"
}
Write-Host "  -> base python: $basePython" -ForegroundColor DarkGray
$pyVer = Get-SemVer ((& $basePython --version 2>&1) | Out-String)
Assert-ToolVersion -Name "Python" -Actual $pyVer -RequiredText $PYTHON_VERSION

# ---- 1c. MariaDB source ----------------------------
$mdbDefaultLabel = if ($DEFAULT_MARIADB_PATH) { " (default, $DEFAULT_MARIADB_PATH)" } else { "" }
Write-Host "`nMariaDB to bundle (option 1 expects directory with a 'bin' dir inside it containing: $($MARIADB_REQUIRED_FILES -join ', ')):"
Write-Host "  1. Provide source directory$mdbDefaultLabel"
Write-Host "  2. No action"
$mdbChoice = (Read-Host "Select").Trim()

$copyMariadb   = $true
$mariadbSource = $null
switch ($mdbChoice) {
    "" {
        if (-not $DEFAULT_MARIADB_PATH) { throw "A selection is required (no default MariaDB path configured)." }
        $mariadbSource = $DEFAULT_MARIADB_PATH
    }
    "1" {
        $mariadbSource = (Read-Host "MariaDB source directory").Trim('"').Trim()
        if (-not $mariadbSource) {
            if (-not $DEFAULT_MARIADB_PATH) { throw "A MariaDB source directory is required." }
            $mariadbSource = $DEFAULT_MARIADB_PATH
        }
    }
    "2" {
        $copyMariadb = $false
        Write-Host "  -> skipping MariaDB bundling" -ForegroundColor DarkGray
    }
    default { throw "Invalid selection: '$mdbChoice'" }
}
if ($copyMariadb) {
    if (-not (Test-Path $mariadbSource)) { throw "MariaDB source not found: $mariadbSource" }
    $mariadbSourceBin = Join-Path $mariadbSource "bin"
    foreach ($f in $MARIADB_REQUIRED_FILES) {
        if (-not (Test-Path (Join-Path $mariadbSourceBin $f))) {
            throw "MariaDB source is missing required file: bin\$f (looked in $mariadbSource)"
        }
    }
    Write-Host "  -> mariadb source: $mariadbSource" -ForegroundColor DarkGray
}

# ---- 2-6. throwaway venv -> install deps -> Nuitka -> copy web + mariadb ----
$distDir     = Join-Path $OUTPUT_DIR "main.dist"   # the Nuitka standalone dist (= app dir)
$webDest     = Join-Path $distDir "web"            # WEB_DIR=web resolves relative to the exe
$mariadbDest = Join-Path $OUTPUT_DIR "mariadb"     # sibling of main.dist, per tray.py (_ROOT_DIR\mariadb)

$venvDir = Join-Path $env:TEMP ("nuitka-build-venv-" + [guid]::NewGuid().ToString("N"))
try {
    Write-Host "`nCreating temp venv: $venvDir" -ForegroundColor Cyan
    & $basePython -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }

    $venvPython = Join-Path $venvDir "Scripts\python.exe"
    Write-Host "Installing requirements + nuitka..." -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
    & $venvPython -m pip install -U -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "requirements install failed" }

    # Snapshot the runtime dependency set NOW, before build-only tools (nuitka, pip-licenses) are
    # added — these are exactly the packages Nuitka bundles, so exactly the ones needing a notice.
    Write-Host "Capturing runtime dependency set..." -ForegroundColor Cyan
    $runtimePkgs = @()
    foreach ($line in (& $venvPython -m pip freeze)) {
        $name = [regex]::Match($line, '^[A-Za-z0-9._-]+').Value
        if ($name) { $runtimePkgs += $name }
    }
    if (-not $runtimePkgs) { throw "could not capture runtime dependency list from pip freeze" }

    & $venvPython -m pip install nuitka==$NUITKA_VERSION
    if ($LASTEXITCODE -ne 0) { throw "nuitka install failed" }
    & $venvPython -m pip install pip-licenses==$PIPLICENSES_VERSION
    if ($LASTEXITCODE -ne 0) { throw "pip-licenses install failed" }

    # ---- THIRD-PARTY-NOTICES.txt: full license text for every bundled runtime dependency ----
    Write-Host "Generating THIRD-PARTY-NOTICES.txt..." -ForegroundColor Cyan
    $noticesPath = Join-Path $ProjectBase "THIRD-PARTY-NOTICES.txt"
    $noticesHeader = @"
Saberr bundles the third-party Python packages listed below. Each is distributed under its
own license, reproduced in full. This file is generated at build time by pip-licenses.

============================================================================

"@
    Set-Content -Path $noticesPath -Value $noticesHeader -Encoding UTF8
    $plArgs = @('--with-license-file', '--no-license-path', '--format=plain-vertical', '--packages') + $runtimePkgs
    (& (Join-Path $venvDir "Scripts\pip-licenses.exe") @plArgs) | Add-Content -Path $noticesPath -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw "pip-licenses generation failed" }

    # build_info.py
    $buildNumber = [int64]((Get-Date).ToUniversalTime().ToString("yyyyMMddHHmm"))
    $buildInfo = @"
CONTEXT = "windows"
BUILD_NUMBER = $buildNumber
"@
    Write-Host "`nWriting build_info.py (build $buildNumber)..." -ForegroundColor Cyan
    Set-Content -Path (Join-Path $ProjectBase "build_info.py") -Value $buildInfo -Encoding UTF8 -NoNewline

    # Nuitka build
    Write-Host "`nRunning Nuitka..." -ForegroundColor Cyan
    $appVerRaw  = ([regex]::Match((Get-Content ".app-version" -Raw), 'app-ver=([\d.]+)')).Groups[1].Value
    $verParts   = @($appVerRaw -split '\.') + @('0', '0', '0', '0')
    $appVersion = (($verParts[0..3] | ForEach-Object { [int]$_ }) -join '.')
    $nuitkaArgs = @(
        "-m", "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--windows-console-mode=disable",
        "--output-filename=Saberr.exe",
        "--windows-icon-from-ico=assets/logo.ico",
        "--company-name=Saberr",
        "--product-name=Saberr",
        "--file-description=Saberr",
        "--product-version=$appVersion",
        "--file-version=$appVersion",
        "--output-dir=$OUTPUT_DIR",
        "--report=$OUTPUT_DIR/compilation-report.xml",
        "--nofollow-import-to=tests",
        "--include-package=uvicorn",
        "--include-package=asyncmy",
        "--include-package=aiomysql",
        "--include-package=pymysql",
        "--include-package=bcrypt",
        "--include-data-dir=assets=assets",
        "--include-data-dir=data.default=data.default",
        "--include-data-dir=scripts/sql=scripts/sql",
        "--include-data-files=scripts/remote/*.py=scripts/remote/",
        "--include-data-files=.app-version=.app-version",
        "--include-data-files=LICENSE=LICENSE",
        "--include-data-files=DISCLAIMER.md=DISCLAIMER.md",
        "--include-data-files=THIRD-PARTY-NOTICES.txt=THIRD-PARTY-NOTICES.txt",
        "--jobs=$JOBS",
        "main.py"
    )
    & $venvPython @nuitkaArgs
    if ($LASTEXITCODE -ne 0) { throw "Nuitka build failed" }

    # ---- 5. UI build + copy ----
    if ($copyUi) {
        if ($uiProjectPath) {
            Write-Host "`nBuilding UI in $uiProjectPath ..." -ForegroundColor Cyan
            Push-Location $uiProjectPath
            npm run build-be
            if ($LASTEXITCODE -ne 0) { Pop-Location; throw "npm run build-be failed in $uiProjectPath" }
            Pop-Location
            $uiBuildPath = Join-Path $uiProjectPath "build_be"
        }
        if (-not (Test-Path $uiBuildPath)) { throw "UI build path not found: $uiBuildPath" }
        Write-Host "Copying UI into $webDest ..." -ForegroundColor Cyan
        New-Item -ItemType Directory -Force $webDest | Out-Null
        Get-ChildItem -Force $webDest | Remove-Item -Recurse -Force
        Copy-Item -Path (Join-Path $uiBuildPath "*") -Destination $webDest -Recurse -Force
    }

    # ---- 6. copy MariaDB next to the dist ----
    if ($copyMariadb) {
        Write-Host "`nCopying MariaDB into $mariadbDest ..." -ForegroundColor Cyan
        New-Item -ItemType Directory -Force $mariadbDest | Out-Null
        Get-ChildItem -Force $mariadbDest | Remove-Item -Recurse -Force
        Copy-Item -Path (Join-Path $mariadbSource "*") -Destination $mariadbDest -Recurse -Force
        $myIni = @"
[mariadbd]
innodb_log_file_size=16M
innodb_buffer_pool_size=32M
innodb_undo_tablespaces=0
"@
        Set-Content -Path (Join-Path $mariadbDest "my.ini") -Value $myIni -Encoding UTF8
    }

    Write-Host "`nDone." -ForegroundColor Green
    Write-Host "  dist:    $ProjectBase\$distDir" -ForegroundColor Green
    if ($copyMariadb) { Write-Host "  mariadb: $ProjectBase\$mariadbDest" -ForegroundColor Green }
}
finally {
    $buildInfoPath = Join-Path $ProjectBase "build_info.py"
    if (Test-Path $buildInfoPath) {
        Write-Host "Removing build_info.py..." -ForegroundColor DarkGray
        Remove-Item -Force $buildInfoPath -ErrorAction SilentlyContinue
    }
    $noticesPath = Join-Path $ProjectBase "THIRD-PARTY-NOTICES.txt"
    if (Test-Path $noticesPath) {
        Write-Host "Removing THIRD-PARTY-NOTICES.txt..." -ForegroundColor DarkGray
        Remove-Item -Force $noticesPath -ErrorAction SilentlyContinue
    }
    if (Test-Path $venvDir) {
        Write-Host "Cleaning up temp venv..." -ForegroundColor DarkGray
        Remove-Item -Recurse -Force $venvDir -ErrorAction SilentlyContinue
    }
}
