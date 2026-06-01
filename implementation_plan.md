# Plan de Integración de Machine Learning en el Bot de Trading

Este plan detalla cómo reemplazar el sistema de votación heurístico (basado en reglas rígidas de `if/else` y puntajes ponderados fijos) del Oráculo actual (`capa3_oraculo.py`) con un modelo de clasificación simple de Machine Learning (**Random Forest Classifier** usando `scikit-learn`).

El modelo evaluará las predicciones de las estrategias existentes, determinará la probabilidad de éxito de cada señal, y buscará activamente ratios de riesgo/beneficio (R:R) agresivos (1:2 o 1:3), aceptando pérdidas controladas en la Testnet de Binance.

---

## 🛠️ Nuevas Librerías a Instalar

Para incorporar Machine Learning y el manejo del modelo sin alterar profundamente la estructura básica del bot, añadiremos las siguientes dependencias al entorno de Python:

```bash
pip install scikit-learn joblib
```

*   **`scikit-learn`**: Proporciona el modelo `RandomForestClassifier`, herramientas de preprocesamiento y funciones de métricas.
*   **`joblib`**: Se utiliza para guardar el modelo entrenado en disco (`.pkl`) y cargarlo de manera ultrarrápida en el bucle principal en vivo sin necesidad de reentrenarlo en cada ciclo.

---

## 📐 Estructura de la Nueva Solución

Proponemos una arquitectura en **dos etapas** para no interferir con la operativa actual de la Testnet mientras desarrollamos y validamos el cerebro de Machine Learning:

### 1. Script de Entrenamiento y Backtesting (`entrenar_oraculo_ml.py` [NEW])
Un script auxiliar para generar el dataset histórico de entrenamiento, entrenar el modelo Random Forest y guardarlo.
*   **Generación de Features (Características):** Ejecuta las 6 estrategias actuales sobre los datos históricos de velas (`df`) para recopilar las decisiones (`BUY`=1, `SELL`=-1, `HOLD`=0) y confianzas de cada una, además de metadatos como el Régimen de Mercado y la Volatilidad (Z-Score/ADX).
*   **Generación de Labels (Etiquetas):** Define el éxito de cada entrada basándose en si el precio tocó primero el Take Profit (TP) en un ratio **1:2** o **1:3** frente al Stop Loss (SL), o si terminó en pérdida.
*   **Entrenamiento:** Entrena un `RandomForestClassifier` optimizado para maximizar la precisión de señales positivas (evitando falsos positivos).
*   **Guardado:** Exporta el modelo entrenado a `modelo_oraculo_rf.pkl`.

### 2. Modificación de Capas Existentes

#### Capa 3: Oráculo Inteligente (`capa3_oraculo.py` [MODIFY])
*   Carga el modelo preentrenado `modelo_oraculo_rf.pkl` al iniciar.
*   Recibe los votos en tiempo real de las estrategias.
*   Usa `.predict_proba()` para estimar estadísticamente la probabilidad de que una operación resulte en ganancia.
*   Toma la decisión final de operar solo si la probabilidad de éxito supera un umbral mínimo dinámico (ej. > 55%).

#### Capa 4: Gestor de Riesgo y Ratios (`capa4_gestor_riesgo.py` [MODIFY])
*   Reemplaza el Stop Loss fijo del 4% por un sistema de **Ratios de Riesgo/Beneficio (R:R)** configurables a **1:2** o **1:3**.
*   Por ejemplo, define un Stop Loss ajustado (ej. 2% o 3%) y un Take Profit explícito (ej. 6% o 9%).

#### Ejecutor y Pipeline (`main_bot_live.py` [MODIFY])
*   Integra el envío de órdenes de Take Profit (TP) limit y Stop Loss (SL) de forma conjunta o realiza el seguimiento en vivo de la posición para cerrarla cuando toque el TP (establecido en ratio 1:2 o 1:3).

---

## 📋 Cambios Propuestos

### [Componente Oráculo y ML]

#### [NEW] [entrenar_oraculo_ml.py](file:///e:/bot%20de%20criptomonedas/entrenar_oraculo_ml.py)
Script independiente para procesar los datos históricos, calcular etiquetas con ratio R:R 1:2/1:3, entrenar el Random Forest Classifier y guardar el archivo `.pkl`.

#### [MODIFY] [capa3_oraculo.py](file:///e:/bot%20de%20criptomonedas/capa3_oraculo.py)
Añadir soporte para cargar el modelo guardado y utilizar la inferencia en `consolidar_votos`:
*   Si el archivo del modelo existe, se formatea la entrada actual de las estrategias como un vector de características (features) y se consulta la probabilidad estadística mediante `.predict_proba()`.
*   Si la probabilidad es baja o el modelo no está entrenado, puede recurrir al sistema híbrido actual de contingencia (voto ponderado) para no detener el bot.

### [Componente de Riesgo y Operación]

#### [MODIFY] [capa4_gestor_riesgo.py](file:///e:/bot%20de%20criptomonedas/capa4_gestor_riesgo.py)
Modificar `evaluar_riesgo` para aceptar configuraciones de **Take Profit** basados en ratio **1:2** o **1:3** del Stop Loss.

#### [MODIFY] [main_bot_live.py](file:///e:/bot%20de%20criptomonedas/main_bot_live.py)
*   Integrar la lógica de salida por Take Profit en el bucle principal o registrar la orden OCO (One-Cancels-the-Other) de salida en Binance si la API lo permite, o gestionarlo de forma sintética (como se hace con la venta actual).
*   Eliminar el "micro-trade forzado por cobardía" o ajustarlo, ya que el modelo ahora asumirá riesgos calculados más agresivos.

---

## 🧪 Plan de Verificación

### Pruebas Automatizadas
1.  **Script de Entrenamiento:** Ejecutar `python entrenar_oraculo_ml.py` para asegurar que genera el archivo `modelo_oraculo_rf.pkl` sin errores y reporta métricas de precisión aceptables.
2.  **Inferencia del Oráculo:** Correr `python capa3_oraculo.py` en modo de prueba para validar que puede cargar el modelo `.pkl` y predecir correctamente una simulación de votos.

### Verificación Manual en Testnet
1.  **Ejecución Simulada (Dry Run):** Correr el bot imprimiendo las decisiones del modelo de ML sin enviar las órdenes reales a la Testnet, para observar cómo se comporta la probabilidad y las decisiones durante 1 hora.
2.  **Operación Real en Testnet:** Iniciar `python main_bot_live.py` y monitorizar en vivo cómo entra en operaciones agresivas con su correspondiente Stop Loss y Take Profit (con ratio 1:2 o 1:3).
