import os
import sqlite3
import stripe
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv
import requests
import pandas as pd
from datetime import datetime

load_dotenv()
app = FastAPI()

# ==============================
# Configuración Stripe & IA
# ==============================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# ==============================
# Precios de acceso
# ==============================
PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}
LINK_DONACION = "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"

# ==============================
# Middleware
# ==============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ==============================
# SQL LOCAL
# ==============================
def query_sql(termino, zip_user=None):
    try:
        conn = sqlite3.connect("cost_estimates.db")
        cur = conn.cursor()
        q = f"%{termino.upper()}%"
        cur.execute("""
            SELECT cpt_code, description, state, zip_code, low_price, high_price
            FROM cost_estimates
            WHERE description LIKE ? OR cpt_code LIKE ?
            LIMIT 20
        """, (q, q))
        rows = cur.fetchall()
        conn.close()
        return rows if rows else "NO_DATA"
    except:
        return "SQL_ERROR"

# ==============================
# Home
# ==============================
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# ==============================
# ESTIMADO PRINCIPAL (REPROGRAMADO)
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    lang: str = Form("es"),
    zip_user: str = Form(None)
):
    datos_sql = query_sql(consulta, zip_user)

    prompt = f"""
ERES **AURA**, MOTOR DE INTELIGENCIA DE PRECIOS MÉDICOS Y DENTALES EN USA.
ACTÚAS COMO ANALISTA DE MERCADO PARA CONSUMIDORES.

CONSULTA: {consulta}
ZIP USUARIO: {zip_user}
DATOS BASE: {datos_sql}

IDIOMA: {lang}

INSTRUCCIONES OBLIGATORIAS:

1️⃣ DESGLOSA EL PROCEDIMIENTO (si son varios, sepáralos).
2️⃣ PRESENTA PRECIOS EN FORMATO REAL DE CONSUMIDOR:

PARA CADA NIVEL:
- ZIP CODE
- CONDADO
- ESTADO
- NACIONAL

EN CADA NIVEL MUESTRA **OBLIGATORIAMENTE**:

A) 💵 PAGO CASH (SIN SEGURO)
   - Mínimo
   - Promedio
   - Máximo
   - Comentario de negociación

B) 🏥 CON SEGURO
   - Precio facturado
   - Lo que normalmente cubre
   - Copago + deducible típico

C) ⚠️ SEGURO CON BAJA COBERTURA
   - Lo que el seguro NO cubre
   - Riesgo financiero real

3️⃣ PARA CADA NIVEL AGREGA:
📍 ZIP XXXXX
🗺️ Google Maps:
https://www.google.com/maps/search/?api=1&query=ZIP

4️⃣ AGREGA UNA SECCIÓN:
💡 ¿DÓNDE SE AHORRA MÁS DINERO Y POR QUÉ?

5️⃣ USA TABLAS, LISTAS Y EMOJIS CLAROS.
6️⃣ NO INVENTES CLÍNICAS.
7️⃣ SÉ CLARO, DIRECTO, CON CIFRAS ÚTILES.

CIERRA SIEMPRE CON:

🛡️ BLINDAJE LEGAL
Aura by May Roga LLC es una agencia independiente de información.
No somos médicos, clínicas ni aseguradoras.
No damos diagnósticos ni cotizaciones.
Este es un ESTIMADO EDUCATIVO basado en mercado y datos públicos.
El precio final lo define el proveedor.
"""

    try:
        r = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return {"resultado": r.choices[0].message.content}
    except Exception as e:
        return {"resultado": "No se pudo generar el estimado."}

# ==============================
# Stripe
# ==============================
@app.post("/create-checkout-session")
async def checkout(plan: str = Form(...)):
    if plan == "donacion":
        return {"url": LINK_DONACION}
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
            mode="payment",
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/"
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==============================
# Admin
# ==============================
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "ok"}
    return JSONResponse(status_code=401, content={"status": "error"})
