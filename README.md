# Crypto Intelligence - Blockchain Dashboard

Aplicación web interactiva desarrollada con Streamlit para analizar redes blockchain en tiempo real. El proyecto parte del caso de estudio de Bitcoin y se amplía a una arquitectura multi-activo con soporte para Bitcoin, Ethereum y Solana.

Enlace desplegado:
https://blockchaindashboard-qprsywtdqi5ecmlemndwbt.streamlit.app/

## Información del proyecto

| Campo | Valor |
|---|---|
| Estudiante | María Muñoz Nadales |
| Usuario de GitHub | mariamunoznadales |
| Título | Crypto Intelligence - Multi-Asset Blockchain Analytics |
| Enfoque de IA | Predicción y comparación de modelos |
| Framework principal | Streamlit |
| Lenguaje | Python |

## Objetivo

El objetivo del trabajo es construir un dashboard que permita observar, verificar y explicar el comportamiento de redes blockchain usando datos públicos en vivo. La aplicación no se limita a mostrar métricas: también reconstruye mecanismos criptográficos, valida reglas de consenso, estima riesgo operativo y aplica modelos sencillos de predicción.

El resultado final es una herramienta visual para estudiar:

- Producción de bloques, slots o gas en tiempo real.
- Validación de cabeceras, hashes, Merkle roots o reglas de protocolo.
- Evolución histórica de dificultad, comisiones o rendimiento.
- Predicciones basadas en modelos simples y comparables.
- Riesgos de seguridad, estabilidad y salud de red.

## Funcionalidades principales

### Dashboard multi-activo

La aplicación permite alternar entre tres redes:

- Bitcoin (BTC): análisis de Proof of Work, dificultad, hash rate, cabeceras y Merkle proofs.
- Ethereum (ETH): análisis de bloques, gas, EIP-1559, base fee y seguridad económica PoS.
- Solana (SOL): análisis de slots, TPS, blockhashes, skip rate y estabilidad de finalización.

Cada activo usa un adaptador propio en `adapters/`, lo que permite que la interfaz mantenga la misma estructura aunque los mecanismos técnicos sean distintos.

### Actualización en vivo

El dashboard usa caché de Streamlit y refrescos parciales cada 10 segundos. La aplicación intenta actualizar solo cuando detecta nuevos bloques, slots o hashes, reduciendo llamadas innecesarias a APIs públicas.

### Interfaz visual

La interfaz está personalizada con CSS, tarjetas KPI, gráficos Plotly, colores por activo y navegación por módulos. Cada red cambia su identidad visual mediante acentos cromáticos definidos en su adaptador.

## Módulos implementados

### M1 - Proof of Work Monitor / Live State

Muestra el estado actual de la red seleccionada.

Para Bitcoin:

- Altura del último bloque.
- Dificultad actual.
- Estimación de hash rate.
- Tiempo medio entre bloques recientes.
- Nivel de estrés de red frente al objetivo de 600 segundos.
- Gráfico de intervalos entre bloques.

Para Ethereum:

- Último bloque.
- Base fee.
- Uso de gas.
- Tiempo medio de bloque.
- Estrés según utilización frente al objetivo EIP-1559.

Para Solana:

- Slot finalizado.
- TPS medio.
- Skip rate.
- Tiempo medio de slot.
- Estado de estabilidad de producción de slots.

### M2 - Block Header Analyzer / Mechanism Analyzer

Explica y verifica el mecanismo interno de cada red.

Para Bitcoin:

- Obtiene la cabecera real de 80 bytes.
- Descompone versión, hash previo, Merkle root, timestamp, bits y nonce.
- Recalcula el doble SHA-256.
- Convierte `bits` a target.
- Comprueba si el hash cumple Proof of Work.
- Verifica coincidencia con los datos devueltos por la API.

Para Ethereum:

- Muestra hash, parent hash, timestamp, gas used y gas limit.
- Calcula el siguiente `baseFeePerGas` según la regla de EIP-1559.
- Presenta los datos clave del bloque en formato auditable.

Para Solana:

- Muestra slot, parent slot, blockhash y previous blockhash.
- Resume transacciones observadas y profundidad de confirmación.
- Explica cómo se encadena el slot finalizado con su padre.

### M3 - Difficulty History / Network Evolution

Visualiza la evolución reciente de la red.

Para Bitcoin:

- Descarga el historial de dificultad de blockchain.info.
- Construye una serie temporal limpia con pandas.
- Muestra dificultad actual, punto anterior, mínimo y máximo.
- Grafica la evolución de dificultad.
- Compara el tiempo de bloque reciente contra el objetivo de 600 segundos.

