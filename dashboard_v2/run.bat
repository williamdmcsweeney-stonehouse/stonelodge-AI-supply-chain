@echo off
setlocal

set "DIR=%~dp0"
set "ROOT=%DIR%.."
set "LOG=%DIR%streamlit_v2.log"
set "PORT=8503"

echo Starting AI Infra Supply Chain Dashboard v2 on port %PORT%...
echo Log:     %LOG%
echo URL:     http://localhost:%PORT%
echo Backend: %STONEHOUSE_BACKEND%
echo.

cd /d "%ROOT%"
python -m streamlit run dashboard_v2/app.py --server.port %PORT% --server.headless false >> "%LOG%" 2>&1
