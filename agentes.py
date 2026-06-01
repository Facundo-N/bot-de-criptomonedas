#!/usr/bin/env python3
"""
agentes.py — 4 Agentes Autónomos de Trading Paralelo v2
=========================================================
Cada agente usa su PROPIO umbral ML (no el del oráculo).
"""

import os, math, time
from datetime import datetime
from binance.spot import Spot as Client
from capa3_oraculo import consolidar_votos
from capa4_gestor_riesgo import evaluar_riesgo
from capa5_ejecutor import ejecutar_orden, obtener_precio_actual

CAPITAL_POR_AGENTE = 2500.0

class Agente:
    def __init__(self, nombre, emoji, capital, rr_ratio, umbral_ml,
                 solo_buy, categorias_requeridas, fuerza_tras_n_analisis=999):
        self.nombre = nombre
        self.emoji = emoji
        self.capital = capital
        self.rr_ratio = rr_ratio
        self.umbral_ml = umbral_ml          # Su PROPIO umbral
        self.solo_buy = solo_buy
        self.categorias_requeridas = categorias_requeridas
        self.fuerza_tras = fuerza_tras_n_analisis  # Forzar compra tras N análisis

        self.btc = 0.0
        self.usdt_invertido = 0.0
        self.precio_compra = 0.0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.pnl_total = 0.0
        self.trades = []
        self.ultimo_flotante = None
        self.analisis_sin_operar = 0
        self.tiempo_entrada = 0  # timestamp cuando compró

    @property
    def saldo_disponible(self):
        base = self.capital + self.pnl_total
        if self.btc > 0: return base - self.usdt_invertido
        return base

    def calcular_flotante(self, precio_actual):
        if self.btc <= 0 or self.precio_compra <= 0: return 0.0
        return (precio_actual - self.precio_compra) * self.btc

    def decidir(self, votos, regimen, adx_valor, vol_z, precio, rsi_valor):
        """
        Usa el ORÁCULO para obtener la probabilidad ML cruda,
        pero decide con SU PROPIO umbral.
        """
        d = consolidar_votos(votos, regimen=regimen.split()[0],
            adx_valor=adx_valor, volatilidad_zscore=vol_z,
            precio_actual=precio, rsi_valor=rsi_valor)

        ml_prob = d.get("ml_probabilidad", None)
        fuente = d.get("fuente", "tradicional")

        # Obtener la acción SIN filtros (solo para SELL si corresponde)
        accion_oraculo = d["accion"]

        # Si es solo BUY y el oráculo dice SELL → ignorar
        if self.solo_buy and accion_oraculo == "SELL":
            accion_oraculo = "HOLD"

        # DECISIÓN PROPIA basada en ML crudo
        if fuente == "ml" and ml_prob is not None:
            if ml_prob >= self.umbral_ml:
                # ML confía → BUY (o SELL si no es solo_buy)
                if self.solo_buy:
                    return {"accion": "BUY", "confianza": ml_prob, "razon": f"ML {ml_prob:.0%}≥{self.umbral_ml:.0%}"}
                else:
                    if accion_oraculo == "SELL":
                        return {"accion": "SELL", "confianza": 1.0-ml_prob, "razon": f"ML {ml_prob:.0%}≥{self.umbral_ml:.0%}"}
                    else:
                        return {"accion": "BUY", "confianza": ml_prob, "razon": f"ML {ml_prob:.0%}≥{self.umbral_ml:.0%}"}
            else:
                return {"accion": "HOLD", "confianza": ml_prob, "razon": f"ML {ml_prob:.0%}<{self.umbral_ml:.0%}"}

        # Fallback: usar acción del oráculo tradicional
        return {"accion": accion_oraculo, "confianza": 0.5, "razon": "tradicional"}

    def ejecutar_compra(self, cli, precio, simbolo, balance_real=None):
        saldo = balance_real if balance_real and balance_real > 10 else max(self.saldo_disponible, 1)
        riesgo = evaluar_riesgo(
            balance_total=saldo,
            precio_entrada=precio,
            operaciones_activas={1: False, 2: False, 3: False},
            rr_ratio=self.rr_ratio
        )
        if not riesgo["autorizado"]: return None
        qty = riesgo["tamano_posicion"]
        sl = riesgo["stop_loss"]
        tp = riesgo["take_profit"]
        r = ejecutar_orden(cliente=cli, simbolo=simbolo,
            accion="BUY", cantidad=qty, stop_loss=None)
        if r["exito"]:
            self.btc = qty
            self.precio_compra = r["precio"]
            self.usdt_invertido = qty * r["precio"]
            self.stop_loss = sl
            self.take_profit = tp
            self.tiempo_entrada = time.time()
            return {"qty": qty, "precio": r["precio"], "sl": sl, "tp": tp}
        return None

    def ejecutar_venta(self, cli, simbolo, razon):
        if self.btc <= 0: return None
        r = ejecutar_orden(cliente=cli, simbolo=simbolo, accion="SELL", cantidad=self.btc)
        if r["exito"]:
            ingreso = self.btc * r["precio"]
            pnl = ingreso - self.usdt_invertido
            pct = (pnl / self.usdt_invertido)*100 if self.usdt_invertido > 0 else 0
            self.pnl_total += pnl
            self.trades.append({
                "hora": datetime.now().strftime('%H:%M:%S'),
                "precio_c": self.precio_compra,
                "precio_v": r["precio"],
                "pnl": round(pnl, 2),
                "pct": round(pct, 2),
                "razon": razon
            })
            self.btc = 0
            self.usdt_invertido = 0
            self.precio_compra = 0
            self.stop_loss = 0
            self.take_profit = 0
            self.tiempo_entrada = 0
            return {"pnl": pnl, "pct": pct, "precio": r["precio"]}
        return None

    def verificar_tp_sl(self, precio_actual):
        if self.take_profit > 0 and precio_actual >= self.take_profit:
            return f"🎯 TP {self.take_profit:.0f}"
        if self.stop_loss > 0 and precio_actual <= self.stop_loss:
            return f"🛑 SL {self.stop_loss:.0f}"
        # Timeout: si pasó > 120s y la posición está plana (<0.1%)
        if self.tiempo_entrada and self.precio_compra > 0:
            pct = (precio_actual / self.precio_compra - 1)
            if time.time() - self.tiempo_entrada > 120 and abs(pct) < 0.001:
                return f"⏰ Timeout 2min"
        return None

    def linea_estado(self, precio_actual):
        flot = self.calcular_flotante(precio_actual)
        c = "🟢" if flot >= 0 else "🔴"
        if self.btc > 0:
            return f"{self.emoji} {self.nombre:12s} 💰{self.saldo_disponible:.0f} {c} Flot:{flot:+.3f} TP:{self.take_profit:.0f} SL:{self.stop_loss:.0f}"
        else:
            return f"{self.emoji} {self.nombre:12s} 💰{self.saldo_disponible:.0f} 🔴 Esperando..."


def crear_agentes(capital_por_agente=CAPITAL_POR_AGENTE):
    return [
        Agente("Toro", "🐂", capital_por_agente, "1:3", 0.40,
               solo_buy=True, categorias_requeridas=["Trend Following", "Breakout & Momentum"]),
        Agente("Range", "📊", capital_por_agente, "1:2", 0.40,
               solo_buy=False, categorias_requeridas=["Mean Reversion", "Micro-Scalping"]),
        Agente("Scalper", "⚡", capital_por_agente, "1:2", 0.30,
               solo_buy=False, categorias_requeridas=[], fuerza_tras_n_analisis=3),
        Agente("Conservador", "🐢", capital_por_agente, "1:2", 0.60,
               solo_buy=True, categorias_requeridas=["Trend Following"]),
    ]
