/**
 * app.js — Dashboard Bot Cripto
 * ================================
 * Se comunica con el servidor Flask via SSE (tiempo real) con
 * fallback a polling REST cada 3 segundos si SSE no está disponible.
 * Dibuja charts con la API Canvas 2D nativa (sin dependencias).
 */

'use strict';

// ── Estado local del dashboard ────────────────────────────────────
const state = {
  precioAnterior: null,
  pnlHistorial: [],
  precioHistorial: [],
  tradesCache: [],
  connected: false,
};

// ── Refs al DOM ───────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ── Colores (deben coincidir con CSS) ────────────────────────────
const C = {
  green:   '#00ff9f',
  red:     '#ff4d6d',
  blue:    '#58a6ff',
  dim:     '#6e7681',
  text:    '#c9d1d9',
  bg3:     '#21262d',
  border:  '#30363d',
};

// ─────────────────────────────────────────────────────────────────
// ACTUALIZACIÓN PRINCIPAL
// ─────────────────────────────────────────────────────────────────

function actualizarUI(data) {
  if (!data) return;

  // Status
  const online = data.activo === true;
  $('status-dot').className = 'status-dot ' + (online ? 'online' : 'offline');
  $('status-texto').textContent = online ? 'Bot activo' : 'Bot detenido';
  if (data.ultimo_update) {
    const t = new Date(data.ultimo_update);
    $('ultimo-update').textContent = 'Upd: ' + t.toLocaleTimeString('es');
  }

  // Precio
  const precio = data.precio_actual || 0;
  $('precio-header').textContent = precio > 0 ? formatPrecio(precio) : '—';
  if (state.precioAnterior !== null && precio > 0) {
    const diff = precio - state.precioAnterior;
    const pct  = ((diff / state.precioAnterior) * 100).toFixed(2);
    const el   = $('precio-cambio');
    el.textContent = (diff >= 0 ? '+' : '') + pct + '%';
    el.className   = 'precio-cambio ' + (diff > 0 ? 'positivo' : diff < 0 ? 'negativo' : 'neutral');
  }
  if (precio > 0) state.precioAnterior = precio;

  // KPIs
  const saldoAct = data.saldo_actual || 0;
  const saldoIni = data.saldo_inicial || 0;
  const pnl      = data.pnl_global;   // puede ser null
  const pnlPct   = data.pnl_pct;      // puede ser null

  $('saldo-actual').textContent = saldoAct > 0 ? formatUSDT(saldoAct) : '—';
  $('saldo-inicial').textContent = saldoIni > 0 ? 'Base: ' + formatUSDT(saldoIni) : 'Base: —';

  if (pnl !== null && pnl !== undefined) {
    setPnlEl($('pnl-global'), pnl, formatPnl(pnl));
    setPnlEl($('pnl-pct'), pnlPct, (pnlPct >= 0 ? '+' : '') + pnlPct.toFixed(2) + '%');
  } else {
    $('pnl-global').textContent = '—';
    $('pnl-global').className = 'kpi-value';
    $('pnl-pct').textContent = '—';
    $('pnl-pct').className = 'kpi-value';
  }

  // Régimen
  const reg = data.regimen || '—';
  const regEl = $('regimen');
  regEl.textContent = reg;
  regEl.className = 'kpi-value ' + regimenColor(reg);
  $('adx-val').textContent = 'ADX: ' + (data.adx || 0).toFixed(1);

  // RSI
  const rsi = data.rsi || 50;
  const rsiEl = $('rsi-val');
  rsiEl.textContent = rsi.toFixed(0);
  rsiEl.className   = 'kpi-value ' + rsiColor(rsi);
  $('vol-zscore').textContent = 'Volatilidad Z: ' + (data.volatilidad_zscore || 0).toFixed(2);

  // Ciclo
  $('ciclo-val').textContent = data.ciclo || '—';
  const totalTrades = (data.agentes || []).reduce((s, a) => s + (a.trades_count || 0), 0);
  $('trades-total').textContent = 'Trades: ' + totalTrades;

  // Agentes
  if (data.agentes && data.agentes.length > 0) {
    renderAgentes(data.agentes);
  }

  // Votos
  if (data.votos) {
    renderVotos(data.votos);
  }

  // P&L chart
  if (data.pnl_historial && data.pnl_historial.length > 1) {
    state.pnlHistorial = data.pnl_historial;
    dibujarChart('chart-pnl', state.pnlHistorial.map(d => d.pnl), {
      color: pnl >= 0 ? C.green : C.red,
      fill: true,
      label: 'P&L',
      yZero: true,
    });
  }

  // Log
  if (data.log_reciente) {
    renderLog(data.log_reciente);
  }
}

