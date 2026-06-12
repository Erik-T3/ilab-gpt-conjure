@echo off
setlocal

set "BUNDLE_DIR=%~dp0"
set "APP_DIR=%BUNDLE_DIR%app"
set "DATA_DIR=%BUNDLE_DIR%data"
set "PYTHON_BIN=%BUNDLE_DIR%python\python.exe"
set "PORT=8787"
set "URL=http://127.0.0.1:%PORT%/"
set "HEALTH_URL=%URL%api/health"
set "WAIT_ATTEMPTS=30"
set "VERSION_FILE=%BUNDLE_DIR%portable-version.txt"
set "LATEST_RELEASE_URL=https://api.github.com/repos/kadevin/ilab-gpt-conjure/releases/latest"

if not exist "%PYTHON_BIN%" (
  echo Portable Python was not found at %PYTHON_BIN%.
  pause
  exit /b 1
)

if not exist "%APP_DIR%\portable_webui_app.py" (
  echo Portable app files were not found at %APP_DIR%.
  pause
  exit /b 1
)

if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%DATA_DIR%\logs" mkdir "%DATA_DIR%\logs"

set "ILAB_CONJURE_DATA_DIR=%DATA_DIR%"
set "PYTHONPATH=%APP_DIR%;%APP_DIR%\.deps"
set "CERTIFI_CA_BUNDLE=%BUNDLE_DIR%python\Lib\site-packages\certifi\cacert.pem"
if exist "%CERTIFI_CA_BUNDLE%" (
  set "SSL_CERT_FILE=%CERTIFI_CA_BUNDLE%"
  set "REQUESTS_CA_BUNDLE=%CERTIFI_CA_BUNDLE%"
)
set "AUTH_SETTINGS_PATH=%DATA_DIR%\webui-auth-settings.json"
"%PYTHON_BIN%" -m codex_image.webui.startup_auth --settings-path "%AUTH_SETTINGS_PATH%" >nul
set "LOG_FILE=%DATA_DIR%\logs\webui-server.log"

cd /d "%APP_DIR%"

echo Starting iLab GPT Conjure at %URL%
echo Data directory: %DATA_DIR%
echo Writing server log to %LOG_FILE%

call :check_latest_release_notice

call :is_webui_ready
if %ERRORLEVEL% EQU 0 (
  echo WebUI is already running at %URL%
  start "" "%URL%"
  exit /b 0
)

start "iLab GPT Conjure WebUI" /b "%PYTHON_BIN%" -m uvicorn portable_webui_app:app --host 127.0.0.1 --port %PORT% --no-access-log >> "%LOG_FILE%" 2>&1

call :wait_for_webui
if %ERRORLEVEL% EQU 0 (
  start "" "%URL%"
) else (
  echo WebUI did not become ready within 30 seconds. Check %LOG_FILE%.
  pause
  exit /b 1
)

echo WebUI server is running. Press Ctrl+C in this window to stop it.
:keep_server_window_open
timeout /t 3600 /nobreak >nul
goto keep_server_window_open

:check_latest_release_notice
if "%ILAB_SKIP_VERSION_CHECK%"=="1" exit /b 0
if not exist "%VERSION_FILE%" exit /b 0
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $current = (Get-Content -Path $env:VERSION_FILE -TotalCount 1 -ErrorAction Stop).Trim(); if (-not $current) { exit 0 }; $release = Invoke-RestMethod -Uri $env:LATEST_RELEASE_URL -Headers @{ 'User-Agent' = 'ilab-gpt-conjure-portable-launcher' } -TimeoutSec 2 -ErrorAction Stop; $latest = ([string]$release.tag_name).Trim(); function Read-SemVer([string]$value) { if ($value -match '^[vV]?(\d+)\.(\d+)\.(\d+)') { return [version]::new([int]$Matches[1], [int]$Matches[2], [int]$Matches[3]) }; return $null }; $currentVersion = Read-SemVer $current; $latestVersion = Read-SemVer $latest; if ($currentVersion -and $latestVersion -and $latestVersion -gt $currentVersion) { Write-Host ('New version available: v{0}. Close WebUI and run Update WebUI Portable.bat to update.' -f $latestVersion.ToString()) } } catch { }"
exit /b 0

:is_webui_ready
powershell -NoProfile -Command "try { $response = Invoke-WebRequest -UseBasicParsing -Uri '%HEALTH_URL%' -TimeoutSec 1; if ($response.StatusCode -eq 200) { exit 0 }; exit 1 } catch { exit 1 }" >nul 2>nul
exit /b %ERRORLEVEL%

:wait_for_webui
set /a ATTEMPT=0
:wait_for_webui_loop
call :is_webui_ready
if %ERRORLEVEL% EQU 0 exit /b 0
set /a ATTEMPT+=1
if %ATTEMPT% GEQ %WAIT_ATTEMPTS% exit /b 1
timeout /t 1 /nobreak >nul
goto wait_for_webui_loop
