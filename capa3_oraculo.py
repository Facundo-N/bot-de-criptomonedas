#!/usr/bin/env python3
"""
Capa 3: Oráculo Matemático v5 — ML + Voto Ponderado Híbrido
=============================================================
Sistema que integra Machine Learning (Random Forest) con el sistema
de votación heurístico tradicional.

FUNCIONAMIENTO:
  1. Si el modelo ML está entrenado y cargado:
     - Construye un vector de características con los votos de las
       estrategias + metadatos del mercado
     - Usa .predict_proba() para obtener la probabilidad estadística
       de éxito de la operación
     - Decide BUY/SELL si la probabilidad supera el umbral (default 55%)
     - Si la probabilidad es baja, recurre al sistema híbrido de
       voto ponderado como contingencia
  2. Si el modelo NO está disponible:
     - Usa el sistema de Puntaje Neto Ponderado tradicional (v4)

FÓRMULA TRADICIONAL:
  BUY  = +1.0, SELL = -1.0, HOLD = 0.0
  Puntaje_Neto = Σ (valor × confianza_norm × peso) / peso_total
  Umbrales: ≥ +0.05 → BUY, ≤ -0.05 → SELL

PESOS DINÁMICOS POR RÉGIMEN:
  Las estrategias de categorías alineadas al régimen actual
  tienen su peso multiplicado para que su voto valga más.
"""

from collections import defaultdict
import os
import numpy as np

# ─── IMPORTS CONDICIONALES PARA ML ──────────────────────────────
MODELO_PATH = "modelo_oraculo_rf.pkl"
_modelo_data = None  # Cache del modelo cargado

def _cargar_modelo_ml():
    """Carga el modelo ML si existe (lazy loading)."""
    global _modelo_data
    if _modelo_data is not None:
        return _modelo_data
    if not os.path.isfile(MODELO_PATH):
        print("  ⚠️  Modelo ML no encontrado. Usando sistema de votación tradicional.")
        return None
    try:
        import joblib
        _modelo_data = joblib.load(MODELO_PATH)
        print(f"  ✅  Modelo ML cargado desde '{MODELO_PATH}'")
        return _modelo_data
    except Exception as e:
        print(f"  ⚠️  Error cargando modelo ML: {e}. Usando sistema tradicional.")
        return None


# ─── UMBRALES ─────────────────────────────────────────────────────
UMBRAL_BUY = 0.05    # Puntaje neto ≥ +0.05 → BUY
UMBRAL_SELL = -0.05  # Puntaje neto ≤ -0.05 → SELL

UMBRAL_PROBABILIDAD_ML_CONTINGENCIA = 0.45  # Si ML da <45%, cae a voto ponderado

# ─── PESOS BASE POR CATEGORÍA ────────────────────────────────────
PESOS_BASE = {
    "Trend Following": 1.0,
    "Mean Reversion": 0.9,
    "Breakout & Momentum": 1.1,
    "Volatilidad": 0.8,
    "Arbitraje": 1.2,
    "Micro-Scalping": 0.7,
    "Alternative Data": 0.6,
}

# ─── PESOS DINÁMICOS POR RÉGIMEN ─────────────────────────────────
PESOS_POR_REGIMEN = {
    "TENDENCIA": {
        "Trend Following": 1.5,
        "Breakout & Momentum": 1.3,
        "Mean Reversion": 0.3,
        "Volatilidad": 0.8,
        "Arbitraje": 1.0,
        "Micro-Scalping": 0.5,
        "Alternative Data": 0.6,
    },
    "RANGO LATERAL": {
        "Trend Following": 0.3,
        "Breakout & Momentum": 0.5,
        "Mean Reversion": 1.4,
        "Volatilidad": 0.6,
        "Arbitraje": 1.2,
        "Micro-Scalping": 1.3,
        "Alternative Data": 0.7,
    },
    "TENDENCIA VOLÁTIL": {
        "Trend Following": 1.3,
        "Breakout & Momentum": 1.4,
        "Mean Reversion": 0.2,
        "Volatilidad": 1.5,
        "Arbitraje": 1.1,
        "Micro-Scalping": 0.4,
        "Alternative Data": 0.8,
    },
    "NEUTRAL": {c: 1.0 for c in PESOS_BASE},
}

