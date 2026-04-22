# NovaTech — Benchmark y Arquitectura

---

## 1. Arquitectura Actual (MVP)

### 1.1 Diagrama de Flujo con Tecnologías

```
                          ┌─────────────────────┐
                          │      👤 USUARIO      │
                          │    Navegador Web     │
                          └──────────┬──────────┘
                                     │ HTTPS / localhost
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                   FRONTEND  ·  Gradio 4.x  ·  Python               │
│                                                                    │
│  ┌──────────────────────────┐   ┌────────────────────────────────┐ │
│  │      PANTALLA LOGIN      │   │        PANEL DE CHAT           │ │
│  │  gr.Blocks · gr.Column   │   │  gr.Chatbot (height=320)       │ │
│  │  gr.Textbox · gr.Button  │   │  gr.Textbox · gr.Examples (8)  │ │
│  │  Auth: dict Python       │   │  gr.HTML spinner (CSS anim.)   │ │
│  │  CSS custom corporativo  │   │  lock/unlock: gr.update()      │ │
│  │                          │   │  Imágenes: tuple format        │ │
│  └──────────────────────────┘   └────────────────────────────────┘ │
└────────────────────────────────────┬───────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                      CAPA DE SEGURIDAD                             │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  BLOQUEO SQL DESTRUCTIVO  ·  módulo: re (Python stdlib)     │   │
│  │  Patrones: DROP · DELETE · TRUNCATE · ALTER · UPDATE        │   │
│  │  INSERT · CREATE · REPLACE                                  │   │
│  │  Ejecución: ANTES de cualquier llamada al LLM               │   │
│  └─────────────────────────────┬───────────────────────────────┘   │
│                                 │ OK                                │
│  ┌─────────────────────────────▼───────────────────────────────┐   │
│  │  GUARDRAIL LLM  ·  gemini-2.5-flash  ·  temperatura: 0.0   │   │
│  │  Cliente: ChatGoogleGenerativeAI (langchain-google-genai)   │   │
│  │  Decisión binaria: PASAR / BLOQUEAR                         │   │
│  │  Contexto: 5 últimos turnos del historial                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬───────────────────────────────┘
                                     │ PASAR
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│              ORQUESTADOR  ·  run_reports_crew()  ·  backend.py     │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  SHORTCUT ANÁLISIS  (si pregunta = "¿por qué?" y hay datos) │   │
│  │  Detección: needs_analysis() · keywords: 'por qué', etc.    │   │
│  │  Usa: last_query_result (estado global en memoria)          │   │
│  │  Sin nueva consulta SQL · directo a _analyze()              │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
│                                 │ no es análisis                   │
│                                 ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  NIVEL 1  ·  match_intent()  ·  ~80ms  ·  0 LLM calls      │   │
│  │  ─────────────────────────────────────────────────────────  │   │
│  │  Normalización: unicodedata.normalize('NFD')                │   │
│  │  Fuzzy match:   difflib.get_close_matches (cutoff=0.75)     │   │
│  │  Detección:     set intersections (_CIUDADES_SET, etc.)     │   │
│  │  Flags:         peor · mejor · tiene_filtro_param           │   │
│  │  Catálogo:      SQLS dict → 45 SQLs estáticos               │   │
│  │  Plantillas:    SQLS_PARAM → 9 templates parametrizados     │   │
│  │                 {where_sucursal} · {where_fecha}            │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
│                                 │ None (no match)                  │
│                                 ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  NIVEL 2  ·  _classify_intent()  ·  ~2–3s  ·  1 LLM call   │   │
│  │  ─────────────────────────────────────────────────────────  │   │
│  │  Modelo:    gemini-2.5-flash  ·  temperatura: 0.0           │   │
│  │  Cliente:   ChatGoogleGenerativeAI (LangChain)              │   │
│  │  Salida:    JSON → {intent, sucursal, fecha_inicio, fecha_fin}│  │
│  │  Parsing:   json.loads() + validación de tipos              │   │
│  │  Params:    _apply_params() → WHERE clauses (validadas re)  │   │
│  │  Salvaguarda ciudad: _CIUDADES_SET + difflib fuzzy          │   │
│  │  Salvaguarda fecha:  _MES_MAP + re.search año 202X          │   │
│  │  Upgrade:   global → paramétrico si hay ciudad o fecha      │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
│                                 │ desconocido                      │
│                                 ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  NIVEL 3  ·  CrewAI Agent  ·  ~8–15s  ·  2–4 LLM calls     │   │
│  │  ─────────────────────────────────────────────────────────  │   │
│  │  Framework: crewai (Agent · Task · Crew · Process.seq.)     │   │
│  │  Modelo:    gemini-2.0-flash  ·  verbose: False             │   │
│  │  Tool 1 — schema_tool():                                    │   │
│  │    @tool decorator · lee sqlite_master → DDL completo       │   │
│  │    Caché: _schema_cache (estado global, persiste sesión)    │   │
│  │  Tool 2 — query_tool():                                     │   │
│  │    Recibe SQL · ejecuta _execute_sql() · retorna markdown   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ SQL query
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                  BASE DE DATOS  ·  SQLite 3                        │
│                                                                    │
│  Archivo:   novatech.db  ·  Modo: solo lectura (SELECT)            │
│  Conexión:  sqlite3.connect() + pandas.read_sql_query()            │
│  Tablas:    sucursales · empleados · productos · clientes          │
│             ventas · cobranza · gastos · inventario  (8 total)     │
│  Índices:   idx_ventas_fecha · idx_ventas_sucursal                 │
│             idx_cobranza_fecha · idx_cobranza_cliente  (4 total)   │
│  Volumen:   15,000 ventas · 500 clientes · 100 empleados           │
│             50 productos · 8 sucursales · 3,000 gastos             │
│  Generado:  01_pipeline.py  (Faker · NumPy · random · datetime)    │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ pandas DataFrame
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                      POST-PROCESAMIENTO                            │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  _naturalize()                                               │  │
│  │  1 fila  → gemini-2.5-flash · temp=0.2                      │  │
│  │            Prompt: presenta dato como hecho confirmado       │  │
│  │            Prohíbe frases de duda o alucinación              │  │
│  │  N filas  → pandas DataFrame.to_markdown() (sin LLM)        │  │
│  │  Formato $: MONEY_KEYWORDS · excluye COUNT_KEYWORDS          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  _analyze()  (solo para preguntas "¿por qué?")               │  │
│  │  Modelo: gemini-2.5-flash · temperatura: 0.3                 │  │
│  │  Entrada: last_query_result (DataFrame en memoria)           │  │
│  │  Solo interpreta datos reales · sin recomendaciones          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  generate_chart()  (si el usuario pide gráfica)              │  │
│  │  Librería:  Plotly Express · px.bar                          │  │
│  │  Selección Y: prefiere columnas monetarias (MONEY_PREF)      │  │
│  │             descarta columnas de conteo (COUNT_EXCL)         │  │
│  │  Estilo:    color_continuous_scale=Blues · hover custom      │  │
│  │  Export:    kaleido 0.2.1 → PNG (750×420 px)                 │  │
│  │             tempfile.NamedTemporaryFile · tuple Gradio       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ texto / tabla markdown / imagen PNG
                           ▼
                    ┌─────────────┐
                    │  FRONTEND   │
                    │  (Gradio)   │
                    └─────────────┘
```

