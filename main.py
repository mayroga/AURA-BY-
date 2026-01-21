# ==============================
# AURA by May Roga LLC
# main.py — PRODUCCIÓN DEFINITIVA
# ==============================

import os
import sqlite3
import stripe
from datetime import datetime

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

import openai
from dotenv import load_dotenv

# ==============================
# CARGA ENV
# ==============================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "aura_brain.db")

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

# Gemini ES OPCIONAL
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
# DB
# ==============================
def get_conn():
    return sqlite3.connect(DB_PATH)

def query_prices(term, zip_user=None):
    """
    Consulta educativa interna (si existe).
    Si no hay datos → devuelve vacío (NO error).
    """
    try:
        conn = get_conn()
        cur = conn.cursor()

        like = f"%{term}%"
        cur.execute("""
            SELECT description, cpt_code, low_price, high_price, state, zip_code
            FROM prices
            WHERE description LIKE ? OR cpt_code LIKE ?
            ORDER BY low_price ASC
            LIMIT 20
        """, (like, like))

        rows = cur.fetchall()
        conn.close()

        return rows if rows else []

    except Exception:
        return []

# ==============================
# INDEX
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()

# ==============================
# ESTIMADO PRINCIPAL (NUNCA FALLA)
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    lang: str = Form("es"),
    zip_user: str = Form(None),
):

    datos_locales = query_prices(consulta, zip_user)

    idiomas = {
        "es": "Español",
        "en": "English",
        "ht": "Haitian Creole"
    }
    idioma = idiomas.get(lang, "Español")

    # ==============================
    # PROMPT MAESTRO AURA
    # ==============================
    prompt = f"""
ERES **AURA**, EL CEREBRO DE ESTIMADOS DE MAY ROGA LLC.

IDIOMA: {idioma}
CONSULTA DEL CLIENTE: {consulta}
UBICACIÓN (ZIP): {zip_user}

FUENTES DE REFERENCIA PROFESIONAL (NO DIGAS LAS FUENTES EXPLÍCITAMENTE):
- Procedimientos MÉDICOS → marco AMA (American Medical Association)
- Procedimientos DENTALES → marco ADA (American Dental Association)
- Precios CMS → solo como referencia pública secundaria
- Mercado privado USA → clínicas, cash prices, self-pay

DATOS INTERNOS DISPONIBLES:
{datos_locales if datos_locales else "No hay datos exactos en base interna"}

INSTRUCCIONES CRÍTICAS:
1. SI NO HAY DATOS EXACTOS → GENERA EL ESTIMADO IGUAL.
2. CREA RANGOS REALISTAS DE USA (LOW / MID / HIGH).
3. COMPARA:
   - Precio CASH
   - Precio con SEGURO (estimado típico)
4. SI ES DENTAL → prioriza lógica ADA.
5. SI ES MÉDICO → prioriza lógica AMA.
6. NO menciones IA, CMS, ADA ni AMA por nombre.
7. Usa tablas, bullets y claridad.
8. TONO: experto, protector del consumidor.

BLINDAJE LEGAL OBLIGATORIO (INCLÚYELO):
Este reporte es emitido por Aura by May Roga LLC.
No somos médicos, clínicas ni aseguradoras.
No brindamos diagnósticos ni cotizaciones.
Este es un ESTIMADO EDUCATIVO.
El proveedor final determina el precio real.
"""

    # ==============================
    # MOTOR DE EJECUCIÓN (FALLBACK REAL)
    # ==============================
    # 1️⃣ Gemini si existe
    if client_gemini:
        try:
            r = client_gemini.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt
            )
            return {"resultado": r.text}
        except Exception as e:
            print(f"[WARN] Gemini falló: {e}")

    # 2️⃣ OpenAI SIEMPRE
    try:
        r = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
        )
        return {"resultado": r.choices[0].message.content}
    except Exception as e:
        return {
            "resultado": f"""
⚠️ Aura generó un estimado general de mercado.

Procedimiento: {consulta}

Rango típico USA:
- Bajo: $XXX
- Medio: $XXX
- Alto: $XXX

Este es un estimado educativo.
"""
        }

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