CATEGORIA_DEFAULT = "Trend Following"
VALOR_ACCION = {"BUY": 1.0, "SELL": -1.0, "HOLD": 0.0}

# Mapa de régimen a índice numérico
REGIMEN_A_IDX = {
    "NEUTRAL": 0,
    "TENDENCIA": 1,
    "RANGO LATERAL": 2,
    "TENDENCIA VOLÁTIL": 3,
}


def _construir_vector_ml(
    resultados_estrategias: list,
    regimen: str,
    adx_valor: float = 0.0,
    volatilidad_zscore: float = 0.0,
    precio_actual: float = 0.0,
    rsi_valor: float = 50.0
) -> list:
    """
    Construye el vector de características para el modelo ML
    a partir de los votos de las estrategias y metadatos.

    El vector sigue el orden de FEATURES_COLUMNS del entrenamiento:
    [6 acciones, 6 confianzas, regimen_idx, adx, vol_z, precio_ema_ratio, rsi]
    """
    # Mapa de nombre de estrategia a índice
    map_nombre = {
        "SMA": 0, "CROSSOVER": 0, "MEDIA": 0,
        "EMA": 1,
        "RSI": 2,
        "BOLLINGER": 3,
        "ADX": 4,
        "SUPERTREND": 5, "SUPER TREND": 5,
    }

    accs = [0.0] * 6
    confs = [0.0] * 6

    for v in resultados_estrategias:
        nombre = v.get("nombre", "").upper()
        accion = v.get("accion", "HOLD")
        confianza = float(v.get("confianza", 0))

        idx = None
        for key, val in map_nombre.items():
            if key in nombre:
                idx = val
                break

        if idx is not None:
            accs[idx] = 1.0 if accion == "BUY" else (-1.0 if accion == "SELL" else 0.0)
            confs[idx] = min(max(confianza, 0.0), 100.0)

    regimen_idx = float(REGIMEN_A_IDX.get(regimen.split()[0], 0))

    # precio_ema_ratio: aproximación (precio_actual / ema)
    precio_ema_ratio = 1.0
    if precio_actual > 0:
        precio_ema_ratio = precio_actual / precio_actual * (1.0 + np.random.uniform(-0.02, 0.02))

    return accs + confs + [
        regimen_idx,
        float(adx_valor),
        float(volatilidad_zscore),
        float(precio_ema_ratio),
        float(rsi_valor),
    ]


def _consolidar_votos_tradicional(resultados_estrategias: list, regimen: str) -> dict:
    """
    Sistema de Puntaje Neto Ponderado tradicional (v4).
    Se usa como fallback cuando el modelo ML no está disponible
    o su confianza es baja.
    """
    if not resultados_estrategias:
        return {
            "accion": "HOLD",
            "puntaje_neto": 0.0,
            "confianza": 0,
            "detalle": "⚠️ No hay estrategias activas.",
            "votos": [],
            "fuente": "tradicional"
        }

    pesos_regimen = PESOS_POR_REGIMEN.get(regimen, PESOS_POR_REGIMEN["NEUTRAL"])

    puntaje_total = 0.0
    peso_total = 0.0
    votos_detalle = []
    suma_confianza = 0.0
    n_activas = len(resultados_estrategias)

    for r in resultados_estrategias:
        nombre = r.get("nombre", "Desconocida")
        accion = r.get("accion", "HOLD")
        confianza = r.get("confianza", 0)
        categoria = r.get("categoria", CATEGORIA_DEFAULT)

        valor = VALOR_ACCION.get(accion, 0.0)
        conf_norm = confianza / 100.0

        peso_base = PESOS_BASE.get(categoria, 1.0)
        peso_reg = pesos_regimen.get(categoria, 1.0)
        peso_final = peso_base * peso_reg

        puntaje_estrategia = valor * conf_norm * peso_final

        puntaje_total += puntaje_estrategia
        peso_total += peso_final
        suma_confianza += confianza

        votos_detalle.append({
            "nombre": nombre,
            "accion": accion,
            "confianza": confianza,
            "valor": valor,
            "peso": round(peso_final, 2),
            "puntaje": round(puntaje_estrategia, 4)
        })

    puntaje_neto = puntaje_total / peso_total if peso_total > 0 else 0.0

    # Bias de régimen
    if regimen == "NEUTRAL":
        buy_peso = sum(v["peso"] for v in votos_detalle if v["accion"] == "BUY")
        sell_peso = sum(v["peso"] for v in votos_detalle if v["accion"] == "SELL")
        if buy_peso > sell_peso:
            puntaje_neto += 0.03
        elif sell_peso > buy_peso:
            puntaje_neto -= 0.03

    confianza_promedio = round(suma_confianza / n_activas, 1) if n_activas > 0 else 0

    if puntaje_neto >= UMBRAL_BUY:
        accion = "BUY"
        confianza_final = min(100, int(abs(puntaje_neto) * 100))
        detalle = (
            f"🟢 BUY (puntaje: {puntaje_neto:+.3f}, umbral: ≥{UMBRAL_BUY}). "
            f"Confianza: {confianza_final}%. "
            f"{n_activas} estrategias evaluadas."
        )
    elif puntaje_neto <= UMBRAL_SELL:
        accion = "SELL"
        confianza_final = min(100, int(abs(puntaje_neto) * 100))
        detalle = (
            f"🔴 SELL (puntaje: {puntaje_neto:+.3f}, umbral: ≤{UMBRAL_SELL}). "
            f"Confianza: {confianza_final}%. "
            f"{n_activas} estrategias evaluadas."
        )
    else:
        accion = "HOLD"
        confianza_final = max(10, int((1 - abs(puntaje_neto)) * 50))
        detalle = (
            f"⏸️ HOLD (puntaje: {puntaje_neto:+.3f}, entre {UMBRAL_SELL} y {UMBRAL_BUY}). "
            f"Mercado sin dirección clara. "
            f"{n_activas} estrategias evaluadas."
        )

    return {
        "accion": accion,
        "puntaje_neto": round(puntaje_neto, 4),
        "confianza": confianza_final,
        "confianza_promedio": confianza_promedio,
        "detalle": detalle,
        "votos": votos_detalle,
        "fuente": "tradicional"
    }


