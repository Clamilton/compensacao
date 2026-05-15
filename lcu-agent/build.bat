@echo off
echo Instalando dependencias...
pip install -r requirements.txt
pip install pyinstaller

echo Gerando executavel...
pyinstaller --onefile --name "X5-LCU-Agent" --console agent.py

echo.
echo Pronto! O executavel esta em: dist\X5-LCU-Agent.exe
pause
