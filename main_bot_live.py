#!/usr/bin/env python3
"""
main_bot_live.py — Multi-Agente Autónomo v6
============================================
4 agentes operando en paralelo con ML + R:R.
Muestra el pensamiento de cada agente en cada análisis.
"""

import os, re, logging, time, sys
from datetime import datetime, timedelta
from binance.spot import Spot as Client
from capa2_regimen_detector import detectar_regimen
from capa3_oraculo import recargar_modelo
from capa4_gestor_riesgo import CAPITAL_TOTAL
from capa5_ejecutor import obtener_precio_actual
from agentes import crear_agentes, CAPITAL_POR_AGENTE
from estrategias.estrategia_medias import evaluar as eval_sma
from estrategias.estrategia_ema import evaluar as eval_ema
from estrategias.estrategia_rsi import evaluar as eval_rsi
from estrategias.estrategia_bollinger import evaluar as eval_bollinger
from estrategias.estrategia_adx import evaluar as eval_adx
from estrategias.estrategia_supertrend import evaluar as eval_supertrend

API_KEY_FILE = "api key.txt"
TESTNET_BASE_URL = "https://testnet.binance.vision"
SIMBOLO = "BTCUSDT"
INTERVALO = "1h"
VELAS = 200
CICLO_S = 0.5
CACHE_KLINES_S = 30

ESTRATEGIAS = [
    {"funcion": eval_sma,"nombre":"SMA Crossover (20/50)","categoria":"Trend Following"},
    {"funcion": eval_ema,"nombre":"EMA Crossover (9/21)","categoria":"Trend Following"},
    {"funcion": eval_rsi,"nombre":"RSI 14 Oversold/Overbought","categoria":"Mean Reversion"},
    {"funcion": eval_bollinger,"nombre":"Bollinger Bands Bounce","categoria":"Mean Reversion"},
    {"funcion": eval_adx,"nombre":"ADX Trend Strength Filter","categoria":"Breakout & Momentum"},
    {"funcion": eval_supertrend,"nombre":"SuperTrend Indicator","categoria":"Trend Following"},
]

_cache_df = None
_cache_ts = 0
_ultimo_rsi = 50

def banner(t):
    print(f"\n{'═'*50}\n  {t}\n{'═'*50}")
def sep():
    print(f"{'─'*50}")

def leer_claves():
    if not os.path.isfile(API_KEY_FILE): return None,None
    with open(API_KEY_FILE) as f: c = f.read()
    ak=re.search(r"API\s*Key:\s*(\S+)",c,re.I)
    sk=re.search(r"Secret\s*Key:\s*(\S+)",c,re.I)
    return (ak.group(1).strip() if ak else None, sk.group(1).strip() if sk else None)

def klines_df(klines):
    import pandas as pd
    df=pd.DataFrame(klines,columns=["openTime","open","high","low","close","volume","closeTime","quoteVolume","trades","takerBuyBase","takerBuyQuote","ignore"])
    for c in ["open","high","low","close","volume"]: df[c]=pd.to_numeric(df[c],errors="coerce")
    df["openTime"]=pd.to_datetime(df["openTime"],unit="ms")
    dc=df[["openTime","open","high","low","close","volume"]].copy()
    dc.columns=["Fecha/Hora","Apertura","Máximo","Mínimo","Cierre","Volumen"]
    return dc

def obtener_df(cli):
    global _cache_df,_cache_ts
    ahora=time.time()
    if _cache_df is not None and (ahora-_cache_ts)<CACHE_KLINES_S: return _cache_df
    try:
        fin=datetime.now(); ini=fin-timedelta(hours=VELAS+10)
        ks=cli.klines(symbol=SIMBOLO,interval=INTERVALO,startTime=int(ini.timestamp()*1000),endTime=int(fin.timestamp()*1000),limit=VELAS)
        if not ks or len(ks)<50: return None
        _cache_df=klines_df(ks); _cache_ts=ahora; return _cache_df
    except: return None

def calc_rsi(df):
    try:
        import numpy as np
        closes=df["Cierre"].values
        if len(closes)<15: return 50
        diffs=np.diff(closes[-15:])
        gains=np.where(diffs>0,diffs,0); losses=np.where(diffs<0,-diffs,0)
        ag=np.mean(gains[-14:]); al=np.mean(losses[-14:])
        if al==0: return 100
        return 100-100/(1+ag/al)
    except: return 50

def filtrar_votos(df,cats):
    res=[]
    for e in ESTRATEGIAS:
        if cats and e["categoria"] not in cats: continue
        try:
            v=e["funcion"](df); v["nombre"]=e["nombre"]; v["categoria"]=e["categoria"]; res.append(v)
        except: pass
    return res

def saldo_real_usdt(cli):
    try:
        ac=cli.account()
        for b in ac["balances"]:
            if b["asset"]=="USDT": return float(b["free"])
    except: pass
    return CAPITAL_TOTAL

