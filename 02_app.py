"""
02_app.py — Frontend: interfaz Gradio de NovaTech Panel Ejecutivo.
Toda la lógica de negocio, IA y datos vive en backend.py.
"""

import os
import gradio as gr
from backend import (
    DB_NAME,
    run_reports_crew,
    check_guardrails,
    needs_chart,
    generate_chart,
    _chart_to_tempfile,
    get_last_query_result,
    warm_schema,
)


# ── LÓGICA DEL CHAT ───────────────────────────────────────────────────────────

SQL_DESTRUCTIVOS = ["drop ", "delete ", "truncate ", "alter ", "update ",
                    "insert ", "create ", "replace "]

def chatbot_response(message, history):
    if not os.path.exists(DB_NAME):
        history.append([message, "Error: Base de datos no encontrada. Ejecuta 01_pipeline.py."])
        return "", history

    # Capa 1: comandos SQL destructivos
    mensaje_lower = message.lower()
    if any(cmd in mensaje_lower for cmd in SQL_DESTRUCTIVOS):
        history.append([message, "Solicitud bloqueada: no está permitido ejecutar comandos que modifiquen o eliminen datos."])
        return "", history

    # Atajo: si el usuario pide una gráfica de los datos anteriores, servirla directo
    _REFS_ANTERIORES = {"esa", "ese", "esos", "esas", "anterior", "anteriores",
                        "ultima", "ultimo", "ultimos", "lo mismo", "mismos", "misma"}
    msg_words = set(message.lower().split())
    if needs_chart(message) and bool(msg_words & _REFS_ANTERIORES):
        df = get_last_query_result()
        if df is not None:
            fig = generate_chart(df)
            if fig:
                img_path, err = _chart_to_tempfile(fig)
                if img_path:
                    history.append([message, "Aquí tienes la gráfica:"])
                    history.append([None, (img_path,)])
                    return "", history
                history.append([message, err or "No se pudo exportar la gráfica."])
                return "", history
            history.append([message, "No se pudo graficar estos datos (necesita al menos una columna numérica y una de texto)."])
            return "", history
        # Sin datos previos: caer al flujo normal

    # Capa 2: guardrail LLM
    decision = check_guardrails(message)
    if "BLOQUEAR" in decision:
        history.append([message, "Lo siento, solo puedo responder preguntas sobre inventario, ventas, gastos, empleados o sucursales de NovaTech."])
        return "", history

    contexto_historial = "Historial de la conversación:\\n"
    if history:
        for pre, res in history[-5:]:
            contexto_historial += f"Usuario: {pre}\\nAsistente: {res}\\n\\n"
    else:
        contexto_historial += "Sin historial previo.\\n"

    try:
        pregunta_con_contexto = f"{contexto_historial}\\nNueva pregunta del usuario: {message}"
        respuesta_final = run_reports_crew(pregunta_con_contexto, message)
        history.append([message, str(respuesta_final)])

        # Gráfica inline si el usuario la pidió en esta misma consulta
        if needs_chart(message):
            df = get_last_query_result()
            if df is not None:
                fig = generate_chart(df)
                if fig:
                    img_path, err = _chart_to_tempfile(fig)
                    if img_path:
                        history.append([None, (img_path,)])
                    else:
                        history.append([None, err or "No se pudo exportar la gráfica."])
                else:
                    history.append([None, "No se pudo graficar estos datos (necesita al menos una columna numérica y una de texto)."])
            else:
                history.append([None, "No hay datos para graficar."])

        return "", history
    except Exception as e:
        history.append([message, f"Ocurrió un error al procesar tu solicitud: {str(e)}"])
        return "", history


# ── ESTILOS ───────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
/* Fondo general */
.gradio-container { background: #f0f4f8 !important; max-width: 1400px !important; }

/* Tarjeta del chat */
#chat-panel {
    background: #ffffff;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
}

/* Etiquetas de sección */
#chat-panel label { font-weight: 600; color: #1e3a5f !important; }

/* Input de texto */
#msg-input textarea {
    border: 1.5px solid #90caf9 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}
#msg-input textarea:focus { border-color: #1565c0 !important; box-shadow: 0 0 0 2px rgba(21,101,192,0.15) !important; }

