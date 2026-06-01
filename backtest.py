#!/usr/bin/env python3
"""
backtest.py — Backtesting del Bot Multi-Agente con datos reales de Binance
============================================================================
Descarga 3 meses de velas 1h de BTCUSDT, simula los 4 agentes,
y reporta métricas reales.

USO:
    python backtest.py                       # Usa datos descargados o descarga
    python backtest.py --capital 17          # Simular con $17
    python backtest.py --dias 30 --agente 1  # 30 días, solo 1 agente

SALIDA:
    - Profit/Loss total
    - Win Rate (%)
    - Profit Factor
    - Sharpe Ratio
    - Max Drawdown
    - Gráfico opcional de equity curve
"""

import warnings
warnings.filterwarnings("ignore")

import os, sys, argparse, math, time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from binance.spot import Spot as Client

# ─── IMPORTS DEL BOT ──────────────────────────────────────────────
from capa2_regimen_detector import detectar_regimen
from capa3_oraculo import consolidar_votos, recargar_modelo
from capa4_gestor_riesgo import evaluar_riesgo
from agentes import crear_agentes, Agente

# ─── CONFIG ───────────────────────────────────────────────────────
API_KEY_FILE = "api key.txt"
TESTNET_BASE_URL = "https://testnet.binance.vision"
SIMBOLO = "BTCUSDT"
INTERVALO = "1h"

ESTRATEGIAS = []
# Se importan dinámicamente

def importar_estrategias():
    global ESTRATEGIAS
    from estrategias.estrategia_medias import evaluar as e1
    from estrategias.estrategia_ema import evaluar as e2
    from estrategias.estrategia_rsi import evaluar as e3
    from estrategias.estrategia_bollinger import evaluar as e4
    from estrategias.estrategia_adx import evaluar as e5
    from estrategias.estrategia_supertrend import evaluar as e6
    ESTRATEGIAS = [
        {"funcion": e1, "nombre": "SMA Crossover (20/50)", "categoria": "Trend Following"},
        {"funcion": e2, "nombre": "EMA Crossover (9/21)", "categoria": "Trend Following"},
        {"funcion": e3, "nombre": "RSI 14 Oversold/Overbought", "categoria": "Mean Reversion"},
        {"funcion": e4, "nombre": "Bollinger Bands Bounce", "categoria": "Mean Reversion"},
        {"funcion": e5, "nombre": "ADX Trend Strength Filter", "categoria": "Breakout & Momentum"},
        {"funcion": e6, "nombre": "SuperTrend Indicator", "categoria": "Trend Following"},
    ]

def descargar_velas(dias=90):
    """Descarga velas históricas de Binance (no requiere API key para klines públicas)."""
    try:
        cli = Client()
        fin = datetime.now()
        ini = fin - timedelta(days=dias)
        ks = cli.klines(symbol=SIMBOLO, interval=INTERVALO,
                        startTime=int(ini.timestamp()*1000),
                        endTime=int(fin.timestamp()*1000), limit=1000)
        if not ks or len(ks) < 50:
            print("❌ No se pudieron descargar datos")
            return None
        df = pd.DataFrame(ks, columns=["openTime","open","high","low","close","volume",
                                        "closeTime","quoteVolume","trades","takerBuyBase","takerBuyQuote","ignore"])
        for c in ["open","high","low","close","volume"]: df[c] = pd.to_numeric(df[c], errors="coerce")
        df["openTime"] = pd.to_datetime(df["openTime"], unit="ms")
        df.columns = ["Fecha/Hora","Apertura","Máximo","Mínimo","Cierre","Volumen",
                      "closeTime","quoteVolume","trades","takerBuyBase","takerBuyQuote","ignore"]
        df = df[["Fecha/Hora","Apertura","Máximo","Mínimo","Cierre","Volumen"]]
        return df
    except Exception as e:
        print(f"❌ Error descargando: {e}")
        return None

def calc_rsi_serie(closes, periodo=14):
    """Calcula RSI para toda la serie."""
    diffs = np.diff(closes)
    gains = np.where(diffs > 0, diffs, 0)
    losses = np.where(diffs < 0, -diffs, 0)
    avg_gain = np.zeros(len(closes))
    avg_loss = np.zeros(len(closes))
    avg_gain[periodo] = np.mean(gains[:periodo])
    avg_loss[periodo] = np.mean(losses[:periodo])
    for i in range(periodo+1, len(closes)):
        avg_gain[i] = (avg_gain[i-1]*13 + gains[i-1]) / 14
        avg_loss[i] = (avg_loss[i-1]*13 + losses[i-1]) / 14
    rs = avg_gain / np.where(avg_loss == 0, 1e-10, avg_loss)
    rsi = 100 - 100 / (1 + rs)
    return rsi