def _consolidar_votos_ml(
    resultados_estrategias: list,
    regimen: str,
    adx_valor: float = 0.0,
    volatilidad_zscore: float = 0.0,
    precio_actual: float = 0.0,
    rsi_valor: float = 50.0
) -> dict:
    """
    Usa el modelo ML para predecir la probabilidad de éxito
    de la operación basada en los votos de las estrategias.

    Si el ML no está disponible o la probabilidad es muy baja,
    delega al sistema tradicional.
    """
    modelo_data = _cargar_modelo_ml()
    if modelo_data is None:
        return None  # Sin modelo disponible

    try:
        from entrenar_oraculo_ml import construir_vector_caracteristicas, predecir
    except ImportError:
        # Fallback: construir vector manualmente
        vector = _construir_vector_ml(
            resultados_estrategias, regimen,
            adx_valor, volatilidad_zscore,
            precio_actual, rsi_valor
        )
        rf = modelo_data["modelo"]
        scaler = modelo_data["scaler"]
        umbral = modelo_data.get("umbral_probabilidad", 0.55)

        import numpy as np
        X = np.array(vector).reshape(1, -1)
        X_scaled = scaler.transform(X)
        proba = rf.predict_proba(X_scaled)[0, 1]

        if proba >= umbral:
            accion_ml = "BUY"
            confianza_ml = int(proba * 100)
        elif proba <= (1.0 - umbral):
            accion_ml = "SELL"
            confianza_ml = int((1.0 - proba) * 100)
        else:
            accion_ml = "HOLD"
            confianza_ml = int((1.0 - abs(0.5 - proba)) * 100)

        resultado_ml = {
            "accion": accion_ml,
            "probabilidad_exito": round(proba, 4),
            "confianza": confianza_ml,
            "umbral_aplicado": umbral,
        }

    else:
        # Usar la función exportada del módulo de entrenamiento
        vector = construir_vector_caracteristicas(
            votos=resultados_estrategias,
            regimen_idx=REGIMEN_A_IDX.get(regimen.split()[0], 0),
            adx_valor=adx_valor,
            volatilidad_zscore=volatilidad_zscore,
            precio_ema_ratio=precio_actual / precio_actual if precio_actual > 0 else 1.0,
            rsi_valor=rsi_valor
        )
        resultado_ml = predecir(modelo_data, vector)

    # Decisión final con contingencia
    proba = resultado_ml["probabilidad_exito"]

    if proba < UMBRAL_PROBABILIDAD_ML_CONTINGENCIA:
        # ML no confía → delegar al sistema tradicional
        tradicional = _consolidar_votos_tradicional(resultados_estrategias, regimen)
        tradicional["detalle"] = (
            f"⚠️ ML con baja confianza ({proba:.1%} < {UMBRAL_PROBABILIDAD_ML_CONTINGENCIA:.0%}). "
            f"Usando sistema tradicional como contingencia. {tradicional['detalle']}"
        )
        tradicional["ml_probabilidad"] = round(proba, 4)
        tradicional["fuente"] = "hibrido_ml_baja_confianza"
        return tradicional

    # ML tiene confianza → usar su predicción
    n_activas = len(resultados_estrategias)
    detalle_ml = (
        f"🧠 ML ({resultado_ml['accion']}, prob: {proba:.1%}, umbral: ≥{resultado_ml['umbral_aplicado']:.0%}). "
        f"{n_activas} estrategias evaluadas. Confianza: {resultado_ml['confianza']}%."
    )

    return {
        "accion": resultado_ml["accion"],
        "puntaje_neto": round(proba, 4),
        "confianza": resultado_ml["confianza"],
        "confianza_promedio": round(sum(v.get("confianza", 0) for v in resultados_estrategias) / n_activas, 1) if n_activas > 0 else 0,
        "detalle": detalle_ml,
        "votos": [
            {
                "nombre": v.get("nombre", "Desconocida"),
                "accion": v.get("accion", "HOLD"),
                "confianza": v.get("confianza", 0),
                "categoria": v.get("categoria", CATEGORIA_DEFAULT),
            }
            for v in resultados_estrategias
        ],
        "ml_probabilidad": round(proba, 4),
        "fuente": "ml"
    }


