# 🤖 Bot de Trading Algorítmico — Binance Testnet

> Pipeline **educativo y experimental** de trading algorítmico en Python.
> ⚠️ Solo funciona en **Testnet** (dinero ficticio). No usar con dinero real.

---

## ✨ ¿Qué incluye?

| Módulo | Descripción |
|---|---|
| 📊 Estrategias | SMA, EMA, RSI, Bollinger Bands, ADX, SuperTrend |
| 🔮 Oráculo | Votación ponderada + clasificador Random Forest |
| 📉 Gestión de riesgo | Stop-Loss 4%, Take-Profit y grilla DCA |
| 🧪 Backtesting | Simulación histórica con datos reales de Binance |
| 🤖 Ejecución | Órdenes MARKET en Binance Testnet con P&L en vivo |

---

## 📋 Índice

- [¿Qué es este bot?](#¿qué-es-este-bot)
- [Funcionamiento Real ("Las Capas")](#funcionamiento-real-las-capas)
- [¿Qué es el Oráculo?](#¿qué-es-el-oráculo)
- [Contras, Limitaciones y Aspectos No Avanzados](#contras-limitaciones-y-aspectos-no-avanzados-)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Instalación y Configuración](#instalación-y-configuración)
- [Guía de Uso e Instancias de Ejecución](#guía-de-uso-e-instancias-de-ejecución)
- [Cómo agregar una nueva estrategia](#cómo-agregar-una-nueva-estrategia)
- [Fórmulas y Lógica interna](#fórmulas-y-lógica-interna)

---

## ¿Qué es este bot?

Este proyecto es una maqueta de software en Python para automatizar decisiones de trading a través de un flujo estructurado secuencialmente. 

El bot simula de manera secuencial (no asincrónica) los siguientes pasos:
1. Descarga datos de mercado públicos (velas de BTCUSDT) desde la API de Binance Spot.
2. Analiza la fuerza y dirección de la tendencia actual a través de un detector de régimen estático.
3. Solicita votos de compra/venta a diferentes estrategias técnicas (SMA, EMA, RSI, Bollinger, ADX, SuperTrend).
4. Consolida las señales mediante un **Puntaje Neto Ponderado** o un modelo de **Machine Learning** de clasificación.
5. Aplica reglas estáticas de gestión de riesgos para calcular precios de Stop-Loss y Take-Profit.
6. Genera niveles matemáticos de reentrada (Grid DCA) en caso de que el precio se mueva en contra.
7. Ejecuta y hace seguimiento en vivo a posiciones utilizando una cuenta de Binance Testnet.

---

## Funcionamiento Real ("Las Capas")

A pesar de que el código original utiliza términos pomposos como "arquitectura de capas" o "ojos, cerebro y oráculo", el funcionamiento real del software se basa en un flujo de ejecución de scripts tradicionales en Python estructurado en módulos secuenciales:

```
            ┌──────────────────────────────────────────────┐
            │ CAPA 0 y 1: Ingesta de Datos (REST Polling)  │
            │  Valida conexión API y descarga velas 1h/5m  │
            └──────────────────────┬───────────────────────┘
                                   ▼
            ┌──────────────────────────────────────────────┐
            │    CAPA 2: Detección de Régimen y Votos      │
            │   - ADX y Z-Score estáticos para el régimen  │
            │   - 6 estrategias técnicas emiten un voto    │
            └──────────────────────┬───────────────────────┘
                                   ▼
            ┌──────────────────────────────────────────────┐
            │          CAPA 3: Consolidación / Oráculo     │
            │  Votación ponderada manual O predicción de  │
            │  probabilidad mediante Random Forest         │
            └──────────────────────┬───────────────────────┘
                                   ▼
            ┌──────────────────────────────────────────────┐
            │      CAPA 4 y 4.5: Gestión de Riesgo y DCA   │
            │   - Divide el capital en 3 sub-operaciones   │
            │   - Calcula SL al 4% y grilla NumPy DCA      │
            └──────────────────────┬───────────────────────┘
                                   ▼
            ┌──────────────────────────────────────────────┐
            │          CAPA 5: Ejecución / Monitoreo       │
            │  Envío de orden MARKET y loop local de P&L   │
            └──────────────────────────────────────────────┘
```

*   **Capa 0 (Prueba de Vida):** Simple script que consume los endpoints privados de la cuenta para validar las credenciales del usuario y recuperar los balances en USDT y BTC.
*   **Capa 1 (Ingesta de velas):** Realiza peticiones REST directas a los endpoints públicos de Binance para generar un `DataFrame` de Pandas con velas históricas.
*   **Capa 2 (Detector de Régimen):** Utiliza umbrales manuales sobre el valor del indicador ADX y un Z-Score del Average True Range (ATR) para clasificar el mercado en Tendencia, Rango o Volátil.
*   **Capa 2 (Estrategias / Cerebros):** Calcula simultáneamente indicadores matemáticos básicos en memoria sobre el `DataFrame`. Cada estrategia retorna una acción (`BUY`/`SELL`/`HOLD`), una confianza estimada (de 0 a 100) y su fundamento teórico.
*   **Capa 3 (Oráculo / Consolidación):** Puede funcionar con un modelo matemático lineal ponderado por pesos de categorías de mercado, o bien, cargando un modelo de clasificación preentrenado con `scikit-learn` (`RandomForestClassifier`) que evalúa el vector de características y predice una probabilidad de éxito.
*   **Capa 4 (Gestor de Riesgo):** Verifica que el saldo de la cuenta sea suficiente para la transacción básica (dividiendo el saldo disponible rígidamente en 3 partes) y calcula niveles estáticos de Stop-Loss a partir del precio de entrada.
*   **Capa 4.5 (Grid DCA):** Genera una grilla matemática con NumPy que define a qué precios el bot colocará órdenes límite de compra adicionales si el precio sigue cayendo, con el objetivo de promediar el precio de entrada a la baja.
*   **Capa 5 (Ejecutor en Testnet):** Ejecuta la orden en tiempo de ejecución a través de llamadas sincrónicas de Binance Testnet, rastrea el balance y entra en un bucle cerrado monitoreando el Profit & Loss (P&L) latente hasta que la posición se cierra por Stop-Loss, Take-Profit o señal del Oráculo.

---

## 🔮 ¿Qué es el Oráculo?

En este proyecto, el **Oráculo** (implementado en `capa3_oraculo.py`) es el módulo de toma de decisiones centralizado. Su función es actuar como un consolidador o "juez" que recibe las señales individuales de múltiples estrategias independientes (Capa 2) y las procesa para dar un veredicto definitivo de acción (`BUY`, `SELL` o `HOLD`).

El Oráculo tiene dos modos de operación programados:

1. **Modo Lineal Ponderado (Por Defecto)**:
   * Consiste en una fórmula matemática tradicional. Cada estrategia tiene asignada una "confianza" (retornada dinámicamente) y un "peso" fijo asignado al agente de trading.
   * El oráculo calcula una suma ponderada de los votos de todas las estrategias activas.
   * Si la puntuación final supera un umbral positivo (ej. $+0.20$), se genera una señal de compra. Si cae por debajo de un umbral negativo (ej. $-0.20$), se genera una de venta.

2. **Modo Machine Learning (Clasificador Random Forest)**:
   * Al entrenar el bot mediante `entrenar_oraculo_ml.py`, se genera un archivo binario `modelo_oraculo_rf.pkl` que contiene un modelo de bosque aleatorio entrenado en `scikit-learn`.
   * En este modo, el Oráculo no suma los votos manualmente. En su lugar, toma un **vector de características (features)** que incluye:
     * La acción recomendada por cada una de las 6 estrategias activas.
     * La confianza de cada una de esas recomendaciones.
     * Datos macro del mercado actual: el régimen de mercado detectado, el valor absoluto del ADX, el Z-Score de volatilidad, la distancia porcentual del precio a la EMA y el RSI de 14 períodos.
   * El modelo de Machine Learning predice de forma probabilística si abrir una operación en este preciso instante tiene una alta probabilidad de éxito (definida como una subida de precio del 3% en las siguientes 12 velas). Si la probabilidad supera el umbral (por defecto $55\%$), el Oráculo emite una señal de compra.

---

## Contras, Limitaciones y Aspectos No Avanzados (¡Bajándole los humos!)

Para mantener una postura técnica realista y honesta sobre el código, es crucial entender que **este bot no es un software avanzado ni profesional**. A continuación se exponen las principales limitaciones y contras del proyecto:

1.  **Dependencia de Indicadores Clásicos con Retraso (*Lag*):**
    Las estrategias se basan en medias móviles (SMA, EMA), RSI, Bandas de Bollinger y ADX. Estos indicadores calculan fórmulas sobre datos históricos cerrados. Por diseño, tienen un retraso inherente muy alto y tienden a generar señales falsas constantes ("whipsaws") cuando el mercado cambia repentinamente de tendencia o cuando entra en un comportamiento ruidoso/lateralizado.
2.  **Modelo de Machine Learning Ultra-Simplista (Random Forest):**
    El entrenamiento del modelo (`entrenar_oraculo_ml.py`) carece de rigurosidad profesional:
    *   **Generación artificial de etiquetas:** El etiquetado asume un éxito (`label = 1`) si el precio sube 3% en las próximas 12 velas o simplemente cierra en positivo en el período posterior. No tiene en cuenta la micro-volatilidad intra-vela ni el costo de comisiones complejas.
    *   **Sobreajuste (Overfitting) por balanceo rudimentario:** El balanceo de datos de entrenamiento se realiza mediante un método SMOTE manual rudimentario, que simplemente **duplica los índices** de la clase minoritaria en memoria. Esto infla artificialmente la métrica de precisión (*accuracy*) y produce sobreajuste severo en entornos de validación real.
    *   **Variables de entrada muy acopladas:** El vector de características son las propias señales crudas y confianzas de los indicadores de lag previos. El modelo simplemente aprende a replicar combinaciones lógicas de indicadores.
3.  **Arquitectura Sincrónica y Bloqueante (Sin Concurrencia de Eventos):**
    Un bot de trading profesional opera mediante programación asincrónica (`asyncio` / WebSockets) con streams en tiempo real que reaccionan a eventos en milisegundos. Este proyecto realiza consultas mediante *polling* (peticiones periódicas por HTTP en bucles sincrónicos bloqueantes). Esto produce una latencia masiva y hace imposible reaccionar a tiempo a oscilaciones bruscas del libro de órdenes.
4.  **Moneda Única y Falta de Rotación Dinámica (Single-Asset):**
    La base del código está cableada y optimizada para operar exclusivamente con un par en paralelo (usando `BTCUSDT`). No cuenta con soporte nativo para evaluar dinámicamente decenas de tokens en paralelo, optimizar el uso de colas distribuidas ni balancear una cartera de activos.
5.  **Backtesting Sumamente Rudimentario:**
    El script `backtest.py` implementa una simulación vectorizada simplista. Carece de:
    *   Modelado realista de tarifas dinámicas de la red y tarifas de financiamiento (Funding rates).
    *   Simulación de deslizamiento real del libro de órdenes (*slippage*): asume ejecuciones completas al precio de cierre exacto de la vela.
    *   Problemas de conexión y reconexión: en el backtest la red nunca falla, mientras que en producción la API puede fallar o tardar segundos en responder.
6.  **Uso Exclusivo en Testnet:**
    El código carece de manejo avanzado de excepciones para rate-limiting (Binance penaliza severamente el abuso de solicitudes y órdenes repetitivas), carece de lógica de reconexión con retraso exponencial (exponential backoff) para fallas de red prolongadas, y no administra el margen de seguridad para evitar liquidaciones si el saldo se congela.
7.  **Operación Forzada Antinatural (Demo Mode):**
    El loop en vivo (`main_bot_live.py`) incluye una compra forzada periódica en caso de inactividad (cada 3 ciclos sin señal) con la única intención de demostrar que el pipeline de órdenes "funciona". En producción real, este comportamiento consumiría comisiones de forma irracional y generaría pérdidas sistémicas inevitables.

---

## Estructura del Proyecto

### 📁 Archivos en la Raíz

| Archivo | Rol Conceptual | Descripción Técnica |
|---------|:--------------:|---------------------|
| `api key.txt` | Configuración | Almacena la API Key y Secret Key para Binance Testnet. |
| `capa0_prueba_de_vida.py` | Entrada | Valida saldo inicial de USDT y BTC, y comprueba conectividad con los endpoints privados de la API. |
| `capa1_ingesta_datos.py` | Ingesta | Descarga velas de Binance mediante API REST. |
| `capa2_regimen_detector.py` | Procesamiento | Calcula el régimen del mercado clasificando el estado usando ADX y Z-Score de volatilidad. |
| `capa3_oraculo.py` | Decisión | Motor de oráculo. Carga opcionalmente el modelo RF y consolida los votos en una decisión final. |
| `capa4_gestor_riesgo.py` | Riesgo | Estima el tamaño estático de la posición y define precios de Stop-Loss y Take-Profit. |
| `capa4_5_grid_dca.py` | Recuperación | Calcula y expone una grilla estática de compras escalonadas usando matrices NumPy vectorizadas. |
| `capa5_ejecutor.py` | Ejecución | Realiza órdenes de compra y venta sincrónicas, y monitorea localmente la P&L. |
| `main_bot.py` | Pipeline | Demostración simple y secuencial de 3 ciclos de evaluación básica del bot de trading. |
| `main_bot_live.py` | Loop Principal | **Bucle infinito** con ejecución real en Binance Testnet, rastreo de posiciones y cálculo continuo de P&L. |
| `demo_bucle_acelerado.py` | Simulación | Ejecuta el loop del bot pero simulando ciclos de tiempo acelerados para fines ilustrativos. |
| `demo_forzada.py` | Prueba | Compra 0.001 BTC inmediatamente, espera 5 segundos, realiza la venta y expone el P&L final. |
| `demo_oraculo.py` | Prueba | Evalúa el oráculo usando datos estáticos y muestra la consolidación de señales. |
| `entrenar_oraculo_ml.py` | Machine Learning | Descarga velas, genera features/labels artificiales y entrena un modelo Random Forest (`modelo_oraculo_rf.pkl`). |
| `backtest.py` | Simulación | Ejecuta el bot de forma histórica sobre datos descargados de velas para reportar win rate y métricas globales. |
| `agentes.py` | Modularidad | Define la clase `Agente` con diferentes configuraciones de perfiles de riesgo y ponderaciones de estrategias. |
| `modelo_oraculo_rf.pkl` | Datos binarios | Archivo serializado con el modelo clasificador Random Forest y el normalizador de variables. |

### 📁 Directorio `estrategias/`

Contiene el código fuente que extrae las lógicas matemáticas para proponer señales individuales:

| Archivo | Estrategia Técnica | Descripción y Parámetros por Defecto |
|---------|-------------------|--------------------------------------|
| `registro_estrategias.py` | Documentación | Un catálogo inactivo con 50 lógicas de trading documentadas para desarrollo futuro. |
| `estrategia_medias.py` | SMA Crossover | Señal basada en el cruce de medias móviles simples de 20 y 50 períodos. |
| `estrategia_ema.py` | EMA Crossover | Señal basada en el cruce de medias móviles exponenciales de 9 y 21 períodos. |
| `estrategia_rsi.py` | RSI 14 | Identifica condiciones de sobrecompra (>70) y sobreventa (<30) para buscar rebotes. |
| `estrategia_bollinger.py` | Bollinger Bands | Evalúa si el precio rompe o toca las bandas superior o inferior para revertir a la media. |
| `estrategia_adx.py` | ADX Strength | Filtro que emite señales de fuerza de tendencia basándose en el indicador ADX. |
| `estrategia_supertrend.py` | SuperTrend | Indicador de tendencia clásica que combina ATR y precios promedio. |

---

## Instalación y Configuración

### 1. Requisitos previos

*   Python 3.8 o superior instalado en el sistema.
*   Una terminal o consola de comandos con acceso a `pip`.

### 2. Instalar dependencias requeridas

Ejecuta el siguiente comando para instalar las librerías necesarias del sistema:

```cmd
pip install binance-connector pandas numpy scikit-learn joblib
```

### 3. Configuración de Credenciales de Binance Testnet

Para utilizar la ejecución en vivo, debes crear una cuenta gratuita en **Binance Testnet Spot**: [https://testnet.binance.vision/](https://testnet.binance.vision/).

Genera un par de llaves API y colócalas en un archivo de texto plano llamado `api key.txt` en la **raíz del proyecto** con la estructura exacta que se muestra a continuación:

```text
API Key: tu_api_key_testnet_aqui
Secret Key: tu_secret_key_testnet_aqui
```

---

## Guía de Uso e Instancias de Ejecución

### 🚀 Bucle en Vivo (Producción Testnet Ficticia)
Para iniciar el bot en modo infinito monitoreando el mercado real en Binance Testnet:
```cmd
python main_bot_live.py
```
*   **Comportamiento:**
    *   Descarga velas cada 5 minutos del par BTCUSDT.
    *   Calcula régimen y procesa las señales de las estrategias.
    *   Si no hay señal tras 3 ciclos (15 minutos), **fuerza una micro-compra** artificial con propósitos demostrativos.
    *   Rastrea el P&L latente del activo comprado en la terminal.
    *   Para finalizar la ejecución presione `Ctrl+C`. Al hacerlo se mostrará el resumen de métricas final del ciclo operativo.

### 📊 Simulación de Backtesting Histórico
Para simular el comportamiento del bot sobre un período histórico de velas reales:
```cmd
python backtest.py
```
Puedes usar opciones por línea de comandos para modificar la simulación:
*   Simular con un capital específico:
    ```cmd
    python backtest.py --capital 5000
    ```
*   Simular una cantidad específica de días y usar un único agente específico:
    ```cmd
    python backtest.py --dias 60 --agente 2
    ```
*   Cargar un archivo CSV específico en lugar de descargar de Binance:
    ```cmd
    python backtest.py --csv mis_velas.csv
    ```

### 🧠 Entrenamiento del Oráculo de Machine Learning
Si deseas regenerar el modelo Random Forest (`modelo_oraculo_rf.pkl`) utilizando datos históricos recientes del mercado real:
```cmd
python entrenar_oraculo_ml.py
```
*   **¿Qué hace este script?**
    1. Descarga los últimos 90 días de velas de temporalidad de 1 hora.
    2. Ejecuta iterativamente todos los indicadores técnicos y calcula el régimen de mercado para cada vela histórica.
    3. Genera un conjunto de datos (*features*) y asigna etiquetas (*labels*) de éxito basándose en la evolución del precio en las siguientes 12 velas.
    4. Balancea la base de datos para equilibrar clases.
    5. Entrena un modelo `RandomForestClassifier` y un normalizador `StandardScaler`.
    6. Muestra métricas de validación como precisión (*accuracy*), matriz de confusión, métrica ROC-AUC e importancia de variables.
    7. Guarda el modelo actualizado en el archivo binario `modelo_oraculo_rf.pkl`.

### ⚡ Diagnóstico Modular de Capas Individuales
Puedes probar los scripts de forma aislada para verificar que cada módulo procese la información correctamente:
```cmd
python capa0_prueba_de_vida.py       # Imprime saldo disponible en Testnet
python capa1_ingesta_datos.py        # Muestra últimas 5 velas históricas descargadas
python capa2_regimen_detector.py     # Imprime el análisis de régimen actual de mercado
python capa3_oraculo.py              # Procesa la consolidación de señales del mercado actual
python capa4_5_grid_dca.py           # Imprime en formato de matriz la grilla NumPy de DCA
```

---

## Cómo agregar una nueva estrategia

Si deseas añadir un indicador técnico adicional al pipeline de evaluación:

1.  **Crear el archivo de la estrategia:**
    Crea un archivo nuevo bajo la ruta `estrategias/estrategia_mi_indicador.py` e implementa una función `evaluar` que acepte un `DataFrame` de Pandas:
    ```python
    def evaluar(df):
        # df posee columnas: Fecha/Hora, Apertura, Máximo, Mínimo, Cierre, Volumen
        
        # ... Tu lógica matemática de cálculo aquí ...
        
        # Debe retornar un diccionario con: accion (BUY/SELL/HOLD), confianza (0-100) y fundamento
        if condicion_alcista:
            return {"accion": "BUY", "confianza": 80, "fundamento": "Mi indicador detectó compra"}
        elif condicion_bajista:
            return {"accion": "SELL", "confianza": 80, "fundamento": "Mi indicador detectó venta"}
        return {"accion": "HOLD", "confianza": 0, "fundamento": "Sin señal clara"}
    ```
2.  **Importar en el script principal:**
    En `main_bot_live.py` (o `backtest.py`), importa tu nueva función:
    ```python
    from estrategias.estrategia_mi_indicador import evaluar as eval_mi_indicador
    ```
3.  **Registrarla en el listado de estrategias activas:**
    Agrega tu estrategia al catálogo para que sea evaluada por el oráculo:
    ```python
    ESTRATEGIAS_ACTIVAS.append({
        "funcion": eval_mi_indicador,
        "nombre": "Mi Indicador Técnico",
        "categoria": "Mean Reversion" # O la categoría correspondiente
    })
    ```

---

## Fórmulas y Lógica interna

### 1. Puntaje Neto Ponderado (Lógica Lineal de Capa 3)
Por defecto, si no se utiliza Machine Learning, el Oráculo consolidará los votos de las estrategias activas mediante una suma lineal ponderada por su confianza y el peso específico del agente:

$$\text{Puntaje Neto} = \frac{\sum_{i} (\text{Valor Voto}_i \times \text{Confianza}_i \times \text{Peso}_i)}{\sum_i \text{Peso}_i}$$

Donde:
*   $\text{Valor Voto} = +1.0$ si la acción es `BUY`.
*   $\text{Valor Voto} = -1.0$ si la acción es `SELL`.
*   $\text{Valor Voto} = 0.0$ si la acción es `HOLD`.
*   $\text{Confianza}$ se normaliza entre $0.0$ y $1.0$ ($\text{Confianza} / 100$).

**Umbrales de Activación:**
*   Si $\text{Puntaje Neto} \geq +0.20 \rightarrow \textbf{BUY}$
*   Si $\text{Puntaje Neto} \leq -0.20 \rightarrow \textbf{SELL}$
*   Cualquier valor intermedio se considera $\textbf{HOLD}$.

### 2. Gestión de Riesgos Estática (Capa 4)
*   **Tamaño de posición:** El bot divide rígidamente el saldo disponible en 3 partes iguales. Solo opera 1/3 del capital por operación.
*   **Stop-Loss estático:** Fijo al **4%** por debajo del precio de compra.
*   **Take-Profit adaptativo:** Calcula un precio objetivo basándose en un ratio de Riesgo:Recompensa (R:R) de 1:2 o 1:3 según el perfil del agente asignado.

### 3. Grilla DCA Escalable (Capa 4.5)
Cuando una operación avanza en contra, el bot calcula una escalera matemática para acumular posiciones más baratas y reducir el precio promedio de entrada:

$$\text{Distancia}_n = \text{Distancia Base} \times 1.25^{(n-1)}$$

$$\text{Tamaño Orden}_n = \text{Orden Base} \times 1.15^{(n-1)}$$

$$\text{Precio Niveles}_n = \text{Precio de Entrada} \times (1 - \text{Desviación Acumulada}_n)$$

$$\text{Precio Promedio} = \frac{\text{Total USDT Invertido}}{\text{Total Tokens BTC Adquiridos}}$$

Esto calcula dinámicamente un punto de salida de equilibrio mucho más bajo en caso de un rebote rápido del mercado.#   b o t - d e - c r i p t o m o n e d a s  
 