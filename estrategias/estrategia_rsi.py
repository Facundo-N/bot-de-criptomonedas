#!/usr/bin/env python3
"""
Estrategia #3: RSI Oversold/Overbought (Reversión a la Media)
--------------------------------------------------------------
El Relative Strength Index (RSI) mide la velocidad y magnitud de los cambios
de precio en una escala de 0 a 100.

FÓRMULA:
  RSI = 100 - [100 / (1 + (Ganancia_promedio / Pérdida_promedio))]
  donde:
    Ganancia_promedio = EMA de las ganancias en los últimos n períodos
    Pérdida_promedio  = EMA de las pérdidas en los últimos n períodos

REGLAS (configuración estándar 14 períodos):
  - RSI < 30 y luego cruza ARRIBA de 30 → BUY (sobreventa agotada)
  - RSI > 70 y luego cruza ABAJO de 70 → SELL (sobrecompra agotada)
  - RSI entre 30 y 70 → HOLD (zona neutral)

ENTRADA:  DataFrame con columna "Cierre"
SALIDA:   dict con {"accion", "confianza", "fundamento"}
"""

import pandas as pd


def calcular_rsi(precios: pd.Series, periodo: int = 14) -> pd.Series:
    """
    Calcula el RSI (Relative Strength Index) usando el método de Wilder (EMA de ganancias/pérdidas).

    Pasos:
      1. Calcular diferencias de precio: delta = precio[t] - precio[t-1]
      2. Separar ganancias (delta > 0) y pérdidas (delta < 0, en valor absoluto)
      3. Calcular EMA de ganancias y pérdidas con período = 14
      4. RSI = 100 - (100 / (1 + EMA_ganancias / EMA_pérdidas))
    """
    delta = precios.diff()

    ganancia = delta.clip(lower=0)   # Solo valores positivos (ganancias)
    perdida = (-delta).clip(lower=0)  # Solo valores negativos (pérdidas, en positivo)

    # EMA de Wilder: usar ewm con alpha = 1/periodo (equivalente a RMA de Wilder)
    alpha = 1.0 / periodo
    media_ganancia = ganancia.ewm(alpha=alpha, adjust=False).mean()
    media_perdida = perdida.ewm(alpha=alpha, adjust=False).mean()

    # Evitar división por cero
    rs = media_ganancia / media_perdida.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))

    return rsi


def evaluar(df: pd.DataFrame) -> dict:
    # Validar datos mínimos
    if df is None or len(df) < 15:
        return {
            "accion": "HOLD",
            "confianza": 0,
            "fundamento": "⚠️ Datos insuficientes (se necesitan ≥ 15 velas para RSI 14)."
        }

    precios = df["Cierre"].copy()
    rsi = calcular_rsi(precios, periodo=14)

    rsi_act = rsi.iloc[-1]    # Valor actual del RSI
    rsi_ant = rsi.iloc[-2]    # Valor anterior del RSI

    if pd.isna(rsi_act):
        return {
            "accion": "HOLD",
            "confianza": 0,
            "fundamento": "⏳ Calculando RSI... datos insuficientes."
        }

    # ─── SEÑAL DE COMPRA: RSI saliendo de sobreventa ──────────
    # Antes < 30, ahora >= 30 → el impulso vendedor se agotó
    if rsi_ant < 30 and rsi_act >= 30:
        # Qué tan profundo fue el RSI → a más bajo, más confianza
        profundidad = 30 - rsi_ant
        confianza = min(90, int(60 + profundidad * 3))

        return {
            "accion": "BUY",
            "confianza": confianza,
            "fundamento": (
                f"✅ RSI SALIENDO DE SOBREVENTA. "
                f"RSI actual: {rsi_act:.1f} (antes: {rsi_ant:.1f}). "
                f"El precio estaba en zona de sobreventa (<30) y está rebotando. "
                f"Confianza: {confianza}%."
            )
        }

    # ─── SEÑAL DE VENTA: RSI saliendo de sobrecompra ──────────
    # Antes > 70, ahora <= 70 → el impulso comprador se agotó
    if rsi_ant > 70 and rsi_act <= 70:
        profundidad = rsi_ant - 70
        confianza = min(90, int(60 + profundidad * 3))

        return {
            "accion": "SELL",
            "confianza": confianza,
            "fundamento": (
                f"❌ RSI SALIENDO DE SOBRECOMPRA. "
                f"RSI actual: {rsi_act:.1f} (antes: {rsi_ant:.1f}). "
                f"El precio estaba en zona de sobrecompra (>70) y está girando. "
                f"Confianza: {confianza}%."
            )
        }

    # ─── ZONA NEUTRAL ─────────────────────────────────────────
    if rsi_act >= 30 and rsi_act <= 70:
        return {
            "accion": "HOLD",
            "confianza": 30,
            "fundamento": (
                f"⏸️ RSI en zona neutral: {rsi_act:.1f} "
                f"(rango normal 30-70). Sin extremos de sobrecompra/venta."
            )
        }

    # ─── EXTREMO PERO SIN CONFIRMACIÓN DE GIRO ────────────────
    if rsi_act < 30:
        return {
            "accion": "HOLD",
            "confianza": 25,
            "fundamento": (
                f"⚠️ RSI en sobreventa ({rsi_act:.1f}) pero aún no confirma giro alcista. "
                f"Esperar cruce arriba de 30."
            )
        }

    if rsi_act > 70:
        return {
            "accion": "HOLD",
            "confianza": 25,
            "fundamento": (
                f"⚠️ RSI en sobrecompra ({rsi_act:.1f}) pero aún no confirma giro bajista. "
                f"Esperar cruce abajo de 70."
            )
        }

    # Fallback
    return {
        "accion": "HOLD",
        "confianza": 10,
        "fundamento": f"ℹ️ RSI: {rsi_act:.1f}. Sin señal clara."
    }


if __name__ == "__main__":
    import numpy as np
    print("🧪  Test: RSI 14 Oversold/Overbought")
    np.random.seed(42)

    # Simular precio con un pico y una caída para probar extremos
    precios = 70000 + np.cumsum(np.random.randn(150) * 100)
    # Forzar zona de sobreventa al final
    precios[-30:] = precios[-30] - np.linspace(0, 5000, 30)

    df_test = pd.DataFrame({
        "Fecha/Hora": pd.date_range("2026-05-01", periods=150, freq="h"),
        "Cierre": precios
    })

    r = evaluar(df_test)
    print(f"  Acción: {r['accion']} | Confianza: {r['confianza']}%")
    print(f"  {r['fundamento']}")

    # Mostrar RSI calculado
    rsi = calcular_rsi(df_test["Cierre"], 14)
    print(f"\n  Últimos 3 RSI: {rsi.iloc[-3]:.1f} → {rsi.iloc[-2]:.1f} → {rsi.iloc[-1]:.1f}")