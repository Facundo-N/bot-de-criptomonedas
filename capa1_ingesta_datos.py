#!/usr/bin/env python3
"""
Capa 1: Ingesta de Datos
-------------------------
Descarga velas (klines) históricas de BTCUSDT desde Binance Testnet.
Intervalo: 1 hora. Rango: últimos 3 días.
"""

import os
import re
import logging
import pandas as pd
from datetime import datetime, timedelta
from binance.spot import Spot as Client

# ─── CONFIGURACIÓN ────────────────────────────────────────────────
MI_API_KEY = "TU_CLAVE_ACA"
MI_SECRET_KEY = "TU_CLAVE_ACA"
TESTNET_BASE_URL = "https://testnet.binance.vision"
API_KEY_FILE = "api key.txt"

# Parámetros de la descarga
SIMBOLO = "BTCUSDT"           # Par a descargar
INTERVALO = "1h"              # Intervalo de cada vela: 1h = 1 hora
DIAS_ATRAS = 3                # Cuántos días hacia atrás bajar


def leer_claves_desde_archivo(ruta: str) -> tuple:
    if not os.path.isfile(ruta):
        return None, None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
    except Exception:
        return None, None
    api_key = secret_key = None
    match_api = re.search(r"API\s*Key:\s*(\S+)", contenido, re.IGNORECASE)
    if match_api:
        api_key = match_api.group(1).strip()
    match_secret = re.search(r"Secret\s*Key:\s*(\S+)", contenido, re.IGNORECASE)
    if match_secret:
        secret_key = match_secret.group(1).strip()
    return api_key, secret_key


def obtener_claves() -> tuple:
    env_api = os.environ.get("BINANCE_API_KEY")
    env_secret = os.environ.get("BINANCE_SECRET_KEY")
    if env_api and env_secret:
        return env_api, env_secret
    if MI_API_KEY != "TU_CLAVE_ACA" and MI_SECRET_KEY != "TU_CLAVE_ACA":
        return MI_API_KEY, MI_SECRET_KEY
    return leer_claves_desde_archivo(API_KEY_FILE)


