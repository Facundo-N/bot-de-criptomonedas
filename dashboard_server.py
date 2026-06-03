#!/usr/bin/env python3
"""
dashboard_server.py — Servidor del Dashboard v1
=================================================
Servidor Flask que expone el estado en tiempo real del bot
a través de una API REST + Server-Sent Events (SSE).

El bot (main_bot_live.py) escribe su estado en un dict compartido
mediante un módulo de estado global (bot_state.py).
El dashboard lee ese estado vía HTTP desde el navegador.

Puerto: 9090
"""

import json
import time
import threading
from datetime import datetime
from flask import Flask, Response, jsonify, send_from_directory
import os

# Importar el estado compartido (se puebla desde main_bot_live.py)
from bot_state import estado

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

app = Flask(__name__, static_folder=DASHBOARD_DIR, static_url_path="/static")

# ─── RUTAS ESTÁTICAS ──────────────────────────────────────────────

@app.route("/")
def index():
    """Sirve el dashboard HTML principal."""
    return send_from_directory(DASHBOARD_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    """Sirve style.css, app.js y cualquier otro asset desde /dashboard/
    Las rutas /api/* quedan excluidas porque Flask las resuelve primero.
    """
    # Evitar que esta ruta capture peticiones de API
    if filename.startswith("api/"):
        from flask import abort
        abort(404)
    return send_from_directory(DASHBOARD_DIR, filename)


# ─── API REST ─────────────────────────────────────────────────────

@app.route("/api/estado")
def api_estado():
    """
    Retorna el estado completo del bot como JSON.
    El dashboard hace polling a este endpoint cada 2 segundos.
    """
    return jsonify(estado.snapshot())


@app.route("/api/trades")
def api_trades():
    """Historial de trades de todos los agentes."""
    return jsonify(estado.get_trades())


@app.route("/api/precio_historial")
def api_precio_historial():
    """Últimos 200 precios para el mini-chart de precio."""
    return jsonify(estado.get_precio_historial())


# ─── SERVER-SENT EVENTS ───────────────────────────────────────────

@app.route("/api/stream")
def api_stream():
    """
    Stream SSE: envía actualizaciones al dashboard sin polling.
    El navegador se suscribe una vez y recibe eventos automáticamente.
    """
    def generar():
        ultimo_ciclo = -1
        while True:
            try:
                snap = estado.snapshot()
                ciclo_actual = snap.get("ciclo", 0)
                if ciclo_actual != ultimo_ciclo:
                    ultimo_ciclo = ciclo_actual
                    data = json.dumps(snap, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                time.sleep(1)
            except GeneratorExit:
                break
            except Exception:
                time.sleep(2)

    return Response(
        generar(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


# ─── ARRANQUE ─────────────────────────────────────────────────────

def iniciar_servidor(host="0.0.0.0", puerto=9090, debug=False):
    """Inicia el servidor Flask en un hilo separado."""
    def _run():
        app.run(host=host, port=puerto, debug=debug, use_reloader=False, threaded=True)

    t = threading.Thread(target=_run, daemon=True, name="DashboardServer")
    t.start()
    print(f"  🌐 Dashboard disponible en http://localhost:{puerto}")
    return t


if __name__ == "__main__":
    print("⚠️  Ejecutar a través de iniciar.bat o junto con main_bot_live.py")
    print("   Iniciando en modo demo (sin bot)...")
    app.run(host="0.0.0.0", port=9090, debug=True)
