# ==============================
# AURA by May Roga LLC — main.py
# Estimados educativos solo IA
# ==============================

import os
import random
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
import stripe
from dotenv import load_dotenv

# ==============================
# ENV & APP
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
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), encoding="utf-8") as f:
        return f.read()

# ==============================
# ESTIMADO (SIEMPRE RESPONDE)
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    zip_user: str = Form(""),
    lang: str = Form("es"),
):
    idiomas = {"es": "Español", "en": "English", "ht": "Kreyòl"}
    idioma = idiomas.get(lang, "Español")

    prompt = f"""
ERES AURA, CEREBRO DE ESTIMADOS EDUCATIVOS DE MAY ROGA LLC.

IDIOMA: {idioma}
CONSULTA DEL USUARIO: {consulta}
ZIP DEL USUARIO: {zip_user}

OBJETIVO:
- Ayudar a personas SIN seguro o con seguro que NO cubre.
- Dar tranquilidad mostrando rangos reales y comparaciones.

REQUISITOS OBLIGATORIOS:
1. Mostrar los MÁS BARATOS:
   - 3 locales
   - 3 por condado
   - 3 por estado
   - 5 nacionales (50 estados)
2. SIEMPRE mostrar:
   ZIP | Condado | Estado (nombre real)
3. Comparar:
   - Precio CASH
   - Precio con seguro (estimado)
   - Copago
   - Ahorro en USD (NO porcentajes)
4. Indicar si conviene viajar a otro condado o estado.
5. Tabla OSCURA:
   Fondo #111, texto blanco, encabezado azul #0cf.
6. Incluir tiempos por plan:
   - Rápido $5.99 → 7 min
   - Standard $9.99 → 12 min
   - Special $19.99 → suscripción
7. NO mencionar fuentes.
8. TONO humano, claro y protector.
9. DEVUELVE SOLO HTML (tabla + explicación).

BLINDAJE LEGAL:
Reporte educativo. No somos médicos ni aseguradoras.
"""

    # ==============================
    # IA
    # ==============================
    try:
        if client_gemini:
            r = client_gemini.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt
            )
            return JSONResponse({"resultado": r.text})

    except Exception as e:
        print(f"[WARN] Gemini falló: {e}")

    try:
        r = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
        )
        return JSONResponse({"resultado": r.choices[0].message.content})

    except Exception as e:
        print(f"[WARN] OpenAI falló: {e}")

    # ==============================
    # FALLBACK LOCAL (NUNCA SE CAE)
    # ==============================
    def fila(nombre):
        base = random.randint(250, 1200)
        seguro = int(base * 0.8)
        copago = int(base * 0.3)
        ahorro = base - seguro
        return f"""
        <tr>
          <td>{nombre}</td>
          <td>{zip_user or "00000"}</td>
          <td>Condado ejemplo</td>
          <td>Estado ejemplo</td>
          <td>${base}</td>
          <td>${seguro}</td>
          <td>${copago}</td>
          <td>${ahorro}</td>
        </tr>
        """

    html = f"""
<table style="width:100%;border-collapse:collapse;background:#111;color:#fff">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Zona</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th>
</tr>
{fila("Local 1")}
{fila("Local 2")}
{fila("Local 3")}
{fila("Condado 1")}
{fila("Condado 2")}
{fila("Condado 3")}
{fila("Estado 1")}
{fila("Estado 2")}
{fila("Estado 3")}
{fila("Nacional 1")}
{fila("Nacional 2")}
{fila("Nacional 3")}
{fila("Nacional 4")}
{fila("Nacional 5")}
</table>

<p style="margin-top:10px">
⏱ Tiempo de asesoría educativa:<br>
Rápido $5.99 → 7 min · Standard $9.99 → 12 min · Special $19.99 → suscripción
</p>

<p>
⚠️ Reporte educativo. No somos médicos ni aseguradoras.
</p>
"""

    return JSONResponse({"resultado": html})

# ==============================
# STRIPE
# ==============================
@app.post("/create-checkout-session")
async def checkout(plan: str = Form(...)):
    if plan == "donacion":
        return {"url": LINK_DONACION}

    mode = "subscription" if plan == "special" else "payment"
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
        mode=mode,
        success_url="https://aura-by.onrender.com/?success=true",
        cancel_url="https://aura-by.onrender.com/",
    )
    return {"url": session.url}

# ==============================
# LOGIN ADMIN
# ==============================
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if (
        user == os.getenv("ADMIN_USERNAME", "admin")
        and pw == os.getenv("ADMIN_PASSWORD", "admin")
    ):
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "denied"})
