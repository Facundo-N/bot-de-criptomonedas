#!/usr/bin/env python3
"""
Capa 2: Meta-Learner — Detector de Regímenes de Mercado
=========================================================
Analiza el contexto macro del mercado y determina qué categorías
de estrategias deben estar activas.

REGLAS POR RÉGIMEN:
  TENDENCIA FUERTE  (ADX > 25)  → Trend Following + Breakout & Momentum
  RANGO LATERAL     (ADX < 20)  → Mean Reversion + Micro-Scalping
  VOLATILIDAD ALTA  (ATR > 2σ)  → Volatilidad + Arbitraje
  NEUTRAL           (ninguno)   → Todas las categorías activas

ALGORITMO:
  1. Calcula ADX (direccionalidad) y ATR (volatilidad)
  2. Compara contra umbrales
  3. Retorna qué categorías apagar/encender

ENTRADA:  DataFrame OHLCV de velas (mínimo 50 períodos para ADX)
SALIDA:   dict con regimen, categorías activas/inactivas, fundamento
"""

import pandas as pd
import numpy as np


# ─── UMBRALES CONFIGURABLES ───────────────────────────────────────
UMBRAL_ADX_TENDENCIA = 25       # ADX > 25 → hay tendencia fuerte
UMBRAL_ADX_RANGO = 20           # ADX < 20 → mercado lateral
UMBRAL_ATR_ZSCORE = 1.5         # Z-Score del ATR > 1.5 → volatilidad anormal


# ─── CATEGORÍAS DEL SISTEMA ───────────────────────────────────────
CATEGORIAS = [
    "Trend Following",
    "Mean Reversion",
    "Breakout & Momentum",
    "Arbitraje",
    "Volatilidad",
    "Micro-Scalping",
    "Alternative Data"
]


def calcular_adx(df: pd.DataFrame, periodo: int = 14) -> float:
    """
    Calcula el ADX (Average Directional Index) usando el método de Wilder.
    
    ADX mide la FUERZA de la tendencia (no la dirección).
    > 25 → tendencia fuerte. < 20 → sin tendencia (rango).

    Pasos:
      1. +DM = max(H_act - H_ant, 0) si > max(L_ant - L_act, 0), sino 0
      2. -DM = max(L_ant - L_act, 0) si > max(H_act - H_ant, 0), sino 0
      3. TR = max(H - L, |H - C_ant|, |L - C_ant|)
      4. Suavizar +DM, -DM, TR con EMA de Wilder
      5. +DI = 100 × +DM_suav / TR_suav
      6. -DI = 100 × -DM_suav / TR_suav
      7. DX = 100 × |+DI - -DI| / (+DI + -DI)
      8. ADX = EMA_wilder(DX, periodo)
    """
    if df is None or len(df) < periodo * 2:
        return 0.0

    high = df["Máximo"].values
    low = df["Mínimo"].values
    close = df["Cierre"].values
    n = len(high)

    # Diferencias entre velas consecutivas
    # np.diff() calcula high[1] - high[0], high[2] - high[1], ...
    up_move = np.diff(high)      # Subidas intrabarra
    down_move = np.diff(low)     # Bajadas intrabarra
    # up_move = high_act - high_ant  (positivo si subió)
    # down_move = low_ant - low_act  (positivo si bajó... ojo con el signo)

    # True Range para cada barra
    # TR = max(H - L, |H - C_prev|, |L - C_prev|)
    hl = high[1:] - low[1:]                    # High - Low de la vela actual
    hc = np.abs(high[1:] - close[:-1])          # |High_act - Close_ant|
    lc = np.abs(low[1:] - close[:-1])           # |Low_act - Close_ant|
    tr = np.maximum(np.maximum(hl, hc), lc)     # Elemento a elemento: max de los 3

    # Direccional Movement
    # +DM = up_move si up_move > down_move y up_move > 0, sino 0
    # -DM = down_move si down_move > up_move y down_move > 0, sino 0
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Suavizado exponencial al estilo Wilder (alpha = 1/periodo)
    alpha = 1.0 / periodo

    # Inicializar arrays para los suavizados
    tr_smooth = np.zeros(n - 1)
    pos_smooth = np.zeros(n - 1)
    neg_smooth = np.zeros(n - 1)

    # Primer valor = promedio simple de los primeros `periodo` elementos
    tr_smooth[periodo - 1] = np.mean(tr[:periodo])
    pos_smooth[periodo - 1] = np.mean(pos_dm[:periodo])
    neg_smooth[periodo - 1] = np.mean(neg_dm[:periodo])

    # Wilder smoothing: valor_act = valor_ant + alpha × (valor_raw - valor_ant)
    for i in range(periodo, n - 1):
        tr_smooth[i] = tr_smooth[i - 1] + alpha * (tr[i] - tr_smooth[i - 1])
        pos_smooth[i] = pos_smooth[i - 1] + alpha * (pos_dm[i] - pos_smooth[i - 1])
        neg_smooth[i] = neg_smooth[i - 1] + alpha * (neg_dm[i] - neg_smooth[i - 1])

    # +DI y -DI
    pos_di = 100 * pos_smooth / np.where(tr_smooth == 0, 1e-10, tr_smooth)
    neg_di = 100 * neg_smooth / np.where(tr_smooth == 0, 1e-10, tr_smooth)

    # DX = 100 × |+DI - -DI| / (+DI + -DI)
    dx = 100 * np.abs(pos_di - neg_di) / np.where((pos_di + neg_di) == 0, 1e-10, pos_di + neg_di)

    # ADX = EMA de Wilder del DX
    adx_values = np.zeros(n - 1)
    adx_values[periodo - 1] = np.mean(dx[:periodo])
    for i in range(periodo, n - 1):
        adx_values[i] = adx_values[i - 1] + alpha * (dx[i] - adx_values[i - 1])

    return float(adx_values[-1]) if not np.isnan(adx_values[-1]) else 0.0


