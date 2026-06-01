#!/usr/bin/env python3
"""
Capa 4: Gestor de Riesgo v5 — Risk Management con R:R Configurable
-------------------------------------------------------------------
Evalúa si una operación es segura antes de ejecutarla, con soporte
para ratios de Riesgo/Beneficio (R:R) de 1:2 y 1:3.

R:R = Risk-to-Reward ratio.
  1:2  → Stop Loss 3%, Take Profit 6%
  1:3  → Stop Loss 2%, Take Profit 6% (más agresivo)

REGLAS DE ORO:
  1. Capital total dividido en 3 partes iguales.
  2. Riesgo máximo por operación: 7% del capital de la parte.
  3. Stop-Loss y Take Profit basados en ratio R:R configurable.
  4. Si el riesgo supera el límite → operación BLOQUEADA.
  5. Si ya hay una operación activa en esa parte → esperar.

ENTRADA:
  - balance_total : float (ej: 10000 USDT)
  - precio_entrada : float (precio al que se planea comprar)
  - operaciones_activas : dict (cuántas partes están en uso)
  - rr_ratio : str ("1:2" o "1:3") — ratio riesgo/beneficio deseado

SALIDA:
  dict con:
    "autorizado"      : bool
    "tamano_posicion"  : float (cantidad de BTC a comprar)
    "stop_loss"       : float (precio al que se vendería si cae)
    "take_profit"     : float (precio objetivo de ganancia)
    "perdida_max"     : float (pérdida máxima en USDT)
    "ganancia_esperada" : float (ganancia esperada en USDT si toca TP)
    "rr_ratio"        : str (ratio usado)
    "parte_usada"     : int (qué parte del capital se usa)
    "fundamento"      : str
"""

# ─── CONFIGURACIÓN ────────────────────────────────────────────────
CAPITAL_TOTAL = 10000.0        # USDT (saldo de prueba en Testnet)
NUM_PARTES = 3                 # Dividir capital en 3
RIESGO_POR_OPERACION = 0.07    # 7% del capital de la parte

# Ratios R:R configurables: { "ratio": (stop_loss_%, take_profit_%) }
RATIOS_RR = {
    "1:2": {"sl_pct": 0.03, "tp_pct": 0.06},   # SL 3%, TP 6%
    "1:3": {"sl_pct": 0.02, "tp_pct": 0.06},   # SL 2%, TP 6%
}

RATIO_DEFAULT = "1:2"  # Ratio por defecto