// ─────────────────────────────────────────────────────────────────
// AGENTES
// ─────────────────────────────────────────────────────────────────

function renderAgentes(agentes) {
  const grid = $('agentes-grid');
  grid.innerHTML = '';

  agentes.forEach(ag => {
    const enPos   = ag.en_posicion;
    const pnl     = ag.pnl_total || 0;
    const flot    = ag.flotante  || 0;
    const perdiendo = enPos && flot < 0;

    const card = document.createElement('div');
    card.className = 'agente-card' +
      (enPos ? ' en-posicion' : '') +
      (perdiendo ? ' perdiendo' : '');

    // Win rate barra
    const wr = ag.win_rate || 0;
    const barClass = wr >= 50 ? '' : ' negativo';

    card.innerHTML = `
      <div class="agente-header">
        <span class="agente-emoji">${ag.emoji}</span>
        <span class="agente-nombre">${ag.nombre}</span>
        <span class="agente-badge ${enPos ? 'badge-activo' : 'badge-espera'}">
          ${enPos ? 'ACTIVO' : 'ESPERA'}
        </span>
      </div>
      <div class="agente-stat">
        <span class="label">P&amp;L Total</span>
        <span class="val ${pnl >= 0 ? 'positivo' : 'negativo'}">${formatPnl(pnl)}</span>
      </div>
      <div class="agente-stat">
        <span class="label">Flotante</span>
        <span class="val ${flot >= 0 ? 'positivo' : 'negativo'}">${formatPnl(flot)}</span>
      </div>
      ${enPos ? `
      <div class="agente-stat">
        <span class="label">Entrada</span>
        <span class="val">${formatPrecio(ag.precio_compra)}</span>
      </div>
      <div class="agente-stat">
        <span class="label">TP / SL</span>
        <span class="val">${formatPrecioCorto(ag.take_profit)} / ${formatPrecioCorto(ag.stop_loss)}</span>
      </div>` : ''}
      <div class="agente-stat">
        <span class="label">Trades</span>
        <span class="val">${ag.trades_count}</span>
      </div>
      <div class="agente-stat">
        <span class="label">Win Rate</span>
        <span class="val ${wr >= 50 ? 'positivo' : 'negativo'}">${wr.toFixed(0)}%</span>
      </div>
      <div class="agente-stat">
        <span class="label">R:R / ML</span>
        <span class="val neutro">${ag.rr_ratio} / ${(ag.umbral_ml * 100).toFixed(0)}%</span>
      </div>
      <div class="progress-bar-wrap">
        <div class="progress-bar${barClass}" style="width:${Math.min(wr, 100)}%"></div>
      </div>
    `;
    grid.appendChild(card);
  });
}

// ─────────────────────────────────────────────────────────────────
// VOTOS
// ─────────────────────────────────────────────────────────────────

function renderVotos(votos) {
  const lista = $('votos-lista');
  if (!votos || votos.length === 0) {
    lista.innerHTML = '<p class="placeholder">Sin votos disponibles</p>';
    return;
  }

  lista.innerHTML = '';
  votos.forEach(v => {
    const accion = v.accion || 'HOLD';
    const div = document.createElement('div');
    div.className = 'voto-item ' + accion.toLowerCase();
    div.innerHTML = `
      <span class="voto-nombre">${v.nombre}</span>
      <span class="voto-categoria">${v.categoria}</span>
      <span class="voto-accion ${accion}">${accion}</span>
      <span class="voto-conf">${v.confianza || 0}%</span>
    `;
    lista.appendChild(div);
  });
}

// ─────────────────────────────────────────────────────────────────
// TRADES
// ─────────────────────────────────────────────────────────────────

