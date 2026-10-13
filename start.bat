@echo off
setlocal

title FarmBridge AI Launcher

set "ROOT=%~dp0"

echo.
echo ==========================================
echo          FARM BRIDGE AI
echo ==========================================
echo.

if not exist "%ROOT%backend\app.py" (
    echo ERROR: Backend app.py was not found.
    echo Expected: %ROOT%backend\app.py
    pause
    exit /b 1
)

if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
    echo ERROR: Backend Python was not found.
    echo Please check the backend .venv folder.
    pause
    exit /b 1
)

if not exist "%ROOT%frontend\package.json" (
    echo ERROR: Frontend package.json was not found.
    echo Expected: %ROOT%frontend\package.json
    pause
    exit /b 1
)

echo Starting backend...
start "FarmBridge AI Backend" /D "%ROOT%backend" "%ROOT%backend\.venv\Scripts\python.exe" "%ROOT%backend\app.py"

timeout /t 3 /nobreak >nul

echo Starting frontend...
start "FarmBridge AI Frontend" /D "%ROOT%frontend" cmd /k "npm run dev"

echo.
echo Startup commands have been launched.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:5173
echo.
pause