def evaluar_riesgo(
    balance_total: float,
    precio_entrada: float,
    operaciones_activas: dict,
    rr_ratio: str = RATIO_DEFAULT
) -> dict:
    """
    Evalúa si se puede abrir una nueva operación según las reglas de riesgo
    y el ratio R:R seleccionado.

    Parámetros
    ----------
    balance_total : float
        Saldo disponible en USDT.
    precio_entrada : float
        Precio actual de BTCUSDT al que compraríamos.
    operaciones_activas : dict
        Diccionario {1: bool, 2: bool, 3: bool} indicando qué partes están ocupadas.
    rr_ratio : str
        Ratio Riesgo/Beneficio deseado: "1:2" o "1:3".

    Retorna
    -------
    dict con resultado de la evaluación.
    """
    # ─── Validar ratio R:R ────────────────────────────────────
    rr_config = RATIOS_RR.get(rr_ratio)
    if rr_config is None:
        rr_config = RATIOS_RR[RATIO_DEFAULT]
        rr_ratio = RATIO_DEFAULT

    sl_pct = rr_config["sl_pct"]
    tp_pct = rr_config["tp_pct"]

    # ─── 1. Capital por parte ──────────────────────────────────
    capital_por_parte = balance_total / NUM_PARTES
    perdida_maxima_permitida = capital_por_parte * RIESGO_POR_OPERACION

    # ─── 2. Buscar una parte libre ─────────────────────────────
    parte_libre = None
    for parte in range(1, NUM_PARTES + 1):
        if not operaciones_activas.get(parte, False):
            parte_libre = parte
            break

    if parte_libre is None:
        return {
            "autorizado": False,
            "tamano_posicion": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "perdida_max": 0.0,
            "ganancia_esperada": 0.0,
            "rr_ratio": rr_ratio,
            "parte_usada": 0,
            "fundamento": "⛔ TODAS LAS PARTES OCUPADAS. Las 3 fracciones de capital ya están en uso. Esperar a que se cierre alguna operación."
        }

    # ─── 3. Calcular Stop-Loss y Take Profit basados en R:R ───
    stop_loss = precio_entrada * (1 - sl_pct)   # SL por debajo
    take_profit = precio_entrada * (1 + tp_pct)  # TP por encima

    # ─── 4. Calcular tamaño de posición ─────────────────────────
    # Máximo que podemos perder: perdida_maxima_permitida
    # Si compramos X BTC y el precio cae sl_pct%, perdemos X * (precio_entrada * sl_pct)
    # Despejamos X:
    #   X * (precio_entrada * sl_pct) = perdida_maxima_permitida
    #   X = perdida_maxima_permitida / (precio_entrada * sl_pct)
    diff_precio_sl = precio_entrada - stop_loss  # = precio_entrada * sl_pct
    diff_precio_tp = take_profit - precio_entrada  # = precio_entrada * tp_pct

    if diff_precio_sl <= 0:
        return {
            "autorizado": False,
            "tamano_posicion": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "perdida_max": 0.0,
            "ganancia_esperada": 0.0,
            "rr_ratio": rr_ratio,
            "parte_usada": 0,
            "fundamento": "❌ Precio de entrada inválido (stop_loss >= precio_entrada)."
        }

    tamano_posicion = perdida_maxima_permitida / diff_precio_sl
    ganancia_esperada = tamano_posicion * diff_precio_tp

    # ─── 5. Verificar que no gastemos más del capital disponible ─
    costo_total = tamano_posicion * precio_entrada
    if costo_total > capital_por_parte:
        # Si la posición nos pide más de lo que tenemos en esta parte, ajustamos
        tamano_posicion = capital_por_parte / precio_entrada
        perdida_real = tamano_posicion * diff_precio_sl
        ganancia_real = tamano_posicion * diff_precio_tp

        return {
            "autorizado": True,
            "tamano_posicion": round(tamano_posicion, 8),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "perdida_max": round(perdida_real, 2),
            "ganancia_esperada": round(ganancia_real, 2),
            "rr_ratio": rr_ratio,
            "parte_usada": parte_libre,
            "fundamento": (
                f"✅ OPERACIÓN AUTORIZADA (ajustada por capital). "
                f"Parte #{parte_libre} | "
                f"R:R {rr_ratio} | "
                f"Posición: {tamano_posicion:.6f} BTC | "
                f"Costo: {costo_total:.2f} USDT | "
                f"SL: {stop_loss:.2f} | "
                f"TP: {take_profit:.2f} | "
                f"Pérdida máx: {perdida_real:.2f} USDT | "
                f"Ganancia esp: {ganancia_real:.2f} USDT"
            )
        }

    # ─── 6. Todo OK → autorizar ─────────────────────────────────
    perdida_real = tamano_posicion * diff_precio_sl
    ganancia_real = tamano_posicion * diff_precio_tp

    return {
        "autorizado": True,
        "tamano_posicion": round(tamano_posicion, 8),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "perdida_max": round(perdida_real, 2),
        "ganancia_esperada": round(ganancia_real, 2),
        "rr_ratio": rr_ratio,
        "parte_usada": parte_libre,
        "fundamento": (
            f"✅ OPERACIÓN AUTORIZADA. "
            f"Parte #{parte_libre} | "
            f"R:R {rr_ratio} | "
            f"Posición: {tamano_posicion:.6f} BTC | "
            f"Costo: {costo_total:.2f} USDT | "
            f"SL: {stop_loss:.2f} | "
            f"TP: {take_profit:.2f} | "
            f"Pérdida máx: {perdida_real:.2f} USDT | "
            f"Ganancia esp: {ganancia_real:.2f} USDT"
        )
    }


def obtener_rr_config(rr_ratio: str = RATIO_DEFAULT) -> dict:
    """Retorna la configuración de un ratio R:R específico."""
    rr = RATIOS_RR.get(rr_ratio, RATIOS_RR[RATIO_DEFAULT])
    return {
        "ratio": rr_ratio,
        "stop_loss_pct": rr["sl_pct"] * 100,
        "take_profit_pct": rr["tp_pct"] * 100,
        "riesgo_beneficio": f"1:{int(rr['tp_pct']/rr['sl_pct'])}",
    }


# ─── PRUEBA RÁPIDA ────────────────────────────────────────────────
if __name__ == "__main__":
    print("🧪  Test: Gestor de Riesgo v5 — R:R Configurable")
    print("─" * 60)

    activas = {1: False, 2: False, 3: False}
    precio_test = 73600.00

    for ratio in ["1:2", "1:3"]:
        print(f"\n📊  Ratio R:R = {ratio}")
        print("─" * 40)
        resultado = evaluar_riesgo(
            balance_total=CAPITAL_TOTAL,
            precio_entrada=precio_test,
            operaciones_activas=activas,
            rr_ratio=ratio
        )
        print(f"  Capital total   : {CAPITAL_TOTAL:.2f} USDT")
        print(f"  Precio entrada  : {precio_test:.2f} USDT")
        print(f"  Autorizado      : {'✅' if resultado['autorizado'] else '❌'}")
        print(f"  R:R             : {resultado['rr_ratio']}")
        print(f"  SL              : {resultado['stop_loss']:.2f} USDT ({((resultado['stop_loss']/precio_test)-1)*100:+.2f}%)")
        print(f"  TP              : {resultado['take_profit']:.2f} USDT ({((resultado['take_profit']/precio_test)-1)*100:+.2f}%)")
        print(f"  Parte usada     : #{resultado['parte_usada']}")
        print(f"  Tamaño posición : {resultado['tamano_posicion']:.6f} BTC")
        print(f"  Pérdida máxima  : {resultado['perdida_max']:.2f} USDT")
        print(f"  Ganancia esperada: {resultado['ganancia_esperada']:.2f} USDT")
        print(f"  Fundamento      : {resultado['fundamento']}")

    print("\n" + "─" * 60)
    print("✅  Gestor de Riesgo v5 funcionando.")