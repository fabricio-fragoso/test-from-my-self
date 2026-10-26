@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto dependencias

py -3 -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv .venv
    if errorlevel 1 goto erro
    goto dependencias
)

python -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 goto sem_python
python -m venv .venv
if errorlevel 1 goto erro

:dependencias
".venv\Scripts\python.exe" -c "import pypdf; assert pypdf.__version__ == '6.10.0'" >nul 2>&1
if not errorlevel 1 goto abrir
echo Instalando dependencia. Aguarde... E necessario acesso a internet.
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto erro

:abrir
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto erro
exit /b 0

:sem_python
echo Instale Python 3.10 ou superior em https://www.python.org/downloads/windows/
echo Mantenha Tcl/Tk habilitado e marque Add Python to PATH no instalador.
echo Depois, abra este arquivo novamente.
pause
exit /b 1

:erro
echo.
echo Nao foi possivel abrir o aplicativo. Confira a mensagem acima.
echo Se precisar de ajuda, envie a mensagem de erro.
pause
exit /b 1
