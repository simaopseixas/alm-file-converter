@echo off
setlocal

title Setup Python Environment

where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

echo.
echo =====================================
echo Installing Python 3.12
echo =====================================

uv python install 3.12
if %ERRORLEVEL% neq 0 (
    echo Failed to install Python 3.12 with uv.
    pause
    exit /b 1
)

echo.
echo =====================================
echo Creating Python 3.12 environment
echo =====================================

uv venv --python 3.12 --managed-python
if %ERRORLEVEL% neq 0 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

echo.
echo =====================================
echo Installing dependencies
echo =====================================

uv pip install --python .venv\Scripts\python.exe -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Environment ready.
pause