---

### 1.2 Stack Tecnológico Completo

| Capa | Tecnología | Rol |
|------|-----------|-----|
| Frontend | Gradio 4.x (`gr.Blocks`, `gr.Chatbot`) | UI conversacional, login, imágenes inline |
| Seguridad SQL | Python `re` (stdlib) | Bloqueo de DROP, DELETE, ALTER, etc. |
| Guardrail | `gemini-2.5-flash` + LangChain | Clasificación PASAR / BLOQUEAR |
| LLM cliente | `langchain-google-genai` · `ChatGoogleGenerativeAI` | Interfaz unificada con Gemini |
| Intent L1 | `unicodedata` · `difflib` · `set` (stdlib) | Normalización y fuzzy matching |
| Intent L2 | `gemini-2.5-flash` · temp=0.0 · JSON | Clasificador determinista de intenciones |
| Intent L3 | `crewai` · `gemini-2.0-flash` | Agente autónomo generador de SQL libre |
| Base de datos | SQLite 3 (stdlib) | Almacenamiento y consulta |
| Data layer | `sqlite3` + `pandas.read_sql_query` | Conexión y transformación de resultados |
| Naturalización | `gemini-2.5-flash` · temp=0.2 | Convierte dato crudo a lenguaje natural |
| Análisis | `gemini-2.5-flash` · temp=0.3 | Interpretación de preguntas "¿por qué?" |
| Gráficas | `plotly.express` + `kaleido 0.2.1` | Bar charts exportados a PNG |
| Generación datos | `Faker` · `NumPy` · `random` | Pipeline sintético (`01_pipeline.py`) |
| API key | `GEMINI_API_KEY` (env var) | Autenticación Google AI |

---

## 2. Benchmark de Rendimiento

### 2.1 Latencia por Componente

