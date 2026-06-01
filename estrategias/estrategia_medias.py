#!/usr/bin/env python3
"""
Estrategia #1: Cruce de Medias Móviles (SMA)
----------------------------------------------
Indicador clásico de seguimiento de tendencia.

REGLAS:
  - SMA rápida (20 periodos) CRUZA ARRIBA de SMA lenta (50)
    → SEÑAL DE COMPRA (bullish crossover)
  - SMA rápida CRUZA ABAJO de SMA lenta
    → SEÑAL DE VENTA (bearish crossover)
  - Si no hay cruce claro → HOLD

ENTRADA:  DataFrame con columnas ["Fecha/Hora", "Apertura", "Máximo", "Mínimo", "Cierre", "Volumen"]
SALIDA:   dict con {"accion": str, "confianza": int, "fundamento": str}
"""

import pandas as pd


def calcular_sma(datos: pd.Series, periodo: int) -> pd.Series:
    """Calcula la media móvil simple (Simple Moving Average)."""
    return datos.rolling(window=periodo).mean()


def evaluar(df: pd.DataFrame) -> dict:
    """
    Evalúa la estrategia de cruce de medias móviles.

    Parámetros
    ----------
    df : pd.DataFrame
        Debe tener al menos 50 filas (para la SMA lenta).
        Usa la columna 'Cierre'.

    Retorna
    -------
    dict con:
        "accion"     : "BUY" | "SELL" | "HOLD"
        "confianza"  : int (0-100)
        "fundamento" : str (explicación legible)
    """
    # Validar que haya suficientes datos
    if df is None or len(df) < 50:
        return {
            "accion": "HOLD",
            "confianza": 0,
            "fundamento": "⚠️ Datos insuficientes (se necesitan ≥ 50 velas)."
        }

    precios = df["Cierre"].copy()

    # Calcular SMA rápida (20) y lenta (50)
    sma_rapida = calcular_sma(precios, 20)   # Periodo 20 → sensible al precio reciente
    sma_lenta  = calcular_sma(precios, 50)   # Periodo 50 → tendencia de más largo plazo

    # Tomar los últimos 2 valores de cada SMA
    #   - actual   = posición [-1] (última vela cerrada)
    #   - anterior = posición [-2] (vela anterior)
    rapida_act   = sma_rapida.iloc[-1]
    rapida_ant   = sma_rapida.iloc[-2]
    lenta_act    = sma_lenta.iloc[-1]
    lenta_ant    = sma_lenta.iloc[-2]

    # Validar que no haya NaNs (necesitamos al menos 50 velas históricas)
    if pd.isna(rapida_act) or pd.isna(lenta_act):
        return {
            "accion": "HOLD",
            "confianza": 0,
            "fundamento": "⏳ Calculando SMA... aún no hay suficientes datos históricos."
        }

    # --- Cruce alcista (Golden Cross) ---
    # Antes: rápida <= lenta  |  Ahora: rápida > lenta
    if rapida_ant <= lenta_ant and rapida_act > lenta_act:
        # Calcular confianza: qué tan separadas están las medias
        distancia = abs(rapida_act - lenta_act) / lenta_act * 100  # % de separación
        confianza = min(90, int(50 + distancia * 10))              # 50% base + extra

        return {
            "accion": "BUY",
            "confianza": confianza,
            "fundamento": (
                f"✅ CRUCE ALCISTA (Golden Cross). "
                f"SMA20 ({rapida_act:.2f}) cruzó ARRIBA de SMA50 ({lenta_act:.2f}). "
                f"Separación: {distancia:.2f}%. Confianza: {confianza}%."
            )
        }

    # --- Cruce bajista (Death Cross) ---
    # Antes: rápida >= lenta  |  Ahora: rápida < lenta
    if rapida_ant >= lenta_ant and rapida_act < lenta_act:
        distancia = abs(rapida_act - lenta_act) / lenta_act * 100
        confianza = min(90, int(50 + distancia * 10))

        return {
            "accion": "SELL",
            "confianza": confianza,
            "fundamento": (
                f"❌ CRUCE BAJISTA (Death Cross). "
                f"SMA20 ({rapida_act:.2f}) cruzó ABAJO de SMA50 ({lenta_act:.2f}). "
                f"Separación: {distancia:.2f}%. Confianza: {confianza}%."
            )
        }

    # --- Sin cruce claro PERO con tendencia definida ---
    # Si SMA20 > SMA50, la tendencia es claramente alcista → BUY suave
    # Si SMA20 < SMA50, la tendencia es claramente bajista → SELL suave
    # Esto evita que la estrategia esté siempre muda
    if rapida_act > lenta_act:
        return {
            "accion": "BUY",
            "confianza": 50,
            "fundamento": (
                f"📈 Tendencia ALCISTA sin cruce. "
                f"SMA20 ({rapida_act:.2f}) está por ENCIMA de SMA50 ({lenta_act:.2f}). "
                f"Mercado con sesgo alcista. Confianza: 50%."
            )
        }
    else:
        return {
            "accion": "SELL",
            "confianza": 50,
            "fundamento": (
                f"📉 Tendencia BAJISTA sin cruce. "
                f"SMA20 ({rapida_act:.2f}) está por DEBAJO de SMA50 ({lenta_act:.2f}). "
                f"Mercado con sesgo bajista. Confianza: 50%."
            )
        }


# ─── PRUEBA RÁPIDA ────────────────────────────────────────────────
if __name__ == "__main__":
    # Generar datos de ejemplo para probar la estrategia
    import numpy as np

    print("🧪  Test de Estrategia: Cruce de Medias Móviles")
    print("─" * 60)

    # Crear 100 velas simuladas: precio subiendo (tendencia alcista)
    np.random.seed(42)
    precios_fake = 70000 + np.cumsum(np.random.randn(100) * 50) + np.linspace(0, 5000, 100)

    df_test = pd.DataFrame({
        "Fecha/Hora": pd.date_range("2026-05-01", periods=100, freq="h"),
        "Cierre": precios_fake
    })

    resultado = evaluar(df_test)
    print(f"  Acción    : {resultado['accion']}")
    print(f"  Confianza : {resultado['confianza']}%")
    print(f"  Fundamento: {resultado['fundamento']}")
    print("─" * 60)
    print("✅  Estrategia compilada y lista.")