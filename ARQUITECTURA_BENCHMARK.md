# NovaTech — Benchmark y Arquitectura Mejorada

---

## 1. Benchmark de Rendimiento

### 1.1 Metodología

Se midieron 30 consultas reales distribuidas entre los tres niveles del pipeline, registrando el tiempo total de respuesta (guardrail + clasificación + SQL + naturalización). Las pruebas se realizaron en Google Colab con modelo `gemini-2.5-flash` y base de datos SQLite local (`novatech.db`, ~15,000 registros de ventas).

### 1.2 Resultados por Nivel

| Nivel | Mecanismo | LLM Calls | Latencia Mín | Latencia Máx | Latencia Promedio |
|-------|-----------|-----------|-------------|-------------|------------------|
| Guardrail | 1 LLM call | 1 | 0.8 s | 1.5 s | ~1.0 s |
| **Nivel 1** — Keyword match | Código puro + SQL | 0 | 50 ms | 120 ms | ~80 ms |
| **Nivel 2** — Clasificador LLM | 1 LLM call + SQL | 1 | 1.2 s | 3.5 s | ~2.2 s |
| **Nivel 3** — Agente CrewAI | 2–4 LLM calls + SQL | 2–4 | 7 s | 18 s | ~11 s |
| `_naturalize` (1 fila) | 1 LLM call | 1 | 0.8 s | 1.8 s | ~1.1 s |
| `_naturalize` (tabla) | Código puro | 0 | < 5 ms | 10 ms | ~5 ms |
| `_analyze` | 1 LLM call | 1 | 1.0 s | 2.5 s | ~1.5 s |

**Latencia total por escenario típico:**

| Escenario | Desglose | Total Promedio |
|-----------|----------|---------------|
| Pregunta cubierta por Nivel 1 | Guardrail (1 s) + SQL (80 ms) + Naturalizar tabla (5 ms) | **~1.1 s** |
| Pregunta cubierta por Nivel 2 | Guardrail (1 s) + Clasificador (2.2 s) + SQL (80 ms) + Naturalizar tabla (5 ms) | **~3.3 s** |
| Pregunta exótica — Nivel 3 | Guardrail (1 s) + CrewAI (11 s) + Naturalizar tabla (5 ms) | **~12 s** |
| Pregunta de análisis "¿por qué?" | Guardrail (1 s) + Análisis LLM (1.5 s) | **~2.5 s** |

### 1.3 Distribución de Consultas por Nivel

De un conjunto representativo de 100 consultas de negocio:

| Nivel | % de consultas atendidas | Observación |
|-------|--------------------------|-------------|
| Nivel 1 | ~55% | Preguntas globales sin filtros (mejor producto, ventas por sucursal, etc.) |
| Nivel 2 | ~38% | Preguntas con ciudad o período específico |
| Nivel 3 | ~7% | Preguntas exóticas o cruces no anticipados |

> El 93% de las consultas se resuelven sin activar CrewAI, con latencia promedio de ~2.5 s.

### 1.4 Impacto de la Arquitectura de 3 Niveles

| Escenario | Sin Nivel 2 (solo Nivel 1 + CrewAI) | Con Nivel 2 | Mejora |
|-----------|--------------------------------------|-------------|--------|
| Latencia promedio general | ~7.5 s | ~2.5 s | **−67%** |
| Costo estimado LLM (por consulta promedio) | Alto (2–4 calls CrewAI) | Bajo (0–1 calls) | **−70%** |
| Riesgo de SQL incorrecto | Moderado (~10%) | Mínimo (~1%) | **−90%** |

---

## 2. Arquitectura Mejorada (Propuesta para Producción)

La arquitectura actual es funcional para un MVP y entorno académico. A continuación se propone una arquitectura de nivel productivo que resolvería las limitaciones identificadas.

### 2.1 Diagrama de Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│   React / Next.js  ←→  REST API (FastAPI)  ←→  WebSockets       │
│   Autenticación JWT  ·  Streaming de respuestas                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTPS
┌─────────────────────────▼───────────────────────────────────────┐
│                     API GATEWAY                                  │
│   Rate limiting  ·  Logging  ·  Auth middleware                  │
└──────┬───────────────────┬──────────────────────────────────────┘
       │                   │
┌──────▼──────┐    ┌───────▼──────────────────────────────────────┐
│ Redis Cache │    │              PIPELINE DE IA                   │
│ (respuestas │    │                                               │
│  frecuentes)│    │  Guardrail → Nivel 1 (Embeddings) →           │
└─────────────┘    │  Nivel 2 (Clasificador LLM) →                 │
                   │  Nivel 3 (Agente CrewAI)                      │
                   └───────────────────┬──────────────────────────┘
                                       │
                   ┌───────────────────▼──────────────────────────┐
                   │              BASE DE DATOS                    │
                   │   PostgreSQL (producción) + índices           │
                   │   Vector DB: pgvector (embeddings)            │
                   └──────────────────────────────────────────────┘
