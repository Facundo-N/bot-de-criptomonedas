#!/usr/bin/env python3
"""
demo_bucle_acelerado.py — Demostración acelerada del Megabot Live
================================================================
Bucle continuo que evalúa el mercado cada 15 segundos en lugar de 5 minutos,
permitiendo visualizar las decisiones del oráculo y operaciones en tiempo real.
"""

import os
import re
import logging
import time
from datetime import datetime, timedelta
from binance.spot import Spot as Client

# ─── Capas ────────────────────────────────────────────────────────
from capa2_regimen_detector import detectar_regimen
from capa3_oraculo import consolidar_votos
from capa4_gestor_riesgo import evaluar_riesgo, CAPITAL_TOTAL
from capa5_ejecutor import ejecutar_orden, obtener_precio_actual

# ─── Estrategias ──────────────────────────────────────────────────
from estrategias.estrategia_medias import evaluar as eval_sma
from estrategias.estrategia_ema import evaluar as eval_ema
from estrategias.estrategia_rsi import evaluar as eval_rsi
from estrategias.estrategia_bollinger import evaluar as eval_bollinger
from estrategias.estrategia_adx import evaluar as eval_adx
from estrategias.estrategia_supertrend import evaluar as eval_supertrend

# ─── Config ───────────────────────────────────────────────────────
TESTNET_BASE_URL = "https://testnet.binance.vision"
API_KEY_FILE = "api key.txt"

SIMBOLO = "BTCUSDT"
INTERVALO = "1h"
VELAS_A_DESCARGAR = 100
SEGUNDOS_ENTRE_CICLOS = 15  # Acelerado a 15 segundos para la demostración
MICRO_CANTIDAD = 0.0005     # BTC

POSICION = {
    "tenemos_btc": False,
    "btc_comprados": 0.0,
    "precio_compra": 0.0,
    "usdt_invertido": 0.0,
    "saldo_inicial": CAPITAL_TOTAL,
    "saldo_actual": CAPITAL_TOTAL,
    "pnl_total": 0.0,
    "operaciones_cerradas": [],
    "ciclos_sin_operar": 0,
}

ESTRATEGIAS_ACTIVAS = [
    {"funcion": eval_sma,         "nombre": "SMA Crossover (20/50)",       "categoria": "Trend Following"},
    {"funcion": eval_ema,         "nombre": "EMA Crossover (9/21)",        "categoria": "Trend Following"},
    {"funcion": eval_rsi,         "nombre": "RSI 14 Oversold/Overbought",  "categoria": "Mean Reversion"},
    {"funcion": eval_bollinger,   "nombre": "Bollinger Bands Bounce",      "categoria": "Mean Reversion"},
    {"funcion": eval_adx,         "nombre": "ADX Trend Strength Filter",   "categoria": "Breakout & Momentum"},
    {"funcion": eval_supertrend,  "nombre": "SuperTrend Indicator",        "categoria": "Trend Following"},
]

def leer_claves():
    if not os.path.isfile(API_KEY_FILE):
        return None, None
    with open(API_KEY_FILE, "r") as f:
        c = f.read()
    ak = re.search(r"API\s*Key:\s*(\S+)", c, re.I)
    sk = re.search(r"Secret\s*Key:\s*(\S+)", c, re.I)
    return (ak.group(1).strip() if ak else None,
            sk.group(1).strip() if sk else None)

def klines_a_dataframe(klines):
    import pandas as pd
    df = pd.DataFrame(klines, columns=[
        "openTime","open","high","low","close","volume",
        "closeTime","quoteVolume","trades",
        "takerBuyBase","takerBuyQuote","ignore"
    ])
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["openTime"] = pd.to_datetime(df["openTime"], unit="ms")
    dc = df[["openTime","open","high","low","close","volume"]].copy()
    dc.columns = ["Fecha/Hora","Apertura","Máximo","Mínimo","Cierre","Volumen"]
    return dc

def actualizar_saldo(cliente):
    try:
        ac = cliente.account()
        for b in ac["balances"]:
            if b["asset"] == "USDT":
                POSICION["saldo_actual"] = float(b["free"])
                return float(b["free"])
    except: pass
    return POSICION["saldo_actual"]

def resumen_venta(pnl, precio, cantidad):
    color = "🟢" if pnl >= 0 else "🔴"
    pct = (pnl / POSICION["usdt_invertido"]) * 100 if POSICION["usdt_invertido"] > 0 else 0
    print(f"\n  {color}  VENTA @ {precio:.2f} | {cantidad:.6f} BTC")
    print(f"  {color}  P&L: {pnl:+.2f} USDT ({pct:+.2f}%) | Total acum: {POSICION['pnl_total']:+.2f} USDT")
    print(f"  💰  Saldo: {POSICION['saldo_actual']:.2f} USDT")

def descargar_velas(cliente):
    fin = datetime.now()
    inicio = fin - timedelta(hours=VELAS_A_DESCARGAR + 10)
    return cliente.klines(symbol=SIMBOLO, interval=INTERVALO,
                          startTime=int(inicio.timestamp()*1000),
                          endTime=int(fin.timestamp()*1000),
                          limit=VELAS_A_DESCARGAR)

