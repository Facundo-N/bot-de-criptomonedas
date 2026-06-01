"""
main_bot.py — Orquestador Principal v3 (Árbol Genealógico)
===========================================================
Pipeline completo del Mega-Bot con todas las capas integradas:

  FLUJO DEL ÁRBOL:
  1. CAPA 1 (Ojos)       → Descargar velas de BTCUSDT
  2. CAPA 2 (Meta-Learner)→ Detectar régimen (Tendencia/Rango/Volátil)
  3. CAPA 2 (Cerebros)   → Solo estrategias ACTIVAS según régimen emiten voto
  4. CAPA 3 (Oráculo)    → Consenso ponderado + filtro 75% + pesos dinámicos
  5. CAPA 4 (Freno)      → Evaluar riesgo, calcular posición y stop-loss
  6. CAPA 4.5 (Grid DCA) → Calcular escalera de recuperación si es compra
  7. CAPA 5 (Brazo)      → Ejecutar orden en Testnet

ESTRATEGIAS ACTIVAS: 6 (de 50 registradas)
  - SMA Crossover 20/50     (Trend Following)
  - EMA Crossover 9/21      (Trend Following)
  - RSI 14 Oversold/Ovrbt   (Mean Reversion)
  - Bollinger Bands Bounce  (Mean Reversion)
  - ADX Trend Filter        (Breakout & Momentum)
  - SuperTrend Indicator    (Trend Following)
"""

import os
import re
import logging
import time
from datetime import datetime, timedelta
from binance.spot import Spot as Client

# ─── Importar capas ───────────────────────────────────────────────
from capa2_regimen_detector import detectar_regimen
from capa3_oraculo import consolidar_votos, obtener_estadisticas
from capa4_gestor_riesgo import evaluar_riesgo, CAPITAL_TOTAL
from capa5_ejecutor import ejecutar_orden, obtener_precio_actual
from capa4_5_grid_dca import calcular_grilla, imprimir_tabla

# ─── Importar estrategias ─────────────────────────────────────────
from estrategias.estrategia_medias import evaluar as eval_sma
from estrategias.estrategia_ema import evaluar as eval_ema
from estrategias.estrategia_rsi import evaluar as eval_rsi
from estrategias.estrategia_bollinger import evaluar as eval_bollinger
from estrategias.estrategia_adx import evaluar as eval_adx
from estrategias.estrategia_supertrend import evaluar as eval_supertrend

# ─── CONFIGURACIÓN ────────────────────────────────────────────────
MI_API_KEY = "TU_CLAVE_ACA"
MI_SECRET_KEY = "TU_CLAVE_ACA"
TESTNET_BASE_URL = "https://testnet.binance.vision"
API_KEY_FILE = "api key.txt"

SIMBOLO = "BTCUSDT"
INTERVALO = "1h"
VELAS_A_DESCARGAR = 200  # Suficientes para todos los indicadores


# ─── Catálogo completo de estrategias ─────────────────────────────
# Cada estrategia tiene su función, categoría y nombre.
# El Meta-Learner activa/desactiva por categoría.
ESTRATEGIAS_ACTIVAS = [
    {"funcion": eval_sma,         "nombre": "SMA Crossover (20/50)",       "categoria": "Trend Following"},
    {"funcion": eval_ema,         "nombre": "EMA Crossover (9/21)",        "categoria": "Trend Following"},
    {"funcion": eval_rsi,         "nombre": "RSI 14 Oversold/Overbought",  "categoria": "Mean Reversion"},
    {"funcion": eval_bollinger,   "nombre": "Bollinger Bands Bounce",      "categoria": "Mean Reversion"},
    {"funcion": eval_adx,         "nombre": "ADX Trend Strength Filter",   "categoria": "Breakout & Momentum"},
    {"funcion": eval_supertrend,  "nombre": "SuperTrend Indicator",        "categoria": "Trend Following"},
]


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


