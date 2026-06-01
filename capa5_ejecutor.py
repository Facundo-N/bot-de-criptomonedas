#!/usr/bin/env python3
"""
Capa 5: Brazo Ejecutor (Execution Engine)
-------------------------------------------
Envía órdenes de compra/venta a Binance Testnet.

Si las Capas 1, 2 y 4 dieron luz verde, esta capa se comunica con la API
y manda la orden a la velocidad de la luz. Luego monitorea la operación.

ENTRADA:
  - cliente  : Spot client de Binance (ya conectado)
  - simbolo  : str (ej: "BTCUSDT")
  - accion   : "BUY" | "SELL"
  - cantidad : float (cantidad de BTC a comprar/vender)
  - stop_loss: float (precio de Stop-Loss)

SALIDA:
  dict con resultado de la ejecución.
"""

import logging
from binance.spot import Spot as Client


logger = logging.getLogger("binance")


def ejecutar_orden(
    cliente: Client,
    simbolo: str,
    accion: str,
    cantidad: float,
    stop_loss: float = None
) -> dict:
    """
    Ejecuta una orden MARKET en Binance Testnet.

    Parámetros
    ----------
    cliente : Spot client
        Conexión activa a Binance.
    simbolo : str
        Par a operar, ej: "BTCUSDT".
    accion : str
        "BUY" para comprar, "SELL" para vender.
    cantidad : float
        Cantidad del activo base (BTC en BTCUSDT).
    stop_loss : float, opcional
        Precio de Stop-Loss. Si se provee, se agrega un Stop-Loss
        como orden LIMIT secundaria (si el exchange lo soporta).

    Retorna
    -------
    dict con:
        "exito"       : bool
        "order_id"    : int
        "precio"      : float (precio promedio ejecutado)
        "comision"    : float
        "status"      : str ("FILLED", "PARTIAL", "ERROR")
        "detalle"     : str
    """
    # Validaciones
    if cantidad <= 0:
        return {
            "exito": False,
            "order_id": 0,
            "precio": 0.0,
            "comision": 0.0,
            "status": "ERROR",
            "detalle": "❌ Cantidad inválida (debe ser > 0)."
        }

    if accion not in ("BUY", "SELL"):
        return {
            "exito": False,
            "order_id": 0,
            "precio": 0.0,
            "comision": 0.0,
            "status": "ERROR",
            "detalle": f"❌ Acción inválida: '{accion}'. Usar 'BUY' o 'SELL'."
        }

    try:
        # ─── TRUNCAR CANTIDAD AL STEP SIZE DE BINANCE ─────────
        # BTCUSDT requiere stepSize = 0.00001 (5 decimales)
        # Si no truncamos, la orden es rechazada con FILTER_FAILURE: LOT_SIZE
        import math
        step_size = 0.00001
        cantidad = math.floor(cantidad / step_size) * step_size
        cantidad = round(cantidad, 8)  # Eliminar errores de precisión flotante
        if cantidad <= 0:
            return {
                "exito": False,
                "order_id": 0,
                "precio": 0.0,
                "comision": 0.0,
                "status": "ERROR",
                "detalle": f"❌ Cantidad muy pequeña después de truncar a step size {step_size}."
            }

        # Enviar orden MARKET
        #   symbol        = "BTCUSDT"        → par a operar
        #   side          = "BUY" o "SELL"   → lado de la orden
        #   type          = "MARKET"         → orden de mercado (se ejecuta al precio actual)
        #   quantity      = float            → cantidad del activo base (BTC)
        #   newOrderRespType = "FULL"        → para recibir datos completos (fills, comisiones)
        print(f"📤  Enviando orden {accion} {cantidad:.6f} {simbolo}...")
        orden = cliente.new_order(
            symbol=simbolo,
            side=accion,
            type="MARKET",
            quantity=cantidad,
            newOrderRespType="FULL"
        )

        # Extraer datos de la respuesta
        order_id = orden.get("orderId", 0)
        status = orden.get("status", "UNKNOWN")
        fills = orden.get("fills", [])

        # Calcular precio promedio y comisión total
        precio_promedio = 0.0
        comision_total = 0.0
        cantidad_ejecutada = 0.0
        for fill in fills:
            precio = float(fill.get("price", 0))
            qty = float(fill.get("qty", 0))
            comision = float(fill.get("commission", 0))
            precio_promedio += precio * qty
            cantidad_ejecutada += qty
            comision_total += comision

        if cantidad_ejecutada > 0:
            precio_promedio /= cantidad_ejecutada

        detalle = (
            f"✅ Orden #{order_id} ejecutada. "
            f"Status: {status} | "
            f"Precio: {precio_promedio:.2f} USDT | "
            f"Comisión: {comision_total:.8f} BTC"
        )
        print(f"  {detalle}")

        # ─── Si tenemos stop_loss, intentar agregarlo ─────────
        if stop_loss and status == "FILLED":
            try:
                # Para Testnet, el Stop-Loss se implementa como una orden
                # STOP_LOSS_LIMIT que se activa cuando el precio toca el nivel.
                # OJO: Testnet puede no soportar todos los tipos de orden.
                orden_sl = cliente.new_order(
                    symbol=simbolo,
                    side="SELL",                       # Vender si el precio cae
                    type="STOP_LOSS_LIMIT",            # Orden condicionada
                    quantity=cantidad,                  # Misma cantidad comprada
                    price=stop_loss,                    # Precio límite (opcional)
                    stopPrice=stop_loss,                # Precio que activa la orden
                    timeInForce="GTC"                  # Good Till Cancelled
                )
                sl_id = orden_sl.get("orderId", 0)
                sl_status = orden_sl.get("status", "UNKNOWN")
                print(f"  🛑 Stop-Loss #{sl_id} colocado en {stop_loss:.2f} USDT (status: {sl_status})")
                detalle += f" | Stop-Loss #{sl_id} en {stop_loss:.2f} USDT"
            except Exception as e_sl:
                print(f"  ⚠️  No se pudo colocar Stop-Loss: {e_sl}")
                detalle += f" | ⚠️ SL no colocado: {e_sl}"

        return {
            "exito": True,
            "order_id": order_id,
            "precio": round(precio_promedio, 2),
            "comision": round(comision_total, 8),
            "status": status,
            "detalle": detalle
        }

    except Exception as e:
        error_msg = str(e)
        print(f"❌  Error al ejecutar orden: {error_msg}")
        return {
            "exito": False,
            "order_id": 0,
            "precio": 0.0,
            "comision": 0.0,
            "status": "ERROR",
            "detalle": f"❌ Error: {error_msg}"
        }


def obtener_precio_actual(cliente: Client, simbolo: str = "BTCUSDT") -> float:
    """
    Obtiene el precio actual de un símbolo desde Binance.
    Retorna el precio como float, o 0.0 si falla.
    """
    try:
        ticker = cliente.ticker_price(symbol=simbolo)
        return float(ticker["price"])
    except Exception as e:
        print(f"⚠️  No se pudo obtener precio de {simbolo}: {e}")
        return 0.0


# ─── PRUEBA RÁPIDA ────────────────────────────────────────────────
if __name__ == "__main__":
    print("🧪  Test: Ejecutor de Órdenes (sin conexión real)")
    print("─" * 60)
    print("  ℹ️   Este módulo requiere conexión a Binance para probarse.")
    print("  ℹ️   Se prueba en conjunto con main_bot.py")
    print("─" * 60)