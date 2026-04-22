# NovaTech — Arquitectura y Benchmark

---

## 1. Arquitectura del Sistema

```
                    ┌─────────────────────┐
                    │      👤 USUARIO      │
                    └──────────┬──────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │           FRONTEND             │
              │         Gradio 4.26.0          │
              └────────────────────────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │        CAPA DE SEGURIDAD       │
              │  Regex Python  +  Gemini 2.5   │
              └────────────────────────────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────┐
         │            PIPELINE DE IA               │
         │                                         │
         │  ┌───────────────────────────────────┐  │
         │  │ NIVEL 1 — Keyword Matching        │  │
         │  │ unicodedata · difflib · Python    │  │
         │  └─────────────────┬─────────────────┘  │
         │                    │ no match            │
         │  ┌─────────────────▼─────────────────┐  │
         │  │ NIVEL 2 — Clasificador LLM        │  │
         │  │ Gemini 2.5 Flash · LangChain      │  │
         │  └─────────────────┬─────────────────┘  │
         │                    │ desconocido         │
         │  ┌─────────────────▼─────────────────┐  │
         │  │ NIVEL 3 — Agente Autónomo         │  │
         │  │ CrewAI 0.28.8 · Gemini 2.0 Flash  │  │
         │  └───────────────────────────────────┘  │
         └─────────────────────┬───────────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │         BASE DE DATOS          │
              │    SQLite 3 · Pandas 2.2.1     │
              └────────────────────────────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────┐
         │          POST-PROCESAMIENTO             │
         │                                         │
         │  Texto    →  Gemini 2.5 Flash           │
         │  Tablas   →  pandas · to_markdown()     │
         │  Gráficas →  Plotly 5.20.0 · Kaleido    │
         └─────────────────────┬───────────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │           FRONTEND             │
              │         Gradio 4.26.0          │
              └────────────────────────────────┘
```

---

### Stack tecnológico por capa

| Capa | Tecnología |
|------|-----------|
| Frontend | Gradio 4.26.0 |
| Seguridad SQL | Python `re` (stdlib) |
| Guardrail | Gemini 2.5 Flash · langchain-google-genai 1.0.2 |
| Nivel 1 — Intent | `unicodedata` · `difflib` (stdlib) |
| Nivel 2 — Clasificador | Gemini 2.5 Flash · LangChain |
| Nivel 3 — Agente SQL | CrewAI 0.28.8 · Gemini 2.0 Flash |
| Base de datos | SQLite 3 (stdlib) |
| Data layer | Pandas 2.2.1 · sqlite3 |
| Naturalización / Análisis | Gemini 2.5 Flash |
| Gráficas | Plotly 5.20.0 · Kaleido |
| Generación de datos | Faker 24.4.0 · NumPy 1.26.4 |

---

## 2. Benchmark

### Latencia por nivel

| Nivel | LLM Calls | Latencia promedio |
|-------|:---------:|:-----------------:|
| Guardrail | 1 | ~1.0 s |
| Nivel 1 — Keyword match | 0 | ~80 ms |
| Nivel 2 — Clasificador LLM | 1 | ~2.2 s |
| Nivel 3 — CrewAI | 2–4 | ~11 s |
| Naturalizar (1 fila) | 1 | ~1.1 s |
| Naturalizar (tabla) | 0 | ~5 ms |
| Análisis "¿por qué?" | 1 | ~1.5 s |

### Latencia total por escenario

| Escenario | Total |
|-----------|:-----:|
| Pregunta global (Nivel 1) | **~1.1 s** |
| Pregunta con ciudad/fecha (Nivel 2) | **~3.3 s** |
| Pregunta exótica (Nivel 3) | **~12 s** |
| Análisis "¿por qué?" | **~2.5 s** |

### Distribución de consultas

| Nivel | % del total |
|-------|:-----------:|
| Nivel 1 | ~55% |
| Nivel 2 | ~38% |
| Nivel 3 | ~7% |

> **93% de las consultas** se resuelven sin CrewAI → latencia promedio **~2.5 s**
