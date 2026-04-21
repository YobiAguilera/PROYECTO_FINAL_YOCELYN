# NovaTech — Panel Ejecutivo de Decisiones

Herramienta de Business Intelligence conversacional para gerentes y directores de NovaTech Solutions. Permite consultar ventas, gastos, inventario, empleados y cobranza en lenguaje natural, con visualizaciones automáticas y análisis interpretativo.

## Requisitos

- Python 3.10+
- API Key de Google Gemini → variable de entorno `GEMINI_API_KEY`

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

**Paso 1 — Generar la base de datos** (solo la primera vez):
```bash
python 01_pipeline.py
```

**Paso 2 — Lanzar la aplicación:**
```bash
python 02_app.py
```

Se abrirá un link local y uno público (Gradio share) en la terminal.

## Credenciales de acceso

| Usuario | Contraseña |
|---------|-----------|
| `gerenteVentas` | `ventas1234` |
| `admin` | `novatech2024` |

## Documentación técnica

Ver [DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md) para arquitectura detallada, métricas de latencia y análisis de alucinaciones.
