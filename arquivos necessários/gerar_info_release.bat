@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "ZIP_FILE=%~1"
set "APP_VERSION=%~2"
set "NOTES_FILE=%~3"
set "SRC_DIR=%~4"
set "PLATFORM=%~5"

if "%SRC_DIR%"=="" set "SRC_DIR=%~dp0..\GitHub"
if "%ZIP_FILE%"=="" set "ZIP_FILE=%~dp0..\ZIP final\Windows\CUMA_windows.zip"
if "%APP_VERSION%"=="" set "APP_VERSION=1.100.29"
if "%NOTES_FILE%"=="" set "NOTES_FILE=NOTAS_RELEASE.md"
if "%PLATFORM%"=="" set "PLATFORM=windows"

if not exist "%SRC_DIR%\cuma.py" (
  echo [ERRO] Pasta GitHub invalida: %SRC_DIR%
  exit /b 1
)

cd /d "%SRC_DIR%"

if not exist "%ZIP_FILE%" (
  echo [ERRO] Pacote nao encontrado: %ZIP_FILE%
  exit /b 1
)

for %%A in ("%ZIP_FILE%") do set "ZIP_SIZE=%%~zA"
for /f "usebackq delims=" %%H in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-FileHash -Path '%ZIP_FILE%' -Algorithm SHA256).Hash.ToUpper()"`) do set "ZIP_SHA256=%%H"

echo.
echo ================= INFORMACOES DA RELEASE =================
echo Versao:     %APP_VERSION%
echo Plataforma: %PLATFORM%
echo Arquivo:    %ZIP_FILE%
echo Tamanho:    %ZIP_SIZE% bytes
echo SHA256:     %ZIP_SHA256%
echo ==========================================================
echo.

(
  echo CUMA %APP_VERSION% - informacoes para GitHub
  echo Plataforma: %PLATFORM%
  echo Arquivo: %ZIP_FILE%
  echo Tamanho: %ZIP_SIZE% bytes
  echo SHA256: %ZIP_SHA256%
) > "%~dp0INFORMACOES_RELEASE_%PLATFORM%.txt"

python scripts\preparar_manifesto_release.py soldieg CUMA %APP_VERSION% "%ZIP_FILE%" Stable "%NOTES_FILE%" %PLATFORM%
if errorlevel 1 echo [AVISO] O manifesto stable.json nao foi atualizado.

endlocal
