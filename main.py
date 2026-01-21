# ==============================
# AURA by May Roga LLC
# main.py — PRODUCCIÓN DEFINITIVA
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
import random

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
# OPENAI
# ==============================
openai.api_key = os.getenv("OPENAI_API_KEY")
client_gemini = None
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    try:
        from google import genai
        client_gemini = genai.Client(api_key=gemini_key)
    except:
        client_gemini = None

# ==============================
# DB UTILITIES
# ==============================
def get_conn():
    return sqlite3.connect(DB_PATH)

# ==============================
# INICIALIZAR BASE DE DATOS CON DATOS EDUCATIVOS
# ==============================
def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            code TEXT,
            cash_price_low REAL,
            cash_price_high REAL,
            insured_price_low REAL,
            insured_price_high REAL,
            copay_low REAL,
            copay_high REAL,
            state TEXT,
            zip_code TEXT,
            county TEXT,
            provider_type TEXT
        )
    """)
    conn.commit()

    # Si la tabla está vacía, llenarla con datos educativos de ejemplo
    cursor.execute("SELECT COUNT(*) FROM prices")
    count = cursor.fetchone()[0]
    if count == 0:
        estados = ["FL","NY","CA","TX","IL","PA","OH","GA","NC","MI"]
        counties = ["Miami-Dade","New York","Los Angeles","Harris","Cook","Philadelphia","Cuyahoga","Fulton","Mecklenburg","Wayne"]
        zip_codes = ["33160","10001","90001","77001","60601","19101","44101","30301","28201","48201"]
        procedimientos = [
            ("Consulta médica general","99213","Médico"),
            ("Evaluación anual preventiva","99396","Médico"),
            ("Ecografía abdominal","76700","Médico"),
            ("Resonancia magnética (MRI)","70551","Médico"),
            ("Consulta especializada cardiología","99243","Médico"),
            ("Limpieza dental rutinaria","D1110","Dental"),
            ("Radiografía bitewing","D0274","Dental"),
            ("Empaste simple resina","D2330","Dental"),
            ("Extracción dental simple","D7140","Dental"),
            ("Endodoncia molar","D3330","Dental")
        ]
        datos = []
        for _ in range(200):
            desc, code, prov_type = random.choice(procedimientos)
            state = random.choice(estados)
            county = random.choice(counties)
            zipc = random.choice(zip_codes)
            cash_low = random.randint(50,500)
            cash_high = cash_low + random.randint(20,200)
            insured_low = max(cash_low - random.randint(10,50),10)
            insured_high = max(cash_high - random.randint(10,100), insured_low)
            copay_low = max(insured_low*0.2,5)
            copay_high = max(insured_high*0.3,10)
            datos.append((desc, code, cash_low, cash_high, insured_low, insured_high, copay_low, copay_high, state, zipc, county, prov_type))
        cursor.executemany("""
            INSERT INTO prices (
                description, code, cash_price_low, cash_price_high,
                insured_price_low, insured_price_high,
                copay_low, copay_high,
                state, zip_code, county, provider_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, datos)
        conn.commit()
    conn.close()

init_db()

# ==============================
# FUNCION CEREBRO DE ESTIMADO
# ==============================
def estimado_cerebro(consulta, zip_user=None):
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM prices", conn)
    conn.close()
    term = consulta.lower()
    df_filtered = df[df['description'].str.lower().str.contains(term) | df['code'].str.contains(term)]
    
    resultado = {}

    # 3 locales más baratos
    if zip_user:
        local = df_filtered[df_filtered['zip_code'] == zip_user]
        resultado['local'] = local.nsmallest(3, 'cash_price_low')
    else:
        resultado['local'] = pd.DataFrame()

    # 3 más baratos por condado
    if zip_user and not resultado['local'].empty:
        county_val = resultado['local']['county'].iloc[0]
        county_df = df_filtered[df_filtered['county'] == county_val]
        resultado['county'] = county_df.nsmallest(3,'cash_price_low')
    else:
        resultado['county'] = pd.DataFrame()

    # 3 más baratos por estado
    if zip_user and not resultado['local'].empty:
        state_val = resultado['local']['state'].iloc[0]
        state_df = df_filtered[df_filtered['state'] == state_val]
        resultado['state'] = state_df.nsmallest(3,'cash_price_low')
    else:
        resultado['state'] = pd.DataFrame()

    # 5 más baratos nacionales
    resultado['national'] = df_filtered.nsmallest(5,'cash_price_low')

    # ==============================
    # CALCULO AHORROS (Cash vs Seguro vs Copago)
    # ==============================
    tablas = {}
    for nivel, df_tab in resultado.items():
        lista = []
        for _, row in df_tab.iterrows():
            ahorro_seguro = row['cash_price_low'] - row['insured_price_low']
            ahorro_copago = row['cash_price_low'] - row['copay_low']
            lista.append({
                "description": row['description'],
                "code": row['code'],
                "cash_low": row['cash_price_low'],
                "cash_high": row['cash_price_high'],
                "insured_low": row['insured_price_low'],
                "insured_high": row['insured_price_high'],
                "copay_low": row['copay_low'],
                "copay_high": row['copay_high'],
                "state": row['state'],
                "county": row['county'],
                "zip_code": row['zip_code'],
                "provider_type": row['provider_type'],
                "ahorro_seguro": ahorro_seguro,
                "ahorro_copago": ahorro_copago
            })
        tablas[nivel] = lista

    return tablas

# ==============================
# ENDPOINT ESTIMADO
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    lang: str = Form("es"),
    zip_user: str = Form(None),
):
    tablas = estimado_cerebro(consulta, zip_user)

    idiomas = {"es":"Español","en":"English","ht":"Haitian Creole"}
    idioma = idiomas.get(lang,"Español")

    return JSONResponse(content={
        "idioma": idioma,
        "consulta": consulta,
        "zip_user": zip_user,
        "tablas_comparativas": tablas,
        "blinda_legal": "Este reporte es educativo. No somos médicos ni aseguradoras. Los precios son estimados."
    })

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
    ADMIN_USER = os.getenv("ADMIN_USERNAME","admin")
    ADMIN_PASS = os.getenv("ADMIN_PASSWORD","admin")
    if user == ADMIN_USER and pw == ADMIN_PASS:
        return {"status":"success"}
    return JSONResponse(status_code=401, content={"status":"denied"})