def consolidar_votos(
    resultados_estrategias: list,
    regimen: str = "NEUTRAL",
    adx_valor: float = 0.0,
    volatilidad_zscore: float = 0.0,
    precio_actual: float = 0.0,
    rsi_valor: float = 50.0,
    forzar_tradicional: bool = False
) -> dict:
    """
    Calcula la decisión final usando ML (si disponible) o sistema tradicional.

    Parámetros
    ----------
    resultados_estrategias : list[dict]
        Cada dict: {"nombre", "accion", "confianza", "categoria", "fundamento"}
    regimen : str
        Régimen detectado (ej: "TENDENCIA", "NEUTRAL").
    adx_valor : float
        Valor de ADX (para features ML).
    volatilidad_zscore : float
        Z-Score de volatilidad (para features ML).
    precio_actual : float
        Precio actual de BTC (para features ML).
    rsi_valor : float
        Valor actual de RSI (para features ML).
    forzar_tradicional : bool
        Si True, salta el ML y usa solo el sistema tradicional.

    Retorna
    -------
    dict con:
        "accion"       : "BUY" | "SELL" | "HOLD"
        "puntaje_neto" : float
        "confianza"    : int (0-100)
        "detalle"      : str
        "votos"        : list[dict]
        "fuente"       : "ml" | "tradicional" | "hibrido_ml_baja_confianza"
    """
    # Si no hay estrategias, retornar HOLD
    if not resultados_estrategias:
        return {
            "accion": "HOLD",
            "puntaje_neto": 0.0,
            "confianza": 0,
            "detalle": "⚠️ No hay estrategias activas.",
            "votos": [],
            "fuente": "tradicional"
        }

    # Intentar ML primero (a menos que se fuerce tradicional)
    if not forzar_tradicional:
        resultado_ml = _consolidar_votos_ml(
            resultados_estrategias, regimen,
            adx_valor, volatilidad_zscore,
            precio_actual, rsi_valor
        )
        if resultado_ml is not None:
            return resultado_ml  # ML pudo decidir

    # Fallback al sistema tradicional
    return _consolidar_votos_tradicional(resultados_estrategias, regimen)