def calcular_volatilidad_zscore(df: pd.DataFrame, periodo_atr: int = 14) -> float:
    """
    Calcula el Z-Score del ATR actual vs su media histórica.
    > 1.5 → volatilidad inusualmente alta.
    < -1.5 → volatilidad inusualmente baja (posible squeeze).
    """
    if df is None or len(df) < periodo_atr * 2:
        return 0.0

    high = df["Máximo"].values
    low = df["Mínimo"].values
    close = df["Cierre"].values

    # True Range básico: max(H-L, |H-C_ant|, |L-C_ant|)
    hl = high - low
    hc = np.abs(high - np.roll(close, 1))
    lc = np.abs(low - np.roll(close, 1))
    tr = np.maximum(np.maximum(hl, hc), lc)
    tr[0] = hl[0]  # primera vela no tiene close anterior

    # ATR = EMA simple de TR
    atr = pd.Series(tr).ewm(span=periodo_atr, adjust=False).mean().values

    atr_actual = atr[-1]
    atr_media = np.mean(atr[-periodo_atr:])
    atr_std = np.std(atr[-periodo_atr:])

    if atr_std == 0:
        return 0.0

    return (atr_actual - atr_media) / atr_std


def detectar_regimen(df: pd.DataFrame) -> dict:
    """
    Determina el régimen actual del mercado basado en ADX y volatilidad.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame con columnas "Máximo", "Mínimo", "Cierre".
        Mínimo 50 velas para ADX confiable.

    Retorna
    -------
    dict con:
        "regimen"            : str
        "adx"                : float
        "volatilidad_zscore" : float
        "categorias_activas" : list[str]
        "categorias_inactivas" : list[str]
        "fundamento"          : str
    """
    if df is None or len(df) < 30:
        return {
            "regimen": "NEUTRAL (datos insuficientes)",
            "adx": 0.0,
            "volatilidad_zscore": 0.0,
            "categorias_activas": CATEGORIAS[:],
            "categorias_inactivas": [],
            "fundamento": "⚠️ Datos insuficientes. Activando todas las categorías por seguridad."
        }

    adx = calcular_adx(df, periodo=14)
    vol_zscore = calcular_volatilidad_zscore(df, periodo_atr=14)

    # ─── Determinar régimen ───────────────────────────────────
    if adx > UMBRAL_ADX_TENDENCIA:
        if vol_zscore > UMBRAL_ATR_ZSCORE:
            # Tendencia + Volatilidad alta → TENDENCIA VOLÁTIL
            regimen = "TENDENCIA VOLÁTIL"
            activas = ["Trend Following", "Breakout & Momentum", "Volatilidad"]
            fundamento = (
                f"📈 TENDENCIA VOLÁTIL. ADX={adx:.1f} (>{UMBRAL_ADX_TENDENCIA}) "
                f"indica tendencia fuerte. Volatilidad Z={vol_zscore:.1f} "
                f"indica alta volatilidad. Activando Trend + Momentum + Volatilidad. "
                f"Desactivando Mean Reversion (contra-tendencia)."
            )
        else:
            # Tendencia clásica
            regimen = "TENDENCIA"
            activas = ["Trend Following", "Breakout & Momentum"]
            fundamento = (
                f"📈 TENDENCIA. ADX={adx:.1f} (>{UMBRAL_ADX_TENDENCIA}) "
                f"indica tendencia direccional fuerte. "
                f"Activando Trend Following y Breakout. "
                f"Desactivando reversión a la media."
            )
    elif adx < UMBRAL_ADX_RANGO:
        regimen = "RANGO LATERAL"
        activas = ["Mean Reversion", "Micro-Scalping", "Arbitraje"]
        fundamento = (
            f"📊 RANGO LATERAL. ADX={adx:.1f} (<{UMBRAL_ADX_RANGO}) "
            f"indica ausencia de tendencia. "
            f"Activando Mean Reversion, Scalping y Arbitraje. "
            f"Desactivando estrategias de seguimiento de tendencia."
        )
    else:
        regimen = "NEUTRAL"
        activas = CATEGORIAS[:]
        fundamento = (
            f"⏸️ NEUTRAL. ADX={adx:.1f} (entre {UMBRAL_ADX_RANGO} y {UMBRAL_ADX_TENDENCIA}). "
            f"Mercado sin dirección clara. Todas las categorías activas."
        )

    # Si volatilidad es extremadamente alta por sí sola, agregar categoría
    if vol_zscore > 2.0 and "Volatilidad" not in activas:
        activas.append("Volatilidad")
        fundamento += " Volatilidad extrema (Z>{:.1f}) activa categoría de volatilidad.".format(2.0)

    inactivas = [c for c in CATEGORIAS if c not in activas]

    return {
        "regimen": regimen,
        "adx": round(adx, 1),
        "volatilidad_zscore": round(vol_zscore, 2),
        "categorias_activas": activas,
        "categorias_inactivas": inactivas,
        "fundamento": fundamento
    }


