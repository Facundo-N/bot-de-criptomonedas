#!/usr/bin/env python3
"""
Demo rápida: muestra cómo el Oráculo decide con Puntaje Neto Ponderado.
Umbrales: ±0.05 (ultra-reactivo) + bias de régimen.
"""
from capa3_oraculo import consolidar_votos

print("=" * 55)
print("  🧪  DEMO: ORÁCULO v4 — Puntaje Neto Ponderado")
print("  ⚡  Umbral: ±0.05 | Bias de régimen: ON")
print("=" * 55)

# Situación actual del mercado: NEUTRAL (ADX=24.3)
print("\n📊 SITUACIÓN HOY (NEUTRAL, sin dirección):")
votos_hoy = [
    {"nombre": "SMA Crossover",   "accion": "BUY",  "confianza": 50, "categoria": "Trend Following"},
    {"nombre": "EMA Crossover",   "accion": "SELL", "confianza": 50, "categoria": "Trend Following"},
    {"nombre": "RSI 14",          "accion": "HOLD", "confianza": 30, "categoria": "Mean Reversion"},
    {"nombre": "Bollinger Bands", "accion": "HOLD", "confianza": 25, "categoria": "Mean Reversion"},
    {"nombre": "ADX Trend Filter","accion": "SELL", "confianza": 71, "categoria": "Breakout & Momentum"},
    {"nombre": "SuperTrend",      "accion": "BUY",  "confianza": 60, "categoria": "Trend Following"},
]
d = consolidar_votos(votos_hoy, "NEUTRAL")
for v in d["votos"]:
    print(f"  {v['nombre']:25s} → {v['accion']:5s}  val:{v['valor']:+1.0f}  conf:{v['confianza']}%  peso:{v['peso']:.1f}")
print(f"  {'─'*50}")
print(f"  Puntaje Neto: {d['puntaje_neto']:+.4f} | {d['accion']} | Conf: {d['confianza']}%")

# Escenario ALCISTA
print("\n📈 ESCENARIO ALCISTA (4 BUY + 1 HOLD + 1 SELL en TENDENCIA):")
votos_bull = [
    {"nombre": "SMA Crossover",   "accion": "BUY",  "confianza": 60, "categoria": "Trend Following"},
    {"nombre": "EMA Crossover",   "accion": "BUY",  "confianza": 65, "categoria": "Trend Following"},
    {"nombre": "RSI 14",          "accion": "HOLD", "confianza": 30, "categoria": "Mean Reversion"},
    {"nombre": "Bollinger Bands", "accion": "BUY",  "confianza": 55, "categoria": "Mean Reversion"},
    {"nombre": "ADX Trend Filter","accion": "SELL", "confianza": 71, "categoria": "Breakout & Momentum"},
    {"nombre": "SuperTrend",      "accion": "BUY",  "confianza": 70, "categoria": "Trend Following"},
]
d2 = consolidar_votos(votos_bull, "TENDENCIA")
for v in d2["votos"]:
    print(f"  {v['nombre']:25s} → {v['accion']:5s}  val:{v['valor']:+1.0f}  conf:{v['confianza']}%  peso:{v['peso']:.1f}")
print(f"  {'─'*50}")
print(f"  Puntaje Neto: {d2['puntaje_neto']:+.4f} | {d2['accion']} | Conf: {d2['confianza']}%")

# Escenario BAJISTA
print("\n📉 ESCENARIO BAJISTA (5 SELL + 1 BUY en TENDENCIA):")
votos_bear = [
    {"nombre": "SMA Crossover",   "accion": "SELL", "confianza": 55, "categoria": "Trend Following"},
    {"nombre": "EMA Crossover",   "accion": "SELL", "confianza": 60, "categoria": "Trend Following"},
    {"nombre": "RSI 14",          "accion": "SELL", "confianza": 70, "categoria": "Mean Reversion"},
    {"nombre": "Bollinger Bands", "accion": "SELL", "confianza": 65, "categoria": "Mean Reversion"},
    {"nombre": "ADX Trend Filter","accion": "SELL", "confianza": 80, "categoria": "Breakout & Momentum"},
    {"nombre": "SuperTrend",      "accion": "BUY",  "confianza": 60, "categoria": "Trend Following"},
]
d3 = consolidar_votos(votos_bear, "TENDENCIA")
for v in d3["votos"]:
    print(f"  {v['nombre']:25s} → {v['accion']:5s}  val:{v['valor']:+1.0f}  conf:{v['confianza']}%  peso:{v['peso']:.1f}")
print(f"  {'─'*50}")
print(f"  Puntaje Neto: {d3['puntaje_neto']:+.4f} | {d3['accion']} | Conf: {d3['confianza']}%")

print("\n" + "=" * 55)
print("  ✅  RESUMEN")
print(f"  Umbral actual: ±0.05 (ultra-reactivo)")
print(f"  Hoy (ADX=24.3, lateral): {d['accion']} ({d['puntaje_neto']:+.3f})")
print(f"  En tendencia alcista  : {d2['accion']} ({d2['puntaje_neto']:+.3f})")
print(f"  En tendencia bajista  : {d3['accion']} ({d3['puntaje_neto']:+.3f})")
print("=" * 55)