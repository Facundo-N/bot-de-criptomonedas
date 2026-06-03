#!/usr/bin/env python3
"""
bot_state.py — Estado Global Compartido
=========================================
Módulo singleton que actúa como bus de datos entre el bot
(main_bot_live.py) y el servidor del dashboard (dashboard_server.py).

Ambos módulos importan 'estado' desde aquí. El bot escribe,
el dashboard lee. Thread-safe mediante threading.Lock.
"""

import threading
from datetime import datetime
from collections import deque


class EstadoBot:
    def __init__(self):
        self._lock = threading.Lock()

        # ── Estado general ──────────────────────────────────────
        self.activo = False
        self.ciclo = 0
        self.inicio = datetime.now().isoformat()
        self.ultimo_update = None

        # ── Mercado ─────────────────────────────────────────────
        self.precio_actual = 0.0
        self.regimen = "NEUTRAL"
        self.adx = 0.0
        self.volatilidad_zscore = 0.0
        self.rsi = 50.0
        self.saldo_inicial = 0.0
        self.saldo_actual = 0.0

        # ── Agentes (lista de dicts) ─────────────────────────────
        # Cada agente: { nombre, emoji, btc, precio_compra, pnl_total,
        #                flotante, stop_loss, take_profit, trades_count,
        #                win_rate, estado, capital }
        self.agentes = []

        # ── Votos de estrategias ─────────────────────────────────
        # Cada voto: { nombre, accion, confianza, categoria }
        self.votos = []

        # ── Historial de trades ──────────────────────────────────
        # Cada trade: { hora, agente, emoji, precio_c, precio_v,
        #               pnl, pct, razon }
        self._trades = deque(maxlen=200)

        # ── Historial de precios para el chart ──────────────────
        self._precio_historial = deque(maxlen=200)

        # ── P&L acumulado por ciclo (para sparkline) ─────────────
        self._pnl_historial = deque(maxlen=200)

        # ── Log de eventos recientes ─────────────────────────────
        self._log = deque(maxlen=50)

    # ─── ESCRITURA (bot → estado) ──────────────────────────────────

    def actualizar_mercado(self, precio, regimen, adx, vol_z, rsi, saldo_inicial, saldo_actual, ciclo):
        with self._lock:
            self.precio_actual = precio
            self.regimen = regimen
            self.adx = adx
            self.volatilidad_zscore = vol_z
            self.rsi = rsi
            self.saldo_inicial = saldo_inicial
            self.saldo_actual = saldo_actual
            self.ciclo = ciclo
            self.activo = True
            self.ultimo_update = datetime.now().isoformat()
            self._precio_historial.append({
                "ts": self.ultimo_update,
                "precio": precio
            })
            pnl_total = saldo_actual - saldo_inicial
            self._pnl_historial.append({
                "ts": self.ultimo_update,
                "pnl": round(pnl_total, 2)
            })

    def actualizar_agentes(self, lista_agentes):
        """
        lista_agentes: lista de objetos Agente del bot.
        Serializa lo que necesita el dashboard.
        """
        with self._lock:
            self.agentes = []
            for ag in lista_agentes:
                trades = getattr(ag, "trades", [])
                wins = len([t for t in trades if t.get("pnl", 0) > 0])
                wr = (wins / len(trades) * 100) if trades else 0

                en_posicion = getattr(ag, "btc", 0) > 0
                self.agentes.append({
                    "nombre": ag.nombre,
                    "emoji": ag.emoji,
                    "btc": round(getattr(ag, "btc", 0), 6),
                    "precio_compra": round(getattr(ag, "precio_compra", 0), 2),
                    "pnl_total": round(getattr(ag, "pnl_total", 0), 2),
                    "flotante": round(getattr(ag, "ultimo_flotante", 0) or 0, 2),
                    "stop_loss": round(getattr(ag, "stop_loss", 0), 2),
                    "take_profit": round(getattr(ag, "take_profit", 0), 2),
                    "trades_count": len(trades),
                    "win_rate": round(wr, 1),
                    "en_posicion": en_posicion,
                    "capital": round(getattr(ag, "capital", 0), 2),
                    "rr_ratio": getattr(ag, "rr_ratio", "1:2"),
                    "umbral_ml": getattr(ag, "umbral_ml", 0.5),
                    "analisis_sin_operar": getattr(ag, "analisis_sin_operar", 0),
                })

    def actualizar_votos(self, votos):
        with self._lock:
            self.votos = [
                {
                    "nombre": v.get("nombre", ""),
                    "accion": v.get("accion", "HOLD"),
                    "confianza": v.get("confianza", 0),
                    "categoria": v.get("categoria", ""),
                    "fundamento": v.get("fundamento", ""),
                }
                for v in (votos or [])
            ]

    def registrar_trade(self, agente_nombre, agente_emoji, trade):
        """Registra un trade completado en el historial global."""
        with self._lock:
            self._trades.appendleft({
                "hora": trade.get("hora", ""),
                "agente": agente_nombre,
                "emoji": agente_emoji,
                "precio_c": trade.get("precio_c", 0),
                "precio_v": trade.get("precio_v", 0),
                "pnl": round(trade.get("pnl", 0), 2),
                "pct": round(trade.get("pct", 0), 2),
                "razon": trade.get("razon", ""),
            })

    def log(self, mensaje, nivel="info"):
        """Agrega una línea al log de eventos."""
        with self._lock:
            self._log.appendleft({
                "ts": datetime.now().strftime("%H:%M:%S"),
                "msg": mensaje,
                "nivel": nivel,
            })

    def marcar_inactivo(self):
        with self._lock:
            self.activo = False

    # ─── LECTURA (dashboard → estado) ──────────────────────────────

    def snapshot(self) -> dict:
        """Retorna una copia completa del estado para el dashboard."""
        with self._lock:
            # Solo calcular P&L si ya hubo al menos un ciclo completo
            # (saldo_actual se puebla en actualizar_mercado)
            saldo_base = self.saldo_inicial if self.saldo_inicial > 0 else None
            saldo_act  = self.saldo_actual  if self.saldo_actual  > 0 else None

            if saldo_base and saldo_act:
                pnl_global = round(saldo_act - saldo_base, 2)
                pnl_pct    = round((pnl_global / saldo_base) * 100, 2)
            else:
                pnl_global = None
                pnl_pct    = None

            return {
                "activo": self.activo,
                "ciclo": self.ciclo,
                "inicio": self.inicio,
                "ultimo_update": self.ultimo_update,
                "precio_actual": self.precio_actual,
                "regimen": self.regimen,
                "adx": self.adx,
                "volatilidad_zscore": self.volatilidad_zscore,
                "rsi": self.rsi,
                "saldo_inicial": self.saldo_inicial,
                "saldo_actual": self.saldo_actual,
                "pnl_global": pnl_global,
                "pnl_pct":    pnl_pct,
                "agentes": list(self.agentes),
                "votos": list(self.votos),
                "log_reciente": list(self._log)[:10],
                "pnl_historial": list(self._pnl_historial)[-50:],
            }

    def get_trades(self) -> list:
        with self._lock:
            return list(self._trades)

    def get_precio_historial(self) -> list:
        with self._lock:
            return list(self._precio_historial)


# Instancia singleton global
estado = EstadoBot()
