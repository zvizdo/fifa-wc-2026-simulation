# Explorador de simulaciones de la Copa Mundial de la FIFA 2026 (en desarrollo)

Se trata de un panel interactivo de Streamlit que visualiza los resultados de 100.000 simulaciones del torneo de la Copa Mundial de la FIFA 2026. Permite explorar los resultados del torneo desde varias perspectivas: la competición en general, los equipos individuales y las ciudades anfitrionas.

## Características

- **Página de inicio**: Podio proyectado (campeón, subcampeón y tercer puesto) con sus probabilidades correspondientes.
- **Explorador de la competición**: Probabilidades de enfrentamientos etapa por etapa, escenarios de grupos y analizador de enfrentamientos directos.
- **Explorador de equipos**: Trayectoria del torneo por equipo, distribución de resultados y posibles oponentes por etapa.
- **Explorador de ciudades**: Proyecciones de enfrentamientos de ciudades anfitrionas en 16 venues de EE. UU., México y Canadá.
- **Simulador**: Ajusta el rango de los equipos con deslizadores para ejecutar simulaciones personalizadas y comparar los resultados con el baseline.

## Modelo de predicción de partidos

Cada partido se simula prediciendo los goles esperados para ambos equipos mediante un modelo de regresión de Poisson. A continuación, se obtiene una puntuación muestreada de una distribución de Poisson bivariada con una corrección de Dixon-Coles para resultados de bajo marcador.

### Una sola característica, muchas cosas integradas

El modelo de producción utiliza una única característica: la expectativa de victoria ofensiva, que comprime un conjunto rico de información en un solo número:

```
off_win_exp = 1 / (1 + (eff_off_rank / eff_opp_def_rank) ^ shape)
```

donde `eff_rank = rank × (1 - host_discount × is_host)`.

Esta fórmula captura cinco señales distintas:

| Señal | Cómo se codifica |
|---|---|
| **Calidad previa al torneo** | Clasificación FIFA base, inicializada a partir de la clasificación previa al torneo |
| **Forma en el torneo** | El rango ofensivo dinámico evoluciona después de cada partido mediante actualizaciones estilo Elo: los equipos que marcan más de lo esperado mejoran |
| **Especificidad del enfrentamiento** | El rango ofensivo se compara con el rango defensivo del oponente, no con su rango general: un ataque clínico contra una defensa deficiente se lee de forma diferente que el mismo ataque contra una defensa sólida |
| **Ventaja del anfitrión** | Las naciones anfitrionas reciben un descuento porcentual en su rango efectivo, lo que hace que la expectativa de victoria sea no linealmente mayor en juegos entre equipos empatados, donde el efecto de la multitud es más importante |
| **Curvatura del rango** | El exponente `shape` controla cuán rápidamente disminuye la probabilidad de victoria con la distancia del rango, y se ajusta conjuntamente con todo lo demás mediante Optuna |

La simplicidad es deliberada. Las pruebas de abolición de características mostraron que agregar la expectativa de victoria de las clasificaciones base, las clasificaciones actuales y la descomposición defensiva introdujo señales correlacionadas que diluyeron en lugar de aumentar el poder predictivo. Una característica bien construida se generaliza mejor bajo el protocolo de validación train-one-evaluate-rest CV, que es la prueba más dura para la extrapolación de simulaciones.

### Rangos dinámicos

Se rastrean tres rangos estilo Elo por equipo a lo largo del torneo, todos comenzando en la clasificación FIFA previa al torneo del equipo:

- **Rango general**: Se actualiza después de cada partido en función del resultado frente a la calidad del oponente.
- **Rango ofensivo**: Se actualiza en función de los goles marcados en relación con la calidad general del oponente. Alimenta directamente la característica `off_win_exp`.
- **Rango defensivo**: Se actualiza en función de los goles concedidos. Se utiliza como el componente defensivo del oponente en `off_win_exp`.

La magnitud de la actualización escala con `log(1 + |rank_diff|)`: las sorpresas producen ajustes más grandes. Todos los parámetros de actualización (forma, factores k, límite de goles) se ajustan conjuntamente con el modelo.