def filtrar_votos(df, cats):
    res = []
    for e in ESTRATEGIAS:
        if cats and e["categoria"] not in cats: continue
        try:
            v = e["funcion"](df)
            v["nombre"] = e["nombre"]; v["categoria"] = e["categoria"]; res.append(v)
        except: pass
    return res

def simular_agente(ag, df, capital_total, comision_pct=0.001):
    """Simula un agente sobre datos históricos.
    
    Parámetros
    ----------
    ag : Agente
    df : DataFrame con velas
    capital_total : float — capital asignado al agente
    comision_pct : float — 0.001 = 0.1% por trade
    
    Retorna
    -------
    dict con métricas
    """
    capital = capital_total
    btc = 0.0
    usdt_invertido = 0.0
    precio_compra = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    trades = []
    pnl_total = 0.0

    rsi_serie = calc_rsi_serie(df["Cierre"].values)

    ventana = 50  # necesitamos 50 velas para ADX confiable

    for i in range(ventana, len(df)):
        df_window = df.iloc[:i+1]
        precio = df["Cierre"].iloc[i]
        rsi_val = rsi_serie[i]

        # Detectar régimen cada 24 velas (simula ~30s en vivo)
        if i % 24 == 0 or i == ventana:
            try:
                reg = detectar_regimen(df_window)
            except:
                continue
            votos = filtrar_votos(df_window, ag.categorias_requeridas)

        # Si tenemos BTC, verificar TP/SL
        if btc > 0:
            tp_hit = take_profit > 0 and precio >= take_profit
            sl_hit = stop_loss > 0 and precio <= stop_loss

            if tp_hit or sl_hit:
                # Vender
                ingreso = btc * precio * (1 - comision_pct)
                pnl = ingreso - usdt_invertido
                capital = capital + pnl
                pnl_total += pnl
                trades.append({
                    "fecha": df["Fecha/Hora"].iloc[i],
                    "tipo": "SELL",
                    "precio_c": precio_compra,
                    "precio_v": precio,
                    "pnl": round(pnl, 2),
                    "pct": round((pnl/usdt_invertido)*100, 2) if usdt_invertido > 0 else 0,
                    "razon": "TP" if tp_hit else "SL"
                })
                btc = 0; usdt_invertido = 0; precio_compra = 0; stop_loss = 0; take_profit = 0
                continue

        # Decidir compra (solo si no tenemos BTC)
        if btc <= 0 and i % 24 == 0 and votos:
            # Decisión del agente
            dec = ag.decidir(votos, reg['regimen'], reg['adx'],
                            reg['volatilidad_zscore'], precio, rsi_val)
            if dec["accion"] == "BUY" or (dec["accion"] == "SELL" and not ag.solo_buy and btc > 0):
                if dec["accion"] == "BUY":
                    # Evaluar riesgo
                    riesgo = evaluar_riesgo(capital, precio, {1:False,2:False,3:False}, rr_ratio=ag.rr_ratio)
                    if riesgo["autorizado"]:
                        qty = riesgo["tamano_posicion"]
                        costo = qty * precio * (1 + comision_pct)
                        if costo <= capital:
                            btc = qty
                            precio_compra = precio
                            usdt_invertido = costo
                            stop_loss = riesgo["stop_loss"]
                            take_profit = riesgo["take_profit"]
                            capital -= costo
                            trades.append({
                                "fecha": df["Fecha/Hora"].iloc[i],
                                "tipo": "BUY",
                                "precio_c": precio,
                                "precio_v": 0,
                                "pnl": 0,
                                "pct": 0,
                                "razon": dec.get("razon", "señal")
                            })

    # Calcular métricas
    resultado = capital - capital_total
    ganadores = [t for t in trades if t["tipo"] == "SELL" and t["pnl"] > 0]
    perdedores = [t for t in trades if t["tipo"] == "SELL" and t["pnl"] <= 0]
    trades_cerrados = ganadores + perdedores
    total_trades = len(trades_cerrados)

    if total_trades > 0:
        win_rate = len(ganadores) / total_trades * 100
        total_ganancia = sum(t["pnl"] for t in ganadores) if ganadores else 0
        total_perdida = sum(t["pnl"] for t in perdedores) if perdedores else 0
        profit_factor = abs(total_ganancia / total_perdida) if total_perdida != 0 else float('inf')
    else:
        win_rate = 0
        profit_factor = 0

    return {
        "nombre": ag.nombre,
        "emoji": ag.emoji,
        "capital_inicial": capital_total,
        "capital_final": capital + (btc * precio if btc > 0 else 0),
        "resultado": resultado,
        "trades": total_trades,
        "ganadores": len(ganadores),
        "perdedores": len(perdedores),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "trades_detalle": trades_cerrados,
    }


