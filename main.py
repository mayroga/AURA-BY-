# ==============================
# AURA by May Roga LLC
# main.py — ESTIMADOS SOLO IA
# ==============================

import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
import stripe
from dotenv import load_dotenv

# ==============================
# CARGA ENV
# ==============================
load_dotenv()

app = FastAPI(title="AURA by May Roga LLC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# STRIPE
# ==============================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw",
}

LINK_DONACION = "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"

# ==============================
# IA
# ==============================
openai.api_key = os.getenv("OPENAI_API_KEY")
client_gemini = None
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    try:
        from google import genai
        client_gemini = genai.Client(api_key=gemini_key)
        print("✔ Gemini disponible")
    except Exception as e:
        print(f"[WARN] Gemini deshabilitado: {e}")

# ==============================
# INDEX
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
    <head>
    <title>AURA by May Roga LLC</title>
    </head>
    <body style="background:#111;color:#fff;font-family:Arial,sans-serif;text-align:center;">
        <h1>AURA — Estimados de Precios Médicos y Dentales</h1>
        <p>Ingrese su consulta y ZIP para obtener estimados educativos.</p>
    </body>
    </html>
    """

# ==============================
# ESTIMADO PRINCIPAL
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    zip_user: str = Form(None),
    lang: str = Form("es")
):
    idiomas = {"es": "Español", "en": "English", "ht": "Haitian Creole"}
    idioma = idiomas.get(lang, "Español")

    prompt = f"""
ERES **AURA**, EL CEREBRO DE ESTIMADOS EDUCATIVOS DE MAY ROGA LLC.

IDIOMA: {idioma}
CONSULTA DEL CLIENTE: {consulta}
UBICACIÓN (ZIP): {zip_user}

INSTRUCCIONES CRÍTICAS:
1. Genera un ESTIMADO EDUCATIVO de precios de procedimientos médicos y dentales.
2. Incluye comparaciones:
   - Precio CASH
   - Precio con SEGURO (estimado típico)
   - Copago (si aplica)
   - Ahorro estimado en USD (no porcentaje)
   - Posible ahorro viajando a otro condado o estado (incluir ZIP, condado y nombre del estado)
3. Presenta los 3 lugares más baratos: local, condado, estado y 5 más baratos a nivel nacional.
4. Indica claramente ZIP, condado y nombre del estado.
5. Haz la tabla oscura con letras legibles (negro #111 fondo, blanco #fff texto, azul #0cf cabeceras)
6. Mantén el contenido educativo, NO menciones de dónde se tomaron los datos.
7. Tono experto y protector del consumidor.
8. Incluye también el tiempo del servicio y el precio según plan:
   - Rápido $5.99 → 7 min
   - Standard $9.99 → 12 min
   - Special $19.99 → suscripción
9. Blindaje legal: Este reporte es educativo. No somos médicos ni aseguradoras.

DEVUELVE EL RESULTADO EN FORMATO HTML DE TABLA OSCURA LEGIBLE.
"""

    # ==============================
    # Motor de ejecución IA
    # ==============================
    # 1️⃣ Gemini si disponible
    if client_gemini:
        try:
            r = client_gemini.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt
            )
            html_result = r.text
            return HTMLResponse(content=html_result)
        except Exception as e:
            print(f"[WARN] Gemini falló: {e}")

    # 2️⃣ OpenAI fallback
    try:
        r = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
        )
        html_result = r.choices[0].message.content
        return HTMLResponse(content=html_result)
    except Exception as e:
        fallback_html = f"""
        <html>
        <body style='background:#111;color:#fff;font-family:Arial,sans-serif;'>
            <h2>Estimado General Educativo</h2>
            <p>Procedimiento: {consulta}</p>
            <table border="1" cellpadding="5" style="width:100%;color:#fff;background:#111;">
                <tr style="background:#0cf;color:#000;">
                    <th>Ubicación</th><th>ZIP</th><th>Condado</th><th>Estado</th><th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th>
                </tr>
                <tr><td>Local</td><td>{zip_user}</td><td>---</td><td>---</td><td>$XXX</td><td>$XXX</td><td>$XXX</td><td>$XXX</td></tr>
                <tr><td>Condado</td><td>---</td><td>---</td><td>---</td><td>$XXX</td><td>$XXX</td><td>$XXX</td><td>$XXX</td></tr>
                <tr><td>Estado</td><td>---</td><td>---</td><td>---</td><td>$XXX</td><td>$XXX</td><td>$XXX</td><td>$XXX</td></tr>
                <tr><td>Nacional</td><td>---</td><td>---</td><td>---</td><td>$XXX</td><td>$XXX</td><td>$XXX</td><td>$XXX</td></tr>
            </table>
            <p>Este es un estimado educativo.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=fallback_html)

# ==============================
# STRIPE CHECKOUT
# ==============================
@app.post("/create-checkout-session")
async def checkout(plan: str = Form(...)):
    if plan == "donacion":
        return {"url": LINK_DONACION}

    try:
        mode = "subscription" if plan == "special" else "payment"
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
            mode=mode,
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/",
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==============================
# LOGIN ADMIN
# ==============================
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin")
    if user == ADMIN_USER and pw == ADMIN_PASS:
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "denied"})
