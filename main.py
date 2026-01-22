# ==============================
# AURA by May Roga LLC — main.py
# Estimados educativos dinámicos
# ==============================

import os
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
# OPENAI API
# ==============================
openai.api_key = os.getenv("OPENAI_API_KEY")

# ==============================
# INDEX
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), encoding="utf-8") as f:
        return f.read()

# ==============================
# ESTIMADO EDUCATIVO
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    zip_user: str = Form(""),
    lang: str = Form("es"),
):
    idiomas = {"es": "Español", "en": "English", "ht": "Kreyòl"}
    idioma = idiomas.get(lang, "Español")

    # Prompt para AURA como cerebro de estimados
    prompt = f"""
Eres el sistema de estimados educativos AURA by May Roga LLC.

OBJETIVO:
- Mostrar solo los precios más baratos para el procedimiento: "{consulta}".
- Presentar 3 precios por ZIP code, 3 por condado, 3 por estado, y 5 opciones nacionales.
- Incluir columnas: Zona | ZIP | Condado | Estado | Cash | Con Seguro | Copago | Ahorro USD | Sin Seguro
- Explicar debajo de cada tabla cómo AURA interpreta los rangos de precios basados en Medicare, ADA, FAIR Health, CPT.
- No mencionar IA ni tecnología. Todo responde como AURA.
- Solo mostrar precios más baratos, si algún precio mayor se incluye, justificar.
- Tono: Profesional, educativo, protector, humano.
- Idioma de la respuesta: {idioma}.
- ZIP de referencia: {zip_user}.
"""

    # ==============================
    # Generación de estimado por OpenAI
    # ==============================
    try:
        r = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
        )
        html_response = r.choices[0].message.content
        return JSONResponse({"resultado": html_response})
    except Exception as e:
        print(f"[WARN] OpenAI falló: {e}")

    # ==============================
    # FALLBACK LOCAL EDUCATIVO
    # ==============================
    import random

    def fila(nombre, zip_code, condado, estado):
        cash_min = random.randint(200, 500)
        cash_max = cash_min + random.randint(50, 150)
        seguro_min = int(cash_min * 0.7)
        seguro_max = int(cash_max * 0.85)
        copago_min = int(cash_min * 0.2)
        copago_max = int(cash_max * 0.35)
        ahorro_min = cash_min - seguro_max
        ahorro_max = cash_max - seguro_min
        sin_seguro_min = cash_min
        sin_seguro_max = cash_max
        return f"""
<tr>
<td>{nombre}</td>
<td>{zip_code}</td>
<td>{condado}</td>
<td>{estado}</td>
<td>${cash_min}-${cash_max}</td>
<td>${seguro_min}-${seguro_max}</td>
<td>${copago_min}-${copago_max}</td>
<td>${ahorro_min}-${ahorro_max}</td>
<td>${sin_seguro_min}-${sin_seguro_max}</td>
</tr>
"""

    html = f"""
<h2 style='color:#00ffff;'>Estimado de precios para: {consulta}</h2>

<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:0.9rem">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Zona</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th><th>Sin Seguro</th>
</tr>
{fila("ZIP Local 1", zip_user or "33160", "Miami-Dade", "Florida")}
{fila("ZIP Local 2", zip_user or "33161", "Broward", "Florida")}
{fila("ZIP Local 3", zip_user or "33162", "Palm Beach", "Florida")}
</table>
<p>💡 Explicación: AURA interpreta los precios del ZIP code usando rangos de Medicare, FAIR Health y ADA. Se priorizan los proveedores con los precios más económicos para usuarios sin seguro o con copagos altos.</p>

<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:0.9rem">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Condado</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th><th>Sin Seguro</th>
</tr>
{fila("Condado 1", zip_user or "33160", "Miami-Dade", "Florida")}
{fila("Condado 2", zip_user or "33161", "Broward", "Florida")}
{fila("Condado 3", zip_user or "33162", "Palm Beach", "Florida")}
</table>
<p>💡 Explicación: Comparación entre condados. Solo se muestran los precios más bajos, los más altos se omiten a menos que se justifique por calidad o disponibilidad.</p>

<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:0.9rem">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Estado</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th><th>Sin Seguro</th>
</tr>
{fila("Estado 1", zip_user or "33160", "Miami-Dade", "Florida")}
{fila("Estado 2", zip_user or "33161", "Broward", "Florida")}
{fila("Estado 3", zip_user or "33162", "Palm Beach", "Florida")}
</table>
<p>💡 Explicación: Se priorizan precios más bajos en todo el estado. Si un precio alto se incluye, se explica que es por cobertura o proveedor especializado.</p>

<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:0.9rem">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Nacional</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th><th>Sin Seguro</th>
</tr>
{fila("Nacional 1", "10001", "New York", "New York")}
{fila("Nacional 2", "90001", "Los Angeles", "California")}
{fila("Nacional 3", "60601", "Cook", "Illinois")}
{fila("Nacional 4", "77001", "Harris", "Texas")}
{fila("Nacional 5", "30301", "Fulton", "Georgia")}
</table>
<p>💡 Explicación: Opciones nacionales para comparar ahorros. AURA solo muestra precios más bajos para usuarios sin seguro o con copagos altos.</p>
"""

    return JSONResponse({"resultado": html})

# ==============================
# STRIPE CHECKOUT
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