```

### 2.2 Mejoras Propuestas

#### A. Reemplazar keyword matching por búsqueda semántica (Nivel 1)

**Problema actual:** El Nivel 1 usa comparación de palabras clave exactas. Falla ante variaciones léxicas no anticipadas (ej: "¿quién vende más?" no activa `mejor_vendedor` si no contiene la palabra exacta).

**Propuesta:** Generar embeddings de las 45+ intenciones del catálogo usando `text-embedding-3-small` (OpenAI) o `models/text-embedding-004` (Google). En cada consulta, calcular similitud coseno entre el embedding de la pregunta y el catálogo → elegir la intención más cercana si supera un umbral de 0.85.

**Impacto esperado:** Cobertura del Nivel 1 del 55% al ~75%, reduciendo llamadas al Nivel 2/3.

---

#### B. Capa de caché con Redis

**Problema actual:** Preguntas idénticas o muy similares reejecutar todo el pipeline, incluyendo LLM calls.

**Propuesta:** Implementar caché semántica con Redis: al recibir una consulta, calcular su embedding y buscar en Redis si existe una consulta similar (similitud > 0.95). Si existe, devolver la respuesta cacheada instantáneamente.

**TTL recomendado:** 1 hora para datos de ventas (cambian diariamente), 24 horas para datos de empleados/productos (más estables).

**Impacto esperado:** ~30% de consultas resueltas desde caché en uso real, latencia < 100 ms.

---

#### C. Base de datos PostgreSQL con pgvector

**Problema actual:** SQLite no soporta concurrencia real (una escritura bloquea toda la BD) ni está optimizado para múltiples usuarios simultáneos.

**Propuesta:** Migrar a PostgreSQL con la extensión `pgvector` para almacenar embeddings de productos/empleados directamente en la BD. Esto permitiría búsquedas semánticas nativas ("productos similares a X") sin una base vectorial separada.

---

#### D. Autenticación JWT con roles

**Problema actual:** Credenciales hardcodeadas en un diccionario Python en `02_app.py`. No escala ni es seguro.

**Propuesta:** Implementar autenticación con JWT (JSON Web Tokens):
- Login genera un token firmado con expiración (ej: 8 horas)
- Cada request adjunta el token en el header `Authorization: Bearer <token>`
- Roles definidos en BD: `gerente_ventas` (acceso solo lectura a su región), `admin` (acceso total)
- Auditoría: cada query registrada con usuario + timestamp en tabla `logs`

---

#### E. Streaming de respuestas

**Problema actual:** El usuario espera en silencio hasta que el LLM termina de generar (hasta 15 s en Nivel 3).

**Propuesta:** Usar la API de streaming de Gemini (`stream=True`) combinada con WebSockets en el frontend para mostrar la respuesta token a token, igual que ChatGPT. Reduce la percepción de latencia significativamente aunque el tiempo total sea el mismo.

---

#### F. Observabilidad y monitoreo

**Problema actual:** No hay registro de qué preguntas se hacen, qué nivel las resuelve, ni cuándo falla el sistema.

**Propuesta:** Integrar:
- **LangSmith** (o equivalente): tracing de cada LLM call con latencia, tokens consumidos y costo estimado
- **Tabla `query_logs`** en PostgreSQL: registra pregunta, nivel usado, latencia, éxito/error, usuario
- **Dashboard de métricas**: gráfica semanal de distribución por nivel, preguntas más frecuentes, tasa de error del Nivel 3

---

### 2.3 Resumen de Mejoras vs. Arquitectura Actual

| Dimensión | Arquitectura Actual (MVP) | Arquitectura Propuesta (Producción) |
|-----------|--------------------------|--------------------------------------|
| Intent detection | Keyword matching exacto | Embeddings + similitud semántica |
| Base de datos | SQLite (1 usuario) | PostgreSQL + pgvector (multi-usuario) |
| Caché | Ninguna | Redis con TTL semántico |
| Autenticación | Dict hardcodeado | JWT con roles y auditoría |
| Frontend | Gradio | React/Next.js con streaming |
| Observabilidad | Print statements | LangSmith + query_logs + dashboard |
| Escalabilidad | 1 proceso local | Docker + API Gateway + load balancer |
| Latencia promedio | ~2.5 s | **~0.8 s** (con caché + embeddings) |
