@echo off
echo Instalando dependencias...
pip install -r requirements.txt
pip install pyinstaller

echo Gerando executavel...
pyinstaller --onefile --name "X5-LCU-Agent" --console agent.py

echo.
echo Pronto! Distribuir: dist\X5-LCU-Agent.exe
echo Basta abrir o .exe enquanto o LoL estiver rodando.
pause