**Reversión a la media**. Después de cada actualización de rango, el rango dinámico se acerca en parte hacia la clasificación FIFA base del equipo:

```
new_rank = (1 - reversion_rate) × dynamic_rank + reversion_rate × base_rank
```

Esto es importante porque los grupos de la Copa del Mundo juegan solo tres partidos antes de la fase de eliminación. Sin la reversión, un solo resultado fortuito (como un equipo destacado que concede un autogol temprano) puede inclinar el rango ofensivo o defensivo lo suficiente como para distorsionar todas las predicciones posteriores. La reversión a la media ancla cada rango dinámico a nuestra mejor previsión previa (la clasificación FIFA previa al torneo) y controla cuán agresivamente un solo partido puede revisarlo. La `reversion_rate` se ajusta mediante Optuna junto con los demás parámetros de preprocesamiento.

### Entrenamiento

```bash
python -m model.train --n-trials 200 --seed 42
```

Búsqueda TPE de Optuna sobre 9 hiperparámetros: 6 que controlan el preprocesamiento de rangos dinámicos (forma, factores k, límite de goles, tasa de reversión) y 3 que controlan el transformador de características y el regresor (forma de la característica, descuento de anfitrión, alfa). Cada prueba se evalúa con validación cruzada train-one-evaluate-rest: se entrena en un solo torneo (~128 filas) y se valida en los 6 restantes (~720 filas). Este protocolo más estricto favorece a los modelos que se extrapolan limpiamente en lugar de aquellos que memorizan patrones de entrenamiento.

El modelo final se entrena con todos los datos y se guarda en `model/expanded_model.pkl`.

## Stack tecnológico

- **Python 3.12+**
- **Streamlit**: panel web
- **DuckDB**: base de datos columnar para consultas eficientes de más de 10 millones de filas de partidos
- **scikit-learn / scipy**: modelo de predicción de partidos mediante regresión de Poisson
- **Optuna**: optimización de hiperparámetros
- **Plotly**: gráficos interactivos
- **Pandas / NumPy**: procesamiento de datos

## Estructura del proyecto

```
├── app/                    # Aplicación Streamlit
│   ├── main.py             # Punto de entrada de la aplicación
│   ├── config.py           # Constantes y configuración
│   ├── sim_worker.py       # Trabajador para ejecuciones paralelas de simulaciones
│   ├── pages/              # Páginas: inicio, competencia, equipo, ciudad, simulador
│   ├── db/                 # Capa de consultas DuckDB (incl. consultas del simulador)
│   ├── ui/                 # Tema, tarjetas, gráficos, brackets, banderas, componentes del simulador
│   └── data/               # Base de datos DuckDB (generada)
├── engine/                 # Motor de simulación
│   ├── sim.py              # Orquestador de la competencia
│   ├── core.py             # Clases Team, Match, Group
│   ├── match.py            # Estrategias de predicción de partidos (WinExpMatch, ModeledMatch)
│   ├── schedule.py         # Bracket del torneo y asignaciones de venues
│   └── venues.py           # Ciudades anfitrionas y estadios
├── model/                  # Entrenamiento y análisis del modelo ML
│   ├── train.py            # Entrenamiento del modelo expandido con Optuna
│   ├── preprocessing.py    # Cálculo de rangos dinámicos e ingeniería de características
│   ├── transformers.py     # Transformadores compatibles con sklearn
│   ├── pipelines.py        # Constructores de pipelines (baseline y completo)
│   ├── cv.py                # Validación cruzada leave-one-tournament-out
│   ├── expanded_model.pkl  # Artefacto del modelo expandido entrenado
│   ├── win_exp_model.pkl   # Artefacto del modelo baseline entrenado
│   ├── win_exp_model_train.py   # Entrenamiento del modelo baseline legado
│   ├── nb_eda_v2.ipynb     # EDA y análisis de características del modelo expandido
│   ├── nb_eda.ipynb        # EDA del modelo baseline
│   └── nb_dataset.ipynb    # Notebook de preparación de dataset
├── data/                   # Datos brutos y plantillas de equipos
│   ├── db/                 # CSV históricos de la Copa del Mundo (ver más abajo)
│   ├── wc_2026_teams.json  # 48 equipos con asignaciones de grupos, clasificaciones FIFA, confederaciones
│   ├── wc_teams.csv/json   # Clasificaciones FIFA históricas antes de cada Copa del Mundo
│   └── dataset.json        # Datos de partidos históricos procesados (pre-generados)
├── main_general_sim.py     # Ejecutar 100K simulaciones (paralelas)
├── main_rank_sim.py        # Simulación alternativa basada en rangos
└── requirements.txt        # Dependencias de Python
```