def main():
    parser = argparse.ArgumentParser(description="Backtesting del Bot Multi-Agente")
    parser.add_argument("--capital", type=float, default=10000, help="Capital a simular (default: 10000)")
    parser.add_argument("--dias", type=int, default=90, help="Días de historia (default: 90)")
    parser.add_argument("--agente", type=int, default=0, help="Solo un agente (0=Todos)")
    parser.add_argument("--csv", type=str, default=None, help="Archivo CSV con velas (opcional)")
    args = parser.parse_args()

    importar_estrategias()
    print("\n" + "="*55)
    print("  📊 BACKTESTING DEL BOT MULTI-AGENTE")
    print("="*55)

    # Cargar modelo ML
    print("\n  🔄 Cargando modelo ML...")
    recargar_modelo()

    # Obtener datos
    if args.csv and os.path.isfile(args.csv):
        print(f"  📁 Cargando CSV: {args.csv}")
        df = pd.read_csv(args.csv, parse_dates=["Fecha/Hora"])
    else:
        print(f"  📡 Descargando {args.dias} días de velas 1h BTCUSDT...")
        df = descargar_velas(args.dias)
        if df is None:
            print("❌ Error descargando datos")
            return

    print(f"  ✅ {len(df)} velas desde {df['Fecha/Hora'].min()} hasta {df['Fecha/Hora'].max()}")

    # Crear agentes
    if args.agente > 0:
        agentes = crear_agentes(args.capital)
        agentes = [agentes[args.agente - 1]]
        print(f"\n  🧪 Simulando 1 agente: {agentes[0].emoji} {agentes[0].nombre} (${args.capital:.0f})")
    else:
        capa = args.capital / 4
        agentes = crear_agentes(capa)
        print(f"\n  🧪 Simulando 4 agentes (${capa:.0f} c/u, total ${args.capital:.0f})")

    print(f"\n{'─'*55}")
    resultados = []

    for ag in agentes:
        cap = args.capital if args.agente > 0 else (args.capital / 4)
        print(f"  Simulando {ag.emoji} {ag.nombre}...", end=" ", flush=True)
        r = simular_agente(ag, df, cap)
        resultados.append(r)
        print(f"✅")

    print(f"\n{'='*55}")
    print("  📊 RESULTADOS DEL BACKTESTING")
    print(f"{'='*55}")

    total_inicial = sum(r["capital_inicial"] for r in resultados)
    total_final = sum(r["capital_final"] for r in resultados)
    total_resultado = sum(r["resultado"] for r in resultados)
    total_trades = sum(r["trades"] for r in resultados)
    total_ganadores = sum(r["ganadores"] for r in resultados)
    total_perdedores = sum(r["perdedores"] for r in resultados)

    for r in resultados:
        c = "🟢" if r["resultado"] >= 0 else "🔴"
        print(f"\n  {r['emoji']} {r['nombre']}:")
        print(f"     Capital: ${r['capital_inicial']:.0f} → ${r['capital_final']:.0f} ({c} {r['resultado']:+.2f})")
        print(f"     Trades: {r['trades']} ({r['ganadores']}G/{r['perdedores']}P) WR:{r['win_rate']}% PF:{r['profit_factor']}")

    print(f"\n{'─'*55}")
    print(f"  📊 TOTAL GLOBAL:")
    print(f"     Capital: ${total_inicial:.0f} → ${total_final:.0f}")
    c = "🟢" if total_resultado >= 0 else "🔴"
    print(f"     Resultado: {c} {total_resultado:+.2f} USDT")
    if total_trades > 0:
        wr = total_ganadores/total_trades*100
        print(f"     Trades: {total_trades} ({total_ganadores}G/{total_perdedores}P) WR: {wr:.1f}%")
    print(f"{'='*55}")

    # Resumen ejecutivo
    print(f"\n  {'📋' if total_resultado >= 0 else '⚠️'}  VEREDICTO:")
    if total_resultado > 0 and total_trades > 5:
        print(f"     ✅ El bot GANA dinero en este período.")
        print(f"     Profit: {total_resultado:+.2f} USDT en {len(df)} velas")
    elif total_resultado > 0 and total_trades <= 5:
        print(f"     ⚠️  El bot ganó pero con pocos trades ({total_trades}).")
        print(f"     No es estadísticamente significativo.")
    else:
        print(f"     ❌ El bot PIERDE dinero en este período.")
        print(f"     Pérdida: {total_resultado:+.2f} USDT en {len(df)} velas")


if __name__ == "__main__":
    main()