Para Ethereum:

- Usa `eth_feeHistory` para graficar la evolución de la base fee.
- Muestra cambios recientes en comisiones y gas usado.

Para Solana:

- Usa muestras de rendimiento RPC.
- Grafica TPS y tiempos de slot.
- Resume la evolución operativa de la red.

### M4 - AI Component

Incluye el componente de predicción principal.

Para Bitcoin:

- Aplica regresión lineal simple sobre la dificultad histórica.
- Predice el siguiente punto de dificultad.
- Calcula tendencia, cambio porcentual y confianza aproximada.
- Muestra una banda de confianza y un punto futuro en Plotly.
- Incluye una animación del proceso: carga, normalización, estimación y cálculo.

Para Ethereum:

- Predice la base fee del siguiente bloque con una extrapolación de corto plazo.
- Compara la predicción con la estimación protocolaria EIP-1559.

Para Solana:

- Predice el TPS esperado usando media reciente y pendiente de corto plazo.
- Ajusta la confianza según el skip rate.

### M5 - Merkle Proof Verifier / Protocol Rule Verifier

Módulo avanzado de verificación.

Para Bitcoin:

- Permite elegir una transacción del bloque actual.
- Construye una prueba de Merkle desde la transacción hasta la raíz.
- Usa doble SHA-256 con el orden de bytes correcto.
- Compara la raíz calculada con la Merkle root del bloque.
- Muestra cada paso de hashing en una tabla.

Para Ethereum:

- Recalcula paso a paso la regla de actualización de la base fee.
- Verifica el resultado frente al cálculo interno del cliente.

Para Solana:

- Comprueba que el `previousBlockhash` del slot actual coincide con el blockhash del parent slot.
- Detecta saltos entre slots padre e hijo.

### M6 - Security Score

Estima seguridad y riesgo bajo supuestos configurables.

Para Bitcoin:

- Estima el coste horario de superar el hash rate de la red.
- Permite modificar eficiencia ASIC, coste eléctrico, coste de hardware y amortización.
- Calcula coste eléctrico y coste total estimado.
- Implementa la probabilidad de alcance de un atacante según Nakamoto 2008, sección 11.
- Grafica probabilidad de ataque frente a número de confirmaciones.

Para Ethereum:

- Estima coste económico de controlar un tercio o dos tercios del stake.
- Usa supuestos editables de precio ETH, ETH en staking y porcentaje de slashing.
- Genera un score de seguridad combinado con el estrés actual de gas.

Para Solana:

- Calcula un score de estabilidad/finalidad basado en skip rate, profundidad y tiempo de slot.
- Grafica riesgo residual al aumentar slots finalizados.

### M7 - Second AI Approach

Compara un segundo modelo predictivo con el modelo principal.

Para Bitcoin:

- Compara regresión lineal con suavizado exponencial.
- Permite ajustar `alpha`.
- Calcula MAE de backtesting.
- Indica que modelo tiene menor error.

Para Ethereum:

- Compara extrapolación lineal de base fee con suavizado exponencial.
- Muestra predicción, variación y MAE.

Para Solana:

- Compara predicción lineal de TPS con suavizado exponencial.
- Evalúa ambos modelos con backtesting.

### M8 - Live Risk Radar

Módulo avanzado adicional para resumir salud operativa.

El radar evalúa cinco dimensiones:

- Security.
- Finality.
- Throughput.
- Fee Health.
- Stability.

Cada red adapta esos factores a sus propias métricas:

- Bitcoin: hash rate, desviación del tiempo de bloque, transacciones y estabilidad.
- Ethereum: gas, base fee, tiempo de bloque y presión de comisiones.
- Solana: TPS, skip rate, profundidad de confirmación y estabilidad de slot.

## Arquitectura del proyecto

```text
Blockchain_Dashboard/
|-- app.py
|-- README.md
|-- requirements.txt
|-- Final_Report.tex
|-- adapters/
|   |-- __init__.py
|   |-- base.py
|   |-- btc.py
|   |-- eth.py
|   `-- sol.py
|-- api/
|   |-- __init__.py
|   |-- blockchain_client.py
|   |-- ethereum_client.py
|   |-- solana_client.py
|   `-- test_api.py
`-- modules/
    |-- __init__.py
    |-- dashboard_theme.py
    |-- m1_pow_monitor.py
    |-- m2_block_header.py
    |-- m3_difficulty_history.py
    |-- m4_ai_component.py
    |-- m5_merkle_proof.py
    |-- m6_security_score.py
    |-- m7_second_ai.py
    |-- m8_risk_radar.py
    |-- eth_live.py
    |-- eth_advanced.py
    |-- sol_live.py
    `-- sol_advanced.py
```