| Componente | Mecanismo | LLM Calls | Mín | Máx | Promedio |
|-----------|-----------|:---------:|-----|-----|:--------:|
| Guardrail | 1 LLM call | 1 | 0.8 s | 1.5 s | ~1.0 s |
| Nivel 1 — match_intent | Código puro (0 LLM) | 0 | 5 ms | 120 ms | ~80 ms |
| SQLite query | sqlite3 + pandas | 0 | 10 ms | 150 ms | ~50 ms |
| Nivel 2 — clasificador | 1 LLM call + SQL | 1 | 1.2 s | 3.5 s | ~2.2 s |
| Nivel 3 — CrewAI | 2–4 LLM calls + SQL | 2–4 | 7 s | 18 s | ~11 s |
| _naturalize (1 fila) | 1 LLM call | 1 | 0.8 s | 1.8 s | ~1.1 s |
| _naturalize (tabla) | pandas to_markdown | 0 | < 5 ms | 10 ms | ~5 ms |
| _analyze | 1 LLM call | 1 | 1.0 s | 2.5 s | ~1.5 s |

### 2.2 Latencia Total por Escenario Real

| Escenario | Desglose | Total |
|-----------|----------|:-----:|
| Nivel 1 + tabla markdown | Guardrail (1s) + SQL (50ms) + to_markdown (5ms) | **~1.1 s** |
| Nivel 2 + tabla markdown | Guardrail (1s) + Clasificador (2.2s) + SQL (50ms) | **~3.3 s** |
| Nivel 3 (pregunta exótica) | Guardrail (1s) + CrewAI (11s) + to_markdown (5ms) | **~12 s** |
| Análisis "¿por qué?" | Guardrail (1s) + _analyze con datos en memoria (1.5s) | **~2.5 s** |

### 2.3 Distribución de Consultas por Nivel

| Nivel | % del Total | Consultas típicas |
|-------|:-----------:|------------------|
| Nivel 1 — keyword match | ~55% | Globales sin filtros: mejor producto, ventas por sucursal |
| Nivel 2 — clasificador LLM | ~38% | Con ciudad o período: vendedores de Monterrey en enero |
| Nivel 3 — CrewAI | ~7% | Exóticas: cruces no anticipados, preguntas complejas |

> **93% de las consultas** se resuelven sin activar CrewAI → latencia promedio **~2.5 s**

### 2.4 Impacto de la Arquitectura de 3 Niveles

| Escenario | Sin Nivel 2 (solo L1 + CrewAI) | Con Nivel 2 | Mejora |
|-----------|:------------------------------:|:-----------:|:------:|
| Latencia promedio general | ~7.5 s | ~2.5 s | **−67%** |
| Costo LLM por consulta promedio | Alto (2–4 calls) | Bajo (0–1 calls) | **~−70%** |
| Riesgo de SQL incorrecto | ~10% (SQL generado libre) | ~1% (SQL estático) | **−90%** |

---

## 3. Arquitectura Mejorada (Propuesta para Producción)

### 3.1 Diagrama de Arquitectura Productiva

