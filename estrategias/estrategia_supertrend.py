#!/usr/bin/env python3
"""
Estrategia #6: SuperTrend Indicator (Trend Following)
------------------------------------------------------
Algoritmo seguidor de tendencia que usa ATR para crear un trailing stop dinámico.

FÓRMULA:
  Bandas = (H + L) / 2 ± ATR × Multiplicador
  SuperTrend cambia cuando el precio cruza la banda opuesta.

REGLAS (configuración: ATR 10, Multiplicador 3):
  - SuperTrend está por DEBAJO del precio → tendencia ALCISTA → BUY
  - SuperTrend está por ENCIMA del precio → tendencia BAJISTA → SELL
  - Sin cambio de estado → mantener decisión anterior

ENTRADA:  DataFrame con "Cierre", "Máximo", "Mínimo"
SALIDA:   dict con {"accion", "confianza", "fundamento"}
"""

import pandas as pd
import numpy as np


def calcular_supertrend(high, low, close, periodo_atr=10, multiplicador=3.0):
    """
    Calcula el SuperTrend. Retorna dos arrays: (supertrend, direccion)
    donde direccion = 1 (alcista) o -1 (bajista).
    """
    h, l, c = np.asarray(high), np.asarray(low), np.asarray(close)
    n = len(c)

    # True Range
    hl = h - l
    hc = np.abs(h - np.roll(c, 1))
    lc = np.abs(l - np.roll(c, 1))
    tr = np.maximum(np.maximum(hl, hc), lc)
    tr[0] = hl[0]

    # ATR = EMA de TR
    atr = pd.Series(tr).ewm(span=periodo_atr, adjust=False).mean().values

    # Bandas básicas
    hl2 = (h + l) / 2.0
    banda_sup = hl2 + multiplicador * atr
    banda_inf = hl2 - multiplicador * atr

    supertrend = np.zeros(n)
    direccion = np.ones(n)  # 1 = alcista, -1 = bajista

    for i in range(1, n):
        if c[i] > banda_sup[i-1]:
            direccion[i] = 1
        elif c[i] < banda_inf[i-1]:
            direccion[i] = -1
        else:
            direccion[i] = direccion[i-1]

        if direccion[i] == 1:
            supertrend[i] = max(banda_inf[i], supertrend[i-1] if direccion[i-1] == 1 else banda_inf[i])
        else:
            supertrend[i] = min(banda_sup[i], supertrend[i-1] if direccion[i-1] == -1 else banda_sup[i])

    return supertrend, direccion


def evaluar(df: pd.DataFrame) -> dict:
    if df is None or len(df) < 12:
        return {"accion": "HOLD", "confianza": 0, "fundamento": "⚠️ Datos insuficientes."}

    precios = df["Cierre"].values
    _, direccion = calcular_supertrend(df["Máximo"].values, df["Mínimo"].values, precios, 10, 3.0)

    dir_act = direccion[-1]
    dir_ant = direccion[-2]

    precio_act = precios[-1]

    # Detectar cambio de dirección (cruce de SuperTrend)
    if dir_ant == -1 and dir_act == 1:
        # Cambió de bajista a alcista → BUY
        return {
            "accion": "BUY",
            "confianza": 75,
            "fundamento": f"✅ SuperTrend cambió a ALCISTA. Precio: {precio_act:.2f}. Inicio de tendencia alcista."
        }
    elif dir_ant == 1 and dir_act == -1:
        return {
            "accion": "SELL",
            "confianza": 75,
            "fundamento": f"❌ SuperTrend cambió a BAJISTA. Precio: {precio_act:.2f}. Inicio de tendencia bajista."
        }

    # Sin cambio: mantener dirección
    if dir_act == 1:
        return {
            "accion": "BUY",
            "confianza": 60,
            "fundamento": f"📈 SuperTrend ALCISTA. Precio: {precio_act:.2f}. Tendencia positiva estable."
        }
    else:
        return {
            "accion": "SELL",
            "confianza": 60,
            "fundamento": f"📉 SuperTrend BAJISTA. Precio: {precio_act:.2f}. Tendencia negativa estable."
        }


if __name__ == "__main__":
    import numpy as np
    print("🧪  Test: SuperTrend Indicator")
    np.random.seed(42)
    precios = 70000 + np.cumsum(np.random.randn(100)*50) + np.linspace(0, 1000, 100)
    df_test = pd.DataFrame({
        "Fecha/Hora": pd.date_range("2026-05-01", periods=100, freq="h"),
        "Apertura": precios, "Máximo": precios+40, "Mínimo": precios-40,
        "Cierre": precios, "Volumen": np.random.randint(10,50,100)
    })
    r = evaluar(df_test)
    print(f"  Acción: {r['accion']} | Confianza: {r['confianza']}%")
    print(f"  {r['fundamento']}")