function actualizarTrades(trades) {
  if (!trades || trades.length === 0) return;
  state.tradesCache = trades;

  const tbody = $('trades-body');
  tbody.innerHTML = '';

  trades.slice(0, 50).forEach(t => {
    const ganado = t.pnl >= 0;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${t.hora || '—'}</td>
      <td>${t.emoji || ''} ${t.agente || '—'}</td>
      <td>${formatPrecio(t.precio_c)}</td>
      <td>${formatPrecio(t.precio_v)}</td>
      <td class="${ganado ? 'ganado' : 'perdido'}">${formatPnl(t.pnl)}</td>
      <td class="${ganado ? 'ganado' : 'perdido'}">${(t.pct >= 0 ? '+' : '') + (t.pct || 0).toFixed(2)}%</td>
      <td>${t.razon || '—'}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ─────────────────────────────────────────────────────────────────
// LOG
// ─────────────────────────────────────────────────────────────────

function renderLog(lineas) {
  const container = $('log-container');
  container.innerHTML = '';
  (lineas || []).forEach(l => {
    const div = document.createElement('div');
    div.className = 'log-line ' + (l.nivel || 'info');
    div.innerHTML = `<span class="log-ts">${l.ts}</span><span class="log-msg">${l.msg}</span>`;
    container.appendChild(div);
  });
}

// ─────────────────────────────────────────────────────────────────
// CHARTS (Canvas 2D nativo — sin dependencias)
// ─────────────────────────────────────────────────────────────────

function dibujarChart(canvasId, valores, opts = {}) {
  const canvas = $(canvasId);
  if (!canvas || valores.length < 2) return;

  const ctx    = canvas.getContext('2d');
  const W      = canvas.offsetWidth  || 600;
  const H      = canvas.offsetHeight || 120;

  // Ajustar resolución para pantallas HiDPI
  const dpr = window.devicePixelRatio || 1;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, W, H);

  const pad   = { top: 10, right: 10, bottom: 20, left: 48 };
  const cW    = W - pad.left - pad.right;
  const cH    = H - pad.top  - pad.bottom;

  let minV = Math.min(...valores);
  let maxV = Math.max(...valores);

  if (opts.yZero) {
    if (minV > 0) minV = 0;
    if (maxV < 0) maxV = 0;
  }

  const rango = maxV - minV || 1;
  const color = opts.color || C.blue;

  // ── Línea base (0) ──────────────────────────────────────────
  if (opts.yZero) {
    const y0 = pad.top + cH - ((0 - minV) / rango) * cH;
    ctx.beginPath();
    ctx.strokeStyle = C.border;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.moveTo(pad.left, y0);
    ctx.lineTo(pad.left + cW, y0);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // ── Construir path ───────────────────────────────────────────
  const puntos = valores.map((v, i) => ({
    x: pad.left + (i / (valores.length - 1)) * cW,
    y: pad.top  + cH - ((v - minV) / rango) * cH,
  }));

  // ── Fill degradado ───────────────────────────────────────────
  if (opts.fill) {
    const y0 = opts.yZero
      ? pad.top + cH - ((0 - minV) / rango) * cH
      : pad.top + cH;

    const grad = ctx.createLinearGradient(0, pad.top, 0, H - pad.bottom);
    const hex  = color.replace('#', '');
    const r = parseInt(hex.slice(0,2),16);
    const g = parseInt(hex.slice(2,4),16);
    const b = parseInt(hex.slice(4,6),16);
    grad.addColorStop(0, `rgba(${r},${g},${b},.25)`);
    grad.addColorStop(1, `rgba(${r},${g},${b},.01)`);

    ctx.beginPath();
    ctx.moveTo(puntos[0].x, y0);
    puntos.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(puntos[puntos.length-1].x, y0);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
  }

  // ── Línea principal ──────────────────────────────────────────
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth   = 1.8;
  ctx.lineJoin    = 'round';
  puntos.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.stroke();

  // ── Punto final ──────────────────────────────────────────────
  const ult = puntos[puntos.length - 1];
  ctx.beginPath();
  ctx.arc(ult.x, ult.y, 3, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();

  // ── Eje Y (etiquetas min / max / 0) ─────────────────────────
  ctx.fillStyle   = C.dim;
  ctx.font        = `10px ${getComputedStyle(document.body).fontFamily}`;
  ctx.textAlign   = 'right';
  ctx.fillText(maxV.toFixed(0), pad.left - 4, pad.top + 4);
  ctx.fillText(minV.toFixed(0), pad.left - 4, H - pad.bottom);
  if (opts.yZero && minV < 0 && maxV > 0) {
    const y0 = pad.top + cH - ((0 - minV) / rango) * cH;
    ctx.fillText('0', pad.left - 4, y0 + 3);
  }
}

function dibujarChartPrecio(valores) {
  if (!valores || valores.length < 2) return;
  dibujarChart('chart-precio', valores.map(d => d.precio), {
    color: C.blue,
    fill: true,
    label: 'Precio BTC',
    yZero: false,
  });
}

// ─────────────────────────────────────────────────────────────────
// FORMATTERS
// ─────────────────────────────────────────────────────────────────

function formatPrecio(v) {
  if (!v || v === 0) return '—';
  return '$' + Number(v).toLocaleString('es-AR', { maximumFractionDigits: 0 });
}
function formatPrecioCorto(v) {
  if (!v || v === 0) return '—';
  return (v / 1000).toFixed(1) + 'k';
}
function formatUSDT(v) {
  if (!v || v === 0) return '—';
  return Number(v).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USDT';
}
function formatPnl(v) {
  const n = Number(v) || 0;
  return (n >= 0 ? '+' : '') + n.toFixed(2) + ' USDT';
}

function setPnlEl(el, valor, texto) {
  el.textContent = texto;
  el.className   = 'kpi-value ' + (valor > 0 ? 'positivo' : valor < 0 ? 'negativo' : '');
}

function regimenColor(reg) {
  if (!reg) return '';
  if (reg.includes('TENDENCIA') && !reg.includes('VOLÁTIL')) return 'positivo';
  if (reg.includes('VOLÁTIL'))   return 'negativo';
  if (reg.includes('RANGO'))     return 'neutro';
  return '';
}
function rsiColor(rsi) {
  if (rsi >= 70) return 'negativo';
  if (rsi <= 30) return 'positivo';
  return '';
}

// ─────────────────────────────────────────────────────────────────
// CONEXIÓN SSE + POLLING
// ─────────────────────────────────────────────────────────────────

function conectarSSE() {
  try {
    const es = new EventSource('/api/stream');

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        actualizarUI(data);
        state.connected = true;
      } catch (_) { /* ignorar */ }
    };

    es.onerror = () => {
      state.connected = false;
      $('status-dot').className = 'status-dot offline';
      $('status-texto').textContent = 'Reconectando...';
      // SSE se reconecta automáticamente, no hay que hacer nada
    };

  } catch (_) {
    // Navegador sin soporte SSE → fallback polling
    iniciarPolling();
  }
}

function iniciarPolling() {
  async function poll() {
    try {
      const r = await fetch('/api/estado');
      if (r.ok) {
        const data = await r.json();
        actualizarUI(data);
        state.connected = true;
      }
    } catch (_) {
      state.connected = false;
    }
  }
  poll();
  setInterval(poll, 3000);
}

// Trades se actualizan cada 5 segundos (tabla separada)
async function actualizarTradesAPI() {
  try {
    const r = await fetch('/api/trades');
    if (r.ok) {
      const data = await r.json();
      actualizarTrades(data);
    }
  } catch (_) { /* silencio */ }
}

// Precio historial cada 10 segundos
async function actualizarPrecioHistorial() {
  try {
    const r = await fetch('/api/precio_historial');
    if (r.ok) {
      const data = await r.json();
      if (data && data.length > 1) {
        state.precioHistorial = data;
        dibujarChartPrecio(data);
      }
    }
  } catch (_) { /* silencio */ }
}

// Redibujar charts al redimensionar ventana
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (state.pnlHistorial.length > 1) {
      const pnl = state.pnlHistorial.map(d => d.pnl);
      const ultimo = pnl[pnl.length - 1];
      dibujarChart('chart-pnl', pnl, {
        color: ultimo >= 0 ? C.green : C.red,
        fill: true,
        yZero: true,
      });
    }
    if (state.precioHistorial.length > 1) {
      dibujarChartPrecio(state.precioHistorial);
    }
  }, 200);
});

// ─────────────────────────────────────────────────────────────────
// ARRANQUE
// ─────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  conectarSSE();
  setInterval(actualizarTradesAPI, 5000);
  setInterval(actualizarPrecioHistorial, 10000);
  actualizarTradesAPI();
  actualizarPrecioHistorial();
});
