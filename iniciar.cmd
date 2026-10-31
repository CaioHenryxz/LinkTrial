@echo off
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
 echo Instale Node.js 24 ou superior e execute novamente.
 pause
 exit /b 1
)
echo Abra http://127.0.0.1:4175 no navegador.
echo Mantenha esta janela aberta durante a demonstracao.
node server.mjs
pause
