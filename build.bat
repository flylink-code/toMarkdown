@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo ========================================
echo  toMarkdown - Local Windows Build
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv. Ensure Python 3.10+ is installed.
        pause
        exit /b 1
    )
) else (
    .venv\Scripts\python.exe --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] .venv Python is unavailable.
        echo        Delete the .venv folder and run this script again.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat

echo [INFO] Installing dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

for /f "delims=" %%v in ('python -c "from tomarkdown import __version__; print(__version__)"') do set "VERSION=%%v"
if not defined VERSION (
    echo [ERROR] Could not read package version from tomarkdown.__init__
    pause
    exit /b 1
)

echo.
echo [INFO] Building toMarkdown v%VERSION% ...
pyinstaller --noconfirm tomarkdown.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

set "ARCHIVE=dist\toMarkdown-v%VERSION%-windows-x64.zip"
if exist "%ARCHIVE%" del /f /q "%ARCHIVE%"

echo [INFO] Creating release archive...
powershell -NoProfile -Command "Compress-Archive -Path 'dist/toMarkdown/*' -DestinationPath '%ARCHIVE%' -Force"
if errorlevel 1 (
    echo [ERROR] Failed to create zip archive.
    pause
    exit /b 1
)

where makensis >nul 2>&1
if errorlevel 1 (
    echo [WARN] NSIS was not found. Skipping installer build.
) else (
    echo [INFO] Creating NSIS installer...
    makensis /DAPP_VERSION=%VERSION% installer\toMarkdown.nsi
    if errorlevel 1 (
        echo [ERROR] NSIS installer build failed.
        pause
        exit /b 1
    )
)

echo.
echo [OK] Build complete.
echo      Executable: dist\toMarkdown\toMarkdown.exe
echo      Archive:    %ARCHIVE%
if exist "dist\toMarkdown-v%VERSION%-windows-x64-setup.exe" echo      Installer:  dist\toMarkdown-v%VERSION%-windows-x64-setup.exe
echo.
pause
