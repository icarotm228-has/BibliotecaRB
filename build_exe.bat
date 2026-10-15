@echo off
rem Gera dist\BibliotecaRB.exe (executar com duplo clique ou no Prompt de Comando, na pasta do projeto)
cd /d "%~dp0"
echo === BibliotecaRB: gerando o executavel ===

if not exist venv\Scripts\activate.bat (
    echo Criando o ambiente virtual...
    python -m venv venv || goto erro
)
call venv\Scripts\activate.bat

echo Instalando as dependencias (Flask, SQLAlchemy, Waitress e PyInstaller)...
pip install -r requirements-exe.txt || goto erro

echo Gerando o executavel...
pyinstaller --noconfirm --clean --onefile --noconsole --name BibliotecaRB ^
  --add-data "templates;templates" --add-data "static;static" ^
  --collect-submodules sqlalchemy.dialects.sqlite --hidden-import waitress ^
  app.py || goto erro

echo.
echo Pronto! O executavel esta em: dist\BibliotecaRB.exe
pause
exit /b 0

:erro
echo.
echo ERRO ao gerar o executavel. Leia as mensagens acima.
pause
exit /b 1
