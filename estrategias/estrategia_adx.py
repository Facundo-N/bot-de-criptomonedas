#!/usr/bin/env python3
"""
Estrategia #5: ADX Trend Strength Filter (Breakout & Momentum)
--------------------------------------------------------------
El Average Directional Index mide la fuerza de la tendencia,
independientemente de su dirección.

FÓRMULA:
  ADX = 100 × EMA(|+DI - -DI| / (+DI + -DI))

REGLAS (configuración 14 períodos):
  - ADX < 20 → sin tendencia. Votar HOLD (el mercado lateral no da señales fuertes)
  - ADX entre 20 y 30 → tendencia en desarrollo. Si precio > EMA 50 → BUY débil
  - ADX > 30 → tendencia fuerte. Si precio > EMA 50 → BUY fuerte. Si no → SELL
  - ADX > 40 → tendencia extremadamente fuerte. Confianza máxima.

ENTRADA:  DataFrame con columnas "Cierre", "Máximo", "Mínimo"
SALIDA:   dict con {"accion", "confianza", "fundamento"}
"""

import pandas as pd
import numpy as np


def calcular_adx(precios_close, precios_high, precios_low, periodo=14):
    """Calcula el ADX usando el método vectorizado de Wilder."""
    high = np.asarray(precios_high, dtype=float)
    low = np.asarray(precios_low, dtype=float)
    close = np.asarray(precios_close, dtype=float)
    n = len(high)

    up_move = np.diff(high)
    down_move = -np.diff(low)

    hl = high[1:] - low[1:]
    hc = np.abs(high[1:] - close[:-1])
    lc = np.abs(low[1:] - close[:-1])
    tr = np.maximum(np.maximum(hl, hc), lc)

    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    alpha = 1.0 / periodo
    m = n - 1
    tr_s = np.zeros(m); pos_s = np.zeros(m); neg_s = np.zeros(m)
    tr_s[periodo-1] = np.mean(tr[:periodo])
    pos_s[periodo-1] = np.mean(pos_dm[:periodo])
    neg_s[periodo-1] = np.mean(neg_dm[:periodo])
    for i in range(periodo, m):
        tr_s[i] = tr_s[i-1] + alpha * (tr[i] - tr_s[i-1])
        pos_s[i] = pos_s[i-1] + alpha * (pos_dm[i] - pos_s[i-1])
        neg_s[i] = neg_s[i-1] + alpha * (neg_dm[i] - neg_s[i-1])

    pdi = 100 * pos_s / np.where(tr_s == 0, 1e-10, tr_s)
    ndi = 100 * neg_s / np.where(tr_s == 0, 1e-10, tr_s)
    dx = 100 * np.abs(pdi - ndi) / np.where((pdi+ndi)==0, 1e-10, pdi+ndi)

    adx_v = np.zeros(m)
    adx_v[periodo-1] = np.mean(dx[:periodo])
    for i in range(periodo, m):
        adx_v[i] = adx_v[i-1] + alpha * (dx[i] - adx_v[i-1])
    return max(adx_v[-1], 0) if not np.isnan(adx_v[-1]) else 0


def evaluar(df: pd.DataFrame) -> dict:
    if df is None or len(df) < 30:
        return {"accion": "HOLD", "confianza": 0, "fundamento": "⚠️ Datos insuficientes."}

    precios = df["Cierre"].copy()
    adx_val = calcular_adx(df["Cierre"], df["Máximo"], df["Mínimo"], 14)

    # Determinar dirección: precio vs EMA 50
    ema_50 = precios.ewm(span=50, adjust=False).mean().iloc[-1]
    precio_act = precios.iloc[-1]
    sobre_ema = precio_act > ema_50

    direccion = "alcista" if sobre_ema else "bajista"

    # Reglas ADX
    if adx_val < 20:
        return {
            "accion": "HOLD",
            "confianza": 15,
            "fundamento": f"⏸️ ADX={adx_val:.1f}. Mercado sin tendencia (ADX<20). No conviene operar."
        }

    if 20 <= adx_val <= 30:
        if sobre_ema:
            confianza = int(40 + (adx_val - 20) * 3)
            return {
                "accion": "BUY",
                "confianza": min(60, confianza),
                "fundamento": f"✅ ADX={adx_val:.1f}. Tendencia en desarrollo ({direccion}). Precio sobre EMA50."
            }
        return {
            "accion": "SELL",
            "confianza": min(55, int(35 + (adx_val - 20) * 3)),
            "fundamento": f"❌ ADX={adx_val:.1f}. Tendencia en desarrollo ({direccion}). Precio bajo EMA50."
        }

    if 30 < adx_val <= 40:
        if sobre_ema:
            confianza = int(60 + (adx_val - 30) * 2)
            return {
                "accion": "BUY",
                "confianza": min(80, confianza),
                "fundamento": f"✅ ADX={adx_val:.1f}. Tendencia fuerte ({direccion}). Alta confianza."
            }
        return {
            "accion": "SELL",
            "confianza": min(75, int(55 + (adx_val - 30) * 2)),
            "fundamento": f"❌ ADX={adx_val:.1f}. Tendencia fuerte ({direccion}). Alta confianza."
        }

    # ADX > 40: tendencia extremadamente fuerte
    if sobre_ema:
        return {
            "accion": "BUY",
            "confianza": 90,
            "fundamento": f"🚀 ADX={adx_val:.1f}. Tendencia EXTREMADAMENTE fuerte ({direccion}). Confianza máxima."
        }
    return {
        "accion": "SELL",
        "confianza": 85,
        "fundamento": f"🔴 ADX={adx_val:.1f}. Tendencia EXTREMADAMENTE fuerte ({direccion}). Confianza máxima."
    }


if __name__ == "__main__":
    import numpy as np
    print("🧪  Test: ADX Trend Filter")
    np.random.seed(42)
    precios = 70000 + np.cumsum(np.random.randn(100)*40) + np.linspace(0, 2000, 100)
    df_test = pd.DataFrame({
        "Fecha/Hora": pd.date_range("2026-05-01", periods=100, freq="h"),
        "Apertura": precios, "Máximo": precios+30, "Mínimo": precios-30,
        "Cierre": precios, "Volumen": np.random.randint(10,50,100)
    })
    r = evaluar(df_test)
    print(f"  Acción: {r['accion']} | Confianza: {r['confianza']}%")
    print(f"  {r['fundamento']}")