## Configuración

### 1. Instalar dependencias

```bash
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

### 2. Agregar datos históricos de la Copa del Mundo

El proyecto requiere datos históricos de la Copa del Mundo en formato CSV del repositorio [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup/tree/master/data-csv). Descarga todos los archivos CSV y colócalos en `data/db/`:

```bash
# Clonar el repositorio fuente y copiar los CSV
git clone https://github.com/jfjelstul/worldcup.git /tmp/worldcup
cp /tmp/worldcup/data-csv/*.csv data/db/
```

Los archivos clave utilizados por el proyecto incluyen `matches.csv`, `tournaments.csv` y otros del conjunto de datos.

### 3. Preparar los datos de los equipos

La simulación requiere `data/wc_2026_teams.json`, un archivo manualmente curado que contiene los 48 equipos calificados organizados por grupo (A–L). Cada entrada de equipo incluye:
- Nombre del equipo
- Clasificación FIFA
- Confederación (UEFA, CONMEBOL, AFC, CAF, CONCACAF, OFC)
- Bandera de anfitrión (si el equipo es una nación anfitriona)

Este archivo debe colocarse en el directorio `data/` antes de ejecutar las simulaciones.

### 4. Dataset principal

El conjunto de datos histórico de partidos procesados ya está incluido en `data/dataset.json`. Contiene las clasificaciones FIFA de cada equipo antes de su respectiva edición de la Copa del Mundo (1998–2022).

Si necesitas regenerarlo (por ejemplo, después de actualizar los CSV fuente), ejecuta el notebook `model/nb_dataset.ipynb`, que lee de `data/db/` y exporta a `data/dataset.json`.

### 5. Ejecutar las simulaciones

Genera la base de datos DuckDB ejecutando 100.000 simulaciones de torneos:

```bash
python main_general_sim.py -n 100000 --db app/data/wc2026_general.duckdb --workers 8
```

Opciones:
- `-n`: Número de simulaciones (predeterminado: 100.000)
- `--db`: Ruta del archivo DuckDB de salida
- `--workers`: Número de procesos de trabajo paralelos (predeterminado: conteo de CPU - 1)

Esto utiliza el multiproceso para simular torneos en fragmentos de 50, con cada simulación ejecutando 104 partidos (72 de fase de grupos + 32 de eliminación directa). La base de datos resultante tiene ~1,3 GB.

### 6. Ejecutar la aplicación

```bash
cd app
streamlit run main.py
```

La aplicación estará disponible en `http://localhost:8501`.

## Implementación

Se incluye un Dockerfile para implementar en Google Cloud Run:

```bash
gcloud run deploy fifa-wc-2026-simulation --source . --region=us-central1 \
  --platform=managed --min-instances=1 --allow-unauthenticated
```

## Fuentes de datos

- **Datos históricos de partidos**: [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup) — Resultados de partidos de la Copa del Mundo, standings y metadatos (1930–2022)
- **Plantilla de equipos 2026**: Manualmente curada en `data/wc_2026_teams.json` — 48 equipos con asignaciones de grupos, clasificaciones FIFA y confederaciones
- **Clasificaciones FIFA históricas**: `data/wc_teams.csv` / `data/wc_teams.json` — Clasificaciones FIFA de cada equipo antes de su respectiva edición de la Copa del Mundo (1998–2022)
