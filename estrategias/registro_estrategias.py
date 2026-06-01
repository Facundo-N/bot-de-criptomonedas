#!/usr/bin/env python3
"""
Registro Maestro de Estrategias (50 en total)
----------------------------------------------
Catálogo centralizado de todas las estrategias disponibles.
Cada entrada contiene: nombre, archivo, categoría, fórmula, parámetros, estado.

ESTADOS:
  ✅ IMPLEMENTADA  → Código listo para usar
  ⏳ PENDIENTE     → Por implementar
  🔬 EN PRUEBA    → Implementada pero no validada en producción
"""

REGISTRO = [
    # ====================================================================
    # 1. SEGUIMIENTO DE TENDENCIA (Trend Following)
    # ====================================================================
    {
        "id": 1,
        "nombre": "SMA Crossover (20/50)",
        "archivo": "estrategia_medias.py",
        "categoria": "Trend Following",
        "formula": "SMA = Σ(P_i) / n",
        "parametros": "Rápida: 20, Lenta: 50",
        "timeframe": "1h - 4h",
        "estado": "✅ IMPLEMENTADA",
        "descripcion": "Compra cuando SMA 20 cruza arriba de SMA 50. Vende en cruce inverso."
    },
    {
        "id": 2,
        "nombre": "EMA Crossover (9/21)",
        "archivo": "estrategia_ema.py",
        "categoria": "Trend Following",
        "formula": "EMA = (P × k) + (EMA_ant × (1 - k)), k=2/(n+1)",
        "parametros": "Rápida: 9, Lenta: 21",
        "timeframe": "15min - 1h",
        "estado": "✅ IMPLEMENTADA",
        "descripcion": "Alta reactividad intradiaria. Compra en cruce alcista EMA 9 sobre EMA 21."
    },
    {
        "id": 3,
        "nombre": "MACD Crossover",
        "archivo": "estrategia_macd.py",
        "categoria": "Trend Following",
        "formula": "MACD = EMA(12) - EMA(26), Señal = EMA(9) del MACD",
        "parametros": "Rápida: 12, Lenta: 26, Señal: 9",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra cuando línea MACD cruza arriba de línea de señal. Preferiblemente bajo nivel cero."
    },
    {
        "id": 4,
        "nombre": "Golden Cross / Death Cross",
        "archivo": "estrategia_golden_death.py",
        "categoria": "Trend Following",
        "formula": "SMA(50) vs SMA(200)",
        "parametros": "Rápida: 50, Lenta: 200, Timeframe: 1D",
        "timeframe": "1d (diario)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Golden Cross → entrada macro Long. Death Cross → salida total o Short."
    },
    {
        "id": 5,
        "nombre": "TEMA (Triple EMA)",
        "archivo": "estrategia_tema.py",
        "categoria": "Trend Following",
        "formula": "TEMA = 3×EMA₁ - 3×EMA₂ + EMA₃",
        "parametros": "Período: 20",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Triple filtrado que elimina casi todo el lag. Compra cuando precio cierra sobre TEMA 20."
    },
    {
        "id": 6,
        "nombre": "Ichimoku Cloud Kumo Breakout",
        "archivo": "estrategia_ichimoku.py",
        "categoria": "Trend Following",
        "formula": "Sistema integral japonés con Kumo, Tenkan, Kijun, Chikou Span",
        "parametros": "Tenkan: 9, Kijun: 26, Senkou: 52, Chikou: 26",
        "timeframe": "1h - 1d",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Opera solo ruptura exterior de la nube. Compra si precio cierra sobre Kumo y Chikou arriba."
    },
    {
        "id": 7,
        "nombre": "Parabolic SAR Trend Riding",
        "archivo": "estrategia_parabolic_sar.py",
        "categoria": "Trend Following",
        "formula": "SAR_ant + AF × (EP - SAR_ant), AF acelera 0.02 → 0.20",
        "parametros": "AF inicial: 0.02, AF máximo: 0.20",
        "timeframe": "1h - 1d",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Trailing Stop algorítmico. Si puntos pasan bajo velas → Long."
    },
    {
        "id": 8,
        "nombre": "Donchian Channels Breakout",
        "archivo": "estrategia_donchian.py",
        "categoria": "Trend Following",
        "formula": "Sup = max(H,n), Inf = min(L,n), Media = (Sup+Inf)/2",
        "parametros": "Período: 20",
        "timeframe": "1h - 1d",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra cuando precio rompe canal superior. Stop Loss en banda inferior."
    },
    {
        "id": 9,
        "nombre": "SuperTrend Indicator",
        "archivo": "estrategia_supertrend.py",
        "categoria": "Trend Following",
        "formula": "Bandas = (H+L)/2 ± ATR × Multiplicador",
        "parametros": "ATR: 10, Multiplicador: 3",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra cuando línea cambia a verde bajo velas. Vende cuando cambia a rojo."
    },
    {
        "id": 10,
        "nombre": "Hull Moving Average (HMA) Directional",
        "archivo": "estrategia_hma.py",
        "categoria": "Trend Following",
        "formula": "HMA = WMA(2×WMA(n/2) - WMA(n), √n)",
        "parametros": "Período: 20",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra cuando HMA 20 cambia dirección de bajista a alcista."
    },
    # ====================================================================
    # 2. REVERSIÓN A LA MEDIA (Mean Reversion)
    # ====================================================================
    {
        "id": 11,
        "nombre": "Bollinger Bands Bounce",
        "archivo": "estrategia_bollinger.py",
        "categoria": "Mean Reversion",
        "formula": "BB_Sup = SMA(20)+2σ, BB_Inf = SMA(20)-2σ",
        "parametros": "Período: 20, Desviaciones: 2",
        "timeframe": "1h - 4h",
        "estado": "✅ IMPLEMENTADA",
        "descripcion": "Compra cuando precio toca banda inferior y rebota. Vende en toque de banda superior."
    },
    {
        "id": 12,
        "nombre": "RSI Oversold/Overbought",
        "archivo": "estrategia_rsi.py",
        "categoria": "Mean Reversion",
        "formula": "RSI = 100 - [100/(1 + EMA_ganancia/EMA_perdida)]",
        "parametros": "Período: 14, Sobrecompra: 70, Sobreventa: 30",
        "timeframe": "1h - 4h",
        "estado": "✅ IMPLEMENTADA",
        "descripcion": "Compra cuando RSI < 30 y cruza arriba. Vende cuando RSI > 70 y cruza abajo."
    },
    {
        "id": 13,
        "nombre": "Stochastic Oscillator Divergence",
        "archivo": "estrategia_stochastic.py",
        "categoria": "Mean Reversion",
        "formula": "%K = (C-min(L))/(max(H)-min(L))×100, %D = SMA(%K)",
        "parametros": "%K: 14, %D: 3, Suavizado: 3",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Busca divergencias. Si precio baja pero Stoch sube en <20 → Long."
    },
    {
        "id": 14,
        "nombre": "Z-Score Mean Reversion",
        "archivo": "estrategia_zscore.py",
        "categoria": "Mean Reversion",
        "formula": "Z = (Precio - SMA) / σ",
        "parametros": "Z extremo: ±2.5 a ±3.0, ventana: 20",
        "timeframe": "1h - 1d",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si Z-Score alcanza -2.5/-3.0, precio anormalmente alejado de la media → Long."
    },
    {
        "id": 15,
        "nombre": "Commodity Channel Index (CCI) Extremes",
        "archivo": "estrategia_cci.py",
        "categoria": "Mean Reversion",
        "formula": "CCI = (Precio - SMA(n)) / (0.015 × σ)",
        "parametros": "Período: 20, Extremo: ±200",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra cuando CCI rechaza -200 y sube. Vende cuando rechaza +200 y baja."
    },
    {
        "id": 16,
        "nombre": "Linear Regression Channel",
        "archivo": "estrategia_linear_reg.py",
        "categoria": "Mean Reversion",
        "formula": "Mínimos cuadrados: y = mx + b, bandas = ±σ máxima",
        "parametros": "Período: 50",
        "timeframe": "1h - 1d",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra en toque de banda inferior del canal con rechazo por volumen."
    },
    {
        "id": 17,
        "nombre": "Williams %R Reversion",
        "archivo": "estrategia_williams_r.py",
        "categoria": "Mean Reversion",
        "formula": "%R = (max(H)-C)/(max(H)-min(L)) × -100",
        "parametros": "Período: 14, Extremo: -80 a -100",
        "timeframe": "15min - 1h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra cuando %R toca -80 a -100 y muestra giro alcista inmediato."
    },
    {
        "id": 18,
        "nombre": "VWAP Mean Reversion",
        "archivo": "estrategia_vwap.py",
        "categoria": "Mean Reversion",
        "formula": "VWAP = Σ(P_i × V_i) / Σ(V_i)",
        "parametros": "Intradiario, desviación porcentual",
        "timeframe": "1min - 15min",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si precio se dispara/desploma alejándose del VWAP sin volumen → reversión."
    },
    {
        "id": 19,
        "nombre": "Relative Vigor Index (RVI) Reversion",
        "archivo": "estrategia_rvi.py",
        "categoria": "Mean Reversion",
        "formula": "RVI = (C-O)/(H-L), suavizado con SMA",
        "parametros": "Período: 10",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra cuando RVI cruza alcista en zona inferior coincidiendo con soporte."
    },
    {
        "id": 20,
        "nombre": "Envelopes Strategy",
        "archivo": "estrategia_envelopes.py",
        "categoria": "Mean Reversion",
        "formula": "Bandas = SMA(n) × (1 ± %/100)",
        "parametros": "SMA: 50, %: 2-5 según volatilidad",
        "timeframe": "1h - 1d",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra cuando precio sale de envolvente inferior esperando retorno a SMA 50."
    },
    # ====================================================================
    # 3. RUPTURAS E IMPULSO (Breakout & Momentum)
    # ====================================================================
    {
        "id": 21,
        "nombre": "Support/Resistance Breakout",
        "archivo": "estrategia_sr_breakout.py",
        "categoria": "Breakout & Momentum",
        "formula": "Máximos/mínimos locales con confirmación de cierre",
        "parametros": "Ventana de búsqueda: 20 velas",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra cuando precio quiebra resistencia con cierre de vela confirmado."
    },
    {
        "id": 22,
        "nombre": "Opening Range Breakout (ORB)",
        "archivo": "estrategia_orb.py",
        "categoria": "Breakout & Momentum",
        "formula": "Rango = Max(H, 1ra hora) - Min(L, 1ra hora)",
        "parametros": "Ventana: 1 hora tras apertura",
        "timeframe": "1min - 5min",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Buy Stop sobre máximo de 1ra hora. Sell Stop bajo mínimo."
    },
    {
        "id": 23,
        "nombre": "Volume-Weighted MACD",
        "archivo": "estrategia_vw_macd.py",
        "categoria": "Breakout & Momentum",
        "formula": "VWMACD = EMA_vw(12) - EMA_vw(26), ponderado por volumen",
        "parametros": "Rápida: 12, Lenta: 26, Señal: 9",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Solo toma señal de cruce si hay volumen sustancial respaldando."
    },
    {
        "id": 24,
        "nombre": "ADX Trend Strength Filtering",
        "archivo": "estrategia_adx.py",
        "categoria": "Breakout & Momentum",
        "formula": "ADX = 100 × EMA(|+DI - -DI| / (+DI + -DI))",
        "parametros": "Período: 14, Umbral: 25",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Filtro primario: solo opera si ADX > 25."
    },
    {
        "id": 25,
        "nombre": "Rate of Change (ROC) Acceleration",
        "archivo": "estrategia_roc.py",
        "categoria": "Breakout & Momentum",
        "formula": "ROC = (P_act - P_n_atras) / P_n_atras × 100",
        "parametros": "Período: 12",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Entra cuando curva ROC experimenta quiebre parabólico hacia arriba."
    },
    {
        "id": 26,
        "nombre": "Chaikin Money Flow (CMF) Breakout",
        "archivo": "estrategia_cmf.py",
        "categoria": "Breakout & Momentum",
        "formula": "CMF = Σ(V×(2C-H-L)/(H-L)) / Σ(V)",
        "parametros": "Período: 20, Umbral: > 0.15",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Valida ruptura de resistencia con CMF > 0.15 (acumulación institucional)."
    },
    {
        "id": 27,
        "nombre": "Inside Bar Breakout",
        "archivo": "estrategia_inside_bar.py",
        "categoria": "Breakout & Momentum",
        "formula": "Vela contenida dentro de vela anterior (Mother Bar)",
        "parametros": "N/A (patrón price action)",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Buy Stop y Sell Stop en extremos de Mother Bar. Se activa la rota primero."
    },
    {
        "id": 28,
        "nombre": "True Strength Index (TSI) Momentum",
        "archivo": "estrategia_tsi.py",
        "categoria": "Breakout & Momentum",
        "formula": "TSI = EMA(EMA(pc,s),s) / EMA(EMA(|pc|,s),s) × 100",
        "parametros": "Suavizado 1: 25, Suavizado 2: 13, Señal: 7",
        "timeframe": "4h - 1d",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Long cuando TSI cruza línea de señal hacia arriba en territorio positivo."
    },
    {
        "id": 29,
        "nombre": "Money Flow Index (MFI) Divergence",
        "archivo": "estrategia_mfi.py",
        "categoria": "Breakout & Momentum",
        "formula": "MFI = 100 - [100/(1 + Σ(V_pos)/Σ(V_neg))]",
        "parametros": "Período: 14",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si precio rompe máximo pero MFI baja → cancela compra y prepara venta."
    },
    {
        "id": 30,
        "nombre": "Keltner Channels Breakout",
        "archivo": "estrategia_keltner.py",
        "categoria": "Breakout & Momentum",
        "formula": "Central = EMA(20), Sup = EMA + ATR, Inf = EMA - ATR",
        "parametros": "EMA: 20, ATR: 10, Multiplicador: 2",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Cierres continuos sobre banda superior → impulso tendencial fuerte."
    },
    # ====================================================================
    # 4. ARBITRAJE (Arbitrage)
    # ====================================================================
    {
        "id": 31,
        "nombre": "Spatial Arbitrage",
        "archivo": "estrategia_spatial_arb.py",
        "categoria": "Arbitraje",
        "formula": "Spread = Precio_A - Precio_B",
        "parametros": "Múltiples exchanges (Binance, Coinbase, Kraken)",
        "timeframe": "Tiempo real (ws)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra donde está más barato, vende donde está más caro."
    },
    {
        "id": 32,
        "nombre": "Triangular Arbitrage",
        "archivo": "estrategia_triangular_arb.py",
        "categoria": "Arbitraje",
        "formula": "USDT→BTC→ETH→USDT, spread entre trayectorias",
        "parametros": "Pares: BTCUSDT, ETHBTC, ETHUSDT",
        "timeframe": "Tiempo real (ws)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Ciclo de 3 conversiones. Si resultado neto > inicial → arbitraje."
    },
    {
        "id": 33,
        "nombre": "Statistical Arbitrage (Pairs Trading)",
        "archivo": "estrategia_pairs_trading.py",
        "categoria": "Arbitraje",
        "formula": "Spread = P_A - β×P_B, Z-score del spread",
        "parametros": "Ventana de cointegración: 60 períodos",
        "timeframe": "1h - 1d",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Long infravalorado + Short sobrevalorado si spread > 2σ."
    },
    {
        "id": 34,
        "nombre": "Funding Rate Arbitrage",
        "archivo": "estrategia_funding_arb.py",
        "categoria": "Arbitraje",
        "formula": "Ganancia = Funding_Rate × Tamaño × Ciclos",
        "parametros": "Spot + Futuros perpetuos, delta-neutral",
        "timeframe": "Cada 8h (ciclo de funding)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra Spot + Short Futuros si funding positiva → cobra tasa pasivamente."
    },
    {
        "id": 35,
        "nombre": "Calendar Spread Arbitrage",
        "archivo": "estrategia_calendar_spread.py",
        "categoria": "Arbitraje",
        "formula": "Spread = Futuro_Junio - Futuro_Septiembre",
        "parametros": "2 contratos de futuros con distinto vencimiento",
        "timeframe": "1d - 1sem",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Long mes cercano + Short mes lejano si spread excede costo de carry."
    },
    # ====================================================================
    # 5. BASADAS EN VOLATILIDAD
    # ====================================================================
    {
        "id": 36,
        "nombre": "Bollinger Bands Squeeze",
        "archivo": "estrategia_bb_squeeze.py",
        "categoria": "Volatilidad",
        "formula": "Bandwidth = (BB_Sup - BB_Inf) / BB_Media",
        "parametros": "BB: 20/2σ, Umbral: percentil 5 de Bandwidth",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Alerta cuando Bandwidth cae a mínimo histórico. Opera la explosión."
    },
    {
        "id": 37,
        "nombre": "ATR Band Breakout",
        "archivo": "estrategia_atr_band.py",
        "categoria": "Volatilidad",
        "formula": "SL = 1.5×ATR, TP = 3×ATR",
        "parametros": "ATR: 14, SL: 1.5×, TP: 3×",
        "timeframe": "1h - 4h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si precio rompe banda a 2×ATR de la media → opera ruptura de volatilidad."
    },
    {
        "id": 38,
        "nombre": "Chande Momentum Oscillator (CMO)",
        "archivo": "estrategia_cmo.py",
        "categoria": "Volatilidad",
        "formula": "CMO = (Σ_ganancias - Σ_perdidas)/(Σ_ganancias + Σ_perdidas)×100",
        "parametros": "Período: 9, Límites: ±50",
        "timeframe": "15min - 1h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Extremadamente reactivo. Opera picos de pánico/euforia en temporalidades bajas."
    },
    {
        "id": 39,
        "nombre": "Historical Volatility Breakout",
        "archivo": "estrategia_hv_breakout.py",
        "categoria": "Volatilidad",
        "formula": "HV = σ_anualizada. Comparación HV_actual vs HV_histórica",
        "parametros": "Ventana: 100 días, Umbral: percentil 10",
        "timeframe": "1d - 1sem",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si HV anormalmente baja y hay pico de volumen → inicio ciclo institucional."
    },
    {
        "id": 40,
        "nombre": "Options Implied Volatility Arbitrage",
        "archivo": "estrategia_iv_arb.py",
        "categoria": "Volatilidad",
        "formula": "IV vs HV, Estrategias: Iron Condor, Straddle corto",
        "parametros": "Delta-neutral, vencimiento 30-45 días",
        "timeframe": "Semanal",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Vende opciones caras cuando IV >> HV. Requiere mercado de opciones."
    },
    # ====================================================================
    # 6. MICRO-SCALPING Y ALTA FRECUENCIA (HFT)
    # ====================================================================
    {
        "id": 41,
        "nombre": "Order Book Imbalance",
        "archivo": "estrategia_orderbook.py",
        "categoria": "Micro-Scalping",
        "formula": "Imbalance = (Vol_Bids - Vol_Asks) / (Vol_Bids + Vol_Asks)",
        "parametros": "Profundidad: 10 niveles",
        "timeframe": "Tiempo real (ws)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si Bids >> Asks → compra inmediata antes de que suba por absorción."
    },
    {
        "id": 42,
        "nombre": "Time and Sales Tape Reading",
        "archivo": "estrategia_tapes.py",
        "categoria": "Micro-Scalping",
        "formula": "Detección Block Trades: Volumen > percentil 95",
        "parametros": "Umbral de block trade: 5+ BTC",
        "timeframe": "Tiempo real (ws)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si detecta compras institucionales secuenciales → entra con la ballena."
    },
    {
        "id": 43,
        "nombre": "Grid Trading",
        "archivo": "estrategia_grid.py",
        "categoria": "Micro-Scalping",
        "formula": "Rejilla de órdenes límite: niveles equidistantes",
        "parametros": "Niveles: 10-20, Spread entre niveles: 0.5%",
        "timeframe": "Tiempo real (ws)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Órdenes de compra escalonadas bajo precio, ventas sobre precio."
    },
    {
        "id": 44,
        "nombre": "Martingale Grid",
        "archivo": "estrategia_martingale_grid.py",
        "categoria": "Micro-Scalping",
        "formula": "Tamaño_n = Tamaño_inicial × 2^(n-1)",
        "parametros": "Duplicación en cada nivel, Máximo 4 dobladas",
        "timeframe": "Tiempo real (ws)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "⚠️ ALTO RIESGO. Duplica posición si precio cae. Sale en primer rebote."
    },
    {
        "id": 45,
        "nombre": "Anti-Martingale Grid",
        "archivo": "estrategia_antimartingale.py",
        "categoria": "Micro-Scalping",
        "formula": "Tamaño_n = Tamaño_base × (1 + ganancia_acum/umbral)",
        "parametros": "Pyramiding en rachas ganadoras",
        "timeframe": "Tiempo real (ws)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Aumenta tamaño solo cuando está en ganancias. Piramidea tendencias."
    },
    {
        "id": 46,
        "nombre": "Spread Scalping (Market Making)",
        "archivo": "estrategia_spread_scalp.py",
        "categoria": "Micro-Scalping",
        "formula": "Ganancia = Ask - Bid (por unidad)",
        "parametros": "Colocado en punta de Bid y Ask simultáneamente",
        "timeframe": "Milisegundos",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Compra Bid, vende Ask. Captura el spread miles de veces al día."
    },
    {
        "id": 47,
        "nombre": "VWAP Micro-Scalping",
        "archivo": "estrategia_vwap_scalp.py",
        "categoria": "Micro-Scalping",
        "formula": "Desviación = Precio - VWAP",
        "parametros": "Timeframe: 1min, Umbral: 0.1% desviación",
        "timeframe": "1min",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si precio se separa abruptamente del VWAP → reversión rápida."
    },
    # ====================================================================
    # 7. DATOS EXTERNOS Y SENTIMIENTO (Alternative Data)
    # ====================================================================
    {
        "id": 48,
        "nombre": "Cumulative Volume Delta (CVD) Divergence",
        "archivo": "estrategia_cvd.py",
        "categoria": "Alternative Data",
        "formula": "CVD_acum = Σ(Vol_BuyMarket - Vol_SellMarket)",
        "parametros": "Delta acumulado por sesión",
        "timeframe": "Tiempo real (ws)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si precio baja pero CVD sube → ballenas absorbiendo → Long."
    },
    {
        "id": 49,
        "nombre": "Social Media Sentiment Analysis",
        "archivo": "estrategia_sentiment.py",
        "categoria": "Alternative Data",
        "formula": "NLP: Clasificación positivo/negativo/neutral de menciones",
        "parametros": "Fuentes: X/Twitter, Reddit, Discord. API de sentiment.",
        "timeframe": "15min - 1h",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si menciones positivas suben 400% en 30min → FOMO → compra."
    },
    {
        "id": 50,
        "nombre": "Whale Wallet Tracking",
        "archivo": "estrategia_whales.py",
        "categoria": "Alternative Data",
        "formula": "Monitoreo de direcciones públicas con alto balance",
        "parametros": "Umbral: transferencias > $10M, Etiquetado de wallets",
        "timeframe": "Tiempo real (ws)",
        "estado": "⏳ PENDIENTE",
        "descripcion": "Si ballena mueve fondos a Exchange → anticipa venta → Short."
    }
]


