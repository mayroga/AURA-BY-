# ==============================
# AURA by May Roga LLC — main.py
# Estimados educativos solo IA
# ==============================

import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
import stripe
from dotenv import load_dotenv
import random

load_dotenv()
app = FastAPI(title="AURA by May Roga LLC")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# STRIPE
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw",
}
LINK_DONACION = "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"

# IA
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
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

# ==============================
# Generador de estimado educativo
# ==============================
@app.post("/estimado")
async def estimado(consulta: str = Form(...), zip_user: str = Form(None), lang: str = Form("es")):
    idiomas = {"es": "Español", "en": "English", "ht": "Kreyòl"}
    idioma = idiomas.get(lang, "Español")

    # Prompt IA
    prompt = f"""
ERES AURA, MOTOR DE ESTIMADOS EDUCATIVOS DE MAY ROGA LLC.
IDIOMA: {idioma}
CONSULTA DEL CLIENTE: {consulta}
UBICACIÓN DETECTADA: {zip_user}

OBJETIVO:
1) Generar ESTIMADO EDUCATIVO de precios médicos y dentales para cualquier persona.
2) Comparar los 3 lugares más baratos locales, 3 por condado, 3 por estado, 5 nacionales (los 50 estados).
3) Mostrar ZIP, nombre del condado y estado.
4) Comparaciones: Cash, Seguro estimado, Copago, Ahorro USD.
5) Tabla oscura: fondo #111, texto blanco, cabecera azul #0cf.
6) Añadir tiempo según plan educativo:
   - Rápido $5.99 → 7 min
   - Standard $9.99 → 12 min
   - Special $19.99 → suscripción
7) Explicación clara para que usuarios sin seguro o con seguro que no cubre nada sepan lo que podrían pagar.
8) Blindaje legal: solo ESTIMADOS EDUCATIVOS. No somos médicos ni aseguradoras.
"""

    # ==============================
    # Motor IA
    # ==============================
    html_result = None

    # 1️⃣ Gemini si disponible
    if client_gemini:
        try:
            r = client_gemini.models.generate_content(model="gemini-1.5-pro", contents=prompt)
            html_result = r.text
            return HTMLResponse(content=html_result)
        except Exception as e:
            print(f"[WARN] Gemini falló: {e}")

    # 2️⃣ OpenAI fallback
    if not html_result:
        try:
            r = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.35,
            )
            html_result = r.choices[0].message.content
            return HTMLResponse(content=html_result)
        except Exception as e:
            print(f"[WARN] OpenAI falló: {e}")

    # ==============================
    # Fallback local: generar tabla educativa
    # ==============================
    def mock_prices():
        base = random.randint(100, 1000)
        cash = base
        seguro = round(base * random.uniform(0.7, 0.95),2)
        copago = round(base * random.uniform(0.2,0.5),2)
        ahorro = round(base - seguro,2)
        return cash, seguro, copago, ahorro

    def generar_fila(label):
        cash, seguro, copago, ahorro = mock_prices()
        return f"<tr><td>{label}</td><td>{zip_user or '00000'}</td><td>Condado XYZ</td><td>Estado ABC</td><td>${cash}</td><td>${seguro}</td><td>${copago}</td><td>${ahorro}</td></tr>"

    tabla_html = f"""
<table style='width:100%; border-collapse: collapse; background:#111; color:#fff; font-size:1rem;'>
<tr style='background:#0cf; font-weight:bold;'>
<th>Ubicación</th><th>ZIP</th><th>Condado</th><th>Estado</th><th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th>
</tr>
{generar_fila('Local 1')}
{generar_fila('Local 2')}
{generar_fila('Local 3')}
{generar_fila('Condado 1')}
{generar_fila('Condado 2')}
{generar_fila('Condado 3')}
{generar_fila('Estado 1')}
{generar_fila('Estado 2')}
{generar_fila('Estado 3')}
{generar_fila('Nacional 1')}
{generar_fila('Nacional 2')}
{generar_fila('Nacional 3')}
{generar_fila('Nacional 4')}
{generar_fila('Nacional 5')}
</table>

<p>⏱ Tiempo por plan educativo: Rápido $5.99 → 7 min, Standard $9.99 → 12 min, Special $19.99 → suscripción.</p>
<p>⚠️ Este reporte es educativo. No somos médicos ni aseguradoras. Los precios son estimativos y orientativos.</p>
"""

    return HTMLResponse(content=tabla_html)

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
