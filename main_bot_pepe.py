#!/usr/bin/env python3
"""
main_bot_pepe.py — Bot Multi-Agente para PEPE/USDT ($17)
==========================================================
Adaptado para micro-capital con moneda de alto volatilidad.
No usa Testnet (solo BTC disponible allí). Operación directa en Mainnet.
"""

import os, re, logging, time, sys
from datetime import datetime, timedelta
from binance.spot import Spot as Client
from capa2_regimen_detector import detectar_regimen
from capa3_oraculo import recargar_modelo
from capa4_gestor_riesgo import CAPITAL_TOTAL
from capa5_ejecutor import ejecutar_orden, obtener_precio_actual
from agentes import crear_agentes

API_KEY_FILE = "api key.txt"
MAINNET_URL = "https://api.binance.com"
SIMBOLO = "PEPEUSDT"
INTERVALO = "1h"
VELAS = 200
CICLO_S = 5  # cada 5s para PEPE
CACHE_KLINES_S = 60

ESTRATEGIAS = []
def importar_estrategias():
    global ESTRATEGIAS
    from estrategias.estrategia_medias import evaluar as e1
    from estrategias.estrategia_ema import evaluar as e2
    from estrategias.estrategia_rsi import evaluar as e3
    from estrategias.estrategia_bollinger import evaluar as e4
    from estrategias.estrategia_adx import evaluar as e5
    from estrategias.estrategia_supertrend import evaluar as e6
    ESTRATEGIAS = [
        {"funcion":e1,"nombre":"SMA Crossover (20/50)","categoria":"Trend Following"},
        {"funcion":e2,"nombre":"EMA Crossover (9/21)","categoria":"Trend Following"},
        {"funcion":e3,"nombre":"RSI 14 Oversold/Overbought","categoria":"Mean Reversion"},
        {"funcion":e4,"nombre":"Bollinger Bands Bounce","categoria":"Mean Reversion"},
        {"funcion":e5,"nombre":"ADX Trend Strength Filter","categoria":"Breakout & Momentum"},
        {"funcion":e6,"nombre":"SuperTrend Indicator","categoria":"Trend Following"},
    ]

_cache_df=None; _cache_ts=0; _ultimo_rsi=50

def banner(t):
    print(f"\n{'='*50}\n  {t}\n{'='*50}")

def leer_claves():
    if not os.path.isfile(API_KEY_FILE): return None,None
    with open(API_KEY_FILE) as f: c=f.read()
    ak=re.search(r"API\s*Key:\s*(\S+)",c,re.I)
    sk=re.search(r"Secret\s*Key:\s*(\S+)",c,re.I)
    return (ak.group(1).strip() if ak else None, sk.group(1).strip() if sk else None)

def klines_df(klines):
    import pandas as pd
    df=pd.DataFrame(klines,columns=["ot","o","h","l","c","v","ct","qv","t","tbb","tbq","ig"])
    for col in ["o","h","l","c","v"]: df[col]=pd.to_numeric(df[col],errors="coerce")
    df["ot"]=pd.to_datetime(df["ot"],unit="ms")
    dc=df[["ot","o","h","l","c","v"]].copy()
    dc.columns=["Fecha/Hora","Apertura","Maximo","Minimo","Cierre","Volumen"]
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
        c=df["Cierre"].values
        if len(c)<15: return 50
        d=np.diff(c[-15:])
        g=np.where(d>0,d,0); l=np.where(d<0,-d,0)
        ag=np.mean(g[-14:]); al=np.mean(l[-14:])
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

def step_size_pepe(cli, simbolo=SIMBOLO):
    """Obtiene el step size minimo y cantidad minima para PEPE."""
    try:
        info=cli.exchange_info(symbol=simbolo)
        for f in info["symbols"][0]["filters"]:
            if f["filterType"]=="LOT_SIZE":
                return float(f["stepSize"]), float(f["minQty"])
    except: pass
    return 1.0, 1.0  # PEPE usa enteros

def truncar_cantidad(qty, step):
    import math
    return math.floor(qty/step)*step