def main():
    print("=" * 55)
    print("  🧪  DEMO BUCLE ACELERADO — Megabot v4 Live")
    print(f"  🕐  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  ⏱   Bucle rápido: cada {SEGUNDOS_ENTRE_CICLOS}s")
    print("=" * 55)
    print("  Presioná Ctrl+C para detener y ver resumen")
    print("=" * 55)

    ak, sk = leer_claves()
    if not ak or not sk:
        print("❌ Error: No se encontraron claves en 'api key.txt'")
        return

    try:
        cliente = Client(ak, sk, base_url=TESTNET_BASE_URL)
    except Exception as e:
        print(f"❌ Error conectando a Binance: {e}")
        return

    actualizar_saldo(cliente)
    POSICION["saldo_inicial"] = POSICION["saldo_actual"]
    ciclo = 0

    try:
        # Correremos un máximo de 4 ciclos para esta demo automatizada o hasta Ctrl+C
        for _ in range(4):
            ciclo += 1
            POSICION["ciclos_sin_operar"] += 1
            print(f"\n\n{'#'*55}")
            print(f"  🔄  CICLO #{ciclo} — {datetime.now().strftime('%H:%M:%S')}")
            status = "🔴 ABIERTA" if POSICION["tenemos_btc"] else "🟢 VACÍA"
            print(f"  {status} | Saldo: {POSICION['saldo_actual']:.2f} USDT | P&L: {POSICION['pnl_total']:+.2f}")
            print(f"{'#'*55}")

            # 1. Ingesta
            try:
                klines = descargar_velas(cliente)
                df = klines_a_dataframe(klines)
                precio = df["Cierre"].iloc[-1]
                print(f"  📊  BTC: {precio:.2f} USDT")
            except Exception as e:
                print(f"⚠️ Error datos: {e}")
                time.sleep(SEGUNDOS_ENTRE_CICLOS)
                continue

            # 2. Meta-Learner (Detección de régimen)
            regimen_info = detectar_regimen(df)
            regimen = regimen_info["regimen"]
            print(f"  📈  Régimen: {regimen} (ADX: {regimen_info['adx']})")

            # 3. Estrategias
            resultados = []
            for est in ESTRATEGIAS_ACTIVAS:
                if est["categoria"] not in regimen_info["categorias_activas"]:
                    continue
                try:
                    v = est["funcion"](df)
                    v["nombre"] = est["nombre"]
                    v["categoria"] = est["categoria"]
                    resultados.append(v)
                except: pass

            # 4. Oráculo
            decision = consolidar_votos(resultados, regimen=regimen.split()[0])
            pun = decision["puntaje_neto"]
            print(f"  🔮  Oráculo: {decision['accion']} (puntaje: {pun:+.4f})")

            # 5. Ejecutor
            hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if POSICION["tenemos_btc"]:
                # Venta si oráculo lo dice o forzamos en el ciclo siguiente
                if decision["accion"] == "SELL" or POSICION["ciclos_sin_operar"] >= 2:
                    print(f"\n🔴  CERRANDO POSICIÓN...")
                    res = ejecutar_orden(cliente, SIMBOLO, "SELL", POSICION["btc_comprados"])
                    if res["exito"]:
                        ingreso = POSICION["btc_comprados"] * res["precio"]
                        pnl = ingreso - POSICION["usdt_invertido"]
                        POSICION["pnl_total"] += pnl
                        POSICION["saldo_actual"] += pnl
                        POSICION["operaciones_cerradas"].append({
                            "hora": hora,
                            "buy": POSICION["precio_compra"],
                            "sell": res["precio"],
                            "btc": POSICION["btc_comprados"],
                            "pnl": round(pnl, 2)
                        })
                        resumen_venta(pnl, res["precio"], POSICION["btc_comprados"])
                        POSICION["tenemos_btc"] = False
                        POSICION["btc_comprados"] = 0
                        POSICION["precio_compra"] = 0
                        POSICION["usdt_invertido"] = 0
                        POSICION["ciclos_sin_operar"] = 0
                        actualizar_saldo(cliente)
                    else:
                        print(f"❌ Error venta: {res['detalle']}")
            else:
                debe_comprar = False
                razon = ""

                if decision["accion"] == "BUY":
                    debe_comprar = True
                    razon = f"señal ORÁCULO (puntaje: {pun:+.3f})"
                elif POSICION["ciclos_sin_operar"] >= 2:  # Bajar a 2 ciclos para demostración rápida
                    debe_comprar = True
                    razon = "MICRO-TRADE forzado (demo acelerada)"

                if debe_comprar:
                    cantidad = MICRO_CANTIDAD
                    print(f"\n🟢  COMPRA ({razon})")
                    res = ejecutar_orden(cliente, SIMBOLO, "BUY", cantidad)
                    if res["exito"]:
                        POSICION["tenemos_btc"] = True
                        POSICION["btc_comprados"] = cantidad
                        POSICION["precio_compra"] = res["precio"]
                        POSICION["usdt_invertido"] = cantidad * res["precio"]
                        POSICION["ciclos_sin_operar"] = 0
                        actualizar_saldo(cliente)
                        print(f"  💳  Comprado: {cantidad:.6f} BTC @ {res['precio']:.2f} USDT")
                    else:
                        print(f"❌ Error compra: {res['detalle']}")
                else:
                    print(f"  ⏸️  Esperando señal... (ciclos sin operar: {POSICION['ciclos_sin_operar']})")

            # Espera para el siguiente ciclo
            print(f"\n  ⏳  Siguiente ciclo en {SEGUNDOS_ENTRE_CICLOS}s...")
            time.sleep(SEGUNDOS_ENTRE_CICLOS)

    except KeyboardInterrupt:
        pass

    print(f"\n\n{'='*55}")
    print("  📊  RESUMEN FINAL DE LA DEMO")
    print(f"{'='*55}")
    print(f"  Ciclos corridos     : {ciclo}")
    print(f"  Operaciones cerradas: {len(POSICION['operaciones_cerradas'])}")
    print(f"  P&L Acumulado       : {POSICION['pnl_total']:+.4f} USDT")
    print(f"  Saldo Final         : {POSICION['saldo_actual']:.2f} USDT")
    print(f"{'='*55}")

if __name__ == "__main__":
    logging.getLogger("binance").setLevel(logging.WARNING)
    main()
