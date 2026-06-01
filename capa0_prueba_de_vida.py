#!/usr/bin/env python3
"""
Capa 0: Prueba de Vida
----------------------
Conecta a Binance Testnet, obtiene y muestra el saldo de la cuenta.
Lee las claves automáticamente desde 'api key.txt' si existe.
"""

import os
import re
import logging
from binance.spot import Spot as Client

# ─── CONFIGURACIÓN ────────────────────────────────────────────────
# Si querés hardcodear tus claves temporalmente, reemplazalas acá:
MI_API_KEY = "TU_CLAVE_ACA"
MI_SECRET_KEY = "TU_CLAVE_ACA"

# Endpoint oficial de la Testnet de Binance
TESTNET_BASE_URL = "https://testnet.binance.vision"

# Archivo donde están guardadas las claves
API_KEY_FILE = "api key.txt"


def leer_claves_desde_archivo(ruta: str) -> tuple:
    """
    Lee API Key y Secret Key desde un archivo con formato:
        API Key: <valor>
        Secret Key: <valor>
    Retorna (api_key, secret_key) o (None, None) si falla.
    """
    if not os.path.isfile(ruta):
        print(f"⚠️  No se encontró el archivo '{ruta}'.")
        return None, None

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
    except Exception as e:
        print(f"❌ Error al leer '{ruta}': {e}")
        return None, None

    api_key = None
    secret_key = None

    # Busca "API Key:" seguido de cualquier cosa que no sea un salto de línea
    match_api = re.search(r"API\s*Key:\s*(\S+)", contenido, re.IGNORECASE)
    if match_api:
        api_key = match_api.group(1).strip()

    # Busca "Secret Key:" seguido de cualquier cosa que no sea un salto de línea
    match_secret = re.search(r"Secret\s*Key:\s*(\S+)", contenido, re.IGNORECASE)
    if match_secret:
        secret_key = match_secret.group(1).strip()

    return api_key, secret_key


def obtener_claves() -> tuple:
    """
    Obtiene las claves priorizando:
    1. Variables de entorno BINANCE_API_KEY / BINANCE_SECRET_KEY
    2. Las hardcodeadas en MI_API_KEY / MI_SECRET_KEY (si no son "TU_CLAVE_ACA")
    3. El archivo api key.txt
    """
    # 1. Variables de entorno
    env_api = os.environ.get("BINANCE_API_KEY")
    env_secret = os.environ.get("BINANCE_SECRET_KEY")
    if env_api and env_secret:
        print("🔑 Usando claves desde variables de entorno.")
        return env_api, env_secret

    # 2. Hardcodeadas en el script (si fueron reemplazadas)
    if MI_API_KEY != "TU_CLAVE_ACA" and MI_SECRET_KEY != "TU_CLAVE_ACA":
        print("🔑 Usando claves hardcodeadas en el script.")
        return MI_API_KEY, MI_SECRET_KEY

    # 3. Archivo api key.txt
    api_key, secret_key = leer_claves_desde_archivo(API_KEY_FILE)
    if api_key and secret_key:
        print(f"🔑 Claves leídas desde '{API_KEY_FILE}'.")
        return api_key, secret_key

    print("❌ No se pudo obtener ninguna clave válida.")
    return None, None


def formatear_saldo(balance: float, asset: str) -> str:
    """Formatea el saldo de forma legible."""
    if float(balance) == 0:
        return ""
    return f"  {asset:>10} : {float(balance):<.8f}"


def main():
    print("=" * 60)
    print("  🧪  Capa 0: Prueba de Vida — Binance Testnet")
    print("=" * 60)

    # ─── Obtener claves ──────────────────────────────────────
    api_key, secret_key = obtener_claves()
    if not api_key or not secret_key:
        print("\n💡 Soluciones:")
        print("   1. Editar 'capa0_prueba_de_vida.py' y reemplazar MI_API_KEY / MI_SECRET_KEY")
        print("   2. O crear variable de entorno BINANCE_API_KEY y BINANCE_SECRET_KEY")
        print("   3. O asegurarte de que 'api key.txt' tenga el formato correcto")
        return

    # ─── Conectar a la Testnet ───────────────────────────────
    print(f"\n🔗 Conectando a: {TESTNET_BASE_URL}")
    try:
        cliente = Client(api_key, secret_key, base_url=TESTNET_BASE_URL)
    except Exception as e:
        print(f"❌ Error al crear el cliente Binance: {e}")
        return

    # ─── Obtener info de la cuenta ───────────────────────────
    print("📡 Solicitando información de la cuenta...\n")
    try:
        cuenta = cliente.account()
    except Exception as e:
        print(f"❌ Error al obtener datos de la cuenta: {e}")
        print("   Posibles causas:")
        print("   - API Key o Secret Key incorrectas")
        print("   - Las claves no tienen permiso para la Testnet")
        print("   - Sin conexión a Internet")
        return

    # ─── Mostrar información relevante ───────────────────────
    print("─" * 60)
    print("  📊  ESTADO DE LA CUENTA")
    print("─" * 60)

    can_trade = cuenta.get("canTrade", False)
    can_withdraw = cuenta.get("canWithdraw", False)
    can_deposit = cuenta.get("canDeposit", False)

    print(f"\n  🔓  Permisos:")
    print(f"       Operar (Trade)    : {'✅ Sí' if can_trade else '❌ No'}")
    print(f"       Retirar (Withdraw): {'✅ Sí' if can_withdraw else '❌ No'}")
    print(f"       Depositar (Deposit): {'✅ Sí' if can_deposit else '❌ No'}")

    print(f"\n  💰  BALANCES (solo saldo disponible > 0):")
    balances_con_saldo = [
        b for b in cuenta.get("balances", [])
        if float(b["free"]) > 0
    ]

    if not balances_con_saldo:
        print("       (vacío — no hay fondos disponibles en la cuenta)")
    else:
        print(f"       {'Activo':>10}   {'Disponible':<18}")
        print(f"       {'─'*10}   {'─'*18}")
        for b in balances_con_saldo:
            activo = b["asset"]
            libre = float(b["free"])
            print(f"       {activo:>10}   {libre:<18.8f}")

    # ─── Buscar USDT específicamente ─────────────────────────
    usdt_balance = 0.0
    for b in cuenta.get("balances", []):
        if b["asset"] == "USDT":
            usdt_balance = float(b["free"])
            break

    print("\n" + "═" * 60)
    print(f"  💵  Tu saldo disponible para trading es: {usdt_balance:.2f} USDT")
    print("═" * 60)

    # ─── Resumen final ────────────────────────────────────────
    print("\n" + "─" * 60)
    print("  ✅  Prueba de Vida completada exitosamente.")
    print("  🚀  Listo para la Capa 1.")
    print("=" * 60)


if __name__ == "__main__":
    # Silenciar logs innecesarios de la librería
    logging.getLogger("binance").setLevel(logging.WARNING)
    main()