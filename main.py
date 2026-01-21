# ==============================
# AURA by May Roga LLC
# main.py — Estimados educativos sin DB
# ==============================

import os
import stripe
from datetime import datetime
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv

# ==============================
# CARGA ENV
# ==============================
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="AURA by May Roga LLC")

# ==============================
# CORS
# ==============================
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
    <head><title>AURA by May Roga LLC</title></head>
    <body style="background-color:#0d1117;color:#c9d1d9;font-family:sans-serif;text-align:center;">
    <h1>AURA — Estimados Educativos</h1>
    <p>Use el endpoint /estimado para obtener precios educativos en USA.</p>
    </body>
    </html>
    """

# ==============================
# ESTIMADO PRINCIPAL
# ==============================
@app.post("/estimado", response_class=HTMLResponse)
async def estimado(
    consulta: str = Form(...),
    lang: str = Form("es"),
    zip_user: str = Form(None)
):
    idiomas = {"es":"Español","en":"English","ht":"Haitian Creole"}
    idioma = idiomas.get(lang,"Español")

    prompt = f"""
ERES **AURA**, CEREBRO DE ESTIMADOS EDUCATIVOS DE MAY ROGA LLC.
IDIOMA: {idioma}
CONSULTA DEL CLIENTE: {consulta}
ZIP USUARIO: {zip_user}

INSTRUCCIONES:
1. Genera estimados educativos de precios médicos/dentales.
2. Muestra comparaciones por ZIP, Condado, Estado y Nacional.
3. Incluye precios: Cash, Seguro, Copago.
4. Calcula ahorro estimado en dólares (no porcentaje).
5. Incluye nombres de ZIP, Condado y Estado.
6. Muestra tabla HTML legible con fondo oscuro y letras claras.
7. No menciones AMA, ADA ni CMS, solo di "educativo".
8. Mantén un tono protector del consumidor.

BLINDAJE LEGAL:
Este es un estimado educativo.
No somos médicos ni aseguradoras.
El precio final lo determina el proveedor.
"""

    # ==============================
    # MOTOR IA: Gemini -> OpenAI
    # ==============================
    resultado_text = ""
    if client_gemini:
        try:
            r = client_gemini.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt
            )
            resultado_text = r.text
        except Exception as e:
            print(f"[WARN] Gemini falló: {e}")

    if not resultado_text:
        try:
            r = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role":"user","content":prompt}],
                temperature=0.35
            )
            resultado_text = r.choices[0].message.content
        except Exception as e:
            resultado_text = f"""
⚠️ Estimado educativo generado de forma general:
Procedimiento: {consulta}
Rango típico USA:
- Bajo: $XXX
- Medio: $XXX
- Alto: $XXX
Este es un estimado educativo.
"""

    # ==============================
    # ENVOLVER EN HTML OSCURO
    # ==============================
    html = f"""
    <html>
    <head>
    <title>Estimado AURA</title>
    <style>
    body {{
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: Arial, sans-serif;
        padding: 20px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
    }}
    th, td {{
        border: 1px solid #30363d;
        padding: 8px;
        text-align: left;
    }}
    th {{
        background-color: #21262d;
        color: #f0f6fc;
    }}
    tr:nth-child(even) {{
        background-color: #161b22;
    }}
    tr:hover {{
        background-color: #30363d;
    }}
    </style>
    </head>
    <body>
    <h2>Estimado educativo — {consulta}</h2>
    <p>Idioma: {idioma} | ZIP: {zip_user}</p>
    <div>{resultado_text}</div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

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