def main():
    global _ultimo_rsi,_cache_ts,_cache_df,_ultimo_rsi
    _cache_ts=0;_cache_df=None

    print("="*55)
    print("  BOT PEPE/USDT v1 — $17")
    print(f"  {datetime.now().strftime('%H:%M:%S')}")
    print("="*55)

    importar_estrategias()

    ak,sk=leer_claves()
    if not ak or not sk: print("SIN CLAVES"); return
    cli=Client(ak,sk,base_url=MAINNET_URL)

    real=saldo_real_usdt(cli)
    print(f"  Saldo real: {real:.2f} USDT")
    if real<10: print("  SALDO MUY BAJO!"); return

    print("  Cargando ML...")
    recargar_modelo()

    # Obtener step size
    step, minq=step_size_pepe(cli)
    print(f"  Step size: {step}, Min: {minq}")

    ciclo=0; ultimo_analisis=0; btc=0; usdt_inv=0; precio_c=0; sl=0; tp=0; pnl_total=0; trades=[]

    try:
        while True:
            ciclo+=1
            ahora=time.time()

            # Obtener precio actual cada ciclo
            cli2=Client()
            try:
                t=cli2.ticker_price(symbol=SIMBOLO)
                precio=float(t["price"])
                cli2.close()
            except:
                time.sleep(CICLO_S); continue

            # Analisis completo cada 60s
            es_analisis=(ahora-_cache_ts)>=CACHE_KLINES_S or ciclo==1

            if es_analisis:
                df=obtener_df(cli)
                if df is None: time.sleep(CICLO_S); continue
                _ultimo_rsi=calc_rsi(df)
                reg=detectar_regimen(df)
                votos=filtrar_votos(df,None)
                print(f"\n--- #{ciclo} | PEPE:{precio:.8f} | RSI:{_ultimo_rsi:.0f} | {reg['regimen']} ---")
                _cache_ts=ahora

            # Monitoreo de TP/SL
            if btc>0:
                if tp>0 and precio>=tp:
                    r=ejecutar_orden(cliente=cli,simbolo=SIMBOLO,accion="SELL",cantidad=btc)
                    if r["exito"]:
                        ing=btc*r["precio"]; pnl=ing-usdt_inv; pnl_total+=pnl
                        c="+" if pnl>=0 else ""
                        print(f"  GANANCIA: ${c}{pnl:.2f}")
                        trades.append(pnl)
                        btc=0; usdt_inv=0; precio_c=0; sl=0; tp=0
                elif sl>0 and precio<=sl:
                    r=ejecutar_orden(cliente=cli,simbolo=SIMBOLO,accion="SELL",cantidad=btc)
                    if r["exito"]:
                        ing=btc*r["precio"]; pnl=ing-usdt_inv; pnl_total+=pnl
                        c="+" if pnl>=0 else ""
                        print(f"  PERDIDA: ${c}{pnl:.2f}")
                        trades.append(pnl)
                        btc=0; usdt_inv=0; precio_c=0; sl=0; tp=0

            # Decision de compra
            if es_analisis and btc<=0:
                from capa3_oraculo import consolidar_votos
                dec=consolidar_votos(votos,regimen=reg['regimen'].split()[0],
                    adx_valor=reg['adx'],volatilidad_zscore=reg['volatilidad_zscore'],
                    precio_actual=precio,rsi_valor=_ultimo_rsi)
                if dec["accion"]=="BUY":
                    from capa4_gestor_riesgo import evaluar_riesgo
                    riesgo=evaluar_riesgo(real,precio,{1:False,2:False,3:False},rr_ratio="1:2")
                    if riesgo["autorizado"]:
                        qty=truncar_cantidad(riesgo["tamano_posicion"],step)
                        if qty>=minq:
                            r=ejecutar_orden(cliente=cli,simbolo=SIMBOLO,accion="BUY",cantidad=qty)
                            if r["exito"]:
                                btc=qty; precio_c=r["precio"]; usdt_inv=qty*r["precio"]
                                sl=riesgo["stop_loss"]; tp=riesgo["take_profit"]
                                print(f"  COMPRADO {qty:.0f} PEPE @ ${precio_c:.8f}")
                                print(f"  TP: ${tp:.8f} | SL: ${sl:.8f}")

            # Estado en cada ciclo
            if btc>0:
                flot=(precio-precio_c)*btc
                c="+" if flot>=0 else ""
                print(f"  Posicion: {btc:.0f} PEPE | Flotante: ${c}{flot:.2f}",end="")
                print(f" | TP:${tp:.8f} SL:${sl:.8f}" if ciclo%12==0 else "")

            t=sum(trades); g=len([x for x in trades if x>0]); p=len([x for x in trades if x<=0])
            print(f"  Saldo: ${real+pnl_total:.2f} | Trades:{len(trades)} ({g}G/{p}P) P&L:{t:+.2f}",end="\r")

            time.sleep(CICLO_S)

    except KeyboardInterrupt:
        print(f"\n\n{'='*55}")
        print(f"  TRADES: {len(trades)}")
        g=len([x for x in trades if x>0]); p=len([x for x in trades if x<=0])
        wr=g/len(trades)*100 if trades else 0
        print(f"  {g}G/{p}P | WR:{wr:.0f}%")
        print(f"  P&L: ${sum(trades):+.2f}")
        print(f"  Saldo final: ${real+pnl_total:.2f}")
        print(f"{'='*55}")

if __name__=="__main__":
    logging.getLogger("binance").setLevel(logging.WARNING)
    main()