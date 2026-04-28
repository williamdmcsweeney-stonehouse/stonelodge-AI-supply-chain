@echo off
setlocal

set "DIR=%~dp0"
set "LOG=%DIR%streamlit.log"
set "PORT=8502"

echo Starting AI Infra Supply Chain Dashboard on port %PORT%...
echo Log:     %LOG%
echo URL:     http://localhost:%PORT%
echo Backend: %STONEHOUSE_BACKEND%
echo.

cd /d "%DIR%"
python -m streamlit run app.py --server.port %PORT% --server.headless false >> "%LOG%" 2>&1
