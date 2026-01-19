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

# Gemini seguro: si no hay key, no bloquea deploy
client_gemini = None
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    try:
        from google import genai
        client_gemini = genai.Client(api_key=gemini_api_key)
    except Exception as e:
        print(f"[WARNING] Gemini no inicializado: {e}")
else:
    print("[WARNING] GEMINI_API_KEY no encontrada, Gemini deshabilitado.")

# OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Precios de acceso
PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}
LINK_DONACION = "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ==============================
# FUNCIONES SQL Y CMS PUBLIC DATA
# ==============================

# Crear o actualizar base de datos desde CMS (mensual)
def ingest_cms_data():
    conn = sqlite3.connect("aura_brain.db")

    CMS_DATASETS = {
        "physician_fee": "https://data.cms.gov/resource/7b3x-3k6u.csv?$limit=50000",
        "outpatient": "https://data.cms.gov/resource/9wzi-peqs.csv?$limit=50000"
    }

    for name, url in CMS_DATASETS.items():
        try:
            print(f"Descargando dataset {name}...")
            df = pd.read_csv(url)

            # NORMALIZACIÓN
            df.columns = [c.lower() for c in df.columns]
            keep = [c for c in df.columns if c in ["hcpcs_code","cpt_code","payment_amount","state","locality"]]
            df = df[keep]
            df["source"] = name
            df["ingested_at"] = datetime.utcnow()

            df.to_sql("government_prices", conn, if_exists="append", index=False)
        except Exception as e:
            print(f"[ERROR INGESTA {name}] {e}")

    conn.close()
    print("✔ CMS data ingested")

# Consulta de precios legales
def get_estimated_price(code, state):
    conn = sqlite3.connect("aura_brain.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT AVG(payment_amount), MIN(payment_amount), MAX(payment_amount)
        FROM government_prices
        WHERE (hcpcs_code=? OR cpt_code=?) AND state=?
    """, (code, code, state))

    row = cur.fetchone()
    conn.close()

    if not row or row[0] is None:
        return None

    avg, min_p, max_p = row
    return {"average": round(avg,2), "min": round(min_p,2), "max": round(max_p,2)}

# Para precios dentales: solo rangos históricos y educativos
def dental_fair_price(low, high):
    return {"fair_min": round(low*0.9,2), "fair_max": round(high*1.1,2)}

# ==============================
# Función SQL local (existente)
# ==============================
def query_sql(termino, zip_user=None):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'cost_estimates.db')
        if not os.path.exists(db_path):
            return "SQL_OFFLINE"

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        busqueda = f"%{termino.strip().upper()}%"

        cursor.execute("""
        SELECT cpt_code, description, state, zip_code, low_price, high_price
        FROM cost_estimates
        WHERE description LIKE ? OR cpt_code LIKE ?
        ORDER BY low_price ASC
        LIMIT 20
        """, (busqueda, busqueda))
        results = cursor.fetchall()
        conn.close()

        if not results:
            return "DATO_NO_SQL"

        local, county, state, national = [], [], [], []
        for r in results:
            code, desc, state_r, zip_r, low, high = r
            if zip_user and zip_r == zip_user:
                local.append(r)
            elif zip_user and zip_r.startswith(zip_user[:3]):
                county.append(r)
            elif zip_user and state_r == zip_user[:2]:
                state.append(r)
            else:
                national.append(r)

        return {"local": local[:3], "county": county[:3], "state": state[:3], "national": national[:5]}

    except Exception as e:
        print(f"[ERROR SQL] {e}")
        return f"ERROR_SQL: {str(e)}"

# ==============================
# Ruta principal
# ==============================
@app.get("/", response_class=HTMLResponse)
async def read_index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

# ==============================
# Obtener estimado con IA + SQL + CMS
# ==============================
@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    # Ingesta CMS automática (puede ser un cron job mensual en producción)
    ingest_cms_data()

    datos_sql = query_sql(consulta, zip_user)
    idiomas = {"es": "Español", "en": "English", "ht": "Kreyòl (Haitian Creole)"}
    idioma_destino = idiomas.get(lang, "Español")

    prompt = f"""
ERES AURA, MOTOR DE ESTIMADOS DE PRECIOS MÉDICOS Y DENTALES DE MAY ROGA LLC.
IDIOMA: {idioma_destino}
DATOS SQL ENCONTRADOS: {datos_sql}
CONSULTA DEL USUARIO: {consulta}
ZIP DETECTADO: {zip_user}

OBJETIVO:
1) Usar datos públicos oficiales (CMS, Hospital Price Transparency) para calcular precios educativos.
2) Si es dental, usar rangos históricos y regionales, NO clínicas.
3) Comparar opciones locales, condado, estado, nacional.
4) Mostrar opción premium educativa.
5) Explicación clara y sencilla, resaltando en azul lo que el usuario preguntó.
6) Siempre contexto de ahorro y ventajas/desventajas.
7) Resumen final con BLINDAJE LEGAL:

BLINDAJE LEGAL
Este reporte es emitido por Aura by May Roga LLC,
agencia de información independiente.
No somos médicos, clínicas ni aseguradoras.
No damos diagnósticos ni cotizaciones.
Este es un ESTIMADO EDUCATIVO.
El proveedor final define el precio.
"""

    motores = []
    if client_gemini:
        try:
            modelos_gemini = client_gemini.models.list().data
            if modelos_gemini:
                motores.append(("gemini", modelos_gemini[0].name))
        except: pass
    motores.append(("openai", "gpt-4"))

    for motor, modelo in motores:
        try:
            if motor == "gemini" and client_gemini:
                response = client_gemini.models.generate_content(model=modelo, contents=prompt)
                return {"resultado": response.text}
            elif motor == "openai":
                response = openai.chat.completions.create(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                )
                return {"resultado": response.choices[0].message.content}
        except:
            continue

    return {"resultado": "Estimado generado automáticamente sin datos exactos SQL."}

# ==============================
# Crear sesión Stripe
# ==============================
@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    if plan.lower() == "donacion":
        return {"url": LINK_DONACION}
    try:
        mode = "subscription" if plan.lower() == "special" else "payment"
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[plan.lower()], "quantity": 1}],
            mode=mode,
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/"
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==============================
# Login Admin / Acceso gratuito
# ==============================
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    ADMIN_USER = os.getenv("ADMIN_USERNAME", "TU_USERNAME")
    ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "TU_PASSWORD")
    if user == ADMIN_USER and pw == ADMIN_PASS:
        return {"status": "success", "access": "full"}
    return JSONResponse(status_code=401, content={"status": "error"})