def descargar_velas(cliente: Client, simbolo: str, interval: str, limite: int = 200) -> list:
    fin = datetime.now()
    inicio = fin - timedelta(hours=limite + 10)
    inicio_ms = int(inicio.timestamp() * 1000)
    fin_ms = int(fin.timestamp() * 1000)
    print(f"📥  Descargando {limite} velas de {simbolo} ({interval})...")
    klines = cliente.klines(symbol=simbolo, interval=interval,
                            startTime=inicio_ms, endTime=fin_ms, limit=limite)
    print(f"     ✅ {len(klines)} velas recibidas.")
    return klines


def klines_a_dataframe(klines: list) -> "pd.DataFrame":
    import pandas as pd
    df = pd.DataFrame(klines, columns=[
        "openTime", "open", "high", "low", "close", "volume",
        "closeTime", "quoteVolume", "trades",
        "takerBuyBase", "takerBuyQuote", "ignore"
    ])
    cols_num = ["open", "high", "low", "close", "volume"]
    df[cols_num] = df[cols_num].apply(pd.to_numeric, errors="coerce")
    df["openTime"] = pd.to_datetime(df["openTime"], unit="ms")
    df_clean = df[["openTime", "open", "high", "low", "close", "volume"]].copy()
    df_clean.columns = ["Fecha/Hora", "Apertura", "Máximo", "Mínimo", "Cierre", "Volumen"]
    return df_clean


def mostrar_banner(titulo: str):
    print("\n" + "═" * 60)
    print(f"  {titulo}")
    print("═" * 60)