def listar_por_estado(estado: str = None) -> list:
    """Filtra estrategias por estado: 'IMPLEMENTADA', 'PENDIENTE', 'EN PRUEBA'."""
    if estado:
        return [e for e in REGISTRO if estado in e["estado"]]
    return REGISTRO


def listar_por_categoria(categoria: str) -> list:
    """Filtra estrategias por categoría."""
    return [e for e in REGISTRO if e["categoria"] == categoria]


def obtener_estrategia(id_estrategia: int) -> dict:
    """Busca una estrategia por su ID."""
    for e in REGISTRO:
        if e["id"] == id_estrategia:
            return e
    return None


def resumen() -> dict:
    """Devuelve un resumen estadístico del registro."""
    total = len(REGISTRO)
    implementadas = len(listar_por_estado("IMPLEMENTADA"))
    pendientes = len(listar_por_estado("PENDIENTE"))

    categorias = {}
    for e in REGISTRO:
        cat = e["categoria"]
        categorias[cat] = categorias.get(cat, 0) + 1

    return {
        "total": total,
        "implementadas": implementadas,
        "pendientes": pendientes,
        "categorias": categorias
    }


if __name__ == "__main__":
    print("=" * 60)
    print("  📋  REGISTRO MAESTRO DE ESTRATEGIAS (50)")
    print("=" * 60)

    r = resumen()
    print(f"\n📊  RESUMEN:")
    print(f"     Total          : {r['total']}")
    print(f"     Implementadas  : {r['implementadas']}")
    print(f"     Pendientes     : {r['pendientes']}")
    print(f"\n     Categorías:")
    for cat, count in sorted(r['categorias'].items(), key=lambda x: -x[1]):
        print(f"       {cat:30s} : {count}")

    print(f"\n📋  ESTRATEGIAS IMPLEMENTADAS ({r['implementadas']}):")
    for e in listar_por_estado("IMPLEMENTADA"):
        print(f"     #{e['id']:2d}  {e['nombre']:40s} → {e['archivo']}")

    print(f"\n📋  PRÓXIMAS A IMPLEMENTAR ({r['pendientes']}):")
    for e in listar_por_estado("PENDIENTE")[:5]:
        print(f"     #{e['id']:2d}  {e['nombre']:40s} → {e['categoria']}")
    print(f"     ... y {r['pendientes'] - 5} más.")