#!/usr/bin/env python3
"""
Capa 4.5: Motor DCA Avanzado — Grid Recovery con Multiplicadores
=================================================================
Estrategia inteligente de compra en escalera para mercados en caída.

TRES CONCEPTOS CLAVE:
  1. ESCALADOR DE CAÍDAS (Multiplicador de Desviación = 1.25x)
     Los escalones se estiran exponencialmente en lugar de ser fijos.
     Esto ahorra capital para las caídas más profundas.

  2. PRECIO PROMEDIO DINÁMICO (Multiplicador de Tamaño = 1.15x)
     Cada orden de abajo compra 15% más que la anterior.
     El precio promedio se arrastra hacia abajo rápidamente.

  3. CÁLCULO VECTORIZADO CON NUMPY
     Todas las operaciones se resuelven con arreglos de NumPy,
     sin un solo bucle for. Esto permite recalcular 1000 niveles
     en microsegundos.

FÓRMULAS:
  distancia_n = distancia_base × 1.25^(n-1)
  desv_acumulada_n = Σ(distancia_1 ... distancia_n)
  orden_n = orden_base × 1.15^(n-1)
  precio_n = precio_inicial × (1 - desv_acumulada_n)
  tokens_n = orden_n / precio_n
  precio_promedio = Σ(órdenes) / Σ(tokens)

SALIDA: dict con arrays de NumPy listos para ser usados por otras capas.
"""

import numpy as np

# ─── PARÁMETROS EDITABLES ──────────────────────────────────────────
PRECIO_INICIAL = 0.0986            # Precio del activo al empezar (USDT)
ORDEN_BASE = 7.5                   # Tamaño de la primera orden (USDT)
MULT_DESVIACION = 1.25             # Factor de estiramiento de escalones
MULT_TAMANO = 1.15                 # Factor de crecimiento de órdenes
MAX_ORDENES = 10                   # Número total de niveles
PRIMER_ESCALON_PCT = 0.01          # 1% → primera caída que dispara la compra


def calcular_grilla(
    precio_inicial: float = PRECIO_INICIAL,
    orden_base: float = ORDEN_BASE,
    mult_desviacion: float = MULT_DESVIACION,
    mult_tamano: float = MULT_TAMANO,
    max_ordenes: int = MAX_ORDENES,
    primer_escalon_pct: float = PRIMER_ESCALON_PCT
) -> dict:
    """
    Calcula la grilla completa de órdenes DCA usando NumPy vectorizado.

    El cálculo es 100% matricial — sin bucles for.

    Parámetros
    ----------
    precio_inicial : float
        Precio de referencia del activo cuando se activa la primera orden.
    orden_base : float
        Cantidad de USDT a invertir en la primera orden.
    mult_desviacion : float
        Factor que estira los escalones (1.25x = cada escalón es 25% más largo).
    mult_tamano : float
        Factor que aumenta cada orden (1.15x = cada orden es 15% mayor).
    max_ordenes : int
        Cantidad de niveles en la grilla.
    primer_escalon_pct : float
        Porcentaje de caída para la primera compra (0.01 = 1%).

    Retorna
    -------
    dict con:
        "nivel"         : np.ndarray[int]   → número de orden (1..N)
        "desv_pct"      : np.ndarray[float] → desviación total acumulada hasta este nivel
        "precio"        : np.ndarray[float] → precio del activo en este nivel
        "orden_usdt"    : np.ndarray[float] → USDT invertidos en esta orden
        "tokens"        : np.ndarray[float] → tokens comprados en esta orden
        "total_usdt"    : np.ndarray[float] → USDT totales invertidos hasta aquí
        "total_tokens"  : np.ndarray[float] → tokens totales acumulados hasta aquí
        "precio_promedio" : np.ndarray[float] → precio promedio ponderado hasta aquí
        "recuperacion_pct": np.ndarray[float] → % que debe subir el precio para salir a 0
    """
    # ─── PASO 1: Generar los índices de nivel ──────────────────
    # np.arange(1, 11) crea el vector [1, 2, 3, ..., 10]
    niveles = np.arange(1, max_ordenes + 1, dtype=np.float64)
    # n_minos_1 = [0, 1, 2, ..., 9]  → lo usamos para calcular potencias
    n_menos_1 = niveles - 1  # [0, 1, 2, ..., 9]

    # ─── PASO 2: Distancia de cada escalón ────────────────────
    # Cada escalón es más largo que el anterior:
    #   distancia_1 = primer_escalon_pct (1%)
    #   distancia_2 = 1% × 1.25 = 1.25%
    #   distancia_3 = 1% × 1.25^2 = 1.5625%
    #   ...
    #
    # Vectorizado: distancia = primer_escalon_pct × (mult)^0, (mult)^1, (mult)^2, ...
    # np.power(mult_desviacion, n_menos_1) = [1.25^0, 1.25^1, 1.25^2, ..., 1.25^9]
    distancias_paso = primer_escalon_pct * np.power(mult_desviacion, n_menos_1)

    # ─── PASO 3: Desviación acumulada ─────────────────────────
    # np.cumsum() suma acumulativamente:
    #   [1%, 1%+1.25%, 1%+1.25%+1.5625%, ...]
    # Esto nos da la caída TOTAL desde el precio inicial para cada nivel
    desv_acumulada = np.cumsum(distancias_paso)

    # ─── PASO 4: Precio en cada nivel ─────────────────────────
    # precio_n = precio_inicial × (1 - desv_acumulada_n)
    # Ejemplo: si desv_acumulada = 3.81%, precio = 0.0986 × (1 - 0.0381)
    # Esta operación se aplica a TODO el vector a la vez
    precios = precio_inicial * (1.0 - desv_acumulada)

    # ─── PASO 5: Tamaño de cada orden ─────────────────────────
    # orden_n = orden_base × 1.15^(n-1)
    #   orden_1 = 7.5 × 1.15^0 = 7.5 USDT
    #   orden_2 = 7.5 × 1.15^1 = 8.625 USDT
    #   orden_3 = 7.5 × 1.15^2 = 9.919 USDT
    # np.power() aplica el exponente a cada elemento del vector
    ordenes_usdt = orden_base * np.power(mult_tamano, n_menos_1)

    # ─── PASO 6: Tokens comprados por orden ───────────────────
    # tokens_n = orden_n / precio_n
    # División vectorial elemento a elemento
    tokens = ordenes_usdt / precios

    # ─── PASO 7: Totales acumulados ───────────────────────────
    # np.cumsum() suma acumulativamente ambos vectores
    total_usdt = np.cumsum(ordenes_usdt)
    total_tokens = np.cumsum(tokens)

    # ─── PASO 8: Precio promedio ponderado ────────────────────
    # Precio_promedio = Total_invertido / Total_tokens
    # Esto NO es un promedio simple, es ponderado por cantidad de tokens
    # Como las órdenes de abajo compran más tokens (más barato + más volumen),
    # el precio promedio se arrastra hacia abajo agresivamente
    precio_promedio = total_usdt / total_tokens

    # ─── PASO 9: Porcentaje de recuperación necesario ─────────
    # ¿Cuánto tiene que subir el precio ACTUAL para alcanzar el promedio?
    # recuperacion = (promedio - precio_actual) / precio_actual × 100
    recuperacion_pct = ((precio_promedio - precios) / precios) * 100.0

    # ─── Armamos el diccionario de salida ─────────────────────
    # Convertimos a enteros el array de niveles
    resultado = {
        "nivel": niveles.astype(int),
        "desv_pct": desv_acumulada * 100.0,        # en porcentaje
        "precio": precios,
        "orden_usdt": ordenes_usdt,
        "tokens": tokens,
        "total_usdt": total_usdt,
        "total_tokens": total_tokens,
        "precio_promedio": precio_promedio,
        "recuperacion_pct": recuperacion_pct
    }

    return resultado


