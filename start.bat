@echo off
setlocal enabledelayedexpansion

:: SIKER AT VI ER I DEN RIGTIGE MAPPE (Vigtigt for OneDrive)
cd /d "%~dp0"

echo ==========================================
echo    OA - OpgaveAgenten
echo ==========================================
echo [INFO] Starter applikationen...
echo.

:: 1. Tjek om Python er installeret
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [FEJL] Python er ikke installeret. Installer Python og proev igen.
        pause
        exit /b
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)
echo [OK] Python fundet

:: 2. Tjek for .env fil
if not exist ".env" (
    echo [INFO] Opretter .env fil...
    echo # AI Konfiguration > ".env"
    echo GOOGLE_API_KEY= >> ".env"
    echo OPENAI_API_KEY= >> ".env"
)

:: 3. Tjek for virtuelt miljo (venv)
if not exist "venv\" (
    echo [INFO] Opretter virtuelt miljø...
    %PYTHON_CMD% -m venv venv
)

:: 4. Aktiver venv
call "%~dp0venv\Scripts\activate"

:: 5. Installer/opdater pakker
echo [INFO] Installerer pakker...
python -m pip install -r requirements.txt --quiet

:: 6. Start applikation og åbn browser automatisk
echo [INFO] Starter OpgaveAgenten...
echo [INFO] Browseren åbnes automatisk om et øjeblik...
echo.
start "" http://localhost:8501
python -m streamlit run app.py --server.headless true

:: Hvis Streamlit lukker, hold vinduet åbent
echo.
echo [INFO] Applikationen er stoppet.
pause
