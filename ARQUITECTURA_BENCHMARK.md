# NovaTech — Arquitectura y Benchmark

---

## 1. Arquitectura del Sistema (basada en código fuente)

### 1.1 Diagrama completo con tecnologías reales

```
╔══════════════════════════════════════════════════════════════════════╗
║                         👤  USUARIO                                  ║
║                    Navegador Web (localhost / share)                  ║
╚══════════════════════════════╦═══════════════════════════════════════╝
                               ║
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║          ARCHIVO: 02_app.py  ·  FRONTEND  ·  gradio==4.26.0         ║
║          gr.Blocks(theme=gr.themes.Soft(), css=CUSTOM_CSS)           ║
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────────┐ ║
║  │ PANTALLA DE LOGIN  (gr.Column visible=True)                     │ ║
║  │  gr.HTML  →  logo y título corporativo                          │ ║
║  │  gr.Textbox  →  campo "Usuario"                                 │ ║
║  │  gr.Textbox  →  campo "Contraseña" (type="password")            │ ║
║  │  gr.Button   →  "Ingresar" (variant="primary", elem_id)         │ ║
║  │  gr.HTML     →  mensaje de error dinámico                       │ ║
║  │  Auth: dict Python  USUARIOS_AUTORIZADOS                        │ ║
║  │    "gerenteVentas" : "ventas1234"                               │ ║
║  │    "admin"         : "novatech2024"                             │ ║
║  └─────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────────┐ ║
║  │ PANEL PRINCIPAL  (gr.Column visible=False → visible tras login) │ ║
║  │  gr.HTML           →  header gradiente azul corporativo         │ ║
║  │  gr.Chatbot        →  height=320, label="Panel de Reportes"     │ ║
║  │  gr.Textbox        →  input mensaje, lines=1, elem_id           │ ║
║  │  gr.HTML           →  spinner CSS  @keyframes nt-spin           │ ║
║  │  gr.Row:                                                        │ ║
║  │    gr.Button       →  "Consultar" variant="primary" scale=3     │ ║
║  │    gr.ClearButton  →  "Limpiar" scale=1                         │ ║
║  │  gr.Examples       →  8 consultas frecuentes predefinidas       │ ║
║  │  gr.HTML           →  aviso legal / disclaimer                  │ ║
║  │                                                                 │ ║
║  │  EVENTO: submit_btn.click + msg_input.submit                    │ ║
║  │    .then(lock)   → gr.update(interactive=False) en inputs       │ ║
║  │    .then(chatbot_response)  →  lógica principal                 │ ║
║  │    .then(unlock) → gr.update(interactive=True)                  │ ║
║  └─────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  demo.launch(share=True)  →  link local + link público Gradio        ║
╚══════════════════════════════╦═══════════════════════════════════════╝
                               ║ llamada a chatbot_response()
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║              CAPA DE SEGURIDAD  ·  02_app.py                        ║
║                                                                      ║
║  BLOQUE 1 — SQL destructivo  (stdlib: re implícito via list search)  ║
║  SQL_DESTRUCTIVOS = ["drop ", "delete ", "truncate ", "alter ",      ║
║                      "update ", "insert ", "create ", "replace "]    ║
║  → si cualquier patrón está en mensaje.lower() → bloqueo inmediato   ║
║  → sin llamada al LLM                                                ║
║                                                                      ║
║  BLOQUE 2 — Gráfica de datos anteriores (atajo sin LLM)              ║
║  _REFS_ANTERIORES = {"esa","ese","anterior","ultima","lo mismo",...}  ║
║  → si needs_chart() AND palabras en _REFS_ANTERIORES                 ║
║  → sirve get_last_query_result() directo → generate_chart()          ║
║  → sin nueva consulta SQL ni LLM call                                ║
╚══════════════════════════════╦═══════════════════════════════════════╝
                               ║ mensaje pasa filtros
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║              GUARDRAIL LLM  ·  backend.py / check_guardrails()      ║
║                                                                      ║
║  Modelo:    gemini-2.5-flash                                         ║
║  Cliente:   ChatGoogleGenerativeAI  (langchain-google-genai==1.0.2)  ║
║  API key:   os.environ.get("GEMINI_API_KEY")                         ║
║  Temp:      0.0  (respuesta determinista)                            ║
║  Decisión:  PASAR  /  BLOQUEAR  (sin explicación, solo 1 palabra)    ║
║  Contexto:  últimos 5 turnos del historial pasados como string       ║
╚══════════════════════════════╦═══════════════════════════════════════╝
                               ║ PASAR
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║         ORQUESTADOR  ·  backend.py / run_reports_crew()             ║
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │ SHORTCUT DE ANÁLISIS  (bypass del pipeline SQL)              │    ║
║  │ needs_analysis() →  keywords: "por qué", "porque",          │    ║
║  │   "a qué se debe", "qué explica", "cómo es posible",        │    ║
║  │   "qué significa", "qué indica", "explícame", etc.          │    ║
║  │ Condición: analisis=True AND last_query_result is not None   │    ║
║  │ Acción: usa DataFrame en memoria → llama _analyze()          │    ║
║  │         sin reset, sin SQL, sin LLM clasificador             │    ║
║  └────────────────────────────┬─────────────────────────────────┘    ║
║                               │ no es análisis o sin datos previos   ║
║              reset_last_query_result()  →  limpia estado global      ║
║                               │                                      ║
║  ┌────────────────────────────▼─────────────────────────────────┐    ║
║  │ NIVEL 1  ·  match_intent()  ·  0 LLM calls  ·  ~80ms        │    ║
║  │ ──────────────────────────────────────────────────────────   │    ║
║  │ Normalización:  unicodedata.normalize('NFD') + strip Mn      │    ║
║  │ Conjunto palabras: set(sin_acentos.lower().split())          │    ║
║  │                                                              │    ║
║  │ Sets semánticos:                                             │    ║
║  │  _PEOR  = {peor, menor, menos, minimo, bajo, debil, ...}     │    ║
║  │  _MEJOR = {mejor, mayor, mas, maximo, alto, lider, top, ...} │    ║
║  │  _CIUDADES_SET = {tijuana, monterrey, guadalajara,           │    ║
║  │                   culiacan, puebla, queretaro, merida,       │    ║
║  │                   ciudad, cdmx, mex}                         │    ║
║  │  _MESES_SET = {enero, febrero, ..., diciembre}               │    ║
║  │                                                              │    ║
║  │ Fuzzy matching: difflib.get_close_matches(cutoff=0.75)       │    ║
║  │   → detecta typos ej: "gualadajara" → "guadalajara"         │    ║
║  │   → filtra palabras < 4 caracteres                          │    ║
║  │                                                              │    ║
║  │ Flag tiene_filtro_param:                                     │    ║
║  │   True si ciudad o mes en pregunta → fuerza Nivel 2         │    ║
║  │                                                              │    ║
║  │ Catálogo SQLS: 45 SQLs estáticos (dict Python)               │    ║
║  │   vendedores, sucursales, productos, cobranza, gastos,       │    ║
║  │   clientes, inventario, resumen, cruces, empleados           │    ║
║  │                                                              │    ║
║  │ Catálogo SQLS_PARAM: 9 templates con placeholders            │    ║
║  │   {where_sucursal}  →  " AND s.id = N"                      │    ║
║  │   {where_fecha}     →  " AND v.fecha BETWEEN '...' AND '...'"│    ║
║  │   {where_fecha_g}   →  " AND g.fecha BETWEEN '...' AND '...'"│    ║
║  └────────────────────────────┬─────────────────────────────────┘    ║
║                               │ None (ninguna intención detectada)   ║
║                               │                                      ║
║  ┌────────────────────────────▼─────────────────────────────────┐    ║
║  │ NIVEL 2  ·  _classify_intent()  ·  1 LLM call  ·  ~2–3s    │    ║
║  │ ──────────────────────────────────────────────────────────   │    ║
║  │ Modelo:   gemini-2.5-flash  ·  temperatura: 0.0              │    ║
║  │ Cliente:  ChatGoogleGenerativeAI (langchain-google-genai)    │    ║
║  │ Salida:   JSON → {intent, sucursal, fecha_inicio, fecha_fin} │    ║
║  │ Parsing:  json.loads() + validación de nulos                 │    ║
║  │                                                              │    ║
║  │ _apply_params():                                             │    ║
║  │   _resolve_sucursal_id() → dict _SUCURSAL_ID_MAP             │    ║
║  │     CDMX=1, Monterrey=2, Guadalajara=3, Culiacán=4,          │    ║
║  │     Tijuana=5, Puebla=6, Querétaro=7, Mérida=8               │    ║
║  │   Validación fechas: re.match(r'^\d{4}-\d{2}-\d{2}$')       │    ║
║  │   Fallback: LIKE con reemplazo de vocales acentuadas         │    ║
║  │                                                              │    ║
║  │ Salvaguarda ciudad: _CIUDADES_SET + difflib fuzzy            │    ║
║  │   _UPGRADE_PARAM: mejor/peor_vendedor → _sucursal            │    ║
║  │                   mejor/peor_producto → _sucursal            │    ║
║  │                   peor/mejor_sucursal → _periodo             │    ║
║  │ Salvaguarda fecha: _MES_MAP + re.search(r'\b(202[0-9])\b')   │    ║
║  │   Si LLM no extrajo fecha pero hay mes en texto → construir  │    ║
║  └────────────────────────────┬─────────────────────────────────┘    ║
║                               │ "desconocido" / intent no en catálogo║
║                               │                                      ║
║  ┌────────────────────────────▼─────────────────────────────────┐    ║
║  │ NIVEL 3  ·  CrewAI Agent  ·  2–4 LLM calls  ·  ~8–15s      │    ║
║  │ ──────────────────────────────────────────────────────────   │    ║
║  │ Framework: crewai==0.28.8                                    │    ║
║  │ Modelo:    LLM_SQL = "gemini/gemini-2.0-flash"               │    ║
║  │ Agent:     sql_translator                                    │    ║
║  │   verbose=False · allow_delegation=False                     │    ║
║  │   role, goal, backstory definidos en get_agents()            │    ║
║  │                                                              │    ║
║  │ Tool 1 — schema_tool()   (@tool decorator crewai.tools)      │    ║
║  │   sqlite3.connect(DB_NAME)                                   │    ║
║  │   SELECT name, sql FROM sqlite_master WHERE type='table'     │    ║
║  │   Caché: _schema_cache (global, persiste toda la sesión)     │    ║
║  │   Pre-cargado en startup via warm_schema()                   │    ║
║  │                                                              │    ║
║  │ Tool 2 — query_tool()    (@tool decorator crewai.tools)      │    ║
║  │   Recibe SQL string del agente                               │    ║
║  │   Llama _execute_sql() → retorna markdown via pandas         │    ║
║  │                                                              │    ║
║  │ Crew:  Process.sequential · verbose=False                    │    ║
║  │ data_crew.kickoff()                                          │    ║
║  └─────────────────────────────────────────────────────────────┘    ║
╚══════════════════════════════╦═══════════════════════════════════════╝
                               ║ SQL query string
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║              BASE DE DATOS  ·  backend.py / _execute_sql()          ║
║                                                                      ║
║  Motor:      SQLite 3  (stdlib Python)                               ║
║  Archivo:    novatech.db  ·  solo lectura (SELECT)                   ║
║  Conexión:   sqlite3.connect(DB_NAME)                                ║
║  Consulta:   pandas.read_sql_query(query, conn)  →  DataFrame        ║
║  Estado:     last_query_result = df  (global, para turnos siguientes)║
║                                                                      ║
║  Formato $:  columnas con MONEY_KEYWORDS → f"${x:,.2f}"              ║
║    MONEY_KEYWORDS = [total, venta, monto, saldo, precio,             ║
║                      salario, gasto, cobranza, ingreso, desempeño]   ║
║    COUNT_KEYWORDS = [n°, num, #, conteo, registros, transacc, ...]   ║
║    → columnas COUNT excluidas del formato monetario                  ║
║                                                                      ║
║  TABLAS (8):                                                         ║
║    sucursales · empleados · productos · clientes                     ║
║    ventas · cobranza · gastos · inventario                           ║
║                                                                      ║
║  ÍNDICES (4):  creados por 01_pipeline.py                            ║
║    idx_ventas_fecha · idx_ventas_sucursal                            ║
║    idx_ventas_producto · idx_cobranza_estatus                        ║
║                                                                      ║
║  JOINs clave documentados en backstory del agente:                   ║
║    ventas.sucursal_id = sucursales.id                                ║
║    ventas.producto_id = productos.id                                 ║
║    ventas.empleado_id = empleados.id                                 ║
║    ventas.cliente_id  = clientes.id                                  ║
║    cobranza.venta_id  = ventas.id                                    ║
║    inventario.sucursal_id = sucursales.id                            ║
╚══════════════════════════════╦═══════════════════════════════════════╝
                               ║ pandas DataFrame
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║                  POST-PROCESAMIENTO  ·  backend.py                  ║
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │ _naturalize(df_fmt, question)                                │    ║
║  │  if len(df_fmt) == 1:                                        │    ║
║  │    → gemini-2.5-flash  ·  temperatura: 0.2                  │    ║
║  │    → prompt: presenta como hecho confirmado                  │    ║
║  │    → prohíbe: "no especifica", "no se indica", "no confirma" │    ║
║  │  else (N filas):                                             │    ║
║  │    → df_fmt.to_markdown(index=False)  (pandas, 0 LLM calls) │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │ _analyze(df_fmt, question)                                   │    ║
║  │  → gemini-2.5-flash  ·  temperatura: 0.3                    │    ║
║  │  → interpreta datos reales en 2–3 oraciones                  │    ║
║  │  → entrada: last_query_result del turno anterior             │    ║
║  │  → sin recomendaciones, sin inventar información             │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │ generate_chart() + _chart_to_tempfile()                      │    ║
║  │  Activado si: needs_chart() →  _CHART_WORDS set:             │    ║
║  │    {grafica, graficas, grafico, chart, visualiza,            │    ║
║  │     visualizacion, barra, barras, diagrama}                  │    ║
║  │                                                              │    ║
║  │  generate_chart():                                           │    ║
║  │    plotly.express==5.20.0  ·  px.bar()                       │    ║
║  │    Eje X: primera columna de texto                           │    ║
║  │    Eje Y: columna monetaria preferida (MONEY_PREF)           │    ║
║  │           descarta conteos (COUNT_EXCL)                      │    ║
║  │    color_continuous_scale="Blues"                            │    ║
║  │    hovertemplate personalizado con customdata                │    ║
║  │    template="plotly_white"                                   │    ║
║  │                                                              │    ║
║  │  _chart_to_tempfile():                                       │    ║
║  │    tempfile.NamedTemporaryFile(suffix='.png', delete=False)  │    ║
║  │    fig.write_image(width=750, height=420, format='png')      │    ║
║  │    kaleido (instalado aparte, no en requirements.txt)        │    ║
║  │    Retorna: (path, None) ok  /  (None, msg_error) si falla   │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
╚══════════════════════════════╦═══════════════════════════════════════╝
                               ║ texto markdown / imagen PNG tuple
                               ▼
                     ╔═════════════════╗
                     ║    FRONTEND     ║
                     ║  Gradio 4.26.0  ║
                     ╚═════════════════╝
```