# ─── PRUEBA RÁPIDA ────────────────────────────────────────────────
if __name__ == "__main__":
    import numpy as np
    print("🧪  Test: Detector de Regímenes (Meta-Learner)")
    print("─" * 60)

    # Crear 100 velas con tendencia alcista fuerte (ADX alto)
    np.random.seed(42)
    precios = 70000 + np.cumsum(np.random.randn(100) * 30) + np.linspace(0, 3000, 100)

    df_test = pd.DataFrame({
        "Fecha/Hora": pd.date_range("2026-05-01", periods=100, freq="h"),
        "Apertura": precios,
        "Máximo": precios + np.random.randint(10, 50, 100),
        "Mínimo": precios - np.random.randint(10, 50, 100),
        "Cierre": precios,
        "Volumen": np.random.randint(10, 100, 100)
    })

    regimen = detectar_regimen(df_test)
    print(f"\n📊  Régimen detectado: {regimen['regimen']}")
    print(f"     ADX              : {regimen['adx']}")
    print(f"     Volatilidad Z    : {regimen['volatilidad_zscore']}")
    print(f"     Categorías activas  : {regimen['categorias_activas']}")
    print(f"     Categorías inactivas: {regimen['categorias_inactivas']}")
    print(f"     Fundamento       : {regimen['fundamento']}")
    print("─" * 60)
    print("✅  Meta-Learner listo.")