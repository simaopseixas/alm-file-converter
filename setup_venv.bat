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
echo Creating Python 3.10 environment
echo =====================================

uv venv --python 3.10

echo.
echo =====================================
echo Installing dependencies
echo =====================================

uv pip install --python .venv\Scripts\python.exe -r requirements.txt

echo.
echo Environment ready.
pause