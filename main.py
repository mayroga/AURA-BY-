# ==============================
# AURA by May Roga LLC
# main.py — PRODUCCIÓN DEFINITIVO
# ==============================

import os
import sqlite3
import stripe
import pandas as pd
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
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
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
    except Exception as e:
        print(f"[WARN] Gemini no disponible: {e}")

# ==============================
# UTILIDADES DB
# ==============================
def get_conn():
    return sqlite3.connect(DB_PATH)

# ==============================
# INGESTA CMS (crudo, seguro)
# ==============================
def ingest_cms_data():
    conn = get_conn()

    CMS_DATASETS = {
        "physician_fee": "https://data.cms.gov/resource/7b3x-3k6u.csv?$limit=50000",
        "outpatient": "https://data.cms.gov/resource/9wzi-peqs.csv?$limit=50000"
    }

    for source, url in CMS_DATASETS.items():
        try:
            df = pd.read_csv(url)
            df.columns = [c.lower() for c in df.columns]

            cols = [c for c in ["hcpcs_code", "cpt_code", "payment_amount", "state", "locality"] if c in df.columns]
            df = df[cols]
            df["source"] = source
            df["ingested_at"] = datetime.utcnow()

            df.to_sql("government_prices", conn, if_exists="append", index=False)
            print(f"✔ CMS {source} cargado")
        except Exception as e:
            print(f"[CMS ERROR] {source}: {e}")

    conn.close()

# ==============================
# CONSULTA PRECIOS (ZIP, CONDADO, ESTADO, NACIONAL)
# ==============================
def query_prices(term, zip_user=None):
    conn = get_conn()
    cur = conn.cursor()

    like = f"%{term}%"
    cur.execute("""
        SELECT description, cpt_code, cash_price, insurance_price, copay_price, zip_code, county, state, provider_type
        FROM prices
        WHERE description LIKE ? OR cpt_code LIKE ?
        ORDER BY cash_price ASC
        LIMIT 100
    """, (like, like))

    rows = cur.fetchall()
    conn.close()

    local, county, state_list, national = [], [], [], []

    for r in rows:
        desc, code, cash, ins, copay, zipc, county_name, st, prov = r
        if zip_user and zipc == zip_user:
            local.append(r)
        elif zip_user and county_name:
            county.append(r)
        elif st:
            state_list.append(r)
        else:
            national.append(r)

    return {
        "zip": local[:3],
        "county": county[:3],
        "state": state_list[:3],
        "national": national[:5]
    }

# ==============================
# CONSULTA CMS (oficial)
# ==============================
def query_cms(code, state):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT AVG(payment_amount), MIN(payment_amount), MAX(payment_amount), state, locality
        FROM government_prices
        WHERE (hcpcs_code=? OR cpt_code=?)
        AND state=?
    """, (code, code, state))

    r = cur.fetchone()
    conn.close()

    if not r or r[0] is None:
        return None

    return {
        "average": round(r[0], 2),
        "min": round(r[1], 2),
        "max": round(r[2], 2),
        "state": r[3],
        "county": r[4]
    }

# ==============================
# INDEX
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
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
    ingest_cms_data()
    datos_prices = query_prices(consulta, zip_user)

    idiomas = {"es": "Español", "en": "English", "ht": "Haitian Creole"}
    idioma = idiomas.get(lang, "Español")

    # Prompt maestro
    prompt = f"""
ERES AURA, MOTOR DE ESTIMADOS DE PRECIOS MÉDICOS Y DENTALES DE MAY ROGA LLC.

IDIOMA: {idioma}
CONSULTA DEL USUARIO: <consulta>{consulta}</consulta>
ZIP DETECTADO: {zip_user}

DATOS EDUCATIVOS DE MERCADO:
{datos_prices}

INSTRUCCIONES:
- Mostrar 3 más baratos por ZIP
- Mostrar 3 más baratos por condado
- Mostrar 3 más baratos por estado
- Mostrar 5 más baratos de los 50 estados
- Mostrar ZIP, condado, estado en todos los resultados
- Comparar Cash vs Seguro vs Copagos
- Mostrar ahorros exactos en números
- Lenguaje claro y directo
- Actuar como asesor experto en precios, seguros, legales
- Si no hay datos exactos, generar estimados usando ADA/AMA

BLINDAJE LEGAL:
Este reporte es educativo, no médico ni cotización oficial.
Los precios pueden variar según proveedor y seguro.
"""

    # Motores IA
    motores = []
    if client_gemini:
        try:
            models = client_gemini.models.list().data
            if models:
                motores.append(("gemini", models[0].name))
        except:
            pass

    motores.append(("openai", "gpt-4"))

    for motor, modelo in motores:
        try:
            if motor == "gemini":
                r = client_gemini.models.generate_content(model=modelo, contents=prompt)
                return HTMLResponse(content=r.text)

            if motor == "openai":
                r = openai.chat.completions.create(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                )
                return HTMLResponse(content=r.choices[0].message.content)
        except:
            continue

    return HTMLResponse(content="<p>Estimado generado sin datos exactos disponibles. Se muestra información educativa.</p>")

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
    ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin")

    if user == ADMIN_USER and pw == ADMIN_PASS:
        return {"status": "success"}

    return JSONResponse(status_code=401, content={"status": "denied"})
