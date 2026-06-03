@echo off
title Bot Cripto — Iniciando...
color 0A

echo.
echo  ================================================
echo    BOT DE TRADING ALGORITMICO - BINANCE TESTNET
echo  ================================================
echo.

:: ── Verificar Python ──────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no esta instalado o no esta en el PATH.
    echo  Instala Python 3.8+ desde https://python.org
    pause
    exit /b 1
)

:: ── Ir al directorio del script ───────────────────────────────────
cd /d "%~dp0"

:: ── Verificar dependencias ────────────────────────────────────────
echo  Verificando dependencias...
python -c "import flask, binance, pandas, numpy, sklearn, joblib" >nul 2>&1
if errorlevel 1 (
    echo  Instalando dependencias faltantes...
    pip install flask binance-connector pandas numpy scikit-learn joblib --quiet
    if errorlevel 1 (
        echo  [ERROR] No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
)
echo  OK - Dependencias listas.

:: ── Verificar archivo de claves ───────────────────────────────────
if not exist "api key.txt" (
    echo.
    echo  [AVISO] No se encontro el archivo "api key.txt"
    echo  Crea el archivo con el siguiente formato:
    echo    API Key: tu_api_key_aqui
    echo    Secret Key: tu_secret_key_aqui
    echo.
    echo  Obtene tus claves en https://testnet.binance.vision/
    echo.
    pause
    exit /b 1
)
echo  OK - Credenciales encontradas.

:: ── Verificar modelo ML ───────────────────────────────────────────
if not exist "modelo_oraculo_rf.pkl" (
    echo.
    echo  Modelo ML no encontrado. Entrenando...
    python entrenar_oraculo_ml.py
    echo  Modelo listo.
    echo.
)

echo.
echo  Iniciando bot y dashboard...
echo  Dashboard disponible en: http://localhost:9090
echo.
echo  Presiona Ctrl+C para detener.
echo  ================================================
echo.

:: ── Abrir el navegador tras 4 segundos ────────────────────────────
start "" /b cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:9090"

:: ── Lanzar el bot (bloquea esta ventana hasta Ctrl+C) ────────────
python main_bot_live.py

echo.
echo  Bot detenido.
pause