def main():
    print("=" * 60)
    print("  📥  Capa 1: Ingesta de Datos — BTCUSDT 1h")
    print("=" * 60)

    # ─── Obtener claves ──────────────────────────────────────
    api_key, secret_key = obtener_claves()
    if not api_key or not secret_key:
        print("❌ No se encontraron las claves de API.")
        return

    # ─── Conectar a la Testnet ───────────────────────────────
    print(f"\n🔗 Conectando a: {TESTNET_BASE_URL}")
    try:
        cliente = Client(api_key, secret_key, base_url=TESTNET_BASE_URL)
    except Exception as e:
        print(f"❌ Error al crear el cliente Binance: {e}")
        return

    # ─── Calcular fechas ─────────────────────────────────────
    fin = datetime.now()
    inicio = fin - timedelta(days=DIAS_ATRAS)

    # Convertimos a milisegundos (timestamp que entiende Binance)
    inicio_ms = int(inicio.timestamp() * 1000)
    fin_ms   = int(fin.timestamp() * 1000)

    print(f"📅  Rango: {inicio.strftime('%Y-%m-%d %H:%M')} → {fin.strftime('%Y-%m-%d %H:%M')}")
    print(f"⏰  Intervalo: {INTERVALO}")
    print(f"📊  Símbolo: {SIMBOLO}")

    # ─── Descargar klines ────────────────────────────────────
    print(f"\n📡  Descargando datos...")
    try:
        # client.klines() recibe:
        #   symbol     = "BTCUSDT"         → par a consultar
        #   interval   = "1h"              → tamaño de cada vela
        #               Valores comunes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M
        #   startTime  = int (ms)          → timestamp UNIX en milisegundos (inicio del rango)
        #   endTime    = int (ms)          → timestamp UNIX en milisegundos (fin del rango)
        #   limit      = int               → máximo de velas a devolver por llamada (default 500, máx 1000)
        klines = cliente.klines(
            symbol=SIMBOLO,
            interval=INTERVALO,
            startTime=inicio_ms,
            endTime=fin_ms,
            limit=1000
        )
    except Exception as e:
        print(f"❌ Error al descargar klines: {e}")
        return

    print(f"✅  Descargadas {len(klines)} velas.\n")

    # ─── Armar DataFrame ─────────────────────────────────────
    # Cada vela (klines[t]) es una lista con 12 valores:
    #   [0] openTime         → timestamp de apertura (ms)
    #   [1] open             → precio de apertura
    #   [2] high             → precio máximo
    #   [3] low              → precio mínimo
    #   [4] close            → precio de cierre
    #   [5] volume           → volumen de la vela
    #   [6] closeTime        → timestamp de cierre (ms)
    #   [7] quoteVolume      → volumen en moneda de cotización (USDT)
    #   [8] trades           → cantidad de trades
    #   [9] takerBuyBase     → volumen comprado por takers (base)
    #   [10] takerBuyQuote   → volumen comprado por takers (quote)
    #   [11] ignore           → campo ignorado
    df = pd.DataFrame(klines, columns=[
        "openTime", "open", "high", "low", "close", "volume",
        "closeTime", "quoteVolume", "trades",
        "takerBuyBase", "takerBuyQuote", "ignore"
    ])

    # Convertir columnas a numéricos
    cols_numericas = ["open", "high", "low", "close", "volume", "quoteVolume", "trades"]
    df[cols_numericas] = df[cols_numericas].apply(pd.to_numeric, errors="coerce")

    # Convertir timestamps a datetime legible
    df["openTime"] = pd.to_datetime(df["openTime"], unit="ms")
    df["closeTime"] = pd.to_datetime(df["closeTime"], unit="ms")

    # ─── Quedarnos solo con las columnas relevantes ──────────
    df_clean = df[["openTime", "open", "high", "low", "close", "volume"]].copy()
    df_clean.columns = ["Fecha/Hora", "Apertura", "Máximo", "Mínimo", "Cierre", "Volumen"]

    # ─── Mostrar por terminal ────────────────────────────────
    print("─" * 85)
    print(f"  ÚLTIMAS 5 VELAS DE {SIMBOLO} ({INTERVALO})")
    print("─" * 85)

    # Imprimimos las últimas 5 filas con formato lindo
    ultimas_5 = df_clean.tail(5)
    for _, row in ultimas_5.iterrows():
        print(
            f"  {row['Fecha/Hora'].strftime('%Y-%m-%d %H:%M')}  |  "
            f"O:{row['Apertura']:>10.2f}  "
            f"H:{row['Máximo']:>10.2f}  "
            f"L:{row['Mínimo']:>10.2f}  "
            f"C:{row['Cierre']:>10.2f}  "
            f"Vol:{row['Volumen']:>8.4f}"
        )

    print("─" * 85)

    # ─── Resumen del DataFrame ───────────────────────────────
    print(f"\n📋  Información del DataFrame:")
    print(f"     Registros : {len(df_clean)}")
    print(f"     Desde     : {df_clean['Fecha/Hora'].min()}")
    print(f"     Hasta     : {df_clean['Fecha/Hora'].max()}")
    print(f"     Precio min: {df_clean['Mínimo'].min():.2f} USDT")
    print(f"     Precio max: {df_clean['Máximo'].max():.2f} USDT")
    print(f"     Precio act: {df_clean['Cierre'].iloc[-1]:.2f} USDT")

    print("\n" + "═" * 60)
    print("  ✅  Ingesta de Datos completada.")
    print("  📦  DataFrame listo para análisis.")
    print("=" * 60)


if __name__ == "__main__":
    logging.getLogger("binance").setLevel(logging.WARNING)
    main()