def main():
    global _ultimo_rsi,_cache_ts,_cache_df
    _cache_ts=0;_cache_df=None

    banner("🤖  MULTI-AGENTE v6 — ML + R:R")
    print(f"  🕐 {datetime.now().strftime('%H:%M:%S')}")

    ak,sk=leer_claves()
    if not ak or not sk: print("❌ Sin claves"); return
    cli=Client(ak,sk,base_url=TESTNET_BASE_URL)

    real=saldo_real_usdt(cli); capa=real/4
    print(f"  💰 Saldo real: {real:.2f} USDT | 4 agentes ({capa:.0f} c/u)")
    print(f"  ⚡ Ciclo: {CICLO_S}s | Análisis: cada {CACHE_KLINES_S}s")
    print("  Ctrl+C para resumen final")
    print("\n  🔄 Cargando ML..."); recargar_modelo()

    agentes=crear_agentes(capital_por_agente=capa); ciclo=0

    try:
        while True:
            ciclo+=1
            df=obtener_df(cli)
            if df is None: time.sleep(CICLO_S); continue
            precio=df["Cierre"].iloc[-1]
            ahora_ts=time.time()

            es_analisis=(ahora_ts-_cache_ts)<=1

            if es_analisis:
                _ultimo_rsi=calc_rsi(df)
                reg=detectar_regimen(df)
                votos_todos=filtrar_votos(df,None)
                sep()
                print(f"  #{ciclo} | BTC:{precio:.0f} | RSI:{_ultimo_rsi:.0f} | {reg['regimen']} ADX:{reg['adx']}")

            for ag in agentes:
                flot_ant=ag.ultimo_flotante
                flot_act=ag.calcular_flotante(precio)
                ag.ultimo_flotante=flot_act

                if ag.btc>0:
                    razon_salida=ag.verificar_tp_sl(precio)
                    if razon_salida or (es_analisis and ag.decidir(votos_todos,reg['regimen'],reg['adx'],reg['volatilidad_zscore'],precio,_ultimo_rsi)["accion"]=="SELL" and not ag.solo_buy):
                        if not razon_salida: razon_salida="🔴 SELL"
                        r=ag.ejecutar_venta(cli,SIMBOLO,razon_salida)
                        if r:
                            c="🟢" if r["pnl"]>=0 else "🔴"
                            lbl="GANADO" if r["pnl"]>=0 else "PERDIDO"
                            print(f"  {ag.emoji} {ag.nombre}: {c} {lbl} {r['pnl']:+.2f}USDT ({r['pct']:+.2f}%) | {razon_salida}")

                if es_analisis and ag.btc<=0:
                    f=filtrar_votos(df,ag.categorias_requeridas)
                    dec=ag.decidir(f,reg['regimen'],reg['adx'],reg['volatilidad_zscore'],precio,_ultimo_rsi)
                    razon=dec.get("razon","")
                    # Forzar compra si pasaron N análisis sin operar
                    forzar = ag.analisis_sin_operar >= ag.fuerza_tras
                    if dec["accion"]=="BUY" or forzar:
                        r=ag.ejecutar_compra(cli,precio,SIMBOLO,balance_real=capa)
                        if r:
                            print(f"  {ag.emoji} {ag.nombre}: 🟢 COMPRADO {r['qty']:.6f} @{r['precio']:.0f} TP:{r['tp']:.0f} SL:{r['sl']:.0f}")
                            ag.analisis_sin_operar = 0
                        else:
                            print(f"  {ag.emoji} {ag.nombre}: ⛔ Sin saldo")
                            ag.analisis_sin_operar += 1
                    else:
                        ag.analisis_sin_operar += 1
                        print(f"  {ag.emoji} {ag.nombre}: ⏸️ {razon}")
                else:
                    if ag.btc>0: ag.analisis_sin_operar = 0

                if ag.btc>0:
                    cambio=abs(flot_act-(flot_ant or 0))
                    if cambio>=0.003 or es_analisis:
                        print(f"  {ag.linea_estado(precio)}")

            if es_analisis:
                tp=sum(a.pnl_total for a in agentes)
                tt=sum(len(a.trades) for a in agentes)
                print(f"  📊 Total: 💰{real+tp:.2f} | P&L:{tp:+.2f} | Trades:{tt}")

            time.sleep(CICLO_S)

    except KeyboardInterrupt:
        tp=sum(a.pnl_total for a in agentes)
        banner("📊  RESUMEN FINAL")
        for ag in agentes:
            g=len([t for t in ag.trades if t["pnl"]>0]); p=len([t for t in ag.trades if t["pnl"]<=0])
            wr=g/len(ag.trades)*100 if ag.trades else 0
            print(f"  {ag.emoji} {ag.nombre}: P&L:{ag.pnl_total:+.2f} | Trades:{len(ag.trades)} ({g}G/{p}P) WR:{wr:.0f}%")
        sep()
        print(f"  💰 Total: {real+tp:.2f} USDT")
        print(f"   P&L Global: {tp:+.2f} USDT")
        banner("✅ BOT DETENIDO")
    except Exception as e:
        import traceback; traceback.print_exc()

if __name__=="__main__":
    logging.getLogger("binance").setLevel(logging.WARNING)
    main()