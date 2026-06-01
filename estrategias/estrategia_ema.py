#!/usr/bin/env python3
"""
Estrategia #2: Cruce de Medias Móviles Exponenciales (EMA 9/21)
----------------------------------------------------------------
Sigue la tendencia con alta reactividad intradiaria.
Ideal para gráficos de 15min a 1h.

FÓRMULA:
  EMA = (Precio × k) + (EMA_anterior × (1 - k))
  donde k = 2 / (n + 1)

REGLAS:
  - EMA rápida (9) CRUZA ARRIBA de EMA lenta (21) → BUY
  - EMA rápida (9) CRUZA ABAJO de EMA lenta (21) → SELL
  - Sin cruce → HOLD

ENTRADA:  DataFrame con columna "Cierre"
SALIDA:   dict con {"accion", "confianza", "fundamento"}
"""

import pandas as pd


def calcular_ema(datos: pd.Series, periodo: int) -> pd.Series:
    """Calcula la media móvil exponencial (Exponential Moving Average)."""
    return datos.ewm(span=periodo, adjust=False).mean()


def evaluar(df: pd.DataFrame) -> dict:
    if df is None or len(df) < 22:
        return {
            "accion": "HOLD",
            "confianza": 0,
            "fundamento": "⚠️ Datos insuficientes (se necesitan ≥ 22 velas para EMA 9/21)."
        }

    precios = df["Cierre"].copy()

    # Calcular EMA rápida (9) y lenta (21)
    #   k_rapida = 2 / (9 + 1)  = 0.2  → más peso al precio reciente
    #   k_lenta  = 2 / (21 + 1) = 0.09 → más suavizada
    ema_rapida = calcular_ema(precios, 9)
    ema_lenta  = calcular_ema(precios, 21)

    rapida_act = ema_rapida.iloc[-1]
    rapida_ant = ema_rapida.iloc[-2]
    lenta_act  = ema_lenta.iloc[-1]
    lenta_ant  = ema_lenta.iloc[-2]

    if pd.isna(rapida_act) or pd.isna(lenta_act):
        return {
            "accion": "HOLD",
            "confianza": 0,
            "fundamento": "⏳ Calculando EMA... datos insuficientes."
        }

    # Cruce alcista: rápida < lenta antes, ahora rápida > lenta
    if rapida_ant <= lenta_ant and rapida_act > lenta_act:
        distancia = abs(rapida_act - lenta_act) / lenta_act * 100
        confianza = min(85, int(55 + distancia * 8))
        return {
            "accion": "BUY",
            "confianza": confianza,
            "fundamento": (
                f"✅ CRUCE ALCISTA EMA. EMA9 ({rapida_act:.2f}) cruzó ARRIBA de EMA21 ({lenta_act:.2f}). "
                f"Separación: {distancia:.2f}%. Confianza: {confianza}%."
            )
        }

    # Cruce bajista: rápida > lenta antes, ahora rápida < lenta
    if rapida_ant >= lenta_ant and rapida_act < lenta_act:
        distancia = abs(rapida_act - lenta_act) / lenta_act * 100
        confianza = min(85, int(55 + distancia * 8))
        return {
            "accion": "SELL",
            "confianza": confianza,
            "fundamento": (
                f"❌ CRUCE BAJISTA EMA. EMA9 ({rapida_act:.2f}) cruzó ABAJO de EMA21 ({lenta_act:.2f}). "
                f"Separación: {distancia:.2f}%. Confianza: {confianza}%."
            )
        }

    # --- Sin cruce claro PERO con tendencia definida ---
    # Si EMA9 > EMA21, tendencia alcista → BUY suave
    # Si EMA9 < EMA21, tendencia bajista → SELL suave
    if rapida_act > lenta_act:
        return {
            "accion": "BUY",
            "confianza": 50,
            "fundamento": (
                f"📈 Tendencia ALCISTA (sin cruce). "
                f"EMA9 ({rapida_act:.2f}) está por ENCIMA de EMA21 ({lenta_act:.2f}). "
                f"Sesión alcista. Confianza: 50%."
            )
        }
    else:
        return {
            "accion": "SELL",
            "confianza": 50,
            "fundamento": (
                f"📉 Tendencia BAJISTA (sin cruce). "
                f"EMA9 ({rapida_act:.2f}) está por DEBAJO de EMA21 ({lenta_act:.2f}). "
                f"Sesión bajista. Confianza: 50%."
            )
        }


if __name__ == "__main__":
    import numpy as np
    print("🧪  Test: EMA 9/21 Crossover")
    np.random.seed(42)
    precios = 70000 + np.cumsum(np.random.randn(100) * 50) + np.linspace(0, 3000, 100)
    df_test = pd.DataFrame({"Fecha/Hora": pd.date_range("2026-05-01", periods=100, freq="h"), "Cierre": precios})
    r = evaluar(df_test)
    print(f"  Acción: {r['accion']} | Confianza: {r['confianza']}%")
    print(f"  {r['fundamento']}")