def main():
    print("=" * 60)
    print("  🌳  BOT DE TRADING v3 — Árbol Genealógico Completo")
    print(f"  🕐  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🧠  Estrategias registradas: {len(ESTRATEGIAS_ACTIVAS)}")
    for e in ESTRATEGIAS_ACTIVAS:
        print(f"       • {e['nombre']} ({e['categoria']})")
    print("=" * 60)

    # ─── 0. Obtener claves y conectar ─────────────────────────
    api_key, secret_key = obtener_claves()
    if not api_key or not secret_key:
        print("❌ No se encontraron las claves de API.")
        return

    print(f"\n🔗 Conectando a Testnet: {TESTNET_BASE_URL}")
    try:
        cliente = Client(api_key, secret_key, base_url=TESTNET_BASE_URL)
    except Exception as e:
        print(f"❌ Error al conectar: {e}")
        return

    operaciones_activas = {1: False, 2: False, 3: False}

    # ============================================================
    #  CICLO PRINCIPAL
    # ============================================================
    ciclo = 1
    while True:
        print(f"\n\n{'#' * 60}")
        print(f"  🔄  CICLO #{ciclo}")
        print(f"{'#' * 60}")

        # ─── CAPA 1: OJOS ────────────────────────────────────
        mostrar_banner("📡 CAPA 1: INGESTA DE DATOS")
        klines = descargar_velas(cliente, SIMBOLO, INTERVALO, VELAS_A_DESCARGAR)
        if not klines or len(klines) < 50:
            print("❌ No hay suficientes datos. Reintentando...")
            time.sleep(5)
            ciclo += 1
            if ciclo > 5:
                break
            continue

        df_velas = klines_a_dataframe(klines)
        ultimo_precio = df_velas['Cierre'].iloc[-1]
        print(f"     Rango: {df_velas['Fecha/Hora'].min()} → {df_velas['Fecha/Hora'].max()}")
        print(f"     Último precio: {ultimo_precio:.2f} USDT")

        # ─── CAPA 2: META-LEARNER (Detectar régimen) ─────────
        mostrar_banner("🔍 CAPA 2: META-LEARNER — DETECTOR DE REGÍMENES")

        regimen_info = detectar_regimen(df_velas)
        regimen = regimen_info["regimen"]
        categorias_activas = regimen_info["categorias_activas"]
        categorias_inactivas = regimen_info["categorias_inactivas"]

        print(f"  📊  Régimen detectado: {regimen}")
        print(f"  📈  ADX: {regimen_info['adx']} | Volatilidad Z: {regimen_info['volatilidad_zscore']}")
        print(f"  🟢  Categorías activas  : {', '.join(categorias_activas)}")
        print(f"  🔴  Categorías inactivas: {', '.join(categorias_inactivas) if categorias_inactivas else '(ninguna)'}")
        print(f"  💬  {regimen_info['fundamento']}")

        # ─── CAPA 2: CEREBROS (Solo categorías activas) ──────
        mostrar_banner("🧠 CAPA 2: COMITÉ DE ESTRATEGIAS (ACTIVAS SEGÚN RÉGIMEN)")

        resultados = []
        estrategias_ejecutadas = 0
        estrategias_filtradas = 0

        for est in ESTRATEGIAS_ACTIVAS:
            # Filtro: solo ejecutar si la categoría de esta estrategia está activa
            if est["categoria"] not in categorias_activas:
                estrategias_filtradas += 1
                continue

            try:
                voto = est["funcion"](df_velas)
                voto["nombre"] = est["nombre"]
                voto["categoria"] = est["categoria"]
                resultados.append(voto)

                emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(voto["accion"], "⚪")
                print(f"  {emoji} {est['nombre']:40s} → {voto['accion']:5s} (conf: {voto['confianza']}%)")
                estrategias_ejecutadas += 1
            except Exception as e:
                print(f"  ❌ Error en {est['nombre']}: {e}")

        print(f"\n     📊 {estrategias_ejecutadas} estrategias votaron | {estrategias_filtradas} filtradas por régimen")

        # ─── CAPA 3: ORÁCULO DE CONSENSO ─────────────────────
        mostrar_banner("🔮 CAPA 3: ORÁCULO (CONSENSO 75% + PESOS POR RÉGIMEN)")

        decision = consolidar_votos(resultados, regimen=regimen.split()[0])
        stats = obtener_estadisticas(resultados)

        print(f"\n  📊  VOTACIÓN ({len(resultados)} estrategias activas):")
        print(f"       BUY : {stats.get('votos_buy', 0)} votos")
        print(f"       SELL: {stats.get('votos_sell', 0)} votos")
        print(f"       HOLD: {stats.get('votos_hold', 0)} votos")
        print(f"       Confianza promedio: {stats.get('confianza_promedio', 0)}%")

        emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⏸️"}.get(decision["accion"], "❓")
        print(f"\n  {emoji}  DECISIÓN FINAL: {decision['accion']} (confianza: {decision['confianza']}%)")
        print(f"  📝  {decision['detalle']}")

        # Si el oráculo dice HOLD → no operamos
        if decision["accion"] == "HOLD":
            print("\n⏸️  Oráculo dice HOLD. No se ejecuta ninguna orden.")
            ciclo += 1
            time.sleep(3)
            if ciclo > 3:
                print("\n🏁  Demo completada (3 ciclos sin señal).")
                break
            continue

        # ─── Obtener precio actual ───────────────────────────
        precio_actual = obtener_precio_actual(cliente, SIMBOLO)
        if precio_actual <= 0:
            print("❌ No se pudo obtener el precio actual.")
            break

        print(f"\n  Precio actual de mercado: {precio_actual:.2f} USDT")

        # ─── CAPA 4: FRENO DE MANO ──────────────────────────
        mostrar_banner("🛑 CAPA 4: GESTOR DE RIESGO")

        riesgo = evaluar_riesgo(
            balance_total=CAPITAL_TOTAL,
            precio_entrada=precio_actual,
            operaciones_activas=operaciones_activas
        )

        print(f"  Autorizado    : {'✅' if riesgo['autorizado'] else '❌'}")
        print(f"  Parte usada   : #{riesgo['parte_usada']}")
        if riesgo["autorizado"]:
            print(f"  Tamaño        : {riesgo['tamano_posicion']:.6f} BTC")
            print(f"  Stop-Loss     : {riesgo['stop_loss']:.2f} USDT")
            print(f"  Pérdida máx   : {riesgo['perdida_max']:.2f} USDT")
        print(f"  {riesgo['fundamento']}")

        if not riesgo["autorizado"]:
            print("\n⛔  Gestor de Riesgo BLOQUEÓ la operación.")
            ciclo += 1
            time.sleep(3)
            if ciclo > 3:
                break
            continue

        # ─── CAPA 4.5: GRID DCA (solo si es COMPRA) ─────────
        if decision["accion"] == "BUY":
            mostrar_banner("📊 CAPA 4.5: GRID DCA — ESCALERA DE RECUPERACIÓN")
            try:
                # Usar el precio actual como precio_inicial del grid
                grid = calcular_grilla(
                    precio_inicial=precio_actual,
                    orden_base=riesgo["tamano_posicion"] * precio_actual * 0.3,  # 30% de la orden en nivel 1
                    mult_desviacion=1.25,
                    mult_tamano=1.15,
                    max_ordenes=10,
                    primer_escalon_pct=0.01
                )
                # Mostrar solo resumen para no saturar
                ultimo = len(grid["nivel"]) - 1
                print(f"  📐  Grilla DCA calculada ({len(grid['nivel'])} niveles):")
                print(f"       Caída máxima cubierta: {grid['desv_pct'][ultimo]:.1f}%")
                print(f"       Precio promedio target: {grid['precio_promedio'][ultimo]:.2f} USDT")
                print(f"       Capital total requerido: {grid['total_usdt'][ultimo]:.2f} USDT")
                print(f"       Rebote necesario: {grid['recuperacion_pct'][ultimo]:.1f}%")
            except Exception as e:
                print(f"  ⚠️  No se pudo calcular grilla DCA: {e}")

        # ─── CAPA 5: BRAZO EJECUTOR ─────────────────────────
        mostrar_banner("🚀 CAPA 5: EJECUCIÓN DE ORDEN")

        resultado = ejecutar_orden(
            cliente=cliente,
            simbolo=SIMBOLO,
            accion=decision["accion"],
            cantidad=riesgo["tamano_posicion"],
            stop_loss=riesgo["stop_loss"]
        )

        print(f"  Resultado: {resultado['detalle']}")

        if resultado["exito"]:
            operaciones_activas[riesgo["parte_usada"]] = True
            print("\n" + "🌟" * 30)
            print(f"  ✅  OPERACIÓN COMPLETADA EXITOSAMENTE")
            print(f"  {'🌟' * 30}")
            print(f"  Acción     : {decision['accion']}")
            print(f"  Cantidad   : {riesgo['tamano_posicion']:.6f} BTC")
            print(f"  Precio     : {resultado['precio']:.2f} USDT")
            print(f"  Inversión  : {riesgo['tamano_posicion'] * resultado['precio']:.2f} USDT")
            print(f"  Parte      : #{riesgo['parte_usada']} de 3")
            print(f"  SL         : {riesgo['stop_loss']:.2f} USDT")
            print(f"  Order ID   : {resultado['order_id']}")
            print(f"  Régimen    : {regimen}")
            print(f"\n  📊  Partes: ", end="")
            for p, ocupada in operaciones_activas.items():
                print(f"#{p}: {'🔴' if ocupada else '🟢'} ", end="")
            print()
            print("\n🏁  Demo completada — orden ejecutada exitosamente.")
            break
        else:
            print("\n❌  La orden NO se ejecutó.")
            break

    # ─── Resumen final ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  🤖  BOT v3 FINALIZADO")
    print("=" * 60)
    print(f"  Ciclos       : {ciclo}")
    print(f"  Partes usadas: {sum(1 for v in operaciones_activas.values() if v)} de 3")
    print(f"  Estrategias  : {len(ESTRATEGIAS_ACTIVAS)} activas de 50 registradas")
    print(f"  Régimen final: {regimen}")
    print(f"\n  🚀  Sistema completo listo.")


if __name__ == "__main__":
    logging.getLogger("binance").setLevel(logging.WARNING)
    main()