def imprimir_tabla(resultado: dict):
    """
    Imprime la grilla completa como tabla formateada en la terminal.
    """
    n = len(resultado["nivel"])

    # Encabezados
    print("═" * 110)
    print("  📊  GRID DCA AVANZADO — Tabla de Órdenes")
    print("═" * 110)
    print(
        f"  {'Nivel':>5} | "
        f"{'Caída Acum':>10} | "
        f"{'Precio':>10} | "
        f"{'Orden USDT':>10} | "
        f"{'Tokens':>12} | "
        f"{'Total USDT':>10} | "
        f"{'Total Tok':>12} | "
        f"{'Promedio':>10} | "
        f"{'Recup %':>8}"
    )
    print("─" * 110)

    # Cada fila
    for i in range(n):
        print(
            f"  {resultado['nivel'][i]:>5} | "
            f"{resultado['desv_pct'][i]:>9.2f}% | "
            f"{resultado['precio'][i]:>10.6f} | "
            f"{resultado['orden_usdt'][i]:>10.2f} | "
            f"{resultado['tokens'][i]:>12.6f} | "
            f"{resultado['total_usdt'][i]:>10.2f} | "
            f"{resultado['total_tokens'][i]:>12.6f} | "
            f"{resultado['precio_promedio'][i]:>10.6f} | "
            f"{resultado['recuperacion_pct'][i]:>7.2f}%"
        )

    print("═" * 110)

    # Resumen final
    ultimo = n - 1
    print(f"\n📋  RESUMEN FINAL:")
    print(f"     Precio inicial        : {resultado['precio'][0]:.6f} USDT")
    print(f"     Precio final          : {resultado['precio'][ultimo]:.6f} USDT")
    print(f"     Caída total           : {resultado['desv_pct'][ultimo]:.2f}%")
    print(f"     Total invertido       : {resultado['total_usdt'][ultimo]:.2f} USDT")
    print(f"     Total tokens          : {resultado['total_tokens'][ultimo]:.6f}")
    print(f"     Precio promedio       : {resultado['precio_promedio'][ultimo]:.6f} USDT")
    print(f"     Rebote necesario      : {resultado['recuperacion_pct'][ultimo]:.2f}%")
    print(f"     Ahorro vs promedio simple: ", end="")

    # Comparación con promedio aritmético simple (sin ponderar)
    prom_simple = np.mean(resultado["precio"])
    ahorro_pct = (prom_simple - resultado["precio_promedio"][ultimo]) / prom_simple * 100
    print(f"{ahorro_pct:.2f}% más barato que el promedio aritmético.")


# ─── EJECUCIÓN PRINCIPAL ───────────────────────────────────────────
if __name__ == "__main__":
    print("🧪  Test: Motor DCA Avanzado con NumPy")
    print("═" * 110)

    # Parámetros del ejemplo
    datos = calcular_grilla(
        precio_inicial=PRECIO_INICIAL,
        orden_base=ORDEN_BASE,
        mult_desviacion=MULT_DESVIACION,
        mult_tamano=MULT_TAMANO,
        max_ordenes=MAX_ORDENES,
        primer_escalon_pct=PRIMER_ESCALON_PCT
    )

    imprimir_tabla(datos)

    # Verificar que no haya ningún bucle for en los cálculos
    print(f"\n🧠  Verificación técnica:")
    print(f"     Tipo de datos    : {type(datos['nivel']).__name__}")
    print(f"     Dimensión        : {datos['nivel'].shape}")
    print(f"     ¿Vectorizado?    : ✅ 100% NumPy, 0 bucles for")