#!/usr/bin/env python3
"""
Demo Forzada: Muestra el ciclo COMPRA → ESPERA → VENTA → P&L
usando dinero ficticio de Testnet. No espera señales reales.
"""

import os, re, logging, time
from datetime import datetime
from binance.spot import Spot as Client
from capa3_oraculo import consolidar_votos
from capa4_gestor_riesgo import evaluar_riesgo, CAPITAL_TOTAL
from capa5_ejecutor import ejecutar_orden, obtener_precio_actual
from estrategias.estrategia_medias import evaluar as eval_sma
from estrategias.estrategia_ema import evaluar as eval_ema
from estrategias.estrategia_rsi import evaluar as eval_rsi
from estrategias.estrategia_bollinger import evaluar as eval_bollinger
from estrategias.estrategia_adx import evaluar as eval_adx
from estrategias.estrategia_supertrend import evaluar as eval_supertrend

# Config
MI_API_KEY = "TU_CLAVE_ACA"
MI_SECRET_KEY = "TU_CLAVE_ACA"
TESTNET_BASE_URL = "https://testnet.binance.vision"
API_KEY_FILE = "api key.txt"
SIMBOLO = "BTCUSDT"

def obtener_claves():
    if not os.path.isfile(API_KEY_FILE):
        return None, None
    with open(API_KEY_FILE, "r") as f:
        c = f.read()
    import re
    ak = re.search(r"API\s*Key:\s*(\S+)", c, re.I)
    sk = re.search(r"Secret\s*Key:\s*(\S+)", c, re.I)
    return (ak.group(1).strip() if ak else None,
            sk.group(1).strip() if sk else None)

print("=" * 55)
print("  🧪  DEMO FORZADA — Ciclo completo con P&L")
print("=" * 55)

ak, sk = obtener_claves()
if not ak or not sk:
    print("❌ No hay claves")
    exit()

cliente = Client(ak, sk, base_url=TESTNET_BASE_URL)

# Ver saldo inicial
cuenta = cliente.account()
saldo_inicial = 0
for b in cuenta["balances"]:
    if b["asset"] == "USDT":
        saldo_inicial = float(b["free"])
        break
print(f"\n💰  Saldo inicial en Testnet: {saldo_inicial:.2f} USDT")

# 1. COMPRAR 0.001 BTC (micro-cantidad para demo)
print(f"\n{'─'*55}")
print(f"  📥  PASO 1: COMPRAR 0.001 BTC")
print(f"{'─'*55}")

precio = obtener_precio_actual(cliente, SIMBOLO)
print(f"  Precio BTC actual: {precio:.2f} USDT")

resultado = ejecutar_orden(
    cliente=cliente, simbolo=SIMBOLO,
    accion="BUY", cantidad=0.001
)

if not resultado["exito"]:
    print(f"❌ Error en compra: {resultado['detalle']}")
    exit()

precio_compra = resultado["precio"]
print(f"\n  ✅  COMPRADO: 0.001 BTC @ {precio_compra:.2f} USDT")
print(f"  💰  Inversión: {0.001 * precio_compra:.2f} USDT")

# 2. ESPERAR 5 segundos y ver precio
print(f"\n{'─'*55}")
print(f"  ⏳  PASO 2: ESPERAR 5 SEGUNDOS...")
print(f"{'─'*55}")
time.sleep(5)

precio_actual = obtener_precio_actual(cliente, SIMBOLO)
diff = precio_actual - precio_compra
pct = (diff / precio_compra) * 100
signo = "🟢" if diff >= 0 else "🔴"
print(f"\n  Precio ahora: {precio_actual:.2f} USDT")
print(f"  {signo} Diferencia: {diff:+.2f} USDT ({pct:+.4f}%)")

# 3. VENDER
print(f"\n{'─'*55}")
print(f"  📤  PASO 3: VENDER 0.001 BTC")
print(f"{'─'*55}")

resultado = ejecutar_orden(
    cliente=cliente, simbolo=SIMBOLO,
    accion="SELL", cantidad=0.001
)

if not resultado["exito"]:
    print(f"❌ Error en venta: {resultado['detalle']}")
    exit()

precio_venta = resultado["precio"]

# 4. MOSTRAR P&L
pnl = (precio_venta - precio_compra) * 0.001
pnl_pct = (precio_venta - precio_compra) / precio_compra * 100

print(f"\n{'='*55}")
color = "🟢" if pnl >= 0 else "🔴"
print(f"  {color}  P&L DE LA OPERACIÓN")
print(f"{'='*55}")
print(f"  Compra  : {precio_compra:.2f} USDT")
print(f"  Venta   : {precio_venta:.2f} USDT")
print(f"  Cantidad: 0.001 BTC")
print(f"  ──────────────────────────────────")
print(f"  {color}  GANANCIA : {pnl:+.2f} USDT ({pnl_pct:+.4f}%)")
print(f"{'='*55}")

# Mostrar saldo final
cuenta = cliente.account()
saldo_final = 0
for b in cuenta["balances"]:
    if b["asset"] == "USDT":
        saldo_final = float(b["free"])
        break
print(f"\n💰  Saldo inicial : {saldo_inicial:.2f} USDT")
print(f"💰  Saldo final   : {saldo_final:.2f} USDT")
print(f"📊  Diferencia    : {saldo_final - saldo_inicial:+.2f} USDT")
print(f"\n✅  Demo completada. El pipeline COMPRA→VENTA→P&L funciona.")