## Componentes técnicos

### `app.py`

Es el punto de entrada de Streamlit. Define:

- Configuración de página.
- Estilos globales.
- Selector BTC/ETH/SOL.
- Precarga de datos.
- Refresco parcial mediante `st.fragment` cuando está disponible.
- Renderizado de KPIs superiores.
- Navegación por módulos M1-M8.

### `adapters/`

Contiene la capa que permite usar la misma interfaz para distintas redes.

- `base.py`: contratos comunes (`AssetIdentity`, `ModuleSpec`, `TopMetric`).
- `btc.py`: conecta Bitcoin con los módulos M1-M8 originales.
- `eth.py`: conecta Ethereum con módulos live y avanzados.
- `sol.py`: conecta Solana con módulos live y avanzados.

### `api/`

Centraliza el acceso a datos externos.

- `blockchain_client.py`: cliente Bitcoin con blockchain.info y Blockstream, caché y fallbacks.
- `ethereum_client.py`: cliente JSON-RPC público para Ethereum.
- `solana_client.py`: cliente JSON-RPC público para Solana.

### `modules/`

Contiene la lógica visual y analítica de cada módulo. Se separan los módulos base de Bitcoin y los módulos específicos de Ethereum y Solana.

## APIs utilizadas

### Bitcoin

- `https://blockchain.info`
- `https://api.blockchain.info`
- `https://blockstream.info/api`

Se usan para obtener bloques recientes, cabeceras, transacciones, Merkle root, dificultad histórica y precio BTC/USD.

### Ethereum

- `https://ethereum-rpc.publicnode.com`

Métodos usados:

- `eth_blockNumber`
- `eth_getBlockByNumber`
- `eth_feeHistory`
- `eth_gasPrice`

### Solana

- `https://api.mainnet-beta.solana.com`

Métodos usados:

- `getSlot`
- `getBlockHeight`
- `getLatestBlockhash`
- `getBlock`
- `getRecentPerformanceSamples`
- `getRecentPrioritizationFees`

## Instalación y ejecución local

### 1. Clonar o abrir el repositorio

```bash
cd Blockchain_Dashboard
```

### 2. Crear un entorno virtual

```bash
python -m venv venv
source venv/bin/activate
```

En Windows:

```bash
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar el dashboard

```bash
streamlit run app.py
```

La aplicación se abrirá normalmente en:

```text
http://localhost:8501
```

## Dependencias

El archivo `requirements.txt` incluye:

```text
requests
pandas
plotly
streamlit
```

## Decisiones de diseño

- Streamlit se eligió por su rapidez para crear dashboards interactivos en Python.
- Plotly se usa para gráficos dinámicos, tooltips y visualización de series temporales.
- Los datos se almacenan en caché con `st.cache_data` para evitar sobrecargar endpoints públicos.
- Bitcoin conserva el enfoque criptográfico más detallado porque es el caso principal del trabajo.
- Ethereum y Solana reutilizan la misma estructura modular adaptando las métricas a sus modelos de consenso.
- La arquitectura con adaptadores permite añadir nuevos activos sin reescribir `app.py`.

## Limitaciones

- El proyecto depende de APIs públicas, por lo que puede verse afectado por límites de rate, caídas temporales o cambios de respuesta.
- Algunas métricas de seguridad son estimaciones pedagógicas y dependen de supuestos configurables.
- Los modelos de IA son intencionadamente simples: regresión lineal, extrapolación y suavizado exponencial. Su objetivo es explicar tendencias, no producir señales financieras.
- En Solana y Ethereum, algunos nombres de módulos mantienen la numeración original del proyecto aunque el contenido se adapte a otra arquitectura de red.

## Resultado final

El trabajo entrega un dashboard funcional, desplegado y ampliado, capaz de:

- Monitorizar datos blockchain en vivo.
- Verificar mecanismos criptográficos y reglas de protocolo.
- Visualizar tendencias históricas.
- Aplicar predicción básica.
- Comparar modelos.
- Estimar riesgo y salud de red.
- Operar sobre tres ecosistemas blockchain con una interfaz común.

Este README sustituye completamente la plantilla inicial y documenta el estado final del proyecto.
