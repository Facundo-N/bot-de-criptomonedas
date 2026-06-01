#!/usr/bin/env python3
"""
Estrategia #4: Bollinger Bands Bounce (Reversión a la Media)
-------------------------------------------------------------
Creada por John Bollinger. Usa bandas de ±2 desviaciones estándar alrededor
de una SMA de 20 períodos para identificar extremos del precio.

FÓRMULA:
  Banda_Superior = SMA(20) + 2 × σ(20)
  Banda_Inferior = SMA(20) - 2 × σ(20)
  donde σ = desviación estándar de los últimos 20 períodos

REGLAS:
  - Precio toca o cruza la BANDA INFERIOR y luego cierra por encima → BUY
  - Precio toca o cruza la BANDA SUPERIOR y luego cierra por debajo → SELL
  - El precio está dentro de las bandas → HOLD

ENTRADA:  DataFrame con columnas "Cierre", "Máximo", "Mínimo"
SALIDA:   dict con {"accion", "confianza", "fundamento"}
"""

import pandas as pd


def calcular_bandas(precios: pd.Series, periodo: int = 20, desviaciones: float = 2.0) -> dict:
    """
    Calcula las Bandas de Bollinger.

    Retorna:
      {"media": pd.Series, "superior": pd.Series, "inferior": pd.Series}
    """
    sma = precios.rolling(window=periodo).mean()
    std = precios.rolling(window=periodo).std(ddof=0)  # ddof=0 = desviación poblacional

    return {
        "media": sma,
        "superior": sma + (std * desviaciones),
        "inferior": sma - (std * desviaciones)
    }


def evaluar(df: pd.DataFrame) -> dict:
    if df is None or len(df) < 21:
        return {
            "accion": "HOLD",
            "confianza": 0,
            "fundamento": "⚠️ Datos insuficientes (se necesitan ≥ 21 velas para Bollinger 20)."
        }

    precios = df["Cierre"].copy()
    bandas = calcular_bandas(precios, periodo=20, desviaciones=2.0)

    # Últimos 2 valores de cada banda
    superior = bandas["superior"]
    inferior = bandas["inferior"]
    media = bandas["media"]

    sup_act = superior.iloc[-1]
    inf_act = inferior.iloc[-1]
    media_act = media.iloc[-1]

    precio_act = precios.iloc[-1]
    precio_ant = precios.iloc[-2]
    precio_ant2 = precios.iloc[-3] if len(precios) >= 3 else precio_ant

    # Validar NaNs
    if pd.isna(sup_act) or pd.isna(inf_act):
        return {
            "accion": "HOLD",
            "confianza": 0,
            "fundamento": "⏳ Calculando Bandas de Bollinger... datos insuficientes."
        }

    # Ancho de banda (para medir volatilidad)
    ancho_banda = (sup_act - inf_act) / media_act * 100  # en porcentaje

    # ─── SEÑAL DE COMPRA: toque de banda inferior ────────────
    # El precio tocó o cruzó la banda inferior y ahora vuelve adentro
    if precio_ant <= inf_act and precio_act > inf_act:
        # Confianza basada en qué tan lejos fue el desvío
        distancia = (inf_act - precio_ant) / media_act * 100 if precio_ant < inf_act else 0
        confianza = min(85, int(55 + abs(distancia) * 15))

        return {
            "accion": "BUY",
            "confianza": confianza,
            "fundamento": (
                f"✅ BOLLINGER BOUNCE (compra). Precio tocó banda inferior "
                f"({precio_ant:.2f} ≤ {inf_act:.2f}) y rebotó → {precio_act:.2f}. "
                f"Ancho de banda: {ancho_banda:.1f}%. "
                f"Confianza: {confianza}%."
            )
        }

    # ─── SEÑAL DE VENTA: toque de banda superior ─────────────
    if precio_ant >= sup_act and precio_act < sup_act:
        distancia = (precio_ant - sup_act) / media_act * 100 if precio_ant > sup_act else 0
        confianza = min(85, int(55 + abs(distancia) * 15))

        return {
            "accion": "SELL",
            "confianza": confianza,
            "fundamento": (
                f"❌ BOLLINGER BOUNCE (venta). Precio tocó banda superior "
                f"({precio_ant:.2f} ≥ {sup_act:.2f}) y cayó → {precio_act:.2f}. "
                f"Ancho de banda: {ancho_banda:.1f}%. "
                f"Confianza: {confianza}%."
            )
        }

    # ─── DENTRO DE LAS BANDAS → HOLD ─────────────────────────
    return {
        "accion": "HOLD",
        "confianza": 25,
        "fundamento": (
            f"⏸️ Precio dentro de bandas. "
            f"Banda Sup: {sup_act:.2f} | Media: {media_act:.2f} | Banda Inf: {inf_act:.2f} | "
            f"Precio: {precio_act:.2f}. Ancho: {ancho_banda:.1f}%."
        )
    }


if __name__ == "__main__":
    import numpy as np
    print("🧪  Test: Bollinger Bands Bounce")
    np.random.seed(42)

    # Simular 100 velas
    precios = 70000 + np.cumsum(np.random.randn(100) * 30)

    # Forzar un toque de banda inferior: que el precio caiga fuerte y rebote
    precios[-5:] = [
        precios[-6] - 200,
        precios[-6] - 400,  # Toca banda inferior
        precios[-6] - 350,
        precios[-6] - 100,
        precios[-6] + 100   # Rebotó
    ]

    df_test = pd.DataFrame({
        "Fecha/Hora": pd.date_range("2026-05-01", periods=100, freq="h"),
        "Apertura": precios,
        "Máximo": precios + 50,
        "Mínimo": precios - 50,
        "Cierre": precios,
        "Volumen": np.random.randint(10, 50, 100)
    })

    r = evaluar(df_test)
    print(f"  Acción: {r['accion']} | Confianza: {r['confianza']}%")
    print(f"  {r['fundamento']}")