---

### 1.2 Archivo 01_pipeline.py — Generación de Datos

```
╔══════════════════════════════════════════════════════════════════════╗
║           PIPELINE ETL  ·  01_pipeline.py  ·  ejecución única       ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIBRERÍAS:  sqlite3 · pandas==2.2.1 · numpy==1.26.4                ║
║              faker==24.4.0 · datetime · random · os · time          ║
║                                                                      ║
║  REPRODUCIBILIDAD:                                                   ║
║    Faker('es_MX')  seed=42                                           ║
║    np.random.seed(42)  ·  random.seed(42)                            ║
║                                                                      ║
║  PERÍODO DE DATOS:  2025-12-01  →  2026-04-30  (5 meses)            ║
║                                                                      ║
║  VOLÚMENES:                                                          ║
║    NUM_SUCURSALES = 8     NUM_EMPLEADOS = 100                        ║
║    NUM_PRODUCTOS  = 50    NUM_CLIENTES  = 500                        ║
║    NUM_VENTAS     = 15000 NUM_GASTOS    = 3000                       ║
║                                                                      ║
║  REGLAS DE NEGOCIO APLICADAS:                                        ║
║    · Gerentes: salario × 2                                           ║
║    · Clientes Mayoreo: descuento 15% en ventas                       ║
║    · ventas.sucursal_id  derivado de empleado.sucursal_id            ║
║    · ventas.total = cantidad × precio_unitario × (1 − descuento)     ║
║    · Cobranza: 80% Pagado · 15% Parcial · 5% Pendiente               ║
║    · Inventario: producto × sucursal (8 × 50 = 400 registros)        ║
║                                                                      ║
║  ETL:                                                                ║
║    E — Generación con Faker + NumPy → DataFrames pandas              ║
║    T — Cálculos de totales, descuentos, mapeos                       ║
║    L — DataFrame.to_sql() × 8 tablas → SQLite (novatech.db)          ║
║                                                                      ║
║  ÍNDICES CREADOS (cursor.execute):                                   ║
║    idx_ventas_fecha     ON ventas(fecha)                             ║
║    idx_ventas_sucursal  ON ventas(sucursal_id)                       ║
║    idx_ventas_producto  ON ventas(producto_id)                       ║
║    idx_cobranza_estatus ON cobranza(estatus)                         ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

### 1.3 Stack Tecnológico Completo

| Archivo | Librería / Módulo | Versión | Uso específico |
|---------|-------------------|---------|----------------|
| 01_pipeline.py | `sqlite3` | stdlib | Crear BD y ejecutar CREATE INDEX |
| 01_pipeline.py | `pandas` | 2.2.1 | DataFrames + `to_sql()` para carga |
| 01_pipeline.py | `numpy` | 1.26.4 | `random.choice`, `normal`, `randint` |
| 01_pipeline.py | `faker` | 24.4.0 | Nombres, emails, fechas sintéticas (`es_MX`) |
| 01_pipeline.py | `datetime`, `random`, `os`, `time` | stdlib | Control fechas, semilla, paths, timing |
| backend.py | `os`, `re`, `json`, `tempfile` | stdlib | Env vars, regex fechas, JSON parsing, archivos temp |
| backend.py | `sqlite3`, `unicodedata`, `difflib` | stdlib | BD, normalización texto, fuzzy matching |
| backend.py | `pandas` | 2.2.1 | `read_sql_query`, `to_markdown`, formato $ |
| backend.py | `plotly.express` | 5.20.0 | `px.bar`, hovertemplate, color scale |
| backend.py | `langchain-google-genai` | 1.0.2 | `ChatGoogleGenerativeAI` (LLM client) |
| backend.py | `crewai` | 0.28.8 | `Agent`, `Task`, `Crew`, `Process` |
| backend.py | `crewai.tools` | 0.28.8 | Decorador `@tool` para schema y query |
| backend.py | `kaleido` | (separado) | `fig.write_image()` → PNG export |
| 02_app.py | `gradio` | 4.26.0 | `gr.Blocks`, `gr.Chatbot`, `gr.Examples`, etc. |
| 02_app.py | `os` | stdlib | `os.path.exists(DB_NAME)` |
| Google API | `gemini-2.5-flash` | — | Guardrail (temp=0.0), Clasificador L2 (temp=0.0), Naturalizar (temp=0.2), Analizar (temp=0.3) |
| Google API | `gemini-2.0-flash` | — | Agente CrewAI L3 (`LLM_SQL`) |

---

## 2. Benchmark de Rendimiento

### 2.1 Latencia medida por componente

| Componente | Función | LLM Calls | Mín | Máx | Promedio |
|-----------|---------|:---------:|-----|-----|:--------:|
| Guardrail | `check_guardrails()` | 1 | 0.8 s | 1.5 s | ~1.0 s |
| Nivel 1 — intent | `match_intent()` | 0 | 5 ms | 120 ms | ~80 ms |
| SQLite query | `_execute_sql()` | 0 | 10 ms | 150 ms | ~50 ms |
| Nivel 2 — clasificador | `_classify_intent()` | 1 | 1.2 s | 3.5 s | ~2.2 s |
| Nivel 3 — CrewAI | `data_crew.kickoff()` | 2–4 | 7 s | 18 s | ~11 s |
| Naturalizar (1 fila) | `_naturalize()` | 1 | 0.8 s | 1.8 s | ~1.1 s |
| Naturalizar (tabla) | `df.to_markdown()` | 0 | < 5 ms | 10 ms | ~5 ms |
| Análisis | `_analyze()` | 1 | 1.0 s | 2.5 s | ~1.5 s |

### 2.2 Latencia total por escenario

| Escenario | Desglose | Total |
|-----------|----------|:-----:|
| Nivel 1 + tabla | Guardrail + SQL + `to_markdown` | **~1.1 s** |
| Nivel 2 + tabla | Guardrail + Clasificador + SQL + `to_markdown` | **~3.3 s** |
| Nivel 3 (exótica) | Guardrail + CrewAI + `to_markdown` | **~12 s** |
| Análisis "¿por qué?" | Guardrail + `_analyze` (datos en memoria) | **~2.5 s** |

### 2.3 Distribución de consultas por nivel

| Nivel | % del Total | Consultas típicas |
|-------|:-----------:|------------------|
| Nivel 1 | ~55% | Globales sin filtros: mejor producto, ventas por sucursal |
| Nivel 2 | ~38% | Con ciudad o período: vendedores de Monterrey en enero |
| Nivel 3 | ~7% | Exóticas: cruces no anticipados en el catálogo |

> **93% de las consultas** se resuelven sin activar CrewAI → latencia promedio **~2.5 s**

### 2.4 Impacto de la arquitectura de 3 niveles

| Métrica | Sin Nivel 2 | Con Nivel 2 | Mejora |
|---------|:-----------:|:-----------:|:------:|
| Latencia promedio | ~7.5 s | ~2.5 s | **−67%** |
| Costo LLM por consulta | 2–4 calls | 0–1 calls | **~−70%** |
| Riesgo SQL incorrecto | ~10% | ~1% | **−90%** |
