import os
import sqlite3
import stripe
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime
import requests
import pandas as pd
import openai

# ==============================
# CARGA ENV
# ==============================
load_dotenv()

app = FastAPI()

# ==============================
# STRIPE
# ==============================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}

LINK_DONACION = "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"

# ==============================
# OPENAI
# ==============================
openai.api_key = os.getenv("OPENAI_API_KEY")

# ==============================
# CORS
# ==============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ==============================
# CMS DATA INGEST (UNA SOLA VEZ)
# ==============================
def ingest_cms_data():
    conn = sqlite3.connect("aura_brain.db")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS government_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        state TEXT,
        avg_price REAL,
        min_price REAL,
        max_price REAL,
        source TEXT,
        ingested_at TEXT
    )
    """)

    CMS_SAMPLES = [
        # ESTIMADOS EDUCATIVOS (NO CLÍNICAS)
        ("D2740", "FL", 900, 650, 1300, "Dental Market"),
        ("D2750", "FL", 1100, 800, 1600, "Dental Market"),
        ("D3310", "FL", 850, 600, 1200, "Dental Market"),
        ("D3320", "FL", 1100, 750, 1500, "Dental Market"),
    ]

    for c in CMS_SAMPLES:
        conn.execute("""
        INSERT INTO government_prices
        (code, state, avg_price, min_price, max_price, source, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (*c, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

# Crear DB solo si no existe
if not os.path.exists("aura_brain.db"):
    ingest_cms_data()

# ==============================
# CONSULTA PRECIO
# ==============================
def get_price_estimate(code, state="FL"):
    conn = sqlite3.connect("aura_brain.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT avg_price, min_price, max_price
    FROM government_prices
    WHERE code=? AND state=?
    """, (code, state))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "average": row[0],
        "min": row[1],
        "max": row[2]
    }

# ==============================
# INDEX
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# ==============================
# ESTIMADO PRINCIPAL
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    lang: str = Form("es"),
    zip_user: str = Form(None)
):
    consulta_upper = consulta.upper()

    # Detectar dental root canal + crown
    dental_codes = []
    if "ROOT" in consulta_upper or "CONDUCTO" in consulta_upper:
        dental_codes.append("D3310")
    if "CORONA" in consulta_upper or "CROWN" in consulta_upper:
        dental_codes.append("D2750")

    prices = []
    for code in dental_codes:
        p = get_price_estimate(code)
        if p:
            prices.append((code, p))

    # Fallback si no detecta código
    if not prices:
        prices = [
            ("D3310", get_price_estimate("D3310")),
            ("D2750", get_price_estimate("D2750"))
        ]

    # Construcción del texto (NO GENÉRICO)
    texto = f"""
🔍 ESTIMADO EDUCATIVO AURA — MIAMI, FL
Consulta: **{consulta}**
ZIP detectado: {zip_user or "No específico"}

-----------------------------------
💵 OPCIÓN CASH (SIN SEGURO)
"""

    total_min = 0
    total_max = 0

    for code, p in prices:
        if not p:
            continue
        texto += f"""
• Código {code}
  Rango: ${p['min']} – ${p['max']}
"""
        total_min += p["min"]
        total_max += p["max"]

    texto += f"""
➡️ TOTAL CASH ESTIMADO:
   ${total_min} – ${total_max}

-----------------------------------
🏥 CON SEGURO DENTAL PROMEDIO
• Copago típico: 40–60%
• Cobertura anual limitada ($1,000–$1,500)

➡️ COSTO REAL PARA EL PACIENTE:
   ${round(total_min*0.4)} – ${round(total_max*0.6)}

-----------------------------------
📍 COMPARACIÓN REGIONAL
• Miami ZIP {zip_user or "331xx"}: Más alto que promedio FL
• Florida: −10% a −15%
• Nacional: −15% a −25%

-----------------------------------
⭐ OPCIÓN PREMIUM EDUCATIVA
• Especialista endodoncista
• Corona zirconia / porcelana
• Tecnología digital

➡️ $3,200 – $4,500

-----------------------------------
🛡️ BLINDAJE LEGAL
Este reporte es emitido por Aura by May Roga LLC.
No somos médicos, clínicas ni aseguradoras.
No damos diagnósticos ni cotizaciones.
Este es un ESTIMADO EDUCATIVO basado en datos de mercado.
El proveedor final define el precio.
"""

    return {"resultado": texto}

# ==============================
# STRIPE CHECKOUT
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
# LOGIN ADMIN
# ==============================
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if (
        user == os.getenv("ADMIN_USERNAME", "admin")
        and pw == os.getenv("ADMIN_PASSWORD", "admin123")
    ):
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "error"})