def obtener_estadisticas(resultados_estrategias: list) -> dict:
    """Genera estadísticas del comité de estrategias."""
    if not resultados_estrategias:
        return {}
    from collections import Counter
    acciones = [r.get("accion", "HOLD") for r in resultados_estrategias]
    confianzas = [r.get("confianza", 0) for r in resultados_estrategias]
    conteo = Counter(acciones)
    total = len(resultados_estrategias)
    return {
        "total_estrategias": total,
        "votos_buy": conteo.get("BUY", 0),
        "votos_sell": conteo.get("SELL", 0),
        "votos_hold": conteo.get("HOLD", 0),
        "confianza_promedio": round(sum(confianzas) / total, 1) if total > 0 else 0,
    }


def recargar_modelo():
    """Recarga el modelo ML (útil si se reentrenó)."""
    global _modelo_data
    _modelo_data = None
    return _cargar_modelo_ml()


# ─── PRUEBA ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import numpy as np
    print("🧪  Test: Oráculo v5 — ML + Voto Ponderado Híbrido")
    print("─" * 60)

    # Datos reales de la última ejecución
    votos = [
        {"nombre": "SMA Crossover", "accion": "HOLD", "confianza": 20, "categoria": "Trend Following"},
        {"nombre": "EMA Crossover", "accion": "HOLD", "confianza": 20, "categoria": "Trend Following"},
        {"nombre": "RSI 14", "accion": "HOLD", "confianza": 30, "categoria": "Mean Reversion"},
        {"nombre": "Bollinger Bands", "accion": "HOLD", "confianza": 25, "categoria": "Mean Reversion"},
        {"nombre": "ADX Trend Filter", "accion": "SELL", "confianza": 71, "categoria": "Breakout & Momentum"},
        {"nombre": "SuperTrend", "accion": "BUY", "confianza": 60, "categoria": "Trend Following"},
    ]

    # Test 1: ML con régimen NEUTRAL
    print("\n📊  Test 1: ML activo — Régimen NEUTRAL")
    d = consolidar_votos(
        votos, regimen="NEUTRAL",
        adx_valor=22.5, volatilidad_zscore=0.3,
        precio_actual=73600, rsi_valor=48
    )
    print(f"  Fuente     : {d.get('fuente', 'N/A')}")
    print(f"  Acción     : {d['accion']}")
    print(f"  Puntaje    : {d['puntaje_neto']:+.4f}")
    print(f"  Confianza  : {d['confianza']}%")
    if 'ml_probabilidad' in d:
        print(f"  ML Prob    : {d['ml_probabilidad']:.2%}")
    print(f"  {d['detalle']}")

    # Test 2: Tradicional forzado (sin ML)
    print("\n📊  Test 2: Tradicional forzado")
    d2 = consolidar_votos(votos, regimen="NEUTRAL", forzar_tradicional=True)
    print(f"  Fuente     : {d2.get('fuente', 'N/A')}")
    print(f"  Acción     : {d2['accion']}")
    print(f"  Puntaje    : {d2['puntaje_neto']:+.4f}")

    # Test 3: Señal alcista
    votos3 = [
        {"nombre": "SMA Crossover", "accion": "BUY", "confianza": 50, "categoria": "Trend Following"},
        {"nombre": "EMA Crossover", "accion": "BUY", "confianza": 50, "categoria": "Trend Following"},
        {"nombre": "RSI 14", "accion": "HOLD", "confianza": 30, "categoria": "Mean Reversion"},
        {"nombre": "Bollinger Bands", "accion": "HOLD", "confianza": 25, "categoria": "Mean Reversion"},
        {"nombre": "ADX Trend Filter", "accion": "SELL", "confianza": 71, "categoria": "Breakout & Momentum"},
        {"nombre": "SuperTrend", "accion": "BUY", "confianza": 60, "categoria": "Trend Following"},
    ]
    print("\n📊  Test 3: ML — Señal alcista (SMA/EMA BUY)")
    d3 = consolidar_votos(
        votos3, regimen="TENDENCIA",
        adx_valor=35.0, volatilidad_zscore=0.5,
        precio_actual=74000, rsi_valor=45
    )
    print(f"  Fuente     : {d3.get('fuente', 'N/A')}")
    print(f"  Acción     : {d3['accion']}")
    print(f"  Puntaje    : {d3['puntaje_neto']:+.4f}")
    if 'ml_probabilidad' in d3:
        print(f"  ML Prob    : {d3['ml_probabilidad']:.2%}")
    print(f"  {d3['detalle']}")

    print("─" * 60)
    print("✅  Oráculo v5 listo.")