/* Botón Consultar */
#submit-btn {
    background: linear-gradient(135deg, #1565c0, #0d47a1) !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: none !important;
}
#submit-btn:hover { background: linear-gradient(135deg, #1976d2, #1565c0) !important; }

/* Botón Limpiar */
#clear-btn { border: 1.5px solid #90caf9 !important; color: #1565c0 !important; border-radius: 8px !important; }

/* Ejemplos */
.examples-holder { background: #ffffff; border-radius: 10px; padding: 10px; box-shadow: 0 1px 6px rgba(0,0,0,0.06); }
.example-button { border: 1px solid #bbdefb !important; color: #1565c0 !important; border-radius: 6px !important; font-size: 12px !important; }
.example-button:hover { background: #e3f2fd !important; }

/* Mensajes del chat */
.message.user   { background: #e3f2fd !important; color: #0d2b4e !important; border-radius: 10px !important; }
.message.bot    { background: #f1f8e9 !important; color: #1b2a1b !important; border-radius: 10px !important; }

/* Ocultar tiempo de respuesta */
.message-bubble-border time,
.message time,
.message .time,
.chatbot .message .timestamp,
.bot time, .user time,
[class*="message"] time { display: none !important; }

/* Login card */
#login-card {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.10);
    padding: 36px 40px;
    max-width: 440px;
    margin: 80px auto 0 auto;
}
#login-card label { font-weight: 600 !important; color: #1e3a5f !important; }
#login-card input {
    border: 1.5px solid #90caf9 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}
#login-card input:focus { border-color: #1565c0 !important; box-shadow: 0 0 0 2px rgba(21,101,192,0.15) !important; }
#login-btn {
    background: linear-gradient(135deg, #1565c0, #0d47a1) !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: none !important;
    margin-top: 6px !important;
}
#login-btn:hover { background: linear-gradient(135deg, #1976d2, #1565c0) !important; }
"""

USUARIOS_AUTORIZADOS = {
    "gerenteVentas": "ventas1234",
    "admin":         "novatech2024",
}

HEADER_HTML = """
<div style="
    background: linear-gradient(135deg, #0d2b4e 0%, #1565c0 100%);
    border-radius: 14px;
    padding: 28px 36px;
    margin-bottom: 8px;
">
    <h1 style="color:#ffffff;font-size:28px;font-weight:700;margin:0 0 8px 0;letter-spacing:-0.3px;">
        NovaTech &mdash; Panel Ejecutivo de Decisiones
    </h1>
    <p style="color:#90caf9;font-size:14px;margin:0;">
        Panel de reportes ejecutivos para Gerentes y Directores Comerciales
        &nbsp;&middot;&nbsp; Consulta ventas y gastos
        &nbsp;&middot;&nbsp; Analiza sucursales y productos
        &nbsp;&middot;&nbsp; Reportes por período y sucursal
    </p>
</div>
"""

SPINNER_HTML = """
<div style="display:flex; align-items:center; gap:10px; padding:6px 0 2px 2px;">
    <div style="
        width:20px; height:20px; border-radius:50%;
        border:3px solid #d0e4f7;
        border-top-color:#1565c0;
        animation:nt-spin 0.8s linear infinite;
        flex-shrink:0;
    "></div>
    <span style="color:#1565c0; font-size:13px; font-weight:500;">Analizando tu consulta...</span>
</div>
<style>
    @keyframes nt-spin { to { transform: rotate(360deg); } }
</style>
"""


# ── LOGIN ─────────────────────────────────────────────────────────────────────

def do_login(usuario, contrasena):
    if USUARIOS_AUTORIZADOS.get(usuario) == contrasena:
        return gr.update(visible=False), gr.update(visible=True), ""
    return gr.update(visible=True), gr.update(visible=False), (
        "<p style='color:#c62828;font-size:13px;text-align:center;margin:8px 0 0 0;'>"
        "Usuario o contraseña incorrectos.</p>"
    )


# ── INTERFAZ ──────────────────────────────────────────────────────────────────

with gr.Blocks(theme=gr.themes.Soft(), css=CUSTOM_CSS, title="NovaTech Panel Ejecutivo") as demo:

    # ── SECCIÓN LOGIN ──
    with gr.Column(visible=True) as login_section:
        with gr.Column(elem_id="login-card"):
            gr.HTML("""
            <div style="
                background: linear-gradient(135deg, #0d2b4e 0%, #1565c0 100%);
                border-radius: 12px;
                padding: 22px 28px;
                margin-bottom: 24px;
                text-align: center;
            ">
                <h1 style="color:#ffffff;font-size:22px;font-weight:700;margin:0 0 6px 0;letter-spacing:-0.3px;">
                    NovaTech Solutions
                </h1>
                <p style="color:#90caf9;font-size:13px;margin:0;">
                    Panel Ejecutivo de Decisiones &mdash; Acceso restringido
                </p>
            </div>
            """)
            login_user = gr.Textbox(label="Usuario", placeholder="Ingresa tu usuario")
            login_pass = gr.Textbox(label="Contraseña", placeholder="Ingresa tu contraseña", type="password")
            login_btn  = gr.Button("Ingresar", variant="primary", elem_id="login-btn")
            login_err  = gr.HTML("")

    # ── SECCIÓN PRINCIPAL (oculta hasta login) ──
    with gr.Column(visible=False) as main_section:
        gr.HTML(HEADER_HTML)

        with gr.Column(elem_id="chat-panel"):
            chatbot_comp = gr.Chatbot(height=320, label="Panel de Reportes", show_label=True)
            msg_input = gr.Textbox(
                placeholder="Ej: ¿Qué sucursal necesita atención urgente?",
                label="Tu pregunta",
                elem_id="msg-input",
                lines=1
            )
            spinner = gr.HTML(value="", visible=False, elem_id="spinner-container")
            with gr.Row():
                submit_btn = gr.Button("Consultar", variant="primary", elem_id="submit-btn", scale=3)
                clear_btn  = gr.ClearButton([msg_input, chatbot_comp], value="Limpiar", elem_id="clear-btn", scale=1)

        gr.Examples(
            examples=[
                "¿Qué sucursal tiene el peor desempeño en ventas?",
                "Muéstrame todos los vendedores de Tijuana y sus ventas en enero 2026",
                "¿Cuál fue el producto más vendido en Monterrey?",
                "¿Cuánta cobranza pendiente tenemos por sucursal?",
                "Compara el total de ventas de todas las sucursales",
                "¿Qué puesto de empleados genera más ingresos para el negocio?",
                "¿Cuánto se vendió en total en enero del 2026 en Guadalajara?",
                "Muéstrame el inventario con stock bajo"
            ],
            inputs=msg_input,
            label="Consultas frecuentes"
        )

        gr.HTML("""
        <div style="background:#fff8e1; border-left:4px solid #f9a825; border-radius:6px;
                    padding:10px 16px; margin-top:8px; font-size:12px; color:#5d4037; line-height:1.5;">
            <strong>Aviso:</strong> Las respuestas se generan con IA y se basan en datos de la BD de NovaTech.
            Valida las cifras clave con tu equipo antes de tomar decisiones estratégicas.
        </div>
        """)

        def lock():
            return gr.update(interactive=False), gr.update(interactive=False), gr.update(visible=True, value=SPINNER_HTML)

        def unlock():
            return gr.update(interactive=True), gr.update(interactive=True), gr.update(visible=False, value="")

        for trigger in [submit_btn.click, msg_input.submit]:
            trigger(
                lock, None, [msg_input, submit_btn, spinner], queue=False, show_progress="hidden"
            ).then(
                chatbot_response, [msg_input, chatbot_comp], [msg_input, chatbot_comp],
                show_progress="hidden"
            ).then(
                unlock, None, [msg_input, submit_btn, spinner], queue=False, show_progress="hidden"
            )

    # Eventos de login
    login_btn.click(do_login, [login_user, login_pass], [login_section, main_section, login_err])
    login_pass.submit(do_login, [login_user, login_pass], [login_section, main_section, login_err])


# ── PUNTO DE ENTRADA ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    warm_schema()
    print("\nLanzando NovaTech Panel Ejecutivo...")
    print("Podrás acceder desde tu navegador o desde el link público (share) de Gradio.")
    demo.launch(share=True)