```
                          ┌─────────────────────┐
                          │      👤 USUARIO      │
                          │    Navegador Web     │
                          └──────────┬──────────┘
                                     │ HTTPS / TLS 1.3
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│              FRONTEND  ·  React 18 + Next.js 14  ·  TypeScript     │
│                                                                    │
│  ┌──────────────────────────┐   ┌────────────────────────────────┐ │
│  │      AUTENTICACIÓN       │   │        PANEL DE CHAT           │ │
│  │  JWT en httpOnly cookie  │   │  Componentes React             │ │
│  │  Refresh token auto      │   │  Streaming: WebSockets         │ │
│  │  Roles: gerente · admin  │   │  Respuesta token a token       │ │
│  │  Tailwind CSS            │   │  Gráficas: Recharts            │ │
│  └──────────────────────────┘   └────────────────────────────────┘ │
└────────────────────────────────────┬───────────────────────────────┘
                                     │ JWT + query
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                API GATEWAY  ·  FastAPI  ·  Python 3.12             │
│                                                                    │
│  Endpoints: POST /chat · POST /query · GET /chart · GET /health    │
│  Rate limiting: slowapi (10 req/min por usuario)                   │
│  Middleware JWT: python-jose · passlib · verifica rol              │
│  Validación: pydantic v2 · sanitización de inputs                  │
│  Docs: Swagger UI autogenerado · async/await completo              │
└──────────┬────────────────────────┬───────────────────────────────┘
           │                        │
           ▼                        ▼
┌─────────────────────┐  ┌──────────────────────────────────────────┐
│  CACHÉ SEMÁNTICA    │  │          PIPELINE DE IA                  │
│  Redis 7            │  │                                          │
│  ─────────────────  │  │  ┌────────────────────────────────────┐  │
│  Clave: embedding   │  │  │  CAPA DE EMBEDDINGS                │  │
│  de la consulta     │  │  │  text-embedding-004 (Google)       │  │
│  Similitud coseno   │  │  │  Índice pre-calculado: 45+ intents │  │
│  > 0.95 → hit       │  │  │  Similitud coseno (numpy)          │  │
│  TTL ventas: 1h     │  │  │  Umbral match L1: ≥ 0.85           │  │
│  TTL empleados: 24h │  │  │  Cobertura esperada: ~75%          │  │
│  Librería: redis-py │  │  └────────────────┬───────────────────┘  │
└─────────────────────┘  │                   │ no match             │
                         │  ┌────────────────▼───────────────────┐  │
                         │  │  NIVEL 2  ·  Clasificador LLM      │  │
                         │  │  gemini-2.5-flash · temp=0.0       │  │
                         │  │  Few-shot prompting mejorado       │  │
                         │  │  Validación pydantic de params     │  │
                         │  └────────────────┬───────────────────┘  │
                         │                   │ desconocido           │
                         │  ┌────────────────▼───────────────────┐  │
                         │  │  NIVEL 3  ·  CrewAI Agent          │  │
                         │  │  gemini-2.0-flash                  │  │
                         │  │  SQL validation antes de ejecutar  │  │
                         │  │  Retry con backoff exponencial     │  │
                         │  └────────────────────────────────────┘  │
                         └──────────────────┬───────────────────────┘
                                            │ SQL async
                                            ▼
┌────────────────────────────────────────────────────────────────────┐
│              BASE DE DATOS  ·  PostgreSQL 16 + pgvector            │
│                                                                    │
│  Extensión pgvector: embeddings nativos en BD                      │
│  Mismo esquema NovaTech (8 tablas) + tabla query_logs              │
│  Conexión: asyncpg (async) · Pool: SQLAlchemy 2.0 async            │
│  Índices: BRIN para fechas · B-tree para IDs                       │
│  Backups: pg_dump diario automático                                │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                       OBSERVABILIDAD                               │
│                                                                    │
│  LangSmith: tracing LLM · latencia · tokens · costo por query      │
│  query_logs (PostgreSQL): usuario · nivel · latencia · éxito       │
│  Alerta: si Nivel 3 > 30% de queries → revisar catálogo            │
└────────────────────────────────────────────────────────────────────┘
                                                          
┌────────────────────────────────────────────────────────────────────┐
│             INFRAESTRUCTURA  ·  Docker Compose + Cloud Run         │
│                                                                    │
│  Contenedores: api · frontend · redis · postgres                   │
│  Variables: .env (sin hardcoding)                                  │
│  CI/CD: GitHub Actions → build + test + deploy                     │
└────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Stack Tecnológico: Actual vs. Propuesto

| Capa | Actual (MVP) | Propuesto (Producción) | Motivo |
|------|-------------|----------------------|--------|
| Frontend | Gradio 4.x | React 18 + Next.js 14 | Streaming, UX, mobile |
| Auth | Dict hardcodeado | JWT + `python-jose` | Seguridad, roles, auditoría |
| API | Embebida en Gradio | FastAPI + async | REST, escalabilidad, Swagger |
| Rate limiting | Ninguno | `slowapi` (10 req/min) | Protección contra abuso |
| Intent L1 | Keyword + difflib | `text-embedding-004` | Cobertura 55% → 75% |
| Caché | Ninguna | Redis 7 (semántica) | ~30% queries sin LLM |
| Base de datos | SQLite | PostgreSQL 16 + pgvector | Concurrencia, embeddings |
| ORM / conexión | `sqlite3` + pandas | SQLAlchemy 2.0 async | Pool de conexiones |
| Observabilidad | `print()` | LangSmith + `query_logs` | Debug, costos, calidad |
| Deploy | `python 02_app.py` | Docker + Cloud Run (GCP) | Escalabilidad, CI/CD |

### 3.3 Impacto Esperado

| Métrica | Actual | Propuesto | Mejora |
|---------|:------:|:---------:|:------:|
| Latencia promedio | ~2.5 s | ~0.9 s | **−64%** |
| Cobertura Nivel 1 | 55% | ~75% | **+20 pp** |
| Queries resueltas por caché | 0% | ~30% | **+30 pp** |
| Usuarios simultáneos | 1 | 50+ | **×50** |
| Riesgo SQL incorrecto (N3) | ~10% | ~5% | **−50%** |
| Costo LLM por 1,000 queries | base | ~40% menor | **−40%** |
